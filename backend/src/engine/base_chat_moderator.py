import os
from uuid import UUID

from aiohttp import ClientSession

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL_NAME,
    RESOURCES_PATH,
    TOPIC_SYSTEM_PROMPT,
)
from core.enums import ChatPlatformType
from utils.llm import parse_to_json


class BaseChatModerator:
    def __init__(self, project_id: UUID) -> None:
        self._project_id = project_id
        self._topics: list[str] | None = None
        self._guidelines: str | None = None
        self._http_sess: ClientSession | None = None

    async def _fetch_llm_response(self, messages: list[dict]):
        body = {"model": LLM_MODEL_NAME, "messages": messages}
        rsp = await self._http_sess.post("chat/completions", json=body)
        rsp.raise_for_status()
        data = await rsp.json()
        content = data["choices"][0]["message"]["content"]
        return parse_to_json(content)

    def _fetch_guidelines(self) -> None:
        with open(os.path.join(RESOURCES_PATH, "guidelines.txt")) as f:
            return f.read()

    async def _fetch_topics(self, platform: ChatPlatformType) -> list[str]:
        return await self._fetch_llm_response(
            [
                {"role": "system", "content": TOPIC_SYSTEM_PROMPT},
                {"role": "user", "content": self._guidelines},
            ]
        )

    async def __aenter__(self):
        self._http_sess = ClientSession(
            base_url=LLM_BASE_URL, headers={"Authorization": f"Bearer {LLM_API_KEY}"}
        )
        return self

    async def __aexit__(self, exc_type, exc_value, tcb) -> None:
        await self._http_sess.close()
        self._http_sess = None
