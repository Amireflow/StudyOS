from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.tables import (
    AiActionProposalTable,
    AiConversationTable,
    AiMessageTable,
    AiReportTable,
)
from app.repositories.learning_sql import _delete_owned_row, _get_owned_row, _upsert_owned_row
from app.schemas.common import AiMessageRole, AiReportType, ProposalStatus


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

    def save_message(self, record: AiMessageRecord) -> AiMessageRecord:
        data = {
            "id": record.id,
            "user_id": record.user_id,
            "conversation_id": record.conversation_id,
            "role": record.role.value,
            "content": record.content,
            "meta": dict(record.metadata),
            "created_at": record.created_at,
        }
        row = _upsert_owned_row(self._db, AiMessageTable, record.id, record.user_id, data)
        return _to_message_record(row)

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
