from uuid import UUID
from fastapi import APIRouter, Depends
from app.api.deps import get_profile_service
from app.core.security import get_current_user_id
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["Profil"])


@router.get("", response_model=ProfileResponse, summary="Lire le profil utilisateur")
def read_profile(
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return profile_service.get_profile(user_id)


@router.patch("", response_model=ProfileResponse, summary="Mettre à jour le profil")
def update_profile(
    payload: ProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return profile_service.update_profile(user_id, payload)
