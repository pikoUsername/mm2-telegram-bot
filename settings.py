import os

from dotenv import load_dotenv

load_dotenv()

# Токен бота
API_TOKEN = os.getenv('BOT_API_TOKEN')
CHAT_ID = os.getenv("CHAT_ID")
DATABASE_URL = "sqlite+aiosqlite:///transactions.db"

SERVICE_API_URL = f"{os.getenv('WEB_API_URL')}/api/{os.getenv('WEB_API_TOKEN')}"
