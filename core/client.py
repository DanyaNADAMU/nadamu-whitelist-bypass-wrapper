"""
Client interface for WhitelistBypass Core.
Communicates with the Core daemon over Unix Domain Socket or local HTTP,
with a seamless in-process fallback when the daemon is offline.
"""

from dataclasses import asdict
import http.client
import json
import os
from pathlib import Path
import socket
from typing import Any, Optional
from urllib.parse import urlencode

from core.config import CoreConfig, config as default_config
from core.models import CommandResult, ProviderType, UserSummary
from core.services.qr_service import QrService
from core.services.tunnel_service import TunnelService
from core.services.user_service import UserService


class UnixHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection over Unix Domain Socket using standard socket library."""

    def __init__(self, socket_path: str, timeout: float = 30.0):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        self.sock = sock


class CoreClient:
    def __init__(self, cfg: Optional[CoreConfig] = None):
        self.config = cfg or default_config
        self.user_service = UserService(self.config)
        self.tunnel_service = TunnelService(self.config, self.user_service)
        self.qr_service = QrService()

    def is_daemon_running(self) -> bool:
        """Check whether the Core daemon socket is accessible and healthy."""
        if not self.config.socket_path.exists():
            return False

        try:
            conn = UnixHTTPConnection(str(self.config.socket_path), timeout=1.0)
            conn.request("GET", "/api/v1/health")
            resp = conn.getresponse()
            conn.close()
            return resp.status == 200
        except Exception:
            return False

    def _daemon_request(
        self, method: str, path: str, payload: Optional[dict[str, Any]] = None, timeout: float = 35.0
    ) -> Optional[dict[str, Any]]:
        """Perform an HTTP request to the Core daemon via UDS."""
        if not self.config.socket_path.exists():
            return None

        try:
            conn = UnixHTTPConnection(str(self.config.socket_path), timeout=timeout)
            body = json.dumps(payload) if payload is not None else None
            headers = {"Content-Type": "application/json"} if body is not None else {}
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read().decode("utf-8")
            conn.close()
            return json.loads(data) if data else {}
        except Exception:
            return None

    def execute_command(self, command: str, **kwargs: Any) -> CommandResult:
        """
        Execute command via Core daemon if running; otherwise fallback directly to in-process logic.
        """
        clean_cmd = command.strip().lower()

        # Try daemon first
        if self.is_daemon_running():
            payload = {"command": clean_cmd, "params": kwargs}
            res = self._daemon_request("POST", "/api/v1/commands/exec", payload=payload)
            if res and isinstance(res, dict) and "success" in res:
                return CommandResult(
                    success=res.get("success", False),
                    command=res.get("command", clean_cmd),
                    user=res.get("user"),
                    message=res.get("message", ""),
                    data=res.get("data"),
                    error=res.get("error"),
                )

        # In-process execution fallback
        return self.execute_direct(clean_cmd, **kwargs)

    def execute_direct(self, command: str, **kwargs: Any) -> CommandResult:
        """Direct in-process execution using core services."""
        user = kwargs.get("user")
        qr_requested = kwargs.get("qr", False)

        if command in ("link", "get-link"):
            if not user:
                return CommandResult(False, command, None, error="Username is required")
            if not self.user_service.user_exists(user):
                return CommandResult(False, command, user, error=f"User directory not found: {user}")

            conf = self.user_service.load_user_conf(user)
            status = self.tunnel_service.get_status(user)
            summary = self.user_service.get_user_summary(user, status)

            if not summary.link:
                return CommandResult(
                    False,
                    command,
                    user,
                    message=f"Conference link has not been provisioned yet for user '{user}'.",
                    error="No active conference link. Run 'rotate' to create one.",
                    data=summary.to_dict(),
                )

            data = summary.to_dict()
            if qr_requested:
                data["qr_ansi"] = self.qr_service.render_ansi(summary.link)
                data["qr_png"] = self.qr_service.render_png_base64(summary.link)

            return CommandResult(
                True,
                command,
                user,
                message=f"Link retrieved for user {user}",
                data=data,
            )

        elif command == "qr":
            if not user:
                return CommandResult(False, command, None, error="Username is required")
            if not self.user_service.user_exists(user):
                return CommandResult(False, command, user, error=f"User directory not found: {user}")

            status = self.tunnel_service.get_status(user)
            summary = self.user_service.get_user_summary(user, status)
            if not summary.link:
                return CommandResult(
                    False,
                    command,
                    user,
                    error=f"Conference link not provisioned for user '{user}'. Run rotate first.",
                )

            data = summary.to_dict()
            data["qr_ansi"] = self.qr_service.render_ansi(summary.link)
            data["qr_png"] = self.qr_service.render_png_base64(summary.link)
            return CommandResult(True, command, user, message="QR code generated", data=data)

        elif command == "rotate":
            if not user:
                return CommandResult(False, command, None, error="Username is required")
            if not self.user_service.user_exists(user):
                return CommandResult(False, command, user, error=f"User directory not found: {user}")

            ok, new_link, err = self.tunnel_service.rotate_room_sync(user)
            if not ok or not new_link:
                return CommandResult(False, command, user, error=err or "Failed to rotate room")

            status = self.tunnel_service.get_status(user)
            summary = self.user_service.get_user_summary(user, status)
            data = summary.to_dict()
            if qr_requested:
                data["qr_ansi"] = self.qr_service.render_ansi(new_link)
                data["qr_png"] = self.qr_service.render_png_base64(new_link)

            return CommandResult(
                True,
                command,
                user,
                message=f"New room provisioned for user '{user}'",
                data=data,
            )

        elif command in ("provider", "set-provider"):
            if not user:
                return CommandResult(False, command, None, error="Username is required")
            provider = kwargs.get("provider")
            if not provider:
                return CommandResult(False, command, user, error="Provider argument is required")
            provider = provider.lower().strip()
            if provider not in ProviderType.values():
                return CommandResult(
                    False,
                    command,
                    user,
                    error=f"Unknown provider '{provider}'. Supported: {', '.join(ProviderType.values())}",
                )

            if not self.user_service.user_exists(user):
                return CommandResult(False, command, user, error=f"User directory not found: {user}")

            self.user_service.set_user_provider(user, provider)
            cookie_info = self.user_service.resolve_cookie_file(user, provider)

            do_rotate = kwargs.get("rotate", False)
            rotate_data = None
            if do_rotate:
                ok, new_link, err = self.tunnel_service.rotate_room_sync(user)
                if not ok:
                    return CommandResult(
                        False,
                        command,
                        user,
                        error=f"Provider set to '{provider}', but room rotation failed: {err}",
                    )
                rotate_data = {"new_link": new_link}

            status = self.tunnel_service.get_status(user)
            summary = self.user_service.get_user_summary(user, status)
            data = summary.to_dict()
            data["cookie_warning"] = (
                not cookie_info.valid
                or f"Missing or empty cookies for {provider}"
                if not cookie_info.valid
                else None
            )
            if rotate_data:
                data.update(rotate_data)
                if qr_requested:
                    data["qr_ansi"] = self.qr_service.render_ansi(data["link"])

            return CommandResult(
                True,
                command,
                user,
                message=f"Provider for user '{user}' set to '{provider}'",
                data=data,
            )

        elif command == "list":
            users = self.user_service.list_users()
            summaries = []
            for u in users:
                status = self.tunnel_service.get_status(u)
                s = self.user_service.get_user_summary(u, status)
                summaries.append(s.to_dict())

            return CommandResult(
                True,
                command,
                None,
                message=f"Found {len(summaries)} user(s)",
                data={"users": summaries},
            )

        elif command == "status":
            if not user:
                return CommandResult(False, command, None, error="Username is required")
            if not self.user_service.user_exists(user):
                return CommandResult(False, command, user, error=f"User directory not found: {user}")

            status = self.tunnel_service.get_status(user)
            summary = self.user_service.get_user_summary(user, status)
            conf = self.user_service.load_user_conf(user)
            journal = self.tunnel_service.get_journal(user, lines=10)

            data = summary.to_dict()
            data["config"] = conf.to_dict()
            data["journal_tail"] = journal

            return CommandResult(True, command, user, message=f"Status: {status}", data=data)

        elif command in ("start", "stop", "restart"):
            if not user:
                return CommandResult(False, command, None, error="Username is required")
            if not self.user_service.user_exists(user):
                return CommandResult(False, command, user, error=f"User directory not found: {user}")

            if command == "start":
                ok, msg = self.tunnel_service.start(user)
            elif command == "stop":
                ok, msg = self.tunnel_service.stop(user)
            else:
                ok, msg = self.tunnel_service.restart(user)

            status = self.tunnel_service.get_status(user)
            return CommandResult(
                ok,
                command,
                user,
                message=f"Service {command} action: {msg}",
                data={"service_status": status},
                error=None if ok else msg,
            )

        elif command == "is-active":
            if not user:
                return CommandResult(False, command, None, error="Username is required")
            status = self.tunnel_service.get_status(user)
            is_active = status in ("active", "activating")
            return CommandResult(
                is_active,
                command,
                user,
                message=status,
                data={"active": is_active, "status": status},
            )

        elif command == "run":
            if not user:
                return CommandResult(False, command, None, error="Username is required")
            self.tunnel_service.run_creator(user)
            return CommandResult(True, command, user, message="Creator finished")

        return CommandResult(False, command, user, error=f"Unknown command '{command}'")
