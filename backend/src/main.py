import asyncio

import uvicorn


def main():
    uvicorn.run("server.app:app", host="localhost", port=8000, reload=True)


async def test():
    from config import DISCORD_BOT_TOKEN
    from engine.discord.actions import BanActionDefinition, MuteActionDefinition
    from engine.discord.config import DiscordConfig
    from engine.discord.moderator import DiscordModerator

    mod = DiscordModerator(
        "61897ee1-c58d-48e8-98a4-51e67dab2cc0",
        "51387d42-f73a-4fbf-b9bf-c633afc3345d",
        DISCORD_BOT_TOKEN,
        DiscordConfig(
            guild_id=1334317047995432980,
            allowed_channels=[1334317050629460114],
            allowed_actions=[MuteActionDefinition(requires_approval=False)],
        ),
    )
    async with mod:
        await mod.moderate()


async def test1():
    from engine.deployment_listener import DeploymentListener

    listener = DeploymentListener()
    listener.listen()


if __name__ == "__main__":
    import sys

    arg = sys.argv[1]

    try:
        if arg == "1":
            asyncio.run(test())
        else:
            main()
    except KeyboardInterrupt:
        sys.exit(1)
