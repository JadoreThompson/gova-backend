from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider

from config import LLM_API_KEY, LLM_MODEL_NAME


AGENT_LLM_PROVIDER = MistralProvider(api_key=LLM_API_KEY)
AGENT_MODEL = MistralModel(LLM_MODEL_NAME, provider=AGENT_LLM_PROVIDER)
