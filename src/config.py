import logging
import os
import sys
from datetime import timedelta
from typing import NamedTuple

import stripe
from dotenv import load_dotenv

from enums import PricingTier


# Paths & Environment
BASE_PATH = os.path.dirname(__file__)
PROJECT_PATH = os.path.dirname(BASE_PATH)
RESOURCES_PATH = os.path.join(BASE_PATH, "resources")
PROMPTS_PATH = os.path.join(RESOURCES_PATH, "prompts")

load_dotenv(os.path.join(PROJECT_PATH, ".env"))

IS_PRODUCTION = bool(int(os.getenv("IS_PRODUCTION", "0")))


# Database
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


# Kafka
KAFKA_HOST = os.getenv("KAFKA_HOST")
KAFKA_PORT = int(os.getenv("KAFKA_PORT"))
KAFKA_BOOTSTRAP_SERVERS = f"{KAFKA_HOST}:{KAFKA_PORT}"
KAFKA_MODERATOR_EVENTS_TOPIC = os.getenv("KAFKA_MODERATOR_EVENTS_TOPIC")
KAKFA_ACTION_EVENTS_TOPIC = os.getenv("KAKFA_ACTION_EVENTS_TOPIC")


# Redis
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_USERNAME = os.getenv("REDIS_USERNAME")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = os.getenv("REDIS_DB")

REDIS_EMAIL_VERIFICATION_KEY_PREFIX = os.getenv("REDIS_EMAIL_VERIFICATION_KEY_PREFIX")
REDIS_STRIPE_INVOICE_METADATA_KEY_PREFIX = os.getenv(
    "REDIS_STRIPE_INVOICE_METADATA_KEY_PREFIX"
)
REDIS_USER_MODERATOR_MESSAGES_PREFIX = os.getenv("REDIS_USER_MODERATOR_MESSAGES_PREFIX")

REDIS_TTL_SECS = int(os.getenv("REDIS_TTL_SECS"))


# Discord
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

DISCORD_REDIRECT_URI = (
    "https://api.gova.chat/auth/discord/oauth"
    if IS_PRODUCTION
    else "http://localhost:8000/auth/discord/oauth"
)


# Stripe
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_PRICING_PRO_WEBHOOK_SECRET = os.getenv("STRIPE_PRICING_PRO_WEBHOOOK_SECRET")
STRIPE_PRICING_PRO_PRICE_ID = os.getenv("STRIPE_PRICING_PRO_PRICE_ID")

stripe.api_key = STRIPE_API_KEY


# LLM
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")

MAX_RETRIES = 5


# Prompts
def load_prompt(filename: str) -> str:
    with open(os.path.join(PROMPTS_PATH, filename), encoding="utf-8") as f:
        return f.read()


SECURITY_SYSTEM_PROMPT = load_prompt("security-system-prompt.txt")
TOPICS_SYSTEM_PROMPT = load_prompt("topic-system-prompt.txt")
SCORE_SYSTEM_PROMPT = load_prompt("score-system-prompt.txt")
SCORE_PROMPT_TEMPLATE = load_prompt("score-prompt-template.txt")
FINAL_SYSTEM_PROMPT = load_prompt("final-system-prompt.txt")
FINAL_PROMPT_TEMPLATE = load_prompt("final-prompt-template.txt")


# Email
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
CUSTOMER_SUPPORT_EMAIL = os.getenv("CUSTOMER_SUPPORT_EMAIL")


# Server
PAGE_SIZE = 10

if IS_PRODUCTION:
    SCHEME = "https"
    SUB_DOMAIN = "www."
    DOMAIN = "gova.chat"
else:
    SCHEME = "http"
    SUB_DOMAIN = ""
    DOMAIN = "localhost:5173"

BASE_URL = f"{SCHEME}://{SUB_DOMAIN}{DOMAIN}"


# Authentication & Security
COOKIE_ALIAS = "app-cookie"

JWT_ALGO = os.getenv("JWT_ALGO")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_EXPIRY_SECS = timedelta(seconds=int(os.getenv("JWT_EXPIRY_SECS")))

PW_HASH_SALT = os.getenv("PW_HASH_SALT")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
ENCRYPTION_IV_LEN = int(os.getenv("ENCRYPTION_IV_LEN"))


# Pricing Tiers
class TierLimit(NamedTuple):
    max_messages: int
    max_moderators: int
    max_concurrent: int


class PricingTierLimits:
    _TIER_LIMITS = {
        PricingTier.FREE: TierLimit(
            max_messages=1000, max_moderators=3, max_concurrent=1
        ),
        PricingTier.PRO: TierLimit(
            max_messages=1000, max_moderators=3, max_concurrent=1
        ),
    }

    @classmethod
    def get(cls, pricing_tier: PricingTier) -> TierLimit:
        if pricing_tier not in cls._TIER_LIMITS:
            raise ValueError(f"Missing tier limits for {pricing_tier}")
        return cls._TIER_LIMITS[pricing_tier]


# Logging
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"

logging.basicConfig(
    filename="app.log",
    filemode="a",
    format=LOG_FORMAT,
    level=logging.INFO,
)

root_logger = logging.getLogger()

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(logging.Formatter(LOG_FORMAT))
root_logger.addHandler(stdout_handler)

logging.getLogger("kafka").setLevel(logging.CRITICAL)
logging.getLogger("stripe").setLevel(logging.CRITICAL)

root_logger.info(
    "MODE=%s",
    "PRODUCTION" if IS_PRODUCTION else "DEV",
)

del root_logger
del stdout_handler
