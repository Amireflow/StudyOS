from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.deps import get_utc_now


def test_projects_max_three_active_pause_frees_slot_and_clears_priority(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    created_ids: list[str] = []
    for idx in range(1, 4):
        res = client.post(
            "/api/v1/projects",
            json={
                "name": f"Projet actif {idx}",
                "goal": f"Livrer jalon {idx}",
                "status": "active",
                "next_action": f"Action concrète {idx}",
            },
            headers=user_a_headers,
        )
        assert res.status_code == 201
        created_ids.append(res.json()["id"])

    # Projet planifié autorisé malgré 3 actifs
    planned = client.post(
        "/api/v1/projects",
        json={
            "name": "Projet futur",
            "goal": "Préparer la suite",
            "status": "planned",
            "next_action": "Définir le scope final",
        },
        headers=user_a_headers,
    )
    assert planned.status_code == 201
    planned_id = planned.json()["id"]

    # 4e projet actif interdit (création et passage en actif)
    fourth = client.post(
        "/api/v1/projects",
        json={
            "name": "Projet en trop",
            "goal": "Dispersion",
            "status": "active",
            "next_action": "Action bloquée",
        },
        headers=user_a_headers,
    )
    assert fourth.status_code == 409
    assert fourth.json()["error"]["code"] == "MAX_ACTIVE_PROJECTS_REACHED"

    activate_planned = client.patch(
        f"/api/v1/projects/{planned_id}",
        json={"status": "active"},
        headers=user_a_headers,
    )
    assert activate_planned.status_code == 409
    assert activate_planned.json()["error"]["code"] == "MAX_ACTIVE_PROJECTS_REACHED"

    # Définir le projet 1 comme priorité principale puis le mettre en pause
    prio_res = client.patch(
        "/api/v1/profile",
        json={"active_priority_project_id": created_ids[0]},
        headers=user_a_headers,
    )
    assert prio_res.status_code == 200
    assert prio_res.json()["active_priority_project_id"] == created_ids[0]

    paused_res = client.patch(
        f"/api/v1/projects/{created_ids[0]}",
        json={"status": "paused"},
        headers=user_a_headers,
    )
    assert paused_res.status_code == 200
    assert paused_res.json()["status"] == "paused"

    # La priorité obsolète est automatiquement nettoyée
    profile_after = client.get("/api/v1/profile", headers=user_a_headers).json()
    assert profile_after["active_priority_project_id"] is None
    assert profile_after["active_priority_title"] is None

    # La mise en pause a libéré un créneau actif
    activated = client.patch(
        f"/api/v1/projects/{planned_id}",
        json={"status": "active"},
        headers=user_a_headers,
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"


def test_tasks_max_three_critical_overdue_first_due_filters_and_priority_cleanup(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    now_local = datetime.now(timezone.utc)
    today_iso = now_local.isoformat()
    future_iso = datetime(2030, 1, 15, 12, 0, tzinfo=timezone.utc).isoformat()

    c1 = client.post(
        "/api/v1/tasks",
        json={"title": "Critique future", "priority": "critical", "due_at": future_iso},
        headers=user_a_headers,
    )
    assert c1.status_code == 201
    c2 = client.post(
        "/api/v1/tasks",
        json={
            "title": "Critique en retard",
            "priority": "critical",
            "due_at": "2020-01-01T10:00:00Z",
        },
        headers=user_a_headers,
    )
    assert c2.status_code == 201
    c3 = client.post(
        "/api/v1/tasks",
        json={"title": "Critique du jour", "priority": "critical", "due_at": today_iso},
        headers=user_a_headers,
    )
    assert c3.status_code == 201

    # 4e tâche critique active -> 409
    c4 = client.post(
        "/api/v1/tasks",
        json={"title": "Critique de trop", "priority": "critical"},
        headers=user_a_headers,
    )
    assert c4.status_code == 409
    assert c4.json()["error"]["code"] == "MAX_CRITICAL_TASKS_REACHED"

    # Promotion d'une tâche existante en critique -> 409
    high_task = client.post(
        "/api/v1/tasks",
        json={"title": "Tâche haute", "priority": "high", "due_at": today_iso},
        headers=user_a_headers,
    )
    assert high_task.status_code == 201
    promote = client.patch(
        f"/api/v1/tasks/{high_task.json()['id']}",
        json={"priority": "critical"},
        headers=user_a_headers,
    )
    assert promote.status_code == 409
    assert promote.json()["error"]["code"] == "MAX_CRITICAL_TASKS_REACHED"

    # Le tri place les tâches en retard en premier
    listed = client.get("/api/v1/tasks", headers=user_a_headers).json()
    assert listed[0]["id"] == c2.json()["id"]

    # Définir c3 comme priorité principale puis la terminer
    assert (
        client.patch(
            "/api/v1/profile",
            json={"active_priority_task_id": c3.json()["id"]},
            headers=user_a_headers,
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/tasks/{c3.json()['id']}",
            json={"status": "done"},
            headers=user_a_headers,
        ).status_code
        == 200
    )

    profile_after = client.get("/api/v1/profile", headers=user_a_headers).json()
    assert profile_after["active_priority_task_id"] is None
    assert profile_after["active_priority_title"] is None

    # Filtres due=today et due=upcoming excluent les tâches terminées/inactives
    today_ids = {t["id"] for t in client.get("/api/v1/tasks", params={"due": "today"}, headers=user_a_headers).json()}
    assert c3.json()["id"] not in today_ids
    assert high_task.json()["id"] in today_ids

    done_future = client.post(
        "/api/v1/tasks",
        json={"title": "Déjà faite future", "status": "done", "due_at": future_iso},
        headers=user_a_headers,
    )
    assert done_future.status_code == 201
    upcoming_ids = {
        t["id"] for t in client.get("/api/v1/tasks", params={"due": "upcoming"}, headers=user_a_headers).json()
    }
    assert done_future.json()["id"] not in upcoming_ids
    assert c1.json()["id"] in upcoming_ids

    # Un emplacement critique est maintenant libéré
    promote_ok = client.patch(
        f"/api/v1/tasks/{high_task.json()['id']}",
        json={"priority": "critical"},
        headers=user_a_headers,
    )
    assert promote_ok.status_code == 200


def test_profile_rejects_inactive_priority_targets(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    paused_project = client.post(
        "/api/v1/projects",
        json={"name": "Projet en pause", "goal": "Tester", "status": "paused"},
        headers=user_a_headers,
    ).json()
    done_task = client.post(
        "/api/v1/tasks",
        json={"title": "Tâche terminée", "status": "done"},
        headers=user_a_headers,
    ).json()
    parked_task = client.post(
        "/api/v1/tasks",
        json={"title": "Idée parking", "status": "parked"},
        headers=user_a_headers,
    ).json()

    r1 = client.patch(
        "/api/v1/profile",
        json={"active_priority_project_id": paused_project["id"]},
        headers=user_a_headers,
    )
    assert r1.status_code == 409
    assert r1.json()["error"]["code"] == "INACTIVE_PRIORITY_TARGET"

    for tid in (done_task["id"], parked_task["id"]):
        r = client.patch(
            "/api/v1/profile",
            json={"active_priority_task_id": tid},
            headers=user_a_headers,
        )
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "INACTIVE_PRIORITY_TARGET"


def test_sessions_transitions_and_module_lesson_coherence(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    path = client.post(
        "/api/v1/learning/paths",
        json={"title": "Parcours Python", "goal": "Maîtriser les bases"},
        headers=user_a_headers,
    ).json()
    mod1 = client.post(
        "/api/v1/learning/modules",
        json={"path_id": path["id"], "title": "Module 1", "position": 1},
        headers=user_a_headers,
    ).json()
    mod2 = client.post(
        "/api/v1/learning/modules",
        json={"path_id": path["id"], "title": "Module 2", "position": 2},
        headers=user_a_headers,
    ).json()
    lesson1 = client.post(
        "/api/v1/learning/lessons",
        json={"module_id": mod1["id"], "title": "Variables"},
        headers=user_a_headers,
    ).json()

    # Incohérence leçon / module -> 422 LESSON_MODULE_MISMATCH
    mismatch = client.post(
        "/api/v1/sessions",
        json={
            "title": "Révision incohérente",
            "category": "Apprentissage",
            "module_id": mod2["id"],
            "lesson_id": lesson1["id"],
        },
        headers=user_a_headers,
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "LESSON_MODULE_MISMATCH"

    # Création valide puis clôture
    started = client.post(
        "/api/v1/sessions",
        json={
            "title": "Séance valide",
            "category": "Apprentissage",
            "started_at": "2026-11-19T10:00:00Z",
            "module_id": mod1["id"],
            "lesson_id": lesson1["id"],
        },
        headers=user_a_headers,
    )
    assert started.status_code == 201
    sid = started.json()["id"]

    finished = client.patch(
        f"/api/v1/sessions/{sid}/finish",
        json={"result": "Exercices terminés et compris.", "ended_at": "2026-11-19T10:45:00Z"},
        headers=user_a_headers,
    )
    assert finished.status_code == 200
    assert finished.json()["status"] == "completed"

    # Revenir completed -> in_progress interdit
    reopen = client.patch(
        f"/api/v1/sessions/{sid}",
        json={"status": "in_progress"},
        headers=user_a_headers,
    )
    assert reopen.status_code == 409
    assert reopen.json()["error"]["code"] == "SESSION_ALREADY_COMPLETED"

    # Effacer / raccourcir le résultat sur completed interdit
    clear_res = client.patch(
        f"/api/v1/sessions/{sid}",
        json={"result": "ok"},
        headers=user_a_headers,
    )
    assert clear_res.status_code == 422

    # Séance annulée -> completed directe interdite
    s2 = client.post(
        "/api/v1/sessions",
        json={"title": "Séance à annuler", "category": "Projet"},
        headers=user_a_headers,
    ).json()
    assert (
        client.patch(
            f"/api/v1/sessions/{s2['id']}",
            json={"status": "cancelled"},
            headers=user_a_headers,
        ).status_code
        == 200
    )
    cancelled_to_done = client.patch(
        f"/api/v1/sessions/{s2['id']}",
        json={"status": "completed"},
        headers=user_a_headers,
    )
    assert cancelled_to_done.status_code == 409


def test_dashboard_12_blocks_separation_and_honest_metrics(
    app: FastAPI,
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    app.dependency_overrides[get_utc_now] = lambda: datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)

    # Projets : 1 planned, 1 paused, 1 active
    client.post(
        "/api/v1/projects",
        json={"name": "Projet Planifié", "goal": "Plus tard", "status": "planned"},
        headers=user_a_headers,
    )
    client.post(
        "/api/v1/projects",
        json={"name": "Projet En Pause", "goal": "Attente", "status": "paused"},
        headers=user_a_headers,
    )
    client.post(
        "/api/v1/projects",
        json={
            "name": "Projet Actif Réel",
            "goal": "Livrer V1",
            "status": "active",
            "next_action": "Écrire tests E2E",
            "target_date": "2026-11-28T18:00:00Z",
        },
        headers=user_a_headers,
    )

    # Tâche critique en retard
    client.post(
        "/api/v1/tasks",
        json={
            "title": "Corriger anomalie SQL",
            "priority": "critical",
            "due_at": "2026-11-18T12:00:00Z",
        },
        headers=user_a_headers,
    )

    # Planning 120 min cette semaine vs 45 min de séance réelle (+ 1 séance annulée exclue)
    client.post(
        "/api/v1/schedule",
        json={
            "title": "Bloc prévu",
            "type": "learning",
            "starts_at": "2026-11-20T09:00:00Z",
            "ends_at": "2026-11-20T11:00:00Z",
        },
        headers=user_a_headers,
    )
    client.post(
        "/api/v1/sessions",
        json={
            "title": "Pratique réelle",
            "category": "Apprentissage",
            "started_at": "2026-11-20T08:00:00Z",
            "ended_at": "2026-11-20T08:45:00Z",
            "result": "Module consolidé avec 3 exercices.",
        },
        headers=user_a_headers,
    )
    cancelled = client.post(
        "/api/v1/sessions",
        json={"title": "Séance annulée", "category": "Projet"},
        headers=user_a_headers,
    ).json()
    client.patch(
        f"/api/v1/sessions/{cancelled['id']}",
        json={"status": "cancelled"},
        headers=user_a_headers,
    )

    # Cours + compétence
    course_res = client.post(
        "/api/v1/courses",
        json={"title": "Cours Python", "subject": "Python", "domain": "Informatique"},
        headers=user_a_headers,
    )
    assert course_res.status_code == 201
    client.post(
        "/api/v1/skills",
        json={"name": "Algorithmique", "domain": "CS", "current_level": 2, "target_level": 3},
        headers=user_a_headers,
    )

    dash = client.get("/api/v1/dashboard", headers=user_a_headers).json()
    assert dash["active_projects_count"] == 1
    assert dash["paused_projects_count"] == 1
    assert [p["name"] for p in dash["active_projects"]] == ["Projet Actif Réel"]
    assert len(dash["critical_tasks"]) == 1
    assert dash["critical_tasks"][0]["title"] == "Corriger anomalie SQL"
    assert dash["courses_progress"]["total_courses"] == 1
    assert dash["courses_progress"]["active_courses"] == 1
    assert dash["skills_progress"]["total_skills"] >= 1
    assert len(dash["today_schedule"]) == 1
    assert len(dash["upcoming_deadlines"]) == 2
    assert dash["weekly_study_metrics"]["real_study_minutes_7d"] == 45
    assert dash["weekly_study_metrics"]["planned_schedule_minutes_7d"] == 120
    assert dash["weekly_study_metrics"]["completed_sessions_7d"] == 1
    assert dash["consistency_streak"]["current_streak_days"] == 1
    assert dash["consistency_streak"]["active_days_7d"] == 1
    assert any(a["code"] == "OVERDUE_TASKS" for a in dash["blockers_and_alerts"])
    assert dash["next_recommended_action"] is not None
    assert dash["next_recommended_action"]["title"] == "Corriger anomalie SQL"
