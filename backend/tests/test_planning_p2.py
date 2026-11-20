from datetime import datetime, timedelta, timezone
import io
import shutil
import subprocess
from types import SimpleNamespace

from fastapi.testclient import TestClient
import openpyxl
from PIL import Image, PngImagePlugin
from pypdf import PdfWriter
import pytest

from app.services.timetable_extractor import extract_timetable_from_bytes
from tests.test_timetable_import import _build_pdf_with_text


def test_timetable_replace_scoped_preview_and_restore(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    today = datetime.now(timezone.utc).date()
    monday_w1 = today - timedelta(days=today.weekday())
    monday_w2 = monday_w1 + timedelta(days=7)

    # 1. Créer un créneau manuel en W1 (ne doit jamais être supprimé par replace_existing_imported)
    manual_ev = client.post(
        "/api/v1/schedule",
        json={
            "title": "Révision personnelle manuelle",
            "type": "learning",
            "starts_at": f"{monday_w1.isoformat()}T14:00:00Z",
            "ends_at": f"{monday_w1.isoformat()}T15:00:00Z",
        },
        headers=user_a_headers,
    )
    assert manual_ev.status_code == 201
    manual_id = manual_ev.json()["id"]

    # 2. Importer un premier EDT sur W1
    pdf_w1_old = _build_pdf_with_text(["Lundi 08:00 - 10:00 Ancien Cours W1 - Cours - S101"])
    a1 = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("edt_w1_old.pdf", pdf_w1_old, "application/pdf")},
        headers=user_a_headers,
    )
    assert a1.status_code == 201
    c1 = client.post(
        f"/api/v1/schedule/imports/{a1.json()['id']}/confirm",
        json={"target_week_start": monday_w1.isoformat(), "recurrence_weeks": 1},
        headers=user_a_headers,
    )
    assert c1.status_code == 201
    old_w1_id = c1.json()["created_events"][0]["id"]

    # 3. Importer un EDT sur W2 (hors période de W1 -> doit rester intact lors du remplacement de W1)
    pdf_w2 = _build_pdf_with_text(["Lundi 08:00 - 10:00 Cours Semaine 2 - Cours - S202"])
    a2 = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("edt_w2.pdf", pdf_w2, "application/pdf")},
        headers=user_a_headers,
    )
    assert a2.status_code == 201
    c2 = client.post(
        f"/api/v1/schedule/imports/{a2.json()['id']}/confirm",
        json={"target_week_start": monday_w2.isoformat(), "recurrence_weeks": 1},
        headers=user_a_headers,
    )
    assert c2.status_code == 201
    w2_id = c2.json()["created_events"][0]["id"]

    # 4. Analyser un nouvel EDT pour W1 et prévisualiser le remplacement ciblé
    pdf_w1_new = _build_pdf_with_text(["Lundi 10:00 - 12:00 Nouveau Cours W1 - Cours - S105"])
    a3 = client.post(
        "/api/v1/schedule/imports/analyze",
        files={"file": ("edt_w1_new.pdf", pdf_w1_new, "application/pdf")},
        headers=user_a_headers,
    )
    assert a3.status_code == 201
    new_import_id = a3.json()["id"]

    preview = client.get(
        f"/api/v1/schedule/imports/{new_import_id}/replace-preview",
        params={"target_week_start": monday_w1.isoformat(), "recurrence_weeks": 1},
        headers=user_a_headers,
    )
    assert preview.status_code == 200
    assert preview.json()["affected_count"] == 1
    assert preview.json()["affected_events"][0]["id"] == old_w1_id

    # 5. Confirmer avec replace_existing_imported=True
    confirm_replace = client.post(
        f"/api/v1/schedule/imports/{new_import_id}/confirm",
        json={
            "target_week_start": monday_w1.isoformat(),
            "recurrence_weeks": 1,
            "replace_existing_imported": True,
        },
        headers=user_a_headers,
    )
    assert confirm_replace.status_code == 201
    assert confirm_replace.json()["replaced_count"] == 1
    assert confirm_replace.json()["created_count"] == 1
    new_w1_id = confirm_replace.json()["created_events"][0]["id"]

    events_after_replace = {
        ev["id"] for ev in client.get("/api/v1/schedule", headers=user_a_headers).json()
    }
    assert manual_id in events_after_replace
    assert w2_id in events_after_replace
    assert new_w1_id in events_after_replace
    assert old_w1_id not in events_after_replace

    # 6. Restaurer l'ancien emploi du temps depuis le snapshot
    restore = client.post(
        f"/api/v1/schedule/imports/{new_import_id}/restore",
        headers=user_a_headers,
    )
    assert restore.status_code == 200
    assert restore.json()["removed_events_count"] == 1
    assert restore.json()["restored_events_count"] == 1

    events_after_restore = {
        ev["id"]: ev["title"]
        for ev in client.get("/api/v1/schedule", headers=user_a_headers).json()
    }
    assert manual_id in events_after_restore
    assert w2_id in events_after_restore
    assert old_w1_id in events_after_restore
    assert new_w1_id not in events_after_restore

    # Seconde restauration impossible (snapshot consommé)
    restore_again = client.post(
        f"/api/v1/schedule/imports/{new_import_id}/restore",
        headers=user_a_headers,
    )
    assert restore_again.status_code == 409
    assert restore_again.json()["error"]["code"] == "NO_SNAPSHOT_TO_RESTORE"


def test_excel_merged_cells_and_serial_float_time_extraction() -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["Jour", "Début", "Fin", "Matière", "Salle"])
    ws.append(["Lundi", 0.375, 0.4583333333333333, "Algorithmique avancée", "Amphi B"])
    ws.append([None, 0.5833333333333334, 0.6666666666666666, "Bases de Données", "Salle 12"])
    ws.merge_cells("A2:A3")

    buf = io.BytesIO()
    wb.save(buf)

    result = extract_timetable_from_bytes(
        filename="planning_fusion.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=buf.getvalue(),
        max_bytes=10 * 1024 * 1024,
    )
    assert len(result.courses) == 2
    assert result.courses[0].day_of_week == 0
    assert result.courses[0].start_time == "09:00"
    assert result.courses[0].end_time == "11:00"
    assert "Algorithmique" in result.courses[0].subject
    assert result.courses[1].day_of_week == 0
    assert result.courses[1].start_time == "14:00"
    assert result.courses[1].end_time == "16:00"
    assert "Bases de Données" in result.courses[1].subject


def test_image_technical_metadata_does_not_skip_ocr_and_scanned_pdf_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    img = Image.new("RGB", (240, 80), color=(255, 255, 255))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Software", "CanvasExport 2.0")
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(300, 300), pnginfo=meta)

    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/tesseract" if cmd == "tesseract" else None)

    def _fake_run(*_args, **_kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="Mardi 09:00 - 11:00 Analyse Mathématique - Cours - Amphi 1\n",
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)

    img_result = extract_timetable_from_bytes(
        filename="edt_dpi.png",
        content_type="image/png",
        content=buf.getvalue(),
        max_bytes=10 * 1024 * 1024,
    )
    assert len(img_result.courses) == 1
    assert img_result.courses[0].day_of_week == 1
    assert img_result.courses[0].start_time == "09:00"
    assert img_result.courses[0].end_time == "11:00"
    assert "Analyse" in img_result.courses[0].subject

    # PDF scanné sans couche texte et sans tesseract -> aucun cours inventé + diagnostic honnête
    monkeypatch.setattr(shutil, "which", lambda _cmd: None)
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    pdf_buf = io.BytesIO()
    writer.write(pdf_buf)

    scanned_result = extract_timetable_from_bytes(
        filename="scan_vide.pdf",
        content_type="application/pdf",
        content=pdf_buf.getvalue(),
        max_bytes=10 * 1024 * 1024,
    )
    assert scanned_result.courses == []
    assert scanned_result.warnings
    assert "scanné" in scanned_result.warnings[0].lower()


def test_duplicate_week_target_and_normalized_dedup(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    # Semaine 1 (lundi 2026-11-16)
    ev1 = client.post(
        "/api/v1/schedule",
        json={
            "title": "Algèbre linéaire",
            "type": "course",
            "starts_at": "2026-11-16T08:00:00Z",
            "ends_at": "2026-11-16T10:00:00Z",
        },
        headers=user_a_headers,
    )
    assert ev1.status_code == 201

    # En semaine 3 (lundi 2026-11-30), un créneau équivalent [Cours] déjà présent
    ev_w3 = client.post(
        "/api/v1/schedule",
        json={
            "title": "[Cours] Algèbre linéaire",
            "type": "course",
            "starts_at": "2026-11-30T08:00:00Z",
            "ends_at": "2026-11-30T10:00:00Z",
        },
        headers=user_a_headers,
    )
    assert ev_w3.status_code == 201

    dup_w3 = client.post(
        "/api/v1/schedule/duplicate-week",
        json={"source_week_start": "2026-11-16", "target_week_start": "2026-11-30"},
        headers=user_a_headers,
    )
    assert dup_w3.status_code == 201
    assert dup_w3.json()["created_count"] == 0
    assert dup_w3.json()["skipped_count"] == 1

    # Duplication vers la semaine 4 (2026-12-07) -> crée bien le créneau
    dup_w4 = client.post(
        "/api/v1/schedule/duplicate-week",
        json={"source_week_start": "2026-11-16", "target_week_start": "2026-12-07"},
        headers=user_a_headers,
    )
    assert dup_w4.status_code == 201
    assert dup_w4.json()["created_count"] == 1
    assert dup_w4.json()["created"][0]["starts_at"].startswith("2026-12-07T08:00:00")
