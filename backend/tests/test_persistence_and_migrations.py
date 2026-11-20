from pathlib import Path
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app


def test_alembic_migrations_and_restart_persistence_with_isolation(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    db_file = tmp_path / "persisted.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    settings = Settings(
        app_env="local",
        allow_local_dev_auth=True,
        database_url=db_url,
    )

    # Instance 1 : écriture réelle sans auto_create_tables (prouve qu'Alembic a créé les tables)
    app1 = create_app(settings=settings, auto_create_tables=False)
    with TestClient(app1) as client1:
        login_a = client1.post(
            "/api/v1/auth/local-login",
            json={"email": "khadim@amireflow.local", "display_name": "Khadim"},
        )
        assert login_a.status_code == 200
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        task = client1.post(
            "/api/v1/tasks",
            json={"title": "Tester Alembic", "priority": "high", "due_at": "2026-11-20T18:00:00Z"},
            headers=headers_a,
        )
        assert task.status_code == 201
        task_id = task.json()["id"]

        client1.patch(
            "/api/v1/profile",
            json={"active_priority_task_id": task_id},
            headers=headers_a,
        )

        event = client1.post(
            "/api/v1/schedule",
            json={
                "title": "Cours BDD",
                "type": "course",
                "starts_at": "2026-11-19T09:00:00Z",
                "ends_at": "2026-11-19T11:00:00Z",
            },
            headers=headers_a,
        )
        assert event.status_code == 201

        session = client1.post(
            "/api/v1/sessions",
            json={
                "title": "Pratique SQL",
                "category": "Apprentissage",
                "started_at": "2026-11-19T14:00:00Z",
                "ended_at": "2026-11-19T15:00:00Z",
                "result": "Migrations validées.",
                "task_id": task_id,
            },
            headers=headers_a,
        )
        assert session.status_code == 201

        path = client1.post(
            "/api/v1/learning/paths",
            json={"title": "Parcours Cloud", "goal": "Déployer FastAPI", "status": "active"},
            headers=headers_a,
        )
        assert path.status_code == 201
        path_id = path.json()["id"]

        module = client1.post(
            "/api/v1/learning/modules",
            json={"path_id": path_id, "title": "Conteneurisation", "position": 1},
            headers=headers_a,
        )
        assert module.status_code == 201
        module_id = module.json()["id"]

        lesson = client1.post(
            "/api/v1/learning/lessons",
            json={"module_id": module_id, "title": "Dockerfile multi-stage", "status": "completed"},
            headers=headers_a,
        )
        assert lesson.status_code == 201

        skill = client1.post(
            "/api/v1/skills",
            json={"name": "SQLAlchemy", "domain": "Backend", "current_level": 3, "target_level": 4},
            headers=headers_a,
        )
        assert skill.status_code == 201
        skill_id = skill.json()["id"]

        evidence = client1.post(
            f"/api/v1/skills/{skill_id}/evidence",
            json={"type": "code", "description": "Dépôt Alembic Palier 2"},
            headers=headers_a,
        )
        assert evidence.status_code == 201

        project = client1.post(
            "/api/v1/projects",
            json={
                "name": "API Study OS",
                "goal": "Socle persistant complet",
                "status": "active",
                "next_action": "Tester la migration 0002",
                "deliverables": ["Schema SQL", "Tests Pytest"],
            },
            headers=headers_a,
        )
        assert project.status_code == 201
        project_id = project.json()["id"]

        conv = client1.post(
            "/api/v1/ai/conversations",
            json={"title": "Coaching SQL"},
            headers=headers_a,
        )
        assert conv.status_code == 201
        conv_id = conv.json()["id"]

        turn = client1.post(
            f"/api/v1/ai/conversations/{conv_id}/messages",
            json={"content": "Crée une tâche : « Préparer le bilan hebdo »"},
            headers=headers_a,
        )
        assert turn.status_code == 201
        assert len(turn.json()["proposals"]) == 1

        briefing = client1.post("/api/v1/ai/briefing", headers=headers_a)
        assert briefing.status_code == 201

    # Instance 2 : redémarrage simulé sur le même fichier SQLite
    app2 = create_app(settings=settings, auto_create_tables=False)
    with TestClient(app2) as client2:
        relogin_a = client2.post(
            "/api/v1/auth/local-login",
            json={"email": "khadim@amireflow.local"},
        )
        headers_a2 = {"Authorization": f"Bearer {relogin_a.json()['access_token']}"}

        profile = client2.get("/api/v1/profile", headers=headers_a2).json()
        assert profile["display_name"] == "Khadim"
        assert profile["active_priority_title"] == "Tester Alembic"

        tasks = client2.get("/api/v1/tasks", headers=headers_a2).json()
        assert len(tasks) == 1
        assert tasks[0]["due_at"].endswith("Z") or "+00:00" in tasks[0]["due_at"]

        events = client2.get("/api/v1/schedule", headers=headers_a2).json()
        assert len(events) == 1
        assert events[0]["title"] == "Cours BDD"

        sessions = client2.get("/api/v1/sessions", headers=headers_a2).json()
        assert len(sessions) == 1
        assert sessions[0]["duration_minutes"] == 60

        dash = client2.get("/api/v1/dashboard", headers=headers_a2).json()
        assert dash["session_summary"]["completed_count"] == 1

        overview = client2.get("/api/v1/learning/overview", headers=headers_a2).json()
        assert len(overview["paths"]) == 1
        assert len(overview["modules"]) == 1
        assert len(overview["lessons"]) == 1

        skills = client2.get("/api/v1/skills", headers=headers_a2).json()
        assert len(skills) == 1
        assert skills[0]["current_level"] == 3
        assert len(client2.get(f"/api/v1/skills/{skill_id}/evidence", headers=headers_a2).json()) == 1

        projects = client2.get("/api/v1/projects", headers=headers_a2).json()
        assert len(projects) == 1
        assert projects[0]["deliverables"] == ["Schema SQL", "Tests Pytest"]

        convs = client2.get("/api/v1/ai/conversations", headers=headers_a2).json()
        assert len(convs) == 1
        proposals = client2.get("/api/v1/ai/proposals", headers=headers_a2).json()
        assert len(proposals) == 1
        reports = client2.get("/api/v1/ai/reports", headers=headers_a2).json()
        assert len(reports) == 1

        # Second utilisateur totalement isolé
        login_b = client2.post(
            "/api/v1/auth/local-login",
            json={"email": "autre@amireflow.local"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
        assert client2.get("/api/v1/tasks", headers=headers_b).json() == []
        assert client2.get(f"/api/v1/tasks/{task_id}", headers=headers_b).status_code == 404
        assert client2.get("/api/v1/learning/overview", headers=headers_b).json()["paths"] == []
        assert client2.get("/api/v1/skills", headers=headers_b).json() == []
        assert client2.get("/api/v1/projects", headers=headers_b).json() == []
        assert client2.get(f"/api/v1/projects/{project_id}", headers=headers_b).status_code == 404
