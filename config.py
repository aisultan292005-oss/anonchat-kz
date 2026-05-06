import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot ───────────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/anonbot"
)

# ── Premium / Payments ────────────────────────────────────────────────────────
PAYMENT_PROVIDER_TOKEN: str = os.getenv("PAYMENT_PROVIDER_TOKEN", "")
PREMIUM_PRICE_XTR: int = int(os.getenv("PREMIUM_PRICE_XTR", "100"))   # Telegram Stars
PREMIUM_DAYS: int = int(os.getenv("PREMIUM_DAYS", "30"))

# ── Limits ────────────────────────────────────────────────────────────────────
MIN_AGE: int = 18
MAX_AGE: int = 80
INACTIVITY_TIMEOUT: int = int(os.getenv("INACTIVITY_TIMEOUT", "300"))  # seconds
ANTI_SPAM_MESSAGES: int = 5      # max messages per window
ANTI_SPAM_WINDOW: int = 5        # seconds
REPORT_HISTORY_LEN: int = 10     # last N messages sent with report

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")

# ── SMS (Mobizon) ─────────────────────────────────────────────────────────────
MOBIZON_API_KEY: str = os.getenv("MOBIZON_API_KEY", "")
SMS_ENABLED: bool = os.getenv("SMS_ENABLED", "true").lower() == "true"
