from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from app.ai.orchestrator import AIOrchestrator
from app.api.deps import get_ai_orchestrator, get_utc_now
from app.core.security import get_current_user_id
from app.schemas.ai import (
    AcceptProposalRequest,
    AiActionProposalResponse,
    AiConversationCreate,
    AiConversationDetailResponse,
    AiConversationResponse,
    AiMessageCreate,
    AiReportResponse,
    AiToolSpec,
    AiTurnResponse,
    RejectProposalRequest,
)
from app.schemas.common import AiReportType, ProposalStatus

router = APIRouter(prefix="/ai", tags=["Copilote IA"])


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
    summary="Lire une conversation IA avec ses messages et propositions",
)
def get_conversation(
    conversation_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiConversationDetailResponse:
    return orchestrator.get_conversation_detail(user_id, conversation_id)


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
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiTurnResponse:
    return orchestrator.send_message(user_id, conversation_id, payload)


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


@router.post(
    "/proposals/{proposal_id}/accept",
    response_model=AiActionProposalResponse,
    summary="Valider et exécuter une proposition d'action IA autorisée",
)
def accept_proposal(
    proposal_id: UUID,
    payload: AcceptProposalRequest | None = None,
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> AiActionProposalResponse:
    return orchestrator.accept_proposal(user_id, proposal_id, payload)


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
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
    now_utc: datetime = Depends(get_utc_now),
) -> AiReportResponse:
    return orchestrator.generate_daily_briefing(user_id, now_utc=now_utc)


@router.post(
    "/weekly-review",
    response_model=AiReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Générer un bilan hebdomadaire fondé sur les données réelles (P1)",
)
def create_weekly_review(
    user_id: UUID = Depends(get_current_user_id),
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
    now_utc: datetime = Depends(get_utc_now),
) -> AiReportResponse:
    return orchestrator.generate_weekly_review(user_id, now_utc=now_utc)


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
