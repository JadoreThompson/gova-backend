import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middlewares import RateLimitMiddleware
from api.routers.actions.router import router as action_router
from api.routers.auth.router import router as auth_router
from api.routers.connections.router import router as connections_router
from api.routers.moderators.router import router as moderators_router
from api.routers.payments.router import router as payments_router
from api.routers.public.router import router as public_router
from config import DOMAIN, SCHEME, SUB_DOMAIN
from services.discord import DiscordService
from services.encryption import EncryptionError
from services.jwt import JWTError
from services.kafka import KafkaManager


async def lifespan(app: FastAPI):
    DiscordService.start()
    await asyncio.gather(KafkaManager.start())

    yield app.state

    await asyncio.gather(DiscordService.stop(), KafkaManager.stop())


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"{SCHEME}://{DOMAIN}",
        f"{SCHEME}://{SUB_DOMAIN}{DOMAIN}",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(RateLimitMiddleware)

app.include_router(action_router)
app.include_router(auth_router)
app.include_router(connections_router)
app.include_router(moderators_router)
app.include_router(payments_router)
app.include_router(public_router)


@app.exception_handler(HTTPException)
async def handle_http_exception(req: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(JWTError)
async def handle_jwt_error(req: Request, exc: JWTError):
    return JSONResponse(status_code=401, content={"error": str(exc)})


@app.exception_handler(EncryptionError)
async def handle_encryption_error(req: Request, exc: EncryptionError):
    return JSONResponse(status_code=500, content={"error": str(exc)})
