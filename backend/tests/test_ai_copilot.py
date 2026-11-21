from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace
from uuid import uuid4
from app.ai.context_builder import BoundedUserContext
from app.ai.prompt_manager import PromptManager
from app.ai.provider import ProviderResult, _parse_llm_json_output
from app.ai.tool_registry import ToolRegistry
from app.planning.content_resolver import SessionContentResolver
from app.schemas.planning import LearningPriorityItem
from app.schemas.ai import RawProposalCandidate


def test_ai_tools_whitelist_excludes_delete_and_sql(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    res = client.get("/api/v1/ai/tools", headers=user_a_headers)
    assert res.status_code == 200
    tools = res.json()
    names = {t["name"] for t in tools}
    assert "create_task" in names
    assert "park_task" in names
    assert "create_schedule_event" in names
    assert "add_skill_evidence" in names
    assert "propose_skill_assessment" in names
    assert "recommend_skill_progression" in names
    assert "update_skill_level" not in names
    assert not any("delete" in name or "sql" in name for name in names)


def test_ai_proposal_approval_gate_overrides_rejection_and_isolation(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    # Créer une conversation
    conv = client.post("/api/v1/ai/conversations", json={}, headers=user_a_headers)
    assert conv.status_code == 201
    conv_id = conv.json()["id"]

    # Envoyer un message demandant la création d'une tâche (AI-01 : aucune mutation immédiate)
    turn = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Crée une tâche : « Réviser les transactions SQLAlchemy »"},
        headers=user_a_headers,
    )
    assert turn.status_code == 201
    turn_data = turn.json()
    assert len(turn_data["proposals"]) == 1
    proposal = turn_data["proposals"][0]
    proposal_id = proposal["id"]
    assert proposal["action_type"] == "create_task"
    assert proposal["status"] == "pending"

    # Tant que l'utilisateur n'a pas validé, aucune tâche n'existe en base
    assert client.get("/api/v1/tasks", headers=user_a_headers).json() == []

    # Isolation stricte : l'utilisateur B ne peut ni voir ni accepter la proposition de A
    assert client.get("/api/v1/ai/conversations", headers=user_b_headers).json() == []
    assert client.get(f"/api/v1/ai/conversations/{conv_id}", headers=user_b_headers).status_code == 404
    assert client.get("/api/v1/ai/proposals", headers=user_b_headers).json() == []
    assert (
        client.post(f"/api/v1/ai/proposals/{proposal_id}/accept", headers=user_b_headers).status_code
        == 404
    )

    # Validation par l'utilisateur A avec ajustement de priorité (payload_overrides)
    accepted = client.post(
        f"/api/v1/ai/proposals/{proposal_id}/accept",
        json={
            "payload_overrides": {
                "title": "Réviser les transactions SQLAlchemy 2.0",
                "priority": "high",
            }
        },
        headers=user_a_headers,
    )
    assert accepted.status_code == 200
    acc_data = accepted.json()
    assert acc_data["status"] == "executed"
    assert acc_data["resolved_at"] is not None
    assert acc_data["execution_result"]["source"] == "ai_proposal"

    # La tâche a maintenant été créée avec source=ai_proposal et proposal_id traçable (AI-07)
    tasks = client.get("/api/v1/tasks", headers=user_a_headers).json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Réviser les transactions SQLAlchemy 2.0"
    assert tasks[0]["priority"] == "high"
    assert tasks[0]["source"] == "ai_proposal"
    assert tasks[0]["proposal_id"] == proposal_id

    # Impossible de ré-exécuter ou rejeter une proposition déjà exécutée (409)
    assert (
        client.post(f"/api/v1/ai/proposals/{proposal_id}/accept", headers=user_a_headers).status_code
        == 409
    )
    assert (
        client.post(f"/api/v1/ai/proposals/{proposal_id}/reject", headers=user_a_headers).status_code
        == 409
    )

    # Demander de placer une tâche au parking (Parcours C) puis rejeter la proposition
    park_turn = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je suis en surcharge, mets cette tâche au parking"},
        headers=user_a_headers,
    )
    assert park_turn.status_code == 201
    park_prop = park_turn.json()["proposals"][0]
    assert park_prop["action_type"] == "park_task"

    rejected = client.post(
        f"/api/v1/ai/proposals/{park_prop['id']}/reject",
        json={"reason": "Je préfère la traiter ce soir"},
        headers=user_a_headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    # La tâche reste active (todo)
    assert client.get("/api/v1/tasks", headers=user_a_headers).json()[0]["status"] == "todo"


def test_ai_rejects_unregistered_tools_and_cross_user_references(
    app: FastAPI,
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    # Tâche appartenant à l'utilisateur B
    task_b = client.post(
        "/api/v1/tasks",
        json={"title": "Tâche privée de B"},
        headers=user_b_headers,
    ).json()

    class MaliciousMockProvider:
        def generate_response(
            self,
            *,
            user_message: str,
            history: list[dict[str, str]],
            context: BoundedUserContext,
            prompt_manager: PromptManager,
        ) -> ProviderResult:
            _ = (user_message, history, context, prompt_manager)
            return ProviderResult(
                reply="Tentative d'appels non autorisés.",
                proposals=[
                    RawProposalCandidate(
                        action_type="delete_all_tasks",
                        title="Supprimer toutes les tâches",
                        explanation="Outil hors liste blanche",
                        payload={},
                    ),
                    RawProposalCandidate(
                        action_type="park_task",
                        title="Mettre la tâche de B au parking",
                        explanation="Référence inter-utilisateurs interdite",
                        payload={"task_id": task_b["id"]},
                    ),
                ],
                is_estimate=False,
                missing_data=[],
                provider_name="mock",
                model_name="mock-v1",
            )

    app.state.ai_provider = MaliciousMockProvider()
    try:
        conv = client.post("/api/v1/ai/conversations", json={}, headers=user_a_headers).json()
        turn = client.post(
            f"/api/v1/ai/conversations/{conv['id']}/messages",
            json={"content": "Test de sécurité ToolRegistry"},
            headers=user_a_headers,
        )
        assert turn.status_code == 201
        data = turn.json()
        # Les 2 propositions illégitimes ont été filtrées par ActionValidator (AI-01, AI-03)
        assert data["proposals"] == []
        assert data["assistant_message"]["metadata"]["rejected_proposals_count"] == 2
        assert client.get("/api/v1/ai/proposals", headers=user_a_headers).json() == []
    finally:
        app.state.ai_provider = None


def test_ai_daily_briefing_and_weekly_review_generation(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    # Sans données initiales, is_estimate=True et missing_data est renseigné (AI-06)
    briefing = client.post("/api/v1/ai/briefing", headers=user_a_headers)
    assert briefing.status_code == 201
    b_data = briefing.json()
    assert b_data["type"] == "daily_briefing"
    assert b_data["metadata"]["is_estimate"] is True
    assert len(b_data["metadata"]["missing_data"]) > 0

    review = client.post("/api/v1/ai/weekly-review", headers=user_a_headers)
    assert review.status_code == 201
    r_data = review.json()
    assert r_data["type"] == "weekly_review"
    assert "Bilan hebdomadaire" in r_data["content"]

    reports_a = client.get("/api/v1/ai/reports", headers=user_a_headers).json()
    assert len(reports_a) == 2

    # Isolation utilisateur B
    assert client.get("/api/v1/ai/reports", headers=user_b_headers).json() == []


def test_parse_llm_json_output_extracts_fenced_and_multiline_json_without_leaking_json() -> None:
    dummy_context = BoundedUserContext(
        profile={},
        included_scopes=["auto"],
        is_partial_data=True,
        missing_data=["Aucune tâche enregistrée."],
    )
    raw_llm_output = (
        "J'ai analysé tes 8 cours importés et identifié tes créneaux libres.\n\n"
        "```json\n"
        "{\n"
        '  "reply": "Voici ma recommandation pour organiser ta semaine autour de tes cours.",\n'
        '  "is_estimate": true,\n'
        '  "missing_data": ["Aucune tâche enregistrée."],\n'
        '  "proposals": [\n'
        "    {\n"
        '      "action_type": "generate_learning_plan",\n'
        '      "title": "Générer un programme sur les créneaux libres",\n'
        '      "explanation": "Planifie tes séances sans chevaucher tes 8 cours universitaires.",\n'
        '      "payload": {\n'
        '        "horizon_days": null,\n'
        '        "create_missing_courses": false,\n'
        '        "apply_immediately": false,\n'
        '        "replace_future_planned": false,\n'
        '        "instruction": "Planifier uniquement sur les créneaux recommandés"\n'
        "      }\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "```"
    )
    parsed = _parse_llm_json_output(raw_llm_output, dummy_context, "river", "gpt-4o-mini")
    assert "```" not in parsed.reply
    assert "create_missing_courses" not in parsed.reply
    assert "J'ai analysé tes 8 cours importés" in parsed.reply
    assert "Voici ma recommandation" in parsed.reply
    assert len(parsed.proposals) == 1
    assert parsed.proposals[0].action_type == "generate_learning_plan"
    assert parsed.proposals[0].payload == {
        "create_missing_courses": False,
        "apply_immediately": False,
        "replace_future_planned": False,
        "instruction": "Planifier uniquement sur les créneaux recommandés",
    }



def test_prompt_requires_the_dedicated_engine_for_every_multi_session_study_plan() -> None:
    context = BoundedUserContext(
        profile={},
        included_scopes=["auto"],
        is_partial_data=False,
        missing_data=[],
    )
    prompt = PromptManager(ToolRegistry()).build_system_prompt(context)
    assert "Toute demande de plan de travail" in prompt
    assert "doit obligatoirement utiliser generate_learning_plan" in prompt
    assert "Ne l'utilise JAMAIS pour construire plusieurs séances d'étude" in prompt
    assert "planifier plusieurs créneaux" not in prompt


def test_legacy_batch_of_study_sessions_is_routed_to_learning_planner(
    app: FastAPI,
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    class LegacyBatchStudyProvider:
        def generate_response(self, *, user_message, history, context, prompt_manager):
            _ = (user_message, history, context, prompt_manager)
            return ProviderResult(
                reply="J'ai préparé trois créneaux d'étude.",
                proposals=[
                    RawProposalCandidate(
                        action_type="batch_actions",
                        title="Actions coordonnées (3 étapes)",
                        explanation="Trois séances d'étude proposées séparément.",
                        payload={
                            "summary": "Trois séances d'apprentissage",
                            "steps": [
                                {
                                    "action_type": "create_schedule_event",
                                    "payload": {
                                        "title": f"Séance {index + 1}",
                                        "type": "learning",
                                        "starts_at": f"2026-11-{22 + index:02d}T09:00:00+00:00",
                                        "ends_at": f"2026-11-{22 + index:02d}T10:00:00+00:00",
                                    },
                                }
                                for index in range(3)
                            ],
                        },
                    )
                ],
                provider_name="test",
                model_name="legacy-batch-fixture",
            )

    app.state.ai_provider = LegacyBatchStudyProvider()
    conversation = client.post(
        "/api/v1/ai/conversations",
        json={"title": "Study plan regression"},
        headers=user_a_headers,
    )
    assert conversation.status_code == 201
    turn = client.post(
        f"/api/v1/ai/conversations/{conversation.json()['id']}/messages",
        json={"content": "Prépare mon programme de travail cette semaine."},
        headers=user_a_headers,
    )
    assert turn.status_code == 201
    proposal = turn.json()["proposals"][0]
    assert proposal["action_type"] == "generate_learning_plan"
    assert proposal["payload"]["max_sessions"] == 3
    assert client.get("/api/v1/schedule", headers=user_a_headers).json() == []



def test_planning_content_resolver_uses_the_configured_user_course_service() -> None:
    user_id = uuid4()

    class FakeCourseService:
        def __init__(self) -> None:
            self.calls = []

        def preview_course(self, payload, *, user_id):
            self.calls.append((payload, user_id))
            return SimpleNamespace(
                title="Parcours REST généré par IA",
                levels_roadmap=[SimpleNamespace(title="Fondations HTTP et REST")],
                first_level_lessons=[
                    SimpleNamespace(
                        title="Concevoir une API REST",
                        summary="Routes, verbes HTTP, statuts et validation des données.",
                        exercises=[SimpleNamespace(title="Créer trois routes CRUD et les tester")],
                    )
                ],
                first_level_project_deliverables=["API REST testée avec des requêtes HTTP"],
            )

    fake_course_service = FakeCourseService()
    resolver = SessionContentResolver(course_service=fake_course_service)
    priority = LearningPriorityItem(
        source_type="personal_goal",
        title="Maîtriser la conception d'API REST",
        subject="API REST",
        domain="Développement backend",
        score=85,
        recommended_minutes=90,
    )

    result = resolver._resolve_preview_course_step(priority, user_id=user_id)

    assert len(fake_course_service.calls) == 1
    request, called_user_id = fake_course_service.calls[0]
    assert request.subject == "API REST"
    assert called_user_id == user_id
    assert result.course_title == "Parcours REST généré par IA"
    assert result.level_title == "Fondations HTTP et REST"
    assert result.lesson_title == "Concevoir une API REST"
    assert result.exercises_focus == ["Créer trois routes CRUD et les tester"]
    assert result.deliverables == ["API REST testée avec des requêtes HTTP"]
