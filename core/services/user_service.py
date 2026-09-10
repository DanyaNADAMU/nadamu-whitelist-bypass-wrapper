"""
User management service for WhitelistBypass Core.
Handles user profiles, configuration parsing, cookie resolution, and room data.
"""

from pathlib import Path
from typing import Optional
from core.config import CoreConfig, config as default_config
from core.models import CookieInfo, RoomInfo, UserConfig, UserSummary


class UserService:
    def __init__(self, cfg: Optional[CoreConfig] = None):
        self.config = cfg or default_config

    def list_users(self) -> list[str]:
        """Return list of configured usernames sorted alphabetically."""
        if not self.config.users_dir.is_dir():
            return []
        users = [
            p.name
            for p in self.config.users_dir.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ]
        return sorted(users)

    def user_exists(self, username: str) -> bool:
        """Check if a user directory exists."""
        if not username or "/" in username or "\\" in username:
            return False
        return (self.config.users_dir / username).is_dir()

    def get_user_dir(self, username: str) -> Path:
        """Return path to user directory."""
        return self.config.users_dir / username

    def load_user_conf(self, username: str) -> UserConfig:
        """Load and parse user.conf for the specified user."""
        user_dir = self.get_user_dir(username)
        conf_file = user_dir / "user.conf"
        user_conf = UserConfig()

        if not conf_file.is_file():
            return user_conf

        try:
            content = conf_file.read_text(encoding="utf-8")
            raw_lines: dict[str, str] = {}
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if (v.startswith('"') and v.endswith('"')) or (
                        v.startswith("'") and v.endswith("'")
                    ):
                        v = v[1:-1]
                    raw_lines[k] = v

            user_conf.raw_values = raw_lines
            if "PROVIDER" in raw_lines:
                user_conf.provider = raw_lines["PROVIDER"].lower()
            if "RESOURCES" in raw_lines:
                user_conf.resources = raw_lines["RESOURCES"]
            if "UPSTREAM_SOCKS" in raw_lines:
                user_conf.upstream_socks = raw_lines["UPSTREAM_SOCKS"] or None
            if "UPSTREAM_USER" in raw_lines:
                user_conf.upstream_user = raw_lines["UPSTREAM_USER"] or None
            if "UPSTREAM_PASS" in raw_lines:
                user_conf.upstream_pass = raw_lines["UPSTREAM_PASS"] or None
            if "DISPLAY_NAME" in raw_lines:
                user_conf.display_name = raw_lines["DISPLAY_NAME"]
            if "PEER_ID" in raw_lines:
                user_conf.peer_id = raw_lines["PEER_ID"] or None
            if "ALLOW_PRIVATE_DST" in raw_lines:
                user_conf.allow_private_dst = raw_lines["ALLOW_PRIVATE_DST"].lower() in (
                    "true",
                    "1",
                    "yes",
                )
            if "DEBUG" in raw_lines:
                user_conf.debug = raw_lines["DEBUG"].lower() in ("true", "1", "yes")
            if "TELEGRAM_ID" in raw_lines and raw_lines["TELEGRAM_ID"]:
                try:
                    user_conf.telegram_id = int(raw_lines["TELEGRAM_ID"])
                except ValueError:
                    pass
            if "VK_ID" in raw_lines and raw_lines["VK_ID"]:
                try:
                    user_conf.vk_id = int(raw_lines["VK_ID"])
                except ValueError:
                    pass
        except Exception:
            pass

        return user_conf

    def set_user_provider(self, username: str, provider: str) -> None:
        """Update PROVIDER setting in user.conf."""
        user_dir = self.get_user_dir(username)
        conf_file = user_dir / "user.conf"
        clean_provider = provider.strip().lower()

        if conf_file.is_file():
            content = conf_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            found = False
            new_lines = []
            for line in lines:
                if line.strip().startswith("PROVIDER="):
                    new_lines.append(f'PROVIDER="{clean_provider}"')
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                new_lines.append(f'PROVIDER="{clean_provider}"')
            conf_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        else:
            conf_file.write_text(f'PROVIDER="{clean_provider}"\n', encoding="utf-8")
            conf_file.chmod(0o600)

    def resolve_cookie_file(self, username: str, provider: str) -> CookieInfo:
        """
        Locate cookie file with prioritized fallback:
        1. cookies-<provider>.json
        2. cookies-yandex.json (if telemost)
        3. cookies.json
        Validates content size > 15 bytes.
        """
        user_dir = self.get_user_dir(username)
        candidates = [user_dir / f"cookies-{provider}.json"]
        if provider == "telemost":
            candidates.append(user_dir / "cookies-yandex.json")
        candidates.append(user_dir / "cookies.json")

        # 1. Prefer files with size > 15 bytes
        for candidate in candidates:
            if candidate.is_file():
                sz = candidate.stat().st_size
                if sz > 15:
                    return CookieInfo(
                        file_path=str(candidate),
                        file_name=candidate.name,
                        exists=True,
                        valid=True,
                        size_bytes=sz,
                    )

        # 2. Fallback to existing candidate so caller can report empty stub error
        for candidate in candidates:
            if candidate.is_file():
                sz = candidate.stat().st_size
                return CookieInfo(
                    file_path=str(candidate),
                    file_name=candidate.name,
                    exists=True,
                    valid=False,
                    size_bytes=sz,
                )

        return CookieInfo(
            file_path=None,
            file_name=None,
            exists=False,
            valid=False,
            size_bytes=0,
        )

    def load_room_info(self, username: str) -> RoomInfo:
        """Load active conference link from room.env and current_link."""
        user_dir = self.get_user_dir(username)
        room_file = user_dir / "room.env"
        current_link_file = user_dir / "current_link"

        call_link: Optional[str] = None
        current_link: Optional[str] = None

        if room_file.is_file():
            try:
                for line in room_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("CALL_LINK=") or line.startswith("TM_LINK="):
                        val = line.split("=", 1)[1].strip()
                        if (val.startswith('"') and val.endswith('"')) or (
                            val.startswith("'") and val.endswith("'")
                        ):
                            val = val[1:-1]
                        if val:
                            call_link = val
            except Exception:
                pass

        if current_link_file.is_file():
            try:
                content = current_link_file.read_text(encoding="utf-8").strip()
                if content:
                    lines = [l.strip() for l in content.splitlines() if l.strip()]
                    if lines:
                        current_link = lines[-1]
            except Exception:
                pass

        return RoomInfo(call_link=call_link, current_link=current_link)

    def save_room_link(self, username: str, link: str) -> None:
        """Persist newly provisioned conference link into room.env."""
        user_dir = self.get_user_dir(username)
        room_file = user_dir / "room.env"
        room_file.write_text(f'CALL_LINK="{link.strip()}"\n', encoding="utf-8")
        room_file.chmod(0o600)

    def resolve_identity(
        self, telegram_id: Optional[int] = None, vk_id: Optional[int] = None
    ) -> Optional[str]:
        """Resolve a user profile by Telegram or VK ID."""
        if not telegram_id and not vk_id:
            return None

        for user in self.list_users():
            conf = self.load_user_conf(user)
            if telegram_id is not None and conf.telegram_id == telegram_id:
                return user
            if vk_id is not None and conf.vk_id == vk_id:
                return user
        return None

    def get_user_summary(self, username: str, service_status: str = "unknown") -> UserSummary:
        """Assemble an overview of user status, configuration, and link."""
        conf = self.load_user_conf(username)
        room = self.load_room_info(username)
        cookie = self.resolve_cookie_file(username, conf.provider)

        return UserSummary(
            username=username,
            provider=conf.provider,
            service_status=service_status,
            link=room.active_link,
            cookie_valid=cookie.valid,
            cookie_file=cookie.file_name,
            cookie_size=cookie.size_bytes,
            telegram_id=conf.telegram_id,
            vk_id=conf.vk_id,
        )
