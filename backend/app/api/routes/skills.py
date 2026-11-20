from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from app.api.deps import get_skill_service
from app.core.security import get_current_user_id
from app.schemas.skills import (
    SkillCreate,
    SkillEvidenceCreate,
    SkillEvidenceResponse,
    SkillEvidenceUpdate,
    SkillResponse,
    SkillUpdate,
)
from app.services.skills_service import SkillService

router = APIRouter(prefix="/skills", tags=["Compétences"])


@router.get("", response_model=list[SkillResponse], summary="Lister les compétences")
def list_skills(
    domain: str | None = Query(default=None),
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> list[SkillResponse]:
    return skill_service.list_skills(user_id, domain=domain)


@router.post(
    "",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une compétence",
)
def create_skill(
    payload: SkillCreate,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillResponse:
    return skill_service.create_skill(user_id, payload)


@router.get(
    "/evidence",
    response_model=list[SkillEvidenceResponse],
    summary="Lister toutes les preuves de compétence de l'utilisateur",
)
def list_all_evidence(
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> list[SkillEvidenceResponse]:
    return skill_service.list_evidence(user_id)


@router.get("/{skill_id}", response_model=SkillResponse, summary="Consulter une compétence")
def get_skill(
    skill_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillResponse:
    return skill_service.get_skill(user_id, skill_id)


@router.patch("/{skill_id}", response_model=SkillResponse, summary="Modifier une compétence")
def update_skill(
    skill_id: UUID,
    payload: SkillUpdate,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillResponse:
    return skill_service.update_skill(user_id, skill_id, payload)


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une compétence",
)
def delete_skill(
    skill_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> Response:
    skill_service.delete_skill(user_id, skill_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{skill_id}/evidence",
    response_model=list[SkillEvidenceResponse],
    summary="Lister les preuves associées à une compétence",
)
def list_skill_evidence(
    skill_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> list[SkillEvidenceResponse]:
    return skill_service.list_evidence(user_id, skill_id=skill_id)


@router.post(
    "/{skill_id}/evidence",
    response_model=SkillEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une preuve de compétence",
)
def add_skill_evidence(
    skill_id: UUID,
    payload: SkillEvidenceCreate,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillEvidenceResponse:
    return skill_service.add_evidence(user_id, skill_id, payload)


@router.patch(
    "/{skill_id}/evidence/{evidence_id}",
    response_model=SkillEvidenceResponse,
    summary="Modifier une preuve de compétence",
)
def update_skill_evidence(
    skill_id: UUID,
    evidence_id: UUID,
    payload: SkillEvidenceUpdate,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillEvidenceResponse:
    return skill_service.update_evidence(user_id, skill_id, evidence_id, payload)


@router.delete(
    "/{skill_id}/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une preuve de compétence",
)
def delete_skill_evidence(
    skill_id: UUID,
    evidence_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> Response:
    skill_service.delete_evidence(user_id, skill_id, evidence_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
