from collections.abc import Iterable, Sequence
from uuid import UUID

from sqlalchemy import func, select

from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model = Product

    async def get_by_name(self, establishment_id: UUID, name: str) -> Product | None:
        stmt = select(Product).where(
            Product.establishment_id == establishment_id,
            func.lower(Product.name) == name.lower(),
        )
        return await self.session.scalar(stmt.limit(1))

    async def count_featured(self, establishment_id: UUID, *, exclude: UUID | None = None) -> int:
        stmt = select(func.count(Product.id)).where(
            Product.establishment_id == establishment_id, Product.featured.is_(True)
        )
        if exclude is not None:
            stmt = stmt.where(Product.id != exclude)
        return await self.session.scalar(stmt) or 0

    async def find_for_establishment(
        self, establishment_id: UUID, product_ids: Iterable[UUID]
    ) -> dict[UUID, Product]:
        stmt = select(Product).where(
            Product.establishment_id == establishment_id, Product.id.in_(list(product_ids))
        )
        return {product.id: product for product in await self.session.scalars(stmt)}

    async def list_for_establishment(
        self,
        establishment_id: UUID,
        *,
        offset: int,
        limit: int,
        search: str | None = None,
        active: bool | None = None,
    ) -> tuple[Sequence[Product], int]:
        conditions = [Product.establishment_id == establishment_id]
        if search:
            conditions.append(Product.name.icontains(search, autoescape=True))
        if active is not None:
            conditions.append(Product.active.is_(active))
        stmt = (
            select(Product)
            .where(*conditions)
            .order_by(func.lower(Product.category), Product.position, func.lower(Product.name))
        )
        items = (await self.session.scalars(stmt.offset(offset).limit(limit))).all()
        total = await self.session.scalar(select(func.count(Product.id)).where(*conditions))
        return items, total or 0
