import logging
from datetime import datetime

import stripe
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import DOMAIN, SCHEME, STRIPE_PRICING_PRO_PRICE_ID, SUB_DOMAIN
from core.enums import PricingTierType
from db_models import Users
from server.dependencies import depends_db_sess, depends_jwt
from server.services import StripeEventHandler
from server.services.stripe_event_handler import VerificationError
from server.typing import JWTPayload
from sqlalchemy import select


router = APIRouter(prefix="/payments", tags=["Payments"])
logger = logging.getLogger("paymnents_router")


@router.get("/payment-link")
async def get_payment_link(
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """Generate a Stripe Checkout link for a given user and pricing tier."""

    # Prevent upgrading to the same tier
    if jwt.pricing_tier == PricingTierType.PRO:
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
            expires_at=int(datetime.now().timestamp() + 3600),
            metadata={"user_id": str(jwt.sub)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create checkout session: {e}"
        )

    return {"url": checkout_session.url}


@router.post("/stripe/webhook",)
async def stripe_webhook(req: Request):
    """Stripe webhook endpoint for handling subscription events."""
    sig_header = req.headers.get("stripe-signature")
    try:
        success = await StripeEventHandler.handle_event(
            await req.body(), sig_header=sig_header
        )
        return {"success": success}
    except VerificationError as e:
        print()
        raise HTTPException(status_code=400, detail=str(e))
