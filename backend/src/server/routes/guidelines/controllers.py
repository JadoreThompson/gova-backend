from aiohttp import ClientSession

from config import BREACH_TYPES_SYSTEM_PROMPT
from utils.llm import fetch_response, parse_to_json


HTTP_SESS: ClientSession | None = None


async def get_breach_types(text: str) -> list[str]:
    data = await fetch_response(
        [
            {"role": "system", "content": BREACH_TYPES_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
    )
    btypes = parse_to_json(data['choices'][0]['message']['content'])
    return btypes
