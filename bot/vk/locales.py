"""
Localization strings (Russian and English) for WhitelistBypass / Iris VK Bot.
Uses clean text formatting compatible with VK message rendering (no raw HTML).
"""

from typing import Any

STRINGS: dict[str, dict[str, str]] = {
    "welcome_user": {
        "ru": (
            "👋 Привет, {username}!\n\n"
            "📡 Провайдер: {provider}\n"
            "🟢 Служба: {status}\n\n"
            "Используйте кнопки меню или команды:\n"
            "• /link — получить активную ссылку\n"
            "• /qr — получить QR-код для подключения\n"
            "• /rotate — пересоздать чистую комнату\n"
            "• /provider — выбор платформы (VK / Telemost)\n"
            "• /status — статус и диагностика\n"
            "• /help — справка по командам"
        ),
        "en": (
            "👋 Hello, {username}!\n\n"
            "📡 Provider: {provider}\n"
            "🟢 Service: {status}\n\n"
            "Use the menu buttons or commands:\n"
            "• /link — get conference link\n"
            "• /qr — display QR code for Joiner\n"
            "• /rotate — provision fresh room\n"
            "• /provider — change provider (VK / Telemost)\n"
            "• /status — service diagnostics\n"
            "• /help — command reference"
        ),
    },
    "welcome_admin": {
        "ru": (
            "👑 Панель администратора Iris\n\n"
            "Вы авторизованы как системный администратор.\n\n"
            "Команды управления:\n"
            "• /list — список всех пользователей и статусов\n"
            "• /link <user> — получить ссылку пользователя\n"
            "• /qr <user> — QR-код пользователя\n"
            "• /rotate <user> — сгенерировать новую комнату\n"
            "• /provider <user> [name] — сменить провайдера\n"
            "• /status <user> — статус службы и логи\n"
            "• /restart <user> — перезапустить службу\n"
            "• /start_service <user> — запустить службу\n"
            "• /stop_service <user> — остановить службу\n"
            "• /help — подробная справка"
        ),
        "en": (
            "👑 Iris Admin Panel\n\n"
            "You are authorized as system administrator.\n\n"
            "Management commands:\n"
            "• /list — list all users and statuses\n"
            "• /link <user> — get user conference link\n"
            "• /qr <user> — display user QR code\n"
            "• /rotate <user> — provision fresh room\n"
            "• /provider <user> [name] — change provider\n"
            "• /status <user> — service status and logs\n"
            "• /restart <user> — restart user tunnel service\n"
            "• /start_service <user> — start user service\n"
            "• /stop_service <user> — stop user service\n"
            "• /help — command reference"
        ),
    },
    "access_denied": {
        "ru": (
            "⛔ Доступ не настроен\n\n"
            "Ваш VK ID: {user_id}\n\n"
            "Передайте этот идентификатор администратору сервера для добавления в ваш файл конфигурации:\n"
            "/etc/whitelist-bypass/users/<имя_пользователя>/user.conf\n"
            "в строку: VK_ID={user_id}"
        ),
        "en": (
            "⛔ Access Not Configured\n\n"
            "Your VK ID: {user_id}\n\n"
            "Send this ID to your administrator to register it in your configuration:\n"
            "/etc/whitelist-bypass/users/<username>/user.conf\n"
            "under: VK_ID={user_id}"
        ),
    },
    "link_card": {
        "ru": (
            "🔗 Активная комната\n"
            "Пользователь: {username}\n"
            "Провайдер: {provider}\n"
            "Служба: {status}\n\n"
            "Ссылка для подключения Joiner:\n"
            "{link}"
        ),
        "en": (
            "🔗 Active Conference Room\n"
            "User: {username}\n"
            "Provider: {provider}\n"
            "Service: {status}\n\n"
            "Joiner connection URL:\n"
            "{link}"
        ),
    },
    "link_not_provisioned": {
        "ru": (
            "⚠️ Комната для {username} еще не создана.\n\n"
            "Используйте команду /rotate или кнопку ниже, чтобы сгенерировать новую ссылку."
        ),
        "en": (
            "⚠️ Conference room for {username} has not been provisioned yet.\n\n"
            "Use /rotate or the button below to generate a new room link."
        ),
    },
    "qr_caption": {
        "ru": (
            "📱 QR-код для подключения Joiner\n"
            "Пользователь: {username} ({provider})\n\n"
            "Ссылка:\n{link}"
        ),
        "en": (
            "📱 Joiner Connection QR Code\n"
            "User: {username} ({provider})\n\n"
            "Link:\n{link}"
        ),
    },
    "rotating_progress": {
        "ru": "⏳ Генерация новой комнаты для {username}...\nОжидаем ответа медиа-сервера (2-5 сек)...",
        "en": "⏳ Provisioning new room for {username}...\nWaiting for media server response (2-5s)...",
    },
    "rotate_success": {
        "ru": (
            "✅ Новая комната успешно создана!\n\n"
            "Пользователь: {username}\n"
            "Провайдер: {provider}\n\n"
            "Ссылка:\n{link}"
        ),
        "en": (
            "✅ New room successfully provisioned!\n\n"
            "User: {username}\n"
            "Provider: {provider}\n\n"
            "Link:\n{link}"
        ),
    },
    "rotate_failed": {
        "ru": "❌ Ошибка при создании комнаты:\n{error}",
        "en": "❌ Room provisioning failed:\n{error}",
    },
    "status_card": {
        "ru": (
            "ℹ️ Диагностика туннеля\n\n"
            "Пользователь: {username}\n"
            "Провайдер: {provider}\n"
            "Статус службы: {status}\n"
            "Cookies: {cookie_status} ({cookie_file}, {cookie_size} байт)\n"
            "Активная комната: {link}"
        ),
        "en": (
            "ℹ️ Tunnel Diagnostics\n\n"
            "User: {username}\n"
            "Provider: {provider}\n"
            "Service status: {status}\n"
            "Cookies: {cookie_status} ({cookie_file}, {cookie_size} bytes)\n"
            "Active link: {link}"
        ),
    },
    "provider_menu": {
        "ru": (
            "⚙️ Выбор провайдера WebRTC\n\n"
            "Пользователь: {username}\n"
            "Текущий провайдер: {provider}\n\n"
            "Выберите платформу для переключения:"
        ),
        "en": (
            "⚙️ Select WebRTC Provider\n\n"
            "User: {username}\n"
            "Current provider: {provider}\n\n"
            "Choose platform to switch to:"
        ),
    },
    "provider_switched": {
        "ru": (
            "✅ Провайдер для {username} изменен на {provider}.{warning}\n\n"
            "Чтобы создать комнату с новым провайдером, выполните /rotate."
        ),
        "en": (
            "✅ Provider for {username} updated to {provider}.{warning}\n\n"
            "To activate a room with the new provider, run /rotate."
        ),
    },
    "help_user": {
        "ru": (
            "📖 Справка по командам Iris:\n\n"
            "• /start — главное меню и состояние службы\n"
            "• /link — получить активную ссылку на конференцию\n"
            "• /qr — получить QR-код картинкой для подключения с телефона\n"
            "• /rotate — пересоздать конференц-комнату (чистая ссылка)\n"
            "• /provider — выбор платформы (VK Звонки / Telemost / WB Stream / DION)\n"
            "• /status — диагностика службы и валидность cookies\n"
            "• /restart — перезапустить службу туннеля\n"
            "• /help — показать эту справку"
        ),
        "en": (
            "📖 Iris Command Reference:\n\n"
            "• /start — main menu and tunnel service status\n"
            "• /link — get active conference room link\n"
            "• /qr — display QR code for mobile client\n"
            "• /rotate — provision fresh room link\n"
            "• /provider — switch media platform (VK Calls / Telemost / WB Stream / DION)\n"
            "• /status — diagnostics, service status, and cookie validity\n"
            "• /restart — restart tunnel service\n"
            "• /help — display this help reference"
        ),
    },
    "help_admin_section": {
        "ru": (
            "\n\n👑 Команды администратора:\n"
            "• /list — список всех пользователей на сервере и их статусов\n"
            "• /link <user> — ссылка конкретного пользователя\n"
            "• /qr <user> — QR-код конкретного пользователя\n"
            "• /rotate <user> — пересоздать комнату пользователю\n"
            "• /provider <user> [name] — сменить платформу пользователю\n"
            "• /status <user> — статус службы и последние логи пользователя\n"
            "• /restart <user> — перезапустить службу пользователя\n"
            "• /start_service <user> — запустить службу пользователя\n"
            "• /stop_service <user> — остановить службу пользователя"
        ),
        "en": (
            "\n\n👑 Administrator Commands:\n"
            "• /list — list all users on the server and their statuses\n"
            "• /link <user> — get user conference link\n"
            "• /qr <user> — display user QR code\n"
            "• /rotate <user> — provision fresh room for user\n"
            "• /provider <user> [name] — switch provider for user\n"
            "• /status <user> — diagnostics and recent journal logs for user\n"
            "• /restart <user> — restart user tunnel service\n"
            "• /start_service <user> — start user tunnel service\n"
            "• /stop_service <user> — stop user tunnel service"
        ),
    },
    "btn_link": {"ru": "🔗 Ссылка", "en": "🔗 Link"},
    "btn_qr": {"ru": "📱 QR-код", "en": "📱 QR Code"},
    "btn_rotate": {"ru": "🔄 Новая комната", "en": "🔄 Rotate Room"},
    "btn_provider": {"ru": "⚙️ Провайдер", "en": "⚙️ Provider"},
    "btn_status": {"ru": "ℹ️ Статус", "en": "ℹ️ Status"},
    "btn_back": {"ru": "◀️ Назад в меню", "en": "◀️ Back to Menu"},
    "btn_admin_list": {"ru": "👥 Список пользователей", "en": "👥 User List"},
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
