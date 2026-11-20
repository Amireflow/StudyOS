from datetime import datetime
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from app.api.deps import get_profile_service, get_task_service, get_utc_now
from app.core.security import get_current_user_id
from app.schemas.common import TaskPriority
from app.schemas.tasks import TaskCreate, TaskResponse, TaskUpdate
from app.services.profile_service import ProfileService
from app.services.tasks_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tâches"])


@router.get("", response_model=list[TaskResponse], summary="Lister et filtrer les tâches")
def list_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    priority: TaskPriority | None = Query(default=None),
    due: Literal["all", "overdue", "today", "upcoming", "no_due"] | None = Query(default=None),
    search: str | None = Query(default=None),
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
    task_service: TaskService = Depends(get_task_service),
    now_utc: datetime = Depends(get_utc_now),
) -> list[TaskResponse]:
    profile = profile_service.get_or_create_record(user_id)
    return task_service.list_tasks(
        user_id,
        status_filter=status_filter,
        priority=priority,
        due=due,
        search=search,
        tz_name=profile.timezone,
        now_utc=now_utc,
    )


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une tâche",
)
def create_task(
    payload: TaskCreate,
    user_id: UUID = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    return task_service.create_task(user_id, payload)


@router.get("/{task_id}", response_model=TaskResponse, summary="Consulter une tâche")
def get_task(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    return task_service.get_task(user_id, task_id)


@router.patch("/{task_id}", response_model=TaskResponse, summary="Modifier une tâche")
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    user_id: UUID = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    return task_service.update_task(user_id, task_id, payload)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une tâche",
)
def delete_task(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
) -> Response:
    task_service.delete_task(user_id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
