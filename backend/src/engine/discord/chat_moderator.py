import asyncio
import json
from uuid import UUID

from aiohttp import ClientError

from config import FINAL_PROMPT, SCORE_SYSTEM_PROMPT
from engine.base_chat_moderator import BaseChatModerator
from engine.discord.actions import BanAction, DiscordActionType, MuteAction
from engine.enums import MaliciousState
from engine.models import MessageContext, MessageEvaluation
from engine.prompt_validator import PromptValidator
from .chat_stream import DiscordChatStream


class DiscordChatModerator(BaseChatModerator):
    def __init__(self, project_id: UUID, stream: DiscordChatStream) -> None:
        super().__init__(project_id)
        self._stream = stream

    async def moderate_chat(self) -> None:
        async for ctx in self._stream:
            eval = await self._evaluate(ctx)
            print(f"Performed eval: {eval}")
            if not eval:
                continue

    async def _evaluate(
        self, ctx: MessageContext, max_attempts: int = 3
    ) -> MessageEvaluation:
        mstate = await PromptValidator.validate_prompt(ctx.message)
        if mstate == MaliciousState.MALICIOUS:
            print("It's malicious", mstate)
            return

        if not self._guidelines:
            guidelines = self._fetch_guidelines()
            if not guidelines:
                print("No guidelines")
                return
            self._guidelines = guidelines

        if not self._topics:
            topics = await self._fetch_topics(ctx.platform)
            if not topics:
                print("No topics")
                return
            self._topics = topics

        attempt = 0
        while attempt < max_attempts:
            msgs= []
            try:
                # Fetching topic scores
                sys_prompt = SCORE_SYSTEM_PROMPT.format(
                    guidelines=self._guidelines, topics=self._topics
                )
                topic_scores: dict[str, float] = await self._fetch_llm_response(
                    [
                        {"role": "system", "content": sys_prompt},
                        {
                            "role": "user",
                            "content": json.dumps(ctx.to_serialisable_dict()),
                        },
                    ]
                )

                msgs.append(topic_scores)

                # Final Output
                prompt = FINAL_PROMPT.format(
                    guidelines=self._guidelines,
                    topics=self._topics,
                    topic_scores=topic_scores,
                    actions=DiscordActionType._value2member_map_.keys(),
                    message=ctx.message,
                    action_formats=[
                        BanAction.model_json_schema(),
                        MuteAction.model_json_schema(),
                    ],
                    context=ctx.to_serialisable_dict(),
                )
                data = await self._fetch_llm_response(
                    [{"role": "user", "content": prompt}]
                )

                
                eval =  MessageEvaluation(**data)
                msgs.append(data)

                for msg in msgs:
                    print(msg)
                    print("\n")

                return eval
            except (ClientError, asyncio.TimeoutError, json.JSONDecodeError):
                pass
            finally:
                attempt += 1
