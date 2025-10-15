import json
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import insert, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db_models import Users
from server.dependencies import depends_db_sess
from server.services import JWTService
from .controllers import fetch_discord_access_token
from .models import UserCreate, UserLogin


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
async def register(body: UserCreate, db_sess: AsyncSession = Depends(depends_db_sess)):
    res = await db_sess.execute(select(Users).where(Users.username == body.username))
    if res.first():
        return JSONResponse(
            status_code=401, content={"error": "User with username already exists."}
        )

    result = await db_sess.execute(
        insert(Users).values(**body.model_dump()).returning(Users)
    )
    new_user = result.scalar_one()
    await db_sess.commit()

    return JWTService.set_cookie(new_user)


@router.post("/login")
async def login(body: UserLogin, db_sess: AsyncSession = Depends(depends_db_sess)):
    if (body.username is None or not body.username.strip()) and (
        body.email is None or not body.email.strip()
    ):
        return JSONResponse(
            status_code=400,
            content={"error": "Either username or email must be provided."},
        )

    res = await db_sess.execute(
        select(Users).where(
            Users.username == body.username, Users.password == body.password
        )
    )
    user = res.scalar_one_or_none()

    if user is None:
        return JSONResponse(status_code=401, content={"error": "Invalid user."})

    return JWTService.set_cookie(user)


@router.get("/discord/oauth")
async def discord_callback(code: str):
    data = await fetch_discord_access_token(code)
    with open("discord-token.json", "w") as f: # TODO: Remove
        json.dump(data, f)
