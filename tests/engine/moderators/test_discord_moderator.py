from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from engine.actions.discord import (
    DiscordActionKick,
    DiscordActionReply,
    DiscordActionTimeout,
    DiscordActionType,
)
from engine.actions.registry import PerformedActionRegistry
from engine.agents.conversation_thread import (
    AddToConversationCommand,
    ConversationThreadAgent,
    ConversationThreadGroup,
    NewConversationCommand,
)
from engine.agents.review import ReviewAgentV2, ReviewAgentOutput
from engine.configs.discord import DiscordModeratorConfig
from engine.contexts.discord import DiscordMessageContext
from engine.conversation.discord.conversation import DiscordConversation
from engine.moderators.discord import DiscordModerator

GUILD_ID = 999_001
CHANNEL_CHAMPIONSHIP = 100
CHANNEL_RACE = 101
CHANNEL_CAR = 102

GUILD_SUMMARY = (
    "This is an enthusiast Discord server dedicated entirely to Formula 1. "
    "Members discuss championship battles, race weekends, technical regulations, "
    "driver transfers, team strategies, and the broader motorsport ecosystem. "
    "The community is passionate and knowledgeable; the goal is high-quality, "
    "on-topic conversation that respects every participant."
)

GUIDELINES = (
    "1. No swearing or profanity of any kind.\n"
    "2. No NSFW content.\n"
    "3. Conversations must remain strictly on-topic — Formula 1 and motorsport only.\n"
    "4. Be respectful to all community members at all times; personal attacks are "
    "strictly forbidden.\n"
    "5. English only — no other languages.\n"
    "6. Do not spam or flood the channel with low-effort messages."
)


def _msg(
    content: str,
    user_id: int,
    channel_id: int,
    username: str | None = None,
    roles: list[str] | None = None,
) -> DiscordMessageContext:
    return DiscordMessageContext(
        guild_id=GUILD_ID,
        channel_id=channel_id,
        channel_name={
            CHANNEL_CHAMPIONSHIP: "championship-talk",
            CHANNEL_RACE: "race-weekend",
            CHANNEL_CAR: "car-tech",
        }.get(channel_id, "general"),
        user_id=user_id,
        username=username or f"user_{user_id}",
        content=content,
        roles=roles or ["member"],
    )

def _championship_messages() -> list[DiscordMessageContext]:
    """~25 messages about the 2025 WDC / WCC battle."""
    return [
        _msg(
            "Verstappen's points lead is starting to look comfortable again.",
            201,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Yeah but Norris has closed the gap twice already — it's not over.",
            202,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Hamilton at Ferrari feels like such a wildcard for the constructors.",
            203,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "I think Ferrari will crack under pressure again in the second half.",
            204,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "McLaren's consistency is what impresses me. No massive DNFs so far.",
            202,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Red Bull's upgrade path has been slower than last year though.",
            205,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "True, RB20 carried a lot of the early-season momentum.",
            201,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "If Verstappen takes another hat-trick of wins it's realistically over.",
            206,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Norris needs at least two wins before the summer break imo.",
            203,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Russell quietly sitting third in the standings, people keep forgetting him.",
            207,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "George is very consistent. Not flashy but accumulates points.",
            202,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Sainz at Williams has been a breath of fresh air for them.",
            208,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Williams might score top-five constructors this year, which is wild.",
            205,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Aston Martin is worrying — they looked so strong last year.",
            201,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Their correlation issues haven't gone away sadly.",
            204,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Alpine seem to have found something this year, at least in qualifying.",
            206,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Gasly's racecraft keeps them scoring when the car gives him a chance.",
            207,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "The Haas midfield fight is fun to watch. Hülkenberg really maximises it.",
            203,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "I'm actually rooting for Tsunoda to outpoint Lawson this half.",
            208,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "VCARB dynamic is interesting — neither driver willing to yield.",
            202,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Championship is Verstappen's to lose, but Norris is his only real threat.",
            205,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Agreed. Ferrari too inconsistent to mount a sustained title challenge.",
            206,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "If McLaren win both championships it resets their legacy completely.",
            201,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Would be one of the best sporting stories in a decade.",
            207,
            CHANNEL_CHAMPIONSHIP,
        ),
        _msg(
            "Let's see after Silverstone — that usually reshuffles everything.",
            204,
            CHANNEL_CHAMPIONSHIP,
        ),
    ]


def _race_messages() -> list[DiscordMessageContext]:
    """~25 messages recapping a recent race weekend."""
    return [
        _msg(
            "What a race in Monaco this weekend — drama from lap one.",
            301,
            CHANNEL_RACE,
        ),
        _msg(
            "The safety car timing was absolutely brutal for Leclerc.",
            302,
            CHANNEL_RACE,
        ),
        _msg(
            "He was on course for a comfortable win until the VSC appeared.",
            303,
            CHANNEL_RACE,
        ),
        _msg(
            "Verstappen's team call to pit under VSC was genius from the pit wall.",
            301,
            CHANNEL_RACE,
        ),
        _msg(
            "Can't argue with the result but it felt lucky rather than dominant.",
            304,
            CHANNEL_RACE,
        ),
        _msg(
            "Racing is racing. You take the calls when they present themselves.",
            302,
            CHANNEL_RACE,
        ),
        _msg(
            "Norris got stuck behind traffic — cost him at least six seconds.",
            305,
            CHANNEL_RACE,
        ),
        _msg(
            "Monaco is still the worst track for overtaking, nothing changes.",
            303,
            CHANNEL_RACE,
        ),
        _msg(
            "Yet it's the most iconic round on the calendar. The tension is unreal.",
            306,
            CHANNEL_RACE,
        ),
        _msg(
            "Hamilton's first lap for Ferrari was genuinely exciting to watch.",
            301,
            CHANNEL_RACE,
        ),
        _msg(
            "He looked comfortable in the car — much better than Bahrain.",
            302,
            CHANNEL_RACE,
        ),
        _msg(
            "P4 is a solid debut result round the streets. Shows promise.",
            304,
            CHANNEL_RACE,
        ),
        _msg(
            "Russell's tyre management in the final stint was exceptional.",
            305,
            CHANNEL_RACE,
        ),
        _msg(
            "He extended those mediums almost ten laps past where I expected.",
            303,
            CHANNEL_RACE,
        ),
        _msg(
            "Piastri got a penalty — did anyone think it was justified?",
            306,
            CHANNEL_RACE,
        ),
        _msg(
            "Tight call. I'd argue he left a car's width, but the stewards disagreed.",
            301,
            CHANNEL_RACE,
        ),
        _msg(
            "Stewards are inconsistent. Same move last year was let go.",
            302,
            CHANNEL_RACE,
        ),
        _msg(
            "The podium presentation felt a bit flat without the usual fanfare.",
            307,
            CHANNEL_RACE,
        ),
        _msg(
            "Monaco podium ceremony is iconic though. Royalty, yachts, the whole thing.",
            304,
            CHANNEL_RACE,
        ),
        _msg(
            "I was there trackside — the atmosphere in the tunnel section is insane.",
            305,
            CHANNEL_RACE,
        ),
        _msg(
            "Lucky you! Did you catch the start from the Sainte-Dévote grandstand?",
            306,
            CHANNEL_RACE,
        ),
        _msg(
            "Yes! The roar when Hamilton came through P3 on lap one was massive.",
            305,
            CHANNEL_RACE,
        ),
        _msg(
            "Fastest lap went to Sainz which helped Williams a point in constructors.",
            307,
            CHANNEL_RACE,
        ),
        _msg("Every point matters at this stage of the season.", 303, CHANNEL_RACE),
        _msg(
            "Roll on Canada — genuinely can't wait for a proper overtaking circuit.",
            301,
            CHANNEL_RACE,
        ),
    ]


def _car_messages() -> list[DiscordMessageContext]:
    """~22 messages on technical / car topics."""
    return [
        _msg(
            "The Red Bull floor update looked significant in the Friday aero rakes.",
            401,
            CHANNEL_CAR,
        ),
        _msg(
            "Their tunnel entry geometry has been redesigned from the looks of it.",
            402,
            CHANNEL_CAR,
        ),
        _msg(
            "McLaren's double-diffuser interpretation is raising eyebrows in the paddock.",
            403,
            CHANNEL_CAR,
        ),
        _msg(
            "Technically it's within regs but expect a protest before long.",
            401,
            CHANNEL_CAR,
        ),
        _msg(
            "Ferrari's power unit step is real — the straight-line numbers back it up.",
            404,
            CHANNEL_CAR,
        ),
        _msg(
            "Finally catching Mercedes and Honda on raw ICE power it seems.",
            402,
            CHANNEL_CAR,
        ),
        _msg(
            "Honda's deployment strategy in low-speed corners is something else.",
            405,
            CHANNEL_CAR,
        ),
        _msg(
            "The way they blend ERS out of hairpins is seamless compared to others.",
            403,
            CHANNEL_CAR,
        ),
        _msg(
            "Mercedes' suspension concept is unique — pullrod front paired with pushrod rear.",
            401,
            CHANNEL_CAR,
        ),
        _msg(
            "Unconventional, but it lets them run a lower ride height in fast corners.",
            404,
            CHANNEL_CAR,
        ),
        _msg(
            "Williams' car finally has proper downforce levels — Capito's investment paying off.",
            406,
            CHANNEL_CAR,
        ),
        _msg(
            "Their wind tunnel correlation was broken for years, glad they fixed it.",
            402,
            CHANNEL_CAR,
        ),
        _msg(
            "Aston Martin's sidepod concept seems outdated now compared to the field.",
            405,
            CHANNEL_CAR,
        ),
        _msg(
            "They haven't really evolved the philosophy since their 2023 peak.",
            401,
            CHANNEL_CAR,
        ),
        _msg(
            "Alpine's updated floor seems to give them more stable aero balance.",
            403,
            CHANNEL_CAR,
        ),
        _msg(
            "That explained the jump in race pace even if qualifying still struggles.",
            404,
            CHANNEL_CAR,
        ),
        _msg(
            "Anyone noticed how Haas have pivoted to a Ferrari-clone philosophy again?",
            406,
            CHANNEL_CAR,
        ),
        _msg(
            "Makes sense — access to Ferrari wind tunnel data under the technical agreement.",
            402,
            CHANNEL_CAR,
        ),
        _msg(
            "RB (formerly AlphaTauri) look more independent this year which is interesting.",
            405,
            CHANNEL_CAR,
        ),
        _msg(
            "The 2026 regs will reset everything anyway — teams banking aero resource now.",
            401,
            CHANNEL_CAR,
        ),
        _msg(
            "Active aero returning is going to change racing so much — can't wait.",
            403,
            CHANNEL_CAR,
        ),
        _msg(
            "Ground effect plus movable elements will make 2026 cars genuinely alien.",
            404,
            CHANNEL_CAR,
        ),
    ]


def _violating_message() -> DiscordMessageContext:
    """
    A message that personally attacks another user with profanity instead of
    merely criticising a team — violates the no-swearing and be-respectful rules.
    """
    return _msg(
        content=(
            "Oh shut up you absolute moron, nobody cares what you think about Ferrari. "
            "You clearly don't understand F1 at all, you stupid fucking idiot. "
            "Go back to watching football, you're too damn dumb for this server."
        ),
        user_id=501,
        channel_id=CHANNEL_CHAMPIONSHIP,
        username="angry_fan_501",
    )


def _make_config() -> DiscordModeratorConfig:
    return DiscordModeratorConfig(
        guild_id=GUILD_ID,
        channel_ids=[CHANNEL_CHAMPIONSHIP, CHANNEL_RACE, CHANNEL_CAR],
        guild_summary=GUILD_SUMMARY,
        guidelines=GUIDELINES,
        actions=[
            DiscordActionReply(requires_approval=False),
            DiscordActionTimeout(default_params=None, requires_approval=False),
            DiscordActionKick(requires_approval=True),
        ],
    )


def _make_moderator(
    config: DiscordModeratorConfig,
) -> tuple[DiscordModerator, MagicMock, MagicMock]:
    """
    Builds a DiscordModerator with mocked infrastructure.

    Returns:
        (moderator, mock_action_handler, mock_kafka_producer)
    """
    mock_action_handler = MagicMock()
    mock_action_handler.handle_reply = AsyncMock()
    mock_action_handler.handle_timeout = AsyncMock()
    mock_action_handler.handle_kick = AsyncMock()

    mock_kafka = AsyncMock()
    mock_kafka.send = AsyncMock()

    moderator = DiscordModerator(
        moderator_id=uuid.uuid4(),
        config=config,
        client_id=888_000,  # bot user-id
        action_handler=mock_action_handler,
        kafka_producer=mock_kafka,
    )

    return moderator, mock_action_handler, mock_kafka

@pytest.mark.asyncio
async def test_moderator_detects_and_acts_on_rule_violating_message(monkeypatch):
    """
    Feed ~75 benign F1 messages across three channels to establish context,
    then process one message that personally attacks another user with swearing.

    Assertions
    ----------
    - severity_score emitted in the EvaluationCreatedModeratorEvent is > 0.5
    - The moderator calls at least one action handler (reply / timeout / kick)
    """
    PerformedActionRegistry.register_discord()

    # Seeding
    conversation_thread_agent = ConversationThreadAgent()
    mock_conversation_thread_agent = AsyncMock(wraps=conversation_thread_agent)
    mock_conversation_thread_agent.build_user_prompt = Mock(
        side_effect=conversation_thread_agent.build_user_prompt
    )
    mock_conversation_thread_agent_cls = Mock()
    mock_conversation_thread_agent_cls.return_value = mock_conversation_thread_agent
    monkeypatch.setattr(
        "engine.moderators.discord.moderator.ConversationThreadAgent",
        mock_conversation_thread_agent_cls,
    )

    review_agent = ReviewAgentV2()
    mock_review_agent = AsyncMock(wraps=review_agent)
    mock_review_agent.build_user_prompt = Mock(
        side_effect=review_agent.build_user_prompt
    )
    mock_review_agent_cls = Mock()
    mock_review_agent_cls.return_value = mock_review_agent
    monkeypatch.setattr(
        "engine.moderators.discord.moderator.ReviewAgentV2", mock_review_agent_cls
    )

    config = _make_config()
    moderator, mock_action_handler, mock_kafka = _make_moderator(config)

    msgs = _championship_messages()
    conversation = DiscordConversation(
        topic="Championship discussion", channel_id=msgs[0].channel_id
    )
    mock_discord_conversation_cls = Mock()
    mock_discord_conversation_cls.return_value = conversation
    monkeypatch.setattr(
        "engine.conversation.discord.manager.DiscordConversation",
        mock_discord_conversation_cls,
    )

    mock_run_result = Mock()
    mock_run_result.output = [
        ReviewAgentOutput(action=None, severity_score=0.0, reason="")
    ]
    mock_review_agent.run.return_value = mock_run_result
    for i, msg in enumerate(msgs):
        if i == 0:
            mock_run_result = Mock()
            mock_run_result.output = [
                ConversationThreadGroup(
                    indices=[0],
                    command=NewConversationCommand(topic=conversation.topic),
                )
            ]
            mock_conversation_thread_agent.run.return_value = mock_run_result
        else:
            mock_run_result = Mock()
            mock_run_result.output = [
                ConversationThreadGroup(
                    indices=[0],
                    command=AddToConversationCommand(
                        conversation_id=conversation.conversation_id
                    ),
                )
            ]
            mock_conversation_thread_agent.run.return_value = mock_run_result

        await moderator.process_message(msg)

    assert (
        moderator._channel_conversations[msgs[0].channel_id].get_conversation(
            conversation.conversation_id
        )
        is conversation
    )

    msgs = _race_messages()
    conversation = DiscordConversation(
        topic="Race discussion", channel_id=msgs[0].channel_id
    )
    mock_discord_conversation_cls.return_value = conversation
    for i, msg in enumerate(msgs):
        if i == 0:
            mock_run_result = Mock()
            mock_run_result.output = [
                ConversationThreadGroup(
                    indices=[0],
                    command=NewConversationCommand(topic=conversation.topic),
                )
            ]
            mock_conversation_thread_agent.run.return_value = mock_run_result
        else:
            mock_run_result = Mock()
            mock_run_result.output = [
                ConversationThreadGroup(
                    indices=[0],
                    command=AddToConversationCommand(
                        conversation_id=conversation.conversation_id
                    ),
                )
            ]
            mock_conversation_thread_agent.run.return_value = mock_run_result

        await moderator.process_message(msg)

    assert (
        moderator._channel_conversations[msgs[0].channel_id].get_conversation(
            conversation.conversation_id
        )
        is conversation
    )

    msgs = _car_messages()
    conversation = DiscordConversation(
        topic="Cars discussion", channel_id=msgs[0].channel_id
    )
    mock_discord_conversation_cls.return_value = conversation
    for i, msg in enumerate(msgs):
        if i == 0:
            mock_run_result = Mock()
            mock_run_result.output = [
                ConversationThreadGroup(
                    indices=[0],
                    command=NewConversationCommand(topic=conversation.topic),
                )
            ]
            mock_conversation_thread_agent.run.return_value = mock_run_result
        else:
            mock_run_result = Mock()
            mock_run_result.output = [
                ConversationThreadGroup(
                    indices=[0],
                    command=AddToConversationCommand(
                        conversation_id=conversation.conversation_id
                    ),
                )
            ]
            mock_conversation_thread_agent.run.return_value = mock_run_result

        await moderator.process_message(msg)

    assert (
        moderator._channel_conversations[msgs[0].channel_id].get_conversation(
            conversation.conversation_id
        )
        is conversation
    )

    # Reset call counts so only the violating-message interactions are measured
    mock_action_handler.handle_reply.reset_mock()
    mock_action_handler.handle_timeout.reset_mock()
    mock_action_handler.handle_kick.reset_mock()
    mock_kafka.send.reset_mock()

    # Process the rule-violating message
    mock_conversation_thread_agent.run.reset_mock(return_value=True)
    mock_review_agent.run.reset_mock(return_value=True)
    bad_msg = _violating_message()
    await moderator.process_message(bad_msg)

    assert mock_kafka.send.called, (
        "Expected at least one Kafka event to be emitted for the violating message."
    )

    emitted_payloads: list[str] = [
        call.args[1].decode() for call in mock_kafka.send.call_args_list
    ]

    import json

    # Find the EvaluationCreatedModeratorEvent payload (contains severity_score)
    evaluation_payload = None
    for raw in emitted_payloads:
        parsed = json.loads(raw)
        if "severity_score" in parsed:
            evaluation_payload = parsed
            break

    assert evaluation_payload is not None, (
        "No EvaluationCreatedModeratorEvent found in Kafka emissions. "
        f"Emitted payloads: {emitted_payloads}"
    )

    severity_score = evaluation_payload["severity_score"]
    assert severity_score > 0.5, (
        f"Expected severity_score > 0.5 for a personal attack with profanity, "
        f"got {severity_score}."
    )

    # Actions that require_approval (kick) will NOT trigger the handler directly
    # but will still emit an ActionPerformedModeratorEvent.  Check both paths.
    action_event_emitted = any(
        "action" in json.loads(payload)
        and json.loads(payload).get("action") is not None
        for payload in emitted_payloads
    )

    action_was_attempted = (
        mock_action_handler.handle_reply.called
        or mock_action_handler.handle_timeout.called
        or mock_action_handler.handle_kick.called
    )

    assert action_was_attempted or action_event_emitted, (
        "Moderator did not attempt any moderation action for the violating message. "
        "Expected handle_reply, handle_timeout, or handle_kick to be called, "
        "or an ActionPerformedModeratorEvent to be emitted."
    )
