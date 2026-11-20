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
        label="Lire les parcours et compétences",
        description="Consulte les parcours, modules, leçons, compétences et preuves de l’utilisateur.",
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
        description="Propose d’enregistrer une preuve vérifiable sur une compétence existante.",
        requires_confirmation=True,
        parameter_keys=["skill_id", "type", "description", "reference_url", "result"],
    ),
    AiToolSpec(
        name=AiActionType.update_skill_level.value,
        access="proposal",
        label="Proposer un niveau de compétence",
        description="Propose une réévaluation du niveau 0..5 d’une compétence (SKILL-01).",
        requires_confirmation=True,
        parameter_keys=["skill_id", "current_level", "target_level"],
    ),
)


class ToolRegistry:
    """Liste blanche stricte des outils métier exposés au copilote IA (AI-02, AI-03).

    Aucune suppression ni action externe ni requête SQL directe n'est enregistrée.
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
