from config import TOPICS_SYSTEM_PROMPT
from utils.llm import fetch_response, parse_to_json


async def get_topics(text: str) -> list[str]:
    data = await fetch_response(
        [
            {"role": "system", "content": TOPICS_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
    )
    topics = parse_to_json(data["choices"][0]["message"]["content"])
    return topics
