import json
import logging
from typing import Any
from uuid import UUID

import stripe
from aiokafka import AIOKafkaProducer
from sqlalchemy import select, update

from config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_MODERATOR_EVENTS_TOPIC,
    REDIS_STRIPE_INVOICE_METADATA_KEY_PREFIX,
    REDIS_USER_MODERATOR_MESSAGES_PREFIX,
    STRIPE_PRICING_PRO_WEBHOOK_SECRET,
)
from db_models import Moderators, Users
from enums import ModeratorStatus, PricingTier
from events.moderator import StopModeratorEvent
from infra.db import get_db_sess
from infra.redis import REDIS_CLIENT
from services.email import BrevoEmailService
from .exceptions import (
    IncorrectEventTypeException,
    StripeHandlerException,
    VerificationError,
)


def ensure_event_type(event_type: str):
    def outer(func):
        def inner(self, event: dict[str, Any], *args, **kw):
            if event.get("type") != event_type:
                raise IncorrectEventTypeException(
                    f"Expected event with type {event_type}"
                    f" received {event.get('type')}"
                )
            return func(self, event, *args, **kw)

        return inner

    return outer


class StripeEventHandler:
    def __init__(
        self,
        webhook_secret: str = STRIPE_PRICING_PRO_WEBHOOK_SECRET,
    ) -> None:
        self._webhook_secret = webhook_secret
        self._logger = logging.getLogger(type(self).__name__)
        self._email_service = BrevoEmailService("Gova", "no-replay@gova.chat")
        self._kafka_producer: AIOKafkaProducer | None = None

    def verify_webhook_signature(
        self, payload: bytes, signature: str, tolerance: int = 300
    ) -> dict[str, Any]:
        """
        Verify the Stripe webhook signature and construct the event.

        Args:
            payload: The raw request body as bytes
            signature: The Stripe-Signature header value
            tolerance: Maximum age of the webhook event in seconds (default: 300)

        Returns:
            The verified event object as a dictionary

        Raises:
            VerificationError: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self._webhook_secret, tolerance
            )
            self._logger.info(
                f"Successfully verified webhook signature for event {event.get('id')} "
                f"(type: {event.get('type')})"
            )
            return event
        except stripe.SignatureVerificationError as e:
            self._logger.error(f"Webhook signature verification failed: {e}", exc_info=e)
            raise VerificationError(f"Invalid webhook signature: {e}")
        except Exception as e:
            self._logger.error(f"Error constructing webhook event: {e}")
            raise VerificationError(f"Failed to construct webhook event: {e}")

    @ensure_event_type("checkout.session.completed")
    async def handle_checkout_session_completed(self, event: dict[str, Any]):
        """Stores checkout metadata in Redis to link the user to the invoice."""
        event_id = event["id"]
        session = event["data"]["object"]
        invoice_id = session.get("invoice")

        if not invoice_id:
            self._logger.warning(
                f"Received event type 'checkout.session.completed' (event_id: {event_id}) - "
                f"No invoice ID found in session"
            )
            return

        await REDIS_CLIENT.set(
            f"{REDIS_STRIPE_INVOICE_METADATA_KEY_PREFIX}{invoice_id}",
            json.dumps(session["metadata"]),
            ex=86400,  # 24 hours to receive the invoice event
        )

        self._logger.info(
            f"Received event type 'checkout.session.completed' (event_id: {event_id}) - "
            f"Stored metadata for invoice {invoice_id}"
        )

    @ensure_event_type("invoice.payment_failed")
    async def handle_invoice_payment_failed(self, event: dict[str, Any]) -> None:
        """Handle when a subscription payment fails."""
        event_id = event["id"]
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
                self._logger.error(
                    f"Received event type 'invoice.payment_failed' (event_id: {event_id}) - "
                    f"No user_id or customer_id found for invoice {invoice_id}"
                )
                raise StripeHandlerException(
                    f"No user_id or customer_id found for invoice {invoice_id}"
                )

            user = await db_sess.scalar(
                update(Users)
                .values(pricing_tier=PricingTier.FREE.value)
                .where(user_lookup_condition)
                .returning(Users)
            )

            if not user:
                self._logger.error(
                    f"Received event type 'invoice.payment_failed' (event_id: {event_id}) - "
                    f"Failed to find user with user_id='{user_id}' or stripe_customer_id='{customer_id}'"
                )
                raise StripeHandlerException(
                    f"Failed to find user with user_id='{user_id}' or stripe_customer_id='{customer_id}'"
                )

            # Get all non-offline moderators for this user
            result = await db_sess.execute(
                select(Moderators.moderator_id).where(
                    Moderators.user_id == user.user_id,
                    Moderators.status != ModeratorStatus.OFFLINE.value
                )
            )
            moderator_ids = result.scalars().all()
            await db_sess.commit()

        # Stop all running moderators
        for mod_id in moderator_ids:
            await self._stop_moderator(mod_id)

        self._logger.info(
            f"Received event type 'invoice.payment_failed' (event_id: {event_id}) - "
            f"Downgraded user {user.user_id} to FREE tier and stopped {len(moderator_ids)} moderator(s)"
        )

        await self._email_service.send_email(
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

    @ensure_event_type("invoice.payment_succeeded")
    async def handle_invoice_payment_succeeded(self, event: dict[str, Any]):
        """Handle when a subscription invoice is successfully paid."""
        event_id = event["id"]
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
                self._logger.error(
                    f"Received event type 'invoice.payment_succeeded' (event_id: {event_id}) - "
                    f"No user_id or customer_id found for invoice {invoice_id}"
                )
                raise StripeHandlerException(
                    f"No user_id or customer_id found for invoice {invoice_id}"
                )

            user = await db_sess.scalar(select(Users).where(user_lookup_condition))
            if not user:
                self._logger.error(
                    f"Received event type 'invoice.payment_succeeded' (event_id: {event_id}) - "
                    f"Failed to find user with user_id='{user_id}' or stripe_customer_id='{customer_id}'"
                )
                raise StripeHandlerException(
                    f"Failed to find user with user_id='{user_id}' or stripe_customer_id='{customer_id}'"
                )

            user.pricing_tier = PricingTier.PRO.value
            user.stripe_customer_id = customer_id
            user_id, username, email = user.user_id, user.username, user.email
            await db_sess.commit()

        key = f"{REDIS_USER_MODERATOR_MESSAGES_PREFIX}{user_id}"
        await REDIS_CLIENT.set(key, 0)

        # Send a different email for new subscriptions vs. renewals
        billing_reason = invoice.get("billing_reason")
        if billing_reason == "subscription_create":
            self._logger.info(
                f"Received event type 'invoice.payment_succeeded' (event_id: {event_id}) - "
                f"New PRO subscription for user {user_id}"
            )
            subject = "Welcome to Gova PRO!"
            body = (
                f"Hi {username or 'there'},\n\n"
                "Thank you for subscribing! Your Gova PRO plan is now active.\n\n"
                "You can now enjoy all the premium features. If you have any questions, "
                "feel free to contact our support team.\n\n"
                "Best regards,\nThe Gova Team"
            )
        else:
            self._logger.info(
                f"Received event type 'invoice.payment_succeeded' (event_id: {event_id}) - "
                f"Subscription renewed for user {user_id}"
            )
            subject = "Your Gova Subscription Has Been Renewed"
            body = (
                f"Hi {username or 'there'},\n\n"
                "Thank you for your payment. Your Gova PRO subscription has been successfully renewed.\n\n"
                "We're glad to have you with us for another billing cycle!\n\n"
                "Best regards,\nThe Gova Team"
            )

        await self._email_service.send_email(email, subject, body)

    @ensure_event_type("invoice.upcoming")
    async def handle_invoice_upcoming(self, event: dict[str, Any]):
        """Send a reminder email for an upcoming subscription payment."""
        event_id = event["id"]
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")

        if not customer_id:
            self._logger.info(
                f"Received event type 'invoice.upcoming' (event_id: {event_id}) - "
                f"No customer ID found, skipping"
            )
            return

        async with get_db_sess() as db_sess:
            user = await db_sess.scalar(
                select(Users).where(Users.stripe_customer_id == customer_id)
            )

        if not user:
            self._logger.warning(
                f"Received event type 'invoice.upcoming' (event_id: {event_id}) - "
                f"No user found for customer '{customer_id}'"
            )
            return

        from datetime import datetime
        amount_due = (
            f"{(invoice['amount_due'] / 100):.2f} {invoice['currency'].upper()}"
        )
        due_timestamp = invoice.get("next_payment_attempt") or invoice.get("due_date")
        due_date = datetime.fromtimestamp(due_timestamp).strftime("%B %d, %Y")

        self._logger.info(
            f"Received event type 'invoice.upcoming' (event_id: {event_id}) - "
            f"Notifying user {user.user_id} of upcoming payment on {due_date}"
        )

        await self._email_service.send_email(
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

    @ensure_event_type("customer.subscription.deleted")
    async def handle_customer_subscription_deleted(self, event: dict[str, Any]):
        """Handle when a subscription is deleted."""
        event_id = event["id"]
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        if not customer_id:
            self._logger.error(
                f"Received event type 'customer.subscription.deleted' (event_id: {event_id}) - "
                f"No customer ID found"
            )
            raise StripeHandlerException("No customer ID found in subscription event")

        async with get_db_sess() as db_sess:
            user = await db_sess.scalar(
                update(Users)
                .values(pricing_tier=PricingTier.FREE.value)
                .where(Users.stripe_customer_id == customer_id)
                .returning(Users)
            )

            if user:
                # Get all non-offline moderators for this user
                result = await db_sess.execute(
                    select(Moderators.moderator_id).where(
                        Moderators.user_id == user.user_id,
                        Moderators.status != ModeratorStatus.OFFLINE.value
                    )
                )
                moderator_ids = result.scalars().all()
            else:
                moderator_ids = []

            await db_sess.commit()

        if not user:
            self._logger.warning(
                f"Received event type 'customer.subscription.deleted' (event_id: {event_id}) - "
                f"No user found for customer '{customer_id}'"
            )
            return

        # Stop all running moderators
        for mod_id in moderator_ids:
            await self._stop_moderator(mod_id)

        self._logger.info(
            f"Received event type 'customer.subscription.deleted' (event_id: {event_id}) - "
            f"Downgraded user {user.user_id} to FREE tier and stopped {len(moderator_ids)} moderator(s)"
        )

        await self._email_service.send_email(
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

    async def _stop_moderator(self, moderator_id: UUID) -> None:
        """Stop a moderator by sending a stop event to Kafka."""
        if self._kafka_producer is None:
            self._kafka_producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS
            )
            await self._kafka_producer.start()

        event = StopModeratorEvent(
            moderator_id=moderator_id, reason="Failed billing cycle."
        )
        await self._kafka_producer.send(
            KAFKA_MODERATOR_EVENTS_TOPIC, event.model_dump_json().encode()
        )
        self._logger.info(f"Sent stop event for moderator {moderator_id}")
