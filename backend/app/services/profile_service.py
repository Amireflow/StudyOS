from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from app.core.errors import AppError
from app.repositories.memory import ProfileRecord, ProfileRepository, TaskRepository
from app.schemas.profile import ProfileResponse, ProfileUpdate


class ProfileService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        task_repo: TaskRepository,
        default_timezone: str = "Africa/Dakar",
        project_repo: Any | None = None,
    ) -> None:
        self._profile_repo = profile_repo
        self._task_repo = task_repo
        self._default_timezone = default_timezone
        self._project_repo = project_repo

    def get_or_create_record(self, user_id: UUID) -> ProfileRecord:
        existing = self._profile_repo.get(user_id)
        if existing is not None:
            return existing

        now = datetime.now(timezone.utc)
        created = ProfileRecord(
            id=user_id,
            display_name="Utilisateur",
            timezone=self._default_timezone,
            created_at=now,
            updated_at=now,
        )
        return self._profile_repo.save(created)

    def get_profile(self, user_id: UUID) -> ProfileResponse:
        record = self.get_or_create_record(user_id)
        return ProfileResponse.model_validate(record.model_dump())

    def update_profile(self, user_id: UUID, payload: ProfileUpdate) -> ProfileResponse:
        record = self.get_or_create_record(user_id)
        fields = payload.model_fields_set
        updates: dict[str, object] = {"updated_at": datetime.now(timezone.utc)}

        if "display_name" in fields and payload.display_name is not None:
            updates["display_name"] = payload.display_name

        if "timezone" in fields and payload.timezone is not None:
            updates["timezone"] = payload.timezone

        if "preferences" in fields and payload.preferences is not None:
            updates["preferences"] = payload.preferences

        if "ai_instructions" in fields:
            updates["ai_instructions"] = payload.ai_instructions

        if "active_priority_project_id" in fields:
            if payload.active_priority_project_id is None:
                updates["active_priority_project_id"] = None
            else:
                project = (
                    self._project_repo.get(user_id, payload.active_priority_project_id)
                    if self._project_repo is not None
                    else None
                )
                if self._project_repo is not None and project is None:
                    raise AppError(404, "NOT_FOUND", "Projet prioritaire introuvable.")
                updates["active_priority_project_id"] = payload.active_priority_project_id
                if (
                    project is not None
                    and "active_priority_title" not in fields
                    and "active_priority_task_id" not in fields
                    and record.active_priority_task_id is None
                ):
                    updates["active_priority_title"] = project.name

        if "active_priority_task_id" in fields:
            if payload.active_priority_task_id is None:
                updates["active_priority_task_id"] = None
            else:
                task = self._task_repo.get(user_id, payload.active_priority_task_id)
                if task is None:
                    raise AppError(404, "NOT_FOUND", "Tâche prioritaire introuvable.")
                updates["active_priority_task_id"] = task.id
                if "active_priority_title" not in fields:
                    updates["active_priority_title"] = task.title

        if "active_priority_title" in fields:
            updates["active_priority_title"] = payload.active_priority_title
            if payload.active_priority_title is None and "active_priority_task_id" not in fields:
                updates["active_priority_task_id"] = None

        updated = record.model_copy(update=updates)
        saved = self._profile_repo.save(updated)
        return ProfileResponse.model_validate(saved.model_dump())
