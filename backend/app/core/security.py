from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
from typing import Any
from uuid import UUID
import jwt
from fastapi import Depends, Header, Request
from jwt import InvalidTokenError, PyJWKClient, PyJWKClientError
from app.core.config import Settings, get_settings
from app.core.errors import AppError

LOCAL_TOKEN_ISSUER = "amireflow-local"
AUTH_TOKEN_ISSUER = "amireflow-auth"
SCRYPT_N = 32768
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32

_COMMON_WEAK_PASSWORDS = {
    "password",
    "password1",
    "password123",
    "12345678",
    "123456789",
    "1234567890",
    "azerty123",
    "azertyui",
    "qwerty123",
    "qwertyui",
    "admin123",
    "letmein1",
    "welcome1",
    "amireflow",
}


@dataclass(frozen=True)
class VerifiedTokenClaims:
    user_id: UUID
    issuer: str | None = None
    token_version: int | None = None
    issued_at: datetime | None = None


def get_app_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if isinstance(settings, Settings):
        return settings
    return get_settings()


def validate_password_policy(password: str) -> str:
    if len(password) < 8 or len(password) > 128:
        raise ValueError("Le mot de passe doit contenir entre 8 et 128 caractères.")
    if password.strip().lower() in _COMMON_WEAK_PASSWORDS:
        raise ValueError("Ce mot de passe est trop courant. Choisissez une combinaison plus sûre.")
    has_letter = bool(re.search(r"[A-Za-zÀ-ÿ]", password))
    has_digit = bool(re.search(r"[0-9]", password))
    if not (has_letter and has_digit):
        raise ValueError(
            "Le mot de passe doit contenir au moins une lettre et un chiffre."
        )
    return password


def hash_password(password: str, *, scrypt_n: int = SCRYPT_N) -> str:
    salt = secrets.token_bytes(16)
    maxmem = max(64 * 1024 * 1024, 128 * scrypt_n * SCRYPT_R * 2)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=scrypt_n,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=maxmem,
        dklen=SCRYPT_DKLEN,
    )
    return f"scrypt${scrypt_n}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${derived.hex()}"


_DUMMY_PASSWORD_HASH = hash_password("StudyOS_Dummy_ConstantTime_918273!")


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, n_str, r_str, p_str, salt_hex, dk_hex = stored_hash.split("$", 5)
        if algorithm != "scrypt":
            return False
        n_val = int(n_str)
        r_val = int(r_str)
        p_val = int(p_str)
        salt = bytes.fromhex(salt_hex)
        expected_dk = bytes.fromhex(dk_hex)
    except (ValueError, TypeError):
        return False

    if not expected_dk:
        return False

    maxmem = max(64 * 1024 * 1024, 128 * n_val * r_val * 2)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n_val,
        r=r_val,
        p=p_val,
        maxmem=maxmem,
        dklen=len(expected_dk),
    )
    return hmac.compare_digest(derived, expected_dk)


def verify_password_constant_time(password: str, stored_hash: str | None) -> bool:
    """Égalise le coût scrypt même lorsqu'aucun compte ne correspond (anti-énumération)."""
    if not stored_hash:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        return False
    return verify_password(password, stored_hash)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_local_access_token(
    user_id: UUID,
    settings: Settings,
    expires_in_seconds: int = 86400,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iss": LOCAL_TOKEN_ISSUER,
        "aud": settings.auth_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def create_access_token(
    user_id: UUID,
    settings: Settings,
    *,
    token_version: int = 1,
    email: str | None = None,
    expires_in_seconds: int | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    ttl = int(expires_in_seconds or settings.access_token_ttl_seconds or 900)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iss": AUTH_TOKEN_ISSUER,
        "aud": settings.auth_audience,
        "tv": int(token_version),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    if email:
        payload["email"] = email
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def _extract_issued_at(payload: dict[str, Any]) -> datetime | None:
    raw_iat = payload.get("iat")
    if isinstance(raw_iat, (int, float)) and not isinstance(raw_iat, bool):
        return datetime.fromtimestamp(float(raw_iat), tz=timezone.utc)
    return None


def decode_bearer_token(
    token: str,
    settings: Settings,
    jwks_client: Any = None,
) -> VerifiedTokenClaims:
    """
    Vérifie un jeton Bearer (compte applicatif HS256 `amireflow-auth`, JWKS RS256/ES256
    Supabase, ou en mode local `amireflow-local` et `dev:<uuid>` si `allow_local_dev_auth=True`).
    """
    if settings.app_env == "local" and settings.allow_local_dev_auth and token.startswith("dev:"):
        raw_uuid = token.removeprefix("dev:").strip()
        try:
            return VerifiedTokenClaims(user_id=UUID(raw_uuid), issuer="dev")
        except ValueError as exc:
            raise AppError(
                401,
                "UNAUTHORIZED",
                "Jeton d’authentification invalide ou expiré.",
            ) from exc

    try:
        unverified_header = jwt.get_unverified_header(token)
    except InvalidTokenError:
        unverified_header = {}

    if unverified_header.get("alg") == "HS256":
        try:
            payload = jwt.decode(
                token,
                settings.app_secret_key,
                algorithms=["HS256"],
                audience=settings.auth_audience or None,
                options={
                    "verify_exp": True,
                    "verify_iss": False,
                    "require": ["sub", "exp", "iss"],
                    "verify_aud": bool(settings.auth_audience),
                },
            )
            issuer = str(payload.get("iss") or "")
            issued_at = _extract_issued_at(payload)
            if issuer == AUTH_TOKEN_ISSUER:
                raw_tv = payload.get("tv")
                if isinstance(raw_tv, bool) or not isinstance(raw_tv, int) or raw_tv < 1:
                    raise ValueError("Version de session invalide.")
                return VerifiedTokenClaims(
                    user_id=UUID(str(payload["sub"])),
                    issuer=AUTH_TOKEN_ISSUER,
                    token_version=raw_tv,
                    issued_at=issued_at,
                )
            if issuer == LOCAL_TOKEN_ISSUER and settings.app_env == "local":
                return VerifiedTokenClaims(
                    user_id=UUID(str(payload["sub"])),
                    issuer=LOCAL_TOKEN_ISSUER,
                    issued_at=issued_at,
                )
            raise ValueError("Émetteur de jeton non autorisé.")
        except (InvalidTokenError, ValueError, KeyError) as exc:
            raise AppError(
                401,
                "UNAUTHORIZED",
                "Jeton d’authentification invalide ou expiré.",
            ) from exc

    if settings.auth_jwks_url or jwks_client is not None:
        client = jwks_client or PyJWKClient(settings.auth_jwks_url)
        try:
            signing_key = client.get_signing_key_from_jwt(token)
            decode_options: dict[str, Any] = {
                "verify_exp": True,
                "require": ["sub", "exp"],
                "verify_aud": bool(settings.auth_audience),
            }
            decode_kwargs: dict[str, Any] = {
                "algorithms": ["RS256", "ES256"],
                "options": decode_options,
            }
            if settings.auth_issuer:
                decode_kwargs["issuer"] = settings.auth_issuer
            if settings.auth_audience:
                decode_kwargs["audience"] = settings.auth_audience

            payload = jwt.decode(token, signing_key.key, **decode_kwargs)
            return VerifiedTokenClaims(
                user_id=UUID(str(payload["sub"])),
                issuer=str(payload.get("iss") or "") or None,
                issued_at=_extract_issued_at(payload),
            )
        except (PyJWKClientError, InvalidTokenError, ValueError, KeyError) as exc:
            raise AppError(
                401,
                "UNAUTHORIZED",
                "Jeton d’authentification invalide ou expiré.",
            ) from exc

    raise AppError(401, "UNAUTHORIZED", "Jeton d’authentification invalide ou expiré.")


def verify_bearer_token(
    token: str,
    settings: Settings,
    jwks_client: Any = None,
) -> UUID:
    return decode_bearer_token(token, settings, jwks_client=jwks_client).user_id


def _assert_account_session_valid(request: Request, claims: VerifiedTokenClaims) -> None:
    if claims.issuer in ("dev", LOCAL_TOKEN_ISSUER):
        return

    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is not None:
        from app.models.tables import AuthTokenRevocationTable, UserAccountTable

        with session_factory() as db:
            if claims.issuer == AUTH_TOKEN_ISSUER:
                row = db.get(UserAccountTable, claims.user_id)
                if (
                    row is None
                    or not row.is_active
                    or row.token_version != claims.token_version
                ):
                    raise AppError(
                        401,
                        "UNAUTHORIZED",
                        "Session expirée ou révoquée. Veuillez vous reconnecter.",
                    )
            else:
                rev = db.get(AuthTokenRevocationTable, claims.user_id)
                if rev is not None and (
                    claims.issued_at is None or claims.issued_at <= rev.revoked_before
                ):
                    raise AppError(
                        401,
                        "UNAUTHORIZED",
                        "Session expirée ou révoquée. Veuillez vous reconnecter.",
                    )
        return

    store = getattr(request.app.state, "store", None)
    if store is not None:
        with store.lock:
            if claims.issuer == AUTH_TOKEN_ISSUER:
                user = getattr(store, "users", {}).get(claims.user_id)
                if (
                    user is None
                    or not getattr(user, "is_active", False)
                    or getattr(user, "token_version", None) != claims.token_version
                ):
                    raise AppError(
                        401,
                        "UNAUTHORIZED",
                        "Session expirée ou révoquée. Veuillez vous reconnecter.",
                    )
            else:
                rev_before = getattr(store, "auth_token_revocations", {}).get(claims.user_id)
                if rev_before is not None and (
                    claims.issued_at is None or claims.issued_at <= rev_before
                ):
                    raise AppError(
                        401,
                        "UNAUTHORIZED",
                        "Session expirée ou révoquée. Veuillez vous reconnecter.",
                    )
        return

    raise AppError(
        401,
        "UNAUTHORIZED",
        "Session expirée ou révoquée. Veuillez vous reconnecter.",
    )


def get_current_user_id(
    request: Request,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_app_settings),
) -> UUID:
    """
    Identifie l'utilisateur courant à partir du jeton Bearer vérifié.
    En mode local avec `allow_local_dev_auth=True`, autorise un profil local par défaut
    lorsqu'aucun en-tête Authorization n'est fourni.
    """
    if authorization is None:
        if settings.app_env == "local" and settings.allow_local_dev_auth:
            return UUID(settings.default_local_user_id)
        raise AppError(401, "UNAUTHORIZED", "Authentification requise.")

    scheme, _, token = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AppError(401, "UNAUTHORIZED", "Jeton d’authentification invalide ou expiré.")

    jwks_client = getattr(request.app.state, "jwks_client", None)
    claims = decode_bearer_token(token.strip(), settings, jwks_client=jwks_client)
    _assert_account_session_valid(request, claims)
    request.state.token_claims = claims
    return claims.user_id
