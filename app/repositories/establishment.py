from uuid import UUID

from sqlalchemy import func, select

from app.models.establishment import Establishment
from app.repositories.base import BaseRepository


class EstablishmentRepository(BaseRepository[Establishment]):
    model = Establishment

    async def get_by_firebase_uid(self, firebase_uid: str) -> Establishment | None:
        return await self.get_by(firebase_uid=firebase_uid)

    async def get_by_slug(self, slug: str) -> Establishment | None:
        return await self.get_by(slug=slug)

    async def slug_taken(self, slug: str, exclude_id: UUID | None = None) -> bool:
        conditions = [Establishment.slug == slug]
        if exclude_id is not None:
            conditions.append(Establishment.id != exclude_id)
        stmt = select(select(Establishment.id).where(*conditions).exists())
        return bool(await self.session.scalar(stmt))

    async def lock(self, establishment_id: UUID) -> Establishment:
        stmt = (
            select(Establishment)
            .where(Establishment.id == establishment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (await self.session.scalars(stmt)).one()

    async def lock_uid(self, firebase_uid: str) -> None:
        await self.session.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended(firebase_uid, 0)))
        )
