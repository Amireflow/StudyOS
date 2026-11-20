from datetime import datetime, timezone
import re
from typing import Any
from uuid import UUID
from pydantic import ValidationError
from app.ai.tool_registry import ToolRegistry
from app.core.errors import AppError
from app.repositories.learning_sql import (
    SqlLearningRepository,
    SqlPersonalGoalRepository,
    SqlProjectRepository,
    SqlSkillRepository,
)
from app.repositories.memory import ScheduleRepository, TaskRepository
from app.repositories.planning_sql import SqlPlanningRepository
from app.schemas.ai import (
    AddEvidenceProposalPayload,
    ArchiveScheduleEventProposalPayload,
    BatchActionsProposalPayload,
    CreateCourseProposalPayload,
    CreateLearningPathProposalPayload,
    CreatePersonalGoalProposalPayload,
    CreateProjectProposalPayload,
    CreateScheduleProposalPayload,
    CreateSkillProposalPayload,
    CreateStudySessionProposalPayload,
    CreateTaskProposalPayload,
    GenerateLearningPlanProposalPayload,
    ManageAvailabilityRuleProposalPayload,
    ParkTaskProposalPayload,
    PauseProjectProposalPayload,
    PlanStrategicActivityProposalPayload,
    ProposeSkillAssessmentPayload,
    RawProposalCandidate,
    RecommendSkillProgressionPayload,
    UpdateLearningPathProposalPayload,
    UpdatePersonalGoalProposalPayload,
    UpdatePreferencesProposalPayload,
    UpdateProjectProposalPayload,
    UpdateScheduleEventProposalPayload,
    UpdateTaskProposalPayload,
)
from app.schemas.common import (
    AiActionType,
    ProjectStatus,
    ScheduleEventSource,
    ScheduleEventType,
    SkillAssessmentStatus,
)
from app.services.assessment_evaluator import (
    pass_threshold_for_level,
    validate_evidence_quality,
)
from app.services.schedule_service import do_events_overlap


_FR_WEEKDAYS = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")


def _normalize_iso_utc_str(val: Any, default_time: str = "18:00:00") -> Any:
    if not isinstance(val, str):
        return val
    s = val.strip()
    if not s:
        return val
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return f"{s}T{default_time}Z"
    if re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}$", s):
        return s.replace(" ", "T") + ":00Z"
    if re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?$", s):
        return s.replace(" ", "T") + "Z"
    return s


def _normalize_priority_str(val: Any) -> Any:
    if not isinstance(val, str):
        return val
    low = val.strip().lower()
    if low in ("low", "basse", "faible", "minor", "mineure"):
        return "low"
    if low in ("normal", "normale", "medium", "moyenne", "standard", "moderate"):
        return "normal"
    if low in ("high", "haute", "élevée", "elevee", "important", "importante"):
        return "high"
    if low in ("critical", "critique", "urgent", "urgente", "highest"):
        return "critical"
    return val


def _normalize_schedule_type_str(val: Any) -> str:
    if not isinstance(val, str):
        return "learning"
    low = val.strip().lower()
    if low in ("course", "learning", "project", "personal", "other"):
        return low
    if any(w in low for w in ("proj", "tp_projet", "livrable")):
        return "project"
    if any(w in low for w in ("perso", "pause", "repos", "sport")):
        return "personal"
    return "learning"


def _normalize_llm_raw_payload(action_type: AiActionType, payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)

    for dt_key in ("starts_at", "ends_at", "due_at", "started_at", "exam_at"):
        if dt_key in out and out[dt_key] is not None:
            out[dt_key] = _normalize_iso_utc_str(out[dt_key])

    if "priority" in out and out["priority"] is not None:
        out["priority"] = _normalize_priority_str(out["priority"])

    if action_type in (AiActionType.create_schedule_event, AiActionType.update_schedule_event):
        date_str = str(out.get("date") or out.get("local_date") or "").strip()
        start_t = str(out.get("start_time") or out.get("local_start_time") or out.get("start") or "").strip()
        end_t = str(out.get("end_time") or out.get("local_end_time") or out.get("end") or "").strip()
        if "starts_at" not in out and date_str and re.match(r"^\d{4}-\d{2}-\d{2}$", date_str) and re.match(r"^\d{2}:\d{2}", start_t):
            out["starts_at"] = f"{date_str}T{start_t[:5]}:00Z"
        if "ends_at" not in out and date_str and re.match(r"^\d{4}-\d{2}-\d{2}$", date_str) and re.match(r"^\d{2}:\d{2}", end_t):
            out["ends_at"] = f"{date_str}T{end_t[:5]}:00Z"
        if action_type == AiActionType.create_schedule_event:
            if "title" not in out and isinstance(out.get("subject") or out.get("name"), str):
                out["title"] = str(out.get("subject") or out.get("name")).strip()
            out["type"] = _normalize_schedule_type_str(out.get("type", "learning"))

    if action_type == AiActionType.create_task:
        if "title" not in out and isinstance(out.get("name") or out.get("task"), str):
            out["title"] = str(out.get("name") or out.get("task")).strip()

    if action_type == AiActionType.plan_strategic_activity:
        if "activity_title" not in out:
            for alt in ("title", "name", "subject", "topic"):
                if isinstance(out.get(alt), str) and out[alt].strip():
                    out["activity_title"] = out[alt].strip()
                    break
        if not isinstance(out.get("goal"), str) or len(str(out.get("goal")).strip()) < 2:
            act = str(out.get("activity_title") or "cet objectif").strip()
            out["goal"] = f"Progresser régulièrement sur {act} sans surcharge."
        raw_dec = str(out.get("decision") or "ACCEPTABLE").strip().upper()
        if "NON" in raw_dec or "NOT_RECOMMENDED" in raw_dec or "PARKING" in raw_dec or raw_dec.startswith("C"):
            out["decision"] = "NOT_RECOMMENDED"
        elif "CONDITION" in raw_dec or raw_dec.startswith("B"):
            out["decision"] = "ACCEPTABLE_WITH_CONDITIONS"
        else:
            out["decision"] = "ACCEPTABLE"
        raw_cat = str(out.get("category") or "learning").strip().lower()
        if raw_cat not in ("learning", "project", "exam_prep", "personal", "university_deepening"):
            out["category"] = "learning"

        raw_slots = out.get("proposed_slots")
        if isinstance(raw_slots, list):
            norm_slots: list[dict[str, Any]] = []
            for s in raw_slots:
                if not isinstance(s, dict):
                    continue
                sc = dict(s)
                loc_d = str(sc.get("local_date") or sc.get("date") or "").strip()
                loc_st = str(sc.get("local_start_time") or sc.get("start_time") or sc.get("start") or "").strip()
                loc_et = str(sc.get("local_end_time") or sc.get("end_time") or sc.get("end") or "").strip()
                if "starts_at" in sc:
                    sc["starts_at"] = _normalize_iso_utc_str(sc["starts_at"])
                elif loc_d and re.match(r"^\d{2}:\d{2}", loc_st):
                    sc["starts_at"] = f"{loc_d}T{loc_st[:5]}:00Z"
                if "ends_at" in sc:
                    sc["ends_at"] = _normalize_iso_utc_str(sc["ends_at"])
                elif loc_d and re.match(r"^\d{2}:\d{2}", loc_et):
                    sc["ends_at"] = f"{loc_d}T{loc_et[:5]}:00Z"
                try:
                    dt_s = datetime.fromisoformat(str(sc["starts_at"]).replace("Z", "+00:00"))
                    dt_e = datetime.fromisoformat(str(sc["ends_at"]).replace("Z", "+00:00"))
                    if not loc_d:
                        loc_d = dt_s.date().isoformat()
                    sc["local_date"] = loc_d[:10]
                    sc["local_start_time"] = loc_st[:5] if len(loc_st) >= 5 else dt_s.strftime("%H:%M")
                    sc["local_end_time"] = loc_et[:5] if len(loc_et) >= 5 else dt_e.strftime("%H:%M")
                    if not sc.get("day_label"):
                        sc["day_label"] = _FR_WEEKDAYS[dt_s.weekday()]
                    if not sc.get("duration_minutes"):
                        dur = max(15, min(240, int((dt_e - dt_s).total_seconds() // 60)))
                        sc["duration_minutes"] = dur
                    norm_slots.append(sc)
                except Exception:
                    continue
            out["proposed_slots"] = norm_slots

    if action_type == AiActionType.batch_actions:
        raw_steps = out.get("steps")
        if not isinstance(raw_steps, list) and isinstance(out.get("actions"), list):
            raw_steps = out.get("actions")
        if isinstance(raw_steps, list):
            norm_steps: list[dict[str, Any]] = []
            for st in raw_steps:
                if not isinstance(st, dict):
                    continue
                st_type = str(
                    st.get("action_type") or st.get("action") or st.get("tool") or st.get("type") or ""
                ).strip()
                if not st_type:
                    continue
                if isinstance(st.get("payload"), dict):
                    st_payload = dict(st["payload"])
                elif isinstance(st.get("parameters"), dict):
                    st_payload = dict(st["parameters"])
                elif isinstance(st.get("arguments"), dict):
                    st_payload = dict(st["arguments"])
                else:
                    st_payload = {
                        k: v
                        for k, v in st.items()
                        if k not in ("action_type", "action", "tool", "type", "link_to_step", "payload", "parameters", "arguments")
                    }
                norm_steps.append(
                    {
                        "action_type": st_type,
                        "payload": st_payload,
                        "link_to_step": st.get("link_to_step") if isinstance(st.get("link_to_step"), dict) else None,
                    }
                )
            out["steps"] = norm_steps

    return out


class ValidatedProposal:
    def __init__(
        self,
        *,
        action_type: AiActionType,
        title: str,
        explanation: str,
        payload: dict[str, Any],
    ) -> None:
        self.action_type = action_type
        self.title = title
        self.explanation = explanation
        self.payload = payload


class ActionValidator:
    """Valide chaque proposition IA contre la liste blanche ToolRegistry et les schémas métier (AI-01, AI-03)."""

    def __init__(
        self,
        *,
        tool_registry: ToolRegistry,
        task_repo: TaskRepository,
        schedule_repo: ScheduleRepository,
        learning_repo: SqlLearningRepository,
        skill_repo: SqlSkillRepository,
        project_repo: SqlProjectRepository,
        goal_repo: SqlPersonalGoalRepository | None = None,
        planning_repo: SqlPlanningRepository | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._task_repo = task_repo
        self._schedule_repo = schedule_repo
        self._learning_repo = learning_repo
        self._skill_repo = skill_repo
        self._project_repo = project_repo
        self._goal_repo = goal_repo
        self._planning_repo = planning_repo

    def validate_candidate(
        self,
        user_id: UUID,
        candidate: RawProposalCandidate,
    ) -> ValidatedProposal:
        if not self._tool_registry.is_allowed_proposal_action(candidate.action_type):
            raise AppError(
                422,
                "UNSUPPORTED_AI_ACTION",
                f"L’action « {candidate.action_type} » n’appartient pas à la liste blanche ToolRegistry.",
            )

        title = candidate.title.strip()
        explanation = candidate.explanation.strip()
        if len(title) < 2 or len(title) > 180:
            raise AppError(422, "VALIDATION_ERROR", "Le titre de la proposition est invalide.")
        if len(explanation) < 2 or len(explanation) > 1000:
            raise AppError(422, "VALIDATION_ERROR", "L’explication de la proposition est invalide.")

        action_enum = AiActionType(candidate.action_type)
        validated_payload = self.validate_action_payload(user_id, action_enum, candidate.payload)

        return ValidatedProposal(
            action_type=action_enum,
            title=title,
            explanation=explanation,
            payload=validated_payload,
        )

    def validate_action_payload(
        self,
        user_id: UUID,
        action_type: AiActionType,
        raw_payload: dict[str, Any],
        *,
        _skip_fks: set[str] | None = None,
    ) -> dict[str, Any]:
        skip_fks = _skip_fks or set()
        raw_payload = _normalize_llm_raw_payload(
            action_type,
            {k: v for k, v in (raw_payload or {}).items() if v is not None},
        )
        try:
            if action_type == AiActionType.create_task:
                model = CreateTaskProposalPayload.model_validate(raw_payload)
                if (
                    "project_id" not in skip_fks
                    and model.project_id is not None
                    and self._project_repo.get(user_id, model.project_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Projet associé introuvable.")
                if (
                    "module_id" not in skip_fks
                    and model.module_id is not None
                    and self._learning_repo.get_module(user_id, model.module_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Module associé introuvable.")
                return {
                    "title": model.title,
                    "description": model.description,
                    "priority": model.priority.value,
                    "due_at": model.due_at.isoformat() if model.due_at else None,
                    "project_id": str(model.project_id) if model.project_id else None,
                    "module_id": str(model.module_id) if model.module_id else None,
                }

            if action_type == AiActionType.update_task:
                model = UpdateTaskProposalPayload.model_validate(raw_payload)
                if "task_id" not in skip_fks and self._task_repo.get(user_id, model.task_id) is None:
                    raise AppError(404, "NOT_FOUND", "Tâche cible introuvable.")
                if (
                    "project_id" not in skip_fks
                    and model.project_id is not None
                    and self._project_repo.get(user_id, model.project_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Projet associé introuvable.")
                if (
                    "module_id" not in skip_fks
                    and model.module_id is not None
                    and self._learning_repo.get_module(user_id, model.module_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Module associé introuvable.")
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.park_task:
                model = ParkTaskProposalPayload.model_validate(raw_payload)
                task = self._task_repo.get(user_id, model.task_id)
                if task is None:
                    raise AppError(404, "NOT_FOUND", "Tâche cible introuvable.")
                return {
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "reason": model.reason,
                }

            if action_type == AiActionType.create_project:
                model = CreateProjectProposalPayload.model_validate(raw_payload)
                if (
                    "goal_id" not in skip_fks
                    and model.goal_id is not None
                    and self._goal_repo is not None
                    and self._goal_repo.get(user_id, model.goal_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Objectif associé introuvable.")
                next_action = model.next_action.strip()
                if model.status == ProjectStatus.active and len(next_action) < 2:
                    next_action = "Définir la première étape concrète"
                out = model.model_copy(update={"next_action": next_action}).model_dump(mode="json")
                return out

            if action_type == AiActionType.update_project:
                model = UpdateProjectProposalPayload.model_validate(raw_payload)
                if "project_id" not in skip_fks and self._project_repo.get(user_id, model.project_id) is None:
                    raise AppError(404, "NOT_FOUND", "Projet cible introuvable.")
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.pause_project:
                model = PauseProjectProposalPayload.model_validate(raw_payload)
                project = self._project_repo.get(user_id, model.project_id)
                if project is None:
                    raise AppError(404, "NOT_FOUND", "Projet cible introuvable.")
                if project.status in (ProjectStatus.completed, ProjectStatus.archived):
                    raise AppError(
                        409,
                        "PROJECT_NOT_PAUSABLE",
                        "Impossible de mettre en pause un projet déjà terminé ou archivé.",
                    )
                return {
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "previous_status": project.status.value,
                    "reason": model.reason,
                }

            if action_type == AiActionType.create_schedule_event:
                model = CreateScheduleProposalPayload.model_validate(raw_payload)
                existing_events = self._schedule_repo.list_by_user(user_id)
                overlapping_events = [
                    ev
                    for ev in existing_events
                    if do_events_overlap(model.starts_at, model.ends_at, ev.starts_at, ev.ends_at)
                ]
                uni_conflicts = [
                    ev.title
                    for ev in overlapping_events
                    if ev.type == ScheduleEventType.course
                    or ev.source == ScheduleEventSource.timetable_import
                ]
                if uni_conflicts and model.type != ScheduleEventType.course:
                    raise AppError(
                        409,
                        "UNIVERSITY_COURSE_CONFLICT",
                        f"Impossible de planifier une séance personnelle sur le créneau du cours universitaire « {uni_conflicts[0]} ».",
                    )
                conflicts = [ev.title for ev in overlapping_events]
                return {
                    "title": model.title,
                    "type": model.type.value,
                    "starts_at": model.starts_at.isoformat(),
                    "ends_at": model.ends_at.isoformat(),
                    "notes": model.notes,
                    "has_conflict": len(conflicts) > 0,
                    "conflicting_titles": conflicts,
                }

            if action_type == AiActionType.update_schedule_event:
                model = UpdateScheduleEventProposalPayload.model_validate(raw_payload)
                ev = self._schedule_repo.get(user_id, model.event_id)
                if ev is None:
                    raise AppError(404, "NOT_FOUND", "Créneau cible introuvable.")
                if (
                    ev.type == ScheduleEventType.course
                    or ev.source == ScheduleEventSource.timetable_import
                ):
                    raise AppError(
                        409,
                        "UNIVERSITY_COURSE_CONFLICT",
                        f"Le cours universitaire « {ev.title} » est protégé et ne peut pas être déplacé automatiquement.",
                    )
                new_start = model.starts_at or ev.starts_at
                new_end = model.ends_at or ev.ends_at
                if new_end <= new_start:
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "L’heure de fin doit être strictement postérieure au début.",
                    )
                for other in self._schedule_repo.list_by_user(user_id):
                    if other.id == ev.id:
                        continue
                    if (
                        other.type == ScheduleEventType.course
                        or other.source == ScheduleEventSource.timetable_import
                    ) and do_events_overlap(new_start, new_end, other.starts_at, other.ends_at):
                        raise AppError(
                            409,
                            "UNIVERSITY_COURSE_CONFLICT",
                            f"Impossible de déplacer ce créneau sur le cours universitaire « {other.title} ».",
                        )
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.archive_schedule_event:
                model = ArchiveScheduleEventProposalPayload.model_validate(raw_payload)
                ev = self._schedule_repo.get(user_id, model.event_id)
                if ev is None:
                    raise AppError(404, "NOT_FOUND", "Créneau cible introuvable.")
                if (
                    ev.type == ScheduleEventType.course
                    or ev.source == ScheduleEventSource.timetable_import
                ):
                    raise AppError(
                        409,
                        "UNIVERSITY_COURSE_CONFLICT",
                        f"Le cours universitaire « {ev.title} » ne peut pas être supprimé via le copilote.",
                    )
                return {"event_id": str(ev.id), "event_title": ev.title, "reason": model.reason}

            if action_type == AiActionType.create_study_session:
                model = CreateStudySessionProposalPayload.model_validate(raw_payload)
                if (
                    "project_id" not in skip_fks
                    and model.project_id is not None
                    and self._project_repo.get(user_id, model.project_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Projet associé introuvable.")
                if (
                    "task_id" not in skip_fks
                    and model.task_id is not None
                    and self._task_repo.get(user_id, model.task_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Tâche associée introuvable.")
                if (
                    "skill_id" not in skip_fks
                    and model.skill_id is not None
                    and self._skill_repo.get_skill(user_id, model.skill_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Compétence associée introuvable.")
                if (
                    "goal_id" not in skip_fks
                    and model.goal_id is not None
                    and self._goal_repo is not None
                    and self._goal_repo.get(user_id, model.goal_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Objectif associé introuvable.")
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.create_skill:
                if raw_payload.get("current_level") not in (None, 0):
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "Une nouvelle compétence démarre obligatoirement au niveau 0 (verrou pédagogique).",
                    )
                cleaned_raw = {k: v for k, v in raw_payload.items() if k != "current_level"}
                model = CreateSkillProposalPayload.model_validate(cleaned_raw)
                if (
                    "goal_id" not in skip_fks
                    and model.goal_id is not None
                    and self._goal_repo is not None
                    and self._goal_repo.get(user_id, model.goal_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Objectif associé introuvable.")
                if (
                    "learning_path_id" not in skip_fks
                    and model.learning_path_id is not None
                    and self._learning_repo.get_path(user_id, model.learning_path_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Parcours associé introuvable.")
                out = model.model_dump(mode="json")
                out["current_level"] = 0
                return out

            if action_type == AiActionType.add_skill_evidence:
                model = AddEvidenceProposalPayload.model_validate(raw_payload)
                skill = self._skill_repo.get_skill(user_id, model.skill_id)
                if skill is None:
                    raise AppError(404, "NOT_FOUND", "Compétence cible introuvable.")
                quality = validate_evidence_quality(
                    model.type,
                    model.description,
                    model.reference_url,
                    model.result,
                )
                if not quality.admissible:
                    raise AppError(
                        422,
                        "EVIDENCE_QUALITY_INSUFFICIENT",
                        quality.reason or "Preuve proposée non admissible.",
                    )
                return {
                    "skill_id": str(skill.id),
                    "skill_name": skill.name,
                    "type": model.type.value,
                    "description": model.description,
                    "reference_url": model.reference_url,
                    "result": model.result,
                }

            if action_type == AiActionType.propose_skill_assessment:
                model = ProposeSkillAssessmentPayload.model_validate(raw_payload)
                skill = self._skill_repo.get_skill(user_id, model.skill_id)
                if skill is None:
                    raise AppError(404, "NOT_FOUND", "Compétence cible introuvable.")
                target_level = (
                    model.target_level
                    if model.target_level is not None
                    else min(5, max(1, skill.current_level + 1))
                )
                if target_level < max(1, skill.current_level) or target_level > 5:
                    raise AppError(
                        422,
                        "INVALID_TARGET_LEVEL",
                        "Le niveau visé par l’évaluation proposée est invalide.",
                    )
                if (
                    model.path_id is not None
                    and self._learning_repo.get_path(user_id, model.path_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Parcours associé introuvable.")
                if (
                    model.module_id is not None
                    and self._learning_repo.get_module(user_id, model.module_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Module associé introuvable.")
                if (
                    model.lesson_id is not None
                    and self._learning_repo.get_lesson(user_id, model.lesson_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Leçon associée introuvable.")
                return {
                    "skill_id": str(skill.id),
                    "skill_name": skill.name,
                    "current_level": skill.current_level,
                    "target_level": target_level,
                    "assessment_type": model.assessment_type.value,
                    "prompt_title": model.prompt_title,
                    "prompt_instructions": model.prompt_instructions,
                    "path_id": str(model.path_id) if model.path_id else None,
                    "module_id": str(model.module_id) if model.module_id else None,
                    "lesson_id": str(model.lesson_id) if model.lesson_id else None,
                }

            if action_type == AiActionType.recommend_skill_progression:
                model = RecommendSkillProgressionPayload.model_validate(raw_payload)
                skill = self._skill_repo.get_skill(user_id, model.skill_id)
                if skill is None:
                    raise AppError(404, "NOT_FOUND", "Compétence cible introuvable.")
                assessment = self._skill_repo.get_assessment(user_id, model.assessment_id)
                if assessment is None or assessment.skill_id != skill.id:
                    raise AppError(404, "NOT_FOUND", "Évaluation de compétence introuvable.")
                if assessment.status == SkillAssessmentStatus.approved:
                    raise AppError(
                        409,
                        "ASSESSMENT_ALREADY_APPROVED",
                        "Cette évaluation a déjà été validée et ne peut plus être réutilisée.",
                    )
                if assessment.status != SkillAssessmentStatus.evaluated:
                    raise AppError(
                        409,
                        "ASSESSMENT_NOT_EVALUATED",
                        "Seule une évaluation corrigée (statut evaluated) peut faire l’objet d’une progression.",
                    )
                threshold = pass_threshold_for_level(assessment.target_level)
                if (
                    assessment.passed is not True
                    or assessment.score is None
                    or assessment.score < threshold
                    or assessment.proposed_level is None
                ):
                    raise AppError(
                        422,
                        "ASSESSMENT_RESULT_INSUFFICIENT",
                        "Le résultat de l’évaluation est insuffisant pour recommander une progression.",
                    )
                if model.proposed_level != assessment.proposed_level:
                    raise AppError(
                        422,
                        "PROPOSED_LEVEL_MISMATCH",
                        "Le niveau recommandé par le Copilote ne correspond pas au niveau issu de l’évaluation.",
                    )

                candidate_evidence_ids = (
                    [str(eid) for eid in model.evidence_ids]
                    if model.evidence_ids
                    else list(assessment.evidence_ids)
                )
                if not candidate_evidence_ids:
                    raise AppError(
                        422,
                        "ASSESSMENT_EVIDENCE_REQUIRED",
                        "Au moins une preuve admissible appartenant à l’utilisateur est requise.",
                    )
                assessment_ev_set = set(assessment.evidence_ids)
                verified_ids: list[str] = []
                for raw_eid in candidate_evidence_ids:
                    try:
                        ev_uuid = UUID(str(raw_eid))
                    except ValueError as exc:
                        raise AppError(422, "ASSESSMENT_EVIDENCE_REQUIRED", "UUID de preuve invalide.") from exc
                    if str(ev_uuid) not in assessment_ev_set:
                        raise AppError(
                            422,
                            "EVIDENCE_NOT_LINKED_TO_ASSESSMENT",
                            "La preuve citée n’est pas rattachée à l’évaluation.",
                        )
                    ev = self._skill_repo.get_evidence(user_id, ev_uuid)
                    if ev is None:
                        raise AppError(
                            404,
                            "EVIDENCE_NOT_FOUND",
                            "Preuve introuvable ou appartenant à un autre utilisateur.",
                        )
                    if ev.skill_id != skill.id:
                        raise AppError(
                            422,
                            "EVIDENCE_SKILL_MISMATCH",
                            "La preuve citée appartient à une autre compétence.",
                        )
                    quality = validate_evidence_quality(
                        ev.type, ev.description, ev.reference_url, ev.result
                    )
                    if not quality.admissible:
                        raise AppError(
                            422,
                            "EVIDENCE_QUALITY_INSUFFICIENT",
                            quality.reason or "Preuve liée non admissible.",
                        )
                    verified_ids.append(str(ev_uuid))

                return {
                    "skill_id": str(skill.id),
                    "skill_name": skill.name,
                    "assessment_id": str(assessment.id),
                    "previous_level": skill.current_level,
                    "proposed_level": assessment.proposed_level,
                    "score": assessment.score,
                    "evidence_ids": verified_ids,
                    "decision_reason": model.decision_reason,
                }

            if action_type == AiActionType.create_learning_path:
                model = CreateLearningPathProposalPayload.model_validate(raw_payload)
                return model.model_dump(mode="json")

            if action_type == AiActionType.update_learning_path:
                model = UpdateLearningPathProposalPayload.model_validate(raw_payload)
                if "path_id" not in skip_fks and self._learning_repo.get_path(user_id, model.path_id) is None:
                    raise AppError(404, "NOT_FOUND", "Parcours cible introuvable.")
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.create_personal_goal:
                model = CreatePersonalGoalProposalPayload.model_validate(raw_payload)
                return model.model_dump(mode="json")

            if action_type == AiActionType.update_personal_goal:
                model = UpdatePersonalGoalProposalPayload.model_validate(raw_payload)
                if (
                    "goal_id" not in skip_fks
                    and self._goal_repo is not None
                    and self._goal_repo.get(user_id, model.goal_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Objectif cible introuvable.")
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.plan_strategic_activity:
                model = PlanStrategicActivityProposalPayload.model_validate(raw_payload)
                if model.park_only:
                    parked_model = model.model_copy(update={"proposed_slots": []})
                    return parked_model.model_dump(mode="json")

                for idx_a in range(len(model.proposed_slots)):
                    slot_a = model.proposed_slots[idx_a]
                    for idx_b in range(idx_a + 1, len(model.proposed_slots)):
                        slot_b = model.proposed_slots[idx_b]
                        if do_events_overlap(
                            slot_a.starts_at, slot_a.ends_at, slot_b.starts_at, slot_b.ends_at
                        ):
                            raise AppError(
                                422,
                                "INTERNAL_SLOT_OVERLAP",
                                "Deux créneaux proposés dans le même plan se chevauchent.",
                            )

                existing_events = self._schedule_repo.list_by_user(user_id)
                for slot in model.proposed_slots:
                    for ev in existing_events:
                        if do_events_overlap(
                            slot.starts_at, slot.ends_at, ev.starts_at, ev.ends_at
                        ):
                            if (
                                ev.type == ScheduleEventType.course
                                or ev.source == ScheduleEventSource.timetable_import
                            ):
                                raise AppError(
                                    409,
                                    "UNIVERSITY_COURSE_CONFLICT",
                                    f"Conflit avec le cours universitaire « {ev.title} » sur le créneau {slot.day_label} {slot.local_start_time}–{slot.local_end_time}.",
                                )
                            raise AppError(
                                409,
                                "SCHEDULE_CONFLICT_DETECTED",
                                f"Le créneau {slot.day_label} {slot.local_start_time}–{slot.local_end_time} entre en conflit avec l’événement existant « {ev.title} ». Veuillez modifier ou recalculer la proposition.",
                            )

                return model.model_dump(mode="json")

            if action_type == AiActionType.create_course:
                if raw_payload.get("current_level") not in (None, 1):
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "Un cours démarre obligatoirement au niveau 1 (verrou pédagogique).",
                    )
                model = CreateCourseProposalPayload.model_validate(
                    {k: v for k, v in raw_payload.items() if k != "current_level"}
                )
                return model.model_dump(mode="json")

            if action_type == AiActionType.update_preferences:
                model = UpdatePreferencesProposalPayload.model_validate(raw_payload)
                dumped = model.model_dump(mode="json", exclude_none=True)
                if not dumped:
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "Au moins une préférence ou disponibilité doit être précisée.",
                    )
                return dumped

            if action_type == AiActionType.manage_availability_rule:
                model = ManageAvailabilityRuleProposalPayload.model_validate(raw_payload)
                if model.recurrence == "weekly" and model.day_of_week is None:
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "Une règle hebdomadaire exige un jour de semaine (0=lundi .. 6=dimanche).",
                    )
                if model.recurrence in ("weekly", "daily") and (not model.start_time or not model.end_time):
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "Une règle récurrente exige start_time et end_time (HH:MM).",
                    )
                return model.model_dump(mode="json")

            if action_type == AiActionType.generate_learning_plan:
                model = GenerateLearningPlanProposalPayload.model_validate(raw_payload)
                if model.plan_version_id is not None and self._planning_repo is not None:
                    version = self._planning_repo.get_plan_version(user_id, model.plan_version_id)
                    if version is None:
                        raise AppError(
                            404,
                            "PLAN_VERSION_NOT_FOUND",
                            "Version de programme introuvable pour cet utilisateur.",
                        )
                return model.model_dump(mode="json")

            if action_type == AiActionType.batch_actions:
                model = BatchActionsProposalPayload.model_validate(raw_payload)
                normalized_steps: list[dict[str, Any]] = []
                for idx, step in enumerate(model.steps):
                    if not self._tool_registry.is_allowed_proposal_action(step.action_type.value):
                        raise AppError(
                            422,
                            "UNSUPPORTED_AI_ACTION",
                            f"L’action « {step.action_type.value} » n’est pas autorisée dans batch_actions.",
                        )
                    link_keys: set[str] = set()
                    if step.link_to_step:
                        for fk_name, src_idx in step.link_to_step.items():
                            if src_idx < 0 or src_idx >= idx:
                                raise AppError(
                                    422,
                                    "VALIDATION_ERROR",
                                    f"Référence inter-étapes invalide ({fk_name} -> étape {src_idx}) à l’étape {idx}.",
                                )
                            link_keys.add(fk_name)
                    step_payload = dict(step.payload or {})
                    for fk_name in link_keys:
                        step_payload.pop(fk_name, None)
                    validated_step_payload = self.validate_action_payload(
                        user_id,
                        step.action_type,
                        step_payload,
                        _skip_fks=link_keys,
                    )
                    normalized_steps.append(
                        {
                            "action_type": step.action_type.value,
                            "payload": validated_step_payload,
                            "link_to_step": dict(step.link_to_step) if step.link_to_step else None,
                        }
                    )
                return {
                    "summary": model.summary,
                    "steps": normalized_steps,
                    "compensate_on_failure": model.compensate_on_failure,
                }
        except ValidationError as exc:
            first_msg = exc.errors()[0].get("msg", "Paramètres d’action invalides.")
            raise AppError(422, "VALIDATION_ERROR", str(first_msg)) from exc

        raise AppError(422, "UNSUPPORTED_AI_ACTION", "Action IA non prise en charge.")
