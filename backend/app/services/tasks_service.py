from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from app.core.errors import AppError
from app.repositories.memory import (
    ProfileRepository,
    SessionRepository,
    TaskRecord,
    TaskRepository,
)
from app.schemas.common import TaskPriority, TaskSource, TaskStatus
from app.schemas.tasks import TaskCreate, TaskResponse, TaskSummary, TaskUpdate

PRIORITY_WEIGHT: dict[TaskPriority, int] = {
    TaskPriority.critical: 4,
    TaskPriority.high: 3,
    TaskPriority.normal: 2,
    TaskPriority.low: 1,
}

MAX_ACTIVE_CRITICAL_TASKS = 3


def is_active_task_status(status: TaskStatus) -> bool:
    return status in (TaskStatus.todo, TaskStatus.in_progress)


def is_task_overdue(
    task: TaskRecord,
    tz_name: str,
    now_utc: datetime | None = None,
) -> bool:
    if task.due_at is None or not is_active_task_status(task.status):
        return False
    tz = ZoneInfo(tz_name)
    reference_now = (now_utc or datetime.now(timezone.utc)).astimezone(tz)
    due_local_date = task.due_at.astimezone(tz).date()
    return due_local_date < reference_now.date()


def is_task_due_today(
    task: TaskRecord,
    tz_name: str,
    now_utc: datetime | None = None,
) -> bool:
    if task.due_at is None:
        return False
    tz = ZoneInfo(tz_name)
    reference_now = (now_utc or datetime.now(timezone.utc)).astimezone(tz)
    return task.due_at.astimezone(tz).date() == reference_now.date()


def sort_tasks_by_urgency(
    tasks: list[TaskRecord],
    tz_name: str = "Africa/Dakar",
    now_utc: datetime | None = None,
) -> list[TaskRecord]:
    max_utc = datetime.max.replace(tzinfo=timezone.utc)
    return sorted(
        tasks,
        key=lambda task: (
            not is_task_overdue(task, tz_name, now_utc),
            -PRIORITY_WEIGHT[task.priority],
            task.due_at is None,
            task.due_at or max_utc,
            -task.created_at.timestamp(),
        ),
    )


def compute_task_summary(
    tasks: list[TaskRecord],
    tz_name: str,
    now_utc: datetime | None = None,
) -> TaskSummary:
    active_count = 0
    done_count = 0
    parked_count = 0
    cancelled_count = 0
    overdue_count = 0

    for task in tasks:
        if is_active_task_status(task.status):
            active_count += 1
            if is_task_overdue(task, tz_name, now_utc):
                overdue_count += 1
        elif task.status == TaskStatus.done:
            done_count += 1
        elif task.status == TaskStatus.parked:
            parked_count += 1
        elif task.status == TaskStatus.cancelled:
            cancelled_count += 1

    denominator = active_count + done_count
    completion_rate = 0 if denominator == 0 else round((done_count / denominator) * 100)
    return TaskSummary(
        active_count=active_count,
        done_count=done_count,
        parked_count=parked_count,
        cancelled_count=cancelled_count,
        overdue_count=overdue_count,
        completion_rate=completion_rate,
    )


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        profile_repo: ProfileRepository,
        session_repo: SessionRepository,
        project_repo: Any | None = None,
        learning_repo: Any | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._profile_repo = profile_repo
        self._session_repo = session_repo
        self._project_repo = project_repo
        self._learning_repo = learning_repo

    def _validate_links(
        self,
        user_id: UUID,
        project_id: UUID | None,
        module_id: UUID | None,
    ) -> None:
        if (
            project_id is not None
            and self._project_repo is not None
            and self._project_repo.get(user_id, project_id) is None
        ):
            raise AppError(404, "NOT_FOUND", "Projet associé introuvable.")
        if (
            module_id is not None
            and self._learning_repo is not None
            and self._learning_repo.get_module(user_id, module_id) is None
        ):
            raise AppError(404, "NOT_FOUND", "Module associé introuvable.")

    def _ensure_critical_slot_available(
        self,
        user_id: UUID,
        exclude_id: UUID | None = None,
    ) -> None:
        active_critical_count = sum(
            1
            for t in self._task_repo.list_by_user(user_id)
            if is_active_task_status(t.status)
            and t.priority == TaskPriority.critical
            and t.id != exclude_id
        )
        if active_critical_count >= MAX_ACTIVE_CRITICAL_TASKS:
            raise AppError(
                409,
                "MAX_CRITICAL_TASKS_REACHED",
                "Limite de 3 tâches critiques actives atteinte : terminez, mettez au parking ou rétrogradez une tâche critique avant d'en ajouter une autre.",
            )

    def list_tasks(
        self,
        user_id: UUID,
        *,
        status_filter: str | None = None,
        priority: TaskPriority | None = None,
        due: str | None = None,
        search: str | None = None,
        tz_name: str = "Africa/Dakar",
        now_utc: datetime | None = None,
    ) -> list[TaskResponse]:
        tasks = self._task_repo.list_by_user(user_id)
        tz = ZoneInfo(tz_name)
        today_local = (now_utc or datetime.now(timezone.utc)).astimezone(tz).date()
        normalized_search = search.strip().lower() if search else ""

        filtered: list[TaskRecord] = []
        for task in tasks:
            if status_filter and status_filter != "all":
                if status_filter == "active":
                    if not is_active_task_status(task.status):
                        continue
                elif task.status.value != status_filter:
                    continue

            if priority is not None and task.priority != priority:
                continue

            if due and due != "all":
                if due == "overdue" and not is_task_overdue(task, tz_name, now_utc):
                    continue
                if due == "today" and (
                    not is_active_task_status(task.status)
                    or not is_task_due_today(task, tz_name, now_utc)
                ):
                    continue
                if due == "upcoming":
                    if (
                        not is_active_task_status(task.status)
                        or task.due_at is None
                        or task.due_at.astimezone(tz).date() <= today_local
                    ):
                        continue
                if due == "no_due" and task.due_at is not None:
                    continue

            if normalized_search:
                haystack = f"{task.title} {task.description or ''}".lower()
                if normalized_search not in haystack:
                    continue

            filtered.append(task)

        ordered = sort_tasks_by_urgency(filtered, tz_name, now_utc)
        return [TaskResponse.model_validate(item.model_dump()) for item in ordered]

    def create_task(
        self,
        user_id: UUID,
        payload: TaskCreate,
        *,
        source: TaskSource = TaskSource.manual,
        proposal_id: UUID | None = None,
    ) -> TaskResponse:
        self._validate_links(user_id, payload.project_id, payload.module_id)
        if is_active_task_status(payload.status) and payload.priority == TaskPriority.critical:
            self._ensure_critical_slot_available(user_id)
        now = datetime.now(timezone.utc)
        record = TaskRecord(
            id=uuid4(),
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            due_at=payload.due_at,
            completed_at=now if payload.status == TaskStatus.done else None,
            source=source,
            proposal_id=proposal_id,
            project_id=payload.project_id,
            module_id=payload.module_id,
            created_at=now,
            updated_at=now,
        )
        saved = self._task_repo.save(record)
        return TaskResponse.model_validate(saved.model_dump())

    def get_task(self, user_id: UUID, task_id: UUID) -> TaskResponse:
        record = self._task_repo.get(user_id, task_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Tâche introuvable.")
        return TaskResponse.model_validate(record.model_dump())

    def update_task(self, user_id: UUID, task_id: UUID, payload: TaskUpdate) -> TaskResponse:
        existing = self._task_repo.get(user_id, task_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Tâche introuvable.")

        now = datetime.now(timezone.utc)
        fields = payload.model_fields_set
        updates: dict[str, object] = {"updated_at": now}

        if "title" in fields and payload.title is not None:
            updates["title"] = payload.title
        if "description" in fields:
            updates["description"] = payload.description
        if "priority" in fields and payload.priority is not None:
            updates["priority"] = payload.priority
        if "due_at" in fields:
            updates["due_at"] = payload.due_at
        if "project_id" in fields:
            self._validate_links(user_id, payload.project_id, None)
            updates["project_id"] = payload.project_id
        if "module_id" in fields:
            self._validate_links(user_id, None, payload.module_id)
            updates["module_id"] = payload.module_id

        next_status = (
            payload.status if "status" in fields and payload.status is not None else existing.status
        )
        next_priority = (
            payload.priority
            if "priority" in fields and payload.priority is not None
            else existing.priority
        )
        was_active_critical = (
            is_active_task_status(existing.status) and existing.priority == TaskPriority.critical
        )
        is_now_active_critical = (
            is_active_task_status(next_status) and next_priority == TaskPriority.critical
        )
        if is_now_active_critical and not was_active_critical:
            self._ensure_critical_slot_available(user_id, exclude_id=task_id)

        if "status" in fields and payload.status is not None:
            updates["status"] = payload.status
            if payload.status == TaskStatus.done:
                updates["completed_at"] = existing.completed_at or now
            else:
                updates["completed_at"] = None

        saved = self._task_repo.save(existing.model_copy(update=updates))

        profile = self._profile_repo.get(user_id)
        if profile is not None and profile.active_priority_task_id == task_id:
            if not is_active_task_status(saved.status):
                profile_updates: dict[str, object] = {
                    "active_priority_task_id": None,
                    "updated_at": now,
                }
                if (
                    profile.active_priority_project_id is None
                    and profile.active_priority_title in (existing.title, saved.title)
                ):
                    profile_updates["active_priority_title"] = None
                self._profile_repo.save(profile.model_copy(update=profile_updates))
            elif "title" in fields and payload.title is not None:
                self._profile_repo.save(
                    profile.model_copy(
                        update={"active_priority_title": saved.title, "updated_at": now}
                    )
                )

        return TaskResponse.model_validate(saved.model_dump())

    def delete_task(self, user_id: UUID, task_id: UUID) -> None:
        deleted = self._task_repo.delete(user_id, task_id)
        if not deleted:
            raise AppError(404, "NOT_FOUND", "Tâche introuvable.")

        self._session_repo.detach_task(user_id, task_id)
        profile = self._profile_repo.get(user_id)
        if profile is not None and profile.active_priority_task_id == task_id:
            self._profile_repo.save(
                profile.model_copy(
                    update={
                        "active_priority_title": None,
                        "active_priority_task_id": None,
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
            )
