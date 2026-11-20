from fastapi.testclient import TestClient


def test_tasks_crud_completed_at_and_combined_filters(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    # Création tâche 1 (en retard, haute priorité)
    t1 = client.post(
        "/api/v1/tasks",
        json={
            "title": "Corriger API FastAPI",
            "description": "Ajouter les tests Pytest",
            "priority": "high",
            "status": "in_progress",
            "due_at": "2020-01-10T18:00:00Z",
        },
        headers=user_a_headers,
    )
    assert t1.status_code == 201
    task1 = t1.json()
    assert task1["completed_at"] is None
    assert task1["source"] == "manual"

    # Création tâche 2 (parking, basse priorité)
    t2 = client.post(
        "/api/v1/tasks",
        json={"title": "Idée future", "priority": "low", "status": "parked"},
        headers=user_a_headers,
    )
    assert t2.status_code == 201

    # Filtres combinés (TASK-03)
    filtered = client.get(
        "/api/v1/tasks",
        params={"status": "active", "priority": "high", "due": "overdue", "search": "fastapi"},
        headers=user_a_headers,
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [task1["id"]]

    # Passage à done -> completed_at fixé et conservé lors d'une édition ultérieure (TASK-01)
    done_res = client.patch(
        f"/api/v1/tasks/{task1['id']}",
        json={"status": "done"},
        headers=user_a_headers,
    )
    assert done_res.status_code == 200
    completed_at = done_res.json()["completed_at"]
    assert completed_at is not None

    edit_res = client.patch(
        f"/api/v1/tasks/{task1['id']}",
        json={"title": "Corriger API FastAPI v2"},
        headers=user_a_headers,
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["completed_at"] == completed_at


def test_cancelled_task_is_not_counted_as_done_and_users_are_isolated(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/tasks",
        json={"title": "Tâche annulée", "status": "cancelled"},
        headers=user_a_headers,
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    # TASK-02 : cancelled ne compte pas comme done sur le dashboard
    dash = client.get("/api/v1/dashboard", headers=user_a_headers).json()
    assert dash["task_summary"]["done_count"] == 0
    assert dash["task_summary"]["cancelled_count"] == 1

    # Isolation stricte entre utilisateurs
    assert client.get("/api/v1/tasks", headers=user_b_headers).json() == []
    assert client.get(f"/api/v1/tasks/{task_id}", headers=user_b_headers).status_code == 404
    assert (
        client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"title": "Piratage"},
            headers=user_b_headers,
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/tasks/{task_id}", headers=user_b_headers).status_code == 404

    # L'utilisateur A peut supprimer sa propre tâche
    assert client.delete(f"/api/v1/tasks/{task_id}", headers=user_a_headers).status_code == 204
    assert client.get(f"/api/v1/tasks/{task_id}", headers=user_a_headers).status_code == 404
