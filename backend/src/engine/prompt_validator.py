import asyncio
from json import JSONDecodeError

from aiohttp import ClientSession, ClientError
from pydantic import ValidationError

from engine.enums import MaliciousState
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME, SECURITY_SYSTEM_PROMPT
from utils.llm import parse_to_json


class PromptValidator:
    @classmethod
    async def validate_prompt(
        cls, prompt: str, sess: ClientSession | None = None, max_attempts: int = 3
    ) -> MaliciousState:
        """
        Validates that the incoming prompt isn't performing any prompt injection
        or malicious actions, with retry logic for transient failures.

        Args:
            prompt (str): The user prompt to validate.
            sess (ClientSession | None): Optional shared HTTP session.
            max_attempts (int): Max number of attempts before giving up.

        Returns:
            bool: Whether or not the prompt is malicious.
        """
        is_local = sess is None
        if is_local:
            sess = ClientSession(
                base_url=LLM_BASE_URL,
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            )

        attempt = 0
        try:
            while attempt < max_attempts:
                try:
                    body = {
                        "model": LLM_MODEL_NAME,
                        "messages": [
                            {"role": "system", "content": SECURITY_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                    }

                    rsp = await sess.post("chat/completions", json=body)
                    rsp.raise_for_status()
                    data = await rsp.json()

                    content = data["choices"][0]["message"]["content"]
                    parsed = parse_to_json(content)

                    return (
                        MaliciousState.MALICIOUS
                        if parsed["malicious"]
                        else MaliciousState.NOT_MALICIOUS
                    )

                except (ClientError, asyncio.TimeoutError, ValidationError, JSONDecodeError):
                    pass
                finally:
                    attempt += 1

            return MaliciousState.UNKNOWN

        finally:
            if is_local:
                await sess.close()
