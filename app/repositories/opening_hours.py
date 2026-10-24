from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.models.opening_hours import OpeningHours
from app.repositories.base import BaseRepository


class OpeningHoursRepository(BaseRepository[OpeningHours]):
    model = OpeningHours

    async def for_establishment(self, establishment_id: UUID) -> Sequence[OpeningHours]:
        stmt = (
            select(OpeningHours)
            .where(OpeningHours.establishment_id == establishment_id)
            .order_by(OpeningHours.weekday)
        )
        return (await self.session.scalars(stmt)).all()
