import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
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
from services.kafka import KafkaProducerManager


async def lifespan(app: FastAPI):
    DiscordService.start()
    await asyncio.gather(KafkaProducerManager.start())

    yield

    result = await asyncio.gather(
        DiscordService.stop(), KafkaProducerManager.stop(), return_exceptions=True
    )
    excs = [r for r in result if isinstance(r, Exception)]
    if excs:
        raise ExceptionGroup("Errors occured whilst stopping lifespan services", excs)


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


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(req: Request, exc: RequestValidationError):
    err = exc.errors()[0]
    err_type = err.get("type", "")
    msg = err.get("msg", "")

    if not err_type or not msg:
        error_msg = "Failed to validate request"
    else:
        msg_lower = msg.lower()
        sub = err_type.replace("_", " ") + ","
        idx = msg_lower.find(sub)
        error_msg = "".join(
            char for i, char in enumerate(msg) if idx + len(sub) <= i or i < idx
        )

    return JSONResponse(status_code=422, content={"error": str(error_msg)})
