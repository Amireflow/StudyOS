from __future__ import annotations

from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.schemas.common import CourseLanguage, CourseSubmissionKind
from app.services import course_curricula, course_generator
from app.services.github_inspector import GitHubInspectionResult


def test_curated_resources_have_no_unverified_youtube_watch_links() -> None:
    for topic, entries in course_curricula.CURATED_RESOURCES.items():
        for entry in entries:
            assert "youtube.com/watch?v=" not in entry["url"], (
                f"URL YouTube personnelle non vérifiée détectée dans {topic}: {entry['url']}"
            )
    for entry in course_curricula.FALLBACK_RESOURCES:
        assert "youtube.com/watch?v=" not in entry["url"]


def test_specialized_tracks_cover_levels_1_to_5_and_split_js_ts() -> None:
    subjects = ["Python", "JavaScript", "TypeScript", "React", "SQL", "Rust", "Java"]
    for subj in subjects:
        levels_map = course_generator._select_levels_map(subj, 5, language_pref="fr")
        assert len(levels_map) == 5, f"{subj} doit couvrir 5 niveaux complets"
        titles = {levels_map[lvl]["title"] for lvl in range(1, 6)}
        assert len(titles) == 5, f"Les titres L1..L5 de {subj} doivent être distincts"
        for lvl in range(1, 6):
            lessons = levels_map[lvl]["lessons"]
            assert len(lessons) == 4
            for lesson in lessons:
                md = lesson["content_markdown"]
                assert "## 1. Objectif pédagogique" in md
                assert "### 2. Prérequis" in md
                assert "### 8. Contrôle de compréhension" in md
                for ex in lesson["exercises"]:
                    assert ex["exercise_type"] in {"closed_quiz", "code", "open_explanation"}

    js_levels = course_generator._select_levels_map("JavaScript", 5, language_pref="fr")
    ts_levels = course_generator._select_levels_map("TypeScript", 5, language_pref="fr")
    assert js_levels[1]["title"] != ts_levels[1]["title"]
    assert "JavaScript" in js_levels[1]["title"]
    assert "TypeScript" in ts_levels[1]["title"]
    assert any(l["exercises"][0]["exercise_type"] == "closed_quiz" or len(l["exercises"]) >= 2 for l in js_levels[1]["lessons"])


def test_expected_answer_not_leaked_and_closed_quiz_grading(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    preview = client.post(
        "/api/v1/courses/preview",
        json={"subject": "Python", "language": "fr", "total_levels": 3},
        headers=user_a_headers,
    )
    assert preview.status_code == 200
    for lesson in preview.json()["first_level_lessons"]:
        for ex in lesson["exercises"]:
            assert "expected_answer" not in ex

    course = client.post(
        "/api/v1/courses",
        json={"subject": "Python", "language": "fr", "total_levels": 3},
        headers=user_a_headers,
    ).json()
    lvl1 = course["levels"][0]
    quiz_pair = None
    for lesson in lvl1["lessons"]:
        for ex in lesson["exercises"]:
            assert "expected_answer" not in ex
            if ex.get("exercise_type") == "closed_quiz" and ex.get("choices"):
                quiz_pair = (lesson["id"], ex)

    assert quiz_pair is not None, "Le chapitre 4 doit contenir un quiz fermé de contrôle"
    lesson_id, quiz_ex = quiz_pair
    wrong_choice = next(c for c in quiz_ex["choices"] if "Ignorer" in c or "Dupliquer" in c)
    right_choice = next(c for c in quiz_ex["choices"] if c != wrong_choice and ("Valider" in c or "assert" in c.lower()))

    bad = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/submissions",
        json={
            "submission_kind": "exercise",
            "lesson_id": lesson_id,
            "exercise_id": quiz_ex["id"],
            "answer_text": wrong_choice,
        },
        headers=user_a_headers,
    )
    assert bad.status_code == 201
    assert bad.json()["passed"] is False
    assert bad.json()["evaluation_mode"] == "closed_quiz"
    assert bad.json()["attempt_number"] == 1

    good = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/submissions",
        json={
            "submission_kind": "exercise",
            "lesson_id": lesson_id,
            "exercise_id": quiz_ex["id"],
            "answer_text": right_choice,
        },
        headers=user_a_headers,
    )
    assert good.status_code == 201
    assert good.json()["passed"] is True
    assert good.json()["score"] == 100
    assert good.json()["attempt_number"] == 2
    assert good.json()["evaluation_mode"] == "closed_quiz"


def test_python_ast_rejects_broken_syntax_and_unchanged_starter_code(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    course = client.post(
        "/api/v1/courses",
        json={"subject": "Python", "language": "fr", "total_levels": 2},
        headers=user_a_headers,
    ).json()
    lvl1 = course["levels"][0]
    lesson = lvl1["lessons"][0]
    ex = lesson["exercises"][0]

    starter_only = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/submissions",
        json={
            "submission_kind": "exercise",
            "lesson_id": lesson["id"],
            "exercise_id": ex["id"],
            "answer_text": "J'ai relu l'énoncé et voici ma proposition avec starter code inchangé et tests.",
            "submitted_code": ex["starter_code"],
        },
        headers=user_a_headers,
    )
    assert starter_only.status_code == 201
    assert starter_only.json()["passed"] is False
    assert starter_only.json()["static_analysis"]["starter_unchanged"] is True

    broken_syntax = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/submissions",
        json={
            "submission_kind": "exercise",
            "lesson_id": lesson["id"],
            "exercise_id": ex["id"],
            "answer_text": "Voici ma fonction Python avec validation de borne et tests assert vérifiés.",
            "submitted_code": "def broken_fn(x:\n    return x + 1",
        },
        headers=user_a_headers,
    )
    assert broken_syntax.status_code == 201
    assert broken_syntax.json()["passed"] is False
    assert broken_syntax.json()["static_analysis"]["valid"] is False


def test_unreachable_github_url_marks_manual_review_and_blocks_validation(
    client: TestClient,
    user_a_headers: dict[str, str],
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        course_generator,
        "inspect_github_evidence",
        lambda url, **kw: GitHubInspectionResult(
            status="unreachable",
            verified=False,
            note="Dépôt privé ou inaccessible lors du contrôle.",
            metadata={"repo": "user/private"},
            inspected_at=datetime.now(timezone.utc),
        ),
    )

    course = client.post(
        "/api/v1/courses",
        json={"subject": "Python", "language": "fr", "total_levels": 2},
        headers=user_a_headers,
    ).json()
    lvl1 = course["levels"][0]
    for lesson in lvl1["lessons"]:
        client.patch(
            f"/api/v1/courses/{course['id']}/lessons/{lesson['id']}",
            json={"status": "completed"},
            headers=user_a_headers,
        )
    ex_lesson = lvl1["lessons"][0]
    client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/submissions",
        json={
            "submission_kind": "exercise",
            "lesson_id": ex_lesson["id"],
            "exercise_id": ex_lesson["exercises"][0]["id"],
            "answer_text": "Fonction complète avec garde et raise ValueError plus test assert nominal.",
            "submitted_code": (
                "def classify_score(score: int) -> str:\n"
                "    if score < 0 or score > 100:\n"
                "        raise ValueError('invalide')\n"
                "    return 'Acquis' if score >= 85 else 'En cours'\n"
                "assert classify_score(90) == 'Acquis'\n"
            ),
        },
        headers=user_a_headers,
    )

    url_only = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/submissions",
        json={
            "submission_kind": "project",
            "answer_text": "Tout mon code Python validé avec pytest et gestion d'erreurs se trouve sur ce dépôt GitHub.",
            "reference_url": "https://github.com/student/private-study-repo",
        },
        headers=user_a_headers,
    )
    assert url_only.status_code == 201
    data = url_only.json()
    assert data["manual_review_required"] is True
    assert data["passed"] is False
    assert data["evaluation_mode"] == "manual_review"

    val_res = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/validate",
        headers=user_a_headers,
    )
    assert val_res.status_code == 422
    assert val_res.json()["error"]["code"] == "PROJECT_VALIDATION_REQUIRED"


def test_regenerate_level_archives_previous_versions_and_blocks_locked_or_validated(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    course = client.post(
        "/api/v1/courses",
        json={"subject": "JavaScript", "language": "fr", "total_levels": 2},
        headers=user_a_headers,
    ).json()
    lvl1 = course["levels"][0]
    lvl2 = course["levels"][1]

    # Soumettre avant régénération pour vérifier que les soumissions passées restent conservées
    ex_lesson = lvl1["lessons"][0]
    sub = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/submissions",
        json={
            "submission_kind": "exercise",
            "lesson_id": ex_lesson["id"],
            "exercise_id": ex_lesson["exercises"][0]["id"],
            "answer_text": "Implémentation JavaScript avec throw Error sur entrée invalide et tests console.",
            "submitted_code": (
                "export function parseScore(raw) {\n"
                "  const n = Number(raw);\n"
                "  if (!Number.isFinite(n) || n < 0 || n > 100) throw new Error('Score invalide');\n"
                "  return n;\n"
                "}\n"
            ),
        },
        headers=user_a_headers,
    )
    assert sub.status_code == 201
    assert sub.json()["passed"] is True

    regen = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/regenerate",
        json={"focus_hint": "Insister sur la validation stricte des entrées"},
        headers=user_a_headers,
    )
    assert regen.status_code == 200
    detail = regen.json()
    updated_lvl1 = detail["levels"][0]
    assert updated_lvl1["revision"] == 2
    assert updated_lvl1["previous_versions_count"] == 1
    assert len(updated_lvl1["submissions"]) == 1

    # Niveau 2 verrouillé -> 409 LEVEL_LOCKED
    locked_regen = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl2['id']}/regenerate",
        json={},
        headers=user_a_headers,
    )
    assert locked_regen.status_code == 409
    assert locked_regen.json()["error"]["code"] == "LEVEL_LOCKED"

    # Valider niveau 1 puis tenter de le régénérer -> 409 LEVEL_ALREADY_VALIDATED
    for l in updated_lvl1["lessons"]:
        client.patch(
            f"/api/v1/courses/{course['id']}/lessons/{l['id']}",
            json={"status": "completed"},
            headers=user_a_headers,
        )
    client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/submissions",
        json={
            "submission_kind": "project",
            "answer_text": "Projet JavaScript complet avec modules ES, gestion d'erreurs explicite et jeu de tests.",
            "submitted_code": (
                "export function summarizeScores(rows) {\n"
                "  if (!Array.isArray(rows)) throw new Error('Tableau requis');\n"
                "  return rows.filter((x) => x >= 0).reduce((a, b) => a + b, 0);\n"
                "}\n"
                "console.assert(summarizeScores([10, 20]) === 30);\n"
            ),
        },
        headers=user_a_headers,
    )
    val = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/validate",
        headers=user_a_headers,
    )
    assert val.status_code == 200
    assert len(val.json()["levels"][1]["resources"]) >= 1

    validated_regen = client.post(
        f"/api/v1/courses/{course['id']}/levels/{lvl1['id']}/regenerate",
        json={},
        headers=user_a_headers,
    )
    assert validated_regen.status_code == 409
    assert validated_regen.json()["error"]["code"] == "LEVEL_ALREADY_VALIDATED"


def test_user_ai_config_preferred_for_enrichment_without_leaking_server_key(monkeypatch) -> None:
    seen_headers: list[dict[str, str]] = []

    class _FakeResp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"title": "Niveau 1 enrichi", "summary": "Plan ciblé enrichi par IA utilisateur", "objectives": ["Obj 1", "Obj 2"], "project_title": "Projet IA", "project_brief": "Brief détaillé validé pour vérifier la génération IA utilisateur."}'
                        }
                    }
                ]
            }

    def _fake_request(method, url, *, settings=None, headers=None, json_body=None, **kw):
        seen_headers.append(dict(headers or {}))
        return _FakeResp()

    monkeypatch.setattr(course_generator, "safe_http_request", _fake_request)
    monkeypatch.setattr(
        course_generator,
        "validate_outbound_url",
        lambda url, **kw: url.rstrip("/"),
    )

    server_settings = Settings(
        ai_provider="openai",
        ai_api_key="server-secret-should-not-leak",
        ai_model="gpt-4o-mini",
    )
    user_cfg = {
        "provider": "openai_compatible",
        "base_url": "https://llm.student-lab.example/v1",
        "model": "custom-tutor-7b",
        "api_key": "",
    }
    patch, source, model = course_generator._try_enrich_level_with_llm(
        subject="Python",
        level_number=1,
        language=CourseLanguage.fr,
        settings=server_settings,
        user_ai_config=user_cfg,
    )
    assert patch is None
    assert len(seen_headers) == 0

    user_cfg_with_key = {**user_cfg, "api_key": "user-own-key-123"}
    generated = course_generator.generate_level_content(
        subject="Python",
        language=CourseLanguage.fr,
        level_number=1,
        total_levels=3,
        settings=server_settings,
        user_ai_config=user_cfg_with_key,
    )
    assert generated["generation_source"] == "user_ai"
    assert generated["generation_model"] == "custom-tutor-7b"
    assert seen_headers[0]["Authorization"] == "Bearer user-own-key-123"
