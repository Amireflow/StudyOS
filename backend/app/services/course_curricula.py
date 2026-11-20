"""Référentiels de ressources vérifiées et curricula détaillés pour le module Cours intelligent."""

from __future__ import annotations

from typing import Any


CURATED_RESOURCES: dict[str, list[dict[str, Any]]] = {
    "python": [
        {
            "title": "Documentation officielle Python 3 (Tutoriel en français)",
            "url": "https://docs.python.org/fr/3/tutorial/",
            "resource_type": "documentation",
            "language": "fr",
            "is_official": True,
            "source_name": "Python Software Foundation",
            "notes": "Référence officielle progressive : syntaxe, structures de données, modules et erreurs.",
            "min_level": 1,
            "max_level": 3,
        },
        {
            "title": "Documentation officielle Python 3 (Standard Library)",
            "url": "https://docs.python.org/3/library/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Python.org",
            "notes": "Référence complète des modules standard (pathlib, json, dataclasses, asyncio, unittest).",
            "min_level": 1,
            "max_level": 5,
        },
        {
            "title": "Harvard CS50P — Introduction to Programming with Python",
            "url": "https://cs50.harvard.edu/python/",
            "resource_type": "interactive",
            "language": "en",
            "is_official": True,
            "source_name": "Harvard University",
            "notes": "Cours universitaire complet avec exercices pratiques progressifs.",
            "min_level": 1,
            "max_level": 3,
        },
        {
            "title": "Harvard CS50P — Introduction to Programming with Python (Cours vidéo officiel)",
            "url": "https://cs50.harvard.edu/python/2022/weeks/",
            "resource_type": "video",
            "language": "en",
            "is_official": True,
            "source_name": "Harvard University (CS50)",
            "notes": "Cours vidéo universitaire complet avec démonstrations pas à pas et exercices progressifs.",
            "min_level": 1,
            "max_level": 3,
        },
        {
            "title": "Pytest — Documentation officielle",
            "url": "https://docs.pytest.org/en/stable/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "pytest.org",
            "notes": "Indispensable pour écrire et structurer vos tests unitaires et fixtures.",
            "min_level": 2,
            "max_level": 5,
        },
        {
            "title": "FastAPI — Tutoriel et guide utilisateur officiel",
            "url": "https://fastapi.tiangolo.com/tutorial/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "FastAPI",
            "notes": "Référence officielle pour Pydantic v2, Depends, async/await et TestClient.",
            "min_level": 3,
            "max_level": 5,
        },
        {
            "title": "SQLAlchemy 2.0 — Tutoriel unifié officiel",
            "url": "https://docs.sqlalchemy.org/en/20/tutorial/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "SQLAlchemy",
            "notes": "ORM moderne typé, transactions, sessions et requêtes préparées.",
            "min_level": 4,
            "max_level": 5,
        },
    ],
    "javascript": [
        {
            "title": "MDN Web Docs — Guide JavaScript (FR)",
            "url": "https://developer.mozilla.org/fr/docs/Web/JavaScript/Guide",
            "resource_type": "documentation",
            "language": "fr",
            "is_official": True,
            "source_name": "Mozilla MDN",
            "notes": "Référence officielle complète sur le langage JavaScript moderne (ES6+).",
            "min_level": 1,
            "max_level": 4,
        },
        {
            "title": "The Modern JavaScript Tutorial (JavaScript.info)",
            "url": "https://javascript.info/",
            "resource_type": "interactive",
            "language": "en",
            "is_official": False,
            "source_name": "JavaScript.info",
            "notes": "Parcours approfondi : closures, prototypes, DOM, événements et promesses.",
            "min_level": 1,
            "max_level": 5,
        },
        {
            "title": "MDN Web Docs — JavaScript asynchrone (FR)",
            "url": "https://developer.mozilla.org/fr/docs/Learn_web_development/Extensions/Async_JS",
            "resource_type": "documentation",
            "language": "fr",
            "is_official": True,
            "source_name": "Mozilla MDN",
            "notes": "Comprendre boucle d'événements, Promesses, Fetch API et async/await.",
            "min_level": 2,
            "max_level": 5,
        },
        {
            "title": "Vitest — Documentation officielle de tests JS/TS",
            "url": "https://vitest.dev/guide/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Vitest",
            "notes": "Tests unitaires et d'intégration rapides avec modules ES.",
            "min_level": 3,
            "max_level": 5,
        },
    ],
    "typescript": [
        {
            "title": "TypeScript Handbook officiel",
            "url": "https://www.typescriptlang.org/docs/handbook/intro.html",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Microsoft TypeScript",
            "notes": "Guide officiel du typage statique, interfaces, unions et génériques.",
            "min_level": 1,
            "max_level": 3,
        },
        {
            "title": "TypeScript Playground officiel",
            "url": "https://www.typescriptlang.org/play",
            "resource_type": "interactive",
            "language": "en",
            "is_official": True,
            "source_name": "TypeScript.org",
            "notes": "Bac à sable interactif pour tester vos types en direct sans installation.",
            "min_level": 1,
            "max_level": 5,
        },
        {
            "title": "TypeScript — Narrowing & Generics (Référence officielle)",
            "url": "https://www.typescriptlang.org/docs/handbook/2/generics.html",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Microsoft TypeScript",
            "notes": "Conception d'abstractions génériques, contraintes `extends` et types utilitaires.",
            "min_level": 2,
            "max_level": 5,
        },
        {
            "title": "TypeScript Utility Types & Conditional Types",
            "url": "https://www.typescriptlang.org/docs/handbook/utility-types.html",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Microsoft TypeScript",
            "notes": "Types dérivés avancés (`Partial`, `Pick`, `Omit`, `Record`, `ReturnType`).",
            "min_level": 3,
            "max_level": 5,
        },
        {
            "title": "MDN Web Docs — JavaScript & Fondamentaux Web (FR)",
            "url": "https://developer.mozilla.org/fr/docs/Web/JavaScript/Guide",
            "resource_type": "documentation",
            "language": "fr",
            "is_official": True,
            "source_name": "MDN Web Docs",
            "notes": "Socle JavaScript moderne exécuté sous TypeScript.",
            "min_level": 1,
            "max_level": 2,
        },
    ],
    "react": [
        {
            "title": "Documentation officielle React (Version française)",
            "url": "https://fr.react.dev/learn",
            "resource_type": "documentation",
            "language": "fr",
            "is_official": True,
            "source_name": "React Team (react.dev)",
            "notes": "Guide officiel interactif : composants, état, hooks et effets sans détour.",
            "min_level": 1,
            "max_level": 3,
        },
        {
            "title": "React Official Docs — Thinking in React",
            "url": "https://react.dev/learn/thinking-in-react",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "React.dev",
            "notes": "Méthode officielle pour découper une interface en composants propres.",
            "min_level": 1,
            "max_level": 3,
        },
        {
            "title": "TanStack Query — Documentation officielle React",
            "url": "https://tanstack.com/query/latest/docs/framework/react/overview",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "TanStack",
            "notes": "Gestion du cache serveur, revalidations, mutations et synchronisation.",
            "min_level": 2,
            "max_level": 5,
        },
        {
            "title": "Testing Library — React Testing Library",
            "url": "https://testing-library.com/docs/react-testing-library/intro/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Testing Library",
            "notes": "Tests d'accessibilité et de parcours utilisateur avec `getByRole` et `userEvent`.",
            "min_level": 2,
            "max_level": 5,
        },
    ],
    "sql": [
        {
            "title": "Documentation officielle PostgreSQL (Tutoriel SQL)",
            "url": "https://www.postgresql.org/docs/current/tutorial.html",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "PostgreSQL Global Development Group",
            "notes": "Tutoriel officiel sur SELECT, jointures, agrégations et transactions.",
            "min_level": 1,
            "max_level": 3,
        },
        {
            "title": "SQLBolt — Exercices interactifs SQL pas à pas",
            "url": "https://sqlbolt.com/",
            "resource_type": "interactive",
            "language": "en",
            "is_official": False,
            "source_name": "SQLBolt",
            "notes": "Leçons courtes et requêtes exécutables directement dans le navigateur.",
            "min_level": 1,
            "max_level": 2,
        },
        {
            "title": "Formation SQL & Bases de données relationnelles (FR)",
            "url": "https://sql.sh/",
            "resource_type": "documentation",
            "language": "fr",
            "is_official": False,
            "source_name": "SQL.sh",
            "notes": "Fiches synthétiques en français pour chaque clause SQL avec exemples.",
            "min_level": 1,
            "max_level": 4,
        },
        {
            "title": "PostgreSQL — Indexation & plans d'exécution (Docs)",
            "url": "https://www.postgresql.org/docs/current/indexes.html",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "PostgreSQL.org",
            "notes": "B-Tree, index composites, index partiels et lecture d'EXPLAIN ANALYZE.",
            "min_level": 3,
            "max_level": 5,
        },
        {
            "title": "PostgreSQL — Contrôle de concurrence & Transactions (MVCC)",
            "url": "https://www.postgresql.org/docs/current/mvcc.html",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "PostgreSQL.org",
            "notes": "Niveaux d'isolation, verrous, deadlocks et intégrité transactionnelle.",
            "min_level": 4,
            "max_level": 5,
        },
    ],
    "rust": [
        {
            "title": "The Rust Programming Language (The Book — Officiel)",
            "url": "https://doc.rust-lang.org/book/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Rust-lang.org",
            "notes": "Référence officielle complète sur l’ownership, le borrowing, les traits et la concurrence.",
            "min_level": 1,
            "max_level": 5,
        },
        {
            "title": "Rust by Example (Officiel)",
            "url": "https://doc.rust-lang.org/rust-by-example/",
            "resource_type": "interactive",
            "language": "en",
            "is_official": True,
            "source_name": "Rust-lang.org",
            "notes": "Exemples compilables et modifiables directement en ligne.",
            "min_level": 1,
            "max_level": 4,
        },
        {
            "title": "Rustlings — Exercices officiels progressifs",
            "url": "https://github.com/rust-lang/rustlings",
            "resource_type": "interactive",
            "language": "en",
            "is_official": True,
            "source_name": "Rust Team",
            "notes": "Petits exercices ciblés pour maîtriser la syntaxe et le compilateur.",
            "min_level": 1,
            "max_level": 3,
        },
        {
            "title": "Asynchronous Programming in Rust (Async Book)",
            "url": "https://rust-lang.github.io/async-book/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Rust-lang.org",
            "notes": "Futures, async/await, Tokio et conception de services concurrents sûrs.",
            "min_level": 4,
            "max_level": 5,
        },
    ],
    "java": [
        {
            "title": "Dev.java — Documentation & Tutoriels officiels Oracle",
            "url": "https://dev.java/learn/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Oracle Java",
            "notes": "Guide officiel moderne : POO, records, collections, streams et concurrence.",
            "min_level": 1,
            "max_level": 5,
        },
        {
            "title": "MOOC Java Programming (University of Helsinki)",
            "url": "https://java-programming.mooc.fi/",
            "resource_type": "interactive",
            "language": "en",
            "is_official": True,
            "source_name": "University of Helsinki",
            "notes": "Parcours universitaire reconnu avec exercices pratiques corrigés.",
            "min_level": 1,
            "max_level": 3,
        },
        {
            "title": "Dev.java — Streams, Optional & Collections modernes",
            "url": "https://dev.java/learn/api/streams/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Oracle Java",
            "notes": "Pipelines fonctionnels, collecteurs et bonnes pratiques sans NullPointerException.",
            "min_level": 2,
            "max_level": 5,
        },
    ],
    "go": [
        {
            "title": "A Tour of Go (Officiel & Interactif)",
            "url": "https://go.dev/tour/",
            "resource_type": "interactive",
            "language": "en",
            "is_official": True,
            "source_name": "go.dev",
            "notes": "Tour officiel interactif des bases, interfaces et goroutines.",
            "min_level": 1,
            "max_level": 3,
        },
        {
            "title": "Documentation officielle Go (Effective Go)",
            "url": "https://go.dev/doc/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "go.dev",
            "notes": "Effective Go et guides officiels de conception idiomatique.",
            "min_level": 1,
            "max_level": 5,
        },
    ],
}

FALLBACK_RESOURCES: list[dict[str, Any]] = [
    {
        "title": "MDN Web Docs — Ressources pour développeurs (FR)",
        "url": "https://developer.mozilla.org/fr/",
        "resource_type": "documentation",
        "language": "fr",
        "is_official": True,
        "source_name": "Mozilla MDN",
        "notes": "Base documentaire fiable et régulièrement mise à jour.",
        "min_level": 1,
        "max_level": 5,
    },
    {
        "title": "Roadmap.sh — Parcours guidés par compétences",
        "url": "https://roadmap.sh/",
        "resource_type": "article",
        "language": "en",
        "is_official": False,
        "source_name": "roadmap.sh",
        "notes": "Cartographie claire des notions par palier de progression.",
        "min_level": 1,
        "max_level": 5,
    },
    {
        "title": "freeCodeCamp — Parcours pratiques gratuits",
        "url": "https://www.freecodecamp.org/learn/",
        "resource_type": "interactive",
        "language": "en",
        "is_official": False,
        "source_name": "freeCodeCamp",
        "notes": "Exercices interactifs et projets progressifs gratuits.",
        "min_level": 1,
        "max_level": 5,
    },
]


SUBJECT_CODE_LANG: dict[str, str] = {
    "python": "python",
    "typescript": "typescript",
    "javascript": "javascript",
    "react": "tsx",
    "sql": "sql",
    "postgresql": "sql",
    "rust": "rust",
    "java": "java",
    "go": "go",
}


SUBJECT_DOMAIN_DEFAULT: dict[str, str] = {
    "python": "Backend & Scripting",
    "typescript": "Frontend & Architecture",
    "javascript": "Développement Web",
    "react": "Interfaces Frontend",
    "sql": "Bases de données",
    "postgresql": "Bases de données",
    "rust": "Systèmes & Performance",
    "java": "Développement Logiciel",
    "go": "Backend & Systèmes",
}


def resolve_topic_key(subject: str) -> str:
    lowered = subject.strip().lower()
    if "python" in lowered or "fastapi" in lowered or "django" in lowered:
        return "python"
    if "typescript" in lowered or re_word_match(lowered, "ts"):
        return "typescript"
    if "javascript" in lowered or re_word_match(lowered, "js"):
        return "javascript"
    if "react" in lowered or "next" in lowered:
        return "react"
    if "sql" in lowered or "postgres" in lowered:
        return "sql"
    if "rust" in lowered:
        return "rust"
    if "java" in lowered and "javascript" not in lowered:
        return "java"
    if re_word_match(lowered, "go") or "golang" in lowered:
        return "go"
    return "generic"


def re_word_match(text: str, word: str) -> bool:
    return f" {word} " in f" {text} " or text == word


def get_curated_resources_for_subject(
    subject: str,
    language_pref: str,
    level_number: int = 1,
) -> list[dict[str, Any]]:
    topic = resolve_topic_key(subject)
    raw_list = CURATED_RESOURCES.get(topic, [])
    base = list(raw_list) if raw_list else list(FALLBACK_RESOURCES)
    scoped = [
        r
        for r in base
        if int(r.get("min_level", 1)) <= level_number <= int(r.get("max_level", 5))
    ]
    combined = scoped if len(scoped) >= 2 else base
    if language_pref == "fr":
        combined.sort(key=lambda r: (0 if r["language"] == "fr" else 1, 0 if r["is_official"] else 1))
    elif language_pref == "en":
        combined.sort(key=lambda r: (0 if r["language"] == "en" else 1, 0 if r["is_official"] else 1))
    else:
        combined.sort(key=lambda r: (0 if r["is_official"] else 1, r["language"]))
    return combined[:6]


def normalize_lesson_to_eight_parts(
    lesson: dict[str, Any],
    *,
    subject: str,
    code_lang: str,
    level_number: int,
    language_pref: str = "fr",
) -> dict[str, Any]:
    """Garantit une structure pédagogique complète en 8 rubriques et des exercices typés."""
    raw_md = str(lesson.get("content_markdown") or "").strip()
    summary = str(lesson.get("summary") or "").strip()
    title = str(lesson.get("title") or "Chapitre").strip()
    examples = [dict(ex) for ex in (lesson.get("code_examples") or []) if isinstance(ex, dict)]
    exercises = list(lesson.get("exercises") or [])

    if len(examples) == 1:
        primary_ex = examples[0]
        ex_lang = str(primary_ex.get("language") or code_lang or "markdown")
        if ex_lang == "python":
            second_code = (
                f"# Cas d'utilisation réel & gestion des cas limites : {title}\n"
                "def validate_and_apply(items: list[str]) -> list[str]:\n"
                "    if not items:\n"
                "        raise ValueError('Entrée vide : au moins un élément est requis.')\n"
                "    return [item.strip() for item in items if item and item.strip()]\n"
                "\n"
                "assert validate_and_apply(['  ok  ', '']) == ['ok']"
            )
        elif ex_lang in ("typescript", "javascript", "tsx"):
            second_code = (
                f"// Cas d'utilisation réel & garde d'entrée : {title}\n"
                "function normalizeEntries(items) {\n"
                "  if (!Array.isArray(items) || items.length === 0) {\n"
                "    throw new Error('Entrée vide : fournissez au moins un élément.');\n"
                "  }\n"
                "  return items.map((x) => String(x).trim()).filter(Boolean);\n"
                "}"
            )
        elif ex_lang == "sql":
            second_code = (
                f"-- Cas d'utilisation réel & protection NULL : {title}\n"
                "SELECT id, COALESCE(title, 'Sans titre') AS safe_title\n"
                "FROM course_items\n"
                "WHERE status = 'active'\n"
                "ORDER BY created_at DESC;"
            )
        else:
            second_code = (
                f"Cas réel ({subject} · Niveau {level_number}) : {title}\n"
                "1. Contrôler les préconditions (entrée vide, borne invalide, valeur nulle).\n"
                "2. Appliquer la règle métier principale de manière déterministe.\n"
                "3. Vérifier la sortie attendue sur un jeu de test nominal et un cas d'erreur."
            )
        examples.append(
            {
                "title": f"Cas réel et gestion des cas limites — {title}",
                "language": ex_lang,
                "code": second_code,
                "explanation": (
                    "Complète le premier exemple en montrant comment protéger les entrées invalides "
                    "et vérifier le résultat attendu avant déploiement."
                ),
            }
        )

    if "### 2. Prérequis" not in raw_md and "### 2. Prerequisites" not in raw_md:
        ex_code_block = ""
        if examples and "```" not in raw_md:
            first_ex = examples[0]
            ex_code_block = (
                f"\n```{first_ex.get('language') or code_lang}\n"
                f"{first_ex.get('code', '')}\n```\n"
                f"*{first_ex.get('explanation', '')}*\n"
            )

        if language_pref == "en":
            sections = [
                f"## 1. Learning Objective\n\n{summary or title}",
                f"### 2. Prerequisites & Real-World Use Case\n\nEnsure previous concepts in **{subject}** (Level {level_number}) are solid before combining them here. In production systems, **{title}** prevents silent data corruption and enforces clear contracts.",
                f"### 3. Step-by-Step Explanation\n\n{raw_md}",
                f"### 4. Annotated Examples\n\nInspect the input contract, transformation logic, edge-case guard, and explicit return value.{ex_code_block}",
                "### 5. Edge Cases & Common Pitfalls\n\n- Always validate empty, null, or out-of-bounds inputs early.\n- Avoid silent fallbacks when an invariant fails.",
                "### 6. Best Practices\n\n- Keep functions single-purpose with shallow nesting and explicit types or contracts.",
                f"### 7. Key Takeaway\n\nMastering **{title}** relies on explicit boundaries, readable invariants, and reproducible verification.",
                "### 8. Comprehension Check\n\nBefore coding, explain *why* each guard exists and test both a nominal case and an invalid input.",
            ]
        else:
            bilingual_note = (
                f"\n\n*(Key terms: prerequisite = prérequis, edge case = cas limite, guard clause = retour anticipé)*"
                if language_pref == "bilingual"
                else ""
            )
            sections = [
                f"## 1. Objectif pédagogique\n\n{summary or title}{bilingual_note}",
                f"### 2. Prérequis & cas d'utilisation réel\n\nPour aborder **{title}** en **{subject}** (Niveau {level_number}), appuyez-vous sur des entrées clairement typées et une séparation nette entre validation et calcul. En conditions réelles, cette pratique évite les régressions silencieuses lors du traitement de données externes.",
                f"### 3. Explication pas à pas\n\n{raw_md}",
                f"### 4. Exemples pratiques commentés\n\nObservez comment les exemples ci-dessous protègent les entrées et rendent le résultat explicite.{ex_code_block}",
                "### 5. Cas limites & erreurs fréquentes\n\n- Entrée vide, nulle (`None`/`null`) ou hors bornes : validez dès le début de la fonction.\n- Ne masquez jamais une erreur par un résultat par défaut trompeur.",
                "### 6. Bonnes pratiques\n\n- Fonctions courtes à responsabilité unique, noms explicites et gestion d’erreurs déterministe.",
                f"### 7. Synthèse à retenir\n\n« {title} » repose sur un contrat clair (entrées attendues -> traitement -> sortie ou erreur explicite).",
                "### 8. Contrôle de compréhension\n\nAvant de passer au chapitre suivant, résumez le rôle du cas limite principal avec vos mots et réalisez l’exercice guidé ci-dessous.",
            ]
        normalized_md = "\n\n".join(sections)
    else:
        normalized_md = raw_md

    normalized_exercises: list[dict[str, Any]] = []
    for idx, ex in enumerate(exercises):
        item = dict(ex)
        if "exercise_type" not in item:
            starter = str(item.get("starter_code") or "").strip()
            if item.get("expected_answer") and item.get("choices"):
                item["exercise_type"] = "closed_quiz"
            elif starter or code_lang != "text":
                item["exercise_type"] = "code"
            else:
                item["exercise_type"] = "open_explanation"
        item.setdefault("choices", [])
        item.setdefault("expected_answer", None)
        hints_list = [str(h).strip() for h in (item.get("hints") or []) if str(h).strip()]
        if len(hints_list) < 2:
            hints_list.append(
                "Vérifiez d'abord les entrées invalides (vide, nul ou hors bornes) avant d'écrire le cas nominal, puis testez avec une assertion explicite."
            )
        item["hints"] = hints_list
        normalized_exercises.append(item)
        # Ajouter un quiz fermé de contrôle de compréhension sur le premier chapitre si absent
        if idx == 0 and len(exercises) == 1 and int(lesson.get("position") or 1) == 4:
            concepts = list(item.get("expected_concepts") or [])
            anchor = concepts[0] if concepts else subject
            correct_choice = (
                f"Valider les entrées/invariants dès le début et vérifier {anchor} sur cas nominal et cas limite"
            )
            normalized_exercises.append(
                {
                    "id": f"{item.get('id', f'lv{level_number}')}-quiz",
                    "title": f"Contrôle rapide : {title}",
                    "difficulty": "guide",
                    "exercise_type": "closed_quiz",
                    "instructions_markdown": (
                        f"Quelle pratique garantit la fiabilité de « {title} » au niveau {level_number} ?"
                    ),
                    "choices": [
                        correct_choice,
                        "Ignorer les entrées invalides pour éviter de lever une erreur",
                        "Dupliquer la logique dans chaque appelant sans tests",
                    ],
                    "expected_answer": correct_choice,
                    "starter_code": None,
                    "hints": [
                        "Pensez aux retours anticipés (guard clauses) et aux cas limites."
                    ],
                    "expected_concepts": concepts[:3] or ["validation", "cas limite"],
                }
            )

    return {
        **lesson,
        "content_markdown": normalized_md,
        "code_examples": examples,
        "exercises": normalized_exercises,
    }


def get_python_levels() -> dict[int, dict[str, Any]]:
    return {
        1: {
            "title": "Niveau 1 — Fondations Python propres et structurées",
            "summary": "Comprendre les variables, types de base, conditions, boucles, fonctions pures et collections essentielles.",
            "objectives": [
                "Manipuler variables, types primitifs (`int`, `float`, `str`, `bool`) et f-strings",
                "Contrôler le flux avec `if/elif/else` et les boucles `for` / `while`",
                "Structurer des données avec listes et dictionnaires sans effets de bord cachés",
                "Écrire des fonctions typées, documentées et gérant les cas limites",
            ],
            "lessons": [
                {
                    "position": 1,
                    "title": "Variables, types de base et formatage lisible",
                    "summary": "Poser des bases saines : typage dynamique, f-strings, conversions sûres et nommage explicite.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "En Python, chaque valeur possède un **type précis** même si vous ne déclarez pas "
                        "le type avant la variable. Écrire du code clair dès le premier jour repose sur des noms "
                        "explicites (`snake_case`) et des conversions maîtrisées.\n\n"
                        "### Explication pas à pas\n\n"
                        "1. **Noms explicites** : préférez `average_score` à `x` ou `res`.\n"
                        "2. **Chaînes formatées (f-strings)** : `f\"{student} : {score}/20\"` reste plus lisible et rapide que la concaténation avec `+`.\n"
                        "3. **Annotations de type** : ajouter `: int`, `: float` ou `: str` aide votre éditeur et documente votre intention.\n\n"
                        "```python\n"
                        "# Déclaration claire avec annotations et f-string\n"
                        "student_name: str = \"Khadim\"\n"
                        "completed_lessons: int = 4\n"
                        "total_lessons: int = 12\n\n"
                        "progress_pct: float = (completed_lessons / total_lessons) * 100\n"
                        "print(f\"{student_name} — progression : {progress_pct:.1f}%\")\n"
                        "```\n\n"
                        "| Type Python | Exemple | Usage principal |\n"
                        "| --- | --- | --- |\n"
                        "| `int` | `42` | Compteurs, âges, indices |\n"
                        "| `float` | `15.75` | Moyennes, taux, mesures |\n"
                        "| `str` | `\"Python\"` | Textes, identifiants lisibles |\n"
                        "| `bool` | `True` / `False` | Conditions et états |\n\n"
                        "> **Piège fréquent :** Diviser deux entiers avec `/` renvoie toujours un `float`. Utilisez `//` pour une division entière."
                    ),
                    "code_examples": [
                        {
                            "title": "Conversion sécurisée d'une entrée texte",
                            "language": "python",
                            "code": (
                                "raw_hours = \"3\"\n"
                                "hours = int(raw_hours.strip())\n"
                                "minutes = hours * 60\n"
                                "print(f\"{hours} h correspondent à {minutes} min\")"
                            ),
                            "explanation": "Nettoyer la chaîne avec `.strip()` avant `int(...)` évite des erreurs sur les espaces superflus.",
                        },
                        {
                            "title": "Calcul formaté avec arrondi",
                            "language": "python",
                            "code": (
                                "score = 17.3333\n"
                                "threshold = 14.0\n"
                                "passed = score >= threshold\n"
                                "print(f\"Note : {score:.2f}/20 — Validé : {passed}\")"
                            ),
                            "explanation": "L’expression booléenne `score >= threshold` évite un `if ...: return True else: return False` inutile.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-1-1-ex1",
                            "title": "Calculateur de temps d'étude hebdomadaire",
                            "difficulty": "guide",
                            "instructions_markdown": (
                                "Écrivez un script Python qui stocke le nombre de séances (`int`) et la durée moyenne en minutes (`int`), "
                                "calcule le total en heures et minutes, puis affiche un résumé formaté via une f-string."
                            ),
                            "starter_code": "sessions_count = 5\nminutes_per_session = 45\n# Calculez total_minutes, hours et remaining_minutes\n",
                            "hints": [
                                "Multipliez `sessions_count * minutes_per_session` pour obtenir `total_minutes`.",
                                "Utilisez `total_minutes // 60` pour les heures et `total_minutes % 60` pour le reste en minutes.",
                                "Formatez l’affichage avec `print(f\"{hours} h {remaining_minutes:02d}\")`.",
                            ],
                            "expected_concepts": ["int", "f-string", "//", "%", "minutes", "heures"],
                        },
                    ],
                },
                {
                    "position": 2,
                    "title": "Conditions et boucles sans imbrication excessive",
                    "summary": "Écrire des branchements lisibles avec retours anticipés et itérer proprement avec `enumerate`.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "La lisibilité d’un programme dépend directement de la façon dont vous structurez vos "
                        "conditions et vos boucles.\n\n"
                        "### Règle d'or : les retours anticipés (guard clauses)\n\n"
                        "Au lieu d’imbriquer 3 niveaux de `if`, vérifiez d’abord les cas invalides ou limites et sortez tôt.\n\n"
                        "```python\n"
                        "def classify_score(score: int) -> str:\n"
                        "    if score < 0 or score > 100:\n"
                        "        raise ValueError(\"Le score doit être compris entre 0 et 100.\")\n"
                        "    if score >= 85:\n"
                        "        return \"Maîtrise\"\n"
                        "    if score >= 70:\n"
                        "        return \"Validé\"\n"
                        "    return \"À renforcer\"\n"
                        "```\n\n"
                        "### Boucler proprement avec `enumerate`\n\n"
                        "```python\n"
                        "chapters = [\"Variables\", \"Conditions\", \"Collections\"]\n"
                        "for index, title in enumerate(chapters, start=1):\n"
                        "    print(f\"Chapitre {index:02d} : {title}\")\n"
                        "```\n\n"
                        "> **Bonnes pratiques :** N’itérez jamais par indice `range(len(items))` quand `enumerate(items)` donne directement l’indice et la valeur."
                    ),
                    "code_examples": [
                        {
                            "title": "Validation par clause de garde",
                            "language": "python",
                            "code": (
                                "def compute_discount(price: float, is_student: bool) -> float:\n"
                                "    if price <= 0:\n"
                                "        return 0.0\n"
                                "    return round(price * (0.8 if is_student else 1.0), 2)"
                            ),
                            "explanation": "Les cas limites sont traités dès la première ligne de la fonction.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-1-2-ex1",
                            "title": "Filtre et classement de notes",
                            "difficulty": "guide",
                            "instructions_markdown": (
                                "À partir d’une liste de notes `scores`, ignorez les valeurs négatives ou > 100, "
                                "comptez combien atteignent au moins 70 et calculez la moyenne des notes valides."
                            ),
                            "starter_code": "scores = [82, -5, 64, 91, 105, 73]\n",
                            "hints": [
                                "Créez une liste `valid_scores = [s for s in scores if 0 <= s <= 100]`.",
                                "Vérifiez si `valid_scores` est vide avant de diviser par `len(valid_scores)`.",
                                "Utilisez `sum(1 for s in valid_scores if s >= 70)` pour compter les réussites.",
                            ],
                            "expected_concepts": ["for", "if", "valid", "sum", "len", "cas limite"],
                        },
                    ],
                },
                {
                    "position": 3,
                    "title": "Listes, dictionnaires et compréhensions",
                    "summary": "Choisir la bonne structure selon le besoin : ordre (list), unicité (set) ou indexation par clé (dict).",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Choisir entre `list`, `dict` et `set` rend votre code plus rapide et deux fois plus court.\n\n"
                        "| Structure | Syntaxe | Ordre | Doublons | Recherche |\n"
                        "| --- | --- | --- | --- | --- |\n"
                        "| `list` | `[1, 2, 3]` | Préservé | Autorisés | `O(n)` |\n"
                        "| `dict` | `{\"k\": 1}` | Insertion | Clés uniques | `O(1)` |\n"
                        "| `set` | `{1, 2, 3}` | Non indexé | Interdits | `O(1)` |\n\n"
                        "```python\n"
                        "tasks = [\n"
                        "    {\"title\": \"Lire le cours\", \"done\": True},\n"
                        "    {\"title\": \"Coder le projet\", \"done\": False},\n"
                        "]\n\n"
                        "pending_titles = [t[\"title\"] for t in tasks if not t[\"done\"]]\n"
                        "status_by_title = {t[\"title\"]: t[\"done\"] for t in tasks}\n"
                        "print(pending_titles, status_by_title.get(\"Inconnu\", False))\n"
                        "```\n\n"
                        "> **Astuce :** Utilisez `mon_dict.get(cle, valeur_defaut)` plutôt que `mon_dict[cle]` quand une clé peut être absente."
                    ),
                    "code_examples": [
                        {
                            "title": "Compteur d'occurrences avec dict.get",
                            "language": "python",
                            "code": (
                                "tags = [\"python\", \"sql\", \"python\", \"api\"]\n"
                                "counts: dict[str, int] = {}\n"
                                "for tag in tags:\n"
                                "    counts[tag] = counts.get(tag, 0) + 1\n"
                                "print(counts)"
                            ),
                            "explanation": "`dict.get(tag, 0)` initialise proprement le compteur sans `KeyError`.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-1-3-ex1",
                            "title": "Indexation de compétences par domaine",
                            "difficulty": "pratique",
                            "instructions_markdown": (
                                "Écrivez une fonction qui reçoit une liste de tuples `(nom, domaine, niveau)` "
                                "et retourne un dictionnaire regroupant les compétences par domaine avec leur niveau moyen."
                            ),
                            "starter_code": "def summarize_by_domain(items: list[tuple[str, str, int]]) -> dict[str, float]:\n    pass\n",
                            "hints": [
                                "Accumulez d’abord les niveaux dans un `dict[str, list[int]]`.",
                                "Parcourez ensuite `grouped.items()` pour calculer `round(sum(lvls) / len(lvls), 2)`.",
                                "Gérez le cas d’une liste vide en retournant `{}`.",
                            ],
                            "expected_concepts": ["dict", "list", "get", "def", "return"],
                        },
                    ],
                },
                {
                    "position": 4,
                    "title": "Fonctions réutilisables, gestion d'erreurs et tests simples",
                    "summary": "Isoler la logique métier dans des fonctions testables avec `try/except` ciblé et assertions.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Une fonction fiable fait **une seule chose clairement**, valide ses paramètres, "
                        "lève une exception explicite en cas d’anomalie et se vérifie avec des `assert`.\n\n"
                        "```python\n"
                        "def compute_average(values: list[float]) -> float:\n"
                        "    \"\"\"Retourne la moyenne arithmétique d'une liste non vide.\"\"\"\n"
                        "    if not values:\n"
                        "        raise ValueError(\"Impossible de calculer la moyenne d'une liste vide.\")\n"
                        "    return round(sum(values) / len(values), 2)\n\n"
                        "assert compute_average([10.0, 20.0]) == 15.0\n"
                        "try:\n"
                        "    compute_average([])\n"
                        "except ValueError as err:\n"
                        "    print(\"Erreur attendue :\", err)\n"
                        "```\n\n"
                        "> **Piège fréquent :** Ne capturez jamais `except Exception:` silencieusement (`pass`) — capturez toujours l’exception précise (`ValueError`, `KeyError`)."
                    ),
                    "code_examples": [
                        {
                            "title": "Tests nominaux et cas d'erreur par assert",
                            "language": "python",
                            "code": (
                                "def parse_positive_int(raw: str) -> int:\n"
                                "    value = int(raw.strip())\n"
                                "    if value <= 0:\n"
                                "        raise ValueError(\"La valeur doit être strictement positive.\")\n"
                                "    return value\n\n"
                                "assert parse_positive_int(\" 42 \") == 42"
                            ),
                            "explanation": "Combiner `.strip()`, la vérification `<= 0` et `assert` rend le comportement vérifiable immédiatement.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-1-4-ex1",
                            "title": "Fonction robuste avec tests d'erreur",
                            "difficulty": "pratique",
                            "instructions_markdown": (
                                "Implémentez `safe_divide(a: float, b: float) -> float` qui lève `ValueError` si `b == 0`, "
                                "puis écrivez 3 assertions couvrant cas nominal et cas d'erreur."
                            ),
                            "starter_code": "def safe_divide(a: float, b: float) -> float:\n    pass\n",
                            "hints": [
                                "Vérifiez `if b == 0: raise ValueError(...)` avant toute division.",
                                "Testez l'erreur avec un bloc `try: safe_divide(10, 0); assert False except ValueError: pass`.",
                                "Expliquez pourquoi une `ValueError` explicite vaut mieux que `ZeroDivisionError` non gérée.",
                            ],
                            "expected_concepts": ["def", "raise", "ValueError", "try", "except", "assert"],
                        },
                    ],
                },
            ],
            "project_title": "Gestionnaire de notes & progression étudiante en CLI",
            "project_brief": (
                "### Contexte du projet Niveau 1\n\n"
                "Concevez un module Python autonome permettant de gérer les notes et le temps d’étude "
                "d’un étudiant par matière.\n\n"
                "### Exigences fonctionnelles\n"
                "1. Définir une structure `dict` par matière contenant son nom, ses notes (`list[float]`) et ses minutes étudiées.\n"
                "2. Implémenter `add_grade(store, subject, grade)` validant `0 <= grade <= 20` (sinon `ValueError`).\n"
                "3. Implémenter `compute_report(store)` qui renvoie la moyenne par matière, la matière la plus forte et la moyenne générale.\n"
                "4. Fournir un jeu de **4 tests `assert`** minimum couvrant cas nominal, matière vide et note invalide (`< 0` ou `> 20`)."
            ),
            "project_deliverables": [
                "Fonctions `add_grade` et `compute_report` typées et documentées",
                "Validation des notes hors bornes [0, 20] par `ValueError`",
                "Au moins 4 assertions / tests couvrant nominal + erreurs",
                "Explication claire des choix de structures de données et cas limites",
            ],
        },
        2: {
            "title": "Niveau 2 — Modularité, POO, fichiers JSON & tests Pytest",
            "summary": "Structurer un vrai projet Python : dataclasses, pathlib, persistance JSON, modules et tests Pytest.",
            "objectives": [
                "Modéliser des entités métier propres avec `@dataclass`",
                "Lire et sauvegarder des données de façon atomique avec `pathlib` et `json`",
                "Organiser son code en modules réutilisables avec gestion d’exceptions métier",
                "Écrire une suite de tests automatisés avec `pytest`",
            ],
            "lessons": [
                {
                    "position": 1,
                    "title": "Modéliser avec @dataclass et méthodes métier",
                    "summary": "Remplacer les dictionnaires fragiles par des classes typées et lisibles.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Quand un programme grandit, manipuler des dictionnaires avec des clés texte favorise les fautes de frappe. "
                        "`@dataclass` génère automatiquement `__init__`, `__repr__` et l’égalité tout en gardant un code concis.\n\n"
                        "```python\n"
                        "from dataclasses import dataclass, field\n\n"
                        "@dataclass\n"
                        "class StudyTask:\n"
                        "    title: str\n"
                        "    minutes: int = 30\n"
                        "    done: bool = False\n"
                        "    tags: list[str] = field(default_factory=list)\n\n"
                        "    def complete(self) -> None:\n"
                        "        self.done = True\n"
                        "```\n\n"
                        "> **Piège fréquent :** Utilisez toujours `field(default_factory=list)` pour une liste par défaut, jamais `tags: list[str] = []`."
                    ),
                    "code_examples": [
                        {
                            "title": "Dataclass immuable avec validation dans __post_init__",
                            "language": "python",
                            "code": (
                                "from dataclasses import dataclass\n\n"
                                "@dataclass(frozen=True)\n"
                                "class Grade:\n"
                                "    subject: str\n"
                                "    value: float\n\n"
                                "    def __post_init__(self) -> None:\n"
                                "        if not (0 <= self.value <= 20):\n"
                                "            raise ValueError(\"Note hors [0, 20]\")"
                            ),
                            "explanation": "`__post_init__` valide les invariants métier dès la construction.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-2-1-ex1",
                            "title": "Entité StudySession en dataclass",
                            "difficulty": "guide",
                            "instructions_markdown": (
                                "Créez une dataclass `StudySession` avec `title`, `minutes` (> 0 validé dans `__post_init__`) "
                                "et une méthode `to_dict()` prête pour l'export JSON."
                            ),
                            "starter_code": "from dataclasses import dataclass\n\n@dataclass\nclass StudySession:\n    pass\n",
                            "hints": [
                                "Ajoutez `title: str` et `minutes: int`.",
                                "Dans `__post_init__`, levez `ValueError` si `self.minutes <= 0`.",
                                "Retourne un dictionnaire dans `to_dict()`.",
                            ],
                            "expected_concepts": ["dataclass", "__post_init__", "ValueError", "def"],
                        },
                    ],
                },
                {
                    "position": 2,
                    "title": "Fichiers modernes avec pathlib et persistance JSON",
                    "summary": "Gérer les chemins sans erreur sous Windows/Linux/macOS et sérialiser en UTF-8.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Oubliez `os.path.join` et les chemins codés en dur : `pathlib.Path` gère automatiquement "
                        "les séparateurs multi-plateformes.\n\n"
                        "```python\n"
                        "import json\n"
                        "from pathlib import Path\n\n"
                        "def save_records(path: Path, records: list[dict]) -> None:\n"
                        "    path.parent.mkdir(parents=True, exist_ok=True)\n"
                        "    payload = json.dumps(records, ensure_ascii=False, indent=2)\n"
                        "    path.write_text(payload, encoding=\"utf-8\")\n\n"
                        "def load_records(path: Path) -> list[dict]:\n"
                        "    if not path.exists():\n"
                        "        return []\n"
                        "    return json.loads(path.read_text(encoding=\"utf-8\"))\n"
                        "```\n\n"
                        "> **Bonnes pratiques :** Précisez toujours `encoding=\"utf-8\"` et `ensure_ascii=False` pour préserver les accents."
                    ),
                    "code_examples": [
                        {
                            "title": "Lecture sécurisée d'un JSON potentiellement absent",
                            "language": "python",
                            "code": (
                                "from pathlib import Path\n"
                                "import json\n\n"
                                "def load_config(file_path: Path) -> dict:\n"
                                "    if not file_path.exists():\n"
                                "        return {\"theme\": \"system\"}\n"
                                "    return json.loads(file_path.read_text(encoding=\"utf-8\"))"
                            ),
                            "explanation": "Retourner une configuration par défaut si le fichier n'existe pas encore rend le script résilient.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-2-2-ex1",
                            "title": "Dépôt JSON réutilisable",
                            "difficulty": "pratique",
                            "instructions_markdown": (
                                "Implémentez `JsonStore(path: Path)` avec `load()` et `save(data)` gérant le dossier inexistant et le JSON invalide."
                            ),
                            "starter_code": "from pathlib import Path\nimport json\n",
                            "hints": [
                                "Créez le dossier parent avec `self.path.parent.mkdir(parents=True, exist_ok=True)`.",
                                "Attrapez `json.JSONDecodeError` dans `load()` pour remonter une erreur claire.",
                            ],
                            "expected_concepts": ["Path", "json", "JSONDecodeError", "utf-8"],
                        },
                    ],
                },
                {
                    "position": 3,
                    "title": "Exceptions métier personnalisées et séparation en couches",
                    "summary": "Découpler stockage, règles métier et interface d'affichage.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Un bon code sépare le **service métier** (règles) du **repository** (persistance) et du **CLI/API**.\n\n"
                        "```python\n"
                        "class DomainError(Exception):\n"
                        "    pass\n\n"
                        "class DuplicateEntryError(DomainError):\n"
                        "    pass\n"
                        "```\n\n"
                        "> **Astuce :** En testant votre couche service indépendamment du terminal (`input`/`print`), vos tests deviennent instantanés et déterministes."
                    ),
                    "code_examples": [
                        {
                            "title": "Service métier découplé du stockage",
                            "language": "python",
                            "code": (
                                "class EnrollmentService:\n"
                                "    def __init__(self, existing_ids: set[str]) -> None:\n"
                                "        self._ids = existing_ids\n\n"
                                "    def register(self, course_id: str) -> None:\n"
                                "        if course_id in self._ids:\n"
                                "            raise ValueError(\"Déjà inscrit\")\n"
                                "        self._ids.add(course_id)"
                            ),
                            "explanation": "Le service n'appelle jamais `print` ; il applique les invariants et lève une exception claire.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-2-3-ex1",
                            "title": "Exception métier ciblée",
                            "difficulty": "guide",
                            "instructions_markdown": (
                                "Créez une exception `LockedLevelError(Exception)` et une méthode `unlock_next` qui la lève si le projet n'est pas validé."
                            ),
                            "starter_code": "class LockedLevelError(Exception):\n    pass\n",
                            "hints": [
                                "Faites hériter `LockedLevelError` de `Exception`.",
                                "Passez un booléen `project_passed` et levez l'exception s'il est `False`.",
                            ],
                            "expected_concepts": ["class", "Exception", "raise", "def"],
                        },
                    ],
                },
                {
                    "position": 4,
                    "title": "Tester sérieusement avec Pytest et tmp_path",
                    "summary": "Écrire des tests unitaires isolés couvrant cas nominaux, exceptions et persistance temporaire.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Pytest fournit automatiquement la fixture `tmp_path` pour tester l’écriture sur disque sans polluer votre dépôt.\n\n"
                        "```python\n"
                        "import pytest\n\n"
                        "def test_save_and_reload(tmp_path):\n"
                        "    target = tmp_path / \"data.json\"\n"
                        "    save_records(target, [{\"name\": \"Python\"}])\n"
                        "    loaded = load_records(target)\n"
                        "    assert loaded == [{\"name\": \"Python\"}]\n\n"
                        "def test_invalid_raises():\n"
                        "    with pytest.raises(ValueError):\n"
                        "        compute_average([])\n"
                        "```\n\n"
                        "> **Bonnes pratiques :** Un test vérifie toujours 3 choses : le cas nominal, la persistance/état et le rejet des entrées invalides."
                    ),
                    "code_examples": [
                        {
                            "title": "Fixture Pytest réutilisable",
                            "language": "python",
                            "code": (
                                "import pytest\n\n"
                                "@pytest.fixture\n"
                                "def sample_scores() -> list[int]:\n"
                                "    return [75, 88, 92]\n\n"
                                "def test_mean(sample_scores):\n"
                                "    assert sum(sample_scores) / len(sample_scores) > 80"
                            ),
                            "explanation": "Les fixtures préparent un jeu de données propre par test.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-2-4-ex1",
                            "title": "Test Pytest avec raises et tmp_path",
                            "difficulty": "pratique",
                            "instructions_markdown": (
                                "Écrivez deux fonctions `test_*` vérifiant la sauvegarde JSON dans `tmp_path` et une erreur avec `pytest.raises`."
                            ),
                            "starter_code": "import pytest\nfrom pathlib import Path\n",
                            "hints": [
                                "Injectez `tmp_path: Path` en paramètre du test.",
                                "Utilisez `with pytest.raises(ValueError):` pour tester le cas d'erreur.",
                            ],
                            "expected_concepts": ["pytest", "tmp_path", "raises", "assert"],
                        },
                    ],
                },
            ],
            "project_title": "Bibliothèque de suivi de budget/temps persistée en JSON + suite Pytest",
            "project_brief": (
                "### Contexte du projet Niveau 2\n\n"
                "Construisez un package Python structuré combinant dataclasses, dépôt JSON via `pathlib`, "
                "service métier avec exceptions dédiées et suite de tests `pytest`.\n\n"
                "### Exigences techniques\n"
                "1. Modèles `@dataclass` avec validation dans `__post_init__`.\n"
                "2. Classe `Repository` utilisant `pathlib.Path` et `json` (gestion fichier manquant ou corrompu).\n"
                "3. Couche `Service` interdisant les montants/durées négatives et les doublons via exceptions métier.\n"
                "4. Suite Pytest d'au moins **5 tests** utilisant `tmp_path` et `pytest.raises`."
            ),
            "project_deliverables": [
                "Modèles `@dataclass` validés",
                "Persistance JSON avec `pathlib.Path`",
                "Exceptions métier et couche Service découplée",
                "Au moins 5 tests `pytest` (incluant `tmp_path` et `pytest.raises`)",
            ],
        },
        3: {
            "title": "Niveau 3 — APIs FastAPI, async/await & qualité production",
            "summary": "Concevoir une API REST moderne avec FastAPI, Pydantic v2, programmation asynchrone et tests d’intégration.",
            "objectives": [
                "Définir des schémas stricts et validateurs Pydantic v2",
                "Créer des endpoints FastAPI propres avec codes HTTP justes et gestion d’erreurs unifiée",
                "Comprendre `async`/`await`, injections de dépendances (`Depends`) et concurrence",
                "Tester l’API de bout en bout avec `TestClient`",
            ],
            "lessons": [
                {
                    "position": 1,
                    "title": "Validation stricte avec Pydantic v2",
                    "summary": "Sécuriser les entrées/sorties API et prévenir les données corrompues dès la frontière HTTP.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Pydantic v2 valide, convertit et documente automatiquement chaque requête entrante dans FastAPI.\n\n"
                        "```python\n"
                        "from pydantic import BaseModel, ConfigDict, Field, field_validator\n\n"
                        "class ArticleCreate(BaseModel):\n"
                        "    model_config = ConfigDict(extra=\"forbid\")\n"
                        "    title: str = Field(min_length=3, max_length=120)\n"
                        "    tags: list[str] = Field(default_factory=list)\n\n"
                        "    @field_validator(\"title\")\n"
                        "    @classmethod\n"
                        "    def strip_title(cls, value: str) -> str:\n"
                        "        return value.strip()\n"
                        "```\n\n"
                        "> **Bonnes pratiques :** Utilisez `ConfigDict(extra=\"forbid\")` sur les payloads de mutation pour rejeter tout champ inconnu ou privilégié."
                    ),
                    "code_examples": [
                        {
                            "title": "Schéma de mise à jour partielle",
                            "language": "python",
                            "code": (
                                "from pydantic import BaseModel\n\n"
                                "class ProfilePatch(BaseModel):\n"
                                "    display_name: str | None = None\n"
                                "    timezone: str | None = None"
                            ),
                            "explanation": "Les champs optionnels permettent des routes `PATCH` partielles sans écraser les autres valeurs.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-3-1-ex1",
                            "title": "Schéma Pydantic avec extra='forbid'",
                            "difficulty": "guide",
                            "instructions_markdown": (
                                "Écrivez un modèle `CourseSubmissionInput` interdisant les champs supplémentaires et validant une URL `https://`."
                            ),
                            "starter_code": "from pydantic import BaseModel, ConfigDict, field_validator\n",
                            "hints": [
                                "Ajoutez `model_config = ConfigDict(extra='forbid')`.",
                                "Dans `@field_validator('url')`, vérifiez `.startswith(('http://', 'https://'))`.",
                            ],
                            "expected_concepts": ["BaseModel", "ConfigDict", "field_validator", "forbid"],
                        },
                    ],
                },
                {
                    "position": 2,
                    "title": "Routes FastAPI, codes HTTP et Depends",
                    "summary": "Composer des routeurs modulaires avec injection de dépendances propre.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "`Depends(...)` permet d’injecter l’utilisateur courant, la session DB et les services métier dans chaque route.\n\n"
                        "```python\n"
                        "from fastapi import APIRouter, Depends, HTTPException, status\n\n"
                        "router = APIRouter(prefix=\"/items\", tags=[\"Items\"])\n\n"
                        "@router.post(\"\", status_code=status.HTTP_201_CREATED)\n"
                        "def create_item(payload: ArticleCreate, user_id: str = Depends(get_user_id)):\n"
                        "    return {\"owner\": user_id, \"title\": payload.title}\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Gestion d'erreur 404 explicite",
                            "language": "python",
                            "code": (
                                "from fastapi import HTTPException\n\n"
                                "def require_item(repo, item_id: str):\n"
                                "    item = repo.get(item_id)\n"
                                "    if item is None:\n"
                                "        raise HTTPException(status_code=404, detail=\"Élément introuvable\")\n"
                                "    return item"
                            ),
                            "explanation": "Une fonction helper évite de dupliquer la vérification `if item is None` dans chaque endpoint.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-3-2-ex1",
                            "title": "Route POST/GET avec Depends",
                            "difficulty": "pratique",
                            "instructions_markdown": (
                                "Écrivez un `APIRouter` FastAPI avec `POST` retournant `201` et `GET /{id}` renvoyant `404` si absent."
                            ),
                            "starter_code": "from fastapi import APIRouter, HTTPException, status\n",
                            "hints": [
                                "Utilisez `status_code=status.HTTP_201_CREATED` sur la route `POST`.",
                                "Levez `HTTPException(status_code=404, ...)` lorsque la ressource n'existe pas.",
                            ],
                            "expected_concepts": ["APIRouter", "Depends", "HTTPException", "201", "404"],
                        },
                    ],
                },
                {
                    "position": 3,
                    "title": "Programmation asynchrone (async / await) & appels externes",
                    "summary": "Éviter de bloquer l’event loop lors des requêtes réseau et paralléliser avec `asyncio.gather`.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "`async/await` excelle pour les opérations I/O (appels HTTP, requêtes DB asynchrones). "
                        "En revanche, n’appelez jamais `time.sleep()` ou `requests.get()` bloquant dans une coroutine `async def`.\n\n"
                        "```python\n"
                        "import asyncio\n\n"
                        "async def fetch_section(name: str) -> str:\n"
                        "    await asyncio.sleep(0.05)\n"
                        "    return f\"Section {name} prête\"\n\n"
                        "async def load_dashboard() -> list[str]:\n"
                        "    return await asyncio.gather(\n"
                        "        fetch_section(\"tâches\"),\n"
                        "        fetch_section(\"cours\"),\n"
                        "    )\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Appels HTTP asynchrones avec timeout httpx",
                            "language": "python",
                            "code": (
                                "import httpx\n\n"
                                "async def get_status(url: str) -> int:\n"
                                "    async with httpx.AsyncClient(timeout=5.0) as client:\n"
                                "        res = await client.get(url)\n"
                                "        return res.status_code"
                            ),
                            "explanation": "Un `timeout` explicite protège votre backend contre les services tiers bloqués.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-3-3-ex1",
                            "title": "Exécution concurrente avec asyncio.gather",
                            "difficulty": "guide",
                            "instructions_markdown": (
                                "Écrivez deux coroutines `async def` et exécutez-les en parallèle avec `asyncio.gather` en mesurant l'ordre."
                            ),
                            "starter_code": "import asyncio\n",
                            "hints": [
                                "Utilisez `await asyncio.gather(task_a(), task_b())`.",
                                "Expliquez la différence avec deux `await` séquentiels.",
                            ],
                            "expected_concepts": ["async", "await", "asyncio", "gather"],
                        },
                    ],
                },
                {
                    "position": 4,
                    "title": "Tests d'intégration FastAPI avec TestClient",
                    "summary": "Valider contrats HTTP, statuts 201/404/422 et isolation utilisateur automatiquement.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "`TestClient(app)` exécute vos vraies routes FastAPI sans démarrer de serveur réseau.\n\n"
                        "```python\n"
                        "from fastapi.testclient import TestClient\n\n"
                        "def test_create_and_forbid_extra_field(client: TestClient):\n"
                        "    bad = client.post(\"/api/v1/items\", json={\"title\": \"Test\", \"role\": \"admin\"})\n"
                        "    assert bad.status_code == 422\n"
                        "    ok = client.post(\"/api/v1/items\", json={\"title\": \"Test\"})\n"
                        "    assert ok.status_code == 201\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Vérification de l'isolation entre deux comptes",
                            "language": "python",
                            "code": (
                                "def test_isolation(client, headers_a, headers_b):\n"
                                "    created = client.post(\"/items\", json={\"title\": \"Privé\"}, headers=headers_a).json()\n"
                                "    res = client.get(f\"/items/{created['id']}\", headers=headers_b)\n"
                                "    assert res.status_code == 404"
                            ),
                            "explanation": "Un autre utilisateur doit recevoir 404 (ou 403), jamais les données d'autrui.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "py-3-4-ex1",
                            "title": "Suite TestClient CRUD + validation 422",
                            "difficulty": "pratique",
                            "instructions_markdown": (
                                "Rédigez un test `TestClient` vérifiant création `201`, lecture `200` et rejet `422`."
                            ),
                            "starter_code": "from fastapi.testclient import TestClient\n",
                            "hints": [
                                "Testez `client.post(...)` avec payload valide (`201`) puis invalide (`422`).",
                                "Vérifiez le corps JSON retourné avec `.json()`.",
                            ],
                            "expected_concepts": ["TestClient", "201", "422", "assert"],
                        },
                    ],
                },
            ],
            "project_title": "Mini-API REST FastAPI testée de bout en bout (Pydantic v2 + TestClient)",
            "project_brief": (
                "### Contexte du projet Niveau 3\n\n"
                "Créez une API FastAPI complète (ex. gestion de notes de cours ou fiches de révision) avec validation Pydantic v2 stricte, "
                "codes HTTP conformes et tests d'intégration `TestClient`.\n\n"
                "### Exigences techniques\n"
                "1. Modèles Pydantic avec `extra='forbid'` et validateurs explicites.\n"
                "2. Endpoints `GET`, `POST` (201), `PATCH`, `DELETE` (204) et gestion `404`.\n"
                "3. Tests `TestClient` couvrant succès, rejet `422` et erreur `404`."
            ),
            "project_deliverables": [
                "Schémas Pydantic v2 avec `extra='forbid'`",
                "Routeur FastAPI CRUD complet",
                "Suite de tests `TestClient` vérifiant 201, 404 et 422",
            ],
        },
        4: {
            "title": "Niveau 4 — SQLAlchemy 2, Alembic réversible, PostgreSQL & indexation",
            "summary": "Modéliser des schémas relationnels robustes, transactions sûres et migrations réversibles.",
            "objectives": [
                "Concevoir des modèles SQLAlchemy 2.0 typés avec clés étrangères et contraintes CHECK",
                "Écrire des migrations Alembic réversibles (`upgrade`/`downgrade`) sans perte de données",
                "Éviter les problèmes N+1 et choisir des index adaptés aux requêtes fréquentes",
                "Encapsuler les mutations multi-tables dans une transaction atomique",
            ],
            "lessons": [
                {
                    "position": 1,
                    "title": "Modèles SQLAlchemy 2.0 et contraintes d'intégrité",
                    "summary": "Garantir les invariants métier directement dans PostgreSQL via CheckConstraint et Index.",
                    "estimated_minutes": 30,
                    "content_markdown": "Utilisez `Mapped[...]` et `mapped_column(...)` avec `CheckConstraint` pour empêcher toute donnée incohérente même hors API.",
                    "code_examples": [
                        {
                            "title": "Table ORM avec contrainte CHECK et index",
                            "language": "python",
                            "code": (
                                "from sqlalchemy import CheckConstraint, Index, Integer, String\n"
                                "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\n\n"
                                "class Base(DeclarativeBase):\n    pass\n\n"
                                "class CourseRow(Base):\n"
                                "    __tablename__ = 'courses'\n"
                                "    __table_args__ = (\n"
                                "        CheckConstraint('current_level BETWEEN 1 AND 5', name='ck_level'),\n"
                                "        Index('ix_courses_owner', 'owner_id'),\n"
                                "    )\n"
                                "    id: Mapped[str] = mapped_column(String(36), primary_key=True)\n"
                                "    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)\n"
                                "    current_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)"
                            ),
                            "explanation": "La base refuse toute insertion hors [1, 5] quel que soit le point d'entrée.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "py-4-1-ex1",
                            "title": "Modèle ORM contraint + index composite",
                            "difficulty": "pratique",
                            "instructions_markdown": "Écrivez une classe SQLAlchemy 2 avec `CheckConstraint` sur `score` (0..100) et `Index` sur `user_id`.",
                            "starter_code": "from sqlalchemy import CheckConstraint, Integer\n",
                            "hints": ["Déclarez `__table_args__ = (CheckConstraint(...), Index(...))`."],
                            "expected_concepts": ["CheckConstraint", "Mapped", "Index"],
                        }
                    ],
                },
                {
                    "position": 2,
                    "title": "Transactions atomiques et rollback sûr",
                    "summary": "Ne jamais laisser d'écriture partielle en base lors d'une opération composée.",
                    "estimated_minutes": 25,
                    "content_markdown": "Utilisez `flush()` pendant les étapes intermédiaires puis un unique `commit()`, ou `with session.begin():`, afin qu'une erreur annule tout le bloc.",
                    "code_examples": [
                        {
                            "title": "Unité de travail atomique avec rollback",
                            "language": "python",
                            "code": (
                                "def approve_and_bump(db, skill_row, assessment_row):\n"
                                "    try:\n"
                                "        assessment_row.status = 'approved'\n"
                                "        skill_row.current_level += 1\n"
                                "        db.commit()\n"
                                "    except Exception:\n"
                                "        db.rollback()\n"
                                "        raise"
                            ),
                            "explanation": "En cas d'exception, aucune modification partielle n'est conservée.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "py-4-2-ex1",
                            "title": "Mutation conditionnelle + rollback",
                            "difficulty": "pratique",
                            "instructions_markdown": "Implémentez une fonction Python effectuant deux mises à jour SQLAlchemy avec `try/except/rollback`.",
                            "starter_code": "def transfer_state(db, src, dst):\n    pass\n",
                            "hints": ["Appelez `db.rollback()` avant `raise` dans `except Exception:`."],
                            "expected_concepts": ["commit", "rollback", "try", "except"],
                        }
                    ],
                },
                {
                    "position": 3,
                    "title": "Migrations Alembic réversibles",
                    "summary": "Faire évoluer le schéma PostgreSQL et SQLite sans casser les données existantes.",
                    "estimated_minutes": 25,
                    "content_markdown": "Chaque migration doit définir `upgrade()` et `downgrade()`, fournir des valeurs par défaut aux nouvelles colonnes NOT NULL et être testée en aller-retour.",
                    "code_examples": [
                        {
                            "title": "Ajout de colonne avec batch_alter_table",
                            "language": "python",
                            "code": (
                                "from alembic import op\n"
                                "import sqlalchemy as sa\n\n"
                                "def upgrade():\n"
                                "    op.add_column('courses', sa.Column('revision', sa.Integer(), nullable=False, server_default='1'))\n\n"
                                "def downgrade():\n"
                                "    op.drop_column('courses', 'revision')"
                            ),
                            "explanation": "`server_default` évite d'échouer sur les lignes déjà présentes.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "py-4-3-ex1",
                            "title": "Migration upgrade/downgrade propre",
                            "difficulty": "pratique",
                            "instructions_markdown": "Écrivez les fonctions `upgrade()` et `downgrade()` Alembic ajoutant un champ indexé sans casser les données.",
                            "starter_code": "from alembic import op\nimport sqlalchemy as sa\n",
                            "hints": ["Créez l'index dans `upgrade` et supprimez-le avant `drop_column` dans `downgrade`."],
                            "expected_concepts": ["op.add_column", "op.drop_column", "upgrade", "downgrade"],
                        }
                    ],
                },
                {
                    "position": 4,
                    "title": "Requêtes efficaces et prévention du N+1",
                    "summary": "Regrouper les lectures et vérifier le coût réel des requêtes.",
                    "estimated_minutes": 25,
                    "content_markdown": "Chargez les relations par lot (`selectinload` ou requête `WHERE id IN (...)`) au lieu d'exécuter une requête SQL par élément dans une boucle.",
                    "code_examples": [
                        {
                            "title": "Regroupement par dictionnaire en Python",
                            "language": "python",
                            "code": (
                                "by_course = {}\n"
                                "for lesson in all_lessons:\n"
                                "    by_course.setdefault(lesson.course_id, []).append(lesson)"
                            ),
                            "explanation": "Une seule requête SQL suffit pour alimenter tous les résumés.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "py-4-4-ex1",
                            "title": "Indexation en mémoire O(n) vs N+1",
                            "difficulty": "defi",
                            "instructions_markdown": "Écrivez une fonction Python qui regroupe des leçons par `level_id` en O(n) et calcule le taux de complétion.",
                            "starter_code": "def summarize_levels(lessons: list[dict]) -> dict[str, float]:\n    pass\n",
                            "hints": ["Groupez avec un dictionnaire intermédiaire puis calculez `completed / total`."],
                            "expected_concepts": ["dict", "return", "for"],
                        }
                    ],
                },
            ],
            "project_title": "Couche de persistance Python SQLAlchemy 2 + Alembic testée (CRUD & transactions)",
            "project_brief": "### Contexte\nConstruisez un dépôt SQLAlchemy 2.0 complet avec contraintes CHECK, index, transaction atomique rollback-safe et test d'aller-retour Alembic.",
            "project_deliverables": [
                "Modèles ORM contraints avec clés étrangères et index",
                "Opération transactionnelle atomique avec test de rollback",
                "Script Alembic réversible testé (`upgrade` / `downgrade`)",
            ],
        },
        5: {
            "title": "Niveau 5 — Architecture sécurisée, observabilité & mise en production Python",
            "summary": "Concevoir un service Python durci : chiffrement AEAD, SSRF-safe HTTP, limitation de débit et tests de non-régression.",
            "objectives": [
                "Protéger les secrets avec chiffrement authentifié (AES-GCM) et zéro fuite dans les logs",
                "Valider toutes les URL sortantes contre le SSRF et gérer les timeouts/redirections",
                "Structurer des tests d'architecture, de sécurité et de performance reproductibles",
            ],
            "lessons": [
                {
                    "position": 1,
                    "title": "Chiffrement authentifié AES-256-GCM des secrets",
                    "summary": "Protéger les clés tierces au repos avec nonce unique et données associées (AAD).",
                    "estimated_minutes": 30,
                    "content_markdown": "Ne stockez jamais de secret tiers en clair : utilisez AES-256-GCM avec nonce aléatoire de 12 octets et l'identifiant propriétaire en AAD.",
                    "code_examples": [
                        {
                            "title": "Enveloppe chiffrée versionnée avec AESGCM",
                            "language": "python",
                            "code": (
                                "import os\nfrom cryptography.hazmat.primitives.ciphers.aead import AESGCM\n\n"
                                "def seal(key: bytes, secret: str, aad: bytes) -> bytes:\n"
                                "    nonce = os.urandom(12)\n"
                                "    return nonce + AESGCM(key).encrypt(nonce, secret.encode('utf-8'), aad)"
                            ),
                            "explanation": "L'AAD lie le texte chiffré à un utilisateur précis pour empêcher toute substitution de ligne en base.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "py-5-1-ex1",
                            "title": "Fail-closed si clé de chiffrement absente",
                            "difficulty": "pratique",
                            "instructions_markdown": "Écrivez un wrapper Python qui refuse de chiffrer si la variable d'environnement est vide au lieu de stocker en clair.",
                            "starter_code": "def encrypt_or_fail(master_key: str, secret: str) -> str:\n    pass\n",
                            "hints": ["Levez `ValueError` ou `RuntimeError` si `not master_key.strip()`."],
                            "expected_concepts": ["raise", "ValueError", "len"],
                        }
                    ],
                },
                {
                    "position": 2,
                    "title": "Client HTTP sortant SSRF-safe",
                    "summary": "Bloquer IP privées, métadonnées cloud, redirections 3xx et réponses géantes.",
                    "estimated_minutes": 30,
                    "content_markdown": "Toute URL fournie par un utilisateur doit être parsée, limitée à HTTPS, vérifiée contre les plages privées/loopback/link-local après résolution DNS, et appelée sans suivre les redirections.",
                    "code_examples": [
                        {
                            "title": "Filtrage ipaddress sur IP résolue",
                            "language": "python",
                            "code": (
                                "import ipaddress\n\n"
                                "def is_safe_public_ip(raw_ip: str) -> bool:\n"
                                "    ip = ipaddress.ip_address(raw_ip)\n"
                                "    return ip.is_global and not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)"
                            ),
                            "explanation": "Bloque aussi 169.254.169.254 et les adresses loopback IPv4/IPv6.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "py-5-2-ex1",
                            "title": "Validateur d'URL sortante",
                            "difficulty": "defi",
                            "instructions_markdown": "Écrivez une fonction Python rejetant `http://`, `@`, query strings et IP privées avec `ipaddress`.",
                            "starter_code": "from urllib.parse import urlparse\nimport ipaddress\n",
                            "hints": ["Vérifiez `parsed.scheme == 'https'`, `not parsed.username`, et testez `ip.is_global`."],
                            "expected_concepts": ["urlparse", "ipaddress", "https", "raise"],
                        }
                    ],
                },
                {
                    "position": 3,
                    "title": "Observabilité, request_id et erreurs propres",
                    "summary": "Corréler chaque erreur sans jamais exposer de trace ni secret au client.",
                    "estimated_minutes": 25,
                    "content_markdown": "Générez un `request_id` unique par requête, loguez les erreurs internes côté serveur et renvoyez un contrat JSON uniforme sans stacktrace.",
                    "code_examples": [
                        {
                            "title": "Contrat d'erreur normalisé",
                            "language": "python",
                            "code": (
                                "def format_error(code: str, message: str, request_id: str) -> dict:\n"
                                "    return {'error': {'code': code, 'message': message, 'request_id': request_id}}"
                            ),
                            "explanation": "Facilite le support tout en protégeant les détails internes.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "py-5-3-ex1",
                            "title": "Sanitisation de logs sans secret",
                            "difficulty": "pratique",
                            "instructions_markdown": "Écrivez une fonction Python masquant toute clé `sk-...` ou `Bearer ...` dans un message d'erreur.",
                            "starter_code": "import re\ndef redact_secrets(text: str) -> str:\n    pass\n",
                            "hints": ["Utilisez `re.sub` pour remplacer les jetons sensibles par `[REDACTED]`."],
                            "expected_concepts": ["re.sub", "return"],
                        }
                    ],
                },
                {
                    "position": 4,
                    "title": "Checklist sécurité & tests de non-régression",
                    "summary": "Automatiser les preuves de sécurité avant déploiement.",
                    "estimated_minutes": 25,
                    "content_markdown": "Chaque règle critique (isolation multi-tenant, absence de fuite de clé, rejet des entrées falsifiées) doit avoir un test Pytest dédié.",
                    "code_examples": [
                        {
                            "title": "Assertion de non-régression IDOR",
                            "language": "python",
                            "code": (
                                "def assert_isolated(status_code: int) -> None:\n"
                                "    assert status_code in (403, 404)"
                            ),
                            "explanation": "Empêche toute régression silencieuse d'accès cross-tenant.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "py-5-4-ex1",
                            "title": "Suite de garde-fous production",
                            "difficulty": "defi",
                            "instructions_markdown": "Écrivez une fonction Python `check_prod_config(env, secret, allow_local)` qui lève une erreur sur configuration faible.",
                            "starter_code": "def check_prod_config(env: str, secret: str, allow_local: bool) -> None:\n    pass\n",
                            "hints": ["En `env == 'production'`, interdisez `allow_local` et exigez `len(secret) >= 32`."],
                            "expected_concepts": ["production", "len", "raise"],
                        }
                    ],
                },
            ],
            "project_title": "Service Python durci prêt pour la production (chiffrement, SSRF, garde-fous & suite Pytest)",
            "project_brief": "### Contexte\nAssemblez un mini-service Python production combinant stockage chiffré de configuration, validation SSRF, garde-fous de démarrage et suite complète de tests Pytest.",
            "project_deliverables": [
                "Chiffrement AEAD fail-closed testé",
                "Validateur SSRF et masquage strict des secrets",
                "Tests Pytest nominaux et adversariaux passants",
            ],
        },
    }


def get_typescript_levels() -> dict[int, dict[str, Any]]:
    return {
        1: {
            "title": "Niveau 1 — Typage statique sûr, unions et fonctions TypeScript",
            "summary": "Maîtriser les annotations essentielles, interfaces, unions discriminées et le narrowing.",
            "objectives": [
                "Typer variables, fonctions et objets avec `interface` / `type` sans recourir à `any`",
                "Modéliser des états impossibles avec des unions littérales et discriminées",
                "Appliquer le rétrécissement de type (`narrowing`) sur `unknown` et `null`",
                "Manipuler tableaux typés avec `map`, `filter` et `reduce`",
            ],
            "lessons": [
                {
                    "position": 1,
                    "title": "Types primitifs, interfaces et rejet de `any`",
                    "summary": "Protéger vos données dès la compilation grâce aux annotations strictes et à `unknown`.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "TypeScript vérifie la cohérence des types **avant même d'exécuter le code**. "
                        "Le principe fondamental est d’éviter `any` (qui désactive le compilateur) et de lui préférer `unknown`.\n\n"
                        "```typescript\n"
                        "interface CourseSummary {\n"
                        "  readonly id: string;\n"
                        "  title: string;\n"
                        "  level: number;\n"
                        "  tags: string[];\n"
                        "}\n\n"
                        "function formatSummary(course: CourseSummary): string {\n"
                        "  return `${course.title} (Niveau ${course.level})`;\n"
                        "}\n"
                        "```\n\n"
                        "| Type | Quand l'utiliser ? | Sécurité |\n"
                        "| --- | --- | --- |\n"
                        "| `string` / `number` | Données connues | Élevée |\n"
                        "| `unknown` | Entrées JSON/API non vérifiées | Oblige à tester |\n"
                        "| `any` | À bannir | Aucune |\n\n"
                        "> **Piège fréquent :** Toujours vérifier `typeof value === 'string'` avant d'appeler `.trim()` sur une valeur `unknown`."
                    ),
                    "code_examples": [
                        {
                            "title": "Interface stricte et transformation immuable",
                            "language": "typescript",
                            "code": (
                                "interface TaskItem {\n"
                                "  id: string;\n"
                                "  title: string;\n"
                                "  done: boolean;\n"
                                "}\n\n"
                                "const toggleTask = (task: TaskItem): TaskItem => ({\n"
                                "  ...task,\n"
                                "  done: !task.done,\n"
                                "});"
                            ),
                            "explanation": "La fonction fléchée renvoie une nouvelle copie sans muter l'objet reçu.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-1-1-ex1",
                            "title": "Typage strict d'un catalogue d'exercices",
                            "difficulty": "guide",
                            "instructions_markdown": (
                                "Définissez une `interface ExerciseItem` et une fonction `countPassed(items: ExerciseItem[]): number` typée sans `any`."
                            ),
                            "starter_code": "interface ExerciseItem {\n  id: string;\n  score: number;\n}\n",
                            "hints": [
                                "Utilisez `.filter((item) => item.score >= 70).length`.",
                                "Indiquez explicitement `: number` comme type de retour.",
                            ],
                            "expected_concepts": ["interface", "number", "filter", "type"],
                        },
                    ],
                },
                {
                    "position": 2,
                    "title": "Unions discriminées et exhaustivité avec `switch`",
                    "summary": "Rendre les états invalides impossibles à représenter dans vos interfaces et stores.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Plutôt que d’avoir `{ loading: boolean; error?: string; data?: T }` où tout peut être vrai en même temps, "
                        "utilisez une **union discriminée**.\n\n"
                        "```typescript\n"
                        "type AsyncState<T> =\n"
                        "  | { status: 'loading' }\n"
                        "  | { status: 'error'; message: string }\n"
                        "  | { status: 'ready'; data: T };\n\n"
                        "function renderStatus(state: AsyncState<string[]>): string {\n"
                        "  switch (state.status) {\n"
                        "    case 'loading': return 'Chargement…';\n"
                        "    case 'error': return state.message;\n"
                        "    case 'ready': return `${state.data.length} éléments`;\n"
                        "  }\n"
                        "}\n"
                        "```\n\n"
                        "> **Bonnes pratiques :** Le compilateur connaît automatiquement les propriétés disponibles dans chaque `case`."
                    ),
                    "code_examples": [
                        {
                            "title": "Guard exhaustif avec `never`",
                            "language": "typescript",
                            "code": (
                                "function assertNever(x: never): never {\n"
                                "  throw new Error(`Cas non géré : ${String(x)}`);\n"
                                "}"
                            ),
                            "explanation": "Si vous ajoutez une variante à l’union et oubliez un `case`, TypeScript échoue à la compilation.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-1-2-ex1",
                            "title": "État de correction en union discriminée",
                            "difficulty": "pratique",
                            "instructions_markdown": (
                                "Modélisez un type `GradingResult` (`pending`, `passed`, `failed`) et écrivez une fonction `formatVerdict` avec `switch`."
                            ),
                            "starter_code": "type GradingResult = { status: 'pending' } | { status: 'passed'; score: number } | { status: 'failed'; reason: string };\n",
                            "hints": [
                                "Branchez sur `result.status` avec un `switch`.",
                                "Accédez à `result.score` uniquement dans `case 'passed'`.",
                            ],
                            "expected_concepts": ["type", "switch", "status", "union"],
                        },
                    ],
                },
                {
                    "position": 3,
                    "title": "Type Guards et narrowing de données externes",
                    "summary": "Transformer `unknown` en type sûr via des prédicats `is` et vérifications explicites.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Les données venues de `localStorage` ou d'une API sont non fiables (`unknown`). "
                        "Un **prédicat de type** (`val is User`) certifie la structure au runtime.\n\n"
                        "```typescript\n"
                        "function isNonEmptyString(value: unknown): value is string {\n"
                        "  return typeof value === 'string' && value.trim().length > 0;\n"
                        "}\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Lecture sûre depuis JSON.parse",
                            "language": "typescript",
                            "code": (
                                "function extractTitle(raw: unknown): string {\n"
                                "  if (typeof raw === 'object' && raw !== null && 'title' in raw && typeof raw.title === 'string') {\n"
                                "    return raw.title;\n"
                                "  }\n"
                                "  return 'Sans titre';\n"
                                "}"
                            ),
                            "explanation": "Vérifier `raw !== null` puis `'title' in raw` évite tout crash runtime.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-1-3-ex1",
                            "title": "Prédicat de type pour réponse API",
                            "difficulty": "guide",
                            "instructions_markdown": (
                                "Écrivez un prédicat `isCoursePayload(val: unknown): val is { title: string; level: number }`."
                            ),
                            "starter_code": "function isCoursePayload(val: unknown): val is { title: string; level: number } {\n  return false;\n}\n",
                            "hints": [
                                "Vérifiez `typeof val === 'object' && val !== null`.",
                                "Castez vers `Record<string, unknown>` après vérification puis testez `typeof` sur `title` et `level`.",
                            ],
                            "expected_concepts": ["unknown", "typeof", "is", "null"],
                        },
                    ],
                },
                {
                    "position": 4,
                    "title": "Collections typées, `Record`, `Pick` et `Omit`",
                    "summary": "Composer de nouveaux types sans duplication grâce aux Utility Types.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Ne dupliquez jamais vos interfaces : dérivez vos formulaires et mises à jour avec `Partial<T>`, `Pick<T, K>` et `Omit<T, K>`.\n\n"
                        "```typescript\n"
                        "interface Project {\n"
                        "  id: string;\n"
                        "  name: string;\n"
                        "  status: 'active' | 'done';\n"
                        "}\n"
                        "type ProjectCreate = Omit<Project, 'id'>;\n"
                        "const labels: Record<Project['status'], string> = { active: 'Actif', done: 'Terminé' };\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Dictionnaire exhaustif avec Record",
                            "language": "typescript",
                            "code": (
                                "type Lang = 'fr' | 'en';\n"
                                "const LANG_LABEL: Record<Lang, string> = { fr: 'Français', en: 'Anglais' };"
                            ),
                            "explanation": "`Record<Lang, string>` garantit qu'aucune langue n'est oubliée dans la table d'affichage.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-1-4-ex1",
                            "title": "Dérivation de types sans duplication",
                            "difficulty": "pratique",
                            "instructions_markdown": (
                                "À partir d’une `interface Course`, créez `CourseDraft = Omit<Course, 'id'>` et un `Record<CourseStatus, string>`."
                            ),
                            "starter_code": "type CourseStatus = 'active' | 'paused' | 'completed';\n",
                            "hints": [
                                "Utilisez `Omit<Course, 'id'>` pour le payload de création.",
                                "Associez chaque statut à son libellé dans `Record<CourseStatus, string>`.",
                            ],
                            "expected_concepts": ["Omit", "Record", "interface", "type"],
                        },
                    ],
                },
            ],
            "project_title": "Moteur typé de suivi de progression de cours en TypeScript strict",
            "project_brief": (
                "### Contexte du projet Niveau 1\n\n"
                "Concevez un module TypeScript (compilable avec `strict: true`, zéro `any`) modélisant un catalogue de cours "
                "à états discriminés, filtrage typé et calcul d’avancement.\n\n"
                "### Exigences\n"
                "1. Modèles `Course`, `Level`, `SubmissionResult` en unions discriminées.\n"
                "2. Garde de type `unknown` validant un import JSON.\n"
                "3. Fonctions pures de filtrage et calcul du taux d’avancement avec gestion des cas limites (0 leçon)."
            ),
            "project_deliverables": [
                "Types stricts avec unions discriminées et `Record`",
                "Prédicat de validation `unknown -> T`",
                "Fonctions pures testées sur cas nominal et tableau vide",
            ],
        },
        2: {
            "title": "Niveau 2 — Génériques, types conditionnels et programmation asynchrone",
            "summary": "Rendre vos utilitaires réutilisables avec `<T>`, sécuriser `fetch` et gérer les promesses typées.",
            "objectives": [
                "Écrire des fonctions et classes génériques contraintes (`<T extends ...>`)",
                "Typer proprement les appels `async/await` et résultats d'erreur sans `try/catch` opaque",
                "Utiliser les génériques pour des repositories ou clients API réutilisables",
            ],
            "lessons": [
                {
                    "position": 1,
                    "title": "Fonctions et interfaces génériques contraintes",
                    "summary": "Paramétrer des structures de données et fonctions sans perdre l’autocomplétion.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Les génériques `<T>` capturent le type exact manipulé à l'appel.\n\n"
                        "```typescript\n"
                        "function groupBy<T, K extends string>(items: T[], getKey: (item: T) => K): Record<string, T[]> {\n"
                        "  const acc: Record<string, T[]> = {};\n"
                        "  for (const item of items) {\n"
                        "    const k = getKey(item);\n"
                        "    (acc[k] ??= []).push(item);\n"
                        "  }\n"
                        "  return acc;\n"
                        "}\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Enveloppe Result<T, E> générique",
                            "language": "typescript",
                            "code": (
                                "type Result<T, E = string> =\n"
                                "  | { ok: true; value: T }\n"
                                "  | { ok: false; error: E };"
                            ),
                            "explanation": "Force l'appelant à inspecter `res.ok` avant de lire `res.value`.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-2-1-ex1",
                            "title": "Helper générique indexById",
                            "difficulty": "guide",
                            "instructions_markdown": (
                                "Implémentez `indexById<T extends { id: string }>(items: T[]): Map<string, T>`."
                            ),
                            "starter_code": "function indexById<T extends { id: string }>(items: T[]): Map<string, T> {\n  return new Map();\n}\n",
                            "hints": [
                                "Parcourez `items` avec `for (const item of items)` et appelez `map.set(item.id, item)`.",
                            ],
                            "expected_concepts": ["<T extends", "Map", "id", "return"],
                        },
                    ],
                },
                {
                    "position": 2,
                    "title": "Client HTTP générique et validation runtime",
                    "summary": "Garantir que les réponses réseau correspondent bien aux types TypeScript déclarés.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "`await res.json() as MyType` est dangereux si le serveur change : couplez `Promise<T>` avec une fonction de validation.\n\n"
                        "```typescript\n"
                        "async function fetchJson<T>(url: string, guard: (raw: unknown) => T): Promise<T> {\n"
                        "  const res = await fetch(url);\n"
                        "  if (!res.ok) throw new Error(`HTTP ${res.status}`);\n"
                        "  const raw: unknown = await res.json();\n"
                        "  return guard(raw);\n"
                        "}\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Gestion propre d'AbortController",
                            "language": "typescript",
                            "code": (
                                "async function fetchWithTimeout(url: string, ms = 5000): Promise<Response> {\n"
                                "  const controller = new AbortController();\n"
                                "  const id = setTimeout(() => controller.abort(), ms);\n"
                                "  try {\n"
                                "    return await fetch(url, { signal: controller.signal });\n"
                                "  } finally {\n"
                                "    clearTimeout(id);\n"
                                "  }\n"
                                "}"
                            ),
                            "explanation": "`finally` garantit le nettoyage du timer même si `fetch` échoue.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-2-2-ex1",
                            "title": "Wrapper API typé avec Promise<Result<T>>",
                            "difficulty": "pratique",
                            "instructions_markdown": (
                                "Écrivez une fonction `safeFetch<T>` qui retourne `{ ok: true, data: T }` ou `{ ok: false, error: string }`."
                            ),
                            "starter_code": "async function safeFetch<T>(url: string): Promise<{ ok: true; data: T } | { ok: false; error: string }> {\n  throw new Error('todo');\n}\n",
                            "hints": [
                                "Entourez `await fetch(url)` d'un `try/catch` et vérifiez `res.ok`.",
                            ],
                            "expected_concepts": ["async", "Promise", "fetch", "try", "catch"],
                        },
                    ],
                },
                {
                    "position": 3,
                    "title": "Invariance, `readonly` et immutabilité stricte",
                    "summary": "Prévenir les mutations accidentelles dans les états React ou Redux.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "`ReadonlyArray<T>` (ou `readonly T[]`) empêche `.push()` ou `.sort()` en place directement au compile-time.\n\n"
                        "```typescript\n"
                        "function sortedCopy(nums: readonly number[]): number[] {\n"
                        "  return [...nums].sort((a, b) => a - b);\n"
                        "}\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Copie triée sans muter la source",
                            "language": "typescript",
                            "code": "const addTag = (tags: readonly string[], next: string): string[] => [...tags, next];",
                            "explanation": "L'opérateur spread crée un nouveau tableau sans toucher à l'entrée.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-2-3-ex1",
                            "title": "Mise à jour immuable d'une liste typée",
                            "difficulty": "guide",
                            "instructions_markdown": (
                                "Écrivez `markCompleted(lessons: readonly Lesson[], id: string): Lesson[]` sans modifier le tableau d'entrée."
                            ),
                            "starter_code": "interface Lesson { id: string; done: boolean; }\n",
                            "hints": ["Utilisez `.map((l) => (l.id === id ? { ...l, done: true } : l))`."],
                            "expected_concepts": ["readonly", "map", "spread", "return"],
                        },
                    ],
                },
                {
                    "position": 4,
                    "title": "Tests unitaires Vitest avec typage strict",
                    "summary": "Vérifier fonctions génériques, promesses rejetées et mocks typés.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Vitest exécute vos tests TypeScript nativement à haute vitesse.\n\n"
                        "```typescript\n"
                        "import { describe, expect, it } from 'vitest';\n\n"
                        "describe('groupBy', () => {\n"
                        "  it('regroupe par clé', () => {\n"
                        "    const res = groupBy([{ d: 'BE', n: 'API' }], (x) => x.d);\n"
                        "    expect(res.BE).toHaveLength(1);\n"
                        "  });\n"
                        "});\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Test asynchrone avec rejects",
                            "language": "typescript",
                            "code": "await expect(fetchJson('/bad', (x) => x)).rejects.toThrow();",
                            "explanation": "`rejects.toThrow()` vérifie que la promesse échoue proprement.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-2-4-ex1",
                            "title": "Test Vitest d'un helper générique",
                            "difficulty": "pratique",
                            "instructions_markdown": "Écrivez un test `describe`/`it` couvrant cas nominal et tableau vide.",
                            "starter_code": "import { describe, expect, it } from 'vitest';\n",
                            "hints": ["Testez avec `expect(...).toEqual(...)`."],
                            "expected_concepts": ["describe", "it", "expect"],
                        },
                    ],
                },
            ],
            "project_title": "Mini-client REST & Cache typé avec génériques + tests Vitest",
            "project_brief": (
                "### Contexte du projet Niveau 2\n\n"
                "Développez un client HTTP générique `ApiClient` supportant le typage strict des réponses, "
                "des résultats `Result<T, E>` et des tests Vitest sans `any`."
            ),
            "project_deliverables": [
                "Client générique avec validation `guard(unknown)`",
                "Gestion d'erreur typée via `Result<T, E>`",
                "Tests Vitest couvrant succès, HTTP 500 et timeout",
            ],
        },
        3: {
            "title": "Niveau 3 — Patterns avancés, inférence et architecture full-stack",
            "summary": "Maîtriser `infer`, types mappés, schémas partagés Zod et architecture propre d'application.",
            "objectives": [
                "Combiner TypeScript et Zod pour partager contrats runtime et types statiques (`z.infer`)",
                "Construire des types mappés et conditionnels lisibles sans sur-ingénierie",
                "Organiser un module frontend maintenable avec séparation API / Store / UI",
            ],
            "lessons": [
                {
                    "position": 1,
                    "title": "Contrats uniques avec Zod et z.infer",
                    "summary": "Éviter la dérive entre validation de formulaire et type TypeScript.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Avec `z.infer<typeof schema>`, la définition Zod devient la source de vérité unique.\n\n"
                        "```typescript\n"
                        "import { z } from 'zod';\n\n"
                        "const courseSchema = z.object({\n"
                        "  subject: z.string().trim().min(2),\n"
                        "  totalLevels: z.number().int().min(2).max(5),\n"
                        "});\n"
                        "type CourseInput = z.infer<typeof courseSchema>;\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Validation de formulaire avec extraction d'erreurs",
                            "language": "typescript",
                            "code": "const parsed = courseSchema.safeParse({ subject: 'Python', totalLevels: 3 });",
                            "explanation": "`safeParse` ne lève pas d'exception et retourne un objet discriminé `success`.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-3-1-ex1",
                            "title": "Schéma Zod + type inféré",
                            "difficulty": "guide",
                            "instructions_markdown": "Créez un schéma Zod `resourceSchema` validant une URL http(s) et inférez son type.",
                            "starter_code": "import { z } from 'zod';\n",
                            "hints": ["Utilisez `.refine((v) => v.startsWith('http://') || v.startsWith('https://'))`."],
                            "expected_concepts": ["z.object", "z.infer", "safeParse"],
                        },
                    ],
                },
                {
                    "position": 2,
                    "title": "Types mappés et littéraux gabarits",
                    "summary": "Automatiser les tables de métadonnées et événements typés.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Les template literal types expriment des conventions strictes comme `` `on${Capitalize<Event>}` ``.\n\n"
                        "```typescript\n"
                        "type ActionKind = 'create' | 'update';\n"
                        "type EventName = `course:${ActionKind}`;\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Dictionnaire de métadonnées garanti",
                            "language": "typescript",
                            "code": (
                                "type LevelState = 'locked' | 'unlocked' | 'validated';\n"
                                "const LABELS: Record<LevelState, string> = {\n"
                                "  locked: 'Verrouillé',\n"
                                "  unlocked: 'Débloqué',\n"
                                "  validated: 'Validé',\n"
                                "};"
                            ),
                            "explanation": "Couvre exhaustivement tous les états possibles.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-3-2-ex1",
                            "title": "Événements typés par gabarit",
                            "difficulty": "pratique",
                            "instructions_markdown": "Définissez un type d'événements `lesson:${'start' | 'complete'}` et un handler typé.",
                            "starter_code": "type LessonEvent = `lesson:${'start' | 'complete'}`;\n",
                            "hints": ["Associez chaque événement à un callback dans un `Record`."],
                            "expected_concepts": ["type", "Record", "function"],
                        },
                    ],
                },
                {
                    "position": 3,
                    "title": "Architecture modulaire API + Store React/TanStack",
                    "summary": "Découpler transport réseau, mapping DTO et composants de présentation.",
                    "estimated_minutes": 30,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "Un module propre isole les DTO backend (`snake_case`) dans `api.ts` et expose des types domaine (`camelCase`) aux composants.\n\n"
                        "```typescript\n"
                        "interface ApiCourse { id: string; current_level: number; }\n"
                        "interface Course { id: string; currentLevel: number; }\n"
                        "const mapCourse = (dto: ApiCourse): Course => ({ id: dto.id, currentLevel: dto.current_level });\n"
                        "```"
                    ),
                    "code_examples": [
                        {
                            "title": "Séparation mapper DTO -> Domaine",
                            "language": "typescript",
                            "code": "export type { Course };\nexport { mapCourse };",
                            "explanation": "L'UI n'est jamais couplée aux noms de colonnes SQL.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-3-3-ex1",
                            "title": "Mapper DTO snake_case vers camelCase",
                            "difficulty": "guide",
                            "instructions_markdown": "Écrivez une fonction pure `mapLevelDto` convertissant un DTO backend typé.",
                            "starter_code": "interface ApiLevel { level_number: number; content_generated: boolean; }\n",
                            "hints": ["Retournez `{ levelNumber: dto.level_number, contentGenerated: dto.content_generated }`."],
                            "expected_concepts": ["interface", "return", "map"],
                        },
                    ],
                },
                {
                    "position": 4,
                    "title": "Zéro erreur TypeScript en CI (`tsc -b --noEmit`)",
                    "summary": "Configurer et auditer un projet strict prêt pour la production.",
                    "estimated_minutes": 25,
                    "content_markdown": (
                        "## Objectif du chapitre\n\n"
                        "En mode strict (`noUnusedLocals`, `strictNullChecks`), le compilateur devient un filet de sécurité permanent avant chaque déploiement."
                    ),
                    "code_examples": [
                        {
                            "title": "Garde de nullité sans assertion `!`",
                            "language": "typescript",
                            "code": (
                                "function getActiveTitle(items: { id: string; title: string }[], id: string | null): string {\n"
                                "  if (!id) return 'Aucun';\n"
                                "  return items.find((i) => i.id === id)?.title ?? 'Introuvable';\n"
                                "}"
                            ),
                            "explanation": "Chaînage optionnel `?.` et opérateur nullish `??` remplacent avantageusement `!`.",
                        },
                    ],
                    "exercises": [
                        {
                            "id": "ts-3-4-ex1",
                            "title": "Refactor sans opérateur `!`",
                            "difficulty": "pratique",
                            "instructions_markdown": "Éliminez un cast `as` et un `!` via un narrowing explicite.",
                            "starter_code": "function firstTitle(list: { title: string }[]): string {\n  return list[0]?.title ?? '';\n}\n",
                            "hints": ["Utilisez `?.` et `??` ou une vérification `if (list.length === 0)`."],
                            "expected_concepts": ["??", "?.", "return"],
                        },
                    ],
                },
            ],
            "project_title": "Module domaine TypeScript complet + validation Zod + mapper DTO testé",
            "project_brief": (
                "### Contexte du projet Niveau 3\n\n"
                "Concevez une mini-architecture domaine complète : schémas Zod (`z.infer`), mapper DTO backend, "
                "états discriminés et suite de tests Vitest."
            ),
            "project_deliverables": [
                "Contrats Zod + `z.infer`",
                "Mapper DTO strict sans `any` ni `!`",
                "Suite de tests Vitest passante",
            ],
        },
        4: {
            "title": "Niveau 4 — Types conditionnels, utilitaires et contrats API génériques",
            "summary": "Concevoir des abstractions génériques sûres avec `keyof`, types conditionnels et inférence contrôlée.",
            "objectives": [
                "Composer `Partial`, `Pick`, `Omit`, `Record` et types utilitaires maison",
                "Inférer automatiquement types de retour et signatures d’actions (`infer`, `satisfies`)",
                "Typage strict des clients HTTP génériques et gestion d'erreurs typée",
            ],
            "lessons": [
                {
                    "position": 1,
                    "title": "Contraintes génériques, `keyof` et opérateur `satisfies`",
                    "summary": "Préserver l’inférence littérale tout en validant un contrat de structure.",
                    "estimated_minutes": 30,
                    "content_markdown": "`satisfies` vérifie qu'une constante respecte un type sans écraser ses types littéraux précis.",
                    "code_examples": [
                        {
                            "title": "Lookup typé avec `keyof T`",
                            "language": "typescript",
                            "code": "function pluck<T, K extends keyof T>(obj: T, key: K): T[K] {\n  return obj[key];\n}",
                            "explanation": "Le compilateur garantit que `key` existe réellement sur `obj`.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "ts-4-1-ex1",
                            "title": "Accesseur générique `pickKeys`",
                            "difficulty": "pratique",
                            "instructions_markdown": "Écrivez une fonction TypeScript générique `pickField<T, K extends keyof T>(item: T, key: K): T[K]`.",
                            "starter_code": "function pickField<T, K extends keyof T>(item: T, key: K): T[K] {\n  throw new Error('TODO');\n}\n",
                            "hints": ["Retournez `item[key]`."],
                            "expected_concepts": ["keyof", "extends", "return"],
                        }
                    ],
                },
                {
                    "position": 2,
                    "title": "Client `apiRequest<T>` générique et erreurs typées",
                    "summary": "Standardiser appels réseau, statuts 401/422 et désérialisation sûre.",
                    "estimated_minutes": 30,
                    "content_markdown": "Encapsulez `fetch` dans un client générique qui valide le statut HTTP et lève une erreur métier structurée.",
                    "code_examples": [
                        {
                            "title": "Type résultat sûr Ok | Err",
                            "language": "typescript",
                            "code": "type Result<T, E = string> = { ok: true; value: T } | { ok: false; error: E };",
                            "explanation": "Oblige chaque appelant à traiter l'échec avant de lire `value`.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "ts-4-2-ex1",
                            "title": "Helper Result<T, E> avec narrowing",
                            "difficulty": "pratique",
                            "instructions_markdown": "Implémentez `unwrapOr<T, E>(res: Result<T, E>, fallback: T): T` sans cast `as`.",
                            "starter_code": "type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };\n",
                            "hints": ["Testez `if (res.ok) return res.value; return fallback;`."],
                            "expected_concepts": ["Result", "if", "return"],
                        }
                    ],
                },
                {
                    "position": 3,
                    "title": "Types conditionnels et validation à l'exécution",
                    "summary": "Relier la sûreté statique TypeScript à des gardes de type runtime (`value is T`).",
                    "estimated_minutes": 25,
                    "content_markdown": "Les types TypeScript disparaissent à l'exécution : toute donnée JSON externe doit passer par un type guard `isX(raw): raw is X`.",
                    "code_examples": [
                        {
                            "title": "Prédicat de type utilisateur",
                            "language": "typescript",
                            "code": "function isNonEmptyString(v: unknown): v is string {\n  return typeof v === 'string' && v.trim().length > 0;\n}",
                            "explanation": "Après `if (isNonEmptyString(x))`, TypeScript sait que `x` est `string`.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "ts-4-3-ex1",
                            "title": "Prédicat `isRecord` sur `unknown`",
                            "difficulty": "pratique",
                            "instructions_markdown": "Écrivez un type guard `isPlainRecord(v: unknown): v is Record<string, unknown>` rejetant `null` et tableaux.",
                            "starter_code": "function isPlainRecord(v: unknown): v is Record<string, unknown> {\n  return false;\n}\n",
                            "hints": ["Vérifiez `typeof v === 'object' && v !== null && !Array.isArray(v)`."],
                            "expected_concepts": ["unknown", "isPlainRecord", "Array.isArray"],
                        }
                    ],
                },
                {
                    "position": 4,
                    "title": "Refactorisation de DTO complexes sans `any`",
                    "summary": "Éliminer `any` et assertions dangereuses dans les stores frontend.",
                    "estimated_minutes": 25,
                    "content_markdown": "Utilisez `Readonly<T>`, `Partial<T>` et des mappers purs testables en Vitest.",
                    "code_examples": [
                        {
                            "title": "Patch typé immuable",
                            "language": "typescript",
                            "code": "function mergePatch<T extends object>(base: T, patch: Partial<T>): T {\n  return { ...base, ...patch };\n}",
                            "explanation": "Empêche d'ajouter des clés inconnues lors d'une mise à jour.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "ts-4-4-ex1",
                            "title": "Mapper défensif de réponse API",
                            "difficulty": "defi",
                            "instructions_markdown": "Écrivez une fonction TypeScript qui convertit un objet `unknown` en `{ id: string; score: number }` ou lève une `Error`.",
                            "starter_code": "function parseScoreDto(raw: unknown): { id: string; score: number } {\n  throw new Error('TODO');\n}\n",
                            "hints": ["Validez `typeof obj === 'object' && obj !== null` puis chaque champ avec `typeof`."],
                            "expected_concepts": ["unknown", "typeof", "throw"],
                        }
                    ],
                },
            ],
            "project_title": "SDK TypeScript générique typé + gardes runtime + tests Vitest",
            "project_brief": "### Contexte\nConcevez une mini-bibliothèque SDK TypeScript : `apiRequest<T>`, type `Result<T, E>`, prédicats runtime et suite de tests Vitest sous `tsc --noEmit` strict.",
            "project_deliverables": [
                "Client générique avec erreurs typées et zéro `any`",
                "Prédicats runtime vérifiant les entrées JSON `unknown`",
                "Tests Vitest couvrant succès, erreur et données corrompues",
            ],
        },
        5: {
            "title": "Niveau 5 — Architecture TypeScript stricte, tests de contrat & production",
            "summary": "Garantir fiabilité bout-en-bout entre schéma backend, build Vite/tsc et sécurité client.",
            "objectives": [
                "Concevoir des machines à états typées sans transitions invalides",
                "Auditer la sécurité frontend (aucun jeton en localStorage, validation d'URL)",
                "Maintenir 0 erreur `tsc --noEmit` et un bundle production propre",
            ],
            "lessons": [
                {
                    "position": 1,
                    "title": "Machines à états et transitions sûres",
                    "summary": "Empêcher les états incohérents directement au niveau des types.",
                    "estimated_minutes": 25,
                    "content_markdown": "Modélisez explicitement les transitions autorisées via des signatures discriminées et `assertNever`.",
                    "code_examples": [
                        {
                            "title": "Transition contrôlée de proposition IA",
                            "language": "typescript",
                            "code": "type ProposalStatus = 'pending' | 'executed' | 'rejected';\nfunction canAccept(s: ProposalStatus): boolean {\n  return s === 'pending';\n}",
                            "explanation": "Centralise les règles de transition dans des helpers purs.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "ts-5-1-ex1",
                            "title": "Transition de niveau verrouillée",
                            "difficulty": "pratique",
                            "instructions_markdown": "Écrivez une fonction TypeScript vérifiant les transitions `'locked' -> 'unlocked' -> 'validated'` sans saut direct.",
                            "starter_code": "type LevelStatus = 'locked' | 'unlocked' | 'validated';\n",
                            "hints": ["Utilisez un objet `Record<LevelStatus, LevelStatus[]>`."],
                            "expected_concepts": ["Record", "includes", "return"],
                        }
                    ],
                },
                {
                    "position": 2,
                    "title": "Sécurité côté navigateur : tokens mémoire & URL sûres",
                    "summary": "Éviter XSS token theft et redirections/requêtes non sécurisées.",
                    "estimated_minutes": 30,
                    "content_markdown": "Conservez les jetons d'accès uniquement en mémoire React et validez toute URL externe avant `fetch`.",
                    "code_examples": [
                        {
                            "title": "Validation HTTPS côté client",
                            "language": "typescript",
                            "code": "function assertHttpsUrl(raw: string): URL {\n  const u = new URL(raw);\n  if (u.protocol !== 'https:') throw new Error('HTTPS requis');\n  return u;\n}",
                            "explanation": "Rejette `javascript:`, `data:` et `http://` externes.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "ts-5-2-ex1",
                            "title": "Validateur client d'URL API",
                            "difficulty": "pratique",
                            "instructions_markdown": "Écrivez `validateClientUrl(raw: string): string` autorisant `https:` et rejetant les IP privées `127.`/`10.`/`192.168.`.",
                            "starter_code": "function validateClientUrl(raw: string): string {\n  throw new Error('TODO');\n}\n",
                            "hints": ["Parsez avec `new URL(raw)` puis vérifiez `u.protocol` et `u.hostname`."],
                            "expected_concepts": ["URL", "protocol", "throw"],
                        }
                    ],
                },
                {
                    "position": 3,
                    "title": "Refresh single-flight et résilience HTTP",
                    "summary": "Éviter les courses de jetons lors des requêtes parallèles.",
                    "estimated_minutes": 30,
                    "content_markdown": "Partagez une unique promesse en vol (`inflightRefresh`) quand plusieurs requêtes reçoivent `401` simultanément.",
                    "code_examples": [
                        {
                            "title": "Mutualisation d'appel asynchrone en vol",
                            "language": "typescript",
                            "code": (
                                "let inflight: Promise<string | null> | null = null;\n"
                                "export async function refreshOnce(fn: () => Promise<string | null>): Promise<string | null> {\n"
                                "  if (!inflight) inflight = fn().finally(() => { inflight = null; });\n"
                                "  return inflight;\n}"
                            ),
                            "explanation": "Évite de révoquer la famille de jetons par doubles appels simultanés.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "ts-5-3-ex1",
                            "title": "Verrou single-flight typé",
                            "difficulty": "defi",
                            "instructions_markdown": "Implémentez un helper générique `singleFlight<T>(fn: () => Promise<T>): () => Promise<T>` réinitialisé dans `.finally()`.",
                            "starter_code": "function singleFlight<T>(fn: () => Promise<T>): () => Promise<T> {\n  throw new Error('TODO');\n}\n",
                            "hints": ["Stockez `let pending: Promise<T> | null = null` dans la closure."],
                            "expected_concepts": ["Promise", "finally", "return"],
                        }
                    ],
                },
                {
                    "position": 4,
                    "title": "Tests de contrat et build strict CI",
                    "summary": "Garantir zéro régression de typage et de bundle avant livraison.",
                    "estimated_minutes": 25,
                    "content_markdown": "Associez `tsc --noEmit`, Vitest et `vite build` dans chaque pipeline.",
                    "code_examples": [
                        {
                            "title": "Garde de contrat stricte",
                            "language": "typescript",
                            "code": "const assertPresent = <T>(v: T | null | undefined, msg: string): T => {\n  if (v == null) throw new Error(msg);\n  return v;\n};",
                            "explanation": "Lève une erreur explicite au lieu de propager `undefined`.",
                        }
                    ],
                    "exercises": [
                        {
                            "id": "ts-5-4-ex1",
                            "title": "Assertion typée réutilisable",
                            "difficulty": "pratique",
                            "instructions_markdown": "Écrivez `assertDefined<T>(val: T | null | undefined): T` avec tests nominaux et nul.",
                            "starter_code": "function assertDefined<T>(val: T | null | undefined): T {\n  throw new Error('TODO');\n}\n",
                            "hints": ["Vérifiez `if (val === null || val === undefined) throw new Error(...)`."],
                            "expected_concepts": ["undefined", "throw", "return"],
                        }
                    ],
                },
            ],
            "project_title": "Client applicatif TypeScript production (machines à états, single-flight & validation sécurité)",
            "project_brief": "### Contexte\nConstruisez un module client TypeScript production avec machine à états typée, refresh single-flight sans fuite, validation d'URL et tests Vitest.",
            "project_deliverables": [
                "Machine à états discriminée exhaustive",
                "Refresh single-flight et validation URL sécurisée",
                "Tests Vitest et 0 erreur `tsc --noEmit`",
            ],
        },
    }


def _build_track_levels(
    *,
    prefix: str,
    code_lang: str,
    specs: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    levels: dict[int, dict[str, Any]] = {}
    for lvl_num, spec in specs.items():
        lessons: list[dict[str, Any]] = []
        for idx, ch in enumerate(spec["chapters"], start=1):
            lessons.append(
                {
                    "position": idx,
                    "title": ch["title"],
                    "summary": ch["summary"],
                    "estimated_minutes": ch.get("minutes", 25),
                    "content_markdown": (
                        f"## 1. Objectif pédagogique\n\n{ch['summary']}\n\n"
                        f"### 2. Prérequis & intuition\n\n{ch.get('intuition', 'Appuyez-vous sur des entrées valides et des fonctions courtes.')}\n\n"
                        f"### 3. Explication pas à pas\n\n{ch['explanation']}\n\n"
                        f"### 4. Exemple concret commenté\n\n```{code_lang}\n{ch['code']}\n```\n\n"
                        f"### 5. Cas limites & pièges fréquents\n\n{ch.get('pitfalls', '- Validez les entrées nulles, vides ou hors bornes dès le début.')}\n\n"
                        f"### 6. Bonnes pratiques\n\n{ch['tip']}\n\n"
                        f"### 7. Synthèse à retenir\n\n{ch['summary']}\n\n"
                        f"### 8. Contrôle de compréhension\n\nComplétez l’exercice ci-dessous en justifiant chaque garde."
                    ),
                    "code_examples": [
                        {
                            "title": ch["example_title"],
                            "language": code_lang,
                            "code": ch["code"],
                            "explanation": ch["tip"],
                        }
                    ],
                    "exercises": [
                        {
                            "id": f"{prefix}-{lvl_num}-{idx}-ex1",
                            "title": ch["exercise_title"],
                            "difficulty": "guide" if idx <= 2 else ("defi" if lvl_num >= 4 and idx == 4 else "pratique"),
                            "exercise_type": ch.get("exercise_type", "code"),
                            "instructions_markdown": ch["exercise_prompt"],
                            "starter_code": ch.get("starter", ""),
                            "hints": ch["hints"],
                            "expected_concepts": ch["concepts"],
                            "choices": ch.get("choices", []),
                            "expected_answer": ch.get("expected_answer"),
                        }
                    ],
                }
            )
        levels[lvl_num] = {
            "title": spec["title"],
            "summary": spec["summary"],
            "objectives": spec["objectives"],
            "lessons": lessons,
            "project_title": spec["project_title"],
            "project_brief": spec["project_brief"],
            "project_deliverables": spec["project_deliverables"],
        }
    return levels


def get_javascript_levels() -> dict[int, dict[str, Any]]:
    specs: dict[int, dict[str, Any]] = {
        1: {
            "title": "Niveau 1 — Fondations JavaScript modernes (ES6+, portée et fonctions)",
            "summary": "Maîtriser `let`/`const`, fonctions pures, tableaux (`map`/`filter`/`reduce`) et contrôle des erreurs.",
            "objectives": [
                "Distinguer `const` et `let` et éviter la mutation involontaire d'objets",
                "Manipuler tableaux et objets ES6+ avec `map`, `filter` et destructuration",
                "Valider explicitement les paramètres et lever des `Error` adaptées",
            ],
            "chapters": [
                {
                    "title": "`const`, `let`, types primitifs et comparaisons strictes (`===`)",
                    "summary": "Éviter les conversions implicites trompeuses de JavaScript.",
                    "explanation": "Utilisez `const` par défaut, `let` uniquement en cas de réaffectation, et `===` pour bannir la coercition implicite de `==`.",
                    "code": "function isPassingScore(score) {\n  if (typeof score !== 'number' || Number.isNaN(score)) return false;\n  return score >= 70;\n}",
                    "example_title": "Validation stricte avec typeof et Number.isNaN",
                    "tip": "Vérifiez toujours `typeof x === 'number' && !Number.isNaN(x)` avant un calcul.",
                    "exercise_title": "Validateur d'âge ou note en JS pur",
                    "exercise_prompt": "Écrivez une fonction JavaScript `normalizeScore(raw)` acceptant nombre ou chaîne numérique entre 0 et 100 et levant `RangeError` sinon.",
                    "starter": "function normalizeScore(raw) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Convertissez avec `Number(raw)` puis testez `Number.isFinite(val)`."],
                    "concepts": ["function", "Number.isFinite", "if", "return"],
                },
                {
                    "title": "Tableaux immuables : `map`, `filter` et `reduce`",
                    "summary": "Transformer des collections sans boucle impérative ni mutation.",
                    "explanation": "Contrairement à `.push()` ou `.sort()`, `.map()` et `.filter()` retournent un nouveau tableau sans altérer l'original.",
                    "code": "const passed = submissions.filter((s) => s.score >= 70).map((s) => s.title);",
                    "example_title": "Pipeline filtre + projection",
                    "tip": "Copiez d'abord (`[...items].sort(...)`) avant d'appeler `.sort()` en JavaScript.",
                    "exercise_title": "Calcul de moyenne des séances validées",
                    "exercise_prompt": "Écrivez une fonction JS `averageCompleted(items)` qui filtre `item.done === true` et calcule la moyenne (0 si vide).",
                    "starter": "function averageCompleted(items) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Vérifiez `doneItems.length === 0` pour éviter `0 / 0 === NaN`."],
                    "concepts": ["filter", "reduce", "length", "return"],
                },
                {
                    "title": "Destructuration, valeurs par défaut et opérateur spread (`...`)",
                    "summary": "Écrire du code ES6 concis et protégé contre `undefined`.",
                    "explanation": "Utilisez le chaînage optionnel `?.` et `??` (nullish coalescing) pour ne traiter que `null` et `undefined` (pas `0` ni `false`).",
                    "code": "function formatCourse({ title, level = 1 }) {\n  return `${title} (Niveau ${level})`;\n}",
                    "example_title": "Destructuration avec défaut sûr",
                    "tip": "Préférez `??` à `||` pour une valeur numérique pouvant valoir `0`.",
                    "exercise_title": "Fusion immuable d'options",
                    "exercise_prompt": "Implémentez `mergeConfig(base, override)` sans muter `base` et avec `??` pour les champs numériques.",
                    "starter": "function mergeConfig(base, override) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Utilisez `{ ...base, ...override }` après contrôle `override ?? {}`."],
                    "concepts": ["??", "function", "return"],
                },
                {
                    "title": "Gestion d'erreurs explicite avec `try / catch` et `throw`",
                    "summary": "Transformer JSON ou entrées externes sans plantage silencieux.",
                    "explanation": "Enveloppez `JSON.parse` dans `try / catch` afin de retourner une erreur claire ou un résultat maîtrisé.",
                    "code": "function safeParseJson(raw) {\n  try { return { ok: true, data: JSON.parse(raw) }; } catch (err) { return { ok: false, error: err.message }; }\n}",
                    "example_title": "Parsing JSON défensif",
                    "tip": "Ne capturez jamais une erreur pour l'ignorer sans retour explicite.",
                    "exercise_title": "Parseur JSON sécurisé",
                    "exercise_prompt": "Écrivez `parseCoursePayload(raw)` vérifiant que `raw` est une chaîne non vide puis appelant `JSON.parse` dans `try/catch`.",
                    "starter": "function parseCoursePayload(raw) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Testez `if (typeof raw !== 'string' || !raw.trim())` avant `JSON.parse`."],
                    "concepts": ["try", "catch", "JSON.parse", "return"],
                },
            ],
            "project_title": "Catalogue JavaScript ES6+ de suivi d'exercices (filtrage immuable & gestion d'erreurs)",
            "project_brief": "### Contexte\nImplémentez en JavaScript pur (ES6+) un gestionnaire de fiches d'exercices : ajout validé, calcul de statistiques immuable, import/export JSON défensif et vérifications.",
            "project_deliverables": [
                "Fonctions pures JS sans mutation d'entrée",
                "Gestion explicite de `NaN`, tableaux vides et JSON invalide",
                "Jeu d'assertions de test passant sans erreur",
            ],
        },
        2: {
            "title": "Niveau 2 — Closures, portée lexicale, DOM & événements navigateur",
            "summary": "Comprendre closures, `this`, délégation d'événements DOM et gestion sûre du texte utilisateur.",
            "objectives": [
                "Expliquer portée lexicale et closures pour encapsuler un état privé",
                "Manipuler le DOM proprement avec `textContent` (sans `innerHTML` sur entrées utilisateur)",
                "Utiliser la délégation d'événements pour des interfaces performantes",
            ],
            "chapters": [
                {
                    "title": "Portée lexicale et closures JavaScript",
                    "summary": "Créer des fabriques d'état privé sans variables globales.",
                    "explanation": "Une closure capture les variables de sa fonction englobante même après le retour de celle-ci.",
                    "code": "function createCounter(min = 0) {\n  let value = min;\n  return { inc: () => ++value, get: () => value };\n}",
                    "example_title": "Compteur encapsulé par closure",
                    "tip": "Les closures évitent de polluer `window` avec des variables partagées.",
                    "exercise_title": "Store local encapsulé par closure",
                    "exercise_prompt": "Écrivez `createTaskStore()` retournant `{ add, list }` où la liste interne ne peut pas être mutée de l'extérieur.",
                    "starter": "function createTaskStore() {\n  const tasks = [];\n  return {};\n}\n",
                    "hints": ["Retournez `[...tasks]` dans `list()` et validez le titre dans `add()`."],
                    "concepts": ["function", "const", "return"],
                },
                {
                    "title": "Manipulation DOM sûre et prévention XSS (`textContent`)",
                    "summary": "Rendre des données dynamiques sans jamais injecter de HTML brut.",
                    "explanation": "Utiliser `.innerHTML = userInput` ouvre une faille XSS immédiate ; `.textContent` échappe automatiquement le contenu.",
                    "code": "const li = document.createElement('li');\nli.textContent = task.title;",
                    "example_title": "Création de nœud DOM sans XSS",
                    "tip": "Bannissez `innerHTML` pour toute donnée saisie ou reçue d'une API.",
                    "exercise_title": "Rendu sécurisé d'une carte DOM",
                    "exercise_prompt": "Écrivez une fonction JS construisant un élément `<li>` avec `createElement` et `textContent` sans `innerHTML`.",
                    "starter": "function renderItem(doc, title) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Appelez `doc.createElement('li')` puis `el.textContent = String(title)`."],
                    "concepts": ["createElement", "textContent", "return"],
                },
                {
                    "title": "Écouteurs, `preventDefault()` et délégation d'événements",
                    "summary": "Gérer listes dynamiques et formulaires avec un seul écouteur.",
                    "explanation": "Écoutez le conteneur parent puis inspectez `event.target.closest('button')`.",
                    "code": "listEl.addEventListener('click', (e) => {\n  const btn = e.target.closest('[data-id]');\n  if (!btn) return;\n});",
                    "example_title": "Délégation DOM avec closest",
                    "tip": "Retirez les écouteurs ou utilisez un `AbortController` lors de la destruction d'une vue.",
                    "exercise_title": "Gestionnaire délégué d'actions",
                    "exercise_prompt": "Écrivez une fonction JS gérant `click` via `closest('[data-action]')` avec garde si null.",
                    "starter": "function handleListClick(event, onDelete) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Vérifiez `if (!btn) return;` avant de lire `btn.dataset.id`."],
                    "concepts": ["closest", "if", "return"],
                },
                {
                    "title": "Timers, `debounce` et nettoyage d'effets",
                    "summary": "Éviter les rafales d'appels pendant la saisie utilisateur.",
                    "explanation": "`clearTimeout` dans une closure `debounce` retarde l'exécution jusqu'à la fin de la saisie.",
                    "code": "function debounce(fn, delayMs) {\n  let id = null;\n  return (...args) => { clearTimeout(id); id = setTimeout(() => fn(...args), delayMs); };\n}",
                    "example_title": "Utilitaire debounce avec closure",
                    "tip": "Prévoyez une méthode `.cancel()` pour nettoyer au démontage.",
                    "exercise_title": "Debounce avec annulation explicite",
                    "exercise_prompt": "Implémentez `debounce(fn, delay)` avec gestion `clearTimeout` et exposition de `cancel`.",
                    "starter": "function debounce(fn, delay) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Attachez `wrapped.cancel = () => clearTimeout(timer)`."],
                    "concepts": ["setTimeout", "clearTimeout", "return"],
                },
            ],
            "project_title": "Mini-interface JavaScript DOM sécurisée (closure store, délégation & debounce)",
            "project_brief": "### Contexte\nRéalisez une interface JS vanilla sans framework gérant une liste filtrable avec store par closure, rendu DOM sûr via `textContent` et champ recherche debouncé.",
            "project_deliverables": [
                "Store privé par closure sans fuite globale",
                "Rendu DOM exclusivement via `textContent`",
                "Délégation d'événements et recherche debouncée",
            ],
        },
        3: {
            "title": "Niveau 3 — JavaScript asynchrone : Promesses, `async/await` & Fetch",
            "summary": "Maîtriser event loop, `Promise.all`, `AbortController`, timeouts et erreurs HTTP.",
            "objectives": [
                "Écrire des flux asynchrones lisibles avec `async`/`await` et `try/catch`",
                "Vérifier systématiquement `response.ok` avec `fetch`",
                "Annuler les requêtes obsolètes avec `AbortController` et gérer les délais",
            ],
            "chapters": [
                {
                    "title": "Event loop, Promesses et `async/await`",
                    "summary": "Comprendre file de microtâches et propagation des rejets.",
                    "explanation": "Une fonction `async` retourne toujours une `Promise`. Utilisez `try/catch` autour d'`await`.",
                    "code": "async function loadSafe(fn) {\n  try { return { ok: true, data: await fn() }; } catch (err) { return { ok: false, error: err }; }\n}",
                    "example_title": "Capture asynchrone propre",
                    "tip": "N'oubliez jamais `await` devant une promesse retournée dans un bloc `try/catch`.",
                    "exercise_title": "Wrapper asynchrone avec repli sûr",
                    "exercise_prompt": "Écrivez une fonction `async` exécutant deux tâches en parallèle avec `Promise.all` et gérant l'erreur via `try/catch`.",
                    "starter": "async function loadBoth(a, b) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Utilisez `const [resA, resB] = await Promise.all([a(), b()])`."],
                    "concepts": ["async", "await", "Promise.all", "try", "catch"],
                },
                {
                    "title": "Client `fetch` sûr avec `response.ok` et timeout",
                    "summary": "Rappeler que `fetch` ne rejette pas sur HTTP 404 ou 500.",
                    "explanation": "`fetch` ne lève d'exception que sur panne réseau : il faut tester `if (!response.ok)` explicitement.",
                    "code": "async function getJson(url, signal) {\n  const res = await fetch(url, { signal });\n  if (!res.ok) throw new Error(`HTTP ${res.status}`);\n  return res.json();\n}",
                    "example_title": "Vérification HTTP obligatoire sur fetch",
                    "tip": "Passez toujours un `AbortSignal.timeout(...)` ou un `AbortController` pour borner l'attente.",
                    "exercise_title": "Client fetch avec timeout AbortController",
                    "exercise_prompt": "Écrivez `fetchWithTimeout(url, timeoutMs)` vérifiant `res.ok` et nettoyant le timer dans `finally`.",
                    "starter": "async function fetchWithTimeout(url, timeoutMs) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Appelez `controller.abort()` dans `setTimeout` et `clearTimeout` dans `finally`."],
                    "concepts": ["fetch", "AbortController", "finally", "throw"],
                },
                {
                    "title": "Retry contrôlé avec backoff et arrêt sur erreur 4xx",
                    "summary": "Réessayer uniquement les pannes transitoires (5xx/réseau), jamais 400/401/422.",
                    "explanation": "Réessayer une requête 401 ou 422 aggrave le blocage et gaspille le quota.",
                    "code": "const shouldRetry = (status) => status >= 500 || status === 429;",
                    "example_title": "Critère de réessai HTTP sain",
                    "tip": "Bornez toujours le nombre maximum de tentatives (ex. 2 ou 3).",
                    "exercise_title": "Politique retry sans boucle infinie",
                    "exercise_prompt": "Écrivez `retryTransient(fn, maxAttempts)` qui réessaie uniquement si `err.status >= 500`.",
                    "starter": "async function retryTransient(fn, maxAttempts = 3) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Bornez la boucle `for (let attempt = 1; attempt <= maxAttempts; attempt++)`."],
                    "concepts": ["async", "for", "catch", "throw"],
                },
                {
                    "title": "Synchronisation concurrente (`Promise.allSettled`)",
                    "summary": "Tolérer l'échec d'une source secondaire sans casser toute la page.",
                    "explanation": "`Promise.allSettled` inspecte individuellement chaque résultat `fulfilled` ou `rejected`.",
                    "code": "const settled = await Promise.allSettled(tasks);\nconst okValues = settled.filter((r) => r.status === 'fulfilled').map((r) => r.value);",
                    "example_title": "Agrégation résiliente de widgets",
                    "tip": "Signalez clairement à l'utilisateur les blocs partiellement indisponibles.",
                    "exercise_title": "Collecteur allSettled avec rapport d'erreurs",
                    "exercise_prompt": "Écrivez `partitionResults(promises)` retournant `{ succeeded, failed }` via `Promise.allSettled`.",
                    "starter": "async function partitionResults(promises) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Séparez `r.status === 'fulfilled'` et `r.status === 'rejected'`."],
                    "concepts": ["Promise.allSettled", "filter", "return"],
                },
            ],
            "project_title": "Client HTTP JavaScript asynchrone résilient (timeout, AbortController & allSettled)",
            "project_brief": "### Contexte\nConstruisez un module réseau JavaScript ES6 avec `fetch`, validation `res.ok`, annulation via `AbortController`, retry sélectif et tests asynchrones.",
            "project_deliverables": [
                "Vérification stricte `response.ok` et timeout dans `finally`",
                "Retry uniquement sur erreurs transitoires",
                "Tests couvrant succès, timeout et erreur 401 non réessayée",
            ],
        },
        4: {
            "title": "Niveau 4 — Modules ESM, architecture propre & tests automatisés JS",
            "summary": "Découper un projet JavaScript en modules ES testables avec mocks contrôlés.",
            "objectives": [
                "Structurer des modules ESM sans dépendances circulaires",
                "Injecter des dépendances (`fetch`, horloge) pour tester sans réseau réel",
                "Écrire des suites de tests unitaires couvrant cas limites et erreurs",
            ],
            "chapters": [
                {
                    "title": "Modules ESM (`import`/`export`) et fonctions pures",
                    "summary": "Isoler logique métier et effets de bord.",
                    "explanation": "Gardez la logique métier dans des modules sans accès direct au DOM ni à `localStorage`.",
                    "code": "export function sortByUrgency(tasks) {\n  return [...tasks].sort((a, b) => a.dueAt.localeCompare(b.dueAt));\n}",
                    "example_title": "Fonction de tri exportée pure",
                    "tip": "Préférez les exports nommés aux exports par défaut pour faciliter le refactoring.",
                    "exercise_title": "Module de tri et filtrage JS",
                    "exercise_prompt": "Écrivez et exportez une fonction JS pure triant des tâches sans muter le tableau reçu.",
                    "starter": "export function rankTasks(tasks) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Clonez le tableau avant `.sort(...)`."],
                    "concepts": ["export", "function", "sort", "return"],
                },
                {
                    "title": "Injection de dépendances pour des tests déterministes",
                    "summary": "Passer `now` ou `httpClient` en paramètre optionnel.",
                    "explanation": "Tester des délais ou appels HTTP devient simple quand la fonction accepte `{ now = () => new Date() }`.",
                    "code": "export function isExpired(expiresAt, nowMs = Date.now()) {\n  return Date.parse(expiresAt) <= nowMs;\n}",
                    "example_title": "Horloge injectable déterministe",
                    "tip": "Ne figez jamais `new Date()` au cœur d'une fonction critique sans paramètre de référence.",
                    "exercise_title": "Calcul d'échéance testable",
                    "exercise_prompt": "Écrivez `isOverdue(dueIso, now = new Date())` gérant `dueIso == null` proprement.",
                    "starter": "function isOverdue(dueIso, now = new Date()) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Retournez `false` si `!dueIso` ou `Number.isNaN(Date.parse(dueIso))`."],
                    "concepts": ["Date", "isNaN", "return"],
                },
                {
                    "title": "Tests unitaires avec mocks et assertions claires",
                    "summary": "Vérifier comportement observable et cas d'erreur.",
                    "explanation": "Chaque fonction publique doit avoir au moins un test nominal, un cas limite et un test d'entrée invalide.",
                    "code": "if (!Array.isArray(items)) throw new TypeError('Liste requise');",
                    "example_title": "Contrat vérifié par TypeError",
                    "tip": "Nettoyez vos mocks entre chaque test.",
                    "exercise_title": "Garde TypeError + test",
                    "exercise_prompt": "Écrivez une fonction JS levant `TypeError` sur entrée non tableau et retournant le résumé.",
                    "starter": "function summarize(items) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Vérifiez `if (!Array.isArray(items)) throw new TypeError(...)`."],
                    "concepts": ["Array.isArray", "TypeError", "throw"],
                },
                {
                    "title": "Audit mémoire et fuites d'abonnements",
                    "summary": "Prévenir listeners orphelins et timers non nettoyés.",
                    "explanation": "Tout `setInterval` ou `addEventListener` doit retourner une fonction de nettoyage `unsubscribe`.",
                    "code": "export function subscribeTick(cb, ms) {\n  const id = setInterval(cb, ms);\n  return () => clearInterval(id);\n}",
                    "example_title": "Pattern cleanup explicite",
                    "tip": "Testez toujours l'appel au cleanup dans vos tests unitaires.",
                    "exercise_title": "Abonnement avec cleanup idempotent",
                    "exercise_prompt": "Écrivez `startTimer(onTick, ms)` retournant une fonction d'arrêt nettoyant `clearInterval`.",
                    "starter": "function startTimer(onTick, ms) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Stockez `let active = true` et annulez l'intervalle au premier appel."],
                    "concepts": ["setInterval", "clearInterval", "return"],
                },
            ],
            "project_title": "Bibliothèque JavaScript modulaire ESM avec injection de dépendances & suite de tests",
            "project_brief": "### Contexte\nAssemblez un mini-package ESM JavaScript organisé en modules purs avec horloge injectable, gestion d'abonnements nettoyables et suite de tests unitaires.",
            "project_deliverables": [
                "Modules ESM propres et découplés",
                "Horloge / client HTTP injectables sans effet de bord caché",
                "Tests unitaires couvrant cas nominaux, bornes et erreurs",
            ],
        },
        5: {
            "title": "Niveau 5 — Sécurité navigateur, performance & qualité production JS",
            "summary": "Prévenir XSS, pollution de prototype, goulots de rendu et sécuriser la communication client-API.",
            "objectives": [
                "Neutraliser les vecteurs XSS, URL `javascript:` et pollution de prototype",
                "Optimiser boucles, structures (`Map`/`Set`) et batching d'opérations coûteuses",
                "Construire un client front résilient respectant cookies HttpOnly et CSRF/CORS",
            ],
            "chapters": [
                {
                    "title": "Protection contre la pollution de prototype et clés réservées",
                    "summary": "Valider les objets JSON dynamiques venus de l'extérieur.",
                    "explanation": "Rejetez les clés `__proto__`, `constructor` et `prototype` lors de fusions d'objets ou utilisez `Object.create(null)` / `Map`.",
                    "code": "const FORBIDDEN = new Set(['__proto__', 'constructor', 'prototype']);\nif (FORBIDDEN.has(key)) throw new Error('Clé interdite');",
                    "example_title": "Dictionnaire sûr avec Set/Map",
                    "tip": "Préférez `new Map()` aux objets simples pour indexer des clés arbitraires.",
                    "exercise_title": "Copie sécurisée d'objet JSON",
                    "exercise_prompt": "Écrivez une fonction JS copiant uniquement les clés sûres d'un objet (en rejetant `__proto__`, `constructor`, `prototype`).",
                    "starter": "function safeAssign(target, source) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Utilisez `Object.keys(source)` et filtrez contre `FORBIDDEN`."],
                    "concepts": ["Object.keys", "Set", "throw", "return"],
                },
                {
                    "title": "Sanitisation des URL et prévention `javascript:`",
                    "summary": "Ne jamais injecter une URL utilisateur brute dans un lien `<a href>`.",
                    "explanation": "Parsez l'URL avec `new URL(raw)` et vérifiez que `protocol` est strictement `'http:'` ou `'https:'`.",
                    "code": "function safeExternalHref(raw) {\n  const u = new URL(raw);\n  if (u.protocol !== 'https:' && u.protocol !== 'http:') return null;\n  return u.toString();\n}",
                    "example_title": "Filtrage de schéma d'URL",
                    "tip": "Ajoutez `rel=\"noopener noreferrer\"` sur tous les liens externes ouvrant un onglet.",
                    "exercise_title": "Validateur strict de lien externe",
                    "exercise_prompt": "Écrivez `toSafeHref(raw)` acceptant uniquement `https://` et renvoyant `null` sur `javascript:` ou texte malformé.",
                    "starter": "function toSafeHref(raw) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Encadrez `new URL(raw)` avec `try / catch`."],
                    "concepts": ["URL", "protocol", "try", "catch"],
                },
                {
                    "title": "Complexité algorithmique avec `Map` et `Set`",
                    "summary": "Remplacer les recherches imbriquées O(n²) par des index O(1).",
                    "explanation": "Dans les tableaux de planning ou de cours, indexez par `id` dans une `Map` avant de joindre les données.",
                    "code": "const byId = new Map(courses.map((c) => [c.id, c]));",
                    "example_title": "Jointure O(n + m) avec Map",
                    "tip": "Mesurez sur 5 000 éléments plutôt que de deviner les coûts.",
                    "exercise_title": "Détecteur de doublons O(n)",
                    "exercise_prompt": "Écrivez `findDuplicateTitles(items)` en JavaScript en temps O(n) via `Set` après normalisation.",
                    "starter": "function findDuplicateTitles(items) {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Stockez `item.trim().toLowerCase()` dans un `new Set()`."],
                    "concepts": ["Set", "toLowerCase", "return"],
                },
                {
                    "title": "Authentification HttpOnly & architecture zéro secret en localStorage",
                    "summary": "Protéger la session contre le vol via XSS.",
                    "explanation": "Ne persistez jamais un JWT d'accès dans `localStorage` ; gardez le jeton court en mémoire et laissez le backend renouveler via cookie HttpOnly avec `credentials: 'include'`.",
                    "code": "await fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'include' });",
                    "example_title": "Renouvellement silencieux sans localStorage",
                    "tip": "Effacez immédiatement l'état mémoire et le cache requêtes à la déconnexion.",
                    "exercise_title": "Gestionnaire mémoire de jeton d'accès",
                    "exercise_prompt": "Écrivez un gestionnaire `createTokenHolder()` gardant le jeton uniquement en closure privée avec méthodes `get`, `set` et `clear`.",
                    "starter": "function createTokenHolder() {\n  throw new Error('TODO');\n}\n",
                    "hints": ["Stockez `let token = null;` dans la closure et ne touchez jamais `localStorage`."],
                    "concepts": ["function", "const", "return"],
                },
            ],
            "project_title": "Couche client JavaScript durcie (sécurité XSS/proto, indexation Map/Set & session mémoire)",
            "project_brief": "### Contexte\nConcevez un utilitaire front JavaScript durci combinant sanitisation d'URL, fusion sûre anti-prototype-pollution, indexation `Map`/`Set` O(n) et stockage session strictement en mémoire.",
            "project_deliverables": [
                "Sanitiseur d'URL et protection `__proto__`",
                "Algorithmes O(n) via `Map`/`Set`",
                "Tests unitaires complets sur vecteurs d'attaque",
            ],
        },
    }
    return _build_track_levels(prefix="js", code_lang="javascript", specs=specs)


def get_generic_levels(
    subject: str,
    total_levels: int,
    language_pref: str = "fr",
) -> dict[int, dict[str, Any]]:
    topic_key = resolve_topic_key(subject)
    code_lang = SUBJECT_CODE_LANG.get(topic_key, "markdown")
    comment_prefix = (
        "#"
        if code_lang == "python"
        else ("--" if code_lang == "sql" else ("" if code_lang == "markdown" else "//"))
    )

    def _fmt_example(ch_title: str, lvl_num: int, idx: int) -> str:
        if comment_prefix == "":
            return (
                f"Étape 1 ({subject} — Niv. {lvl_num}.{idx}) : définir l'objectif et les hypothèses initiales.\n"
                f"Étape 2 : appliquer la méthode propre à « {ch_title} » étape par étape.\n"
                "Étape 3 : vérifier le résultat sur un cas standard et un contre-exemple."
            )
        return (
            f"{comment_prefix} Exemple méthodologique — {subject} (Niveau {lvl_num}, Chapitre {idx})\n"
            f"{comment_prefix} 1) Valider les données d'entrée\n"
            f"{comment_prefix} 2) Traiter « {ch_title} »\n"
            f"{comment_prefix} 3) Vérifier le résultat nominal et le cas limite"
        )

    level_defs: dict[int, tuple[str, str, list[str]]] = {
        1: (
            f"Niveau 1 — Fondations et concepts essentiels en {subject}",
            f"Trame méthodologique adaptable en {subject} : vocabulaire exact, bases opératoires et premiers exercices guidés.",
            [
                f"Maîtriser les notions fondamentales et le vocabulaire de {subject}",
                f"Résoudre des exercices simples en {subject} en expliquant chaque étape",
                "Identifier et vérifier au moins un cas limite ou piège classique",
                "Valider un mini-projet concret de niveau fondation",
            ],
        ),
        2: (
            f"Niveau 2 — Structuration, méthode et cas limites en {subject}",
            f"Structurer des réalisations réutilisables en {subject}, gérer les erreurs et justifier ses choix.",
            [
                f"Décomposer un problème en {subject} en sous-étapes vérifiables",
                "Traiter explicitement les anomalies, exceptions ou contre-exemples",
                "Documenter et tester chaque résultat produit",
            ],
        ),
        3: (
            f"Niveau 3 — Conception autonome et projet appliqué en {subject}",
            f"Construire une production complète et vérifiable en {subject} évaluée sur critères réels.",
            [
                f"Appliquer les bonnes pratiques reconnues en {subject}",
                "Analyser la qualité, la robustesse et la maintenabilité",
                "Soutenir le livrable avec preuves et tests reproductibles",
            ],
        ),
        4: (
            f"Niveau 4 — Approfondissement, optimisation et fiabilité en {subject}",
            f"Diagnostiquer les points faibles, optimiser et fiabiliser une réalisation avancée en {subject}.",
            [
                f"Comparer plusieurs approches en {subject} avec compromis argumentés",
                "Gérer les cas avancés et contraintes réelles de fiabilité",
                "Fournir une documentation technique rigoureuse",
            ],
        ),
        5: (
            f"Niveau 5 — Maîtrise et livrable de référence en {subject}",
            f"Concevoir, vérifier, sécuriser et justifier un projet complet de référence en {subject}.",
            [
                f"Piloter une réalisation complète et critique en {subject}",
                "Démontrer sa robustesse par des vérifications exhaustives",
                "Défendre chaque décision face à une grille d'évaluation exigeante",
            ],
        ),
    }

    levels: dict[int, dict[str, Any]] = {}
    for lvl_num in range(1, total_levels + 1):
        title, summary, objectives = level_defs[lvl_num]
        chapter_topics = [
            (
                f"Notions clés et cadre de travail ({subject} — Niv. {lvl_num})",
                f"Poser le modèle mental du niveau {lvl_num} en {subject} avec la terminologie exacte.",
                25,
            ),
            (
                "Méthode de résolution et traitement des cas limites",
                f"Appliquer une démarche rigoureuse en {subject} sans ignorer les cas d'erreur.",
                25,
            ),
            (
                "Structuration, modularité et justification des choix",
                f"Organiser une production lisible et vérifiable en {subject}.",
                30,
            ),
            (
                "Vérification, revue critique et synthèse pratique",
                f"Contrôler la qualité d'un travail en {subject} avant d'aborder le projet de palier.",
                30,
            ),
        ]
        lessons: list[dict[str, Any]] = []
        for idx, (ch_title, ch_summary, mins) in enumerate(chapter_topics, start=1):
            example_text = _fmt_example(ch_title, lvl_num, idx)
            starter = (
                f"Rédigez votre réponse et votre exemple concret en {subject} pour « {ch_title} »."
                if code_lang == "markdown"
                else f"{comment_prefix} Votre solution {subject} pour : {ch_title}\n"
            )
            ex_type = "open_explanation" if code_lang == "markdown" else "code"
            lessons.append(
                {
                    "position": idx,
                    "title": ch_title,
                    "summary": ch_summary,
                    "estimated_minutes": mins,
                    "content_markdown": (
                        f"## 1. Objectif pédagogique\n\n{ch_summary}\n\n"
                        f"### 2. Prérequis & intuition\n\nCette trame générique vous guide pour relier théorie et pratique en **{subject}**.\n\n"
                        f"### 3. Explication pas à pas\n\n"
                        f"1. **Clarifier le problème** : précisez les données d'entrée et le résultat attendu en **{subject}**.\n"
                        "2. **Structurer par étapes** : isolez chaque règle ou transformation.\n"
                        "3. **Vérifier les limites** : testez un cas nominal et un cas d'erreur.\n\n"
                        f"### 4. Exemple concret commenté\n\n```{code_lang}\n{example_text}\n```\n\n"
                        "### 5. Cas limites & pièges fréquents\n\n- Négliger les cas invalides ou supposer qu'une lecture suffit sans production vérifiable.\n\n"
                        "### 6. Bonnes pratiques\n\n- Documentez toujours le *pourquoi* de vos choix et vérifiez vos affirmations avec les ressources officielles.\n\n"
                        f"### 7. Synthèse à retenir\n\n« {ch_title} » relie théorie, pratique et preuve vérifiable en {subject}.\n\n"
                        "### 8. Contrôle de compréhension\n\nExpliquez votre démarche étape par étape dans l'exercice ci-dessous."
                    ),
                    "code_examples": [
                        {
                            "title": f"Canevas structuré — Chapitre {idx}",
                            "language": code_lang,
                            "code": example_text,
                            "explanation": f"Organise la progression pour « {ch_title} » ({language_pref}).",
                        }
                    ],
                    "exercises": [
                        {
                            "id": f"gen-{lvl_num}-{idx}-ex1",
                            "title": f"Mise en pratique : {ch_title}",
                            "difficulty": "guide" if idx <= 2 else "pratique",
                            "exercise_type": ex_type,
                            "instructions_markdown": (
                                f"Produisez un exemple concret illustrant **{ch_title}** en {subject}. "
                                "Justifiez votre choix technique (« parce que… ») et décrivez un cas limite ou une vérification."
                            ),
                            "starter_code": starter,
                            "hints": [
                                f"Indice 1 : Définissez clairement le périmètre et l'objectif en {subject}.",
                                "Indice 2 : Ajoutez un contrôle explicite pour un cas limite.",
                                "Indice 3 : Indiquez comment vous vérifiez le résultat.",
                            ],
                            "expected_concepts": [subject.lower(), "vérification", "limite", "exemple"],
                        }
                    ],
                }
            )

        levels[lvl_num] = {
            "title": title,
            "summary": summary,
            "objectives": objectives,
            "lessons": lessons,
            "project_title": f"Projet pratique Niveau {lvl_num} — Réalisation complète en {subject}",
            "project_brief": (
                f"### Contexte du projet Niveau {lvl_num}\n\n"
                f"Réalisez une production autonome et vérifiable mobilisant les notions du niveau {lvl_num} en **{subject}**.\n\n"
                "### Exigences de rendu\n"
                "1. Production concrète et structurée avec traitement des cas limites.\n"
                "2. Justification écrite de vos choix et de leur raison d’être.\n"
                "3. Preuve de vérification ou scénario de test documenté."
            ),
            "project_deliverables": [
                f"Production concrète structurée en {subject}",
                "Gestion explicite d'au moins un cas limite / erreur",
                "Vérification reproductible avec résultat observé",
                "Explication claire de la démarche",
            ],
        }
    return levels
