from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from app.api.deps import get_project_service
from app.core.security import get_current_user_id
from app.schemas.common import ProjectStatus
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.projects_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projets"])


@router.get("", response_model=list[ProjectResponse], summary="Lister les projets")
def list_projects(
    status_filter: ProjectStatus | None = Query(default=None, alias="status"),
    user_id: UUID = Depends(get_current_user_id),
    project_service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    return project_service.list_projects(user_id, status_filter=status_filter)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un projet",
)
def create_project(
    payload: ProjectCreate,
    user_id: UUID = Depends(get_current_user_id),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return project_service.create_project(user_id, payload)


@router.get("/{project_id}", response_model=ProjectResponse, summary="Consulter un projet")
def get_project(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return project_service.get_project(user_id, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse, summary="Modifier un projet")
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    user_id: UUID = Depends(get_current_user_id),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return project_service.update_project(user_id, project_id, payload)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un projet",
)
def delete_project(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    project_service: ProjectService = Depends(get_project_service),
) -> Response:
    project_service.delete_project(user_id, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
