from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import depends_db_sess, depends_jwt
from api.types import JWTPayload
from enums import MessagePlatform
from infra.db.models import Users
from services.discord import DiscordService
from services.encryption import EncryptionService
from services.jwt import JWTService
from utils import get_datetime
from .controller import handle_fetch_discord_identity, remove_jwt, set_cookie
from .exceptions import MaxEmailVerificationAttemptsException
from .models import (
    UserCreate,
    UserLogin,
    VerifyCode,
    VerifyAction,
    UpdateUsername,
    UpdatePassword,
    UserMe,
    UserConnection,
    ForgotPassword,
    ResetPassword,
)
from .service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
async def register(
    body: UserCreate,
    bg_tasks: BackgroundTasks,
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    user = await AuthService.register_user(body, bg_tasks, db_sess)
    rsp = await set_cookie(user, Response(), db_sess)
    await db_sess.commit()
    return rsp


@router.post("/login")
async def login(body: UserLogin, db_sess: AsyncSession = Depends(depends_db_sess)):
    user = await AuthService.verify_credentials(body, db_sess)
    rsp = await set_cookie(user, Response(), db_sess)
    await db_sess.commit()
    return rsp


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPassword,
    bg_tasks: BackgroundTasks,
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    return await AuthService.forgot_password(body, bg_tasks, db_sess)


@router.post("/reset-password")
async def reset_password(
    body: ResetPassword, db_sess: AsyncSession = Depends(depends_db_sess)
):
    rsp = await AuthService.reset_password(body, db_sess)
    await db_sess.commit()
    return rsp


@router.post("/request-email-verification")
async def request_email_verification(
    bg_tasks: BackgroundTasks,
    jwt: JWTPayload = Depends(depends_jwt(False)),
):
    try:
        await AuthService.request_email_verification(
            user_id=str(jwt.sub),
            email=jwt.em,
            bg_tasks=bg_tasks,
        )
    except MaxEmailVerificationAttemptsException as e:
        raise HTTPException(
            status_code=429,
            detail=e.args[0],
            headers={"Retry-After": str(e.timeout)},
        )


@router.post("/verify-email")
async def verify_email(
    body: VerifyCode,
    jwt: JWTPayload = Depends(depends_jwt(False)),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    rsp = await AuthService.verify_email(
        user_id=str(jwt.sub),
        code=body.code,
        db_sess=db_sess,
    )
    return await set_cookie(rsp, Response(), db_sess)


@router.post("/logout")
async def logout(
    jwt: JWTPayload = Depends(depends_jwt(True)),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    await db_sess.execute(
        update(Users).values(jwt=None).where(Users.user_id == jwt.sub)
    )
    await db_sess.commit()
    return JWTService.remove_jwt()


@router.get("/me", response_model=UserMe)
async def get_me(
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    connections = {}

    if user.discord_oauth_payload is not None:
        decrypted = EncryptionService.decrypt(
            user.discord_oauth_payload, expected_aad=str(user.user_id)
        )
        identity = await handle_fetch_discord_identity(decrypted, user)
        await db_sess.commit()
        if identity.success:
            connections[MessagePlatform.DISCORD] = UserConnection(
                username=identity.username,
                avatar=identity.avatar,
            )

    return UserMe(
        username=user.username,
        pricing_tier=user.pricing_tier,
        connections=connections,
    )


@router.get("/discord/oauth", status_code=204)
async def discord_oauth_callback(
    code: str,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    payload = await DiscordService.fetch_discord_oauth_payload(code)
    payload["created_at"] = get_datetime().timestamp()
    payload["expires_at"] = payload["created_at"] + payload["expires_in"]

    encrypted = EncryptionService.encrypt(payload, aad=str(jwt.sub))

    user = await db_sess.scalar(
        update(Users)
        .values(discord_oauth_payload=encrypted)
        .where(Users.user_id == jwt.sub)
        .returning(Users)
    )

    rsp =  Response(status_code=204)
    rsp = await set_cookie(user, rsp, db_sess)
    await db_sess.commit()
    return rsp


@router.get(
    "/discord/oauth/bot", status_code=204, dependencies=[Depends(depends_jwt())]
)
async def discord_oauth_bot_callback(code: str):
    """Handle Discord bot OAuth callback to add bot to guild."""
    payload = await DiscordService.fetch_discord_bot_oauth_payload(code)

    if "error" in payload:
        raise HTTPException(
            status_code=400,
            detail=f"Discord OAuth error: {payload.get('error_description', payload['error'])}",
        )


@router.post("/change-username", status_code=202)
async def change_username(
    body: UpdateUsername,
    bg_tasks: BackgroundTasks,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    return await AuthService.initiate_change_action(
        user_id=str(jwt.sub),
        email=jwt.em,
        action="change_username",
        new_value=body.username,
        bg_tasks=bg_tasks,
        db_sess=db_sess,
    )


@router.post("/change-password", status_code=202)
async def change_password(
    body: UpdatePassword,
    bg_tasks: BackgroundTasks,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    return await AuthService.initiate_change_action(
        user_id=str(jwt.sub),
        email=jwt.em,
        action="change_password",
        new_value=body.password,
        bg_tasks=bg_tasks,
        db_sess=db_sess,
    )


@router.post("/verify-action")
async def verify_action(
    body: VerifyAction,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    await AuthService.verify_and_execute_action(
        user_id=str(jwt.sub), body=body, db_sess=db_sess
    )
    await db_sess.commit()

    rsp = Response(status_code=204)
    if body.action == "change_password":
        rsp = remove_jwt(rsp)

    return rsp
