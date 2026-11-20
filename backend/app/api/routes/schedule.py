import base64
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from app.api.deps import get_profile_service, get_schedule_service
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import get_app_settings, get_current_user_id
from app.schemas.schedule import (
    DuplicateWeekRequest,
    DuplicateWeekResponse,
    ScheduleEventCreate,
    ScheduleEventResponse,
    ScheduleEventUpdate,
    TimetableImportAnalyzeBase64Request,
    TimetableImportConfirmRequest,
    TimetableImportConfirmResponse,
    TimetableImportResponse,
    TimetableImportRestoreResponse,
    TimetableImportUpdateDraftRequest,
    TimetableReplacePreviewResponse,
)
from app.services.profile_service import ProfileService
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedule", tags=["Planning"])


@router.get("", response_model=list[ScheduleEventResponse], summary="Lister les créneaux")
def list_schedule_events(
    week_start: date | None = Query(default=None),
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> list[ScheduleEventResponse]:
    profile = profile_service.get_or_create_record(user_id)
    return schedule_service.list_events(
        user_id,
        week_start=week_start,
        tz_name=profile.timezone,
    )


@router.post(
    "",
    response_model=ScheduleEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un créneau",
)
def create_schedule_event(
    payload: ScheduleEventCreate,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleEventResponse:
    return schedule_service.create_event(user_id, payload)


@router.post(
    "/duplicate-week",
    response_model=DuplicateWeekResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dupliquer les créneaux d'une semaine vers la suivante",
)
def duplicate_week(
    payload: DuplicateWeekRequest,
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> DuplicateWeekResponse:
    profile = profile_service.get_or_create_record(user_id)
    return schedule_service.duplicate_week(
        user_id,
        source_week_start=payload.source_week_start,
        tz_name=profile.timezone,
        target_week_start=payload.target_week_start,
    )


# -----------------------------------------------------------------------------
# ROUTES D'IMPORT INTELLIGENT DE L'EMPLOI DU TEMPS (avant /{event_id})
# -----------------------------------------------------------------------------


def _resolve_user_ai_config(
    user_id: UUID,
    profile_service: ProfileService,
    settings: Settings,
) -> dict[str, object]:
    from app.ai.provider import canonicalize_provider_name, normalize_provider_base_url

    saved = profile_service.get_ai_provider_config(user_id)
    if saved and saved.get("provider") and saved.get("provider") != "local":
        provider_key = canonicalize_provider_name(str(saved.get("provider")))
        base_url = normalize_provider_base_url(provider_key, saved.get("base_url"))
        default_url = normalize_provider_base_url(provider_key, None)
        env_provider = canonicalize_provider_name(settings.ai_provider)
        env_url = normalize_provider_base_url(env_provider, settings.ai_base_url)
        is_custom_url = bool(base_url and base_url != default_url and not (env_provider == provider_key and base_url == env_url))

        resolved_key = str(saved.get("api_key") or "").strip()
        if not resolved_key and env_provider == provider_key and not is_custom_url:
            resolved_key = (settings.ai_api_key or "").strip()

        return {
            "provider": provider_key,
            "api_key": resolved_key,
            "model": saved.get("model") or settings.ai_model,
            "base_url": base_url,
            "timeout_seconds": settings.ai_timeout_seconds,
            "settings": settings,
        }
    return {
        "provider": settings.ai_provider,
        "api_key": settings.ai_api_key,
        "model": settings.ai_model,
        "base_url": settings.ai_base_url,
        "timeout_seconds": settings.ai_timeout_seconds,
        "settings": settings,
    }


@router.get(
    "/imports",
    response_model=list[TimetableImportResponse],
    summary="Lister les sessions d'importation d'emploi du temps",
)
def list_timetable_imports(
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> list[TimetableImportResponse]:
    return schedule_service.list_imports(user_id)


@router.post(
    "/imports/analyze",
    response_model=TimetableImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyser un document d'emploi du temps (PDF, Image, Excel, Word) sans enregistrer les cours",
)
async def analyze_timetable_file(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    settings: Settings = Depends(get_app_settings),
) -> TimetableImportResponse:
    profile = profile_service.get_or_create_record(user_id)
    content = await file.read()
    return schedule_service.analyze_timetable_import(
        user_id,
        filename=file.filename or "",
        content_type=file.content_type,
        content=content,
        max_bytes=settings.timetable_import_max_bytes,
        rate_limit_per_minute=settings.timetable_import_rate_limit_per_minute,
        tz_name=profile.timezone,
        ai_config=_resolve_user_ai_config(user_id, profile_service, settings),
    )


@router.post(
    "/imports/analyze-base64",
    response_model=TimetableImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyser un document d'emploi du temps encodé en Base64",
)
def analyze_timetable_base64(
    payload: TimetableImportAnalyzeBase64Request,
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    settings: Settings = Depends(get_app_settings),
) -> TimetableImportResponse:
    profile = profile_service.get_or_create_record(user_id)
    raw_b64 = payload.content_base64.strip()
    if "," in raw_b64 and raw_b64.startswith("data:"):
        raw_b64 = raw_b64.split(",", 1)[1]
    try:
        content = base64.b64decode(raw_b64, validate=True)
    except Exception as exc:
        raise AppError(
            422,
            "INVALID_BASE64_CONTENT",
            "Le contenu Base64 du document est invalide.",
        ) from exc

    return schedule_service.analyze_timetable_import(
        user_id,
        filename=payload.filename,
        content_type=payload.content_type,
        content=content,
        max_bytes=settings.timetable_import_max_bytes,
        rate_limit_per_minute=settings.timetable_import_rate_limit_per_minute,
        tz_name=profile.timezone,
        ai_config=_resolve_user_ai_config(user_id, profile_service, settings),
    )


@router.get(
    "/imports/{import_id}",
    response_model=TimetableImportResponse,
    summary="Consulter une session d'importation d'emploi du temps",
)
def get_timetable_import(
    import_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> TimetableImportResponse:
    return schedule_service.get_import(user_id, import_id)


@router.patch(
    "/imports/{import_id}",
    response_model=TimetableImportResponse,
    summary="Modifier l'aperçu des cours détectés avant validation",
)
def update_timetable_import_draft(
    import_id: UUID,
    payload: TimetableImportUpdateDraftRequest,
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> TimetableImportResponse:
    profile = profile_service.get_or_create_record(user_id)
    return schedule_service.update_import_draft(
        user_id,
        import_id,
        payload,
        tz_name=profile.timezone,
    )


@router.get(
    "/imports/{import_id}/replace-preview",
    response_model=TimetableReplacePreviewResponse,
    summary="Prévisualiser les cours importés qui seraient remplacés sur la période",
)
def preview_replace_imported_schedule(
    import_id: UUID,
    target_week_start: date | None = Query(default=None),
    recurrence_weeks: int = Query(default=1, ge=1, le=24),
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> TimetableReplacePreviewResponse:
    profile = profile_service.get_or_create_record(user_id)
    return schedule_service.preview_replace_imported(
        user_id,
        import_id,
        target_week_start=target_week_start,
        recurrence_weeks=recurrence_weeks,
        tz_name=profile.timezone,
    )


@router.post(
    "/imports/{import_id}/restore",
    response_model=TimetableImportRestoreResponse,
    summary="Restaurer les anciens créneaux importés remplacés lors de cet import",
)
def restore_replaced_timetable_import(
    import_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> TimetableImportRestoreResponse:
    return schedule_service.restore_import_snapshot(user_id, import_id)


@router.post(
    "/imports/{import_id}/confirm",
    response_model=TimetableImportConfirmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Valider explicitement l'aperçu et enregistrer les cours dans le calendrier",
)
def confirm_timetable_import(
    import_id: UUID,
    payload: TimetableImportConfirmRequest | None = None,
    user_id: UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> TimetableImportConfirmResponse:
    profile = profile_service.get_or_create_record(user_id)
    return schedule_service.confirm_import(
        user_id,
        import_id,
        payload,
        tz_name=profile.timezone,
    )


@router.post(
    "/imports/{import_id}/cancel",
    response_model=TimetableImportResponse,
    summary="Annuler l'importation sans enregistrer aucun cours",
)
def cancel_timetable_import(
    import_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> TimetableImportResponse:
    return schedule_service.cancel_import(user_id, import_id)


@router.delete(
    "/imports/{import_id}/source",
    response_model=TimetableImportResponse,
    summary="Supprimer l'extrait du document source tout en conservant les cours validés",
)
def delete_timetable_import_source(
    import_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> TimetableImportResponse:
    return schedule_service.delete_import_source(user_id, import_id)


# -----------------------------------------------------------------------------
# ROUTES CRUD UNITAIRES DE CRÉNEAUX
# -----------------------------------------------------------------------------


@router.get(
    "/{event_id}",
    response_model=ScheduleEventResponse,
    summary="Consulter un créneau",
)
def get_schedule_event(
    event_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleEventResponse:
    return schedule_service.get_event(user_id, event_id)


@router.patch(
    "/{event_id}",
    response_model=ScheduleEventResponse,
    summary="Modifier un créneau",
)
def update_schedule_event(
    event_id: UUID,
    payload: ScheduleEventUpdate,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleEventResponse:
    return schedule_service.update_event(user_id, event_id, payload)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un créneau",
)
def delete_schedule_event(
    event_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> Response:
    schedule_service.delete_event(user_id, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
