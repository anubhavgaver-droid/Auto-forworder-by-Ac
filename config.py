import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Credentials
API_ID = int(os.getenv("API_ID", "1234567"))
API_HASH = os.getenv("API_HASH", "YOUR_API_HASH")

# BotFather से मिला Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_FROM_BOTFATHER")

# Admin Control (आपका Telegram User ID ताकि आपके अलावा कोई और कमांड न चला सके)
ADMINS = [int(x) for x in os.getenv("ADMINS", "123456789").split()]

# Render Keep-Alive / Self-Ping Engine Configurations
APP_URL = os.getenv("APP_URL", "")  # Render URL (जैसे https://my-bot.onrender.com)
PORT = int(os.getenv("PORT", 8080))  # Render पोर्ट
