import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))
DEFAULT_TEMPERATURE = float(os.getenv("TEMPERATURE", "0.8"))

DEFAULT_SYSTEM_PROMPT = (
    "Ты — умный и дружелюбный AI-ассистент. "
    "Отвечай информативно, четко и вежливо."
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_database.db")
