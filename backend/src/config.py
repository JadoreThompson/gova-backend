import os
from dotenv import load_dotenv


BASE_PATH = os.path.dirname(__file__)


load_dotenv(os.path.join(BASE_PATH, ".env"))

with open(os.path.join(BASE_PATH, "resources", "system-prompt.txt")) as f:
    SYSTEM_PROMPT = f.read()


# LLM
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_AGENT_ID = os.getenv("LLM_AGENT_ID")
