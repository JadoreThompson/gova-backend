from datetime import timedelta
from logging import Logger

import discord

from engine.base_action import BaseAction
from engine.base_action_handler import BaseActionHandler
from engine.discord.actions import BanAction, DiscordActionType, KickAction, MuteAction
from engine.discord.context import DiscordMessageContext
from engine.exc import UnkownActionExc


class DiscordActionHandler(BaseActionHandler):
    def __init__(self, client: discord.Client, logger: Logger) -> None:
        super().__init__()
        self._client = client
        self.logger = logger
        self._handlers = {
            DiscordActionType.BAN: self._handle_ban,
            DiscordActionType.MUTE: self._handle_mute,
            DiscordActionType.KICK: self._handle_kick,
        }

    async def handle(self, action: BaseAction, ctx: DiscordMessageContext) -> bool:
        func = self._handlers.get(action.type)
        if func:
            return await func(action, ctx)

        self.logger.warning(f"Unknown aciton type '{action.type.value}'")
        raise UnkownActionExc()

    async def _handle_ban(self, action: BanAction, ctx: DiscordMessageContext) -> bool:
        """
        Ban a user from a Discord guild.
        """
        try:
            guild = await self._fetch_guild(ctx.discord.guild_id)
            member = await self._fetch_member(action.user_id, guild)

            await guild.ban(member, reason=action.reason)
            self.logger.info(
                f"Banned user {member} from guild '{guild.name}'. Reason: {action.reason}"
            )
            return True

        except discord.Forbidden:
            self.logger.error(
                f"Insufficient permissions to ban user {action.user_id}. Guild: {guild.name}"
            )
        except discord.HTTPException as e:
            self.logger.error(f"Ban failed due to HTTP exception: {e}")
        except Exception as e:
            self.logger.exception(
                f"Unexpected error while banning user {action.user_id}: {e}"
            )
        return False

    async def _handle_mute(
        self, action: MuteAction, ctx: DiscordMessageContext
    ) -> bool:
        """
        Temporarily mute a user in a Discord guild using Discord's timeout feature.
        """
        try:
            guild = await self._fetch_guild(ctx.discord.guild_id)
            member = await self._fetch_member(action.user_id, guild)

            duration_seconds = action.duration / 1000
            timeout_until = timedelta(seconds=duration_seconds)

            await member.timeout(timeout_until, reason=action.reason)
            self.logger.info(
                f"Muted user {member} for {duration_seconds:.1f} seconds. Reason: {action.reason}"
            )
            return True

        except discord.Forbidden:
            self.logger.error("Insufficient permissions to mute this user.")
        except discord.HTTPException as e:
            self.logger.error(f"Muting failed due to HTTP exception: {e}")
        except Exception as e:
            self.logger.exception(f"Unexpected error muting user {action.user_id}: {e}")
        return False
    
    async def _handle_kick(self, action: KickAction, ctx: DiscordMessageContext) -> bool:
        try:
            guild = await self._fetch_guild(ctx.discord.guild_id)
            member = await self._fetch_member(action.user_id, guild)
            await member.kick(reason=action.reason)
            return True
        
        except discord.Forbidden:
            self.logger.error("Insufficient permissions to kick this user.")
        except discord.HTTPException as e:
            self.logger.error(f"Muting failed due to HTTP exception: {e}")
        except Exception as e:
            self.logger.exception(f"Unexpected error kicking user {action.user_id}: {e}")
        return False
    

    async def _fetch_guild(self, guild_id: int) -> discord.Guild | None:
        guild = self._client.get_guild(guild_id)
        if guild:
            return guild

        try:
            return await self._client.fetch_guild(guild_id)
        except discord.NotFound:
            self.logger.error(f"Failed to find sever {guild_id}.")

    async def _fetch_member(
        self, user_id: int, guild: discord.Guild
    ) -> discord.Member | None:
        member = guild.get_member(user_id)
        if member:
            return member

        try:
            return await guild.fetch_member(user_id)
        except discord.NotFound:
            self.logger.error(
                f"Failed to find user {user_id}. User not found on Discord."
            )
