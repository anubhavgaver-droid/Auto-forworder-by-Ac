import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Credentials
API_ID = int(os.getenv("API_ID", "1234567"))
API_HASH = os.getenv("API_HASH", "YOUR_API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING", "YOUR_PYROGRAM_SESSION_STRING")

# Admin Control (Space-separated Telegram User IDs)
ADMINS = [int(x) for x in os.getenv("ADMINS", "123456789").split()]

# Render Keep-Alive / Self-Ping Engine Configurations
# Render पर लाइव होने के बाद जो URL मिलेगा (जैसे: https://my-bot.onrender.com)
APP_URL = os.getenv("APP_URL", "")  
PORT = int(os.getenv("PORT", 8080))  # Render स्वतः 'PORT' असाइन करता है
