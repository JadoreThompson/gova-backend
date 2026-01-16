import json
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error
from fastapi import HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    BREVO_API_KEY,
    PW_HASH_SALT,
    REDIS_EMAIL_VERIFICATION_KEY_PREFIX,
)
from api.services import JWTService
from db_models import Users
from infra.redis import REDIS_CLIENT
from services.email import BrevoEmailService
from utils import get_datetime
from .controller import gen_verification_code
from .exceptions import MaxEmailVerificationAttemptsException
from .models import UserCreate, UserLogin, VerifyAction


class AuthService:
    _pw_hasher = PasswordHasher()
    _em_service = BrevoEmailService(
        "No-Reply", "no-reply@gova.chat"
    )
    _MAX_EMAIL_VERIFICATION_ATTEMPTS = 5
    _REDIS_EXPIRY_SECS =900

    def __init__(self):
        raise RuntimeWarning(f"Cannot instantiate an instance of {type(self).__name__}")

    @classmethod
    async def register_user(
        cls, body: UserCreate, bg_tasks: BackgroundTasks, db_sess: AsyncSession
    ):
        res = await db_sess.scalar(select(Users).where(Users.email == body.email))
        if res is not None:
            raise HTTPException(status_code=400, detail="Email already exists.")

        hashed_pw = cls._pw_hasher.hash(body.password, salt=PW_HASH_SALT.encode())

        user_data = body.model_dump()
        user_data["password"] = hashed_pw

        user = await db_sess.scalar(insert(Users).values(**user_data).returning(Users))

        code = gen_verification_code()
        key = f"{REDIS_EMAIL_VERIFICATION_KEY_PREFIX}{str(user.user_id)}"
        await REDIS_CLIENT.delete(key)
        # await REDIS_CLIENT.set(key, code, ex=REDIS_EXPIRY_SECS)
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
            body.email,
            "Verify your email",
            f"Your verification code is: {code}",
        )

        rsp = await JWTService.set_user_cookie(user, db_sess)
        rsp.status_code = 202
        return rsp

    @classmethod
    async def login_user(cls, body: UserLogin, db_sess: AsyncSession):
        query = select(Users)
        if body.username is not None:
            query = query.where(Users.username == body.username)
        if body.email is not None:
            query = query.where(Users.email == body.email)

        user = await db_sess.scalar(query)
        if user is None:
            raise HTTPException(status_code=400, detail="User doesn't exist.")

        try:
            cls._pw_hasher.verify(user.password, body.password)
        except Argon2Error:
            raise HTTPException(status_code=400, detail="Invalid password.")

        rsp = await JWTService.set_user_cookie(user, db_sess)
        if user.verified_at is None:
            rsp.status_code = 403
        return rsp

    @classmethod
    async def request_email_verification(
        cls, user_id: str, email: str, bg_tasks: BackgroundTasks
    ):
        code = gen_verification_code()
        key = f"{REDIS_EMAIL_VERIFICATION_KEY_PREFIX}{user_id}"
        ts = int(get_datetime().timestamp())

        # await REDIS_CLIENT.delete(key)
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

        await REDIS_CLIENT.set(
            key, json.dumps(payload), ex=cls._REDIS_EXPIRY_SECS
        )

        bg_tasks.add_task(
            cls._em_service.send_email,
            email,
            "Verify your email",
            f"Your verification code is: {code}",
        )

    @classmethod
    async def verify_email(cls, user_id: str, code: str, db_sess: AsyncSession):
        key = f"{REDIS_EMAIL_VERIFICATION_KEY_PREFIX}{user_id}"
        payload = await REDIS_CLIENT.get(key)

        if payload is None:
            raise HTTPException(
                status_code=400, detail="Expired verification code."
            ) 
        
        if json.loads(payload).get("code") != code:
            raise HTTPException(
                status_code=400, detail="Invalid verification code."
            )

        await REDIS_CLIENT.delete(key)
        user = await db_sess.scalar(select(Users).where(Users.user_id == user_id))
        user.verified_at = get_datetime()
        return await JWTService.set_user_cookie(user, db_sess)

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
            subject = "Confirm Your Username Change"
            target_email = email
        if action == "change_email":
            existing_user = await db_sess.scalar(
                select(Users).where(Users.email == new_value)
            )
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already exists.")
            subject = "Confirm Your Email Change"
            target_email = new_value
        elif action == "change_password":
            subject = "Confirm Your Password Change"
            target_email = email
        else:
            raise HTTPException(status_code=400, detail="Invalid action.")

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
        await REDIS_CLIENT.set(
            redis_key, payload, ex=cls._REDIS_EXPIRY_SECS
        )

        bg_tasks.add_task(
            cls._em_service.send_email,
            target_email,
            subject,
            f"Your verification code is: {verification_code}",
        )

        return {
            "message": f"A verification code has been sent to your {'new ' if action == 'change_email' else ''}email."
        }

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
            raise HTTPException(status_code=401, detail="Unauthorised request.")

        action = data["action"]
        new_value = data["new_value"]

        if action == "change_username":
            return await cls._handle_change_username(user_id, new_value, db_sess)
        if action == "change_email":
            return await cls._handle_change_email(user_id, new_value, db_sess)
        elif action == "change_password":
            return await cls._handle_change_password(user_id, new_value, db_sess)
        else:
            raise HTTPException(status_code=400, detail="Unknown action specified.")

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
        return await JWTService.set_user_cookie(user, db_sess)

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
        return JWTService.remove_cookie(rsp)
