# api/paywall.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import stripe

router = APIRouter()


class CheckoutSessionResponse(BaseModel):
    session_id: str


@router.post("/checkout/unlock", response_model=CheckoutSessionResponse)
def create_unlock_checkout():
    """
    Crée une session Stripe Checkout pour débloquer les grilles très bien notées.
    Prix : 0,50 € (en centimes).
    """
    try:
        # stripe.api_key vient de app.py (chargé depuis .env)
        print("DEBUG stripe.api_key set ?", bool(stripe.api_key))

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {
                            "name": "Déblocage des meilleures grilles LuckyAI",
                        },
                        "unit_amount": 50,  # 0,50 € en centimes
                    },
                    "quantity": 1,
                }
            ],
success_url="https://www.luckyai.fr/index.html?premium=1",
cancel_url="https://www.luckyai.fr/index.html",
        )

        print("Stripe checkout session créée:", session.id)

        return CheckoutSessionResponse(session_id=session["id"])

    except Exception as e:
        print("Stripe error in /checkout/unlock:", repr(e))
        raise HTTPException(
            status_code=500,
            detail=f"Stripe error: {e}",
        )