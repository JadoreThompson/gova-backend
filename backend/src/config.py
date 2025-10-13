import logging
import os
import sys
from datetime import timedelta
from urllib.parse import quote

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine


BASE_PATH = os.path.dirname(__file__)
RESOURCES_PATH = os.path.join(BASE_PATH, "resources")
PROMPTS_PATH = os.path.join(RESOURCES_PATH, "prompts")


load_dotenv(os.path.join(BASE_PATH, ".env"))


PRODUCTION = False


# Auth
COOKIE_ALIAS = "app-cookie"
JWT_ALGO = os.getenv("JWT_ALGO", "HS256")
JWT_SECRET = os.getenv("JWT_SECRET", "secret")
JWT_EXPIRY = timedelta(days=1000)


# DB
DB_HOST_CREDS = f"{os.getenv("DB_HOST", "localhost")}:{os.getenv("DB_PORT", 5132)}"
DB_USER_CREDS = f"{os.getenv("DB_USER", "postgres")}:{quote(os.getenv("PASSWORD", "password"))}"
DB_NAME = os.getenv("DB_NAME", "ai_chat_mod")
DB_ENGINE = create_async_engine(
    f"postgresql+asyncpg://{DB_USER_CREDS}@{DB_HOST_CREDS}/{DB_NAME}"
)


# Logging
logging.basicConfig(format="%(asctime)s - [%(levelname)s] - %(module)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter("%(asctime)s - [%(levelname)s] - %(module)s - %(message)s")
)
logger.addHandler(handler)


# Prompts
with open(os.path.join(PROMPTS_PATH, "topic-system-prompt.txt")) as f:
    TOPIC_PROMPT = f.read()
with open(os.path.join(PROMPTS_PATH, "score-system-prompt.txt")) as f:
    SCORE_PROMPT = f.read()
with open(os.path.join(PROMPTS_PATH, "final-prompt.txt")) as f:
    FINAL_PROMPT = f.read()


# LLM
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_AGENT_ID = os.getenv("LLM_AGENT_ID")
