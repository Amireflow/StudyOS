from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4
from app.core.errors import AppError
from app.planning.availability import AvailabilityEngine
from app.planning.collector import PlanningContextCollector, _ensure_utc
from app.planning.content_resolver import SessionContentResolver
from app.planning.prioritizer import LearningPrioritizer
from app.planning.allocator import WeeklyPlanAllocator
from app.repositories.ai_sql import SqlAiMemoryRepository
from app.repositories.courses_sql import SqlCourseRepository
from app.repositories.learning_sql import (
    SqlLearningRepository,
    SqlPersonalGoalRepository,
    SqlProjectRepository,
    SqlSkillRepository,
)
from app.repositories.memory import (
    ProfileRepository,
    ScheduleEventRecord,
    ScheduleRepository,
    SessionRepository,
    TaskRepository,
)
from app.repositories.planning_sql import (
    LearningPlanVersionRecord,
    SqlPlanningRepository,
    UserAvailabilityRuleRecord,
)
from app.schemas.common import (
    CourseLanguage,
    ScheduleEventSource,
    ScheduleEventType,
    SessionStatus,
    TaskPriority,
)
from app.schemas.courses import CourseCreate
from app.schemas.planning import (
    AvailabilityComputationResponse,
    AvailabilityRuleCreate,
    AvailabilityRuleResponse,
    AvailabilityRuleUpdate,
    LearningPlanAdjustRequest,
    LearningPlanApplyRequest,
    LearningPlanGenerateRequest,
    LearningPlanVersionResponse,
    LearningPriorityItem,
    PlanArbitrageItem,
    PlanLoadSummary,
    PlanMissingInfoItem,
    PlanVersionStatus,
    PlannedSessionProposal,
    ScheduleValidityResponse,
)
from app.schemas.schedule import ScheduleEventCreate
from app.schemas.tasks import TaskCreate
from app.services.courses_service import CourseService
from app.services.schedule_service import ScheduleService
from app.services.tasks_service import TaskService


def _intervals_overlap(s1: datetime, e1: datetime, s2: datetime, e2: datetime) -> bool:
    return s1 < e2 and e1 > s2


def _to_rule_response(rec: UserAvailabilityRuleRecord) -> AvailabilityRuleResponse:
    return AvailabilityRuleResponse(**rec.model_dump())


class LearningPlanningService:
    """Service central orchestrant l'analyse des données, disponibilités, priorités et application transactionnelle."""

    def __init__(
        self,
        *,
        planning_repo: SqlPlanningRepository,
        profile_repo: ProfileRepository,
        schedule_repo: ScheduleRepository,
        task_repo: TaskRepository,
        session_repo: SessionRepository,
        schedule_service: ScheduleService,
        task_service: TaskService,
        project_repo: SqlProjectRepository | None = None,
        goal_repo: SqlPersonalGoalRepository | None = None,
        learning_repo: SqlLearningRepository | None = None,
        skill_repo: SqlSkillRepository | None = None,
        course_repo: SqlCourseRepository | None = None,
        course_service: CourseService | None = None,
        ai_memory_repo: SqlAiMemoryRepository | None = None,
    ) -> None:
        self._planning_repo = planning_repo
        self._schedule_repo = schedule_repo
        self._schedule_service = schedule_service
        self._task_service = task_service
        self._course_service = course_service
        self._collector = PlanningContextCollector(
            profile_repo=profile_repo,
            schedule_repo=schedule_repo,
            task_repo=task_repo,
            session_repo=session_repo,
            project_repo=project_repo,
            goal_repo=goal_repo,
            learning_repo=learning_repo,
            skill_repo=skill_repo,
            course_repo=course_repo,
            ai_memory_repo=ai_memory_repo,
            planning_repo=planning_repo,
        )
        self._availability_engine = AvailabilityEngine()
        self._prioritizer = LearningPrioritizer()
        self._content_resolver = SessionContentResolver(course_service=course_service)
        self._allocator = WeeklyPlanAllocator(self._content_resolver)

    # ------------------------------------------------------------------
    # Règles de disponibilité
    # ------------------------------------------------------------------
    def list_availability_rules(self, user_id: UUID) -> list[AvailabilityRuleResponse]:
        return [
            _to_rule_response(r)
            for r in self._planning_repo.list_availability_rules(user_id, active_only=False)
        ]

    def create_availability_rule(
        self,
        user_id: UUID,
        payload: AvailabilityRuleCreate,
    ) -> AvailabilityRuleResponse:
        now = datetime.now(timezone.utc)
        rec = UserAvailabilityRuleRecord(
            id=uuid4(),
            user_id=user_id,
            label=payload.label.strip(),
            rule_type=payload.rule_type,
            day_of_week=payload.day_of_week,
            start_time=payload.start_time,
            end_time=payload.end_time,
            starts_at=_ensure_utc(payload.starts_at),
            ends_at=_ensure_utc(payload.ends_at),
            timezone=payload.timezone.strip(),
            recurrence=payload.recurrence,
            active=payload.active,
            notes=payload.notes.strip() if payload.notes else None,
            created_at=now,
            updated_at=now,
        )
        saved = self._planning_repo.save_availability_rule(rec)
        return _to_rule_response(saved)

    def update_availability_rule(
        self,
        user_id: UUID,
        rule_id: UUID,
        payload: AvailabilityRuleUpdate,
    ) -> AvailabilityRuleResponse:
        existing = self._planning_repo.get_availability_rule(user_id, rule_id)
        if existing is None:
            raise AppError(404, "AVAILABILITY_RULE_NOT_FOUND", "Règle de disponibilité introuvable.")
        patch_data = payload.model_dump(exclude_unset=True)
        patch_data["updated_at"] = datetime.now(timezone.utc)
        if "starts_at" in patch_data:
            patch_data["starts_at"] = _ensure_utc(patch_data["starts_at"])
        if "ends_at" in patch_data:
            patch_data["ends_at"] = _ensure_utc(patch_data["ends_at"])
        updated = existing.model_copy(update=patch_data)
        return _to_rule_response(self._planning_repo.save_availability_rule(updated))

    def delete_availability_rule(self, user_id: UUID, rule_id: UUID) -> None:
        if not self._planning_repo.delete_availability_rule(user_id, rule_id):
            raise AppError(404, "AVAILABILITY_RULE_NOT_FOUND", "Règle de disponibilité introuvable.")

    # ------------------------------------------------------------------
    # Calcul des disponibilités
    # ------------------------------------------------------------------
    def compute_availability(
        self,
        user_id: UUID,
        *,
        horizon_days: int = 7,
        range_start: datetime | None = None,
        timezone_name: str | None = None,
        min_session_minutes: int = 30,
        buffer_minutes: int = 10,
        include_potential: bool = True,
        replace_future_planned: bool = True,
    ) -> AvailabilityComputationResponse:
        snapshot = self._collector.collect(user_id, timezone_override=timezone_name)
        anchor = _ensure_utc(range_start) or snapshot.collected_at
        excluded = (
            set(snapshot.applied_event_ids)
            if replace_future_planned and snapshot.applied_event_ids
            else set()
        )
        return self._availability_engine.compute(
            snapshot,
            range_start=anchor,
            horizon_days=horizon_days,
            timezone_name=timezone_name,
            min_session_minutes=min_session_minutes,
            buffer_minutes=buffer_minutes,
            include_potential=include_potential,
            excluded_event_ids=excluded,
        )

    # ------------------------------------------------------------------
    # Génération & ajustement de programme
    # ------------------------------------------------------------------
    def generate_plan(
        self,
        user_id: UUID,
        payload: LearningPlanGenerateRequest,
        *,
        idempotency_key: str | None = None,
        parent_version_id: UUID | None = None,
    ) -> LearningPlanVersionResponse:
        eff_key = (idempotency_key or payload.idempotency_key or "").strip() or None
        if eff_key:
            existing = self._planning_repo.get_plan_version_by_idempotency(user_id, eff_key)
            if existing is not None:
                return self._record_to_response(existing)

        now = datetime.now(timezone.utc)
        snapshot = self._collector.collect(
            user_id,
            now=now,
            timezone_override=payload.timezone,
        )
        anchor = _ensure_utc(payload.range_start) or now

        # Exclure les anciens événements auto-planifiés futurs pour le recalcul sans conflit artificiel
        excluded_ids = {
            str(ev.id)
            for ev in snapshot.planned_learning_events
            if str(ev.id) in set(snapshot.applied_event_ids)
            and (_ensure_utc(ev.starts_at) or now) >= anchor
        }

        availability = self._availability_engine.compute(
            snapshot,
            range_start=anchor,
            horizon_days=payload.horizon_days,
            timezone_name=payload.timezone or snapshot.timezone,
            min_session_minutes=payload.min_session_minutes,
            buffer_minutes=payload.buffer_minutes,
            include_potential=payload.include_potential_slots,
            excluded_event_ids=excluded_ids,
        )

        priorities = self._prioritizer.prioritize(
            snapshot,
            focus_subject=payload.focus_subject,
            exam_title=payload.exam_title,
            exam_at=_ensure_utc(payload.exam_at),
        )

        created_course_ids: list[str] = []
        if payload.create_missing_courses and self._course_service is not None and priorities:
            existing_subjects = {c.subject.strip().lower() for c in snapshot.active_courses}
            top_goal = next(
                (
                    p
                    for p in priorities
                    if p.source_type in ("personal_goal", "skill", "exam_revision")
                    and p.subject.strip().lower() not in existing_subjects
                ),
                None,
            )
            if top_goal is not None:
                course = self._course_service.create_course(
                    user_id,
                    CourseCreate(
                        subject=top_goal.subject[:120],
                        language=CourseLanguage.fr,
                        total_levels=3,
                        goal=f"Programme structuré pour {top_goal.subject}",
                    ),
                )
                created_course_ids.append(str(course.id))
                snapshot = self._collector.collect(
                    user_id,
                    now=now,
                    timezone_override=payload.timezone,
                )
                priorities = self._prioritizer.prioritize(
                    snapshot,
                    focus_subject=payload.focus_subject,
                    exam_title=payload.exam_title,
                    exam_at=_ensure_utc(payload.exam_at),
                )

        (
            planned_sessions,
            arbitrage_items,
            load_summary,
            missing_info,
            warnings,
        ) = self._allocator.allocate(
            snapshot=snapshot,
            availability=availability,
            priorities=priorities,
            weekly_hours_override=payload.weekly_hours_override,
            daily_max_minutes=payload.daily_max_minutes,
            preferred_session_minutes=payload.preferred_session_minutes,
            min_session_minutes=payload.min_session_minutes,
            max_sessions=payload.max_sessions,
        )

        rationale = self._build_overall_rationale(
            priorities=priorities,
            planned_sessions=planned_sessions,
            arbitrage_items=arbitrage_items,
            availability=availability,
            note=payload.note,
        )

        version_num = self._planning_repo.next_version_number(user_id)
        plan_payload = {
            "request": payload.model_dump(mode="json"),
            "priorities": [p.model_dump(mode="json") for p in priorities],
            "planned_sessions": [s.model_dump(mode="json") for s in planned_sessions],
            "arbitrage_items": [a.model_dump(mode="json") for a in arbitrage_items],
            "load_summary": load_summary.model_dump(mode="json"),
            "availability_summary": availability.model_dump(mode="json"),
            "missing_info": [m.model_dump(mode="json") for m in missing_info],
            "warnings": list(warnings),
        }
        record = LearningPlanVersionRecord(
            id=uuid4(),
            user_id=user_id,
            version_number=version_num,
            status=PlanVersionStatus.proposed,
            horizon_days=payload.horizon_days,
            timezone=availability.timezone,
            idempotency_key=eff_key,
            rationale=rationale,
            plan_payload=plan_payload,
            applied_event_ids=[],
            applied_task_ids=[],
            applied_course_ids=created_course_ids,
            replaced_event_snapshots=[],
            parent_version_id=parent_version_id,
            applied_at=None,
            created_at=now,
            updated_at=now,
        )
        saved = self._planning_repo.save_plan_version(record)
        return self._record_to_response(saved)

    def adjust_plan(
        self,
        user_id: UUID,
        payload: LearningPlanAdjustRequest,
        *,
        idempotency_key: str | None = None,
    ) -> LearningPlanVersionResponse:
        latest_versions = self._planning_repo.list_plan_versions(user_id, limit=5)
        parent = latest_versions[0] if latest_versions else None
        text_l = payload.instruction.lower()

        horizon_days = payload.horizon_days or (parent.horizon_days if parent else 7)
        daily_max = 120 if any(k in text_l for k in ("allège", "allege", "moins", "léger", "leger", "fatigue")) else None
        weekly_override: float | None = None
        hours_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:h|heures?)", text_l)
        if hours_match:
            weekly_override = max(1.0, min(60.0, float(hours_match.group(1).replace(",", "."))))
        elif daily_max is not None:
            weekly_override = 6.0

        pref_mins: int | None = None
        mins_match = re.search(r"séances?\s+de\s+(\d+)\s*min", text_l)
        if mins_match:
            pref_mins = max(25, min(180, int(mins_match.group(1))))

        range_start = _ensure_utc(payload.range_start)
        if range_start is None and any(k in text_l for k in ("semaine prochaine", "lundi prochain", "reporte")):
            range_start = datetime.now(timezone.utc) + timedelta(days=7)

        focus_subject: str | None = None
        focus_match = re.search(r"(?:plus de|priorité à|priorite a|focus sur)\s+([a-zA-ZÀ-ÿ0-9_+-]{2,40})", payload.instruction, re.I)
        if focus_match:
            focus_subject = focus_match.group(1).strip()

        gen_req = LearningPlanGenerateRequest(
            horizon_days=horizon_days,
            range_start=range_start,
            timezone=payload.timezone or (parent.timezone if parent else None),
            focus_subject=focus_subject,
            weekly_hours_override=weekly_override,
            daily_max_minutes=daily_max,
            preferred_session_minutes=pref_mins,
            idempotency_key=idempotency_key or payload.idempotency_key,
            note=f"Ajustement demandé : {payload.instruction}",
        )
        return self.generate_plan(
            user_id,
            gen_req,
            idempotency_key=idempotency_key or payload.idempotency_key,
            parent_version_id=parent.id if parent else None,
        )

    # ------------------------------------------------------------------
    # Application, rejet, historique & restauration
    # ------------------------------------------------------------------
    def list_versions(self, user_id: UUID, limit: int = 20) -> list[LearningPlanVersionResponse]:
        return [
            self._record_to_response(v)
            for v in self._planning_repo.list_plan_versions(user_id, limit=limit)
        ]

    def get_version(self, user_id: UUID, version_id: UUID) -> LearningPlanVersionResponse:
        rec = self._planning_repo.get_plan_version(user_id, version_id)
        if rec is None:
            raise AppError(404, "PLAN_VERSION_NOT_FOUND", "Version de programme introuvable.")
        return self._record_to_response(rec)

    def apply_plan(
        self,
        user_id: UUID,
        version_id: UUID,
        payload: LearningPlanApplyRequest,
    ) -> LearningPlanVersionResponse:
        rec = self._planning_repo.get_plan_version(user_id, version_id)
        if rec is None:
            raise AppError(404, "PLAN_VERSION_NOT_FOUND", "Version de programme introuvable.")
        if rec.status == PlanVersionStatus.applied:
            return self._record_to_response(rec)

        now = datetime.now(timezone.utc)
        sessions = [
            PlannedSessionProposal(**item)
            for item in (rec.plan_payload.get("planned_sessions") or [])
        ]
        if payload.selected_slot_ids is not None:
            wanted = set(payload.selected_slot_ids)
            sessions = [s for s in sessions if s.slot_id in wanted]

        if not sessions:
            raise AppError(400, "PLAN_EMPTY", "Aucune séance sélectionnée à appliquer dans le calendrier.")

        # Identifier les futurs événements auto-planifiés pouvant être remplacés
        prev_applied = self._planning_repo.get_latest_applied_version(user_id)
        prev_event_ids = set(prev_applied.applied_event_ids) if prev_applied else set()
        live_events = self._schedule_repo.list_by_user(user_id)

        to_replace_ids: set[UUID] = set()
        replaced_snapshots: list[dict[str, Any]] = []
        if payload.replace_future_planned:
            for ev in live_events:
                ev_s = _ensure_utc(ev.starts_at) or now
                is_prev_plan_event = str(ev.id) in prev_event_ids
                is_future_ai_study_event = (
                    ev.source == ScheduleEventSource.ai_proposal
                    and ev.type in (ScheduleEventType.learning, ScheduleEventType.project)
                )
                if (is_prev_plan_event or is_future_ai_study_event) and ev_s >= now - timedelta(minutes=5):
                    to_replace_ids.add(ev.id)
                    replaced_snapshots.append(ev.model_dump(mode="json"))

        # Vérification des conflits en temps réel sur l'agenda restant (événements fixes + manuels) et entre séances du plan
        remaining_events = [ev for ev in live_events if ev.id not in to_replace_ids]
        checked_new: list[tuple[datetime, datetime, str]] = []
        for sess in sessions:
            s_utc = _ensure_utc(sess.starts_at) or now
            e_utc = _ensure_utc(sess.ends_at) or now
            for prev_s, prev_e, prev_title in checked_new:
                if _intervals_overlap(s_utc, e_utc, prev_s, prev_e):
                    raise AppError(
                        409,
                        "PLANNING_CONFLICT_DETECTED",
                        f"Chevauchement interne détecté entre « {prev_title} » et « {sess.title} ». Recalculez le programme.",
                    )
            checked_new.append((s_utc, e_utc, sess.title))
            for ev in remaining_events:
                ev_s = _ensure_utc(ev.starts_at) or now
                ev_e = _ensure_utc(ev.ends_at) or now
                if _intervals_overlap(s_utc, e_utc, ev_s, ev_e):
                    raise AppError(
                        409,
                        "PLANNING_CONFLICT_DETECTED",
                        f"Conflit détecté avec « {ev.title} » pour la séance « {sess.title} ». Recalculez le programme.",
                    )

        # Remplacer puis créer atomiquement avec rollback LIFO en cas d'erreur
        deleted_events: list[ScheduleEventRecord] = []
        created_event_ids: list[UUID] = []
        created_task_ids: list[UUID] = []
        try:
            for ev_id in to_replace_ids:
                ev_rec = self._schedule_repo.get(user_id, ev_id)
                if ev_rec is not None:
                    self._schedule_service.delete_event(user_id, ev_id)
                    deleted_events.append(ev_rec)

            # Optionnel : créer 1 tâche synthétique par examen sans tâche associée
            priorities = [
                LearningPriorityItem(**p)
                for p in (rec.plan_payload.get("priorities") or [])
            ]
            exam_priorities = [p for p in priorities if p.source_type == "exam_revision"][:2]
            existing_task_titles = {t.title.lower() for t in self._collector._task_repo.list_by_user(user_id)}
            for ep in exam_priorities:
                t_title = f"Réviser : {ep.subject}"[:140]
                if t_title.lower() not in existing_task_titles:
                    created_t = self._task_service.create_task(
                        user_id,
                        TaskCreate(
                            title=t_title,
                            description=ep.reasons[0] if ep.reasons else "Tâche générée par le moteur de planification.",
                            priority=TaskPriority.high,
                            due_at=ep.deadline_at,
                        ),
                    )
                    created_task_ids.append(created_t.id)
                    existing_task_titles.add(t_title.lower())

            for sess in sessions:
                ev_type = (
                    ScheduleEventType.project
                    if sess.session_type == "project"
                    else ScheduleEventType.learning
                )
                linked_goal_id = None
                if sess.priority_source_type == "personal_goal" and sess.priority_source_id:
                    try:
                        linked_goal_id = UUID(str(sess.priority_source_id))
                    except ValueError:
                        linked_goal_id = None
                created_ev = self._schedule_service.create_event(
                    user_id,
                    ScheduleEventCreate(
                        title=sess.title[:140],
                        type=ev_type,
                        starts_at=sess.starts_at,
                        ends_at=sess.ends_at,
                        notes=sess.rationale[:950],
                        source=ScheduleEventSource.ai_proposal,
                        goal_id=linked_goal_id,
                        course_id=sess.course_id,
                        project_id=sess.project_id,
                        task_id=sess.task_id,
                    ),
                )
                created_event_ids.append(created_ev.id)
        except Exception:
            for eid in reversed(created_event_ids):
                try:
                    self._schedule_service.delete_event(user_id, eid)
                except Exception:
                    pass
            for tid in reversed(created_task_ids):
                try:
                    self._task_service.delete_task(user_id, tid)
                except Exception:
                    pass
            for old_ev in deleted_events:
                try:
                    self._schedule_repo.save(old_ev)
                except Exception:
                    pass
            raise

        if prev_applied is not None and prev_applied.id != rec.id:
            self._planning_repo.save_plan_version(
                prev_applied.model_copy(
                    update={"status": PlanVersionStatus.superseded, "updated_at": now}
                )
            )

        updated = rec.model_copy(
            update={
                "status": PlanVersionStatus.applied,
                "applied_event_ids": [str(eid) for eid in created_event_ids],
                "applied_task_ids": [str(tid) for tid in created_task_ids],
                "replaced_event_snapshots": replaced_snapshots,
                "applied_at": now,
                "updated_at": now,
            }
        )
        saved = self._planning_repo.save_plan_version(updated)
        return self._record_to_response(saved)

    def reject_plan(self, user_id: UUID, version_id: UUID) -> LearningPlanVersionResponse:
        rec = self._planning_repo.get_plan_version(user_id, version_id)
        if rec is None:
            raise AppError(404, "PLAN_VERSION_NOT_FOUND", "Version de programme introuvable.")
        updated = rec.model_copy(
            update={
                "status": PlanVersionStatus.rejected,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        return self._record_to_response(self._planning_repo.save_plan_version(updated))

    def restore_plan_version(self, user_id: UUID, version_id: UUID) -> LearningPlanVersionResponse:
        target = self._planning_repo.get_plan_version(user_id, version_id)
        if target is None:
            raise AppError(404, "PLAN_VERSION_NOT_FOUND", "Version de programme introuvable.")

        now = datetime.now(timezone.utc)
        current_applied = self._planning_repo.get_latest_applied_version(user_id)
        if current_applied is not None and current_applied.id != target.id:
            for eid_str in current_applied.applied_event_ids:
                try:
                    eid = UUID(eid_str)
                except ValueError:
                    continue
                ev = self._schedule_repo.get(user_id, eid)
                if ev is not None and (_ensure_utc(ev.starts_at) or now) >= now - timedelta(minutes=5):
                    self._schedule_service.delete_event(user_id, eid)
            self._planning_repo.save_plan_version(
                current_applied.model_copy(
                    update={"status": PlanVersionStatus.superseded, "updated_at": now}
                )
            )

        # Ré-appliquer les créneaux futurs de la version cible sans chevauchement fixe
        sessions = [
            PlannedSessionProposal(**item)
            for item in (target.plan_payload.get("planned_sessions") or [])
            if (_ensure_utc(item.get("starts_at") if isinstance(item.get("starts_at"), datetime) else datetime.fromisoformat(str(item["starts_at"]).replace("Z", "+00:00"))) or now) >= now
        ]
        live_events = self._schedule_repo.list_by_user(user_id)
        restored_event_ids: list[str] = []
        for sess in sessions:
            s_u = _ensure_utc(sess.starts_at) or now
            e_u = _ensure_utc(sess.ends_at) or now
            conflict = any(
                _intervals_overlap(s_u, e_u, _ensure_utc(ev.starts_at) or now, _ensure_utc(ev.ends_at) or now)
                for ev in live_events
            )
            if not conflict:
                ev_type = (
                    ScheduleEventType.project
                    if sess.session_type == "project"
                    else ScheduleEventType.learning
                )
                linked_goal_id = None
                if sess.priority_source_type == "personal_goal" and sess.priority_source_id:
                    try:
                        linked_goal_id = UUID(str(sess.priority_source_id))
                    except ValueError:
                        linked_goal_id = None
                created_ev = self._schedule_service.create_event(
                    user_id,
                    ScheduleEventCreate(
                        title=sess.title[:140],
                        type=ev_type,
                        starts_at=sess.starts_at,
                        ends_at=sess.ends_at,
                        notes=sess.rationale[:950],
                        source=ScheduleEventSource.ai_proposal,
                        goal_id=linked_goal_id,
                        course_id=sess.course_id,
                        project_id=sess.project_id,
                        task_id=sess.task_id,
                    ),
                )
                restored_event_ids.append(str(created_ev.id))

        updated = target.model_copy(
            update={
                "status": PlanVersionStatus.restored,
                "applied_event_ids": restored_event_ids or list(target.applied_event_ids),
                "applied_at": now,
                "updated_at": now,
            }
        )
        return self._record_to_response(self._planning_repo.save_plan_version(updated))

    # ------------------------------------------------------------------
    # Détection d'obsolescence & validité du planning
    # ------------------------------------------------------------------
    def check_schedule_validity(
        self,
        user_id: UUID,
        *,
        timezone_name: str | None = None,
    ) -> ScheduleValidityResponse:
        now = datetime.now(timezone.utc)
        snapshot = self._collector.collect(user_id, now=now, timezone_override=timezone_name)
        from app.planning.availability import resolve_zoneinfo

        tz, _ = resolve_zoneinfo(snapshot.timezone)

        completed_ranges = [
            (
                _ensure_utc(s.started_at) or now,
                _ensure_utc(s.ended_at) or ((_ensure_utc(s.started_at) or now) + timedelta(minutes=60)),
            )
            for s in snapshot.sessions
            if s.status == SessionStatus.completed
        ]

        expired_events = 0
        missed_sessions = 0
        daily_study_minutes: dict[str, int] = {}
        conflicting_ids: list[str] = []

        for ev in snapshot.planned_learning_events:
            ev_s = _ensure_utc(ev.starts_at) or now
            ev_e = _ensure_utc(ev.ends_at) or now
            if ev_e < now:
                expired_events += 1
                backed = any(abs((cs - ev_s).total_seconds()) <= 5400 for cs, _ in completed_ranges)
                if not backed:
                    missed_sessions += 1
            else:
                d_key = ev_s.astimezone(tz).date().isoformat()
                mins = max(0, int((ev_e - ev_s).total_seconds() // 60))
                daily_study_minutes[d_key] = daily_study_minutes.get(d_key, 0) + mins

                # Conflit avec un événement fixe ajouté récemment
                for fixed in snapshot.fixed_events:
                    if fixed.id == ev.id:
                        continue
                    f_s = _ensure_utc(fixed.starts_at) or now
                    f_e = _ensure_utc(fixed.ends_at) or now
                    if _intervals_overlap(ev_s, ev_e, f_s, f_e):
                        conflicting_ids.append(str(ev.id))
                        break

        overloaded_days = [day for day, mins in daily_study_minutes.items() if mins > 240]
        stale_reasons: list[str] = []
        if len(snapshot.overdue_tasks) > 0:
            stale_reasons.append(f"{len(snapshot.overdue_tasks)} tâche(s) en retard.")
        if missed_sessions > 0:
            stale_reasons.append(f"{missed_sessions} séance(s) planifiée(s) passée(s) non complétée(s).")
        if conflicting_ids:
            stale_reasons.append(f"{len(conflicting_ids)} conflit(s) avec de nouveaux événements fixes.")
        if overloaded_days:
            stale_reasons.append(f"Surcharge détectée sur {len(overloaded_days)} jour(s).")

        is_valid = not stale_reasons
        recommendation = (
            "Votre planning est cohérent avec vos engagements."
            if is_valid
            else "Recalcul recommandé : " + " ".join(stale_reasons)
        )
        return ScheduleValidityResponse(
            is_valid=is_valid,
            expired_event_count=expired_events,
            expired_task_count=len(snapshot.overdue_tasks),
            overloaded_days=overloaded_days,
            missed_session_count=missed_sessions,
            conflicting_event_ids=conflicting_ids,
            stale_reasons=stale_reasons,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_overall_rationale(
        self,
        *,
        priorities: list[LearningPriorityItem],
        planned_sessions: list[PlannedSessionProposal],
        arbitrage_items: list[PlanArbitrageItem],
        availability: AvailabilityComputationResponse,
        note: str | None,
    ) -> str:
        parts: list[str] = []
        if note:
            parts.append(note.strip())
        if planned_sessions:
            total_mins = sum(s.duration_minutes for s in planned_sessions)
            top_names = ", ".join(dict.fromkeys(p.subject for p in priorities[:3]))
            parts.append(
                f"Programme généré : {len(planned_sessions)} séance(s) totalisant {total_mins} min "
                f"sur les priorités ({top_names or 'apprentissage'}) dans {availability.timezone}."
            )
        else:
            parts.append(
                f"Aucune séance planifiable trouvée sur cet horizon ({availability.summary})."
            )
        if arbitrage_items:
            parts.append(
                f"Arbitrage anti-surcharge : {len(arbitrage_items)} élément(s) partiellement reporté(s)."
            )
        return " ".join(parts)

    def _record_to_response(self, rec: LearningPlanVersionRecord) -> LearningPlanVersionResponse:
        payload = rec.plan_payload or {}
        avail_raw = payload.get("availability_summary")
        load_raw = payload.get("load_summary")
        return LearningPlanVersionResponse(
            id=rec.id,
            user_id=rec.user_id,
            version_number=rec.version_number,
            status=rec.status,
            horizon_days=rec.horizon_days,
            timezone=rec.timezone,
            rationale=rec.rationale,
            priorities=[LearningPriorityItem(**p) for p in (payload.get("priorities") or [])],
            planned_sessions=[
                PlannedSessionProposal(**s) for s in (payload.get("planned_sessions") or [])
            ],
            arbitrage_items=[
                PlanArbitrageItem(**a) for a in (payload.get("arbitrage_items") or [])
            ],
            load_summary=PlanLoadSummary(**load_raw) if load_raw else PlanLoadSummary(),
            availability_summary=AvailabilityComputationResponse(**avail_raw)
            if avail_raw
            else None,
            missing_info=[PlanMissingInfoItem(**m) for m in (payload.get("missing_info") or [])],
            warnings=list(payload.get("warnings") or []),
            applied_event_ids=list(rec.applied_event_ids or []),
            applied_task_ids=list(rec.applied_task_ids or []),
            applied_course_ids=list(rec.applied_course_ids or []),
            parent_version_id=rec.parent_version_id,
            applied_at=rec.applied_at,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
            plan_payload=dict(payload),
        )
