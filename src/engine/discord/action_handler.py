import logging
from datetime import timedelta
from typing import Callable

import discord

from engine.base.base_action import BaseAction
from engine.base.base_action_handler import BaseActionHandler
from engine.discord.actions import BanAction, DiscordAction, KickAction, MuteAction
from engine.discord.context import DiscordMessageContext
from engine.exc import UnkownActionExc


logger = logging.getLogger("discord_action_handler")


class DiscordActionHandler(BaseActionHandler):
    """Handles moderation actions (ban, mute, kick) for Discord."""

    _instance: "DiscordActionHandler | None" = None

    def __new__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, client: discord.Client) -> None:
        if hasattr(self, "_initialised") and self._initialised:
            return
        super().__init__()
        self._client: discord.Client = client
        self._handlers: dict[DiscordAction, Callable] = {
            DiscordAction.BAN: self._handle_ban,
            DiscordAction.MUTE: self._handle_mute,
            DiscordAction.KICK: self._handle_kick,
        }
        self._initialised = True

    async def handle(self, action: BaseAction, ctx: DiscordMessageContext) -> bool:
        """Routes an action to the appropriate Discord handler.

        Raises:
            ValueError: If the Discord client is not set.
            UnkownActionExc: If the provided action type is not supported.
        """
        if not self._client:
            raise ValueError("Discord client not set. Call `set_client()` first.")

        func = self._handlers.get(action.type)
        if func:
            return await func(action, ctx)

        msg = f"Unknown action type '{action.type.value}'"
        logger.warning(msg)
        raise UnkownActionExc(msg)

    async def _handle_ban(self, action: BanAction, ctx: DiscordMessageContext) -> bool:
        """Ban a user from a Discord guild."""
        try:
            guild = await self._fetch_guild(ctx.metadata.guild_id)
            member = await self._fetch_member(action.user_id, guild)

            await guild.ban(member, reason=action.reason)
            logger.info(
                f"Banned user {member} from guild '{guild.name}'. Reason: {action.reason}"
            )
            return True

        except discord.Forbidden:
            logger.error(
                f"Insufficient permissions to ban user {action.user_id}. Guild: {guild.name}"
            )
        except discord.HTTPException as e:
            logger.error(f"Ban failed due to HTTP exception: {e}")
        except Exception as e:
            logger.exception(
                f"Unexpected error while banning user {action.user_id}: {e}"
            )
        return False

    async def _handle_mute(
        self, action: MuteAction, ctx: DiscordMessageContext
    ) -> bool:
        """Temporarily mute a user in a Discord guild."""
        try:
            guild = await self._fetch_guild(ctx.metadata.guild_id)
            member = await self._fetch_member(action.user_id, guild)

            duration_seconds = action.duration / 1000
            timeout_until = timedelta(seconds=duration_seconds)

            await member.timeout(timeout_until, reason=action.reason)
            logger.info(
                f"Muted user {member} for {duration_seconds:.1f} seconds. "
                f"Reason: {action.reason}"
            )
            return True

        except discord.Forbidden:
            logger.error("Insufficient permissions to mute this user.")
        except discord.HTTPException as e:
            logger.error(f"Muting failed due to HTTP exception: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error muting user {action.user_id}: {e}")
        return False

    async def _handle_kick(
        self, action: KickAction, ctx: DiscordMessageContext
    ) -> bool:
        """Kick a user from a Discord guild."""
        try:
            guild = await self._fetch_guild(ctx.metadata.guild_id)
            member = await self._fetch_member(action.user_id, guild)
            await member.kick(reason=action.reason)
            logger.info(f"Kicked user {member} from guild '{guild.name}'.")
            return True

        except discord.Forbidden:
            logger.error("Insufficient permissions to kick this user.")
        except discord.HTTPException as e:
            logger.error(f"Kicking failed due to HTTP exception: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error kicking user {action.user_id}: {e}")
        return False

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
            logger.error(f"Failed to find server {guild_id}.")

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
            logger.error(f"Failed to find user {user_id}. User not found on Discord.")
