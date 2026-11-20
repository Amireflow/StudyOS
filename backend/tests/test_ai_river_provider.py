import socket
from typing import Any
from fastapi.testclient import TestClient
import httpx
import pytest


def _mock_river_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    original_getaddrinfo = socket.getaddrinfo

    def fake_getaddrinfo(host: str, port: Any, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        if str(host).lower() in ("api.river.ai", "console.river.ai"):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("35.228.48.71", int(port or 443)))]
        return original_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
from app.ai.context_builder import BoundedUserContext
from app.ai.prompt_manager import PromptManager
from app.ai.provider import (
    OPENAI_DEFAULT_BASE_URL,
    RIVER_DEFAULT_BASE_URL,
    OpenAICompatibleAIProvider,
    RiverAIProvider,
    build_ai_provider_from_config,
    _parse_llm_json_output,
    _sanitize_ai_reply_dashes,
    build_ai_provider,
    canonicalize_provider_name,
    normalize_provider_base_url,
)
from app.ai.tool_registry import ToolRegistry
from app.core.config import Settings
from app.core.errors import AppError


def test_river_url_normalization_and_https_security_guard(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    assert canonicalize_provider_name("console.river.ai") == "river"
    assert canonicalize_provider_name("River_AI") == "river"
    assert normalize_provider_base_url("river", "") == RIVER_DEFAULT_BASE_URL
    assert normalize_provider_base_url("river", "console.river.ai") == RIVER_DEFAULT_BASE_URL
    assert normalize_provider_base_url("river", "https://console.river.ai/") == RIVER_DEFAULT_BASE_URL
    assert normalize_provider_base_url("river", "https://api.river.ai") == RIVER_DEFAULT_BASE_URL
    assert normalize_provider_base_url("river", "https://api.river.ai/v1/") == RIVER_DEFAULT_BASE_URL

    env_provider = build_ai_provider(
        Settings(
            ai_provider="river",
            ai_api_key="rk_env_test_12345678",
            ai_model="claude-3-7-sonnet",
            ai_base_url="https://console.river.ai",
        )
    )
    assert isinstance(env_provider, RiverAIProvider)
    assert env_provider._base_url == RIVER_DEFAULT_BASE_URL  # noqa: SLF001

    # Rejet d'une URL HTTP externe non localhost
    bad_res = client.post(
        "/api/v1/ai/provider/models",
        json={
            "provider": "river",
            "api_key": "rk_live_secret_1234",
            "base_url": "http://insecure.river.ai/v1",
        },
        headers=user_a_headers,
    )
    assert bad_res.status_code == 400
    assert bad_res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_river_models_discovery_with_api_key_and_invalid_key_handling(
    client: TestClient,
    user_a_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_river_dns(monkeypatch)
    captured_calls: list[dict[str, Any]] = []
    original_get = httpx.Client.get

    def fake_get(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        if not str(url).startswith("https://api.river.ai"):
            return original_get(self, url, **kwargs)
        headers = dict(kwargs.get("headers") or {})
        captured_calls.append({"url": url, "headers": headers})
        req = httpx.Request("GET", url, headers=headers)
        if headers.get("Authorization") == "Bearer rk_bad_key_0000":
            return httpx.Response(401, request=req, json={"error": {"message": "Unauthorized"}})
        return httpx.Response(
            200,
            request=req,
            json={
                "object": "list",
                "data": [
                    {
                        "id": "gpt-4o",
                        "owned_by": "openai",
                        "context_window": 128000,
                    },
                    {
                        "id": "claude-3-7-sonnet",
                        "display_name": "Claude 3.7 Sonnet",
                        "owned_by": "anthropic",
                        "context_length": 200000,
                    },
                    {
                        "id": "gpt-4o",
                        "owned_by": "duplicate-should-be-ignored",
                    },
                ],
            },
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    ok_res = client.post(
        "/api/v1/ai/provider/models",
        json={
            "provider": "console.river.ai",
            "api_key": "rk_valid_river_key_9999",
            "base_url": "https://console.river.ai",
        },
        headers=user_a_headers,
    )
    assert ok_res.status_code == 200
    body = ok_res.json()
    assert body["provider"] == "river"
    assert body["base_url"] == "https://api.river.ai/v1"
    assert body["count"] == 2
    assert [m["id"] for m in body["models"]] == ["claude-3-7-sonnet", "gpt-4o"]
    assert body["models"][0]["label"] == "Claude 3.7 Sonnet"
    assert body["models"][0]["owned_by"] == "anthropic"
    assert body["models"][0]["context_window"] == 200000

    assert len(captured_calls) == 1
    assert captured_calls[0]["url"] == "https://api.river.ai/v1/models"
    assert captured_calls[0]["headers"]["Authorization"] == "Bearer rk_valid_river_key_9999"

    # Clé rejetée par River AI -> 401 AI_INVALID_API_KEY
    err_res = client.post(
        "/api/v1/ai/provider/models",
        json={
            "provider": "river",
            "api_key": "rk_bad_key_0000",
        },
        headers=user_a_headers,
    )
    assert err_res.status_code == 401
    assert err_res.json()["error"]["code"] == "AI_INVALID_API_KEY"


def test_river_config_persistence_secret_masking_isolation_and_copilot_chat(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_river_dns(monkeypatch)
    secret_key = "rk_live_super_secret_token_abcd"

    # Initialement local sans clé
    initial_cfg = client.get("/api/v1/ai/provider/config", headers=user_a_headers)
    assert initial_cfg.status_code == 200
    assert initial_cfg.json()["provider"] == "local"
    assert initial_cfg.json()["has_api_key"] is False
    assert any(p["id"] == "river" for p in initial_cfg.json()["available_providers"])

    # Enregistrement River AI + modèle choisi
    saved_cfg = client.put(
        "/api/v1/ai/provider/config",
        json={
            "provider": "river",
            "api_key": secret_key,
            "base_url": "https://console.river.ai",
            "model": "claude-3-7-sonnet",
        },
        headers=user_a_headers,
    )
    assert saved_cfg.status_code == 200
    saved_body = saved_cfg.json()
    assert saved_body["provider"] == "river"
    assert saved_body["base_url"] == "https://api.river.ai/v1"
    assert saved_body["model"] == "claude-3-7-sonnet"
    assert saved_body["has_api_key"] is True
    assert saved_body["api_key_preview"] == "rk_l…abcd"
    assert secret_key not in str(saved_body)

    # La clé brute ne doit JAMAIS fuiter dans GET /profile même après un PATCH preferences
    profile_patch = client.patch(
        "/api/v1/profile",
        json={"preferences": {"compact": True}},
        headers=user_a_headers,
    )
    assert profile_patch.status_code == 200
    assert profile_patch.json()["preferences"] == {"compact": True}
    assert secret_key not in str(profile_patch.json())

    profile_get = client.get("/api/v1/profile", headers=user_a_headers)
    assert profile_get.status_code == 200
    assert profile_get.json()["preferences"] == {"compact": True}
    assert secret_key not in str(profile_get.json())

    # Rafraîchir les modèles sans renvoyer api_key réutilise la clé enregistrée côté serveur
    seen_get_auth: list[str] = []
    original_get = httpx.Client.get

    def fake_get_models(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        if not str(url).startswith("https://api.river.ai"):
            return original_get(self, url, **kwargs)
        auth = str((kwargs.get("headers") or {}).get("Authorization") or "")
        seen_get_auth.append(auth)
        req = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=req,
            json={"data": [{"id": "claude-3-7-sonnet", "owned_by": "river"}]},
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get_models)
    refresh_res = client.post(
        "/api/v1/ai/provider/models",
        json={"provider": "river"},
        headers=user_a_headers,
    )
    assert refresh_res.status_code == 200
    assert refresh_res.json()["count"] == 1
    assert seen_get_auth == [f"Bearer {secret_key}"]

    # Isolation stricte multi-utilisateur : B n'a pas accès à la clé de A
    cfg_b = client.get("/api/v1/ai/provider/config", headers=user_b_headers)
    assert cfg_b.status_code == 200
    assert cfg_b.json()["provider"] == "local"
    assert cfg_b.json()["has_api_key"] is False

    no_key_b = client.post(
        "/api/v1/ai/provider/models",
        json={"provider": "river"},
        headers=user_b_headers,
    )
    assert no_key_b.status_code == 400
    assert no_key_b.json()["error"]["code"] == "AI_API_KEY_REQUIRED"

    # Envoi d'un message au Copilote IA utilisant le fournisseur River AI + modèle choisi
    post_calls: list[dict[str, Any]] = []
    original_post = httpx.Client.post

    def fake_post_chat(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        if not str(url).startswith("https://api.river.ai"):
            return original_post(self, url, **kwargs)
        post_calls.append(
            {
                "url": url,
                "headers": dict(kwargs.get("headers") or {}),
                "json": dict(kwargs.get("json") or {}),
            }
        )
        req = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=req,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"reply": "Réponse générée via River AI.", '
                                '"proposals": [], "is_estimate": false, "missing_data": []}'
                            )
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post_chat)

    conv_res = client.post("/api/v1/ai/conversations", json={}, headers=user_a_headers)
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    msg_res = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Fais un point rapide sur ma journée."},
        headers=user_a_headers,
    )
    assert msg_res.status_code == 201
    assistant_msg = msg_res.json()["assistant_message"]
    assert assistant_msg["content"] == "Réponse générée via River AI."
    assert assistant_msg["metadata"]["provider"] == "river"
    assert assistant_msg["metadata"]["model"] == "claude-3-7-sonnet"

    assert len(post_calls) == 1
    assert post_calls[0]["url"] == "https://api.river.ai/v1/chat/completions"
    assert post_calls[0]["headers"]["Authorization"] == f"Bearer {secret_key}"
    assert post_calls[0]["json"]["model"] == "claude-3-7-sonnet"

    # Suppression de la clé et retour au moteur local
    cleared = client.put(
        "/api/v1/ai/provider/config",
        json={"provider": "local", "clear_api_key": True},
        headers=user_a_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["provider"] == "local"
    assert cleared.json()["has_api_key"] is False
    assert cleared.json()["api_key_preview"] is None


def test_ai_prompt_style_rule_and_reply_dash_sanitization() -> None:
    ctx = BoundedUserContext(
        included_scopes=["profile"],
        profile={"display_name": "Khadim", "timezone": "Africa/Dakar"},
    )
    prompt = PromptManager(ToolRegistry()).build_system_prompt(ctx)
    assert "tirets cadratins (`—`)" in prompt
    assert "demi-cadratins (`–`)" in prompt

    raw_sample = (
        "1. **Cadrer ta priorité active** — tes instructions mentionnent trois axes.\n"
        "2. **Construire un programme réaliste** — tu disposes de 3 créneaux (08:00–09:30, 10:00–11:00), "
        "marges de 15–20 min.\n"
        "3. **Créer un cours structuré** - par exemple Python.\n"
        "- élément de liste normal\n"
        "Une phrase — précision utile — fin de phrase, titre - précision, peut-être utile.\n"
        "Calcul simple : 10 - 3 = 7 et commande `pytest -q`.\n"
        "```python\nx = a - b  # — commentaire en code\n```\n"
        "STOP — DISPERSION DÉTECTÉE."
    )
    cleaned = _sanitize_ai_reply_dashes(raw_sample)

    assert "1. **Cadrer ta priorité active** : tes instructions mentionnent trois axes." in cleaned
    assert "2. **Construire un programme réaliste** : tu disposes de 3 créneaux (08:00 à 09:30, 10:00 à 11:00)" in cleaned
    assert "15 à 20 min" in cleaned
    assert "3. **Créer un cours structuré** : par exemple Python." in cleaned
    assert "\n- élément de liste normal\n" in cleaned
    assert "Une phrase, précision utile, fin de phrase, titre, précision, peut-être utile." in cleaned
    assert "10 - 3 = 7" in cleaned
    assert "`pytest -q`" in cleaned
    assert "```python\nx = a - b  # — commentaire en code\n```" in cleaned
    assert "STOP — DISPERSION DÉTECTÉE." in cleaned

    json_payload = (
        '{"reply": "1. **Cadrer ta priorité active** — détails (08:00–09:30).", '
        '"is_estimate": false, "missing_data": [], '
        '"proposals": [{"action_type": "create_task", "title": "**Tâche** — Révision", '
        '"explanation": "Créneau 14:00–16:00 — important", "payload": {"title": "Révision"}}]}'
    )
    parsed = _parse_llm_json_output(json_payload, ctx, "river", "deepseek-ai/DeepSeek-V4.1-Flash-1017")
    assert "—" not in parsed.reply
    assert "–" not in parsed.reply
    assert "**Cadrer ta priorité active** : détails (08:00 à 09:30)." in parsed.reply
    assert parsed.proposals[0].title == "**Tâche** : Révision"
    assert parsed.proposals[0].explanation == "Créneau 14:00 à 16:00, important"


def test_timetable_import_uses_configured_river_ai_for_image_analysis(
    client: TestClient,
    user_a_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_river_dns(monkeypatch)
    import io
    from PIL import Image

    client.put(
        "/api/v1/ai/provider/config",
        json={
            "provider": "river",
            "api_key": "rk_timetable_vision_key_1234",
            "model": "gpt-4o-mini",
        },
        headers=user_a_headers,
    )

    ai_calls: list[dict[str, Any]] = []
    original_post = httpx.Client.post

    def fake_post(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        if not str(url).startswith("https://api.river.ai"):
            return original_post(self, url, **kwargs)
        ai_calls.append({"url": url, "json": dict(kwargs.get("json") or {})})
        req = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=req,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"valid_from": "2026-11-16", "valid_until": "2026-12-20", '
                                '"courses": [{"subject": "Intelligence Artificielle", '
                                '"day_of_week": "Mercredi", "start_time": "10:00", "end_time": "12:00", '
                                '"session_type": "cours", "teacher": "Pr. Fall", "room": "Amphi B", '
                                '"group_name": "M1", "uncertain": false, "uncertainty_reasons": []}]}'
                            )
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    buf = io.BytesIO()
    Image.new("RGB", (120, 80), color=(255, 255, 255)).save(buf, format="PNG")
    png_bytes = buf.getvalue()

    res = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("capture_edt.png", png_bytes, "image/png")},
        headers=user_a_headers,
    )
    assert res.status_code == 201
    body = res.json()
    assert len(ai_calls) == 1
    assert ai_calls[0]["url"] == "https://api.river.ai/v1/chat/completions"
    assert len(body["extracted_courses"]) == 1
    course = body["extracted_courses"][0]
    assert course["subject"] == "Intelligence Artificielle"
    assert course["day_of_week"] == 2
    assert course["day_label"] == "Mercredi"
    assert course["start_time"] == "10:00"
    assert course["end_time"] == "12:00"
    assert course["room"] == "Amphi B"
    assert body["blocking_anomalies_count"] == 0




def test_official_openai_defaults_to_gpt62_sol_and_uses_responses_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class _FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"reply":"Réponse avec raisonnement GPT-6.","proposals":[],"is_estimate":false,"missing_data":[]}',
                            }
                        ],
                    }
                ]
            }

    def fake_request(method: str, url: str, **kwargs: Any) -> _FakeResponse:
        captured["method"] = method
        captured["url"] = url
        captured["body"] = kwargs.get("json_body") or {}
        captured["headers"] = kwargs.get("headers") or {}
        return _FakeResponse()

    monkeypatch.setattr("app.ai.provider.safe_http_request", fake_request)
    provider = build_ai_provider_from_config(
        provider="openai_compatible",
        api_key="sk-test-openai-key",
        model_name=None,
        base_url=OPENAI_DEFAULT_BASE_URL,
    )
    assert isinstance(provider, OpenAICompatibleAIProvider)
    assert provider._model_name == "gpt-6.2-sol"  # noqa: SLF001

    context = BoundedUserContext(
        included_scopes=["profile"],
        profile={"display_name": "Apprenant", "timezone": "Africa/Dakar"},
    )
    result = provider.generate_response(
        user_message="Aide-moi à choisir la meilleure méthode.",
        history=[],
        context=context,
        prompt_manager=PromptManager(ToolRegistry()),
    )

    assert result.reply == "Réponse avec raisonnement GPT-6."
    assert captured["method"] == "POST"
    assert captured["url"] == f"{OPENAI_DEFAULT_BASE_URL}/responses"
    assert captured["body"]["model"] == "gpt-6.2-sol"
    assert captured["body"]["reasoning"] == {"effort": "medium"}
    assert captured["body"]["store"] is False
    assert "temperature" not in captured["body"]
