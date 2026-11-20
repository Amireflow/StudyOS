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
    ProjectStatus.paused: 2,
    ProjectStatus.planned: 3,
    ProjectStatus.completed: 4,
    ProjectStatus.archived: 5,
}

PRIORITY_ORDER: dict[TaskPriority, int] = {
    TaskPriority.critical: 0,
    TaskPriority.high: 1,
    TaskPriority.normal: 2,
    TaskPriority.low: 3,
}

MAX_ACTIVE_PROJECTS = 3
INACTIVE_PROJECT_STATUSES = {
    ProjectStatus.paused,
    ProjectStatus.completed,
    ProjectStatus.archived,
}


class ProjectService:
    def __init__(
        self,
        repo: SqlProjectRepository,
        profile_repo: ProfileRepository,
    ) -> None:
        self._repo = repo
        self._profile_repo = profile_repo

    def _ensure_active_slot_available(self, user_id: UUID, exclude_id: UUID | None = None) -> None:
        active_count = sum(
            1
            for p in self._repo.list_projects(user_id)
            if p.status == ProjectStatus.active and p.id != exclude_id
        )
        if active_count >= MAX_ACTIVE_PROJECTS:
            raise AppError(
                409,
                "MAX_ACTIVE_PROJECTS_REACHED",
                f"Limite de {MAX_ACTIVE_PROJECTS} projets actifs atteinte : mettez en pause, terminez ou archivez un projet avant d’en activer un nouveau.",
            )

    def _clear_stale_priority(self, user_id: UUID, project_id: UUID, project_name: str) -> None:
        profile = self._profile_repo.get(user_id)
        if profile is None or profile.active_priority_project_id != project_id:
            return
        profile_updates: dict[str, object] = {
            "active_priority_project_id": None,
            "updated_at": datetime.now(timezone.utc),
        }
        if profile.active_priority_task_id is None and profile.active_priority_title == project_name:
            profile_updates["active_priority_title"] = None
        self._profile_repo.save(profile.model_copy(update=profile_updates))

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
        if payload.status == ProjectStatus.active:
            self._ensure_active_slot_available(user_id)
        now = datetime.now(timezone.utc)
        record = ProjectRecord(
            id=uuid4(),
            user_id=user_id,
            category=payload.category or "project",
            name=payload.name,
            description=payload.description,
            goal=payload.goal,
            status=payload.status,
            priority=payload.priority,
            motivation=payload.motivation,
            start_date=payload.start_date or now,
            weekly_target_minutes=payload.weekly_target_minutes,
            next_action=payload.next_action,
            steps=payload.steps or [],
            deliverables=payload.deliverables,
            success_criteria=payload.success_criteria or [],
            progress_history=[
                {
                    "timestamp": now.isoformat(),
                    "event": "created",
                    "summary": f"Projet « {payload.name} » initialisé ({payload.status.value}).",
                }
            ],
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
        if next_status == ProjectStatus.active and existing.status != ProjectStatus.active:
            self._ensure_active_slot_available(user_id, exclude_id=project_id)
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
        if "category" in fields and payload.category is not None:
            updates["category"] = payload.category
        if "description" in fields:
            updates["description"] = payload.description
        if "goal" in fields and payload.goal is not None:
            updates["goal"] = payload.goal
        if "priority" in fields and payload.priority is not None:
            updates["priority"] = payload.priority
        if "motivation" in fields:
            updates["motivation"] = payload.motivation
        if "start_date" in fields:
            updates["start_date"] = payload.start_date
        if "weekly_target_minutes" in fields and payload.weekly_target_minutes is not None:
            updates["weekly_target_minutes"] = payload.weekly_target_minutes
        if "steps" in fields and payload.steps is not None:
            updates["steps"] = payload.steps
        if "deliverables" in fields:
            updates["deliverables"] = payload.deliverables
        if "success_criteria" in fields and payload.success_criteria is not None:
            updates["success_criteria"] = payload.success_criteria
        if "target_date" in fields:
            updates["target_date"] = payload.target_date

        saved = self._repo.save(existing.model_copy(update=updates))
        if saved.status in INACTIVE_PROJECT_STATUSES:
            self._clear_stale_priority(user_id, saved.id, existing.name)
            if saved.name != existing.name:
                self._clear_stale_priority(user_id, saved.id, saved.name)
        elif "name" in fields and payload.name is not None:
            profile = self._profile_repo.get(user_id)
            if (
                profile is not None
                and profile.active_priority_project_id == project_id
                and profile.active_priority_task_id is None
            ):
                self._profile_repo.save(
                    profile.model_copy(
                        update={"active_priority_title": saved.name, "updated_at": now}
                    )
                )
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
