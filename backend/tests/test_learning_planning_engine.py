from datetime import datetime, time, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient


def _next_weekday(anchor: datetime, target_weekday: int) -> datetime:
    delta = (target_weekday - anchor.weekday()) % 7
    if delta == 0:
        delta = 7
    return (anchor + timedelta(days=delta)).replace(hour=0, minute=0, second=0, microsecond=0)


def _overlaps(s1: str, e1: str, s2: datetime, e2: datetime) -> bool:
    dt1_s = datetime.fromisoformat(s1.replace("Z", "+00:00"))
    dt1_e = datetime.fromisoformat(e1.replace("Z", "+00:00"))
    return dt1_s < e2 and dt1_e > s2


def test_01_respects_university_fixed_events_and_buffers(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    anchor = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    course_start = anchor.replace(hour=8, minute=0)
    course_end = anchor.replace(hour=12, minute=0)

    ev_res = client.post(
        "/api/v1/schedule",
        json={
            "title": "Architecture Logicielle — Cours",
            "type": "course",
            "starts_at": course_start.isoformat(),
            "ends_at": course_end.isoformat(),
            "source": "timetable_import",
            "session_subtype": "cours",
        },
        headers=user_a_headers,
    )
    assert ev_res.status_code == 201

    goal_res = client.post(
        "/api/v1/objectives",
        json={
            "category": "framework",
            "title": "React",
            "goal": "Maîtriser les hooks React",
            "priority": "high",
            "weekly_target_minutes": 180,
        },
        headers=user_a_headers,
    )
    assert goal_res.status_code == 201

    gen_res = client.post(
        "/api/v1/planning/generate",
        json={
            "horizon_days": 5,
            "range_start": anchor.isoformat(),
            "timezone": "UTC",
            "buffer_minutes": 15,
        },
        headers=user_a_headers,
    )
    assert gen_res.status_code == 201
    data = gen_res.json()
    assert len(data["planned_sessions"]) >= 1

    buf_start = course_start - timedelta(minutes=15)
    buf_end = course_end + timedelta(minutes=15)
    for sess in data["planned_sessions"]:
        assert not _overlaps(sess["starts_at"], sess["ends_at"], buf_start, buf_end)


def test_02_personal_unavailability_strictly_excluded(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    anchor = _next_weekday(datetime.now(timezone.utc), 2)  # Mercredi UTC 00:00
    wed_start = anchor.replace(hour=14, minute=0)
    wed_end = anchor.replace(hour=18, minute=0)

    rule_res = client.post(
        "/api/v1/planning/availability-rules",
        json={
            "label": "Indisponibilité mercredi après-midi",
            "rule_type": "personal_unavailability",
            "day_of_week": 2,
            "start_time": "14:00",
            "end_time": "18:00",
            "timezone": "UTC",
            "recurrence": "weekly",
        },
        headers=user_a_headers,
    )
    assert rule_res.status_code == 201

    client.post(
        "/api/v1/objectives",
        json={
            "category": "language",
            "title": "Python",
            "goal": "Automatisation Python",
            "priority": "high",
            "weekly_target_minutes": 360,
        },
        headers=user_a_headers,
    )

    avail = client.get(
        "/api/v1/planning/availability/compute",
        params={"horizon_days": 3, "range_start": anchor.isoformat(), "timezone": "UTC"},
        headers=user_a_headers,
    )
    assert avail.status_code == 200
    assert any(u["local_date"] == anchor.date().isoformat() for u in avail.json()["unavailable_slots"])

    gen = client.post(
        "/api/v1/planning/generate",
        json={
            "horizon_days": 3,
            "range_start": anchor.isoformat(),
            "timezone": "UTC",
            "daily_max_minutes": 360,
        },
        headers=user_a_headers,
    )
    assert gen.status_code == 201
    for sess in gen.json()["planned_sessions"]:
        assert not _overlaps(sess["starts_at"], sess["ends_at"], wed_start, wed_end)


def test_03_imminent_exam_ranks_first_before_exam_date(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    anchor = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    exam_dt = anchor + timedelta(days=3, hours=10)

    client.post(
        "/api/v1/schedule",
        json={
            "title": "Examen Java POO",
            "type": "course",
            "session_subtype": "examen",
            "starts_at": exam_dt.isoformat(),
            "ends_at": (exam_dt + timedelta(hours=2)).isoformat(),
            "source": "timetable_import",
        },
        headers=user_a_headers,
    )
    client.post(
        "/api/v1/objectives",
        json={
            "category": "learning_goal",
            "title": "Design UI secondaire",
            "goal": "Découvrir Figma",
            "priority": "low",
            "weekly_target_minutes": 90,
        },
        headers=user_a_headers,
    )

    gen = client.post(
        "/api/v1/planning/generate",
        json={
            "horizon_days": 7,
            "range_start": anchor.isoformat(),
            "timezone": "UTC",
        },
        headers=user_a_headers,
    )
    assert gen.status_code == 201
    body = gen.json()
    assert body["priorities"][0]["source_type"] == "exam_revision"
    assert "Java" in body["priorities"][0]["title"]

    exam_sessions = [s for s in body["planned_sessions"] if s["priority_source_type"] == "exam_revision"]
    assert len(exam_sessions) >= 1
    for s in exam_sessions:
        assert datetime.fromisoformat(s["ends_at"].replace("Z", "+00:00")) <= exam_dt


def test_04_multi_objectives_balanced_with_concrete_pedagogical_steps(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    anchor = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    client.post(
        "/api/v1/courses",
        json={"subject": "Python", "language": "fr", "total_levels": 3},
        headers=user_a_headers,
    )
    client.post(
        "/api/v1/objectives",
        json={
            "category": "framework",
            "title": "React",
            "goal": "Maîtriser hooks et composants",
            "priority": "high",
            "weekly_target_minutes": 180,
        },
        headers=user_a_headers,
    )

    gen = client.post(
        "/api/v1/planning/generate",
        json={
            "horizon_days": 7,
            "range_start": anchor.isoformat(),
            "timezone": "UTC",
        },
        headers=user_a_headers,
    )
    assert gen.status_code == 201
    sessions = gen.json()["planned_sessions"]
    subjects = {s["subject"].lower() for s in sessions}
    assert any("python" in sub for sub in subjects)
    assert any("react" in sub for sub in subjects)
    for s in sessions:
        ped = s["pedagogical_content"]
        assert ped["next_step_summary"].strip() != ""
        assert len(ped["exercises_focus"]) >= 1
        assert s["title"].strip().lower() not in ("apprendre react", "apprendre python")


def test_05_paused_objectives_and_courses_never_scheduled(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    anchor = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    client.post(
        "/api/v1/objectives",
        json={
            "category": "language",
            "title": "RustEnPause",
            "goal": "Ne pas planifier pour l'instant",
            "status": "paused",
            "weekly_target_minutes": 180,
        },
        headers=user_a_headers,
    )
    c_res = client.post(
        "/api/v1/courses",
        json={"subject": "GoLangPause", "language": "fr", "total_levels": 2},
        headers=user_a_headers,
    )
    cid = c_res.json()["id"]
    client.patch(f"/api/v1/courses/{cid}", json={"status": "paused"}, headers=user_a_headers)

    client.post(
        "/api/v1/objectives",
        json={
            "category": "language",
            "title": "SQL Actif",
            "goal": "Requêtes avancées",
            "status": "active",
            "priority": "high",
            "weekly_target_minutes": 120,
        },
        headers=user_a_headers,
    )

    gen = client.post(
        "/api/v1/planning/generate",
        json={"horizon_days": 7, "range_start": anchor.isoformat(), "timezone": "UTC"},
        headers=user_a_headers,
    )
    assert gen.status_code == 201
    all_titles = " ".join(s["title"] + " " + s["subject"] for s in gen.json()["planned_sessions"])
    assert "RustEnPause" not in all_titles
    assert "GoLangPause" not in all_titles
    assert "SQL Actif" in all_titles


def test_06_overdue_tasks_and_schedule_validity_detection(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    past_due = now - timedelta(days=2)

    client.post(
        "/api/v1/tasks",
        json={
            "title": "Rendre TP Réseaux en retard",
            "priority": "high",
            "due_at": past_due.isoformat(),
        },
        headers=user_a_headers,
    )
    client.post(
        "/api/v1/schedule",
        json={
            "title": "Séance manquée hier",
            "type": "learning",
            "starts_at": (now - timedelta(hours=10)).isoformat(),
            "ends_at": (now - timedelta(hours=9)).isoformat(),
            "source": "ai_proposal",
        },
        headers=user_a_headers,
    )

    val_res = client.get("/api/v1/planning/validity", headers=user_a_headers)
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert val_data["expired_task_count"] >= 1
    assert val_data["missed_session_count"] >= 1

    anchor = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    gen = client.post(
        "/api/v1/planning/generate",
        json={"horizon_days": 5, "range_start": anchor.isoformat(), "timezone": "UTC"},
        headers=user_a_headers,
    )
    assert gen.status_code == 201
    assert gen.json()["priorities"][0]["title"] == "Rendre TP Réseaux en retard"


def test_07_failed_exercise_triggers_remediation_and_respects_prerequisites(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    course_res = client.post(
        "/api/v1/courses",
        json={"subject": "Python", "language": "fr", "total_levels": 3},
        headers=user_a_headers,
    )
    assert course_res.status_code == 201
    course = course_res.json()
    lvl1 = next(lv for lv in course["levels"] if lv["level_number"] == 1)
    first_lesson = lvl1["lessons"][0]
    first_exercise = first_lesson["exercises"][0]

    sub_res = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/submissions",
        json={
            "lesson_id": first_lesson["id"],
            "submission_kind": "exercise",
            "exercise_id": first_exercise["id"],
            "title": first_exercise["title"],
            "answer_text": "je ne sais pas",
        },
        headers=user_a_headers,
    )
    assert sub_res.status_code == 201
    assert sub_res.json()["passed"] is False

    anchor = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    gen = client.post(
        "/api/v1/planning/generate",
        json={"horizon_days": 5, "range_start": anchor.isoformat(), "timezone": "UTC"},
        headers=user_a_headers,
    )
    assert gen.status_code == 201
    sessions = gen.json()["planned_sessions"]
    assert len(sessions) >= 1
    first_ped = sessions[0]["pedagogical_content"]
    assert first_ped["remediation_needed"] is True
    assert first_ped["level_number"] == 1
    assert first_ped["recommended_session_type"] == "remediation"
    assert len(first_ped["blocked_prerequisites"]) >= 1


def test_08_overload_arbitrage_non_utc_timezone_and_cross_midnight(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    anchor = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # Règle traversant minuit en fuseau America/New_York
    rule_res = client.post(
        "/api/v1/planning/availability-rules",
        json={
            "label": "Repos nocturne croisant minuit",
            "rule_type": "personal_unavailability",
            "start_time": "21:30",
            "end_time": "02:00",
            "timezone": "America/New_York",
            "recurrence": "daily",
        },
        headers=user_a_headers,
    )
    assert rule_res.status_code == 201

    for idx, title in enumerate(("Task A", "Task B", "Task C", "Task D")):
        client.post(
            "/api/v1/tasks",
            json={"title": f"{title} importante", "priority": "high"},
            headers=user_a_headers,
        )

    gen = client.post(
        "/api/v1/planning/generate",
        json={
            "horizon_days": 5,
            "range_start": anchor.isoformat(),
            "timezone": "America/New_York",
            "weekly_hours_override": 2.0,
            "daily_max_minutes": 90,
        },
        headers=user_a_headers,
    )
    assert gen.status_code == 201
    body = gen.json()
    assert body["timezone"] == "America/New_York"
    assert body["load_summary"]["weekly_planned_minutes"] <= 120
    assert body["load_summary"]["is_overloaded"] is False
    assert all(m <= 90 for m in body["load_summary"]["daily_minutes"].values())
    assert len(body["arbitrage_items"]) >= 1

    ny_tz = ZoneInfo("America/New_York")
    for s in body["planned_sessions"]:
        loc_start = datetime.fromisoformat(s["starts_at"].replace("Z", "+00:00")).astimezone(ny_tz).time()
        loc_end = datetime.fromisoformat(s["ends_at"].replace("Z", "+00:00")).astimezone(ny_tz).time()
        assert loc_start >= time(2, 0) and loc_end <= time(21, 30)


def test_09_generate_and_reject_mutate_nothing(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    anchor = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    client.post(
        "/api/v1/objectives",
        json={"category": "language", "title": "TypeScript", "goal": "Typage strict"},
        headers=user_a_headers,
    )
    before_events = client.get("/api/v1/schedule", headers=user_a_headers).json()
    before_tasks = client.get("/api/v1/tasks", headers=user_a_headers).json()

    gen = client.post(
        "/api/v1/planning/generate",
        json={"horizon_days": 5, "range_start": anchor.isoformat(), "timezone": "UTC"},
        headers=user_a_headers,
    )
    assert gen.status_code == 201
    vid = gen.json()["id"]

    rej = client.post(f"/api/v1/planning/versions/{vid}/reject", headers=user_a_headers)
    assert rej.status_code == 200
    assert rej.json()["status"] == "rejected"

    after_events = client.get("/api/v1/schedule", headers=user_a_headers).json()
    after_tasks = client.get("/api/v1/tasks", headers=user_a_headers).json()
    assert len(after_events) == len(before_events)
    assert len(after_tasks) == len(before_tasks)


def test_10_apply_conflict_guard_adjust_and_restore_version(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    anchor = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    client.post(
        "/api/v1/objectives",
        json={"category": "framework", "title": "FastAPI", "goal": "APIs propres", "priority": "high"},
        headers=user_a_headers,
    )

    gen1 = client.post(
        "/api/v1/planning/generate",
        json={"horizon_days": 5, "range_start": anchor.isoformat(), "timezone": "UTC"},
        headers=user_a_headers,
    ).json()
    v1_id = gen1["id"]
    first_slot = gen1["planned_sessions"][0]

    # Simule un événement manuel ajouté pendant que v1 était en attente -> 409 CONFLICT !
    conflict_ev = client.post(
        "/api/v1/schedule",
        json={
            "title": "Rendez-vous imprévu",
            "type": "personal",
            "starts_at": first_slot["starts_at"],
            "ends_at": first_slot["ends_at"],
            "source": "manual",
        },
        headers=user_a_headers,
    )
    assert conflict_ev.status_code == 201

    apply_fail = client.post(
        f"/api/v1/planning/versions/{v1_id}/apply",
        json={"replace_future_planned": True},
        headers=user_a_headers,
    )
    assert apply_fail.status_code == 409
    assert apply_fail.json()["error"]["code"] == "PLANNING_CONFLICT_DETECTED"

    # Recalcule proprement en tenant compte du rendez-vous imprévu, puis applique
    gen2 = client.post(
        "/api/v1/planning/adjust",
        json={"instruction": "Allège cette semaine à 4h", "range_start": anchor.isoformat(), "timezone": "UTC"},
        headers=user_a_headers,
    ).json()
    v2_id = gen2["id"]
    assert gen2["parent_version_id"] == v1_id

    apply_ok = client.post(
        f"/api/v1/planning/versions/{v2_id}/apply",
        json={"replace_future_planned": True},
        headers=user_a_headers,
    )
    assert apply_ok.status_code == 200
    assert apply_ok.json()["status"] == "applied"
    assert len(apply_ok.json()["applied_event_ids"]) >= 1

    # Supprime le rendez-vous manuel puis restaure v1
    client.delete(f"/api/v1/schedule/{conflict_ev.json()['id']}", headers=user_a_headers)
    restored = client.post(f"/api/v1/planning/versions/{v1_id}/restore", headers=user_a_headers)
    assert restored.status_code == 200
    assert restored.json()["status"] == "restored"


def test_11_copilot_natural_language_integration_and_idempotency(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    anchor = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    idem_key = f"idem-{uuid4().hex[:12]}"
    g1 = client.post(
        "/api/v1/planning/generate",
        json={"horizon_days": 5, "range_start": anchor.isoformat(), "timezone": "UTC"},
        headers={**user_a_headers, "Idempotency-Key": idem_key},
    )
    g2 = client.post(
        "/api/v1/planning/generate",
        json={"horizon_days": 5, "range_start": anchor.isoformat(), "timezone": "UTC"},
        headers={**user_a_headers, "Idempotency-Key": idem_key},
    )
    assert g1.status_code == 201 and g2.status_code == 201
    assert g1.json()["id"] == g2.json()["id"]

    # Copilote IA : indisponibilité naturelle -> manage_availability_rule
    conv = client.post("/api/v1/ai/conversations", json={"title": "Test Planification"}, headers=user_a_headers).json()
    turn1 = client.post(
        f"/api/v1/ai/conversations/{conv['id']}/messages",
        json={"content": "Je suis indisponible mercredi après-midi"},
        headers=user_a_headers,
    )
    assert turn1.status_code in (200, 201)
    prop1 = turn1.json()["proposals"][0]
    assert prop1["action_type"] == "manage_availability_rule"
    assert prop1["payload"]["day_of_week"] == 2

    acc1 = client.post(
        f"/api/v1/ai/proposals/{prop1['id']}/accept",
        json={"idempotency_key": uuid4().hex},
        headers=user_a_headers,
    )
    assert acc1.status_code == 200
    rules = client.get("/api/v1/planning/availability-rules", headers=user_a_headers).json()
    assert any(r["day_of_week"] == 2 for r in rules)

    # Ajoute un objectif pour que le plan généré contienne au moins une séance
    client.post(
        "/api/v1/objectives",
        json={"category": "language", "title": "Java", "goal": "Préparer l'examen"},
        headers=user_a_headers,
    )

    # Copilote IA : programme complet -> generate_learning_plan -> création réelle
    turn2 = client.post(
        f"/api/v1/ai/conversations/{conv['id']}/messages",
        json={"content": "Crée-moi un programme d'apprentissage adapté à mon emploi du temps"},
        headers=user_a_headers,
    )
    assert turn2.status_code in (200, 201)
    prop2 = turn2.json()["proposals"][0]
    assert prop2["action_type"] == "generate_learning_plan"

    acc2 = client.post(
        f"/api/v1/ai/proposals/{prop2['id']}/accept",
        json={"idempotency_key": uuid4().hex},
        headers=user_a_headers,
    )
    assert acc2.status_code == 200
    assert acc2.json()["execution_result"]["entity"] == "learning_plan"
    assert acc2.json()["execution_result"]["applied_event_count"] >= 1


def test_12_strict_cross_user_isolation_returns_404(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    rule = client.post(
        "/api/v1/planning/availability-rules",
        json={
            "label": "Règle privée A",
            "rule_type": "personal_unavailability",
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "12:00",
        },
        headers=user_a_headers,
    ).json()

    plan = client.post(
        "/api/v1/planning/generate",
        json={"horizon_days": 5, "timezone": "UTC"},
        headers=user_a_headers,
    ).json()

    assert client.patch(
        f"/api/v1/planning/availability-rules/{rule['id']}",
        json={"label": "Piratage"},
        headers=user_b_headers,
    ).status_code == 404
    assert client.delete(f"/api/v1/planning/availability-rules/{rule['id']}", headers=user_b_headers).status_code == 404

    for method, url in (
        ("get", f"/api/v1/planning/versions/{plan['id']}"),
        ("post", f"/api/v1/planning/versions/{plan['id']}/apply"),
        ("post", f"/api/v1/planning/versions/{plan['id']}/reject"),
        ("post", f"/api/v1/planning/versions/{plan['id']}/restore"),
    ):
        res = getattr(client, method)(url, headers=user_b_headers)
        assert res.status_code == 404


def test_13_planning_and_validity_succeed_with_completed_and_cancelled_sessions_and_persist_links(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    course = client.post(
        "/api/v1/courses",
        json={"subject": "Python", "language": "fr", "total_levels": 3},
        headers=user_a_headers,
    ).json()

    # Crée une séance terminée + une séance annulée (reproduit BUG-01)
    s1 = client.post(
        "/api/v1/sessions",
        json={
            "title": "Session Python pratique",
            "category": "Python",
            "started_at": (now - timedelta(hours=3)).isoformat(),
            "ended_at": (now - timedelta(hours=2)).isoformat(),
            "result": "Exercices boucles réussis",
        },
        headers=user_a_headers,
    )
    assert s1.status_code == 201
    s2 = client.post(
        "/api/v1/sessions",
        json={"title": "Session interrompue", "category": "Python"},
        headers=user_a_headers,
    ).json()
    client.post(f"/api/v1/sessions/{s2['id']}/cancel", headers=user_a_headers)

    val = client.get("/api/v1/planning/validity", headers=user_a_headers)
    assert val.status_code == 200

    anchor = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    gen = client.post(
        "/api/v1/planning/generate",
        json={"horizon_days": 5, "range_start": anchor.isoformat(), "timezone": "UTC"},
        headers=user_a_headers,
    )
    assert gen.status_code == 201
    vid = gen.json()["id"]

    ap = client.post(
        f"/api/v1/planning/versions/{vid}/apply",
        json={"replace_future_planned": True},
        headers=user_a_headers,
    )
    assert ap.status_code == 200
    applied_ids = set(ap.json()["applied_event_ids"])
    assert len(applied_ids) >= 1

    # Vérifie BUG-05 : au moins un ScheduleEvent créé persiste réellement course_id
    events = client.get("/api/v1/schedule", headers=user_a_headers).json()
    linked = [e for e in events if e["id"] in applied_ids]
    assert any(e.get("course_id") == course["id"] for e in linked)


def test_14_all_10_natural_phrases_and_multi_turn_sync_in_local_mode(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

    client.post(
        "/api/v1/objectives",
        json={"category": "language", "title": "Python", "goal": "Automatiser en Python"},
        headers=user_a_headers,
    )
    proj = client.post(
        "/api/v1/projects",
        json={"name": "API FastAPI", "goal": "Backend propre", "status": "active", "next_action": "Init"},
        headers=user_a_headers,
    ).json()
    client.post(
        "/api/v1/tasks",
        json={"title": "Corriger bug auth JWT", "priority": "normal", "due_at": (now - timedelta(days=1)).isoformat()},
        headers=user_a_headers,
    )
    client.post(
        "/api/v1/schedule",
        json={
            "title": "Séance Python demain",
            "type": "learning",
            "starts_at": tomorrow.isoformat(),
            "ends_at": (tomorrow + timedelta(hours=1)).isoformat(),
        },
        headers=user_a_headers,
    )

    conv_id = client.post(
        "/api/v1/ai/conversations",
        json={"title": "Audit 5.1"},
        headers=user_a_headers,
    ).json()["id"]

    def _ask(msg: str) -> dict:
        r = client.post(
            f"/api/v1/ai/conversations/{conv_id}/messages",
            json={"content": msg},
            headers=user_a_headers,
        )
        assert r.status_code in (200, 201)
        return r.json()

    r1 = _ask("Je veux apprendre React.")
    assert r1["proposals"][0]["action_type"] == "plan_strategic_activity"

    r2 = _ask("Je veux continuer Python.")
    assert r2["proposals"][0]["action_type"] == "update_learning_path"

    r3 = _ask("Ajoute une compétence liée aux hooks React.")
    assert r3["proposals"][0]["action_type"] == "create_skill"
    assert not r3["proposals"][0]["payload"]["name"].lower().startswith("liée")

    r4 = _ask("Crée-moi un projet pour pratiquer Python.")
    assert r4["proposals"][0]["action_type"] == "create_project"

    r5 = _ask("Ajoute une tâche à mon projet.")
    assert r5["proposals"][0]["action_type"] == "create_task"
    assert r5["proposals"][0]["payload"].get("project_id") == proj["id"]

    r6 = _ask("Programme mes séances de cette semaine.")
    assert r6["proposals"][0]["action_type"] == "generate_learning_plan"

    r7 = _ask("Déplace ma séance de demain.")
    assert r7["proposals"][0]["action_type"] == "update_schedule_event"

    r8 = _ask("Je n'ai pas terminé mon travail hier. Réorganise ma journée.")
    assert r8["proposals"][0]["action_type"] == "batch_actions"

    react_goal = client.post(
        "/api/v1/objectives",
        json={"category": "framework", "title": "React", "goal": "Hooks React"},
        headers=user_a_headers,
    ).json()
    r9 = _ask("Mets React en pause pendant deux semaines.")
    assert r9["proposals"][0]["action_type"] in ("update_personal_goal", "batch_actions")

    r10 = _ask("Prépare mes révisions pour l'examen de Java.")
    assert r10["proposals"][0]["action_type"] == "generate_learning_plan"
    assert "Java" in (r10["proposals"][0]["payload"].get("exam_title") or "")

    r_inc = _ask("Augmente le temps consacré à React.")
    assert r_inc["proposals"][0]["action_type"] == "update_personal_goal"
    assert r_inc["proposals"][0]["payload"]["goal_id"] == react_goal["id"]
    assert r_inc["proposals"][0]["payload"]["weekly_target_minutes"] > 120

    r_read = _ask("Quelles sont mes tâches en cours ?")
    assert "Corriger bug auth JWT" in r_read["assistant_message"]["content"]

    r_mod = _ask("Passe la tâche Corriger bug auth JWT en priorité haute")
    assert r_mod["proposals"][0]["action_type"] == "update_task"
    assert r_mod["proposals"][0]["payload"]["priority"] == "high"
