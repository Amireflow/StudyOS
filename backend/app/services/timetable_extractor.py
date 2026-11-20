from __future__ import annotations

import base64
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
from typing import Any
import zipfile
from zoneinfo import ZoneInfo

import docx
import httpx
import openpyxl
from PIL import Image
from pypdf import PdfReader
import xlrd

from app.core.errors import AppError
from app.repositories.memory import ScheduleEventRecord
from app.schemas.common import (
    CourseSessionSubtype,
    TimetableAnomalyType,
    TimetableFileFormat,
)
from app.schemas.schedule import (
    ExtractedCourseRowSchema,
    TimetableAnomalySchema,
)

DAY_NAMES_FR: dict[int, str] = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche",
}

DAY_PATTERNS: list[tuple[int, re.Pattern[str]]] = [
    (0, re.compile(r"\b(?:lundi|lun\.?)\b", re.IGNORECASE)),
    (1, re.compile(r"\b(?:mardi|mar\.?)\b", re.IGNORECASE)),
    (2, re.compile(r"\b(?:mercredi|mer\.?)\b", re.IGNORECASE)),
    (3, re.compile(r"\b(?:jeudi|jeu\.?)\b", re.IGNORECASE)),
    (4, re.compile(r"\b(?:vendredi|ven\.?)\b", re.IGNORECASE)),
    (5, re.compile(r"\b(?:samedi|sam\.?)\b", re.IGNORECASE)),
    (6, re.compile(r"\b(?:dimanche|dim\.?)\b", re.IGNORECASE)),
]

ALLOWED_EXTENSIONS: dict[str, TimetableFileFormat] = {
    ".pdf": TimetableFileFormat.pdf,
    ".png": TimetableFileFormat.image,
    ".jpg": TimetableFileFormat.image,
    ".jpeg": TimetableFileFormat.image,
    ".webp": TimetableFileFormat.image,
    ".xlsx": TimetableFileFormat.excel,
    ".xls": TimetableFileFormat.excel,
    ".docx": TimetableFileFormat.word,
}

ALLOWED_MIME_PREFIXES: dict[TimetableFileFormat, tuple[str, ...]] = {
    TimetableFileFormat.pdf: ("application/pdf", "application/x-pdf", "application/octet-stream"),
    TimetableFileFormat.image: (
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "application/octet-stream",
    ),
    TimetableFileFormat.excel: (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/excel",
        "application/x-excel",
        "application/octet-stream",
    ),
    TimetableFileFormat.word: (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/octet-stream",
    ),
}

FORBIDDEN_SIGNATURES: tuple[bytes, ...] = (
    b"MZ",
    b"\x7fELF",
    b"#!/",
    b"<?php",
    b"<script",
)


class ExtractedTimetableResult:
    def __init__(
        self,
        *,
        file_format: TimetableFileFormat,
        mime_type: str,
        file_sha256: str,
        preview_text: str,
        courses: list[ExtractedCourseRowSchema],
        valid_from: str | None,
        valid_until: str | None,
        warnings: list[str],
    ) -> None:
        self.file_format = file_format
        self.mime_type = mime_type
        self.file_sha256 = file_sha256
        self.preview_text = preview_text
        self.courses = courses
        self.valid_from = valid_from
        self.valid_until = valid_until
        self.warnings = warnings


def validate_and_classify_file(
    *,
    filename: str,
    content_type: str | None,
    content: bytes,
    max_bytes: int,
) -> tuple[TimetableFileFormat, str, str]:
    """Vérifie la taille, l'extension, le type MIME et la signature binaire réelle du fichier."""
    clean_name = (filename or "").strip()
    if not clean_name:
        raise AppError(422, "INVALID_TIMETABLE_FILENAME", "Le nom du fichier est obligatoire.")

    if len(content) == 0:
        raise AppError(422, "EMPTY_TIMETABLE_FILE", "Le fichier importé est vide.")

    if len(content) > max_bytes:
        max_mb = round(max_bytes / (1024 * 1024), 1)
        raise AppError(
            413,
            "TIMETABLE_FILE_TOO_LARGE",
            f"Le fichier dépasse la taille maximale autorisée ({max_mb} Mo).",
        )

    lower_name = clean_name.lower()
    ext = ""
    if "." in lower_name:
        ext = "." + lower_name.rsplit(".", 1)[-1]

    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(
            422,
            "UNSUPPORTED_TIMETABLE_FORMAT",
            "Format non pris en charge. Formats acceptés : PDF (.pdf), Images (.png, .jpg, .jpeg, .webp), Excel (.xlsx, .xls) et Word (.docx).",
        )

    file_format = ALLOWED_EXTENSIONS[ext]
    normalized_mime = (content_type or "application/octet-stream").split(";")[0].strip().lower()
    if not normalized_mime:
        normalized_mime = "application/octet-stream"

    allowed_mimes = ALLOWED_MIME_PREFIXES[file_format]
    if normalized_mime not in allowed_mimes:
        raise AppError(
            422,
            "INVALID_TIMETABLE_MIME_TYPE",
            f"Le type MIME « {normalized_mime} » ne correspond pas à l’extension « {ext} ».",
        )

    head = content[:64]
    for sig in FORBIDDEN_SIGNATURES:
        if head.startswith(sig):
            raise AppError(
                422,
                "INVALID_TIMETABLE_FILE_CONTENT",
                "Contenu de fichier exécutable ou potentiellement malveillant rejeté.",
            )

    # Vérification de la signature binaire réelle (magic bytes)
    if file_format == TimetableFileFormat.pdf:
        if b"%PDF-" not in content[:1024]:
            raise AppError(
                422,
                "INVALID_TIMETABLE_FILE_CONTENT",
                "Le contenu du fichier ne correspond pas à un document PDF valide.",
            )
    elif file_format == TimetableFileFormat.image:
        is_png = content.startswith(b"\x89PNG\r\n\x1a\n")
        is_jpg = content.startswith(b"\xff\xd8\xff")
        is_webp = content.startswith(b"RIFF") and content[8:12] == b"WEBP"
        if not (is_png or is_jpg or is_webp):
            raise AppError(
                422,
                "INVALID_TIMETABLE_FILE_CONTENT",
                "La signature binaire du fichier ne correspond pas à une image PNG, JPEG ou WEBP valide.",
            )
    elif ext == ".docx":
        if not content.startswith(b"PK\x03\x04"):
            raise AppError(
                422,
                "INVALID_TIMETABLE_FILE_CONTENT",
                "Le fichier .docx n’est pas une archive OpenXML valide.",
            )
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                if "word/document.xml" not in zf.namelist():
                    raise ValueError("word/document.xml manquant")
        except Exception as exc:
            raise AppError(
                422,
                "INVALID_TIMETABLE_FILE_CONTENT",
                "Le contenu du fichier Word (.docx) est corrompu ou invalide.",
            ) from exc
    elif ext == ".xlsx":
        if not content.startswith(b"PK\x03\x04"):
            raise AppError(
                422,
                "INVALID_TIMETABLE_FILE_CONTENT",
                "Le fichier .xlsx n’est pas un classeur OpenXML valide.",
            )
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                names = zf.namelist()
                if not any(name.startswith("xl/") for name in names):
                    raise ValueError("xl/ manquant")
        except Exception as exc:
            raise AppError(
                422,
                "INVALID_TIMETABLE_FILE_CONTENT",
                "Le contenu du fichier Excel (.xlsx) est corrompu ou invalide.",
            ) from exc
    elif ext == ".xls":
        is_ole2 = content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
        is_zip_xlsx = content.startswith(b"PK\x03\x04")
        is_tabular_text = False
        if not is_ole2 and not is_zip_xlsx:
            try:
                decoded = content.decode("utf-8", errors="strict")
                is_tabular_text = any(sep in decoded for sep in ("\t", ";", "|", ",")) and len(decoded.strip()) >= 5
            except UnicodeDecodeError:
                is_tabular_text = False
        if not (is_ole2 or is_zip_xlsx or is_tabular_text):
            raise AppError(
                422,
                "INVALID_TIMETABLE_FILE_CONTENT",
                "Le contenu du fichier Excel (.xls) est invalide ou illisible.",
            )

    sha256_hex = hashlib.sha256(content).hexdigest()
    return file_format, normalized_mime, sha256_hex


def _match_day_of_week(text: str) -> int | None:
    if not text:
        return None
    for day_idx, pattern in DAY_PATTERNS:
        if pattern.search(text):
            return day_idx
    return None


def _normalize_time_token(hour_str: str, minute_str: str | None) -> str | None:
    if "?" in hour_str or (minute_str and "?" in minute_str):
        return None
    try:
        hour = int(hour_str)
        minute = int(minute_str) if minute_str else 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    except ValueError:
        return None
    return None


TIME_RANGE_REGEX = re.compile(
    r"(?<!\d)(\d{1,2}|\?\?)\s*[hH:\.]\s*(\d{2}|\?\?)?\s*(?:-|–|—|à|a|/|au|->)\s*(\d{1,2}|\?\?)\s*[hH:\.]?\s*(\d{2}|\?\?)?(?!\d)",
    re.IGNORECASE,
)

SINGLE_TIME_REGEX = re.compile(
    r"^\s*(\d{1,2}|\?\?)\s*[hH:\.]\s*(\d{2}|\?\?)?\s*$"
)

UNREADABLE_TIME_HINT_REGEX = re.compile(
    r"(?:\?\?\s*[hH:]|[hH:]\s*\?\?|horaire\s+illisible|heure\s+illisible|tbd|inconnu|\?\?\s*-\s*\?\?)",
    re.IGNORECASE,
)


def _extract_time_range(text: str) -> tuple[str | None, str | None, bool, str | None]:
    """
    Extrait (start_time, end_time, has_unreadable_time, matched_span_text) depuis une chaîne.
    Ne fabrique jamais un horaire si l'un des éléments est illisible.
    """
    if not text:
        return None, None, False, None

    match = TIME_RANGE_REGEX.search(text)
    if match:
        h1, m1, h2, m2 = match.group(1), match.group(2), match.group(3), match.group(4)
        start_t = _normalize_time_token(h1, m1)
        end_t = _normalize_time_token(h2, m2)
        unreadable = start_t is None or end_t is None
        return start_t, end_t, unreadable, match.group(0)

    if UNREADABLE_TIME_HINT_REGEX.search(text):
        return None, None, True, None

    return None, None, False, None


def _parse_single_time(text: str) -> tuple[str | None, bool]:
    cleaned = (text or "").strip()
    if not cleaned:
        return None, False
    match = SINGLE_TIME_REGEX.match(cleaned)
    if match:
        t = _normalize_time_token(match.group(1), match.group(2))
        return t, t is None
    if "?" in cleaned or "illisible" in cleaned.lower():
        return None, True
    # Format HH:MM simple
    m2 = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", cleaned)
    if m2:
        t = _normalize_time_token(m2.group(1), m2.group(2))
        return t, t is None
    return None, False


def _detect_session_subtype(text: str) -> CourseSessionSubtype:
    if not text:
        return CourseSessionSubtype.cours
    if re.search(r"\b(?:examen|partiel|contr[ôo]le|ds|épreuve)\b", text, re.IGNORECASE):
        return CourseSessionSubtype.examen
    if re.search(r"\b(?:tp|travaux\s+pratiques|labo(?:ratoire)?)\b", text, re.IGNORECASE):
        return CourseSessionSubtype.tp
    if re.search(r"\b(?:td|travaux\s+dirig[ée]s)\b", text, re.IGNORECASE):
        return CourseSessionSubtype.td
    if re.search(r"\b(?:cm|cours(?:\s+magistral)?|amphi)\b", text, re.IGNORECASE):
        return CourseSessionSubtype.cours
    return CourseSessionSubtype.cours


TEACHER_REGEX = re.compile(
    r"(?:(?:enseignant|prof(?:esseur)?|intervenant)\s*[:\-]\s*([A-Za-zÀ-ÖØ-öø-ÿ\.\-\s]{2,50})|\b((?:Pr\.?|Prof\.?|Dr\.?|M\.|Mme|Mlle)\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ\-]+(?:\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ\-]+)?))",
    re.IGNORECASE,
)

ROOM_REGEX = re.compile(
    r"\b((?:Salle|Amphi(?:théâtre)?|Labo(?:ratoire)?|Bât(?:iment)?)\s*[A-Za-z0-9\-\.]+(?:\s+[A-Za-z0-9\-\.]+)?)\b",
    re.IGNORECASE,
)

GROUP_REGEX = re.compile(
    r"\b((?:Groupe|Grp\.?|Classe|Section)\s*[A-Za-z0-9\-]+|\b(?:L[123]|M[12])\s*[A-Za-z0-9\-]+|\b(?:TD|TP)\s*\d+)\b",
    re.IGNORECASE,
)

DATE_ISO_REGEX = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
DATE_FR_REGEX = re.compile(r"\b(\d{2})/(\d{2})/(20\d{2})\b")


def _extract_validity_dates(text: str) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    found_dates: list[str] = []
    for m in DATE_ISO_REGEX.finditer(text):
        found_dates.append(m.group(1))
    for m in DATE_FR_REGEX.finditer(text):
        day_s, month_s, year_s = m.group(1), m.group(2), m.group(3)
        found_dates.append(f"{year_s}-{month_s}-{day_s}")

    valid_dates: list[str] = []
    for d_str in found_dates:
        try:
            date.fromisoformat(d_str)
            if d_str not in valid_dates:
                valid_dates.append(d_str)
        except ValueError:
            continue

    if len(valid_dates) >= 2:
        sorted_d = sorted(valid_dates[:2])
        return sorted_d[0], sorted_d[1]
    if len(valid_dates) == 1:
        return valid_dates[0], None
    return None, None


def _clean_subject_name(raw_text: str, *tokens_to_strip: str | None) -> str:
    cleaned = raw_text
    for tok in tokens_to_strip:
        if tok:
            cleaned = cleaned.replace(tok, " ")

    # Retirer les mentions de jour au début
    for _, pat in DAY_PATTERNS:
        cleaned = pat.sub(" ", cleaned)

    # Retirer les préfixes génériques et les types de séance entourés de séparateurs
    cleaned = re.sub(
        r"\b(?:enseignant|prof(?:esseur)?|salle|groupe|classe|horaire|cours\s+de)\s*[:\-]?\s*",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"(?:^|[\s\[\(\-|/]+)(?:CM|TD|TP|Cours(?:\s+magistral)?|Travaux\s+dirig[ée]s|Travaux\s+pratiques|Examen|Partiel)(?:$|[\s\]\)\-|/:]+)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[\|\t•·;]+", " ", cleaned)
    cleaned = re.sub(r"(?:\s*[-–—:/,]+\s*){2,}", " - ", cleaned)
    cleaned = re.sub(r"(?:\s*[-–—:/,]+\s*)+$", "", cleaned)
    cleaned = re.sub(r"^(?:\s*[-–—:/,]+\s*)+", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    if cleaned.lower() in ("", "?", "??", "???", "illisible", "inconnu", "n/a", "tbd", "-"):
        return ""
    return cleaned[:140]


def _parse_cell_or_block_details(
    raw_text: str,
    *,
    default_day: int | None = None,
    default_start: str | None = None,
    default_end: str | None = None,
    row_index: int,
) -> ExtractedCourseRowSchema | None:
    text = (raw_text or "").strip()
    if not text or text.lower() in ("-", "—", "libre", "pause", "déjeuner", "repas", "vide"):
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    joined = " | ".join(lines)

    day_idx = _match_day_of_week(joined)
    if day_idx is None:
        day_idx = default_day

    start_t, end_t, unreadable_time, time_span = _extract_time_range(joined)
    if start_t is None and default_start is not None and not unreadable_time:
        start_t = default_start
    if end_t is None and default_end is not None and not unreadable_time:
        end_t = default_end

    teacher: str | None = None
    teacher_span: str | None = None
    t_match = TEACHER_REGEX.search(joined)
    if t_match:
        teacher = (t_match.group(1) or t_match.group(2) or "").strip(" -|,;")
        teacher_span = t_match.group(0)

    room: str | None = None
    room_span: str | None = None
    r_match = ROOM_REGEX.search(joined)
    if r_match:
        room = r_match.group(1).strip(" -|,;")
        room_span = r_match.group(0)

    group_name: str | None = None
    group_span: str | None = None
    g_match = GROUP_REGEX.search(joined)
    if g_match:
        group_name = g_match.group(1).strip(" -|,;")
        group_span = g_match.group(0)

    subtype = _detect_session_subtype(joined)

    # Pour isoler la matière, si le bloc est multi-lignes, privilégier la première ligne non horaire
    subject_source = joined
    if len(lines) > 1:
        for candidate_line in lines:
            c_start, c_end, _, _ = _extract_time_range(candidate_line)
            if c_start and c_end and len(_clean_subject_name(candidate_line, time_span)) < 2:
                continue
            if ROOM_REGEX.fullmatch(candidate_line) or TEACHER_REGEX.fullmatch(candidate_line):
                continue
            subject_source = candidate_line
            break

    subject = _clean_subject_name(
        subject_source,
        time_span,
        teacher_span,
        room_span,
        group_span,
    )

    uncertainty_reasons: list[str] = []
    if unreadable_time or start_t is None or end_t is None:
        uncertainty_reasons.append("Horaire manquant ou partiellement illisible.")
    if day_idx is None:
        uncertainty_reasons.append("Jour de la semaine non identifié.")
    if not subject or "?" in subject or "illisible" in subject.lower():
        uncertainty_reasons.append("Nom de la matière manquant ou ambigu.")
    if "?" in joined:
        uncertainty_reasons.append("Caractères incertains (?) détectés dans le document source.")

    return ExtractedCourseRowSchema(
        row_id=f"row_{row_index}",
        subject=subject,
        day_of_week=day_idx,
        day_label=DAY_NAMES_FR.get(day_idx) if day_idx is not None else None,
        start_time=start_t,
        end_time=end_t,
        teacher=teacher,
        room=room,
        group_name=group_name,
        session_type=subtype,
        uncertain=len(uncertainty_reasons) > 0,
        uncertainty_reasons=uncertainty_reasons,
        ignored=False,
        raw_excerpt=joined[:240],
    )


def parse_schedule_table_matrix(
    matrix: list[list[str]],
    *,
    starting_row_index: int = 1,
) -> list[ExtractedCourseRowSchema]:
    """
    Analyse une table 2D issue d'Excel, Word ou texte tabulaire :
    - Cas A : Table structurée par colonnes (Jour | Début/Horaire | Fin | Matière | Type | Enseignant | Salle | Groupe)
    - Cas B : Grille hebdomadaire 2D (Colonnes = Lundi..Samedi, Lignes = plages horaires 08:00-10:00)
    """
    cleaned_rows = [
        [str(cell or "").strip() for cell in row]
        for row in matrix
        if any(str(cell or "").strip() for cell in row)
    ]
    if not cleaned_rows:
        return []

    header = [c.lower() for c in cleaned_rows[0]]
    results: list[ExtractedCourseRowSchema] = []
    row_counter = starting_row_index

    # Détection Cas B : Grille 2D avec jours de la semaine en en-tête de colonnes
    col_days: dict[int, int] = {}
    for col_idx, cell_text in enumerate(cleaned_rows[0]):
        d = _match_day_of_week(cell_text)
        if d is not None:
            col_days[col_idx] = d

    if len(col_days) >= 2:
        for r_idx in range(1, len(cleaned_rows)):
            row = cleaned_rows[r_idx]
            if not row:
                continue
            row_start, row_end, row_unreadable, _ = _extract_time_range(row[0])
            for col_idx, day_idx in col_days.items():
                if col_idx >= len(row):
                    continue
                cell_val = row[col_idx].strip()
                if not cell_val:
                    continue
                # Évite de dupliquer verticalement la même cellule fusionnée si identique même créneau
                parsed = _parse_cell_or_block_details(
                    cell_val,
                    default_day=day_idx,
                    default_start=row_start,
                    default_end=row_end,
                    row_index=row_counter,
                )
                if parsed is not None:
                    if row_unreadable and (parsed.start_time is None or parsed.end_time is None):
                        parsed.uncertain = True
                        if "Horaire manquant ou partiellement illisible." not in parsed.uncertainty_reasons:
                            parsed.uncertainty_reasons.append("Horaire manquant ou partiellement illisible.")
                    results.append(parsed)
                    row_counter += 1
        return results

    # Détection Cas A : Table par lignes avec en-têtes explicites
    col_map: dict[str, int] = {}
    for idx, col_name in enumerate(header):
        if any(k in col_name for k in ("jour", "day")):
            col_map.setdefault("day", idx)
        elif any(k in col_name for k in ("début", "debut", "start")):
            col_map.setdefault("start", idx)
        elif any(k in col_name for k in ("fin", "end")):
            col_map.setdefault("end", idx)
        elif any(k in col_name for k in ("horaire", "heure", "créneau", "creneau", "time")):
            col_map.setdefault("time_range", idx)
        elif any(k in col_name for k in ("matière", "matiere", "cours", "module", "intitulé", "sujet", "subject", "ue")):
            col_map.setdefault("subject", idx)
        elif any(k in col_name for k in ("enseignant", "prof", "intervenant", "teacher")):
            col_map.setdefault("teacher", idx)
        elif any(k in col_name for k in ("salle", "amphi", "lieu", "room", "local")):
            col_map.setdefault("room", idx)
        elif any(k in col_name for k in ("groupe", "classe", "section", "group", "promo")):
            col_map.setdefault("group", idx)
        elif any(k in col_name for k in ("type", "nature", "format")):
            col_map.setdefault("type", idx)

    if "subject" in col_map or ("day" in col_map and ("start" in col_map or "time_range" in col_map)):
        last_seen_day: int | None = None
        for r_idx in range(1, len(cleaned_rows)):
            row = cleaned_rows[r_idx]
            if not any(row):
                continue

            def _get_col(key: str) -> str:
                c_idx = col_map.get(key)
                if c_idx is not None and c_idx < len(row):
                    return row[c_idx].strip()
                return ""

            day_raw = _get_col("day")
            day_idx = _match_day_of_week(day_raw)
            if day_idx is not None:
                last_seen_day = day_idx
            elif not day_raw and last_seen_day is not None:
                # Gestion des cellules fusionnées verticalement sur la colonne Jour
                day_idx = last_seen_day

            start_t: str | None = None
            end_t: str | None = None
            unreadable_time = False

            if "start" in col_map or "end" in col_map:
                s_val, s_bad = _parse_single_time(_get_col("start"))
                e_val, e_bad = _parse_single_time(_get_col("end"))
                start_t = s_val
                end_t = e_val
                unreadable_time = s_bad or e_bad
                if start_t is None and end_t is None and _get_col("start"):
                    s2, e2, bad2, _ = _extract_time_range(_get_col("start"))
                    start_t, end_t, unreadable_time = s2, e2, bad2

            if (start_t is None or end_t is None) and "time_range" in col_map:
                s2, e2, bad2, _ = _extract_time_range(_get_col("time_range"))
                start_t = start_t or s2
                end_t = end_t or e2
                unreadable_time = unreadable_time or bad2

            subject = _get_col("subject")
            teacher = _get_col("teacher") or None
            room = _get_col("room") or None
            group_name = _get_col("group") or None
            type_raw = _get_col("type")
            subtype = _detect_session_subtype(f"{type_raw} {subject}")

            if subject.lower() in ("?", "??", "???", "illisible", "inconnu"):
                subject = ""

            uncertainty_reasons: list[str] = []
            if unreadable_time or start_t is None or end_t is None:
                uncertainty_reasons.append("Horaire manquant ou partiellement illisible.")
            if day_idx is None:
                uncertainty_reasons.append("Jour de la semaine non identifié.")
            if not subject:
                uncertainty_reasons.append("Nom de la matière manquant ou non identifié.")

            raw_excerpt = " | ".join(c for c in row if c)[:240]
            results.append(
                ExtractedCourseRowSchema(
                    row_id=f"row_{row_counter}",
                    subject=subject[:140],
                    day_of_week=day_idx,
                    day_label=DAY_NAMES_FR.get(day_idx) if day_idx is not None else None,
                    start_time=start_t,
                    end_time=end_t,
                    teacher=teacher,
                    room=room,
                    group_name=group_name,
                    session_type=subtype,
                    uncertain=len(uncertainty_reasons) > 0,
                    uncertainty_reasons=uncertainty_reasons,
                    ignored=False,
                    raw_excerpt=raw_excerpt,
                )
            )
            row_counter += 1
        return results

    # Cas C : Tableau sans en-tête standard -> analyse ligne par ligne
    current_day: int | None = None
    for row in cleaned_rows:
        joined_line = " | ".join(c for c in row if c)
        d = _match_day_of_week(joined_line)
        start_t, end_t, unreadable_t, _ = _extract_time_range(joined_line)
        if d is not None and start_t is None and not unreadable_t and len(row) == 1:
            current_day = d
            continue
        parsed = _parse_cell_or_block_details(
            joined_line,
            default_day=d if d is not None else current_day,
            row_index=row_counter,
        )
        if parsed and (parsed.day_of_week is not None or parsed.start_time is not None or parsed.uncertain):
            if d is not None:
                current_day = d
            results.append(parsed)
            row_counter += 1
    return results


def parse_schedule_text(raw_text: str, *, starting_row_index: int = 1) -> list[ExtractedCourseRowSchema]:
    """
    Extrait les créneaux depuis un texte structuré ou semi-structuré (PDF, OCR image, paragraphes Word).
    Gère les cours sur une seule ligne ou répartis sur plusieurs lignes sous un en-tête de jour.
    """
    if not raw_text or not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # Si le texte contient des lignes tabulaires (séparées par \t ou ; ou | avec un en-tête)
    tabular_rows = [
        [cell.strip() for cell in re.split(r"\t|;", line)]
        for line in lines
        if "\t" in line or line.count(";") >= 2
    ]
    if len(tabular_rows) >= 2:
        from_matrix = parse_schedule_table_matrix(tabular_rows, starting_row_index=starting_row_index)
        if from_matrix:
            return from_matrix

    results: list[ExtractedCourseRowSchema] = []
    current_day: int | None = None
    row_counter = starting_row_index
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        lower_line = line.lower()

        # Ignorer les lignes purement administratives ou titres de document
        if any(
            skip in lower_line
            for skip in (
                "emploi du temps",
                "année universitaire",
                "semestre",
                "valide du",
                "validité",
            )
        ) and _extract_time_range(line)[0] is None and not UNREADABLE_TIME_HINT_REGEX.search(line):
            idx += 1
            continue

        day_in_line = _match_day_of_week(line)
        start_t, end_t, unreadable_t, _ = _extract_time_range(line)

        # En-tête de jour isolé (ex: "LUNDI" ou "Mardi :")
        cleaned_day_only = re.sub(r"[:\-\s]+", "", line)
        if (
            day_in_line is not None
            and start_t is None
            and not unreadable_t
            and len(cleaned_day_only) <= 12
        ):
            current_day = day_in_line
            idx += 1
            continue

        if start_t is not None or unreadable_t or day_in_line is not None:
            effective_day = day_in_line if day_in_line is not None else current_day
            if day_in_line is not None:
                current_day = day_in_line

            # Vérifier si les lignes suivantes complètent ce créneau (ex. Enseignant / Salle sur la ligne suivante)
            combined_lines = [line]
            lookahead = idx + 1
            while lookahead < len(lines) and lookahead <= idx + 2:
                next_line = lines[lookahead]
                next_day = _match_day_of_week(next_line)
                next_s, next_e, next_unreadable, _ = _extract_time_range(next_line)
                if next_day is not None or next_s is not None or next_unreadable:
                    break
                if any(
                    hint in next_line.lower()
                    for hint in ("salle", "amphi", "labo", "enseignant", "prof", "pr.", "dr.", "m.", "mme", "groupe", "td", "tp")
                ):
                    combined_lines.append(next_line)
                    lookahead += 1
                else:
                    break

            parsed = _parse_cell_or_block_details(
                "\n".join(combined_lines),
                default_day=effective_day,
                row_index=row_counter,
            )
            if parsed is not None:
                results.append(parsed)
                row_counter += 1
            idx = lookahead
            continue

        idx += 1

    return results


def _extract_from_pdf(content: bytes) -> tuple[str, list[ExtractedCourseRowSchema], list[str]]:
    warnings: list[str] = []
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise AppError(
            422,
            "INVALID_TIMETABLE_FILE_CONTENT",
            "Impossible de lire le document PDF : fichier endommagé ou protégé.",
        ) from exc

    page_texts: list[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
            if txt.strip():
                page_texts.append(txt.strip())
        except Exception:
            continue

    full_text = "\n".join(page_texts).strip()
    courses = parse_schedule_text(full_text)

    if not full_text:
        warnings.append(
            "Ce PDF semble être un document scanné sans couche texte sélectionnable. Vérifiez ou complétez les créneaux manuellement."
        )
    elif not courses:
        warnings.append(
            "Aucun créneau horaire structuré n’a pu être détecté automatiquement dans ce PDF. Vous pouvez ajouter les cours dans le tableau."
        )

    return full_text[:3000], courses, warnings


def _extract_from_docx(content: bytes) -> tuple[str, list[ExtractedCourseRowSchema], list[str]]:
    warnings: list[str] = []
    try:
        document = docx.Document(io.BytesIO(content))
    except Exception as exc:
        raise AppError(
            422,
            "INVALID_TIMETABLE_FILE_CONTENT",
            "Impossible de lire le document Word (.docx).",
        ) from exc

    paragraphs = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
    preview_parts: list[str] = list(paragraphs)
    courses: list[ExtractedCourseRowSchema] = []
    next_idx = 1

    for table in document.tables:
        matrix: list[list[str]] = []
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells]
            # Déduplication de cellules fusionnées horizontalement si ce sont des plages d'en-tête identiques
            matrix.append(row_cells)
            if any(row_cells):
                preview_parts.append(" | ".join(c.replace("\n", " ") for c in row_cells if c))
        table_courses = parse_schedule_table_matrix(matrix, starting_row_index=next_idx)
        courses.extend(table_courses)
        next_idx += len(table_courses)

    if paragraphs:
        para_text = "\n".join(paragraphs)
        para_courses = parse_schedule_text(para_text, starting_row_index=next_idx)
        # Évite de dupliquer si déjà extrait des tableaux
        if not courses and para_courses:
            courses.extend(para_courses)

    preview_text = "\n".join(preview_parts).strip()[:3000]
    if not courses:
        warnings.append(
            "Aucun cours structuré n’a été détecté dans ce document Word. Vous pouvez saisir ou corriger les lignes ci-dessous."
        )
    return preview_text, courses, warnings


def _extract_from_excel(
    content: bytes,
    filename: str,
) -> tuple[str, list[ExtractedCourseRowSchema], list[str]]:
    warnings: list[str] = []
    ext = "." + filename.lower().rsplit(".", 1)[-1] if "." in filename else ".xlsx"
    courses: list[ExtractedCourseRowSchema] = []
    preview_lines: list[str] = []
    next_idx = 1

    if ext == ".xlsx" or content.startswith(b"PK\x03\x04"):
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        except Exception as exc:
            raise AppError(
                422,
                "INVALID_TIMETABLE_FILE_CONTENT",
                "Impossible d’ouvrir le classeur Excel (.xlsx).",
            ) from exc

        for sheet in wb.worksheets:
            max_r = min(sheet.max_row or 0, 200)
            max_c = min(sheet.max_column or 0, 30)
            if max_r == 0 or max_c == 0:
                continue

            grid: list[list[str]] = []
            for r in range(1, max_r + 1):
                row_vals: list[str] = []
                for c in range(1, max_c + 1):
                    val = sheet.cell(row=r, column=c).value
                    if isinstance(val, datetime):
                        row_vals.append(val.strftime("%H:%M") if val.year == 1900 else val.strftime("%Y-%m-%d"))
                    elif isinstance(val, time):
                        row_vals.append(val.strftime("%H:%M"))
                    elif val is None:
                        row_vals.append("")
                    else:
                        row_vals.append(str(val).strip())
                grid.append(row_vals)

            # Résolution des cellules fusionnées (propagation de la valeur en haut à gauche)
            for merged_range in sheet.merged_cells.ranges:
                top_val = grid[merged_range.min_row - 1][merged_range.min_col - 1]
                if not top_val:
                    continue
                for r in range(merged_range.min_row, min(merged_range.max_row, max_r) + 1):
                    for c in range(merged_range.min_col, min(merged_range.max_col, max_c) + 1):
                        if r == merged_range.min_row and c == merged_range.min_col:
                            continue
                        # Propager uniquement sur la colonne Jour (col 1) ou l'en-tête (ligne 1)
                        if c == 1 or r == 1:
                            grid[r - 1][c - 1] = top_val

            for row_vals in grid:
                if any(row_vals):
                    preview_lines.append(" | ".join(v for v in row_vals if v))

            sheet_courses = parse_schedule_table_matrix(grid, starting_row_index=next_idx)
            courses.extend(sheet_courses)
            next_idx += len(sheet_courses)
    else:
        # Format .xls (BIFF via xlrd ou export tabulaire universitaire)
        if content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            try:
                book = xlrd.open_workbook(file_contents=content)
                for sheet in book.sheets():
                    grid = []
                    for r in range(min(sheet.nrows, 200)):
                        row_vals = [str(sheet.cell_value(r, c)).strip() for c in range(min(sheet.ncols, 30))]
                        grid.append(row_vals)
                        if any(row_vals):
                            preview_lines.append(" | ".join(v for v in row_vals if v))
                    sheet_courses = parse_schedule_table_matrix(grid, starting_row_index=next_idx)
                    courses.extend(sheet_courses)
                    next_idx += len(sheet_courses)
            except Exception as exc:
                raise AppError(
                    422,
                    "INVALID_TIMETABLE_FILE_CONTENT",
                    "Impossible de lire le fichier Excel (.xls).",
                ) from exc
        else:
            decoded = content.decode("utf-8", errors="replace")
            preview_lines.append(decoded[:3000])
            courses = parse_schedule_text(decoded, starting_row_index=1)

    preview_text = "\n".join(preview_lines).strip()[:3000]
    if not courses:
        warnings.append(
            "Aucun créneau horaire n’a pu être extrait automatiquement des feuilles Excel."
        )
    return preview_text, courses, warnings


def _extract_from_image(content: bytes) -> tuple[str, list[ExtractedCourseRowSchema], list[str]]:
    warnings: list[str] = []
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        img = Image.open(io.BytesIO(content))
    except Exception as exc:
        raise AppError(
            422,
            "INVALID_TIMETABLE_FILE_CONTENT",
            "Le fichier image est corrompu ou illisible.",
        ) from exc

    extracted_chunks: list[str] = []

    # 1. Métadonnées textuelles embarquées (PNG tEXt/iTXt, Description, Comment, EXIF ImageDescription)
    for key, val in (img.info or {}).items():
        if isinstance(val, str) and val.strip() and key.lower() not in ("icc_profile", "exif", "xmp"):
            extracted_chunks.append(val.strip())
        elif isinstance(val, bytes):
            try:
                decoded = val.decode("utf-8", errors="ignore").strip()
                if decoded and len(decoded) >= 5:
                    extracted_chunks.append(decoded)
            except Exception:
                pass

    try:
        exif_data = img.getexif()
        if exif_data:
            for tag_id in (0x010E, 0x9286):  # ImageDescription, UserComment
                tag_val = exif_data.get(tag_id)
                if isinstance(tag_val, str) and tag_val.strip():
                    extracted_chunks.append(tag_val.strip())
                elif isinstance(tag_val, bytes):
                    decoded = tag_val.decode("utf-8", errors="ignore").strip("\x00 ")
                    if decoded:
                        extracted_chunks.append(decoded)
    except Exception:
        pass

    # 2. OCR local via Tesseract si présent sur la machine
    if not extracted_chunks and shutil.which("tesseract"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp_in:
                img.save(tmp_in.name, format="PNG")
                proc = subprocess.run(
                    ["tesseract", tmp_in.name, "stdout", "-l", "fra+eng"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    extracted_chunks.append(proc.stdout.strip())
        except Exception:
            pass

    ocr_text = "\n".join(extracted_chunks).strip()
    courses = parse_schedule_text(ocr_text) if ocr_text else []

    if not ocr_text:
        warnings.append(
            f"Image ({img.width}×{img.height}px) reçue : aucun texte OCR lisible n’a pu être extrait avec certitude. "
            "Conformément à la règle de fiabilité, aucun cours n’a été inventé — complétez ou corrigez le tableau ci-dessous."
        )
    elif not courses:
        warnings.append(
            "Le texte extrait de l’image est partiellement ambigu. Vérifiez les créneaux détectés avant d’enregistrer."
        )

    preview_text = (
        ocr_text[:3000]
        if ocr_text
        else f"[Aperçu image {img.format or 'IMG'} — {img.width}×{img.height} px]"
    )
    return preview_text, courses, warnings


def _normalize_ai_time_str(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    m = re.match(r"^(\d{1,2})\s*[:hH.]\s*(\d{2})$", text)
    if not m:
        return None
    h, mins = int(m.group(1)), int(m.group(2))
    if 0 <= h <= 23 and 0 <= mins <= 59:
        return f"{h:02d}:{mins:02d}"
    return None


def _normalize_ai_day(raw_day: Any) -> int | None:
    if isinstance(raw_day, int) and not isinstance(raw_day, bool) and 0 <= raw_day <= 6:
        return raw_day
    if isinstance(raw_day, str):
        cleaned = raw_day.strip()
        if cleaned.isdigit() and 0 <= int(cleaned) <= 6:
            return int(cleaned)
        for day_idx, pattern in DAY_PATTERNS:
            if pattern.search(cleaned):
                return day_idx
    return None


def _normalize_ai_session_type(raw_type: Any) -> CourseSessionSubtype:
    cleaned = str(raw_type or "cours").strip().lower()
    if cleaned in ("td", "travaux dirigés", "travaux diriges"):
        return CourseSessionSubtype.td
    if cleaned in ("tp", "travaux pratiques", "labo"):
        return CourseSessionSubtype.tp
    if cleaned in ("examen", "exam", "partiel", "ds", "contrôle", "controle"):
        return CourseSessionSubtype.examen
    return CourseSessionSubtype.cours


def _try_extract_courses_with_ai(
    *,
    file_format: TimetableFileFormat,
    mime_type: str,
    content: bytes,
    preview_text: str,
    ai_config: dict[str, Any] | None,
) -> tuple[list[ExtractedCourseRowSchema], str | None, str | None]:
    """
    Utilise le modèle IA configuré (River AI / OpenAI / Gemini) pour extraire et structurer
    l'emploi du temps depuis une image (vision) ou un texte complexe, avec validation backend stricte.
    """
    if not ai_config:
        return [], None, None

    from app.ai.provider import (
        _extract_openai_message_text,
        _validate_outbound_base_url,
        canonicalize_provider_name,
        normalize_provider_base_url,
    )

    provider = canonicalize_provider_name(ai_config.get("provider"))
    api_key = str(ai_config.get("api_key") or "").strip()
    if provider == "local" or not api_key:
        return [], None, None

    model = str(ai_config.get("model") or "").strip() or (
        "gemini-2.5-flash" if provider == "gemini" else "gpt-4o-mini"
    )
    base_url = _validate_outbound_base_url(
        normalize_provider_base_url(provider, ai_config.get("base_url"))
    )
    timeout = float(ai_config.get("timeout_seconds") or 18.0)

    instruction = (
        "Tu es un extracteur d'emploi du temps universitaire rigoureux. "
        "Analyse le document fourni et extrais uniquement les cours réellement présents. "
        "RÈGLE ABSOLUE : N'invente JAMAIS une matière, un jour, un horaire, un enseignant ou une salle. "
        "Si une information est absente ou illisible, mets null et uncertain=true avec la raison dans uncertainty_reasons.\n"
        "Réponds UNIQUEMENT par un objet JSON valide de la forme :\n"
        "{\n"
        '  "valid_from": "YYYY-MM-DD" ou null,\n'
        '  "valid_until": "YYYY-MM-DD" ou null,\n'
        '  "courses": [\n'
        "    {\n"
        '      "subject": "Nom de la matière",\n'
        '      "day_of_week": 0 (0=Lundi, 1=Mardi, 2=Mercredi, 3=Jeudi, 4=Vendredi, 5=Samedi, 6=Dimanche) ou null,\n'
        '      "start_time": "HH:MM" ou null,\n'
        '      "end_time": "HH:MM" ou null,\n'
        '      "session_type": "cours" | "td" | "tp" | "examen",\n'
        '      "teacher": "Nom" ou null,\n'
        '      "room": "Salle" ou null,\n'
        '      "group_name": "Groupe" ou null,\n'
        '      "uncertain": false,\n'
        '      "uncertainty_reasons": []\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    raw_reply = ""
    try:
        with httpx.Client(timeout=timeout) as client:
            if provider == "gemini":
                parts: list[dict[str, Any]] = [{"text": instruction}]
                if file_format == TimetableFileFormat.image:
                    parts.append(
                        {
                            "inlineData": {
                                "mimeType": mime_type if mime_type.startswith("image/") else "image/png",
                                "data": base64.b64encode(content).decode("ascii"),
                            }
                        }
                    )
                if preview_text and not preview_text.startswith("[Aperçu image"):
                    parts.append({"text": f"\nContenu textuel extrait :\n{preview_text[:12000]}"})
                res = client.post(
                    f"{base_url}/models/{model}:generateContent",
                    headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                    json={
                        "contents": [{"role": "user", "parts": parts}],
                        "generationConfig": {
                            "temperature": 0.1,
                            "responseMimeType": "application/json",
                        },
                    },
                )
                res.raise_for_status()
                raw_reply = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                if file_format == TimetableFileFormat.image:
                    img_mime = mime_type if mime_type.startswith("image/") else "image/png"
                    b64_str = base64.b64encode(content).decode("ascii")
                    user_content: Any = [
                        {"type": "text", "text": instruction},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{img_mime};base64,{b64_str}"},
                        },
                    ]
                    if preview_text and not preview_text.startswith("[Aperçu image"):
                        user_content.append(
                            {"type": "text", "text": f"Texte OCR auxiliaire :\n{preview_text[:8000]}"}
                        )
                else:
                    if not preview_text.strip():
                        return [], None, None
                    user_content = f"{instruction}\n\nDocument extrait :\n{preview_text[:12000]}"

                res = client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": user_content}],
                        "temperature": 0.1,
                    },
                )
                res.raise_for_status()
                raw_reply = _extract_openai_message_text(
                    res.json()["choices"][0]["message"]["content"]
                )
    except Exception:
        return [], None, None

    cleaned = raw_reply.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL).strip()

    try:
        parsed = json.loads(cleaned)
    except Exception:
        return [], None, None

    raw_courses = parsed.get("courses") if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
    if not isinstance(raw_courses, list):
        return [], None, None

    ai_valid_from: str | None = None
    ai_valid_until: str | None = None
    if isinstance(parsed, dict):
        vf = parsed.get("valid_from")
        vu = parsed.get("valid_until")
        if isinstance(vf, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", vf.strip()):
            ai_valid_from = vf.strip()
        if isinstance(vu, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", vu.strip()):
            ai_valid_until = vu.strip()

    validated_rows: list[ExtractedCourseRowSchema] = []
    for idx, item in enumerate(raw_courses, start=1):
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject") or "").strip()[:140]
        day_idx = _normalize_ai_day(item.get("day_of_week") if "day_of_week" in item else item.get("day"))
        start_t = _normalize_ai_time_str(item.get("start_time"))
        end_t = _normalize_ai_time_str(item.get("end_time"))
        session_t = _normalize_ai_session_type(item.get("session_type"))
        teacher = str(item.get("teacher")).strip()[:120] if item.get("teacher") else None
        room = str(item.get("room")).strip()[:80] if item.get("room") else None
        group_name = str(item.get("group_name")).strip()[:80] if item.get("group_name") else None

        reasons: list[str] = []
        raw_reasons = item.get("uncertainty_reasons")
        if isinstance(raw_reasons, list):
            reasons.extend(str(r).strip() for r in raw_reasons if str(r).strip())
        if len(subject) < 2:
            reasons.append("Matière non identifiée avec certitude.")
        if day_idx is None:
            reasons.append("Jour de la semaine manquant ou ambigu.")
        if start_t is None or end_t is None:
            reasons.append("Horaire de début ou de fin illisible.")

        uncertain = bool(item.get("uncertain")) or len(reasons) > 0
        validated_rows.append(
            ExtractedCourseRowSchema(
                row_id=f"row_{idx}",
                subject=subject,
                day_of_week=day_idx,
                day_label=DAY_NAMES_FR.get(day_idx) if day_idx is not None else None,
                start_time=start_t,
                end_time=end_t,
                teacher=teacher,
                room=room,
                group_name=group_name,
                session_type=session_t,
                valid_from=ai_valid_from,
                valid_until=ai_valid_until,
                uncertain=uncertain,
                uncertainty_reasons=reasons,
                ignored=False,
                raw_excerpt="Extrait par analyse IA",
            )
        )

    return validated_rows, ai_valid_from, ai_valid_until


def extract_timetable_from_bytes(
    *,
    filename: str,
    content_type: str | None,
    content: bytes,
    max_bytes: int,
    ai_config: dict[str, Any] | None = None,
) -> ExtractedTimetableResult:
    """Point d'entrée principal d'extraction multi-format (PDF, Image, Excel, Word) enrichi par l'IA."""
    file_format, normalized_mime, file_sha256 = validate_and_classify_file(
        filename=filename,
        content_type=content_type,
        content=content,
        max_bytes=max_bytes,
    )

    if file_format == TimetableFileFormat.pdf:
        preview_text, courses, warnings = _extract_from_pdf(content)
    elif file_format == TimetableFileFormat.word:
        preview_text, courses, warnings = _extract_from_docx(content)
    elif file_format == TimetableFileFormat.excel:
        preview_text, courses, warnings = _extract_from_excel(content, filename)
    else:
        preview_text, courses, warnings = _extract_from_image(content)

    # Si l'extraction déterministe n'a trouvé aucun cours ou contient des lignes incertaines,
    # sollicite le fournisseur IA configuré (River AI / OpenAI / Gemini) pour analyser le document.
    if ai_config and (not courses or any(c.uncertain for c in courses)):
        ai_courses, ai_valid_from, ai_valid_until = _try_extract_courses_with_ai(
            file_format=file_format,
            mime_type=normalized_mime,
            content=content,
            preview_text=preview_text,
            ai_config=ai_config,
        )
        if ai_courses:
            courses = ai_courses
            warnings = [
                w
                for w in warnings
                if "aucun texte OCR lisible" not in w and "Aucun créneau horaire" not in w
            ]
            if ai_valid_from and not preview_text.startswith("[Aperçu image"):
                preview_text = f"{preview_text}\nValidité: {ai_valid_from} - {ai_valid_until or ''}".strip()

    valid_from, valid_until = _extract_validity_dates(preview_text)
    for row in courses:
        if row.valid_from is None and valid_from is not None:
            row.valid_from = valid_from
        if row.valid_until is None and valid_until is not None:
            row.valid_until = valid_until
        if valid_from is None and row.valid_from is not None:
            valid_from = row.valid_from
        if valid_until is None and row.valid_until is not None:
            valid_until = row.valid_until

    return ExtractedTimetableResult(
        file_format=file_format,
        mime_type=normalized_mime,
        file_sha256=file_sha256,
        preview_text=preview_text,
        courses=courses,
        valid_from=valid_from,
        valid_until=valid_until,
        warnings=warnings,
    )


def _time_str_to_minutes(t_str: str | None) -> int | None:
    if not t_str or not re.match(r"^\d{2}:\d{2}$", t_str):
        return None
    parts = t_str.split(":")
    h, m = int(parts[0]), int(parts[1])
    if 0 <= h <= 23 and 0 <= m <= 59:
        return h * 60 + m
    return None


def detect_timetable_anomalies(
    courses: list[ExtractedCourseRowSchema],
    *,
    existing_events: list[ScheduleEventRecord] | None = None,
    target_week_monday: date | None = None,
    tz_name: str = "Africa/Dakar",
) -> list[TimetableAnomalySchema]:
    """
    Analyse les lignes non ignorées pour détecter :
    - Horaires manquants ou jour manquant (`missing_time`)
    - Durée invalide (`invalid_duration`)
    - Matière non identifiée (`missing_subject`)
    - Doublons possibles (`duplicate_course`)
    - Chevauchements entre cours de l'import (`overlap_conflict`)
    - Chevauchements avec les créneaux existants du calendrier (`existing_calendar_conflict`)
    - Extractions incertaines (`uncertain_extraction`)
    """
    anomalies: list[TimetableAnomalySchema] = []
    active_rows = [row for row in courses if not row.ignored]
    counter = 1

    def _add(
        a_type: TimetableAnomalyType,
        severity: str,
        message: str,
        row_id: str | None = None,
        related_row_id: str | None = None,
    ) -> None:
        nonlocal counter
        anomalies.append(
            TimetableAnomalySchema(
                id=f"anom_{counter}",
                row_id=row_id,
                related_row_id=related_row_id,
                type=a_type,
                severity=severity,
                message=message,
            )
        )
        counter += 1

    valid_timed_rows: list[tuple[ExtractedCourseRowSchema, int, int]] = []

    for row in active_rows:
        label = row.subject.strip() or f"Ligne {row.row_id}"
        if not row.subject.strip() or len(row.subject.strip()) < 2:
            _add(
                TimetableAnomalyType.missing_subject,
                "error",
                f"Matière non identifiée sur la ligne ({row.raw_excerpt or row.row_id}).",
                row_id=row.row_id,
            )

        start_min = _time_str_to_minutes(row.start_time)
        end_min = _time_str_to_minutes(row.end_time)

        if row.day_of_week is None or row.day_of_week < 0 or row.day_of_week > 6:
            _add(
                TimetableAnomalyType.missing_time,
                "error",
                f"Jour de la semaine manquant ou illisible pour « {label} ».",
                row_id=row.row_id,
            )

        if start_min is None or end_min is None:
            _add(
                TimetableAnomalyType.missing_time,
                "error",
                f"Horaire de début ou de fin manquant/illisible pour « {label} ».",
                row_id=row.row_id,
            )
        elif end_min <= start_min:
            _add(
                TimetableAnomalyType.invalid_duration,
                "error",
                f"Durée invalide pour « {label} » ({row.start_time} – {row.end_time}) : la fin doit être postérieure au début.",
                row_id=row.row_id,
            )
        elif (end_min - start_min) < 15 or (end_min - start_min) > 600:
            _add(
                TimetableAnomalyType.invalid_duration,
                "error",
                f"Durée atypique ou invalide pour « {label} » ({end_min - start_min} min).",
                row_id=row.row_id,
            )
        elif row.day_of_week is not None and 0 <= row.day_of_week <= 6:
            valid_timed_rows.append((row, start_min, end_min))

        if row.uncertain and start_min is not None and end_min is not None and row.subject.strip():
            reasons = " ".join(row.uncertainty_reasons) or "Extraction partiellement ambiguë."
            _add(
                TimetableAnomalyType.uncertain_extraction,
                "warning",
                f"Information à vérifier sur « {label} » : {reasons}",
                row_id=row.row_id,
            )

    # Détection des doublons et chevauchements internes
    for i in range(len(valid_timed_rows)):
        row_a, start_a, end_a = valid_timed_rows[i]
        day_a = row_a.day_of_week
        day_name = DAY_NAMES_FR.get(day_a or 0, "Jour")
        for j in range(i + 1, len(valid_timed_rows)):
            row_b, start_b, end_b = valid_timed_rows[j]
            if row_a.day_of_week != row_b.day_of_week:
                continue

            same_subject = (
                row_a.subject.strip().lower() == row_b.subject.strip().lower()
                and bool(row_a.subject.strip())
            )
            if same_subject and start_a == start_b and end_a == end_b:
                _add(
                    TimetableAnomalyType.duplicate_course,
                    "warning",
                    f"Doublon possible détecté le {day_name} ({row_a.start_time}–{row_a.end_time}) pour « {row_a.subject} ».",
                    row_id=row_b.row_id,
                    related_row_id=row_a.row_id,
                )
            elif start_a < end_b and start_b < end_a:
                _add(
                    TimetableAnomalyType.overlap_conflict,
                    "warning",
                    f"Chevauchement horaire le {day_name} entre « {row_a.subject or row_a.row_id} » ({row_a.start_time}–{row_a.end_time}) et « {row_b.subject or row_b.row_id} » ({row_b.start_time}–{row_b.end_time}).",
                    row_id=row_b.row_id,
                    related_row_id=row_a.row_id,
                )

    # Détection des conflits avec les créneaux déjà présents dans le calendrier sur la semaine cible
    if existing_events and target_week_monday is not None:
        tz = ZoneInfo(tz_name)
        for row, start_min, end_min in valid_timed_rows:
            assert row.day_of_week is not None
            course_date = target_week_monday + timedelta(days=row.day_of_week)
            c_start_local = datetime.combine(
                course_date,
                time(start_min // 60, start_min % 60),
                tzinfo=tz,
            )
            c_end_local = datetime.combine(
                course_date,
                time(end_min // 60, end_min % 60),
                tzinfo=tz,
            )
            c_start_utc = c_start_local.astimezone(timezone.utc)
            c_end_utc = c_end_local.astimezone(timezone.utc)

            for ev in existing_events:
                if c_start_utc < ev.ends_at and ev.starts_at < c_end_utc:
                    # Si c'est exactement le même cours au même horaire, sera traité comme doublon ignoré
                    if (
                        ev.title.strip().lower().endswith(row.subject.strip().lower())
                        and ev.starts_at == c_start_utc
                        and ev.ends_at == c_end_utc
                    ):
                        continue
                    _add(
                        TimetableAnomalyType.existing_calendar_conflict,
                        "warning",
                        f"Chevauchement avec le créneau existant « {ev.title} » le {DAY_NAMES_FR.get(row.day_of_week, '')}.",
                        row_id=row.row_id,
                    )
                    break

    return anomalies
