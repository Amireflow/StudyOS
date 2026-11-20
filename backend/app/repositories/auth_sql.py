from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.errors import AppError
from app.models.tables import (
    AuthRefreshSessionTable,
    AuthTokenRevocationTable,
    UserAccountTable,
)
from app.repositories.memory import InMemoryStore


class UserAccountRecord(BaseModel):
    id: UUID
    email: str
    password_hash: str
    is_active: bool = True
    email_verified: bool = False
    email_verified_at: datetime | None = None
    token_version: int = 1
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AuthRefreshSessionRecord(BaseModel):
    id: UUID
    user_id: UUID
    token_hash: str
    token_version: int = 1
    expires_at: datetime
    revoked_at: datetime | None = None
    replaced_by_id: UUID | None = None
    user_agent: str | None = None
    ip_hash: str | None = None
    created_at: datetime


def _to_user_record(row: UserAccountTable) -> UserAccountRecord:
    return UserAccountRecord(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        is_active=bool(row.is_active),
        email_verified=bool(getattr(row, "email_verified", False)),
        email_verified_at=getattr(row, "email_verified_at", None),
        token_version=int(row.token_version),
        last_login_at=row.last_login_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_refresh_session_record(row: AuthRefreshSessionTable) -> AuthRefreshSessionRecord:
    return AuthRefreshSessionRecord(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        token_version=int(row.token_version),
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        replaced_by_id=row.replaced_by_id,
        user_agent=row.user_agent,
        ip_hash=row.ip_hash,
        created_at=row.created_at,
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


class SqlAuthSessionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_session(self, record: AuthRefreshSessionRecord) -> AuthRefreshSessionRecord:
        row = AuthRefreshSessionTable(**record.model_dump())
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return _to_refresh_session_record(row)

    def get_by_token_hash(self, token_hash: str) -> AuthRefreshSessionRecord | None:
        row = self._db.scalar(
            select(AuthRefreshSessionTable).where(
                AuthRefreshSessionTable.token_hash == token_hash
            )
        )
        return _to_refresh_session_record(row) if row else None

    def revoke_session(
        self,
        session_id: UUID,
        *,
        revoked_at: datetime,
        replaced_by_id: UUID | None = None,
    ) -> bool:
        result = self._db.execute(
            update(AuthRefreshSessionTable)
            .where(
                AuthRefreshSessionTable.id == session_id,
                AuthRefreshSessionTable.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at, replaced_by_id=replaced_by_id)
        )
        self._db.commit()
        return int(result.rowcount or 0) > 0

    def revoke_all_for_user(self, user_id: UUID, *, revoked_at: datetime) -> None:
        self._db.execute(
            update(AuthRefreshSessionTable)
            .where(
                AuthRefreshSessionTable.user_id == user_id,
                AuthRefreshSessionTable.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        self._db.commit()

    def record_token_revocation(self, user_id: UUID, revoked_before: datetime) -> None:
        row = self._db.scalar(
            select(AuthTokenRevocationTable).where(AuthTokenRevocationTable.user_id == user_id)
        )
        now = datetime.now(timezone.utc)
        if row is None:
            self._db.add(
                AuthTokenRevocationTable(
                    user_id=user_id,
                    revoked_before=revoked_before,
                    updated_at=now,
                )
            )
        else:
            row.revoked_before = revoked_before
            row.updated_at = now
        self._db.commit()

    def get_revoked_before(self, user_id: UUID) -> datetime | None:
        row = self._db.scalar(
            select(AuthTokenRevocationTable).where(AuthTokenRevocationTable.user_id == user_id)
        )
        return row.revoked_before if row else None


class InMemoryAuthSessionRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def create_session(self, record: AuthRefreshSessionRecord) -> AuthRefreshSessionRecord:
        with self._store.lock:
            stored = record.model_copy(deep=True)
            self._store.auth_refresh_sessions[record.id] = stored
            return stored.model_copy(deep=True)

    def get_by_token_hash(self, token_hash: str) -> AuthRefreshSessionRecord | None:
        with self._store.lock:
            for item in self._store.auth_refresh_sessions.values():
                if isinstance(item, AuthRefreshSessionRecord) and item.token_hash == token_hash:
                    return item.model_copy(deep=True)
            return None

    def revoke_session(
        self,
        session_id: UUID,
        *,
        revoked_at: datetime,
        replaced_by_id: UUID | None = None,
    ) -> bool:
        with self._store.lock:
            item = self._store.auth_refresh_sessions.get(session_id)
            if not isinstance(item, AuthRefreshSessionRecord) or item.revoked_at is not None:
                return False
            self._store.auth_refresh_sessions[session_id] = item.model_copy(
                update={"revoked_at": revoked_at, "replaced_by_id": replaced_by_id}
            )
            return True

    def revoke_all_for_user(self, user_id: UUID, *, revoked_at: datetime) -> None:
        with self._store.lock:
            for sid, item in list(self._store.auth_refresh_sessions.items()):
                if (
                    isinstance(item, AuthRefreshSessionRecord)
                    and item.user_id == user_id
                    and item.revoked_at is None
                ):
                    self._store.auth_refresh_sessions[sid] = item.model_copy(
                        update={"revoked_at": revoked_at}
                    )

    def record_token_revocation(self, user_id: UUID, revoked_before: datetime) -> None:
        with self._store.lock:
            self._store.auth_token_revocations[user_id] = revoked_before

    def get_revoked_before(self, user_id: UUID) -> datetime | None:
        with self._store.lock:
            return self._store.auth_token_revocations.get(user_id)
