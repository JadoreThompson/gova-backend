from datetime import timedelta
from logging import Logger

import discord

from engine.base_action import BaseAction
from engine.discord.actions import BanAction, DiscordActionType, MuteAction
from engine.discord.context import DiscordMessageContext
from engine.exc import UnkownActionExc
from engine.base_action_handler import BaseActionHandler


class DiscordActionHandler(BaseActionHandler):
    def __init__(self, client: discord.Client, logger: Logger):
        super().__init__()
        self._client = client
        self.logger = logger
        self._handlers = {
            DiscordActionType.BAN: self._handle_ban,
            DiscordActionType.MUTE: self._handle_mute,
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
            guild = ctx.msg.guild

            member = guild.get_member(action.user_id)
            if member is None:
                try:
                    user = await self._client.fetch_user(action.user_id)
                except discord.NotFound:
                    self.logger.error(
                        f"Failed to ban user {action.user_id}. User not found on Discord."
                    )
                    return False
            else:
                user = member

            await guild.ban(user, reason=action.reason)
            self.logger.info(
                f"Banned user {user} from guild '{guild.name}'. Reason: {action.reason}"
            )
            return True

        except discord.Forbidden:
            self.logger.error(
                f"Insufficient permissions to ban user {action.user_id}. Guild: {ctx.msg.guild.name}"
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
            guild = ctx.msg.guild
            member = guild.get_member(action.user_id)

            if member is None:
                self.logger.error(
                    f"Failed to mute user {action.user_id}. User not found in guild {guild.name}."
                )
                return False

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
