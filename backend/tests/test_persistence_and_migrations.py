from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
import app.models  # noqa: F401
from app.core.config import Settings
from app.core.database import Base, create_db_engine
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
            json={"name": "SQLAlchemy", "domain": "Backend", "current_level": 0, "target_level": 4},
            headers=headers_a,
        )
        assert skill.status_code == 201
        skill_id = skill.json()["id"]

        evidence = client1.post(
            f"/api/v1/skills/{skill_id}/evidence",
            json={"type": "code", "description": "Dépôt Alembic Palier 2 avec tests de migration"},
            headers=headers_a,
        )
        assert evidence.status_code == 201
        ev_id = evidence.json()["id"]

        assessment = client1.post(
            f"/api/v1/skills/{skill_id}/assessments",
            json={"target_level": 1, "path_id": path_id, "module_id": module_id},
            headers=headers_a,
        )
        assert assessment.status_code == 201
        assessment_id = assessment.json()["id"]
        client1.post(
            f"/api/v1/skills/{skill_id}/assessments/{assessment_id}/submit",
            json={
                "submission_text": (
                    "Les migrations Alembic garantissent l'évolution reproductible du schéma "
                    "parce que chaque révision versionne upgrade et downgrade et gère les erreurs."
                ),
                "submission_code": "def upgrade() -> None:\n    op.create_table('skill_assessments', ...)",
                "evidence_ids": [ev_id],
            },
            headers=headers_a,
        )
        client1.post(
            f"/api/v1/skills/{skill_id}/assessments/{assessment_id}/evaluate",
            headers=headers_a,
        )
        val_res = client1.post(
            f"/api/v1/skills/{skill_id}/assessments/{assessment_id}/validate",
            headers=headers_a,
        )
        assert val_res.status_code == 200

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

        course = client1.post(
            "/api/v1/courses",
            json={"subject": "Python", "language": "fr", "total_levels": 3, "link_skill": False},
            headers=headers_a,
        )
        assert course.status_code == 201
        course_id = course.json()["id"]

        goal = client1.post(
            "/api/v1/objectives",
            json={
                "title": "React",
                "category": "framework",
                "goal": "Maîtriser React et Vitest",
                "weekly_target_minutes": 180,
                "is_primary": False,
                "create_linked_entities": False,
            },
            headers=headers_a,
        )
        assert goal.status_code == 201
        goal_id = goal.json()["id"]

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
        assert skills[0]["current_level"] == 1
        assert len(client2.get(f"/api/v1/skills/{skill_id}/evidence", headers=headers_a2).json()) == 1
        assessments = client2.get(f"/api/v1/skills/{skill_id}/assessments", headers=headers_a2).json()
        assert len(assessments) == 1
        assert assessments[0]["status"] == "approved"

        projects = client2.get("/api/v1/projects", headers=headers_a2).json()
        assert len(projects) == 1
        assert projects[0]["deliverables"] == ["Schema SQL", "Tests Pytest"]

        convs = client2.get("/api/v1/ai/conversations", headers=headers_a2).json()
        assert len(convs) == 1
        proposals = client2.get("/api/v1/ai/proposals", headers=headers_a2).json()
        assert len(proposals) == 1
        reports = client2.get("/api/v1/ai/reports", headers=headers_a2).json()
        assert len(reports) == 1

        courses = client2.get("/api/v1/courses", headers=headers_a2).json()
        assert len(courses) == 1
        assert courses[0]["subject"] == "Python"
        assert courses[0]["current_level"] == 1
        course_detail = client2.get(f"/api/v1/courses/{course_id}", headers=headers_a2).json()
        assert len(course_detail["levels"]) == 3
        assert len(course_detail["levels"][0]["lessons"]) == 4

        goals = client2.get("/api/v1/objectives", headers=headers_a2).json()
        assert len(goals) == 1
        assert goals[0]["id"] == goal_id
        assert goals[0]["title"] == "React"

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
        assert client2.get("/api/v1/courses", headers=headers_b).json() == []
        assert client2.get(f"/api/v1/courses/{course_id}", headers=headers_b).status_code == 404
        assert client2.get("/api/v1/objectives", headers=headers_b).json() == []
        assert client2.get(f"/api/v1/objectives/{goal_id}", headers=headers_b).status_code == 404


def test_migration_0004_preserves_historical_skill_levels_and_data(tmp_path: Path) -> None:
    """Vérifie que la migration 0004 préserve les compétences historiques déjà enregistrées à un niveau > 0."""
    backend_root = Path(__file__).resolve().parents[1]
    db_file = tmp_path / "historical_upgrade.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. Monter jusqu'à 0003 (avant le verrou pédagogique) et insérer une compétence historique au niveau 3
    command.upgrade(alembic_cfg, "0003_palier2_ai_copilot")
    legacy_skill_id = str(uuid4())
    user_id = "11111111-1111-1111-1111-111111111111"
    now_iso = datetime.now(timezone.utc).isoformat()

    engine = create_db_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO skills (id, user_id, name, domain, description, current_level, target_level, last_assessed_at, created_at, updated_at) "
                "VALUES (:id, :uid, :name, :domain, :desc, :lvl, :target, :assessed, :c_at, :u_at)"
            ),
            {
                "id": UUID(legacy_skill_id).hex,
                "uid": UUID(user_id).hex,
                "name": "Compétence Historique",
                "domain": "Architecture",
                "desc": "Niveau acquis avant migration 0004",
                "lvl": 3,
                "target": 5,
                "assessed": now_iso,
                "c_at": now_iso,
                "u_at": now_iso,
            },
        )
    engine.dispose()

    # 2. Appliquer la migration 0004 (head)
    command.upgrade(alembic_cfg, "head")

    # 3. Vérifier via l'API que le niveau historique 3 est intégralement préservé et que les métadonnées restent modifiables
    app = create_app(
        settings=Settings(app_env="local", allow_local_dev_auth=True, database_url=db_url),
        auto_create_tables=False,
    )
    headers = {"Authorization": f"Bearer dev:{user_id}"}
    with TestClient(app) as client:
        skills = client.get("/api/v1/skills", headers=headers).json()
        assert len(skills) == 1
        assert skills[0]["name"] == "Compétence Historique"
        assert skills[0]["current_level"] == 3
        assert skills[0]["target_level"] == 5

        patched = client.patch(
            f"/api/v1/skills/{skills[0]['id']}",
            json={"description": "Description mise à jour sans perdre le niveau 3"},
            headers=headers,
        )
        assert patched.status_code == 200
        assert patched.json()["current_level"] == 3


def test_alembic_reversible_downgrade_and_orm_schema_parity(tmp_path: Path) -> None:
    """Vérifie upgrade head -> downgrade base -> upgrade head et la parité exacte ORM vs Alembic."""
    backend_root = Path(__file__).resolve().parents[1]
    alembic_db = tmp_path / "alembic_parity.db"
    alembic_url = f"sqlite:///{alembic_db.as_posix()}"

    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", alembic_url)

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    check_engine = create_db_engine(alembic_url)
    try:
        insp_after_down = inspect(check_engine)
        remaining_app_tables = set(insp_after_down.get_table_names()) & set(
            Base.metadata.tables.keys()
        )
        assert remaining_app_tables == set()
    finally:
        check_engine.dispose()

    command.upgrade(cfg, "head")

    orm_db = tmp_path / "orm_parity.db"
    orm_engine = create_db_engine(f"sqlite:///{orm_db.as_posix()}")
    alembic_engine = create_db_engine(alembic_url)
    try:
        Base.metadata.create_all(orm_engine)
        alembic_insp = inspect(alembic_engine)
        orm_insp = inspect(orm_engine)

        alembic_tables = set(alembic_insp.get_table_names()) - {"alembic_version"}
        orm_tables = set(orm_insp.get_table_names())
        assert alembic_tables == orm_tables

        for table_name in sorted(orm_tables):
            alembic_cols = {c["name"] for c in alembic_insp.get_columns(table_name)}
            orm_cols = {c["name"] for c in orm_insp.get_columns(table_name)}
            assert alembic_cols == orm_cols, (
                f"Dérive de colonnes sur '{table_name}': "
                f"alembic-only={alembic_cols - orm_cols}, orm-only={orm_cols - alembic_cols}"
            )
    finally:
        orm_engine.dispose()
        alembic_engine.dispose()


def test_alembic_revision_ids_fit_widened_postgres_column_and_helper_widens_on_pg() -> None:
    """Vérifie que chaque identifiant de révision tient dans VARCHAR(128) et que env.py l'élargit sous PostgreSQL."""
    import ast
    import re
    from types import SimpleNamespace
    from sqlalchemy import text

    backend_root = Path(__file__).resolve().parents[1]
    versions_dir = backend_root / "alembic" / "versions"
    revision_files = sorted(versions_dir.glob("*.py"))
    assert len(revision_files) == 13

    for rev_file in revision_files:
        match = re.search(r'^revision(?:\s*:\s*str)?\s*=\s*"([^"]+)"', rev_file.read_text(encoding="utf-8"), re.M)
        assert match is not None, f"Révision absente dans {rev_file.name}"
        assert len(match.group(1)) <= 128

    env_path = backend_root / "alembic" / "env.py"
    tree = ast.parse(env_path.read_text(encoding="utf-8"), filename=str(env_path))
    fn_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_ensure_postgres_version_column_width"
    )
    namespace = {"text": text}
    exec(compile(ast.Module(body=[fn_node], type_ignores=[]), str(env_path), "exec"), namespace)
    widen_fn = namespace["_ensure_postgres_version_column_width"]

    class _FakeConn:
        def __init__(self, dialect_name: str) -> None:
            self.dialect = SimpleNamespace(name=dialect_name)
            self.statements: list[str] = []
            self.committed = False

        def execute(self, stmt) -> None:  # type: ignore[no-untyped-def]
            self.statements.append(str(stmt))

        def commit(self) -> None:
            self.committed = True

    sqlite_conn = _FakeConn("sqlite")
    widen_fn(sqlite_conn)
    assert sqlite_conn.statements == []
    assert sqlite_conn.committed is False

    pg_conn = _FakeConn("postgresql")
    widen_fn(pg_conn)
    assert pg_conn.committed is True
    assert len(pg_conn.statements) == 2
    assert "CREATE TABLE IF NOT EXISTS alembic_version" in pg_conn.statements[0]
    assert "VARCHAR(128)" in pg_conn.statements[0]
    assert "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)" in pg_conn.statements[1]
