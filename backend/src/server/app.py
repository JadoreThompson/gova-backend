from fastapi import FastAPI
from server.routes.auth.route import router as auth_router
from server.routes.guidelines.route import router as guidelines_router
from server.routes.moderators.route import router as moderators_router


app = FastAPI()

app.include_router(auth_router)
app.include_router(guidelines_router)
app.include_router(moderators_router)
