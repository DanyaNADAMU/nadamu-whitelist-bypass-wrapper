"""
Lightweight asynchronous VK API & Bots LongPoll client using aiohttp.
"""

import asyncio
import json
import logging
import random
from typing import Any, AsyncGenerator, Optional
import aiohttp

from bot.vk.config import VkBotConfig, vk_config

logger = logging.getLogger("whitelist-bypass-vk-client")


class VkApiError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(f"VK API Error [{code}]: {message}")
        self.code = code
        self.message = message


class VkClient:
    """Async client for VK Bots API and LongPoll events."""

    def __init__(self, config: Optional[VkBotConfig] = None):
        self.config = config or vk_config
        self.base_url = "https://api.vk.com/method"
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=45.0)
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def call(self, method: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Execute a VK API method."""
        session = await self.get_session()
        payload = {
            "v": self.config.api_version,
            "access_token": self.config.group_token,
        }
        if params:
            for k, v in params.items():
                if v is not None:
                    payload[k] = str(v)

        url = f"{self.base_url}/{method}"
        async with session.post(url, data=payload) as resp:
            data = await resp.json(content_type=None)

        if "error" in data:
            err = data["error"]
            code = err.get("error_code", 0)
            msg = err.get("error_msg", "Unknown VK API error")
            raise VkApiError(code, msg)

        return data.get("response", {})

    async def send_message(
        self,
        peer_id: int,
        message: str,
        keyboard: Optional[dict[str, Any]] = None,
        attachment: Optional[str] = None,
    ) -> int:
        """Send a message to a user or chat with optional inline keyboard and attachment."""
        params: dict[str, Any] = {
            "peer_id": peer_id,
            "message": message,
            "random_id": random.randint(1, 2**31 - 1),
            "dont_parse_links": 0,
        }
        if keyboard:
            params["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
        if attachment:
            params["attachment"] = attachment

        res = await self.call("messages.send", params)
        if isinstance(res, int):
            return res
        elif isinstance(res, list) and res:
            return res[0].get("message_id", 0)
        return 0

    async def upload_message_photo(
        self, peer_id: int, photo_bytes: bytes, filename: str = "qr.png"
    ) -> Optional[str]:
        """Upload a photo and return its attachment identifier (e.g., 'photo123_456')."""
        try:
            # 1. Get upload URL
            upload_info = await self.call(
                "photos.getMessagesUploadServer", {"peer_id": peer_id}
            )
            upload_url = upload_info.get("upload_url")
            if not upload_url:
                return None

            # 2. Upload file via multipart/form-data
            session = await self.get_session()
            data = aiohttp.FormData()
            data.add_field("photo", photo_bytes, filename=filename, content_type="image/png")

            async with session.post(upload_url, data=data) as resp:
                upload_res = await resp.json(content_type=None)

            # 3. Save photo
            server = upload_res.get("server")
            photo = upload_res.get("photo")
            hash_code = upload_res.get("hash")
            if not photo or server is None or not hash_code:
                return None

            saved = await self.call(
                "photos.saveMessagesPhoto",
                {"server": server, "photo": photo, "hash": hash_code},
            )

            if isinstance(saved, list) and saved:
                photo_obj = saved[0]
                owner_id = photo_obj.get("owner_id")
                photo_id = photo_obj.get("id")
                return f"photo{owner_id}_{photo_id}"
        except Exception as e:
            logger.warning(f"Failed to upload VK message photo: {e}")

        return None

    async def get_long_poll_server(self) -> dict[str, Any]:
        """Fetch LongPoll server credentials."""
        return await self.call(
            "groups.getLongPollServer", {"group_id": self.config.group_id}
        )

    async def poll_events(self) -> AsyncGenerator[dict[str, Any], None]:
        """
        Continuous Bots LongPoll event generator with automatic reconnection
        and error recovery (failed codes 1, 2, 3).
        """
        server_info = await self.get_long_poll_server()
        server = server_info["server"]
        key = server_info["key"]
        ts = str(server_info["ts"])

        logger.info("VK Bots LongPoll connected successfully.")

        session = await self.get_session()

        while True:
            url = f"{server}?act=a_check&key={key}&ts={ts}&wait=25"
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=35.0)) as resp:
                    data = await resp.json(content_type=None)

                if "failed" in data:
                    failed = data["failed"]
                    if failed == 1:
                        ts = str(data.get("ts", ts))
                    elif failed in (2, 3):
                        logger.info("LongPoll key expired, renewing server credentials...")
                        server_info = await self.get_long_poll_server()
                        server = server_info["server"]
                        key = server_info["key"]
                        if failed == 3:
                            ts = str(server_info["ts"])
                    continue

                ts = str(data.get("ts", ts))
                updates = data.get("updates", [])
                for update in updates:
                    yield update

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"LongPoll network error: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3.0)
                try:
                    server_info = await self.get_long_poll_server()
                    server = server_info["server"]
                    key = server_info["key"]
                    ts = str(server_info["ts"])
                except Exception:
                    pass
