from pathlib import Path
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core.config import Settings
from app.main import create_app
from app.models.tables import UserAccountTable


def test_register_login_hashing_and_duplicate_rejection(
    app: FastAPI,
    client: TestClient,
) -> None:
    bad_pw = client.post(
        "/api/v1/auth/register",
        json={
            "email": "short@amireflow.local",
            "password": "123",
            "display_name": "Court",
        },
    )
    assert bad_pw.status_code == 422
    assert bad_pw.json()["error"]["code"] == "VALIDATION_ERROR"

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Alice@Amireflow.local",
            "password": "SecretPass123!",
            "display_name": "Alice",
            "timezone": "Europe/Paris",
        },
    )
    assert reg.status_code == 201
    reg_body = reg.json()
    assert reg_body["token_type"] == "bearer"
    assert reg_body["email"] == "alice@amireflow.local"
    assert reg_body["profile"]["display_name"] == "Alice"
    assert reg_body["profile"]["timezone"] == "Europe/Paris"
    assert reg_body["profile"]["preferences"] == {"theme": "system"}

    # Vérifier en base que le mot de passe est haché (scrypt) et jamais en clair
    with app.state.session_factory() as db:
        user_row = db.scalar(
            select(UserAccountTable).where(UserAccountTable.email == "alice@amireflow.local")
        )
        assert user_row is not None
        assert user_row.password_hash.startswith("scrypt$")
        assert "SecretPass123!" not in user_row.password_hash
        assert user_row.token_version == 1

    # Doublon d'e-mail (insensible à la casse) -> 409
    dup = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ALICE@amireflow.local",
            "password": "AnotherPass123!",
            "display_name": "Alice 2",
        },
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    # Identifiants invalides : même réponse générique
    wrong_pw = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@amireflow.local", "password": "WrongPassword!"},
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": "inconnu@amireflow.local", "password": "WrongPassword!"},
    )
    assert wrong_pw.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_pw.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert unknown_email.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert wrong_pw.json()["error"]["message"] == unknown_email.json()["error"]["message"]

    # Connexion valide
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@amireflow.local", "password": "SecretPass123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    account_res = client.get(
        "/api/v1/auth/account",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert account_res.status_code == 200
    acc_body = account_res.json()
    assert acc_body["email"] == "alice@amireflow.local"
    assert acc_body["auth_provider"] == "password"
    assert acc_body["has_password_account"] is True


def test_complete_multi_user_data_and_settings_isolation(client: TestClient) -> None:
    alice_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice.iso@amireflow.local",
            "password": "AlicePassword99!",
            "display_name": "Alice",
            "timezone": "Europe/Paris",
        },
    )
    assert alice_reg.status_code == 201
    alice_headers = {"Authorization": f"Bearer {alice_reg.json()['access_token']}"}

    bob_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob.iso@amireflow.local",
            "password": "BobPassword99!",
            "display_name": "Bob",
            "timezone": "Africa/Dakar",
        },
    )
    assert bob_reg.status_code == 201
    bob_headers = {"Authorization": f"Bearer {bob_reg.json()['access_token']}"}

    # Alice configure ses paramètres personnels + fournisseur River AI + données métier
    alice_prof = client.patch(
        "/api/v1/profile",
        json={
            "display_name": "Alice Pro",
            "timezone": "America/Montreal",
            "ai_instructions": "Consignes privées d'Alice",
            "preferences": {"theme": "dark"},
        },
        headers=alice_headers,
    )
    assert alice_prof.status_code == 200

    alice_ai_cfg = client.put(
        "/api/v1/ai/provider/config",
        json={
            "provider": "river",
            "api_key": "rk_alice_secret_key_7890",
            "model": "claude-3-7-sonnet",
        },
        headers=alice_headers,
    )
    assert alice_ai_cfg.status_code == 200
    assert alice_ai_cfg.json()["api_key_preview"] == "rk_a…7890"

    task_a = client.post(
        "/api/v1/tasks",
        json={"title": "Tâche privée d'Alice", "priority": "critical"},
        headers=alice_headers,
    ).json()
    sched_a = client.post(
        "/api/v1/schedule",
        json={
            "title": "Cours privé Alice",
            "type": "course",
            "starts_at": "2026-11-21T09:00:00Z",
            "ends_at": "2026-11-21T11:00:00Z",
        },
        headers=alice_headers,
    ).json()
    proj_a = client.post(
        "/api/v1/projects",
        json={
            "name": "Projet confidentiel Alice",
            "goal": "Livrer V2",
            "status": "active",
            "next_action": "Définir architecture",
        },
        headers=alice_headers,
    ).json()
    skill_a = client.post(
        "/api/v1/skills",
        json={"name": "Sécurité JWT", "domain": "Backend", "current_level": 0, "target_level": 4},
        headers=alice_headers,
    ).json()
    conv_a = client.post("/api/v1/ai/conversations", json={}, headers=alice_headers).json()

    # Bob ne voit RIEN des données ni paramètres d'Alice
    bob_prof = client.get("/api/v1/profile", headers=bob_headers).json()
    assert bob_prof["display_name"] == "Bob"
    assert bob_prof["timezone"] == "Africa/Dakar"
    assert bob_prof["ai_instructions"] is None
    assert bob_prof["preferences"] == {"theme": "system"}

    bob_ai_cfg = client.get("/api/v1/ai/provider/config", headers=bob_headers).json()
    assert bob_ai_cfg["provider"] == "local"
    assert bob_ai_cfg["has_api_key"] is False

    assert client.get("/api/v1/tasks", headers=bob_headers).json() == []
    assert client.get("/api/v1/schedule", headers=bob_headers).json() == []
    assert client.get("/api/v1/projects", headers=bob_headers).json() == []
    assert client.get("/api/v1/skills", headers=bob_headers).json() == []
    assert client.get("/api/v1/courses", headers=bob_headers).json() == []
    assert client.get("/api/v1/ai/conversations", headers=bob_headers).json() == []

    # Accès direct aux IDs d'Alice refusé (404)
    assert client.get(f"/api/v1/tasks/{task_a['id']}", headers=bob_headers).status_code == 404
    assert client.patch(f"/api/v1/schedule/{sched_a['id']}", json={"title": "Hack"}, headers=bob_headers).status_code == 404
    assert client.get(f"/api/v1/projects/{proj_a['id']}", headers=bob_headers).status_code == 404
    assert client.get(f"/api/v1/skills/{skill_a['id']}", headers=bob_headers).status_code == 404
    assert client.get(f"/api/v1/ai/conversations/{conv_a['id']}", headers=bob_headers).status_code == 404

    # Bob modifie ses propres paramètres et données sans affecter Alice
    client.patch(
        "/api/v1/profile",
        json={"preferences": {"theme": "light"}},
        headers=bob_headers,
    )
    client.post(
        "/api/v1/tasks",
        json={"title": "Tâche personnelle de Bob"},
        headers=bob_headers,
    )

    alice_tasks = client.get("/api/v1/tasks", headers=alice_headers).json()
    bob_tasks = client.get("/api/v1/tasks", headers=bob_headers).json()
    assert [t["title"] for t in alice_tasks] == ["Tâche privée d'Alice"]
    assert [t["title"] for t in bob_tasks] == ["Tâche personnelle de Bob"]

    alice_prof_after = client.get("/api/v1/profile", headers=alice_headers).json()
    assert alice_prof_after["preferences"] == {"theme": "dark"}


def test_change_password_and_logout_revoke_previous_tokens(client: TestClient) -> None:
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "revoke@amireflow.local",
            "password": "InitialPassword1!",
            "display_name": "Khadim",
        },
    )
    assert reg.status_code == 201
    token1 = reg.json()["access_token"]

    assert client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token1}"}).status_code == 200

    # Changement de mot de passe -> révoque token1 et émet token2
    cp = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "InitialPassword1!",
            "new_password": "UpdatedPassword2!",
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert cp.status_code == 200
    token2 = cp.json()["access_token"]

    assert client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token1}"}).status_code == 401
    assert client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token2}"}).status_code == 200

    # Ancien mot de passe refusé, nouveau accepté
    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "revoke@amireflow.local", "password": "InitialPassword1!"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "revoke@amireflow.local", "password": "UpdatedPassword2!"},
    )
    assert new_login.status_code == 200
    token3 = new_login.json()["access_token"]

    # Déconnexion globale -> révoque token2 et token3
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token3}"},
    )
    assert logout_res.status_code == 204
    assert client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token3}"}).status_code == 401
    assert client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token2}"}).status_code == 401


def test_alembic_0007_and_production_password_auth(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    db_file = tmp_path / "prod_auth_alembic.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    prod_app = create_app(
        settings=Settings(
            app_env="production",
            allow_local_dev_auth=False,
            app_secret_key="production-secret-key-minimum-32-chars",
            database_url=db_url,
        ),
        auto_create_tables=False,
    )
    with TestClient(prod_app) as prod_client:
        # La connexion dev locale est bloquée en production
        assert (
            prod_client.post(
                "/api/v1/auth/local-login",
                json={"email": "dev@amireflow.local"},
            ).status_code
            == 403
        )
        # Inscription et connexion réelles fonctionnent en production sans Supabase
        reg = prod_client.post(
            "/api/v1/auth/register",
            json={
                "email": "prod.user@amireflow.app",
                "password": "ProdPassword123!",
                "display_name": "Utilisateur Prod",
            },
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        me = prod_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me.status_code == 200
        assert me.json()["display_name"] == "Utilisateur Prod"
