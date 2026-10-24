from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select

from app.models.courier import Courier, CourierInvite
from app.models.order import Order
from app.repositories.base import BaseRepository


class CourierRepository(BaseRepository[Courier]):
    model = Courier

    async def active_for_uid(self, firebase_uid: str) -> Sequence[Courier]:
        stmt = select(Courier).where(Courier.firebase_uid == firebase_uid, Courier.active)
        return (await self.session.scalars(stmt.order_by(Courier.created_at))).all()

    async def active_uids(self, establishment_id: UUID) -> list[str]:
        stmt = select(Courier.firebase_uid).where(
            Courier.establishment_id == establishment_id, Courier.active
        )
        return list((await self.session.scalars(stmt)).all())

    async def list_for_establishment(
        self, establishment_id: UUID, *, offset: int, limit: int
    ) -> tuple[Sequence[Courier], int]:
        condition = Courier.establishment_id == establishment_id
        stmt = select(Courier).where(condition).order_by(func.lower(Courier.name), Courier.id)
        items = (await self.session.scalars(stmt.offset(offset).limit(limit))).all()
        total = await self.session.scalar(select(func.count(Courier.id)).where(condition))
        return items, total or 0

    async def has_orders(self, courier_id: UUID) -> bool:
        used = select(Order.id).where(Order.courier_id == courier_id)
        return bool(await self.session.scalar(select(used.exists())))


class CourierInviteRepository(BaseRepository[CourierInvite]):
    model = CourierInvite

    async def get_by_hash(self, token_hash: str) -> CourierInvite | None:
        return await self.get_by(token_hash=token_hash)
