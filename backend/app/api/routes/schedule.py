from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from app.api.deps import get_profile_service, get_schedule_service
from app.core.security import get_current_user_id
from app.schemas.schedule import (
    DuplicateWeekRequest,
    DuplicateWeekResponse,
    ScheduleEventCreate,
    ScheduleEventResponse,
    ScheduleEventUpdate,
)
from app.services.profile_service import ProfileService
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedule", tags=["Planning"])


@router.get("", response_model=list[ScheduleEventResponse], summary="Lister les créneaux")
def list_schedule_events(
    week_start: date | None = Query(default=None),
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> list[ScheduleEventResponse]:
    profile = profile_service.get_or_create_record(user_id)
    return schedule_service.list_events(
        user_id,
        week_start=week_start,
        tz_name=profile.timezone,
    )


@router.post(
    "",
    response_model=ScheduleEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un créneau",
)
def create_schedule_event(
    payload: ScheduleEventCreate,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleEventResponse:
    return schedule_service.create_event(user_id, payload)


@router.post(
    "/duplicate-week",
    response_model=DuplicateWeekResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dupliquer les créneaux d'une semaine vers la suivante",
)
def duplicate_week(
    payload: DuplicateWeekRequest,
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> DuplicateWeekResponse:
    profile = profile_service.get_or_create_record(user_id)
    return schedule_service.duplicate_week(
        user_id,
        source_week_start=payload.source_week_start,
        tz_name=profile.timezone,
    )


@router.get(
    "/{event_id}",
    response_model=ScheduleEventResponse,
    summary="Consulter un créneau",
)
def get_schedule_event(
    event_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleEventResponse:
    return schedule_service.get_event(user_id, event_id)


@router.patch(
    "/{event_id}",
    response_model=ScheduleEventResponse,
    summary="Modifier un créneau",
)
def update_schedule_event(
    event_id: UUID,
    payload: ScheduleEventUpdate,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleEventResponse:
    return schedule_service.update_event(user_id, event_id, payload)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un créneau",
)
def delete_schedule_event(
    event_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> Response:
    schedule_service.delete_event(user_id, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
