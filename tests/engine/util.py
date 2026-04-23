from engine.contexts.discord import DiscordMessageContext


def make_discord_message(content: str, user_id: int = 1) -> DiscordMessageContext:
    return DiscordMessageContext(
        guild_id=1,
        channel_id=1,
        channel_name="general",
        user_id=user_id,
        username=f"user-{user_id}",
        content=content,
        roles=["member"],
    )
