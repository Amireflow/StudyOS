import type {
  CourseCodeExample,
  CourseCriterionResult,
  CourseDetail,
  CourseExercise,
  CourseLanguage,
  CourseLesson,
  CourseLevel,
  CoursePreview,
  CoursePreviewLesson,
  CoursePreviewLevel,
  CoursePreviewResource,
  CourseResource,
  CourseResourceType,
  CourseRubricCriterion,
  CourseSubmission,
  CourseSubmissionKind,
  CourseSummary,
} from '../../types/domain';
import type {
  CourseCreateInput,
  CoursePreviewInput,
  CourseSubmissionInput,
} from '../../lib/coursesApi';
import { generateId } from '../../lib/storage';
import { EXTERNAL_URL_DISCLAIMER } from '../skills/assessmentEngine';

export function passThresholdForCourseLevel(levelNumber: number): number {
  return levelNumber >= 4 ? 75 : 70;
}

export function defaultProjectRubric(): CourseRubricCriterion[] {
  return [
    {
      key: 'comprehension',
      label: 'Compréhension & démarche',
      description: 'Explication claire du raisonnement, des choix techniques et du fonctionnement.',
      maxScore: 25,
    },
    {
      key: 'implementation',
      label: 'Implémentation & exactitude technique',
      description: 'Code fonctionnel ou livrable concret respectant les notions clés du niveau.',
      maxScore: 35,
    },
    {
      key: 'edge_cases',
      label: 'Cas limites, erreurs & tests',
      description: 'Prise en compte des entrées invalides, erreurs et scénarios de vérification.',
      maxScore: 20,
    },
    {
      key: 'structure',
      label: 'Clarté, structure & bonnes pratiques',
      description: 'Lisibilité, découpage modulaire, nommage et documentation du livrable.',
      maxScore: 20,
    },
  ];
}

interface ResourceSeed {
  title: string;
  url: string;
  resourceType: CourseResourceType;
  language: 'fr' | 'en';
  isOfficial: boolean;
  sourceName: string;
  notes: string;
}

const CURATED_RESOURCES: Record<string, ResourceSeed[]> = {
  python: [
    {
      title: 'Documentation officielle Python (Tutoriel FR)',
      url: 'https://docs.python.org/fr/3/tutorial/',
      resourceType: 'documentation',
      language: 'fr',
      isOfficial: true,
      sourceName: 'Python Software Foundation',
      notes: 'Référence officielle progressive pour maîtriser la syntaxe et la bibliothèque standard.',
    },
    {
      title: 'Référence de la bibliothèque standard Python',
      url: 'https://docs.python.org/3/library/index.html',
      resourceType: 'documentation',
      language: 'en',
      isOfficial: true,
      sourceName: 'Python Docs',
      notes: 'Catalogue complet des modules natifs (pathlib, json, csv, dataclasses, unittest).',
    },
    {
      title: 'Python pour débutants — Tutoriel complet (vidéo FR)',
      url: 'https://www.youtube.com/watch?v=LamjAFnybo0',
      resourceType: 'video',
      language: 'fr',
      isOfficial: false,
      sourceName: 'Graven / YouTube',
      notes: 'Cours vidéo francophone progressif couvrant variables, boucles, fonctions et fichiers.',
    },
    {
      title: 'CS50P — Introduction à la programmation avec Python',
      url: 'https://cs50.harvard.edu/python/',
      resourceType: 'interactive',
      language: 'en',
      isOfficial: false,
      sourceName: 'Harvard CS50',
      notes: 'Cours vidéo universitaire et exercices progressifs guidés.',
    },
  ],
  typescript: [
    {
      title: 'TypeScript Handbook officiel',
      url: 'https://www.typescriptlang.org/docs/handbook/intro.html',
      resourceType: 'documentation',
      language: 'en',
      isOfficial: true,
      sourceName: 'Microsoft TypeScript',
      notes: 'Guide officiel sur le système de types, le narrowing et les génériques.',
    },
    {
      title: 'TypeScript Playground officiel',
      url: 'https://www.typescriptlang.org/play',
      resourceType: 'interactive',
      language: 'en',
      isOfficial: true,
      sourceName: 'TypeScript',
      notes: 'Environnement interactif dans le navigateur pour tester les inférences de types.',
    },
    {
      title: 'Apprendre TypeScript — Formation vidéo (FR)',
      url: 'https://www.youtube.com/watch?v=JR3x5e2qJ9g',
      resourceType: 'video',
      language: 'fr',
      isOfficial: false,
      sourceName: 'Grafikart / YouTube',
      notes: 'Série vidéo francophone claire pour maîtriser types, interfaces et narrowing.',
    },
    {
      title: 'Total TypeScript — TypeScript Beginners Tutorial',
      url: 'https://www.totaltypescript.com/tutorials/beginners-typescript',
      resourceType: 'interactive',
      language: 'en',
      isOfficial: false,
      sourceName: 'Total TypeScript',
      notes: 'Série d’exercices pratiques orientés erreurs réelles de typage.',
    },
  ],
  react: [
    {
      title: 'Documentation officielle React (FR)',
      url: 'https://fr.react.dev/learn',
      resourceType: 'documentation',
      language: 'fr',
      isOfficial: true,
      sourceName: 'React Team',
      notes: 'Documentation officielle moderne avec composants fonctionnels, états et effets.',
    },
    {
      title: 'Référence des Hooks React',
      url: 'https://react.dev/reference/react/hooks',
      resourceType: 'documentation',
      language: 'en',
      isOfficial: true,
      sourceName: 'React Docs',
      notes: 'Contrats précis de useState, useEffect, useMemo, useCallback et hooks personnalisés.',
    },
    {
      title: 'Formation React complète (vidéo FR)',
      url: 'https://www.youtube.com/watch?v=f0X1Tl8aHtA',
      resourceType: 'video',
      language: 'fr',
      isOfficial: false,
      sourceName: 'Grafikart / YouTube',
      notes: 'Comprendre JSX, état, formulaires contrôlés et hooks sur des cas concrets.',
    },
  ],
  sql: [
    {
      title: 'Documentation PostgreSQL — Tutoriel SQL (EN)',
      url: 'https://www.postgresql.org/docs/current/tutorial.html',
      resourceType: 'documentation',
      language: 'en',
      isOfficial: true,
      sourceName: 'PostgreSQL Global Development Group',
      notes: 'Référence SQL standard, jointures, agrégations, contraintes et index.',
    },
    {
      title: 'SQLBolt — Leçons et requêtes interactives',
      url: 'https://sqlbolt.com/',
      resourceType: 'interactive',
      language: 'en',
      isOfficial: false,
      sourceName: 'SQLBolt',
      notes: 'Exercices interactifs dans le navigateur sur SELECT, JOIN et GROUP BY.',
    },
    {
      title: 'SQL & Bases de données relationnelles (vidéo FR)',
      url: 'https://www.youtube.com/watch?v=o6P4gH48h3M',
      resourceType: 'video',
      language: 'fr',
      isOfficial: false,
      sourceName: 'YouTube FR',
      notes: 'Modélisation relationnelle, clés étrangères et requêtes analytiques expliquées pas à pas.',
    },
  ],
  rust: [
    {
      title: 'The Rust Programming Language (Le Rust Book)',
      url: 'https://doc.rust-lang.org/book/',
      resourceType: 'documentation',
      language: 'en',
      isOfficial: true,
      sourceName: 'Rust Foundation',
      notes: 'Livre officiel de référence sur ownership, borrowing, traits et gestion d’erreurs.',
    },
    {
      title: 'Rust by Example',
      url: 'https://doc.rust-lang.org/rust-by-example/',
      resourceType: 'interactive',
      language: 'en',
      isOfficial: true,
      sourceName: 'Rust Docs',
      notes: 'Exemples exécutables chapitre par chapitre.',
    },
    {
      title: 'Découvrir Rust en français (vidéo)',
      url: 'https://www.youtube.com/watch?v=Br6P_9n9g4M',
      resourceType: 'video',
      language: 'fr',
      isOfficial: false,
      sourceName: 'YouTube FR',
      notes: 'Introduction claire à Cargo, ownership et Result/Option.',
    },
  ],
  java: [
    {
      title: 'Documentation officielle Java SE (Dev.java)',
      url: 'https://dev.java/learn/',
      resourceType: 'documentation',
      language: 'en',
      isOfficial: true,
      sourceName: 'Oracle Java',
      notes: 'Tutoriels officiels sur POO, collections, streams et records.',
    },
    {
      title: 'Apprendre Java — Cours complet (vidéo FR)',
      url: 'https://www.youtube.com/watch?v=UmnCZ7-9yDY',
      resourceType: 'video',
      language: 'fr',
      isOfficial: false,
      sourceName: 'Graven / YouTube',
      notes: 'Fondamentaux Java, classes, interfaces et gestion d’exceptions.',
    },
  ],
  go: [
    {
      title: 'Documentation officielle Go — A Tour of Go',
      url: 'https://go.dev/tour/welcome/1',
      resourceType: 'interactive',
      language: 'en',
      isOfficial: true,
      sourceName: 'Go Team',
      notes: 'Visite officielle interactive de Go : slices, structs, interfaces et goroutines.',
    },
    {
      title: 'Go Documentation & Effective Go',
      url: 'https://go.dev/doc/effective_go',
      resourceType: 'documentation',
      language: 'en',
      isOfficial: true,
      sourceName: 'Go Docs',
      notes: 'Conventions idiomatiques, gestion d’erreurs explicite et concurrence.',
    },
  ],
};

function detectSubjectKey(subject: string): string {
  const lowered = subject.trim().toLowerCase();
  if (lowered.includes('python') || lowered.includes('django') || lowered.includes('fastapi')) {
    return 'python';
  }
  if (lowered.includes('typescript') || lowered === 'ts') return 'typescript';
  if (lowered.includes('react') || lowered.includes('next')) return 'react';
  if (lowered.includes('sql') || lowered.includes('postgres') || lowered.includes('mysql')) {
    return 'sql';
  }
  if (lowered.includes('rust')) return 'rust';
  if (lowered.includes('java') && !lowered.includes('javascript')) return 'java';
  if (lowered === 'go' || lowered.includes('golang')) return 'go';
  return 'generic';
}

function inferDomain(subject: string, explicitDomain?: string): string {
  if (explicitDomain?.trim()) return explicitDomain.trim();
  const key = detectSubjectKey(subject);
  if (key === 'python' || key === 'java' || key === 'go' || key === 'rust') {
    return 'Développement Backend & Systèmes';
  }
  if (key === 'typescript' || key === 'react') {
    return 'Développement Frontend & Web';
  }
  if (key === 'sql') {
    return 'Bases de données & SQL';
  }
  return 'Ingénierie & Informatique';
}

function buildGenericResources(subject: string): ResourceSeed[] {
  const encoded = encodeURIComponent(subject.trim());
  return [
    {
      title: `MDN Web Docs — Recherche « ${subject} »`,
      url: `https://developer.mozilla.org/fr/search?q=${encoded}`,
      resourceType: 'documentation',
      language: 'fr',
      isOfficial: true,
      sourceName: 'MDN Web Docs',
      notes: 'Guides de référence et articles de fond vérifiés.',
    },
    {
      title: `freeCodeCamp — Cours et guides sur ${subject}`,
      url: `https://www.freecodecamp.org/news/search/?query=${encoded}`,
      resourceType: 'video',
      language: 'en',
      isOfficial: false,
      sourceName: 'freeCodeCamp',
      notes: 'Tutoriels vidéo longs et articles pas à pas orientés projets.',
    },
    {
      title: `YouTube — Playlist d’apprentissage ${subject}`,
      url: `https://www.youtube.com/results?search_query=cours+complet+${encoded}`,
      resourceType: 'video',
      language: 'fr',
      isOfficial: false,
      sourceName: 'YouTube',
      notes: 'Conférences et ateliers pratiques pour compléter chaque chapitre.',
    },
  ];
}

function selectResourcesForLevel(
  subject: string,
  levelNumber: number,
  language: CourseLanguage,
): ResourceSeed[] {
  const key = detectSubjectKey(subject);
  const pool = CURATED_RESOURCES[key] ?? buildGenericResources(subject);
  const sorted = [...pool].sort((a, b) => {
    const aLangPref =
      language === 'fr' ? (a.language === 'fr' ? 0 : 1) : language === 'en' ? (a.language === 'en' ? 0 : 1) : 0;
    const bLangPref =
      language === 'fr' ? (b.language === 'fr' ? 0 : 1) : language === 'en' ? (b.language === 'en' ? 0 : 1) : 0;
    if (a.isOfficial !== b.isOfficial) return a.isOfficial ? -1 : 1;
    return aLangPref - bLangPref;
  });
  return levelNumber === 1 ? sorted : sorted.slice(0, 3);
}

interface LessonDraft {
  position: number;
  title: string;
  summary: string;
  estimatedMinutes: number;
  contentMarkdown: string;
  codeExamples: CourseCodeExample[];
  exercises: CourseExercise[];
}

interface LevelBlueprintDraft {
  levelNumber: number;
  title: string;
  summary: string;
  objectives: string[];
  projectTitle: string;
  projectBrief: string;
  projectDeliverables: string[];
  lessons: LessonDraft[];
}

function buildPythonLevel1(subjectLabel: string): LevelBlueprintDraft {
  return {
    levelNumber: 1,
    title: 'Fondamentaux, types et contrôle de flux',
    summary: `Maîtriser les variables typées, les structures de décision, les collections de base et l’écriture de fonctions propres en ${subjectLabel}.`,
    objectives: [
      'Déclarer et manipuler nombres, chaînes, booléens et types explicites',
      'Écrire des conditions lisibles et des boucles sans effets de bord cachés',
      'Manipuler listes et dictionnaires pour agréger des données',
      'Découper un script en fonctions pures testables',
    ],
    projectTitle: 'Analyseur CLI de relevés d’étude en Python',
    projectBrief:
      'Construisez un script Python structuré capable d’analyser une série de sessions d’étude (matière, durée, score), d’ignorer proprement les entrées invalides et de produire un bilan agrégé par matière.\n\n- **Contrainte** : découper la logique en fonctions pures testables avec annotations de type et `if __name__ == "__main__":`.\n- **Validation** : expliquez vos choix de structure de données, la gestion des lignes vides ou négatives et joignez votre code.',
    projectDeliverables: [
      'Une fonction `analyser_sessions(entrees)` typée retournant un dictionnaire agrégé',
      'Gestion explicite des durées invalides (<= 0) et chaînes vides sans crash',
      'Jeu de test minimal vérifiant au moins 2 matières et 1 cas limite',
    ],
    lessons: [
      {
        position: 1,
        title: 'Variables, types fondamentaux et f-strings',
        summary: 'Comprendre le typage dynamique, les annotations de type et le formatage clair.',
        estimatedMinutes: 30,
        contentMarkdown:
          '## Pourquoi soigner les types dès le départ\n\n' +
          'En Python, chaque valeur porte un type précis (`int`, `float`, `str`, `bool`), même si les variables ne figent pas leur type à la compilation. Ajouter des **annotations de type** rend vos fonctions immédiatement lisibles.\n\n' +
          '| Type | Usage typique | Exemple |\n' +
          '| --- | --- | --- |\n' +
          '| `int` | Compteurs, scores entiers | `niveau = 1` |\n' +
          '| `float` | Moyennes, taux de réussite | `taux = 82.5` |\n' +
          '| `str` | Libellés, identifiants texte | `sujet = "Python"` |\n' +
          '| `bool` | États binaires validés | `reussi = True` |\n\n' +
          '> Astuce : utilisez toujours les **f-strings** (`f"{nom} : {score}/100"`) plutôt que `+` avec `str(...)` : c’est plus lisible et plus rapide.\n\n' +
          '### Règles de nommage PEP 8\n' +
          '- Variables et fonctions en `snake_case`.\n' +
          '- Constantes en `MAJUSCULES`.\n' +
          '- Évitez les noms muets (`x`, `data2`) au profit d’intentions claires (`duree_minutes`).',
        codeExamples: [
          {
            title: 'Fiche récapitulative avec annotations et f-string',
            language: 'python',
            code:
              'cours: str = "Python"\n' +
              'chapitres_termines: int = 1\n' +
              'note_projet: float = 84.5\n' +
              'est_valide: bool = note_projet >= 70.0\n\n' +
              'resume = f"{cours} · Chapitre {chapitres_termines} · Score {note_projet:.1f}/100 (validé={est_valide})"\n' +
              'print(resume)',
            explanation:
              'Les annotations (`: str`, `: int`) documentent l’intention sans changer l’exécution, et `:.1f` formate proprement à une décimale.',
          },
        ],
        exercises: [
          {
            id: 'py-l1-c1-ex1',
            title: 'Calculateur de progression de chapitre',
            difficulty: 'guide',
            instructionsMarkdown:
              'Écrivez un bloc Python calculant `pourcentage = (termines / total) * 100` en évitant la division par zéro quand `total == 0`, puis formatez une synthèse avec une f-string.',
            starterCode:
              'termines: int = 3\ntotal: int = 4\n# Calculez taux puis affichez : "Progression : 75.0 %"',
            hints: [
              'Utilisez une expression conditionnelle `if total > 0 else 0.0` avant la division.',
              'Formatez avec `f"Progression : {taux:.1f} %"` pour garder une décimale.',
            ],
            expectedConcepts: ['if', 'else', 'total', 'f"', 'return', 'print'],
          },
          {
            id: 'py-l1-c1-ex2',
            title: 'Nettoyage d’une entrée texte brute',
            difficulty: 'pratique',
            instructionsMarkdown:
              'Écrivez une fonction `normaliser_titre(brut: str) -> str` qui supprime les espaces superflus autour et normalise la casse proprement sans modifier une chaîne vide.',
            starterCode: 'def normaliser_titre(brut: str) -> str:\n    pass',
            hints: [
              'Combinez `.strip()` pour nettoyer les bords et `" ".join(brut.split())` pour condenser les espaces internes.',
            ],
            expectedConcepts: ['def ', 'strip', 'split', 'return'],
          },
        ],
      },
      {
        position: 2,
        title: 'Conditions, garde-fous et boucles maîtrisées',
        summary: 'Éliminer l’imbrication excessive grâce aux retours anticipés et à enumerate.',
        estimatedMinutes: 35,
        contentMarkdown:
          '## Préférer les garde-fous aux pyramides de `if`\n\n' +
          'Une fonction difficile à lire empile 4 niveaux d’indentation. Le motif **guard clause** (retour anticipé) valide les cas invalides tout en haut de la fonction.\n\n' +
          '> Attention : vérifiez toujours `is None` avec `is` et jamais avec `==`, car un objet personnalisé peut surcharger `==`.\n\n' +
          '### Boucles idiomatiques en Python\n' +
          '- Préférez `for index, element in enumerate(items, start=1):` à `for i in range(len(items)):`.\n' +
          '- Utilisez `while` uniquement lorsque le nombre d’itérations est inconnu à l’avance, avec une condition de sortie garantie.',
        codeExamples: [
          {
            title: 'Garde-fou propre vs imbrication profonde',
            language: 'python',
            code:
              'def evaluer_note(score: int | None) -> str:\n' +
              '    if score is None:\n' +
              '        return "Non évalué"\n' +
              '    if score < 0 or score > 100:\n' +
              '        raise ValueError("Le score doit être compris entre 0 et 100")\n' +
              '    if score >= 70:\n' +
              '        return "Validé"\n' +
              '    return "À retravailler"',
            explanation:
              'Chaque cas invalide ou final sort immédiatement de la fonction : zéro `else` inutile, lecture linéaire.',
          },
        ],
        exercises: [
          {
            id: 'py-l1-c2-ex1',
            title: 'Somme filtrée des minutes d’étude',
            difficulty: 'guide',
            instructionsMarkdown:
              'Écrivez `total_minutes_valides(durees: list[int]) -> int` qui ignore les valeurs `<= 0` et retourne la somme des durées strictement positives.',
            starterCode: 'def total_minutes_valides(durees: list[int]) -> int:\n    pass',
            hints: ['Utilisez `if d <= 0: continue` ou une compréhension `[d for d in durees if d > 0]`.'],
            expectedConcepts: ['def ', 'for ', 'if ', 'return'],
          },
        ],
      },
      {
        position: 3,
        title: 'Listes, dictionnaires et ensembles',
        summary: 'Choisir la bonne collection selon l’opération dominante (accès, unicité, ordre).',
        estimatedMinutes: 40,
        contentMarkdown:
          '## Quelle structure de données choisir ?\n\n' +
          '| Collection | Ordonnée | Doublons | Cas idéal |\n' +
          '| --- | --- | --- | --- |\n' +
          '| `list` | Oui | Autorisés | Séquence d’éléments, file chronologique |\n' +
          '| `dict` | Oui | Clés uniques | Indexation par clé (`id -> objet`), comptages |\n' +
          '| `set` | Non | Interdits | Test d’appartenance rapide en $O(1)$ |\n' +
          '| `tuple` | Oui (immuable) | Autorisés | Retours multiples, paires fixes |\n\n' +
          '> Astuce : utilisez `compteur.get(cle, 0) + 1` sur un dictionnaire pour éviter toute erreur `KeyError`.',
        codeExamples: [
          {
            title: 'Agrégation par matière avec dictionnaire',
            language: 'python',
            code:
              'seances = [("Python", 45), ("SQL", 30), ("Python", 25)]\n' +
              'minutes_par_sujet: dict[str, int] = {}\n\n' +
              'for sujet, duree in seances:\n' +
              '    minutes_par_sujet[sujet] = minutes_par_sujet.get(sujet, 0) + duree\n\n' +
              'print(minutes_par_sujet)  # {"Python": 70, "SQL": 30}',
            explanation:
              'Le déballage `(sujet, duree)` dans le `for` rend la boucle expressive et évite `item[0]` / `item[1]`.',
          },
        ],
        exercises: [
          {
            id: 'py-l1-c3-ex1',
            title: 'Indexation de cours par domaine',
            difficulty: 'pratique',
            instructionsMarkdown:
              'Écrivez `compter_occurrences(mots: list[str]) -> dict[str, int]` ignorant les chaînes vides après `.strip()`.',
            starterCode: 'def compter_occurrences(mots: list[str]) -> dict[str, int]:\n    pass',
            hints: ['Nettoyez chaque mot avec `.strip().lower()`, ignorez si vide, puis incrémentez `.get(mot, 0) + 1`.'],
            expectedConcepts: ['def ', 'dict', 'for ', 'get', 'return'],
          },
        ],
      },
      {
        position: 4,
        title: 'Fonctions pures, exceptions et tests unitaires simples',
        summary: 'Séparer calcul pur et affichage, lever des erreurs explicites et tester avec assert.',
        estimatedMinutes: 40,
        contentMarkdown:
          '## Concevoir une fonction fiable\n\n' +
          'Une bonne fonction **calcule et retourne** un résultat plutôt que d’afficher avec `print()` en son sein. Vous pouvez ainsi la réutiliser dans une API, un script CLI et un test unitaire.\n\n' +
          '### Gérer les exceptions au bon niveau\n' +
          '- Levez `ValueError` quand un argument métier est incohérent.\n' +
          '- Ne capturez **jamais** `except Exception:` en silence (`pass`), journalisez ou transformez explicitement l’erreur.\n' +
          '- Protégez le point d’entrée par `if __name__ == "__main__":` pour permettre l’import sans exécution involontaire.',
        codeExamples: [
          {
            title: 'Fonction testable avec assert intégré',
            language: 'python',
            code:
              'def moyenne(notes: list[float]) -> float:\n' +
              '    if not notes:\n' +
              '        raise ValueError("La liste de notes ne peut pas être vide")\n' +
              '    return sum(notes) / len(notes)\n\n' +
              'assert moyenne([80.0, 90.0]) == 85.0',
            explanation:
              'La précondition explicite protège contre `ZeroDivisionError` avec un message métier clair.',
          },
        ],
        exercises: [
          {
            id: 'py-l1-c4-ex1',
            title: 'Fonction robuste avec jeu de tests',
            difficulty: 'defi',
            instructionsMarkdown:
              'Implémentez `calculer_reussite(scores: list[int], seuil: int = 70) -> dict[str, int | float]` qui retourne `{"total": ..., "reussis": ..., "taux": ...}` et gérez le cas liste vide.',
            starterCode: 'def calculer_reussite(scores: list[int], seuil: int = 70) -> dict:\n    pass',
            hints: ['Si `not scores`, retournez `{"total": 0, "reussis": 0, "taux": 0.0}` ou levez `ValueError`.'],
            expectedConcepts: ['def ', 'return', 'assert', 'len', 'if '],
          },
        ],
      },
    ],
  };
}

function buildPythonLevelN(levelNumber: number): LevelBlueprintDraft {
  if (levelNumber === 2) {
    return {
      levelNumber: 2,
      title: 'Modularité, fichiers, JSON et gestion d’erreurs',
      summary: 'Structurer un projet multi-modules avec pathlib, JSON, dataclasses et tests automatisés.',
      objectives: [
        'Manipuler les chemins et fichiers avec pathlib et encoding="utf-8"',
        'Sérialiser et valider des données JSON / CSV',
        'Modéliser des entités métier avec @dataclass',
        'Écrire des tests unitaires isolés',
      ],
      projectTitle: 'Gestionnaire persistant de fiches de révision JSON',
      projectBrief:
        'Créez un module Python qui lit et sauvegarde des fiches de révision dans un fichier JSON via `pathlib.Path`, valide chaque fiche avec une `@dataclass` et filtre les fiches à revoir.',
      projectDeliverables: [
        'Dataclass `FicheRevision` avec validation de champ dans `__post_init__`',
        'Fonctions `charger_fiches(chemin)` et `sauvegarder_fiches(chemin, fiches)` gérant le fichier absent',
        'Tests `pytest` ou `unittest` couvrant ajout, sauvegarde et fichier manquant',
      ],
      lessons: [
        {
          position: 1,
          title: 'Manipulation sûre de fichiers avec pathlib',
          summary: 'Lire et écrire des fichiers portables sous Windows, macOS et Linux.',
          estimatedMinutes: 35,
          contentMarkdown:
            '## Pourquoi pathlib remplace os.path\n\n`Path("dossier") / "fichier.json"` construit des chemins portables et explicites. Spécifiez toujours `encoding="utf-8"` lors des lectures/écritures sous Windows.\n\n> Astuce : utilisez le bloc `with path.open("r", encoding="utf-8") as f:` pour fermer le fichier même si une exception survient.',
          codeExamples: [
            {
              title: 'Lecture JSON tolérante à l’absence du fichier',
              language: 'python',
              code:
                'from pathlib import Path\nimport json\n\n' +
                'def lire_json(chemin: Path) -> list[dict]:\n' +
                '    if not chemin.exists():\n' +
                '        return []\n' +
                '    return json.loads(chemin.read_text(encoding="utf-8"))',
              explanation: 'Vérifier `.exists()` évite un crash au premier démarrage de l’application.',
            },
          ],
          exercises: [
            {
              id: 'py-l2-c1-ex1',
              title: 'Sauvegarde JSON atomique simple',
              difficulty: 'guide',
              instructionsMarkdown: 'Écrivez `ecrire_json(chemin: Path, data: list[dict]) -> None` qui crée le dossier parent si absent (`mkdir(parents=True, exist_ok=True)`).',
              starterCode: 'from pathlib import Path\nimport json\n\ndef ecrire_json(chemin: Path, data: list[dict]) -> None:\n    pass',
              hints: ['Appelez `chemin.parent.mkdir(parents=True, exist_ok=True)` puis `chemin.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")`.'],
              expectedConcepts: ['Path', 'mkdir', 'json.dumps', 'utf-8'],
            },
          ],
        },
        {
          position: 2,
          title: 'Modélisation métier avec dataclasses',
          summary: 'Remplacer les dictionnaires fragiles par des structures typées.',
          estimatedMinutes: 35,
          contentMarkdown:
            '## Sortir du « dictly-typed code »\n\nLes dictionnaires sans schéma cachent les fautes de frappe (`"titre"` vs `"title"`). `@dataclass` génère `__init__`, `__repr__` et l’égalité automatiquement.',
          codeExamples: [
            {
              title: 'Dataclass validée avec __post_init__',
              language: 'python',
              code:
                'from dataclasses import dataclass\n\n@dataclass(slots=True)\nclass SessionEtude:\n    sujet: str\n    minutes: int\n\n    def __post_init__(self) -> None:\n        if self.minutes <= 0:\n            raise ValueError("minutes doit être positif")',
              explanation: '`slots=True` réduit l’empreinte mémoire et empêche l’ajout accidentel d’attributs inconnus.',
            },
          ],
          exercises: [
            {
              id: 'py-l2-c2-ex1',
              title: 'Modèle CarteMemoire',
              difficulty: 'pratique',
              instructionsMarkdown: 'Créez une dataclass `CarteMemoire(question: str, reponse: str, niveau: int = 1)` qui refuse une question vide ou un niveau hors `[1, 5]`.',
              starterCode: 'from dataclasses import dataclass\n\n@dataclass\nclass CarteMemoire:\n    question: str\n    reponse: str\n    niveau: int = 1',
              hints: ['Ajoutez `def __post_init__(self) -> None:` et vérifiez `if not self.question.strip(): raise ValueError(...)`.'],
              expectedConcepts: ['dataclass', '__post_init__', 'raise ValueError'],
            },
          ],
        },
        {
          position: 3,
          title: 'Compréhensions, générateurs et tri clé',
          summary: 'Écrire des transformations de collections concises et économes en mémoire.',
          estimatedMinutes: 35,
          contentMarkdown:
            '## Lisibilité avant tout\n\nUne compréhension `[x for x in items if x.actif]` est excellente sur 1 condition. Au-delà de deux conditions imbriquées, revenez à une boucle `for` claire ou à une fonction nommée.',
          codeExamples: [
            {
              title: 'Trier des objets par priorité puis nom',
              language: 'python',
              code:
                'taches_triees = sorted(taches, key=lambda t: (-t.priorite, t.titre.lower()))',
              explanation: 'Le tuple clé permet un tri multi-critères déterministe en une ligne.',
            },
          ],
          exercises: [
            {
              id: 'py-l2-c3-ex1',
              title: 'Extraction et tri des cours actifs',
              difficulty: 'guide',
              instructionsMarkdown: 'Écrivez une expression retournant les titres triés des cours dont `statut == "active"`.',
              starterCode: 'def titres_actifs(cours: list[dict]) -> list[str]:\n    pass',
              hints: ['Utilisez `sorted(c["title"] for c in cours if c.get("status") == "active")`.'],
              expectedConcepts: ['sorted', 'for ', 'if ', 'return'],
            },
          ],
        },
        {
          position: 4,
          title: 'Tests unitaires et découpage en modules',
          summary: 'Fiabiliser le code avec pytest / unittest et tmp_path.',
          estimatedMinutes: 40,
          contentMarkdown:
            '## Tester avant de passer au niveau suivant\n\nUn test vérifie un contrat précis (nominal + cas limite) en moins de quelques millisecondes grâce aux fixtures temporaires (`tmp_path`).',
          codeExamples: [
            {
              title: 'Test pytest avec tmp_path',
              language: 'python',
              code:
                'def test_ecriture_lecture(tmp_path):\n' +
                '    cible = tmp_path / "memo.json"\n' +
                '    ecrire_json(cible, [{"sujet": "Python"}])\n' +
                '    assert lire_json(cible) == [{"sujet": "Python"}]',
              explanation: '`tmp_path` crée un répertoire temporaire isolé supprimé après les tests.',
            },
          ],
          exercises: [
            {
              id: 'py-l2-c4-ex1',
              title: 'Test de cas d’erreur attendu',
              difficulty: 'pratique',
              instructionsMarkdown: 'Écrivez un test vérifiant qu’un `ValueError` est bien levé lorsqu’une session a une durée `0` ou négative.',
              starterCode: 'import pytest\n\ndef test_session_duree_invalide():\n    pass',
              hints: ['Utilisez `with pytest.raises(ValueError): SessionEtude("Python", 0)`.'],
              expectedConcepts: ['def test_', 'pytest.raises', 'ValueError'],
            },
          ],
        },
      ],
    };
  }

  return buildAdaptiveLevelN('Python', levelNumber, levelNumber >= 4 ? 'Architecture, asynchronisme & qualité logicielle' : 'POO, design patterns & API');
}

function buildTypeScriptLevel1(subjectLabel: string): LevelBlueprintDraft {
  return {
    levelNumber: 1,
    title: 'Système de types, interfaces et narrowing strict',
    summary: `Exploiter l’inférence, les unions discriminées et le mode strict de ${subjectLabel} pour éliminer les bugs à la compilation.`,
    objectives: [
      'Configurer et lire les types primitifs, littéraux et inférés',
      'Modéliser des données avec type, interface et readonly',
      'Maîtriser les unions discriminées et le type narrowing',
      'Éviter any grâce à unknown et aux type guards',
    ],
    projectTitle: 'Moteur typé de validation de tâches d’étude en TypeScript',
    projectBrief:
      'Écrivez un module TypeScript strict modélisant des tâches (`todo`, `done`, `parked`) avec une union discriminée pour les transitions d’état, une fonction de comptage sans `any`, et au moins un type guard vérifiant des données `unknown`.',
    projectDeliverables: [
      'Interfaces/types stricts avec `readonly` et union discriminée',
      'Type guard `isTaskPayload(raw: unknown): raw is ...` sans assertion `as any`',
      'Explication écrite du narrowing appliqué dans votre code',
    ],
    lessons: [
      {
        position: 1,
        title: 'Inférence, types littéraux et interdiction de any',
        summary: 'Laisser TypeScript inférer ce qui est évident et typer explicitement les frontières.',
        estimatedMinutes: 30,
        contentMarkdown:
          '## `unknown` vs `any` : la règle d’or\n\n`any` désactive le compilateur sur toute la chaîne d’appels. À l’inverse, `unknown` accepte toute valeur en entrée mais vous oblige à vérifier sa forme avant de l’utiliser.\n\n> Attention : activer `"strict": true` dans `tsconfig.json` active notamment `strictNullChecks`, indispensable pour éviter `Cannot read properties of undefined`.',
        codeExamples: [
          {
            title: 'Typage des paramètres et valeur de retour',
            language: 'typescript',
            code:
              'type Priority = "low" | "normal" | "high";\n\n' +
              'export function scorePriority(priority: Priority): number {\n' +
              '  if (priority === "high") return 3;\n' +
              '  if (priority === "normal") return 2;\n' +
              '  return 1;\n' +
              '}',
            explanation: 'Un type union littéral empêche toute faute de frappe dès l’édition.',
          },
        ],
        exercises: [
          {
            id: 'ts-l1-c1-ex1',
            title: 'Type guard sûr sur donnée inconnue',
            difficulty: 'guide',
            instructionsMarkdown: 'Écrivez `extractNonEmptyString(value: unknown): string | null` qui vérifie `typeof value === "string"` et retourne la chaîne nettoyée ou `null`.',
            starterCode: 'export function extractNonEmptyString(value: unknown): string | null {\n  // TODO\n}',
            hints: ['Testez `if (typeof value !== "string") return null;` puis utilisez `.trim()`.'],
            expectedConcepts: ['unknown', 'typeof', 'string', 'null', 'return'],
          },
        ],
      },
      {
        position: 2,
        title: 'Interfaces, types d’objets et readonly',
        summary: 'Décrire des contrats clairs et prévenir les mutations accidentelles.',
        estimatedMinutes: 35,
        contentMarkdown:
          '## Contrats d’objets immuables\n\nAnnoter vos propriétés importantes en `readonly` garantit à la compilation qu’une fonction de lecture ou de rendu ne modifie pas le tableau ou l’objet reçu.',
        codeExamples: [
          {
            title: 'Interface CourseSummary avec tableau readonly',
            language: 'typescript',
            code:
              'export interface CourseCard {\n' +
              '  readonly id: string;\n' +
              '  title: string;\n' +
              '  readonly tags: readonly string[];\n' +
              '}',
            explanation: '`readonly string[]` interdit `.push()` sur le tableau dans les fonctions purement lectrices.',
          },
        ],
        exercises: [
          {
            id: 'ts-l1-c2-ex1',
            title: 'Modèle d’exercice typé',
            difficulty: 'pratique',
            instructionsMarkdown: 'Définissez une interface `StudyTask` avec `id: string`, `title: string`, `minutes: number` et une fonction pure `addMinutes(tasks: readonly StudyTask[]): number`.',
            starterCode: 'export interface StudyTask {\n  id: string;\n  title: string;\n  minutes: number;\n}',
            hints: ['Utilisez `tasks.reduce((sum, item) => sum + Math.max(0, item.minutes), 0)`.'],
            expectedConcepts: ['interface', 'readonly', 'reduce', 'number'],
          },
        ],
      },
      {
        position: 3,
        title: 'Unions discriminées et contrôle d’exhaustivité',
        summary: 'Modéliser les états métier sans champs optionnels ambigus.',
        estimatedMinutes: 40,
        contentMarkdown:
          '## Rendre les états impossibles non représentables\n\nAu lieu d’un objet `{ loading: boolean; error?: string; data?: T }`, préférez une union discriminée sur le champ `status` : TypeScript réduit automatiquement les propriétés disponibles dans chaque branche `switch`.',
        codeExamples: [
          {
            title: 'Union discriminée pour résultat d’évaluation',
            language: 'typescript',
            code:
              'type GradeState =\n' +
              '  | { kind: "pending" }\n' +
              '  | { kind: "passed"; score: number }\n' +
              '  | { kind: "failed"; score: number; reason: string };\n\n' +
              'function summarize(state: GradeState): string {\n' +
              '  switch (state.kind) {\n' +
              '    case "pending": return "En attente";\n' +
              '    case "passed": return `Validé (${state.score}/100)`;\n' +
              '    case "failed": return `Échec (${state.score}/100) : ${state.reason}`;\n' +
              '  }\n' +
              '}',
            explanation: 'Dans `case "failed"`, `state.reason` est garanti défini sans `!` ni `?.`.',
          },
        ],
        exercises: [
          {
            id: 'ts-l1-c3-ex1',
            title: 'Union d’actions sur un cours',
            difficulty: 'pratique',
            instructionsMarkdown: 'Créez un type union `CourseAction` (`start`, `complete_lesson`, `validate_level`) avec `switch` exhaustif utilisant `never`.',
            starterCode: 'function assertNever(x: never): never {\n  throw new Error(`Cas inattendu: ${String(x)}`);\n}',
            hints: ['Ajoutez un champ discriminant `type` sur chaque variante et appelez `assertNever(action)` dans `default:`.'],
            expectedConcepts: ['type ', 'switch', 'never', 'case '],
          },
        ],
      },
      {
        position: 4,
        title: 'Génériques essentiels et Utility Types',
        summary: 'Écrire des fonctions réutilisables avec T, Pick, Omit et Record.',
        estimatedMinutes: 40,
        contentMarkdown:
          '## Écrire moins de code grâce aux génériques\n\n`Record<K, V>`, `Pick<T, Keys>` et `Omit<T, Keys>` dérivent de nouveaux types à partir d’un modèle unique sans duplication.',
        codeExamples: [
          {
            title: 'Fonction générique indexBy',
            language: 'typescript',
            code:
              'export function groupCount<T extends string>(items: readonly T[]): Record<string, number> {\n' +
              '  const acc: Record<string, number> = {};\n' +
              '  for (const item of items) acc[item] = (acc[item] ?? 0) + 1;\n' +
              '  return acc;\n' +
              '}',
            explanation: 'Le paramètre générique `<T extends string>` contraint l’entrée tout en restant souple.',
          },
        ],
        exercises: [
          {
            id: 'ts-l1-c4-ex1',
            title: 'Patch partiel typé',
            difficulty: 'defi',
            instructionsMarkdown: 'Écrivez `updateEntity<T extends { id: string }>(items: readonly T[], id: string, patch: Partial<Omit<T, "id">>): T[]` qui met à jour sans muter.',
            starterCode: 'export function updateEntity<T extends { id: string }>(items: readonly T[], id: string, patch: Partial<Omit<T, "id">>): T[] {\n  // TODO\n}',
            hints: ['Utilisez `items.map((item) => (item.id === id ? { ...item, ...patch } : item))`.'],
            expectedConcepts: ['Partial', 'Omit', 'map', 'return'],
          },
        ],
      },
    ],
  };
}

function buildAdaptiveLevelN(
  subject: string,
  levelNumber: number,
  customTitle?: string,
): LevelBlueprintDraft {
  const codeLang =
    detectSubjectKey(subject) === 'sql'
      ? 'sql'
      : detectSubjectKey(subject) === 'rust'
        ? 'rust'
        : detectSubjectKey(subject) === 'java'
          ? 'java'
          : detectSubjectKey(subject) === 'go'
            ? 'go'
            : detectSubjectKey(subject) === 'typescript' || detectSubjectKey(subject) === 'react'
              ? 'typescript'
              : 'python';

  const levelTitles: Record<number, string> = {
    1: `Fondamentaux essentiels et premier modèle en ${subject}`,
    2: `Structuration, modularité et gestion d’erreurs en ${subject}`,
    3: `Asynchronisme, persistance et tests automatisés en ${subject}`,
    4: `Architecture modulaire, performance et qualité en ${subject}`,
    5: `Projet de synthèse avancé et mise en production ${subject}`,
  };

  const title = customTitle ? `${customTitle} (${subject})` : levelTitles[levelNumber] ?? `Niveau ${levelNumber} — ${subject}`;
  const threshold = passThresholdForCourseLevel(levelNumber);

  const chapterThemes = [
    {
      title: `Concepts clés et syntaxe idiomatique (Niveau ${levelNumber})`,
      summary: `Poser les bases conceptuelles exactes du niveau ${levelNumber} en ${subject}.`,
      focus: 'modélisation claire, invariants et lisibilité',
      call: 'Astuce : privilégiez toujours des exemples minimaux exécutables que vous comprenez ligne par ligne avant d’abstraire.',
    },
    {
      title: `Structuration des données et logique métier`,
      summary: `Organiser les structures de données et isoler les règles métier.`,
      focus: 'contrats explicites et découplage',
      call: 'Attention : ne mélangez jamais validation des entrées, calcul métier et affichage ou accès base dans une même fonction monolithique.',
    },
    {
      title: `Cas limites, robustesse et diagnostics`,
      summary: `Identifier les erreurs fréquentes et protéger les frontières de votre code.`,
      focus: 'validation des entrées, messages d’erreur exploitables et tests',
      call: 'Important : testez systématiquement le cas vide, le cas nul et les valeurs hors bornes.',
    },
    {
      title: `Atelier guidé de préparation au projet`,
      summary: `Assembler les compétences du niveau ${levelNumber} sur un scénario concret.`,
      focus: 'architecture du mini-projet, jeux d’essai et relecture',
      call: 'Conseil : avant d’écrire la première ligne du projet, listez les entrées, sorties attendues et critères de réussite.',
    },
  ];

  const lessons: LessonDraft[] = chapterThemes.map((theme, idx) => {
    const pos = idx + 1;
    const sampleCode =
      codeLang === 'sql'
        ? `-- Exemple Niveau ${levelNumber} · Chapitre ${pos}\nSELECT domaine, COUNT(*) AS nb_cours\nFROM cours\nWHERE statut = 'active'\nGROUP BY domaine\nORDER BY nb_cours DESC;`
        : codeLang === 'typescript'
          ? `// Exemple ${subject} · Niveau ${levelNumber}.${pos}\nexport interface StepResult {\n  readonly valid: boolean;\n  readonly score: number;\n  readonly note: string;\n}\n\nexport function checkThreshold(score: number, min = ${threshold}): StepResult {\n  return {\n    valid: score >= min,\n    score,\n    note: score >= min ? "Seuil atteint" : "Révision requise",\n  };\n}`
          : codeLang === 'rust'
            ? `// Exemple Rust · Niveau ${levelNumber}.${pos}\npub fn evaluer_seuil(score: u8, min: u8) -> Result<&'static str, &'static str> {\n    if score > 100 {\n        return Err("Score invalide");\n    }\n    if score >= min { Ok("Validé") } else { Ok("À retravailler") }\n}`
            : `# Exemple ${subject} · Niveau ${levelNumber}.${pos}\ndef evaluer_etape(nom: str, score: int, seuil: int = ${threshold}) -> dict:\n    if not nom.strip():\n        raise ValueError("Le nom d'étape est obligatoire")\n    return {\n        "etape": nom.strip(),\n        "reussi": score >= seuil,\n        "score": score,\n    }`;

    return {
      position: pos,
      title: theme.title,
      summary: theme.summary,
      estimatedMinutes: 30 + idx * 5,
      contentMarkdown:
        `## Objectif du chapitre ${pos}\n\n` +
        `Ce chapitre développe **${theme.focus}** dans le cadre de **${subject}** (Niveau ${levelNumber}).\n\n` +
        `### Points essentiels à maîtriser\n` +
        `- Identifier clairement les entrées attendues et les invariants à préserver.\n` +
        `- Vérifier les cas limites avant d’implémenter le flux principal.\n` +
        `- Écrire un exemple court et vérifiable pour valider chaque hypothèse.\n\n` +
        `> ${theme.call}\n\n` +
        `### Grille d’auto-contrôle rapide\n` +
        `| Critère | Vérification |\n` +
        `| --- | --- |\n` +
        `| Clarté | Les noms expriment l’intention métier |\n` +
        `| Robustesse | Les cas vides ou invalides sont traités explicitement |\n` +
        `| Testabilité | La logique principale peut être testée isolément |`,
      codeExamples: [
        {
          title: `Modèle appliqué — ${theme.title}`,
          language: codeLang,
          code: sampleCode,
          explanation: `Illustre un contrat explicite avec validation des préconditions et retour structuré en ${subject}.`,
        },
      ],
      exercises: [
        {
          id: `${detectSubjectKey(subject)}-l${levelNumber}-c${pos}-ex1`,
          title: `Mise en pratique — ${theme.title}`,
          difficulty: pos <= 2 ? 'guide' : 'pratique',
          instructionsMarkdown:
            `Implémentez une fonction ou requête en **${subject}** répondant au thème **« ${theme.title} »** : traitez explicitement au moins un cas nominal et un cas d’erreur.`,
          starterCode: sampleCode,
          hints: [
            'Commencez par valider les entrées nulles, vides ou hors bornes en début de traitement.',
            'Ajoutez un commentaire court expliquant pourquoi votre structure garantit la robustesse.',
          ],
          expectedConcepts: ['return', 'if', 'test', subject.toLowerCase()],
        },
      ],
    };
  });

  return {
    levelNumber,
    title,
    summary: `Consolider ${subject} au niveau ${levelNumber} via quatre chapitres structurés et un projet noté à ${threshold}/100.`,
    objectives: [
      `Comprendre et appliquer les concepts du niveau ${levelNumber} en ${subject}`,
      'Justifier ses choix d’architecture et anticiper les cas limites',
      `Produire un mini-projet fonctionnel évalué à au moins ${threshold}/100`,
    ],
    projectTitle: `Mini-projet Niveau ${levelNumber} : Livrable pratique ${subject}`,
    projectBrief:
      `Réalisez un livrable concret en **${subject}** mettant en œuvre les notions des 4 chapitres du Niveau ${levelNumber}.\n\n` +
      `- **Seuil de validation** : **${threshold}/100** minimum.\n` +
      `- **Attendu** : décrivez votre démarche technique, les cas limites gérés, et joignez l’extrait de code ou les requêtes produites.`,
    projectDeliverables: [
      `Code ou livrable structuré en ${subject} couvrant le flux nominal et les erreurs`,
      'Explication écrite des choix techniques et d’au moins deux cas de test',
    ],
    lessons,
  };
}

function buildLevelDraft(
  subject: string,
  levelNumber: number,
): LevelBlueprintDraft {
  const key = detectSubjectKey(subject);
  if (key === 'python') {
    return levelNumber === 1 ? buildPythonLevel1(subject) : buildPythonLevelN(levelNumber);
  }
  if (key === 'typescript' && levelNumber === 1) {
    return buildTypeScriptLevel1(subject);
  }
  return buildAdaptiveLevelN(subject, levelNumber);
}

export function previewCourseLocal(input: CoursePreviewInput): CoursePreview {
  const subject = input.subject.trim();
  const totalLevels = Math.min(5, Math.max(2, input.totalLevels ?? 3));
  const language: CourseLanguage = input.language ?? 'fr';
  const domain = inferDomain(subject, input.domain);
  const title = input.title?.trim() || `Maîtriser ${subject} — Parcours complet`;
  const description =
    input.goal?.trim() ||
    `Cours progressif en ${totalLevels} niveaux pour apprendre ${subject} avec leçons formatées, exemples commentés, exercices et projets corrigés.`;

  const roadmap: CoursePreviewLevel[] = [];
  let level1Draft: LevelBlueprintDraft | null = null;

  for (let lvl = 1; lvl <= totalLevels; lvl += 1) {
    const draft = buildLevelDraft(subject, lvl);
    if (lvl === 1) level1Draft = draft;
    roadmap.push({
      levelNumber: draft.levelNumber,
      title: draft.title,
      summary: draft.summary,
      objectives: draft.objectives,
      projectTitle: draft.projectTitle,
    });
  }

  const first = level1Draft!;
  const firstLessons: CoursePreviewLesson[] = first.lessons.map((l) => ({
    position: l.position,
    title: l.title,
    summary: l.summary,
    estimatedMinutes: l.estimatedMinutes,
    contentMarkdown: l.contentMarkdown,
    codeExamples: l.codeExamples,
    exercises: l.exercises,
  }));

  const firstResources: CoursePreviewResource[] = selectResourcesForLevel(
    subject,
    1,
    language,
  ).map((r) => ({
    title: r.title,
    url: r.url,
    resourceType: r.resourceType,
    language: r.language,
    isOfficial: r.isOfficial,
    sourceName: r.sourceName,
    notes: r.notes,
  }));

  return {
    title,
    subject,
    domain,
    description,
    language,
    totalLevels,
    levelsRoadmap: roadmap,
    firstLevelLessons: firstLessons,
    firstLevelProjectTitle: first.projectTitle,
    firstLevelProjectBrief: first.projectBrief,
    firstLevelProjectDeliverables: first.projectDeliverables,
    firstLevelResources: firstResources,
  };
}

function materializeLevel(
  userId: string,
  courseId: string,
  subject: string,
  language: CourseLanguage,
  levelNumber: number,
  unlocked: boolean,
  nowIso: string,
): { level: CourseLevel; resources: CourseResource[] } {
  const draft = buildLevelDraft(subject, levelNumber);
  const levelId = generateId();
  const rubric = defaultProjectRubric();

  const lessons: CourseLesson[] = unlocked
    ? draft.lessons.map((l) => ({
        id: generateId(),
        userId,
        courseId,
        levelId,
        position: l.position,
        title: l.title,
        summary: l.summary,
        estimatedMinutes: l.estimatedMinutes,
        contentMarkdown: l.contentMarkdown,
        codeExamples: l.codeExamples,
        exercises: l.exercises,
        status: 'not_started',
        completedAt: null,
        createdAt: nowIso,
        updatedAt: nowIso,
      }))
    : [];

  const resources: CourseResource[] = unlocked
    ? selectResourcesForLevel(subject, levelNumber, language).map((r) => ({
        id: generateId(),
        userId,
        courseId,
        levelId,
        lessonId: null,
        title: r.title,
        url: r.url,
        resourceType: r.resourceType,
        language: r.language,
        isOfficial: r.isOfficial,
        sourceName: r.sourceName,
        notes: r.notes,
        createdAt: nowIso,
        updatedAt: nowIso,
      }))
    : [];

  return {
    level: {
      id: levelId,
      userId,
      courseId,
      levelNumber,
      title: draft.title,
      summary: draft.summary,
      objectives: draft.objectives,
      status: unlocked ? 'unlocked' : 'locked',
      contentGenerated: unlocked,
      projectTitle: draft.projectTitle,
      projectBrief: unlocked ? draft.projectBrief : null,
      projectDeliverables: unlocked ? draft.projectDeliverables : [],
      projectRubric: rubric,
      validatedAt: null,
      lessons,
      resources,
      submissions: [],
      passThreshold: passThresholdForCourseLevel(levelNumber),
      projectPassed: false,
      createdAt: nowIso,
      updatedAt: nowIso,
    },
    resources,
  };
}

export function createCourseDetailLocal(
  userId: string,
  input: CourseCreateInput,
  skillId: string | null = null,
): CourseDetail {
  const nowIso = new Date().toISOString();
  const courseId = generateId();
  const preview = previewCourseLocal(input);
  const description = input.description?.trim() || preview.description;

  const levels: CourseLevel[] = [];
  const allResources: CourseResource[] = [];

  for (let lvl = 1; lvl <= preview.totalLevels; lvl += 1) {
    const unlocked = lvl === 1;
    const { level, resources } = materializeLevel(
      userId,
      courseId,
      preview.subject,
      preview.language,
      lvl,
      unlocked,
      nowIso,
    );
    levels.push(level);
    allResources.push(...resources);
  }

  return {
    id: courseId,
    userId,
    title: preview.title,
    subject: preview.subject,
    domain: preview.domain,
    description,
    language: preview.language,
    currentLevel: 1,
    totalLevels: preview.totalLevels,
    status: 'active',
    skillId,
    learningPathId: null,
    completedLessonsCount: 0,
    totalLessonsCount: levels[0]?.lessons.length ?? 0,
    resourcesCount: allResources.length,
    createdAt: nowIso,
    updatedAt: nowIso,
    levels,
    resources: allResources,
  };
}

export function summarizeCourse(detail: CourseDetail): CourseSummary {
  const allLessons = detail.levels.flatMap((lv) => lv.lessons);
  const completedLessonsCount = allLessons.filter((l) => l.status === 'completed').length;
  return {
    id: detail.id,
    userId: detail.userId,
    title: detail.title,
    subject: detail.subject,
    domain: detail.domain,
    description: detail.description,
    language: detail.language,
    currentLevel: detail.currentLevel,
    totalLevels: detail.totalLevels,
    status: detail.status,
    skillId: detail.skillId,
    learningPathId: detail.learningPathId,
    completedLessonsCount,
    totalLessonsCount: allLessons.length,
    resourcesCount: detail.resources.length,
    createdAt: detail.createdAt,
    updatedAt: detail.updatedAt,
  };
}

const DECLARATIVE_PATTERNS = [
  /\bj['’]?ai\s+(bien\s+)?compris\b/i,
  /\bje\s+ma[îi]trise\b/i,
  /\bje\s+connais\b/i,
  /\bc['’]?est\s+(bon|fait|acquis|ok|compris|fini)\b/i,
  /\bj['’]?ai\s+(lu|vu|regard[ée]|termin[ée]|fini)\b/i,
  /\bje\s+sais\s+faire\b/i,
  /\ble[çc]on\s+termin[ée]e?\b/i,
  /\bje\s+ne\s+sais\s+pas\b/i,
  /\baucune\s+id[ée]e\b/i,
  /\bbrouillon\s+incomplet\b/i,
];

const CODE_MARKERS = [
  'def ',
  'class ',
  'function',
  'const ',
  'let ',
  'return ',
  'select ',
  'import ',
  'export ',
  'interface ',
  'if ',
  'for ',
  'switch',
  'assert',
  'raise ',
  'fn ',
  'pub ',
  '=>',
];

const EDGE_CASE_KEYWORDS = [
  'erreur',
  'exception',
  'invalide',
  'vide',
  'null',
  'none',
  'undefined',
  'valueerror',
  'edge',
  'limite',
  'test',
  'assert',
  'try',
  'catch',
  'raise',
  'vérifi',
  'cas ',
];

export function evaluateCourseSubmissionLocal(params: {
  course: CourseDetail;
  level: CourseLevel;
  submissionKind: CourseSubmissionKind;
  input: CourseSubmissionInput;
}): CourseSubmission {
  const { course, level, submissionKind, input } = params;
  const nowIso = new Date().toISOString();
  const answer = input.answerText.trim();
  const code = input.submittedCode?.trim() || '';
  const combinedLower = `${answer}\n${code}`.toLowerCase();
  const threshold = submissionKind === 'project' ? level.passThreshold : 65;

  const isDeclarative = DECLARATIVE_PATTERNS.some((rx) => rx.test(answer));
  const codeHits = CODE_MARKERS.filter((m) => combinedLower.includes(m)).length;
  const edgeHits = EDGE_CASE_KEYWORDS.filter((k) => combinedLower.includes(k)).length;
  const words = answer.split(/\s+/).filter((w) => w.length >= 2);
  const hasRealCode = code.length >= 24 && codeHits >= 1;

  const rubric =
    level.projectRubric.length > 0 ? level.projectRubric : defaultProjectRubric();

  let criteriaResults: CourseCriterionResult[] = [];
  let totalScore = 0;
  let passed = false;
  const strengths: string[] = [];
  const improvements: string[] = [];
  let nextStepHint = '';

  if ((isDeclarative && !hasRealCode) || words.length < 4 || answer.length < 18) {
    criteriaResults = rubric.map((c) => ({
      key: c.key,
      label: c.label,
      score: Math.min(5, Math.round(c.maxScore * 0.2)),
      maxScore: c.maxScore,
      passed: false,
      feedback:
        'Explication purement déclarative ou insuffisante : décrivez votre logique technique réelle et fournissez un extrait concret.',
    }));
    totalScore = criteriaResults.reduce((acc, c) => acc + c.score, 0);
    passed = false;
    improvements.push(
      'Remplacer les formulations déclaratives par une explication concrète des fonctions, types et cas limites traités.',
    );
    if (!hasRealCode) {
      improvements.push('Joindre un extrait de code ou de livrable vérifiable dans la zone de code.');
    }
    nextStepHint =
      'Relisez les chapitres du niveau, exécutez votre solution sur 2 entrées (normale + invalide) et soumettez le code avec votre démarche.';
  } else {
    const compScore = Math.min(
      rubric[0]?.maxScore ?? 25,
      Math.round(
        (words.length >= 20 ? 0.92 : words.length >= 10 ? 0.8 : 0.6) *
          (rubric[0]?.maxScore ?? 25),
      ),
    );
    const implRatio = hasRealCode
      ? codeHits >= 3
        ? 0.94
        : 0.82
      : code.length >= 12
        ? 0.68
        : 0.48;
    const implScore = Math.min(
      rubric[1]?.maxScore ?? 35,
      Math.round(implRatio * (rubric[1]?.maxScore ?? 35)),
    );
    const edgeRatio = edgeHits >= 2 ? 0.9 : edgeHits >= 1 ? 0.72 : 0.4;
    const edgeScore = Math.min(
      rubric[2]?.maxScore ?? 20,
      Math.round(edgeRatio * (rubric[2]?.maxScore ?? 20)),
    );
    const structRatio =
      answer.length >= 60 && (code.includes('\n') || answer.includes('\n')) ? 0.9 : 0.75;
    const structScore = Math.min(
      rubric[3]?.maxScore ?? 20,
      Math.round(structRatio * (rubric[3]?.maxScore ?? 20)),
    );

    const scores = [compScore, implScore, edgeScore, structScore];
    criteriaResults = rubric.map((c, idx) => {
      const s = scores[idx] ?? Math.round(c.maxScore * 0.7);
      const critPassed = s >= Math.round(c.maxScore * 0.65);
      return {
        key: c.key,
        label: c.label,
        score: s,
        maxScore: c.maxScore,
        passed: critPassed,
        feedback: critPassed
          ? `Critère validé (${s}/${c.maxScore}) : éléments concrets présents.`
          : `À renforcer (${s}/${c.maxScore}) : précisez davantage ce point avec un exemple ou cas limite.`,
      };
    });

    totalScore = criteriaResults.reduce((acc, c) => acc + c.score, 0);
    passed = totalScore >= threshold;

    if (words.length >= 10) strengths.push('Démarche technique expliquée de manière compréhensible.');
    if (hasRealCode) strengths.push('Code ou livrable concret fourni à l’appui.');
    if (edgeHits >= 1) strengths.push('Attention portée aux cas limites ou à la validation.');

    if (!hasRealCode) {
      improvements.push('Ajoutez l’extrait de code complet pour consolider le critère d’implémentation.');
    }
    if (edgeHits === 0) {
      improvements.push('Explicitez au moins un cas d’erreur ou d’entrée vide et la réaction attendue.');
    }
    nextStepHint = passed
      ? submissionKind === 'project'
        ? `Projet approuvé (${totalScore}/100 >= ${threshold}/100) : vous pouvez maintenant cliquer sur « Valider le niveau ${level.levelNumber} » pour débloquer la suite.`
        : 'Exercice validé : passez à l’exercice suivant ou au projet de fin de niveau.'
      : `Score ${totalScore}/100 inférieur au seuil (${threshold}/100) : enrichissez les points listés puis soumettez à nouveau.`;
  }

  const externalNote = input.referenceUrl?.trim() ? `\n\n> Note : ${EXTERNAL_URL_DISCLAIMER}` : '';
  const feedbackMarkdown =
    `### Correction (${submissionKind === 'project' ? 'Projet du niveau' : 'Exercice'}) : **${totalScore}/100**\n\n` +
    (passed
      ? `**Résultat : Validé** (seuil requis : ${threshold}/100).`
      : `**Résultat : À retravailler** (seuil requis : ${threshold}/100).`) +
    externalNote;

  return {
    id: generateId(),
    userId: course.userId,
    courseId: course.id,
    levelId: level.id,
    lessonId: input.lessonId ?? null,
    submissionKind,
    exerciseId: input.exerciseId ?? null,
    title:
      input.title?.trim() ||
      (submissionKind === 'project'
        ? level.projectTitle || `Projet Niveau ${level.levelNumber}`
        : `Exercice Niveau ${level.levelNumber}`),
    answerText: answer,
    submittedCode: code || null,
    referenceUrl: input.referenceUrl?.trim() || null,
    status: 'evaluated',
    score: totalScore,
    passed,
    criteriaResults,
    feedbackMarkdown,
    strengths,
    improvements,
    nextStepHint,
    createdAt: nowIso,
    updatedAt: nowIso,
  };
}

export function validateCourseLevelLocal(
  course: CourseDetail,
  levelId: string,
): { updated: CourseDetail; error?: string } {
  const targetIdx = course.levels.findIndex((lv) => lv.id === levelId);
  if (targetIdx === -1) {
    return { updated: course, error: 'Niveau introuvable dans ce cours.' };
  }
  const target = course.levels[targetIdx];
  if (target.status === 'locked') {
    return {
      updated: course,
      error: 'Ce niveau est encore verrouillé : validez d’abord le niveau précédent.',
    };
  }
  if (!target.projectPassed) {
    return {
      updated: course,
      error: `Impossible de valider le niveau ${target.levelNumber} : le projet doit d’abord atteindre au moins ${target.passThreshold}/100.`,
    };
  }

  const nowIso = new Date().toISOString();
  const nextLevels = course.levels.map((lv) => ({ ...lv }));
  nextLevels[targetIdx] = {
    ...target,
    status: 'validated',
    validatedAt: nowIso,
    updatedAt: nowIso,
  };

  let nextResources = [...course.resources];
  let nextCurrentLevel = course.currentLevel;
  let nextStatus = course.status;

  if (targetIdx + 1 < nextLevels.length) {
    const nextLv = nextLevels[targetIdx + 1];
    nextCurrentLevel = nextLv.levelNumber;
    if (!nextLv.contentGenerated || nextLv.status === 'locked') {
      const materialized = materializeLevel(
        course.userId,
        course.id,
        course.subject,
        course.language,
        nextLv.levelNumber,
        true,
        nowIso,
      );
      nextLevels[targetIdx + 1] = {
        ...materialized.level,
        id: nextLv.id,
        lessons: materialized.level.lessons.map((l) => ({ ...l, levelId: nextLv.id })),
        resources: materialized.level.resources.map((r) => ({ ...r, levelId: nextLv.id })),
      };
      const existingUrls = new Set(nextResources.map((r) => r.url.trim().toLowerCase()));
      const newCourseResources = materialized.resources
        .map((r) => ({ ...r, levelId: nextLv.id }))
        .filter((r) => !existingUrls.has(r.url.trim().toLowerCase()));
      nextResources = [...nextResources, ...newCourseResources];
    }
  } else {
    nextStatus = 'completed';
  }

  const nextAllLessons = nextLevels.flatMap((lv) => lv.lessons);
  const updated: CourseDetail = {
    ...course,
    currentLevel: nextCurrentLevel,
    status: nextStatus,
    levels: nextLevels,
    resources: nextResources,
    completedLessonsCount: nextAllLessons.filter((l) => l.status === 'completed').length,
    totalLessonsCount: nextAllLessons.length,
    resourcesCount: nextResources.length,
    updatedAt: nowIso,
  };

  return { updated };
}
