from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from app.core.errors import AppError
from app.repositories.memory import ScheduleEventRecord, ScheduleRepository
from app.schemas.schedule import (
    DuplicateWeekResponse,
    ScheduleEventCreate,
    ScheduleEventResponse,
    ScheduleEventUpdate,
)


def do_events_overlap(
    a_start: datetime,
    a_end: datetime,
    b_start: datetime,
    b_end: datetime,
) -> bool:
    """Chevauchement strict : deux créneaux consécutifs ne sont pas en conflit (SCHED-03)."""
    return a_start < b_end and b_start < a_end


def _shift_local_days(dt_utc: datetime, days: int, tz: ZoneInfo) -> datetime:
    local_dt = dt_utc.astimezone(tz)
    target_date = local_dt.date() + timedelta(days=days)
    shifted_local = datetime.combine(
        target_date,
        local_dt.timetz().replace(tzinfo=None),
        tzinfo=tz,
    )
    return shifted_local.astimezone(timezone.utc)


def enrich_schedule_events(
    events_to_render: list[ScheduleEventRecord],
    all_user_events: list[ScheduleEventRecord],
) -> list[ScheduleEventResponse]:
    sorted_events = sorted(events_to_render, key=lambda event: event.starts_at)
    sorted_all = sorted(all_user_events, key=lambda event: event.starts_at)

    responses: list[ScheduleEventResponse] = []
    for event in sorted_events:
        conflicting_ids = [
            other.id
            for other in sorted_all
            if other.id != event.id
            and do_events_overlap(event.starts_at, event.ends_at, other.starts_at, other.ends_at)
        ]
        duration_minutes = max(0, round((event.ends_at - event.starts_at).total_seconds() / 60))
        responses.append(
            ScheduleEventResponse(
                id=event.id,
                user_id=event.user_id,
                title=event.title,
                type=event.type,
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                notes=event.notes,
                duration_minutes=duration_minutes,
                has_conflict=bool(conflicting_ids),
                conflicting_event_ids=conflicting_ids,
                created_at=event.created_at,
                updated_at=event.updated_at,
            )
        )
    return responses


class ScheduleService:
    def __init__(self, schedule_repo: ScheduleRepository) -> None:
        self._schedule_repo = schedule_repo

    def list_events(
        self,
        user_id: UUID,
        *,
        week_start: date | None = None,
        tz_name: str = "Africa/Dakar",
    ) -> list[ScheduleEventResponse]:
        all_events = self._schedule_repo.list_by_user(user_id)
        if week_start is None:
            return enrich_schedule_events(all_events, all_events)

        tz = ZoneInfo(tz_name)
        monday = week_start - timedelta(days=week_start.weekday())
        sunday = monday + timedelta(days=6)
        week_events = [
            event
            for event in all_events
            if monday <= event.starts_at.astimezone(tz).date() <= sunday
        ]
        return enrich_schedule_events(week_events, all_events)

    def create_event(self, user_id: UUID, payload: ScheduleEventCreate) -> ScheduleEventResponse:
        now = datetime.now(timezone.utc)
        record = ScheduleEventRecord(
            id=uuid4(),
            user_id=user_id,
            title=payload.title,
            type=payload.type,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        saved = self._schedule_repo.save(record)
        all_events = self._schedule_repo.list_by_user(user_id)
        return enrich_schedule_events([saved], all_events)[0]

    def get_event(self, user_id: UUID, event_id: UUID) -> ScheduleEventResponse:
        record = self._schedule_repo.get(user_id, event_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Créneau introuvable.")
        all_events = self._schedule_repo.list_by_user(user_id)
        return enrich_schedule_events([record], all_events)[0]

    def update_event(
        self,
        user_id: UUID,
        event_id: UUID,
        payload: ScheduleEventUpdate,
    ) -> ScheduleEventResponse:
        existing = self._schedule_repo.get(user_id, event_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Créneau introuvable.")

        fields = payload.model_fields_set
        next_starts_at = payload.starts_at if "starts_at" in fields and payload.starts_at else existing.starts_at
        next_ends_at = payload.ends_at if "ends_at" in fields and payload.ends_at else existing.ends_at
        if next_ends_at <= next_starts_at:
            raise AppError(
                422,
                "VALIDATION_ERROR",
                "L’heure de fin doit être strictement postérieure au début.",
            )

        updates: dict[str, object] = {
            "starts_at": next_starts_at,
            "ends_at": next_ends_at,
            "updated_at": datetime.now(timezone.utc),
        }
        if "title" in fields and payload.title is not None:
            updates["title"] = payload.title
        if "type" in fields and payload.type is not None:
            updates["type"] = payload.type
        if "notes" in fields:
            updates["notes"] = payload.notes

        saved = self._schedule_repo.save(existing.model_copy(update=updates))
        all_events = self._schedule_repo.list_by_user(user_id)
        return enrich_schedule_events([saved], all_events)[0]

    def delete_event(self, user_id: UUID, event_id: UUID) -> None:
        if not self._schedule_repo.delete(user_id, event_id):
            raise AppError(404, "NOT_FOUND", "Créneau introuvable.")

    def duplicate_week(
        self,
        user_id: UUID,
        source_week_start: date,
        tz_name: str = "Africa/Dakar",
    ) -> DuplicateWeekResponse:
        tz = ZoneInfo(tz_name)
        all_events = self._schedule_repo.list_by_user(user_id)
        monday = source_week_start - timedelta(days=source_week_start.weekday())
        sunday = monday + timedelta(days=6)

        source_events = sorted(
            [
                event
                for event in all_events
                if monday <= event.starts_at.astimezone(tz).date() <= sunday
            ],
            key=lambda event: event.starts_at,
        )

        existing_keys = {
            (event.title.strip().lower(), event.starts_at, event.ends_at)
            for event in all_events
        }

        now = datetime.now(timezone.utc)
        to_create: list[ScheduleEventRecord] = []
        skipped_count = 0

        for event in source_events:
            next_starts = _shift_local_days(event.starts_at, 7, tz)
            next_ends = _shift_local_days(event.ends_at, 7, tz)
            fingerprint = (event.title.strip().lower(), next_starts, next_ends)

            if fingerprint in existing_keys:
                skipped_count += 1
                continue

            existing_keys.add(fingerprint)
            to_create.append(
                ScheduleEventRecord(
                    id=uuid4(),
                    user_id=user_id,
                    title=event.title,
                    type=event.type,
                    starts_at=next_starts,
                    ends_at=next_ends,
                    notes=event.notes,
                    created_at=now,
                    updated_at=now,
                )
            )

        saved_records = self._schedule_repo.save_many(to_create) if to_create else []
        updated_all = self._schedule_repo.list_by_user(user_id)
        enriched = enrich_schedule_events(saved_records, updated_all)

        return DuplicateWeekResponse(
            created=enriched,
            created_count=len(enriched),
            skipped_count=skipped_count,
        )
