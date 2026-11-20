from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient


def _local_dt(day_offset: int, hour: int, minute: int = 0, tz_name: str = "Africa/Dakar") -> datetime:
    tz = ZoneInfo(tz_name)
    local_today = datetime.now(timezone.utc).astimezone(tz).date()
    target = local_today + timedelta(days=day_offset)
    return datetime.combine(target, time(hour, minute), tzinfo=tz).astimezone(timezone.utc)


def _new_conversation(client: TestClient, headers: dict[str, str], title: str) -> str:
    res = client.post("/api/v1/ai/conversations", json={"title": title}, headers=headers)
    assert res.status_code == 201
    return res.json()["id"]


def test_01_06_08_10_compatible_request_reuses_skill_modify_accept_and_prevent_double_validation(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénarios 1, 6, 8 et 10 :
    1. Demande compatible avec les disponibilités (réutilise le niveau existant de la compétence React).
    8. Proposition modifiée via PATCH /proposals/{id} avec recalcul.
    6. Proposition acceptée : crée le parcours + module + tâche liée + séances calendrier.
    10. Double validation bloquée (409).
    """
    # Crée une compétence existante "React" (niveau 0 verrouillé) pour vérifier la réutilisation du profil
    skill_res = client.post(
        "/api/v1/skills",
        json={"name": "React", "domain": "Frontend", "target_level": 4},
        headers=user_a_headers,
    )
    assert skill_res.status_code == 201

    conv_id = _new_conversation(client, user_a_headers, "Apprendre React")
    turn_res = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je voudrais apprendre le développement avec React."},
        headers=user_a_headers,
    )
    assert turn_res.status_code == 201
    data = turn_res.json()
    reply = data["assistant_message"]["content"]

    # Réutilise le niveau déjà enregistré sans le redemander et affiche l'avertissement de validation
    assert "0/5" in reply
    assert "Quel est ton niveau actuel" not in reply
    assert "Cette proposition ne sera pas enregistrée tant que tu ne l'auras pas validée" in reply

    assert len(data["proposals"]) == 1
    prop = data["proposals"][0]
    prop_id = prop["id"]
    assert prop["action_type"] == "plan_strategic_activity"
    assert prop["status"] == "pending"
    assert prop["payload"]["decision"] == "ACCEPTABLE"
    assert len(prop["payload"]["proposed_slots"]) >= 1

    # Avant validation : aucun parcours ni tâche ni créneau créé
    assert client.get("/api/v1/learning/paths", headers=user_a_headers).json() == []
    assert client.get("/api/v1/tasks", headers=user_a_headers).json() == []
    assert client.get("/api/v1/schedule", headers=user_a_headers).json() == []

    # Scénario 8 : Modification de la proposition (objectif + fréquence = 1 séance/sem. avec recalcul)
    patch_res = client.patch(
        f"/api/v1/ai/proposals/{prop_id}",
        json={
            "payload_overrides": {
                "activity_title": "React & TypeScript avancé",
                "goal": "Maîtriser composants, props, state et tests Vitest en 3 semaines.",
                "frequency_per_week": 1,
            },
            "recalculate_slots": True,
        },
        headers=user_a_headers,
    )
    assert patch_res.status_code == 200
    patched = patch_res.json()
    assert patched["status"] == "pending"
    assert patched["payload"]["activity_title"] == "React & TypeScript avancé"
    assert len(patched["payload"]["proposed_slots"]) == 1

    # Scénario 6 : Validation explicite -> crée le parcours, module, tâche objectif et le créneau calendrier
    accept_res = client.post(
        f"/api/v1/ai/proposals/{prop_id}/accept",
        json={},
        headers=user_a_headers,
    )
    assert accept_res.status_code == 200
    acc_data = accept_res.json()
    assert acc_data["status"] == "executed"
    assert acc_data["execution_result"]["created_events_count"] == 1
    assert acc_data["execution_result"]["learning_path_id"] is not None

    paths = client.get("/api/v1/learning/paths", headers=user_a_headers).json()
    assert len(paths) == 1
    assert paths[0]["title"] == "React & TypeScript avancé"

    tasks = client.get("/api/v1/tasks", headers=user_a_headers).json()
    assert len(tasks) == 1
    assert tasks[0]["proposal_id"] == prop_id

    events = client.get("/api/v1/schedule", headers=user_a_headers).json()
    assert len(events) == 1
    assert events[0]["title"] == "React & TypeScript avancé"
    assert events[0]["source"] == "ai_proposal"

    # Scénario 10 : Double validation refusée (409) sans aucun doublon
    second_accept = client.post(
        f"/api/v1/ai/proposals/{prop_id}/accept",
        json={},
        headers=user_a_headers,
    )
    assert second_accept.status_code == 409
    assert len(client.get("/api/v1/schedule", headers=user_a_headers).json()) == 1
    assert len(client.get("/api/v1/learning/paths", headers=user_a_headers).json()) == 1


def test_02_no_available_slots_returns_not_recommended_without_inventing_times(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénario 2 : Demande sans créneau disponible sur 7 jours -> NOT_RECOMMENDED,
    aucune disponibilité inventée, proposition Parking uniquement.
    """
    # Sature chacun des 7 prochains jours avec 6h de cours/réunions (>= 300 min/jour)
    for offset in range(7):
        res = client.post(
            "/api/v1/schedule",
            json={
                "title": f"Bloc intensif jour {offset}",
                "type": "course",
                "starts_at": _local_dt(offset, 8, 0).isoformat(),
                "ends_at": _local_dt(offset, 14, 0).isoformat(),
            },
            headers=user_a_headers,
        )
        assert res.status_code == 201

    conv_id = _new_conversation(client, user_a_headers, "Calendrier saturé")
    turn = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je voudrais suivre une formation complète en Rust cette semaine."},
        headers=user_a_headers,
    )
    assert turn.status_code == 201
    prop = turn.json()["proposals"][0]
    assert prop["payload"]["decision"] == "NOT_RECOMMENDED"
    assert prop["payload"]["park_only"] is True
    assert prop["payload"]["proposed_slots"] == []
    assert "NON RECOMMANDÉE POUR LE MOMENT" in turn.json()["assistant_message"]["content"]


def test_03_university_course_conflict_is_flagged_and_rejected_by_validator(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénario 3 : Demande entrant en conflit avec un cours universitaire (Java 18h-21h demain)
    -> conflit détecté, cours jamais écrasé, créneau alternatif hors cours, et rejet 409 si forcé.
    """
    java_start = _local_dt(1, 18, 0)
    java_end = _local_dt(1, 21, 0)
    ev = client.post(
        "/api/v1/schedule",
        json={
            "title": "Programmation Java",
            "type": "course",
            "source": "timetable_import",
            "starts_at": java_start.isoformat(),
            "ends_at": java_end.isoformat(),
        },
        headers=user_a_headers,
    )
    assert ev.status_code == 201

    conv_id = _new_conversation(client, user_a_headers, "Conflit cours Java")
    turn = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={
            "content": "Je voudrais apprendre les bases de Docker demain de 18h à 20h.",
        },
        headers=user_a_headers,
    )
    assert turn.status_code == 201
    data = turn.json()
    reply = data["assistant_message"]["content"]
    prop = data["proposals"][0]

    assert prop["payload"]["decision"] == "ACCEPTABLE_WITH_CONDITIONS"
    assert any("Programmation Java" in c for c in prop["payload"]["conditions"])
    assert "Programmation Java" in reply

    # Aucun créneau proposé ne chevauche 18h-21h demain
    for slot in prop["payload"]["proposed_slots"]:
        s_dt = datetime.fromisoformat(slot["starts_at"])
        e_dt = datetime.fromisoformat(slot["ends_at"])
        assert not (s_dt < java_end and java_start < e_dt)

    # Tenter de forcer un créneau sur le cours de Java lors de l'acceptation échoue avec 409
    bad_slot = {
        "day_label": "Demain",
        "local_date": java_start.astimezone(ZoneInfo("Africa/Dakar")).date().isoformat(),
        "local_start_time": "18:30",
        "local_end_time": "20:00",
        "starts_at": _local_dt(1, 18, 30).isoformat(),
        "ends_at": _local_dt(1, 20, 0).isoformat(),
        "duration_minutes": 90,
    }
    forced = client.post(
        f"/api/v1/ai/proposals/{prop['id']}/accept",
        json={"payload_overrides": {"proposed_slots": [bad_slot]}},
        headers=user_a_headers,
    )
    assert forced.status_code == 409
    assert forced.json()["error"]["code"] == "UNIVERSITY_COURSE_CONFLICT"


def test_04_weekly_overload_triggers_conditions_or_not_recommended(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénario 4 : Demande qui surcharge une semaine déjà très chargée (>= 25h + tâches critiques).
    """
    # 6 jours x 4h = 24h (1440 min) + 1 jour x 3h = 27h (1620 min >= 1500) + 3 tâches critiques
    for offset in range(6):
        assert (
            client.post(
                "/api/v1/schedule",
                json={
                    "title": f"Cours magistral {offset}",
                    "type": "course",
                    "starts_at": _local_dt(offset, 8, 0).isoformat(),
                    "ends_at": _local_dt(offset, 12, 0).isoformat(),
                },
                headers=user_a_headers,
            ).status_code
            == 201
        )
    assert (
        client.post(
            "/api/v1/schedule",
            json={
                "title": "Projet tuteuré",
                "type": "project",
                "starts_at": _local_dt(6, 9, 0).isoformat(),
                "ends_at": _local_dt(6, 12, 0).isoformat(),
            },
            headers=user_a_headers,
        ).status_code
        == 201
    )
    for i in range(3):
        assert (
            client.post(
                "/api/v1/tasks",
                json={"title": f"Livrable critique {i+1}", "priority": "critical"},
                headers=user_a_headers,
            ).status_code
            == 201
        )

    conv_id = _new_conversation(client, user_a_headers, "Surcharge hebdomadaire")
    turn = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je voudrais apprendre Kubernetes cette semaine."},
        headers=user_a_headers,
    )
    assert turn.status_code == 201
    prop = turn.json()["proposals"][0]
    assert prop["payload"]["decision"] in ("ACCEPTABLE_WITH_CONDITIONS", "NOT_RECOMMENDED")
    assert len(prop["payload"]["conditions"]) >= 1


def test_05_dispersion_against_active_priority_triggers_stop_and_parking(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénario 5 : Nouvelle idée incompatible avec la priorité active -> STOP — DISPERSION DÉTECTÉE
    et proposition Parking sans programmation dans le calendrier.
    """
    assert (
        client.patch(
            "/api/v1/profile",
            json={"active_priority_title": "Finaliser le backend FastAPI et les migrations SQL"},
            headers=user_a_headers,
        ).status_code
        == 200
    )

    conv_id = _new_conversation(client, user_a_headers, "Nouvelle idée hors priorité")
    turn = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "J'ai une nouvelle idée : lancer un podcast hebdomadaire sur le design"},
        headers=user_a_headers,
    )
    assert turn.status_code == 201
    data = turn.json()
    reply = data["assistant_message"]["content"]
    assert "STOP — DISPERSION DÉTECTÉE." in reply

    prop = data["proposals"][0]
    assert prop["payload"]["decision"] == "NOT_RECOMMENDED"
    assert prop["payload"]["park_only"] is True
    assert prop["payload"]["proposed_slots"] == []

    # Accepter la recommandation place uniquement l'idée au Parking sans créer de créneau calendrier
    acc = client.post(f"/api/v1/ai/proposals/{prop['id']}/accept", json={}, headers=user_a_headers)
    assert acc.status_code == 200
    assert acc.json()["execution_result"]["entity"] == "parked_idea"
    assert client.get("/api/v1/schedule", headers=user_a_headers).json() == []
    tasks = client.get("/api/v1/tasks", headers=user_a_headers).json()
    assert len(tasks) == 1
    assert tasks[0]["status"] == "parked"


def test_07_09_reject_proposal_and_calendar_mutation_after_proposal(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénarios 7 et 9 :
    7. Proposition refusée -> rien n'est enregistré.
    9. Modification du calendrier après génération de la proposition -> acceptation bloquée (409 SCHEDULE_CONFLICT_DETECTED).
    """
    # Scénario 7 : Refus explicite
    conv1 = _new_conversation(client, user_a_headers, "Refus proposition")
    turn1 = client.post(
        f"/api/v1/ai/conversations/{conv1}/messages",
        json={"content": "Je voudrais apprendre TypeScript avancé."},
        headers=user_a_headers,
    )
    prop1_id = turn1.json()["proposals"][0]["id"]
    rej = client.post(
        f"/api/v1/ai/proposals/{prop1_id}/reject",
        json={"reason": "Pas maintenant"},
        headers=user_a_headers,
    )
    assert rej.status_code == 200
    assert rej.json()["status"] == "rejected"
    assert client.get("/api/v1/learning/paths", headers=user_a_headers).json() == []
    assert client.get("/api/v1/schedule", headers=user_a_headers).json() == []

    # Scénario 9 : Un événement vient occuper le premier créneau proposé APRÈS la génération de la proposition
    conv2 = _new_conversation(client, user_a_headers, "Conflit post-proposition")
    turn2 = client.post(
        f"/api/v1/ai/conversations/{conv2}/messages",
        json={"content": "Je voudrais apprendre GraphQL avec 1 séance par semaine."},
        headers=user_a_headers,
    )
    prop2 = turn2.json()["proposals"][0]
    first_slot = prop2["payload"]["proposed_slots"][0]

    # L'utilisateur ajoute manuellement un rendez-vous sur ce même créneau entretemps
    assert (
        client.post(
            "/api/v1/schedule",
            json={
                "title": "Réunion ajoutée entretemps",
                "type": "personal",
                "starts_at": first_slot["starts_at"],
                "ends_at": first_slot["ends_at"],
            },
            headers=user_a_headers,
        ).status_code
        == 201
    )

    # Lors de la validation finale, le backend détecte la collision survenue après la proposition (409)
    accept_conflict = client.post(
        f"/api/v1/ai/proposals/{prop2['id']}/accept",
        json={},
        headers=user_a_headers,
    )
    assert accept_conflict.status_code == 409
    assert accept_conflict.json()["error"]["code"] == "SCHEDULE_CONFLICT_DETECTED"
    # La proposition reste en attente pour permettre un recalcul et aucun parcours n'est créé
    assert client.get(f"/api/v1/ai/proposals/{prop2['id']}", headers=user_a_headers).json()["status"] == "pending"
    assert client.get("/api/v1/learning/paths", headers=user_a_headers).json() == []

    # L'utilisateur demande le recalcul sur un autre créneau libre puis valide
    recalc = client.patch(
        f"/api/v1/ai/proposals/{prop2['id']}",
        json={"payload_overrides": {}, "recalculate_slots": True},
        headers=user_a_headers,
    )
    assert recalc.status_code == 200
    accept_ok = client.post(
        f"/api/v1/ai/proposals/{prop2['id']}/accept",
        json={},
        headers=user_a_headers,
    )
    assert accept_ok.status_code == 200
    assert accept_ok.json()["status"] == "executed"


def test_11_follow_up_of_accepted_but_uncompleted_sessions(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Scénario 11 : Suivi d'une activité acceptée mais non réalisée ->
    ne la considère jamais comme terminée et recommande un ajustement plutôt que d'accumuler.
    """
    # Crée 2 créneaux passés de type "learning" sur les 3 derniers jours SANS séance d'étude complétée
    for past_offset in (-2, -1):
        res = client.post(
            "/api/v1/schedule",
            json={
                "title": f"Apprentissage React — Séance {abs(past_offset)}",
                "type": "learning",
                "starts_at": _local_dt(past_offset, 10, 0).isoformat(),
                "ends_at": _local_dt(past_offset, 11, 30).isoformat(),
            },
            headers=user_a_headers,
        )
        assert res.status_code == 201

    conv_id = _new_conversation(client, user_a_headers, "Suivi séances manquées")
    turn = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Fais le suivi de mon activité et de mes séances manquées cette semaine."},
        headers=user_a_headers,
    )
    assert turn.status_code == 201
    data = turn.json()
    reply = data["assistant_message"]["content"]

    assert "n’ont pas été effectuées" in reply
    assert "2 séance(s)" in reply
    assert "ajustement" in reply.lower()

    # Proposition d'ajustement léger (1 séance max, create_learning_path=False)
    assert len(data["proposals"]) == 1
    prop = data["proposals"][0]
    assert prop["payload"]["decision"] == "ACCEPTABLE_WITH_CONDITIONS"
    assert prop["payload"]["create_learning_path"] is False
    assert prop["payload"]["frequency_per_week"] == 1

    # Vérifie aussi que le bilan hebdomadaire signale ces séances non réalisées
    weekly = client.post("/api/v1/ai/weekly-review", headers=user_a_headers)
    assert weekly.status_code == 201
    assert "Suivi d’exécution" in weekly.json()["content"]
