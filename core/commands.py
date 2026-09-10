"""
Unified Command Registry for WhitelistBypass Core.
All interfaces (CLI, Telegram bot, VK bot, Web UI, REST API) share these definitions.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from core.models import ProviderType


@dataclass
class ArgSpec:
    name: str
    required: bool = True
    choices: Optional[list[str]] = None
    help: str = ""


@dataclass
class OptionSpec:
    flags: list[str]
    action: str = "store_true"  # "store_true", "store"
    type: Any = bool
    default: Any = False
    help: str = ""


@dataclass
class CommandSpec:
    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    category: str = "General"
    args: list[ArgSpec] = field(default_factory=list)
    options: list[OptionSpec] = field(default_factory=list)


COMMAND_REGISTRY: dict[str, CommandSpec] = {
    "link": CommandSpec(
        name="link",
        aliases=["get-link"],
        description="Show active conference room link and service status",
        category="Room and Link Management",
        args=[
            ArgSpec("user", required=True, help="Target username"),
        ],
        options=[
            OptionSpec(["--qr", "-q"], action="store_true", default=False, help="Render QR code"),
        ],
    ),
    "qr": CommandSpec(
        name="qr",
        aliases=[],
        description="Display conference room QR code and link",
        category="Room and Link Management",
        args=[
            ArgSpec("user", required=True, help="Target username"),
        ],
    ),
    "rotate": CommandSpec(
        name="rotate",
        aliases=[],
        description="Rotate conference room and persist new link",
        category="Room and Link Management",
        args=[
            ArgSpec("user", required=True, help="Target username"),
        ],
        options=[
            OptionSpec(["--qr", "-q"], action="store_true", default=False, help="Render QR code for new link"),
        ],
    ),
    "provider": CommandSpec(
        name="provider",
        aliases=["set-provider"],
        description="Change conference provider for user",
        category="Room and Link Management",
        args=[
            ArgSpec("user", required=True, help="Target username"),
            ArgSpec(
                "provider",
                required=True,
                choices=ProviderType.values(),
                help="Conference provider (telemost, vk, wbstream, dion)",
            ),
        ],
        options=[
            OptionSpec(
                ["--rotate", "-r"],
                action="store_true",
                default=False,
                help="Immediately rotate and generate a new room with the new provider",
            ),
        ],
    ),
    "list": CommandSpec(
        name="list",
        aliases=[],
        description="List all configured users and their service statuses",
        category="Room and Link Management",
    ),
    "status": CommandSpec(
        name="status",
        aliases=[],
        description="Show detailed systemd service status and user configuration",
        category="Service Control",
        args=[
            ArgSpec("user", required=True, help="Target username"),
        ],
    ),
    "start": CommandSpec(
        name="start",
        aliases=[],
        description="Start user tunnel service",
        category="Service Control",
        args=[
            ArgSpec("user", required=True, help="Target username"),
        ],
    ),
    "stop": CommandSpec(
        name="stop",
        aliases=[],
        description="Stop user tunnel service",
        category="Service Control",
        args=[
            ArgSpec("user", required=True, help="Target username"),
        ],
    ),
    "restart": CommandSpec(
        name="restart",
        aliases=[],
        description="Restart user tunnel service",
        category="Service Control",
        args=[
            ArgSpec("user", required=True, help="Target username"),
        ],
    ),
    "is-active": CommandSpec(
        name="is-active",
        aliases=[],
        description="Check whether user tunnel service is active",
        category="Service Control",
        args=[
            ArgSpec("user", required=True, help="Target username"),
        ],
    ),
    "run": CommandSpec(
        name="run",
        aliases=[],
        description="Internal daemon runner invoked by systemd template unit",
        category="System",
        args=[
            ArgSpec("user", required=True, help="Target username"),
        ],
    ),
    "help": CommandSpec(
        name="help",
        aliases=["-h", "--help"],
        description="Show available commands and usage instructions",
        category="General",
    ),
}


def resolve_command(name: str) -> Optional[CommandSpec]:
    """Find a command specification by its canonical name or alias."""
    name_clean = name.strip().lower()
    if name_clean in COMMAND_REGISTRY:
        return COMMAND_REGISTRY[name_clean]

    for cmd in COMMAND_REGISTRY.values():
        if name_clean in cmd.aliases:
            return cmd
    return None
