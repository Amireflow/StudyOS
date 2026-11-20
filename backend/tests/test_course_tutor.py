from fastapi.testclient import TestClient


def test_course_lesson_tutor_progressive_flow(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    course = client.post(
        "/api/v1/courses",
        json={"subject": "Python", "language": "fr", "total_levels": 3},
        headers=user_a_headers,
    ).json()
    course_id = course["id"]
    lvl1 = course["levels"][0]
    lesson = lvl1["lessons"][0]
    assert lesson["tutor_messages"] == []
    assert lesson["current_step_index"] == 0
    # Les métadonnées internes ne fuient jamais dans les exemples de code
    assert all("_meta_kind" not in ex for ex in lesson["code_examples"])

    # 1. Progression étape par étape persistée sans valider le chapitre
    step = client.patch(
        f"/api/v1/courses/{course_id}/lessons/{lesson['id']}",
        json={"current_step_index": 2},
        headers=user_a_headers,
    )
    assert step.status_code == 200
    assert step.json()["current_step_index"] == 2
    assert step.json()["status"] == "in_progress"

    # 2. Question rapide au tuteur (repli pédagogique local, sans fournisseur IA)
    ask = client.post(
        f"/api/v1/courses/{course_id}/lessons/{lesson['id']}/ask",
        json={
            "message": "Explique-moi plus simplement",
            "quick_action": "simplify",
            "step_index": 2,
            "step_title": "Exemple",
        },
        headers=user_a_headers,
    )
    assert ask.status_code == 200
    data = ask.json()
    assert data["user_message"]["role"] == "user"
    assert data["assistant_message"]["role"] == "assistant"
    assert len(data["assistant_message"]["content"]) > 20
    assert len(data["assistant_message"]["follow_up_prompts"]) >= 1
    assert len(data["lesson"]["tutor_messages"]) == 2
    assert data["lesson"]["current_step_index"] == 2

    # 3. Historique persisté dans le détail du cours, étape conservée
    detail = client.get(f"/api/v1/courses/{course_id}", headers=user_a_headers).json()
    persisted = next(l for l in detail["levels"][0]["lessons"] if l["id"] == lesson["id"])
    assert len(persisted["tutor_messages"]) == 2
    assert persisted["current_step_index"] == 2
    assert all("_meta_kind" not in ex for ex in persisted["code_examples"])

    # 4. Le verrou pédagogique reste intact : poser des questions ne termine pas le chapitre
    assert persisted["status"] == "in_progress"
    assert detail["levels"][0]["can_validate"] is False

    # 5. Isolation utilisateur et niveau verrouillé
    assert (
        client.post(
            f"/api/v1/courses/{course_id}/lessons/{lesson['id']}/ask",
            json={"message": "Bonjour"},
            headers=user_b_headers,
        ).status_code
        == 404
    )
    empty = client.post(
        f"/api/v1/courses/{course_id}/lessons/{lesson['id']}/ask",
        json={"message": "   "},
        headers=user_a_headers,
    )
    assert empty.status_code == 422

    # 6. Marquer lu reste compatible avec l'ancien contrat
    done = client.patch(
        f"/api/v1/courses/{course_id}/lessons/{lesson['id']}",
        json={"status": "completed"},
        headers=user_a_headers,
    )
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert len(done.json()["tutor_messages"]) == 2
