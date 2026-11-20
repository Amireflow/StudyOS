import logging
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("amireflow.api")


class AppError(Exception):
    """Erreur métier normalisée traduite au format d'erreur JSON uniforme (CdC §7.1)."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    generated = f"req_{uuid4().hex[:12]}"
    request.state.request_id = generated
    return generated


def error_json_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": get_request_id(request),
            }
        },
    )


def _format_validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Les données envoyées sont invalides."

    first = errors[0]
    raw_message = str(first.get("msg", "Données invalides."))
    clean_message = raw_message.removeprefix("Value error, ").strip()
    loc = [str(part) for part in first.get("loc", ()) if part not in ("body", "query", "path")]
    if loc:
        return f"Champ « {'.'.join(loc)} » : {clean_message}"
    return clean_message


def _status_to_error_code(status_code: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
    }
    return mapping.get(status_code, "HTTP_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_json_response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return error_json_response(
            request,
            status_code=422,
            code="VALIDATION_ERROR",
            message=_format_validation_message(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        message = str(exc.detail) if exc.detail else "Requête invalide."
        if exc.status_code == 404 and message == "Not Found":
            message = "Ressource introuvable."
        return error_json_response(
            request,
            status_code=exc.status_code,
            code=_status_to_error_code(exc.status_code),
            message=message,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on request %s", get_request_id(request), exc_info=exc)
        return error_json_response(
            request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="Une erreur interne est survenue.",
        )
