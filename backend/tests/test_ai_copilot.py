from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.ai.context_builder import BoundedUserContext
from app.ai.prompt_manager import PromptManager
from app.ai.provider import ProviderResult
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
    assert "update_skill_level" in names
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
