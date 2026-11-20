from fastapi.testclient import TestClient


def test_sessions_lifecycle_finish_validation_and_cancellation(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    # Démarrer une séance en direct
    started = client.post(
        "/api/v1/sessions",
        json={
            "title": "Atelier FastAPI",
            "category": "Apprentissage",
            "started_at": "2026-11-19T10:00:00Z",
        },
        headers=user_a_headers,
    )
    assert started.status_code == 201
    session_id = started.json()["id"]
    assert started.json()["status"] == "in_progress"
    assert started.json()["ended_at"] is None

    # Clôture refusée sans résultat (SESSION-02)
    bad_finish = client.patch(
        f"/api/v1/sessions/{session_id}/finish",
        json={"result": " "},
        headers=user_a_headers,
    )
    assert bad_finish.status_code == 422

    # Clôture valide avec durée calculée (SESSION-01)
    finished = client.patch(
        f"/api/v1/sessions/{session_id}/finish",
        json={
            "result": "Routes /tasks et /schedule implémentées.",
            "ended_at": "2026-11-19T11:15:00Z",
        },
        headers=user_a_headers,
    )
    assert finished.status_code == 200
    assert finished.json()["status"] == "completed"
    assert finished.json()["duration_minutes"] == 75

    # Clôturer une deuxième fois -> 409 CONFLICT
    second_finish = client.patch(
        f"/api/v1/sessions/{session_id}/finish",
        json={"result": "Encore"},
        headers=user_a_headers,
    )
    assert second_finish.status_code == 409

    # Séance passée rejetée si fin <= début
    bad_manual = client.post(
        "/api/v1/sessions",
        json={
            "title": "TP invalide",
            "category": "Cours",
            "started_at": "2026-11-19T14:00:00Z",
            "ended_at": "2026-11-19T13:00:00Z",
            "result": "Rien",
        },
        headers=user_a_headers,
    )
    assert bad_manual.status_code == 422

    # Séance démarrée puis annulée -> exclue du résumé achevé (SESSION-03)
    to_cancel = client.post(
        "/api/v1/sessions",
        json={
            "title": "Séance annulée",
            "category": "Révision",
            "started_at": "2026-11-19T15:00:00Z",
        },
        headers=user_a_headers,
    ).json()
    cancelled = client.patch(
        f"/api/v1/sessions/{to_cancel['id']}",
        json={"status": "cancelled"},
        headers=user_a_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    dash = client.get("/api/v1/dashboard", headers=user_a_headers).json()
    assert dash["session_summary"] == {
        "completed_count": 1,
        "total_completed_minutes": 75,
        "in_progress_count": 0,
        "cancelled_count": 1,
    }

    # Isolation stricte utilisateur B
    assert client.get("/api/v1/sessions", headers=user_b_headers).json() == []
    assert (
        client.patch(
            f"/api/v1/sessions/{session_id}/finish",
            json={"result": "Vol"},
            headers=user_b_headers,
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/sessions/{session_id}", headers=user_b_headers).status_code == 404
