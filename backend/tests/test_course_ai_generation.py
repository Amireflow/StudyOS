import pytest

from app.core.errors import AppError
from app.schemas.common import CourseLanguage
from app.services import course_generator


def test_ai_blueprint_uses_personalized_learner_context(monkeypatch):
    captured = {}
    generated = {
        "title": "Python pour l'automatisation métier",
        "domain": "Automatisation",
        "description": "Créer des outils fiables pour automatiser des tâches métier.",
        "levels_roadmap": [
            {
                "level_number": 1,
                "title": "Python utile et fondamentaux appliqués",
                "summary": "Acquérir les bases nécessaires à l'automatisation de tâches concrètes.",
                "objectives": [
                    "Écrire des scripts Python exécutables",
                    "Manipuler des fichiers CSV et JSON",
                    "Gérer les erreurs et valider les entrées",
                ],
                "project_title": "Automatiser un rapport CSV",
            },
            {
                "level_number": 2,
                "title": "Automatisation de flux de données",
                "summary": "Construire des traitements de données réutilisables et testables.",
                "objectives": [
                    "Concevoir des fonctions réutilisables",
                    "Consommer une API HTTP",
                    "Tester les traitements et leurs erreurs",
                ],
                "project_title": "Synchroniseur de données",
            },
        ],
    }

    def fake_call(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return generated, "user_ai", "gpt-test-model"

    monkeypatch.setattr(course_generator, "_call_course_ai_json", fake_call)
    blueprint = course_generator.build_course_blueprint(
        subject="Python",
        language=CourseLanguage.fr,
        total_levels=2,
        goal="Automatiser des rapports pour une petite entreprise",
        user_ai_config={
            "provider": "openai",
            "api_key": "test-key",
            "model": "gpt-test-model",
        },
        learner_context={
            "demonstrated_skills": [{"name": "Excel", "current_level": 3}],
            "learner_profile": {"learning_preferences": {"style": "projets pratiques"}},
        },
    )

    assert blueprint["generation_source"] == "user_ai"
    assert blueprint["generation_model"] == "gpt-test-model"
    assert blueprint["levels_roadmap"][0]["title"] == generated["levels_roadmap"][0]["title"]
    assert "Automatiser des rapports pour une petite entreprise" in captured["prompt"]
    assert "Excel" in captured["prompt"]
    assert "projets pratiques" in captured["prompt"]


def test_ai_blueprint_rejects_repeated_level_titles(monkeypatch):
    generated = {
        "title": "Parcours Python",
        "levels_roadmap": [
            {
                "level_number": 1,
                "title": "Bases de Python",
                "summary": "Comprendre les fondations du langage et les appliquer.",
                "objectives": ["Écrire du code", "Manipuler des variables", "Créer des fonctions"],
                "project_title": "Projet initial",
            },
            {
                "level_number": 2,
                "title": "Bases de Python",
                "summary": "Approfondir les fondations du langage et les appliquer.",
                "objectives": ["Écrire du code avancé", "Manipuler des données", "Créer des modules"],
                "project_title": "Projet avancé",
            },
        ],
    }
    monkeypatch.setattr(
        course_generator,
        "_call_course_ai_json",
        lambda **kwargs: (generated, "user_ai", "gpt-test-model"),
    )

    with pytest.raises(AppError) as error:
        course_generator.build_course_blueprint(
            subject="Python",
            language=CourseLanguage.fr,
            total_levels=2,
            user_ai_config={"provider": "openai", "api_key": "test-key"},
        )

    assert error.value.code == "AI_COURSE_INVALID_ROADMAP"


def test_remote_course_generation_never_silently_falls_back_without_key():
    with pytest.raises(AppError) as error:
        course_generator._resolve_course_ai_runtime(
            settings=None,
            user_ai_config={"provider": "openai", "api_key": "", "model": "gpt-4o-mini"},
        )

    assert error.value.code == "AI_COURSE_PROVIDER_NOT_CONFIGURED"


def test_generated_level_requires_substantial_teaching_content():
    valid, issues = course_generator.validate_generated_level_content(
        {
            "title": "Bases",
            "summary": "Une introduction courte aux bases essentielles.",
            "objectives": ["Comprendre les variables", "Écrire des fonctions"],
            "lessons": [],
        }
    )

    assert valid is False
    assert any("3 objectifs" in issue for issue in issues)
    assert any("3 et 6 chapitres" in issue for issue in issues)
