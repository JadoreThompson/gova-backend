import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openapi_pydantic import Components, Info, OpenAPI, Schema

import engine.discord.actions as discord_actions
from config import ACTION_DEFINITIONS_PATH
from core.enums import MessagePlatformType
from infra import KafkaManager, DiscordClientManager
from server.exc import JWTError
from server.routes.actions.route import router as action_router
from server.routes.auth.route import router as auth_router
from server.routes.connections.route import router as connections_router
from server.routes.deployments.route import router as deployments_router
from server.routes.guidelines.route import router as guidelines_router
from server.routes.moderators.route import router as moderators_router
from server.services import DiscordService


def build_definitions():
    mods = ((MessagePlatformType.DISCORD, discord_actions.__dict__),)
    schemas: dict[str, Schema] = {}

    for plat, mod in mods:
        for name, model in mod.items():
            if name.endswith("Definition"):
                model_schema = model.model_json_schema()
                schema_name = model_schema.get("title") or f"{plat.name}_{name}"
                schemas[schema_name] = Schema(**model_schema)

    openapi = OpenAPI(
        openapi="3.1.1",
        info=Info(
            title="Action Definitions API",
            version="0.0.0",
            description="Automatically generated from Pydantic models for action definitions.",
        ),
        paths={},
        components=Components(schemas=schemas),
    )

    with open(ACTION_DEFINITIONS_PATH, "w") as f:
        f.write(openapi.model_dump_json(indent=2, exclude_none=True))

    print(f"OpenAPI schema written to {ACTION_DEFINITIONS_PATH}")


async def lifespan(app: FastAPI):
    build_definitions()
    DiscordService.start()
    await asyncio.gather(
        DiscordClientManager.start(),
        KafkaManager.start(),
    )

    yield

    await asyncio.gather(
        DiscordClientManager.stop(), KafkaManager.stop(), DiscordService.stop()
    )


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(action_router)
app.include_router(auth_router)
app.include_router(connections_router)
app.include_router(deployments_router)
app.include_router(guidelines_router)
app.include_router(moderators_router)


@app.exception_handler(HTTPException)
async def handle_http_exception(req: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(JWTError)
async def handle_jwt_exception(req: Request, exc: JWTError):
    return JSONResponse(status_code=401, content={"error": str(exc)})
