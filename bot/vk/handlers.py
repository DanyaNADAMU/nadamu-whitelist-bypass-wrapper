"""
Command and payload dispatcher for WhitelistBypass / Iris VK Bot.
"""

import asyncio
import base64
import json
import logging
from typing import Any, Optional

from bot.vk.client import VkClient
from bot.vk.config import vk_config
from bot.vk.keyboards import (
    get_post_rotate_keyboard,
    get_provider_keyboard,
    get_rotate_confirm_keyboard,
    get_user_main_keyboard,
)
from bot.vk.locales import get_text
from core.client import CoreClient
from core.models import ProviderType

logger = logging.getLogger("whitelist-bypass-vk-handlers")


class VkHandler:
    def __init__(self, vk_client: VkClient, core_client: Optional[CoreClient] = None):
        self.vk = vk_client
        self.core = core_client or CoreClient()
        self.lang = vk_config.default_lang

    def resolve_context_user(
        self, from_id: int, explicit_arg: Optional[str] = None
    ) -> tuple[Optional[str], bool]:
        """
        Resolve target username and admin status from VK ID.
        Returns (username, is_admin).
        """
        is_admin = vk_config.is_admin(from_id)

        # 1. Admin specifying explicit target user
        if is_admin and explicit_arg:
            clean_user = explicit_arg.strip().lower()
            if self.core.user_service.user_exists(clean_user):
                return clean_user, True
            return None, True

        # 2. Resolve via VK_ID mapped in user.conf
        matched_user = self.core.user_service.resolve_identity(vk_id=from_id)
        if matched_user:
            return matched_user, is_admin

        return None, is_admin

    async def handle_update(self, event: dict[str, Any]) -> None:
        """Main dispatcher for incoming LongPoll events."""
        event_type = event.get("type")
        if event_type != "message_new":
            return

        message = event.get("object", {}).get("message", {})
        from_id = message.get("from_id", 0)
        peer_id = message.get("peer_id", 0)
        raw_text = (message.get("text") or "").strip()
        payload_raw = message.get("payload")

        if not peer_id or not from_id:
            return

        # 1. Check if payload from inline keyboard was clicked
        if payload_raw:
            try:
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
                if isinstance(payload, dict) and "cmd" in payload:
                    await self._handle_payload(peer_id, from_id, payload)
                    return
            except Exception as e:
                logger.warning(f"Failed to parse payload: {e}")

        # 2. Parse text commands
        await self._handle_text_command(peer_id, from_id, raw_text)

    async def _handle_payload(self, peer_id: int, from_id: int, payload: dict[str, Any]) -> None:
        """Handle inline button actions."""
        cmd = payload.get("cmd")
        target_user = payload.get("user")
        is_admin = vk_config.is_admin(from_id)

        if not target_user and cmd != "admin_list":
            target_user, _ = self.resolve_context_user(from_id)

        if not target_user and cmd != "admin_list":
            await self.vk.send_message(
                peer_id, get_text("access_denied", self.lang, user_id=from_id)
            )
            return

        if cmd == "qr":
            await self._cmd_qr(peer_id, from_id, target_user)
        elif cmd == "rot_confirm":
            kb = get_rotate_confirm_keyboard(target_user, self.lang)
            text = (
                f"⚠️ Подтверждение ротации для {target_user}\n\n"
                f"Текущая конференц-комната будет завершена и сгенерирована новая ссылка. Продолжить?"
            )
            await self.vk.send_message(peer_id, text, keyboard=kb)
        elif cmd == "rot_do":
            await self._cmd_rotate(peer_id, from_id, target_user)
        elif cmd == "prov_menu":
            summary = self.core.get_user_summary(target_user)
            kb = get_provider_keyboard(target_user, summary.provider, self.lang)
            text = get_text(
                "provider_menu",
                self.lang,
                username=target_user,
                provider=summary.provider.upper(),
            )
            await self.vk.send_message(peer_id, text, keyboard=kb)
        elif cmd == "set_prov":
            new_prov = payload.get("prov", "")
            await self._cmd_provider(peer_id, from_id, target_user, new_prov)
        elif cmd == "status":
            await self._cmd_status(peer_id, from_id, target_user)
        elif cmd == "back_main":
            await self._cmd_start(peer_id, from_id)
        elif cmd == "admin_list":
            await self._cmd_list(peer_id, from_id)

    async def _handle_text_command(self, peer_id: int, from_id: int, text: str) -> None:
        """Parse and execute text commands."""
        parts = text.split()
        if not parts:
            return

        cmd_raw = parts[0].lower()
        # Strip leading slash if present
        clean_cmd = cmd_raw.lstrip("/")
        arg1 = parts[1].strip() if len(parts) > 1 else None
        arg2 = parts[2].strip() if len(parts) > 2 else None

        if clean_cmd in ("start", "menu", "начать", "меню", "старт", "привет"):
            await self._cmd_start(peer_id, from_id)
        elif clean_cmd in ("link", "ссылка"):
            await self._cmd_link(peer_id, from_id, arg1)
        elif clean_cmd in ("qr", "код"):
            await self._cmd_qr(peer_id, from_id, arg1)
        elif clean_cmd in ("rotate", "ротация"):
            await self._cmd_rotate(peer_id, from_id, arg1)
        elif clean_cmd in ("provider", "провайдер"):
            await self._cmd_provider_text(peer_id, from_id, parts[1:])
        elif clean_cmd in ("status", "статус"):
            await self._cmd_status(peer_id, from_id, arg1)
        elif clean_cmd in ("restart", "перезапуск"):
            await self._cmd_restart(peer_id, from_id, arg1)
        elif clean_cmd in ("start_service", "старт_служба"):
            await self._cmd_start_service(peer_id, from_id, arg1)
        elif clean_cmd in ("stop_service", "стоп_служба"):
            await self._cmd_stop_service(peer_id, from_id, arg1)
        elif clean_cmd in ("list", "список", "пользователи"):
            await self._cmd_list(peer_id, from_id)
        elif clean_cmd in ("help", "помощь", "справка", "?"):
            await self._cmd_help(peer_id, from_id)
        else:
            # Default fallback for unknown text: show start menu if authorized
            username, _ = self.resolve_context_user(from_id)
            if username:
                await self._cmd_start(peer_id, from_id)
            else:
                await self.vk.send_message(
                    peer_id, get_text("access_denied", self.lang, user_id=from_id)
                )

    async def _cmd_start(self, peer_id: int, from_id: int) -> None:
        username, is_admin = self.resolve_context_user(from_id)
        if not username:
            if is_admin:
                await self.vk.send_message(peer_id, get_text("welcome_admin", self.lang))
                return
            await self.vk.send_message(
                peer_id, get_text("access_denied", self.lang, user_id=from_id)
            )
            return

        summary = self.core.get_user_summary(username)
        status_emoji = (
            "🟢 active"
            if summary.service_status in ("active", "activating")
            else f"⚪ {summary.service_status}"
        )
        text = get_text(
            "welcome_user",
            self.lang,
            username=username,
            provider=summary.provider.upper(),
            status=status_emoji,
        )
        if is_admin:
            text += "\n\n👑 Режим администратора (/help, /list)."

        kb = get_user_main_keyboard(username, self.lang, is_admin=is_admin)
        await self.vk.send_message(peer_id, text, keyboard=kb)

    async def _cmd_link(self, peer_id: int, from_id: int, arg: Optional[str]) -> None:
        username, is_admin = self.resolve_context_user(from_id, arg)
        if not username:
            if is_admin:
                await self.vk.send_message(peer_id, "ℹ️ Использование: /link <user>")
            else:
                await self.vk.send_message(
                    peer_id, get_text("access_denied", self.lang, user_id=from_id)
                )
            return

        res = self.core.execute_command("link", user=username)
        kb = get_user_main_keyboard(username, self.lang, is_admin=is_admin)

        if not res.success or not res.data or not res.data.get("link"):
            await self.vk.send_message(
                peer_id,
                get_text("link_not_provisioned", self.lang, username=username),
                keyboard=kb,
            )
            return

        data = res.data
        status_emoji = (
            "🟢 active"
            if data.get("service_status") in ("active", "activating")
            else f"⚪ {data.get('service_status', 'inactive')}"
        )
        text = get_text(
            "link_card",
            self.lang,
            username=username,
            provider=data.get("provider", "—").upper(),
            status=status_emoji,
            link=data.get("link"),
        )
        await self.vk.send_message(peer_id, text, keyboard=kb)

    async def _cmd_qr(self, peer_id: int, from_id: int, arg: Optional[str]) -> None:
        username, is_admin = self.resolve_context_user(from_id, arg)
        if not username:
            if is_admin:
                await self.vk.send_message(peer_id, "ℹ️ Использование: /qr <user>")
            else:
                await self.vk.send_message(
                    peer_id, get_text("access_denied", self.lang, user_id=from_id)
                )
            return

        res = self.core.execute_command("qr", user=username)
        kb = get_user_main_keyboard(username, self.lang, is_admin=is_admin)

        if not res.success or not res.data or not res.data.get("link"):
            await self.vk.send_message(
                peer_id,
                get_text("link_not_provisioned", self.lang, username=username),
                keyboard=kb,
            )
            return

        data = res.data
        link = data.get("link")
        caption = get_text(
            "qr_caption",
            self.lang,
            username=username,
            provider=data.get("provider", "").upper(),
            link=link,
        )

        attachment = None
        png_b64 = data.get("qr_png")
        if png_b64:
            try:
                photo_bytes = base64.b64decode(png_b64)
                attachment = await self.vk.upload_message_photo(
                    peer_id, photo_bytes, filename=f"qr_{username}.png"
                )
            except Exception as e:
                logger.warning(f"Failed to upload QR photo to VK: {e}")

        await self.vk.send_message(peer_id, caption, keyboard=kb, attachment=attachment)

    async def _cmd_rotate(self, peer_id: int, from_id: int, arg: Optional[str]) -> None:
        username, is_admin = self.resolve_context_user(from_id, arg)
        if not username:
            if is_admin:
                await self.vk.send_message(peer_id, "ℹ️ Использование: /rotate <user>")
            else:
                await self.vk.send_message(
                    peer_id, get_text("access_denied", self.lang, user_id=from_id)
                )
            return

        await self.vk.send_message(
            peer_id, get_text("rotating_progress", self.lang, username=username)
        )

        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None, lambda: self.core.execute_command("rotate", user=username, qr=True)
        )

        if not res.success or not res.data or not res.data.get("link"):
            err = res.error or "Unknown rotation error"
            await self.vk.send_message(
                peer_id, get_text("rotate_failed", self.lang, error=err)
            )
            return

        data = res.data
        new_link = data.get("link")
        caption = get_text(
            "rotate_success",
            self.lang,
            username=username,
            provider=data.get("provider", "").upper(),
            link=new_link,
        )
        kb = get_post_rotate_keyboard(username, self.lang)

        attachment = None
        png_b64 = data.get("qr_png")
        if png_b64:
            try:
                photo_bytes = base64.b64decode(png_b64)
                attachment = await self.vk.upload_message_photo(
                    peer_id, photo_bytes, filename=f"qr_{username}.png"
                )
            except Exception as e:
                logger.warning(f"Failed to upload rotated QR photo to VK: {e}")

        await self.vk.send_message(peer_id, caption, keyboard=kb, attachment=attachment)

    async def _cmd_provider_text(self, peer_id: int, from_id: int, args: list[str]) -> None:
        is_admin = vk_config.is_admin(from_id)
        target_user: Optional[str] = None
        target_prov: Optional[str] = None

        if is_admin and len(args) >= 2:
            target_user = args[0].strip().lower()
            target_prov = args[1].strip().lower()
        elif is_admin and len(args) == 1 and args[0].strip().lower() not in ProviderType.values():
            target_user = args[0].strip().lower()
        elif len(args) >= 1 and args[0].strip().lower() in ProviderType.values():
            target_prov = args[0].strip().lower()

        if not target_user:
            target_user, _ = self.resolve_context_user(from_id)

        if not target_user:
            if is_admin:
                await self.vk.send_message(
                    peer_id, "ℹ️ Использование: /provider <user> [telemost|vk|wbstream|dion]"
                )
            else:
                await self.vk.send_message(
                    peer_id, get_text("access_denied", self.lang, user_id=from_id)
                )
            return

        if not target_prov:
            summary = self.core.get_user_summary(target_user)
            kb = get_provider_keyboard(target_user, summary.provider, self.lang)
            text = get_text(
                "provider_menu",
                self.lang,
                username=target_user,
                provider=summary.provider.upper(),
            )
            await self.vk.send_message(peer_id, text, keyboard=kb)
            return

        await self._cmd_provider(peer_id, from_id, target_user, target_prov)

    async def _cmd_provider(
        self, peer_id: int, from_id: int, target_user: str, target_prov: str
    ) -> None:
        is_admin = vk_config.is_admin(from_id)
        res = self.core.execute_command("provider", user=target_user, provider=target_prov)
        if not res.success:
            await self.vk.send_message(peer_id, f"❌ {res.error or 'Failed to switch provider'}")
            return

        warning = ""
        if res.data and res.data.get("cookie_warning"):
            warning = "\n\n⚠️ Внимание: Cookies для нового провайдера отсутствуют или пусты!"

        kb = get_user_main_keyboard(target_user, self.lang, is_admin=is_admin)
        text = get_text(
            "provider_switched",
            self.lang,
            username=target_user,
            provider=target_prov.upper(),
            warning=warning,
        )
        await self.vk.send_message(peer_id, text, keyboard=kb)

    async def _cmd_status(self, peer_id: int, from_id: int, arg: Optional[str]) -> None:
        username, is_admin = self.resolve_context_user(from_id, arg)
        if not username:
            if is_admin:
                await self.vk.send_message(peer_id, "ℹ️ Использование: /status <user>")
            else:
                await self.vk.send_message(
                    peer_id, get_text("access_denied", self.lang, user_id=from_id)
                )
            return

        res = self.core.execute_command("status", user=username)
        kb = get_user_main_keyboard(username, self.lang, is_admin=is_admin)

        if not res.success or not res.data:
            await self.vk.send_message(
                peer_id, f"❌ {res.error or 'Failed to fetch status'}", keyboard=kb
            )
            return

        data = res.data
        cookie_valid_text = (
            "✅ Валидны" if data.get("cookie_valid") else "⚠️ Пустая заглушка / Отсутствуют"
        )
        status_emoji = (
            "🟢 active"
            if data.get("service_status") in ("active", "activating")
            else f"⚪ {data.get('service_status', 'inactive')}"
        )

        text = get_text(
            "status_card",
            self.lang,
            username=username,
            provider=data.get("provider", "—").upper(),
            status=status_emoji,
            cookie_status=cookie_valid_text,
            cookie_file=data.get("cookie_file") or "none",
            cookie_size=data.get("cookie_size", 0),
            link=data.get("link") or "—",
        )
        await self.vk.send_message(peer_id, text, keyboard=kb)

    async def _cmd_restart(self, peer_id: int, from_id: int, arg: Optional[str]) -> None:
        username, is_admin = self.resolve_context_user(from_id, arg)
        if not username:
            if is_admin:
                await self.vk.send_message(peer_id, "ℹ️ Использование: /restart <user>")
            else:
                await self.vk.send_message(
                    peer_id, get_text("access_denied", self.lang, user_id=from_id)
                )
            return

        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None, lambda: self.core.execute_command("restart", user=username)
        )
        if res.success:
            await self.vk.send_message(
                peer_id, f"🔄 Служба туннеля для {username} успешно перезапущена!"
            )
        else:
            await self.vk.send_message(
                peer_id, f"❌ Ошибка перезапуска: {res.error or 'Failed'}"
            )

    async def _cmd_start_service(self, peer_id: int, from_id: int, arg: Optional[str]) -> None:
        username, is_admin = self.resolve_context_user(from_id, arg)
        if not is_admin:
            await self.vk.send_message(peer_id, "⛔ Данная команда доступна только администраторам.")
            return

        if not username:
            await self.vk.send_message(peer_id, "ℹ️ Использование: /start_service <user>")
            return

        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None, lambda: self.core.execute_command("start", user=username)
        )
        if res.success:
            await self.vk.send_message(peer_id, f"▶️ Служба для {username} успешно запущена!")
        else:
            await self.vk.send_message(peer_id, f"❌ Ошибка запуска: {res.error or 'Failed'}")

    async def _cmd_stop_service(self, peer_id: int, from_id: int, arg: Optional[str]) -> None:
        username, is_admin = self.resolve_context_user(from_id, arg)
        if not is_admin:
            await self.vk.send_message(peer_id, "⛔ Данная команда доступна только администраторам.")
            return

        if not username:
            await self.vk.send_message(peer_id, "ℹ️ Использование: /stop_service <user>")
            return

        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None, lambda: self.core.execute_command("stop", user=username)
        )
        if res.success:
            await self.vk.send_message(peer_id, f"⏹️ Служба для {username} остановлена!")
        else:
            await self.vk.send_message(peer_id, f"❌ Ошибка остановки: {res.error or 'Failed'}")

    async def _cmd_list(self, peer_id: int, from_id: int) -> None:
        if not vk_config.is_admin(from_id):
            await self.vk.send_message(peer_id, "⛔ Данная команда доступна только администраторам.")
            return

        res = self.core.execute_command("list")
        users = (res.data or {}).get("users", [])
        if not users:
            await self.vk.send_message(peer_id, "ℹ️ На сервере нет настроенных пользователей.")
            return

        lines = ["📋 Список пользователей Iris:\n"]
        for u in users:
            uname = u.get("username", "—")
            prov = u.get("provider", "—").upper()
            status = u.get("service_status", "inactive")
            status_icon = "🟢" if status in ("active", "activating") else "⚪"
            link = u.get("link") or "—"
            lines.append(f"{status_icon} {uname} [{prov}]:\n{link}\n")

        await self.vk.send_message(peer_id, "\n".join(lines))

    async def _cmd_help(self, peer_id: int, from_id: int) -> None:
        is_admin = vk_config.is_admin(from_id)
        username = self.core.user_service.resolve_identity(vk_id=from_id)

        if not username and not is_admin:
            await self.vk.send_message(
                peer_id, get_text("access_denied", self.lang, user_id=from_id)
            )
            return

        text = get_text("help_user", self.lang)
        if is_admin:
            text += get_text("help_admin_section", self.lang)

        kb = get_user_main_keyboard(username, self.lang, is_admin=is_admin) if username else None
        await self.vk.send_message(peer_id, text, keyboard=kb)
