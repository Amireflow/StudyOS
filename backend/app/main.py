from contextlib import asynccontextmanager
import logging
import time
from typing import Any
from uuid import uuid4
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from jwt import PyJWKClient
import app.models  # noqa: F401 - enregistre les modèles ORM dans Base.metadata
from app.api.routes import (
    ai,
    auth,
    courses,
    dashboard,
    learning,
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


def create_app(
    settings: Settings | None = None,
    store: InMemoryStore | None = None,
    *,
    auto_create_tables: bool = True,
    jwks_client: Any = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    if (
        resolved_settings.app_env.strip().lower() == "production"
        and resolved_settings.allow_local_dev_auth
    ):
        raise RuntimeError(
            "Configuration dangereuse refusée : ALLOW_LOCAL_DEV_AUTH doit être false en production."
        )

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        engine = getattr(app_instance.state, "db_engine", None)
        if engine is not None and auto_create_tables:
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
        docs_url="/docs",
        openapi_url="/openapi.json",
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
        allow_methods=["*"],
        allow_headers=["*"],
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
        logger.info(
            "http_request request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @application.get("/health", tags=["Santé"], summary="Vérifier la disponibilité de l'API")
    def health_check() -> dict[str, str]:
        return {"status": "ok", "env": resolved_settings.app_env}

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
    application.include_router(ai.router, prefix=api_prefix)

    return application


app = create_app()
