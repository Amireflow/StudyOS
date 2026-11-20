from collections.abc import Generator
from datetime import datetime, timezone
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from app.ai.action_validator import ActionValidator
from app.ai.context_builder import ContextBuilder
from app.ai.orchestrator import AIOrchestrator
from app.ai.prompt_manager import PromptManager
from app.ai.provider import AIProvider, build_ai_provider
from app.ai.tool_registry import ToolRegistry
from app.core.config import Settings
from app.core.security import get_app_settings
from app.repositories.ai_sql import SqlAiRepository
from app.repositories.learning_sql import (
    SqlLearningRepository,
    SqlProjectRepository,
    SqlSkillRepository,
)
from app.repositories.memory import (
    ProfileRepository,
    ScheduleRepository,
    SessionRepository,
    TaskRepository,
)
from app.repositories.sql import (
    SqlProfileRepository,
    SqlScheduleRepository,
    SqlSessionRepository,
    SqlTaskRepository,
)
from app.services.dashboard_service import DashboardService
from app.services.learning_service import LearningService
from app.services.profile_service import ProfileService
from app.services.projects_service import ProjectService
from app.services.schedule_service import ScheduleService
from app.services.sessions_service import SessionService
from app.services.skills_service import SkillService
from app.services.tasks_service import TaskService


def get_db_session(request: Request) -> Generator[Session | None, None, None]:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        yield None
        return

    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_profile_repository(
    request: Request,
    db: Session | None = Depends(get_db_session),
) -> ProfileRepository | SqlProfileRepository:
    if db is not None:
        return SqlProfileRepository(db)
    return ProfileRepository(request.app.state.store)


def get_task_repository(
    request: Request,
    db: Session | None = Depends(get_db_session),
) -> TaskRepository | SqlTaskRepository:
    if db is not None:
        return SqlTaskRepository(db)
    return TaskRepository(request.app.state.store)


def get_schedule_repository(
    request: Request,
    db: Session | None = Depends(get_db_session),
) -> ScheduleRepository | SqlScheduleRepository:
    if db is not None:
        return SqlScheduleRepository(db)
    return ScheduleRepository(request.app.state.store)


def get_session_repository(
    request: Request,
    db: Session | None = Depends(get_db_session),
) -> SessionRepository | SqlSessionRepository:
    if db is not None:
        return SqlSessionRepository(db)
    return SessionRepository(request.app.state.store)


def get_learning_repository(
    db: Session | None = Depends(get_db_session),
) -> SqlLearningRepository:
    if db is None:
        raise RuntimeError("Une base SQLAlchemy est requise pour les parcours d’apprentissage.")
    return SqlLearningRepository(db)


def get_skill_repository(
    db: Session | None = Depends(get_db_session),
) -> SqlSkillRepository:
    if db is None:
        raise RuntimeError("Une base SQLAlchemy est requise pour les compétences.")
    return SqlSkillRepository(db)


def get_project_repository(
    db: Session | None = Depends(get_db_session),
) -> SqlProjectRepository:
    if db is None:
        raise RuntimeError("Une base SQLAlchemy est requise pour les projets.")
    return SqlProjectRepository(db)


def get_profile_service(
    profile_repo: ProfileRepository | SqlProfileRepository = Depends(get_profile_repository),
    task_repo: TaskRepository | SqlTaskRepository = Depends(get_task_repository),
    settings: Settings = Depends(get_app_settings),
    db: Session | None = Depends(get_db_session),
) -> ProfileService:
    project_repo = SqlProjectRepository(db) if db is not None else None
    return ProfileService(
        profile_repo=profile_repo,  # type: ignore[arg-type]
        task_repo=task_repo,  # type: ignore[arg-type]
        default_timezone=settings.default_timezone,
        project_repo=project_repo,
    )


def get_task_service(
    task_repo: TaskRepository | SqlTaskRepository = Depends(get_task_repository),
    profile_repo: ProfileRepository | SqlProfileRepository = Depends(get_profile_repository),
    session_repo: SessionRepository | SqlSessionRepository = Depends(get_session_repository),
    db: Session | None = Depends(get_db_session),
) -> TaskService:
    return TaskService(
        task_repo=task_repo,  # type: ignore[arg-type]
        profile_repo=profile_repo,  # type: ignore[arg-type]
        session_repo=session_repo,  # type: ignore[arg-type]
        project_repo=SqlProjectRepository(db) if db is not None else None,
        learning_repo=SqlLearningRepository(db) if db is not None else None,
    )


def get_schedule_service(
    schedule_repo: ScheduleRepository | SqlScheduleRepository = Depends(get_schedule_repository),
) -> ScheduleService:
    return ScheduleService(schedule_repo=schedule_repo)  # type: ignore[arg-type]


def get_session_service(
    session_repo: SessionRepository | SqlSessionRepository = Depends(get_session_repository),
    task_repo: TaskRepository | SqlTaskRepository = Depends(get_task_repository),
    db: Session | None = Depends(get_db_session),
) -> SessionService:
    return SessionService(
        session_repo=session_repo,  # type: ignore[arg-type]
        task_repo=task_repo,  # type: ignore[arg-type]
        project_repo=SqlProjectRepository(db) if db is not None else None,
        learning_repo=SqlLearningRepository(db) if db is not None else None,
        skill_repo=SqlSkillRepository(db) if db is not None else None,
    )


def get_learning_service(
    learning_repo: SqlLearningRepository = Depends(get_learning_repository),
) -> LearningService:
    return LearningService(repo=learning_repo)


def get_skill_service(
    skill_repo: SqlSkillRepository = Depends(get_skill_repository),
) -> SkillService:
    return SkillService(repo=skill_repo)


def get_project_service(
    project_repo: SqlProjectRepository = Depends(get_project_repository),
    profile_repo: ProfileRepository | SqlProfileRepository = Depends(get_profile_repository),
) -> ProjectService:
    return ProjectService(
        repo=project_repo,
        profile_repo=profile_repo,  # type: ignore[arg-type]
    )


def get_ai_repository(
    db: Session | None = Depends(get_db_session),
) -> SqlAiRepository:
    if db is None:
        raise RuntimeError("Une base SQLAlchemy est requise pour le Copilote IA.")
    return SqlAiRepository(db)


def get_ai_provider(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> AIProvider:
    custom_provider = getattr(request.app.state, "ai_provider", None)
    if custom_provider is not None:
        return custom_provider
    return build_ai_provider(settings)


def get_ai_orchestrator(
    ai_repo: SqlAiRepository = Depends(get_ai_repository),
    profile_service: ProfileService = Depends(get_profile_service),
    task_repo: TaskRepository | SqlTaskRepository = Depends(get_task_repository),
    schedule_repo: ScheduleRepository | SqlScheduleRepository = Depends(get_schedule_repository),
    session_repo: SessionRepository | SqlSessionRepository = Depends(get_session_repository),
    learning_repo: SqlLearningRepository = Depends(get_learning_repository),
    skill_repo: SqlSkillRepository = Depends(get_skill_repository),
    project_repo: SqlProjectRepository = Depends(get_project_repository),
    task_service: TaskService = Depends(get_task_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    skill_service: SkillService = Depends(get_skill_service),
    provider: AIProvider = Depends(get_ai_provider),
    settings: Settings = Depends(get_app_settings),
) -> AIOrchestrator:
    tool_registry = ToolRegistry()
    context_builder = ContextBuilder(
        profile_service=profile_service,
        task_repo=task_repo,  # type: ignore[arg-type]
        schedule_repo=schedule_repo,  # type: ignore[arg-type]
        session_repo=session_repo,  # type: ignore[arg-type]
        learning_repo=learning_repo,
        skill_repo=skill_repo,
        project_repo=project_repo,
    )
    prompt_manager = PromptManager(tool_registry=tool_registry)
    action_validator = ActionValidator(
        tool_registry=tool_registry,
        task_repo=task_repo,  # type: ignore[arg-type]
        schedule_repo=schedule_repo,  # type: ignore[arg-type]
        learning_repo=learning_repo,
        skill_repo=skill_repo,
        project_repo=project_repo,
    )
    return AIOrchestrator(
        ai_repo=ai_repo,
        tool_registry=tool_registry,
        context_builder=context_builder,
        prompt_manager=prompt_manager,
        action_validator=action_validator,
        provider=provider,
        task_service=task_service,
        schedule_service=schedule_service,
        skill_service=skill_service,
        rate_limit_per_minute=settings.ai_rate_limit_per_minute,
    )


def get_dashboard_service(
    profile_service: ProfileService = Depends(get_profile_service),
    task_repo: TaskRepository | SqlTaskRepository = Depends(get_task_repository),
    schedule_repo: ScheduleRepository | SqlScheduleRepository = Depends(get_schedule_repository),
    session_repo: SessionRepository | SqlSessionRepository = Depends(get_session_repository),
) -> DashboardService:
    return DashboardService(
        profile_service=profile_service,
        task_repo=task_repo,  # type: ignore[arg-type]
        schedule_repo=schedule_repo,  # type: ignore[arg-type]
        session_repo=session_repo,  # type: ignore[arg-type]
    )
