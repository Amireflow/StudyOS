from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from app.ai.action_validator import ActionValidator
from app.ai.context_builder import ContextBuilder
from app.ai.prompt_manager import PromptManager
from app.ai.provider import AIProvider
from app.ai.tool_registry import ToolRegistry
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
    AiReportResponse,
    AiToolSpec,
    AiTurnResponse,
    RejectProposalRequest,
)
from app.schemas.common import (
    AiActionType,
    AiContextScope,
    AiMessageRole,
    AiReportType,
    ProposalStatus,
    ScheduleEventType,
    SkillEvidenceType,
    TaskPriority,
    TaskSource,
    TaskStatus,
)
from app.schemas.schedule import ScheduleEventCreate
from app.schemas.skills import SkillEvidenceCreate, SkillUpdate
from app.schemas.tasks import TaskCreate, TaskUpdate
from app.services.schedule_service import ScheduleService
from app.services.skills_service import SkillService
from app.services.tasks_service import TaskService

PROPOSAL_TTL_DAYS = 7


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
        self._rate_limit = rate_limit_per_minute

    def list_tools(self) -> list[AiToolSpec]:
        return self._tool_registry.list_tools()

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

        provider_result = self._provider.generate_response(
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

        if action_type == AiActionType.update_skill_level:
            updated_skill = self._skill_service.update_skill(
                user_id,
                UUID(payload["skill_id"]),
                SkillUpdate(
                    current_level=int(payload["current_level"]),
                    target_level=payload.get("target_level"),
                ),
            )
            return {
                "entity": "skill",
                "skill_id": str(updated_skill.id),
                "name": updated_skill.name,
                "current_level": updated_skill.current_level,
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
        overdue_count = ctx.stats.get("overdue_tasks_count", 0)
        active_projects = [p for p in ctx.projects if p.get("status") == "active"]

        lines = [
            f"## Briefing quotidien — {ctx.profile['local_date']} ({ctx.profile['timezone']})",
            f"- **Priorité principale active** : {priority or 'Non définie (à fixer pour éviter la dispersion)'}",
            f"- **Créneaux du jour** : {len(today_events)} créneau(x) planifié(s).",
        ]
        for ev in today_events[:5]:
            lines.append(f"  - `{ev['type']}` — **{ev['title']}**")

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
            f"- **Progression apprentissage** : {lessons_done} / {lessons_total} leçon(s) terminée(s).",
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
