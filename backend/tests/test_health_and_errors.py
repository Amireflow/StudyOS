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
