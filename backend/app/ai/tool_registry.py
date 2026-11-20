from app.schemas.ai import AiToolSpec
from app.schemas.common import AiActionType

READ_TOOLS: tuple[AiToolSpec, ...] = (
    AiToolSpec(
        name="read_schedule",
        access="read",
        label="Lire le planning",
        description="Consulte les créneaux horaires de l’utilisateur connecté uniquement.",
        requires_confirmation=False,
        parameter_keys=[],
    ),
    AiToolSpec(
        name="read_tasks",
        access="read",
        label="Lire les tâches",
        description="Consulte les tâches actives, en retard ou au parking de l’utilisateur.",
        requires_confirmation=False,
        parameter_keys=[],
    ),
    AiToolSpec(
        name="read_learning_and_skills",
        access="read",
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
        label="Lire les projets et séances",
        description="Consulte les projets et l’historique des séances d’étude de l’utilisateur.",
        requires_confirmation=False,
        parameter_keys=[],
    ),
    AiToolSpec(
        name="read_courses",
        access="read",
        label="Lire les cours",
        description="Consulte les cours structurés, niveaux atteints, projets et ressources de l’utilisateur.",
        requires_confirmation=False,
        parameter_keys=[],
    ),
)

PROPOSAL_TOOLS: tuple[AiToolSpec, ...] = (
    AiToolSpec(
        name=AiActionType.create_task.value,
        access="proposal",
        label="Proposer une tâche",
        description="Propose la création d’une nouvelle tâche (soumise à validation utilisateur).",
        requires_confirmation=True,
        parameter_keys=["title", "description", "priority", "due_at", "project_id", "module_id"],
    ),
    AiToolSpec(
        name=AiActionType.park_task.value,
        access="proposal",
        label="Proposer de placer une tâche au parking",
        description="Propose de reporter une tâche non prioritaire au parking (Parcours C).",
        requires_confirmation=True,
        parameter_keys=["task_id", "reason"],
    ),
    AiToolSpec(
        name=AiActionType.create_schedule_event.value,
        access="proposal",
        label="Proposer un créneau",
        description="Propose un créneau dans le planning avec détection préalable des conflits.",
        requires_confirmation=True,
        parameter_keys=["title", "type", "starts_at", "ends_at", "notes"],
    ),
    AiToolSpec(
        name=AiActionType.add_skill_evidence.value,
        access="proposal",
        label="Proposer une preuve de compétence",
        description="Propose d’enregistrer une preuve concrète et vérifiable sur une compétence existante.",
        requires_confirmation=True,
        parameter_keys=["skill_id", "type", "description", "reference_url", "result"],
    ),
    AiToolSpec(
        name=AiActionType.propose_skill_assessment.value,
        access="proposal",
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
        name=AiActionType.plan_strategic_activity.value,
        access="proposal",
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
        label="Proposer la création d’un cours",
        description=(
            "Propose un cours complet progressif démarrant au niveau 1 (explications, exemples, "
            "exercices, projet à rendre et ressources officielles), soumis à validation utilisateur."
        ),
        requires_confirmation=True,
        parameter_keys=["subject", "title", "domain", "language", "total_levels", "goal"],
    ),
)


class ToolRegistry:
    """Liste blanche stricte des outils métier exposés au copilote IA (AI-02, AI-03).

    Aucune suppression, modification directe de niveau, ni requête SQL directe n'est enregistrée.
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
