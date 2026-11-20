from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
from app.models.tables import LearningPlanVersionTable, UserAvailabilityRuleTable
from app.repositories.learning_sql import _delete_owned_row, _get_owned_row, _upsert_owned_row
from app.schemas.planning import (
    AvailabilityRecurrence,
    AvailabilityRuleType,
    PlanVersionStatus,
)


class UserAvailabilityRuleRecord(BaseModel):
    id: UUID
    user_id: UUID
    label: str
    rule_type: AvailabilityRuleType = AvailabilityRuleType.personal_unavailability
    day_of_week: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str = "Europe/Paris"
    recurrence: AvailabilityRecurrence = AvailabilityRecurrence.weekly
    active: bool = True
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class LearningPlanVersionRecord(BaseModel):
    id: UUID
    user_id: UUID
    version_number: int = 1
    status: PlanVersionStatus = PlanVersionStatus.proposed
    horizon_days: int = 7
    timezone: str = "Europe/Paris"
    idempotency_key: str | None = None
    rationale: str = ""
    plan_payload: dict[str, Any] = Field(default_factory=dict)
    applied_event_ids: list[str] = Field(default_factory=list)
    applied_task_ids: list[str] = Field(default_factory=list)
    applied_course_ids: list[str] = Field(default_factory=list)
    replaced_event_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    parent_version_id: UUID | None = None
    applied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


def _to_rule_record(row: UserAvailabilityRuleTable) -> UserAvailabilityRuleRecord:
    return UserAvailabilityRuleRecord(
        id=row.id,
        user_id=row.user_id,
        label=row.label,
        rule_type=AvailabilityRuleType(row.rule_type),
        day_of_week=row.day_of_week,
        start_time=row.start_time,
        end_time=row.end_time,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        timezone=row.timezone,
        recurrence=AvailabilityRecurrence(row.recurrence),
        active=bool(row.active),
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_version_record(row: LearningPlanVersionTable) -> LearningPlanVersionRecord:
    return LearningPlanVersionRecord(
        id=row.id,
        user_id=row.user_id,
        version_number=int(row.version_number),
        status=PlanVersionStatus(row.status),
        horizon_days=int(row.horizon_days),
        timezone=row.timezone,
        idempotency_key=row.idempotency_key,
        rationale=row.rationale or "",
        plan_payload=dict(row.plan_payload or {}),
        applied_event_ids=list(row.applied_event_ids or []),
        applied_task_ids=list(row.applied_task_ids or []),
        applied_course_ids=list(row.applied_course_ids or []),
        replaced_event_snapshots=list(row.replaced_event_snapshots or []),
        parent_version_id=row.parent_version_id,
        applied_at=row.applied_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlPlanningRepository:
    """Dépôt persistant pour les règles de disponibilité et le versionnement des plans."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_availability_rules(
        self,
        user_id: UUID,
        *,
        active_only: bool = False,
    ) -> list[UserAvailabilityRuleRecord]:
        stmt = select(UserAvailabilityRuleTable).where(
            UserAvailabilityRuleTable.user_id == user_id
        )
        if active_only:
            stmt = stmt.where(UserAvailabilityRuleTable.active.is_(True))
        stmt = stmt.order_by(
            UserAvailabilityRuleTable.day_of_week.asc(),
            UserAvailabilityRuleTable.start_time.asc(),
            UserAvailabilityRuleTable.created_at.asc(),
        )
        rows = self._db.scalars(stmt).all()
        return [_to_rule_record(r) for r in rows]

    def get_availability_rule(
        self,
        user_id: UUID,
        rule_id: UUID,
    ) -> UserAvailabilityRuleRecord | None:
        row = _get_owned_row(self._db, UserAvailabilityRuleTable, rule_id, user_id)
        return _to_rule_record(row) if row is not None else None

    def save_availability_rule(
        self,
        record: UserAvailabilityRuleRecord,
    ) -> UserAvailabilityRuleRecord:
        data = record.model_dump()
        data["rule_type"] = record.rule_type.value
        data["recurrence"] = record.recurrence.value
        row = _upsert_owned_row(self._db, UserAvailabilityRuleTable, record.id, record.user_id, data)
        return _to_rule_record(row)

    def delete_availability_rule(self, user_id: UUID, rule_id: UUID) -> bool:
        return _delete_owned_row(self._db, UserAvailabilityRuleTable, rule_id, user_id)

    def list_plan_versions(
        self,
        user_id: UUID,
        *,
        limit: int = 30,
    ) -> list[LearningPlanVersionRecord]:
        stmt = (
            select(LearningPlanVersionTable)
            .where(LearningPlanVersionTable.user_id == user_id)
            .order_by(
                desc(LearningPlanVersionTable.version_number),
                desc(LearningPlanVersionTable.created_at),
            )
            .limit(max(1, min(limit, 100)))
        )
        rows = self._db.scalars(stmt).all()
        return [_to_version_record(r) for r in rows]

    def get_plan_version(
        self,
        user_id: UUID,
        version_id: UUID,
    ) -> LearningPlanVersionRecord | None:
        row = _get_owned_row(self._db, LearningPlanVersionTable, version_id, user_id)
        return _to_version_record(row) if row is not None else None

    def get_plan_version_by_idempotency(
        self,
        user_id: UUID,
        idempotency_key: str,
    ) -> LearningPlanVersionRecord | None:
        key = idempotency_key.strip()
        if not key:
            return None
        row = self._db.scalar(
            select(LearningPlanVersionTable).where(
                LearningPlanVersionTable.user_id == user_id,
                LearningPlanVersionTable.idempotency_key == key,
            )
        )
        return _to_version_record(row) if row is not None else None

    def next_version_number(self, user_id: UUID) -> int:
        current = self._db.scalar(
            select(func.max(LearningPlanVersionTable.version_number)).where(
                LearningPlanVersionTable.user_id == user_id
            )
        )
        return int(current or 0) + 1

    def get_latest_applied_version(
        self,
        user_id: UUID,
    ) -> LearningPlanVersionRecord | None:
        row = self._db.scalar(
            select(LearningPlanVersionTable)
            .where(
                LearningPlanVersionTable.user_id == user_id,
                LearningPlanVersionTable.status.in_(["applied", "restored"]),
            )
            .order_by(
                desc(LearningPlanVersionTable.applied_at),
                desc(LearningPlanVersionTable.version_number),
            )
        )
        return _to_version_record(row) if row is not None else None

    def save_plan_version(
        self,
        record: LearningPlanVersionRecord,
    ) -> LearningPlanVersionRecord:
        data = record.model_dump()
        data["status"] = record.status.value
        row = _upsert_owned_row(
            self._db,
            LearningPlanVersionTable,
            record.id,
            record.user_id,
            data,
        )
        return _to_version_record(row)
