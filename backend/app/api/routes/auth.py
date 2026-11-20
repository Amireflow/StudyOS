from uuid import NAMESPACE_URL, UUID, uuid5
from fastapi import APIRouter, Depends, Response, status
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

router = APIRouter(prefix="/auth", tags=["Authentification"])

LOCAL_TOKEN_TTL_SECONDS = 86400


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte utilisateur personnel isolé",
)
def register_account(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    return auth_service.register(payload)


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Connexion par adresse e-mail et mot de passe",
)
def login_account(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    return auth_service.login(payload)


@router.post(
    "/change-password",
    response_model=AuthTokenResponse,
    summary="Modifier le mot de passe et renouveler le jeton de session",
)
def change_password(
    payload: ChangePasswordRequest,
    user_id: UUID = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    return auth_service.change_password(user_id, payload)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Révoquer toutes les sessions actives de l'utilisateur",
)
def logout_all_sessions(
    user_id: UUID = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    auth_service.logout_all_sessions(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
