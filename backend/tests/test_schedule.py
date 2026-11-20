from fastapi.testclient import TestClient


def test_schedule_validation_conflicts_and_duplication_across_timezones(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    # SCHED-01 : rejette ends_at <= starts_at
    bad_range = client.post(
        "/api/v1/schedule",
        json={
            "title": "Créneau invalide",
            "starts_at": "2026-11-19T14:00:00Z",
            "ends_at": "2026-11-19T13:00:00Z",
        },
        headers=user_a_headers,
    )
    assert bad_range.status_code == 422

    # Rejette datetime naïf sans fuseau horaire
    naive_res = client.post(
        "/api/v1/schedule",
        json={
            "title": "Créneau naïf",
            "starts_at": "2026-11-19T09:00:00",
            "ends_at": "2026-11-19T11:00:00",
        },
        headers=user_a_headers,
    )
    assert naive_res.status_code == 422

    # Créneau 1 : 09:00 - 11:00 UTC
    ev1 = client.post(
        "/api/v1/schedule",
        json={
            "title": "Cours Python",
            "type": "course",
            "starts_at": "2026-11-19T09:00:00Z",
            "ends_at": "2026-11-19T11:00:00Z",
        },
        headers=user_a_headers,
    )
    assert ev1.status_code == 201
    ev1_data = ev1.json()
    assert ev1_data["duration_minutes"] == 120
    assert ev1_data["has_conflict"] is False

    # Créneau consécutif : 11:00 - 13:00 UTC -> PAS de conflit (SCHED-03)
    ev2 = client.post(
        "/api/v1/schedule",
        json={
            "title": "TP SQL",
            "type": "learning",
            "starts_at": "2026-11-19T11:00:00Z",
            "ends_at": "2026-11-19T13:00:00Z",
        },
        headers=user_a_headers,
    )
    assert ev2.status_code == 201
    assert ev2.json()["has_conflict"] is False

    # Créneau chevauchant : 10:00 - 12:00 UTC -> conflit signalé sans bloquer l'enregistrement (SCHED-03)
    ev3 = client.post(
        "/api/v1/schedule",
        json={
            "title": "Réunion projet",
            "type": "project",
            "starts_at": "2026-11-19T10:00:00Z",
            "ends_at": "2026-11-19T12:00:00Z",
        },
        headers=user_a_headers,
    )
    assert ev3.status_code == 201
    ev3_data = ev3.json()
    assert ev3_data["has_conflict"] is True
    assert set(ev3_data["conflicting_event_ids"]) == {ev1_data["id"], ev2.json()["id"]}

    # Passage du profil en Europe/Paris et duplication de la semaine (SCHED-02, SCHED-04)
    assert (
        client.patch(
            "/api/v1/profile",
            json={"timezone": "Europe/Paris"},
            headers=user_a_headers,
        ).status_code
        == 200
    )

    dup = client.post(
        "/api/v1/schedule/duplicate-week",
        json={"source_week_start": "2026-11-16"},
        headers=user_a_headers,
    )
    assert dup.status_code == 201
    assert dup.json()["created_count"] == 3
    assert dup.json()["skipped_count"] == 0

    # Seconde duplication immédiate -> 3 doublons ignorés
    dup_again = client.post(
        "/api/v1/schedule/duplicate-week",
        json={"source_week_start": "2026-11-16"},
        headers=user_a_headers,
    )
    assert dup_again.status_code == 201
    assert dup_again.json()["created_count"] == 0
    assert dup_again.json()["skipped_count"] == 3

    # Isolation stricte utilisateur B
    assert client.get("/api/v1/schedule", headers=user_b_headers).json() == []
    assert client.delete(f"/api/v1/schedule/{ev1_data['id']}", headers=user_b_headers).status_code == 404
