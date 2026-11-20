"""Scénarios d'acceptation de bout en bout du Cahier des charges §11.3 (E2E-01 à E2E-04)
et garde-fous de déploiement production (Lot 8).
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app


def test_e2e_01_plan_and_complete_priority_task(client: TestClient) -> None:
    """E2E-01 — Planifier et terminer une tâche."""
    login = client.post(
        "/api/v1/auth/local-login",
        json={"email": "e2e01@amireflow.local", "display_name": "Khadim E2E"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    task_res = client.post(
        "/api/v1/tasks",
        json={
            "title": "Valider le scénario E2E-01",
            "priority": "critical",
            "due_at": "2026-11-20T18:00:00Z",
        },
        headers=headers,
    )
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]

    profile_res = client.patch(
        "/api/v1/profile",
        json={"active_priority_task_id": task_id},
        headers=headers,
    )
    assert profile_res.status_code == 200

    dash_before = client.get("/api/v1/dashboard", headers=headers).json()
    assert dash_before["active_priority"]["title"] == "Valider le scénario E2E-01"
    assert dash_before["task_summary"]["active_count"] == 1
    assert dash_before["priority_tasks"][0]["id"] == task_id

    done_res = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "done"},
        headers=headers,
    )
    assert done_res.status_code == 200
    assert done_res.json()["status"] == "done"
    assert done_res.json()["completed_at"] is not None

    done_tasks = client.get("/api/v1/tasks?status=done", headers=headers).json()
    assert len(done_tasks) == 1
    assert done_tasks[0]["id"] == task_id
    dash_after = client.get("/api/v1/dashboard", headers=headers).json()
    assert dash_after["task_summary"]["done_count"] == 1
    assert dash_after["task_summary"]["active_count"] == 0


def test_e2e_02_follow_learning_path_to_skill_evidence(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """E2E-02 — Suivre un apprentissage jusqu'à une preuve et une évaluation validée."""
    skill = client.post(
        "/api/v1/skills",
        json={"name": "Python & FastAPI", "domain": "Backend", "current_level": 0, "target_level": 4},
        headers=user_a_headers,
    ).json()
    skill_id = skill["id"]

    path = client.post(
        "/api/v1/learning/paths",
        json={"title": "Parcours Python Backend", "goal": "Livrer une API REST", "status": "active"},
        headers=user_a_headers,
    ).json()

    module = client.post(
        "/api/v1/learning/modules",
        json={"path_id": path["id"], "title": "Tests & Validation", "position": 1, "status": "active"},
        headers=user_a_headers,
    ).json()

    lesson = client.post(
        "/api/v1/learning/lessons",
        json={"module_id": module["id"], "title": "Fixtures Pytest", "position": 1},
        headers=user_a_headers,
    ).json()
    done_lesson = client.patch(
        f"/api/v1/learning/lessons/{lesson['id']}",
        json={"status": "completed"},
        headers=user_a_headers,
    )
    assert done_lesson.status_code == 200
    assert client.get(f"/api/v1/skills/{skill_id}", headers=user_a_headers).json()["current_level"] == 0

    session = client.post(
        "/api/v1/sessions",
        json={
            "title": "Écriture de la suite E2E Pytest",
            "category": "Apprentissage",
            "started_at": "2026-11-20T08:00:00Z",
            "ended_at": "2026-11-20T09:15:00Z",
            "result": "4 scénarios E2E écrits et vérifiés.",
            "module_id": module["id"],
            "lesson_id": lesson["id"],
            "skill_id": skill_id,
        },
        headers=user_a_headers,
    )
    assert session.status_code == 201
    assert session.json()["duration_minutes"] == 75

    ev = client.post(
        f"/api/v1/skills/{skill_id}/evidence",
        json={
            "type": "assessment",
            "description": "Suite test_e2e_acceptance.py exécutée avec succès",
            "reference_url": "https://github.com/amireflow/study-os",
            "result": "100% pass",
        },
        headers=user_a_headers,
    )
    assert ev.status_code == 201

    evidence_list = client.get(
        f"/api/v1/skills/{skill_id}/evidence",
        headers=user_a_headers,
    ).json()
    assert len(evidence_list) == 1
    assert evidence_list[0]["description"] == "Suite test_e2e_acceptance.py exécutée avec succès"


def test_e2e_03_use_ai_copilot_reject_then_accept_proposal(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """E2E-03 — Utiliser le copilote (contexte contrôlé, rejet sans mutation, acceptation traçable)."""
    conv = client.post("/api/v1/ai/conversations", json={}, headers=user_a_headers).json()
    conv_id = conv["id"]

    turn1 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={
            "content": "Crée une tâche : « Tâche à rejeter »",
            "context_scopes": ["today", "tasks"],
        },
        headers=user_a_headers,
    )
    assert turn1.status_code == 201
    t1_data = turn1.json()
    assert set(t1_data["assistant_message"]["metadata"]["included_scopes"]) == {"today", "tasks"}
    prop1_id = t1_data["proposals"][0]["id"]

    rej = client.post(
        f"/api/v1/ai/proposals/{prop1_id}/reject",
        json={"reason": "Non prioritaire"},
        headers=user_a_headers,
    )
    assert rej.status_code == 200
    assert rej.json()["status"] == "rejected"
    assert client.get("/api/v1/tasks", headers=user_a_headers).json() == []

    turn2 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Crée une tâche : « Finaliser le déploiement Lot 8 »"},
        headers=user_a_headers,
    )
    assert turn2.status_code == 201
    prop2_id = turn2.json()["proposals"][0]["id"]

    acc = client.post(
        f"/api/v1/ai/proposals/{prop2_id}/accept",
        headers=user_a_headers,
    )
    assert acc.status_code == 200
    assert acc.json()["status"] == "executed"

    tasks = client.get("/api/v1/tasks", headers=user_a_headers).json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Finaliser le déploiement Lot 8"
    assert tasks[0]["source"] == "ai_proposal"
    assert tasks[0]["proposal_id"] == prop2_id


def test_e2e_04_data_isolation_and_production_security_guards(
    client: TestClient,
    strict_auth_client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    """E2E-04 — Isolation des données entre comptes, jetons invalides et garde-fous production."""
    task_a = client.post(
        "/api/v1/tasks",
        json={"title": "Ressource confidentielle A"},
        headers=user_a_headers,
    ).json()
    project_a = client.post(
        "/api/v1/projects",
        json={
            "name": "Projet privé A",
            "goal": "Objectif A",
            "status": "active",
            "next_action": "Action A",
        },
        headers=user_a_headers,
    ).json()
    conv_a = client.post("/api/v1/ai/conversations", json={}, headers=user_a_headers).json()

    unauth = strict_auth_client.get(f"/api/v1/tasks/{task_a['id']}")
    assert unauth.status_code == 401
    assert unauth.headers["X-Content-Type-Options"] == "nosniff"
    assert unauth.headers["X-Frame-Options"] == "DENY"

    assert client.get(f"/api/v1/tasks/{task_a['id']}", headers=user_b_headers).status_code == 404
    assert (
        client.get(f"/api/v1/projects/{project_a['id']}", headers=user_b_headers).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/ai/conversations/{conv_a['id']}", headers=user_b_headers).status_code
        == 404
    )

    with pytest.raises(RuntimeError, match="ALLOW_LOCAL_DEV_AUTH"):
        create_app(
            settings=Settings(
                app_env="production",
                allow_local_dev_auth=True,
                database_url=f"sqlite:///{(tmp_path / 'prod_check.db').as_posix()}",
            )
        )
