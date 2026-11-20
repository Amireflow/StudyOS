from fastapi.testclient import TestClient


def test_skills_scale_assessed_timestamp_evidence_and_isolation(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    # Hors échelle 0..5 -> 422
    bad_skill = client.post(
        "/api/v1/skills",
        json={"name": "Rust", "domain": "Systèmes", "current_level": 6},
        headers=user_a_headers,
    )
    assert bad_skill.status_code == 422

    # Niveau initial 0 -> last_assessed_at None
    s0 = client.post(
        "/api/v1/skills",
        json={"name": "TypeScript", "domain": "Frontend", "current_level": 0, "target_level": 4},
        headers=user_a_headers,
    )
    assert s0.status_code == 201
    skill_id = s0.json()["id"]
    assert s0.json()["last_assessed_at"] is None

    # Mise à jour vers niveau 3 -> last_assessed_at renseigné
    s3 = client.patch(
        f"/api/v1/skills/{skill_id}",
        json={"current_level": 3},
        headers=user_a_headers,
    )
    assert s3.status_code == 200
    assert s3.json()["current_level"] == 3
    assert s3.json()["last_assessed_at"] is not None

    # URL de preuve non http(s) -> 422
    bad_ev = client.post(
        f"/api/v1/skills/{skill_id}/evidence",
        json={
            "type": "code",
            "description": "Dépôt GitHub typé",
            "reference_url": "ftp://example.com/repo",
        },
        headers=user_a_headers,
    )
    assert bad_ev.status_code == 422

    # Ajout preuve valide (SKILL-02)
    ev = client.post(
        f"/api/v1/skills/{skill_id}/evidence",
        json={
            "type": "code",
            "description": "Module TasksPage avec React Hook Form + Zod",
            "reference_url": "https://github.com/amireflow/study-os",
            "result": "34 tests Vitest passants",
        },
        headers=user_a_headers,
    )
    assert ev.status_code == 201
    ev_id = ev.json()["id"]

    # Mise à jour preuve
    ev_patch = client.patch(
        f"/api/v1/skills/{skill_id}/evidence/{ev_id}",
        json={"result": "Build strict OK"},
        headers=user_a_headers,
    )
    assert ev_patch.status_code == 200
    assert ev_patch.json()["result"] == "Build strict OK"

    # Filtre par domaine
    filtered = client.get("/api/v1/skills?domain=frontend", headers=user_a_headers)
    assert len(filtered.json()) == 1

    # Lier une séance puis vérifier l'isolation utilisateur B
    session = client.post(
        "/api/v1/sessions",
        json={"title": "Refactor TS", "category": "Code", "skill_id": skill_id},
        headers=user_a_headers,
    )
    assert session.status_code == 201
    session_id = session.json()["id"]

    assert client.get("/api/v1/skills", headers=user_b_headers).json() == []
    assert client.get(f"/api/v1/skills/{skill_id}/evidence", headers=user_b_headers).status_code == 404
    assert (
        client.post(
            f"/api/v1/skills/{skill_id}/evidence",
            json={"type": "exercise", "description": "Fausse preuve"},
            headers=user_b_headers,
        ).status_code
        == 404
    )

    # Remise à 0 efface last_assessed_at
    reset = client.patch(
        f"/api/v1/skills/{skill_id}",
        json={"current_level": 0},
        headers=user_a_headers,
    )
    assert reset.status_code == 200
    assert reset.json()["last_assessed_at"] is None

    # Suppression compétence -> détache séance et supprime preuves
    assert client.delete(f"/api/v1/skills/{skill_id}", headers=user_a_headers).status_code == 204
    assert client.get("/api/v1/skills/evidence", headers=user_a_headers).json() == []
    sessions_after = client.get("/api/v1/sessions", headers=user_a_headers).json()
    assert next(item for item in sessions_after if item["id"] == session_id)["skill_id"] is None
