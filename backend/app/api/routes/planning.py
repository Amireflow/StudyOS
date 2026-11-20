from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Query, Response, status
from app.api.deps import get_learning_planning_service
from app.core.security import get_current_user_id
from app.planning.service import LearningPlanningService
from app.schemas.planning import (
    AvailabilityComputationResponse,
    AvailabilityRuleCreate,
    AvailabilityRuleResponse,
    AvailabilityRuleUpdate,
    LearningPlanAdjustRequest,
    LearningPlanApplyRequest,
    LearningPlanGenerateRequest,
    LearningPlanVersionResponse,
    ScheduleValidityResponse,
)

router = APIRouter(prefix="/planning", tags=["Moteur de Planification"])


@router.get(
    "/availability-rules",
    response_model=list[AvailabilityRuleResponse],
    summary="Lister les règles de disponibilité, d’indisponibilité et de récupération",
)
def list_availability_rules(
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> list[AvailabilityRuleResponse]:
    return planning_service.list_availability_rules(user_id)


@router.post(
    "/availability-rules",
    response_model=AvailabilityRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une règle de disponibilité ou d’indisponibilité personnelle",
)
def create_availability_rule(
    payload: AvailabilityRuleCreate,
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> AvailabilityRuleResponse:
    return planning_service.create_availability_rule(user_id, payload)


@router.patch(
    "/availability-rules/{rule_id}",
    response_model=AvailabilityRuleResponse,
    summary="Mettre à jour une règle de disponibilité",
)
def update_availability_rule(
    rule_id: UUID,
    payload: AvailabilityRuleUpdate,
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> AvailabilityRuleResponse:
    return planning_service.update_availability_rule(user_id, rule_id, payload)


@router.delete(
    "/availability-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une règle de disponibilité",
)
def delete_availability_rule(
    rule_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> Response:
    planning_service.delete_availability_rule(user_id, rule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/availability/compute",
    response_model=AvailabilityComputationResponse,
    summary="Calculer de façon déterministe les créneaux disponibles, fixes, indisponibles et de récupération",
)
def compute_availability(
    horizon_days: int = Query(default=7, ge=1, le=30),
    range_start: datetime | None = Query(default=None),
    timezone: str | None = Query(default=None, min_length=2, max_length=64),
    min_session_minutes: int = Query(default=30, ge=15, le=120),
    buffer_minutes: int = Query(default=10, ge=0, le=45),
    include_potential: bool = Query(default=True),
    replace_future_planned: bool = Query(default=True),
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> AvailabilityComputationResponse:
    return planning_service.compute_availability(
        user_id,
        horizon_days=horizon_days,
        range_start=range_start,
        timezone_name=timezone,
        min_session_minutes=min_session_minutes,
        buffer_minutes=buffer_minutes,
        include_potential=include_potential,
        replace_future_planned=replace_future_planned,
    )


@router.post(
    "/generate",
    response_model=LearningPlanVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyser toutes les sources et générer un programme d’apprentissage personnalisé (sans mutation directe)",
)
def generate_learning_plan(
    payload: LearningPlanGenerateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> LearningPlanVersionResponse:
    return planning_service.generate_plan(user_id, payload, idempotency_key=idempotency_key)


@router.post(
    "/adjust",
    response_model=LearningPlanVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Recalculer ou ajuster le programme selon de nouvelles contraintes ou demandes",
)
def adjust_learning_plan(
    payload: LearningPlanAdjustRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> LearningPlanVersionResponse:
    return planning_service.adjust_plan(user_id, payload, idempotency_key=idempotency_key)


@router.get(
    "/versions",
    response_model=list[LearningPlanVersionResponse],
    summary="Lister l’historique des versions de programmes d’apprentissage",
)
def list_plan_versions(
    limit: int = Query(default=20, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> list[LearningPlanVersionResponse]:
    return planning_service.list_versions(user_id, limit=limit)


@router.get(
    "/versions/{version_id}",
    response_model=LearningPlanVersionResponse,
    summary="Consulter le détail d’une version de programme",
)
def get_plan_version(
    version_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> LearningPlanVersionResponse:
    return planning_service.get_version(user_id, version_id)


@router.post(
    "/versions/{version_id}/apply",
    response_model=LearningPlanVersionResponse,
    summary="Appliquer réellement une version de programme dans le calendrier et les tâches (avec rollback)",
)
def apply_plan_version(
    version_id: UUID,
    payload: LearningPlanApplyRequest = LearningPlanApplyRequest(),
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> LearningPlanVersionResponse:
    return planning_service.apply_plan(user_id, version_id, payload)


@router.post(
    "/versions/{version_id}/reject",
    response_model=LearningPlanVersionResponse,
    summary="Rejeter une proposition de programme sans modifier le calendrier",
)
def reject_plan_version(
    version_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> LearningPlanVersionResponse:
    return planning_service.reject_plan(user_id, version_id)


@router.post(
    "/versions/{version_id}/restore",
    response_model=LearningPlanVersionResponse,
    summary="Restaurer une version antérieure du programme d’apprentissage",
)
def restore_plan_version(
    version_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> LearningPlanVersionResponse:
    return planning_service.restore_plan_version(user_id, version_id)


@router.get(
    "/validity",
    response_model=ScheduleValidityResponse,
    summary="Vérifier l’obsolescence du planning (tâches en retard, séances manquées, conflits, surcharge)",
)
def check_schedule_validity(
    timezone: str | None = Query(default=None, min_length=2, max_length=64),
    user_id: UUID = Depends(get_current_user_id),
    planning_service: LearningPlanningService = Depends(get_learning_planning_service),
) -> ScheduleValidityResponse:
    return planning_service.check_schedule_validity(user_id, timezone_name=timezone)
