from typing import Literal
from app.schemas.ai import AiToolSpec
from app.schemas.common import AiActionType

READ_TOOLS: tuple[AiToolSpec, ...] = (
    AiToolSpec(
        name="read_schedule",
        access="read",
        risk_level="read",
        label="Lire le planning",
        description="Consulte les créneaux horaires de l’utilisateur connecté uniquement.",
        requires_confirmation=False,
        parameter_keys=[],
    ),
    AiToolSpec(
        name="read_tasks",
        access="read",
        risk_level="read",
        label="Lire les tâches",
        description="Consulte les tâches actives, en retard ou au parking de l’utilisateur.",
        requires_confirmation=False,
        parameter_keys=[],
    ),
    AiToolSpec(
        name="read_learning_and_skills",
        access="read",
        risk_level="read",
        label="Lire les parcours, compétences et évaluations",
        description=(
            "Consulte les parcours, modules, leçons, compétences, preuves et l’historique "
            "des évaluations de l’utilisateur."
        ),
        requires_confirmation=False,
        parameter_keys=[],
    ),
    AiToolSpec(
        name="read_projects_and_sessions",
        access="read",
        risk_level="read",
        label="Lire les projets et séances",
        description="Consulte les projets et l’historique des séances d’étude de l’utilisateur.",
        requires_confirmation=False,
        parameter_keys=[],
    ),
    AiToolSpec(
        name="read_courses",
        access="read",
        risk_level="read",
        label="Lire les cours",
        description="Consulte les cours structurés, niveaux atteints, projets et ressources de l’utilisateur.",
        requires_confirmation=False,
        parameter_keys=[],
    ),
    AiToolSpec(
        name="read_personal_goals_and_memory",
        access="read",
        risk_level="read",
        label="Lire les objectifs et la mémoire personnelle",
        description=(
            "Consulte les objectifs personnels, contraintes, disponibilités mémorisées "
            "et décisions précédentes de l’utilisateur."
        ),
        requires_confirmation=False,
        parameter_keys=[],
    ),
)

PROPOSAL_TOOLS: tuple[AiToolSpec, ...] = (
    AiToolSpec(
        name=AiActionType.create_task.value,
        access="proposal",
        risk_level="simple",
        label="Proposer ou créer une tâche",
        description="Crée une nouvelle tâche (directement si le mode autonome simple est activé).",
        requires_confirmation=True,
        parameter_keys=["title", "description", "priority", "due_at", "project_id", "module_id"],
    ),
    AiToolSpec(
        name=AiActionType.update_task.value,
        access="proposal",
        risk_level="simple",
        label="Mettre à jour une tâche",
        description="Met à jour le statut, la priorité, l’échéance ou le rattachement d’une tâche.",
        requires_confirmation=True,
        parameter_keys=["task_id", "title", "description", "status", "priority", "due_at", "project_id", "module_id"],
    ),
    AiToolSpec(
        name=AiActionType.park_task.value,
        access="proposal",
        risk_level="simple",
        label="Placer une tâche au parking",
        description="Reporte une tâche non prioritaire au parking (Parcours C).",
        requires_confirmation=True,
        parameter_keys=["task_id", "reason"],
    ),
    AiToolSpec(
        name=AiActionType.create_project.value,
        access="proposal",
        risk_level="simple",
        label="Créer un projet",
        description="Crée un projet concret avec son objectif, ses livrables et sa prochaine action.",
        requires_confirmation=True,
        parameter_keys=["name", "category", "description", "goal", "status", "priority", "motivation", "weekly_target_minutes", "next_action", "deliverables", "goal_id"],
    ),
    AiToolSpec(
        name=AiActionType.update_project.value,
        access="proposal",
        risk_level="simple",
        label="Mettre à jour un projet",
        description="Met à jour les informations, l’objectif, la priorité ou le statut d’un projet.",
        requires_confirmation=True,
        parameter_keys=["project_id", "name", "description", "goal", "status", "priority", "next_action", "weekly_target_minutes"],
    ),
    AiToolSpec(
        name=AiActionType.pause_project.value,
        access="proposal",
        risk_level="simple",
        label="Mettre un projet en pause",
        description="Met un projet actif en pause pour libérer un emplacement actif (max 3).",
        requires_confirmation=True,
        parameter_keys=["project_id", "reason"],
    ),
    AiToolSpec(
        name=AiActionType.create_schedule_event.value,
        access="proposal",
        risk_level="simple",
        label="Planifier un créneau",
        description="Crée un événement ponctuel isolé dans l’agenda avec détection préalable des conflits. Ne compose pas un planning de plusieurs séances : utilise generate_learning_plan.",
        requires_confirmation=True,
        parameter_keys=["title", "type", "starts_at", "ends_at", "notes"],
    ),
    AiToolSpec(
        name=AiActionType.update_schedule_event.value,
        access="proposal",
        risk_level="structuring",
        label="Reprogrammer un créneau",
        description="Déplace ou ajuste un créneau personnel existant (jamais un cours universitaire importé).",
        requires_confirmation=True,
        parameter_keys=["event_id", "title", "starts_at", "ends_at", "notes", "reason"],
    ),
    AiToolSpec(
        name=AiActionType.archive_schedule_event.value,
        access="proposal",
        risk_level="sensitive",
        label="Annuler un créneau personnel",
        description="Retire un créneau personnel non universitaire sur confirmation explicite.",
        requires_confirmation=True,
        parameter_keys=["event_id", "reason"],
    ),
    AiToolSpec(
        name=AiActionType.create_study_session.value,
        access="proposal",
        risk_level="simple",
        label="Enregistrer ou démarrer une séance",
        description="Crée une séance d’étude liée à une tâche, un projet, une compétence ou un objectif.",
        requires_confirmation=True,
        parameter_keys=["title", "category", "planned_activity", "started_at", "project_id", "goal_id", "task_id", "skill_id"],
    ),
    AiToolSpec(
        name=AiActionType.create_skill.value,
        access="proposal",
        risk_level="simple",
        label="Ajouter une compétence",
        description="Enregistre une nouvelle compétence à développer (niveau initial strictement verrouillé à 0).",
        requires_confirmation=True,
        parameter_keys=["name", "domain", "description", "target_level", "goal_id", "learning_path_id"],
    ),
    AiToolSpec(
        name=AiActionType.add_skill_evidence.value,
        access="proposal",
        risk_level="simple",
        label="Ajouter une preuve de compétence",
        description="Enregistre une preuve concrète et vérifiable sur une compétence existante.",
        requires_confirmation=True,
        parameter_keys=["skill_id", "type", "description", "reference_url", "result"],
    ),
    AiToolSpec(
        name=AiActionType.propose_skill_assessment.value,
        access="proposal",
        risk_level="structuring",
        label="Proposer une évaluation de compétence",
        description=(
            "Propose un exercice ou une évaluation structurée sur une compétence "
            "(ne modifie jamais directement le niveau)."
        ),
        requires_confirmation=True,
        parameter_keys=[
            "skill_id",
            "target_level",
            "assessment_type",
            "prompt_title",
            "prompt_instructions",
            "path_id",
            "module_id",
            "lesson_id",
        ],
    ),
    AiToolSpec(
        name=AiActionType.recommend_skill_progression.value,
        access="proposal",
        risk_level="sensitive",
        label="Recommander une progression vérifiée",
        description=(
            "Recommande la validation officielle d’une évaluation déjà soumise, évaluée positivement "
            "et appuyée par des preuves admissibles appartenant à l’utilisateur."
        ),
        requires_confirmation=True,
        parameter_keys=[
            "skill_id",
            "assessment_id",
            "proposed_level",
            "evidence_ids",
            "decision_reason",
        ],
    ),
    AiToolSpec(
        name=AiActionType.create_learning_path.value,
        access="proposal",
        risk_level="structuring",
        label="Créer un parcours pédagogique",
        description="Crée un parcours d’apprentissage structuré avec ses modules initiaux.",
        requires_confirmation=True,
        parameter_keys=["title", "goal", "description", "status", "modules"],
    ),
    AiToolSpec(
        name=AiActionType.update_learning_path.value,
        access="proposal",
        risk_level="simple",
        label="Mettre à jour un parcours existant",
        description="Met à jour l’objectif, le statut ou enrichit un parcours existant sans doublon.",
        requires_confirmation=True,
        parameter_keys=["path_id", "title", "goal", "description", "status", "add_module_title", "add_lesson_title"],
    ),
    AiToolSpec(
        name=AiActionType.create_personal_goal.value,
        access="proposal",
        risk_level="simple",
        label="Créer un objectif personnel",
        description="Enregistre un nouvel objectif d’apprentissage ou personnel et le rattache aux modules utiles.",
        requires_confirmation=True,
        parameter_keys=["title", "category", "goal", "description", "current_level", "target_level", "priority", "is_primary", "motivation", "weekly_target_minutes", "next_action", "create_linked_entities"],
    ),
    AiToolSpec(
        name=AiActionType.update_personal_goal.value,
        access="proposal",
        risk_level="simple",
        label="Mettre à jour un objectif personnel",
        description="Met à jour, suspend, reprend ou ajuste un objectif personnel existant.",
        requires_confirmation=True,
        parameter_keys=["goal_id", "title", "goal", "description", "priority", "status", "is_primary", "weekly_target_minutes", "next_action"],
    ),
    AiToolSpec(
        name=AiActionType.plan_strategic_activity.value,
        access="proposal",
        risk_level="structuring",
        label="Planifier une activité ou un parcours validé",
        description=(
            "Analyse la faisabilité stratégique et programme, uniquement après validation explicite, "
            "un nouvel apprentissage, projet ou préparation d’examen avec ses créneaux vérifiés sans conflit."
        ),
        requires_confirmation=True,
        parameter_keys=[
            "activity_title",
            "category",
            "goal",
            "decision",
            "conditions",
            "opportunity_cost_note",
            "create_learning_path",
            "create_project",
            "park_only",
            "frequency_per_week",
            "session_duration_minutes",
            "estimated_weeks",
            "start_date",
            "proposed_slots",
        ],
    ),
    AiToolSpec(
        name=AiActionType.create_course.value,
        access="proposal",
        risk_level="structuring",
        label="Proposer la création d’un cours",
        description=(
            "Propose un cours complet progressif démarrant au niveau 1 (explications, exemples, "
            "exercices, projet à rendre et ressources officielles), soumis à validation utilisateur."
        ),
        requires_confirmation=True,
        parameter_keys=["subject", "title", "domain", "language", "total_levels", "goal"],
    ),
    AiToolSpec(
        name=AiActionType.update_preferences.value,
        access="proposal",
        risk_level="simple",
        label="Mettre à jour les préférences et disponibilités",
        description="Met à jour durablement le volume hebdomadaire, les plages horaires et la mémoire personnelle IA.",
        requires_confirmation=True,
        parameter_keys=["weekly_study_hours", "study_start_hour", "study_end_hour", "max_daily_study_minutes", "preferred_session_minutes", "excluded_days", "ai_instructions", "constraints", "long_term_goals", "academic_context"],
    ),
    AiToolSpec(
        name=AiActionType.manage_availability_rule.value,
        access="proposal",
        risk_level="simple",
        label="Enregistrer une règle de disponibilité ou d’indisponibilité",
        description="Ajoute une indisponibilité personnelle, une disponibilité confirmée ou un créneau de récupération respecté par le moteur de planification.",
        requires_confirmation=True,
        parameter_keys=["label", "rule_type", "day_of_week", "start_time", "end_time", "starts_at", "ends_at", "timezone", "recurrence", "notes"],
    ),
    AiToolSpec(
        name=AiActionType.generate_learning_plan.value,
        access="proposal",
        risk_level="structuring",
        label="Générer et appliquer un programme d’apprentissage personnalisé",
        description="Outil obligatoire pour tout plan de travail, planning hebdomadaire ou programme multi-séances. Analyse cours, objectifs, compétences, tâches, disponibilités et historique, puis répartit les étapes pédagogiques sans conflit ni surcharge.",
        requires_confirmation=True,
        parameter_keys=["horizon_days", "max_sessions", "focus_subject", "exam_title", "exam_at", "weekly_hours_override", "daily_max_minutes", "preferred_session_minutes", "include_potential_slots", "create_missing_courses", "apply_immediately", "replace_future_planned", "plan_version_id", "instruction"],
    ),
    AiToolSpec(
        name=AiActionType.batch_actions.value,
        access="proposal",
        risk_level="structuring",
        label="Exécuter un plan multi-actions coordonné",
        description="Regroupe des mutations métier hétérogènes et dépendantes avec compensation atomique. Ne jamais l’utiliser pour planifier plusieurs séances d’apprentissage, qui relèvent de generate_learning_plan.",
        requires_confirmation=True,
        parameter_keys=["summary", "steps", "compensate_on_failure"],
    ),
)


class ToolRegistry:
    """Liste blanche stricte des outils métier exposés au copilote IA (AI-02, AI-03).

    Aucune suppression directe destructrice, modification directe de niveau, ni requête SQL directe n'est enregistrée.
    """

    def __init__(self) -> None:
        self._read_tools = {tool.name: tool for tool in READ_TOOLS}
        self._proposal_tools = {tool.name: tool for tool in PROPOSAL_TOOLS}

    def list_tools(self) -> list[AiToolSpec]:
        return [*READ_TOOLS, *PROPOSAL_TOOLS]

    def list_proposal_tools(self) -> list[AiToolSpec]:
        return list(PROPOSAL_TOOLS)

    def is_allowed_proposal_action(self, action_type: str) -> bool:
        return action_type in self._proposal_tools

    def get_proposal_tool(self, action_type: str) -> AiToolSpec | None:
        return self._proposal_tools.get(action_type)

    def get_risk_level(
        self,
        action_type: str,
    ) -> Literal["read", "simple", "structuring", "sensitive"]:
        tool = self._proposal_tools.get(action_type)
        return tool.risk_level if tool is not None else "sensitive"

    def can_auto_execute(
        self,
        action_type: str,
        *,
        allow_simple: bool,
        user_instructed: bool = True,
    ) -> bool:
        if not allow_simple or not user_instructed:
            return False
        return self.get_risk_level(action_type) == "simple"
