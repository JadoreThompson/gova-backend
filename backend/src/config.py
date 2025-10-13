import os
from dotenv import load_dotenv


BASE_PATH = os.path.dirname(__file__)
RESOURCES_PATH = os.path.join(BASE_PATH, "resources")
PROMPTS_PATH = os.path.join(RESOURCES_PATH, "prompts")


load_dotenv(os.path.join(BASE_PATH, ".env"))


with open(os.path.join(PROMPTS_PATH, "topic-system-prompt.txt")) as f:
    TOPIC_PROMPT = f.read()
with open(os.path.join(PROMPTS_PATH, "score-system-prompt.txt")) as f:
    SCORE_PROMPT = f.read()
with open(os.path.join(PROMPTS_PATH, "final-prompt.txt")) as f:
    FINAL_PROMPT = f.read()


# LLM
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_AGENT_ID = os.getenv("LLM_AGENT_ID")
