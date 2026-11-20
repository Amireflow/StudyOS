from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.core.errors import AppError
from app.repositories.memory import (
    ScheduleEventRecord,
    ScheduleRepository,
    TimetableImportRecord,
)
from app.schemas.common import (
    CourseSessionSubtype,
    ScheduleEventSource,
    ScheduleEventType,
    TimetableImportStatus,
)
from app.schemas.schedule import (
    DuplicateWeekResponse,
    ExtractedCourseRowSchema,
    ScheduleEventCreate,
    ScheduleEventResponse,
    ScheduleEventUpdate,
    TimetableAnomalySchema,
    TimetableImportConfirmRequest,
    TimetableImportConfirmResponse,
    TimetableImportResponse,
    TimetableImportUpdateDraftRequest,
)
from app.services.timetable_extractor import (
    DAY_NAMES_FR,
    detect_timetable_anomalies,
    extract_timetable_from_bytes,
)

SUBTYPE_LABELS_FR: dict[str, str] = {
    "cours": "Cours",
    "td": "TD",
    "tp": "TP",
    "examen": "Examen",
    "autre": "Séance",
}


def do_events_overlap(
    a_start: datetime,
    a_end: datetime,
    b_start: datetime,
    b_end: datetime,
) -> bool:
    """Chevauchement strict : deux créneaux consécutifs ne sont pas en conflit (SCHED-03)."""
    return a_start < b_end and b_start < a_end


def _shift_local_days(dt_utc: datetime, days: int, tz: ZoneInfo) -> datetime:
    local_dt = dt_utc.astimezone(tz)
    target_date = local_dt.date() + timedelta(days=days)
    shifted_local = datetime.combine(
        target_date,
        local_dt.timetz().replace(tzinfo=None),
        tzinfo=tz,
    )
    return shifted_local.astimezone(timezone.utc)


def _normalize_subject_fingerprint(title: str) -> str:
    cleaned = title.strip().lower()
    for prefix in ("[cours] ", "[td] ", "[tp] ", "[examen] ", "[séance] "):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    return cleaned


def _format_course_title(subject: str, session_type: str | None) -> str:
    clean_subj = subject.strip()
    st = (session_type or "cours").lower()
    if st in ("td", "tp", "examen"):
        prefix = f"[{SUBTYPE_LABELS_FR[st]}]"
        if not clean_subj.lower().startswith(prefix.lower()):
            return f"{prefix} {clean_subj}"[:140]
    return clean_subj[:140]


def _format_course_notes(
    *,
    session_type: str | None,
    teacher: str | None,
    room: str | None,
    group_name: str | None,
    valid_from: str | None,
    valid_until: str | None,
) -> str | None:
    _ = (session_type, teacher, room, group_name, valid_from, valid_until)
    return None


def enrich_schedule_events(
    events_to_render: list[ScheduleEventRecord],
    all_user_events: list[ScheduleEventRecord],
) -> list[ScheduleEventResponse]:
    sorted_events = sorted(events_to_render, key=lambda event: event.starts_at)
    sorted_all = sorted(all_user_events, key=lambda event: event.starts_at)

    responses: list[ScheduleEventResponse] = []
    for event in sorted_events:
        conflicting_ids = [
            other.id
            for other in sorted_all
            if other.id != event.id
            and do_events_overlap(event.starts_at, event.ends_at, other.starts_at, other.ends_at)
        ]
        duration_minutes = max(0, round((event.ends_at - event.starts_at).total_seconds() / 60))
        responses.append(
            ScheduleEventResponse(
                id=event.id,
                user_id=event.user_id,
                title=event.title,
                type=event.type,
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                notes=event.notes,
                source=event.source,
                import_id=event.import_id,
                session_subtype=event.session_subtype,
                teacher=event.teacher,
                room=event.room,
                group_name=event.group_name,
                duration_minutes=duration_minutes,
                has_conflict=bool(conflicting_ids),
                conflicting_event_ids=conflicting_ids,
                created_at=event.created_at,
                updated_at=event.updated_at,
            )
        )
    return responses


def _to_import_response(record: TimetableImportRecord) -> TimetableImportResponse:
    courses = [ExtractedCourseRowSchema.model_validate(item) for item in record.extracted_courses]
    anomalies = [TimetableAnomalySchema.model_validate(item) for item in record.anomalies]
    blocking_count = sum(1 for a in anomalies if a.severity == "error")
    return TimetableImportResponse(
        id=record.id,
        user_id=record.user_id,
        filename=record.filename,
        file_format=record.file_format,
        mime_type=record.mime_type,
        file_size_bytes=record.file_size_bytes,
        source_preview_text=None if record.source_deleted else record.source_preview_text,
        source_deleted=record.source_deleted,
        status=record.status,
        valid_from=record.valid_from,
        valid_until=record.valid_until,
        extracted_courses=courses,
        anomalies=anomalies,
        warnings=list(record.warnings),
        blocking_anomalies_count=blocking_count,
        created_events_count=record.created_events_count,
        skipped_duplicates_count=record.skipped_duplicates_count,
        replaced_events_count=record.replaced_events_count,
        created_at=record.created_at,
        updated_at=record.updated_at,
        validated_at=record.validated_at,
    )


class ScheduleService:
    def __init__(self, schedule_repo: ScheduleRepository) -> None:
        self._schedule_repo = schedule_repo

    def list_events(
        self,
        user_id: UUID,
        *,
        week_start: date | None = None,
        tz_name: str = "Africa/Dakar",
    ) -> list[ScheduleEventResponse]:
        all_events = self._schedule_repo.list_by_user(user_id)
        if week_start is None:
            return enrich_schedule_events(all_events, all_events)

        tz = ZoneInfo(tz_name)
        monday = week_start - timedelta(days=week_start.weekday())
        sunday = monday + timedelta(days=6)
        week_events = [
            event
            for event in all_events
            if monday <= event.starts_at.astimezone(tz).date() <= sunday
        ]
        return enrich_schedule_events(week_events, all_events)

    def create_event(self, user_id: UUID, payload: ScheduleEventCreate) -> ScheduleEventResponse:
        now = datetime.now(timezone.utc)
        record = ScheduleEventRecord(
            id=uuid4(),
            user_id=user_id,
            title=payload.title,
            type=payload.type,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            notes=payload.notes,
            source=payload.source,
            import_id=payload.import_id,
            session_subtype=payload.session_subtype.value if payload.session_subtype else None,
            teacher=payload.teacher,
            room=payload.room,
            group_name=payload.group_name,
            created_at=now,
            updated_at=now,
        )
        saved = self._schedule_repo.save(record)
        all_events = self._schedule_repo.list_by_user(user_id)
        return enrich_schedule_events([saved], all_events)[0]

    def get_event(self, user_id: UUID, event_id: UUID) -> ScheduleEventResponse:
        record = self._schedule_repo.get(user_id, event_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Créneau introuvable.")
        all_events = self._schedule_repo.list_by_user(user_id)
        return enrich_schedule_events([record], all_events)[0]

    def update_event(
        self,
        user_id: UUID,
        event_id: UUID,
        payload: ScheduleEventUpdate,
    ) -> ScheduleEventResponse:
        existing = self._schedule_repo.get(user_id, event_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Créneau introuvable.")

        fields = payload.model_fields_set
        next_starts_at = (
            payload.starts_at
            if "starts_at" in fields and payload.starts_at
            else existing.starts_at
        )
        next_ends_at = (
            payload.ends_at if "ends_at" in fields and payload.ends_at else existing.ends_at
        )
        if next_ends_at <= next_starts_at:
            raise AppError(
                422,
                "VALIDATION_ERROR",
                "L’heure de fin doit être strictement postérieure au début.",
            )

        updates: dict[str, object] = {
            "starts_at": next_starts_at,
            "ends_at": next_ends_at,
            "updated_at": datetime.now(timezone.utc),
        }
        if "title" in fields and payload.title is not None:
            updates["title"] = payload.title
        if "type" in fields and payload.type is not None:
            updates["type"] = payload.type
        if "notes" in fields:
            updates["notes"] = payload.notes
        if "session_subtype" in fields:
            updates["session_subtype"] = (
                payload.session_subtype.value if payload.session_subtype else None
            )
        if "teacher" in fields:
            updates["teacher"] = payload.teacher
        if "room" in fields:
            updates["room"] = payload.room
        if "group_name" in fields:
            updates["group_name"] = payload.group_name

        saved = self._schedule_repo.save(existing.model_copy(update=updates))
        all_events = self._schedule_repo.list_by_user(user_id)
        return enrich_schedule_events([saved], all_events)[0]

    def delete_event(self, user_id: UUID, event_id: UUID) -> None:
        if not self._schedule_repo.delete(user_id, event_id):
            raise AppError(404, "NOT_FOUND", "Créneau introuvable.")

    def duplicate_week(
        self,
        user_id: UUID,
        source_week_start: date,
        tz_name: str = "Africa/Dakar",
    ) -> DuplicateWeekResponse:
        tz = ZoneInfo(tz_name)
        all_events = self._schedule_repo.list_by_user(user_id)
        monday = source_week_start - timedelta(days=source_week_start.weekday())
        sunday = monday + timedelta(days=6)

        source_events = sorted(
            [
                event
                for event in all_events
                if monday <= event.starts_at.astimezone(tz).date() <= sunday
            ],
            key=lambda event: event.starts_at,
        )

        existing_keys = {
            (event.title.strip().lower(), event.starts_at, event.ends_at)
            for event in all_events
        }

        now = datetime.now(timezone.utc)
        to_create: list[ScheduleEventRecord] = []
        skipped_count = 0

        for event in source_events:
            next_starts = _shift_local_days(event.starts_at, 7, tz)
            next_ends = _shift_local_days(event.ends_at, 7, tz)
            fingerprint = (event.title.strip().lower(), next_starts, next_ends)

            if fingerprint in existing_keys:
                skipped_count += 1
                continue

            existing_keys.add(fingerprint)
            to_create.append(
                ScheduleEventRecord(
                    id=uuid4(),
                    user_id=user_id,
                    title=event.title,
                    type=event.type,
                    starts_at=next_starts,
                    ends_at=next_ends,
                    notes=event.notes,
                    source=event.source,
                    import_id=event.import_id,
                    session_subtype=event.session_subtype,
                    teacher=event.teacher,
                    room=event.room,
                    group_name=event.group_name,
                    created_at=now,
                    updated_at=now,
                )
            )

        saved_records = self._schedule_repo.save_many(to_create) if to_create else []
        updated_all = self._schedule_repo.list_by_user(user_id)
        enriched = enrich_schedule_events(saved_records, updated_all)

        return DuplicateWeekResponse(
            created=enriched,
            created_count=len(enriched),
            skipped_count=skipped_count,
        )

    # -------------------------------------------------------------------------
    # IMPORT INTELLIGENT DE L'EMPLOI DU TEMPS (Sections 3 à 9)
    # -------------------------------------------------------------------------

    def _check_import_rate_limit(
        self,
        user_id: UUID,
        now_utc: datetime,
        rate_limit_per_minute: int,
    ) -> None:
        one_min_ago = now_utc - timedelta(minutes=1)
        recent_imports = [
            imp
            for imp in self._schedule_repo.list_imports_by_user(user_id)
            if imp.created_at >= one_min_ago
        ]
        if len(recent_imports) >= rate_limit_per_minute:
            raise AppError(
                429,
                "TIMETABLE_IMPORT_RATE_LIMITED",
                "Trop de tentatives d’importation en une minute. Veuillez patienter quelques instants.",
            )

    def analyze_timetable_import(
        self,
        user_id: UUID,
        *,
        filename: str,
        content_type: str | None,
        content: bytes,
        max_bytes: int = 10 * 1024 * 1024,
        rate_limit_per_minute: int = 15,
        tz_name: str = "Africa/Dakar",
        ai_config: dict[str, object] | None = None,
    ) -> TimetableImportResponse:
        now = datetime.now(timezone.utc)
        self._check_import_rate_limit(user_id, now, rate_limit_per_minute)

        extracted = extract_timetable_from_bytes(
            filename=filename,
            content_type=content_type,
            content=content,
            max_bytes=max_bytes,
            ai_config=ai_config,
        )

        tz = ZoneInfo(tz_name)
        local_today = now.astimezone(tz).date()
        current_monday = local_today - timedelta(days=local_today.weekday())
        existing_events = self._schedule_repo.list_by_user(user_id)

        anomalies = detect_timetable_anomalies(
            extracted.courses,
            existing_events=existing_events,
            target_week_monday=current_monday,
            tz_name=tz_name,
        )

        record = TimetableImportRecord(
            id=uuid4(),
            user_id=user_id,
            filename=filename.strip()[:255],
            file_format=extracted.file_format,
            mime_type=extracted.mime_type,
            file_size_bytes=len(content),
            file_sha256=extracted.file_sha256,
            source_preview_text=extracted.preview_text,
            source_deleted=False,
            status=TimetableImportStatus.pending_review,
            valid_from=extracted.valid_from,
            valid_until=extracted.valid_until,
            extracted_courses=[c.model_dump(mode="json") for c in extracted.courses],
            anomalies=[a.model_dump(mode="json") for a in anomalies],
            warnings=extracted.warnings,
            created_events_count=0,
            skipped_duplicates_count=0,
            replaced_events_count=0,
            created_at=now,
            updated_at=now,
            validated_at=None,
        )
        saved = self._schedule_repo.save_import(record)
        return _to_import_response(saved)

    def list_imports(self, user_id: UUID) -> list[TimetableImportResponse]:
        records = self._schedule_repo.list_imports_by_user(user_id)
        return [_to_import_response(rec) for rec in records]

    def get_import(self, user_id: UUID, import_id: UUID) -> TimetableImportResponse:
        record = self._schedule_repo.get_import(user_id, import_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Session d’importation d’emploi du temps introuvable.")
        return _to_import_response(record)

    def update_import_draft(
        self,
        user_id: UUID,
        import_id: UUID,
        payload: TimetableImportUpdateDraftRequest,
        *,
        tz_name: str = "Africa/Dakar",
    ) -> TimetableImportResponse:
        record = self._schedule_repo.get_import(user_id, import_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Session d’importation d’emploi du temps introuvable.")
        if record.status != TimetableImportStatus.pending_review:
            raise AppError(
                409,
                "TIMETABLE_IMPORT_ALREADY_RESOLVED",
                "Cet import a déjà été validé ou annulé et ne peut plus être modifié.",
            )

        now = datetime.now(timezone.utc)
        tz = ZoneInfo(tz_name)
        local_today = now.astimezone(tz).date()
        current_monday = local_today - timedelta(days=local_today.weekday())
        existing_events = self._schedule_repo.list_by_user(user_id)

        normalized_courses: list[ExtractedCourseRowSchema] = []
        for idx, c in enumerate(payload.courses, start=1):
            day_label = DAY_NAMES_FR.get(c.day_of_week) if c.day_of_week is not None else None
            # Une fois corrigée par l'utilisateur avec matière + jour + horaires valides, l'incertitude initiale est levée
            still_uncertain = (
                c.day_of_week is None
                or not c.start_time
                or not c.end_time
                or not c.subject.strip()
            )
            normalized_courses.append(
                c.model_copy(
                    update={
                        "row_id": c.row_id or f"row_{idx}",
                        "day_label": day_label,
                        "valid_from": payload.valid_from if payload.valid_from is not None else c.valid_from,
                        "valid_until": payload.valid_until if payload.valid_until is not None else c.valid_until,
                        "uncertain": still_uncertain,
                        "uncertainty_reasons": c.uncertainty_reasons if still_uncertain else [],
                    }
                )
            )

        anomalies = detect_timetable_anomalies(
            normalized_courses,
            existing_events=existing_events,
            target_week_monday=current_monday,
            tz_name=tz_name,
        )

        updated = record.model_copy(
            update={
                "valid_from": payload.valid_from if payload.valid_from is not None else record.valid_from,
                "valid_until": payload.valid_until if payload.valid_until is not None else record.valid_until,
                "extracted_courses": [c.model_dump(mode="json") for c in normalized_courses],
                "anomalies": [a.model_dump(mode="json") for a in anomalies],
                "updated_at": now,
            }
        )
        saved = self._schedule_repo.save_import(updated)
        return _to_import_response(saved)

    def cancel_import(self, user_id: UUID, import_id: UUID) -> TimetableImportResponse:
        record = self._schedule_repo.get_import(user_id, import_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Session d’importation d’emploi du temps introuvable.")
        if record.status == TimetableImportStatus.validated:
            raise AppError(
                409,
                "TIMETABLE_IMPORT_ALREADY_RESOLVED",
                "Un import déjà validé ne peut plus être annulé.",
            )
        if record.status == TimetableImportStatus.cancelled:
            return _to_import_response(record)

        now = datetime.now(timezone.utc)
        cancelled = record.model_copy(
            update={
                "status": TimetableImportStatus.cancelled,
                "updated_at": now,
            }
        )
        saved = self._schedule_repo.save_import(cancelled)
        return _to_import_response(saved)

    def delete_import_source(self, user_id: UUID, import_id: UUID) -> TimetableImportResponse:
        record = self._schedule_repo.get_import(user_id, import_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Session d’importation d’emploi du temps introuvable.")
        now = datetime.now(timezone.utc)
        wiped = record.model_copy(
            update={
                "source_preview_text": None,
                "source_deleted": True,
                "updated_at": now,
            }
        )
        saved = self._schedule_repo.save_import(wiped)
        return _to_import_response(saved)

    def confirm_import(
        self,
        user_id: UUID,
        import_id: UUID,
        payload: TimetableImportConfirmRequest | None = None,
        *,
        tz_name: str = "Africa/Dakar",
    ) -> TimetableImportConfirmResponse:
        record = self._schedule_repo.get_import(user_id, import_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Session d’importation d’emploi du temps introuvable.")
        if record.status != TimetableImportStatus.pending_review:
            raise AppError(
                409,
                "TIMETABLE_IMPORT_ALREADY_RESOLVED",
                "Cet import a déjà été validé ou annulé.",
            )

        req = payload or TimetableImportConfirmRequest()
        courses_list = (
            req.courses
            if req.courses is not None
            else [ExtractedCourseRowSchema.model_validate(item) for item in record.extracted_courses]
        )

        valid_from = req.valid_from if req.valid_from is not None else record.valid_from
        valid_until = req.valid_until if req.valid_until is not None else record.valid_until

        normalized_courses: list[ExtractedCourseRowSchema] = []
        for idx, c in enumerate(courses_list, start=1):
            day_label = DAY_NAMES_FR.get(c.day_of_week) if c.day_of_week is not None else None
            still_uncertain = (
                c.day_of_week is None
                or not c.start_time
                or not c.end_time
                or not c.subject.strip()
            )
            normalized_courses.append(
                c.model_copy(
                    update={
                        "row_id": c.row_id or f"row_{idx}",
                        "day_label": day_label,
                        "valid_from": valid_from or c.valid_from,
                        "valid_until": valid_until or c.valid_until,
                        "uncertain": still_uncertain,
                        "uncertainty_reasons": c.uncertainty_reasons if still_uncertain else [],
                    }
                )
            )

        active_courses = [c for c in normalized_courses if not c.ignored]
        if not active_courses:
            raise AppError(
                422,
                "TIMETABLE_NO_ACTIVE_COURSES",
                "Aucun cours actif à enregistrer. Ajoutez ou activez au moins une ligne de cours.",
            )

        now = datetime.now(timezone.utc)
        tz = ZoneInfo(tz_name)
        local_today = now.astimezone(tz).date()

        base_date = req.target_week_start or local_today
        base_monday = base_date - timedelta(days=base_date.weekday())

        existing_events = self._schedule_repo.list_by_user(user_id)
        anomalies = detect_timetable_anomalies(
            normalized_courses,
            existing_events=existing_events,
            target_week_monday=base_monday,
            tz_name=tz_name,
        )
        blocking_errors = [a for a in anomalies if a.severity == "error"]
        if blocking_errors:
            raise AppError(
                422,
                "TIMETABLE_VALIDATION_FAILED",
                f"Impossible de valider l’emploi du temps ({len(blocking_errors)} anomalie(s) bloquante(s)) : {blocking_errors[0].message}",
            )

        # Calcul du nombre de semaines à générer
        recurrence_weeks = max(1, min(req.recurrence_weeks, 24))
        parsed_valid_from: date | None = None
        parsed_valid_until: date | None = None
        if valid_from:
            try:
                parsed_valid_from = date.fromisoformat(valid_from)
            except ValueError:
                parsed_valid_from = None
        if valid_until:
            try:
                parsed_valid_until = date.fromisoformat(valid_until)
            except ValueError:
                parsed_valid_until = None

        if parsed_valid_from and parsed_valid_until and parsed_valid_until < parsed_valid_from:
            raise AppError(
                422,
                "TIMETABLE_INVALID_VALIDITY_RANGE",
                "La date de fin de validité doit être postérieure ou égale à la date de début.",
            )

        if req.target_week_start is None and parsed_valid_from is not None:
            # Si la période de validité inclut la semaine courante, on commence à la semaine courante ou au début de validité
            if parsed_valid_from <= local_today <= (parsed_valid_until or local_today):
                base_monday = local_today - timedelta(days=local_today.weekday())
            else:
                base_monday = parsed_valid_from - timedelta(days=parsed_valid_from.weekday())

        # Option de remplacement d'un ancien emploi du temps importé (sans toucher aux séances ni aux créneaux manuels)
        replaced_count = 0
        if req.replace_existing_imported:
            replaced_count = self._schedule_repo.delete_imported_events(user_id)
            existing_events = self._schedule_repo.list_by_user(user_id)

        existing_fingerprints: set[tuple[str, datetime, datetime]] = set()
        for ev in existing_events:
            existing_fingerprints.add(
                (_normalize_subject_fingerprint(ev.title), ev.starts_at, ev.ends_at)
            )
            existing_fingerprints.add((ev.title.strip().lower(), ev.starts_at, ev.ends_at))

        to_create: list[ScheduleEventRecord] = []
        skipped_duplicates = 0

        for week_offset in range(recurrence_weeks):
            week_monday = base_monday + timedelta(days=7 * week_offset)
            for row in active_courses:
                assert row.day_of_week is not None
                assert row.start_time is not None
                assert row.end_time is not None

                course_date = week_monday + timedelta(days=row.day_of_week)
                if (
                    recurrence_weeks > 1
                    and parsed_valid_from is not None
                    and course_date < parsed_valid_from
                ):
                    continue
                if (
                    recurrence_weeks > 1
                    and parsed_valid_until is not None
                    and course_date > parsed_valid_until
                ):
                    continue

                sh, sm = [int(x) for x in row.start_time.split(":")]
                eh, em = [int(x) for x in row.end_time.split(":")]

                starts_local = datetime.combine(course_date, time(sh, sm), tzinfo=tz)
                ends_local = datetime.combine(course_date, time(eh, em), tzinfo=tz)
                starts_utc = starts_local.astimezone(timezone.utc)
                ends_utc = ends_local.astimezone(timezone.utc)

                formatted_title = _format_course_title(row.subject, row.session_type.value)
                norm_subj = _normalize_subject_fingerprint(row.subject)

                fp_norm = (norm_subj, starts_utc, ends_utc)
                fp_full = (formatted_title.lower(), starts_utc, ends_utc)

                if fp_norm in existing_fingerprints or fp_full in existing_fingerprints:
                    skipped_duplicates += 1
                    continue

                existing_fingerprints.add(fp_norm)
                existing_fingerprints.add(fp_full)

                notes = _format_course_notes(
                    session_type=row.session_type.value,
                    teacher=row.teacher,
                    room=row.room,
                    group_name=row.group_name,
                    valid_from=valid_from,
                    valid_until=valid_until,
                )

                to_create.append(
                    ScheduleEventRecord(
                        id=uuid4(),
                        user_id=user_id,
                        title=formatted_title,
                        type=ScheduleEventType.course,
                        starts_at=starts_utc,
                        ends_at=ends_utc,
                        notes=notes,
                        source=ScheduleEventSource.timetable_import,
                        import_id=record.id,
                        session_subtype=(
                            row.session_type.value
                            if isinstance(row.session_type, CourseSessionSubtype)
                            else str(row.session_type)
                        ),
                        teacher=row.teacher,
                        room=row.room,
                        group_name=row.group_name,
                        created_at=now,
                        updated_at=now,
                    )
                )

        saved_events = self._schedule_repo.save_many(to_create) if to_create else []
        updated_all_events = self._schedule_repo.list_by_user(user_id)
        enriched_created = enrich_schedule_events(saved_events, updated_all_events)

        updated_import = record.model_copy(
            update={
                "status": TimetableImportStatus.validated,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "extracted_courses": [c.model_dump(mode="json") for c in normalized_courses],
                "anomalies": [a.model_dump(mode="json") for a in anomalies],
                "created_events_count": len(enriched_created),
                "skipped_duplicates_count": skipped_duplicates,
                "replaced_events_count": replaced_count,
                "updated_at": now,
                "validated_at": now,
            }
        )
        saved_import = self._schedule_repo.save_import(updated_import)

        return TimetableImportConfirmResponse(
            import_record=_to_import_response(saved_import),
            created_events=enriched_created,
            created_count=len(enriched_created),
            skipped_duplicates_count=skipped_duplicates,
            replaced_count=replaced_count,
        )
