from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID
import jwt
from fastapi import Depends, Header, Request
from jwt import InvalidTokenError, PyJWKClient, PyJWKClientError
from app.core.config import Settings, get_settings
from app.core.errors import AppError

LOCAL_TOKEN_ISSUER = "amireflow-local"


def get_app_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if isinstance(settings, Settings):
        return settings
    return get_settings()


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


def verify_bearer_token(
    token: str,
    settings: Settings,
    jwks_client: Any = None,
) -> UUID:
    """
    Vérifie un jeton Bearer (JWKS RS256/ES256 Supabase, ou en mode local les jetons
    HS256 `amireflow-local` et `dev:<uuid>` lorsque `allow_local_dev_auth=True`).
    """
    if settings.app_env == "local":
        if settings.allow_local_dev_auth and token.startswith("dev:"):
            raw_uuid = token.removeprefix("dev:").strip()
            try:
                return UUID(raw_uuid)
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
                    issuer=LOCAL_TOKEN_ISSUER,
                    audience=settings.auth_audience or None,
                    options={
                        "verify_exp": True,
                        "require": ["sub", "exp"],
                        "verify_aud": bool(settings.auth_audience),
                    },
                )
                return UUID(str(payload["sub"]))
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
            return UUID(str(payload["sub"]))
        except (PyJWKClientError, InvalidTokenError, ValueError, KeyError) as exc:
            raise AppError(
                401,
                "UNAUTHORIZED",
                "Jeton d’authentification invalide ou expiré.",
            ) from exc

    raise AppError(401, "UNAUTHORIZED", "Jeton d’authentification invalide ou expiré.")


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
    return verify_bearer_token(token.strip(), settings, jwks_client=jwks_client)
