"""
Configuration settings for WhitelistBypass Telegram Bot.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional


def _parse_env_file(path: Path) -> dict[str, str]:
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


@dataclass
class TelegramBotConfig:
    bot_token: str
    admin_ids: set[int] = field(default_factory=set)
    default_lang: str = "ru"
    env_file_path: Path = Path("/etc/whitelist-bypass/telegram-bot.env")

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


def load_telegram_config() -> TelegramBotConfig:
    env_path = Path(
        os.environ.get("TELEGRAM_BOT_ENV", "/etc/whitelist-bypass/telegram-bot.env")
    )
    file_env = _parse_env_file(env_path)

    def get_val(name: str, default: str = "") -> str:
        return os.environ.get(name, file_env.get(name, default))

    bot_token = get_val("TELEGRAM_BOT_TOKEN", "").strip()

    admin_ids_raw = get_val("ADMIN_IDS", "").strip()
    admin_ids: set[int] = set()
    if admin_ids_raw:
        for item in admin_ids_raw.replace(";", ",").split(","):
            item = item.strip()
            if item.isdigit():
                admin_ids.add(int(item))

    default_lang = get_val("DEFAULT_LANG", "ru").strip().lower() or "ru"

    return TelegramBotConfig(
        bot_token=bot_token,
        admin_ids=admin_ids,
        default_lang=default_lang,
        env_file_path=env_path,
    )


bot_config = load_telegram_config()
