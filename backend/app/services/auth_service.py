from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import UUID, uuid4
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.auth_sql import (
    InMemoryUserRepository,
    SqlUserRepository,
    UserAccountRecord,
)
from app.schemas.auth import (
    AuthAccountResponse,
    AuthTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
)
from app.schemas.profile import ProfileUpdate
from app.services.profile_service import ProfileService

ACCOUNT_TOKEN_TTL_SECONDS = 7 * 86400
LOGIN_MAX_FAILED_ATTEMPTS = 10
LOGIN_WINDOW_SECONDS = 300


class LoginRateLimiter:
    """Protection simple en mémoire contre les attaques par force brute par adresse e-mail."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._attempts: dict[str, list[datetime]] = {}

    def assert_allowed(self, email: str, now_utc: datetime) -> None:
        cutoff = now_utc - timedelta(seconds=LOGIN_WINDOW_SECONDS)
        with self._lock:
            recent = [ts for ts in self._attempts.get(email, []) if ts >= cutoff]
            self._attempts[email] = recent
            if len(recent) >= LOGIN_MAX_FAILED_ATTEMPTS:
                raise AppError(
                    429,
                    "RATE_LIMITED",
                    "Trop de tentatives de connexion échouées. Patientez quelques minutes avant de réessayer.",
                )

    def record_failure(self, email: str, now_utc: datetime) -> None:
        cutoff = now_utc - timedelta(seconds=LOGIN_WINDOW_SECONDS)
        with self._lock:
            recent = [ts for ts in self._attempts.get(email, []) if ts >= cutoff]
            recent.append(now_utc)
            self._attempts[email] = recent

    def reset(self, email: str) -> None:
        with self._lock:
            self._attempts.pop(email, None)


class AuthService:
    """Gère l'inscription, la connexion, le mot de passe et l'isolation des comptes."""

    def __init__(
        self,
        *,
        user_repo: SqlUserRepository | InMemoryUserRepository,
        profile_service: ProfileService,
        settings: Settings,
        rate_limiter: LoginRateLimiter | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._profile_service = profile_service
        self._settings = settings
        self._rate_limiter = rate_limiter or LoginRateLimiter()

    def register(self, payload: RegisterRequest) -> AuthTokenResponse:
        existing = self._user_repo.get_by_email(payload.email)
        if existing is not None:
            raise AppError(
                409,
                "EMAIL_ALREADY_EXISTS",
                "Un compte existe déjà avec cette adresse e-mail.",
            )

        now = datetime.now(timezone.utc)
        user_id = uuid4()
        account = UserAccountRecord(
            id=user_id,
            email=payload.email,
            password_hash=hash_password(payload.password),
            is_active=True,
            token_version=1,
            last_login_at=now,
            created_at=now,
            updated_at=now,
        )
        created_account = self._user_repo.create(account)

        self._profile_service.get_or_create_record(created_account.id)
        profile_patch = ProfileUpdate(
            display_name=payload.display_name,
            timezone=payload.timezone or self._settings.default_timezone,
            preferences={"theme": "system"},
        )
        profile = self._profile_service.update_profile(created_account.id, profile_patch)

        token = create_access_token(
            created_account.id,
            self._settings,
            token_version=created_account.token_version,
            email=created_account.email,
            expires_in_seconds=ACCOUNT_TOKEN_TTL_SECONDS,
        )
        return AuthTokenResponse(
            access_token=token,
            expires_in=ACCOUNT_TOKEN_TTL_SECONDS,
            email=created_account.email,
            profile=profile,
        )

    def login(self, payload: LoginRequest) -> AuthTokenResponse:
        now = datetime.now(timezone.utc)
        self._rate_limiter.assert_allowed(payload.email, now)

        account = self._user_repo.get_by_email(payload.email)
        if account is None or not account.is_active or not verify_password(payload.password, account.password_hash):
            self._rate_limiter.record_failure(payload.email, now)
            raise AppError(
                401,
                "INVALID_CREDENTIALS",
                "Adresse e-mail ou mot de passe incorrect.",
            )

        self._rate_limiter.reset(payload.email)
        updated_account = self._user_repo.save(
            account.model_copy(
                update={
                    "last_login_at": now,
                    "updated_at": now,
                }
            )
        )
        profile = self._profile_service.get_profile(updated_account.id)
        token = create_access_token(
            updated_account.id,
            self._settings,
            token_version=updated_account.token_version,
            email=updated_account.email,
            expires_in_seconds=ACCOUNT_TOKEN_TTL_SECONDS,
        )
        return AuthTokenResponse(
            access_token=token,
            expires_in=ACCOUNT_TOKEN_TTL_SECONDS,
            email=updated_account.email,
            profile=profile,
        )

    def change_password(
        self,
        user_id: UUID,
        payload: ChangePasswordRequest,
    ) -> AuthTokenResponse:
        account = self._user_repo.get_by_id(user_id)
        if account is None or not account.is_active:
            raise AppError(
                404,
                "NOT_FOUND",
                "Aucun compte mot de passe local trouvé pour cette session.",
            )

        if not verify_password(payload.current_password, account.password_hash):
            raise AppError(
                401,
                "INVALID_CREDENTIALS",
                "Le mot de passe actuel est incorrect.",
            )

        if payload.current_password == payload.new_password:
            raise AppError(
                400,
                "VALIDATION_ERROR",
                "Le nouveau mot de passe doit être différent de l’ancien.",
            )

        now = datetime.now(timezone.utc)
        updated = self._user_repo.save(
            account.model_copy(
                update={
                    "password_hash": hash_password(payload.new_password),
                    "token_version": account.token_version + 1,
                    "updated_at": now,
                }
            )
        )
        profile = self._profile_service.get_profile(updated.id)
        token = create_access_token(
            updated.id,
            self._settings,
            token_version=updated.token_version,
            email=updated.email,
            expires_in_seconds=ACCOUNT_TOKEN_TTL_SECONDS,
        )
        return AuthTokenResponse(
            access_token=token,
            expires_in=ACCOUNT_TOKEN_TTL_SECONDS,
            email=updated.email,
            profile=profile,
        )

    def logout_all_sessions(self, user_id: UUID) -> None:
        account = self._user_repo.get_by_id(user_id)
        if account is None:
            return
        now = datetime.now(timezone.utc)
        self._user_repo.save(
            account.model_copy(
                update={
                    "token_version": account.token_version + 1,
                    "updated_at": now,
                }
            )
        )

    def get_account_info(self, user_id: UUID) -> AuthAccountResponse:
        profile = self._profile_service.get_profile(user_id)
        account = self._user_repo.get_by_id(user_id)
        if account is None:
            return AuthAccountResponse(
                id=profile.id,
                email=None,
                auth_provider="external",
                has_password_account=False,
                last_login_at=None,
                created_at=profile.created_at,
                profile=profile,
            )
        return AuthAccountResponse(
            id=account.id,
            email=account.email,
            auth_provider="password",
            has_password_account=True,
            last_login_at=account.last_login_at,
            created_at=account.created_at,
            profile=profile,
        )
