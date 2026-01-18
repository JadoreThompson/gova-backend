import logging

import stripe
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import depends_db_sess, depends_jwt
from api.types import JWTPayload
from config import DOMAIN, SCHEME, STRIPE_PRICING_PRO_PRICE_ID, SUB_DOMAIN
from db_models import Users
from enums import PricingTier
from services.event_handlers import StripeEventHandler
from services.event_handlers.exceptions import VerificationError
from utils import get_datetime


router = APIRouter(prefix="/payments", tags=["Payments"])
stripe_handler = StripeEventHandler()
logger = logging.getLogger("payments.router")


@router.get("/payment-link")
async def get_payment_link(
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """Generate a Stripe Checkout link for a given user and pricing tier."""

    # Prevent upgrading to the same tier
    if jwt.pricing_tier == PricingTier.PRO:
        raise HTTPException(status_code=400, detail="User already has PRO access.")

    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))

    customer_id = user.stripe_customer_id if user else None

    # Create a new Stripe customer if none exists
    if not customer_id:
        try:
            customer = stripe.Customer.create(
                name=str(jwt.sub),
                email=jwt.em,
                metadata={"user_id": str(jwt.sub)},
            )
            customer_id = customer.id
            if user:
                user.stripe_customer_id = customer_id
                db_sess.add(user)
                await db_sess.commit()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create customer: {e}"
            )

    # Create the checkout session
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[
                {
                    "price": STRIPE_PRICING_PRO_PRICE_ID,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=f"{SCHEME}://{SUB_DOMAIN}{DOMAIN}/profile",
            cancel_url=f"{SCHEME}://{SUB_DOMAIN}{DOMAIN}/profile",
            expires_at=int(get_datetime().timestamp() + 3600),
            metadata={"user_id": str(jwt.sub)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create checkout session: {e}"
        )

    return {"url": checkout_session.url}


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """Stripe webhook endpoint for handling subscription events."""
    payload = await request.body()

    # Verify webhook signature
    try:
        event = stripe_handler.verify_webhook_signature(payload, stripe_signature)
    except VerificationError as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_id = event.get("id")
    event_type = event.get("type")

    try:
        if event_type == "checkout.session.completed":
            await stripe_handler.handle_checkout_session_completed(event)
        elif event_type == "invoice.payment_failed":
            await stripe_handler.handle_invoice_payment_failed(event)
        elif event_type == "invoice.payment_succeeded":
            await stripe_handler.handle_invoice_payment_succeeded(event)
        elif event_type == "invoice.upcoming":
            await stripe_handler.handle_invoice_upcoming(event)
        elif event_type == "customer.subscription.deleted":
            await stripe_handler.handle_customer_subscription_deleted(event)
        else:
            logger.info(
                f"Received unhandled Stripe event type: {event_type} (event_id: {event_id})"
            )

        return {"status": "success", "event_type": event_type}

    except Exception as e:
        logger.error(
            f"Error processing Stripe webhook event {event_id} (type: {event_type}): {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Internal server error processing webhook"
        )
