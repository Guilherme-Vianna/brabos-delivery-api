from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.exceptions import NotFoundError
from app.models.absence import Absence
from app.models.base import utc_now
from app.repositories.absence import AbsenceRepository
from app.repositories.establishment import EstablishmentRepository
from app.schemas.absence import AbsenceCreate
from app.services.common import require_establishment


class AbsenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.establishments = EstablishmentRepository(session)
        self.absences = AbsenceRepository(session)

    async def create(self, user: AuthenticatedUser, data: AbsenceCreate) -> Absence:
        establishment = await require_establishment(self.establishments, user)
        absence = await self.absences.add(
            Absence(establishment_id=establishment.id, **data.model_dump())
        )
        await self.session.commit()
        return absence

    async def list(
        self, user: AuthenticatedUser, *, offset: int, limit: int, include_past: bool
    ) -> tuple[Sequence[Absence], int]:
        establishment = await require_establishment(self.establishments, user)
        return await self.absences.list_for_establishment(
            establishment.id,
            offset=offset,
            limit=limit,
            ends_after=None if include_past else utc_now(),
        )

    async def delete(self, user: AuthenticatedUser, absence_id: UUID) -> None:
        establishment = await require_establishment(self.establishments, user)
        absence = await self.absences.get_by(id=absence_id, establishment_id=establishment.id)
        if absence is None:
            raise NotFoundError(f"Absence {absence_id} not found")
        await self.absences.delete(absence)
        await self.session.commit()
