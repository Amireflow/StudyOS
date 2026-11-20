from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai import provider as ai_provider_module
from app.ai.context_builder import BoundedUserContext
from app.ai.orchestrator import MAX_HISTORY_MESSAGES, _build_bounded_history
from app.ai.prompt_manager import PromptManager
from app.ai.provider import GeminiAIProvider
from app.ai.tool_registry import ToolRegistry
from app.core.errors import AppError
from app.repositories.ai_sql import AiMessageRecord
from app.schemas.common import AiMessageRole
from uuid import uuid4


def test_gemini_provider_forwards_history_and_handles_empty_or_safety_blocks(
    monkeypatch,
) -> None:
    captured_bodies: list[dict] = []

    class _MockResp:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    monkeypatch.setattr(
        ai_provider_module,
        "_validate_outbound_base_url",
        lambda url, **kw: url.rstrip("/"),
    )

    def _mock_ok(method, url, *, json_body=None, **kw):
        captured_bodies.append({"url": url, "body": json_body})
        return _MockResp(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"reply": "Réponse Gemini contextualisée", "proposals": []}'
                                }
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(ai_provider_module, "safe_http_request", _mock_ok)

    gemini = GeminiAIProvider(
        api_key="gem-key-123",
        model_name="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )
    ctx = BoundedUserContext(
        included_scopes=["today"],
        profile={"display_name": "Khadim", "timezone": "Europe/Paris", "local_date": "2026-11-20"},
    )
    history = [
        {"role": "user", "content": "Bonjour, je prépare Python."},
        {"role": "assistant", "content": "Très bien, quel est votre objectif ?"},
    ]
    res = gemini.generate_response(
        user_message="Organise ma semaine.",
        history=history,
        context=ctx,
        prompt_manager=PromptManager(ToolRegistry()),
    )
    assert res.reply == "Réponse Gemini contextualisée"
    sent_contents = captured_bodies[0]["body"]["contents"]
    assert len(sent_contents) == 3
    assert sent_contents[0] == {"role": "user", "parts": [{"text": "Bonjour, je prépare Python."}]}
    assert sent_contents[1] == {"role": "model", "parts": [{"text": "Très bien, quel est votre objectif ?"}]}
    assert sent_contents[2] == {"role": "user", "parts": [{"text": "Organise ma semaine."}]}

    # Cas safety block / empty candidates
    monkeypatch.setattr(
        ai_provider_module,
        "safe_http_request",
        lambda *a, **kw: _MockResp({"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}),
    )
    try:
        gemini.generate_response(
            user_message="Test blocage",
            history=[],
            context=ctx,
            prompt_manager=PromptManager(ToolRegistry()),
        )
        assert False, "Devait lever AppError AI_PROVIDER_SAFETY_BLOCKED"
    except AppError as exc:
        assert exc.status_code == 502
        assert exc.code == "AI_PROVIDER_SAFETY_BLOCKED"


def test_bounded_history_12_and_orphan_user_message_rollback_on_failure(
    app: FastAPI,
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    assert MAX_HISTORY_MESSAGES == 12
    conv_id_dummy = uuid4()
    uid_dummy = uuid4()
    records = [
        AiMessageRecord(
            id=uuid4(),
            user_id=uid_dummy,
            conversation_id=conv_id_dummy,
            role=AiMessageRole.user if i % 2 == 0 else AiMessageRole.assistant,
            content=f"Message numéro {i}",
            created_at=datetime.now(timezone.utc) + timedelta(seconds=i),
        )
        for i in range(16)
    ]
    bounded = _build_bounded_history(records)
    # 1 message de synthèse + 12 derniers messages
    assert len(bounded) == 13
    assert "Contexte des 4 message(s) précédent(s)" in bounded[0]["content"]

    class _FailingProvider:
        def generate_response(self, **kw):
            raise AppError(502, "AI_PROVIDER_ERROR", "Panne simulée du fournisseur.")

    conv = client.post("/api/v1/ai/conversations", json={"title": "Test rollback"}, headers=user_a_headers).json()
    app.state.ai_provider = _FailingProvider()
    try:
        failed_turn = client.post(
            f"/api/v1/ai/conversations/{conv['id']}/messages",
            json={"content": "Ce message doit être annulé si le fournisseur échoue"},
            headers=user_a_headers,
        )
        assert failed_turn.status_code == 502
    finally:
        app.state.ai_provider = None

    detail = client.get(f"/api/v1/ai/conversations/{conv['id']}", headers=user_a_headers).json()
    assert detail["messages"] == [], "Aucun message utilisateur orphelin ne doit subsister après échec provider"


def test_context_builder_21d_horizon_midnight_clipping_availability_courses_and_missed_blocks(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    # Configurer des préférences de disponibilité (exclure dimanche = 6, plage 9h-18h)
    prof_res = client.patch(
        "/api/v1/profile",
        json={
            "timezone": "UTC",
            "preferences": {
                "availability": {
                    "study_start_hour": 9,
                    "study_end_hour": 18,
                    "excluded_days": ["sunday"],
                }
            },
        },
        headers=user_a_headers,
    )
    assert prof_res.status_code == 200

    # Créer un cours actif pour vérifier sa présence avec next_incomplete_lesson dans le contexte
    course = client.post(
        "/api/v1/courses",
        json={"subject": "Python", "language": "fr", "total_levels": 3},
        headers=user_a_headers,
    ).json()
    assert course["current_level"] == 1

    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    today_midnight = now_utc.replace(hour=0)

    # Événement à cheval sur minuit (23:00 -> 01:00 le lendemain = 60 min aujourd'hui + 60 min demain)
    cross_start = today_midnight + timedelta(hours=23)
    cross_end = cross_start + timedelta(hours=2)
    ev_cross = client.post(
        "/api/v1/schedule",
        json={
            "title": "Révision nocturne",
            "type": "learning",
            "starts_at": cross_start.isoformat(),
            "ends_at": cross_end.isoformat(),
        },
        headers=user_a_headers,
    )
    assert ev_cross.status_code == 201

    # Deux blocs d'étude passés hier, mais une seule session terminée hier -> 1 bloc manqué
    yesterday_10h = today_midnight - timedelta(days=1) + timedelta(hours=10)
    yesterday_15h = today_midnight - timedelta(days=1) + timedelta(hours=15)
    for idx, st in enumerate((yesterday_10h, yesterday_15h), start=1):
        client.post(
            "/api/v1/schedule",
            json={
                "title": f"Bloc étude passé {idx}",
                "type": "learning",
                "starts_at": st.isoformat(),
                "ends_at": (st + timedelta(hours=1)).isoformat(),
            },
            headers=user_a_headers,
        )
    client.post(
        "/api/v1/sessions",
        json={
            "title": "Bloc étude passé 1",
            "category": "learning",
            "status": "completed",
            "started_at": yesterday_10h.isoformat(),
            "ended_at": (yesterday_10h + timedelta(hours=1)).isoformat(),
            "result": "Exercices chapitre 1 résolus",
        },
        headers=user_a_headers,
    )

    # Événement à J+14 (dans l'horizon 21 jours)
    day14_start = today_midnight + timedelta(days=14, hours=10)
    ev_14 = client.post(
        "/api/v1/schedule",
        json={
            "title": "Examen blanc J+14",
            "type": "learning",
            "starts_at": day14_start.isoformat(),
            "ends_at": (day14_start + timedelta(hours=2)).isoformat(),
        },
        headers=user_a_headers,
    )
    assert ev_14.status_code == 201

    # Vérifier via le briefing / bilan hebdomadaire que les statistiques reflètent exactement ces règles
    review = client.post("/api/v1/ai/weekly-review?force=true", headers=user_a_headers)
    assert review.status_code == 201
    stats = review.json()["metadata"]["stats"]
    assert stats["missed_study_blocks_count"] == 1
    # L'événement de 2h à cheval sur minuit compte 60 min sur J0 + 60 min sur J1 = 120 min (jamais 240 min)
    assert stats["weekly_scheduled_minutes"] == 120


def test_pause_project_and_multi_week_strategic_planning_and_atomic_claim(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    proj = client.post(
        "/api/v1/projects",
        json={
            "name": "Projet Secondaire Alpha",
            "goal": "Livrer un prototype secondaire",
            "status": "active",
            "priority": "normal",
            "next_action": "Initialiser le dépôt",
        },
        headers=user_a_headers,
    ).json()

    conv = client.post("/api/v1/ai/conversations", json={}, headers=user_a_headers).json()
    pause_turn = client.post(
        f"/api/v1/ai/conversations/{conv['id']}/messages",
        json={"content": "Peux-tu mettre en pause le projet actif pour réduire ma dispersion ?"},
        headers=user_a_headers,
    )
    assert pause_turn.status_code == 201
    pause_props = [p for p in pause_turn.json()["proposals"] if p["action_type"] == "pause_project"]
    assert len(pause_props) == 1
    pause_prop_id = pause_props[0]["id"]

    acc = client.post(f"/api/v1/ai/proposals/{pause_prop_id}/accept", headers=user_a_headers)
    assert acc.status_code == 200
    assert acc.json()["execution_result"]["status"] == "paused"

    # Un second accept concurrent/consécutif est rejeté atomiquement (409)
    dup_acc = client.post(f"/api/v1/ai/proposals/{pause_prop_id}/accept", headers=user_a_headers)
    assert dup_acc.status_code == 409

    updated_projects = client.get("/api/v1/projects", headers=user_a_headers).json()
    assert next(p for p in updated_projects if p["id"] == proj["id"])["status"] == "paused"

    # Planification stratégique multi-semaines (2 séances/semaine sur 3 semaines = 6 créneaux sans conflit)
    strat_turn = client.post(
        f"/api/v1/ai/conversations/{conv['id']}/messages",
        json={
            "content": "Je voudrais apprendre Rust : 2 séances par semaine de 60 minutes pendant 3 semaines pour créer un outil CLI."
        },
        headers=user_a_headers,
    )
    assert strat_turn.status_code == 201
    strat_props = [
        p for p in strat_turn.json()["proposals"] if p["action_type"] == "plan_strategic_activity"
    ]
    assert len(strat_props) == 1
    strat_prop = strat_props[0]
    assert len(strat_prop["payload"]["proposed_slots"]) >= 4

    exec_strat = client.post(
        f"/api/v1/ai/proposals/{strat_prop['id']}/accept",
        json={"payload_overrides": {"create_course": True, "course_subject": "Rust"}},
        headers=user_a_headers,
    )
    assert exec_strat.status_code == 200
    exec_res = exec_strat.json()["execution_result"]
    assert exec_res["created_events_count"] >= 4
    assert exec_res["course_id"] is not None


def test_idempotent_timezone_scoped_reports_and_ensure_endpoint(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    ensured_1 = client.post("/api/v1/ai/reports/ensure", headers=user_a_headers)
    assert ensured_1.status_code == 200
    data_1 = ensured_1.json()
    assert data_1["created_daily"] is True
    assert data_1["created_weekly"] is True
    daily_id = data_1["daily_briefing"]["id"]
    weekly_id = data_1["weekly_review"]["id"]

    # Second appel sur la même période -> idempotent, aucun doublon créé
    ensured_2 = client.post("/api/v1/ai/reports/ensure", headers=user_a_headers)
    assert ensured_2.status_code == 200
    data_2 = ensured_2.json()
    assert data_2["created_daily"] is False
    assert data_2["created_weekly"] is False
    assert data_2["daily_briefing"]["id"] == daily_id
    assert data_2["weekly_review"]["id"] == weekly_id

    all_reports = client.get("/api/v1/ai/reports", headers=user_a_headers).json()
    assert len(all_reports) == 2

    # Appel avec force=true -> régénère explicitement
    forced = client.post("/api/v1/ai/briefing?force=true", headers=user_a_headers)
    assert forced.status_code == 201
    assert forced.json()["id"] != daily_id
