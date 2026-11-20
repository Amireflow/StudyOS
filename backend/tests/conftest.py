from collections.abc import Iterator
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app


TEST_AI_ENCRYPTION_KEY = "k1:MDAxMTIyMzM0NDU1NjY3Nzg4OTlhYWJiY2NkZGVlZmY="


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    db_file = tmp_path / "test_study_os.db"
    return create_app(
        settings=Settings(
            app_env="local",
            allow_local_dev_auth=True,
            ai_key_encryption_key=TEST_AI_ENCRYPTION_KEY,
            database_url=f"sqlite:///{db_file.as_posix()}",
        ),
    )


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def strict_auth_client(tmp_path: Path) -> Iterator[TestClient]:
    db_file = tmp_path / "test_strict_auth.db"
    strict_app = create_app(
        settings=Settings(
            app_env="local",
            allow_local_dev_auth=False,
            ai_key_encryption_key=TEST_AI_ENCRYPTION_KEY,
            database_url=f"sqlite:///{db_file.as_posix()}",
        ),
    )
    with TestClient(strict_app) as test_client:
        yield test_client


@pytest.fixture
def user_a_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev:11111111-1111-1111-1111-111111111111"}


@pytest.fixture
def user_b_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev:22222222-2222-2222-2222-222222222222"}
