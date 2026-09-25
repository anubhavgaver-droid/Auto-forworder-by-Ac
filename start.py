import asyncio
import logging
import aiohttp
from threading import Thread
from flask import Flask, jsonify
from pyrogram import Client, filters
from pyrogram.types import Message

from config import API_ID, API_HASH, SESSION_STRING, ADMINS, APP_URL, PORT
from database import Database
from forwarder import ForwarderEngine

# ----------------- LOGGING SETUP ----------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MainBot")

# ----------------- KEEP-ALIVE FLASK ENGINE ----------------- #
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return jsonify({"status": "online", "message": "Render Keep-Alive Active!"}), 200

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

# ----------------- TELEGRAM CLIENT INIT ----------------- #
if not SESSION_STRING:
    logger.critical("❌ SESSION_STRING गायब है! Render पर चलाने के लिए SESSION_STRING अनिवार्य है।")
    exit(1)

app = Client("auto_forwarder_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
db = Database()
engine = ForwarderEngine(app, db)

# ----------------- BOT COMMANDS ----------------- #

@app.on_message(filters.command("start") & filters.me)
async def start_cmd(client: Client, message: Message):
    welcome_text = (
        "🤖 **Auto-Forwarder Engine is Active!**\n\n"
        "यह यूजरबॉट Render पर **Self-Ping (24/7 Awake)** के साथ एक्टिव है।\n\n"
        "🌐 **सपोर्टेड राउटिंग प्रकार:**\n"
        "• Channel ➔ Channel\n"
        "• Group ➔ Group\n"
        "• Topic Group ➔ Topic Group (Specific Topic Thread ID)\n"
        "• Channel ➔ Topic Group\n\n"
        "🛠 **कमांड्स:**\n"
        "• `/add_task <source_id> <target_id> [topic_id]` - लाइव ऑटो-फॉरवर्ड टास्क जोड़ें\n"
        "• `/range_forward <source_id> <target_id> <start_id> <end_id> [topic_id]` - पुराने मैसेज फॉरवर्ड करें"
    )
    await message.reply_text(welcome_text)

@app.on_message(filters.command("add_task") & filters.me)
async def add_task_cmd(client: Client, message: Message):
    args = message.command[1:]
    if len(args) < 2:
        await message.reply_text("❌ **Usage:** `/add_task <source_chat_id> <target_chat_id> [target_topic_id]`")
        return

    source_id = int(args[0])
    target_id = int(args[1])
    topic_id = int(args[2]) if len(args) > 2 else None

    task_id = await db.add_task(source_id, target_id, target_topic_id=topic_id)
    await message.reply_text(f"✅ **Task Added!**\n• Task ID: `{task_id}`\n• Source: `{source_id}`\n• Target: `{target_id}`\n• Topic ID: `{topic_id or 'None'}`")

@app.on_message(filters.command("range_forward") & filters.me)
async def range_forward_cmd(client: Client, message: Message):
    args = message.command[1:]
    if len(args) < 4:
        await message.reply_text("❌ **Usage:** `/range_forward <source> <target> <start_id> <end_id> [topic_id]`")
        return

    source_id = int(args[0])
    target_id = int(args[1])
    start_id = int(args[2])
    end_id = int(args[3])
    topic_id = int(args[4]) if len(args) > 4 else None

    await message.reply_text(f"⏳ Starting range forwarding Msg ID `{start_id}` to `{end_id}`...")
    asyncio.create_task(engine.run_range_forwarder(source_id, target_id, start_id, end_id, topic_id=topic_id))

# ----------------- REALTIME EVENT LISTENER ----------------- #

@app.on_message(~filters.me & ~filters.private)
async def realtime_listener(client: Client, message: Message):
    await engine.handle_incoming_message(message)

# ----------------- MAIN RUNNER ----------------- #

async def main():
    # 1. Initialize DB
    await db.init()

    # 2. Start Web Server in Background Thread
    t = Thread(target=run_flask_server, args=(PORT,), daemon=True)
    t.start()
    logger.info(f"🌐 Keep-Alive Web Server listening on port {PORT}")

    # 3. Start Pyrogram Client
    await app.start()
    logger.info("==========================================")
    logger.info("🤖 Auto Forwarder Bot Started Successfully!")
    logger.info("==========================================")

    # 4. Start Self-Ping Engine (Prevents Render Sleep)
    if APP_URL:
        asyncio.create_task(self_ping_loop(APP_URL, interval=300))

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot Stopped!")
