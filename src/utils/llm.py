import logging
from json import loads

from aiohttp import ClientSession

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME


logger = logging.getLogger("utils.llm")


def parse_to_json(value: str) -> dict | list:
    logger.info(f"Handling '{value}'")

    try:
        s = "```json"
        ind = value.index(s)
        value = value[ind + len(s) :]
    except ValueError:
        pass

    try:
        s = "```"
        ind = value.index(s)
        value = value[:ind]
    except ValueError:
        pass

    logger.info(f"Parsed to {value}")
    return loads(value)


def _create_request():
    http_sess = None

    async def fetch(messages: list[dict], temperature: float = 0.7):
        nonlocal http_sess

        if http_sess is None:
            http_sess = ClientSession(
                base_url=LLM_BASE_URL,
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            )

        body = {"model": LLM_MODEL_NAME, "messages": messages, "temperature": temperature}
        rsp = await http_sess.post("chat/completions", json=body)
        rsp.raise_for_status()
        data = await rsp.json()
        return data

    return fetch


fetch_response = _create_request()
