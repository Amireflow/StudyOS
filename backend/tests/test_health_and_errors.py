from fastapi.testclient import TestClient


def test_health_and_request_id(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "env": "local"}
    assert response.headers["X-Request-ID"].startswith("req_")


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
