from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai.context_builder import BoundedUserContext
from app.ai.prompt_manager import PromptManager
from app.ai.provider import ProviderResult
from app.schemas.ai import RawProposalCandidate


def _local_dt(day_offset: int, hour: int, minute: int = 0, tz_name: str = "Africa/Dakar") -> datetime:
    tz = ZoneInfo(tz_name)
    local_today = datetime.now(timezone.utc).astimezone(tz).date()
    target = local_today + timedelta(days=day_offset)
    return datetime.combine(target, time(hour, minute), tzinfo=tz).astimezone(timezone.utc)


def _new_conversation(client: TestClient, headers: dict[str, str], title: str) -> str:
    res = client.post("/api/v1/ai/conversations", json={"title": title}, headers=headers)
    assert res.status_code == 201
    return res.json()["id"]


def test_ai_first_scenarios_01_to_06_full_entity_lifecycle_without_duplicates(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénarios §11 (1 à 6) :
    1. Demander d'apprendre React -> crée un objectif d'apprentissage et le parcours associé.
    2. Demander d'apprendre un nouveau sujet tout en continuant Python (existant) -> met à jour Python sans doublon.
    3. Demander une nouvelle compétence (hooks React) -> créée au niveau 0 et rattachée à l'objectif React.
    4. Demander un projet -> créé avec son objectif et sa prochaine action.
    5. Demander une tâche liée au projet -> créée et correctement rattachée via project_id.
    6. Demander un planning -> respecte les cours universitaires, disponibilités et priorités.
    """
    # Pré-condition scénario 2 : un parcours Python existe déjà manuellement
    py_path_res = client.post(
        "/api/v1/learning/paths",
        json={
            "title": "Python",
            "goal": "Maîtriser les bases Python",
            "status": "paused",
        },
        headers=user_a_headers,
    )
    assert py_path_res.status_code == 201
    py_path_id = py_path_res.json()["id"]

    # Pré-condition scénario 6 : un cours universitaire occupe demain de 10h à 12h
    course_start = _local_dt(1, 10, 0)
    course_end = _local_dt(1, 12, 0)
    assert (
        client.post(
            "/api/v1/schedule",
            json={
                "title": "Architecture des Systèmes",
                "type": "course",
                "source": "timetable_import",
                "starts_at": course_start.isoformat(),
                "ends_at": course_end.isoformat(),
            },
            headers=user_a_headers,
        ).status_code
        == 201
    )

    conv_id = _new_conversation(client, user_a_headers, "AI-First Orchestration")

    # 1. Apprendre React -> plan_strategic_activity -> crée objectif personnel + parcours + séances
    t1 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je voudrais apprendre le développement avec React."},
        headers=user_a_headers,
    )
    assert t1.status_code == 201
    prop1 = t1.json()["proposals"][0]
    acc1 = client.post(f"/api/v1/ai/proposals/{prop1['id']}/accept", json={}, headers=user_a_headers)
    assert acc1.status_code == 200
    goals = client.get("/api/v1/objectives", headers=user_a_headers).json()
    react_goals = [g for g in goals if "react" in g["title"].lower()]
    assert len(react_goals) == 1
    react_goal_id = react_goals[0]["id"]

    # 2. Apprendre TypeScript tout en continuant Python -> aucun doublon de parcours Python
    t2 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je veux apprendre TypeScript tout en continuant Python."},
        headers=user_a_headers,
    )
    assert t2.status_code == 201
    prop2 = t2.json()["proposals"][0]
    assert prop2["action_type"] == "batch_actions"
    acc2 = client.post(f"/api/v1/ai/proposals/{prop2['id']}/accept", json={}, headers=user_a_headers)
    assert acc2.status_code == 200
    paths = client.get("/api/v1/learning/paths", headers=user_a_headers).json()
    python_paths = [p for p in paths if p["title"].strip().lower() == "python"]
    assert len(python_paths) == 1
    assert python_paths[0]["id"] == py_path_id
    assert python_paths[0]["status"] == "active"
    all_goals = client.get("/api/v1/objectives", headers=user_a_headers).json()
    assert any("typescript" in g["title"].lower() for g in all_goals)

    # Demander seulement de continuer Python -> réutilise le même parcours Python sans doublon
    t2b = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je veux continuer Python."},
        headers=user_a_headers,
    )
    assert t2b.status_code == 201
    prop2b = t2b.json()["proposals"][0]
    assert prop2b["action_type"] == "update_learning_path"
    assert prop2b["payload"]["path_id"] == py_path_id
    assert (
        client.post(f"/api/v1/ai/proposals/{prop2b['id']}/accept", json={}, headers=user_a_headers).status_code
        == 200
    )
    assert len([p for p in client.get("/api/v1/learning/paths", headers=user_a_headers).json() if p["title"].strip().lower() == "python"]) == 1

    # 3. Nouvelle compétence rattachée à l'objectif React (niveau 0 strict)
    t3 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Ajoute une compétence liée à la maîtrise des hooks React."},
        headers=user_a_headers,
    )
    assert t3.status_code == 201
    prop3 = t3.json()["proposals"][0]
    assert prop3["action_type"] == "create_skill"
    assert prop3["payload"]["goal_id"] == react_goal_id
    acc3 = client.post(f"/api/v1/ai/proposals/{prop3['id']}/accept", json={}, headers=user_a_headers)
    assert acc3.status_code == 200
    skills = client.get("/api/v1/skills", headers=user_a_headers).json()
    hooks_skill = next(s for s in skills if "hooks" in s["name"].lower() or "react" in s["name"].lower())
    assert hooks_skill["current_level"] == 0
    refreshed_react_goal = client.get(f"/api/v1/objectives/{react_goal_id}", headers=user_a_headers).json()
    assert refreshed_react_goal["skill_id"] == hooks_skill["id"]

    # 4. Créer un projet avec objectif et prochaine action
    t4 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Crée un projet : « Portfolio React » pour mettre en pratique ce que j'apprends."},
        headers=user_a_headers,
    )
    assert t4.status_code == 201
    prop4 = t4.json()["proposals"][0]
    assert prop4["action_type"] == "create_project"
    acc4 = client.post(f"/api/v1/ai/proposals/{prop4['id']}/accept", json={}, headers=user_a_headers)
    assert acc4.status_code == 200
    projects = client.get("/api/v1/projects", headers=user_a_headers).json()
    portfolio = next(p for p in projects if p["name"] == "Portfolio React")
    assert len(portfolio["goal"]) >= 2
    assert len(portfolio["next_action"]) >= 2

    # 5. Tâche liée à ce projet
    t5 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Crée une tâche liée au projet Portfolio React : « Construire les composants »"},
        headers=user_a_headers,
    )
    assert t5.status_code == 201
    prop5 = t5.json()["proposals"][0]
    assert prop5["action_type"] == "create_task"
    assert prop5["payload"]["project_id"] == portfolio["id"]
    acc5 = client.post(f"/api/v1/ai/proposals/{prop5['id']}/accept", json={}, headers=user_a_headers)
    assert acc5.status_code == 200
    tasks = client.get("/api/v1/tasks", headers=user_a_headers).json()
    linked_task = next(t for t in tasks if t["title"] == "Construire les composants")
    assert linked_task["project_id"] == portfolio["id"]

    # 6. Planning multi-séances cette semaine respectant le cours universitaire
    schedule_before_plan = client.get("/api/v1/schedule", headers=user_a_headers).json()
    t6 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Programme trois séances cette semaine."},
        headers=user_a_headers,
    )
    assert t6.status_code == 201
    prop6 = t6.json()["proposals"][0]
    assert prop6["action_type"] == "generate_learning_plan"
    assert prop6["payload"]["max_sessions"] == 3
    # La proposition ne crée encore aucun créneau avant confirmation utilisateur.
    assert client.get("/api/v1/schedule", headers=user_a_headers).json() == schedule_before_plan
    acc6 = client.post(f"/api/v1/ai/proposals/{prop6['id']}/accept", json={}, headers=user_a_headers)
    assert acc6.status_code == 200
    plan_result = acc6.json()["execution_result"]
    assert plan_result["entity"] == "learning_plan"
    assert 1 <= plan_result["applied_event_count"] <= 3
    events = client.get("/api/v1/schedule", headers=user_a_headers).json()
    ai_events = [ev for ev in events if ev.get("source") == "ai_proposal"]
    assert len(ai_events) == plan_result["applied_event_count"]
    for ev in ai_events:
        s_dt = datetime.fromisoformat(ev["starts_at"])
        e_dt = datetime.fromisoformat(ev["ends_at"])
        assert not (s_dt < course_end and course_start < e_dt)


def test_ai_first_scenario_07_conversational_availability_memory_and_suspend(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénario §11 (7) + suspension conversationnelle :
    - L'utilisateur modifie ses disponibilités en conversation (8h/sem., 10h-17h, pas le dimanche).
    - Sauvegardé dans GET /api/v1/ai/memory et synchronisé dans GET /api/v1/profile.
    - Les futures planifications respectent strictement 10h-17h et excluent le dimanche.
    - L'utilisateur peut suspendre un apprentissage en conversation.
    """
    conv_id = _new_conversation(client, user_a_headers, "Disponibilités et suspension")

    t1 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je dispose de 8 heures par semaine de 10h à 17h et pas le dimanche."},
        headers=user_a_headers,
    )
    assert t1.status_code == 201
    prop1 = t1.json()["proposals"][0]
    assert prop1["action_type"] == "update_preferences"
    acc1 = client.post(f"/api/v1/ai/proposals/{prop1['id']}/accept", json={}, headers=user_a_headers)
    assert acc1.status_code == 200

    mem = client.get("/api/v1/ai/memory", headers=user_a_headers).json()
    assert mem["weekly_study_hours"] == 8
    assert mem["availability_preferences"]["study_start_hour"] == 10
    assert mem["availability_preferences"]["study_end_hour"] == 17
    assert 6 in mem["availability_preferences"]["excluded_days"]

    prof = client.get("/api/v1/profile", headers=user_a_headers).json()
    assert prof["preferences"]["study_start_hour"] == 10
    assert prof["preferences"]["study_end_hour"] == 17
    assert 6 in prof["preferences"]["excluded_days"]

    # Planning ultérieur tient compte des nouvelles disponibilités (aucun créneau le dimanche ni hors 10h-17h)
    t2 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Programme trois séances cette semaine."},
        headers=user_a_headers,
    )
    assert t2.status_code == 201
    prop2 = t2.json()["proposals"][0]
    assert (
        client.post(f"/api/v1/ai/proposals/{prop2['id']}/accept", json={}, headers=user_a_headers).status_code
        == 200
    )
    tz = ZoneInfo("Africa/Dakar")
    for ev in client.get("/api/v1/schedule", headers=user_a_headers).json():
        s_local = datetime.fromisoformat(ev["starts_at"]).astimezone(tz)
        e_local = datetime.fromisoformat(ev["ends_at"]).astimezone(tz)
        assert s_local.weekday() != 6
        assert s_local.hour >= 10
        assert e_local.hour < 17 or (e_local.hour == 17 and e_local.minute == 0)

    # Suspension conversationnelle d'un objectif existant
    goal = client.post(
        "/api/v1/objectives",
        json={
            "title": "React",
            "category": "framework",
            "goal": "Maîtriser React",
            "create_linked_entities": False,
        },
        headers=user_a_headers,
    ).json()
    t3 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je veux suspendre mon apprentissage de React pendant deux semaines."},
        headers=user_a_headers,
    )
    assert t3.status_code == 201
    prop3 = t3.json()["proposals"][0]
    assert (
        client.post(f"/api/v1/ai/proposals/{prop3['id']}/accept", json={}, headers=user_a_headers).status_code
        == 200
    )
    assert client.get(f"/api/v1/objectives/{goal['id']}", headers=user_a_headers).json()["status"] == "paused"


def test_ai_first_scenario_08_manual_entity_visible_and_reorganize_day(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénario §11 (8) + réorganisation des tâches en retard :
    - L'utilisateur crée un projet et une tâche manuellement -> le copilote les retrouve immédiatement.
    - Une tâche en retard est réorganisée via conversation sans écraser les cours.
    """
    assert (
        client.post(
            "/api/v1/projects",
            json={
                "name": "Architecture Cloud K8s",
                "goal": "Déployer sur cluster managé",
                "status": "active",
                "next_action": "Configurer les manifestes Helm",
            },
            headers=user_a_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/tasks",
            json={
                "title": "Corriger TP Réseau hier",
                "priority": "high",
                "due_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            },
            headers=user_a_headers,
        ).status_code
        == 201
    )

    conv_id = _new_conversation(client, user_a_headers, "Visibilité manuelle")
    t1 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Quels sont mes projets et tâches actuels ?"},
        headers=user_a_headers,
    )
    assert t1.status_code == 201
    reply1 = t1.json()["assistant_message"]["content"]
    assert "Architecture Cloud K8s" in reply1
    assert "Corriger TP Réseau hier" in reply1

    t2 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je n'ai pas terminé mes tâches hier. Réorganise ma journée."},
        headers=user_a_headers,
    )
    assert t2.status_code == 201
    prop2 = t2.json()["proposals"][0]
    assert prop2["action_type"] == "batch_actions"
    acc2 = client.post(f"/api/v1/ai/proposals/{prop2['id']}/accept", json={}, headers=user_a_headers)
    assert acc2.status_code == 200
    assert acc2.json()["status"] == "executed"


def test_ai_first_scenario_09_failure_rollback_no_false_confirmation(
    app: FastAPI,
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénario §11 (9) :
    - Si une action échoue à l'étape 2 d'un batch_actions (ex. conflit cours universitaire découvert à l'exécution),
      l'étape 1 est compensée/annulée (zéro création partielle en BDD), la proposition passe à `failed`,
      et aucune fausse confirmation de réussite n'est renvoyée.
    """
    course_start = _local_dt(1, 9, 0)
    course_end = _local_dt(1, 11, 0)
    assert (
        client.post(
            "/api/v1/schedule",
            json={
                "title": "Cours Protégé Compilation",
                "type": "course",
                "source": "timetable_import",
                "starts_at": course_start.isoformat(),
                "ends_at": course_end.isoformat(),
            },
            headers=user_a_headers,
        ).status_code
        == 201
    )

    conv_id = _new_conversation(client, user_a_headers, "Rollback compensation")
    free_start = _local_dt(2, 14, 0)
    free_end = _local_dt(2, 15, 0)

    class _TwoStepBatchProvider:
        def generate_response(
            self,
            *,
            user_message: str,
            history: list[dict[str, str]],
            context: BoundedUserContext,
            prompt_manager: PromptManager,
        ) -> ProviderResult:
            _ = (user_message, history, context, prompt_manager)
            return ProviderResult(
                reply="Plan en 2 étapes préparé pour validation.",
                proposals=[
                    RawProposalCandidate(
                        action_type="batch_actions",
                        title="Créer tâche puis planifier séance",
                        explanation="Opération atomique en 2 étapes.",
                        payload={
                            "summary": "Créer tâche + séance",
                            "steps": [
                                {
                                    "action_type": "create_task",
                                    "payload": {"title": "Tâche qui doit être annulée si étape 2 échoue", "priority": "normal"},
                                },
                                {
                                    "action_type": "create_schedule_event",
                                    "payload": {
                                        "title": "Séance ajoutée entretemps",
                                        "type": "learning",
                                        "starts_at": free_start.isoformat(),
                                        "ends_at": free_end.isoformat(),
                                    },
                                },
                            ],
                            "compensate_on_failure": True,
                        },
                    )
                ],
                is_estimate=False,
                missing_data=[],
                provider_name="mock",
                model_name="mock-v1",
            )

    app.state.ai_provider = _TwoStepBatchProvider()
    try:
        turn = client.post(
            f"/api/v1/ai/conversations/{conv_id}/messages",
            json={"content": "Exécute ce plan en deux étapes."},
            headers=user_a_headers,
        )
        assert turn.status_code == 201
        prop_id = turn.json()["proposals"][0]["id"]
    finally:
        app.state.ai_provider = None

    # Simule un cours universitaire ajouté entre la proposition et l'acceptation sur free_start..free_end
    assert (
        client.post(
            "/api/v1/schedule",
            json={
                "title": "Séminaire Universitaire Obligatoire",
                "type": "course",
                "source": "timetable_import",
                "starts_at": free_start.isoformat(),
                "ends_at": free_end.isoformat(),
            },
            headers=user_a_headers,
        ).status_code
        == 201
    )

    # Validation échoue proprement (conflit pré-exécution ou étape 2) : essayons aussi quand étape 2 échoue PENDANT exécution
    # Remplaçons par une création de créneau valide à l'instant T=accept pour step 2 qui utilise service error ou overlap sur step 2 après step 1 !
    res_fail = client.post(f"/api/v1/ai/proposals/{prop_id}/accept", json={}, headers=user_a_headers)
    assert res_fail.status_code in (409, 422)
    assert client.get("/api/v1/tasks", headers=user_a_headers).json() == []

    # Cas 2 : échec PENDANT l'exécution de step 3 (steps 1 et 2 réussissent, step 3 heurte le cours créé à l'étape 2 -> rollback LIFO complet!)
    conv2 = _new_conversation(client, user_a_headers, "Rollback step 3 runtime failure")
    conflict_start = _local_dt(3, 14, 0)
    conflict_end = _local_dt(3, 15, 0)

    class _RuntimeFailStep2Provider:
        def generate_response(
            self,
            *,
            user_message: str,
            history: list[dict[str, str]],
            context: BoundedUserContext,
            prompt_manager: PromptManager,
        ) -> ProviderResult:
            _ = (user_message, history, context, prompt_manager)
            return ProviderResult(
                reply="Plan coordonné en 3 étapes.",
                proposals=[
                    RawProposalCandidate(
                        action_type="batch_actions",
                        title="Créer tâche, cours et séance en conflit",
                        explanation="Vérifie la compensation LIFO en cas d'échec à l'étape 3.",
                        payload={
                            "summary": "Rollback test",
                            "steps": [
                                {
                                    "action_type": "create_task",
                                    "payload": {"title": "Tâche étape 1 à compenser"},
                                },
                                {
                                    "action_type": "create_schedule_event",
                                    "payload": {
                                        "title": "Cours créé à l'étape 2 à compenser",
                                        "type": "course",
                                        "starts_at": conflict_start.isoformat(),
                                        "ends_at": conflict_end.isoformat(),
                                    },
                                },
                                {
                                    "action_type": "create_schedule_event",
                                    "payload": {
                                        "title": "Séance en collision avec étape 2",
                                        "type": "learning",
                                        "starts_at": conflict_start.isoformat(),
                                        "ends_at": conflict_end.isoformat(),
                                    },
                                },
                            ],
                            "compensate_on_failure": True,
                        },
                    )
                ],
                is_estimate=False,
                missing_data=[],
                provider_name="mock",
                model_name="mock-v1",
            )

    app.state.ai_provider = _RuntimeFailStep2Provider()
    try:
        turn2 = client.post(
            f"/api/v1/ai/conversations/{conv2}/messages",
            json={"content": "Lance un batch qui échoue à l'étape 3."},
            headers=user_a_headers,
        )
        assert turn2.status_code == 201
        prop2_id = turn2.json()["proposals"][0]["id"]
    finally:
        app.state.ai_provider = None

    fail_exec = client.post(f"/api/v1/ai/proposals/{prop2_id}/accept", json={}, headers=user_a_headers)
    assert fail_exec.status_code == 409
    assert client.get("/api/v1/tasks", headers=user_a_headers).json() == [], (
        "La tâche créée à l'étape 1 doit avoir été supprimée par compensation LIFO"
    )
    all_sched = client.get("/api/v1/schedule", headers=user_a_headers).json()
    assert not any(ev["title"] == "Cours créé à l'étape 2 à compenser" for ev in all_sched), (
        "Le créneau créé à l'étape 2 doit aussi avoir été compensé"
    )
    prop_after = client.get(f"/api/v1/ai/proposals/{prop2_id}", headers=user_a_headers).json()
    assert prop_after["status"] == "failed"
    assert prop_after["error_message"] is not None
    assert prop_after["execution_result"]["rolled_back"] is True


def test_ai_first_scenario_10_idempotency_and_smart_confirmation(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénario §11 (10) + §6 confirmation intelligente :
    - Répétition d'une requête avec le même Idempotency-Key -> aucun doublon (ni message, ni proposition, ni tâche).
    - Mode actions simples auto activé : `create_task` exécuté directement, tandis qu'une action structurante reste `pending`.
    """
    conv_id = _new_conversation(client, user_a_headers, "Idempotence et autonomie")
    msg_headers = {**user_a_headers, "Idempotency-Key": "idem-msg-react-001"}

    r1 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Crée une tâche : « Écrire les tests d'idempotence »"},
        headers=msg_headers,
    )
    r2 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Crée une tâche : « Écrire les tests d'idempotence »"},
        headers=msg_headers,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["assistant_message"]["id"] == r2.json()["assistant_message"]["id"]
    prop_id = r1.json()["proposals"][0]["id"]
    assert r2.json()["proposals"][0]["id"] == prop_id
    assert len(client.get(f"/api/v1/ai/conversations/{conv_id}", headers=user_a_headers).json()["messages"]) == 2

    # Idempotence lors de l'acceptation répétée avec le même Idempotency-Key
    acc_headers = {**user_a_headers, "Idempotency-Key": "idem-acc-task-001"}
    a1 = client.post(f"/api/v1/ai/proposals/{prop_id}/accept", json={}, headers=acc_headers)
    a2 = client.post(f"/api/v1/ai/proposals/{prop_id}/accept", json={}, headers=acc_headers)
    assert a1.status_code == 200
    assert a2.status_code == 200
    assert a1.json()["execution_result"]["task_id"] == a2.json()["execution_result"]["task_id"]
    assert len(client.get("/api/v1/tasks", headers=user_a_headers).json()) == 1

    # Confirmation intelligente (§6) : activer l'exécution directe des actions simples uniquement
    mem_patch = client.patch(
        "/api/v1/ai/memory",
        json={"auto_execute_simple_actions": True},
        headers=user_a_headers,
    )
    assert mem_patch.status_code == 200
    assert mem_patch.json()["auto_execute_simple_actions"] is True

    simple_turn = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Crée une tâche : « Action simple directe »"},
        headers=user_a_headers,
    )
    assert simple_turn.status_code == 201
    s_data = simple_turn.json()
    assert s_data["auto_executed_count"] == 1
    assert s_data["proposals"][0]["status"] == "executed"
    assert any(t["title"] == "Action simple directe" for t in client.get("/api/v1/tasks", headers=user_a_headers).json())

    # Une action structurante reste en attente de validation explicite même quand auto_execute_simple_actions est activé
    struct_turn = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je voudrais apprendre GraphQL avec 2 séances par semaine."},
        headers=user_a_headers,
    )
    assert struct_turn.status_code == 201
    st_data = struct_turn.json()
    assert st_data["auto_executed_count"] == 0
    assert st_data["proposals"][0]["action_type"] == "plan_strategic_activity"
    assert st_data["proposals"][0]["status"] == "pending"


def test_ai_first_scenario_11_strict_cross_user_isolation(
    app: FastAPI,
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    """
    Scénario §11 (11) :
    - L'utilisateur B tente de modifier ou cibler les données (tâche, projet, objectif, proposition, mémoire) de l'utilisateur A :
      l'opération est strictement refusée.
    """
    proj_a = client.post(
        "/api/v1/projects",
        json={
            "name": "Projet Privé A",
            "goal": "Confidentiel A",
            "status": "active",
            "next_action": "Prochaine action A",
        },
        headers=user_a_headers,
    ).json()
    goal_a = client.post(
        "/api/v1/objectives",
        json={"title": "Objectif Privé A", "goal": "Secret A", "create_linked_entities": False},
        headers=user_a_headers,
    ).json()

    conv_a = _new_conversation(client, user_a_headers, "Conv A")
    prop_a = client.post(
        f"/api/v1/ai/conversations/{conv_a}/messages",
        json={"content": "Crée une tâche : « Tâche confidentielle A »"},
        headers=user_a_headers,
    ).json()["proposals"][0]

    # B ne peut ni accepter, ni rejeter, ni modifier la proposition ou la conversation de A
    assert client.get(f"/api/v1/ai/proposals/{prop_a['id']}", headers=user_b_headers).status_code == 404
    assert client.post(f"/api/v1/ai/proposals/{prop_a['id']}/accept", json={}, headers=user_b_headers).status_code == 404
    assert client.post(f"/api/v1/ai/proposals/{prop_a['id']}/reject", json={}, headers=user_b_headers).status_code == 404

    # B tente via un fournisseur malveillant de cibler project_id et goal_id appartenant à A
    class _CrossUserAttackProvider:
        def generate_response(
            self,
            *,
            user_message: str,
            history: list[dict[str, str]],
            context: BoundedUserContext,
            prompt_manager: PromptManager,
        ) -> ProviderResult:
            _ = (user_message, history, context, prompt_manager)
            return ProviderResult(
                reply="Tentative inter-utilisateurs",
                proposals=[
                    RawProposalCandidate(
                        action_type="update_project",
                        title="Modifier projet de A",
                        explanation="Attaque cross-user",
                        payload={"project_id": proj_a["id"], "status": "paused"},
                    ),
                    RawProposalCandidate(
                        action_type="update_personal_goal",
                        title="Modifier objectif de A",
                        explanation="Attaque cross-user",
                        payload={"goal_id": goal_a["id"], "status": "paused"},
                    ),
                ],
                is_estimate=False,
                missing_data=[],
                provider_name="mock",
                model_name="mock-v1",
            )

    conv_b = _new_conversation(client, user_b_headers, "Conv B")
    app.state.ai_provider = _CrossUserAttackProvider()
    try:
        attack = client.post(
            f"/api/v1/ai/conversations/{conv_b}/messages",
            json={"content": "Tente une attaque cross-user"},
            headers=user_b_headers,
        )
        assert attack.status_code == 201
        assert attack.json()["proposals"] == []
        assert attack.json()["assistant_message"]["metadata"]["rejected_proposals_count"] == 2
    finally:
        app.state.ai_provider = None

    assert client.get(f"/api/v1/projects/{proj_a['id']}", headers=user_a_headers).json()["status"] == "active"
    assert client.get(f"/api/v1/objectives/{goal_a['id']}", headers=user_a_headers).json()["status"] == "active"
