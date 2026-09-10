"""
Domain models and data structures for WhitelistBypass Core.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class ProviderType(str, Enum):
    TELEMOST = "telemost"
    VK = "vk"
    WBSTREAM = "wbstream"
    DION = "dion"

    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]


class ServiceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class UserConfig:
    provider: str = "telemost"
    resources: str = "default"
    upstream_socks: Optional[str] = None
    upstream_user: Optional[str] = None
    upstream_pass: Optional[str] = None
    display_name: str = "Headless"
    peer_id: Optional[str] = None
    allow_private_dst: bool = False
    debug: bool = False
    telegram_id: Optional[int] = None
    vk_id: Optional[int] = None
    raw_values: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RoomInfo:
    call_link: Optional[str] = None
    current_link: Optional[str] = None

    @property
    def active_link(self) -> Optional[str]:
        return self.call_link or self.current_link

    @property
    def is_provisioned(self) -> bool:
        return bool(self.active_link)

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_link": self.call_link,
            "current_link": self.current_link,
            "active_link": self.active_link,
            "is_provisioned": self.is_provisioned,
        }


@dataclass
class CookieInfo:
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    exists: bool = False
    valid: bool = False
    size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UserSummary:
    username: str
    provider: str
    service_status: str
    link: Optional[str] = None
    cookie_valid: bool = False
    cookie_file: Optional[str] = None
    cookie_size: int = 0
    telegram_id: Optional[int] = None
    vk_id: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CommandResult:
    success: bool
    command: str
    user: Optional[str] = None
    message: str = ""
    data: Any = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "command": self.command,
            "user": self.user,
            "message": self.message,
            "data": self.data,
            "error": self.error,
        }
