from uuid import NAMESPACE_URL, UUID, uuid5
from fastapi import APIRouter, Depends
from app.api.deps import get_profile_service
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    create_local_access_token,
    get_app_settings,
    get_current_user_id,
)
from app.schemas.auth import AuthTokenResponse, LocalLoginRequest
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/auth", tags=["Authentification"])

LOCAL_TOKEN_TTL_SECONDS = 86400


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
        profile=profile,
    )


@router.get("/me", response_model=ProfileResponse, summary="Profil de la session active")
def read_current_user_profile(
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return profile_service.get_profile(user_id)
