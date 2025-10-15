from json import loads

from aiohttp import ClientSession

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME

HTTP_SESS: ClientSession | None = None


def parse_to_json(value: str) -> dict | list:
    s = "```json"
    ind = value.index(s)
    value = value[ind + len(s) :]

    s = "```"
    ind = value.index(s)
    value = value[:ind]

    return loads(value)


def get_http_sess() -> ClientSession:
    global HTTP_SESS

    if not HTTP_SESS:
        HTTP_SESS = ClientSession(
            base_url=LLM_BASE_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        )

    return HTTP_SESS


async def fetch_response(messages: list[dict]):
    http_sess = get_http_sess()
    body = {"model": LLM_MODEL_NAME, "messages": messages}
    rsp = await http_sess.post("chat/completions", json=body)
    rsp.raise_for_status()
    data = await rsp.json()
    return data
