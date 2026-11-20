from __future__ import annotations

import ast
from dataclasses import dataclass
import re
from typing import Any
from app.schemas.common import (
    EvidenceVerificationStatus,
    SkillAssessmentType,
    SkillEvaluationMode,
    SkillEvidenceType,
)
from app.services.sandbox_executor import verify_code_deliverable_safely

RUBRIC_VERSION = "rubric-v2"
EVALUATOR_VERSION = "eval-v2"

EXTERNAL_URL_DISCLAIMER = (
    "Référence externe non inspectée automatiquement par le serveur : la validation repose "
    "uniquement sur la production, les justifications et les résultats soumis."
)

STATIC_ANALYSIS_NOTE = (
    "Analyse statique et structurelle effectuée côté serveur sans exécution de code arbitraire."
)

_SELF_DECLARATIVE_PATTERNS = (
    re.compile(r"\bj['’]?ai\s+(bien\s+|tout\s+)?compris\b", re.IGNORECASE),
    re.compile(r"\bj['’]?ai\s+tout\s+(assimil[ée]|vu)\b", re.IGNORECASE),
    re.compile(r"\bje\s+ma[îi]trise\b", re.IGNORECASE),
    re.compile(r"\bje\s+connais\b", re.IGNORECASE),
    re.compile(r"\bc['’]?est\s+(bon|fait|acquis|ok|compris)\b", re.IGNORECASE),
    re.compile(r"\bj['’]?ai\s+(lu|vu|regard[ée]|termin[ée]|fini)\b", re.IGNORECASE),
    re.compile(r"\bje\s+sais\s+faire\b", re.IGNORECASE),
    re.compile(r"\ble[çc]on\s+termin[ée]e?\b", re.IGNORECASE),
    re.compile(r"\bi\s+(have\s+)?understood\b", re.IGNORECASE),
    re.compile(r"\bi\s+master(ed)?\b", re.IGNORECASE),
    re.compile(r"\b(completed|finished)\s+the\s+lesson\b", re.IGNORECASE),
)

_CONCRETE_ARTIFACT_KEYWORDS = (
    "def ",
    "class ",
    "function",
    "return ",
    "select ",
    "create ",
    "async ",
    "import ",
    "pytest",
    "vitest",
    "test",
    "exercice",
    "script",
    "fonction",
    "requête",
    "endpoint",
    "route",
    "algorithme",
    "correction",
    "refactor",
    "module",
    "composant",
    "résultat",
    "score",
    "erreur",
    "exception",
    "validation",
    "benchmark",
    "livrable",
    "code",
)

_FAILURE_PHRASE_PATTERNS = (
    re.compile(r"\bje\s+ne\s+sais\s+pas\b", re.IGNORECASE),
    re.compile(r"\baucune\s+id[ée]e\b", re.IGNORECASE),
    re.compile(r"\br[ée]ponse\s+incorrecte\b", re.IGNORECASE),
    re.compile(r"\bexercice\s+[ée]chou[ée]\b", re.IGNORECASE),
    re.compile(r"\bnon\s+r[ée]solu\b", re.IGNORECASE),
    re.compile(r"\bpas\s+r[ée]ussi\b", re.IGNORECASE),
    re.compile(r"\bpas\s+encore\s+fait\b", re.IGNORECASE),
    re.compile(r"\bbrouillon\s+incomplet\b", re.IGNORECASE),
    re.compile(r"\bincomplet\s*$", re.IGNORECASE),
)


@dataclass(frozen=True)
class EvidenceQualityResult:
    admissible: bool
    reason: str | None
    external_reference_verified: bool
    verification_note: str | None


@dataclass(frozen=True)
class CodeStaticAnalysisResult:
    present: bool
    valid: bool
    quality_score: int  # 0..100
    has_logic: bool
    has_error_handling: bool
    summary: str
    gaps: list[str]


@dataclass(frozen=True)
class GeneratedExercise:
    prompt_title: str
    prompt_instructions: str
    hints: list[str]
    criteria: list[dict[str, Any]]
    rubric_version: str = RUBRIC_VERSION


@dataclass(frozen=True)
class EvaluatedSubmission:
    criteria: list[dict[str, Any]]
    score: int
    passed: bool
    proposed_level: int
    feedback: str
    mastered_points: list[str]
    gaps_identified: list[str]
    remediation_recommendation: str | None
    external_verification_warning: str | None
    evaluation_mode: SkillEvaluationMode = SkillEvaluationMode.automated
    manual_review_required: bool = False
    rubric_version: str = RUBRIC_VERSION
    evaluator_version: str = EVALUATOR_VERSION


def pass_threshold_for_level(target_level: int) -> int:
    return 75 if target_level >= 4 else 70


def _balanced_delimiters(code: str) -> bool:
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack: list[str] = []
    in_str: str | None = None
    escaped = False
    for ch in code:
        if escaped:
            escaped = False
            continue
        if in_str is not None:
            if ch == "\\":
                escaped = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ("'", '"'):
            in_str = ch
        elif ch in pairs:
            stack.append(pairs[ch])
        elif ch in (")", "]", "}"):
            if not stack or stack.pop() != ch:
                return False
    return not stack and in_str is None


def analyze_code_statically(
    code: str | None,
    *,
    skill_name: str = "",
    skill_domain: str = "",
) -> CodeStaticAnalysisResult:
    """Analyse statique sûre (AST Python / structure syntaxique par langage), sans exécution."""
    cleaned = (code or "").strip()
    if not cleaned:
        return CodeStaticAnalysisResult(
            present=False,
            valid=False,
            quality_score=0,
            has_logic=False,
            has_error_handling=False,
            summary="Aucun extrait de code fourni.",
            gaps=["Aucun extrait de code fourni."],
        )

    hint_text = f"{skill_name} {skill_domain}".lower()
    is_python = any(
        tok in hint_text or tok in cleaned.lower()
        for tok in ("python", "fastapi", "sqlalchemy", "pytest", "alembic", "def ")
    ) and not any(tok in hint_text for tok in ("javascript", "typescript", "react", "java ", "rust"))
    is_sql = ("sql" in hint_text or "postgres" in hint_text) and not is_python
    is_js_ts = any(
        tok in hint_text for tok in ("javascript", "typescript", "react", "node")
    )

    if len(cleaned) < 12 or len(set(cleaned.replace(" ", ""))) < 5:
        return CodeStaticAnalysisResult(
            present=True,
            valid=False,
            quality_score=10,
            has_logic=False,
            has_error_handling=False,
            summary="Extrait de code trop court ou répétitif pour être exploitable.",
            gaps=["Code non significatif ou trivial."],
        )

    if is_python:
        try:
            tree = ast.parse(cleaned)
        except SyntaxError as exc:
            return CodeStaticAnalysisResult(
                present=True,
                valid=False,
                quality_score=15,
                has_logic=False,
                has_error_handling=False,
                summary=f"Erreur de syntaxe Python détectée (ligne {exc.lineno}).",
                gaps=[f"Erreur de syntaxe Python à la ligne {exc.lineno}."],
            )

        body_nodes = list(ast.walk(tree))
        sandbox_report = verify_code_deliverable_safely(cleaned, language_hint="python")
        if sandbox_report.is_stub_only or not sandbox_report.has_real_implementation:
            return CodeStaticAnalysisResult(
                present=True,
                valid=False,
                quality_score=20,
                has_logic=False,
                has_error_handling=False,
                summary=(
                    sandbox_report.findings[0]
                    if sandbox_report.findings
                    else "Syntaxe Python valide mais aucune logique fonctionnelle réelle détectée."
                ),
                gaps=(
                    sandbox_report.findings
                    or ["Implémentez une logique réelle (fonction non vide, condition, transformation ou appel)."]
                ),
            )

        has_error_handling = sandbox_report.has_edge_case_handling
        gaps_list: list[str] = list(sandbox_report.findings)
        if not has_error_handling:
            gaps_list.append("Ajoutez une gestion explicite des cas limites/erreurs.")
        if not sandbox_report.has_tests_or_assertions:
            gaps_list.append("Ajoutez des vérifications ou assertions (`assert`, tests) sur les résultats attendus.")

        return CodeStaticAnalysisResult(
            present=True,
            valid=True,
            quality_score=max(65, sandbox_report.quality_score),
            has_logic=True,
            has_error_handling=has_error_handling,
            summary="Syntaxe et logique Python vérifiées par analyse statique isolée (AST).",
            gaps=gaps_list,
        )

    if is_sql:
        upper = cleaned.upper()
        has_sql_stmt = any(kw in upper for kw in ("SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE ", "WITH "))
        balanced = _balanced_delimiters(cleaned)
        if not has_sql_stmt or not balanced:
            return CodeStaticAnalysisResult(
                present=True,
                valid=False,
                quality_score=25,
                has_logic=False,
                has_error_handling=False,
                summary="Requête SQL incomplète ou syntaxiquement déséquilibrée.",
                gaps=["Fournissez une requête SQL complète avec clauses valides."],
            )
        has_filter_or_join = any(kw in upper for kw in ("WHERE ", "JOIN ", "GROUP BY ", "HAVING ", "CONSTRAINT "))
        return CodeStaticAnalysisResult(
            present=True,
            valid=True,
            quality_score=95 if has_filter_or_join else 78,
            has_logic=True,
            has_error_handling=has_filter_or_join,
            summary="Structure SQL vérifiée statiquement.",
            gaps=[],
        )

    if is_js_ts:
        balanced = _balanced_delimiters(cleaned)
        has_construct = any(
            kw in cleaned for kw in ("function ", "=>", "const ", "let ", "class ", "export ", "return ")
        )
        if not balanced or not has_construct:
            return CodeStaticAnalysisResult(
                present=True,
                valid=False,
                quality_score=25,
                has_logic=False,
                has_error_handling=False,
                summary="Extrait JS/TS déséquilibré ou dépourvu de structure fonctionnelle.",
                gaps=["Corrigez la syntaxe JS/TS et incluez une fonction ou logique complète."],
            )
        has_guard = any(kw in cleaned for kw in ("if ", "if(", "try ", "catch", "throw "))
        return CodeStaticAnalysisResult(
            present=True,
            valid=True,
            quality_score=95 if has_guard else 80,
            has_logic=True,
            has_error_handling=has_guard,
            summary="Structure JS/TS validée statiquement.",
            gaps=[],
        )

    balanced = _balanced_delimiters(cleaned)
    has_generic_construct = any(
        tok in cleaned
        for tok in ("def ", "class ", "function", "fn ", "public ", "return", "=>", "SELECT ", "{", "(")
    )
    if not balanced or not has_generic_construct or len(cleaned) < 20:
        return CodeStaticAnalysisResult(
            present=True,
            valid=False,
            quality_score=30,
            has_logic=False,
            has_error_handling=False,
            summary="Extrait de code syntaxiquement déséquilibré ou incomplet.",
            gaps=["Fournissez un extrait de code complet et syntaxiquement cohérent."],
        )

    has_guard = any(tok in cleaned.lower() for tok in ("if", "try", "catch", "raise", "throw", "match ", "err"))
    return CodeStaticAnalysisResult(
        present=True,
        valid=True,
        quality_score=92 if has_guard else 78,
        has_logic=True,
        has_error_handling=has_guard,
        summary="Structure syntaxique du code vérifiée statiquement.",
        gaps=[],
    )


def validate_evidence_quality(
    evidence_type: SkillEvidenceType | str,
    description: str,
    reference_url: str | None = None,
    result: str | None = None,
    *,
    verification_status: EvidenceVerificationStatus | str | None = None,
) -> EvidenceQualityResult:
    """Vérifie qu'une preuve représente un travail concret et non une simple auto-déclaration."""
    ev_type_str = evidence_type.value if hasattr(evidence_type, "value") else str(evidence_type)
    cleaned = " ".join((description or "").split())
    lowered = cleaned.lower()
    words = [w for w in re.split(r"\s+", cleaned) if len(w) >= 2]

    has_url = bool(reference_url and reference_url.strip())
    verified_external = str(verification_status or "") in (
        EvidenceVerificationStatus.verified.value,
        EvidenceVerificationStatus.approved.value,
    )
    verification_note = (
        "Référence externe inspectée et vérifiée par le serveur."
        if verified_external
        else (EXTERNAL_URL_DISCLAIMER if has_url else None)
    )

    if len(cleaned) < 12 or len(words) < 3:
        return EvidenceQualityResult(
            admissible=False,
            reason=(
                "Preuve refusée : décrivez précisément la production réalisée "
                "(au moins 12 caractères et 3 mots concrets, ex. exercice résolu, code écrit, résultat)."
            ),
            external_reference_verified=verified_external,
            verification_note=verification_note,
        )

    matches_declarative = any(pattern.search(lowered) for pattern in _SELF_DECLARATIVE_PATTERNS)
    has_concrete_kw = any(kw in lowered for kw in _CONCRETE_ARTIFACT_KEYWORDS)
    has_concrete_result = bool(result and len(result.strip()) >= 4)

    if matches_declarative and not has_concrete_kw and not has_concrete_result:
        return EvidenceQualityResult(
            admissible=False,
            reason=(
                "Preuve insuffisante : une simple affirmation (« j'ai compris », « leçon terminée ») "
                "ne démontre pas la compétence. Décrivez l'exercice, le code ou le résultat obtenu."
            ),
            external_reference_verified=verified_external,
            verification_note=verification_note,
        )

    if matches_declarative and len(cleaned) < 40 and not has_concrete_result:
        return EvidenceQualityResult(
            admissible=False,
            reason=(
                "Preuve trop vague : détaillez ce qui a été produit, testé ou corrigé "
                "ainsi que le résultat observé."
            ),
            external_reference_verified=verified_external,
            verification_note=verification_note,
        )

    if ev_type_str in ("project", "deliverable") and len(words) < 4 and not has_url and not has_concrete_result:
        return EvidenceQualityResult(
            admissible=False,
            reason=(
                "Preuve projet/livrable incomplète : précisez les livrables produits, résultats ou URL associée."
            ),
            external_reference_verified=verified_external,
            verification_note=verification_note,
        )

    return EvidenceQualityResult(
        admissible=True,
        reason=None,
        external_reference_verified=verified_external,
        verification_note=verification_note,
    )


def default_criteria_rubric(assessment_type: SkillAssessmentType, target_level: int) -> list[dict[str, Any]]:
    _ = assessment_type
    return [
        {
            "key": "relevance",
            "label": "Pertinence par rapport à la compétence",
            "description": f"La production répond directement à l’objectif du niveau {target_level}/5.",
            "weight": 25,
            "max_score": 25,
            "score": 0,
            "passed": False,
            "feedback": "",
        },
        {
            "key": "technical_accuracy",
            "label": "Correction technique & précision",
            "description": "Exactitude du code, des concepts, des cas limites et de la terminologie.",
            "weight": 30,
            "max_score": 30,
            "score": 0,
            "passed": False,
            "feedback": "",
        },
        {
            "key": "reasoning_explanation",
            "label": "Capacité à expliquer le raisonnement",
            "description": "Justification claire des choix techniques, causes, effets ou compromis.",
            "weight": 25,
            "max_score": 25,
            "score": 0,
            "passed": False,
            "feedback": "",
        },
        {
            "key": "concrete_evidence",
            "label": "Preuve concrète et admissible",
            "description": "Production vérifiable et preuve recevable rattachées à l’utilisateur.",
            "weight": 20,
            "max_score": 20,
            "score": 0,
            "passed": False,
            "feedback": "",
        },
    ]


def build_assessment_exercise(
    *,
    skill_name: str,
    skill_domain: str,
    skill_description: str | None,
    current_level: int,
    target_level: int,
    assessment_type: SkillAssessmentType,
    previous_gaps: list[str] | None = None,
    lesson_title: str | None = None,
) -> GeneratedExercise:
    is_remediation = bool(previous_gaps)
    prefix = "Exercice correctif" if is_remediation else "Évaluation"
    prompt_title = f"{prefix} — {skill_name} (niveau {target_level}/5)"[:180]

    scope_note = (
        f"Périmètre attendu : {skill_description.strip()}."
        if skill_description and skill_description.strip()
        else f"Domaine : {skill_domain}."
    )
    lesson_note = f"\nContexte de leçon associé : « {lesson_title} »." if lesson_title else ""
    gaps_note = (
        "\nPoints à corriger en priorité suite à l’essai précédent :\n- "
        + "\n- ".join(previous_gaps[:4])
        if previous_gaps
        else ""
    )

    difficulty_guidance = {
        1: "Expliquez le concept fondamental avec vos propres mots et donnez un exemple simple et fonctionnel.",
        2: "Résolvez un exercice guidé en gérant au moins un cas nominal et un cas d’erreur.",
        3: "Produisez une implémentation autonome complète, expliquez vos choix et documentez les tests effectués.",
        4: "Analysez un cas complexe, traitez les cas limites/sécurité et justifiez les compromis d’architecture.",
        5: "Démontrez une maîtrise avancée : conception robuste, optimisation, tests et retour critique documenté.",
    }[target_level]

    type_guidance = {
        SkillAssessmentType.quiz: "Répondez précisément aux questions de compréhension et justifiez chaque réponse.",
        SkillAssessmentType.practical_exercise: "Fournissez la solution pratique, les étapes suivies et le résultat obtenu.",
        SkillAssessmentType.code_review: "Fournissez un extrait de code fonctionnel, analysez les erreurs potentielles et expliquez votre correction.",
        SkillAssessmentType.explanation: "Expliquez clairement le mécanisme interne, les cas d’usage et les pièges à éviter.",
        SkillAssessmentType.deliverable: "Décrivez le livrable produit, son architecture, ses vérifications et les résultats mesurés.",
        SkillAssessmentType.mixed: "Combinez une réponse expliquée, un exemple de code ou cas pratique et une preuve concrète.",
    }[assessment_type]

    prompt_instructions = (
        f"Compétence évaluée : {skill_name} (niveau actuel vérifié : {current_level}/5 → niveau visé : {target_level}/5).\n"
        f"{scope_note}{lesson_note}\n"
        f"Exigence du palier {target_level}/5 : {difficulty_guidance}\n"
        f"Format demandé : {type_guidance}\n"
        f"Important : associez au moins une preuve concrète et expliquez votre raisonnement (une simple affirmation ou un lien non commenté ne suffit pas)."
        f"{gaps_note}"
    )

    hints = [
        f"Indice 1 — Cadrage : commencez par définir clairement l’entrée, le traitement attendu et le critère de réussite pour « {skill_name} ».",
        "Indice 2 — Vérification : identifiez un cas nominal et un cas d’erreur (donnée invalide, borne ou exception) et expliquez comment votre solution y répond.",
        "Indice 3 — Raisonnement & preuve : précisez *pourquoi* votre approche fonctionne et joignez une preuve décrivant ce qui a été exécuté ou testé.",
    ]

    criteria = default_criteria_rubric(assessment_type, target_level)
    return GeneratedExercise(
        prompt_title=prompt_title,
        prompt_instructions=prompt_instructions,
        hints=hints,
        criteria=criteria,
        rubric_version=RUBRIC_VERSION,
    )


def _is_blatantly_insufficient(submission_text: str, submission_code: str | None) -> str | None:
    cleaned = " ".join((submission_text or "").split())
    lowered = cleaned.lower()
    code_clean = (submission_code or "").strip()

    for pattern in _FAILURE_PHRASE_PATTERNS:
        if pattern.search(lowered):
            return "La soumission exprime explicitement un blocage ou une réponse incorrecte/incomplète."

    if any(p.search(lowered) for p in _SELF_DECLARATIVE_PATTERNS) and len(cleaned) < 55 and not code_clean:
        return "La réponse se limite à une affirmation sans démonstration ni explication technique."

    words = [w for w in re.split(r"\s+", cleaned) if len(w) >= 2]
    if len(cleaned) < 25 or (len(words) < 6 and len(code_clean) < 15):
        return "La production soumise est trop courte pour évaluer une maîtrise réelle."

    unique_words = {w.lower() for w in words}
    if len(words) >= 6 and len(unique_words) <= 2:
        return "La réponse soumise est répétitive et ne contient pas d’explication exploitable."

    return None


def _skill_keywords(skill_name: str, skill_domain: str) -> set[str]:
    tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9_+#-]{3,}", f"{skill_name} {skill_domain}".lower())
    stop = {"avec", "pour", "dans", "les", "des", "une", "sur", "par"}
    return {t for t in tokens if t not in stop}


def evaluate_assessment_submission(
    *,
    skill_name: str,
    skill_domain: str,
    starting_level: int,
    target_level: int,
    assessment_type: SkillAssessmentType,
    submission_text: str,
    submission_code: str | None,
    submission_reference_url: str | None,
    evidence_records: list[Any],
    base_criteria: list[dict[str, Any]] | None = None,
    rubric_version: str = RUBRIC_VERSION,
    has_isolated_sandbox: bool = False,
) -> EvaluatedSubmission:
    """
    Évalue une soumission strictement côté serveur à partir du référentiel figé.
    N'accepte aucune note ni surcharge de critère en provenance du client.
    """
    rubric = (
        [dict(item) for item in base_criteria]
        if base_criteria
        else default_criteria_rubric(assessment_type, target_level)
    )

    admissible_evidences: list[Any] = []
    verified_external_count = 0
    has_external_url = bool(submission_reference_url and submission_reference_url.strip())
    for ev in evidence_records:
        ev_type = ev.type.value if hasattr(ev.type, "value") else str(getattr(ev, "type", "exercise"))
        desc = getattr(ev, "description", "")
        ref_url = getattr(ev, "reference_url", None)
        result = getattr(ev, "result", None)
        verif_status = getattr(ev, "verification_status", None)
        if hasattr(verif_status, "value"):
            verif_status = verif_status.value
        if ref_url:
            has_external_url = True
        quality = validate_evidence_quality(
            ev_type,
            desc,
            ref_url,
            result,
            verification_status=verif_status,
        )
        if quality.admissible:
            admissible_evidences.append(ev)
            if quality.external_reference_verified:
                verified_external_count += 1

    insufficient_reason = _is_blatantly_insufficient(submission_text, submission_code)
    cleaned_text = " ".join((submission_text or "").split())
    lowered_text = cleaned_text.lower()
    code_clean = (submission_code or "").strip()
    combined_lower = f"{lowered_text}\n{code_clean.lower()}"
    text_words = [w for w in re.split(r"\s+", cleaned_text) if len(w) >= 2]
    skill_kws = _skill_keywords(skill_name, skill_domain)
    has_topic_overlap = (
        any(kw in combined_lower for kw in skill_kws)
        or any(kw in combined_lower for kw in _CONCRETE_ARTIFACT_KEYWORDS)
    )
    has_reasoning_markers = any(
        re.search(rf"\b{re.escape(marker)}\b", lowered_text)
        for marker in (
            "car",
            "parce que",
            "donc",
            "afin de",
            "permet",
            "évite",
            "cas",
            "erreur",
            "exception",
            "avantage",
            "limite",
            "complexité",
            "test",
            "étape",
            "puisque",
        )
    )
    code_analysis = analyze_code_statically(
        code_clean,
        skill_name=skill_name,
        skill_domain=skill_domain,
    )

    evaluated_criteria: list[dict[str, Any]] = []
    mastered_points: list[str] = []
    gaps_identified: list[str] = []

    for crit in rubric:
        key = str(crit.get("key", ""))
        max_score = int(crit.get("max_score", crit.get("weight", 25)) or 25)

        if key == "concrete_evidence":
            if len(admissible_evidences) == 0:
                score_val = 0
                passed_crit = False
                crit_fb = "Aucune preuve concrète et admissible liée à cette évaluation."
            else:
                score_val = max_score if verified_external_count > 0 or not has_external_url else round(max_score * 0.9)
                passed_crit = True
                crit_fb = (
                    f"{len(admissible_evidences)} preuve(s) admissible(s) enregistrée(s) "
                    f"({verified_external_count} vérifiée(s) en externe)."
                    if has_external_url
                    else f"{len(admissible_evidences)} preuve(s) concrète(s) admissible(s) enregistrée(s)."
                )

        elif insufficient_reason is not None:
            score_val = min(5, max_score // 4) if key == "relevance" and has_topic_overlap else 0
            passed_crit = False
            crit_fb = insufficient_reason

        elif key == "relevance":
            if len(cleaned_text) >= 40 and has_topic_overlap:
                score_val = max_score
                passed_crit = True
                crit_fb = f"Production alignée avec la compétence « {skill_name} »."
            else:
                score_val = round(max_score * 0.35)
                passed_crit = False
                crit_fb = f"Réponse hors-sujet ou trop générique par rapport à la compétence « {skill_name} »."

        elif key == "technical_accuracy":
            if assessment_type in (SkillAssessmentType.practical_exercise, SkillAssessmentType.code_review):
                if code_analysis.present:
                    if code_analysis.valid and code_analysis.has_logic and (has_reasoning_markers or len(text_words) >= 10):
                        score_val = round(max_score * (code_analysis.quality_score / 100.0))
                        passed_crit = code_analysis.quality_score >= 65
                        crit_fb = f"{code_analysis.summary} {STATIC_ANALYSIS_NOTE}"
                    else:
                        score_val = round(max_score * 0.25)
                        passed_crit = False
                        crit_fb = code_analysis.summary
                else:
                    score_val = round(max_score * 0.25)
                    passed_crit = False
                    crit_fb = (
                        "Une explication théorique seule ne remplace pas une réalisation pratique : "
                        "fournissez du code ou un livrable technique vérifiable."
                    )
            else:
                if has_topic_overlap and len(text_words) >= 14 and has_reasoning_markers:
                    score_val = (
                        max_score
                        if (code_analysis.present and code_analysis.valid) or len(text_words) >= 22
                        else round(max_score * 0.85)
                    )
                    passed_crit = True
                    crit_fb = "Contenu techniquement exact et structuré."
                else:
                    score_val = round(max_score * 0.4)
                    passed_crit = False
                    crit_fb = "Manque de précision conceptuelle et de justification technique."

        elif key == "reasoning_explanation":
            if len(text_words) >= 12 and has_reasoning_markers:
                score_val = max_score if len(text_words) >= 18 else round(max_score * 0.84)
                passed_crit = True
                crit_fb = "Explication claire du raisonnement et des cas traités."
            else:
                score_val = round(max_score * 0.3)
                passed_crit = False
                crit_fb = "Raisonnement non détaillé : expliquez explicitement le pourquoi, les choix techniques et les cas limites."

        else:
            score_val = round(max_score * 0.4)
            passed_crit = False
            crit_fb = "Critère non reconnu par le référentiel serveur."

        crit_label = str(crit.get("label", key))
        evaluated_criteria.append(
            {
                "key": key,
                "label": crit_label,
                "description": str(crit.get("description", "")),
                "weight": int(crit.get("weight", max_score)),
                "max_score": max_score,
                "score": score_val,
                "passed": passed_crit,
                "feedback": crit_fb,
            }
        )
        if passed_crit:
            mastered_points.append(f"{crit_label} ({score_val}/{max_score})")
        else:
            gaps_identified.append(f"{crit_label} : {crit_fb}")

    raw_total = sum(int(c["score"]) for c in evaluated_criteria)
    raw_max = sum(int(c["max_score"]) for c in evaluated_criteria) or 100
    score = max(0, min(100, round((raw_total / raw_max) * 100)))

    evidence_crit_ok = any(c["key"] == "concrete_evidence" and bool(c["passed"]) for c in evaluated_criteria)
    tech_crit_ok = any(c["key"] == "technical_accuracy" and bool(c["passed"]) for c in evaluated_criteria)
    passed_count = sum(1 for c in evaluated_criteria if c["passed"])
    threshold = pass_threshold_for_level(target_level)

    preliminary_pass = (
        insufficient_reason is None
        and evidence_crit_ok
        and tech_crit_ok
        and passed_count >= 3
        and score >= threshold
    )

    # Si aucune exécution isolée ou inspection réelle pour les niveaux avancés / livrables,
    # ne jamais attribuer automatiquement une validation : classer en revue manuelle requise.
    needs_manual_review = False
    manual_reason: str | None = None
    if preliminary_pass and not has_isolated_sandbox:
        if assessment_type == SkillAssessmentType.deliverable and verified_external_count == 0:
            needs_manual_review = True
            manual_reason = (
                "Revue manuelle requise : ce livrable pratique n'a pas été inspecté en environnement isolé "
                "et aucune référence externe vérifiée n'est rattachée."
            )
        elif target_level >= 3 and assessment_type in (
            SkillAssessmentType.practical_exercise,
            SkillAssessmentType.code_review,
            SkillAssessmentType.mixed,
        ) and verified_external_count == 0:
            needs_manual_review = True
            manual_reason = (
                f"Revue manuelle requise pour le niveau {target_level}/5 : aucun environnement d'exécution "
                "isolé n'est configuré pour exécuter des tests automatisés sur ce travail."
            )

    if needs_manual_review:
        passed = False
        proposed_level = starting_level
        eval_mode = SkillEvaluationMode.manual_review
        if manual_reason:
            gaps_identified.append(manual_reason)
    elif preliminary_pass:
        passed = True
        # Progression strictement bornée à +1 palier à la fois
        proposed_level = min(5, starting_level + 1, target_level)
        eval_mode = SkillEvaluationMode.automated
    else:
        passed = False
        proposed_level = starting_level
        eval_mode = SkillEvaluationMode.automated

    if needs_manual_review:
        remediation = (
            "Faites inspecter le dépôt GitHub lié ou soumettez cette production à un évaluateur "
            "humain avant validation finale."
        )
    elif not passed:
        if not evidence_crit_ok:
            remediation = (
                "Associez une preuve concrète décrivant votre exercice, code ou test exécuté, "
                "puis relancez un exercice correctif."
            )
        else:
            remediation = (
                f"Réalisez un exercice correctif ciblé sur « {skill_name} » en détaillant le raisonnement, "
                "un cas d’erreur et en joignant un code valide."
            )
    else:
        remediation = None

    external_warning = EXTERNAL_URL_DISCLAIMER if has_external_url and verified_external_count == 0 else None

    if needs_manual_review:
        verdict = (
            f"Préanalyse favorable ({score}/100, seuil {threshold}/100) — revue manuelle requise "
            f"avant toute validation au niveau {target_level}/5."
        )
    elif passed:
        verdict = f"Évaluation réussie ({score}/100, seuil {threshold}/100). Niveau proposé : {proposed_level}/5."
    else:
        verdict = (
            f"Évaluation non validée ({score}/100, seuil requis {threshold}/100). "
            f"Le niveau reste à {starting_level}/5."
        )
    details = " · ".join(f"{c['label']} : {c['score']}/{c['max_score']}" for c in evaluated_criteria)
    feedback = f"{verdict}\nDétail : {details}."
    if code_analysis.present and code_analysis.valid:
        feedback = f"{feedback}\nAnalyse : {STATIC_ANALYSIS_NOTE}"
    if external_warning:
        feedback = f"{feedback}\nNote : {external_warning}"

    return EvaluatedSubmission(
        criteria=evaluated_criteria,
        score=score,
        passed=passed,
        proposed_level=proposed_level,
        feedback=feedback,
        mastered_points=mastered_points,
        gaps_identified=gaps_identified,
        remediation_recommendation=remediation,
        external_verification_warning=external_warning,
        evaluation_mode=eval_mode,
        manual_review_required=needs_manual_review,
        rubric_version=rubric_version,
        evaluator_version=EVALUATOR_VERSION,
    )
