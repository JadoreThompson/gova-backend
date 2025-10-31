from engine.discord.actions import DiscordAction
from engine.models import MessageEvaluation


class DiscordMessageEvaluation(MessageEvaluation):
    action: DiscordAction | None
