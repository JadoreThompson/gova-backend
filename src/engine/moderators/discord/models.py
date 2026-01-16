from engine.actions.discord import DiscordActionType
from engine.agents.review import ReviewAgentAction, ReviewAgentOutput


class DiscordReviewAgentOutput(ReviewAgentOutput):
    action: ReviewAgentAction[DiscordActionType] | None = None
