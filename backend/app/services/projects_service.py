from datetime import datetime, timezone
from uuid import UUID, uuid4
from app.core.errors import AppError
from app.repositories.learning_sql import ProjectRecord, SqlProjectRepository
from app.repositories.memory import ProfileRepository
from app.schemas.common import ProjectStatus, TaskPriority
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate

STATUS_ORDER: dict[ProjectStatus, int] = {
    ProjectStatus.active: 0,
    ProjectStatus.blocked: 1,
    ProjectStatus.planned: 2,
    ProjectStatus.completed: 3,
    ProjectStatus.archived: 4,
}

PRIORITY_ORDER: dict[TaskPriority, int] = {
    TaskPriority.critical: 0,
    TaskPriority.high: 1,
    TaskPriority.normal: 2,
    TaskPriority.low: 3,
}


class ProjectService:
    def __init__(
        self,
        repo: SqlProjectRepository,
        profile_repo: ProfileRepository,
    ) -> None:
        self._repo = repo
        self._profile_repo = profile_repo

    def list_projects(
        self,
        user_id: UUID,
        *,
        status_filter: ProjectStatus | None = None,
    ) -> list[ProjectResponse]:
        records = self._repo.list_projects(user_id)
        if status_filter is not None:
            records = [item for item in records if item.status == status_filter]
        records.sort(
            key=lambda item: (
                STATUS_ORDER[item.status],
                PRIORITY_ORDER[item.priority],
                -item.created_at.timestamp(),
            )
        )
        return [ProjectResponse.model_validate(item.model_dump()) for item in records]

    def get_project(self, user_id: UUID, project_id: UUID) -> ProjectResponse:
        record = self._repo.get(user_id, project_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Projet introuvable.")
        return ProjectResponse.model_validate(record.model_dump())

    def create_project(self, user_id: UUID, payload: ProjectCreate) -> ProjectResponse:
        now = datetime.now(timezone.utc)
        record = ProjectRecord(
            id=uuid4(),
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            goal=payload.goal,
            status=payload.status,
            priority=payload.priority,
            next_action=payload.next_action,
            deliverables=payload.deliverables,
            target_date=payload.target_date,
            created_at=now,
            updated_at=now,
        )
        saved = self._repo.save(record)
        return ProjectResponse.model_validate(saved.model_dump())

    def update_project(
        self,
        user_id: UUID,
        project_id: UUID,
        payload: ProjectUpdate,
    ) -> ProjectResponse:
        existing = self._repo.get(user_id, project_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Projet introuvable.")

        fields = payload.model_fields_set
        next_status = (
            payload.status
            if "status" in fields and payload.status is not None
            else existing.status
        )
        next_action = (
            payload.next_action
            if "next_action" in fields and payload.next_action is not None
            else existing.next_action
        )
        if next_status == ProjectStatus.active and len(next_action.strip()) < 2:
            raise AppError(
                422,
                "VALIDATION_ERROR",
                "Une prochaine action concrète (min. 2 caractères) est obligatoire pour un projet actif.",
            )

        now = datetime.now(timezone.utc)
        updates: dict[str, object] = {
            "status": next_status,
            "next_action": next_action,
            "updated_at": now,
        }
        if "name" in fields and payload.name is not None:
            updates["name"] = payload.name
        if "description" in fields:
            updates["description"] = payload.description
        if "goal" in fields and payload.goal is not None:
            updates["goal"] = payload.goal
        if "priority" in fields and payload.priority is not None:
            updates["priority"] = payload.priority
        if "deliverables" in fields:
            updates["deliverables"] = payload.deliverables
        if "target_date" in fields:
            updates["target_date"] = payload.target_date

        saved = self._repo.save(existing.model_copy(update=updates))
        return ProjectResponse.model_validate(saved.model_dump())

    def delete_project(self, user_id: UUID, project_id: UUID) -> None:
        existing = self._repo.get(user_id, project_id)
        if existing is None or not self._repo.delete(user_id, project_id):
            raise AppError(404, "NOT_FOUND", "Projet introuvable.")

        profile = self._profile_repo.get(user_id)
        if profile is not None and profile.active_priority_project_id == project_id:
            profile_updates: dict[str, object] = {
                "active_priority_project_id": None,
                "updated_at": datetime.now(timezone.utc),
            }
            if (
                profile.active_priority_task_id is None
                and profile.active_priority_title == existing.name
            ):
                profile_updates["active_priority_title"] = None
            self._profile_repo.save(profile.model_copy(update=profile_updates))
