from fastapi.testclient import TestClient


def test_profile_auto_provisioning_and_update(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    get_res = client.get("/api/v1/profile", headers=user_a_headers)
    assert get_res.status_code == 200
    profile = get_res.json()
    assert profile["id"] == "11111111-1111-1111-1111-111111111111"
    assert profile["timezone"] == "Africa/Dakar"
    assert profile["display_name"] == "Utilisateur"

    patch_res = client.patch(
        "/api/v1/profile",
        json={
            "display_name": "Khadim",
            "timezone": "Europe/Paris",
            "active_priority_title": "Maîtriser FastAPI",
            "ai_instructions": "Explications concises avec exemples.",
        },
        headers=user_a_headers,
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["display_name"] == "Khadim"
    assert updated["timezone"] == "Europe/Paris"
    assert updated["active_priority_title"] == "Maîtriser FastAPI"
    assert updated["ai_instructions"] == "Explications concises avec exemples."


def test_profile_rejects_unknown_iana_timezone(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    res = client.patch(
        "/api/v1/profile",
        json={"timezone": "Mars/Olympus"},
        headers=user_a_headers,
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
