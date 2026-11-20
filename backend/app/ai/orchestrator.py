from datetime import datetime, timedelta, timezone
from typing import Any, Literal
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
    _validate_outbound_base_url,
    build_ai_provider_from_config,
    canonicalize_provider_name,
    fetch_provider_models,
    normalize_provider_base_url,
)
from app.ai.tool_registry import ToolRegistry
from app.core.config import Settings
from app.core.errors import AppError
from app.repositories.ai_sql import (
    AiActionProposalRecord,
    AiConversationRecord,
    AiMessageRecord,
    AiReportRecord,
    SqlAiRepository,
)
from app.schemas.ai import (
    AcceptProposalRequest,
    AiActionProposalResponse,
    AiConversationCreate,
    AiConversationDetailResponse,
    AiConversationResponse,
    AiMessageCreate,
    AiMessageResponse,
    AiProviderCatalogItem,
    AiProviderConfigResponse,
    AiProviderConfigUpdate,
    AiProviderModelInfo,
    AiReportResponse,
    AiToolSpec,
    AiTurnResponse,
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
from app.schemas.learning import LearningModuleCreate, LearningPathCreate
from app.schemas.projects import ProjectCreate
from app.schemas.schedule import ScheduleEventCreate
from app.schemas.skills import (
    SkillAssessmentCreate,
    SkillAssessmentDecision,
    SkillEvidenceCreate,
)
from app.schemas.tasks import TaskCreate, TaskUpdate
from app.services.courses_service import CourseService
from app.services.learning_service import LearningService
from app.services.profile_service import ProfileService
from app.services.projects_service import ProjectService
from app.services.schedule_service import ScheduleService
from app.services.skills_service import SkillService
from app.services.tasks_service import TaskService

PROPOSAL_TTL_DAYS = 7

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
        label="Local (déterministe, sans clé API)",
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
        self._settings = settings
        self._has_custom_provider = has_custom_provider
        self._rate_limit = rate_limit_per_minute

    def list_tools(self) -> list[AiToolSpec]:
        return self._tool_registry.list_tools()

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
            api_key = str(saved.get("api_key") or "").strip()
            if (
                not api_key
                and self._settings is not None
                and canonicalize_provider_name(self._settings.ai_provider) == provider_key
            ):
                api_key = (self._settings.ai_api_key or "").strip()
            base_url = normalize_provider_base_url(provider_key, saved.get("base_url"))
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
        if source == "user":
            timeout = self._settings.ai_timeout_seconds if self._settings else 20.0
            return build_ai_provider_from_config(
                provider=provider_key,
                api_key=api_key,
                model_name=model,
                base_url=base_url,
                timeout_seconds=timeout,
            )
        return self._provider

    def get_provider_config(self, user_id: UUID) -> AiProviderConfigResponse:
        provider_key, api_key, base_url, model, source = self._resolve_effective_ai_config(user_id)
        return AiProviderConfigResponse(
            provider=provider_key,  # type: ignore[arg-type]
            base_url=base_url,
            model=model,
            has_api_key=bool(api_key),
            api_key_preview=_mask_api_key(api_key),
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

        effective_key = persisted_api_key or ("" if payload.clear_api_key else server_env_key)

        if provider_key == "local":
            resolved_url = ""
            resolved_model = (payload.model or "").strip() or "local-coach-v1"
            persisted_api_key = ""
        else:
            if not effective_key:
                raise AppError(
                    400,
                    "AI_API_KEY_REQUIRED",
                    "Veuillez saisir une clé API pour activer ce fournisseur IA.",
                )
            resolved_url = _validate_outbound_base_url(
                normalize_provider_base_url(provider_key, payload.base_url)
            )
            resolved_model = (payload.model or "").strip() or _default_model_for_provider(provider_key)

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
    ) -> FetchProviderModelsResponse:
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

        resolved_key = (payload.api_key or "").strip()
        if not resolved_key and same_saved_provider:
            resolved_key = str(saved.get("api_key") or "").strip()
        if not resolved_key and same_env_provider and self._settings is not None:
            resolved_key = (self._settings.ai_api_key or "").strip()

        resolved_base_url: str | None = payload.base_url
        if not resolved_base_url and same_saved_provider:
            resolved_base_url = saved.get("base_url")
        if not resolved_base_url and same_env_provider and self._settings is not None:
            resolved_base_url = self._settings.ai_base_url

        timeout = min(15.0, self._settings.ai_timeout_seconds) if self._settings else 15.0
        effective_url, raw_models = fetch_provider_models(
            provider=provider_key,
            api_key=resolved_key,
            base_url=resolved_base_url,
            timeout_seconds=timeout,
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
            return self._ai_repo.save_proposal(expired)
        return record

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
        conv = self._ai_repo.get_conversation(user_id, conversation_id)
        if conv is None:
            raise AppError(404, "NOT_FOUND", "Conversation IA introuvable.")

        now = datetime.now(timezone.utc)
        messages = self._ai_repo.list_messages(user_id, conversation_id)
        messages.sort(key=lambda item: item.created_at)

        proposals = [
            self._refresh_proposal_expiration(item, now)
            for item in self._ai_repo.list_proposals(user_id, conversation_id=conversation_id)
        ]
        proposals.sort(key=lambda item: item.created_at, reverse=True)

        return AiConversationDetailResponse(
            conversation=AiConversationResponse.model_validate(conv.model_dump()),
            messages=[AiMessageResponse.model_validate(m.model_dump()) for m in messages],
            proposals=[AiActionProposalResponse.model_validate(p.model_dump()) for p in proposals],
        )

    def delete_conversation(self, user_id: UUID, conversation_id: UUID) -> None:
        if not self._ai_repo.delete_conversation(user_id, conversation_id):
            raise AppError(404, "NOT_FOUND", "Conversation IA introuvable.")

    def _check_rate_limit(self, user_id: UUID, conversation_id: UUID, now_utc: datetime) -> None:
        one_minute_ago = now_utc - timedelta(minutes=1)
        recent_user_messages = [
            m
            for m in self._ai_repo.list_messages(user_id, conversation_id)
            if m.role == AiMessageRole.user and m.created_at >= one_minute_ago
        ]
        if len(recent_user_messages) >= self._rate_limit:
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

        history_pairs = [
            {"role": m.role.value, "content": m.content}
            for m in existing_messages[-8:]
            if m.role in (AiMessageRole.user, AiMessageRole.assistant)
        ]

        active_provider = self._resolve_provider_for_user(user_id)
        provider_result = active_provider.generate_response(
            user_message=payload.content,
            history=history_pairs,
            context=bounded_context,
            prompt_manager=self._prompt_manager,
        )

        saved_proposals: list[AiActionProposalRecord] = []
        rejected_candidates_count = 0
        reply_Now = datetime.now(timezone.utc)

        for candidate in provider_result.proposals:
            try:
                validated = self._action_validator.validate_candidate(user_id, candidate)
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
                        created_at=reply_Now,
                    )
                )
                saved_proposals.append(proposal_record)
            except AppError:
                rejected_candidates_count += 1

        assistant_msg = self._ai_repo.save_message(
            AiMessageRecord(
                id=uuid4(),
                user_id=user_id,
                conversation_id=conversation_id,
                role=AiMessageRole.assistant,
                content=provider_result.reply,
                metadata={
                    "provider": provider_result.provider_name,
                    "model": provider_result.model_name,
                    "is_estimate": provider_result.is_estimate,
                    "missing_data": provider_result.missing_data,
                    "included_scopes": bounded_context.included_scopes,
                    "proposal_ids": [str(p.id) for p in saved_proposals],
                    "rejected_proposals_count": rejected_candidates_count,
                },
                created_at=reply_Now,
            )
        )

        return AiTurnResponse(
            user_message=AiMessageResponse.model_validate(user_msg.model_dump()),
            assistant_message=AiMessageResponse.model_validate(assistant_msg.model_dump()),
            proposals=[
                AiActionProposalResponse.model_validate(p.model_dump()) for p in saved_proposals
            ],
        )

    def list_proposals(
        self,
        user_id: UUID,
        *,
        status_filter: ProposalStatus | None = None,
    ) -> list[AiActionProposalResponse]:
        now = datetime.now(timezone.utc)
        records = [
            self._refresh_proposal_expiration(item, now)
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
        refreshed = self._refresh_proposal_expiration(record, datetime.now(timezone.utc))
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
            weekly_slots = list((ctx.availability or {}).get("weekly_candidate_slots") or [])
            if not weekly_slots:
                raise AppError(
                    409,
                    "NO_AVAILABLE_SLOTS",
                    "Aucun créneau libre disponible dans le calendrier pour recalculer cette proposition.",
                )
            target_freq = max(1, min(7, int(merged_payload.get("frequency_per_week") or 2)))
            target_dur = max(30, min(240, int(merged_payload.get("session_duration_minutes") or 60)))

            selected_raw: list[dict[str, Any]] = []
            used_dates: set[str] = set()
            for cand in weekly_slots:
                if len(selected_raw) >= target_freq:
                    break
                if cand["local_date"] not in used_dates:
                    selected_raw.append(cand)
                    used_dates.add(cand["local_date"])
            if len(selected_raw) < target_freq:
                for cand in weekly_slots:
                    if len(selected_raw) >= target_freq:
                        break
                    if cand not in selected_raw:
                        selected_raw.append(cand)

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
            merged_payload["frequency_per_week"] = len(recalculated_slots)
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
                slot_count = len(validated_payload.get("proposed_slots") or [])
                next_title = f"Programmer « {act_title} » ({slot_count} séance(s)/sem.)"
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

        # Étape intermédiaire traçable : accepted avant exécution
        accepted_record = self._ai_repo.save_proposal(
            record.model_copy(
                update={
                    "status": ProposalStatus.accepted,
                    "payload": validated_payload,
                }
            )
        )

        try:
            execution_result = self._execute_validated_action(
                user_id, accepted_record.id, action_enum, validated_payload
            )
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
            return AiActionProposalResponse.model_validate(executed.model_dump())
        except Exception as exc:
            err_msg = exc.message if isinstance(exc, AppError) else "Échec lors de l’exécution."
            self._ai_repo.save_proposal(
                accepted_record.model_copy(
                    update={
                        "status": ProposalStatus.failed,
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
    ) -> dict[str, Any]:
        if action_type == AiActionType.create_task:
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
            return {
                "entity": "task",
                "task_id": str(created_task.id),
                "title": created_task.title,
                "source": created_task.source.value,
            }

        if action_type == AiActionType.park_task:
            updated_task = self._task_service.update_task(
                user_id,
                UUID(payload["task_id"]),
                TaskUpdate(status=TaskStatus.parked),
            )
            return {
                "entity": "task",
                "task_id": str(updated_task.id),
                "title": updated_task.title,
                "status": updated_task.status.value,
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
                ),
            )
            return {
                "entity": "schedule_event",
                "event_id": str(created_event.id),
                "title": created_event.title,
                "has_conflict": created_event.has_conflict,
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
            return {
                "entity": "skill_evidence",
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
                    prompt_title=payload.get("prompt_title"),
                    prompt_instructions=payload.get("prompt_instructions"),
                    path_id=UUID(payload["path_id"]) if payload.get("path_id") else None,
                    module_id=UUID(payload["module_id"]) if payload.get("module_id") else None,
                    lesson_id=UUID(payload["lesson_id"]) if payload.get("lesson_id") else None,
                ),
            )
            return {
                "entity": "skill_assessment",
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
                "assessment_id": str(approved_assessment.id),
                "skill_id": str(updated_skill.id),
                "name": updated_skill.name,
                "current_level": updated_skill.current_level,
                "applied_level_delta": approved_assessment.applied_level_delta,
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
                return {
                    "entity": "parked_idea",
                    "task_id": str(parked_task.id),
                    "activity_title": activity_title,
                    "created_events_count": 0,
                    "confirmation": (
                        f"Idée « {activity_title} » enregistrée dans votre Parking sans aucune surcharge de planning."
                    ),
                }

            learning_path_id: str | None = None
            module_id: str | None = None
            project_id: str | None = None

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

            event_type = (
                ScheduleEventType.project
                if category == "project" or payload.get("create_project")
                else (
                    ScheduleEventType.personal
                    if category == "personal"
                    else ScheduleEventType.learning
                )
            )
            created_event_ids: list[str] = []
            for idx, slot in enumerate(payload.get("proposed_slots") or [], start=1):
                note_parts = [f"Objectif : {goal}", f"Séance {idx}"]
                if learning_path_id:
                    note_parts.append(f"Parcours ID : {learning_path_id}")
                if project_id:
                    note_parts.append(f"Projet ID : {project_id}")
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
                created_event_ids.append(str(created_ev.id))

            return {
                "entity": "strategic_activity",
                "activity_title": activity_title,
                "learning_path_id": learning_path_id,
                "module_id": module_id,
                "project_id": project_id,
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
            return {
                "entity": "course",
                "course_id": str(created_course.id),
                "title": created_course.title,
                "subject": created_course.subject,
                "current_level": created_course.current_level,
                "total_levels": created_course.total_levels,
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
        period_start = ref_now - timedelta(days=7)

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
                period_end=ref_now,
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

    def list_reports(
        self,
        user_id: UUID,
        *,
        report_type: AiReportType | None = None,
    ) -> list[AiReportResponse]:
        records = self._ai_repo.list_reports(user_id, report_type=report_type)
        records.sort(key=lambda item: item.created_at, reverse=True)
        return [AiReportResponse.model_validate(item.model_dump()) for item in records]
