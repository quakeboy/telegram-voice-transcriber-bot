import logging
from typing import Optional, List
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger("transcriber")


class TelegramHandler:
    def __init__(self, bot_token: str, allowed_user_ids: List[int]):
        self.bot = Bot(token=bot_token)
        self.allowed_user_ids = allowed_user_ids
        self.last_update_id = 0

    async def get_voice_updates(self) -> List[dict]:
        """Poll for new voice messages from whitelisted users. Returns list of voice message updates."""
        try:
            updates = await self.bot.get_updates(offset=self.last_update_id + 1)
            voice_updates = []

            for update in updates:
                self.last_update_id = update.update_id

                if not update.message or not update.message.voice:
                    continue

                user_id = update.message.from_user.id
                if self.allowed_user_ids and user_id not in self.allowed_user_ids:
                    logger.debug(f"Ignoring voice from non-whitelisted user {user_id}")
                    continue

                voice_updates.append({
                    "update_id": update.update_id,
                    "user_id": user_id,
                    "username": update.message.from_user.username or f"user_{user_id}",
                    "first_name": update.message.from_user.first_name,
                    "voice_file_id": update.message.voice.file_id,
                    "duration": update.message.voice.duration,
                    "timestamp": update.message.date,
                    "message_id": update.message.message_id,
                })
                logger.info(f"Received voice from {voice_updates[-1]['username']} (ID: {user_id})")

            return voice_updates

        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            return []

    async def download_voice_file(self, file_id: str) -> Optional[bytes]:
        """Download voice file from Telegram. Returns file bytes or None on error."""
        try:
            file = await self.bot.get_file(file_id)
            file_bytes = await file.download_as_bytearray()
            return bytes(file_bytes)
        except TelegramError as e:
            logger.error(f"Failed to download voice file {file_id}: {e}")
            return None

    async def send_message(self, user_id: int, text: str, reply_to_message_id: Optional[int] = None) -> Optional[str]:
        """Send a message to user. Returns message_id on success or None on error."""
        try:
            message = await self.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown", reply_to_message_id=reply_to_message_id)
            return str(message.message_id)
        except TelegramError as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            return None

    async def edit_message(self, user_id: int, message_id: str, text: str) -> bool:
        """Edit an existing message. Returns True on success, False on error."""
        try:
            await self.bot.edit_message_text(chat_id=user_id, message_id=int(message_id), text=text, parse_mode="Markdown")
            return True
        except TelegramError as e:
            logger.warning(f"Failed to edit message {message_id} for user {user_id}: {e}")
            return False
