from uuid import UUID

from aiohttp import ClientSession
from sentence_transformers import SentenceTransformer
from sqlalchemy import insert, select

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME
from db_models import Guidelines, MessagesEvaluations, Moderators
from engine.models import MessageContext, MessageEvaluation
from utils.db import get_db_sess
from utils.llm import parse_to_json


class BaseChatModerator:
    _embedding_model: SentenceTransformer | None = None

    def __init__(self, moderator_id: UUID) -> None:
        self._moderator_id = moderator_id
        self._http_sess: ClientSession | None = None
        self._breach_types: list[str] | None = None
        self._guidelines: str | None = None

    def _load_embedding_model(self):
        if self._embedding_model:
            return
        self._embedding_model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

    async def _fetch_llm_response(self, messages: list[dict]):
        body = {"model": LLM_MODEL_NAME, "messages": messages}
        rsp = await self._http_sess.post("chat/completions", json=body)
        rsp.raise_for_status()
        data = await rsp.json()
        content = data["choices"][0]["message"]["content"]
        return parse_to_json(content)

    async def _fetch_guidelines(self) -> tuple[str, list[str]]:
        async with get_db_sess() as db_sess:
            res = await db_sess.execute(
                select(Guidelines.text, Guidelines.breach_types).where(
                    Guidelines.guideline_id
                    == select(Moderators.guideline_id).where(
                        Moderators.moderator_id == self._moderator_id
                    )
                )
            )

            return res.first()

    async def _save_evaluation(
        self, eval: MessageEvaluation, ctx: MessageContext
    ) -> None:
        """
        Stores the eval and generates embeddings for future
        similar retrieval.

        Args:
            eval (MessageEvaluation): Evaluation of the message.
            ctx (MessageContext): Context for the evaluation.
        """
        embedding = self._embedding_model.encode([ctx.content])[0]

        records = [
            {
                "moderator_id": self._moderator_id,
                "platform": ctx.platform.value,
                "content": ctx.content,
                "embedding": embedding,
                "breach_type": breach.breach_type,
                "breach_score": breach.breach_score,
            }
            for breach in eval.breaches
        ]

        if not records:
            return

        async with get_db_sess() as db_sess:
            await db_sess.execute(insert(MessagesEvaluations), records)
            await db_sess.commit()

    async def _fetch_similar(self, text: str) -> tuple[tuple[str, float], ...]:
        embedding = self._embedding_model.encode([text])[0]
        async with get_db_sess() as db_sess:
            res = await db_sess.scalars(
                select(MessagesEvaluations).where(
                    MessagesEvaluations.embedding.l2_distance(embedding) < 0.5,
                    MessagesEvaluations.breach_type.in_(self._breach_types),
                )
            )

            return tuple((r.breach_type, r.breach_score) for r in res.yield_per(1000))

    async def __aenter__(self):
        self._http_sess = ClientSession(
            base_url=LLM_BASE_URL, headers={"Authorization": f"Bearer {LLM_API_KEY}"}
        )
        return self

    async def __aexit__(self, exc_type, exc_value, tcb) -> None:
        await self._http_sess.close()
        self._http_sess = None
