"""
Tunnel management service for WhitelistBypass Core.
Supervises systemd services, room rotations, and direct creator binary execution.
"""

import asyncio
import grp
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import threading
import time
from typing import Optional
from core.config import CoreConfig, config as default_config
from core.services.user_service import UserService


class TunnelService:
    def __init__(self, cfg: Optional[CoreConfig] = None, user_service: Optional[UserService] = None):
        self.config = cfg or default_config
        self.user_service = user_service or UserService(self.config)
        self._async_locks: dict[str, asyncio.Lock] = {}
        self._sync_locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _chown_service(self, path: Path) -> None:
        """Ensure file is owned by service_user:service_group if running as root."""
        if os.geteuid() == 0:
            try:
                uid = pwd.getpwnam(self.config.service_user).pw_uid
                gid = grp.getgrnam(self.config.service_group).gr_gid
                os.chown(path, uid, gid)
            except Exception:
                pass

    def get_unit_name(self, username: str) -> str:
        return f"whitelist-bypass@{username}.service"

    def _get_sync_lock(self, username: str) -> threading.Lock:
        with self._locks_guard:
            if username not in self._sync_locks:
                self._sync_locks[username] = threading.Lock()
            return self._sync_locks[username]

    def _get_async_lock(self, username: str) -> asyncio.Lock:
        with self._locks_guard:
            if username not in self._async_locks:
                self._async_locks[username] = asyncio.Lock()
            return self._async_locks[username]

    def _run_cmd(self, cmd: list[str]) -> tuple[int, str, str]:
        """Execute a system command, elevating with sudo if not root."""
        full_cmd = list(cmd)
        if os.geteuid() != 0 and cmd[0] in ("systemctl", "journalctl"):
            full_cmd = ["sudo"] + full_cmd

        proc = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

    def get_status(self, username: str) -> str:
        """Check whether user tunnel service is active."""
        if not shutil.which("systemctl"):
            return "unknown"
        unit = self.get_unit_name(username)
        code, stdout, _ = self._run_cmd(["systemctl", "is-active", unit])
        status = stdout.strip()
        return status if status else "inactive"

    def get_journal(self, username: str, lines: int = 15) -> str:
        """Fetch recent journal entries for a user's unit."""
        if not shutil.which("journalctl"):
            return ""
        unit = self.get_unit_name(username)
        _, stdout, stderr = self._run_cmd(
            ["journalctl", "-u", unit, "-n", str(lines), "--no-pager"]
        )
        return stdout or stderr

    def start(self, username: str) -> tuple[bool, str]:
        """Start user tunnel service."""
        unit = self.get_unit_name(username)
        code, stdout, stderr = self._run_cmd(["systemctl", "start", unit])
        return (code == 0, stderr if code != 0 else "Started")

    def stop(self, username: str) -> tuple[bool, str]:
        """Stop user tunnel service."""
        unit = self.get_unit_name(username)
        code, stdout, stderr = self._run_cmd(["systemctl", "stop", unit])
        return (code == 0, stderr if code != 0 else "Stopped")

    def restart(self, username: str) -> tuple[bool, str]:
        """Restart user tunnel service."""
        unit = self.get_unit_name(username)
        code, stdout, stderr = self._run_cmd(["systemctl", "restart", unit])
        return (code == 0, stderr if code != 0 else "Restarted")

    def rotate_room_sync(self, username: str, timeout: int = 20) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Synchronous conference room rotation with per-user locking.
        Stops service, purges old room links, restarts service, and awaits native --write-file.
        Returns (success, new_link, error_message).
        """
        if not self.user_service.user_exists(username):
            return False, None, f"User '{username}' does not exist"

        lock = self._get_sync_lock(username)
        with lock:
            user_dir = self.user_service.get_user_dir(username)
            room_env = user_dir / "room.env"
            current_link_file = user_dir / "current_link"
            unit = self.get_unit_name(username)

            # 1. Stop existing service
            self.stop(username)

            # 2. Remove obsolete room files
            if room_env.exists():
                room_env.unlink(missing_ok=True)
            if current_link_file.exists():
                current_link_file.unlink(missing_ok=True)

            # 3. Start service to provision new room
            ok, err = self.start(username)
            if not ok:
                return False, None, f"Failed to start service {unit}: {err}"

            # 4. Poll for provisioned link
            interval = 0.2
            max_steps = int(timeout / interval)
            new_link: Optional[str] = None

            for _ in range(max_steps):
                if current_link_file.is_file():
                    try:
                        content = current_link_file.read_text(encoding="utf-8").strip()
                        if content:
                            lines = [l.strip() for l in content.splitlines() if l.strip()]
                            if lines:
                                new_link = lines[-1]
                                break
                    except Exception:
                        pass

                # Check if service exited prematurely
                status = self.get_status(username)
                if status not in ("active", "activating"):
                    journal = self.get_journal(username, lines=15)
                    return (
                        False,
                        None,
                        f"Service {unit} exited prematurely with status '{status}':\n{journal}",
                    )

                time.sleep(interval)

            if not new_link:
                journal = self.get_journal(username, lines=15)
                return (
                    False,
                    None,
                    f"Timeout ({timeout}s) waiting for room link from media server:\n{journal}",
                )

            # 5. Persist provisioned link
            self.user_service.save_room_link(username, new_link)
            return True, new_link, None

    async def rotate_room_async(self, username: str, timeout: int = 20) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Asynchronous conference room rotation utilizing asyncio.Lock and run_in_executor.
        """
        async_lock = self._get_async_lock(username)
        async with async_lock:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.rotate_room_sync, username, timeout)

    def run_creator(self, username: str) -> None:
        """
        Internal daemon runner invoked by systemd template unit.
        Prepares environment and replaces current process via os.execv.
        """
        if not self.user_service.user_exists(username):
            raise ValueError(f"User '{username}' not found in {self.config.users_dir}")

        user_dir = self.user_service.get_user_dir(username)
        user_conf = self.user_service.load_user_conf(username)
        provider = user_conf.provider.lower()

        cookie_info = self.user_service.resolve_cookie_file(username, provider)
        if not cookie_info.exists:
            raise FileNotFoundError(
                f"Cookie file for provider '{provider}' not found in {user_dir}. "
                f"Expected: cookies-{provider}.json or cookies.json"
            )

        if not cookie_info.valid:
            raise ValueError(
                f"Cookie file '{cookie_info.file_name}' is empty or an unpopulated stub ({cookie_info.size_bytes} bytes). "
                f"Export valid authenticated session cookies from your browser."
            )

        binary_map = {
            "telemost": "headless-telemost-creator",
            "vk": "headless-vk-creator",
            "wbstream": "headless-wbstream-creator",
            "dion": "headless-dion-creator",
        }

        if provider not in binary_map:
            raise ValueError(
                f"Unknown provider '{provider}'. Supported: {', '.join(binary_map.keys())}"
            )

        binary_name = binary_map[provider]
        binary_path = self.config.bin_dir / binary_name

        if not binary_path.is_file() or not os.access(binary_path, os.X_OK):
            raise FileNotFoundError(
                f"Binary {binary_path} not found or lacks executable permissions."
            )

        current_link_file = user_dir / "current_link"
        room_info = self.user_service.load_room_info(username)
        call_link = room_info.call_link

        args: list[str] = [
            str(binary_path),
            "--cookies",
            str(cookie_info.file_path),
            "--write-file",
            str(current_link_file),
            "--resources",
            user_conf.resources,
        ]

        if user_conf.upstream_socks:
            args.extend(["--upstream-socks", user_conf.upstream_socks])
        if user_conf.upstream_user:
            args.extend(["--upstream-user", user_conf.upstream_user])
        if user_conf.upstream_pass:
            args.extend(["--upstream-pass", user_conf.upstream_pass])
        if user_conf.debug:
            args.append("--debug")
        if user_conf.allow_private_dst:
            args.append("--allow-private-dst")

        if provider == "telemost":
            if call_link:
                args.extend(["--tm-link", call_link])
        elif provider == "vk":
            if call_link:
                args.extend(["--vk-link", call_link])
            if user_conf.peer_id:
                args.extend(["--peer-id", user_conf.peer_id])
        elif provider in ("wbstream", "dion"):
            if call_link:
                args.extend(["--room", call_link])
            if user_conf.display_name:
                args.extend(["--name", user_conf.display_name])

        # Truncate / touch current_link file with 0644
        current_link_file.unlink(missing_ok=True)
        current_link_file.touch(mode=0o644)
        self._chown_service(current_link_file)

        # Replace process image
        os.execv(str(binary_path), args)
