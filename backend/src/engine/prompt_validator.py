import asyncio
import logging
from json import JSONDecodeError

from aiohttp import ClientSession, ClientError
from pydantic import ValidationError

from config import LLM_API_KEY, LLM_BASE_URL, SECURITY_SYSTEM_PROMPT
from engine.enums import MaliciousState
from utils.llm import fetch_response, parse_to_json

logger = logging.getLogger("prompt_validator")


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

        logger.info(f"Handling prompt '{prompt}'")
        attempt = 0
        try:
            while attempt < max_attempts:
                try:
                    data = await fetch_response(
                        [
                            {"role": "system", "content": SECURITY_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ]
                    )
                    content = data["choices"][0]["message"]["content"]
                    logger.info(f"Content: {content}")
                    parsed = parse_to_json(content)

                    return (
                        MaliciousState.MALICIOUS
                        if parsed["malicious"]
                        else MaliciousState.NOT_MALICIOUS
                    )

                except (
                    ClientError,
                    asyncio.TimeoutError,
                    ValidationError,
                    JSONDecodeError,
                    ValueError,
                ) as e:
                    logger.info(
                        f"Attempt {attempt + 1} failed. Error -> {type(e)} - {str(e)}"
                    )
                finally:
                    attempt += 1

            return MaliciousState.UNKNOWN

        finally:
            if is_local:
                await sess.close()
