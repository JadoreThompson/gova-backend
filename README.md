Gova is your AI powered moderator for your social community, able to perform high order actions to review your chat, ban, kick, timeout the bad actors.

## Features

- Synthesis: The moderator will synthesis the stream of messages and summarise the current threads of conversation
- Autonomous actions: Your agent will perform high order actions such as replying, timing out or kicking users.
- Human in the loop: Choose to have the actions reviewed by your first will full context available

## Architecture

A distributed event driven architecture comprised of 3 components.

- Unified API Layer
    - Moderator Management: Create, Delete, Start and Stop your moderator
    - Actions Management: Retrieve, Approve and Reject actions
    - Connections: Manage connections to social platforms e.g. Discord
- Moderator Orchestrator
    - Orchestration: Orchestrates instances of moderators grouped by the platform type
    - Event Consumption: Listen for Start, Stop, UpdateConfig events and applies them to the rightful moderator
    - Event Emitting: Emits event to signal ActionPerformed, DeadModerator downstream
- Event Handler
    - Event consumption: Listens to events from the moderator orchestrator and performs DB operations and calculations

## Initialisation

```jsx
git clone https://github.com/JadoreThompson/gova-backend

cd gova-backend

cp .env.example .env

docker compose -f docker/dev-compose.yaml --env-file .env up -d postgres kafka redis

# Run the HTTP API
uv run src/main.py http run

# Run the ModeratorOrchestrator
uv run src/main.py orchestrator run

# Run the EventHandler
uv run src/main.py event_handler run
```