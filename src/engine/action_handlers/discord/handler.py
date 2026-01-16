import logging
from datetime import timedelta

import discord

from engine.contexts.discord import DiscordMessageContext
from engine.params.discord import (
    DiscordPerformedActionParamsKick,
    DiscordPerformedActionParamsReply,
    DiscordPerformedActionParamsTimeout,
)
from .exceptions import DiscordActionHandlerError


class DiscordActionHandler:
    """Handles moderation actions (ban, mute, kick) for Discord."""

    def __init__(self, client: discord.Client) -> None:
        self._client: discord.Client = client
        self._logger = logging.getLogger(type(self).__name__)

    async def handle_reply(
        self, params: DiscordPerformedActionParamsReply, ctx: DiscordMessageContext
    ) -> None:
        channel = self._client.get_channel(ctx.channel_id)
        if channel is None:
            raise DiscordActionHandlerError(
                f"Channel id={ctx.channel_id}, name={ctx.channel_name} not found"
            )

        await channel.send(params.content)

    async def handle_timeout(
        self,
        params: DiscordPerformedActionParamsTimeout,
        ctx: DiscordMessageContext,
    ) -> None:
        """Temporarily mute a user in a Discord guild."""
        try:
            guild = await self._fetch_guild(ctx.guild_id)
            member = await self._fetch_member(params.user_id, guild)

            duration_seconds = params.duration / 1000
            timeout_until = timedelta(seconds=duration_seconds)

            await member.timeout(timeout_until, reason=params.reason)

        except discord.Forbidden:
            raise DiscordActionHandlerError(
                "Insufficient permissions to mute this user."
            )
        except Exception:
            self._logger.error(
                f"An error occured whilst timeouting user id={ctx.user_id}, params={params}",
                exc_info=True,
            )
            raise DiscordActionHandlerError(
                f"Unexpected error occured muting user id={ctx.user_id}"
            )

    async def handle_kick(
        self, params: DiscordPerformedActionParamsKick, ctx: DiscordMessageContext
    ) -> None:
        """Kick a user from a Discord guild."""
        try:
            guild = await self._fetch_guild(ctx.guild_id)
            member = await self._fetch_member(params.user_id, guild)
            await member.kick(reason=params.reason)
        except discord.Forbidden:
            raise DiscordActionHandlerError(
                "Insufficient permissions to kick this user."
            )
        except Exception:
            self._logger.error(
                f"An error occured whilst timeouting user id={ctx.user_id}, params={params}",
                exc_info=True,
            )
            raise DiscordActionHandlerError(
                f"Unexpected error occured muting user id={ctx.user_id}"
            )

    async def _fetch_guild(self, guild_id: int) -> discord.Guild | None:
        """Fetch a Discord guild, preferring cached data when possible."""
        if not self._client:
            raise ValueError("Discord client not set. Call `set_client()` first.")

        guild = self._client.get_guild(guild_id)
        if guild:
            return guild

        try:
            return await self._client.fetch_guild(guild_id)
        except discord.NotFound:
            self._logger.error(f"Failed to find server {guild_id}.")

    async def _fetch_member(
        self, user_id: int, guild: discord.Guild
    ) -> discord.Member | None:
        """Fetch a guild member by ID, preferring cached data."""
        member = guild.get_member(user_id)
        if member:
            return member

        try:
            return await guild.fetch_member(user_id)
        except discord.NotFound:
            self._logger.error(
                f"Failed to find user {user_id}. User not found on Discord."
            )
