"""
Configuration settings and directory path resolution for WhitelistBypass Core.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional


@dataclass
class CoreConfig:
    conf_dir: Path
    bin_dir: Path
    users_dir: Path
    socket_dir: Path
    socket_path: Path
    http_host: str
    http_port: int
    http_enabled: bool
    service_user: str
    service_group: str
    core_env_path: Path


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a simple bash-style env file (KEY=VALUE)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values

    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (
                    val.startswith("'") and val.endswith("'")
                ):
                    val = val[1:-1]
                values[key] = val
    except Exception:
        pass
    return values


def load_config() -> CoreConfig:
    """Load core configuration from environment and optional core.env."""
    conf_dir = Path(os.environ.get("WLB_CONF_DIR", "/etc/whitelist-bypass"))
    core_env_path = conf_dir / "core.env"
    file_env = _parse_env_file(core_env_path)

    def get_val(name: str, default: str) -> str:
        # Priority: explicit os.environ > core.env file > default
        return os.environ.get(name, file_env.get(name, default))

    bin_dir = Path(get_val("WLB_BIN_DIR", "/opt/whitelist-bypass/bin"))
    users_dir = Path(get_val("WLB_USERS_DIR", str(conf_dir / "users")))
    socket_dir = Path(get_val("WLB_SOCKET_DIR", "/run/whitelist-bypass"))
    socket_path = Path(get_val("WLB_SOCKET_PATH", str(socket_dir / "core.sock")))

    http_host = get_val("WLB_HTTP_HOST", "127.0.0.1")
    http_port_str = get_val("WLB_HTTP_PORT", "8080")
    try:
        http_port = int(http_port_str)
    except ValueError:
        http_port = 8080

    http_enabled_raw = get_val("WLB_HTTP_ENABLED", "false").lower()
    http_enabled = http_enabled_raw in ("1", "true", "yes")

    service_user = get_val("WLB_SERVICE_USER", "whitelist-bypass")
    service_group = get_val("WLB_SERVICE_GROUP", "whitelist-bypass")

    return CoreConfig(
        conf_dir=conf_dir,
        bin_dir=bin_dir,
        users_dir=users_dir,
        socket_dir=socket_dir,
        socket_path=socket_path,
        http_host=http_host,
        http_port=http_port,
        http_enabled=http_enabled,
        service_user=service_user,
        service_group=service_group,
        core_env_path=core_env_path,
    )


# Default global instance
config = load_config()
