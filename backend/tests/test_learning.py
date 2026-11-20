from fastapi.testclient import TestClient


def test_learning_crud_links_no_auto_skill_validation_and_isolation(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    # Créer une compétence au niveau 0 pour vérifier LEARN-03 (aucune validation automatique)
    skill = client.post(
        "/api/v1/skills",
        json={"name": "FastAPI", "domain": "Backend", "current_level": 0, "target_level": 3},
        headers=user_a_headers,
    ).json()

    # Parcours -> Module -> Leçon
    path_res = client.post(
        "/api/v1/learning/paths",
        json={
            "title": "Architecture API Python",
            "goal": "Construire des services REST testés",
            "status": "active",
        },
        headers=user_a_headers,
    )
    assert path_res.status_code == 201
    path_id = path_res.json()["id"]

    mod_res = client.post(
        "/api/v1/learning/modules",
        json={"path_id": path_id, "title": "Modélisation SQLAlchemy", "position": 1, "status": "active"},
        headers=user_a_headers,
    )
    assert mod_res.status_code == 201
    module_id = mod_res.json()["id"]

    # URL dangereuse rejetée (422)
    bad_lesson = client.post(
        "/api/v1/learning/lessons",
        json={
            "module_id": module_id,
            "title": "Injection URL",
            "resource_url": "javascript:alert(1)",
        },
        headers=user_a_headers,
    )
    assert bad_lesson.status_code == 422

    lesson_res = client.post(
        "/api/v1/learning/lessons",
        json={
            "module_id": module_id,
            "title": "Relations et migrations Alembic",
            "resource_url": "https://alembic.sqlalchemy.org/en/latest/",
            "position": 1,
        },
        headers=user_a_headers,
    )
    assert lesson_res.status_code == 201
    lesson_id = lesson_res.json()["id"]

    # Lier tâche et séance au module / à la leçon (LEARN-04)
    task = client.post(
        "/api/v1/tasks",
        json={"title": "Implémenter les modèles", "module_id": module_id},
        headers=user_a_headers,
    )
    assert task.status_code == 201
    task_id = task.json()["id"]
    assert task.json()["module_id"] == module_id

    session = client.post(
        "/api/v1/sessions",
        json={
            "title": "Lecture doc Alembic",
            "category": "Apprentissage",
            "module_id": module_id,
            "lesson_id": lesson_id,
        },
        headers=user_a_headers,
    )
    assert session.status_code == 201
    session_id = session.json()["id"]
    assert session.json()["lesson_id"] == lesson_id

    # Clôturer la leçon -> compétence reste à 0 et sans last_assessed_at (LEARN-03)
    done_lesson = client.patch(
        f"/api/v1/learning/lessons/{lesson_id}",
        json={"status": "completed"},
        headers=user_a_headers,
    )
    assert done_lesson.status_code == 200
    assert done_lesson.json()["status"] == "completed"

    skill_after = client.get(f"/api/v1/skills/{skill['id']}", headers=user_a_headers).json()
    assert skill_after["current_level"] == 0
    assert skill_after["last_assessed_at"] is None

    # Isolation stricte utilisateur B
    assert client.get("/api/v1/learning/overview", headers=user_b_headers).json() == {
        "paths": [],
        "modules": [],
        "lessons": [],
    }
    assert (
        client.patch(
            f"/api/v1/learning/lessons/{lesson_id}",
            json={"title": "Piratage"},
            headers=user_b_headers,
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/learning/modules",
            json={"path_id": path_id, "title": "Module B"},
            headers=user_b_headers,
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/tasks",
            json={"title": "Tâche B liée", "module_id": module_id},
            headers=user_b_headers,
        ).status_code
        == 404
    )

    # Suppression du parcours -> cascade modules/leçons et détachement tâche/séance
    del_path = client.delete(f"/api/v1/learning/paths/{path_id}", headers=user_a_headers)
    assert del_path.status_code == 204
    assert client.get("/api/v1/learning/overview", headers=user_a_headers).json()["modules"] == []
    assert client.get(f"/api/v1/tasks/{task_id}", headers=user_a_headers).json()["module_id"] is None
    sess_list = client.get("/api/v1/sessions", headers=user_a_headers).json()
    detached_session = next(item for item in sess_list if item["id"] == session_id)
    assert detached_session["module_id"] is None
    assert detached_session["lesson_id"] is None
