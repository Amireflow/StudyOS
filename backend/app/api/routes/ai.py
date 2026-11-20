from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from app.ai.orchestrator import AIOrchestrator
from app.api.deps import get_ai_orchestrator, get_rate_limiter, get_utc_now
from app.core.config import Settings
from app.core.security import get_app_settings, get_current_user_id
from app.services.rate_limiter import PersistentRateLimiter, resolve_client_ip
from app.schemas.ai import (
    AcceptProposalRequest,
    AiActionProposalResponse,
    AiConversationCreate,
    AiConversationDetailResponse,
    AiConversationResponse,
    AiMemoryResponse,
    AiMemoryUpdateRequest,
    AiMessageCreate,
    AiProviderConfigResponse,
    AiProviderConfigUpdate,
    AiReportResponse,
    AiToolSpec,
    AiTurnResponse,
    EnsureAiReportsResponse,
    FetchProviderModelsRequest,
    FetchProviderModelsResponse,
    RejectProposalRequest,
    UpdateProposalRequest,
)
from app.schemas.common import AiReportType, ProposalStatus

router = APIRouter(prefix="/ai", tags=["Copilote IA"])


@router.get(
    "/provider/config",
    response_model=AiProviderConfigResponse,
    summary="Consulter la configuration active du fournisseur IA (clé masquée)",
)
def get_ai_provider_config(
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiProviderConfigResponse:
    return orchestrator.get_provider_config(user_id)


@router.put(
    "/provider/config",
    response_model=AiProviderConfigResponse,
    summary="Enregistrer le fournisseur IA, la clé API et le modèle côté serveur",
)
def update_ai_provider_config(
    payload: AiProviderConfigUpdate,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiProviderConfigResponse:
    return orchestrator.update_provider_config(user_id, payload)


@router.post(
    "/provider/models",
    response_model=FetchProviderModelsResponse,
    summary="Récupérer la liste des modèles disponibles pour le fournisseur et la clé API",
)
def fetch_ai_provider_models(
    payload: FetchProviderModelsRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
    rate_limiter: PersistentRateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_app_settings),
) -> FetchProviderModelsResponse:
    return orchestrator.fetch_available_models(
        user_id,
        payload,
        client_ip=resolve_client_ip(request, settings),
        rate_limiter=rate_limiter,
    )


@router.get(
    "/tools",
    response_model=list[AiToolSpec],
    summary="Consulter la liste blanche des outils exposés au Copilote IA (ToolRegistry)",
)
def list_ai_tools(
    _user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> list[AiToolSpec]:
    return orchestrator.list_tools()


@router.get(
    "/conversations",
    response_model=list[AiConversationResponse],
    summary="Lister les conversations IA de l'utilisateur",
)
def list_conversations(
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> list[AiConversationResponse]:
    return orchestrator.list_conversations(user_id)


@router.post(
    "/conversations",
    response_model=AiConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle conversation IA",
)
def create_conversation(
    payload: AiConversationCreate | None = None,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiConversationResponse:
    return orchestrator.create_conversation(user_id, payload or AiConversationCreate())


@router.get(
    "/conversations/{conversation_id}",
    response_model=AiConversationDetailResponse,
    summary="Lire une conversation IA avec ses messages et propositions (lecture pure sans effet de bord)",
)
def get_conversation(
    conversation_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiConversationDetailResponse:
    return orchestrator.get_conversation_detail(user_id, conversation_id)


@router.post(
    "/conversations/{conversation_id}/repair",
    response_model=AiConversationDetailResponse,
    summary="Réparer et normaliser de manière idempotente l'historique d'une conversation IA",
)
def repair_conversation(
    conversation_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiConversationDetailResponse:
    return orchestrator.repair_conversation(user_id, conversation_id)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une conversation IA",
)
def delete_conversation(
    conversation_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> Response:
    orchestrator.delete_conversation(user_id, conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AiTurnResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Envoyer un message au Copilote IA et recevoir une réponse contextualisée",
)
def send_message(
    conversation_id: UUID,
    payload: AiMessageCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiTurnResponse:
    resolved = (
        payload.model_copy(update={"idempotency_key": idempotency_key.strip()[:80]})
        if idempotency_key and idempotency_key.strip() and not payload.idempotency_key
        else payload
    )
    return orchestrator.send_message(user_id, conversation_id, resolved)


@router.get(
    "/proposals",
    response_model=list[AiActionProposalResponse],
    summary="Lister les propositions d'actions IA",
)
def list_proposals(
    status_filter: ProposalStatus | None = Query(default=None, alias="status"),
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> list[AiActionProposalResponse]:
    return orchestrator.list_proposals(user_id, status_filter=status_filter)


@router.get(
    "/proposals/{proposal_id}",
    response_model=AiActionProposalResponse,
    summary="Consulter une proposition d'action IA",
)
def get_proposal(
    proposal_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiActionProposalResponse:
    return orchestrator.get_proposal(user_id, proposal_id)


@router.patch(
    "/proposals/{proposal_id}",
    response_model=AiActionProposalResponse,
    summary="Modifier ou recalculer une proposition d'action IA avant validation",
)
def update_proposal(
    proposal_id: UUID,
    payload: UpdateProposalRequest,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiActionProposalResponse:
    return orchestrator.update_proposal(user_id, proposal_id, payload)


@router.post(
    "/proposals/{proposal_id}/accept",
    response_model=AiActionProposalResponse,
    summary="Valider et exécuter une proposition d'action IA autorisée",
)
def accept_proposal(
    proposal_id: UUID,
    payload: AcceptProposalRequest | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiActionProposalResponse:
    resolved_req = payload or AcceptProposalRequest()
    if idempotency_key and idempotency_key.strip() and not resolved_req.idempotency_key:
        resolved_req = resolved_req.model_copy(
            update={"idempotency_key": idempotency_key.strip()[:80]}
        )
    return orchestrator.accept_proposal(user_id, proposal_id, resolved_req)


@router.post(
    "/proposals/{proposal_id}/reject",
    response_model=AiActionProposalResponse,
    summary="Rejeter une proposition d'action IA",
)
def reject_proposal(
    proposal_id: UUID,
    payload: RejectProposalRequest | None = None,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiActionProposalResponse:
    return orchestrator.reject_proposal(user_id, proposal_id, payload)


@router.post(
    "/briefing",
    response_model=AiReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Générer un briefing quotidien fondé sur les données réelles (P1)",
)
def create_daily_briefing(
    force: bool = Query(default=False),
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
    now_utc: datetime = Depends(get_utc_now),
) -> AiReportResponse:
    return orchestrator.generate_daily_briefing(user_id, now_utc=now_utc, force=force)


@router.post(
    "/weekly-review",
    response_model=AiReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Générer un bilan hebdomadaire fondé sur les données réelles (P1)",
)
def create_weekly_review(
    force: bool = Query(default=False),
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
    now_utc: datetime = Depends(get_utc_now),
) -> AiReportResponse:
    return orchestrator.generate_weekly_review(user_id, now_utc=now_utc, force=force)


@router.post(
    "/reports/ensure",
    response_model=EnsureAiReportsResponse,
    summary="Garantir de manière idempotente le briefing quotidien et le bilan hebdomadaire sur le fuseau de l'utilisateur",
)
def ensure_periodic_reports(
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
    now_utc: datetime = Depends(get_utc_now),
) -> EnsureAiReportsResponse:
    return orchestrator.ensure_periodic_reports(user_id, now_utc=now_utc)


@router.get(
    "/reports",
    response_model=list[AiReportResponse],
    summary="Lister les briefings quotidiens et bilans hebdomadaires générés",
)
def list_reports(
    report_type: AiReportType | None = Query(default=None, alias="type"),
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> list[AiReportResponse]:
    return orchestrator.list_reports(user_id, report_type=report_type)


@router.get(
    "/memory",
    response_model=AiMemoryResponse,
    summary="Consulter la mémoire structurée persistante du Copilote IA",
)
def get_ai_memory(
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiMemoryResponse:
    return orchestrator.get_memory(user_id)


@router.patch(
    "/memory",
    response_model=AiMemoryResponse,
    summary="Mettre à jour la mémoire structurée et le mode d'autonomie simple du Copilote IA",
)
def update_ai_memory(
    payload: AiMemoryUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiMemoryResponse:
    return orchestrator.update_memory(user_id, payload)
