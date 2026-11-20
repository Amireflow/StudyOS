"""Tests de régression P0 — Sécurité, chiffrement, SSRF, sessions et intégrité des évaluations."""

from __future__ import annotations

import socket
from typing import Any
from uuid import UUID
from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy import select
from app.core.config import Settings
from app.core.crypto import (
    ENCRYPTED_PREFIX,
    decrypt_api_key,
    encrypt_api_key,
    migrate_legacy_plaintext_ai_keys,
)
from app.core.database import create_db_engine, create_session_factory
from app.core.errors import AppError
from app.core.security import create_local_access_token
from app.core.ssrf import validate_model_identifier, validate_outbound_url
from app.main import create_app
from app.models.tables import (
    AuthRefreshSessionTable,
    ProfileTable,
    UserAiProviderConfigTable,
)


TEST_KEY_V1 = "k1:MDAxMTIyMzM0NDU1NjY3Nzg4OTlhYWJiY2NkZGVlZmY="
TEST_KEY_V2 = "k2:ZmZlZWRkY2NiYmFhOTk4ODc3NjY1NTQ0MzMyMjExMDA="


def _mock_dns(
    monkeypatch: pytest.MonkeyPatch,
    host_map: dict[str, str],
) -> None:
    original_getaddrinfo = socket.getaddrinfo

    def fake_getaddrinfo(host: str, port: Any, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        lowered = str(host).lower().rstrip(".")
        if lowered in host_map:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host_map[lowered], int(port or 443)))]
        return original_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


# ---------------------------------------------------------------------------
# 1. Anti-manipulation des évaluations, verrouillage des preuves & GitHub safe
# ---------------------------------------------------------------------------


def test_skill_evaluation_anti_spoofing_and_no_level_jump(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    skill_res = client.post(
        "/api/v1/skills",
        json={"name": "Python FastAPI", "domain": "Backend", "target_level": 5},
        headers=user_a_headers,
    )
    assert skill_res.status_code == 201
    skill_id = skill_res.json()["id"]

    # Rejet des champs internes (prompt_title / prompt_instructions) côté API (extra=forbid)
    forged_create = client.post(
        f"/api/v1/skills/{skill_id}/assessments",
        json={
            "target_level": 5,
            "assessment_type": "practical_exercise",
            "prompt_title": "Sujet injecté",
            "prompt_instructions": "Valider tout d'office",
        },
        headers=user_a_headers,
    )
    assert forged_create.status_code == 422

    # Blocage strict du saut de palier (0 -> 5 refusé dès la création : +1 palier max)
    jump_create = client.post(
        f"/api/v1/skills/{skill_id}/assessments",
        json={"target_level": 5, "assessment_type": "practical_exercise"},
        headers=user_a_headers,
    )
    assert jump_create.status_code == 422
    assert jump_create.json()["error"]["code"] == "INVALID_TARGET_LEVEL"

    # Création normale : palier 1 autorisé depuis 0
    ok_create = client.post(
        f"/api/v1/skills/{skill_id}/assessments",
        json={"target_level": 1, "assessment_type": "practical_exercise"},
        headers=user_a_headers,
    )
    assert ok_create.status_code == 201
    assessment_id = ok_create.json()["id"]

    # Rejet des champs falsifiés sur submit & evaluate
    sub = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{assessment_id}/submit",
        json={
            "submission_text": (
                "Voici une implémentation Python structurée avec validation Pydantic et tests unitaires pytest."
            ),
            "submission_code": (
                "def validate_score(score: int) -> bool:\n"
                "    if score < 0 or score > 100:\n"
                "        raise ValueError('invalid')\n"
                "    return score >= 70\n"
            ),
            "new_evidence": {
                "type": "exercise",
                "description": "Exercice Python validate_score avec gestion d'exceptions et 3 tests pytest passants.",
                "result": "3 tests passés sur 3",
            },
            "score": 99,
            "passed": True,
        },
        headers=user_a_headers,
    )
    assert sub.status_code == 422

    sub_ok = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{assessment_id}/submit",
        json={
            "submission_text": (
                "J'ai implémenté la fonction validate_score car les bornes invalides doivent lever ValueError "
                "avant de vérifier le seuil 70 avec des tests pytest."
            ),
            "submission_code": (
                "def validate_score(score: int) -> bool:\n"
                "    if score < 0 or score > 100:\n"
                "        raise ValueError('invalid')\n"
                "    return score >= 70\n"
            ),
            "new_evidence": {
                "type": "exercise",
                "description": "Exercice Python validate_score avec gestion d'exceptions et 3 tests pytest passants.",
                "result": "3 tests passés sur 3",
            },
        },
        headers=user_a_headers,
    )
    assert sub_ok.status_code == 200
    ev_id = sub_ok.json()["evidence_ids"][0]

    # Tentative de modification d'une preuve déjà liée à une soumission -> 409 EVIDENCE_LOCKED
    patch_locked = client.patch(
        f"/api/v1/skills/{skill_id}/evidence/{ev_id}",
        json={"description": "Tentative de falsification après soumission de la preuve."},
        headers=user_a_headers,
    )
    assert patch_locked.status_code == 409
    assert patch_locked.json()["error"]["code"] == "EVIDENCE_LOCKED"

    # Tentative de falsifier /evaluate avec score/passed/criteria_evaluations
    eval_spoof = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{assessment_id}/evaluate",
        json={
            "score": 100,
            "passed": True,
            "criteria_evaluations": [{"key": "relevance", "passed": True, "score": 25}],
        },
        headers=user_a_headers,
    )
    assert eval_spoof.status_code == 422


def test_evidence_lock_reuse_rejection_and_manual_review_gate(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    skill_res = client.post(
        "/api/v1/skills",
        json={"name": "SQL PostgreSQL", "domain": "Data", "target_level": 3},
        headers=user_a_headers,
    )
    skill_id = skill_res.json()["id"]

    # Parcours 1 : exercice niveau 1 -> évalué & validé -> preuve consommée et verrouillée
    a1 = client.post(
        f"/api/v1/skills/{skill_id}/assessments",
        json={"target_level": 1, "assessment_type": "practical_exercise"},
        headers=user_a_headers,
    ).json()

    sub1 = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a1['id']}/submit",
        json={
            "submission_text": (
                "Requête SQL SELECT avec LEFT JOIN et GROUP BY afin de compter toutes les leçons "
                "sans perdre les cours vides, car INNER JOIN exclurait les zéros."
            ),
            "submission_code": (
                "SELECT c.id, COUNT(l.id) AS total FROM courses c "
                "LEFT JOIN lessons l ON l.course_id = c.id GROUP BY c.id;"
            ),
            "new_evidence": {
                "type": "exercise",
                "description": "Requête PostgreSQL LEFT JOIN et GROUP BY testée sur jeu de 5 lignes.",
                "result": "Résultat exact vérifié",
            },
        },
        headers=user_a_headers,
    )
    assert sub1.status_code == 200
    ev1_id = sub1.json()["evidence_ids"][0]

    ev1_eval = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a1['id']}/evaluate",
        json={},
        headers=user_a_headers,
    )
    assert ev1_eval.status_code == 200
    assert ev1_eval.json()["status"] == "evaluated"
    assert ev1_eval.json()["passed"] is True
    assert ev1_eval.json()["proposed_level"] == 1

    val1 = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a1['id']}/validate",
        json={},
        headers=user_a_headers,
    )
    assert val1.status_code == 200
    assert val1.json()["status"] == "approved"

    # Suppression d'une preuve approuvée -> 409 EVIDENCE_LOCKED
    del_approved = client.delete(
        f"/api/v1/skills/{skill_id}/evidence/{ev1_id}",
        headers=user_a_headers,
    )
    assert del_approved.status_code == 409
    assert del_approved.json()["error"]["code"] == "EVIDENCE_LOCKED"

    # Réutilisation de la même preuve sur une 2e évaluation -> 422 EVIDENCE_ALREADY_CONSUMED
    a2 = client.post(
        f"/api/v1/skills/{skill_id}/assessments",
        json={"target_level": 2, "assessment_type": "practical_exercise"},
        headers=user_a_headers,
    ).json()
    reuse = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a2['id']}/submit",
        json={
            "submission_text": (
                "Tentative de réutilisation de la même preuve sur une deuxième évaluation "
                "afin de vérifier le blocage strict par le serveur."
            ),
            "evidence_ids": [ev1_id],
        },
        headers=user_a_headers,
    )
    assert reuse.status_code == 422
    assert reuse.json()["error"]["code"] == "EVIDENCE_ALREADY_CONSUMED"

    # Livrable pratique sans preuve externe inspectée -> passe en needs_manual_review, /validate bloqué
    a_deliv = client.post(
        f"/api/v1/skills/{skill_id}/assessments",
        json={"target_level": 2, "assessment_type": "deliverable"},
        headers=user_a_headers,
    ).json()
    sub_deliv = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a_deliv['id']}/submit",
        json={
            "submission_text": (
                "Livrable complet SQL avec script CREATE TABLE, contraintes CHECK, index composites "
                "et documentation des cas limites car chaque invariant doit être garanti en base."
            ),
            "submission_code": (
                "CREATE TABLE study_logs (id UUID PRIMARY KEY, minutes INT CHECK (minutes > 0));\n"
                "SELECT id, minutes FROM study_logs WHERE minutes >= 30;"
            ),
            "new_evidence": {
                "type": "deliverable",
                "description": "Script SQL complet livrable avec contraintes CHECK et jeu de requêtes analytiques.",
                "result": "Exécution validée localement",
            },
        },
        headers=user_a_headers,
    )
    assert sub_deliv.status_code == 200

    eval_deliv = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a_deliv['id']}/evaluate",
        json={},
        headers=user_a_headers,
    )
    assert eval_deliv.status_code == 200
    assert eval_deliv.json()["status"] == "needs_manual_review"
    assert eval_deliv.json()["manual_review_required"] is True

    val_blocked = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a_deliv['id']}/validate",
        json={},
        headers=user_a_headers,
    )
    assert val_blocked.status_code == 422
    assert val_blocked.json()["error"]["code"] == "MANUAL_REVIEW_REQUIRED"


def test_github_inspector_controlled_and_honest_unreachable(
    client: TestClient,
    user_a_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_dns(monkeypatch, {"api.github.com": "140.82.121.6"})
    skill = client.post(
        "/api/v1/skills",
        json={"name": "FastAPI", "domain": "Backend"},
        headers=user_a_headers,
    ).json()

    ev_ok = client.post(
        f"/api/v1/skills/{skill['id']}/evidence",
        json={
            "type": "project",
            "description": "Dépôt GitHub public avec application FastAPI, tests Pytest et README.",
            "reference_url": "https://github.com/Amireflow/StudyOS",
            "result": "Suite Pytest verte",
        },
        headers=user_a_headers,
    ).json()

    ev_missing = client.post(
        f"/api/v1/skills/{skill['id']}/evidence",
        json={
            "type": "project",
            "description": "Dépôt GitHub privé ou introuvable devant retourner unreachable sans mentir.",
            "reference_url": "https://github.com/Amireflow/PrivateMissingRepo",
            "result": "Dépôt privé",
        },
        headers=user_a_headers,
    ).json()

    original_get = httpx.Client.get

    def fake_github_get(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        s_url = str(url)
        if not s_url.startswith("https://api.github.com"):
            return original_get(self, url, **kwargs)
        req = httpx.Request("GET", url)
        if "/PrivateMissingRepo" in s_url:
            return httpx.Response(404, request=req, json={"message": "Not Found"})
        if s_url.endswith("/repos/Amireflow/StudyOS"):
            return httpx.Response(
                200,
                request=req,
                json={
                    "full_name": "Amireflow/StudyOS",
                    "default_branch": "main",
                    "private": False,
                    "language": "Python",
                },
            )
        if "/contents/README.md" in s_url:
            return httpx.Response(
                200,
                request=req,
                json={"name": "README.md", "path": "README.md", "type": "file"},
            )
        if "/contents" in s_url:
            return httpx.Response(
                200,
                request=req,
                json=[{"name": "README.md", "type": "file"}],
            )
        return httpx.Response(404, request=req)

    monkeypatch.setattr(httpx.Client, "get", fake_github_get)

    insp_ok = client.post(
        f"/api/v1/skills/{skill['id']}/evidence/{ev_ok['id']}/inspect",
        json={"expected_files": ["README.md"]},
        headers=user_a_headers,
    )
    assert insp_ok.status_code == 200
    assert insp_ok.json()["verification_status"] == "verified"
    assert insp_ok.json()["external_reference_verified"] is True
    assert insp_ok.json()["inspection_metadata"]["full_name"] == "Amireflow/StudyOS"

    insp_fail = client.post(
        f"/api/v1/skills/{skill['id']}/evidence/{ev_missing['id']}/inspect",
        json={},
        headers=user_a_headers,
    )
    assert insp_fail.status_code == 200
    assert insp_fail.json()["verification_status"] == "unreachable"
    assert insp_fail.json()["external_reference_verified"] is False


# ---------------------------------------------------------------------------
# 2. Chiffrement AEAD AES-256-GCM des clés API IA & anti-exfiltration
# ---------------------------------------------------------------------------


def test_ai_api_key_aead_encryption_rotation_fail_closed_and_legacy_migration(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_file = tmp_path / "crypto_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    # 1. Fail-closed sans AI_KEY_ENCRYPTION_KEY (503 AI_ENCRYPTION_NOT_CONFIGURED)
    no_key_app = create_app(
        settings=Settings(
            app_env="local",
            allow_local_dev_auth=True,
            ai_key_encryption_key="",
            database_url=db_url,
        )
    )
    with TestClient(no_key_app) as c_nokey:
        headers = {"Authorization": "Bearer dev:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}
        res_503 = c_nokey.put(
            "/api/v1/ai/provider/config",
            json={
                "provider": "openai_compatible",
                "api_key": "sk-plaintext-never-saved",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
            },
            headers=headers,
        )
        assert res_503.status_code == 503
        assert res_503.json()["error"]["code"] == "AI_ENCRYPTION_NOT_CONFIGURED"

    # 2. Avec clé k1 : stockage chiffré enc:v1:k1:..., aucune fuite dans profiles.preferences
    enc_app = create_app(
        settings=Settings(
            app_env="local",
            allow_local_dev_auth=True,
            ai_key_encryption_key=TEST_KEY_V1,
            database_url=db_url,
        )
    )
    uid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    secret = "sk-super-secret-aead-98765"
    with TestClient(enc_app) as c_enc:
        headers = {"Authorization": f"Bearer dev:{uid}"}
        res_ok = c_enc.put(
            "/api/v1/ai/provider/config",
            json={
                "provider": "openai_compatible",
                "api_key": secret,
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
            },
            headers=headers,
        )
        assert res_ok.status_code == 200
        assert res_ok.json()["has_api_key"] is True
        assert secret not in str(res_ok.json())

        prof = c_enc.get("/api/v1/profile", headers=headers).json()
        assert "_ai_provider_config" not in prof["preferences"]
        assert secret not in str(prof)

    # Inspection directe en base SQLite
    engine = create_db_engine(db_url)
    SessionLocal = create_session_factory(engine)
    with SessionLocal() as db:
        row = db.scalar(
            select(UserAiProviderConfigTable).where(UserAiProviderConfigTable.user_id == uid)
        )
        assert row is not None
        assert row.encrypted_api_key is not None
        assert row.encrypted_api_key.startswith(f"{ENCRYPTED_PREFIX}k1:")
        assert secret not in row.encrypted_api_key

        # 3. Rotation de clé (k2 primaire, k1 en fallback) : déchiffre k1 sans perte
        rotated_settings = Settings(
            app_env="local",
            ai_key_encryption_key=TEST_KEY_V2,
            ai_key_encryption_fallback_keys=TEST_KEY_V1,
        )
        assert decrypt_api_key(row.encrypted_api_key, uid, rotated_settings) == secret
        # Un mauvais user_id (AAD) échoue au déchiffrement
        with pytest.raises(AppError) as exc_aad:
            decrypt_api_key(
                row.encrypted_api_key,
                UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                rotated_settings,
            )
        assert exc_aad.value.code == "AI_DECRYPTION_FAILED"

        # 4. Migration contrôlée d'une ancienne clé stockée en clair dans profiles.preferences
        legacy_uid = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        legacy_secret = "sk-legacy-plaintext-key-1234"
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        db.add(
            ProfileTable(
                id=legacy_uid,
                display_name="Legacy",
                timezone="Africa/Dakar",
                preferences={
                    "_ai_provider_config": {
                        "provider": "openai_compatible",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4o-mini",
                        "api_key": legacy_secret,
                    },
                    "theme": "light",
                },
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
        migrated_count = migrate_legacy_plaintext_ai_keys(db, rotated_settings)
        assert migrated_count == 1
        refreshed_prof = db.scalar(select(ProfileTable).where(ProfileTable.id == legacy_uid))
        assert "_ai_provider_config" not in refreshed_prof.preferences  # type: ignore[union-attr]
        assert refreshed_prof.preferences["theme"] == "light"  # type: ignore[union-attr]
        migrated_cfg = db.scalar(
            select(UserAiProviderConfigTable).where(UserAiProviderConfigTable.user_id == legacy_uid)
        )
        assert migrated_cfg is not None
        assert migrated_cfg.encrypted_api_key.startswith(f"{ENCRYPTED_PREFIX}k2:")  # type: ignore[union-attr]
        assert decrypt_api_key(migrated_cfg.encrypted_api_key, legacy_uid, rotated_settings) == legacy_secret
    engine.dispose()


def test_server_ai_key_not_exfiltrated_via_custom_base_url(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_dns(monkeypatch, {"attacker.example": "93.184.216.34", "api.openai.com": "104.18.7.192"})
    db_file = tmp_path / "exfil.db"
    server_secret = "sk-server-env-master-secret-9999"
    app = create_app(
        settings=Settings(
            app_env="local",
            allow_local_dev_auth=True,
            ai_key_encryption_key=TEST_KEY_V1,
            ai_provider="openai_compatible",
            ai_api_key=server_secret,
            ai_base_url="https://api.openai.com/v1",
            ai_model="gpt-4o-mini",
            database_url=f"sqlite:///{db_file.as_posix()}",
        )
    )
    sent_headers: list[tuple[str, str]] = []
    original_post = httpx.Client.post

    def fake_post(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        s_url = str(url)
        if not s_url.startswith("https://attacker.example") and not s_url.startswith("https://api.openai.com"):
            return original_post(self, url, **kwargs)
        sent_headers.append((s_url, str((kwargs.get("headers") or {}).get("Authorization") or "")))
        req = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=req,
            json={"choices": [{"message": {"content": '{"reply": "ok", "proposals": []}'}}]},
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer dev:11111111-1111-1111-1111-111111111111"}
        # Sans clé utilisateur : api_key_preview ne doit JAMAIS révéler de preview sur server_env
        cfg_env = client.get("/api/v1/ai/provider/config", headers=headers).json()
        assert cfg_env["source"] == "server_env"
        assert cfg_env["api_key_preview"] is None

        # Utilisateur configure une URL personnalisée SANS clé personnelle : refus d'injecter settings.ai_api_key !
        client.put(
            "/api/v1/ai/provider/config",
            json={
                "provider": "openai_compatible",
                "base_url": "https://attacker.example/v1",
                "model": "gpt-4o-mini",
            },
            headers=headers,
        )
        conv = client.post("/api/v1/ai/conversations", json={}, headers=headers).json()
        msg_res = client.post(
            f"/api/v1/ai/conversations/{conv['id']}/messages",
            json={"content": "Bonjour copilote"},
            headers=headers,
        )
        assert msg_res.status_code == 201
        for url, auth in sent_headers:
            assert "attacker.example" not in url or server_secret not in auth


# ---------------------------------------------------------------------------
# 3. Protection SSRF (IP privées, metadata, DNS rebinding, redirect, modèle Gemini)
# ---------------------------------------------------------------------------


def test_ssrf_blocks_private_ips_metadata_dns_rebinding_redirects_and_bad_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prod_settings = Settings(
        app_env="production",
        app_secret_key="a-very-long-random-production-secret-key-at-least-32-chars",
        allow_local_dev_auth=False,
        allow_insecure_local_ai_url=False,
        ai_key_encryption_key=TEST_KEY_V1,
        auth_jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json",
        auth_issuer="https://example.supabase.co/auth/v1",
        frontend_origin="https://app.example.com",
    )

    bad_urls = [
        "http://127.0.0.1:8080/v1",
        "https://127.0.0.1/v1",
        "https://169.254.169.254/latest/meta-data",
        "https://10.0.0.1/v1",
        "https://192.168.1.10/v1",
        "https://[::1]/v1",
        "https://metadata.google.internal/computeMetadata/v1",
        "https://user:pass@api.openai.com/v1",
        "https://api.openai.com/v1?foo=bar",
    ]
    for bad in bad_urls:
        with pytest.raises(AppError):
            validate_outbound_url(bad, settings=prod_settings, allow_http_local=True, verify_dns=False)

    # DNS rebinding vers une IP privée 10.0.0.5 bloquée même pour un nom de domaine public apparent
    _mock_dns(monkeypatch, {"rebind.example.com": "10.0.0.5"})
    with pytest.raises(AppError) as exc_rebind:
        validate_outbound_url("https://rebind.example.com/v1", settings=prod_settings, verify_dns=True)
    assert exc_rebind.value.code == "SSRF_BLOCKED"

    # Rejet redirection HTTP 302
    _mock_dns(monkeypatch, {"public.example.com": "93.184.216.34"})

    def fake_redirect_get(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(302, request=httpx.Request("GET", url), headers={"Location": "http://169.254.169.254/"})

    monkeypatch.setattr(httpx.Client, "get", fake_redirect_get)
    from app.core.ssrf import safe_http_request

    with pytest.raises(AppError) as exc_redir:
        safe_http_request("GET", "https://public.example.com/v1/models", settings=prod_settings)
    assert exc_redir.value.code == "SSRF_BLOCKED"

    # Injection chemin Gemini model
    for bad_model in ("../admin", "gemini-2.5-flash?key=123", "model/../../etc"):
        with pytest.raises(AppError):
            validate_model_identifier(bad_model)


# ---------------------------------------------------------------------------
# 4. Sessions HttpOnly, rotation/réutilisation, rate-limit persistant & XFF
# ---------------------------------------------------------------------------


def test_http_only_refresh_cookie_rotation_reuse_detection_and_logout_all(
    strict_auth_client: TestClient,
) -> None:
    reg = strict_auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "sec.user@amireflow.local",
            "password": "StrongPassword123",
            "display_name": "Sec User",
        },
    )
    assert reg.status_code == 201
    cookie_1 = reg.cookies.get("amireflow_refresh_token")
    assert cookie_1

    # Rotation du cookie via /refresh
    ref1 = strict_auth_client.post("/api/v1/auth/refresh", cookies={"amireflow_refresh_token": cookie_1})
    assert ref1.status_code == 200
    cookie_2 = ref1.cookies.get("amireflow_refresh_token")
    assert cookie_2 and cookie_2 != cookie_1

    # Réutilisation de l'ancien cookie_1 -> détection de compromission et révocation de toute la famille !
    reuse = strict_auth_client.post("/api/v1/auth/refresh", cookies={"amireflow_refresh_token": cookie_1})
    assert reuse.status_code == 401

    # Même le nouveau cookie_2 est maintenant révoqué suite à la détection de réutilisation !
    after_reuse = strict_auth_client.post("/api/v1/auth/refresh", cookies={"amireflow_refresh_token": cookie_2})
    assert after_reuse.status_code == 401

    # Nouvelle connexion puis logout-all
    login = strict_auth_client.post(
        "/api/v1/auth/login",
        json={"email": "sec.user@amireflow.local", "password": "StrongPassword123"},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    cookie_3 = login.cookies.get("amireflow_refresh_token")
    assert cookie_3

    out = strict_auth_client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert out.status_code == 204
    assert strict_auth_client.post("/api/v1/auth/refresh", cookies={"amireflow_refresh_token": cookie_3}).status_code == 401
    assert strict_auth_client.get("/api/v1/profile", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_persistent_rate_limiting_and_untrusted_xff_ignored(
    tmp_path: Any,
) -> None:
    db_file = tmp_path / "ratelimit.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    app = create_app(
        settings=Settings(
            app_env="local",
            allow_local_dev_auth=False,
            ai_key_encryption_key=TEST_KEY_V1,
            trusted_proxy_ips="10.0.0.1",
            database_url=db_url,
        )
    )
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "victim@amireflow.local",
                "password": "ValidPassword123",
                "display_name": "Victim",
            },
        )
        # 10 échecs malgré une usine d'en-têtes X-Forwarded-For différents (peer "testclient" hors trusted_proxy_ips)
        for idx in range(10):
            res = client.post(
                "/api/v1/auth/login",
                json={"email": "victim@amireflow.local", "password": f"WrongPass{idx}"},
                headers={"X-Forwarded-For": f"203.0.113.{idx + 10}"},
            )
            assert res.status_code == 401

        blocked = client.post(
            "/api/v1/auth/login",
            json={"email": "victim@amireflow.local", "password": "ValidPassword123"},
            headers={"X-Forwarded-For": "198.51.100.99"},
        )
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "RATE_LIMITED"


def test_cross_user_idor_and_production_guardrails(tmp_path: Any) -> None:
    # IDOR import_id sur schedule.events
    db_file = tmp_path / "idor.db"
    app = create_app(
        settings=Settings(
            app_env="local",
            allow_local_dev_auth=True,
            ai_key_encryption_key=TEST_KEY_V1,
            database_url=f"sqlite:///{db_file.as_posix()}",
        )
    )
    with TestClient(app) as client:
        import io
        from PIL import Image, PngImagePlugin

        user_a = {"Authorization": "Bearer dev:11111111-1111-1111-1111-111111111111"}
        user_b = {"Authorization": "Bearer dev:22222222-2222-2222-2222-222222222222"}

        img = Image.new("RGB", (320, 200), color=(255, 255, 255))
        meta = PngImagePlugin.PngInfo()
        meta.add_text("Description", "Lundi 08:00 - 10:00 Algorithmique - CM - Pr. Diop")
        buf = io.BytesIO()
        img.save(buf, format="PNG", pnginfo=meta)

        imp = client.post(
            "/api/v1/schedule/imports/analyze",
            files={"file": ("edt.png", buf.getvalue(), "image/png")},
            headers=user_a,
        )
        assert imp.status_code == 201
        import_id_a = imp.json()["id"]

        idor_ev = client.post(
            "/api/v1/schedule",
            json={
                "title": "Tentative IDOR import_id",
                "type": "course",
                "starts_at": "2026-11-23T08:00:00Z",
                "ends_at": "2026-11-23T10:00:00Z",
                "import_id": import_id_a,
            },
            headers=user_b,
        )
        assert idor_ev.status_code == 404

    # Garde-fous démarrage production
    base_prod = dict(
        app_env="production",
        allow_local_dev_auth=False,
        allow_insecure_local_ai_url=False,
        app_secret_key="super-strong-production-secret-key-at-least-32-chars",
        ai_key_encryption_key=TEST_KEY_V1,
        auth_jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json",
        auth_issuer="https://example.supabase.co/auth/v1",
        frontend_origin="https://studyos.example.com",
        database_url=f"sqlite:///{(tmp_path / 'prod_ok.db').as_posix()}",
    )
    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        create_app(settings=Settings(**{**base_prod, "app_secret_key": "dev-secret-change-in-production"}))

    with pytest.raises(RuntimeError, match="ALLOW_INSECURE_LOCAL_AI_URL"):
        create_app(settings=Settings(**{**base_prod, "allow_insecure_local_ai_url": True}))

    with pytest.raises(RuntimeError, match="FRONTEND_ORIGIN"):
        create_app(settings=Settings(**{**base_prod, "frontend_origin": "*"}))
