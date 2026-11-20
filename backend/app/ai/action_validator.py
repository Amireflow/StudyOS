from typing import Any
from uuid import UUID
from pydantic import ValidationError
from app.ai.tool_registry import ToolRegistry
from app.core.errors import AppError
from app.repositories.learning_sql import (
    SqlLearningRepository,
    SqlProjectRepository,
    SqlSkillRepository,
)
from app.repositories.memory import ScheduleRepository, TaskRepository
from app.schemas.ai import (
    AddEvidenceProposalPayload,
    CreateScheduleProposalPayload,
    CreateTaskProposalPayload,
    ParkTaskProposalPayload,
    RawProposalCandidate,
    UpdateSkillLevelProposalPayload,
)
from app.schemas.common import AiActionType
from app.services.schedule_service import do_events_overlap


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
    ) -> None:
        self._tool_registry = tool_registry
        self._task_repo = task_repo
        self._schedule_repo = schedule_repo
        self._learning_repo = learning_repo
        self._skill_repo = skill_repo
        self._project_repo = project_repo

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
    ) -> dict[str, Any]:
        try:
            if action_type == AiActionType.create_task:
                model = CreateTaskProposalPayload.model_validate(raw_payload)
                if (
                    model.project_id is not None
                    and self._project_repo.get(user_id, model.project_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Projet associé introuvable.")
                if (
                    model.module_id is not None
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

            if action_type == AiActionType.create_schedule_event:
                model = CreateScheduleProposalPayload.model_validate(raw_payload)
                existing_events = self._schedule_repo.list_by_user(user_id)
                conflicts = [
                    ev.title
                    for ev in existing_events
                    if do_events_overlap(model.starts_at, model.ends_at, ev.starts_at, ev.ends_at)
                ]
                return {
                    "title": model.title,
                    "type": model.type.value,
                    "starts_at": model.starts_at.isoformat(),
                    "ends_at": model.ends_at.isoformat(),
                    "notes": model.notes,
                    "has_conflict": len(conflicts) > 0,
                    "conflicting_titles": conflicts,
                }

            if action_type == AiActionType.add_skill_evidence:
                model = AddEvidenceProposalPayload.model_validate(raw_payload)
                skill = self._skill_repo.get_skill(user_id, model.skill_id)
                if skill is None:
                    raise AppError(404, "NOT_FOUND", "Compétence cible introuvable.")
                return {
                    "skill_id": str(skill.id),
                    "skill_name": skill.name,
                    "type": model.type.value,
                    "description": model.description,
                    "reference_url": model.reference_url,
                    "result": model.result,
                }

            if action_type == AiActionType.update_skill_level:
                model = UpdateSkillLevelProposalPayload.model_validate(raw_payload)
                skill = self._skill_repo.get_skill(user_id, model.skill_id)
                if skill is None:
                    raise AppError(404, "NOT_FOUND", "Compétence cible introuvable.")
                return {
                    "skill_id": str(skill.id),
                    "skill_name": skill.name,
                    "previous_level": skill.current_level,
                    "current_level": model.current_level,
                    "target_level": (
                        model.target_level
                        if model.target_level is not None
                        else skill.target_level
                    ),
                }
        except ValidationError as exc:
            first_msg = exc.errors()[0].get("msg", "Paramètres d’action invalides.")
            raise AppError(422, "VALIDATION_ERROR", str(first_msg)) from exc

        raise AppError(422, "UNSUPPORTED_AI_ACTION", "Action IA non prise en charge.")
