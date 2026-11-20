from datetime import datetime, time, timedelta, timezone
import io
from uuid import UUID
from zoneinfo import ZoneInfo

import docx
from fastapi.testclient import TestClient
import openpyxl
from PIL import Image, PngImagePlugin


def _build_pdf_with_text(lines: list[str]) -> bytes:
    """Construit un vrai document PDF 1.4 lisible par pypdf contenant les lignes fournies."""

    def _escape_pdf_text(val: str) -> str:
        # Conversion ASCII/WinAnsi pour opérateur TJ/Tj PDF standard
        replacements = {
            "é": "e",
            "è": "e",
            "ê": "e",
            "à": "a",
            "â": "a",
            "ù": "u",
            "ô": "o",
            "î": "i",
            "ç": "c",
            "–": "-",
            "—": "-",
            "’": "'",
        }
        out = val
        for k, v in replacements.items():
            out = out.replace(k, v)
        out = out.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return out

    stream_lines = ["BT", "/F1 11 Tf", "50 760 Td", "16 TL"]
    for idx, line in enumerate(lines):
        esc = _escape_pdf_text(line)
        if idx == 0:
            stream_lines.append(f"({esc}) Tj")
        else:
            stream_lines.append(f"T* ({esc}) Tj")
    stream_lines.append("ET")
    stream_bytes = "\n".join(stream_lines).encode("latin-1", errors="replace")

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets: list[int] = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(f"{i} 0 obj\n".encode("ascii"))
        buf.write(obj)
        buf.write(b"\nendobj\n")

    xref_pos = buf.tell()
    buf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode("ascii"))

    buf.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return buf.getvalue()


def _build_excel_xlsx_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Emploi du temps L3"
    ws.append(["Jour", "Début", "Fin", "Matière", "Type", "Enseignant", "Salle", "Groupe"])
    ws.append(["Lundi", "08:00", "10:00", "Algorithmique Avancée", "Cours", "Pr. Diallo", "Amphi A", "L3 Info"])
    # Cellule fusionnée verticalement sur le Jour (Lundi) pour un TD l'après-midi
    ws.append(["", "14:00", "16:00", "Algorithmique Avancée", "TD", "M. Ndiaye", "Salle 204", "G2"])
    ws.merge_cells("A2:A3")
    ws.append(["Mercredi", "10:00", "12:00", "Bases de Données PostgreSQL", "TP", "Dr. Sow", "Labo Info 1", "G2"])

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _build_word_docx_bytes() -> bytes:
    doc = docx.Document()
    doc.add_paragraph("Emploi du temps Semestre 1 — Validité du 2026-11-16 au 2026-12-20")
    table = doc.add_table(rows=1, cols=6)
    hdr = table.rows[0].cells
    hdr[0].text = "Jour"
    hdr[1].text = "Horaire"
    hdr[2].text = "Matière"
    hdr[3].text = "Type"
    hdr[4].text = "Enseignant"
    hdr[5].text = "Salle"

    row1 = table.add_row().cells
    row1[0].text = "Mardi"
    row1[1].text = "09:00 - 11:00"
    row1[2].text = "Réseaux & Protocoles TCP/IP"
    row1[3].text = "Cours"
    row1[4].text = "Pr. Fall"
    row1[5].text = "Amphi B"

    row2 = table.add_row().cells
    row2[0].text = "Jeudi"
    row2[1].text = "15:00 - 17:00"
    row2[2].text = "Architecture Logicielle"
    row2[3].text = "TD"
    row2[4].text = "Mme Ba"
    row2[5].text = "Salle 105"

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _build_png_image_bytes(embedded_ocr_text: str) -> bytes:
    img = Image.new("RGB", (640, 360), color=(248, 250, 252))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Description", embedded_ocr_text)
    out = io.BytesIO()
    img.save(out, format="PNG", pnginfo=meta)
    return out.getvalue()


def test_import_formats_pdf_image_excel_word_and_security_validation(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Couvre les scénarios 1, 2, 3, 4 et la validation de sécurité des fichiers :
    1. Import d'un PDF correctement structuré.
    2. Import d'une image (.png).
    3. Import d'un fichier Excel (.xlsx avec cellules fusionnées).
    4. Import d'un document Word (.docx avec tableau et dates de validité).
    """
    # 0. Rejet d'un format non supporté (.exe) et d'un faux PDF
    bad_ext = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("malware.exe", b"MZ\x90\x00\x03", "application/octet-stream")},
        headers=user_a_headers,
    )
    assert bad_ext.status_code == 422
    assert bad_ext.json()["error"]["code"] == "UNSUPPORTED_TIMETABLE_FORMAT"

    fake_pdf = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("faux.pdf", b"Ceci n est pas un PDF", "application/pdf")},
        headers=user_a_headers,
    )
    assert fake_pdf.status_code == 422
    assert fake_pdf.json()["error"]["code"] == "INVALID_TIMETABLE_FILE_CONTENT"

    # 1. Import d'un PDF structuré
    pdf_bytes = _build_pdf_with_text(
        [
            "Emploi du temps Master 1 - Valide du 2026-11-16 au 2026-12-18",
            "Lundi 08:30 - 10:30 Programmation Java - CM - Pr. Diop - Amphi C - Groupe M1",
            "Mardi 14:00 - 16:00 Systeme Linux - TP - Dr. Faye - Labo 2 - Groupe M1",
        ]
    )
    pdf_res = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("edt_semestre1.pdf", pdf_bytes, "application/pdf")},
        headers=user_a_headers,
    )
    assert pdf_res.status_code == 201
    pdf_data = pdf_res.json()
    assert pdf_data["file_format"] == "pdf"
    assert pdf_data["status"] == "pending_review"
    assert pdf_data["valid_from"] == "2026-11-16"
    assert pdf_data["valid_until"] == "2026-12-18"
    assert len(pdf_data["extracted_courses"]) == 2
    assert pdf_data["extracted_courses"][0]["subject"] == "Programmation Java"
    assert pdf_data["extracted_courses"][0]["day_of_week"] == 0
    assert pdf_data["extracted_courses"][0]["start_time"] == "08:30"
    assert pdf_data["extracted_courses"][0]["end_time"] == "10:30"
    assert pdf_data["extracted_courses"][0]["teacher"] == "Pr. Diop"
    assert pdf_data["extracted_courses"][0]["room"] == "Amphi C"
    assert pdf_data["extracted_courses"][1]["session_type"] == "tp"

    # Vérifier qu'AUCUN cours n'est enregistré dans le calendrier avant validation explicite
    assert client.get("/api/v1/schedule", headers=user_a_headers).json() == []

    # 2. Import d'une image PNG
    png_bytes = _build_png_image_bytes(
        "Vendredi 09:00 - 11:00 Intelligence Artificielle | Cours | Pr. Sy | Salle 301 | Groupe L3"
    )
    img_res = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("capture_edt.png", png_bytes, "image/png")},
        headers=user_a_headers,
    )
    assert img_res.status_code == 201
    img_data = img_res.json()
    assert img_data["file_format"] == "image"
    assert len(img_data["extracted_courses"]) == 1
    assert img_data["extracted_courses"][0]["subject"] == "Intelligence Artificielle"
    assert img_data["extracted_courses"][0]["day_of_week"] == 4
    assert img_data["extracted_courses"][0]["start_time"] == "09:00"
    assert img_data["extracted_courses"][0]["end_time"] == "11:00"
    assert img_data["extracted_courses"][0]["room"] == "Salle 301"

    # 3. Import d'un fichier Excel (.xlsx avec cellules fusionnées)
    xlsx_bytes = _build_excel_xlsx_bytes()
    xls_res = client.post(
        "/api/v1/schedule/imports/analyze",
        files={
            "file": (
                "edt_l3.xlsx",
                xlsx_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=user_a_headers,
    )
    assert xls_res.status_code == 201
    xls_data = xls_res.json()
    assert xls_data["file_format"] == "excel"
    assert len(xls_data["extracted_courses"]) == 3
    # La 2e ligne a hérité de "Lundi" (day_of_week == 0) grâce à la résolution des cellules fusionnées A2:A3
    assert xls_data["extracted_courses"][1]["day_of_week"] == 0
    assert xls_data["extracted_courses"][1]["session_type"] == "td"
    assert xls_data["extracted_courses"][1]["room"] == "Salle 204"

    # 4. Import d'un document Word (.docx)
    docx_bytes = _build_word_docx_bytes()
    doc_res = client.post(
        "/api/v1/schedule/imports/analyze",
        files={
            "file": (
                "edt_word.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers=user_a_headers,
    )
    assert doc_res.status_code == 201
    doc_data = doc_res.json()
    assert doc_data["file_format"] == "word"
    assert doc_data["valid_from"] == "2026-11-16"
    assert doc_data["valid_until"] == "2026-12-20"
    assert len(doc_data["extracted_courses"]) == 2
    assert doc_data["extracted_courses"][0]["subject"] == "Réseaux & Protocoles TCP/IP"
    assert doc_data["extracted_courses"][1]["session_type"] == "td"


def test_unreadable_times_overlap_detection_manual_correction_and_cancellation(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """
    Couvre les scénarios 5, 6, 7 et 8 :
    5. Document contenant des horaires illisibles (ne jamais inventer un horaire).
    6. Détection d'un chevauchement entre deux cours.
    7. Correction manuelle d'un horaire avant validation.
    8. Annulation de l'import (aucun cours enregistré).
    """
    pdf_with_anomalies = _build_pdf_with_text(
        [
            "Lundi 08:00 - 10:30 Mathematiques Discretes - CM - Pr. Kane - Amphi 1",
            "Lundi 09:30 - 11:30 Physique Quantique - TD - Dr. Gueye - Salle 12",
            "Mardi ??:?? - 16:00 Compilation & Langages - TP - Salle 202",
        ]
    )
    res = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("edt_anomalies.pdf", pdf_with_anomalies, "application/pdf")},
        headers=user_a_headers,
    )
    assert res.status_code == 201
    import_data = res.json()
    import_id = import_data["id"]

    # Scénario 5 : L'horaire illisible ??:?? n'a PAS été inventé -> start_time est None et uncertain est True
    row_mardi = import_data["extracted_courses"][2]
    assert row_mardi["start_time"] is None
    assert row_mardi["end_time"] == "16:00"
    assert row_mardi["uncertain"] is True

    # Scénario 6 : Détection d'un chevauchement sur Lundi (08:00-10:30 et 09:30-11:30) + horaire manquant sur Mardi
    anomaly_types = {a["type"] for a in import_data["anomalies"]}
    assert "missing_time" in anomaly_types
    assert "overlap_conflict" in anomaly_types
    assert import_data["blocking_anomalies_count"] >= 1

    # Tentative de validation directe alors qu'un horaire est manquant -> refus 422 TIMETABLE_VALIDATION_FAILED
    premature_confirm = client.post(
        f"/api/v1/schedule/imports/{import_id}/confirm",
        json={},
        headers=user_a_headers,
    )
    assert premature_confirm.status_code == 422
    assert premature_confirm.json()["error"]["code"] == "TIMETABLE_VALIDATION_FAILED"

    # Scénario 7 : Correction manuelle de l'horaire illisible et du chevauchement
    corrected_courses = import_data["extracted_courses"]
    # Décale Physique Quantique à 10:30 - 12:30 (plus de chevauchement)
    corrected_courses[1]["start_time"] = "10:30"
    corrected_courses[1]["end_time"] = "12:30"
    # Corrige l'horaire de Mardi à 14:00 - 16:00
    corrected_courses[2]["start_time"] = "14:00"
    corrected_courses[2]["end_time"] = "16:00"

    patch_res = client.patch(
        f"/api/v1/schedule/imports/{import_id}",
        json={
            "courses": corrected_courses,
            "valid_from": "2026-11-16",
            "valid_until": "2026-11-22",
        },
        headers=user_a_headers,
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert patched_data["blocking_anomalies_count"] == 0
    assert patched_data["anomalies"] == []

    # Scénario 8 : Annulation de l'import
    cancel_res = client.post(
        f"/api/v1/schedule/imports/{import_id}/cancel",
        headers=user_a_headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Un import annulé ne peut plus être confirmé et le calendrier reste vide
    confirm_after_cancel = client.post(
        f"/api/v1/schedule/imports/{import_id}/confirm",
        json={},
        headers=user_a_headers,
    )
    assert confirm_after_cancel.status_code == 409
    assert client.get("/api/v1/schedule", headers=user_a_headers).json() == []


def test_confirm_import_deduplication_user_isolation_and_ai_copilot_conflict_avoidance(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    """
    Couvre les scénarios 9, 10, 11, 12 et 13 :
    9. Validation et enregistrement dans le calendrier.
    10. Nouvelle importation sans doublons (et suppression possible du document source).
    11. Isolation stricte des données entre utilisateurs.
    12. Accès des horaires validés au Context Builder et au Copilote IA.
    13. Génération d'un programme quotidien sans conflit avec les cours (ex. Cours de Java 18h-21h).
    """
    tz = ZoneInfo("Africa/Dakar")
    local_today = datetime.now(timezone.utc).astimezone(tz).date()
    today_weekday = local_today.weekday()
    monday_this_week = local_today - timedelta(days=today_weekday)
    today_day_name = [
        "Lundi",
        "Mardi",
        "Mercredi",
        "Jeudi",
        "Vendredi",
        "Samedi",
        "Dimanche",
    ][today_weekday]

    # L'utilisateur a cours de Programmation Java aujourd'hui de 18:00 à 21:00
    pdf_bytes = _build_pdf_with_text(
        [
            f"{today_day_name} 18:00 - 21:00 Programmation Java - Cours - Pr. Diallo - Amphi A - L3 Info",
        ]
    )
    analyze_res = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("edt_java.pdf", pdf_bytes, "application/pdf")},
        headers=user_a_headers,
    )
    assert analyze_res.status_code == 201
    import_id = analyze_res.json()["id"]

    # Scénario 11 : Isolation stricte — User B ne peut ni lire, ni modifier, ni valider l'import de User A
    assert (
        client.get(f"/api/v1/schedule/imports/{import_id}", headers=user_b_headers).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/schedule/imports/{import_id}/confirm",
            json={},
            headers=user_b_headers,
        ).status_code
        == 404
    )

    # Scénario 9 : Validation et enregistrement par User A sur la semaine courante
    confirm_res = client.post(
        f"/api/v1/schedule/imports/{import_id}/confirm",
        json={
            "target_week_start": monday_this_week.isoformat(),
            "recurrence_weeks": 1,
        },
        headers=user_a_headers,
    )
    assert confirm_res.status_code == 201
    confirm_data = confirm_res.json()
    assert confirm_data["created_count"] == 1
    assert confirm_data["skipped_duplicates_count"] == 0
    assert confirm_data["import_record"]["status"] == "validated"

    created_event = confirm_data["created_events"][0]
    assert created_event["title"] == "Programmation Java"
    assert created_event["type"] == "course"
    assert created_event["source"] == "timetable_import"
    assert created_event["teacher"] == "Pr. Diallo"
    assert created_event["room"] == "Amphi A"
    assert created_event["group_name"] == "L3 Info"

    # Suppression du document source (Section 9) tout en conservant le cours dans le calendrier
    del_src = client.delete(
        f"/api/v1/schedule/imports/{import_id}/source",
        headers=user_a_headers,
    )
    assert del_src.status_code == 200
    assert del_src.json()["source_deleted"] is True
    assert del_src.json()["source_preview_text"] is None

    # Scénario 10 : Nouvelle importation du même fichier -> 0 doublon créé, 1 doublon ignoré
    re_analyze = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("edt_java_copie.pdf", pdf_bytes, "application/pdf")},
        headers=user_a_headers,
    )
    assert re_analyze.status_code == 201
    re_confirm = client.post(
        f"/api/v1/schedule/imports/{re_analyze.json()['id']}/confirm",
        json={
            "target_week_start": monday_this_week.isoformat(),
            "recurrence_weeks": 1,
        },
        headers=user_a_headers,
    )
    assert re_confirm.status_code == 201
    assert re_confirm.json()["created_count"] == 0
    assert re_confirm.json()["skipped_duplicates_count"] == 1

    # Vérifier que User A a toujours 1 seul cours et User B n'en a aucun
    assert len(client.get("/api/v1/schedule", headers=user_a_headers).json()) == 1
    assert client.get("/api/v1/schedule", headers=user_b_headers).json() == []

    # Scénarios 12 & 13 : Connexion au Copilote IA & Planification sans conflit avec le cours de Java (18h-21h)
    conv_res = client.post(
        "/api/v1/ai/conversations",
        json={"title": "Planification autour des cours"},
        headers=user_a_headers,
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    msg_res = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Organise mon programme et planifie un créneau de révision aujourd'hui."},
        headers=user_a_headers,
    )
    assert msg_res.status_code == 201
    turn_data = msg_res.json()
    reply_text = turn_data["assistant_message"]["content"]

    # Le Copilote connaît le cours de Programmation Java (18:00–21:00)
    assert "Programmation Java" in reply_text
    assert "18:00" in reply_text and "21:00" in reply_text

    # La proposition de créneau générée par l'IA ne chevauche JAMAIS 18:00 - 21:00
    assert len(turn_data["proposals"]) == 1
    proposal = turn_data["proposals"][0]
    assert proposal["action_type"] == "create_schedule_event"
    prop_start = datetime.fromisoformat(proposal["payload"]["starts_at"])
    prop_end = datetime.fromisoformat(proposal["payload"]["ends_at"])

    java_start = datetime.combine(local_today, time(18, 0), tzinfo=tz).astimezone(timezone.utc)
    java_end = datetime.combine(local_today, time(21, 0), tzinfo=tz).astimezone(timezone.utc)
    assert not (prop_start < java_end and java_start < prop_end)
    assert proposal["payload"]["has_conflict"] is False

    # Et si quelqu'un tente de forcer l'acceptation de la proposition avec payload_overrides sur 18:30-20:00 (pendant le cours de Java),
    # ActionValidator la rejette avec 409 UNIVERSITY_COURSE_CONFLICT !
    forced_conflict_start = (
        datetime.combine(local_today, time(18, 30), tzinfo=tz).astimezone(timezone.utc).isoformat()
    )
    forced_conflict_end = (
        datetime.combine(local_today, time(20, 0), tzinfo=tz).astimezone(timezone.utc).isoformat()
    )
    conflict_accept = client.post(
        f"/api/v1/ai/proposals/{proposal['id']}/accept",
        json={
            "payload_overrides": {
                "starts_at": forced_conflict_start,
                "ends_at": forced_conflict_end,
            }
        },
        headers=user_a_headers,
    )
    assert conflict_accept.status_code == 409
    assert conflict_accept.json()["error"]["code"] == "UNIVERSITY_COURSE_CONFLICT"
