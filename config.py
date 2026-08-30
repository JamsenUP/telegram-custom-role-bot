import os
from dotenv import load_dotenv

load_dotenv()

# Очищаем токен от пробелов, кавычек и скрытых символов
raw_tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_TOKEN = raw_tg_token.strip().strip("'\"").strip()

raw_openai_key = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_KEY = raw_openai_key.strip().strip("'\"").strip()

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip().strip("'\"").strip() or None
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct").strip().strip("'\"").strip()
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))
DEFAULT_TEMPERATURE = float(os.getenv("TEMPERATURE", "0.8"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1500"))

DEFAULT_SYSTEM_PROMPT = (
    "Ты — умный и дружелюбный AI-ассистент. "
    "Отвечай информативно, четко и вежливо."
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_database.db")
