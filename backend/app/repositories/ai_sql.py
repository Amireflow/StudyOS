from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.tables import (
    AiActionProposalTable,
    AiConversationTable,
    AiMessageTable,
    AiReportTable,
    UserAiMemoryTable,
    UserAiProviderConfigTable,
)
from app.repositories.learning_sql import _delete_owned_row, _get_owned_row, _upsert_owned_row
from app.repositories.memory import InMemoryStore
from app.schemas.common import AiMessageRole, AiReportType, ProposalStatus


class UserAiProviderConfigRecord(BaseModel):
    user_id: UUID
    provider: str = "local"
    base_url: str = ""
    model: str = ""
    encrypted_api_key: str | None = None
    key_version: int = 1
    api_key_last4: str | None = None
    created_at: datetime
    updated_at: datetime


class SqlAiProviderConfigRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: UUID) -> UserAiProviderConfigRecord | None:
        row = self._db.scalar(
            select(UserAiProviderConfigTable).where(UserAiProviderConfigTable.user_id == user_id)
        )
        if row is None:
            return None
        return UserAiProviderConfigRecord(
            user_id=row.user_id,
            provider=row.provider,
            base_url=row.base_url,
            model=row.model,
            encrypted_api_key=row.encrypted_api_key,
            key_version=int(row.key_version),
            api_key_last4=row.api_key_last4,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def save(self, record: UserAiProviderConfigRecord) -> UserAiProviderConfigRecord:
        row = self._db.scalar(
            select(UserAiProviderConfigTable).where(
                UserAiProviderConfigTable.user_id == record.user_id
            )
        )
        data = record.model_dump()
        if row is None:
            row = UserAiProviderConfigTable(**data)
            self._db.add(row)
        else:
            for key, value in data.items():
                setattr(row, key, value)
        self._db.commit()
        self._db.refresh(row)
        return UserAiProviderConfigRecord(
            user_id=row.user_id,
            provider=row.provider,
            base_url=row.base_url,
            model=row.model,
            encrypted_api_key=row.encrypted_api_key,
            key_version=int(row.key_version),
            api_key_last4=row.api_key_last4,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class InMemoryAiProviderConfigRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def get(self, user_id: UUID) -> UserAiProviderConfigRecord | None:
        with self._store.lock:
            rec = self._store.ai_provider_configs.get(user_id)
            return rec.model_copy(deep=True) if isinstance(rec, UserAiProviderConfigRecord) else None

    def save(self, record: UserAiProviderConfigRecord) -> UserAiProviderConfigRecord:
        with self._store.lock:
            stored = record.model_copy(deep=True)
            self._store.ai_provider_configs[record.user_id] = stored
            return stored.model_copy(deep=True)


class AiConversationRecord(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class AiMessageRecord(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID
    role: AiMessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    created_at: datetime


class AiActionProposalRecord(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID
    action_type: str
    title: str
    explanation: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: ProposalStatus = ProposalStatus.pending
    expires_at: datetime | None = None
    execution_result: dict[str, Any] | None = None
    error_message: str | None = None
    idempotency_key: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class AiReportRecord(BaseModel):
    id: UUID
    user_id: UUID
    type: AiReportType
    period_start: datetime
    period_end: datetime
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class UserAiMemoryRecord(BaseModel):
    user_id: UUID
    academic_context: dict[str, Any] = Field(default_factory=dict)
    availability_preferences: dict[str, Any] = Field(default_factory=dict)
    learning_preferences: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    long_term_goals: list[str] = Field(default_factory=list)
    recent_decisions: list[dict[str, Any]] = Field(default_factory=list)
    execution_history: list[dict[str, Any]] = Field(default_factory=list)
    weekly_study_hours: int | None = None
    default_session_minutes: int = 60
    auto_execute_simple_actions: bool = False
    created_at: datetime
    updated_at: datetime


def _to_conversation_record(row: AiConversationTable) -> AiConversationRecord:
    return AiConversationRecord(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_message_record(row: AiMessageTable) -> AiMessageRecord:
    return AiMessageRecord(
        id=row.id,
        user_id=row.user_id,
        conversation_id=row.conversation_id,
        role=AiMessageRole(row.role),
        content=row.content,
        metadata=dict(row.meta or {}),
        idempotency_key=row.idempotency_key,
        created_at=row.created_at,
    )


def _to_proposal_record(row: AiActionProposalTable) -> AiActionProposalRecord:
    return AiActionProposalRecord(
        id=row.id,
        user_id=row.user_id,
        conversation_id=row.conversation_id,
        action_type=row.action_type,
        title=row.title,
        explanation=row.explanation,
        payload=dict(row.payload or {}),
        status=ProposalStatus(row.status),
        expires_at=row.expires_at,
        execution_result=dict(row.execution_result) if row.execution_result is not None else None,
        error_message=row.error_message,
        idempotency_key=row.idempotency_key,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


def _to_report_record(row: AiReportTable) -> AiReportRecord:
    return AiReportRecord(
        id=row.id,
        user_id=row.user_id,
        type=AiReportType(row.type),
        period_start=row.period_start,
        period_end=row.period_end,
        content=row.content,
        metadata=dict(row.meta or {}),
        created_at=row.created_at,
    )


def _to_memory_record(row: UserAiMemoryTable) -> UserAiMemoryRecord:
    return UserAiMemoryRecord(
        user_id=row.user_id,
        academic_context=dict(row.academic_context or {}),
        availability_preferences=dict(row.availability_preferences or {}),
        learning_preferences=dict(row.learning_preferences or {}),
        constraints=[str(item) for item in (row.constraints or [])],
        long_term_goals=[str(item) for item in (row.long_term_goals or [])],
        recent_decisions=list(row.recent_decisions or []),
        execution_history=list(row.execution_history or []),
        weekly_study_hours=row.weekly_study_hours,
        default_session_minutes=int(row.default_session_minutes or 60),
        auto_execute_simple_actions=bool(row.auto_execute_simple_actions),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAiRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_conversations(self, user_id: UUID) -> list[AiConversationRecord]:
        rows = self._db.scalars(
            select(AiConversationTable).where(AiConversationTable.user_id == user_id)
        ).all()
        return [_to_conversation_record(row) for row in rows]

    def get_conversation(self, user_id: UUID, conversation_id: UUID) -> AiConversationRecord | None:
        row = _get_owned_row(self._db, AiConversationTable, conversation_id, user_id)
        return _to_conversation_record(row) if row else None

    def save_conversation(self, record: AiConversationRecord) -> AiConversationRecord:
        row = _upsert_owned_row(
            self._db,
            AiConversationTable,
            record.id,
            record.user_id,
            record.model_dump(),
        )
        return _to_conversation_record(row)

    def delete_conversation(self, user_id: UUID, conversation_id: UUID) -> bool:
        return _delete_owned_row(self._db, AiConversationTable, conversation_id, user_id)

    def list_messages(self, user_id: UUID, conversation_id: UUID) -> list[AiMessageRecord]:
        rows = self._db.scalars(
            select(AiMessageTable).where(
                AiMessageTable.user_id == user_id,
                AiMessageTable.conversation_id == conversation_id,
            )
        ).all()
        return [_to_message_record(row) for row in rows]

    def count_user_messages_since(self, user_id: UUID, cutoff: datetime) -> int:
        return int(
            self._db.scalar(
                select(func.count(AiMessageTable.id)).where(
                    AiMessageTable.user_id == user_id,
                    AiMessageTable.role == AiMessageRole.user.value,
                    AiMessageTable.created_at >= cutoff,
                )
            )
            or 0
        )

    def save_message(self, record: AiMessageRecord) -> AiMessageRecord:
        data = {
            "id": record.id,
            "user_id": record.user_id,
            "conversation_id": record.conversation_id,
            "role": record.role.value,
            "content": record.content,
            "meta": dict(record.metadata),
            "idempotency_key": record.idempotency_key,
            "created_at": record.created_at,
        }
        row = _upsert_owned_row(self._db, AiMessageTable, record.id, record.user_id, data)
        return _to_message_record(row)

    def get_message_by_idempotency_key(
        self,
        user_id: UUID,
        conversation_id: UUID,
        idempotency_key: str,
    ) -> AiMessageRecord | None:
        cleaned = idempotency_key.strip()[:80]
        if not cleaned:
            return None
        row = self._db.scalar(
            select(AiMessageTable)
            .where(
                AiMessageTable.user_id == user_id,
                AiMessageTable.conversation_id == conversation_id,
                AiMessageTable.idempotency_key == cleaned,
            )
            .order_by(AiMessageTable.created_at.desc())
        )
        return _to_message_record(row) if row is not None else None

    def delete_message(self, user_id: UUID, message_id: UUID) -> bool:
        return _delete_owned_row(self._db, AiMessageTable, message_id, user_id)

    def claim_proposal_for_execution(
        self,
        user_id: UUID,
        proposal_id: UUID,
        validated_payload: dict[str, Any],
    ) -> AiActionProposalRecord | None:
        from sqlalchemy import update as sa_update

        res = self._db.execute(
            sa_update(AiActionProposalTable)
            .where(
                AiActionProposalTable.id == proposal_id,
                AiActionProposalTable.user_id == user_id,
                AiActionProposalTable.status == ProposalStatus.pending.value,
            )
            .values(
                status=ProposalStatus.accepted.value,
                payload=validated_payload,
            )
        )
        self._db.commit()
        if int(res.rowcount or 0) != 1:
            return None
        return self.get_proposal(user_id, proposal_id)

    def get_proposal_by_idempotency_key(
        self,
        user_id: UUID,
        idempotency_key: str,
    ) -> AiActionProposalRecord | None:
        cleaned = idempotency_key.strip()[:80]
        if not cleaned:
            return None
        row = self._db.scalar(
            select(AiActionProposalTable).where(
                AiActionProposalTable.user_id == user_id,
                AiActionProposalTable.idempotency_key == cleaned,
            )
        )
        return _to_proposal_record(row) if row is not None else None

    def list_recent_executed_proposals(
        self,
        user_id: UUID,
        *,
        limit: int = 10,
    ) -> list[AiActionProposalRecord]:
        rows = self._db.scalars(
            select(AiActionProposalTable)
            .where(
                AiActionProposalTable.user_id == user_id,
                AiActionProposalTable.status == ProposalStatus.executed.value,
            )
            .order_by(AiActionProposalTable.created_at.desc())
            .limit(max(1, min(limit, 30)))
        ).all()
        return [_to_proposal_record(row) for row in rows]

    def list_proposals(
        self,
        user_id: UUID,
        *,
        conversation_id: UUID | None = None,
    ) -> list[AiActionProposalRecord]:
        stmt = select(AiActionProposalTable).where(AiActionProposalTable.user_id == user_id)
        if conversation_id is not None:
            stmt = stmt.where(AiActionProposalTable.conversation_id == conversation_id)
        rows = self._db.scalars(stmt).all()
        return [_to_proposal_record(row) for row in rows]

    def get_proposal(self, user_id: UUID, proposal_id: UUID) -> AiActionProposalRecord | None:
        row = _get_owned_row(self._db, AiActionProposalTable, proposal_id, user_id)
        return _to_proposal_record(row) if row else None

    def save_proposal(self, record: AiActionProposalRecord) -> AiActionProposalRecord:
        data = record.model_dump()
        data["status"] = record.status.value
        row = _upsert_owned_row(
            self._db, AiActionProposalTable, record.id, record.user_id, data
        )
        return _to_proposal_record(row)

    def list_reports(
        self,
        user_id: UUID,
        *,
        report_type: AiReportType | None = None,
    ) -> list[AiReportRecord]:
        stmt = select(AiReportTable).where(AiReportTable.user_id == user_id)
        if report_type is not None:
            stmt = stmt.where(AiReportTable.type == report_type.value)
        rows = self._db.scalars(stmt).all()
        return [_to_report_record(row) for row in rows]

    def save_report(self, record: AiReportRecord) -> AiReportRecord:
        data = {
            "id": record.id,
            "user_id": record.user_id,
            "type": record.type.value,
            "period_start": record.period_start,
            "period_end": record.period_end,
            "content": record.content,
            "meta": dict(record.metadata),
            "created_at": record.created_at,
        }
        row = _upsert_owned_row(self._db, AiReportTable, record.id, record.user_id, data)
        return _to_report_record(row)


class SqlAiMemoryRepository:
    """Dépôt persistant de la mémoire structurée du copilote IA par utilisateur."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: UUID) -> UserAiMemoryRecord | None:
        row = self._db.scalar(
            select(UserAiMemoryTable).where(UserAiMemoryTable.user_id == user_id)
        )
        return _to_memory_record(row) if row is not None else None

    def get_or_create(self, user_id: UUID) -> UserAiMemoryRecord:
        existing = self.get(user_id)
        if existing is not None:
            return existing
        now = datetime.now(timezone.utc)
        record = UserAiMemoryRecord(
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        return self.save(record)

    def save(self, record: UserAiMemoryRecord) -> UserAiMemoryRecord:
        row = self._db.scalar(
            select(UserAiMemoryTable).where(UserAiMemoryTable.user_id == record.user_id)
        )
        data = record.model_dump()
        if row is None:
            row = UserAiMemoryTable(**data)
            self._db.add(row)
        else:
            for key, value in data.items():
                if key != "created_at":
                    setattr(row, key, value)
        self._db.commit()
        self._db.refresh(row)
        return _to_memory_record(row)

    def patch(
        self,
        user_id: UUID,
        **updates: Any,
    ) -> UserAiMemoryRecord:
        current = self.get_or_create(user_id)
        merged: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        for key, value in updates.items():
            if value is None and key not in ("weekly_study_hours",):
                continue
            if key in ("academic_context", "availability_preferences", "learning_preferences") and isinstance(value, dict):
                base = dict(getattr(current, key) or {})
                base.update(value)
                merged[key] = base
            elif key in ("constraints", "long_term_goals") and isinstance(value, list):
                merged[key] = [str(item).strip() for item in value if str(item).strip()][:30]
            elif hasattr(current, key):
                merged[key] = value
        updated = current.model_copy(update=merged)
        return self.save(updated)

    def append_decision(
        self,
        user_id: UUID,
        decision: dict[str, Any],
    ) -> UserAiMemoryRecord:
        current = self.get_or_create(user_id)
        entries = list(current.recent_decisions or [])
        summary = str(decision.get("summary") or "").strip()
        if summary:
            entries = [e for e in entries if str(e.get("summary") or "").strip() != summary]
        entries.insert(0, decision)
        updated = current.model_copy(
            update={
                "recent_decisions": entries[:25],
                "updated_at": datetime.now(timezone.utc),
            }
        )
        return self.save(updated)

    def append_execution(
        self,
        user_id: UUID,
        execution: dict[str, Any],
    ) -> UserAiMemoryRecord:
        current = self.get_or_create(user_id)
        entries = list(current.execution_history or [])
        entries.insert(0, execution)
        updated = current.model_copy(
            update={
                "execution_history": entries[:40],
                "updated_at": datetime.now(timezone.utc),
            }
        )
        return self.save(updated)
