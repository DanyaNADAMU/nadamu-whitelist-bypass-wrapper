"""
Main entrypoint for WhitelistBypass Telegram Bot.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.telegram.config import bot_config
from bot.telegram.handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
)
logger = logging.getLogger("whitelist-bypass-tg-bot")


async def register_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Главное меню и статус"),
        BotCommand(command="link", description="Получить ссылку на комнату"),
        BotCommand(command="qr", description="Отобразить QR-код для Joiner"),
        BotCommand(command="rotate", description="Пересоздать комнату (новая ссылка)"),
        BotCommand(command="provider", description="Сменить провайдера (VK / Telemost)"),
        BotCommand(command="status", description="Статус туннеля и cookies"),
        BotCommand(command="help", description="Справка по командам"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Failed to set bot commands: {e}")


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
