from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.errors import AppError
from app.models.tables import UserAccountTable
from app.repositories.memory import InMemoryStore


class UserAccountRecord(BaseModel):
    id: UUID
    email: str
    password_hash: str
    is_active: bool = True
    token_version: int = 1
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


def _to_user_record(row: UserAccountTable) -> UserAccountRecord:
    return UserAccountRecord(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        is_active=bool(row.is_active),
        token_version=int(row.token_version),
        last_login_at=row.last_login_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlUserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: UUID) -> UserAccountRecord | None:
        row = self._db.scalar(select(UserAccountTable).where(UserAccountTable.id == user_id))
        return _to_user_record(row) if row else None

    def get_by_email(self, email: str) -> UserAccountRecord | None:
        normalized = email.strip().lower()
        row = self._db.scalar(select(UserAccountTable).where(UserAccountTable.email == normalized))
        return _to_user_record(row) if row else None

    def create(self, record: UserAccountRecord) -> UserAccountRecord:
        normalized_record = record.model_copy(update={"email": record.email.strip().lower()})
        row = UserAccountTable(**normalized_record.model_dump())
        self._db.add(row)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise AppError(
                409,
                "EMAIL_ALREADY_EXISTS",
                "Un compte existe déjà avec cette adresse e-mail.",
            ) from exc
        self._db.refresh(row)
        return _to_user_record(row)

    def save(self, record: UserAccountRecord) -> UserAccountRecord:
        row = self._db.scalar(select(UserAccountTable).where(UserAccountTable.id == record.id))
        if row is None:
            return self.create(record)
        data = record.model_copy(update={"email": record.email.strip().lower()}).model_dump()
        for key, value in data.items():
            setattr(row, key, value)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise AppError(
                409,
                "EMAIL_ALREADY_EXISTS",
                "Un compte existe déjà avec cette adresse e-mail.",
            ) from exc
        self._db.refresh(row)
        return _to_user_record(row)


class InMemoryUserRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def get_by_id(self, user_id: UUID) -> UserAccountRecord | None:
        with self._store.lock:
            rec = self._store.users.get(user_id)
            return rec.model_copy(deep=True) if isinstance(rec, UserAccountRecord) else None

    def get_by_email(self, email: str) -> UserAccountRecord | None:
        normalized = email.strip().lower()
        with self._store.lock:
            for rec in self._store.users.values():
                if isinstance(rec, UserAccountRecord) and rec.email == normalized:
                    return rec.model_copy(deep=True)
            return None

    def create(self, record: UserAccountRecord) -> UserAccountRecord:
        normalized = record.model_copy(update={"email": record.email.strip().lower()})
        with self._store.lock:
            for existing in self._store.users.values():
                if isinstance(existing, UserAccountRecord) and existing.email == normalized.email:
                    raise AppError(
                        409,
                        "EMAIL_ALREADY_EXISTS",
                        "Un compte existe déjà avec cette adresse e-mail.",
                    )
            self._store.users[normalized.id] = normalized.model_copy(deep=True)
            return normalized.model_copy(deep=True)

    def save(self, record: UserAccountRecord) -> UserAccountRecord:
        normalized = record.model_copy(update={"email": record.email.strip().lower()})
        with self._store.lock:
            if normalized.id not in self._store.users:
                return self.create(normalized)
            self._store.users[normalized.id] = normalized.model_copy(deep=True)
            return normalized.model_copy(deep=True)
