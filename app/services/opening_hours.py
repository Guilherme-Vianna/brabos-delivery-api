from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.models.opening_hours import OpeningHours
from app.repositories.establishment import EstablishmentRepository
from app.repositories.opening_hours import OpeningHoursRepository
from app.schemas.opening_hours import OpeningDay, OpeningHoursRead, OpeningHoursUpdate
from app.services.common import existing_establishment, require_establishment


class OpeningHoursService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.establishments = EstablishmentRepository(session)
        self.hours = OpeningHoursRepository(session)

    async def get_public(self, slug: str) -> OpeningHoursRead:
        establishment = await existing_establishment(self.establishments, slug)
        return await self._read(establishment.id)

    async def get(self, user: AuthenticatedUser) -> OpeningHoursRead:
        establishment = await require_establishment(self.establishments, user)
        return await self._read(establishment.id)

    async def replace(self, user: AuthenticatedUser, data: OpeningHoursUpdate) -> OpeningHoursRead:
        establishment = await require_establishment(self.establishments, user)
        current = {
            item.weekday: item for item in await self.hours.for_establishment(establishment.id)
        }
        wanted = {day.weekday: day for day in data.days}
        for weekday, item in current.items():
            if weekday not in wanted:
                await self.hours.delete(item)
        for weekday, day in wanted.items():
            item = current.get(weekday)
            if item is None:
                await self.hours.add(
                    OpeningHours(establishment_id=establishment.id, **day.model_dump())
                )
            elif (item.opens_at, item.closes_at) != (day.opens_at, day.closes_at):
                item.opens_at, item.closes_at = day.opens_at, day.closes_at
                await self.hours.save(item)
        await self.session.commit()
        return await self._read(establishment.id)

    async def _read(self, establishment_id) -> OpeningHoursRead:
        hours = await self.hours.for_establishment(establishment_id)
        return OpeningHoursRead(days=[OpeningDay.model_validate(item) for item in hours])
