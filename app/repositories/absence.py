from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from app.models.absence import Absence
from app.repositories.base import BaseRepository


class AbsenceRepository(BaseRepository[Absence]):
    model = Absence

    async def active_at(self, establishment_id: UUID, moment: datetime) -> Absence | None:
        stmt = (
            select(Absence)
            .where(
                Absence.establishment_id == establishment_id,
                Absence.starts_at <= moment,
                Absence.ends_at > moment,
            )
            .order_by(Absence.ends_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def list_for_establishment(
        self, establishment_id: UUID, *, offset: int, limit: int, ends_after: datetime | None
    ) -> tuple[Sequence[Absence], int]:
        conditions = [Absence.establishment_id == establishment_id]
        if ends_after is not None:
            conditions.append(Absence.ends_at > ends_after)
        stmt = select(Absence).where(*conditions).order_by(Absence.starts_at)
        items = (await self.session.scalars(stmt.offset(offset).limit(limit))).all()
        total = await self.session.scalar(select(func.count(Absence.id)).where(*conditions))
        return items, total or 0
