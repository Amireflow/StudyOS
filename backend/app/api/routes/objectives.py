from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from app.api.deps import get_objectives_service
from app.core.security import get_current_user_id
from app.schemas.common import ObjectiveStatus
from app.schemas.objectives import (
    ConfirmIntakeRequest,
    ConfirmIntakeResponse,
    ConversationalIntakeRequest,
    ConversationalIntakeResponse,
    ObjectivesOverviewResponse,
    PersonalGoalCreate,
    PersonalGoalResponse,
    PersonalGoalUpdate,
    UnifiedPlanApplyRequest,
    UnifiedPlanApplyResponse,
    UnifiedPlanGenerateRequest,
    UnifiedPlanResponse,
)
from app.services.objectives_service import ObjectivesService

router = APIRouter(prefix="/objectives", tags=["Objectifs & Projets"])


@router.get(
    "/overview",
    response_model=ObjectivesOverviewResponse,
    summary="Vue unifiée des 3 sources indépendantes (académique, objectifs personnels, projets)",
)
def get_objectives_overview(
    user_id: UUID = Depends(get_current_user_id),
    objectives_service: ObjectivesService = Depends(get_objectives_service),
) -> ObjectivesOverviewResponse:
    return objectives_service.get_overview(user_id)


@router.post(
    "/intake/analyze",
    response_model=ConversationalIntakeResponse,
    summary="Analyser des besoins exprimés en langage naturel et produire un récapitulatif structuré",
)
def analyze_intake(
    payload: ConversationalIntakeRequest,
    user_id: UUID = Depends(get_current_user_id),
    objectives_service: ObjectivesService = Depends(get_objectives_service),
) -> ConversationalIntakeResponse:
    return objectives_service.analyze_conversational_intake(user_id, payload)


@router.post(
    "/intake/confirm",
    response_model=ConfirmIntakeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer définitivement les objectifs et projets confirmés",
)
def confirm_intake(
    payload: ConfirmIntakeRequest,
    user_id: UUID = Depends(get_current_user_id),
    objectives_service: ObjectivesService = Depends(get_objectives_service),
) -> ConfirmIntakeResponse:
    return objectives_service.confirm_conversational_intake(user_id, payload)


@router.post(
    "/plan/generate",
    response_model=UnifiedPlanResponse,
    summary="Générer un programme unifié combinant cours universitaires, objectifs personnels et projets",
)
def generate_unified_plan(
    payload: UnifiedPlanGenerateRequest | None = None,
    user_id: UUID = Depends(get_current_user_id),
    objectives_service: ObjectivesService = Depends(get_objectives_service),
) -> UnifiedPlanResponse:
    return objectives_service.generate_unified_plan(user_id, payload)


@router.post(
    "/plan/apply",
    response_model=UnifiedPlanApplyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Valider et appliquer le programme unifié au planning et aux tâches",
)
def apply_unified_plan(
    payload: UnifiedPlanApplyRequest,
    user_id: UUID = Depends(get_current_user_id),
    objectives_service: ObjectivesService = Depends(get_objectives_service),
) -> UnifiedPlanApplyResponse:
    return objectives_service.apply_unified_plan(user_id, payload)


@router.get(
    "",
    response_model=list[PersonalGoalResponse],
    summary="Lister les objectifs personnels hors emploi du temps",
)
def list_personal_goals(
    status_filter: ObjectiveStatus | None = Query(default=None, alias="status"),
    user_id: UUID = Depends(get_current_user_id),
    objectives_service: ObjectivesService = Depends(get_objectives_service),
) -> list[PersonalGoalResponse]:
    return objectives_service.list_goals(user_id, status_filter=status_filter)


@router.post(
    "",
    response_model=PersonalGoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un objectif personnel d'apprentissage",
)
def create_personal_goal(
    payload: PersonalGoalCreate,
    user_id: UUID = Depends(get_current_user_id),
    objectives_service: ObjectivesService = Depends(get_objectives_service),
) -> PersonalGoalResponse:
    return objectives_service.create_goal(user_id, payload)


@router.get(
    "/{goal_id}",
    response_model=PersonalGoalResponse,
    summary="Consulter un objectif personnel",
)
def get_personal_goal(
    goal_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    objectives_service: ObjectivesService = Depends(get_objectives_service),
) -> PersonalGoalResponse:
    return objectives_service.get_goal(user_id, goal_id)


@router.patch(
    "/{goal_id}",
    response_model=PersonalGoalResponse,
    summary="Modifier ou suspendre un objectif personnel",
)
def update_personal_goal(
    goal_id: UUID,
    payload: PersonalGoalUpdate,
    user_id: UUID = Depends(get_current_user_id),
    objectives_service: ObjectivesService = Depends(get_objectives_service),
) -> PersonalGoalResponse:
    return objectives_service.update_goal(user_id, goal_id, payload)


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un objectif personnel",
)
def delete_personal_goal(
    goal_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    objectives_service: ObjectivesService = Depends(get_objectives_service),
) -> Response:
    objectives_service.delete_goal(user_id, goal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
