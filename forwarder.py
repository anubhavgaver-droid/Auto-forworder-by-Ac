import asyncio
import logging
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait

logger = logging.getLogger("ForwarderEngine")

class ForwarderEngine:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db

    def is_valid_media(self, message: Message, filter_type: str) -> bool:
        if filter_type == "all":
            return True
        elif filter_type == "video" and (message.video or message.animation):
            return True
        elif filter_type == "audio" and (message.audio or message.voice):
            return True
        elif filter_type == "document" and message.document:
            return True
        elif filter_type == "photo" and message.photo:
            return True
        elif filter_type == "text" and message.text:
            return True
        return False

    async def forward_message(self, message: Message, task):
        target_chat = task["target_id"]
        topic_id = task["target_topic_id"]
        remove_caption = bool(task["remove_caption"])
        custom_footer = task["custom_footer"]

        try:
            caption = None
            if not remove_caption and message.caption:
                caption = message.caption + (f"\n\n{custom_footer}" if custom_footer else "")
            elif custom_footer and not message.text:
                caption = custom_footer

            # 1. Text Message
            if message.text:
                text_content = message.text + (f"\n\n{custom_footer}" if custom_footer else "")
                await self.app.send_message(
                    chat_id=target_chat,
                    text=text_content,
                    message_thread_id=topic_id  # Topic Group Thread ID
                )

            # 2. Files / Media (Video, Audio, Docs, Photos, Voice, Stickers etc.)
            else:
                await message.copy(
                    chat_id=target_chat,
                    caption=caption,
                    message_thread_id=topic_id  # Topic Group Thread ID
                )

            logger.info(f"✅ [BOT] Forwarded Msg {message.id} -> Chat {target_chat} (Topic Thread: {topic_id})")

        except FloodWait as e:
            logger.warning(f"⏳ Rate limit hit. Sleeping for {e.value} seconds...")
            await asyncio.sleep(e.value)
            await self.forward_message(message, task)
        except Exception as e:
            logger.error(f"❌ Bot Forwarding error for Msg {message.id}: {e}")

    async def handle_incoming_message(self, message: Message):
        source_id = message.chat.id
        tasks = await self.db.get_tasks_by_source(source_id)

        if not tasks:
            return

        for task in tasks:
            if self.is_valid_media(message, task["filter_type"]):
                await self.forward_message(message, task)

    async def run_range_forwarder(self, source_id: int, target_id: int, start_id: int, end_id: int, topic_id: int = None, filter_type: str = "all"):
        logger.info(f"🚀 Batch Range Started: {source_id} -> {target_id} [Msg {start_id} to {end_id}]")
        
        task = {
            "target_id": target_id,
            "target_topic_id": topic_id,
            "remove_caption": False,
            "custom_footer": None
        }

        for msg_id in range(start_id, end_id + 1):
            try:
                msg = await self.app.get_messages(source_id, msg_id)
                if msg and not msg.empty and self.is_valid_media(msg, filter_type):
                    await self.forward_message(msg, task)
                    await asyncio.sleep(2.5)
            except Exception as e:
                logger.error(f"Error fetching Msg {msg_id}: {e}")
