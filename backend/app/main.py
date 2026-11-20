from contextlib import asynccontextmanager
import logging
from pathlib import Path
import time
from typing import Any
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from jwt import PyJWKClient
from sqlalchemy import text
import app.models  # noqa: F401 - enregistre les modèles ORM dans Base.metadata
from app.api.routes import (
    ai,
    auth,
    courses,
    dashboard,
    learning,
    objectives,
    planning,
    profile,
    projects,
    schedule,
    sessions,
    skills,
    tasks,
)
from app.core.config import Settings, get_settings
from app.core.database import Base, create_db_engine, create_session_factory
from app.core.errors import register_exception_handlers
from app.repositories.memory import InMemoryStore


logger = logging.getLogger("amireflow.study_os")


_DEFAULT_SECRET_VALUES = {
    "",
    "local-dev-secret-key-change-me-32bytes",
    "change-me-in-local-env",
}


def _validate_production_settings(settings: Settings) -> None:
    if settings.app_env.strip().lower() != "production":
        return

    if settings.allow_local_dev_auth:
        raise RuntimeError(
            "Configuration dangereuse refusée : ALLOW_LOCAL_DEV_AUTH doit être false en production."
        )
    if settings.allow_insecure_local_ai_url:
        raise RuntimeError(
            "Configuration dangereuse refusée : ALLOW_INSECURE_LOCAL_AI_URL doit être false en production."
        )
    secret = (settings.app_secret_key or "").strip()
    if secret in _DEFAULT_SECRET_VALUES or len(secret) < 32:
        raise RuntimeError(
            "Configuration dangereuse refusée : APP_SECRET_KEY doit contenir au moins 32 caractères non par défaut en production."
        )
    if "*" in settings.cors_origins:
        raise RuntimeError(
            "Configuration dangereuse refusée : FRONTEND_ORIGIN ne doit pas autoriser '*' en production."
        )
    if settings.database_url.strip() == "sqlite:///./amireflow_local.db":
        raise RuntimeError(
            "Configuration dangereuse refusée : DATABASE_URL SQLite par défaut interdit en production."
        )


def create_app(
    settings: Settings | None = None,
    store: InMemoryStore | None = None,
    *,
    auto_create_tables: bool | None = None,
    jwks_client: Any = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    _validate_production_settings(resolved_settings)
    is_prod = resolved_settings.app_env.strip().lower() == "production"
    should_create_tables = (
        (resolved_settings.app_env.strip().lower() == "local")
        if auto_create_tables is None
        else auto_create_tables
    )

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        engine = getattr(app_instance.state, "db_engine", None)
        if engine is not None and should_create_tables:
            Base.metadata.create_all(engine)
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    application = FastAPI(
        title="Amireflow Study OS API",
        version="1.0.0",
        description="API REST Amireflow Study OS v1.0 (Paliers 1 & 2 — Lots 1 à 8).",
        docs_url=None if is_prod else "/docs",
        openapi_url=None if is_prod else "/openapi.json",
        lifespan=lifespan,
    )

    application.state.settings = resolved_settings
    if jwks_client is not None:
        application.state.jwks_client = jwks_client
    elif resolved_settings.auth_jwks_url:
        application.state.jwks_client = PyJWKClient(resolved_settings.auth_jwks_url)
    else:
        application.state.jwks_client = None

    if store is not None:
        application.state.store = store
        application.state.db_engine = None
        application.state.session_factory = None
    else:
        engine = create_db_engine(resolved_settings.database_url)
        application.state.store = None
        application.state.db_engine = engine
        application.state.session_factory = create_session_factory(engine)

    register_exception_handlers(application)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Idempotency-Key"],
        expose_headers=["X-Request-ID"],
    )

    @application.middleware("http")
    async def attach_request_id(request: Request, call_next) -> Response:
        request_id = f"req_{uuid4().hex[:12]}"
        request.state.request_id = request_id
        start_perf = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_perf) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if is_prod or request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        logger.info(
            "http_request request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    spa_dist_dir: Path | None = None
    if resolved_settings.frontend_dist_dir.strip():
        candidate_dir = Path(resolved_settings.frontend_dist_dir.strip()).resolve()
        if (candidate_dir / "index.html").is_file():
            spa_dist_dir = candidate_dir

    if spa_dist_dir is None:
        @application.get("/", include_in_schema=False)
        def service_root() -> dict[str, str]:
            return {
                "service": "Amireflow Study OS API",
                "status": "ok",
                "health": "/health",
            }

    @application.get("/health", tags=["Santé"], summary="Vérifier la disponibilité de l'API")
    def health_check(request: Request) -> Response:
        engine = getattr(request.app.state, "db_engine", None)
        if engine is None:
            return JSONResponse(
                status_code=200,
                content={"status": "ok", "env": resolved_settings.app_env, "database": "memory"},
            )
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return JSONResponse(
                status_code=200,
                content={"status": "ok", "env": resolved_settings.app_env, "database": "ok"},
            )
        except Exception:
            logger.exception("health_check_database_failed")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "degraded",
                    "env": resolved_settings.app_env,
                    "database": "error",
                },
            )

    api_prefix = "/api/v1"
    application.include_router(auth.router, prefix=api_prefix)
    application.include_router(profile.router, prefix=api_prefix)
    application.include_router(dashboard.router, prefix=api_prefix)
    application.include_router(tasks.router, prefix=api_prefix)
    application.include_router(schedule.router, prefix=api_prefix)
    application.include_router(sessions.router, prefix=api_prefix)
    application.include_router(learning.router, prefix=api_prefix)
    application.include_router(courses.router, prefix=api_prefix)
    application.include_router(skills.router, prefix=api_prefix)
    application.include_router(projects.router, prefix=api_prefix)
    application.include_router(objectives.router, prefix=api_prefix)
    application.include_router(planning.router, prefix=api_prefix)
    application.include_router(ai.router, prefix=api_prefix)

    if spa_dist_dir is not None:
        spa_index = spa_dist_dir / "index.html"

        @application.get("/", include_in_schema=False)
        def spa_root() -> FileResponse:
            return FileResponse(spa_index, headers={"Cache-Control": "no-cache"})

        @application.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str) -> FileResponse:
            cleaned = full_path.lstrip("/")
            if (
                cleaned == "api"
                or cleaned.startswith("api/")
                or cleaned in {"health", "docs", "redoc", "openapi.json"}
            ):
                raise HTTPException(status_code=404, detail="Ressource introuvable.")

            if cleaned:
                candidate = (spa_dist_dir / cleaned).resolve()
                if not candidate.is_relative_to(spa_dist_dir):
                    raise HTTPException(status_code=404, detail="Ressource introuvable.")
                if candidate.is_file():
                    if cleaned == "manifest.webmanifest":
                        return FileResponse(
                            candidate,
                            media_type="application/manifest+json",
                            headers={"Cache-Control": "no-cache"},
                        )
                    if cleaned == "sw.js":
                        return FileResponse(
                            candidate,
                            media_type="application/javascript",
                            headers={
                                "Cache-Control": "no-cache, no-store, must-revalidate",
                                "Service-Worker-Allowed": "/",
                            },
                        )
                    headers = (
                        {"Cache-Control": "public, max-age=31536000, immutable"}
                        if cleaned.startswith("assets/")
                        else None
                    )
                    return FileResponse(candidate, headers=headers)
                if cleaned.startswith("assets/"):
                    raise HTTPException(status_code=404, detail="Ressource statique introuvable.")

            return FileResponse(spa_index, headers={"Cache-Control": "no-cache"})

    return application


app = create_app()
