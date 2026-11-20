from fastapi.testclient import TestClient


def test_projects_active_next_action_rule_priority_link_and_isolation(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    # PROJ-02 : projet actif sans next_action -> 422
    invalid_active = client.post(
        "/api/v1/projects",
        json={
            "name": "Amireflow MVP",
            "goal": "Livrer le socle Study OS",
            "status": "active",
            "next_action": "",
        },
        headers=user_a_headers,
    )
    assert invalid_active.status_code == 422

    # Création d'un projet planifié sans prochaine action (autorisé)
    planned = client.post(
        "/api/v1/projects",
        json={
            "name": "Portfolio V2",
            "goal": "Présenter 3 études de cas",
            "status": "planned",
            "deliverables": ["Page d'accueil", "Étude de cas 1", "  "],
        },
        headers=user_a_headers,
    )
    assert planned.status_code == 201
    project_id = planned.json()["id"]
    assert planned.json()["deliverables"] == ["Page d'accueil", "Étude de cas 1"]

    # Passage à active sans next_action -> 422
    activate_without_action = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "active"},
        headers=user_a_headers,
    )
    assert activate_without_action.status_code == 422

    # Passage à active avec next_action valide -> 200
    activated = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "active", "next_action": "Rédiger l'étude de cas Amireflow"},
        headers=user_a_headers,
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"

    # Effacer next_action sur un projet actif -> 422
    clear_action = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"next_action": ""},
        headers=user_a_headers,
    )
    assert clear_action.status_code == 422

    # PROJ-03 : définir comme projet prioritaire dans le profil
    profile_res = client.patch(
        "/api/v1/profile",
        json={"active_priority_project_id": project_id},
        headers=user_a_headers,
    )
    assert profile_res.status_code == 200
    assert profile_res.json()["active_priority_project_id"] == project_id
    assert profile_res.json()["active_priority_title"] == "Portfolio V2"

    # Associer une tâche au projet
    task = client.post(
        "/api/v1/tasks",
        json={"title": "Exporter captures d'écran", "project_id": project_id},
        headers=user_a_headers,
    )
    assert task.status_code == 201
    task_id = task.json()["id"]
    assert task.json()["project_id"] == project_id

    # Isolation stricte utilisateur B
    assert client.get("/api/v1/projects", headers=user_b_headers).json() == []
    assert client.get(f"/api/v1/projects/{project_id}", headers=user_b_headers).status_code == 404
    assert (
        client.patch(
            "/api/v1/profile",
            json={"active_priority_project_id": project_id},
            headers=user_b_headers,
        ).status_code
        == 404
    )

    # Suppression du projet -> détache tâche et nettoie active_priority_project_id
    assert client.delete(f"/api/v1/projects/{project_id}", headers=user_a_headers).status_code == 204
    assert client.get(f"/api/v1/tasks/{task_id}", headers=user_a_headers).json()["project_id"] is None
    profile_after = client.get("/api/v1/profile", headers=user_a_headers).json()
    assert profile_after["active_priority_project_id"] is None
    assert profile_after["active_priority_title"] is None
