import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from aiokafka import AIOKafkaProducer
import stripe
from sqlalchemy import select, update

from core.events import StopDeploymentEvent
from utils.kafka import dump_model
from config import (
    KAFKA_BOOTSTRAP_SERVER,
    KAFKA_DEPLOYMENT_EVENTS_TOPIC,
    REDIS_CLIENT,
    REDIS_STRIPE_INVOICE_METADATA_KEY_PREFIX,
)
from core.enums import ModeratorDeploymentStatus, PricingTierType
from db_models import ModeratorDeployments, Users
from server.services.email_service import EmailService
from utils.db import get_db_sess


logger = logging.getLogger("payment_service")


class VerificationError(Exception):
    pass


class PaymentService:
    _handlers: dict | None = None
    _email_service: EmailService | None = None
    _kafka_producer: AIOKafkaProducer | None = None

    @classmethod
    async def handle_event(
        cls, event_bytes: bytes, sig_header: str, secret: str
    ) -> bool:
        if not cls._handlers:
            cls._handlers = {
                "checkout.session.completed": cls._handle_checkout_session_completed,
                "customer.subscription.deleted": cls._handle_customer_subscription_deleted,
                "invoice.payment_succeeded": cls._handle_invoice_payment_succeeded,
                "invoice.payment_failed": cls._handle_invoice_payment_failed,
                "invoice.upcoming": cls._handle_invoice_upcoming,
            }
        if not cls._email_service:
            cls._email_service = EmailService("Gova", "no-replay@gova.chat")

        try:
            event = stripe.Webhook.construct_event(
                payload=event_bytes,
                sig_header=sig_header,
                secret=secret,
            )
        except stripe.SignatureVerificationError:
            raise VerificationError("Invalid signature.")

        event_type = event.get("type")
        func = cls._handlers.get(event_type)
        if func:
            return await func(event)

        logger.warning(f"Handler for event type '{event_type}' not found.")
        return False

    @classmethod
    async def _handle_checkout_session_completed(cls, event: dict[str, Any]):
        """Stores checkout metadata in Redis to link the user to the invoice."""
        session = event["data"]["object"]
        await REDIS_CLIENT.set(
            f"{REDIS_STRIPE_INVOICE_METADATA_KEY_PREFIX}{session['invoice']}",
            json.dumps(session["metadata"]),
            ex=86400,  # 24 hours to receive the invoice event
        )
        return True

    @classmethod
    async def _handle_invoice_payment_failed(cls, event: dict[str, Any]):
        """Handles failed payments and downgrades the user."""
        invoice = event["data"]["object"]
        invoice_id = invoice["id"]
        customer_id = invoice.get("customer")
        user_id = None

        # Attempt to get user_id from Redis metadata from the initial checkout
        redis_key = f"{REDIS_STRIPE_INVOICE_METADATA_KEY_PREFIX}{invoice_id}"
        metadata_str: str | None = await REDIS_CLIENT.get(redis_key)
        if metadata_str:
            user_id = json.loads(metadata_str).get("user_id")
            await REDIS_CLIENT.delete(redis_key)

        async with get_db_sess() as db_sess:
            if user_id:
                user_lookup_condition = Users.user_id == user_id
            elif customer_id:
                user_lookup_condition = Users.stripe_customer_id == customer_id
            else:
                logger.warning(
                    f"No user_id or customer_id found for failed invoice {invoice_id}"
                )
                return False

            user = await db_sess.scalar(
                update(Users)
                .values(pricing_tier=PricingTierType.FREE.value)
                .where(user_lookup_condition)
                .returning(Users)
            )

            res = await db_sess.scalars(
                select(ModeratorDeployments.deployment_id).where(
                    ModeratorDeployments.status
                    != ModeratorDeploymentStatus.OFFLINE.value
                )
            )
            dids = res.all()

            await db_sess.commit()

        await cls._stop_deployments(dids)

        if not user:
            logger.error(
                f"Payment failed for invoice {invoice_id}, but no matching user found "
                f"with user_id='{user_id}' or stripe_customer_id='{customer_id}'."
            )
            return False

        logger.info(
            f"Payment failed for user_id={user.user_id}, invoice={invoice_id}. Downgrading to FREE."
        )

        await cls._email_service.send_email(
            recipient=user.email,
            subject="Your Gova Subscription Payment Failed",
            body=(
                f"Hi {user.username},\n\n"
                "We were unable to process the payment for your Gova PRO subscription. "
                "Your account has been downgraded to the FREE plan.\n\n"
                "To continue enjoying PRO features, please update your payment method in your account settings.\n\n"
                "If you believe this is an error, please contact our support team.\n\n"
                "Best regards,\nThe Gova Team"
            ),
        )
        return True

    @classmethod
    async def _stop_deployments(cls, deployment_ids: list[UUID]) -> None:
        if not cls._kafka_producer:
            cls._kafka_producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVER
            )

        for did in deployment_ids:
            ev = StopDeploymentEvent(deployment_id=did)
            await cls._kafka_producer.send(
                KAFKA_DEPLOYMENT_EVENTS_TOPIC, dump_model(ev)
            )

    @classmethod
    async def _handle_invoice_payment_succeeded(cls, event: dict[str, Any]):
        """Handles successful payments, upgrades the user, and sends a confirmation email."""
        invoice = event["data"]["object"]
        invoice_id = invoice["id"]
        customer_id = invoice["customer"]
        user_id = None

        redis_key = f"{REDIS_STRIPE_INVOICE_METADATA_KEY_PREFIX}{invoice_id}"
        metadata_str: str | None = await REDIS_CLIENT.get(redis_key)
        if metadata_str:
            user_id = json.loads(metadata_str).get("user_id")
            await REDIS_CLIENT.delete(redis_key)

        async with get_db_sess() as db_sess:
            if user_id:
                user_lookup_condition = Users.user_id == user_id
            elif customer_id:
                user_lookup_condition = Users.stripe_customer_id == customer_id
            else:
                logger.error(
                    f"Invoice {invoice_id} has no user_id in metadata and no customer_id."
                )
                return False

            user = await db_sess.scalar(
                update(Users)
                .values(
                    pricing_tier=PricingTierType.PRO.value,
                    stripe_customer_id=customer_id,
                )
                .where(user_lookup_condition)
                .returning(Users)
            )
            await db_sess.commit()

        if not user:
            logger.error(
                f"Payment succeeded for invoice {invoice_id}, but no matching user found "
                f"with user_id='{user_id}' or stripe_customer_id='{customer_id}'."
            )
            return False

        # Send a different email for new subscriptions vs. renewals
        billing_reason = invoice.get("billing_reason")
        if billing_reason == "subscription_create":
            logger.info(
                f"New PRO subscription for user {user.user_id}, invoice {invoice_id}."
            )
            subject = "Welcome to Gova PRO!"
            body = (
                f"Hi {user.username or 'there'},\n\n"
                "Thank you for subscribing! Your Gova PRO plan is now active.\n\n"
                "You can now enjoy all the premium features. If you have any questions, "
                "feel free to contact our support team.\n\n"
                "Best regards,\nThe Gova Team"
            )
        else:
            logger.info(
                f"Subscription renewed for user {user.user_id}, invoice {invoice_id}."
            )
            subject = "Your Gova Subscription Has Been Renewed"
            body = (
                f"Hi {user.username or 'there'},\n\n"
                "Thank you for your payment. Your Gova PRO subscription has been successfully renewed.\n\n"
                "We're glad to have you with us for another billing cycle!\n\n"
                "Best regards,\nThe Gova Team"
            )

        await cls._email_service.send_email(
            recipient=user.email, subject=subject, body=body
        )
        return True

    @classmethod
    async def _handle_invoice_upcoming(cls, event: dict[str, Any]):
        """Sends a reminder email for an upcoming subscription payment."""
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")

        if not customer_id:
            logger.info(
                "Received 'invoice.upcoming' event with no customer ID. Skipping."
            )
            return True

        async with get_db_sess() as db_sess:
            user = await db_sess.scalar(
                select(Users).where(Users.stripe_customer_id == customer_id)
            )

        if not user:
            logger.warning(
                f"Received 'invoice.upcoming' for customer '{customer_id}' but no user found."
            )
            return True

        amount_due = (
            f"{(invoice['amount_due'] / 100):.2f} {invoice['currency'].upper()}"
        )
        due_timestamp = invoice.get("next_payment_attempt") or invoice.get("due_date")
        due_date = datetime.fromtimestamp(due_timestamp).strftime("%B %d, %Y")

        logger.info(f"Notifying user {user.user_id} of upcoming payment on {due_date}.")
        await cls._email_service.send_email(
            recipient=user.email,
            subject="Your Gova Subscription Renewal is Coming Up",
            body=(
                f"Hi {user.username or 'there'},\n\n"
                f"This is a friendly reminder that your Gova PRO subscription is scheduled to renew on {due_date}.\n\n"
                f"The renewal amount will be {amount_due}.\n\n"
                "No action is needed if your payment method is up to date. "
                "To make changes, please visit your account settings.\n\n"
                "Best regards,\nThe Gova Team"
            ),
        )
        return True

    @classmethod
    async def _handle_customer_subscription_deleted(cls, event: dict[str, Any]):
        """Handles subscription cancellation and downgrades the user."""
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        if not customer_id:
            logger.warning(
                "Received 'customer.subscription.deleted' event without a customer ID."
            )
            return False

        async with get_db_sess() as db_sess:
            user = await db_sess.scalar(
                update(Users)
                .values(pricing_tier=PricingTierType.FREE.value)
                .where(Users.stripe_customer_id == customer_id)
                .returning(Users)
            )
            await db_sess.commit()

        if not user:
            logger.warning(
                f"Subscription deleted for customer '{customer_id}' but no user found to downgrade."
            )
            return True

        logger.info(
            f"Subscription canceled for user {user.user_id}. Downgraded to FREE."
        )

        await cls._email_service.send_email(
            recipient=user.email,
            subject="Your Gova Subscription Has Been Canceled",
            body=(
                f"Hi {user.username or 'there'},\n\n"
                "Your subscription to Gova PRO has been canceled, and your account has been reverted to the FREE plan.\n\n"
                "You can continue to use our free features. If you change your mind, you can upgrade again at any time from your account settings.\n\n"
                "We're sorry to see you go!\n\n"
                "Best regards,\nThe Gova Team"
            ),
        )
        return True
