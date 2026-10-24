import re
import unicodedata

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.core.payments import PaymentGateway
from app.core.storage import ObjectStorage
from app.models.establishment import Establishment
from app.repositories.absence import AbsenceRepository
from app.repositories.courier import CourierInviteRepository, CourierRepository
from app.repositories.establishment import EstablishmentRepository
from app.repositories.opening_hours import OpeningHoursRepository
from app.repositories.order import OrderItemRepository, OrderRepository
from app.repositories.order_event import OrderEventRepository
from app.repositories.product import ProductRepository
from app.repositories.push_device import PushDeviceRepository
from app.schemas.establishment import EstablishmentCreate, EstablishmentUpdate
from app.schemas.types import RESERVED_SLUGS
from app.services.availability import Availability
from app.services.common import (
    OpenStatus,
    discard_media,
    ensure_media_key,
    existing_establishment,
)


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")[:50].strip("-")
    return slug if len(slug) >= 3 and slug not in RESERVED_SLUGS else f"loja-{slug}".strip("-")


class EstablishmentService:
    def __init__(
        self,
        session: AsyncSession,
        storage: ObjectStorage | None = None,
        gateway: PaymentGateway | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.gateway = gateway
        self.establishments = EstablishmentRepository(session)

    async def get_public(self, slug: str) -> tuple[Establishment, OpenStatus]:
        establishment = await existing_establishment(self.establishments, slug)
        return establishment, await Availability(self.session).status(establishment)

    async def get_for_user(self, user: AuthenticatedUser) -> Establishment:
        establishment = await self.establishments.get_by_firebase_uid(user.uid)
        if establishment is None:
            raise NotFoundError("Current user has no registered establishment")
        return establishment

    async def register(self, user: AuthenticatedUser, data: EstablishmentCreate) -> Establishment:
        await self.establishments.lock_uid(user.uid)
        if await self.establishments.get_by_firebase_uid(user.uid) is not None:
            raise ConflictError("User already has a registered establishment")
        if data.slug is not None and await self.establishments.slug_taken(data.slug):
            raise ConflictError("Slug is already in use")
        slug = data.slug or await self._free_slug(slugify(data.name))
        establishment = Establishment(
            firebase_uid=user.uid, **data.model_dump(exclude={"slug"}), slug=slug
        )
        return await self._persist(self.establishments.add(establishment))

    async def update(self, user: AuthenticatedUser, data: EstablishmentUpdate) -> Establishment:
        establishment = await self.get_for_user(user)
        changes = data.model_dump(exclude_unset=True)
        if "slug" in changes and await self.establishments.slug_taken(
            changes["slug"], establishment.id
        ):
            raise ConflictError("Slug is already in use")
        if changes.get("online_payments_enabled") and self.gateway is None:
            raise UnprocessableError("Online payments are not configured")
        if "logo_key" in changes:
            ensure_media_key(self.storage, establishment, changes["logo_key"])
        previous_logo = establishment.logo_key
        for field, value in changes.items():
            setattr(establishment, field, value)
        saved = await self._persist(self.establishments.save(establishment))
        if previous_logo and previous_logo != saved.logo_key:
            await discard_media(self.storage, previous_logo)
        return saved

    async def unregister(self, user: AuthenticatedUser) -> None:
        establishment = await self.get_for_user(user)
        orders = OrderRepository(self.session)
        items = OrderItemRepository(self.session)
        for order in await orders.find_for_establishment(establishment.id):
            for item in await items.find_by(order_id=order.id):
                await items.delete(item)
            await orders.delete(order)
        repositories = (
            OrderEventRepository(self.session),
            AbsenceRepository(self.session),
            OpeningHoursRepository(self.session),
            ProductRepository(self.session),
            CourierInviteRepository(self.session),
            CourierRepository(self.session),
            PushDeviceRepository(self.session),
        )
        media = [establishment.logo_key]
        for repository in repositories:
            for entity in await repository.find_by(establishment_id=establishment.id):
                media.append(getattr(entity, "image_key", None))
                await repository.delete(entity)
        await self.establishments.delete(establishment)
        await self.session.commit()
        for key in media:
            await discard_media(self.storage, key)

    async def _free_slug(self, base: str) -> str:
        candidate, suffix = base, 2
        while await self.establishments.slug_taken(candidate):
            candidate = f"{base[:55]}-{suffix}"
            suffix += 1
        return candidate

    async def _persist(self, operation) -> Establishment:
        try:
            establishment = await operation
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Establishment conflicts with an existing one") from exc
        return establishment
