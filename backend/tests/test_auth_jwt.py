from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app


class FakeJwksClient:
    def __init__(self, public_key) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, _token: str) -> SimpleNamespace:
        return SimpleNamespace(key=self._public_key)


def _generate_rsa_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def test_jwks_rs256_token_verification_and_claims_enforcement(tmp_path: Path) -> None:
    private_key, public_key = _generate_rsa_pair()
    other_private_key, _ = _generate_rsa_pair()

    issuer = "https://example.supabase.co/auth/v1"
    audience = "authenticated"
    user_sub = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    settings = Settings(
        app_env="production",
        allow_local_dev_auth=False,
        database_url=f"sqlite:///{(tmp_path / 'jwks.db').as_posix()}",
        auth_jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json",
        auth_issuer=issuer,
        auth_audience=audience,
    )
    app = create_app(settings=settings, jwks_client=FakeJwksClient(public_key))

    now = datetime.now(timezone.utc)

    def make_token(
        *,
        key=private_key,
        sub: str = user_sub,
        iss: str = issuer,
        aud: str = audience,
        exp_delta: timedelta = timedelta(minutes=15),
    ) -> str:
        return jwt.encode(
            {
                "sub": sub,
                "iss": iss,
                "aud": aud,
                "iat": int(now.timestamp()),
                "exp": int((now + exp_delta).timestamp()),
            },
            key,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

    with TestClient(app) as client:
        # Jeton RS256 valide
        ok = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {make_token()}"},
        )
        assert ok.status_code == 200
        assert ok.json()["id"] == user_sub

        # Jeton expiré -> 401
        expired = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {make_token(exp_delta=timedelta(minutes=-5))}"},
        )
        assert expired.status_code == 401

        # Mauvais émetteur (iss) -> 401
        bad_iss = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {make_token(iss='https://evil.example.com')}"},
        )
        assert bad_iss.status_code == 401

        # Mauvaise audience (aud) -> 401
        bad_aud = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {make_token(aud='wrong-audience')}"},
        )
        assert bad_aud.status_code == 401

        # Signature invalide -> 401
        bad_sig = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {make_token(key=other_private_key)}"},
        )
        assert bad_sig.status_code == 401


def test_local_login_issues_valid_hs256_jwt_and_respects_flag(tmp_path: Path) -> None:
    local_app = create_app(
        settings=Settings(
            app_env="local",
            allow_local_dev_auth=True,
            database_url=f"sqlite:///{(tmp_path / 'local_auth.db').as_posix()}",
        )
    )
    with TestClient(local_app) as client:
        login_res = client.post(
            "/api/v1/auth/local-login",
            json={"email": "etudiant@amireflow.local", "display_name": "Amire"},
        )
        assert login_res.status_code == 200
        data = login_res.json()
        assert data["token_type"] == "bearer"
        assert data["profile"]["display_name"] == "Amire"

        profile_res = client.get(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert profile_res.status_code == 200
        assert profile_res.json()["display_name"] == "Amire"

    disabled_app = create_app(
        settings=Settings(
            app_env="local",
            allow_local_dev_auth=False,
            database_url=f"sqlite:///{(tmp_path / 'disabled_auth.db').as_posix()}",
        )
    )
    with TestClient(disabled_app) as disabled_client:
        res = disabled_client.post(
            "/api/v1/auth/local-login",
            json={"email": "etudiant@amireflow.local"},
        )
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"
