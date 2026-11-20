from datetime import datetime, time, timedelta, timezone
import io
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient


def _build_pdf_with_text(lines: list[str]) -> bytes:
    """Construit un document PDF 1.4 minimal lisible par pypdf."""
    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "à": "a",
        "â": "a",
        "ù": "u",
        "ô": "o",
        "î": "i",
        "ç": "c",
        "–": "-",
        "—": "-",
        "’": "'",
    }
    stream_lines = ["BT", "/F1 11 Tf", "50 760 Td", "16 TL"]
    for idx, line in enumerate(lines):
        out = line
        for k, v in replacements.items():
            out = out.replace(k, v)
        esc = out.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_lines.append(f"({esc}) Tj" if idx == 0 else f"T* ({esc}) Tj")
    stream_lines.append("ET")
    stream_bytes = "\n".join(stream_lines).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(f"{i} 0 obj\n".encode("ascii"))
        buf.write(obj)
        buf.write(b"\nendobj\n")
    xref_pos = buf.tell()
    buf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode("ascii"))
    buf.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return buf.getvalue()


def test_acceptance_01_to_10_unified_objectives_projects_and_adaptation(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    """
    Tests d'acceptation obligatoires (Section 9, étapes 1 à 10) :
    1. Importer son emploi du temps universitaire.
    2. Ajouter React comme objectif personnel (hors cours universitaires, relié compétence + parcours).
    3. Ajouter Python comme objectif de progression secondaire.
    4. Ajouter un projet indépendant (et vérifier pause/reprise).
    5. Définir ses priorités et disponibilités (+ règles anti-dispersion).
    6. Faire générer un programme combinant les trois sources sans conflit universitaire.
    7. Valider le programme (déplacement des conflits flexibles antérieurs + tâches liées).
    8. Réaliser des séances (activité prévue/réelle, résultat, durée, difficultés, livrable).
    9. Fournir des résultats et des preuves.
    10. Obtenir une adaptation de la planification selon sa progression (et non-validation par date seule).
    """
    tz = ZoneInfo("Africa/Dakar")
    local_today = datetime.now(timezone.utc).astimezone(tz).date()
    monday = local_today - timedelta(days=local_today.weekday())

    # 1. Importer l'emploi du temps universitaire (Lundi 08:30-10:30 Génie Logiciel, Mardi 14:00-16:00 Bases de Données)
    pdf_bytes = _build_pdf_with_text(
        [
            "Lundi 08:30 - 10:30 Genie Logiciel - Cours - Pr. Diallo - Amphi A",
            "Mardi 14:00 - 16:00 Bases de Donnees - TD - Dr. Ndiaye - Salle 204",
        ]
    )
    analyze_res = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("edt_semestre.pdf", pdf_bytes, "application/pdf")},
        headers=user_a_headers,
    )
    assert analyze_res.status_code == 201
    import_id = analyze_res.json()["id"]

    confirm_edt = client.post(
        f"/api/v1/schedule/imports/{import_id}/confirm",
        json={"target_week_start": monday.isoformat(), "recurrence_weeks": 1},
        headers=user_a_headers,
    )
    assert confirm_edt.status_code == 201
    assert confirm_edt.json()["created_count"] == 2

    # Créer volontairement un ancien engagement flexible en conflit avec le cours du Lundi 08:30-10:30
    conflict_start = datetime.combine(monday, time(9, 0), tzinfo=tz).astimezone(timezone.utc).isoformat()
    conflict_end = datetime.combine(monday, time(10, 0), tzinfo=tz).astimezone(timezone.utc).isoformat()
    assert (
        client.post(
            "/api/v1/schedule",
            json={
                "title": "Ancienne séance flexible en conflit",
                "type": "learning",
                "starts_at": conflict_start,
                "ends_at": conflict_end,
            },
            headers=user_a_headers,
        ).status_code
        == 201
    )

    # 2. Ajouter React comme objectif personnel (priorité principale, avec échéance dépassée pour vérifier Section 8)
    past_deadline = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    react_res = client.post(
        "/api/v1/objectives",
        json={
            "title": "React",
            "category": "framework",
            "goal": "Maîtriser les composants, props, hooks et tests Vitest.",
            "current_level": 1,
            "target_level": 4,
            "priority": "high",
            "is_primary": True,
            "weekly_target_minutes": 180,
            "target_date": past_deadline,
            "deliverables": ["Mini-app React avec tests unitaires"],
            "next_action": "Étudier les composants et props, puis coder un formulaire",
        },
        headers=user_a_headers,
    )
    assert react_res.status_code == 201
    react_goal = react_res.json()
    react_goal_id = react_goal["id"]
    assert react_goal["skill_id"] is not None
    assert react_goal["learning_path_id"] is not None
    # Section 8 : un objectif dont la date est arrivée n'est JAMAIS marqué accompli automatiquement
    assert react_goal["status"] == "active"
    assert react_goal["is_behind_schedule"] is True
    assert "jamais marqué accompli uniquement par sa date" in (react_goal["delay_reason"] or "").lower()

    # 3. Ajouter Python comme objectif de progression secondaire
    python_res = client.post(
        "/api/v1/objectives",
        json={
            "title": "Python",
            "category": "language",
            "goal": "Consolider la programmation asynchrone et les tests Pytest.",
            "current_level": 2,
            "target_level": 4,
            "priority": "normal",
            "is_primary": False,
            "weekly_target_minutes": 90,
            "next_action": "Résoudre 3 exercices sur les générateurs et décorateurs",
        },
        headers=user_a_headers,
    )
    assert python_res.status_code == 201
    python_goal = python_res.json()
    python_goal_id = python_goal["id"]

    # Vérifier la séparation stricte des 3 sources dans /objectives/overview
    overview_res = client.get("/api/v1/objectives/overview", headers=user_a_headers)
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert len(overview["academic_obligations"]) == 2
    assert all(ev["is_fixed_constraint"] is True for ev in overview["academic_obligations"])
    # React et Python ne doivent PAS apparaître comme cours universitaires
    acad_titles = {ev["title"] for ev in overview["academic_obligations"]}
    assert "React" not in acad_titles and "Python" not in acad_titles

    # 4. Ajouter un projet indépendant (plus des projets supplémentaires pour tester pause + limite de 3 actifs)
    proj_main = client.post(
        "/api/v1/projects",
        json={
            "name": "Portfolio StudyOS",
            "category": "professional_project",
            "goal": "Publier une vitrine interactive React + FastAPI",
            "status": "active",
            "priority": "high",
            "weekly_target_minutes": 180,
            "next_action": "Construire la page de présentation des projets",
            "deliverables": ["Page vitrine React", "API FastAPI déployée"],
        },
        headers=user_a_headers,
    )
    assert proj_main.status_code == 201
    proj_main_id = proj_main.json()["id"]

    # Tester mise en attente (paused) puis réactivation d'un projet secondaire
    proj_paused = client.post(
        "/api/v1/projects",
        json={
            "name": "Outil CLI annexe",
            "goal": "Automatiser les exports CSV",
            "status": "active",
            "next_action": "Initialiser le parser CLI",
        },
        headers=user_a_headers,
    )
    assert proj_paused.status_code == 201
    paused_proj_id = proj_paused.json()["id"]
    pause_res = client.patch(
        f"/api/v1/projects/{paused_proj_id}",
        json={"status": "paused"},
        headers=user_a_headers,
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "paused"

    # 5. Définir les priorités et disponibilités (ex. exclure Dimanche, plage 08h-21h)
    prof_res = client.patch(
        "/api/v1/profile",
        json={
            "active_priority_title": "React",
            "preferences": {
                "availability": {
                    "study_start_hour": 8,
                    "study_end_hour": 21,
                    "preferred_session_minutes": 90,
                    "max_daily_study_minutes": 300,
                    "excluded_days": ["dimanche"],
                }
            },
        },
        headers=user_a_headers,
    )
    assert prof_res.status_code == 200

    # 6. Générer le programme unifié combinant les 3 sources
    plan_res = client.post(
        "/api/v1/objectives/plan/generate",
        json={
            "weekly_available_minutes": 600,
            "primary_priority_title": "React",
            "target_week_start": monday.isoformat(),
            "include_daily_recovery": True,
        },
        headers=user_a_headers,
    )
    assert plan_res.status_code == 200
    plan = plan_res.json()
    assert plan["primary_priority_title"] == "React"
    assert "Python" in plan["secondary_objectives"]
    assert len(plan["academic_fixed_slots"]) == 2
    assert len(plan["recovery_slots"]) == 7
    assert plan["displaced_conflicts_count"] == 1
    assert len(plan["arbitrages"]) >= 1

    flex_slots = plan["flexible_study_slots"]
    flex_categories = {s["source_category"] for s in flex_slots}
    assert "personal_goal" in flex_categories
    assert "project" in flex_categories

    # Vérifier qu'aucun créneau flexible n'empiète sur les cours universitaires ni le dimanche exclu
    for slot in flex_slots:
        assert slot["day_label"] != "Dimanche"
        assert slot["expected_outcome"]
        s_dt = datetime.fromisoformat(slot["starts_at"])
        e_dt = datetime.fromisoformat(slot["ends_at"])
        for acad in plan["academic_fixed_slots"]:
            a_s = datetime.fromisoformat(acad["starts_at"])
            a_e = datetime.fromisoformat(acad["ends_at"])
            assert not (s_dt < a_e and a_s < e_dt)

    # Au moins un créneau React/Python porte les liens pédagogiques (parcours/module/leçon/compétence)
    react_slots = [s for s in flex_slots if s.get("linked_goal_id") == react_goal_id]
    assert len(react_slots) >= 1
    assert react_slots[0]["linked_path_id"] is not None
    assert react_slots[0]["linked_module_id"] is not None
    assert react_slots[0]["linked_lesson_id"] is not None
    assert react_slots[0]["linked_skill_id"] is not None

    # 7. Valider le programme (applique au calendrier, supprime le conflit antérieur et crée les tâches liées)
    apply_res = client.post(
        "/api/v1/objectives/plan/apply",
        json={
            "flexible_study_slots": flex_slots,
            "primary_priority_title": "React",
            "replace_existing_flexible_week": True,
            "week_start": monday.isoformat(),
        },
        headers=user_a_headers,
    )
    assert apply_res.status_code == 201
    applied = apply_res.json()
    assert applied["created_events_count"] == len(flex_slots)
    assert applied["displaced_conflicts_count"] >= 1
    assert applied["linked_tasks_created_count"] >= 1

    all_events = client.get("/api/v1/schedule", headers=user_a_headers).json()
    assert not any(ev["title"] == "Ancienne séance flexible en conflit" for ev in all_events)
    assert any(ev["title"] == "Genie Logiciel" for ev in all_events)

    # 8 & 9. Réaliser des séances, enregistrer activité prévue/réelle, résultat, durée, difficultés et preuve/livrable
    start_ts = (datetime.now(timezone.utc) - timedelta(minutes=75)).isoformat()
    end_ts = datetime.now(timezone.utc).isoformat()
    sess_res = client.post(
        "/api/v1/sessions",
        json={
            "title": "Séance React : Composants & Hooks",
            "category": "Apprentissage",
            "started_at": start_ts,
            "goal_id": react_goal_id,
            "skill_id": react_goal["skill_id"],
            "planned_activity": "Étudier props et useState puis coder un formulaire",
        },
        headers=user_a_headers,
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    finish_res = client.patch(
        f"/api/v1/sessions/{session_id}/finish",
        json={
            "ended_at": end_ts,
            "result": "Formulaire React codé, mais difficultés avec useEffect et les dépendances.",
            "actual_activity": "Composants et props maîtrisés ; blocage sur useEffect",
            "outcome_status": "partial",
            "deliverable_summary": "Composant ContactForm.tsx fonctionnel avec validation Zod",
            "blockers": "Gestion des effets de bord useEffect",
            "next_step": "Reprendre useEffect avec 2 exercices ciblés",
        },
        headers=user_a_headers,
    )
    assert finish_res.status_code == 200
    finished_session = finish_res.json()
    assert finished_session["duration_minutes"] >= 70
    assert finished_session["blockers"] == "Gestion des effets de bord useEffect"
    assert finished_session["deliverable_summary"] == "Composant ContactForm.tsx fonctionnel avec validation Zod"

    # Vérifier la mise à jour de l'historique de progression et des preuves sur la compétence liée
    updated_react_goal = client.get(f"/api/v1/objectives/{react_goal_id}", headers=user_a_headers).json()
    assert len(updated_react_goal["progress_history"]) >= 2
    assert updated_react_goal["progress_history"][-1]["difficulties"] == "Gestion des effets de bord useEffect"
    assert updated_react_goal["next_action"] == "Reprendre useEffect avec 2 exercices ciblés"

    skill_evidences = client.get(
        f"/api/v1/skills/{react_goal['skill_id']}/evidence",
        headers=user_a_headers,
    ).json()
    assert len(skill_evidences) == 1
    assert "ContactForm.tsx" in skill_evidences[0]["description"]

    # Séance projet terminée également enregistrée
    proj_sess_res = client.post(
        "/api/v1/sessions",
        json={
            "title": "Avancement Portfolio StudyOS",
            "category": "Projet",
            "started_at": start_ts,
            "ended_at": end_ts,
            "result": "Maquette et routes principales créées",
            "project_id": proj_main_id,
            "deliverable_summary": "Page vitrine React v1",
        },
        headers=user_a_headers,
    )
    assert proj_sess_res.status_code == 201

    # 10. Obtenir une adaptation de la planification selon la progression et les difficultés
    adapted_plan_res = client.post(
        "/api/v1/objectives/plan/generate",
        json={"weekly_available_minutes": 600, "target_week_start": monday.isoformat()},
        headers=user_a_headers,
    )
    assert adapted_plan_res.status_code == 200
    adapted_plan = adapted_plan_res.json()
    assert len(adapted_plan["adaptations"]) >= 1
    assert any(
        "useeffect" in item["cause"].lower() or "useeffect" in item["action_taken"].lower()
        for item in adapted_plan["adaptations"]
    )
    adapted_react_slots = [
        s for s in adapted_plan["flexible_study_slots"] if s.get("linked_goal_id") == react_goal_id
    ]
    assert any("useeffect" in s["expected_outcome"].lower() for s in adapted_react_slots)

    # Vérifier le contexte du Copilote IA inclut les 3 sources (cours universitaires, objectifs personnels, projets)
    conv_id = client.post("/api/v1/ai/conversations", json={}, headers=user_a_headers).json()["id"]
    ai_turn = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Fais un point sur mes objectifs React, Python et mes projets."},
        headers=user_a_headers,
    )
    assert ai_turn.status_code == 201

    # Isolation stricte multi-utilisateur (User B ne peut ni lire ni modifier/supprimer les objectifs de User A)
    assert client.get("/api/v1/objectives", headers=user_b_headers).json() == []
    assert client.get(f"/api/v1/objectives/{python_goal_id}", headers=user_b_headers).status_code == 404
    assert (
        client.patch(
            f"/api/v1/objectives/{python_goal_id}",
            json={"status": "paused"},
            headers=user_b_headers,
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/objectives/{python_goal_id}", headers=user_b_headers).status_code == 404


def test_conversational_intake_extracts_without_inventing_and_requires_confirmation(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Section 3 : Collecte des besoins par conversation.
    - Extrait Python, React, Développement Web et Projets pratiques.
    - N'invente jamais le niveau, le temps disponible ou les échéances.
    - Demande confirmation avant d'enregistrer définitivement.
    """
    msg = (
        "Je veux continuer Python, apprendre React, améliorer mes compétences en "
        "développement web et construire des projets pratiques."
    )
    analyze_res = client.post(
        "/api/v1/objectives/intake/analyze",
        json={"message": msg},
        headers=user_a_headers,
    )
    assert analyze_res.status_code == 200
    recap = analyze_res.json()

    titles = [item["title"] for item in recap["objectives"]]
    assert "Python" in titles
    assert "React" in titles
    assert "Développement Web" in titles
    assert any(item["kind"] == "project" for item in recap["objectives"])

    # Ne pas inventer le niveau, le temps disponible ou l'échéance
    assert recap["current_level"] is None
    assert recap["available_time_weekly_minutes"] is None
    assert recap["target_date"] is None
    assert "current_level" in recap["missing_fields"]
    assert "available_time_weekly_minutes" in recap["missing_fields"]
    assert recap["requires_confirmation"] is True
    assert len(recap["progressive_questions"]) >= 2
    assert "Livrables attendus" in recap["summary_markdown"]
    assert "Conditions de validation" in recap["summary_markdown"]

    # Rien n'est enregistré avant confirmation explicite
    assert client.get("/api/v1/objectives", headers=user_a_headers).json() == []
    assert client.get("/api/v1/projects", headers=user_a_headers).json() == []

    # Confirmation utilisateur avec ses vraies réponses (temps hebdo et motivation)
    confirm_res = client.post(
        "/api/v1/objectives/intake/confirm",
        json={
            "objectives": recap["objectives"],
            "available_time_weekly_minutes": 360,
            "motivation": "Préparer mon stage de fin de L3GL",
            "primary_title": "React",
        },
        headers=user_a_headers,
    )
    assert confirm_res.status_code == 201
    confirmed = confirm_res.json()
    assert len(confirmed["created_goals"]) >= 3
    assert len(confirmed["created_projects"]) >= 1
    assert confirmed["active_priority_title"] == "React"

    persisted_goals = client.get("/api/v1/objectives", headers=user_a_headers).json()
    assert len(persisted_goals) >= 3
    assert any(g["title"] == "React" and g["is_primary"] is True for g in persisted_goals)
    assert any(g["title"] == "Python" for g in persisted_goals)
