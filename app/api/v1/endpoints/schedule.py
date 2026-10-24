from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import AbsenceServiceDep, CurrentUserDep, OpeningHoursServiceDep
from app.api.pagination import PaginationDep, to_page
from app.schemas.absence import AbsenceCreate, AbsenceRead
from app.schemas.common import Page
from app.schemas.opening_hours import OpeningHoursRead, OpeningHoursUpdate

router = APIRouter(tags=["schedule"])


@router.get("/opening-hours", response_model=OpeningHoursRead)
async def get_opening_hours(
    user: CurrentUserDep, service: OpeningHoursServiceDep
) -> OpeningHoursRead:
    return await service.get(user)


@router.put("/opening-hours", response_model=OpeningHoursRead)
async def replace_opening_hours(
    data: OpeningHoursUpdate, user: CurrentUserDep, service: OpeningHoursServiceDep
) -> OpeningHoursRead:
    return await service.replace(user, data)


@router.post("/absences", response_model=AbsenceRead, status_code=status.HTTP_201_CREATED)
async def create_absence(
    data: AbsenceCreate, user: CurrentUserDep, service: AbsenceServiceDep
) -> AbsenceRead:
    return AbsenceRead.model_validate(await service.create(user, data))


@router.get("/absences", response_model=Page[AbsenceRead])
async def list_absences(
    user: CurrentUserDep,
    service: AbsenceServiceDep,
    pagination: PaginationDep,
    include_past: bool = False,
) -> Page[AbsenceRead]:
    result = await service.list(
        user, offset=pagination.offset, limit=pagination.limit, include_past=include_past
    )
    return to_page(AbsenceRead, result, pagination)


@router.delete("/absences/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_absence(
    absence_id: UUID, user: CurrentUserDep, service: AbsenceServiceDep
) -> None:
    await service.delete(user, absence_id)
