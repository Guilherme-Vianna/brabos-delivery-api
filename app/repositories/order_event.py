from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func, select

from app.models.order import Order, OrderActor
from app.models.order_event import OrderEvent, OrderEventKind
from app.repositories.base import BaseRepository


class OrderEventRepository(BaseRepository[OrderEvent]):
    model = OrderEvent

    async def record(
        self,
        order: Order,
        kind: OrderEventKind,
        actor: OrderActor,
        actor_uid: str | None = None,
        detail: str | None = None,
    ) -> OrderEvent:
        return await self.add(
            OrderEvent(
                establishment_id=order.establishment_id,
                order_id=order.id,
                order_number=order.number,
                kind=kind,
                actor=actor,
                actor_uid=actor_uid,
                detail=detail,
            )
        )

    async def list_for_establishment(
        self,
        establishment_id: UUID,
        *,
        offset: int,
        limit: int,
        order_id: UUID | None = None,
        created_from: datetime | None = None,
        created_until: datetime | None = None,
    ) -> tuple[Sequence[OrderEvent], int]:
        conditions: list[ColumnElement[bool]] = [OrderEvent.establishment_id == establishment_id]
        if order_id is not None:
            conditions.append(OrderEvent.order_id == order_id)
        if created_from is not None:
            conditions.append(OrderEvent.created_at >= created_from)
        if created_until is not None:
            conditions.append(OrderEvent.created_at < created_until)
        stmt = (
            select(OrderEvent)
            .where(*conditions)
            .order_by(OrderEvent.created_at.desc(), OrderEvent.id.desc())
        )
        items = (await self.session.scalars(stmt.offset(offset).limit(limit))).all()
        total = await self.session.scalar(select(func.count(OrderEvent.id)).where(*conditions))
        return items, total or 0

    async def for_order(self, order_id: UUID) -> Sequence[OrderEvent]:
        stmt = (
            select(OrderEvent)
            .where(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.created_at, OrderEvent.id)
        )
        return (await self.session.scalars(stmt)).all()
