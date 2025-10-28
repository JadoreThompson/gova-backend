import asyncio
import json

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import DOMAIN, PW_HASH_SALT, REDIS_CLIENT, REDIS_EXPIRY, SCHEME, SUB_DOMAIN
from core.enums import MessagePlatformType
from db_models import Users
from server.dependencies import depends_db_sess, depends_jwt
from server.services import DiscordService, EmailService, EncryptionService, JWTService
from server.typing import JWTPayload
from utils.db import get_datetime
from .controller import gen_verification_code
from .models import (
    PlatformConnection,
    UpdatePassword,
    UpdateUsername,
    UserCreate,
    UserLogin,
    UserMe,
    VerifyAction,
    VerifyCode,
)


router = APIRouter(prefix="/auth", tags=["Auth"])
em_service = EmailService("No-Reply", "no-reply@gova.chat")
pw_hasher = PasswordHasher()


@router.post("/register", status_code=202)
async def register(
    body: UserCreate,
    bg_tasks: BackgroundTasks,
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    global em_service, pw_hasher

    res = await db_sess.scalar(
        select(Users).where(
            (Users.username == body.username) | (Users.email == body.email)
        )
    )
    if res is not None:
        raise HTTPException(status_code=400, detail="Username or email already exists.")

    body.password = pw_hasher.hash(body.password, salt=PW_HASH_SALT.encode())

    new_user_id = await db_sess.scalar(
        insert(Users).values(**body.model_dump()).returning(Users.user_id)
    )
    code = gen_verification_code()
    await REDIS_CLIENT.set(code, str(new_user_id), ex=REDIS_EXPIRY)

    bg_tasks.add_task(
        em_service.send_email,
        body.email,
        "Verify your email",
        f"Your verification code is: {code}",
    )
    await db_sess.commit()


@router.post("/login")
async def login(body: UserLogin, db_sess: AsyncSession = Depends(depends_db_sess)):
    if (body.username is None or not body.username.strip()) and (
        body.email is None or not body.email.strip()
    ):
        raise HTTPException(
            status_code=400, detail="Either username or email must be provided."
        )

    query = select(Users)
    if body.username is not None:
        query = query.where(Users.username == body.username)
    else:
        query = query.where(Users.email == body.email)

    user = await db_sess.scalar(query)
    if user is None:
        raise HTTPException(status_code=400, detail="User doesn't exist.")

    try:
        pw_hasher.verify(user.password, body.password)
    except Argon2Error:
        raise HTTPException(status_code=400, detail="Invalid password.")

    return JWTService.set_cookie(user)


@router.post("/request-email-verification")
async def request_email_verification(
    bg_tasks: BackgroundTasks, jwt: JWTPayload = Depends(depends_jwt)
):
    global em_service

    code = gen_verification_code()
    await REDIS_CLIENT.set(code, str(jwt.sub), ex=REDIS_EXPIRY)
    bg_tasks.add_task(
        em_service.send_email,
        jwt.em,
        "Verify your email",
        f"Your verification code is: {code}",
    )


@router.post("/verify-email")
async def verify_email(
    body: VerifyCode, db_sess: AsyncSession = Depends(depends_db_sess)
):
    user_id = await REDIS_CLIENT.get(body.code)
    if not user_id:
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification code."
        )
    await REDIS_CLIENT.delete(body.code)

    user = await db_sess.scalar(
        update(Users)
        .where(Users.user_id == user_id)
        .values(authenticated_at=get_datetime())
        .returning(Users)
    )
    rsp = JWTService.set_cookie(user)
    await db_sess.commit()
    return rsp


@router.post("/logout")
async def logout():
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
            decrypted = EncryptionService.decrypt(data, expected_aad=str(user.user_id))
            coros.append(wrapper(plat, func(decrypted)))

    plat_conns = {}
    if coros:
        res = await asyncio.gather(*coros)
        for plat, identity in res:
            plat_conns[plat] = PlatformConnection(
                username=identity.username, avatar=identity.avatar
            )

    return UserMe(
        username=user.username, connections=plat_conns, pricing_tier=user.pricing_tier
    )


@router.get("/discord/oauth")
async def discord_oauth_callback(
    code: str,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    created_at = get_datetime().timestamp()
    data = await DiscordService.fetch_discord_access_token(code)

    conns = await db_sess.scalar(
        select(Users.connections).where(Users.user_id == jwt.sub)
    )
    if not conns:
        conns = {}
    
    data['created_at'] = created_at
    data['expires_at'] = data['created_at'] + data['expires_in']
    conns[MessagePlatformType.DISCORD] = EncryptionService.encrypt(data, aad=str(jwt.sub))
    await db_sess.execute(
        update(Users).values(connections=conns).where(Users.user_id == jwt.sub)
    )
    await db_sess.commit()

    return RedirectResponse(url=f"{SCHEME}://{SUB_DOMAIN}{DOMAIN}/connections")


@router.post("/change-username", status_code=202)
async def change_username(
    body: UpdateUsername,
    bg_tasks: BackgroundTasks,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    global em_service

    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_user = await db_sess.scalar(
        select(Users).where(Users.username == body.username)
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists.")

    prefix = f"{jwt.sub}:change_username:"
    async for key in REDIS_CLIENT.scan_iter(f"{prefix}*"):
        await REDIS_CLIENT.delete(key)

    verification_code = gen_verification_code()
    payload = json.dumps(
        {
            "user_id": str(user.user_id),
            "action": "change_username",
            "new_value": body.username,
        }
    )
    redis_key = f"{jwt.sub}:change_username:{verification_code}"
    await REDIS_CLIENT.set(
        redis_key,
        payload,
        ex=REDIS_EXPIRY,
    )

    bg_tasks.add_task(
        em_service.send_email,
        user.email,
        "Confirm Your Username Change",
        f"Your verification code is: {verification_code}",
    )

    return {"message": "A verification code has been sent to your email."}


@router.post("/change-password", status_code=202)
async def change_password(
    body: UpdatePassword,
    bg_tasks: BackgroundTasks,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    global em_service

    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prefix = f"{jwt.sub}:change_password:"
    async for key in REDIS_CLIENT.scan_iter(f"{prefix}*"):
        await REDIS_CLIENT.delete(key)

    verification_code = gen_verification_code()

    payload = json.dumps(
        {
            "user_id": str(user.user_id),
            "action": "change_password",
            "new_value": body.password,
        }
    )

    await REDIS_CLIENT.set(
        f"{prefix}{verification_code}",
        payload,
        ex=REDIS_EXPIRY,
    )

    bg_tasks.add_task(
        em_service.send_email,
        user.email,
        "Confirm Your Password Change",
        f"Your verification code is: {verification_code}",
    )

    return {"message": "A verification code has been sent to your email."}


@router.post("/verify-action")
async def verify_action(
    body: VerifyAction,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    global pw_hasher

    redis_key = f"{jwt.sub}:{body.action}:{body.code}"
    data_str = await REDIS_CLIENT.get(redis_key)
    if not data_str:
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification code."
        )
    await REDIS_CLIENT.delete(redis_key)

    data = json.loads(data_str)
    user_id = data["user_id"]
    if user_id != jwt.sub:
        raise HTTPException(status_code=401, detail="Unauthorised request.")

    action = data["action"]
    new_value = data["new_value"]

    if action == "change_username":
        # Final check for username uniqueness to avoid race conditions
        existing_user = await db_sess.scalar(
            select(Users).where(Users.username == new_value)
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken.")

        await db_sess.execute(
            update(Users).where(Users.user_id == user_id).values(username=new_value)
        )
        message = "Username changed successfully."
        await db_sess.commit()

    elif action == "change_password":
        await db_sess.execute(
            update(Users)
            .where(Users.user_id == user_id)
            .values(password=pw_hasher.hash(new_value, salt=PW_HASH_SALT.encode()))
        )
        await db_sess.commit()

        rsp = JSONResponse(
            status_code=200, content={"message": "Password changed successfully."}
        )
        return JWTService.remove_cookie(rsp)

    else:
        raise HTTPException(status_code=400, detail="Unknown action specified.")

    return {"message": message}
