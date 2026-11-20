from datetime import datetime, timedelta, timezone
import json
import logging
import re
from typing import Any, Callable, Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from app.ai.action_validator import ActionValidator
from app.ai.context_builder import ContextBuilder
from app.ai.prompt_manager import PromptManager
from app.ai.provider import (
    AIProvider,
    GEMINI_DEFAULT_BASE_URL,
    OPENAI_DEFAULT_BASE_URL,
    RIVER_DEFAULT_BASE_URL,
    _PROTOCOL_JSON_MARKERS_RE,
    _parse_llm_json_output,
    _validate_outbound_base_url,
    build_ai_provider_from_config,
    canonicalize_provider_name,
    fetch_provider_models,
    normalize_provider_base_url,
)
from app.ai.tool_registry import ToolRegistry
from app.core.config import Settings
from app.core.errors import AppError
from app.core.ssrf import validate_model_identifier
from app.services.rate_limiter import (
    MODELS_PROBE_IP_MAX_ATTEMPTS,
    MODELS_PROBE_WINDOW_SECONDS,
    PersistentRateLimiter,
)
from app.repositories.ai_sql import (
    AiActionProposalRecord,
    AiConversationRecord,
    AiMessageRecord,
    AiReportRecord,
    SqlAiMemoryRepository,
    SqlAiRepository,
)
from app.repositories.learning_sql import SqlPersonalGoalRepository
from app.schemas.ai import (
    AcceptProposalRequest,
    AiActionProposalResponse,
    AiConversationCreate,
    AiConversationDetailResponse,
    AiConversationResponse,
    AiMemoryResponse,
    AiMemoryUpdateRequest,
    AiMessageCreate,
    AiMessageResponse,
    AiProviderCatalogItem,
    AiProviderConfigResponse,
    AiProviderConfigUpdate,
    AiProviderModelInfo,
    AiReportResponse,
    AiToolSpec,
    AiTurnResponse,
    EnsureAiReportsResponse,
    FetchProviderModelsRequest,
    FetchProviderModelsResponse,
    RejectProposalRequest,
    UpdateProposalRequest,
)
from app.schemas.common import (
    AiActionType,
    AiContextScope,
    AiMessageRole,
    AiReportType,
    LearningStatus,
    ObjectiveCategory,
    ObjectiveStatus,
    ProjectStatus,
    ProposalStatus,
    ScheduleEventSource,
    ScheduleEventType,
    SkillAssessmentType,
    SkillEvidenceType,
    TaskPriority,
    TaskSource,
    TaskStatus,
)
from app.schemas.courses import CourseCreate
from app.schemas.learning import LearningModuleCreate, LearningPathCreate, LearningPathUpdate, LessonCreate
from app.schemas.objectives import PersonalGoalCreate, PersonalGoalUpdate
from app.schemas.profile import ProfileUpdate
from app.schemas.projects import ProjectCreate, ProjectUpdate
from app.schemas.schedule import ScheduleEventCreate, ScheduleEventUpdate
from app.schemas.sessions import SessionCreate
from app.schemas.skills import (
    SkillAssessmentCreate,
    SkillAssessmentDecision,
    SkillCreate,
    SkillEvidenceCreate,
)
from app.schemas.tasks import TaskCreate, TaskUpdate
from app.planning.service import LearningPlanningService
from app.services.courses_service import CourseService
from app.services.learning_service import LearningService
from app.services.objectives_service import ObjectivesService
from app.services.profile_service import ProfileService
from app.services.projects_service import ProjectService
from app.services.schedule_service import ScheduleService, do_events_overlap
from app.services.sessions_service import SessionService
from app.services.skills_service import SkillService
from app.services.tasks_service import TaskService

logger = logging.getLogger("amireflow.study_os.ai")

PROPOSAL_TTL_DAYS = 7
MAX_HISTORY_MESSAGES = 12


def _build_bounded_history(existing_messages: list[AiMessageRecord]) -> list[dict[str, str]]:
    chat_msgs = [
        m
        for m in existing_messages
        if m.role in (AiMessageRole.user, AiMessageRole.assistant)
    ]
    if len(chat_msgs) <= MAX_HISTORY_MESSAGES:
        return [{"role": m.role.value, "content": m.content} for m in chat_msgs]

    older = chat_msgs[:-MAX_HISTORY_MESSAGES]
    recent = chat_msgs[-MAX_HISTORY_MESSAGES:]
    summary_snippets = [
        f"{m.role.value}: {' '.join(m.content.split())[:80]}" for m in older[-6:]
    ]
    summary_turn = {
        "role": "user",
        "content": (
            f"[Contexte des {len(older)} message(s) précédent(s) de la conversation : "
            + " | ".join(summary_snippets)
            + "]"
        ),
    }
    return [summary_turn, *[{"role": m.role.value, "content": m.content} for m in recent]]

PROVIDER_CATALOG: list[AiProviderCatalogItem] = [
    AiProviderCatalogItem(
        id="river",
        label="River AI (console.river.ai)",
        console_url="https://console.river.ai",
        default_base_url=RIVER_DEFAULT_BASE_URL,
        requires_api_key=True,
    ),
    AiProviderCatalogItem(
        id="local",
        label="Moteur local déterministe (règles métier, sans LLM)",
        console_url=None,
        default_base_url="",
        requires_api_key=False,
    ),
    AiProviderCatalogItem(
        id="openai_compatible",
        label="OpenAI / Compatible",
        console_url="https://platform.openai.com",
        default_base_url=OPENAI_DEFAULT_BASE_URL,
        requires_api_key=True,
    ),
    AiProviderCatalogItem(
        id="gemini",
        label="Google Gemini",
        console_url="https://aistudio.google.com",
        default_base_url=GEMINI_DEFAULT_BASE_URL,
        requires_api_key=True,
    ),
]


def _mask_api_key(api_key: str) -> str | None:
    cleaned = (api_key or "").strip()
    if not cleaned:
        return None
    if len(cleaned) <= 8:
        return "••••"
    return f"{cleaned[:4]}…{cleaned[-4:]}"


def _default_model_for_provider(provider_key: str) -> str:
    if provider_key == "local":
        return "local-coach-v1"
    if provider_key == "gemini":
        return "gemini-2.5-flash"
    return "gpt-4o-mini"


class _RollbackAppError(AppError):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        rollback_info: dict[str, Any],
    ) -> None:
        super().__init__(status_code, code, message)
        self.rollback_info = rollback_info


class AIOrchestrator:
    """Coordonne les conversations IA, le contexte contrôlé, les propositions et les bilans (AI-01 à AI-07)."""

    def __init__(
        self,
        *,
        ai_repo: SqlAiRepository,
        tool_registry: ToolRegistry,
        context_builder: ContextBuilder,
        prompt_manager: PromptManager,
        action_validator: ActionValidator,
        provider: AIProvider,
        task_service: TaskService,
        schedule_service: ScheduleService,
        skill_service: SkillService,
        learning_service: LearningService | None = None,
        project_service: ProjectService | None = None,
        course_service: CourseService | None = None,
        profile_service: ProfileService | None = None,
        objectives_service: ObjectivesService | None = None,
        planning_service: LearningPlanningService | None = None,
        session_service: SessionService | None = None,
        ai_memory_repo: SqlAiMemoryRepository | None = None,
        goal_repo: SqlPersonalGoalRepository | None = None,
        settings: Settings | None = None,
        has_custom_provider: bool = False,
        rate_limit_per_minute: int = 30,
    ) -> None:
        self._ai_repo = ai_repo
        self._tool_registry = tool_registry
        self._context_builder = context_builder
        self._prompt_manager = prompt_manager
        self._action_validator = action_validator
        self._provider = provider
        self._task_service = task_service
        self._schedule_service = schedule_service
        self._skill_service = skill_service
        self._learning_service = learning_service
        self._project_service = project_service
        self._course_service = course_service
        self._profile_service = profile_service or getattr(context_builder, "_profile_service", None)
        self._objectives_service = objectives_service
        self._planning_service = planning_service
        self._session_service = session_service
        self._ai_memory_repo = ai_memory_repo or getattr(context_builder, "_ai_memory_repo", None)
        self._goal_repo = goal_repo or getattr(context_builder, "_goal_repo", None)
        self._settings = settings
        self._has_custom_provider = has_custom_provider
        self._rate_limit = rate_limit_per_minute

    def list_tools(self) -> list[AiToolSpec]:
        return self._tool_registry.list_tools()

    def _sync_availability_to_profile(
        self,
        user_id: UUID,
        avail_patch: dict[str, Any],
        *,
        weekly_study_hours: int | None = None,
        default_session_minutes: int | None = None,
        ai_instructions: str | None = None,
    ) -> None:
        if self._profile_service is None:
            return
        profile = self._profile_service.get_or_create_record(user_id)
        prefs = dict(profile.preferences or {})
        nested = dict(prefs.get("availability") or {}) if isinstance(prefs.get("availability"), dict) else {}
        for k, v in avail_patch.items():
            if v is not None:
                prefs[k] = v
                nested[k] = v
        if weekly_study_hours is not None:
            prefs["weekly_study_hours"] = weekly_study_hours
            nested["weekly_study_hours"] = weekly_study_hours
        if default_session_minutes is not None:
            prefs["preferred_session_minutes"] = default_session_minutes
            nested["preferred_session_minutes"] = default_session_minutes
        prefs["availability"] = nested
        update_kwargs: dict[str, Any] = {"preferences": prefs}
        if ai_instructions is not None:
            update_kwargs["ai_instructions"] = ai_instructions
        self._profile_service.update_profile(user_id, ProfileUpdate(**update_kwargs))

    def get_memory(self, user_id: UUID) -> AiMemoryResponse:
        if self._ai_memory_repo is None:
            raise AppError(500, "MEMORY_UNAVAILABLE", "La mémoire IA structurée n’est pas configurée.")
        rec = self._ai_memory_repo.get_or_create(user_id)
        return AiMemoryResponse.model_validate(rec.model_dump())

    def update_memory(self, user_id: UUID, payload: AiMemoryUpdateRequest) -> AiMemoryResponse:
        if self._ai_memory_repo is None:
            raise AppError(500, "MEMORY_UNAVAILABLE", "La mémoire IA structurée n’est pas configurée.")
        updates = payload.model_dump(exclude_unset=True)
        saved = self._ai_memory_repo.patch(user_id, **updates)
        if any(
            k in updates
            for k in ("availability_preferences", "weekly_study_hours", "default_session_minutes")
        ):
            self._sync_availability_to_profile(
                user_id,
                dict(saved.availability_preferences or {}),
                weekly_study_hours=saved.weekly_study_hours,
                default_session_minutes=saved.default_session_minutes,
            )
        return AiMemoryResponse.model_validate(saved.model_dump())

    def _safe_rollback(self, compensations: list[Callable[[], None]]) -> None:
        for undo in reversed(compensations):
            try:
                undo()
            except Exception:
                logger.warning("ai_compensation_rollback_failed", exc_info=True)

    def _record_memory_after_execution(
        self,
        user_id: UUID,
        *,
        proposal: AiActionProposalRecord,
        action_enum: AiActionType,
        execution_result: dict[str, Any],
    ) -> None:
        if self._ai_memory_repo is None:
            return
        now_iso = datetime.now(timezone.utc).isoformat()
        self._ai_memory_repo.append_execution(
            user_id,
            {
                "proposal_id": str(proposal.id),
                "action_type": action_enum.value,
                "summary": proposal.title,
                "entity": execution_result.get("entity"),
                "executed_at": now_iso,
            },
        )
        if action_enum in (
            AiActionType.plan_strategic_activity,
            AiActionType.create_personal_goal,
            AiActionType.update_personal_goal,
            AiActionType.update_preferences,
            AiActionType.manage_availability_rule,
            AiActionType.generate_learning_plan,
            AiActionType.pause_project,
            AiActionType.create_project,
            AiActionType.create_skill,
            AiActionType.batch_actions,
        ):
            self._ai_memory_repo.append_decision(
                user_id,
                {
                    "action_type": action_enum.value,
                    "summary": proposal.title,
                    "decided_at": now_iso,
                },
            )

    def _is_custom_base_url(self, provider_key: str, resolved_base_url: str) -> bool:
        default_url = normalize_provider_base_url(provider_key, None)
        if not resolved_base_url or resolved_base_url == default_url:
            return False
        if self._settings is not None:
            env_provider = canonicalize_provider_name(self._settings.ai_provider)
            env_url = normalize_provider_base_url(env_provider, self._settings.ai_base_url)
            if env_provider == provider_key and resolved_base_url == env_url:
                return False
        return True

    def _resolve_effective_ai_config(
        self,
        user_id: UUID,
    ) -> tuple[str, str, str, str, Literal["user", "server_env", "default"]]:
        saved = (
            self._profile_service.get_ai_provider_config(user_id)
            if self._profile_service is not None
            else None
        )
        if saved:
            provider_key = canonicalize_provider_name(saved.get("provider"))
            base_url = normalize_provider_base_url(provider_key, saved.get("base_url"))
            api_key = str(saved.get("api_key") or "").strip()
            if (
                not api_key
                and self._settings is not None
                and canonicalize_provider_name(self._settings.ai_provider) == provider_key
                and not self._is_custom_base_url(provider_key, base_url)
            ):
                api_key = (self._settings.ai_api_key or "").strip()
            model = str(saved.get("model") or "").strip() or _default_model_for_provider(provider_key)
            return provider_key, api_key, base_url, model, "user"

        if self._settings is not None:
            provider_key = canonicalize_provider_name(self._settings.ai_provider)
            api_key = (self._settings.ai_api_key or "").strip()
            base_url = normalize_provider_base_url(provider_key, self._settings.ai_base_url)
            model = (self._settings.ai_model or "").strip() or _default_model_for_provider(provider_key)
            source: Literal["server_env", "default"] = (
                "server_env" if (provider_key != "local" or bool(api_key)) else "default"
            )
            return provider_key, api_key, base_url, model, source

        return "local", "", "", "local-coach-v1", "default"

    def _resolve_provider_for_user(self, user_id: UUID) -> AIProvider:
        if self._has_custom_provider:
            return self._provider
        provider_key, api_key, base_url, model, source = self._resolve_effective_ai_config(user_id)
        if source in ("user", "server_env"):
            timeout = self._settings.ai_timeout_seconds if self._settings else 20.0
            return build_ai_provider_from_config(
                provider=provider_key,
                api_key=api_key,
                model_name=model,
                base_url=base_url,
                timeout_seconds=timeout,
                settings=self._settings,
                require_api_key_for_remote=True,
            )
        return self._provider

    def get_provider_config(self, user_id: UUID) -> AiProviderConfigResponse:
        provider_key, api_key, base_url, model, source = self._resolve_effective_ai_config(user_id)
        # Ne jamais exposer d'aperçu même partiel de la clé serveur globale
        preview = _mask_api_key(api_key) if source == "user" else None
        return AiProviderConfigResponse(
            provider=provider_key,  # type: ignore[arg-type]
            base_url=base_url,
            model=model,
            has_api_key=bool(api_key),
            api_key_preview=preview,
            source=source,
            available_providers=PROVIDER_CATALOG,
        )

    def update_provider_config(
        self,
        user_id: UUID,
        payload: AiProviderConfigUpdate,
    ) -> AiProviderConfigResponse:
        if self._profile_service is None:
            raise AppError(500, "INTERNAL_ERROR", "Service profil indisponible.")

        provider_key = canonicalize_provider_name(payload.provider)
        saved = self._profile_service.get_ai_provider_config(user_id) or {}
        same_saved_provider = canonicalize_provider_name(saved.get("provider")) == provider_key
        existing_key = str(saved.get("api_key") or "").strip() if same_saved_provider else ""
        server_env_key = (
            (self._settings.ai_api_key or "").strip()
            if (
                self._settings is not None
                and canonicalize_provider_name(self._settings.ai_provider) == provider_key
            )
            else ""
        )

        new_key = (payload.api_key or "").strip()
        if payload.clear_api_key and not new_key:
            persisted_api_key = ""
        elif new_key:
            persisted_api_key = new_key
        else:
            persisted_api_key = existing_key

        if provider_key == "local":
            resolved_url = ""
            resolved_model = (payload.model or "").strip() or "local-coach-v1"
            persisted_api_key = ""
        else:
            normalized_url = normalize_provider_base_url(provider_key, payload.base_url)
            resolved_url = _validate_outbound_base_url(
                normalized_url,
                settings=self._settings,
                verify_dns=True,
            )
            is_custom = self._is_custom_base_url(provider_key, resolved_url)
            effective_key = persisted_api_key or (
                "" if (payload.clear_api_key or is_custom) else server_env_key
            )
            if not effective_key:
                raise AppError(
                    400,
                    "AI_API_KEY_REQUIRED",
                    "Veuillez saisir une clé API pour activer ce fournisseur IA.",
                )
            resolved_model = validate_model_identifier(
                (payload.model or "").strip() or _default_model_for_provider(provider_key)
            )

        self._profile_service.save_ai_provider_config(
            user_id,
            {
                "provider": provider_key,
                "base_url": resolved_url,
                "model": resolved_model,
                "api_key": persisted_api_key,
            },
        )
        return self.get_provider_config(user_id)

    def fetch_available_models(
        self,
        user_id: UUID,
        payload: FetchProviderModelsRequest,
        *,
        client_ip: str = "unknown",
        rate_limiter: PersistentRateLimiter | None = None,
    ) -> FetchProviderModelsResponse:
        if rate_limiter is not None:
            now = datetime.now(timezone.utc)
            probe_key = f"{user_id}:{client_ip}"
            count = rate_limiter.count_all_in_window(
                scope="models_probe",
                client_ip=probe_key,
                now_utc=now,
                window_seconds=MODELS_PROBE_WINDOW_SECONDS,
            )
            if count >= MODELS_PROBE_IP_MAX_ATTEMPTS:
                raise AppError(
                    429,
                    "RATE_LIMITED",
                    "Trop de requêtes de découverte de modèles. Patientez une minute.",
                )
            rate_limiter.record_attempt(
                scope="models_probe",
                account_key=str(user_id),
                client_ip=probe_key,
                succeeded=True,
                now_utc=now,
            )

        provider_key = canonicalize_provider_name(payload.provider)
        saved = (
            self._profile_service.get_ai_provider_config(user_id)
            if self._profile_service is not None
            else None
        ) or {}
        same_saved_provider = canonicalize_provider_name(saved.get("provider")) == provider_key
        same_env_provider = (
            self._settings is not None
            and canonicalize_provider_name(self._settings.ai_provider) == provider_key
        )

        resolved_base_url: str | None = payload.base_url
        if not resolved_base_url and same_saved_provider:
            resolved_base_url = saved.get("base_url")
        if not resolved_base_url and same_env_provider and self._settings is not None:
            resolved_base_url = self._settings.ai_base_url

        normalized_target_url = normalize_provider_base_url(provider_key, resolved_base_url)
        is_custom_target = self._is_custom_base_url(provider_key, normalized_target_url)

        resolved_key = (payload.api_key or "").strip()
        if not resolved_key and same_saved_provider:
            saved_base = normalize_provider_base_url(provider_key, saved.get("base_url"))
            if not payload.base_url or normalized_target_url == saved_base:
                resolved_key = str(saved.get("api_key") or "").strip()
        # Ne jamais envoyer la clé serveur globale vers une URL personnalisée
        if (
            not resolved_key
            and same_env_provider
            and self._settings is not None
            and not is_custom_target
        ):
            resolved_key = (self._settings.ai_api_key or "").strip()

        timeout = min(15.0, self._settings.ai_timeout_seconds) if self._settings else 15.0
        effective_url, raw_models = fetch_provider_models(
            provider=provider_key,
            api_key=resolved_key,
            base_url=resolved_base_url,
            timeout_seconds=timeout,
            settings=self._settings,
        )
        models = [AiProviderModelInfo.model_validate(item) for item in raw_models]
        return FetchProviderModelsResponse(
            provider=provider_key,  # type: ignore[arg-type]
            base_url=effective_url,
            models=models,
            count=len(models),
        )

    def _refresh_proposal_expiration(
        self,
        record: AiActionProposalRecord,
        now_utc: datetime,
        *,
        persist: bool = True,
    ) -> AiActionProposalRecord:
        if (
            record.status == ProposalStatus.pending
            and record.expires_at is not None
            and record.expires_at <= now_utc
        ):
            expired = record.model_copy(
                update={
                    "status": ProposalStatus.expired,
                    "resolved_at": now_utc,
                }
            )
            return self._ai_repo.save_proposal(expired) if persist else expired
        return record

    @staticmethod
    def _proposal_signature(action_type: str, payload: dict[str, Any]) -> str:
        return f"{action_type}::{json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)}"

    def list_conversations(self, user_id: UUID) -> list[AiConversationResponse]:
        records = self._ai_repo.list_conversations(user_id)
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return [AiConversationResponse.model_validate(item.model_dump()) for item in records]

    def create_conversation(
        self,
        user_id: UUID,
        payload: AiConversationCreate,
    ) -> AiConversationResponse:
        now = datetime.now(timezone.utc)
        record = AiConversationRecord(
            id=uuid4(),
            user_id=user_id,
            title=payload.title or "Nouvelle conversation",
            created_at=now,
            updated_at=now,
        )
        saved = self._ai_repo.save_conversation(record)
        return AiConversationResponse.model_validate(saved.model_dump())

    def get_conversation_detail(
        self,
        user_id: UUID,
        conversation_id: UUID,
    ) -> AiConversationDetailResponse:
        """Lecture pure (sans effet de bord en base) d'une conversation et de ses propositions."""
        conv = self._ai_repo.get_conversation(user_id, conversation_id)
        if conv is None:
            raise AppError(404, "NOT_FOUND", "Conversation IA introuvable.")

        now = datetime.now(timezone.utc)
        raw_messages = self._ai_repo.list_messages(user_id, conversation_id)
        raw_messages.sort(key=lambda item: item.created_at)

        messages: list[AiMessageRecord] = []
        for msg in raw_messages:
            if (
                msg.role == AiMessageRole.assistant
                and ("```" in msg.content or msg.content.lstrip().startswith("{"))
                and _PROTOCOL_JSON_MARKERS_RE.search(msg.content)
            ):
                dummy_ctx = self._context_builder.build_context(
                    user_id,
                    explicit_scopes=[AiContextScope.auto],
                    now_utc=now,
                )
                re_parsed = _parse_llm_json_output(
                    msg.content,
                    dummy_ctx,
                    str((msg.metadata or {}).get("provider") or "local"),
                    str((msg.metadata or {}).get("model") or "local-coach-v1"),
                )
                if re_parsed.reply != msg.content:
                    msg = msg.model_copy(update={"content": re_parsed.reply})
            messages.append(msg)

        proposals = [
            self._refresh_proposal_expiration(item, now, persist=False)
            for item in self._ai_repo.list_proposals(user_id, conversation_id=conversation_id)
        ]
        proposals.sort(key=lambda item: item.created_at, reverse=True)

        return AiConversationDetailResponse(
            conversation=AiConversationResponse.model_validate(conv.model_dump()),
            messages=[AiMessageResponse.model_validate(m.model_dump()) for m in messages],
            proposals=[AiActionProposalResponse.model_validate(p.model_dump()) for p in proposals],
        )

    def repair_conversation(
        self,
        user_id: UUID,
        conversation_id: UUID,
    ) -> AiConversationDetailResponse:
        """Opération dédiée, contrôlée et idempotente pour nettoyer d'anciens messages JSON et expirer les propositions échues."""
        conv = self._ai_repo.get_conversation(user_id, conversation_id)
        if conv is None:
            raise AppError(404, "NOT_FOUND", "Conversation IA introuvable.")

        now = datetime.now(timezone.utc)
        raw_messages = self._ai_repo.list_messages(user_id, conversation_id)
        raw_messages.sort(key=lambda item: item.created_at)

        existing_proposals = self._ai_repo.list_proposals(user_id, conversation_id=conversation_id)
        existing_sigs = {
            self._proposal_signature(p.action_type, p.payload)
            for p in existing_proposals
            if p.status == ProposalStatus.pending
        }

        repaired_messages: list[AiMessageRecord] = []
        for msg in raw_messages:
            if (
                msg.role == AiMessageRole.assistant
                and ("```" in msg.content or msg.content.lstrip().startswith("{"))
                and _PROTOCOL_JSON_MARKERS_RE.search(msg.content)
            ):
                dummy_ctx = self._context_builder.build_context(
                    user_id,
                    explicit_scopes=[AiContextScope.auto],
                    now_utc=now,
                )
                re_parsed = _parse_llm_json_output(
                    msg.content,
                    dummy_ctx,
                    str((msg.metadata or {}).get("provider") or "local"),
                    str((msg.metadata or {}).get("model") or "local-coach-v1"),
                )
                if re_parsed.reply != msg.content:
                    meta = dict(msg.metadata or {})
                    existing_prop_ids = list(meta.get("proposal_ids") or [])
                    if not existing_prop_ids and re_parsed.proposals:
                        for cand in re_parsed.proposals:
                            try:
                                validated = self._action_validator.validate_candidate(user_id, cand)
                                sig = self._proposal_signature(validated.action_type.value, validated.payload)
                                if sig in existing_sigs:
                                    continue
                                saved_p = self._ai_repo.save_proposal(
                                    AiActionProposalRecord(
                                        id=uuid4(),
                                        user_id=user_id,
                                        conversation_id=conversation_id,
                                        action_type=validated.action_type.value,
                                        title=validated.title,
                                        explanation=validated.explanation,
                                        payload=validated.payload,
                                        status=ProposalStatus.pending,
                                        expires_at=now + timedelta(days=PROPOSAL_TTL_DAYS),
                                        created_at=msg.created_at,
                                    )
                                )
                                existing_sigs.add(sig)
                                existing_prop_ids.append(str(saved_p.id))
                            except AppError:
                                continue
                    meta["proposal_ids"] = existing_prop_ids
                    msg = self._ai_repo.save_message(
                        msg.model_copy(
                            update={
                                "content": re_parsed.reply,
                                "metadata": meta,
                            }
                        )
                    )
            repaired_messages.append(msg)

        proposals = [
            self._refresh_proposal_expiration(item, now, persist=True)
            for item in self._ai_repo.list_proposals(user_id, conversation_id=conversation_id)
        ]
        proposals.sort(key=lambda item: item.created_at, reverse=True)

        return AiConversationDetailResponse(
            conversation=AiConversationResponse.model_validate(conv.model_dump()),
            messages=[AiMessageResponse.model_validate(m.model_dump()) for m in repaired_messages],
            proposals=[AiActionProposalResponse.model_validate(p.model_dump()) for p in proposals],
        )

    def delete_conversation(self, user_id: UUID, conversation_id: UUID) -> None:
        if not self._ai_repo.delete_conversation(user_id, conversation_id):
            raise AppError(404, "NOT_FOUND", "Conversation IA introuvable.")

    def _check_rate_limit(self, user_id: UUID, conversation_id: UUID, now_utc: datetime) -> None:
        _ = conversation_id
        one_minute_ago = now_utc - timedelta(minutes=1)
        count = self._ai_repo.count_user_messages_since(user_id, one_minute_ago)
        if count >= self._rate_limit:
            raise AppError(
                429,
                "RATE_LIMITED",
                "Limite de fréquence atteinte pour le Copilote IA. Patientez quelques secondes.",
            )

    def send_message(
        self,
        user_id: UUID,
        conversation_id: UUID,
        payload: AiMessageCreate,
    ) -> AiTurnResponse:
        conv = self._ai_repo.get_conversation(user_id, conversation_id)
        if conv is None:
            raise AppError(404, "NOT_FOUND", "Conversation IA introuvable.")

        # Idempotence au tour conversationnel (AI-First §7)
        if payload.idempotency_key:
            prev_user = self._ai_repo.get_message_by_idempotency_key(
                user_id, conversation_id, payload.idempotency_key
            )
            if prev_user is not None:
                conv_msgs = self._ai_repo.list_messages(user_id, conversation_id)
                asst_id = prev_user.metadata.get("turn_assistant_message_id")
                prev_asst = next(
                    (m for m in conv_msgs if asst_id and str(m.id) == str(asst_id)),
                    None,
                )
                if prev_asst is not None:
                    prop_ids = list(prev_user.metadata.get("turn_proposal_ids") or [])
                    prev_props: list[AiActionProposalRecord] = []
                    for pid in prop_ids:
                        try:
                            found_p = self._ai_repo.get_proposal(user_id, UUID(str(pid)))
                            if found_p is not None:
                                prev_props.append(found_p)
                        except ValueError:
                            continue
                    return AiTurnResponse(
                        user_message=AiMessageResponse.model_validate(prev_user.model_dump()),
                        assistant_message=AiMessageResponse.model_validate(prev_asst.model_dump()),
                        proposals=[
                            AiActionProposalResponse.model_validate(p.model_dump())
                            for p in prev_props
                        ],
                        auto_executed_count=int(prev_user.metadata.get("auto_executed_count", 0)),
                    )

        now = datetime.now(timezone.utc)
        self._check_rate_limit(user_id, conversation_id, now)

        existing_messages = self._ai_repo.list_messages(user_id, conversation_id)
        existing_messages.sort(key=lambda item: item.created_at)

        user_msg = self._ai_repo.save_message(
            AiMessageRecord(
                id=uuid4(),
                user_id=user_id,
                conversation_id=conversation_id,
                role=AiMessageRole.user,
                content=payload.content,
                metadata={
                    "requested_scopes": [s.value for s in (payload.context_scopes or [AiContextScope.auto])]
                },
                idempotency_key=payload.idempotency_key,
                created_at=now,
            )
        )

        # Renomme automatiquement une conversation neuve à partir du premier message
        if conv.title == "Nouvelle conversation" and not existing_messages:
            auto_title = payload.content[:60].strip()
            self._ai_repo.save_conversation(
                conv.model_copy(update={"title": auto_title, "updated_at": now})
            )
        else:
            self._ai_repo.save_conversation(conv.model_copy(update={"updated_at": now}))

        bounded_context = self._context_builder.build_context(
            user_id,
            message=payload.content,
            explicit_scopes=payload.context_scopes,
            now_utc=now,
        )

        history_pairs = _build_bounded_history(existing_messages)

        active_provider = self._resolve_provider_for_user(user_id)
        try:
            provider_result = active_provider.generate_response(
                user_message=payload.content,
                history=history_pairs,
                context=bounded_context,
                prompt_manager=self._prompt_manager,
            )
        except Exception:
            self._ai_repo.delete_message(user_id, user_msg.id)
            raise

        saved_proposals: list[AiActionProposalRecord] = []
        rejected_candidates_count = 0
        reply_Now = datetime.now(timezone.utc)

        existing_pending_sigs = {
            self._proposal_signature(p.action_type, p.payload)
            for p in self._ai_repo.list_proposals(user_id, conversation_id=conversation_id)
            if p.status == ProposalStatus.pending
            and (p.expires_at is None or p.expires_at > reply_Now)
        }
        seen_turn_sigs: set[str] = set()

        for idx, candidate in enumerate(provider_result.proposals):
            try:
                validated = self._action_validator.validate_candidate(user_id, candidate)
                sig = self._proposal_signature(validated.action_type.value, validated.payload)
                if sig in seen_turn_sigs or sig in existing_pending_sigs:
                    continue
                seen_turn_sigs.add(sig)
                prop_idem = (
                    f"m:{payload.idempotency_key[:68]}:{idx}"
                    if payload.idempotency_key
                    else None
                )
                proposal_record = self._ai_repo.save_proposal(
                    AiActionProposalRecord(
                        id=uuid4(),
                        user_id=user_id,
                        conversation_id=conversation_id,
                        action_type=validated.action_type.value,
                        title=validated.title,
                        explanation=validated.explanation,
                        payload=validated.payload,
                        status=ProposalStatus.pending,
                        expires_at=reply_Now + timedelta(days=PROPOSAL_TTL_DAYS),
                        idempotency_key=prop_idem,
                        created_at=reply_Now,
                    )
                )
                saved_proposals.append(proposal_record)
            except AppError:
                rejected_candidates_count += 1

        # Confirmation intelligente : exécution directe uniquement pour une action simple explicitement autorisée
        memory_allow_simple = (
            self._ai_memory_repo.get_or_create(user_id).auto_execute_simple_actions
            if self._ai_memory_repo is not None
            else False
        )
        allow_simple = (
            bool(payload.auto_execute_simple)
            if payload.auto_execute_simple is not None
            else memory_allow_simple
        )

        final_reply = provider_result.reply
        auto_executed_count = 0
        response_proposals: list[AiActionProposalResponse] = []

        if (
            len(saved_proposals) == 1
            and self._tool_registry.can_auto_execute(
                saved_proposals[0].action_type,
                allow_simple=allow_simple,
                user_instructed=True,
            )
        ):
            target_prop = saved_proposals[0]
            try:
                exec_resp = self.accept_proposal(
                    user_id,
                    target_prop.id,
                    AcceptProposalRequest(
                        idempotency_key=f"auto:{target_prop.id}"[:80],
                    ),
                )
                refreshed_p = self._ai_repo.get_proposal(user_id, target_prop.id)
                if refreshed_p is not None:
                    saved_proposals[0] = refreshed_p
                response_proposals = [exec_resp]
                auto_executed_count = 1
                final_reply = (
                    f"{provider_result.reply}\n\n"
                    f"Action exécutée directement : **{target_prop.title}**."
                )
            except AppError as exc:
                failed_p = self._ai_repo.get_proposal(user_id, target_prop.id)
                if failed_p is not None:
                    saved_proposals[0] = failed_p
                    response_proposals = [
                        AiActionProposalResponse.model_validate(failed_p.model_dump())
                    ]
                else:
                    response_proposals = [
                        AiActionProposalResponse.model_validate(target_prop.model_dump())
                    ]
                final_reply = (
                    f"L’action proposée n’a pas pu être exécutée côté backend : {exc.message} "
                    "Aucune opération n’a été appliquée."
                )
        else:
            response_proposals = [
                AiActionProposalResponse.model_validate(p.model_dump())
                for p in saved_proposals
            ]

        assistant_msg = self._ai_repo.save_message(
            AiMessageRecord(
                id=uuid4(),
                user_id=user_id,
                conversation_id=conversation_id,
                role=AiMessageRole.assistant,
                content=final_reply,
                metadata={
                    "provider": provider_result.provider_name,
                    "model": provider_result.model_name,
                    "is_estimate": provider_result.is_estimate,
                    "missing_data": provider_result.missing_data,
                    "included_scopes": bounded_context.included_scopes,
                    "proposal_ids": [str(p.id) for p in saved_proposals],
                    "rejected_proposals_count": rejected_candidates_count,
                    "auto_executed_count": auto_executed_count,
                },
                created_at=reply_Now,
            )
        )

        # Persiste les liens du tour pour garantir une réponse idempotente exacte
        user_msg = self._ai_repo.save_message(
            user_msg.model_copy(
                update={
                    "metadata": {
                        **user_msg.metadata,
                        "turn_assistant_message_id": str(assistant_msg.id),
                        "turn_proposal_ids": [str(p.id) for p in saved_proposals],
                        "auto_executed_count": auto_executed_count,
                    }
                }
            )
        )

        return AiTurnResponse(
            user_message=AiMessageResponse.model_validate(user_msg.model_dump()),
            assistant_message=AiMessageResponse.model_validate(assistant_msg.model_dump()),
            proposals=response_proposals,
            auto_executed_count=auto_executed_count,
        )

    def list_proposals(
        self,
        user_id: UUID,
        *,
        status_filter: ProposalStatus | None = None,
    ) -> list[AiActionProposalResponse]:
        now = datetime.now(timezone.utc)
        records = [
            self._refresh_proposal_expiration(item, now, persist=False)
            for item in self._ai_repo.list_proposals(user_id)
        ]
        if status_filter is not None:
            records = [item for item in records if item.status == status_filter]
        records.sort(key=lambda item: item.created_at, reverse=True)
        return [AiActionProposalResponse.model_validate(item.model_dump()) for item in records]

    def get_proposal(self, user_id: UUID, proposal_id: UUID) -> AiActionProposalResponse:
        record = self._ai_repo.get_proposal(user_id, proposal_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Proposition d’action introuvable.")
        refreshed = self._refresh_proposal_expiration(record, datetime.now(timezone.utc), persist=False)
        return AiActionProposalResponse.model_validate(refreshed.model_dump())

    def update_proposal(
        self,
        user_id: UUID,
        proposal_id: UUID,
        request: UpdateProposalRequest,
    ) -> AiActionProposalResponse:
        record = self._ai_repo.get_proposal(user_id, proposal_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Proposition d’action introuvable.")

        now = datetime.now(timezone.utc)
        record = self._refresh_proposal_expiration(record, now)
        if record.status != ProposalStatus.pending:
            raise AppError(
                409,
                "CONFLICT",
                "Seule une proposition en attente peut être modifiée.",
            )

        if not self._tool_registry.is_allowed_proposal_action(record.action_type):
            raise AppError(422, "UNSUPPORTED_AI_ACTION", "Outil non autorisé dans ToolRegistry.")

        action_enum = AiActionType(record.action_type)
        overrides = dict(request.payload_overrides or {})
        merged_payload = {**record.payload, **overrides}

        # Recalcul des créneaux réels si demandé ou si fréquence/durée modifiée sans créneaux fournis
        if (
            action_enum == AiActionType.plan_strategic_activity
            and not bool(merged_payload.get("park_only"))
            and (
                request.recalculate_slots
                or (
                    ("frequency_per_week" in overrides or "session_duration_minutes" in overrides)
                    and "proposed_slots" not in overrides
                )
            )
        ):
            ctx = self._context_builder.build_context(
                user_id,
                explicit_scopes=[AiContextScope.schedule],
                now_utc=now,
            )
            weekly_slots = list(
                (ctx.availability or {}).get("multi_week_candidate_slots")
                or (ctx.availability or {}).get("weekly_candidate_slots")
                or []
            )
            if not weekly_slots:
                raise AppError(
                    409,
                    "NO_AVAILABLE_SLOTS",
                    "Aucun créneau libre disponible dans le calendrier pour recalculer cette proposition.",
                )
            target_freq = max(1, min(7, int(merged_payload.get("frequency_per_week") or 2)))
            target_dur = max(30, min(240, int(merged_payload.get("session_duration_minutes") or 60)))
            target_weeks = max(1, min(3, int(merged_payload.get("estimated_weeks") or 1)))

            selected_raw: list[dict[str, Any]] = []
            for wk in range(target_weeks):
                wk_pool = [c for c in weekly_slots if int(c.get("week_index", 0)) == wk]
                if not wk_pool and wk == 0:
                    wk_pool = list(weekly_slots)
                wk_sel: list[dict[str, Any]] = []
                used_dates: set[str] = set()
                for cand in wk_pool:
                    if len(wk_sel) >= target_freq:
                        break
                    if cand["local_date"] not in used_dates:
                        wk_sel.append(cand)
                        used_dates.add(cand["local_date"])
                if len(wk_sel) < target_freq:
                    for cand in wk_pool:
                        if len(wk_sel) >= target_freq:
                            break
                        if cand not in wk_sel:
                            wk_sel.append(cand)
                selected_raw.extend(wk_sel)

            recalculated_slots: list[dict[str, Any]] = []
            for slot in selected_raw:
                start_dt = datetime.fromisoformat(slot["starts_at"])
                actual_dur = min(int(slot["duration_minutes"]), target_dur)
                if actual_dur < 30:
                    actual_dur = int(slot["duration_minutes"])
                end_dt = start_dt + timedelta(minutes=actual_dur)
                sh, sm = [int(p) for p in slot["local_start_time"].split(":")]
                end_tot_min = sh * 60 + sm + actual_dur
                recalculated_slots.append(
                    {
                        "day_label": slot["day_label"],
                        "local_date": slot["local_date"],
                        "local_start_time": slot["local_start_time"],
                        "local_end_time": f"{end_tot_min // 60:02d}:{end_tot_min % 60:02d}",
                        "starts_at": start_dt.isoformat(),
                        "ends_at": end_dt.isoformat(),
                        "duration_minutes": actual_dur,
                    }
                )
            merged_payload["proposed_slots"] = recalculated_slots
            merged_payload["frequency_per_week"] = target_freq
            merged_payload["start_date"] = recalculated_slots[0]["local_date"]

        validated_payload = self._action_validator.validate_action_payload(
            user_id, action_enum, merged_payload
        )

        next_title = record.title
        if action_enum == AiActionType.plan_strategic_activity:
            act_title = validated_payload.get("activity_title", "Activité")
            if validated_payload.get("park_only"):
                next_title = f"Placer « {act_title} » dans le Parking des idées"
            else:
                freq_val = int(validated_payload.get("frequency_per_week") or 1)
                next_title = f"Programmer « {act_title} » ({freq_val} séance(s)/sem.)"
        elif isinstance(overrides.get("title"), str) and overrides["title"].strip():
            next_title = overrides["title"].strip()[:180]

        updated = self._ai_repo.save_proposal(
            record.model_copy(
                update={
                    "title": next_title,
                    "payload": validated_payload,
                }
            )
        )
        return AiActionProposalResponse.model_validate(updated.model_dump())

    def accept_proposal(
        self,
        user_id: UUID,
        proposal_id: UUID,
        request: AcceptProposalRequest | None = None,
    ) -> AiActionProposalResponse:
        record = self._ai_repo.get_proposal(user_id, proposal_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Proposition d’action introuvable.")

        idem_key = request.idempotency_key if request and request.idempotency_key else None
        if (
            idem_key is not None
            and record.status == ProposalStatus.executed
            and (record.execution_result or {}).get("accept_idempotency_key") == idem_key
        ):
            return AiActionProposalResponse.model_validate(record.model_dump())

        now = datetime.now(timezone.utc)
        record = self._refresh_proposal_expiration(record, now)
        if record.status == ProposalStatus.expired:
            raise AppError(
                409,
                "PROPOSAL_EXPIRED",
                "Cette proposition a expiré et ne peut plus être exécutée.",
            )
        if record.status != ProposalStatus.pending:
            raise AppError(
                409,
                "CONFLICT",
                "Seule une proposition en attente peut être acceptée.",
            )

        if not self._tool_registry.is_allowed_proposal_action(record.action_type):
            raise AppError(422, "UNSUPPORTED_AI_ACTION", "Outil non autorisé dans ToolRegistry.")

        action_enum = AiActionType(record.action_type)
        merged_payload = {
            **record.payload,
            **((request.payload_overrides if request else None) or {}),
        }
        validated_payload = self._action_validator.validate_action_payload(
            user_id, action_enum, merged_payload
        )

        # Réclamation atomique conditionnelle (WHERE status = 'pending') anti-double-exécution
        accepted_record = self._ai_repo.claim_proposal_for_execution(
            user_id, record.id, validated_payload
        )
        if accepted_record is None:
            raise AppError(
                409,
                "CONFLICT",
                "Cette proposition a déjà été réclamée ou traitée par une requête concurrente.",
            )

        try:
            execution_result = self._execute_validated_action(
                user_id, accepted_record.id, action_enum, validated_payload
            )
            if idem_key is not None:
                execution_result["accept_idempotency_key"] = idem_key
            executed = self._ai_repo.save_proposal(
                accepted_record.model_copy(
                    update={
                        "status": ProposalStatus.executed,
                        "execution_result": execution_result,
                        "error_message": None,
                        "resolved_at": datetime.now(timezone.utc),
                    }
                )
            )
            self._record_memory_after_execution(
                user_id,
                proposal=executed,
                action_enum=action_enum,
                execution_result=execution_result,
            )
            return AiActionProposalResponse.model_validate(executed.model_dump())
        except Exception as exc:
            err_msg = exc.message if isinstance(exc, AppError) else "Échec lors de l’exécution."
            rollback_info = getattr(exc, "rollback_info", None)
            self._ai_repo.save_proposal(
                accepted_record.model_copy(
                    update={
                        "status": ProposalStatus.failed,
                        "execution_result": rollback_info if isinstance(rollback_info, dict) else None,
                        "error_message": err_msg,
                        "resolved_at": datetime.now(timezone.utc),
                    }
                )
            )
            raise

    def _execute_validated_action(
        self,
        user_id: UUID,
        proposal_id: UUID,
        action_type: AiActionType,
        payload: dict[str, Any],
        *,
        compensations: list[Callable[[], None]] | None = None,
    ) -> dict[str, Any]:
        if action_type == AiActionType.create_task:
            norm_title = " ".join(str(payload["title"]).strip().lower().split())
            existing_task = next(
                (
                    t
                    for t in self._task_service.list_tasks(user_id)
                    if t.status in (TaskStatus.todo, TaskStatus.in_progress, TaskStatus.parked)
                    and " ".join(t.title.strip().lower().split()) == norm_title
                ),
                None,
            )
            if existing_task is not None:
                return {
                    "entity": "task",
                    "entity_id": str(existing_task.id),
                    "task_id": str(existing_task.id),
                    "title": existing_task.title,
                    "project_id": str(existing_task.project_id) if existing_task.project_id else None,
                    "source": existing_task.source.value,
                    "reused_existing": True,
                }
            created_task = self._task_service.create_task(
                user_id,
                TaskCreate(
                    title=payload["title"],
                    description=payload.get("description"),
                    priority=TaskPriority(payload.get("priority", "normal")),
                    due_at=payload.get("due_at"),
                    project_id=UUID(payload["project_id"]) if payload.get("project_id") else None,
                    module_id=UUID(payload["module_id"]) if payload.get("module_id") else None,
                ),
                source=TaskSource.ai_proposal,
                proposal_id=proposal_id,
            )
            if compensations is not None:
                tid = created_task.id
                compensations.append(lambda tid=tid: self._task_service.delete_task(user_id, tid))
            return {
                "entity": "task",
                "entity_id": str(created_task.id),
                "task_id": str(created_task.id),
                "title": created_task.title,
                "project_id": str(created_task.project_id) if created_task.project_id else None,
                "source": created_task.source.value,
            }

        if action_type == AiActionType.update_task:
            tid = UUID(payload["task_id"])
            prev_task = self._task_service.get_task(user_id, tid)
            patch_data: dict[str, Any] = {}
            for k in ("title", "description", "due_at"):
                if k in payload:
                    patch_data[k] = payload[k]
            if "status" in payload and payload["status"] is not None:
                patch_data["status"] = TaskStatus(payload["status"])
            if "priority" in payload and payload["priority"] is not None:
                patch_data["priority"] = TaskPriority(payload["priority"])
            if "project_id" in payload and payload["project_id"]:
                patch_data["project_id"] = UUID(payload["project_id"])
            if "module_id" in payload and payload["module_id"]:
                patch_data["module_id"] = UUID(payload["module_id"])
            updated_task = self._task_service.update_task(user_id, tid, TaskUpdate(**patch_data))
            if compensations is not None:
                compensations.append(
                    lambda tid=tid, prev=prev_task: self._task_service.update_task(
                        user_id,
                        tid,
                        TaskUpdate(
                            title=prev.title,
                            status=prev.status,
                            priority=prev.priority,
                            due_at=prev.due_at,
                        ),
                    )
                )
            return {
                "entity": "task",
                "entity_id": str(updated_task.id),
                "task_id": str(updated_task.id),
                "title": updated_task.title,
                "status": updated_task.status.value,
                "priority": updated_task.priority.value,
            }

        if action_type == AiActionType.park_task:
            tid = UUID(payload["task_id"])
            prev_task = self._task_service.get_task(user_id, tid)
            updated_task = self._task_service.update_task(
                user_id,
                tid,
                TaskUpdate(status=TaskStatus.parked),
            )
            if compensations is not None:
                compensations.append(
                    lambda tid=tid, prev_s=prev_task.status: self._task_service.update_task(
                        user_id, tid, TaskUpdate(status=prev_s)
                    )
                )
            return {
                "entity": "task",
                "entity_id": str(updated_task.id),
                "task_id": str(updated_task.id),
                "title": updated_task.title,
                "status": updated_task.status.value,
            }

        if action_type == AiActionType.create_project:
            if self._project_service is None:
                raise AppError(500, "PROJECT_SERVICE_UNAVAILABLE", "Le service Projets est indisponible.")
            norm_proj = " ".join(str(payload["name"]).strip().lower().split())
            existing_proj = next(
                (
                    p
                    for p in self._project_service.list_projects(user_id)
                    if p.status != ProjectStatus.archived
                    and " ".join(p.name.strip().lower().split()) == norm_proj
                ),
                None,
            )
            if existing_proj is not None:
                return {
                    "entity": "project",
                    "entity_id": str(existing_proj.id),
                    "project_id": str(existing_proj.id),
                    "name": existing_proj.name,
                    "goal": existing_proj.goal,
                    "next_action": existing_proj.next_action,
                    "status": existing_proj.status.value,
                    "reused_existing": True,
                }
            proj_status = ProjectStatus(payload.get("status", "active"))
            next_act = str(payload.get("next_action") or "").strip()
            if proj_status == ProjectStatus.active and len(next_act) < 2:
                next_act = "Définir la première étape concrète"
            created_proj = self._project_service.create_project(
                user_id,
                ProjectCreate(
                    name=str(payload["name"]),
                    category=str(payload.get("category") or "project"),
                    description=payload.get("description"),
                    goal=str(payload["goal"]),
                    status=proj_status,
                    priority=TaskPriority(payload.get("priority", "normal")),
                    motivation=payload.get("motivation"),
                    weekly_target_minutes=int(payload.get("weekly_target_minutes", 180)),
                    next_action=next_act,
                    deliverables=list(payload.get("deliverables") or []) or None,
                ),
            )
            if compensations is not None:
                pid = created_proj.id
                compensations.append(lambda pid=pid: self._project_service.delete_project(user_id, pid))  # type: ignore[union-attr]
            return {
                "entity": "project",
                "entity_id": str(created_proj.id),
                "project_id": str(created_proj.id),
                "name": created_proj.name,
                "goal": created_proj.goal,
                "next_action": created_proj.next_action,
                "status": created_proj.status.value,
            }

        if action_type == AiActionType.update_project:
            if self._project_service is None:
                raise AppError(500, "PROJECT_SERVICE_UNAVAILABLE", "Le service Projets est indisponible.")
            pid = UUID(payload["project_id"])
            prev_proj = self._project_service.get_project(user_id, pid)
            patch_data = {}
            for k in ("name", "description", "goal", "next_action", "weekly_target_minutes"):
                if k in payload:
                    patch_data[k] = payload[k]
            if "status" in payload and payload["status"] is not None:
                patch_data["status"] = ProjectStatus(payload["status"])
            if "priority" in payload and payload["priority"] is not None:
                patch_data["priority"] = TaskPriority(payload["priority"])
            updated_proj = self._project_service.update_project(user_id, pid, ProjectUpdate(**patch_data))
            if compensations is not None:
                compensations.append(
                    lambda pid=pid, prev=prev_proj: self._project_service.update_project(  # type: ignore[union-attr]
                        user_id, pid, ProjectUpdate(status=prev.status, next_action=prev.next_action)
                    )
                )
            return {
                "entity": "project",
                "entity_id": str(updated_proj.id),
                "project_id": str(updated_proj.id),
                "name": updated_proj.name,
                "status": updated_proj.status.value,
            }

        if action_type == AiActionType.pause_project:
            if self._project_service is None:
                raise AppError(500, "PROJECT_SERVICE_UNAVAILABLE", "Le service Projets est indisponible.")
            pid = UUID(payload["project_id"])
            prev_proj = self._project_service.get_project(user_id, pid)
            updated_proj = self._project_service.update_project(
                user_id,
                pid,
                ProjectUpdate(status=ProjectStatus.paused),
            )
            if compensations is not None:
                compensations.append(
                    lambda pid=pid, prev_s=prev_proj.status: self._project_service.update_project(  # type: ignore[union-attr]
                        user_id, pid, ProjectUpdate(status=prev_s)
                    )
                )
            return {
                "entity": "project",
                "entity_id": str(updated_proj.id),
                "project_id": str(updated_proj.id),
                "name": updated_proj.name,
                "status": updated_proj.status.value,
            }

        if action_type == AiActionType.create_schedule_event:
            created_event = self._schedule_service.create_event(
                user_id,
                ScheduleEventCreate(
                    title=payload["title"],
                    type=ScheduleEventType(payload.get("type", "learning")),
                    starts_at=payload["starts_at"],
                    ends_at=payload["ends_at"],
                    notes=payload.get("notes"),
                    source=ScheduleEventSource.ai_proposal,
                ),
            )
            if compensations is not None:
                eid = created_event.id
                compensations.append(lambda eid=eid: self._schedule_service.delete_event(user_id, eid))
            return {
                "entity": "schedule_event",
                "entity_id": str(created_event.id),
                "event_id": str(created_event.id),
                "title": created_event.title,
                "has_conflict": created_event.has_conflict,
            }

        if action_type == AiActionType.update_schedule_event:
            eid = UUID(payload["event_id"])
            prev_ev = self._schedule_service.get_event(user_id, eid)
            patch_data = {}
            for k in ("title", "starts_at", "ends_at", "notes"):
                if k in payload:
                    patch_data[k] = payload[k]
            updated_ev = self._schedule_service.update_event(
                user_id, eid, ScheduleEventUpdate(**patch_data)
            )
            if compensations is not None:
                compensations.append(
                    lambda eid=eid, prev=prev_ev: self._schedule_service.update_event(
                        user_id,
                        eid,
                        ScheduleEventUpdate(
                            title=prev.title,
                            starts_at=prev.starts_at,
                            ends_at=prev.ends_at,
                            notes=prev.notes,
                        ),
                    )
                )
            return {
                "entity": "schedule_event",
                "entity_id": str(updated_ev.id),
                "event_id": str(updated_ev.id),
                "title": updated_ev.title,
            }

        if action_type == AiActionType.archive_schedule_event:
            eid = UUID(payload["event_id"])
            prev_ev = self._schedule_service.get_event(user_id, eid)
            self._schedule_service.delete_event(user_id, eid)
            return {
                "entity": "schedule_event_archived",
                "entity_id": str(eid),
                "event_id": str(eid),
                "title": prev_ev.title,
            }

        if action_type == AiActionType.create_study_session:
            if self._session_service is None:
                raise AppError(500, "SESSION_SERVICE_UNAVAILABLE", "Le service Séances est indisponible.")
            created_sess = self._session_service.create_session(
                user_id,
                SessionCreate(
                    title=str(payload["title"]),
                    category=str(payload.get("category") or "Apprentissage"),
                    planned_activity=payload.get("planned_activity"),
                    started_at=payload.get("started_at"),
                    project_id=UUID(payload["project_id"]) if payload.get("project_id") else None,
                    goal_id=UUID(payload["goal_id"]) if payload.get("goal_id") else None,
                    task_id=UUID(payload["task_id"]) if payload.get("task_id") else None,
                    skill_id=UUID(payload["skill_id"]) if payload.get("skill_id") else None,
                ),
            )
            if compensations is not None:
                sid = created_sess.id
                compensations.append(lambda sid=sid: self._session_service.delete_session(user_id, sid))  # type: ignore[union-attr]
            return {
                "entity": "study_session",
                "entity_id": str(created_sess.id),
                "session_id": str(created_sess.id),
                "title": created_sess.title,
            }

        if action_type == AiActionType.create_skill:
            norm_skill_name = " ".join(str(payload["name"]).strip().lower().split())
            existing_skill = next(
                (
                    s
                    for s in self._skill_service.list_skills(user_id)
                    if " ".join(s.name.strip().lower().split()) == norm_skill_name
                ),
                None,
            )
            if existing_skill is not None:
                return {
                    "entity": "skill",
                    "entity_id": str(existing_skill.id),
                    "skill_id": str(existing_skill.id),
                    "name": existing_skill.name,
                    "current_level": existing_skill.current_level,
                    "goal_id": payload.get("goal_id"),
                    "learning_path_id": payload.get("learning_path_id"),
                    "reused_existing": True,
                }
            created_skill = self._skill_service.create_skill(
                user_id,
                SkillCreate(
                    name=str(payload["name"]),
                    domain=str(payload.get("domain") or "Développement"),
                    description=payload.get("description"),
                    current_level=0,
                    target_level=int(payload["target_level"]) if payload.get("target_level") else 3,
                ),
            )
            if compensations is not None:
                skid = created_skill.id
                compensations.append(lambda skid=skid: self._skill_service.delete_skill(user_id, skid))
            if payload.get("goal_id") and self._goal_repo is not None:
                goal_rec = self._goal_repo.get(user_id, UUID(str(payload["goal_id"])))
                if goal_rec is not None and goal_rec.skill_id is None:
                    self._goal_repo.save(
                        goal_rec.model_copy(
                            update={
                                "skill_id": created_skill.id,
                                "updated_at": datetime.now(timezone.utc),
                            }
                        )
                    )
            return {
                "entity": "skill",
                "entity_id": str(created_skill.id),
                "skill_id": str(created_skill.id),
                "name": created_skill.name,
                "current_level": created_skill.current_level,
                "goal_id": payload.get("goal_id"),
                "learning_path_id": payload.get("learning_path_id"),
            }

        if action_type == AiActionType.add_skill_evidence:
            created_evidence = self._skill_service.add_evidence(
                user_id,
                UUID(payload["skill_id"]),
                SkillEvidenceCreate(
                    type=SkillEvidenceType(payload.get("type", "exercise")),
                    description=payload["description"],
                    reference_url=payload.get("reference_url"),
                    result=payload.get("result"),
                ),
            )
            if compensations is not None:
                skid = created_evidence.skill_id
                evid = created_evidence.id
                compensations.append(
                    lambda skid=skid, evid=evid: self._skill_service.delete_evidence(user_id, skid, evid)
                )
            return {
                "entity": "skill_evidence",
                "entity_id": str(created_evidence.id),
                "evidence_id": str(created_evidence.id),
                "skill_id": str(created_evidence.skill_id),
            }

        if action_type == AiActionType.propose_skill_assessment:
            created_assessment = self._skill_service.create_assessment(
                user_id,
                UUID(payload["skill_id"]),
                SkillAssessmentCreate(
                    target_level=int(payload["target_level"]) if payload.get("target_level") else None,
                    assessment_type=SkillAssessmentType(
                        payload.get("assessment_type", "practical_exercise")
                    ),
                    path_id=UUID(payload["path_id"]) if payload.get("path_id") else None,
                    module_id=UUID(payload["module_id"]) if payload.get("module_id") else None,
                    lesson_id=UUID(payload["lesson_id"]) if payload.get("lesson_id") else None,
                ),
                internal_prompt_title=payload.get("prompt_title"),
                internal_prompt_instructions=payload.get("prompt_instructions"),
            )
            return {
                "entity": "skill_assessment",
                "entity_id": str(created_assessment.id),
                "assessment_id": str(created_assessment.id),
                "skill_id": str(created_assessment.skill_id),
                "status": created_assessment.status.value,
                "target_level": created_assessment.target_level,
            }

        if action_type == AiActionType.recommend_skill_progression:
            approved_assessment = self._skill_service.validate_assessment(
                user_id,
                UUID(payload["skill_id"]),
                UUID(payload["assessment_id"]),
                SkillAssessmentDecision(reason=payload.get("decision_reason")),
            )
            updated_skill = self._skill_service.get_skill(user_id, UUID(payload["skill_id"]))
            return {
                "entity": "skill_progression",
                "entity_id": str(updated_skill.id),
                "assessment_id": str(approved_assessment.id),
                "skill_id": str(updated_skill.id),
                "name": updated_skill.name,
                "current_level": updated_skill.current_level,
                "applied_level_delta": approved_assessment.applied_level_delta,
            }

        if action_type == AiActionType.create_learning_path:
            if self._learning_service is None:
                raise AppError(500, "LEARNING_SERVICE_UNAVAILABLE", "Le service Apprentissage est indisponible.")
            norm_lp = " ".join(str(payload["title"]).strip().lower().split())
            overview_lp = self._learning_service.get_overview(user_id)
            existing_lp = next(
                (
                    p
                    for p in overview_lp.paths
                    if " ".join(p.title.strip().lower().split()) == norm_lp
                ),
                None,
            )
            if existing_lp is not None:
                return {
                    "entity": "learning_path",
                    "entity_id": str(existing_lp.id),
                    "learning_path_id": str(existing_lp.id),
                    "title": existing_lp.title,
                    "module_ids": [],
                    "reused_existing": True,
                }
            created_path = self._learning_service.create_path(
                user_id,
                LearningPathCreate(
                    title=str(payload["title"]),
                    goal=str(payload["goal"]),
                    description=payload.get("description"),
                    status=LearningStatus(payload.get("status", "active")),
                ),
            )
            if compensations is not None:
                lpid = created_path.id
                compensations.append(lambda lpid=lpid: self._learning_service.delete_path(user_id, lpid))  # type: ignore[union-attr]
            created_mod_ids: list[str] = []
            for idx, m_item in enumerate(list(payload.get("modules") or [])[:6], start=1):
                m_title = str((m_item or {}).get("title") or f"Module {idx}").strip()[:140]
                if len(m_title) >= 2:
                    c_mod = self._learning_service.create_module(
                        user_id,
                        LearningModuleCreate(
                            path_id=created_path.id,
                            title=m_title,
                            description=(m_item or {}).get("description"),
                            position=idx,
                            status=LearningStatus.active if idx == 1 else LearningStatus.not_started,
                        ),
                    )
                    created_mod_ids.append(str(c_mod.id))
            return {
                "entity": "learning_path",
                "entity_id": str(created_path.id),
                "learning_path_id": str(created_path.id),
                "title": created_path.title,
                "module_ids": created_mod_ids,
            }

        if action_type == AiActionType.update_learning_path:
            if self._learning_service is None:
                raise AppError(500, "LEARNING_SERVICE_UNAVAILABLE", "Le service Apprentissage est indisponible.")
            lpid = UUID(payload["path_id"])
            patch_data: dict[str, Any] = {}
            for k in ("title", "goal", "description"):
                if k in payload and payload[k] is not None:
                    patch_data[k] = payload[k]
            if "status" in payload and payload["status"] is not None:
                patch_data["status"] = LearningStatus(payload["status"])
            if patch_data:
                updated_path = self._learning_service.update_path(
                    user_id, lpid, LearningPathUpdate(**patch_data)
                )
            else:
                overview = self._learning_service.get_overview(user_id)
                updated_path = next((p for p in overview.paths if p.id == lpid), None)
                if updated_path is None:
                    raise AppError(404, "NOT_FOUND", "Parcours introuvable.")
            if payload.get("add_module_title"):
                existing_mods = self._learning_service.list_modules(user_id, path_id=lpid)
                self._learning_service.create_module(
                    user_id,
                    LearningModuleCreate(
                        path_id=lpid,
                        title=str(payload["add_module_title"])[:140],
                        position=len(existing_mods) + 1,
                        status=LearningStatus.active,
                    ),
                )
            if payload.get("add_lesson_title"):
                mods = self._learning_service.list_modules(user_id, path_id=lpid)
                if mods:
                    self._learning_service.create_lesson(
                        user_id,
                        LessonCreate(
                            module_id=mods[0].id,
                            title=str(payload["add_lesson_title"])[:140],
                            status=LearningStatus.not_started,
                        ),
                    )
            return {
                "entity": "learning_path",
                "entity_id": str(updated_path.id),
                "learning_path_id": str(updated_path.id),
                "title": updated_path.title,
                "status": updated_path.status.value,
            }

        if action_type == AiActionType.create_personal_goal:
            if self._objectives_service is None:
                raise AppError(500, "OBJECTIVES_SERVICE_UNAVAILABLE", "Le service Objectifs est indisponible.")
            norm_goal = " ".join(str(payload["title"]).strip().lower().split())
            existing_goal = next(
                (
                    g
                    for g in self._objectives_service.list_goals(user_id)
                    if g.status != ObjectiveStatus.archived
                    and " ".join(g.title.strip().lower().split()) == norm_goal
                ),
                None,
            )
            if existing_goal is not None:
                return {
                    "entity": "personal_goal",
                    "entity_id": str(existing_goal.id),
                    "goal_id": str(existing_goal.id),
                    "title": existing_goal.title,
                    "learning_path_id": str(existing_goal.learning_path_id) if existing_goal.learning_path_id else None,
                    "skill_id": str(existing_goal.skill_id) if existing_goal.skill_id else None,
                    "reused_existing": True,
                }
            created_goal = self._objectives_service.create_goal(
                user_id,
                PersonalGoalCreate(
                    title=str(payload["title"]),
                    category=ObjectiveCategory(payload.get("category", "learning_goal")),
                    goal=str(payload["goal"]),
                    description=payload.get("description"),
                    current_level=payload.get("current_level"),
                    target_level=payload.get("target_level"),
                    priority=TaskPriority(payload.get("priority", "high")),
                    is_primary=bool(payload.get("is_primary", False)),
                    motivation=payload.get("motivation"),
                    weekly_target_minutes=int(payload.get("weekly_target_minutes", 180)),
                    next_action=str(payload.get("next_action") or "Planifier la première séance"),
                    create_linked_entities=bool(payload.get("create_linked_entities", True)),
                ),
            )
            if compensations is not None:
                gid = created_goal.id
                linked_sk = created_goal.skill_id
                linked_lp = created_goal.learning_path_id
                def _undo_goal(
                    gid: UUID = gid,
                    linked_sk: UUID | None = linked_sk,
                    linked_lp: UUID | None = linked_lp,
                ) -> None:
                    self._objectives_service.delete_goal(user_id, gid)  # type: ignore[union-attr]
                    if linked_sk is not None:
                        try:
                            self._skill_service.delete_skill(user_id, linked_sk)
                        except AppError:
                            pass
                    if linked_lp is not None and self._learning_service is not None:
                        try:
                            self._learning_service.delete_path(user_id, linked_lp)
                        except AppError:
                            pass
                compensations.append(_undo_goal)
            return {
                "entity": "personal_goal",
                "entity_id": str(created_goal.id),
                "goal_id": str(created_goal.id),
                "title": created_goal.title,
                "learning_path_id": str(created_goal.learning_path_id) if created_goal.learning_path_id else None,
                "skill_id": str(created_goal.skill_id) if created_goal.skill_id else None,
            }

        if action_type == AiActionType.update_personal_goal:
            if self._objectives_service is None:
                raise AppError(500, "OBJECTIVES_SERVICE_UNAVAILABLE", "Le service Objectifs est indisponible.")
            gid = UUID(payload["goal_id"])
            prev_goal = self._objectives_service.get_goal(user_id, gid)
            patch_data = {}
            for k in ("title", "goal", "description", "is_primary", "weekly_target_minutes", "next_action"):
                if k in payload and payload[k] is not None:
                    patch_data[k] = payload[k]
            if "priority" in payload and payload["priority"] is not None:
                patch_data["priority"] = TaskPriority(payload["priority"])
            if "status" in payload and payload["status"] is not None:
                patch_data["status"] = ObjectiveStatus(payload["status"])
            updated_goal = self._objectives_service.update_goal(
                user_id, gid, PersonalGoalUpdate(**patch_data)
            )
            if compensations is not None:
                compensations.append(
                    lambda gid=gid, prev=prev_goal: self._objectives_service.update_goal(  # type: ignore[union-attr]
                        user_id, gid, PersonalGoalUpdate(status=prev.status, next_action=prev.next_action)
                    )
                )
            return {
                "entity": "personal_goal",
                "entity_id": str(updated_goal.id),
                "goal_id": str(updated_goal.id),
                "title": updated_goal.title,
                "status": updated_goal.status.value,
            }

        if action_type == AiActionType.plan_strategic_activity:
            activity_title = str(payload["activity_title"]).strip()
            goal = str(payload["goal"]).strip()
            category = str(payload.get("category", "learning"))

            if payload.get("park_only"):
                parked_task = self._task_service.create_task(
                    user_id,
                    TaskCreate(
                        title=activity_title,
                        description=(
                            f"Idée placée au Parking par le Copilote IA. Objectif : {goal}"
                        ),
                        priority=TaskPriority.low,
                        status=TaskStatus.parked,
                    ),
                    source=TaskSource.ai_proposal,
                    proposal_id=proposal_id,
                )
                if compensations is not None:
                    tid = parked_task.id
                    compensations.append(lambda tid=tid: self._task_service.delete_task(user_id, tid))
                return {
                    "entity": "parked_idea",
                    "entity_id": str(parked_task.id),
                    "task_id": str(parked_task.id),
                    "activity_title": activity_title,
                    "created_events_count": 0,
                    "confirmation": (
                        f"Idée « {activity_title} » enregistrée dans votre Parking sans aucune surcharge de planning."
                    ),
                }

            local_compensations: list[Callable[[], None]] = []
            learning_path_id: str | None = None
            module_id: str | None = None
            project_id: str | None = None
            course_id: str | None = None
            goal_id: str | None = None

            try:
                if payload.get("create_course") and self._course_service is not None:
                    created_course = self._course_service.create_course(
                        user_id,
                        CourseCreate(
                            subject=str(payload.get("course_subject") or activity_title),
                            title=activity_title,
                            goal=goal,
                            language="fr",
                            total_levels=3,
                        ),
                    )
                    course_id = str(created_course.id)
                    cid = created_course.id
                    local_compensations.append(lambda cid=cid: self._course_service.delete_course(user_id, cid))  # type: ignore[union-attr]

                if payload.get("create_project") and self._project_service is not None:
                    created_proj = self._project_service.create_project(
                        user_id,
                        ProjectCreate(
                            name=activity_title,
                            description=f"Projet initié et vérifié via le Copilote IA. {payload.get('opportunity_cost_note') or ''}".strip(),
                            goal=goal,
                            status=ProjectStatus.active,
                            priority=TaskPriority.normal,
                            next_action=f"Démarrer la première séance : {activity_title}"[:240],
                        ),
                    )
                    project_id = str(created_proj.id)
                    pid = created_proj.id
                    local_compensations.append(lambda pid=pid: self._project_service.delete_project(user_id, pid))  # type: ignore[union-attr]
                elif payload.get("create_learning_path", True) and self._learning_service is not None:
                    created_path = self._learning_service.create_path(
                        user_id,
                        LearningPathCreate(
                            title=activity_title,
                            description=(
                                f"Parcours planifié avec le Copilote IA ({payload.get('frequency_per_week', 2)} séance(s)/sem., ~{payload.get('estimated_weeks', 3)} sem.)."
                            ),
                            goal=goal,
                            status=LearningStatus.active,
                        ),
                    )
                    learning_path_id = str(created_path.id)
                    lpid = created_path.id
                    local_compensations.append(lambda lpid=lpid: self._learning_service.delete_path(user_id, lpid))  # type: ignore[union-attr]
                    created_module = self._learning_service.create_module(
                        user_id,
                        LearningModuleCreate(
                            path_id=created_path.id,
                            title="Module 1 — Fondamentaux et mise en pratique",
                            description=goal,
                            position=1,
                            status=LearningStatus.active,
                        ),
                    )
                    module_id = str(created_module.id)

                goal_task = self._task_service.create_task(
                    user_id,
                    TaskCreate(
                        title=f"Objectif : {activity_title}"[:140],
                        description=goal,
                        priority=TaskPriority.normal,
                        status=TaskStatus.todo,
                        project_id=UUID(project_id) if project_id else None,
                        module_id=UUID(module_id) if module_id else None,
                    ),
                    source=TaskSource.ai_proposal,
                    proposal_id=proposal_id,
                )
                gtid = goal_task.id
                local_compensations.append(lambda gtid=gtid: self._task_service.delete_task(user_id, gtid))

                if self._objectives_service is not None:
                    existing_goals = self._objectives_service.list_goals(user_id)
                    existing_same = next(
                        (
                            g
                            for g in existing_goals
                            if g.title.strip().lower() == activity_title.lower()
                            and g.status != ObjectiveStatus.archived
                        ),
                        None,
                    )
                    if existing_same is None:
                        obj_cat = (
                            ObjectiveCategory.project
                            if category == "project"
                            else ObjectiveCategory.learning_goal
                        )
                        freq_w = max(1, int(payload.get("frequency_per_week") or 2))
                        sess_m = max(30, int(payload.get("session_duration_minutes") or 60))
                        created_goal = self._objectives_service.create_goal(
                            user_id,
                            PersonalGoalCreate(
                                title=activity_title,
                                category=obj_cat,
                                goal=goal,
                                priority=TaskPriority.high,
                                is_primary=False,
                                weekly_target_minutes=min(2400, freq_w * sess_m),
                                next_action=f"Démarrer : {activity_title}"[:240],
                                create_linked_entities=False,
                            ),
                        )
                        goal_id = str(created_goal.id)
                        gid = created_goal.id
                        local_compensations.append(lambda gid=gid: self._objectives_service.delete_goal(user_id, gid))  # type: ignore[union-attr]
                        if self._goal_repo is not None:
                            g_rec = self._goal_repo.get(user_id, gid)
                            if g_rec is not None:
                                matching_skill = next(
                                    (
                                        s
                                        for s in self._skill_service.list_skills(user_id)
                                        if s.name.strip().lower() in activity_title.lower()
                                        or activity_title.lower() in s.name.strip().lower()
                                    ),
                                    None,
                                )
                                self._goal_repo.save(
                                    g_rec.model_copy(
                                        update={
                                            "learning_path_id": UUID(learning_path_id) if learning_path_id else g_rec.learning_path_id,
                                            "course_id": UUID(course_id) if course_id else g_rec.course_id,
                                            "skill_id": matching_skill.id if matching_skill else g_rec.skill_id,
                                            "updated_at": datetime.now(timezone.utc),
                                        }
                                    )
                                )
                    else:
                        goal_id = str(existing_same.id)

                event_type = (
                    ScheduleEventType.project
                    if category == "project" or payload.get("create_project")
                    else (
                        ScheduleEventType.personal
                        if category == "personal"
                        else ScheduleEventType.learning
                    )
                )
                raw_slots = list(payload.get("proposed_slots") or [])
                estimated_weeks = max(1, min(4, int(payload.get("estimated_weeks") or 1)))
                existing_events = self._schedule_service.list_events(user_id)
                expanded_slots = list(raw_slots)
                if estimated_weeks > 1 and raw_slots:
                    slot_dates = sorted({str(s.get("local_date") or "")[:10] for s in raw_slots if s.get("local_date")})
                    spans_single_week = True
                    if len(slot_dates) >= 2:
                        try:
                            d_min = datetime.fromisoformat(slot_dates[0]).date()
                            d_max = datetime.fromisoformat(slot_dates[-1]).date()
                            spans_single_week = (d_max - d_min).days < 7
                        except ValueError:
                            spans_single_week = True
                    if spans_single_week:
                        for wk in range(1, min(3, estimated_weeks)):
                            for base_slot in raw_slots:
                                b_start = datetime.fromisoformat(str(base_slot["starts_at"])) + timedelta(days=7 * wk)
                                b_end = datetime.fromisoformat(str(base_slot["ends_at"])) + timedelta(days=7 * wk)
                                has_conflict = any(
                                    do_events_overlap(b_start, b_end, ev.starts_at, ev.ends_at)
                                    for ev in existing_events
                                )
                                if not has_conflict:
                                    expanded_slots.append(
                                        {
                                            **base_slot,
                                            "local_date": b_start.date().isoformat(),
                                            "starts_at": b_start.isoformat(),
                                            "ends_at": b_end.isoformat(),
                                        }
                                    )

                created_event_ids: list[str] = []
                for idx, slot in enumerate(expanded_slots, start=1):
                    note_parts = [f"Objectif : {goal}", f"Séance {idx}"]
                    if learning_path_id:
                        note_parts.append(f"Parcours ID : {learning_path_id}")
                    if project_id:
                        note_parts.append(f"Projet ID : {project_id}")
                    if course_id:
                        note_parts.append(f"Cours ID : {course_id}")
                    if goal_id:
                        note_parts.append(f"Objectif ID : {goal_id}")
                    note_parts.append(f"Tâche liée : {goal_task.id}")
                    created_ev = self._schedule_service.create_event(
                        user_id,
                        ScheduleEventCreate(
                            title=activity_title,
                            type=event_type,
                            starts_at=slot["starts_at"],
                            ends_at=slot["ends_at"],
                            notes=" · ".join(note_parts)[:1000],
                            source=ScheduleEventSource.ai_proposal,
                        ),
                    )
                    evid = created_ev.id
                    local_compensations.append(lambda evid=evid: self._schedule_service.delete_event(user_id, evid))
                    created_event_ids.append(str(created_ev.id))
            except Exception as exc:
                self._safe_rollback(local_compensations)
                if isinstance(exc, AppError):
                    raise _RollbackAppError(
                        exc.status_code,
                        exc.code,
                        exc.message,
                        rollback_info={
                            "rolled_back": True,
                            "compensated_count": len(local_compensations),
                        },
                    ) from exc
                raise

            if compensations is not None:
                compensations.extend(local_compensations)

            return {
                "entity": "strategic_activity",
                "entity_id": goal_id or learning_path_id or project_id or str(goal_task.id),
                "activity_title": activity_title,
                "goal_id": goal_id,
                "learning_path_id": learning_path_id,
                "module_id": module_id,
                "project_id": project_id,
                "course_id": course_id,
                "task_id": str(goal_task.id),
                "created_event_ids": created_event_ids,
                "created_events_count": len(created_event_ids),
                "confirmation": (
                    f"« {activity_title} » enregistré : {len(created_event_ids)} séance(s) ajoutée(s) au calendrier et reliée(s) à votre objectif."
                ),
            }

        if action_type == AiActionType.create_course:
            if self._course_service is None:
                raise AppError(
                    500,
                    "COURSE_SERVICE_UNAVAILABLE",
                    "Le service Cours n’est pas configuré.",
                )
            norm_subj = " ".join(str(payload["subject"]).strip().lower().split())
            norm_ctitle = " ".join(str(payload.get("title") or "").strip().lower().split())
            existing_course = next(
                (
                    c
                    for c in self._course_service.list_courses(user_id)
                    if c.status.value != "archived"
                    and (
                        " ".join(c.subject.strip().lower().split()) == norm_subj
                        or (norm_ctitle and " ".join(c.title.strip().lower().split()) == norm_ctitle)
                    )
                ),
                None,
            )
            if existing_course is not None:
                return {
                    "entity": "course",
                    "entity_id": str(existing_course.id),
                    "course_id": str(existing_course.id),
                    "title": existing_course.title,
                    "subject": existing_course.subject,
                    "current_level": existing_course.current_level,
                    "total_levels": existing_course.total_levels,
                    "reused_existing": True,
                }
            created_course = self._course_service.create_course(
                user_id,
                CourseCreate(
                    subject=str(payload["subject"]),
                    title=payload.get("title"),
                    domain=payload.get("domain"),
                    language=payload.get("language", "fr"),
                    total_levels=int(payload.get("total_levels", 3)),
                    goal=payload.get("goal"),
                ),
            )
            if compensations is not None:
                cid = created_course.id
                compensations.append(lambda cid=cid: self._course_service.delete_course(user_id, cid))  # type: ignore[union-attr]
            return {
                "entity": "course",
                "entity_id": str(created_course.id),
                "course_id": str(created_course.id),
                "title": created_course.title,
                "subject": created_course.subject,
                "current_level": created_course.current_level,
                "total_levels": created_course.total_levels,
            }

        if action_type == AiActionType.update_preferences:
            if self._ai_memory_repo is None:
                raise AppError(500, "MEMORY_UNAVAILABLE", "La mémoire IA structurée n’est pas configurée.")
            prev_mem = self._ai_memory_repo.get_or_create(user_id)
            avail_keys = (
                "study_start_hour",
                "study_end_hour",
                "max_daily_study_minutes",
                "preferred_session_minutes",
                "excluded_days",
            )
            avail_patch = {k: payload[k] for k in avail_keys if k in payload and payload[k] is not None}
            mem_updates: dict[str, Any] = {}
            if avail_patch:
                mem_updates["availability_preferences"] = avail_patch
            if "weekly_study_hours" in payload and payload["weekly_study_hours"] is not None:
                mem_updates["weekly_study_hours"] = int(payload["weekly_study_hours"])
            if "preferred_session_minutes" in payload and payload["preferred_session_minutes"] is not None:
                mem_updates["default_session_minutes"] = int(payload["preferred_session_minutes"])
            if "constraints" in payload and payload["constraints"] is not None:
                mem_updates["constraints"] = list(payload["constraints"])
            if "long_term_goals" in payload and payload["long_term_goals"] is not None:
                mem_updates["long_term_goals"] = list(payload["long_term_goals"])
            if "academic_context" in payload and payload["academic_context"] is not None:
                mem_updates["academic_context"] = dict(payload["academic_context"])
            saved_mem = self._ai_memory_repo.patch(user_id, **mem_updates)
            self._sync_availability_to_profile(
                user_id,
                dict(saved_mem.availability_preferences or {}),
                weekly_study_hours=saved_mem.weekly_study_hours,
                default_session_minutes=saved_mem.default_session_minutes,
                ai_instructions=payload.get("ai_instructions"),
            )
            if compensations is not None:
                compensations.append(lambda prev=prev_mem: self._ai_memory_repo.save(prev))  # type: ignore[union-attr]
            return {
                "entity": "preferences",
                "entity_id": str(user_id),
                "weekly_study_hours": saved_mem.weekly_study_hours,
                "availability_preferences": saved_mem.availability_preferences,
            }

        if action_type == AiActionType.batch_actions:
            raw_steps = list(payload.get("steps") or [])
            compensate = bool(payload.get("compensate_on_failure", True))
            batch_compensations: list[Callable[[], None]] = []
            step_results: list[dict[str, Any]] = []
            for idx, step in enumerate(raw_steps):
                step_action = AiActionType(step["action_type"])
                step_payload = dict(step.get("payload") or {})
                link_map = step.get("link_to_step") or {}
                for fk_name, src_idx in link_map.items():
                    if not isinstance(src_idx, int) or src_idx < 0 or src_idx >= len(step_results):
                        if compensate:
                            self._safe_rollback(batch_compensations)
                        raise _RollbackAppError(
                            422,
                            "VALIDATION_ERROR",
                            f"Lien inter-étapes invalide à l’étape {idx}.",
                            rollback_info={
                                "rolled_back": compensate,
                                "failed_step_index": idx,
                                "compensated_count": len(batch_compensations) if compensate else 0,
                            },
                        )
                    src_res = step_results[src_idx]
                    resolved_id = src_res.get(fk_name)
                    if not resolved_id:
                        if compensate:
                            self._safe_rollback(batch_compensations)
                        raise _RollbackAppError(
                            422,
                            "VALIDATION_ERROR",
                            f"Identifiant « {fk_name} » introuvable après l’étape {src_idx}.",
                            rollback_info={
                                "rolled_back": compensate,
                                "failed_step_index": idx,
                                "compensated_count": len(batch_compensations) if compensate else 0,
                            },
                        )
                    step_payload[fk_name] = resolved_id
                try:
                    validated_step = self._action_validator.validate_action_payload(
                        user_id, step_action, step_payload
                    )
                    res = self._execute_validated_action(
                        user_id,
                        proposal_id,
                        step_action,
                        validated_step,
                        compensations=batch_compensations,
                    )
                    step_results.append({"action_type": step_action.value, **res})
                except Exception as exc:
                    if compensate:
                        self._safe_rollback(batch_compensations)
                    if isinstance(exc, AppError):
                        raise _RollbackAppError(
                            exc.status_code,
                            exc.code,
                            exc.message,
                            rollback_info={
                                "rolled_back": compensate,
                                "failed_step_index": idx,
                                "compensated_count": len(batch_compensations) if compensate else 0,
                            },
                        ) from exc
                    raise _RollbackAppError(
                        500,
                        "BATCH_EXECUTION_FAILED",
                        "Échec lors de l’exécution coordonnée des actions.",
                        rollback_info={
                            "rolled_back": compensate,
                            "failed_step_index": idx,
                            "compensated_count": len(batch_compensations) if compensate else 0,
                        },
                    ) from exc

            if compensations is not None:
                compensations.extend(batch_compensations)
            return {
                "entity": "batch",
                "summary": payload.get("summary") or f"{len(step_results)} actions exécutées",
                "steps_count": len(step_results),
                "step_results": step_results,
            }

        if action_type == AiActionType.manage_availability_rule:
            if self._planning_service is None:
                raise AppError(
                    500,
                    "PLANNING_SERVICE_UNAVAILABLE",
                    "Le moteur de planification n’est pas configuré.",
                )
            from app.schemas.planning import AvailabilityRuleCreate

            rule = self._planning_service.create_availability_rule(
                user_id,
                AvailabilityRuleCreate(
                    label=str(payload["label"]),
                    rule_type=payload.get("rule_type", "personal_unavailability"),
                    day_of_week=payload.get("day_of_week"),
                    start_time=payload.get("start_time"),
                    end_time=payload.get("end_time"),
                    starts_at=payload.get("starts_at"),
                    ends_at=payload.get("ends_at"),
                    timezone=payload.get("timezone", "Europe/Paris"),
                    recurrence=payload.get("recurrence", "weekly"),
                    notes=payload.get("notes"),
                ),
            )
            if compensations is not None:
                rid = rule.id
                compensations.append(
                    lambda rid=rid: self._planning_service.delete_availability_rule(user_id, rid)  # type: ignore[union-attr]
                )
            return {
                "entity": "availability_rule",
                "entity_id": str(rule.id),
                "label": rule.label,
                "rule_type": rule.rule_type.value,
                "day_of_week": rule.day_of_week,
                "start_time": rule.start_time,
                "end_time": rule.end_time,
            }

        if action_type == AiActionType.generate_learning_plan:
            if self._planning_service is None:
                raise AppError(
                    500,
                    "PLANNING_SERVICE_UNAVAILABLE",
                    "Le moteur de planification n’est pas configuré.",
                )
            from app.schemas.planning import LearningPlanApplyRequest, LearningPlanGenerateRequest

            plan_version_id_raw = payload.get("plan_version_id")
            if plan_version_id_raw:
                version = self._planning_service.get_version(user_id, UUID(str(plan_version_id_raw)))
            elif payload.get("instruction"):
                from app.schemas.planning import LearningPlanAdjustRequest

                version = self._planning_service.adjust_plan(
                    user_id,
                    LearningPlanAdjustRequest(
                        instruction=str(payload["instruction"]),
                        horizon_days=payload.get("horizon_days"),
                        replace_future_planned=bool(payload.get("replace_future_planned", True)),
                    ),
                )
            else:
                version = self._planning_service.generate_plan(
                    user_id,
                    LearningPlanGenerateRequest(
                        horizon_days=int(payload.get("horizon_days") or 7),
                        focus_subject=payload.get("focus_subject"),
                        exam_title=payload.get("exam_title"),
                        exam_at=payload.get("exam_at"),
                        weekly_hours_override=payload.get("weekly_hours_override"),
                        daily_max_minutes=payload.get("daily_max_minutes"),
                        preferred_session_minutes=payload.get("preferred_session_minutes"),
                        include_potential_slots=bool(payload.get("include_potential_slots", True)),
                        create_missing_courses=bool(payload.get("create_missing_courses", False)),
                    ),
                )

            applied = version
            if version.planned_sessions:
                applied = self._planning_service.apply_plan(
                    user_id,
                    version.id,
                    LearningPlanApplyRequest(
                        replace_future_planned=bool(payload.get("replace_future_planned", True)),
                    ),
                )
            return {
                "entity": "learning_plan",
                "entity_id": str(applied.id),
                "version_id": str(applied.id),
                "version_number": applied.version_number,
                "status": applied.status.value,
                "applied_event_ids": applied.applied_event_ids,
                "applied_task_ids": applied.applied_task_ids,
                "applied_event_count": len(applied.applied_event_ids),
                "confirmation": applied.rationale,
            }

        raise AppError(422, "UNSUPPORTED_AI_ACTION", "Action IA non prise en charge.")

    def reject_proposal(
        self,
        user_id: UUID,
        proposal_id: UUID,
        request: RejectProposalRequest | None = None,
    ) -> AiActionProposalResponse:
        record = self._ai_repo.get_proposal(user_id, proposal_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Proposition d’action introuvable.")

        now = datetime.now(timezone.utc)
        record = self._refresh_proposal_expiration(record, now)
        if record.status != ProposalStatus.pending:
            raise AppError(
                409,
                "CONFLICT",
                "Seule une proposition en attente peut être rejetée.",
            )

        rejected = self._ai_repo.save_proposal(
            record.model_copy(
                update={
                    "status": ProposalStatus.rejected,
                    "error_message": request.reason if request and request.reason else None,
                    "resolved_at": now,
                }
            )
        )
        return AiActionProposalResponse.model_validate(rejected.model_dump())

    def generate_daily_briefing(
        self,
        user_id: UUID,
        *,
        now_utc: datetime | None = None,
        force: bool = False,
    ) -> AiReportResponse:
        ref_now = now_utc or datetime.now(timezone.utc)
        ctx = self._context_builder.build_context(
            user_id,
            explicit_scopes=[AiContextScope.today, AiContextScope.tasks, AiContextScope.schedule, AiContextScope.projects],
            now_utc=ref_now,
        )
        tz = ZoneInfo(ctx.profile["timezone"])
        local_now = ref_now.astimezone(tz)
        day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(
            timezone.utc
        )
        day_end = local_now.replace(hour=23, minute=59, second=59, microsecond=0).astimezone(
            timezone.utc
        )
        if not force:
            existing_daily = self._ai_repo.list_reports(
                user_id, report_type=AiReportType.daily_briefing
            )
            for item in existing_daily:
                if item.period_start.astimezone(tz).date() == local_now.date():
                    return AiReportResponse.model_validate(item.model_dump())

        priority = ctx.profile.get("active_priority_title")
        today_events = [e for e in ctx.schedule_events if e.get("is_today")]
        today_uni_courses = [e for e in today_events if e.get("is_university_course")]
        today_personal_blocks = [e for e in today_events if not e.get("is_university_course")]
        today_rec_windows = (
            ((ctx.availability or {}).get("today") or {}).get("recommended_study_windows") or []
        )
        overdue_count = ctx.stats.get("overdue_tasks_count", 0)
        active_projects = [p for p in ctx.projects if p.get("status") == "active"]

        lines = [
            f"## Briefing quotidien : {ctx.profile['local_date']} ({ctx.profile['timezone']})",
            f"- **Priorité principale active** : {priority or 'Non définie (à fixer pour éviter la dispersion)'}",
            f"- **Créneaux du jour** : {len(today_events)} créneau(x) planifié(s) "
            f"({len(today_uni_courses)} cours universitaire(s), {len(today_personal_blocks)} séance(s) personnelle(s)).",
        ]
        for ev in today_uni_courses[:5]:
            time_tag = (
                f" ({ev['local_start_time']} à {ev['local_end_time']})"
                if ev.get("local_start_time")
                else ""
            )
            room_tag = f" · {ev['room']}" if ev.get("room") else ""
            lines.append(f"  - `[Cours universitaire]` **{ev['title']}**{time_tag}{room_tag}")
        for ev in today_personal_blocks[:5]:
            time_tag = (
                f" ({ev['local_start_time']} à {ev['local_end_time']})"
                if ev.get("local_start_time")
                else ""
            )
            lines.append(f"  - `[{ev['type']}]` **{ev['title']}**{time_tag}")
        if today_rec_windows:
            win_str = ", ".join(
                f"{w['local_start_time']} à {w['local_end_time']}" for w in today_rec_windows[:3]
            )
            lines.append(f"- **Créneaux libres recommandés (hors cours & pauses)** : {win_str}")

        lines.append(
            f"- **Tâches actives** : {ctx.stats.get('active_tasks_count', 0)} (dont {overdue_count} en retard)."
        )
        for task in ctx.tasks[:3]:
            overdue_tag = " *(en retard)*" if task.get("is_overdue") else ""
            lines.append(f"  - [{task['priority']}] **{task['title']}**{overdue_tag}")

        if active_projects:
            p0 = active_projects[0]
            lines.append(
                f"- **Prochaine action projet ({p0['name']})** : {p0['next_action']}"
            )

        if ctx.is_partial_data:
            lines.append(
                "\n> **Note AI-06 (données partielles)** : " + " ; ".join(ctx.missing_data)
            )

        saved = self._ai_repo.save_report(
            AiReportRecord(
                id=uuid4(),
                user_id=user_id,
                type=AiReportType.daily_briefing,
                period_start=day_start,
                period_end=day_end,
                content="\n".join(lines),
                metadata={
                    "is_estimate": ctx.is_partial_data,
                    "missing_data": ctx.missing_data,
                    "stats": ctx.stats,
                },
                created_at=ref_now,
            )
        )
        return AiReportResponse.model_validate(saved.model_dump())

    def generate_weekly_review(
        self,
        user_id: UUID,
        *,
        now_utc: datetime | None = None,
        force: bool = False,
    ) -> AiReportResponse:
        ref_now = now_utc or datetime.now(timezone.utc)
        ctx = self._context_builder.build_context(
            user_id,
            explicit_scopes=[
                AiContextScope.weekly,
                AiContextScope.tasks,
                AiContextScope.learning,
                AiContextScope.skills,
                AiContextScope.projects,
            ],
            now_utc=ref_now,
        )
        tz = ZoneInfo(ctx.profile["timezone"])
        local_now = ref_now.astimezone(tz)
        period_end = local_now.replace(hour=23, minute=59, second=59, microsecond=0).astimezone(
            timezone.utc
        )
        period_start = (
            local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
        ).astimezone(timezone.utc)

        if not force:
            existing_weekly = self._ai_repo.list_reports(
                user_id, report_type=AiReportType.weekly_review
            )
            for item in existing_weekly:
                if item.period_end.astimezone(tz).date() == local_now.date():
                    return AiReportResponse.model_validate(item.model_dump())

        sessions_7d = ctx.stats.get("completed_sessions_last_7d_count", 0)
        minutes_7d = ctx.stats.get("completed_minutes_last_7d", 0)
        done_tasks_7d = ctx.stats.get("done_tasks_last_7d_count", 0)
        active_tasks_count = ctx.stats.get("active_tasks_count", 0)
        overdue_count = ctx.stats.get("overdue_tasks_count", 0)
        lessons_done = ctx.learning.get("lessons_completed", 0)
        lessons_total = ctx.learning.get("lessons_total", 0)
        approved_assessments = ctx.stats.get("approved_assessments_count", 0)
        needs_reinforcement = ctx.stats.get("needs_reinforcement_count", 0)
        unsubstantiated_skills = [
            s["name"]
            for s in ctx.skills
            if int(s.get("current_level", 0)) >= 3 and int(s.get("evidence_count", 0)) == 0
        ]
        active_projects = [p for p in ctx.projects if p.get("status") == "active"]

        lines = [
            "## Bilan hebdomadaire (7 derniers jours)",
            f"- **Temps d’étude réel achevé** : {minutes_7d} min réparties sur {sessions_7d} séance(s) terminée(s).",
            f"- **Exécution des tâches** : {done_tasks_7d} terminée(s) sur 7 jours · {active_tasks_count} encore active(s) ({overdue_count} en retard).",
            f"- **Progression apprentissage** : {lessons_done} / {lessons_total} leçon(s) terminée(s) *(leçon terminée ≠ compétence validée)*.",
            f"- **Validation des compétences** : {approved_assessments} évaluation(s) validée(s) · {needs_reinforcement} évaluation(s) à renforcer.",
            f"- **Projets actifs** : {len(active_projects)} projet(s) actif(s).",
        ]

        if len(active_projects) > 3:
            lines.append(
                "  - ⚠️ **Alerte dispersion (PROJ-01)** : plus de 3 projets sont actifs simultanément."
            )

        if unsubstantiated_skills:
            lines.append(
                "  - ⚠️ **Compétences ≥ 3 sans preuve (SKILL-03)** : "
                + ", ".join(unsubstantiated_skills)
            )

        missed_count = int(ctx.stats.get("missed_study_blocks_count", 0))
        if missed_count > 0:
            missed_titles = (ctx.strategic_analysis or {}).get("missed_block_titles") or []
            lines.append(
                f"  - ⚠️ **Suivi d’exécution** : {missed_count} séance(s) planifiée(s) n’ont pas été réalisées "
                f"({', '.join(missed_titles[:3])}). Un ajustement du rythme est recommandé."
            )

        if ctx.is_partial_data:
            lines.append(
                "\n> **Note AI-06 (estimation / données manquantes)** : "
                + " ; ".join(ctx.missing_data)
            )

        saved = self._ai_repo.save_report(
            AiReportRecord(
                id=uuid4(),
                user_id=user_id,
                type=AiReportType.weekly_review,
                period_start=period_start,
                period_end=period_end,
                content="\n".join(lines),
                metadata={
                    "is_estimate": ctx.is_partial_data,
                    "missing_data": ctx.missing_data,
                    "stats": ctx.stats,
                },
                created_at=ref_now,
            )
        )
        return AiReportResponse.model_validate(saved.model_dump())

    def ensure_periodic_reports(
        self,
        user_id: UUID,
        *,
        now_utc: datetime | None = None,
    ) -> EnsureAiReportsResponse:
        ref_now = now_utc or datetime.now(timezone.utc)
        existing_ids = {r.id for r in self._ai_repo.list_reports(user_id)}
        daily = self.generate_daily_briefing(user_id, now_utc=ref_now, force=False)
        weekly = self.generate_weekly_review(user_id, now_utc=ref_now, force=False)
        return EnsureAiReportsResponse(
            daily_briefing=daily,
            weekly_review=weekly,
            created_daily=daily.id not in existing_ids,
            created_weekly=weekly.id not in existing_ids,
        )

    def list_reports(
        self,
        user_id: UUID,
        *,
        report_type: AiReportType | None = None,
    ) -> list[AiReportResponse]:
        records = self._ai_repo.list_reports(user_id, report_type=report_type)
        records.sort(key=lambda item: item.created_at, reverse=True)
        return [AiReportResponse.model_validate(item.model_dump()) for item in records]
