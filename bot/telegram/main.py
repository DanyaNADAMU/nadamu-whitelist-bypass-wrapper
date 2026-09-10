"""
Main entrypoint for WhitelistBypass Telegram Bot.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    MenuButtonCommands,
)

from bot.telegram.config import bot_config
from bot.telegram.handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
)
logger = logging.getLogger("whitelist-bypass-tg-bot")


async def register_bot_commands(bot: Bot) -> None:
    """Register commands across scopes (Default, AllPrivateChats, AdminChats) and language codes."""
    user_commands_ru = [
        BotCommand(command="start", description="Главное меню и статус"),
        BotCommand(command="link", description="Получить ссылку на встречу"),
        BotCommand(command="qr", description="QR-код для подключения Joiner"),
        BotCommand(command="rotate", description="Пересоздать чистую комнату"),
        BotCommand(command="provider", description="Сменить платформу (VK/Telemost)"),
        BotCommand(command="status", description="Статус туннеля и cookies"),
        BotCommand(command="restart", description="Перезапустить службу туннеля"),
        BotCommand(command="help", description="Подробная справка по командам"),
    ]
    user_commands_en = [
        BotCommand(command="start", description="Main menu and service status"),
        BotCommand(command="link", description="Get active room link"),
        BotCommand(command="qr", description="Display QR code for Joiner"),
        BotCommand(command="rotate", description="Provision fresh room"),
        BotCommand(command="provider", description="Change media provider"),
        BotCommand(command="status", description="Tunnel status and diagnostics"),
        BotCommand(command="restart", description="Restart tunnel service"),
        BotCommand(command="help", description="Command reference and help"),
    ]

    admin_commands_ru = user_commands_ru + [
        BotCommand(command="list", description="[Admin] Список всех пользователей"),
        BotCommand(command="start_service", description="[Admin] Запустить службу пользователя"),
        BotCommand(command="stop_service", description="[Admin] Остановить службу пользователя"),
    ]
    admin_commands_en = user_commands_en + [
        BotCommand(command="list", description="[Admin] List all users"),
        BotCommand(command="start_service", description="[Admin] Start user service"),
        BotCommand(command="stop_service", description="[Admin] Stop user service"),
    ]

    # 1. Default scopes
    try:
        await bot.set_my_commands(user_commands_ru, scope=BotCommandScopeDefault(), language_code="ru")
        await bot.set_my_commands(user_commands_en, scope=BotCommandScopeDefault(), language_code="en")
        await bot.set_my_commands(user_commands_ru, scope=BotCommandScopeDefault())
    except Exception as e:
        logger.warning(f"Failed to set default bot commands: {e}")

    # 2. All private chats scope (required by Telegram mobile and desktop for 1-to-1 chats)
    try:
        await bot.set_my_commands(user_commands_ru, scope=BotCommandScopeAllPrivateChats(), language_code="ru")
        await bot.set_my_commands(user_commands_en, scope=BotCommandScopeAllPrivateChats(), language_code="en")
        await bot.set_my_commands(user_commands_ru, scope=BotCommandScopeAllPrivateChats())
    except Exception as e:
        logger.warning(f"Failed to set private chat commands: {e}")

    # 3. Admin chats scope
    for admin_id in bot_config.admin_ids:
        try:
            await bot.set_my_commands(admin_commands_ru, scope=BotCommandScopeChat(chat_id=admin_id), language_code="ru")
            await bot.set_my_commands(admin_commands_en, scope=BotCommandScopeChat(chat_id=admin_id), language_code="en")
            await bot.set_my_commands(admin_commands_ru, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.warning(f"Failed to set admin commands for chat {admin_id}: {e}")

    # 4. Explicitly enable the Menu button in the chat input bar
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception as e:
        logger.warning(f"Failed to set chat menu button: {e}")


async def main_async() -> None:
    if not bot_config.bot_token:
        logger.error(
            "TELEGRAM_BOT_TOKEN is not set!\n"
            f"Please specify your bot token in {bot_config.env_file_path} "
            "or via TELEGRAM_BOT_TOKEN environment variable."
        )
        sys.exit(1)

    bot = Bot(
        token=bot_config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await register_bot_commands(bot)

    logger.info("WhitelistBypass Telegram Bot is starting polling...")
    await dp.start_polling(bot)


def main() -> None:
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Telegram Bot stopped.")


if __name__ == "__main__":
    main()
