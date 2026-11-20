from uuid import NAMESPACE_URL, UUID, uuid5
from fastapi import APIRouter, Depends, Query, Request, Response, status
from app.api.deps import get_auth_service, get_profile_service
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    create_local_access_token,
    get_app_settings,
    get_current_user_id,
)
from app.schemas.auth import (
    AuthAccountResponse,
    AuthTokenResponse,
    ChangePasswordRequest,
    LocalLoginRequest,
    LoginRequest,
    RegisterRequest,
)
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.auth_service import AuthService
from app.services.profile_service import ProfileService
from app.services.rate_limiter import resolve_client_ip

router = APIRouter(prefix="/auth", tags=["Authentification"])

LOCAL_TOKEN_TTL_SECONDS = 86400


def _resolve_cookie_samesite(settings: Settings) -> str:
    configured = (settings.auth_cookie_samesite or "").strip().lower()
    if configured in ("lax", "strict", "none"):
        return configured
    return "none" if settings.app_env.strip().lower() == "production" else "lax"


def _set_refresh_cookie(
    response: Response,
    request: Request,
    raw_refresh_token: str | None,
    settings: Settings,
) -> None:
    if not raw_refresh_token:
        return
    is_prod = settings.app_env.strip().lower() == "production"
    samesite = _resolve_cookie_samesite(settings)
    secure = is_prod or request.url.scheme == "https" or samesite == "none"
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=raw_refresh_token,
        max_age=int(settings.refresh_token_ttl_seconds or (14 * 86400)),
        path="/api/v1/auth",
        httponly=True,
        secure=secure,
        samesite=samesite,  # type: ignore[arg-type]
    )


def _clear_refresh_cookie(response: Response, request: Request, settings: Settings) -> None:
    is_prod = settings.app_env.strip().lower() == "production"
    samesite = _resolve_cookie_samesite(settings)
    secure = is_prod or request.url.scheme == "https" or samesite == "none"
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/api/v1/auth",
        httponly=True,
        secure=secure,
        samesite=samesite,  # type: ignore[arg-type]
    )


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte utilisateur personnel isolé",
)
def register_account(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    client_ip = resolve_client_ip(request, settings)
    user_agent = request.headers.get("user-agent")
    token_res, raw_refresh = auth_service.register(
        payload, client_ip=client_ip, user_agent=user_agent
    )
    _set_refresh_cookie(response, request, raw_refresh, settings)
    return token_res


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Connexion par adresse e-mail et mot de passe",
)
def login_account(
    payload: LoginRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    client_ip = resolve_client_ip(request, settings)
    user_agent = request.headers.get("user-agent")
    token_res, raw_refresh = auth_service.login(
        payload, client_ip=client_ip, user_agent=user_agent
    )
    _set_refresh_cookie(response, request, raw_refresh, settings)
    return token_res


@router.post(
    "/refresh",
    response_model=AuthTokenResponse,
    summary="Renouveler le jeton d'accès via le cookie de session HttpOnly (rotation)",
)
def refresh_access_token(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    raw_cookie = request.cookies.get(settings.auth_cookie_name)
    client_ip = resolve_client_ip(request, settings)
    user_agent = request.headers.get("user-agent")
    try:
        token_res, next_raw_refresh = auth_service.refresh_session(
            raw_cookie, client_ip=client_ip, user_agent=user_agent
        )
    except AppError:
        _clear_refresh_cookie(response, request, settings)
        raise
    _set_refresh_cookie(response, request, next_raw_refresh, settings)
    return token_res


@router.post(
    "/change-password",
    response_model=AuthTokenResponse,
    summary="Modifier le mot de passe et renouveler le jeton de session",
)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    settings: Settings = Depends(get_app_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    client_ip = resolve_client_ip(request, settings)
    user_agent = request.headers.get("user-agent")
    token_res, raw_refresh = auth_service.change_password(
        user_id, payload, client_ip=client_ip, user_agent=user_agent
    )
    _set_refresh_cookie(response, request, raw_refresh, settings)
    return token_res


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Déconnecter la session courante ou toutes les sessions actives",
)
def logout_all_sessions(
    request: Request,
    current_only: bool = Query(default=False),
    user_id: UUID = Depends(get_current_user_id),
    settings: Settings = Depends(get_app_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    raw_cookie = request.cookies.get(settings.auth_cookie_name)
    auth_service.logout_session(
        user_id,
        raw_refresh_token=raw_cookie,
        all_sessions=not current_only,
    )
    res = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(res, request, settings)
    return res


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Révoquer toutes les sessions actives de l'utilisateur",
)
def logout_all_explicit(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    settings: Settings = Depends(get_app_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    auth_service.logout_all_sessions(user_id)
    res = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(res, request, settings)
    return res


@router.get(
    "/account",
    response_model=AuthAccountResponse,
    summary="Informations du compte authentifié et profil associé",
)
def read_account_info(
    user_id: UUID = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthAccountResponse:
    return auth_service.get_account_info(user_id)


@router.post(
    "/local-login",
    response_model=AuthTokenResponse,
    summary="Connexion locale de développement (JWT HS256)",
)
def local_login(
    payload: LocalLoginRequest,
    settings: Settings = Depends(get_app_settings),
    profile_service: ProfileService = Depends(get_profile_service),
) -> AuthTokenResponse:
    if not (settings.app_env == "local" and settings.allow_local_dev_auth):
        raise AppError(
            403,
            "FORBIDDEN",
            "La connexion locale de développement est désactivée.",
        )

    user_id = uuid5(NAMESPACE_URL, f"amireflow-local:{payload.email}")
    profile_service.get_or_create_record(user_id)
    if payload.display_name is not None:
        profile = profile_service.update_profile(
            user_id,
            ProfileUpdate(display_name=payload.display_name),
        )
    else:
        profile = profile_service.get_profile(user_id)

    token = create_local_access_token(
        user_id,
        settings,
        expires_in_seconds=LOCAL_TOKEN_TTL_SECONDS,
    )
    return AuthTokenResponse(
        access_token=token,
        expires_in=LOCAL_TOKEN_TTL_SECONDS,
        email=payload.email,
        profile=profile,
    )


@router.get("/me", response_model=ProfileResponse, summary="Profil de la session active")
def read_current_user_profile(
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return profile_service.get_profile(user_id)
