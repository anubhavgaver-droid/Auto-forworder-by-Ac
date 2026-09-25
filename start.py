
import asyncio
import logging
import aiohttp
from threading import Thread
from flask import Flask, jsonify
from pyrogram import Client, filters
from pyrogram.types import Message

from config import API_ID, API_HASH, BOT_TOKEN, ADMINS, APP_URL, PORT
from database import Database
from forwarder import ForwarderEngine

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MainBot")

# Keep-Alive Web Server
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return jsonify({"status": "online", "message": "Render Keep-Alive Web Server Active!"}), 200

@web_app.route('/health')
def health():
    return "OK", 200

def run_flask_server(port: int):
    web_app.run(host="0.0.0.0", port=port)

async def self_ping_loop(app_url: str, interval: int = 300):
    if not app_url:
        logger.warning("⚠️ APP_URL सेट नहीं है! Render पर ऐप सो सकता है। Variable ज़रूर सेट करें।")
        return

    ping_url = f"{app_url.rstrip('/')}/health"
    logger.info(f"🚀 Self-Pinger Engine Active: {ping_url}")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(ping_url) as resp:
                    if resp.status == 200:
                        logger.info("💓 [PING SUCCESS] Self-Ping Complete! Server Sleeping Prevented.")
                    else:
                        logger.warning(f"⚠️ Self-Ping returned status code: {resp.status}")
            except Exception as e:
                logger.error(f"❌ Self-Ping Ping Error: {e}")

            await asyncio.sleep(interval)

# Telegram Bot Client Init
if not BOT_TOKEN:
    logger.critical("❌ BOT_TOKEN गायब है! कृपया config.py या Environment Variable में BOT_TOKEN डालें।")
    exit(1)

app = Client("auto_forwarder_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = Database()
engine = ForwarderEngine(app, db)

# ----------------- BOT COMMANDS ----------------- #

# /start कमांड (प्राइवेट और ग्रुप दोनों जगह काम करेगी)
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_name = message.from_user.first_name if message.from_user else "User"
    welcome_text = (
        f"👋 **नमस्ते {user_name}!**\n\n"
        "🤖 **मैं आपका Auto-Forwarder Telegram Bot हूँ!**\n"
        "मैं Render पर **Self-Ping (24/7 Alive)** के साथ एक्टिव हूँ।\n\n"
        "⚙️ **ज़रूरी स्टेप:**\n"
        "मुझे Source Channel/Group और Target Channel/Group दोनों में **Admin** बनाएं।\n\n"
        "🛠 **कमांड्स:**\n"
        "• `/add_task <source_id> <target_id> [topic_id]` - नया लाइव टास्क जोड़ें\n"
        "• `/range_forward <source_id> <target_id> <start_id> <end_id> [topic_id]` - पुराने मैसेज फॉरवर्ड करें"
    )
    await message.reply_text(welcome_text)

# Task जोड़ने की कमांड
@app.on_message(filters.command("add_task"))
async def add_task_cmd(client: Client, message: Message):
    # Admin Verification
    if ADMINS and message.from_user and message.from_user.id not in ADMINS:
        await message.reply_text("❌ **आपके पास इस कमांड को इस्तेमाल करने की परमिशन नहीं है!**")
        return

    args = message.command[1:]
    if len(args) < 2:
        await message.reply_text("❌ **Usage:** `/add_task <source_chat_id> <target_chat_id> [target_topic_id]`")
        return

    try:
        source_id = int(args[0])
        target_id = int(args[1])
        topic_id = int(args[2]) if len(args) > 2 else None

        task_id = await db.add_task(source_id, target_id, target_topic_id=topic_id)
        await message.reply_text(
            f"✅ **Task Added Successfully!**\n\n"
            f"• Task ID: `{task_id}`\n"
            f"• Source ID: `{source_id}`\n"
            f"• Target ID: `{target_id}`\n"
            f"• Topic ID: `{topic_id or 'None'}`"
        )
    except ValueError:
        await message.reply_text("❌ **गलत चैट ID दर्ज की गई है। कृपया संख्या (Numbers) में दर्ज करें!**")

# Range Forwarding कमांड
@app.on_message(filters.command("range_forward"))
async def range_forward_cmd(client: Client, message: Message):
    if ADMINS and message.from_user and message.from_user.id not in ADMINS:
        await message.reply_text("❌ **आपके पास इस कमांड को इस्तेमाल करने की परमिशन नहीं है!**")
        return

    args = message.command[1:]
    if len(args) < 4:
        await message.reply_text("❌ **Usage:** `/range_forward <source> <target> <start_id> <end_id> [topic_id]`")
        return

    try:
        source_id = int(args[0])
        target_id = int(args[1])
        start_id = int(args[2])
        end_id = int(args[3])
        topic_id = int(args[4]) if len(args) > 4 else None

        await message.reply_text(f"⏳ Starting range forwarding Msg ID `{start_id}` to `{end_id}`...")
        asyncio.create_task(engine.run_range_forwarder(source_id, target_id, start_id, end_id, topic_id=topic_id))
    except ValueError:
        await message.reply_text("❌ **गलत फ़ॉर्मेट! कृपया संख्याएँ दर्ज करें।**")

# ----------------- REALTIME EVENT LISTENER ----------------- #

@app.on_message(~filters.private)
async def realtime_listener(client: Client, message: Message):
    await engine.handle_incoming_message(message)

# ----------------- MAIN RUNNER ----------------- #

async def main():
    await db.init()

    # Web Server स्टार्ट करें (Render Port Requirement)
    t = Thread(target=run_flask_server, args=(PORT,), daemon=True)
    t.start()
    logger.info(f"🌐 Keep-Alive Web Server listening on port {PORT}")

    # Bot स्टार्ट करें
    await app.start()
    logger.info("==========================================")
    logger.info("🤖 Auto Forwarder Bot Started Successfully!")
    logger.info("==========================================")

    # Self-Ping Loop स्टार्ट करें
    if APP_URL:
        asyncio.create_task(self_ping_loop(APP_URL, interval=300))

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot Stopped!")
