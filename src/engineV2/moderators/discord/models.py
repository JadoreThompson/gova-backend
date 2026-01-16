from engineV2.actions.discord import DiscordActionType
from engineV2.agents.review import ReviewAgentAction, ReviewAgentOutput


class DiscordReviewAgentOutput(ReviewAgentOutput):
    action: ReviewAgentAction[DiscordActionType] | None = None
