import logging
import os
import sys
from datetime import timedelta
from urllib.parse import quote

import stripe
from dotenv import load_dotenv
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine


BASE_PATH = os.path.dirname(__file__)
RESOURCES_PATH = os.path.join(BASE_PATH, "resources")
PROMPTS_PATH = os.path.join(RESOURCES_PATH, "prompts")

load_dotenv(os.path.join(BASE_PATH, ".env"))

IS_PRODUCTION = bool(os.getenv("IS_PRODUCTION"))

# DB
DB_HOST_CREDS = f"{os.getenv("DB_HOST", "localhost")}:{os.getenv("DB_PORT", 5132)}"
DB_USER_CREDS = (
    f"{os.getenv("DB_USER", "postgres")}:{quote(os.getenv("PASSWORD", "password"))}"
)
DB_NAME = os.getenv("DB_NAME")
DB_ENGINE = create_async_engine(
    f"postgresql+asyncpg://{DB_USER_CREDS}@{DB_HOST_CREDS}/{DB_NAME}"
)
DB_ENGINE_SYNC = create_engine(
    f"postgresql+psycopg2://{DB_USER_CREDS}@{DB_HOST_CREDS}/{DB_NAME}"
)

# Kafka
KAFKA_HOST = os.getenv("KAFKA_HOST")
KAFKA_PORT = int(os.getenv("KAFKA_PORT"))
KAFKA_BOOTSTRAP_SERVER = f"{KAFKA_HOST}:{KAFKA_PORT}"
KAFKA_DEPLOYMENT_EVENTS_TOPIC = os.getenv("KAFKA_DEPLOYMENT_EVENTS_TOPIC")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_CLIENT = AsyncRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    encoding="utf-8",
    decode_responses=True,
)
REDIS_EMAIL_VERIFICATION_KEY_PREFIX = os.getenv("REDIS_EMAIL_VERIFICATION_KEY_PREFIX")
REDIS_STRIPE_INVOICE_METADATA_KEY_PREFIX = os.getenv(
    "REDIS_STRIPE_INVOICE_METADATA_KEY_PREFIX"
)
REDIS_EXPIRY = 900

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

# Auth
COOKIE_ALIAS = "app-cookie"
JWT_ALGO = os.getenv("JWT_ALGO")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_EXPIRY = timedelta(days=1000)

# Security
PW_HASH_SALT = os.getenv("PW_HASH_SALT")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
ENCRYPTION_IV_LEN = int(os.getenv("ENCRYPTION_IV_LEN"))

# LLM
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_AGENT_ID = os.getenv("LLM_AGENT_ID")
LLM_BASE_URL = "https://api.mistral.ai/v1/"
LLM_MODEL_NAME = "open-mixtral-8x22b"

# Prompts
with open(os.path.join(PROMPTS_PATH, "security-system-prompt.txt")) as f:
    SECURITY_SYSTEM_PROMPT = f.read()
with open(os.path.join(PROMPTS_PATH, "topic-system-prompt.txt")) as f:
    TOPICS_SYSTEM_PROMPT = f.read()
with open(os.path.join(PROMPTS_PATH, "score-system-prompt.txt")) as f:
    SCORE_SYSTEM_PROMPT = f.read()
with open(os.path.join(PROMPTS_PATH, "score-prompt-template.txt")) as f:
    SCORE_PROMPT_TEMPLATE = f.read()
with open(os.path.join(PROMPTS_PATH, "final-system-prompt.txt")) as f:
    FINAL_SYSTEM_PROMPT = f.read()
with open(os.path.join(PROMPTS_PATH, "final-prompt-template.txt")) as f:
    FINAL_PROMPT_TEMPLATE = f.read()

# Discord
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if IS_PRODUCTION:
    DISCORD_REDIRECT_URI = "https://api.gova.chat/auth/discord/oauth"
else:
    DISCORD_REDIRECT_URI = "http://localhost:8000/auth/discord/oauth"

# Stripe
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_PRICING_PRO_WEBHOOOK_SECRET = os.getenv("STRIPE_PRICING_PRO_WEBHOOOK_SECRET")
STRIPE_PRICING_PRO_PRICE_ID = os.getenv("STRIPE_PRICING_PRO_PRICE_ID")
stripe.api_key = STRIPE_API_KEY

# SMTP
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_LOGIN = os.getenv("SMTP_LOGIN")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Brevo
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

# Email
PERSONAL_EMAIL = os.getenv("PERSONAL_EMAIL")

# Logging
logging.basicConfig(
    filename="app.log",
    filemode="a",
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter("%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")
)
logger.addHandler(handler)

kafka_logger = logging.getLogger("kafka")
kafka_logger.setLevel(logging.CRITICAL)
del kafka_logger

stripe_logger = logging.getLogger("stripe")
stripe_logger.setLevel(logging.CRITICAL)
del stripe_logger

logger.info(f"PRODUCTION={IS_PRODUCTION}")
del logger
