"""Générateur de cours structurés multi-niveaux et correcteur pédagogique sur 100 points."""

from __future__ import annotations

import json
import re
from typing import Any
import httpx
from app.core.config import Settings
from app.schemas.common import CourseLanguage, CourseSubmissionKind
from app.services.assessment_evaluator import (
    EXTERNAL_URL_DISCLAIMER,
    _CONCRETE_ARTIFACT_KEYWORDS,
    _is_blatantly_insufficient,
)
from app.services.course_curricula import (
    SUBJECT_CODE_LANG,
    SUBJECT_DOMAIN_DEFAULT,
    get_curated_resources_for_subject,
    get_generic_levels,
    get_python_levels,
    get_typescript_levels,
    resolve_topic_key,
)


def pass_threshold_for_course_level(level_number: int) -> int:
    return 75 if level_number >= 4 else 70


def default_project_rubric(level_number: int) -> list[dict[str, Any]]:
    return [
        {
            "key": "coverage",
            "label": "Conformité & couverture des concepts",
            "description": f"Les notions attendues et exigences fonctionnelles du niveau {level_number} sont couvertes.",
            "max_score": 25,
        },
        {
            "key": "technical",
            "label": "Qualité technique & implémentation",
            "description": "Code ou artefact techniquement exact, structuré et lisible.",
            "max_score": 30,
        },
        {
            "key": "reasoning",
            "label": "Clarté du raisonnement & cas limites",
            "description": "Justification des choix, traitement des erreurs et cas limites documentés.",
            "max_score": 25,
        },
        {
            "key": "deliverables",
            "label": "Livrables & vérifiabilité",
            "description": "Tests, traces d’exécution ou démonstration reproductible des livrables.",
            "max_score": 20,
        },
    ]


def _build_specialized_levels(
    *,
    subject: str,
    code_lang: str,
    specs: dict[int, dict[str, Any]],
    total_levels: int,
) -> dict[int, dict[str, Any]]:
    """Construit des niveaux spécialisés pour React, SQL, Rust ou Java, complétés si total_levels > 3."""
    base = get_generic_levels(subject, total_levels)
    for lvl_num, spec in specs.items():
        if lvl_num > total_levels:
            continue
        lessons: list[dict[str, Any]] = []
        for idx, ch in enumerate(spec["chapters"], start=1):
            code_snippet = ch["code"]
            lessons.append(
                {
                    "position": idx,
                    "title": ch["title"],
                    "summary": ch["summary"],
                    "estimated_minutes": ch.get("minutes", 25),
                    "content_markdown": (
                        f"## Objectif du chapitre\n\n{ch['summary']}\n\n"
                        f"### Explication pas à pas\n\n{ch['explanation']}\n\n"
                        f"```{code_lang}\n{code_snippet}\n```\n\n"
                        f"> **Bonnes pratiques :** {ch['tip']}"
                    ),
                    "code_examples": [
                        {
                            "title": ch["example_title"],
                            "language": code_lang,
                            "code": code_snippet,
                            "explanation": ch["tip"],
                        }
                    ],
                    "exercises": [
                        {
                            "id": f"{spec['prefix']}-{lvl_num}-{idx}-ex1",
                            "title": ch["exercise_title"],
                            "difficulty": "guide" if idx <= 2 else "pratique",
                            "instructions_markdown": ch["exercise_prompt"],
                            "starter_code": ch.get("starter", ""),
                            "hints": ch["hints"],
                            "expected_concepts": ch["concepts"],
                        }
                    ],
                }
            )
        base[lvl_num] = {
            "title": spec["title"],
            "summary": spec["summary"],
            "objectives": spec["objectives"],
            "lessons": lessons,
            "project_title": spec["project_title"],
            "project_brief": spec["project_brief"],
            "project_deliverables": spec["project_deliverables"],
        }
    return base


def _get_react_specs() -> dict[int, dict[str, Any]]:
    return {
        1: {
            "prefix": "react",
            "title": "Niveau 1 — Composants React, JSX, props et état local",
            "summary": "Construire des interfaces modulaires avec composants fonctionnels, props typées et `useState`.",
            "objectives": [
                "Découper une interface en composants fonctionnels réutilisables",
                "Transmettre données et callbacks via des props typées en TypeScript",
                "Gérer les interactions et formulaires contrôlés avec `useState`",
            ],
            "chapters": [
                {
                    "title": "Composants fonctionnels et JSX typé",
                    "summary": "Rendre une vue déclarative à partir de props immuables.",
                    "explanation": "Un composant React est une fonction pure qui transforme des `props` en arbre JSX. Ne modifiez jamais les `props` directement.",
                    "code": "interface BadgeProps { label: string; }\nexport function LevelBadge({ label }: BadgeProps) {\n  return <span>{label}</span>;\n}",
                    "example_title": "Composant pur avec interface de props",
                    "tip": "Gardez chaque composant focalisé sur une responsabilité visuelle claire.",
                    "exercise_title": "Carte de leçon réutilisable",
                    "exercise_prompt": "Écrivez un composant `LessonBadge` acceptant `title: string` et `done: boolean` avec rendu conditionnel.",
                    "starter": "interface LessonBadgeProps { title: string; done: boolean; }\n",
                    "hints": ["Utilisez une expression ternaire ou `&&` dans le JSX.", "Typez explicitement les props."],
                    "concepts": ["props", "interface", "return", "tsx"],
                },
                {
                    "title": "État local avec `useState` et mises à jour immuables",
                    "summary": "Faire évoluer listes et objets sans mutation directe.",
                    "explanation": "React détecte les changements par référence : pour modifier un tableau dans `useState`, créez toujours un nouveau tableau via `map` ou `filter`.",
                    "code": "const [items, setItems] = useState<string[]>([]);\nconst addItem = (name: string) => setItems((prev) => [...prev, name]);",
                    "example_title": "Mise à jour fonctionnelle `prev => ...`",
                    "tip": "Utilisez la forme `setState((prev) => ...)` dès que le nouvel état dépend de l'ancien.",
                    "exercise_title": "Compteur avec réinitialisation et palier",
                    "exercise_prompt": "Implémentez un composant React gérant un score avec `useState` qui refuse de passer sous 0.",
                    "starter": "import { useState } from 'react';\n",
                    "hints": ["Utilisez `Math.max(0, prev - 1)` lors de la décrémentation."],
                    "concepts": ["useState", "prev", "function", "return"],
                },
                {
                    "title": "Listes clés (`key`) et rendu conditionnel propre",
                    "summary": "Éviter les bugs de réconciliation React sur les listes dynamiques.",
                    "explanation": "Chaque élément issu de `.map()` doit porter une `key` stable et unique (idéalement `item.id`, pas l'index du tableau).",
                    "code": "{lessons.map((l) => <li key={l.id}>{l.title}</li>)}",
                    "example_title": "Rendu de liste par ID stable",
                    "tip": "N'utilisez jamais l'index `.map((_, idx) => ...)` pour des listes filtrables ou réordonnables.",
                    "exercise_title": "Liste filtrable par recherche",
                    "exercise_prompt": "Créez une liste React filtrée par un champ `search` avec message d'état vide si aucun élément ne correspond.",
                    "starter": "const filtered = items.filter((i) => i.title.toLowerCase().includes(query.toLowerCase()));\n",
                    "hints": ["Testez `filtered.length === 0` pour afficher l'état vide."],
                    "concepts": ["map", "key", "filter", "useState"],
                },
                {
                    "title": "Formulaires contrôlés et accessibilité",
                    "summary": "Valider les champs avant soumission avec labels explicites.",
                    "explanation": "Reliez toujours `<label htmlFor=\"...\">` à l'`id` du champ et validez dans `onSubmit` après `event.preventDefault()`.",
                    "code": "<form onSubmit={(e) => { e.preventDefault(); submit(); }} noValidate>",
                    "example_title": "Formulaire contrôlé accessible",
                    "tip": "Affichez les erreurs dans un bloc `role=\"alert\"` relié au champ.",
                    "exercise_title": "Formulaire de création avec validation",
                    "exercise_prompt": "Écrivez un formulaire React contrôlé rejetant un titre < 3 caractères avec message d'erreur explicite.",
                    "starter": "function handleSubmit(e: React.FormEvent) { e.preventDefault(); }\n",
                    "hints": ["Stockez `error` dans un `useState<string | null>(null)`."],
                    "concepts": ["preventDefault", "onSubmit", "useState", "label"],
                },
            ],
            "project_title": "Tableau interactif de révision React (filtres + formulaire validé)",
            "project_brief": "### Contexte\nCréez une application React composée d'un formulaire de création de fiches validé, d'un filtre par état et d'un compteur d'avancement.",
            "project_deliverables": [
                "Composants typés en TypeScript sans `any`",
                "Formulaire contrôlé accessible avec validation",
                "Listes avec `key` stable et mises à jour immuables",
            ],
        },
        2: {
            "prefix": "react",
            "title": "Niveau 2 — Hooks avancés, effets propres & TanStack Query",
            "summary": "Gérer dérivations (`useMemo`), effets de bord sans fuite et chargement asynchrone.",
            "objectives": [
                "Distinguer état calculable (`useMemo`) et vrai état React",
                "Synchroniser des requêtes API avec TanStack Query et invalidation",
                "Tester des interactions utilisateur avec Testing Library + Vitest",
            ],
            "chapters": [
                {
                    "title": "Éviter `useEffect` superflu avec `useMemo`",
                    "summary": "Calculer les totaux et filtres pendant le rendu plutôt que dans un effet.",
                    "explanation": "Un `useEffect` qui met simplement à jour un autre `useState` déclenche deux rendus et des bugs de synchronisation. Utilisez `useMemo`.",
                    "code": "const activeCount = useMemo(() => tasks.filter((t) => !t.done).length, [tasks]);",
                    "example_title": "Calcul dérivé avec `useMemo`",
                    "tip": "Réservez `useEffect` à la synchronisation avec le monde extérieur (timers, DOM, abonnements).",
                    "exercise_title": "Remplacer un `useEffect` redondant",
                    "exercise_prompt": "Transformez un état dérivé calculé via `useEffect` en `useMemo` et expliquez le gain.",
                    "starter": "const summary = useMemo(() => items.length, [items]);\n",
                    "hints": ["Passez uniquement les dépendances lues à l'intérieur de `useMemo`."],
                    "concepts": ["useMemo", "filter", "return"],
                },
                {
                    "title": "Requêtes & mutations avec TanStack Query",
                    "summary": "Cacher, revalider et gérer chargement/erreur proprement.",
                    "explanation": "`useQuery` gère cache, chargement et erreurs ; après un `POST`, `queryClient.invalidateQueries` rafraîchit la vue.",
                    "code": "const { data, isLoading, error } = useQuery({ queryKey: ['courses'], queryFn: fetchCourses });",
                    "example_title": "Query et invalidation ciblée",
                    "tip": "Structurez toujours vos clés `queryKey` avec `userId` pour isoler les sessions.",
                    "exercise_title": "Hook personnalisé `useCourses`",
                    "exercise_prompt": "Écrivez un hook combinant `useQuery` et `useMutation` avec invalidation du cache.",
                    "starter": "import { useQuery, useQueryClient } from '@tanstack/react-query';\n",
                    "hints": ["Appelez `queryClient.invalidateQueries({ queryKey: ['courses'] })` dans `onSuccess`."],
                    "concepts": ["useQuery", "invalidateQueries", "async"],
                },
                {
                    "title": "Contexte modulaire et séparation Store / Présentation",
                    "summary": "Partager l'état sans prop-drilling ni re-rendus inutiles.",
                    "explanation": "Exposez un hook typé `useModuleStore()` qui vérifie que le contexte n'est pas `null`.",
                    "code": "if (!ctx) throw new Error('useCoursesStore doit être utilisé dans CoursesStoreProvider');",
                    "example_title": "Hook de contexte sécurisé",
                    "tip": "Mémoïsez la valeur retournée au Provider.",
                    "exercise_title": "Provider typé",
                    "exercise_prompt": "Écrivez un `Context` React et son hook consommateur levant une erreur explicite hors Provider.",
                    "starter": "const Ctx = createContext<State | null>(null);\n",
                    "hints": ["Vérifiez `if (!value) throw new Error(...)` dans le hook."],
                    "concepts": ["createContext", "useContext", "Error"],
                },
                {
                    "title": "Tests d'intégration React Testing Library",
                    "summary": "Tester par rôles accessibles (`getByRole`, `getByLabelText`) comme un vrai utilisateur.",
                    "explanation": "Privilégiez `userEvent.setup()` et les requêtes par rôle/label plutôt que des classes CSS.",
                    "code": "await user.click(screen.getByRole('button', { name: 'Valider' }));",
                    "example_title": "Interaction complète avec userEvent",
                    "tip": "Ne testez pas les détails internes d'état, testez ce que l'utilisateur voit à l'écran.",
                    "exercise_title": "Test de soumission formulaire",
                    "exercise_prompt": "Écrivez un test Vitest/RTL saisissant un titre avec `user.type` et vérifiant l'affichage.",
                    "starter": "import { render, screen } from '@testing-library/react';\n",
                    "hints": ["Utilisez `getByLabelText` et `getByRole('button')`."],
                    "concepts": ["render", "screen", "getByRole", "userEvent"],
                },
            ],
            "project_title": "Module React connecté (TanStack Query + Context + tests RTL)",
            "project_brief": "### Contexte\nConstruisez un module React complet avec gestion `Loading`/`Error`, hook de contexte sécurisé et 3 tests Vitest/Testing Library.",
            "project_deliverables": [
                "Composant gérant `isLoading` et `error` avec bouton Réessayer",
                "Logique métier isolée dans un hook/store",
                "Tests RTL passant avec `userEvent`",
            ],
        },
    }


def _get_sql_specs() -> dict[int, dict[str, Any]]:
    return {
        1: {
            "prefix": "sql",
            "title": "Niveau 1 — Modélisation relationnelle & requêtes SELECT / JOIN",
            "summary": "Concevoir des tables normalisées, filtrer, trier, agréger et relier par jointures SQL.",
            "objectives": [
                "Définir clés primaires, clés étrangères et contraintes `CHECK` / `NOT NULL`",
                "Filtrer et trier avec `WHERE`, `ORDER BY` et `LIMIT`",
                "Maîtriser `INNER JOIN`, `LEFT JOIN`, `GROUP BY` et `HAVING`",
            ],
            "chapters": [
                {
                    "title": "Création de tables, types et contraintes d'intégrité",
                    "summary": "Protéger la qualité des données directement dans le moteur SQL.",
                    "explanation": "Une base fiable empêche les états invalides via `NOT NULL`, `CHECK (...)` et `FOREIGN KEY`.",
                    "code": "CREATE TABLE courses (\n  id UUID PRIMARY KEY,\n  title VARCHAR(160) NOT NULL,\n  level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 5)\n);",
                    "example_title": "Table avec contrainte CHECK",
                    "tip": "Définissez toujours `ON DELETE CASCADE` ou `SET NULL` explicitement sur vos clés étrangères.",
                    "exercise_title": "Schéma Cours & Leçons",
                    "exercise_prompt": "Écrivez les requêtes `CREATE TABLE` de `courses` et `lessons` liées par clé étrangère avec contrainte sur la position (> 0).",
                    "starter": "CREATE TABLE courses (\n  id UUID PRIMARY KEY\n);\n",
                    "hints": ["Ajoutez `REFERENCES courses(id) ON DELETE CASCADE` et `CHECK (position >= 1)`."],
                    "concepts": ["CREATE TABLE", "PRIMARY KEY", "REFERENCES", "CHECK"],
                },
                {
                    "title": "Sélection, filtrage (`WHERE`) et pagination",
                    "summary": "Ne sélectionner que les colonnes et lignes nécessaires.",
                    "explanation": "Évitez `SELECT *` en production et combinez `WHERE`, `ORDER BY` et `LIMIT/OFFSET`.",
                    "code": "SELECT id, title, level FROM courses\nWHERE status = 'active' AND level >= 1\nORDER BY updated_at DESC\nLIMIT 20;",
                    "example_title": "Requête ciblée ordonnée",
                    "tip": "Posez un index sur les colonnes filtrées fréquemment (`user_id`, `status`).",
                    "exercise_title": "Filtrer les leçons terminées",
                    "exercise_prompt": "Écrivez une requête `SELECT` retournant les 10 dernières leçons terminées pour un `user_id` donné.",
                    "starter": "SELECT id, title FROM course_lessons\nWHERE user_id = :uid\n",
                    "hints": ["Filtrez `status = 'completed'` et triez par `completed_at DESC LIMIT 10`."],
                    "concepts": ["SELECT", "WHERE", "ORDER BY", "LIMIT"],
                },
                {
                    "title": "Jointures (`INNER JOIN` vs `LEFT JOIN`)",
                    "summary": "Relier plusieurs tables sans perdre les lignes sans correspondance.",
                    "explanation": "`INNER JOIN` ne garde que les paires existantes ; `LEFT JOIN` conserve toutes les lignes de la table de gauche même s'il n'y a aucune ligne associée à droite.",
                    "code": "SELECT c.title, COUNT(l.id) AS total_lessons\nFROM courses c\nLEFT JOIN course_lessons l ON l.course_id = c.id\nGROUP BY c.id, c.title;",
                    "example_title": "Compter les leçons même sur un cours vide",
                    "tip": "Attention : avec `LEFT JOIN`, utilisez `COUNT(l.id)` et jamais `COUNT(*)` si vous voulez `0` pour les lignes sans correspondance.",
                    "exercise_title": "Cours sans aucune soumission",
                    "exercise_prompt": "Trouvez tous les cours d'un utilisateur avec le nombre de soumissions associées via `LEFT JOIN` et `GROUP BY`.",
                    "starter": "SELECT c.id, c.title\nFROM courses c\n",
                    "hints": ["Utilisez `LEFT JOIN course_submissions s ON s.course_id = c.id` puis `COUNT(s.id)`."],
                    "concepts": ["LEFT JOIN", "GROUP BY", "COUNT", "ON"],
                },
                {
                    "title": "Agrégations et filtrage de groupes (`HAVING`)",
                    "summary": "Calculer moyennes, min/max et filtrer après agrégation.",
                    "explanation": "`WHERE` filtre les lignes **avant** regroupement ; `HAVING` filtre les groupes **après** `GROUP BY`.",
                    "code": "SELECT course_id, AVG(score) AS avg_score\nFROM course_submissions\nGROUP BY course_id\nHAVING AVG(score) >= 70;",
                    "example_title": "Filtrer par moyenne minimale avec HAVING",
                    "tip": "N'utilisez `HAVING` que pour des conditions portant sur des agrégats (`AVG`, `COUNT`, `SUM`).",
                    "exercise_title": "Niveaux avec au moins 2 soumissions validées",
                    "exercise_prompt": "Écrivez une requête groupant `course_submissions` par `level_id` pour ne garder que ceux ayant `COUNT(*) >= 2` et `AVG(score) >= 70`.",
                    "starter": "SELECT level_id, COUNT(*) AS nb, AVG(score) AS moyenne\nFROM course_submissions\n",
                    "hints": ["Ajoutez `WHERE passed = TRUE` avant `GROUP BY level_id` puis `HAVING COUNT(*) >= 2`."],
                    "concepts": ["GROUP BY", "HAVING", "AVG", "COUNT"],
                },
            ],
            "project_title": "Schéma PostgreSQL complet & requêtes analytiques de suivi d'étude",
            "project_brief": "### Contexte\nConcevez un mini-schéma relationnel (3 tables liées avec contraintes CHECK et index) + 4 requêtes analytiques (`LEFT JOIN`, `GROUP BY`, `HAVING`).",
            "project_deliverables": [
                "Script `CREATE TABLE` avec PK, FK et contraintes `CHECK`",
                "Index sur clés étrangères et colonnes filtrées",
                "Requêtes `LEFT JOIN` et `GROUP BY`/`HAVING` documentées",
            ],
        },
    }


def _get_rust_or_java_specs(topic: str) -> dict[int, dict[str, Any]]:
    if topic == "rust":
        return {
            1: {
                "prefix": "rust",
                "title": "Niveau 1 — Ownership, Borrowing, Structs et Enums Rust",
                "summary": "Comprendre les règles de propriété mémoire, emprunts `&`/`&mut`, `Option`/`Result` et pattern matching.",
                "objectives": [
                    "Distinguer transfert de propriété (`move`) et emprunts (`&T`, `&mut T`)",
                    "Modéliser des données avec `struct` et `enum` + `match` exhaustif",
                    "Gérer l’absence (`Option`) et les erreurs (`Result<T, E>`) sans `unwrap()` aveugle",
                ],
                "chapters": [
                    {
                        "title": "Immutabilité par défaut et Ownership",
                        "summary": "Pourquoi chaque valeur en Rust a exactement un propriétaire unique.",
                        "explanation": "Par défaut `let x = 5;` est immuable. Avec les types alloués sur le tas (`String`), une affectation déplace (`move`) la propriété sauf si vous empruntez (`&`).",
                        "code": "fn print_len(s: &str) {\n    println!(\"{}: {}\", s, s.len());\n}\nlet title = String::from(\"Rust\");\nprint_len(&title);",
                        "example_title": "Emprunt immuable `&str` sans copier",
                        "tip": "Acceptez `&str` plutôt que `&String` dans vos signatures de fonctions pour plus de souplesse.",
                        "exercise_title": "Fonction avec emprunt sans move",
                        "exercise_prompt": "Écrivez une fonction Rust prenant `&String` ou `&str` et retournant un booléen sans consommer la variable de l'appelant.",
                        "starter": "fn is_valid_title(title: &str) -> bool {\n    false\n}\n",
                        "hints": ["Vérifiez `title.trim().len() >= 2`."],
                        "concepts": ["fn", "&str", "bool", "return"],
                    },
                    {
                        "title": "Structs, implémentations (`impl`) et constructeurs",
                        "summary": "Encapsuler état et comportement idiomatiquement.",
                        "explanation": "En Rust, les données vivent dans `struct` et les méthodes associées dans un bloc `impl`.",
                        "code": "struct Course { title: String, level: u8 }\nimpl Course {\n    fn new(title: String) -> Self { Self { title, level: 1 } }\n}",
                        "example_title": "Struct et constructeur `new`",
                        "tip": "Initialisez les entités à un état sûr (niveau 1) directement dans `new`.",
                        "exercise_title": "Struct `ScoreCard` avec méthode de réussite",
                        "exercise_prompt": "Définissez `struct ScoreCard { score: u8 }` avec une méthode `fn is_passed(&self) -> bool` (`>= 70`).",
                        "starter": "struct ScoreCard { score: u8 }\n",
                        "hints": ["Utilisez `self.score >= 70` dans `impl ScoreCard`."],
                        "concepts": ["struct", "impl", "self", "fn"],
                    },
                    {
                        "title": "`Option`, `Result` et l'opérateur `?`",
                        "summary": "Remplacer `null` et exceptions par des types explicites vérifiés à la compilation.",
                        "explanation": "`match` et `?` obligent à traiter chaque erreur possible avant de continuer.",
                        "code": "fn validate_score(v: i32) -> Result<u8, String> {\n    if (0..=100).contains(&v) { Ok(v as u8) } else { Err(\"Hors bornes\".into()) }\n}",
                        "example_title": "Validation explicite avec Result<T, E>",
                        "tip": "Évitez `.unwrap()` dans le code applicatif ; préférez `match`, `unwrap_or` ou `?`.",
                        "exercise_title": "Division sécurisée retournant Result",
                        "exercise_prompt": "Implémentez `fn safe_div(a: f64, b: f64) -> Result<f64, String>` refusant `b == 0.0`.",
                        "starter": "fn safe_div(a: f64, b: f64) -> Result<f64, String> {\n    todo!()\n}\n",
                        "hints": ["Retournez `Err(...)` si `b == 0.0`, sinon `Ok(a / b)`."],
                        "concepts": ["Result", "Ok", "Err", "fn"],
                    },
                    {
                        "title": "Itérateurs, vecteurs et tests intégrés `#[test]`",
                        "summary": "Écrire des pipelines sans allocations inutiles et les tester avec `cargo test`.",
                        "explanation": "Rust intègre nativement les tests unitaires dans chaque module via `#[cfg(test)]`.",
                        "code": "#[test]\nfn test_pass() { assert!(ScoreCard { score: 80 }.is_passed()); }",
                        "example_title": "Test unitaire intégré",
                        "tip": "Lancez `cargo test` après chaque fonction ajoutée.",
                        "exercise_title": "Module de test avec Result",
                        "exercise_prompt": "Écrivez deux tests `#[test]` vérifiant un cas `Ok(...)` et un cas `Err(...)`.",
                        "starter": "#[cfg(test)]\nmod tests {\n    use super::*;\n}\n",
                        "hints": ["Utilisez `assert!(res.is_ok())` et `assert!(bad.is_err())`."],
                        "concepts": ["test", "assert", "Result"],
                    },
                ],
                "project_title": "Outil CLI Rust de validation et calcul de notes (Result + tests)",
                "project_brief": "### Contexte\nDéveloppez un module Rust avec structs, gestion d'erreur `Result<T, String>` et suite de tests `#[test]`.",
                "project_deliverables": [
                    "Structs typées sans `unwrap()` sur entrées utilisateur",
                    "Gestion explicite `Result<T, E>`",
                    "Tests `#[test]` nominaux et d'erreur",
                ],
            }
        }
    return {
        1: {
            "prefix": "java",
            "title": "Niveau 1 — Fondations Java modernes, POO claire & Collections",
            "summary": "Maîtriser syntaxe typée, classes/records Java modernes, collections (`List`, `Map`) et exceptions.",
            "objectives": [
                "Structurer des classes, constructeurs, encapsulation et `record` Java",
                "Manipuler `List`, `Map` et itérations / Streams simples",
                "Valider les entrées via exceptions explicites et écrire des tests unitaires",
            ],
            "chapters": [
                {
                    "title": "Types, classes encapsulées et `record`",
                    "summary": "Modéliser proprement des données métier immuables ou encapsulées.",
                    "explanation": "Depuis Java 17+, les `record` éliminent le boilerplate des DTO immuables tout en permettant la validation dans le constructeur compact.",
                    "code": "public record Grade(String subject, int score) {\n  public Grade {\n    if (score < 0 || score > 100) throw new IllegalArgumentException(\"Score invalide\");\n  }\n}",
                    "example_title": "Record Java avec constructeur compact validé",
                    "tip": "Validez toujours les invariants dans le constructeur pour qu'aucun objet invalide n'existe en mémoire.",
                    "exercise_title": "Record `CourseUnit` validé",
                    "exercise_prompt": "Écrivez un `record` ou une `class` Java validant un niveau compris entre 1 et 5 via `IllegalArgumentException`.",
                    "starter": "public record CourseUnit(String title, int level) {\n}\n",
                    "hints": ["Ajoutez `if (level < 1 || level > 5) throw new IllegalArgumentException(...);`."],
                    "concepts": ["class", "IllegalArgumentException", "int", "String"],
                },
                {
                    "title": "Conditions, méthodes et gestion des cas limites",
                    "summary": "Écrire des méthodes lisibles avec retours anticipés.",
                    "explanation": "Évitez les `NullPointerException` en vérifiant les paramètres dès l'entrée de chaque méthode.",
                    "code": "public String classify(int score) {\n  if (score >= 70) return \"Validé\";\n  return \"À renforcer\";\n}",
                    "example_title": "Méthode déterministe avec seuil clair",
                    "tip": "Préférez `Objects.requireNonNull(...)` pour signaler immédiatement une référence nulle inattendue.",
                    "exercise_title": "Calcul de moyenne sécurisé",
                    "exercise_prompt": "Implémentez une méthode Java calculant la moyenne d'une `List<Integer>` et levant `IllegalArgumentException` si vide.",
                    "starter": "import java.util.List;\n",
                    "hints": ["Testez `if (scores == null || scores.isEmpty())`."],
                    "concepts": ["List", "throw", "if", "return"],
                },
                {
                    "title": "Collections (`List`, `Map`) et boucles",
                    "summary": "Regrouper et compter des éléments en temps constant.",
                    "explanation": "`Map<String, List<Integer>>` et `computeIfAbsent` simplifient le regroupement sans vérifications nulles répétées.",
                    "code": "Map<String, Integer> counts = new HashMap<>();\ncounts.merge(\"Java\", 1, Integer::sum);",
                    "example_title": "Compteur avec Map.merge",
                    "tip": "Programmez toujours contre l'interface (`List`, `Map`) plutôt que l'implémentation concrète dans les signatures.",
                    "exercise_title": "Regroupement par domaine",
                    "exercise_prompt": "Utilisez une `Map<String, Integer>` en Java pour compter le nombre de cours par domaine.",
                    "starter": "import java.util.*;\n",
                    "hints": ["Utilisez `counts.merge(domain, 1, Integer::sum)`."],
                    "concepts": ["Map", "HashMap", "List", "return"],
                },
                {
                    "title": "Tests unitaires et vérifications de contrat",
                    "summary": "Automatiser la preuve de bon fonctionnement.",
                    "explanation": "Tout code critique doit être accompagné de tests vérifiant le cas nominal et les exceptions attendues.",
                    "code": "assert classify(85).equals(\"Validé\");",
                    "example_title": "Vérification nominale et exception",
                    "tip": "Testez chaque exception métier explicitement.",
                    "exercise_title": "Classe de tests nominaux et bornes",
                    "exercise_prompt": "Écrivez un scénario de test Java couvrant note valide (80) et note invalide (-1).",
                    "starter": "// Vérification nominale et cas d'erreur\n",
                    "hints": ["Encadrez le cas invalide avec `try { ... } catch (IllegalArgumentException e) {}`."],
                    "concepts": ["try", "catch", "IllegalArgumentException", "test"],
                },
            ],
            "project_title": "Gestionnaire Java orienté objet de progression de cours",
            "project_brief": "### Contexte\nImplémentez une mini-bibliothèque Java avec classes/records validés, `Map`/`List` et scénario de tests complet.",
            "project_deliverables": [
                "Modèles Java avec validation dans les constructeurs",
                "Collections `List`/`Map` propres",
                "Tests couvrant cas nominal et `IllegalArgumentException`",
            ],
        }
    }


def _select_levels_map(subject: str, total_levels: int) -> dict[int, dict[str, Any]]:
    topic = resolve_topic_key(subject)
    if topic == "python":
        base = get_generic_levels(subject, total_levels)
        for k, v in get_python_levels().items():
            if k <= total_levels:
                base[k] = v
        return base
    if topic == "typescript":
        base = get_generic_levels(subject, total_levels)
        for k, v in get_typescript_levels().items():
            if k <= total_levels:
                base[k] = v
        return base
    if topic == "react":
        return _build_specialized_levels(
            subject=subject,
            code_lang="tsx",
            specs=_get_react_specs(),
            total_levels=total_levels,
        )
    if topic == "sql":
        return _build_specialized_levels(
            subject=subject,
            code_lang="sql",
            specs=_get_sql_specs(),
            total_levels=total_levels,
        )
    if topic in ("rust", "java"):
        return _build_specialized_levels(
            subject=subject,
            code_lang=topic,
            specs=_get_rust_or_java_specs(topic),
            total_levels=total_levels,
        )
    return get_generic_levels(subject, total_levels)


def _try_enrich_level_with_llm(
    *,
    subject: str,
    level_number: int,
    language: CourseLanguage,
    settings: Settings | None,
) -> dict[str, Any] | None:
    """Enrichit optionnellement la fiche de niveau via le fournisseur LLM configuré côté serveur, avec repli sûr."""
    if settings is None:
        return None
    from app.ai.provider import canonicalize_provider_name, normalize_provider_base_url

    provider = canonicalize_provider_name(settings.ai_provider)
    api_key = (settings.ai_api_key or "").strip()
    if not api_key or provider == "local":
        return None

    lang_text = {"fr": "français", "en": "anglais", "bilingual": "français avec termes anglais"}.get(
        language.value, "français"
    )
    prompt = (
        f"Génère un plan pédagogique JSON strict pour le niveau {level_number} d'un cours sur « {subject} » "
        f"rédigé en {lang_text}. Réponds en JSON avec les clés : "
        '{"title": "...", "summary": "...", "objectives": ["..."], "project_title": "...", "project_brief": "..."}.'
    )
    try:
        if provider == "gemini":
            model = settings.ai_model or "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            with httpx.Client(timeout=min(12.0, settings.ai_timeout_seconds)) as client:
                res = client.post(
                    url,
                    headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                    json={
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
                    },
                )
                res.raise_for_status()
                raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            model = settings.ai_model or "gpt-4o-mini"
            base_url = normalize_provider_base_url(provider, settings.ai_base_url)
            with httpx.Client(timeout=min(12.0, settings.ai_timeout_seconds)) as client:
                res = client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                    },
                )
                res.raise_for_status()
                raw_text = res.json()["choices"][0]["message"]["content"]

        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip(), flags=re.DOTALL).strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and parsed.get("title"):
            return parsed
    except Exception:
        return None
    return None


def build_course_blueprint(
    *,
    subject: str,
    title: str | None = None,
    domain: str | None = None,
    description: str | None = None,
    language: CourseLanguage = CourseLanguage.fr,
    total_levels: int = 3,
    goal: str | None = None,
) -> dict[str, Any]:
    cleaned_subject = subject.strip()
    topic_key = resolve_topic_key(cleaned_subject)
    resolved_domain = domain.strip() if domain else SUBJECT_DOMAIN_DEFAULT.get(topic_key, "Programmation & Ingénierie")
    resolved_title = title.strip() if title else f"Maîtriser {cleaned_subject} — Cours complet progressif"
    resolved_description = (
        description.strip()
        if description
        else (
            goal.strip()
            if goal
            else f"Parcours complet en {total_levels} niveaux pour apprendre {cleaned_subject} par explications progressives, exercices guidés, projets corrigés et ressources officielles."
        )
    )

    levels_map = _select_levels_map(cleaned_subject, total_levels)
    roadmap: list[dict[str, Any]] = []
    for num in range(1, total_levels + 1):
        spec = levels_map[num]
        roadmap.append(
            {
                "level_number": num,
                "title": spec["title"],
                "summary": spec["summary"],
                "objectives": list(spec["objectives"]),
                "project_title": spec["project_title"],
            }
        )

    return {
        "title": resolved_title[:160],
        "subject": cleaned_subject[:120],
        "domain": resolved_domain[:80],
        "description": resolved_description[:2000],
        "language": language,
        "total_levels": total_levels,
        "levels_roadmap": roadmap,
    }


def generate_level_content(
    *,
    subject: str,
    language: CourseLanguage,
    level_number: int,
    total_levels: int,
    settings: Settings | None = None,
) -> dict[str, Any]:
    levels_map = _select_levels_map(subject.strip(), max(total_levels, level_number))
    spec = dict(levels_map[level_number])

    llm_patch = _try_enrich_level_with_llm(
        subject=subject,
        level_number=level_number,
        language=language,
        settings=settings,
    )
    if llm_patch:
        if isinstance(llm_patch.get("summary"), str) and llm_patch["summary"].strip():
            spec["summary"] = llm_patch["summary"].strip()[:1000]
        if isinstance(llm_patch.get("project_brief"), str) and len(llm_patch["project_brief"].strip()) >= 30:
            spec["project_brief"] = llm_patch["project_brief"].strip()

    resources = get_curated_resources_for_subject(subject, language.value)
    return {
        "level_number": level_number,
        "title": spec["title"],
        "summary": spec["summary"],
        "objectives": list(spec["objectives"]),
        "lessons": list(spec["lessons"]),
        "project_title": spec["project_title"],
        "project_brief": spec["project_brief"],
        "project_deliverables": list(spec["project_deliverables"]),
        "project_rubric": default_project_rubric(level_number),
        "resources": resources,
    }


def _extract_subject_keywords(subject: str, title: str, expected_concepts: list[str]) -> set[str]:
    raw = " ".join([subject, title, *expected_concepts]).lower()
    tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9_+#-]{2,}", raw)
    stop = {"avec", "pour", "dans", "les", "des", "une", "sur", "par", "niveau", "projet"}
    return {t for t in tokens if t not in stop}


def evaluate_course_submission(
    *,
    subject: str,
    level_number: int,
    kind: CourseSubmissionKind,
    title: str,
    answer_text: str,
    submitted_code: str | None,
    reference_url: str | None,
    expected_concepts: list[str] | None = None,
    deliverables: list[str] | None = None,
) -> dict[str, Any]:
    """Corrige rigoureusement un exercice ou un projet de cours sur 100 points."""
    cleaned_text = " ".join((answer_text or "").split())
    lowered_text = cleaned_text.lower()
    code_clean = (submitted_code or "").strip()
    combined_lower = f"{lowered_text}\n{code_clean.lower()}"
    words = [w for w in re.split(r"\s+", cleaned_text) if len(w) >= 2]
    has_external_url = bool(reference_url and reference_url.strip())

    insufficient_reason = _is_blatantly_insufficient(cleaned_text, code_clean)
    concept_pool = list(expected_concepts or []) + list(deliverables or [])
    target_kws = _extract_subject_keywords(subject, title, concept_pool)
    topic_key = resolve_topic_key(subject)
    code_lang = SUBJECT_CODE_LANG.get(topic_key, "")

    matched_concepts = [kw for kw in target_kws if kw in combined_lower]
    has_artifact_kw = any(kw in combined_lower for kw in _CONCRETE_ARTIFACT_KEYWORDS)
    has_code_construct = bool(
        code_clean
        and (
            len(code_clean) >= 20
            or any(
                tok in code_clean
                for tok in ("def ", "class ", "fn ", "SELECT ", "CREATE ", "return", "=>", "{", "(")
            )
        )
    )
    has_reasoning = any(
        marker in lowered_text
        for marker in (
            "car ",
            "parce que",
            "afin de",
            "permet de",
            "donc ",
            "évite",
            "erreur",
            "exception",
            "cas limite",
            "borne",
            "test",
            "assert",
            "pytest",
            "vitest",
            "validation",
        )
    )
    has_verification_evidence = any(
        tok in combined_lower
        for tok in ("assert", "pytest", "vitest", "test", "passe", "passant", "résultat", "sortie", "0 erreur", "ok")
    )

    rubric = default_project_rubric(level_number)
    criteria_results: list[dict[str, Any]] = []
    strengths: list[str] = []
    improvements: list[str] = []

    for crit in rubric:
        key = crit["key"]
        label = crit["label"]
        max_score = int(crit["max_score"])

        if insufficient_reason is not None:
            score_val = min(4, max_score // 5) if key == "coverage" and matched_concepts else 0
            crit_passed = False
            crit_fb = insufficient_reason
        elif key == "coverage":
            concept_hits = len(matched_concepts)
            if concept_hits >= 2 or (has_artifact_kw and len(words) >= 12):
                score_val = max_score if concept_hits >= 3 else round(max_score * 0.85)
                crit_passed = True
                crit_fb = f"Notions clés de {subject} mobilisées ({', '.join(matched_concepts[:4]) or 'concepts vérifiés'})."
            elif concept_hits >= 1 or len(words) >= 10:
                score_val = round(max_score * 0.65)
                crit_passed = True
                crit_fb = f"Couverture partielle des attendus sur {subject}."
            else:
                score_val = round(max_score * 0.35)
                crit_passed = False
                crit_fb = f"Reliez explicitement votre solution aux notions attendues du chapitre ({', '.join(concept_pool[:3]) or subject})."

        elif key == "technical":
            if has_code_construct and (has_artifact_kw or len(words) >= 10):
                score_val = max_score if len(code_clean) >= 45 else round(max_score * 0.88)
                crit_passed = True
                crit_fb = "Implémentation concrète structurée et cohérente avec les attentes du niveau."
            elif has_artifact_kw and len(words) >= 15 and has_reasoning:
                score_val = round(max_score * 0.72)
                crit_passed = True
                crit_fb = "Explication technique solide ; joindre l'extrait complet du code améliorera encore votre score."
            else:
                score_val = round(max_score * 0.35)
                crit_passed = False
                crit_fb = f"Fournissez du code concret ({code_lang or subject}) ou les commandes/requêtes réellement écrites."

        elif key == "reasoning":
            if has_reasoning and len(words) >= 14:
                score_val = max_score if len(words) >= 22 else round(max_score * 0.88)
                crit_passed = True
                crit_fb = "Raisonnement clair : choix techniques et gestion des cas d'erreur explicités."
            elif len(words) >= 12:
                score_val = round(max_score * 0.65)
                crit_passed = True
                crit_fb = "Démarche compréhensible ; précisez davantage le *pourquoi* et au moins un cas limite."
            else:
                score_val = round(max_score * 0.3)
                crit_passed = False
                crit_fb = "Détaillez votre raisonnement (« parce que… ») et la gestion des entrées invalides."

        else:  # deliverables
            if has_verification_evidence and (has_code_construct or len(words) >= 12):
                score_val = max_score
                crit_passed = True
                crit_fb = "Vérifications concrètes ou jeu de tests explicitement documentés."
            elif has_code_construct or len(words) >= 14:
                score_val = round(max_score * 0.7)
                crit_passed = True
                crit_fb = "Livrable fourni ; ajoutez vos résultats d’exécution ou assertions pour atteindre 20/20."
            else:
                score_val = round(max_score * 0.35)
                crit_passed = False
                crit_fb = "Indiquez comment vous avez testé votre travail et le résultat concret observé."

        criteria_results.append(
            {
                "key": key,
                "label": label,
                "score": score_val,
                "max_score": max_score,
                "passed": crit_passed,
                "feedback": crit_fb,
            }
        )
        if crit_passed:
            strengths.append(f"{label} ({score_val}/{max_score})")
        else:
            improvements.append(f"{label} : {crit_fb}")

    total_score = max(0, min(100, sum(int(c["score"]) for c in criteria_results)))
    threshold = pass_threshold_for_course_level(level_number)
    tech_ok = any(c["key"] == "technical" and c["passed"] for c in criteria_results)
    passed = insufficient_reason is None and tech_ok and total_score >= threshold

    kind_label = "Projet" if kind == CourseSubmissionKind.project else "Exercice"
    if passed:
        next_step_hint = (
            f"{kind_label} validé ({total_score}/100, seuil {threshold}/100). "
            + (
                f"Vous pouvez maintenant valider le niveau {level_number} pour débloquer la suite."
                if kind == CourseSubmissionKind.project
                else "Passez au chapitre suivant ou attaquez le projet du niveau."
            )
        )
    else:
        next_step_hint = (
            f"Score obtenu : {total_score}/100 (seuil requis : {threshold}/100). "
            "Corrigez les points signalés (code vérifiable, cas d'erreur et justification) puis soumettez à nouveau."
        )

    fb_lines = [
        f"### Correction — {title}",
        f"**Verdict :** {'Validé' if passed else 'À renforcer'} · **Score :** `{total_score}/100` *(seuil : {threshold}/100)*",
        "",
        "| Critère | Score | Retour |",
        "| --- | --- | --- |",
    ]
    for crit in criteria_results:
        fb_lines.append(f"| {crit['label']} | {crit['score']}/{crit['max_score']} | {crit['feedback']} |")
    if has_external_url:
        fb_lines.extend(["", f"> **Transparence :** {EXTERNAL_URL_DISCLAIMER}"])

    return {
        "score": total_score,
        "passed": passed,
        "criteria_results": criteria_results,
        "feedback_markdown": "\n".join(fb_lines),
        "strengths": strengths,
        "improvements": improvements,
        "next_step_hint": next_step_hint,
    }
