from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.deps import get_utc_now


def test_dashboard_aggregation_and_timezone_day_boundary(
    app: FastAPI,
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    # Horloge figée au 19 nov. 2026 à 23:45 UTC :
    # - À Africa/Dakar (UTC+0) : nous sommes le 19 nov. (23:45)
    # - À Europe/Paris (UTC+1 en nov.) : nous sommes déjà le 20 nov. (00:45)
    app.dependency_overrides[get_utc_now] = lambda: datetime(2026, 11, 19, 23, 45, tzinfo=timezone.utc)

    # Événement à 22:30 UTC (19 nov à Dakar ET 19 nov 23:30 à Paris -> hier par rapport au 20 nov 00:45 Paris)
    ev_earlier = client.post(
        "/api/v1/schedule",
        json={
            "title": "Session 22h30 UTC",
            "type": "learning",
            "starts_at": "2026-11-19T22:30:00Z",
            "ends_at": "2026-11-19T22:50:00Z",
        },
        headers=user_a_headers,
    )
    assert ev_earlier.status_code == 201

    # Événement tardif le 19 nov. à 23:30 UTC (le 19 à Dakar, mais déjà le 20 à 00:30 à Paris)
    ev = client.post(
        "/api/v1/schedule",
        json={
            "title": "Révision nocturne",
            "type": "learning",
            "starts_at": "2026-11-19T23:30:00Z",
            "ends_at": "2026-11-19T23:55:00Z",
        },
        headers=user_a_headers,
    )
    assert ev.status_code == 201

    task = client.post(
        "/api/v1/tasks",
        json={"title": "Finaliser FastAPI", "priority": "critical"},
        headers=user_a_headers,
    ).json()
    client.patch(
        "/api/v1/profile",
        json={"active_priority_task_id": task["id"]},
        headers=user_a_headers,
    )

    client.post(
        "/api/v1/sessions",
        json={
            "title": "Session API",
            "category": "Projet",
            "started_at": "2026-11-19T20:00:00Z",
            "ended_at": "2026-11-19T21:00:00Z",
            "result": "Endpoints opérationnels.",
        },
        headers=user_a_headers,
    )

    # En Africa/Dakar : les deux créneaux appartiennent au 19 nov.
    dash_dakar = client.get("/api/v1/dashboard", headers=user_a_headers).json()
    assert dash_dakar["timezone"] == "Africa/Dakar"
    assert dash_dakar["active_priority"]["title"] == "Finaliser FastAPI"
    assert dash_dakar["active_priority"]["task_id"] == task["id"]
    assert [e["title"] for e in dash_dakar["today_events"]] == [
        "Session 22h30 UTC",
        "Révision nocturne",
    ]
    assert len(dash_dakar["priority_tasks"]) == 1
    assert dash_dakar["session_summary"]["completed_count"] == 1
    assert dash_dakar["session_summary"]["total_completed_minutes"] == 60

    client.patch(
        "/api/v1/profile",
        json={"timezone": "Europe/Paris"},
        headers=user_a_headers,
    )
    dash_paris = client.get("/api/v1/dashboard", headers=user_a_headers).json()
    assert dash_paris["timezone"] == "Europe/Paris"
    # À 23:45 UTC (20 nov 00:45 Paris), seul "Révision nocturne" (20 nov 00:30 Paris) est aujourd'hui ;
    # "Session 22h30 UTC" (19 nov 23:30 Paris) était hier.
    assert [e["title"] for e in dash_paris["today_events"]] == ["Révision nocturne"]
