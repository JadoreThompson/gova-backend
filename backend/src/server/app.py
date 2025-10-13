from fastapi import FastAPI
from server.routes.auth.route import router as auth_router

app = FastAPI()

app.include_router(auth_router)
