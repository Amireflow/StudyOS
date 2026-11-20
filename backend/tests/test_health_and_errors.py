from fastapi.testclient import TestClient


def test_health_and_request_id(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["env"] == "local"
    assert body["database"] in {"ok", "memory"}
    assert response.headers["X-Request-ID"].startswith("req_")


def test_health_returns_503_without_leaking_secrets_when_db_fails(client: TestClient) -> None:
    class _BrokenEngine:
        def connect(self):
            raise RuntimeError("postgresql://postgres:super_secret_pw@db.internal:5432/postgres unreachable")

    original_engine = client.app.state.db_engine  # type: ignore[union-attr]
    client.app.state.db_engine = _BrokenEngine()  # type: ignore[union-attr]
    try:
        response = client.get("/health")
    finally:
        client.app.state.db_engine = original_engine  # type: ignore[union-attr]

    assert response.status_code == 503
    body = response.json()
    assert body == {"status": "degraded", "env": "local", "database": "error"}
    assert "super_secret_pw" not in response.text
    assert "db.internal" not in response.text


def test_openapi_documents_expected_v1_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    expected_paths = {
        "/api/v1/auth/local-login",
        "/api/v1/auth/me",
        "/api/v1/profile",
        "/api/v1/dashboard",
        "/api/v1/tasks",
        "/api/v1/tasks/{task_id}",
        "/api/v1/schedule",
        "/api/v1/schedule/duplicate-week",
        "/api/v1/schedule/{event_id}",
        "/api/v1/sessions",
        "/api/v1/sessions/{session_id}",
        "/api/v1/sessions/{session_id}/finish",
        "/api/v1/learning/overview",
        "/api/v1/learning/paths",
        "/api/v1/learning/modules",
        "/api/v1/learning/lessons",
        "/api/v1/skills",
        "/api/v1/skills/evidence",
        "/api/v1/skills/{skill_id}/evidence",
        "/api/v1/projects",
        "/api/v1/projects/{project_id}",
        "/api/v1/ai/tools",
        "/api/v1/ai/conversations",
        "/api/v1/ai/conversations/{conversation_id}",
        "/api/v1/ai/conversations/{conversation_id}/messages",
        "/api/v1/ai/proposals",
        "/api/v1/ai/proposals/{proposal_id}",
        "/api/v1/ai/proposals/{proposal_id}/accept",
        "/api/v1/ai/proposals/{proposal_id}/reject",
        "/api/v1/ai/briefing",
        "/api/v1/ai/weekly-review",
        "/api/v1/ai/reports",
    }
    assert expected_paths.issubset(set(paths.keys()))


def test_invalid_or_missing_token_returns_401_uniform_error(
    client: TestClient,
    strict_auth_client: TestClient,
) -> None:
    invalid_res = client.get("/api/v1/profile", headers={"Authorization": "Bearer invalid"})
    assert invalid_res.status_code == 401
    invalid_body = invalid_res.json()
    assert invalid_body["error"]["code"] == "UNAUTHORIZED"
    assert invalid_body["error"]["request_id"].startswith("req_")

    missing_res = strict_auth_client.get("/api/v1/profile")
    assert missing_res.status_code == 401
    assert missing_res.json()["error"]["code"] == "UNAUTHORIZED"


def test_validation_422_and_not_found_404_use_uniform_error_format(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    bad_res = client.post("/api/v1/tasks", json={"title": "A"}, headers=user_a_headers)
    assert bad_res.status_code == 422
    bad_body = bad_res.json()
    assert bad_body["error"]["code"] == "VALIDATION_ERROR"
    assert "title" in bad_body["error"]["message"]
    assert bad_body["error"]["request_id"].startswith("req_")

    not_found = client.get(
        "/api/v1/tasks/99999999-9999-9999-9999-999999999999",
        headers=user_a_headers,
    )
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "NOT_FOUND"


def test_cors_allows_idempotency_key_and_rls_covers_all_tables(client: TestClient) -> None:
    import re
    from pathlib import Path
    import app.models  # noqa: F401
    from app.core.database import Base

    preflight = client.options(
        "/api/v1/planning/generate",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
        },
    )
    assert preflight.status_code == 200
    allow_headers = (preflight.headers.get("access-control-allow-headers") or "").lower()
    assert "idempotency-key" in allow_headers

    rls_path = Path(__file__).resolve().parents[1] / "alembic" / "rls_supabase.sql"
    rls_sql = rls_path.read_text(encoding="utf-8")
    enabled_tables = set(
        re.findall(
            r'ALTER TABLE\s+(?:public\.)?"?([a-z0-9_]+)"?\s+ENABLE ROW LEVEL SECURITY',
            rls_sql,
            re.IGNORECASE,
        )
    )
    orm_tables = set(Base.metadata.tables.keys())
    assert enabled_tables == orm_tables


def test_root_endpoint_returns_service_metadata(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "service": "Amireflow Study OS API",
        "status": "ok",
        "health": "/health",
    }


def test_normalize_postgres_schemes_for_render_and_supabase() -> None:
    from app.core.database import normalize_database_url

    assert (
        normalize_database_url("postgres://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )
    assert (
        normalize_database_url("postgresql://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )


def test_render_production_app_dry_run_cors_and_docs_disabled(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.core.config import Settings
    from app.main import create_app

    prod_app = create_app(
        settings=Settings(
            app_env="production",
            allow_local_dev_auth=False,
            allow_insecure_local_ai_url=False,
            app_secret_key="render-production-secret-key-at-least-32-chars",
            ai_key_encryption_key="k1:MDAxMTIyMzM0NDU1NjY3Nzg4OTlhYWJiY2NkZGVlZmY=",
            auth_cookie_samesite="none",
            auth_jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json",
            auth_issuer="https://example.supabase.co/auth/v1",
            frontend_origin="https://amireflow-study-os-web.onrender.com",
            database_url=f"sqlite:///{(tmp_path / 'render_prod.db').as_posix()}",
        ),
        auto_create_tables=False,
    )
    with TestClient(prod_app) as prod_client:
        root_res = prod_client.get("/")
        assert root_res.status_code == 200
        assert root_res.json()["status"] == "ok"

        health_res = prod_client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["env"] == "production"
        assert health_res.json()["database"] == "ok"

        assert prod_client.get("/docs").status_code == 404

        cors_res = prod_client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://amireflow-study-os-web.onrender.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert cors_res.status_code == 200
        assert (
            cors_res.headers.get("access-control-allow-origin")
            == "https://amireflow-study-os-web.onrender.com"
        )
        assert cors_res.headers.get("access-control-allow-credentials") == "true"


def test_render_blueprint_declares_unified_single_service() -> None:
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    render_yaml = repo_root / "render.yaml"
    dockerfile = repo_root / "Dockerfile"
    content = render_yaml.read_text(encoding="utf-8")
    docker_content = dockerfile.read_text(encoding="utf-8")

    assert "FROM node:22-slim AS frontend-builder" in docker_content
    assert "FRONTEND_DIST_DIR=/app/frontend_dist" in docker_content
    assert "VITE_API_BASE_URL=/api/v1" in docker_content

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        yaml = None

    if yaml is not None:
        parsed = yaml.safe_load(content)
        assert len(parsed["services"]) == 1
        service = parsed["services"][0]
        assert service["name"] == "amireflow-study-os"
        assert service["runtime"] == "docker"
        assert service["dockerfilePath"] == "./Dockerfile"
        assert service["dockerContext"] == "."
        assert service["healthCheckPath"] == "/health"
        assert "preDeployCommand" not in service
        svc_env = {item["key"]: item for item in service["envVars"]}
        assert svc_env["APP_ENV"]["value"] == "production"
        assert svc_env["ALLOW_LOCAL_DEV_AUTH"]["value"] == "false"
        assert svc_env["AUTH_COOKIE_SAMESITE"]["value"] == "lax"
        assert svc_env["DATABASE_URL"]["sync"] is False
        assert svc_env["AI_KEY_ENCRYPTION_KEY"]["sync"] is False
    else:
        assert content.count("- type: web") == 1
        assert "name: amireflow-study-os" in content
        assert "runtime: docker" in content
        assert "dockerfilePath: ./Dockerfile" in content
        assert "healthCheckPath: /health" in content
        assert "preDeployCommand" not in content
        assert "value: lax" in content


def test_unified_spa_serving_assets_fallback_api_404_and_path_traversal_guard(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    from app.core.config import Settings
    from app.main import create_app

    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<!doctype html><html><body>SPA</body></html>", encoding="utf-8")
    (assets_dir / "app.js").write_text("console.log('studyos');", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("TOP_SECRET", encoding="utf-8")

    unified_app = create_app(
        settings=Settings(
            app_env="production",
            allow_local_dev_auth=False,
            allow_insecure_local_ai_url=False,
            app_secret_key="render-production-secret-key-at-least-32-chars",
            ai_key_encryption_key="k1:MDAxMTIyMzM0NDU1NjY3Nzg4OTlhYWJiY2NkZGVlZmY=",
            auth_cookie_samesite="lax",
            auth_jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json",
            auth_issuer="https://example.supabase.co/auth/v1",
            frontend_origin="",
            frontend_dist_dir=str(dist_dir),
            render_external_url="https://amireflow-study-os.onrender.com",
            database_url=f"sqlite:///{(tmp_path / 'unified_prod.db').as_posix()}",
        ),
        auto_create_tables=False,
    )

    with TestClient(unified_app) as client:
        root_res = client.get("/")
        assert root_res.status_code == 200
        assert "SPA" in root_res.text
        assert root_res.headers.get("cache-control") == "no-cache"

        login_res = client.get("/login")
        assert login_res.status_code == 200
        assert "SPA" in login_res.text

        course_res = client.get("/courses/abc")
        assert course_res.status_code == 200
        assert "SPA" in course_res.text

        asset_res = client.get("/assets/app.js")
        assert asset_res.status_code == 200
        assert "console.log('studyos');" in asset_res.text
        assert asset_res.headers.get("cache-control") == "public, max-age=31536000, immutable"

        missing_asset = client.get("/assets/missing.js")
        assert missing_asset.status_code == 404

        missing_api = client.get("/api/v1/does-not-exist")
        assert missing_api.status_code == 404
        assert missing_api.json()["error"]["code"] == "NOT_FOUND"

        health_res = client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["database"] == "ok"

        traversal_res = client.get("/%2e%2e/secret.txt")
        assert "TOP_SECRET" not in traversal_res.text

        cors_res = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://amireflow-study-os.onrender.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert cors_res.status_code == 200
        assert cors_res.headers.get("access-control-allow-origin") == "https://amireflow-study-os.onrender.com"
        assert cors_res.headers.get("access-control-allow-credentials") == "true"
