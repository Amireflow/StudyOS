from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from app.api.deps import get_session_service
from app.core.security import get_current_user_id
from app.schemas.common import SessionStatus
from app.schemas.sessions import (
    SessionCreate,
    SessionFinish,
    SessionResponse,
    SessionUpdate,
)
from app.services.sessions_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Séances"])


@router.get("", response_model=list[SessionResponse], summary="Lister les séances")
def list_sessions(
    status_filter: SessionStatus | None = Query(default=None, alias="status"),
    user_id: UUID = Depends(get_current_user_id),
    session_service: SessionService = Depends(get_session_service),
) -> list[SessionResponse]:
    return session_service.list_sessions(user_id, status_filter=status_filter)


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Démarrer ou enregistrer une séance",
)
def create_session(
    payload: SessionCreate,
    user_id: UUID = Depends(get_current_user_id),
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return session_service.create_session(user_id, payload)


@router.patch("/{session_id}", response_model=SessionResponse, summary="Modifier ou annuler une séance")
def update_session(
    session_id: UUID,
    payload: SessionUpdate,
    user_id: UUID = Depends(get_current_user_id),
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return session_service.update_session(user_id, session_id, payload)


@router.patch(
    "/{session_id}/finish",
    response_model=SessionResponse,
    summary="Clôturer une séance en cours",
)
def finish_session(
    session_id: UUID,
    payload: SessionFinish,
    user_id: UUID = Depends(get_current_user_id),
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return session_service.finish_session(user_id, session_id, payload)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une séance",
)
def delete_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session_service: SessionService = Depends(get_session_service),
) -> Response:
    session_service.delete_session(user_id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
