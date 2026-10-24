import base64
import json
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from uuid import UUID, uuid4

from app.core.auth import AuthenticatedUser
from app.core.cache import EPOCH_FIELD
from app.core.exceptions import UnauthorizedError, UnprocessableError
from app.core.payments import CheckoutLine, CheckoutSession, PaymentEvent, PaymentEventKind
from app.core.push import PushMessage
from app.core.storage import PresignedUpload
from app.models.base import utc_now

TOKEN_LIFETIME_SECONDS = 3600


def fake_token(uid: str, expires_at: float | None = None) -> str:
    claims = {"uid": uid, "exp": expires_at or time.time() + TOKEN_LIFETIME_SECONDS}
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"header.{payload}.signature"


class FakeIdentityProvider:
    def __init__(self) -> None:
        self.tokens: dict[str, str] = {}
        self.names: dict[str, str | None] = {}

    def add_user(self, uid: str, name: str | None = None) -> str:
        token = fake_token(uid)
        self.tokens[token] = uid
        self.names[uid] = name
        return token

    async def verify_token(self, token: str) -> AuthenticatedUser:
        uid = self.tokens.get(token)
        if uid is None:
            raise UnauthorizedError("Invalid or expired authentication token")
        return AuthenticatedUser(uid=uid, email=f"{uid}@example.com", name=self.names[uid])


class FakeResponseCache:
    def __init__(self) -> None:
        self.entries: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}
        self.versions: dict[str, int | str] = {}
        self.available = True

    async def lookup(self, key: str) -> tuple[bytes | None, dict[str, str] | None]:
        if not self.available:
            return None, None
        if EPOCH_FIELD not in self.versions:
            self.versions[EPOCH_FIELD] = uuid4().hex
            return None, self._versions()
        return self.entries.get(key), self._versions()

    async def store(self, key: str, value: bytes, ttl: int) -> None:
        if self.available:
            self.entries[key] = value
            self.ttls[key] = ttl

    async def invalidate(self, names: Iterable[str]) -> None:
        if not self.available:
            return
        for name in names:
            current = self.versions.get(name, 0)
            assert isinstance(current, int)
            self.versions[name] = current + 1

    def _versions(self) -> dict[str, str]:
        return {name: str(value) for name, value in self.versions.items()}


class FakePushNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[list[str], PushMessage]] = []
        self.invalid: set[str] = set()

    async def send(self, tokens: Sequence[str], message: PushMessage) -> list[str]:
        self.sent.append((list(tokens), message))
        return [token for token in tokens if token in self.invalid]

    def titles_for(self, token: str) -> list[str]:
        return [message.title for tokens, message in self.sent if token in tokens]


class FakeObjectStorage:
    def __init__(self) -> None:
        self.presigned: list[str] = []
        self.deleted: list[str] = []

    async def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        self.presigned.append(key)
        return PresignedUpload(
            url=f"https://upload.test/{key}",
            method="PUT",
            headers={"Content-Type": content_type},
            expires_at=utc_now() + timedelta(minutes=10),
        )

    def public_url(self, key: str) -> str:
        return f"https://cdn.test/{key}"

    async def delete(self, key: str) -> None:
        self.deleted.append(key)


class FakePaymentGateway:
    def __init__(self) -> None:
        self.checkouts: list[tuple[UUID, list[CheckoutLine]]] = []
        self.refunds: list[str] = []

    async def create_checkout(
        self, order_id: UUID, lines: list[CheckoutLine], success_url: str, cancel_url: str
    ) -> CheckoutSession:
        self.checkouts.append((order_id, lines))
        return CheckoutSession(reference=f"cs_{order_id.hex}", url=f"https://pay.test/{order_id}")

    def parse_webhook(self, payload: bytes, signature: str) -> PaymentEvent:
        if signature != "valid":
            raise UnprocessableError("Invalid Stripe webhook")
        data = json.loads(payload)
        return PaymentEvent(
            kind=PaymentEventKind(data["kind"]),
            checkout_reference=data.get("checkout_reference"),
            payment_reference=data.get("payment_reference"),
            order_id=UUID(data["order_id"]) if data.get("order_id") else None,
        )

    async def refund(self, payment_reference: str) -> None:
        self.refunds.append(payment_reference)


@dataclass
class FakeIntegrations:
    push: FakePushNotifier = field(default_factory=FakePushNotifier)
    storage: FakeObjectStorage | None = None
    gateway: FakePaymentGateway | None = None
