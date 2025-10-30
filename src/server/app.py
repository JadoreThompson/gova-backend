import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import DOMAIN, SCHEME, SUB_DOMAIN
from infra import KafkaManager, DiscordClientManager
from server.exc import CustomValidationError, JWTError
from server.routes.actions.route import router as action_router
from server.routes.auth.route import router as auth_router
from server.routes.connections.route import router as connections_router
from server.routes.deployments.route import router as deployments_router
from server.routes.guidelines.route import router as guidelines_router
from server.routes.moderators.route import router as moderators_router
from server.routes.payments.route import router as payments_router
from server.routes.public.route import router as public_router
from server.services import DiscordService
from server.services.encryption_service import EncryptionError


async def lifespan(app: FastAPI):
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
    allow_origins=[
        f"{SCHEME}://{DOMAIN}",
        f"{SCHEME}://{SUB_DOMAIN}{DOMAIN}",
    ],
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
app.include_router(payments_router)
app.include_router(public_router)


@app.exception_handler(CustomValidationError)
async def handle_http_exception(req: Request, exc: CustomValidationError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.msg})


@app.exception_handler(HTTPException)
async def handle_http_exception(req: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(JWTError)
async def handle_jwt_error(req: Request, exc: JWTError):
    return JSONResponse(status_code=401, content={"error": str(exc)})


@app.exception_handler(EncryptionError)
async def handle_encryption_error(req: Request, exc: EncryptionError):
    return JSONResponse(status_code=500, content={"error": str(exc)})
