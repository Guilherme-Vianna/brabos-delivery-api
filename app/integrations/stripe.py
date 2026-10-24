import asyncio
from decimal import Decimal
from functools import lru_cache
from uuid import UUID

import stripe

from app.core.config import settings
from app.core.exceptions import UnprocessableError
from app.core.payments import CheckoutLine, CheckoutSession, PaymentEvent, PaymentEventKind

CURRENCY = "brl"


def to_cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


class StripePaymentGateway:
    def __init__(self, secret_key: str, webhook_secret: str | None) -> None:
        self._client = stripe.StripeClient(secret_key)
        self._webhook_secret = webhook_secret

    async def create_checkout(
        self,
        order_id: UUID,
        lines: list[CheckoutLine],
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession:
        params = {
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": str(order_id),
            "metadata": {"order_id": str(order_id)},
            "line_items": [
                {
                    "quantity": line.quantity,
                    "price_data": {
                        "currency": CURRENCY,
                        "unit_amount": to_cents(line.unit_amount),
                        "product_data": {"name": line.name},
                    },
                }
                for line in lines
            ],
        }
        session = await asyncio.to_thread(self._client.v1.checkout.sessions.create, params)
        return CheckoutSession(reference=session.id, url=session.url or "")

    def parse_webhook(self, payload: bytes, signature: str) -> PaymentEvent:
        if not self._webhook_secret:
            raise UnprocessableError("Stripe webhook secret is not configured")
        try:
            event = self._client.construct_event(payload, signature, self._webhook_secret)
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise UnprocessableError("Invalid Stripe webhook") from exc
        session = event.data.object
        order_id = (session.get("metadata") or {}).get("order_id")
        kinds = {
            "checkout.session.completed": PaymentEventKind.PAID,
            "checkout.session.expired": PaymentEventKind.EXPIRED,
        }
        return PaymentEvent(
            kind=kinds.get(event.type, PaymentEventKind.IGNORED),
            checkout_reference=session.get("id"),
            payment_reference=session.get("payment_intent"),
            order_id=UUID(order_id) if order_id else None,
        )

    async def refund(self, payment_reference: str) -> None:
        await asyncio.to_thread(
            self._client.v1.refunds.create, {"payment_intent": payment_reference}
        )


@lru_cache
def get_payment_gateway() -> StripePaymentGateway | None:
    if not settings.stripe_secret_key:
        return None
    return StripePaymentGateway(settings.stripe_secret_key, settings.stripe_webhook_secret)
