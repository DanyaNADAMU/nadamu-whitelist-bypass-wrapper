"""
Unified CLI interface for WhitelistBypass.
Orchestrates commands via the Core daemon or in-process fallback,
with styled terminal output and structured --json support.
"""

import argparse
import json
import os
import sys
from typing import Any, NoReturn, Optional

from core.commands import COMMAND_REGISTRY, resolve_command
from core.client import CoreClient
from core.config import config as default_config
from core.models import CommandResult, ProviderType
from core.services.qr_service import QrService
from core.services.tunnel_service import TunnelService
from core.services.user_service import UserService


# Terminal color styling
def _supports_color() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


USE_COLOR = _supports_color()
C_RESET = "\033[0m" if USE_COLOR else ""
C_BOLD = "\033[1m" if USE_COLOR else ""
C_RED = "\033[31m" if USE_COLOR else ""
C_GREEN = "\033[32m" if USE_COLOR else ""
C_YELLOW = "\033[33m" if USE_COLOR else ""
C_CYAN = "\033[36m" if USE_COLOR else ""


def log_info(msg: str) -> None:
    print(f"{C_CYAN}[INFO]{C_RESET} {msg}")


def log_ok(msg: str) -> None:
    print(f"{C_GREEN}[OK]{C_RESET} {msg}")


def log_warn(msg: str) -> None:
    print(f"{C_YELLOW}[WARN]{C_RESET} {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"{C_RED}[ERROR]{C_RESET} {msg}", file=sys.stderr)


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def format_link_output(data: dict[str, Any], show_qr: bool = False) -> None:
    if show_qr and data.get("qr_ansi"):
        print("\n" + data["qr_ansi"] + "\n")
    print(f"User:     {data.get('username')}")
    print(f"Provider: {data.get('provider')}")
    print(f"Service:  {data.get('service_status')}")
    print(f"Link:     {data.get('link')}")


def format_status_output(data: dict[str, Any]) -> None:
    print(f"User:           {data.get('username')}")
    print(f"Provider:       {data.get('provider')}")
    print(f"Service Status: {data.get('service_status')}")
    cookie_valid = "valid" if data.get("cookie_valid") else "invalid / stub"
    cookie_file = data.get("cookie_file") or "none"
    cookie_size = data.get("cookie_size", 0)
    print(f"Cookie File:    {cookie_file} ({cookie_size} bytes, {cookie_valid})")
    print(f"Active Link:    {data.get('link') or '—'}")
    if data.get("telegram_id"):
        print(f"Telegram ID:    {data['telegram_id']}")
    if data.get("vk_id"):
        print(f"VK ID:          {data['vk_id']}")

    journal = data.get("journal_tail")
    if journal:
        print("\nRecent Logs:")
        for line in journal.splitlines()[-10:]:
            print(f"  {line}")


def format_list_output(users: list[dict[str, Any]]) -> None:
    if not users:
        print("No configured users found.")
        return

    print(f"{'USER':<18} {'PROVIDER':<12} {'STATUS':<12} {'ACTIVE LINK'}")
    print(f"{'-'*18} {'-'*12} {'-'*12} {'-'*40}")
    for u in users:
        uname = u.get("username", "—")
        prov = u.get("provider", "—")
        status = u.get("service_status", "inactive")
        link = u.get("link") or "—"
        print(f"{uname:<18} {prov:<12} {status:<12} {link}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whitelist-bypass",
        description="WhitelistBypass Multi-Account Orchestrator and Client",
        add_help=False,
    )
    parser.add_argument("--json", action="store_true", default=False, help="Output in structured JSON")
    parser.add_argument("-h", "--help", action="store_true", default=False, help="Show help message")

    subparsers = parser.add_subparsers(dest="subcommand")

    # link / get-link
    p_link = subparsers.add_parser("link", aliases=["get-link"], help="Show active conference room link")
    p_link.add_argument("user", help="Target username")
    p_link.add_argument("--qr", "-q", action="store_true", help="Render terminal QR code")

    # qr
    p_qr = subparsers.add_parser("qr", help="Display conference room QR code")
    p_qr.add_argument("user", help="Target username")

    # rotate
    p_rotate = subparsers.add_parser("rotate", help="Rotate conference room and persist new link")
    p_rotate.add_argument("user", help="Target username")
    p_rotate.add_argument("--qr", "-q", action="store_true", help="Render terminal QR code for new link")

    # provider / set-provider
    p_prov = subparsers.add_parser(
        "provider", aliases=["set-provider"], help="Change conference provider"
    )
    p_prov.add_argument("user", help="Target username")
    p_prov.add_argument("provider", choices=ProviderType.values(), help="Target provider")
    p_prov.add_argument(
        "--rotate",
        "-r",
        action="store_true",
        help="Immediately rotate and generate room with new provider",
    )

    # list
    subparsers.add_parser("list", help="List all configured users and service statuses")

    # status
    p_status = subparsers.add_parser("status", help="Show systemd service status and user details")
    p_status.add_argument("user", help="Target username")

    # service controls
    for act in ("start", "stop", "restart", "is-active"):
        p_act = subparsers.add_parser(act, help=f"{act.capitalize()} user tunnel service")
        p_act.add_argument("user", help="Target username")

    # run (internal daemon runner)
    p_run = subparsers.add_parser("run", help="Internal daemon runner invoked by systemd")
    p_run.add_argument("user", help="Target username")

    # help
    subparsers.add_parser("help", help="Show this help message")

    return parser


def show_custom_usage() -> None:
    print(
        """WhitelistBypass Multi-Account Orchestrator

Usage:
  whitelist-bypass <command> [options]

Room and Link Management:
  link, get-link <user> [--qr]         Show active conference room link and status
  qr <user>                            Display terminal QR code and link
  rotate <user> [--qr]                 Rotate conference room and persist new link
  provider, set-provider <user> <provider> [--rotate]
                                       Change provider (telemost, vk, wbstream, dion)
  list                                 List all configured users and service statuses

Systemd Service Control:
  start <user>                         Start whitelist-bypass@<user> service
  stop <user>                          Stop whitelist-bypass@<user> service
  restart <user>                       Restart whitelist-bypass@<user> service
  status <user>                        Show systemd service status and user details
  is-active <user>                     Check if service is active

System Commands:
  run <user>                           Internal daemon runner (invoked by systemd)
  help                                 Show this help message

Global Options:
  --json                               Output results in JSON format
"""
    )


def main(argv: Optional[list[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Support --json anywhere in command line
    json_mode = False
    cleaned_argv = []
    for arg in argv:
        if arg == "--json":
            json_mode = True
        else:
            cleaned_argv.append(arg)

    if not cleaned_argv or cleaned_argv[0] in ("-h", "--help", "help"):
        if json_mode:
            print_json({"error": "No command specified", "available_commands": list(COMMAND_REGISTRY.keys())})
            return 1
        show_custom_usage()
        return 0

    parser = build_parser()
    args, unknown = parser.parse_known_args(cleaned_argv)

    if args.help or args.subcommand == "help":
        show_custom_usage()
        return 0

    if not args.subcommand:
        show_custom_usage()
        return 1

    subcmd = args.subcommand


    client = CoreClient()

    # Special handling for internal run command: directly exec binary
    if subcmd == "run":
        try:
            client.tunnel_service.run_creator(args.user)
            return 0
        except Exception as e:
            log_error(str(e))
            return 1

    # Map parsed args to dictionary
    cmd_kwargs: dict[str, Any] = {}
    if hasattr(args, "user") and args.user:
        cmd_kwargs["user"] = args.user
    if hasattr(args, "qr"):
        cmd_kwargs["qr"] = args.qr
    if hasattr(args, "provider") and args.provider:
        cmd_kwargs["provider"] = args.provider
    if hasattr(args, "rotate"):
        cmd_kwargs["rotate"] = args.rotate

    # Non-json progress info for long-running rotation
    if not json_mode:
        if subcmd == "rotate":
            log_info(f"Rotating conference room for {args.user}...")
        elif subcmd in ("provider", "set-provider") and getattr(args, "rotate", False):
            log_info(f"Updating provider to {args.provider} and rotating room...")

    result = client.execute_command(subcmd, **cmd_kwargs)

    if json_mode:
        print_json(result.to_dict())
        return 0 if result.success else 1

    # Human-readable output formatting
    if not result.success:
        log_error(result.error or result.message or "Command failed")
        if result.data and isinstance(result.data, dict) and result.data.get("link"):
            print(f"User:     {result.data.get('username')}")
            print(f"Provider: {result.data.get('provider')}")
        return 1

    if subcmd in ("link", "get-link"):
        format_link_output(result.data, show_qr=getattr(args, "qr", False))
    elif subcmd == "qr":
        if result.data.get("qr_ansi"):
            print("\n" + result.data["qr_ansi"] + "\n")
        print(f"User:     {result.data.get('username')}")
        print(f"Provider: {result.data.get('provider')}")
        print(f"Link:     {result.data.get('link')}")
    elif subcmd == "rotate":
        log_ok("New room successfully provisioned and persisted:")
        if getattr(args, "qr", False) and result.data.get("qr_ansi"):
            print("\n" + result.data["qr_ansi"] + "\n")
        print(result.data.get("link"))
    elif subcmd in ("provider", "set-provider"):
        log_ok(f"Provider for user '{args.user}' changed to '{args.provider}'.")
        if result.data.get("cookie_warning"):
            log_warn(
                f"Cookie file for provider '{args.provider}' is missing or an unpopulated stub! "
                f"Populate cookies-{args.provider}.json before running."
            )
        if getattr(args, "rotate", False):
            log_ok(f"Provisioned new link: {result.data.get('link')}")
        else:
            log_info(f"To apply changes and provision a new room, execute:")
            log_info(f"  whitelist-bypass rotate {args.user} --qr")
    elif subcmd == "list":
        format_list_output(result.data.get("users", []))
    elif subcmd == "status":
        format_status_output(result.data)
    elif subcmd in ("start", "stop", "restart"):
        log_ok(result.message)
    elif subcmd == "is-active":
        print(result.message)

    return 0


if __name__ == "__main__":
    sys.exit(main())
