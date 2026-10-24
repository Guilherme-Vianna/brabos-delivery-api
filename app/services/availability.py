from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_until
from app.models.base import utc_now
from app.models.establishment import Establishment
from app.repositories.absence import AbsenceRepository
from app.repositories.opening_hours import OpeningHoursRepository
from app.services.common import OPEN_STATUS_TTL, OpenStatus, is_within_hours


class Availability:
    def __init__(self, session: AsyncSession) -> None:
        self.hours = OpeningHoursRepository(session)
        self.absences = AbsenceRepository(session)

    async def status(
        self, establishment: Establishment, moment: datetime | None = None
    ) -> OpenStatus:
        now = moment or utc_now()
        cache_until(now + OPEN_STATUS_TTL)
        absence = await self.absences.active_at(establishment.id, now)
        hours = await self.hours.for_establishment(establishment.id)
        return OpenStatus(is_open=absence is None and is_within_hours(hours, now), absence=absence)
