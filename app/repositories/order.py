from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from app.models.order import Order, OrderItem, OrderStatus
from app.repositories.base import BaseRepository


def order_aggregate_options() -> list[ExecutableOption]:
    return [selectinload(Order.items)]


class OrderRepository(BaseRepository[Order]):
    model = Order

    async def get_aggregate(
        self, order_id: UUID, establishment_id: UUID | None = None
    ) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(*order_aggregate_options())
            .execution_options(populate_existing=True)
        )
        if establishment_id is not None:
            stmt = stmt.where(Order.establishment_id == establishment_id)
        return await self.session.scalar(stmt)

    async def get_by_payment_reference(self, reference: str) -> Order | None:
        return await self.get_by(payment_reference=reference)

    async def list_for_establishment(
        self,
        establishment_id: UUID,
        *,
        offset: int,
        limit: int,
        statuses: Sequence[OrderStatus] | None = None,
        created_from: datetime | None = None,
        created_until: datetime | None = None,
    ) -> tuple[Sequence[Order], int]:
        conditions: list[ColumnElement[bool]] = [Order.establishment_id == establishment_id]
        if statuses:
            conditions.append(Order.status.in_(statuses))
        if created_from is not None:
            conditions.append(Order.created_at >= created_from)
        if created_until is not None:
            conditions.append(Order.created_at < created_until)
        return await self._page(conditions, offset, limit, newest_first=True)

    async def list_for_customer(
        self,
        *,
        offset: int,
        limit: int,
        establishment_id: UUID | None = None,
        token_hash: str | None = None,
        customer_uid: str | None = None,
    ) -> tuple[Sequence[Order], int]:
        owners: list[ColumnElement[bool]] = []
        if token_hash is not None:
            owners.append(Order.customer_token_hash == token_hash)
        if customer_uid is not None:
            owners.append(Order.customer_uid == customer_uid)
        conditions: list[ColumnElement[bool]] = [or_(*owners)]
        if establishment_id is not None:
            conditions.append(Order.establishment_id == establishment_id)
        return await self._page(conditions, offset, limit, newest_first=True)

    async def list_for_couriers(
        self, establishment_ids: Sequence[UUID], *, offset: int, limit: int
    ) -> tuple[Sequence[Order], int]:
        conditions: list[ColumnElement[bool]] = [
            Order.establishment_id.in_(establishment_ids),
            Order.status == OrderStatus.ACCEPTED,
        ]
        return await self._page(conditions, offset, limit, newest_first=False)

    async def in_period(
        self, establishment_id: UUID, created_from: datetime, created_until: datetime
    ) -> Sequence[Order]:
        stmt = (
            select(Order)
            .where(
                Order.establishment_id == establishment_id,
                Order.created_at >= created_from,
                Order.created_at < created_until,
            )
            .options(*order_aggregate_options())
        )
        return (await self.session.scalars(stmt)).all()

    async def find_for_establishment(self, establishment_id: UUID) -> Sequence[Order]:
        return await self.find_by(establishment_id=establishment_id)

    async def _page(
        self,
        conditions: list[ColumnElement[bool]],
        offset: int,
        limit: int,
        *,
        newest_first: bool,
    ) -> tuple[Sequence[Order], int]:
        order = Order.created_at.desc() if newest_first else Order.created_at
        stmt = (
            select(Order)
            .where(*conditions)
            .order_by(order, Order.id)
            .options(*order_aggregate_options())
        )
        items = (await self.session.scalars(stmt.offset(offset).limit(limit))).all()
        total = await self.session.scalar(select(func.count(Order.id)).where(*conditions))
        return items, total or 0


class OrderItemRepository(BaseRepository[OrderItem]):
    model = OrderItem

    async def is_product_used(self, product_id: UUID) -> bool:
        used = select(OrderItem.id).where(
            or_(OrderItem.product_id == product_id, OrderItem.half_product_id == product_id)
        )
        return bool(await self.session.scalar(select(used.exists())))
