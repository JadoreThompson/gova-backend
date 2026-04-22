import json

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error
from fastapi import HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    PW_HASH_SALT,
    REDIS_EMAIL_VERIFICATION_KEY_PREFIX,
    REDIS_FORGOT_PASSWORD_KEY_PREFIX,
    BASE_URL,
)
from infra.db.models import Users
from infra.redis import REDIS_CLIENT
from utils import get_datetime
from services.email import BrevoEmailService
from services.jwt import JWTService
from .controller import gen_verification_code
from .exceptions import AuthError, MaxEmailVerificationAttemptsException
from .models import UserCreate, UserLogin, VerifyAction, ForgotPassword, ResetPassword


class AuthService:
    _pw_hasher = PasswordHasher()
    _em_service = BrevoEmailService("No-Reply", "no-reply@gova.chat")
    _MAX_EMAIL_VERIFICATION_ATTEMPTS = 5
    _REDIS_EXPIRY_SECS = 900

    def __init__(self):
        raise RuntimeWarning(f"Cannot instantiate an instance of {type(self).__name__}")

    @classmethod
    async def register_user(
        cls, body: UserCreate, bg_tasks: BackgroundTasks, db_sess: AsyncSession
    ) -> Users:
        res = await db_sess.scalar(select(Users).where(Users.email == body.email))
        if res is not None:
            raise HTTPException(status_code=400, detail="Email already exists.")

        res = await db_sess.scalar(select(Users).where(Users.username == body.username))
        if res is not None:
            raise HTTPException(status_code=400, detail="Username already exists.")

        hashed_pw = cls._pw_hasher.hash(body.password, salt=PW_HASH_SALT.encode())

        user_data = body.model_dump()
        user_data["password"] = hashed_pw

        user = await db_sess.scalar(insert(Users).values(**user_data).returning(Users))
        await cls._send_email_verification_email(user.user_id, user.email, bg_tasks)
        return user

    @classmethod
    async def _send_email_verification_email(
        cls, user_id: str, email: str, bg_tasks: BackgroundTasks
    ):
        code = gen_verification_code()
        key = f"{REDIS_EMAIL_VERIFICATION_KEY_PREFIX}{user_id}"
        await REDIS_CLIENT.delete(key)
        ts = int(get_datetime().timestamp())
        await REDIS_CLIENT.set(
            key,
            json.dumps(
                {"code": code, "attempts": 1, "timestamp": ts, "last_timestamp": ts}
            ),
            ex=cls._REDIS_EXPIRY_SECS,
        )

        bg_tasks.add_task(
            cls._em_service.send_email,
            email,
            "Verify your email",
            f"Your verification code is: {code}",
        )

    @classmethod
    async def verify_credentials(cls, body: UserLogin, db_sess: AsyncSession) -> Users:
        query = select(Users).where(Users.email == body.email)
        user = await db_sess.scalar(query)
        if user is None:
            raise AuthError("User doesn't exist.")

        try:
            cls._pw_hasher.verify(user.password, body.password)
        except Argon2Error:
            raise AuthError("Invalid password.")

        return user

    @classmethod
    async def request_email_verification(
        cls, user_id: str, email: str, bg_tasks: BackgroundTasks
    ):
        code = gen_verification_code()
        key = f"{REDIS_EMAIL_VERIFICATION_KEY_PREFIX}{user_id}"
        ts = int(get_datetime().timestamp())

        prev = await REDIS_CLIENT.get(key)
        payload = None

        if prev is not None:
            data = json.loads(prev)
            end = data["timestamp"] + cls._REDIS_EXPIRY_SECS

            if ts <= end:
                if data["attempts"] == cls._MAX_EMAIL_VERIFICATION_ATTEMPTS:
                    raise MaxEmailVerificationAttemptsException(
                        "Max attempts reached",
                        max(30, end - ts),
                    )

                payload = data
                payload["code"] = code
                payload["attempts"] += 1
                payload["last_timestamp"] = ts

        if payload is None:
            payload = {
                "code": code,
                "attempts": 1,
                "timestamp": ts,
                "last_timestamp": ts,
            }

        await REDIS_CLIENT.set(key, json.dumps(payload), ex=cls._REDIS_EXPIRY_SECS)

        bg_tasks.add_task(
            cls._em_service.send_email,
            email,
            "Verify your email",
            f"Your verification code is: {code}",
        )

    @classmethod
    async def verify_email(
        cls, user_id: str, code: str, db_sess: AsyncSession
    ) -> Users:
        key = f"{REDIS_EMAIL_VERIFICATION_KEY_PREFIX}{user_id}"
        payload = await REDIS_CLIENT.get(key)

        if payload is None:
            raise AuthError("Expired verification code.")

        if json.loads(payload).get("code") != code:
            raise AuthError("Invalid verification code.")

        await REDIS_CLIENT.delete(key)
        user = await db_sess.scalar(select(Users).where(Users.user_id == user_id))
        user.verified_at = get_datetime()
        return user

    @classmethod
    async def initiate_change_action(
        cls,
        user_id: str,
        email: str,
        action: str,
        new_value: str,
        bg_tasks: BackgroundTasks,
        db_sess: AsyncSession,
    ):
        if action == "change_username":
            existing_user = await db_sess.scalar(
                select(Users).where(Users.username == new_value)
            )
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already exists.")

        await cls.send_verification_for_change_action(
            user_id=user_id,
            email=email,
            action=action,
            new_value=new_value,
            bg_tasks=bg_tasks,
        )

        return {
            "message": f"A verification code has been sent to your {'new ' if action == 'change_email' else ''}email."
        }

    @classmethod
    async def send_verification_for_change_action(
        cls,
        user_id: str,
        email: str,
        action: str,
        new_value: str,
        bg_tasks: BackgroundTasks,
    ) -> None:
        prefix = f"{action}:{user_id}:"
        async for key in REDIS_CLIENT.scan_iter(f"{prefix}*"):
            await REDIS_CLIENT.delete(key)

        verification_code = gen_verification_code()
        payload = json.dumps(
            {
                "user_id": str(user_id),
                "action": action,
                "new_value": new_value,
            }
        )
        redis_key = f"{prefix}{verification_code}"
        await REDIS_CLIENT.set(redis_key, payload, ex=cls._REDIS_EXPIRY_SECS)

        subject = f"Confirm Your {'Username' if action == 'change_username' else 'Password'} Change"

        bg_tasks.add_task(
            cls._em_service.send_email,
            email,
            subject,
            f"Your verification code is: {verification_code}",
        )

    @classmethod
    async def verify_and_execute_action(
        cls, user_id: str, body: VerifyAction, db_sess: AsyncSession
    ):
        redis_key = f"{body.action}:{user_id}:{body.code}"
        data_str = await REDIS_CLIENT.get(redis_key)
        if not data_str:
            raise HTTPException(
                status_code=400, detail="Invalid or expired verification code."
            )
        await REDIS_CLIENT.delete(redis_key)

        data = json.loads(data_str)
        if data["user_id"] != str(user_id):
            raise HTTPException(status_code=403, detail="Unauthorised request.")

        action = data["action"]
        new_value = data["new_value"]

        if action == "change_username":
            return await cls._handle_change_username(user_id, new_value, db_sess)
        elif action == "change_password":
            return await cls._handle_change_password(user_id, new_value, db_sess)
        raise AuthError("Unknown action specified.")

    @classmethod
    async def _handle_change_username(
        cls, user_id: str, new_username: str, db_sess: AsyncSession
    ):
        existing_user = await db_sess.scalar(
            select(Users).where(Users.username == new_username)
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken.")

        await db_sess.execute(
            update(Users).where(Users.user_id == user_id).values(username=new_username)
        )
        return {"message": "Username changed successfully."}

    @classmethod
    async def _handle_change_email(
        cls, user_id: str, new_email: str, db_sess: AsyncSession
    ):
        existing_user = await db_sess.scalar(
            select(Users).where(Users.email == new_email)
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already taken.")

        user = await db_sess.scalar(select(Users).where(Users.user_id == user_id))
        await db_sess.execute(
            update(Users).where(Users.user_id == user_id).values(email=new_email)
        )
        return user

    @classmethod
    async def _handle_change_password(
        cls, user_id: str, new_password: str, db_sess: AsyncSession
    ):
        hashed_pw = cls._pw_hasher.hash(new_password, salt=PW_HASH_SALT.encode())
        await db_sess.execute(
            update(Users)
            .where(Users.user_id == user_id)
            .values(password=hashed_pw, jwt=None)
        )

        rsp = JSONResponse(
            status_code=200, content={"message": "Password changed successfully."}
        )
        return JWTService.remove_jwt(rsp)

    @classmethod
    async def forgot_password(
        cls, body: ForgotPassword, bg_tasks: BackgroundTasks, db_sess: AsyncSession
    ):
        user = await db_sess.scalar(select(Users).where(Users.email == body.email))

        if user is None:
            return {"message": "If the email exists, a reset link has been sent."}

        verification_code = gen_verification_code()
        key = f"{REDIS_FORGOT_PASSWORD_KEY_PREFIX}{verification_code}"
        payload = json.dumps({"user_id": str(user.user_id), "email": body.email})
        await REDIS_CLIENT.set(key, payload, ex=cls._REDIS_EXPIRY_SECS)

        forgot_password_link = f"{BASE_URL}/reset-password?code={verification_code}"
        bg_tasks.add_task(
            cls._em_service.send_email,
            body.email,
            "Reset Your Password",
            f"Click the link to reset your password: {forgot_password_link}",
        )

        return {"message": "If the email exists, a reset link has been sent."}

    @classmethod
    async def reset_password(cls, body: ResetPassword, db_sess: AsyncSession):
        key = f"{REDIS_FORGOT_PASSWORD_KEY_PREFIX}{body.code}"
        payload = await REDIS_CLIENT.get(key)

        if not payload:
            raise HTTPException(
                status_code=400, detail="Invalid or expired reset code."
            )

        await REDIS_CLIENT.delete(key)

        data = json.loads(payload)
        user_id = data["user_id"]

        user = await db_sess.scalar(select(Users).where(Users.user_id == user_id))
        if not user:
            raise HTTPException(status_code=400, detail="User not found.")

        hashed_pw = cls._pw_hasher.hash(body.password, salt=PW_HASH_SALT.encode())
        await db_sess.execute(
            update(Users)
            .where(Users.user_id == user_id)
            .values(password=hashed_pw, jwt=None)
        )

        return {"message": "Password reset successfully."}
