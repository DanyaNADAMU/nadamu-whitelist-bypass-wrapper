"""
Message and callback query handlers for WhitelistBypass Telegram Bot.
"""

import asyncio
import base64
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.telegram.config import bot_config
from bot.telegram.keyboards import (
    get_post_rotate_keyboard,
    get_provider_keyboard,
    get_rotate_confirm_keyboard,
    get_user_main_keyboard,
)
from bot.telegram.locales import get_text
from core.client import CoreClient
from core.models import ProviderType

router = Router()
client = CoreClient()


def get_user_lang(event: Message | CallbackQuery) -> str:
    user = event.from_user
    if user and user.language_code:
        return user.language_code
    return bot_config.default_lang


def resolve_context_user(event: Message | CallbackQuery, explicit_arg: Optional[str] = None) -> tuple[Optional[str], bool]:
    """
    Resolve target username and admin status.
    Returns (username, is_admin).
    """
    user_id = event.from_user.id if event.from_user else 0
    is_admin = bot_config.is_admin(user_id)

    # 1. Admin specifying explicit target user
    if is_admin and explicit_arg:
        clean_user = explicit_arg.strip().lower()
        if client.user_service.user_exists(clean_user):
            return clean_user, True
        return None, True

    # 2. Resolve via TELEGRAM_ID mapped in user.conf
    matched_user = client.user_service.resolve_identity(telegram_id=user_id)
    if matched_user:
        return matched_user, is_admin

    return None, is_admin


def get_cmd_arg(message: Message) -> Optional[str]:
    """Extract first argument from a command message."""
    text = message.text or ""
    parts = text.split()
    return parts[1] if len(parts) > 1 else None


@router.message(CommandStart())
async def cmd_start(message: Message):
    lang = get_user_lang(message)
    username, is_admin = resolve_context_user(message)

    if not username:
        if is_admin:
            await message.answer(get_text("welcome_admin", lang), parse_mode="HTML")
            return
        await message.answer(
            get_text("access_denied", lang, user_id=message.from_user.id),
            parse_mode="HTML",
        )
        return

    summary = client.get_user_summary(username)
    status_emoji = "🟢 active" if summary.service_status in ("active", "activating") else f"⚪ {summary.service_status}"

    text = get_text(
        "welcome_user",
        lang,
        username=username,
        provider=summary.provider.upper(),
        status=status_emoji,
    )
    if is_admin:
        admin_hint = "\n\n👑 <i>Режим администратора (/help, /list).</i>" if lang == "ru" else "\n\n👑 <i>Administrator mode (/help, /list).</i>"
        text += admin_hint

    kb = get_user_main_keyboard(username, lang, is_admin=is_admin)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    lang = get_user_lang(message)
    user_id = message.from_user.id if message.from_user else 0
    is_admin = bot_config.is_admin(user_id)
    username = client.user_service.resolve_identity(telegram_id=user_id)

    if not username and not is_admin:
        await message.answer(
            get_text("access_denied", lang, user_id=user_id),
            parse_mode="HTML",
        )
        return

    text = get_text("help_user", lang)
    if is_admin:
        text += get_text("help_admin_section", lang)

    kb = get_user_main_keyboard(username, lang, is_admin=is_admin) if username else None
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("link"))
async def cmd_link(message: Message):
    lang = get_user_lang(message)
    arg = get_cmd_arg(message)
    username, is_admin = resolve_context_user(message, arg)

    if not username:
        if is_admin:
            await message.answer("ℹ️ Использование: <code>/link &lt;user&gt;</code>", parse_mode="HTML")
        else:
            await message.answer(get_text("access_denied", lang, user_id=message.from_user.id), parse_mode="HTML")
        return

    res = client.execute_command("link", user=username)
    if not res.success or not res.data or not res.data.get("link"):
        kb = get_user_main_keyboard(username, lang, is_admin=is_admin)
        await message.answer(get_text("link_not_provisioned", lang, username=username), reply_markup=kb, parse_mode="HTML")
        return

    data = res.data
    status_emoji = "🟢 active" if data.get("service_status") in ("active", "activating") else f"⚪ {data.get('service_status', 'inactive')}"
    text = get_text(
        "link_card",
        lang,
        username=username,
        provider=data.get("provider", "—").upper(),
        status=status_emoji,
        link=data.get("link"),
    )
    kb = get_user_main_keyboard(username, lang, is_admin=is_admin)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("qr"))
async def cmd_qr(message: Message):
    lang = get_user_lang(message)
    arg = get_cmd_arg(message)
    username, is_admin = resolve_context_user(message, arg)

    if not username:
        if is_admin:
            await message.answer("ℹ️ Использование: <code>/qr &lt;user&gt;</code>", parse_mode="HTML")
        else:
            await message.answer(get_text("access_denied", lang, user_id=message.from_user.id), parse_mode="HTML")
        return

    res = client.execute_command("qr", user=username)
    if not res.success or not res.data or not res.data.get("link"):
        await message.answer(get_text("link_not_provisioned", lang, username=username), parse_mode="HTML")
        return

    data = res.data
    link = data.get("link")
    caption = get_text("qr_caption", lang, username=username, provider=data.get("provider", "").upper(), link=link)

    png_b64 = data.get("qr_png")
    if png_b64:
        try:
            img_bytes = base64.b64decode(png_b64)
            photo = BufferedInputFile(img_bytes, filename=f"qr_{username}.png")
            kb = get_user_main_keyboard(username, lang, is_admin=is_admin)
            await message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")
            return
        except Exception:
            pass

    # Fallback to text link if photo decoding fails
    await message.answer(caption, parse_mode="HTML")


@router.message(Command("rotate"))
async def cmd_rotate(message: Message):
    lang = get_user_lang(message)
    arg = get_cmd_arg(message)
    username, is_admin = resolve_context_user(message, arg)

    if not username:
        if is_admin:
            await message.answer("ℹ️ Использование: <code>/rotate &lt;user&gt;</code>", parse_mode="HTML")
        else:
            await message.answer(get_text("access_denied", lang, user_id=message.from_user.id), parse_mode="HTML")
        return

    progress_msg = await message.answer(
        get_text("rotating_progress", lang, username=username),
        parse_mode="HTML",
    )

    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(None, lambda: client.execute_command("rotate", user=username, qr=True))

    if not res.success or not res.data or not res.data.get("link"):
        err = res.error or "Unknown rotation error"
        await progress_msg.edit_text(get_text("rotate_failed", lang, error=err), parse_mode="HTML")
        return

    data = res.data
    new_link = data.get("link")
    await progress_msg.delete()

    caption = get_text("rotate_success", lang, username=username, provider=data.get("provider", "").upper(), link=new_link)
    kb = get_post_rotate_keyboard(username, lang)

    png_b64 = data.get("qr_png")
    if png_b64:
        try:
            img_bytes = base64.b64decode(png_b64)
            photo = BufferedInputFile(img_bytes, filename=f"qr_{username}.png")
            await message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")
            return
        except Exception:
            pass

    await message.answer(caption, reply_markup=kb, parse_mode="HTML")


@router.message(Command("provider"))
async def cmd_provider(message: Message):
    lang = get_user_lang(message)
    parts = (message.text or "").split()
    # /provider [user] [new_provider] or /provider [new_provider]
    user_id = message.from_user.id if message.from_user else 0
    is_admin = bot_config.is_admin(user_id)

    target_user: Optional[str] = None
    target_prov: Optional[str] = None

    if is_admin and len(parts) >= 3:
        target_user = parts[1].strip().lower()
        target_prov = parts[2].strip().lower()
    elif is_admin and len(parts) == 2 and parts[1].strip().lower() not in ProviderType.values():
        target_user = parts[1].strip().lower()
    elif len(parts) >= 2 and parts[1].strip().lower() in ProviderType.values():
        target_prov = parts[1].strip().lower()

    if not target_user:
        target_user, _ = resolve_context_user(message)

    if not target_user:
        if is_admin:
            await message.answer("ℹ️ Использование: <code>/provider &lt;user&gt; [telemost|vk|wbstream|dion]</code>", parse_mode="HTML")
        else:
            await message.answer(get_text("access_denied", lang, user_id=user_id), parse_mode="HTML")
        return

    summary = client.get_user_summary(target_user)

    if not target_prov:
        kb = get_provider_keyboard(target_user, summary.provider, lang)
        await message.answer(
            get_text("provider_menu", lang, username=target_user, provider=summary.provider.upper()),
            reply_markup=kb,
            parse_mode="HTML",
        )
        return

    # Set specified provider
    res = client.execute_command("provider", user=target_user, provider=target_prov)
    if not res.success:
        await message.answer(f"❌ {res.error or 'Failed to change provider'}")
        return

    warning = ""
    if res.data and res.data.get("cookie_warning"):
        warning = "\n\n⚠️ <i>Внимание: Cookies для нового провайдера отсутствуют или не заполнены!</i>"

    kb = get_user_main_keyboard(target_user, lang, is_admin=is_admin)
    await message.answer(
        get_text("provider_switched", lang, username=target_user, provider=target_prov.upper(), warning=warning),
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.message(Command("status"))
async def cmd_status(message: Message):
    lang = get_user_lang(message)
    arg = get_cmd_arg(message)
    username, is_admin = resolve_context_user(message, arg)

    if not username:
        if is_admin:
            await message.answer("ℹ️ Использование: <code>/status &lt;user&gt;</code>", parse_mode="HTML")
        else:
            await message.answer(get_text("access_denied", lang, user_id=message.from_user.id), parse_mode="HTML")
        return

    res = client.execute_command("status", user=username)
    if not res.success or not res.data:
        await message.answer(f"❌ {res.error or 'Failed to fetch status'}")
        return

    data = res.data
    cookie_valid_text = "✅ Валидны" if data.get("cookie_valid") else "⚠️ Пустая заглушка / Отсутствуют"
    status_emoji = "🟢 active" if data.get("service_status") in ("active", "activating") else f"⚪ {data.get('service_status', 'inactive')}"

    text = get_text(
        "status_card",
        lang,
        username=username,
        provider=data.get("provider", "—").upper(),
        status=status_emoji,
        cookie_status=cookie_valid_text,
        cookie_file=data.get("cookie_file") or "none",
        cookie_size=data.get("cookie_size", 0),
        link=data.get("link") or "—",
    )
    kb = get_user_main_keyboard(username, lang, is_admin=is_admin)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("restart"))
async def cmd_restart(message: Message):
    lang = get_user_lang(message)
    arg = get_cmd_arg(message)
    username, is_admin = resolve_context_user(message, arg)

    if not username:
        if is_admin:
            await message.answer("ℹ️ Использование: <code>/restart &lt;user&gt;</code>", parse_mode="HTML")
        else:
            await message.answer(get_text("access_denied", lang, user_id=message.from_user.id), parse_mode="HTML")
        return

    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(None, lambda: client.execute_command("restart", user=username))
    if res.success:
        await message.answer(f"🔄 Служба туннеля для <b>{username}</b> успешно перезапущена!", parse_mode="HTML")
    else:
        await message.answer(f"❌ Ошибка перезапуска: {res.error or 'Failed'}", parse_mode="HTML")


@router.message(Command("start_service"))
async def cmd_start_service(message: Message):
    lang = get_user_lang(message)
    arg = get_cmd_arg(message)
    username, is_admin = resolve_context_user(message, arg)

    if not is_admin:
        await message.answer("⛔ Данная команда доступна только администраторам.")
        return

    if not username:
        await message.answer("ℹ️ Использование: <code>/start_service &lt;user&gt;</code>", parse_mode="HTML")
        return

    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(None, lambda: client.execute_command("start", user=username))
    if res.success:
        await message.answer(f"▶️ Служба для <b>{username}</b> успешно запущена!", parse_mode="HTML")
    else:
        await message.answer(f"❌ Ошибка запуска: {res.error or 'Failed'}", parse_mode="HTML")


@router.message(Command("stop_service"))
async def cmd_stop_service(message: Message):
    lang = get_user_lang(message)
    arg = get_cmd_arg(message)
    username, is_admin = resolve_context_user(message, arg)

    if not is_admin:
        await message.answer("⛔ Данная команда доступна только администраторам.")
        return

    if not username:
        await message.answer("ℹ️ Использование: <code>/stop_service &lt;user&gt;</code>", parse_mode="HTML")
        return

    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(None, lambda: client.execute_command("stop", user=username))
    if res.success:
        await message.answer(f"⏹️ Служба для <b>{username}</b> остановлена!", parse_mode="HTML")
    else:
        await message.answer(f"❌ Ошибка остановки: {res.error or 'Failed'}", parse_mode="HTML")


@router.message(Command("list"))
async def cmd_list(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not bot_config.is_admin(user_id):
        await message.answer("⛔ Данная команда доступна только администраторам.")
        return

    res = client.execute_command("list")
    users = (res.data or {}).get("users", [])
    if not users:
        await message.answer("ℹ️ На сервере нет настроенных пользователей.")
        return

    lines = ["📋 <b>Список пользователей Iris:</b>\n"]
    for u in users:
        uname = u.get("username", "—")
        prov = u.get("provider", "—").upper()
        status = u.get("service_status", "inactive")
        status_icon = "🟢" if status in ("active", "activating") else "⚪"
        link = u.get("link")
        link_str = f'<a href="{link}">Ссылка</a>' if link else "—"
        lines.append(f"{status_icon} <b>{uname}</b> [{prov}]: {link_str}")

    await message.answer("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


@router.callback_query(F.data == "admin_list")
async def cb_admin_list(callback: CallbackQuery):
    user_id = callback.from_user.id if callback.from_user else 0
    if not bot_config.is_admin(user_id):
        await callback.answer("⛔ Только для администраторов", show_alert=True)
        return
    await callback.answer()

    res = client.execute_command("list")
    users = (res.data or {}).get("users", [])
    if not users:
        await callback.message.answer("ℹ️ На сервере нет настроенных пользователей.")
        return

    lines = ["📋 <b>Список пользователей Iris:</b>\n"]
    for u in users:
        uname = u.get("username", "—")
        prov = u.get("provider", "—").upper()
        status = u.get("service_status", "inactive")
        status_icon = "🟢" if status in ("active", "activating") else "⚪"
        link = u.get("link")
        link_str = f'<a href="{link}">Ссылка</a>' if link else "—"
        lines.append(f"{status_icon} <b>{uname}</b> [{prov}]: {link_str}")

    await callback.message.answer("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


# Callback Query Handlers
@router.callback_query(F.data.startswith("qr:"))
async def cb_qr(callback: CallbackQuery):
    await callback.answer()
    username = callback.data.split(":", 1)[1]
    lang = get_user_lang(callback)

    res = client.execute_command("qr", user=username)
    if not res.success or not res.data or not res.data.get("link"):
        await callback.message.answer(get_text("link_not_provisioned", lang, username=username), parse_mode="HTML")
        return

    data = res.data
    link = data.get("link")
    caption = get_text("qr_caption", lang, username=username, provider=data.get("provider", "").upper(), link=link)

    png_b64 = data.get("qr_png")
    if png_b64:
        try:
            img_bytes = base64.b64decode(png_b64)
            photo = BufferedInputFile(img_bytes, filename=f"qr_{username}.png")
            is_admin = bot_config.is_admin(callback.from_user.id if callback.from_user else 0)
            kb = get_user_main_keyboard(username, lang, is_admin=is_admin)
            await callback.message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")
            return
        except Exception:
            pass

    await callback.message.answer(caption, parse_mode="HTML")


@router.callback_query(F.data.startswith("rot_confirm:"))
async def cb_rot_confirm(callback: CallbackQuery):
    await callback.answer()
    username = callback.data.split(":", 1)[1]
    lang = get_user_lang(callback)
    kb = get_rotate_confirm_keyboard(username, lang)
    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение ротации для {username}</b>\n\n"
        f"Текущая комната будет завершена и создана новая ссылка. Продолжить?",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("rot_do:"))
async def cb_rot_do(callback: CallbackQuery):
    await callback.answer()
    username = callback.data.split(":", 1)[1]
    lang = get_user_lang(callback)

    await callback.message.edit_text(
        get_text("rotating_progress", lang, username=username),
        parse_mode="HTML",
    )

    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(None, lambda: client.execute_command("rotate", user=username, qr=True))

    if not res.success or not res.data or not res.data.get("link"):
        err = res.error or "Unknown error"
        await callback.message.edit_text(get_text("rotate_failed", lang, error=err), parse_mode="HTML")
        return

    data = res.data
    new_link = data.get("link")
    caption = get_text("rotate_success", lang, username=username, provider=data.get("provider", "").upper(), link=new_link)
    kb = get_post_rotate_keyboard(username, lang)

    await callback.message.delete()

    png_b64 = data.get("qr_png")
    if png_b64:
        try:
            img_bytes = base64.b64decode(png_b64)
            photo = BufferedInputFile(img_bytes, filename=f"qr_{username}.png")
            await callback.message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")
            return
        except Exception:
            pass

    await callback.message.answer(caption, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("prov_menu:"))
async def cb_prov_menu(callback: CallbackQuery):
    await callback.answer()
    username = callback.data.split(":", 1)[1]
    lang = get_user_lang(callback)
    summary = client.get_user_summary(username)
    kb = get_provider_keyboard(username, summary.provider, lang)
    await callback.message.edit_text(
        get_text("provider_menu", lang, username=username, provider=summary.provider.upper()),
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("set_prov:"))
async def cb_set_prov(callback: CallbackQuery):
    await callback.answer()
    _, username, new_provider = callback.data.split(":", 2)
    lang = get_user_lang(callback)

    res = client.execute_command("provider", user=username, provider=new_provider)
    if not res.success:
        await callback.message.answer(f"❌ {res.error or 'Failed to switch provider'}")
        return

    warning = ""
    if res.data and res.data.get("cookie_warning"):
        warning = "\n\n⚠️ <i>Внимание: Cookies для нового провайдера отсутствуют или не заполнены!</i>"

    is_admin = bot_config.is_admin(callback.from_user.id if callback.from_user else 0)
    kb = get_user_main_keyboard(username, lang, is_admin=is_admin)
    await callback.message.edit_text(
        get_text("provider_switched", lang, username=username, provider=new_provider.upper(), warning=warning),
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("status:"))
async def cb_status(callback: CallbackQuery):
    await callback.answer("Обновление статуса...")
    username = callback.data.split(":", 1)[1]
    lang = get_user_lang(callback)

    res = client.execute_command("status", user=username)
    if not res.success or not res.data:
        await callback.message.answer(f"❌ {res.error or 'Failed to fetch status'}")
        return

    data = res.data
    cookie_valid_text = "✅ Валидны" if data.get("cookie_valid") else "⚠️ Пустая заглушка / Отсутствуют"
    status_emoji = "🟢 active" if data.get("service_status") in ("active", "activating") else f"⚪ {data.get('service_status', 'inactive')}"

    text = get_text(
        "status_card",
        lang,
        username=username,
        provider=data.get("provider", "—").upper(),
        status=status_emoji,
        cookie_status=cookie_valid_text,
        cookie_file=data.get("cookie_file") or "none",
        cookie_size=data.get("cookie_size", 0),
        link=data.get("link") or "—",
    )
    is_admin = bot_config.is_admin(callback.from_user.id if callback.from_user else 0)
    kb = get_user_main_keyboard(username, lang, is_admin=is_admin)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("back_main:"))
async def cb_back_main(callback: CallbackQuery):
    await callback.answer()
    username = callback.data.split(":", 1)[1]
    lang = get_user_lang(callback)

    summary = client.get_user_summary(username)
    status_emoji = "🟢 active" if summary.service_status in ("active", "activating") else f"⚪ {summary.service_status}"

    text = get_text(
        "welcome_user",
        lang,
        username=username,
        provider=summary.provider.upper(),
        status=status_emoji,
    )
    is_admin = bot_config.is_admin(callback.from_user.id if callback.from_user else 0)
    if is_admin:
        admin_hint = "\n\n👑 <i>Режим администратора (/help, /list).</i>" if lang == "ru" else "\n\n👑 <i>Administrator mode (/help, /list).</i>"
        text += admin_hint

    kb = get_user_main_keyboard(username, lang, is_admin=is_admin)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
