import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import MessagePlatformType
from db_models import Users
from server.dependencies import depends_db_sess, depends_jwt
from server.services import DiscordService, JWTService
from server.typing import JWTPayload
from .models import (
    PlatformConnection,
    UpdatePassword,
    UpdateUsername,
    UserCreate,
    UserLogin,
    UserMe,
)


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
async def register(body: UserCreate, db_sess: AsyncSession = Depends(depends_db_sess)):
    res = await db_sess.execute(select(Users).where((Users.username == body.username) | (Users.email == body.email)))
    if res.first():
        return JSONResponse(
            status_code=401, content={"error": "User with username already exists."}
        )

    result = await db_sess.execute(
        insert(Users).values(**body.model_dump()).returning(Users)
    )
    new_user = result.scalar_one()

    rsp = JWTService.set_cookie(new_user)
    await db_sess.commit()
    return rsp


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


@router.post("/logout")
async def logout(jwt: JWTPayload = Depends(depends_jwt)):
    return JWTService.remove_cookie()


@router.get("/me", response_model=UserMe)
async def get_me(
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    async def wrapper(platform: MessagePlatformType, coro):
        identity = await coro
        return platform, identity

    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    funcs = {MessagePlatformType.DISCORD: DiscordService.fetch_identity}
    coros = []

    for plat, data in (user.connections or {}).items():
        func = funcs.get(plat)
        if func:
            coros.append(wrapper(plat, func(data)))

    plat_conns = {}
    if coros:
        res = await asyncio.gather(*coros)
        for plat, identity in res:
            plat_conns[plat] = PlatformConnection(
                username=identity.username, avatar=identity.avatar
            )

    return UserMe(username=user.username, connections=plat_conns)


@router.get("/discord/oauth")
async def discord_callback(
    code: str,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    data = await DiscordService.fetch_discord_access_token(code)

    conns = await db_sess.scalar(
        select(Users.connections).where(Users.user_id == jwt.sub)
    )
    if not conns:
        conns = {}

    conns[MessagePlatformType.DISCORD] = data
    await db_sess.execute(
        update(Users).values(connections=conns).where(Users.user_id == jwt.sub)
    )
    await db_sess.commit()

    return RedirectResponse(url="http://localhost:5173/connections")


@router.patch("/change-username")
async def change_username(
    body: UpdateUsername,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    # TODO: Auth and validation
    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db_sess.execute(
        update(Users)
        .where(Users.user_id == user.user_id)
        .values(username=body.username)
    )
    await db_sess.commit()


@router.patch("/change-password")
async def change_password(
    body: UpdatePassword,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    # TODO: Auth and validation
    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db_sess.execute(
        update(Users)
        .where(Users.user_id == user.user_id)
        .values(password=body.password)
    )
    await db_sess.commit()
