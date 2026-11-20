from datetime import datetime, timezone
from uuid import UUID, uuid4
from app.core.errors import AppError
from app.repositories.learning_sql import (
    LearningModuleRecord,
    LearningPathRecord,
    LessonRecord,
    SqlLearningRepository,
)
from app.schemas.learning import (
    LearningModuleCreate,
    LearningModuleResponse,
    LearningModuleUpdate,
    LearningOverviewResponse,
    LearningPathCreate,
    LearningPathResponse,
    LearningPathUpdate,
    LessonCreate,
    LessonResponse,
    LessonUpdate,
)


class LearningService:
    def __init__(self, repo: SqlLearningRepository) -> None:
        self._repo = repo

    def get_overview(self, user_id: UUID) -> LearningOverviewResponse:
        return LearningOverviewResponse(
            paths=self.list_paths(user_id),
            modules=self.list_modules(user_id),
            lessons=self.list_lessons(user_id),
        )

    def list_paths(self, user_id: UUID) -> list[LearningPathResponse]:
        records = self._repo.list_paths(user_id)
        records.sort(key=lambda item: item.created_at)
        return [LearningPathResponse.model_validate(item.model_dump()) for item in records]

    def create_path(self, user_id: UUID, payload: LearningPathCreate) -> LearningPathResponse:
        now = datetime.now(timezone.utc)
        record = LearningPathRecord(
            id=uuid4(),
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            goal=payload.goal,
            created_at=now,
            updated_at=now,
        )
        saved = self._repo.save_path(record)
        return LearningPathResponse.model_validate(saved.model_dump())

    def update_path(
        self,
        user_id: UUID,
        path_id: UUID,
        payload: LearningPathUpdate,
    ) -> LearningPathResponse:
        existing = self._repo.get_path(user_id, path_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Parcours d’apprentissage introuvable.")

        fields = payload.model_fields_set
        updates: dict[str, object] = {"updated_at": datetime.now(timezone.utc)}
        if "title" in fields and payload.title is not None:
            updates["title"] = payload.title
        if "description" in fields:
            updates["description"] = payload.description
        if "goal" in fields and payload.goal is not None:
            updates["goal"] = payload.goal
        if "status" in fields and payload.status is not None:
            updates["status"] = payload.status

        saved = self._repo.save_path(existing.model_copy(update=updates))
        return LearningPathResponse.model_validate(saved.model_dump())

    def delete_path(self, user_id: UUID, path_id: UUID) -> None:
        modules = self._repo.list_modules(user_id, path_id=path_id)
        module_ids = [module.id for module in modules]
        lesson_ids = [
            lesson.id
            for module_id in module_ids
            for lesson in self._repo.list_lessons(user_id, module_id=module_id)
        ]
        if not self._repo.delete_path(user_id, path_id):
            raise AppError(404, "NOT_FOUND", "Parcours d’apprentissage introuvable.")
        self._repo.detach_lessons(user_id, lesson_ids)
        self._repo.detach_modules(user_id, module_ids)

    def list_modules(
        self,
        user_id: UUID,
        *,
        path_id: UUID | None = None,
    ) -> list[LearningModuleResponse]:
        if path_id is not None and self._repo.get_path(user_id, path_id) is None:
            raise AppError(404, "NOT_FOUND", "Parcours d’apprentissage introuvable.")
        records = self._repo.list_modules(user_id, path_id=path_id)
        records.sort(key=lambda item: (item.position, item.created_at))
        return [LearningModuleResponse.model_validate(item.model_dump()) for item in records]

    def create_module(
        self,
        user_id: UUID,
        payload: LearningModuleCreate,
    ) -> LearningModuleResponse:
        if self._repo.get_path(user_id, payload.path_id) is None:
            raise AppError(404, "NOT_FOUND", "Parcours d’apprentissage introuvable.")
        now = datetime.now(timezone.utc)
        record = LearningModuleRecord(
            id=uuid4(),
            user_id=user_id,
            path_id=payload.path_id,
            title=payload.title,
            description=payload.description,
            position=payload.position,
            status=payload.status,
            created_at=now,
            updated_at=now,
        )
        saved = self._repo.save_module(record)
        return LearningModuleResponse.model_validate(saved.model_dump())

    def update_module(
        self,
        user_id: UUID,
        module_id: UUID,
        payload: LearningModuleUpdate,
    ) -> LearningModuleResponse:
        existing = self._repo.get_module(user_id, module_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Module d’apprentissage introuvable.")

        fields = payload.model_fields_set
        updates: dict[str, object] = {"updated_at": datetime.now(timezone.utc)}
        if "title" in fields and payload.title is not None:
            updates["title"] = payload.title
        if "description" in fields:
            updates["description"] = payload.description
        if "position" in fields and payload.position is not None:
            updates["position"] = payload.position
        if "status" in fields and payload.status is not None:
            updates["status"] = payload.status

        saved = self._repo.save_module(existing.model_copy(update=updates))
        return LearningModuleResponse.model_validate(saved.model_dump())

    def delete_module(self, user_id: UUID, module_id: UUID) -> None:
        lesson_ids = [
            lesson.id for lesson in self._repo.list_lessons(user_id, module_id=module_id)
        ]
        if not self._repo.delete_module(user_id, module_id):
            raise AppError(404, "NOT_FOUND", "Module d’apprentissage introuvable.")
        self._repo.detach_lessons(user_id, lesson_ids)
        self._repo.detach_modules(user_id, [module_id])

    def list_lessons(
        self,
        user_id: UUID,
        *,
        module_id: UUID | None = None,
    ) -> list[LessonResponse]:
        if module_id is not None and self._repo.get_module(user_id, module_id) is None:
            raise AppError(404, "NOT_FOUND", "Module d’apprentissage introuvable.")
        records = self._repo.list_lessons(user_id, module_id=module_id)
        records.sort(key=lambda item: (item.position, item.created_at))
        return [LessonResponse.model_validate(item.model_dump()) for item in records]

    def create_lesson(self, user_id: UUID, payload: LessonCreate) -> LessonResponse:
        if self._repo.get_module(user_id, payload.module_id) is None:
            raise AppError(404, "NOT_FOUND", "Module d’apprentissage introuvable.")
        now = datetime.now(timezone.utc)
        record = LessonRecord(
            id=uuid4(),
            user_id=user_id,
            module_id=payload.module_id,
            title=payload.title,
            content=payload.content,
            resource_url=payload.resource_url,
            position=payload.position,
            status=payload.status,
            created_at=now,
            updated_at=now,
        )
        saved = self._repo.save_lesson(record)
        return LessonResponse.model_validate(saved.model_dump())

    def update_lesson(
        self,
        user_id: UUID,
        lesson_id: UUID,
        payload: LessonUpdate,
    ) -> LessonResponse:
        """Met à jour une leçon sans jamais modifier automatiquement les compétences (LEARN-03)."""
        existing = self._repo.get_lesson(user_id, lesson_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Leçon introuvable.")

        fields = payload.model_fields_set
        updates: dict[str, object] = {"updated_at": datetime.now(timezone.utc)}
        if "title" in fields and payload.title is not None:
            updates["title"] = payload.title
        if "content" in fields:
            updates["content"] = payload.content
        if "resource_url" in fields:
            updates["resource_url"] = payload.resource_url
        if "position" in fields and payload.position is not None:
            updates["position"] = payload.position
        if "status" in fields and payload.status is not None:
            updates["status"] = payload.status

        saved = self._repo.save_lesson(existing.model_copy(update=updates))
        return LessonResponse.model_validate(saved.model_dump())

    def delete_lesson(self, user_id: UUID, lesson_id: UUID) -> None:
        if not self._repo.delete_lesson(user_id, lesson_id):
            raise AppError(404, "NOT_FOUND", "Leçon introuvable.")
        self._repo.detach_lessons(user_id, [lesson_id])
