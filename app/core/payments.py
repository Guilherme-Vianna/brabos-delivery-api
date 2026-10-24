from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class PaymentEventKind(StrEnum):
    PAID = "paid"
    EXPIRED = "expired"
    IGNORED = "ignored"


@dataclass(frozen=True, slots=True)
class CheckoutLine:
    name: str
    unit_amount: Decimal
    quantity: int


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    reference: str
    url: str


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    kind: PaymentEventKind
    checkout_reference: str | None = None
    payment_reference: str | None = None
    order_id: UUID | None = None


class PaymentGateway(Protocol):
    async def create_checkout(
        self,
        order_id: UUID,
        lines: list[CheckoutLine],
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession: ...

    def parse_webhook(self, payload: bytes, signature: str) -> PaymentEvent: ...

    async def refund(self, payment_reference: str) -> None: ...
