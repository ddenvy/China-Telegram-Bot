# Configuration for China IT News Bot
import os
from dotenv import load_dotenv
load_dotenv()

def str_to_bool(value: str, default=True):
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "y", "on")

# Telegram bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Shanghai")

# Admins
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# LLM provider settings
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")  # deepseek | openai | gemini
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# LLM models and endpoints
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Publishing settings
PUBLISH_TIME = os.getenv("PUBLISH_TIME", "10:00")
ENABLE_HOURLY_POST = str_to_bool(os.getenv("ENABLE_HOURLY_POST", "true"), default=True)
ENABLE_DAILY_POST = str_to_bool(os.getenv("ENABLE_DAILY_POST", "false"), default=False)
MAX_ARTICLES_PER_DAY = int(os.getenv("MAX_ARTICLES_PER_DAY", "3"))

# RSS feeds and filters
RSS_FEEDS = [
    "https://www.scmp.com/rss/91/feed",
    "https://www.techinasia.com/feed",
]
EXCLUDE_KEYWORDS = ["sponsored", "advertisement"]

# Content limits
MAX_POST_LENGTH = int(os.getenv("MAX_POST_LENGTH", "3500"))

# AI polishing flags
AI_POLISH_ENABLE_VACANCY = str_to_bool(os.getenv("AI_POLISH_ENABLE_VACANCY", "true"), default=True)
AI_POLISH_ENABLE_AD = str_to_bool(os.getenv("AI_POLISH_ENABLE_AD", "true"), default=True)


def validate_config():
    """Validate essential configuration."""
    errors = []
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN не задан")
    if not CHANNEL_ID:
        errors.append("CHANNEL_ID не задан")
    # LLM key presence is optional depending on provider; warn if provider selected but key missing
    if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY не задан при LLM_PROVIDER=openai")
    if LLM_PROVIDER == "deepseek" and not DEEPSEEK_API_KEY:
        errors.append("DEEPSEEK_API_KEY не задан при LLM_PROVIDER=deepseek")
    if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY не задан при LLM_PROVIDER=gemini")

    if errors:
        raise ValueError("Ошибка конфигурации: " + "; ".join(errors))