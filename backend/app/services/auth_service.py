from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID, uuid4
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_password_constant_time,
)
from app.repositories.auth_sql import (
    AuthRefreshSessionRecord,
    InMemoryAuthSessionRepository,
    InMemoryUserRepository,
    SqlAuthSessionRepository,
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
from app.services.rate_limiter import (
    DEFAULT_ACCOUNT_MAX_FAILURES,
    DEFAULT_IP_MAX_FAILURES,
    DEFAULT_WINDOW_SECONDS,
    REGISTER_IP_MAX_ATTEMPTS,
    REGISTER_WINDOW_SECONDS,
    PersistentRateLimiter,
)

# Conservé pour compatibilité d'import éventuelle ; le TTL par défaut vient de Settings
ACCOUNT_TOKEN_TTL_SECONDS = 900
LOGIN_MAX_FAILED_ATTEMPTS = DEFAULT_ACCOUNT_MAX_FAILURES
LOGIN_WINDOW_SECONDS = DEFAULT_WINDOW_SECONDS


class AuthService:
    """Gère l'inscription, la connexion, les sessions refresh, la révocation et l'isolation des comptes."""

    def __init__(
        self,
        *,
        user_repo: SqlUserRepository | InMemoryUserRepository,
        profile_service: ProfileService,
        settings: Settings,
        session_repo: SqlAuthSessionRepository | InMemoryAuthSessionRepository | None = None,
        rate_limiter: PersistentRateLimiter | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._profile_service = profile_service
        self._settings = settings
        self._session_repo = session_repo
        self._rate_limiter = rate_limiter or PersistentRateLimiter(db=None, settings=settings)

    def _hash_ip(self, client_ip: str) -> str:
        salt = (self._settings.app_secret_key or "studyos").encode("utf-8")
        return hashlib.sha256(salt + b"|ip|" + client_ip.encode("utf-8")).hexdigest()

    def _issue_tokens(
        self,
        *,
        user_id: UUID,
        email: str,
        token_version: int,
        user_agent: str | None = None,
        client_ip: str = "unknown",
        session_id: UUID | None = None,
        now_utc: datetime | None = None,
    ) -> tuple[str, int, str | None]:
        now = now_utc or datetime.now(timezone.utc)
        access_ttl = int(self._settings.access_token_ttl_seconds or ACCOUNT_TOKEN_TTL_SECONDS)
        access_token = create_access_token(
            user_id,
            self._settings,
            token_version=token_version,
            email=email,
            expires_in_seconds=access_ttl,
        )
        raw_refresh: str | None = None
        if self._session_repo is not None:
            raw_refresh = secrets.token_urlsafe(48)
            refresh_ttl = int(self._settings.refresh_token_ttl_seconds or (14 * 86400))
            rec = AuthRefreshSessionRecord(
                id=session_id or uuid4(),
                user_id=user_id,
                token_hash=hash_refresh_token(raw_refresh),
                token_version=token_version,
                expires_at=now + timedelta(seconds=refresh_ttl),
                revoked_at=None,
                replaced_by_id=None,
                user_agent=(user_agent or "")[:255] or None,
                ip_hash=self._hash_ip(client_ip),
                created_at=now,
            )
            self._session_repo.create_session(rec)
        return access_token, access_ttl, raw_refresh

    def register(
        self,
        payload: RegisterRequest,
        *,
        client_ip: str = "unknown",
        user_agent: str | None = None,
    ) -> tuple[AuthTokenResponse, str | None]:
        now = datetime.now(timezone.utc)
        reg_count = self._rate_limiter.count_all_in_window(
            scope="register",
            client_ip=client_ip,
            now_utc=now,
            window_seconds=REGISTER_WINDOW_SECONDS,
        )
        if reg_count >= REGISTER_IP_MAX_ATTEMPTS:
            raise AppError(
                429,
                "RATE_LIMITED",
                "Trop de créations de compte depuis cette origine. Patientez avant de réessayer.",
            )

        existing = self._user_repo.get_by_email(payload.email)
        if existing is not None:
            self._rate_limiter.record_attempt(
                scope="register",
                account_key=payload.email,
                client_ip=client_ip,
                succeeded=False,
                now_utc=now,
            )
            raise AppError(
                409,
                "EMAIL_ALREADY_EXISTS",
                "Un compte existe déjà avec cette adresse e-mail.",
            )

        user_id = uuid4()
        account = UserAccountRecord(
            id=user_id,
            email=payload.email,
            password_hash=hash_password(payload.password),
            is_active=True,
            email_verified=False,
            email_verified_at=None,
            token_version=1,
            last_login_at=now,
            created_at=now,
            updated_at=now,
        )
        created_account = self._user_repo.create(account)
        self._rate_limiter.record_attempt(
            scope="register",
            account_key=created_account.email,
            client_ip=client_ip,
            succeeded=True,
            now_utc=now,
        )

        self._profile_service.get_or_create_record(created_account.id)
        profile_patch = ProfileUpdate(
            display_name=payload.display_name,
            timezone=payload.timezone or self._settings.default_timezone,
            preferences={"theme": "system"},
        )
        profile = self._profile_service.update_profile(created_account.id, profile_patch)

        token, access_ttl, raw_refresh = self._issue_tokens(
            user_id=created_account.id,
            email=created_account.email,
            token_version=created_account.token_version,
            user_agent=user_agent,
            client_ip=client_ip,
            now_utc=now,
        )
        return (
            AuthTokenResponse(
                access_token=token,
                expires_in=access_ttl,
                email=created_account.email,
                profile=profile,
            ),
            raw_refresh,
        )

    def login(
        self,
        payload: LoginRequest,
        *,
        client_ip: str = "unknown",
        user_agent: str | None = None,
    ) -> tuple[AuthTokenResponse, str | None]:
        now = datetime.now(timezone.utc)
        self._rate_limiter.assert_allowed(
            scope="login",
            account_key=payload.email,
            client_ip=client_ip,
            now_utc=now,
            window_seconds=LOGIN_WINDOW_SECONDS,
            max_account_failures=LOGIN_MAX_FAILED_ATTEMPTS,
            max_ip_failures=DEFAULT_IP_MAX_FAILURES,
        )

        account = self._user_repo.get_by_email(payload.email)
        password_valid = verify_password_constant_time(
            payload.password,
            account.password_hash if account is not None else None,
        )
        if account is None or not account.is_active or not password_valid:
            self._rate_limiter.record_attempt(
                scope="login",
                account_key=payload.email,
                client_ip=client_ip,
                succeeded=False,
                now_utc=now,
            )
            raise AppError(
                401,
                "INVALID_CREDENTIALS",
                "Adresse e-mail ou mot de passe incorrect.",
            )

        self._rate_limiter.record_attempt(
            scope="login",
            account_key=payload.email,
            client_ip=client_ip,
            succeeded=True,
            now_utc=now,
        )
        updated_account = self._user_repo.save(
            account.model_copy(
                update={
                    "last_login_at": now,
                    "updated_at": now,
                }
            )
        )
        profile = self._profile_service.get_profile(updated_account.id)
        token, access_ttl, raw_refresh = self._issue_tokens(
            user_id=updated_account.id,
            email=updated_account.email,
            token_version=updated_account.token_version,
            user_agent=user_agent,
            client_ip=client_ip,
            now_utc=now,
        )
        return (
            AuthTokenResponse(
                access_token=token,
                expires_in=access_ttl,
                email=updated_account.email,
                profile=profile,
            ),
            raw_refresh,
        )

    def refresh_session(
        self,
        raw_refresh_token: str | None,
        *,
        client_ip: str = "unknown",
        user_agent: str | None = None,
    ) -> tuple[AuthTokenResponse, str | None]:
        if not raw_refresh_token or self._session_repo is None:
            raise AppError(401, "UNAUTHORIZED", "Session expirée. Veuillez vous reconnecter.")

        now = datetime.now(timezone.utc)
        rec = self._session_repo.get_by_token_hash(hash_refresh_token(raw_refresh_token))
        if rec is None:
            raise AppError(401, "UNAUTHORIZED", "Session expirée ou invalide.")

        # Détection de réutilisation d'un jeton déjà tourné ou révoqué
        if rec.revoked_at is not None:
            self.logout_all_sessions(rec.user_id)
            raise AppError(
                401,
                "SESSION_REVOKED",
                "Réutilisation de session détectée : toutes les sessions ont été révoquées par sécurité.",
            )

        if rec.expires_at <= now:
            self._session_repo.revoke_session(rec.id, revoked_at=now)
            raise AppError(401, "UNAUTHORIZED", "Session expirée. Veuillez vous reconnecter.")

        account = self._user_repo.get_by_id(rec.user_id)
        if (
            account is None
            or not account.is_active
            or account.token_version != rec.token_version
        ):
            self._session_repo.revoke_session(rec.id, revoked_at=now)
            raise AppError(401, "UNAUTHORIZED", "Session révoquée. Veuillez vous reconnecter.")

        next_session_id = uuid4()
        revoked_ok = self._session_repo.revoke_session(
            rec.id,
            revoked_at=now,
            replaced_by_id=next_session_id,
        )
        if not revoked_ok:
            self.logout_all_sessions(rec.user_id)
            raise AppError(401, "SESSION_REVOKED", "Session révoquée par sécurité.")

        profile = self._profile_service.get_profile(account.id)
        token, access_ttl, next_raw_refresh = self._issue_tokens(
            user_id=account.id,
            email=account.email,
            token_version=account.token_version,
            user_agent=user_agent,
            client_ip=client_ip,
            session_id=next_session_id,
            now_utc=now,
        )
        return (
            AuthTokenResponse(
                access_token=token,
                expires_in=access_ttl,
                email=account.email,
                profile=profile,
            ),
            next_raw_refresh,
        )

    def change_password(
        self,
        user_id: UUID,
        payload: ChangePasswordRequest,
        *,
        client_ip: str = "unknown",
        user_agent: str | None = None,
    ) -> tuple[AuthTokenResponse, str | None]:
        now = datetime.now(timezone.utc)
        self._rate_limiter.assert_allowed(
            scope="change_password",
            account_key=str(user_id),
            client_ip=client_ip,
            now_utc=now,
            window_seconds=LOGIN_WINDOW_SECONDS,
            max_account_failures=8,
            max_ip_failures=20,
        )

        account = self._user_repo.get_by_id(user_id)
        if account is None or not account.is_active:
            raise AppError(
                404,
                "NOT_FOUND",
                "Aucun compte mot de passe local trouvé pour cette session.",
            )

        if not verify_password(payload.current_password, account.password_hash):
            self._rate_limiter.record_attempt(
                scope="change_password",
                account_key=str(user_id),
                client_ip=client_ip,
                succeeded=False,
                now_utc=now,
            )
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

        self._rate_limiter.record_attempt(
            scope="change_password",
            account_key=str(user_id),
            client_ip=client_ip,
            succeeded=True,
            now_utc=now,
        )

        updated = self._user_repo.save(
            account.model_copy(
                update={
                    "password_hash": hash_password(payload.new_password),
                    "token_version": account.token_version + 1,
                    "updated_at": now,
                }
            )
        )
        if self._session_repo is not None:
            self._session_repo.revoke_all_for_user(updated.id, revoked_at=now)

        profile = self._profile_service.get_profile(updated.id)
        token, access_ttl, raw_refresh = self._issue_tokens(
            user_id=updated.id,
            email=updated.email,
            token_version=updated.token_version,
            user_agent=user_agent,
            client_ip=client_ip,
            now_utc=now,
        )
        return (
            AuthTokenResponse(
                access_token=token,
                expires_in=access_ttl,
                email=updated.email,
                profile=profile,
            ),
            raw_refresh,
        )

    def logout_session(
        self,
        user_id: UUID,
        *,
        raw_refresh_token: str | None = None,
        all_sessions: bool = True,
    ) -> None:
        now = datetime.now(timezone.utc)
        if not all_sessions and raw_refresh_token and self._session_repo is not None:
            rec = self._session_repo.get_by_token_hash(hash_refresh_token(raw_refresh_token))
            if rec is not None and rec.user_id == user_id:
                self._session_repo.revoke_session(rec.id, revoked_at=now)
                return

        self.logout_all_sessions(user_id)

    def logout_all_sessions(self, user_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        if self._session_repo is not None:
            self._session_repo.revoke_all_for_user(user_id, revoked_at=now)
            self._session_repo.record_token_revocation(user_id, now)

        account = self._user_repo.get_by_id(user_id)
        if account is None:
            return
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
                email_verified=False,
                can_change_password=False,
                password_reset_mode="external_provider",
                last_login_at=None,
                created_at=profile.created_at,
                profile=profile,
            )
        return AuthAccountResponse(
            id=account.id,
            email=account.email,
            auth_provider="password",
            has_password_account=True,
            email_verified=account.email_verified,
            can_change_password=True,
            password_reset_mode="unavailable_no_mailer",
            last_login_at=account.last_login_at,
            created_at=account.created_at,
            profile=profile,
        )
