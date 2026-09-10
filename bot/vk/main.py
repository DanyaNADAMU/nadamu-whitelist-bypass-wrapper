"""
Main entrypoint for WhitelistBypass / Iris VK Bot Dispatcher.
"""

import asyncio
import logging
import signal
import sys

from bot.vk.client import VkClient
from bot.vk.config import vk_config
from bot.vk.handlers import VkHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
)
logger = logging.getLogger("whitelist-bypass-vk-bot")


async def main_async() -> None:
    if not vk_config.group_token or not vk_config.group_id:
        logger.error(
            "VK_GROUP_TOKEN or VK_GROUP_ID is not set!\n"
            f"Please specify your community token and group ID in {vk_config.env_file_path}\n"
            "or via VK_GROUP_TOKEN and VK_GROUP_ID environment variables."
        )
        sys.exit(1)

    vk_client = VkClient(vk_config)
    handler = VkHandler(vk_client)

    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    logger.info(f"Iris VK Bot starting LongPoll for group_id={vk_config.group_id}...")

    try:
        async for event in vk_client.poll_events():
            if stop_event.is_set():
                break
            try:
                await handler.handle_update(event)
            except Exception as e:
                logger.exception(f"Error handling VK update: {e}")
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Closing VK API client session...")
        await vk_client.close()
        logger.info("Iris VK Bot stopped.")


def main() -> None:
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Iris VK Bot stopped.")


if __name__ == "__main__":
    main()
