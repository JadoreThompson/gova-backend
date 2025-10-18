from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infra.kafka_manager import KafkaManager
from server.routes.auth.route import router as auth_router
from server.routes.deployments.route import router as deployments_router
from server.routes.guidelines.route import router as guidelines_router
from server.routes.moderators.route import router as moderators_router


async def lifespan(app: FastAPI):
    await KafkaManager.start()
    yield
    await KafkaManager.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth_router)
app.include_router(deployments_router)
app.include_router(guidelines_router)
app.include_router(moderators_router)
