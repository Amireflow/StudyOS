from fastapi.testclient import TestClient


def test_course_preview_creation_and_level_lock(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    # 1. Prévisualisation complète sans écriture en base
    preview = client.post(
        "/api/v1/courses/preview",
        json={"subject": "Python", "language": "fr", "total_levels": 3},
        headers=user_a_headers,
    )
    assert preview.status_code == 200
    pv = preview.json()
    assert pv["subject"] == "Python"
    assert len(pv["levels_roadmap"]) == 3
    assert len(pv["first_level_lessons"]) == 4
    assert "```python" in pv["first_level_lessons"][0]["content_markdown"]
    assert len(pv["first_level_resources"]) >= 3
    assert pv["first_level_project_title"]
    assert client.get("/api/v1/courses", headers=user_a_headers).json() == []

    # 2. Tentative d'injection de current_level lors de la création -> 422
    bad_create = client.post(
        "/api/v1/courses",
        json={"subject": "Python", "current_level": 3},
        headers=user_a_headers,
    )
    assert bad_create.status_code == 422

    # 3. Création légitime au niveau 1
    created = client.post(
        "/api/v1/courses",
        json={"subject": "Python", "language": "fr", "total_levels": 3},
        headers=user_a_headers,
    )
    assert created.status_code == 201
    course = created.json()
    course_id = course["id"]
    assert course["current_level"] == 1
    assert course["status"] == "active"
    assert course["levels"][0]["status"] == "unlocked"
    assert course["levels"][0]["content_generated"] is True
    assert course["levels"][1]["status"] == "locked"
    assert course["levels"][1]["content_generated"] is False
    assert course["levels"][2]["status"] == "locked"

    # 4. Tentative d'injection current_level via PATCH -> 422
    bad_patch = client.patch(
        f"/api/v1/courses/{course_id}",
        json={"current_level": 2},
        headers=user_a_headers,
    )
    assert bad_patch.status_code == 422

    # 5. Isolation stricte vis-à-vis de l'utilisateur B
    assert client.get(f"/api/v1/courses/{course_id}", headers=user_b_headers).status_code == 404
    assert (
        client.patch(
            f"/api/v1/courses/{course_id}",
            json={"title": "Piraté"},
            headers=user_b_headers,
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/courses/{course_id}", headers=user_b_headers).status_code == 404
    lvl1_id = course["levels"][0]["id"]
    assert (
        client.post(
            f"/api/v1/courses/{course_id}/levels/{lvl1_id}/submissions",
            json={
                "submission_kind": "project",
                "answer_text": "Tentative utilisateur externe avec code valide",
            },
            headers=user_b_headers,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/courses/{course_id}/levels/{lvl1_id}/validate",
            headers=user_b_headers,
        ).status_code
        == 404
    )


def test_course_pedagogical_lock_grading_and_level_unlock(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    course = client.post(
        "/api/v1/courses",
        json={"subject": "Python", "language": "fr", "total_levels": 3, "link_skill": True},
        headers=user_a_headers,
    ).json()
    course_id = course["id"]
    lvl1 = course["levels"][0]
    lvl2 = course["levels"][1]
    lvl3 = course["levels"][2]

    # 1. Terminer toutes les leçons du Niveau 1 ne débloque PAS le niveau suivant
    for lesson in lvl1["lessons"]:
        res = client.patch(
            f"/api/v1/courses/{course_id}/lessons/{lesson['id']}",
            json={"status": "completed"},
            headers=user_a_headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "completed"

    premature_validate = client.post(
        f"/api/v1/courses/{course_id}/levels/{lvl1['id']}/validate",
        headers=user_a_headers,
    )
    assert premature_validate.status_code == 422
    assert premature_validate.json()["error"]["code"] == "PROJECT_VALIDATION_REQUIRED"

    # 2. Soumettre une auto-déclaration creuse -> échec corrigé
    bad_sub = client.post(
        f"/api/v1/courses/{course_id}/levels/{lvl1['id']}/submissions",
        json={
            "submission_kind": "project",
            "answer_text": "J'ai bien compris Python et j'ai fini",
        },
        headers=user_a_headers,
    )
    assert bad_sub.status_code == 201
    bad_data = bad_sub.json()
    assert bad_data["passed"] is False
    assert bad_data["score"] < 70
    assert len(bad_data["improvements"]) > 0

    # 3. Soumettre sur le Niveau 3 encore verrouillé -> 409 LEVEL_LOCKED
    locked_sub = client.post(
        f"/api/v1/courses/{course_id}/levels/{lvl3['id']}/submissions",
        json={
            "submission_kind": "project",
            "answer_text": "Soumission anticipée sur niveau verrouillé avec explication détaillée.",
        },
        headers=user_a_headers,
    )
    assert locked_sub.status_code == 409
    assert locked_sub.json()["error"]["code"] == "LEVEL_LOCKED"

    # 4. Soumettre un vrai projet Python complet (explication causale + code structuré + tests)
    good_sub = client.post(
        f"/api/v1/courses/{course_id}/levels/{lvl1['id']}/submissions",
        json={
            "submission_kind": "project",
            "title": lvl1["project_title"],
            "answer_text": (
                "J'ai structuré un dictionnaire store par matière parce que l'accès par clé est en O(1), "
                "validé les notes entre 0 et 20 avec ValueError pour éviter les entrées invalides et vérifié "
                "tous les cas limites dont une liste vide grâce à 4 assertions pytest."
            ),
            "submitted_code": (
                "def add_grade(store: dict[str, list[float]], subject: str, grade: float) -> None:\n"
                "    if not (0 <= grade <= 20):\n"
                "        raise ValueError('Note hors bornes [0, 20]')\n"
                "    store.setdefault(subject, []).append(grade)\n\n"
                "def compute_report(store: dict[str, list[float]]) -> dict:\n"
                "    return {k: round(sum(v)/len(v), 2) for k, v in store.items() if v}\n\n"
                "data = {}\n"
                "add_grade(data, 'Python', 18)\n"
                "assert compute_report(data)['Python'] == 18.0\n"
            ),
        },
        headers=user_a_headers,
    )
    assert good_sub.status_code == 201
    good_data = good_sub.json()
    assert good_data["passed"] is True
    assert good_data["score"] >= 70
    assert len(good_data["criteria_results"]) == 4
    assert "### Correction" in good_data["feedback_markdown"]

    # 5. Valider le Niveau 1 -> débloque et génère automatiquement le Niveau 2
    validated = client.post(
        f"/api/v1/courses/{course_id}/levels/{lvl1['id']}/validate",
        headers=user_a_headers,
    )
    assert validated.status_code == 200
    detail = validated.json()
    assert detail["current_level"] == 2
    assert detail["levels"][0]["status"] == "validated"
    assert detail["levels"][1]["id"] == lvl2["id"]
    assert detail["levels"][1]["status"] == "unlocked"
    assert detail["levels"][1]["content_generated"] is True
    assert len(detail["levels"][1]["lessons"]) == 4
    assert detail["levels"][1]["project_title"]

    # 6. La compétence liée a reçu une preuve concrète MAIS son current_level reste à 0 (verrou de compétence préservé)
    skills = client.get("/api/v1/skills", headers=user_a_headers).json()
    py_skill = next(s for s in skills if s["id"] == detail["skill_id"])
    assert py_skill["current_level"] == 0
    ev = client.get(f"/api/v1/skills/{py_skill['id']}/evidence", headers=user_a_headers).json()
    assert len(ev) == 1
    assert ev[0]["type"] == "project"


def test_course_resources_crud_and_url_validation(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    course = client.post(
        "/api/v1/courses",
        json={"subject": "TypeScript", "language": "fr", "total_levels": 2},
        headers=user_a_headers,
    ).json()
    course_id = course["id"]

    # URL dangereuse rejetée (422)
    bad_res = client.post(
        f"/api/v1/courses/{course_id}/resources",
        json={
            "title": "Lien XSS",
            "url": "javascript:alert(1)",
            "resource_type": "article",
            "language": "fr",
        },
        headers=user_a_headers,
    )
    assert bad_res.status_code == 422

    # URL valide acceptée puis supprimée
    good_res = client.post(
        f"/api/v1/courses/{course_id}/resources",
        json={
            "title": "Documentation officielle TypeScript Deep Dive",
            "url": "https://www.typescriptlang.org/docs/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "TypeScript.org",
        },
        headers=user_a_headers,
    )
    assert good_res.status_code == 201
    res_id = good_res.json()["id"]

    deleted = client.delete(
        f"/api/v1/courses/{course_id}/resources/{res_id}",
        headers=user_a_headers,
    )
    assert deleted.status_code == 204


def test_ai_copilot_create_course_proposal_workflow(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    conv = client.post("/api/v1/ai/conversations", json={}, headers=user_a_headers).json()
    turn = client.post(
        f"/api/v1/ai/conversations/{conv['id']}/messages",
        json={"content": "Crée un cours complet pour apprendre Python"},
        headers=user_a_headers,
    )
    assert turn.status_code == 201
    turn_data = turn.json()
    assert len(turn_data["proposals"]) == 1
    prop = turn_data["proposals"][0]
    assert prop["action_type"] == "create_course"
    assert prop["status"] == "pending"

    # Aucun cours créé tant que la proposition n'est pas validée
    assert client.get("/api/v1/courses", headers=user_a_headers).json() == []

    # Accepter la proposition -> crée le cours complet au Niveau 1
    acc = client.post(f"/api/v1/ai/proposals/{prop['id']}/accept", headers=user_a_headers)
    assert acc.status_code == 200
    assert acc.json()["status"] == "executed"
    assert acc.json()["execution_result"]["entity"] == "course"
    assert acc.json()["execution_result"]["current_level"] == 1

    courses = client.get("/api/v1/courses", headers=user_a_headers).json()
    assert len(courses) == 1
    assert courses[0]["subject"] == "Python"
    assert courses[0]["current_level"] == 1
