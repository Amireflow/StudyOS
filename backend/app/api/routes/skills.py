from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from app.api.deps import get_skill_service
from app.core.config import Settings
from app.core.security import get_app_settings, get_current_user_id
from app.schemas.common import SkillAssessmentStatus
from app.schemas.skills import (
    SkillAssessmentCreate,
    SkillAssessmentDecision,
    SkillAssessmentEvaluate,
    SkillAssessmentResponse,
    SkillAssessmentSubmit,
    SkillCreate,
    SkillEvidenceCreate,
    SkillEvidenceInspectRequest,
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
    summary="Créer une compétence (niveau initial verrouillé à 0)",
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


@router.get(
    "/assessments",
    response_model=list[SkillAssessmentResponse],
    summary="Lister l'historique des évaluations de compétences de l'utilisateur",
)
def list_all_assessments(
    skill_id: UUID | None = Query(default=None),
    status_filter: SkillAssessmentStatus | None = Query(default=None, alias="status"),
    path_id: UUID | None = Query(default=None),
    module_id: UUID | None = Query(default=None),
    lesson_id: UUID | None = Query(default=None),
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> list[SkillAssessmentResponse]:
    return skill_service.list_assessments(
        user_id,
        skill_id=skill_id,
        status=status_filter,
        path_id=path_id,
        module_id=module_id,
        lesson_id=lesson_id,
    )


@router.get("/{skill_id}", response_model=SkillResponse, summary="Consulter une compétence")
def get_skill(
    skill_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillResponse:
    return skill_service.get_skill(user_id, skill_id)


@router.patch(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Modifier les métadonnées d'une compétence (niveau actuel verrouillé)",
)
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
    summary="Ajouter une preuve concrète de compétence",
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


@router.post(
    "/{skill_id}/evidence/{evidence_id}/inspect",
    response_model=SkillEvidenceResponse,
    summary="Inspecter de manière contrôlée une preuve GitHub externe",
)
def inspect_skill_evidence(
    skill_id: UUID,
    evidence_id: UUID,
    payload: SkillEvidenceInspectRequest | None = None,
    user_id: UUID = Depends(get_current_user_id),
    settings: Settings = Depends(get_app_settings),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillEvidenceResponse:
    return skill_service.inspect_evidence(
        user_id,
        skill_id,
        evidence_id,
        expected_files=payload.expected_files if payload else None,
        settings=settings,
    )


@router.get(
    "/{skill_id}/assessments",
    response_model=list[SkillAssessmentResponse],
    summary="Lister les évaluations d'une compétence",
)
def list_skill_assessments(
    skill_id: UUID,
    status_filter: SkillAssessmentStatus | None = Query(default=None, alias="status"),
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> list[SkillAssessmentResponse]:
    return skill_service.list_assessments(user_id, skill_id=skill_id, status=status_filter)


@router.post(
    "/{skill_id}/assessments",
    response_model=SkillAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle évaluation pédagogique pour une compétence",
)
def create_skill_assessment(
    skill_id: UUID,
    payload: SkillAssessmentCreate,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillAssessmentResponse:
    return skill_service.create_assessment(user_id, skill_id, payload)


@router.get(
    "/{skill_id}/assessments/{assessment_id}",
    response_model=SkillAssessmentResponse,
    summary="Consulter le détail d'une évaluation",
)
def get_skill_assessment(
    skill_id: UUID,
    assessment_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillAssessmentResponse:
    return skill_service.get_assessment(user_id, skill_id, assessment_id)


@router.post(
    "/{skill_id}/assessments/{assessment_id}/hint",
    response_model=SkillAssessmentResponse,
    summary="Dévoiler l'indice pédagogique suivant (sans révéler la solution)",
)
def reveal_skill_assessment_hint(
    skill_id: UUID,
    assessment_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillAssessmentResponse:
    return skill_service.reveal_assessment_hint(user_id, skill_id, assessment_id)


@router.post(
    "/{skill_id}/assessments/{assessment_id}/submit",
    response_model=SkillAssessmentResponse,
    summary="Soumettre une production et ses preuves pour évaluation",
)
def submit_skill_assessment(
    skill_id: UUID,
    assessment_id: UUID,
    payload: SkillAssessmentSubmit,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillAssessmentResponse:
    return skill_service.submit_assessment(user_id, skill_id, assessment_id, payload)


@router.post(
    "/{skill_id}/assessments/{assessment_id}/evaluate",
    response_model=SkillAssessmentResponse,
    summary="Évaluer la production soumise selon les critères pédagogiques",
)
def evaluate_skill_assessment(
    skill_id: UUID,
    assessment_id: UUID,
    payload: SkillAssessmentEvaluate | None = None,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillAssessmentResponse:
    return skill_service.evaluate_assessment(user_id, skill_id, assessment_id, payload)


@router.post(
    "/{skill_id}/assessments/{assessment_id}/validate",
    response_model=SkillAssessmentResponse,
    summary="Valider une évaluation réussie et mettre à jour le niveau de compétence",
)
def validate_skill_assessment(
    skill_id: UUID,
    assessment_id: UUID,
    payload: SkillAssessmentDecision | None = None,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillAssessmentResponse:
    return skill_service.validate_assessment(user_id, skill_id, assessment_id, payload)


@router.post(
    "/{skill_id}/assessments/{assessment_id}/reject",
    response_model=SkillAssessmentResponse,
    summary="Rejeter une évaluation sans modifier le niveau de compétence",
)
def reject_skill_assessment(
    skill_id: UUID,
    assessment_id: UUID,
    payload: SkillAssessmentDecision | None = None,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillAssessmentResponse:
    return skill_service.reject_assessment(user_id, skill_id, assessment_id, payload)


@router.post(
    "/{skill_id}/assessments/{assessment_id}/cancel",
    response_model=SkillAssessmentResponse,
    summary="Annuler une évaluation en attente ou en cours",
)
def cancel_skill_assessment(
    skill_id: UUID,
    assessment_id: UUID,
    payload: SkillAssessmentDecision | None = None,
    user_id: UUID = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillAssessmentResponse:
    return skill_service.cancel_assessment(user_id, skill_id, assessment_id, payload)
