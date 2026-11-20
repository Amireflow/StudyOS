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
        },
        {
            "title": "Documentation officielle Python 3 (Standard Library)",
            "url": "https://docs.python.org/3/library/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "Python.org",
            "notes": "Référence complète des modules standard (pathlib, json, dataclasses, unittest).",
        },
        {
            "title": "Pytest — Documentation officielle",
            "url": "https://docs.pytest.org/en/stable/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "pytest.org",
            "notes": "Indispensable pour écrire et structurer vos tests unitaires dès le niveau 2.",
        },
        {
            "title": "Formation complète Python pour débutants (Vidéo FR)",
            "url": "https://www.youtube.com/watch?v=LamjAFnybo0",
            "resource_type": "video",
            "language": "fr",
            "is_official": False,
            "source_name": "Graven / YouTube",
            "notes": "Explication vidéo pas à pas des bases Python avec exercices guidés.",
        },
        {
            "title": "Harvard CS50P — Introduction to Programming with Python",
            "url": "https://cs50.harvard.edu/python/",
            "resource_type": "video",
            "language": "en",
            "is_official": True,
            "source_name": "Harvard University",
            "notes": "Cours universitaire complet en vidéo et exercices pratiques progressifs.",
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
        },
        {
            "title": "MDN Web Docs — JavaScript & Fondamentaux Web (FR)",
            "url": "https://developer.mozilla.org/fr/docs/Web/JavaScript/Guide",
            "resource_type": "documentation",
            "language": "fr",
            "is_official": True,
            "source_name": "MDN Web Docs",
            "notes": "Socle JavaScript moderne indispensable sous TypeScript.",
        },
        {
            "title": "TypeScript Playground officiel",
            "url": "https://www.typescriptlang.org/play",
            "resource_type": "interactive",
            "language": "en",
            "is_official": True,
            "source_name": "TypeScript.org",
            "notes": "Bac à sable interactif pour tester vos types en direct sans installation.",
        },
        {
            "title": "Apprendre TypeScript en pratique (Vidéo FR)",
            "url": "https://grafikart.fr/formations/typescript",
            "resource_type": "video",
            "language": "fr",
            "is_official": False,
            "source_name": "Grafikart",
            "notes": "Série vidéo structurée en français : syntaxe, narrowing et génériques.",
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
        },
        {
            "title": "React Official Docs — Thinking in React",
            "url": "https://react.dev/learn/thinking-in-react",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "React.dev",
            "notes": "Méthode officielle pour découper une interface en composants propres.",
        },
        {
            "title": "Formation React moderne (Vidéo FR)",
            "url": "https://grafikart.fr/formations/react",
            "resource_type": "video",
            "language": "fr",
            "is_official": False,
            "source_name": "Grafikart",
            "notes": "Vidéos pratiques progressives sur React, hooks et formulaires.",
        },
    ],
    "sql": [
        {
            "title": "Documentation officielle PostgreSQL (Référence SQL)",
            "url": "https://www.postgresql.org/docs/current/tutorial.html",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "PostgreSQL Global Development Group",
            "notes": "Tutoriel officiel sur SELECT, jointures, agrégations et transactions.",
        },
        {
            "title": "SQLBolt — Exercices interactifs SQL pas à pas",
            "url": "https://sqlbolt.com/",
            "resource_type": "interactive",
            "language": "en",
            "is_official": False,
            "source_name": "SQLBolt",
            "notes": "Leçons courtes et requêtes exécutables directement dans le navigateur.",
        },
        {
            "title": "Formation SQL & Bases de données relationnelles (FR)",
            "url": "https://sql.sh/",
            "resource_type": "documentation",
            "language": "fr",
            "is_official": False,
            "source_name": "SQL.sh",
            "notes": "Fiches synthétiques en français pour chaque clause SQL avec exemples.",
        },
        {
            "title": "PostgreSQL & SQL Full Course (Vidéo EN)",
            "url": "https://www.youtube.com/watch?v=qw--VYLpxG4",
            "resource_type": "video",
            "language": "en",
            "is_official": False,
            "source_name": "freeCodeCamp",
            "notes": "Cours complet de 4 h couvrant schémas, requêtes, index et jointures.",
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
            "notes": "Référence officielle complète sur l’ownership, le borrowing et les traits.",
        },
        {
            "title": "Rust by Example (Officiel)",
            "url": "https://doc.rust-lang.org/rust-by-example/",
            "resource_type": "interactive",
            "language": "en",
            "is_official": True,
            "source_name": "Rust-lang.org",
            "notes": "Exemples compilables et modifiables directement en ligne.",
        },
        {
            "title": "Rustlings — Exercices officiels progressifs",
            "url": "https://github.com/rust-lang/rustlings",
            "resource_type": "interactive",
            "language": "en",
            "is_official": True,
            "source_name": "Rust Team",
            "notes": "Petits exercices ciblés pour maîtriser la syntaxe et le compilateur.",
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
            "notes": "Guide officiel moderne : POO, collections, streams et concurrence.",
        },
        {
            "title": "MOOC Java Programming (University of Helsinki)",
            "url": "https://java-programming.mooc.fi/",
            "resource_type": "interactive",
            "language": "en",
            "is_official": True,
            "source_name": "University of Helsinki",
            "notes": "Parcours universitaire reconnu avec exercices pratiques corrigés.",
        },
        {
            "title": "Cours Java Orienté Objet complet (Vidéo FR)",
            "url": "https://www.youtube.com/watch?v=rM2zT5C4R88",
            "resource_type": "video",
            "language": "fr",
            "is_official": False,
            "source_name": "YouTube FR",
            "notes": "Vidéo claire en français pour démarrer avec les classes et méthodes Java.",
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
        },
        {
            "title": "Documentation officielle Go",
            "url": "https://go.dev/doc/",
            "resource_type": "documentation",
            "language": "en",
            "is_official": True,
            "source_name": "go.dev",
            "notes": "Effective Go et guides officiels de conception idiomatique.",
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
    },
    {
        "title": "Roadmap.sh — Parcours guidés par compétences",
        "url": "https://roadmap.sh/",
        "resource_type": "article",
        "language": "en",
        "is_official": False,
        "source_name": "roadmap.sh",
        "notes": "Cartographie claire des notions par palier de progression.",
    },
    {
        "title": "Grafikart — Tutoriels vidéo pratiques en français",
        "url": "https://grafikart.fr/tutoriels",
        "resource_type": "video",
        "language": "fr",
        "is_official": False,
        "source_name": "Grafikart",
        "notes": "Explications vidéo structurées en français avec cas concrets.",
    },
    {
        "title": "freeCodeCamp — Cours vidéo complets gratuits",
        "url": "https://www.freecodecamp.org/learn/",
        "resource_type": "video",
        "language": "en",
        "is_official": False,
        "source_name": "freeCodeCamp",
        "notes": "Cours approfondis gratuits avec projets pratiques.",
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
    if "typescript" in lowered or lowered == "ts":
        return "typescript"
    if "javascript" in lowered or lowered == "js":
        return "typescript"
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


def get_curated_resources_for_subject(subject: str, language_pref: str) -> list[dict[str, Any]]:
    topic = resolve_topic_key(subject)
    raw_list = CURATED_RESOURCES.get(topic, [])
    combined = list(raw_list) if raw_list else list(FALLBACK_RESOURCES)
    if language_pref == "fr":
        combined.sort(key=lambda r: (0 if r["language"] == "fr" else 1, 0 if r["is_official"] else 1))
    elif language_pref == "en":
        combined.sort(key=lambda r: (0 if r["language"] == "en" else 1, 0 if r["is_official"] else 1))
    else:
        combined.sort(key=lambda r: (0 if r["is_official"] else 1, r["language"]))
    return combined[:6]


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
    }


def get_generic_levels(subject: str, total_levels: int) -> dict[int, dict[str, Any]]:
    code_lang = SUBJECT_CODE_LANG.get(resolve_topic_key(subject), "text")
    level_defs: dict[int, tuple[str, str, list[str]]] = {
        1: (
            f"Niveau 1 — Fondations et premiers programmes en {subject}",
            f"Acquérir les bases solides de {subject} : concepts clés, syntaxe essentielle, structuration et premiers exercices vérifiés.",
            [
                f"Comprendre le modèle mental et l’écosystème officiel de {subject}",
                f"Écrire des unités simples et lisibles en {subject} en gérant les entrées invalides",
                f"Structurer des données et itérations propres en {subject}",
                "Expliquer son code et valider un mini-projet concret de niveau débutant",
            ],
        ),
        2: (
            f"Niveau 2 — Modularité, gestion d’erreurs et tests en {subject}",
            f"Structurer un projet {subject} réutilisable, gérer les erreurs explicitement et automatiser les vérifications.",
            [
                f"Découper un programme {subject} en modules et interfaces claires",
                "Traiter les erreurs et cas limites sans comportement silencieux",
                f"Persister ou échanger des données structurées avec {subject}",
                "Écrire des tests automatisés couvrant cas nominaux et anomalies",
            ],
        ),
        3: (
            f"Niveau 3 — Conception autonome et projet avancé en {subject}",
            f"Construire une application complète et robuste en {subject}, prête à être évaluée sur critères réels.",
            [
                f"Appliquer les idiomes et patrons recommandés en {subject}",
                "Évaluer la complexité, la maintenabilité et la sécurité du code",
                "Intégrer documentation, gestion d’état/flux et jeux de tests complets",
            ],
        ),
        4: (
            f"Niveau 4 — Architecture, performance et fiabilité en {subject}",
            f"Optimiser les goulots d’étranglement, structurer des architectures découplées et auditer la qualité en {subject}.",
            [
                f"Profiler et optimiser une application {subject} sur des charges réalistes",
                "Isoler les dépendances et garantir l’évolutivité du code",
                "Documenter les compromis techniques d’architecture",
            ],
        ),
        5: (
            f"Niveau 5 — Maîtrise et livrable de niveau production en {subject}",
            f"Concevoir, tester, sécuriser et documenter un projet complet de référence en {subject}.",
            [
                f"Concevoir de bout en bout une solution critique en {subject}",
                "Garantir couverture de tests, observabilité et gestion de pannes",
                "Soutenir techniquement chaque choix face à une grille exigeante",
            ],
        ),
    }

    levels: dict[int, dict[str, Any]] = {}
    for lvl_num in range(1, total_levels + 1):
        title, summary, objectives = level_defs[lvl_num]
        chapter_topics = [
            (
                f"Concepts fondamentaux et environnement ({subject} — Niv. {lvl_num})",
                f"Poser le modèle mental du niveau {lvl_num} avec la terminologie exacte et un premier exemple fonctionnel.",
                25,
            ),
            (
                f"Structuration de la logique et cas limites",
                f"Écrire des blocs clairs et défensifs en {subject} grâce aux retours anticipés et au découpage.",
                25,
            ),
            (
                f"Données, abstractions et gestion d'erreurs",
                f"Manipuler les structures recommandées par la documentation officielle {subject}.",
                30,
            ),
            (
                f"Vérification, tests et bonnes pratiques",
                f"Valider le fonctionnement sur des cas nominaux et d'erreur avant de passer au projet du niveau {lvl_num}.",
                30,
            ),
        ]
        lessons: list[dict[str, Any]] = []
        for idx, (ch_title, ch_summary, mins) in enumerate(chapter_topics, start=1):
            lessons.append(
                {
                    "position": idx,
                    "title": ch_title,
                    "summary": ch_summary,
                    "estimated_minutes": mins,
                    "content_markdown": (
                        f"## Objectif du chapitre {idx}\n\n"
                        f"{ch_summary}\n\n"
                        "### Explication pas à pas\n\n"
                        f"1. **Clarifier le contrat** : définissez toujours les entrées attendues, le résultat exact et les erreurs possibles en **{subject}**.\n"
                        "2. **Privilégier la lisibilité** : nommez explicitement vos fonctions/variables et isolez chaque responsabilité.\n"
                        "3. **Tester les cas limites** : entrée vide, valeur nulle ou hors bornes.\n\n"
                        f"```{code_lang}\n"
                        f"// Exemple progressif — {subject} (Niveau {lvl_num}, Chapitre {idx})\n"
                        "// 1) Valider l'entrée dès le début\n"
                        "// 2) Appliquer la transformation métier\n"
                        "// 3) Vérifier le résultat attendu sur cas nominal et cas limite\n"
                        "```\n\n"
                        "| Point clé | Objectif | Vérification |\n"
                        "| --- | --- | --- |\n"
                        "| Clarté | Intention lisible | Nommage explicite |\n"
                        "| Robustesse | Zéro crash silencieux | Cas limite testé |\n\n"
                        "> **Bonnes pratiques :** Appuyez-vous systématiquement sur la documentation officielle fournie dans l’onglet **Docs & Vidéos**."
                    ),
                    "code_examples": [
                        {
                            "title": f"Gabarit structuré — Chapitre {idx}",
                            "language": code_lang,
                            "code": f"// {ch_title}\n// Entrée -> Validation -> Traitement -> Sortie vérifiée",
                            "explanation": f"Illustre l’organisation recommandée pour « {ch_title} ».",
                        }
                    ],
                    "exercises": [
                        {
                            "id": f"gen-{lvl_num}-{idx}-ex1",
                            "title": f"Mise en pratique : {ch_title}",
                            "difficulty": "guide" if idx <= 2 else "pratique",
                            "instructions_markdown": (
                                f"Implémentez un cas concret illustrant **{ch_title}** en {subject}. "
                                "Expliquez votre raisonnement (« parce que… »), montrez votre code et décrivez au moins un cas d'erreur géré."
                            ),
                            "starter_code": f"// Votre solution {subject} pour : {ch_title}\n",
                            "hints": [
                                f"Indice 1 : Définissez clairement la signature ou structure en {subject}.",
                                "Indice 2 : Ajoutez un contrôle explicite pour une donnée invalide ou vide.",
                                "Indice 3 : Précisez le résultat concret obtenu lors de vos tests.",
                            ],
                            "expected_concepts": [subject.lower(), "test", "erreur", "exemple"],
                        }
                    ],
                }
            )

        levels[lvl_num] = {
            "title": title,
            "summary": summary,
            "objectives": objectives,
            "lessons": lessons,
            "project_title": f"Projet pratique Niveau {lvl_num} — Application complète en {subject}",
            "project_brief": (
                f"### Contexte du projet Niveau {lvl_num}\n\n"
                f"Réalisez un mini-projet autonome mobilisant l’ensemble des notions du niveau {lvl_num} en **{subject}**.\n\n"
                "### Exigences de rendu\n"
                "1. Code source propre et structuré avec gestion explicite des cas d’erreur.\n"
                "2. Justification écrite de vos choix techniques et de leur raison d’être.\n"
                "3. Jeu de tests ou scénario de vérification démontrant le cas nominal et au moins un cas limite."
            ),
            "project_deliverables": [
                f"Code source structuré en {subject}",
                "Gestion explicite d'au moins un cas limite / erreur",
                "Tests ou vérification reproductible avec résultat mesuré",
                "Explication claire de la démarche technique",
            ],
        }
    return levels
