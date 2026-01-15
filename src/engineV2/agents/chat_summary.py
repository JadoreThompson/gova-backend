from pydantic import BaseModel

from engineV2.contexts.discord import DiscordMessageContext
from .base import BaseAgent


class ChatSummaryAgentOutput(BaseModel):
    summary: str


class ChatSummaryAgent(BaseAgent):
    _SYSTEM_PROMPT = """
    You're going to be presented with the last n messages sent within
    a discord server and metadata for each. Your task is to summarise the batch
    of messages.

    If you notice that there's multiple conversations occuring simultaneously
    within the batch then you're to break it down into several paragraphs for
    each sub conversation.
    """

    _USER_PROMPT_TMPL = """
    Below is a summary of the discord server you're currently moderating.
    This'll help you understand type of conversations expected within the chat.
    
    <ServerSummary>
    {server_summary}
    </ServerSummary>
    
    Here's the current summary of the chat:
    <ChatSummary>
    {chat_summary}
    </ChatSummary>

    Here are the last {n} messages sent within the chat with their metadata.

    <Messages>
    {messages}
    </Messages>

    """

    def __init__(self):
        super().__init__(output_type=ChatSummaryAgentOutput)

    def build_user_prompt(
        self,
        server_summary: str,
        messages: list[DiscordMessageContext],
        chat_summary: str | None = None,
    ):
        cls = self.__class__
        return cls._USER_PROMPT_TMPL.format(
            server_summary=server_summary,
            chat_summary=chat_summary,
            n=len(messages),
            messages=messages,
        )
