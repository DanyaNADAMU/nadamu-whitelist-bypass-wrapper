"""
Localization strings (Russian and English) for WhitelistBypass Telegram Bot.
"""

from typing import Any

STRINGS: dict[str, dict[str, str]] = {
    "welcome_user": {
        "ru": (
            "👋 Привет, <b>{username}</b>!\n\n"
            "📡 Провайдер: <b>{provider}</b>\n"
            "🟢 Служба: <b>{status}</b>\n\n"
            "Используй кнопки ниже или команды:\n"
            "• /link — получить ссылку\n"
            "• /qr — отобразить QR-код для подключения\n"
            "• /rotate — пересоздать комнату\n"
            "• /provider — сменить провайдера (VK / Telemost)\n"
            "• /status — статус и диагностика"
        ),
        "en": (
            "👋 Hello, <b>{username}</b>!\n\n"
            "📡 Provider: <b>{provider}</b>\n"
            "🟢 Service: <b>{status}</b>\n\n"
            "Use the buttons below or commands:\n"
            "• /link — get conference link\n"
            "• /qr — display QR code for Joiner\n"
            "• /rotate — provision fresh room\n"
            "• /provider — change provider (VK / Telemost)\n"
            "• /status — service diagnostics"
        ),
    },
    "welcome_admin": {
        "ru": (
            "👑 <b>Панель администратора WhitelistBypass</b>\n\n"
            "Вы авторизованы как системный администратор.\n\n"
            "Команды управления:\n"
            "• /list — список всех пользователей и статусов\n"
            "• /link &lt;user&gt; — получить ссылку пользователя\n"
            "• /qr &lt;user&gt; — QR-код пользователя\n"
            "• /rotate &lt;user&gt; — сгенерировать новую комнату\n"
            "• /provider &lt;user&gt; [name] — сменить провайдера\n"
            "• /status &lt;user&gt; — статус службы и логи\n"
            "• /start_user &lt;user&gt;, /stop_user &lt;user&gt;"
        ),
        "en": (
            "👑 <b>WhitelistBypass Admin Panel</b>\n\n"
            "You are authorized as system administrator.\n\n"
            "Management commands:\n"
            "• /list — list all users and statuses\n"
            "• /link &lt;user&gt; — get user conference link\n"
            "• /qr &lt;user&gt; — display user QR code\n"
            "• /rotate &lt;user&gt; — provision fresh room\n"
            "• /provider &lt;user&gt; [name] — change provider\n"
            "• /status &lt;user&gt; — service status and logs\n"
            "• /start_user &lt;user&gt;, /stop_user &lt;user&gt;"
        ),
    },
    "access_denied": {
        "ru": (
            "⛔ <b>Доступ не настроен</b>\n\n"
            "Ваш Telegram ID: <code>{user_id}</code>\n\n"
            "Отправьте этот идентификатор администратору сервера, чтобы он добавил его в ваш "
            "конфигурационный файл:\n"
            "<code>/etc/whitelist-bypass/users/&lt;ваше_имя&gt;/user.conf</code>\n"
            "в строку: <code>TELEGRAM_ID={user_id}</code>"
        ),
        "en": (
            "⛔ <b>Access Not Configured</b>\n\n"
            "Your Telegram ID: <code>{user_id}</code>\n\n"
            "Send this ID to your server administrator to register it in your configuration:\n"
            "<code>/etc/whitelist-bypass/users/&lt;your_name&gt;/user.conf</code>\n"
            "under: <code>TELEGRAM_ID={user_id}</code>"
        ),
    },
    "link_card": {
        "ru": (
            "🔗 <b>Активная комната</b>\n"
            "Пользователь: <b>{username}</b>\n"
            "Провайдер: <b>{provider}</b>\n"
            "Служба: <b>{status}</b>\n\n"
            "Ссылка для подключения Joiner:\n"
            "<code>{link}</code>"
        ),
        "en": (
            "🔗 <b>Active Conference Room</b>\n"
            "User: <b>{username}</b>\n"
            "Provider: <b>{provider}</b>\n"
            "Service: <b>{status}</b>\n\n"
            "Joiner connection URL:\n"
            "<code>{link}</code>"
        ),
    },
    "link_not_provisioned": {
        "ru": (
            "⚠️ Комната для <b>{username}</b> еще не создана.\n\n"
            "Нажмите кнопку ниже, чтобы сгенерировать новую ссылку."
        ),
        "en": (
            "⚠️ Conference room for <b>{username}</b> has not been provisioned yet.\n\n"
            "Click the button below to generate a new room link."
        ),
    },
    "qr_caption": {
        "ru": (
            "📱 <b>QR-код для подключения</b>\n"
            "Пользователь: <b>{username}</b> ({provider})\n\n"
            "Ссылка:\n<code>{link}</code>"
        ),
        "en": (
            "📱 <b>Connection QR Code</b>\n"
            "User: <b>{username}</b> ({provider})\n\n"
            "Link:\n<code>{link}</code>"
        ),
    },
    "rotating_progress": {
        "ru": "⏳ <b>Генерация новой комнаты для {username}...</b>\nОжидаем ответа медиа-сервера (2-5 сек)...",
        "en": "⏳ <b>Provisioning new room for {username}...</b>\nWaiting for media server response (2-5s)...",
    },
    "rotate_success": {
        "ru": (
            "✅ <b>Новая комната успешно создана!</b>\n\n"
            "Пользователь: <b>{username}</b>\n"
            "Провайдер: <b>{provider}</b>\n\n"
            "Ссылка:\n<code>{link}</code>"
        ),
        "en": (
            "✅ <b>New room successfully provisioned!</b>\n\n"
            "User: <b>{username}</b>\n"
            "Provider: <b>{provider}</b>\n\n"
            "Link:\n<code>{link}</code>"
        ),
    },
    "rotate_failed": {
        "ru": "❌ <b>Ошибка при создании комнаты:</b>\n<code>{error}</code>",
        "en": "❌ <b>Room provisioning failed:</b>\n<code>{error}</code>",
    },
    "status_card": {
        "ru": (
            "ℹ️ <b>Диагностика туннеля</b>\n\n"
            "Пользователь: <b>{username}</b>\n"
            "Провайдер: <b>{provider}</b>\n"
            "Статус службы: <b>{status}</b>\n"
            "Cookies: <b>{cookie_status}</b> ({cookie_file}, {cookie_size} байт)\n"
            "Активная комната: <code>{link}</code>"
        ),
        "en": (
            "ℹ️ <b>Tunnel Diagnostics</b>\n\n"
            "User: <b>{username}</b>\n"
            "Provider: <b>{provider}</b>\n"
            "Service status: <b>{status}</b>\n"
            "Cookies: <b>{cookie_status}</b> ({cookie_file}, {cookie_size} bytes)\n"
            "Active link: <code>{link}</code>"
        ),
    },
    "provider_menu": {
        "ru": (
            "⚙️ <b>Выбор провайдера WebRTC</b>\n\n"
            "Пользователь: <b>{username}</b>\n"
            "Текущий провайдер: <b>{provider}</b>\n\n"
            "Выберите платформу для переключения:"
        ),
        "en": (
            "⚙️ <b>Select WebRTC Provider</b>\n\n"
            "User: <b>{username}</b>\n"
            "Current provider: <b>{provider}</b>\n\n"
            "Choose a platform to switch to:"
        ),
    },
    "provider_switched": {
        "ru": (
            "✅ Провайдер для <b>{username}</b> изменен на <b>{provider}</b>.{warning}\n\n"
            "Чтобы создать комнату с новым провайдером, нажмите «🔄 Сгенерировать ссылку»."
        ),
        "en": (
            "✅ Provider for <b>{username}</b> updated to <b>{provider}</b>.{warning}\n\n"
            "To activate a room with the new provider, click '🔄 Rotate Room'."
        ),
    },
    "btn_link": {"ru": "🔗 Ссылка", "en": "🔗 Link"},
    "btn_qr": {"ru": "📱 QR-код", "en": "📱 QR Code"},
    "btn_rotate": {"ru": "🔄 Новая комната", "en": "🔄 Rotate Room"},
    "btn_provider": {"ru": "⚙️ Провайдер", "en": "⚙️ Provider"},
    "btn_status": {"ru": "ℹ️ Статус", "en": "ℹ️ Status"},
    "btn_refresh": {"ru": "🔄 Обновить", "en": "🔄 Refresh"},
    "btn_back": {"ru": "◀️ Назад", "en": "◀️ Back"},
}


def get_text(key: str, lang: str = "ru", **kwargs: Any) -> str:
    """Retrieve localized string formatted with keyword arguments."""
    lang_code = "ru" if lang.startswith("ru") else "en"
    node = STRINGS.get(key, {})
    template = node.get(lang_code, node.get("ru", f"[{key}]"))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
