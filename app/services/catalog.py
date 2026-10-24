from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.exceptions import ConflictError, NotFoundError
from app.core.storage import ObjectStorage
from app.models.establishment import Establishment
from app.models.product import Product
from app.repositories.establishment import EstablishmentRepository
from app.repositories.order import OrderItemRepository
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.common import (
    discard_media,
    ensure_media_key,
    existing_establishment,
    require_establishment,
)

NAME_TAKEN = "A product with this name already exists"


class CatalogService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage | None = None) -> None:
        self.session = session
        self.storage = storage
        self.establishments = EstablishmentRepository(session)
        self.products = ProductRepository(session)

    async def list_public(
        self, slug: str, *, offset: int, limit: int
    ) -> tuple[Sequence[Product], int]:
        establishment = await existing_establishment(self.establishments, slug)
        return await self.products.list_for_establishment(
            establishment.id, offset=offset, limit=limit, active=True
        )

    async def list(
        self,
        user: AuthenticatedUser,
        *,
        offset: int,
        limit: int,
        search: str | None,
        active: bool | None,
    ) -> tuple[Sequence[Product], int]:
        establishment = await require_establishment(self.establishments, user)
        return await self.products.list_for_establishment(
            establishment.id, offset=offset, limit=limit, search=search, active=active
        )

    async def get(self, user: AuthenticatedUser, product_id: UUID) -> Product:
        establishment = await require_establishment(self.establishments, user)
        return await self._owned(establishment, product_id)

    async def create(self, user: AuthenticatedUser, data: ProductCreate) -> Product:
        establishment = await require_establishment(self.establishments, user)
        ensure_media_key(self.storage, establishment, data.image_key)
        if await self.products.get_by_name(establishment.id, data.name):
            raise ConflictError(NAME_TAKEN)
        product = Product(establishment_id=establishment.id, **data.model_dump())
        return await self._persist(self.products.add(product))

    async def update(
        self, user: AuthenticatedUser, product_id: UUID, data: ProductUpdate
    ) -> Product:
        establishment = await require_establishment(self.establishments, user)
        product = await self._owned(establishment, product_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes:
            existing = await self.products.get_by_name(establishment.id, changes["name"])
            if existing is not None and existing.id != product.id:
                raise ConflictError(NAME_TAKEN)
        if "image_key" in changes:
            ensure_media_key(self.storage, establishment, changes["image_key"])
        previous_image = product.image_key
        for field, value in changes.items():
            setattr(product, field, value)
        saved = await self._persist(self.products.save(product))
        if previous_image and previous_image != saved.image_key:
            await discard_media(self.storage, previous_image)
        return saved

    async def delete(self, user: AuthenticatedUser, product_id: UUID) -> None:
        establishment = await require_establishment(self.establishments, user)
        product = await self._owned(establishment, product_id)
        if await OrderItemRepository(self.session).is_product_used(product.id):
            raise ConflictError("Product has orders; deactivate it instead")
        image = product.image_key
        await self.products.delete(product)
        await self.session.commit()
        await discard_media(self.storage, image)

    async def _owned(self, establishment: Establishment, product_id: UUID) -> Product:
        product = await self.products.get_by(id=product_id, establishment_id=establishment.id)
        if product is None:
            raise NotFoundError(f"Product {product_id} not found")
        return product

    async def _persist(self, operation) -> Product:
        try:
            product = await operation
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(NAME_TAKEN) from exc
        return product
