from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
from app.schemas.common import SkillAssessmentType, SkillEvidenceType

EXTERNAL_URL_DISCLAIMER = (
    "Référence externe non inspectée automatiquement par le serveur : la validation repose "
    "uniquement sur la production, les justifications et les résultats soumis."
)

_SELF_DECLARATIVE_PATTERNS = (
    re.compile(r"\bj['’]?ai\s+(bien\s+)?compris\b", re.IGNORECASE),
    re.compile(r"\bje\s+ma[îi]trise\b", re.IGNORECASE),
    re.compile(r"\bje\s+connais\b", re.IGNORECASE),
    re.compile(r"\bc['’]?est\s+(bon|fait|acquis|ok|compris)\b", re.IGNORECASE),
    re.compile(r"\bj['’]?ai\s+(lu|vu|regard[ée]|termin[ée]|fini)\b", re.IGNORECASE),
    re.compile(r"\bje\s+sais\s+faire\b", re.IGNORECASE),
    re.compile(r"\ble[çc]on\s+termin[ée]e?\b", re.IGNORECASE),
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
class GeneratedExercise:
    prompt_title: str
    prompt_instructions: str
    hints: list[str]
    criteria: list[dict[str, Any]]


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


def pass_threshold_for_level(target_level: int) -> int:
    return 75 if target_level >= 4 else 70


def validate_evidence_quality(
    evidence_type: SkillEvidenceType | str,
    description: str,
    reference_url: str | None = None,
    result: str | None = None,
) -> EvidenceQualityResult:
    """Vérifie qu'une preuve représente un travail concret et non une simple auto-déclaration."""
    _ = evidence_type
    cleaned = " ".join((description or "").split())
    lowered = cleaned.lower()
    words = [w for w in re.split(r"\s+", cleaned) if len(w) >= 2]

    has_url = bool(reference_url and reference_url.strip())
    verification_note = EXTERNAL_URL_DISCLAIMER if has_url else None

    if len(cleaned) < 12 or len(words) < 3:
        return EvidenceQualityResult(
            admissible=False,
            reason=(
                "Preuve refusée : décrivez précisément la production réalisée "
                "(au moins 12 caractères et 3 mots concrets, ex. exercice résolu, code écrit, résultat)."
            ),
            external_reference_verified=False,
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
            external_reference_verified=False,
            verification_note=verification_note,
        )

    if matches_declarative and len(cleaned) < 40 and not has_concrete_result:
        return EvidenceQualityResult(
            admissible=False,
            reason=(
                "Preuve trop vague : détaillez ce qui a été produit, testé ou corrigé "
                "ainsi que le résultat observé."
            ),
            external_reference_verified=False,
            verification_note=verification_note,
        )

    return EvidenceQualityResult(
        admissible=True,
        reason=None,
        external_reference_verified=False,
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

    word_count = len([w for w in re.split(r"\s+", cleaned) if len(w) >= 2])
    if len(cleaned) < 25 or (word_count < 6 and len(code_clean) < 15):
        return "La production soumise est trop courte pour évaluer une maîtrise réelle."

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
    criteria_overrides: list[dict[str, Any]] | None = None,
    explicit_feedback: str | None = None,
    explicit_mastered: list[str] | None = None,
    explicit_gaps: list[str] | None = None,
    explicit_remediation: str | None = None,
) -> EvaluatedSubmission:
    rubric = (
        [dict(item) for item in base_criteria]
        if base_criteria
        else default_criteria_rubric(assessment_type, target_level)
    )
    overrides_by_key = {
        str(item["key"]): item for item in (criteria_overrides or []) if "key" in item
    }

    admissible_evidences: list[Any] = []
    has_external_url = bool(submission_reference_url and submission_reference_url.strip())
    for ev in evidence_records:
        ev_type = ev.type.value if hasattr(ev.type, "value") else str(getattr(ev, "type", "exercise"))
        desc = getattr(ev, "description", "")
        ref_url = getattr(ev, "reference_url", None)
        result = getattr(ev, "result", None)
        if ref_url:
            has_external_url = True
        quality = validate_evidence_quality(ev_type, desc, ref_url, result)
        if quality.admissible:
            admissible_evidences.append(ev)

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
        marker in lowered_text
        for marker in (
            "car ",
            "parce que",
            "donc ",
            "afin de",
            "permet de",
            "évite",
            "cas ",
            "erreur",
            "exception",
            "avantage",
            "limite",
            "complexité",
            "test",
            "étape",
        )
    )
    has_code_construct = bool(
        code_clean
        and (
            len(code_clean) >= 20
            or any(tok in code_clean for tok in ("def ", "class ", "return", "=>", "SELECT ", "async ", "{", "("))
        )
    )

    evaluated_criteria: list[dict[str, Any]] = []
    mastered_points: list[str] = []
    gaps_identified: list[str] = []

    for crit in rubric:
        key = str(crit.get("key", ""))
        max_score = int(crit.get("max_score", crit.get("weight", 25)) or 25)
        override = overrides_by_key.get(key)

        if key == "concrete_evidence":
            if len(admissible_evidences) == 0:
                score_val = 0
                passed_crit = False
                crit_fb = "Aucune preuve concrète et admissible liée à cette évaluation."
            else:
                if override is not None:
                    score_val = max(0, min(max_score, int(override.get("score", max_score))))
                    passed_crit = bool(override.get("passed", score_val >= int(max_score * 0.6)))
                    crit_fb = str(
                        override.get("feedback")
                        or f"{len(admissible_evidences)} preuve(s) admissible(s) associée(s)."
                    )
                else:
                    score_val = max_score
                    passed_crit = True
                    crit_fb = f"{len(admissible_evidences)} preuve(s) concrète(s) vérifiée(s) sur votre compte."

        elif insufficient_reason is not None:
            score_val = min(5, max_score // 4) if key == "relevance" and has_topic_overlap else 0
            passed_crit = False
            crit_fb = insufficient_reason

        elif override is not None:
            score_val = max(0, min(max_score, int(override.get("score", 0))))
            passed_crit = bool(override.get("passed", score_val >= int(max_score * 0.6)))
            crit_fb = str(override.get("feedback") or "Critère évalué selon la grille.")

        elif key == "relevance":
            if len(cleaned_text) >= 40 and has_topic_overlap:
                score_val = max_score
                passed_crit = True
                crit_fb = f"Production alignée avec la compétence « {skill_name} »."
            elif len(cleaned_text) >= 35:
                score_val = round(max_score * 0.68)
                passed_crit = True
                crit_fb = "Réponse globalement pertinente mais lien explicite à renforcer."
            else:
                score_val = round(max_score * 0.35)
                passed_crit = False
                crit_fb = "Réponse trop générique par rapport à la compétence ciblée."

        elif key == "technical_accuracy":
            if assessment_type in (SkillAssessmentType.practical_exercise, SkillAssessmentType.code_review):
                if has_code_construct and (has_reasoning_markers or len(text_words) >= 10):
                    score_val = max_score
                    passed_crit = True
                    crit_fb = "Code et éléments techniques cohérents avec le niveau visé."
                elif has_topic_overlap and len(text_words) >= 12 and has_reasoning_markers:
                    score_val = round(max_score * 0.8)
                    passed_crit = True
                    crit_fb = "Raisonnement technique solide ; ajouter du code vérifiable renforcerait encore la note."
                else:
                    score_val = round(max_score * 0.4) if len(text_words) >= 8 else round(max_score * 0.2)
                    passed_crit = False
                    crit_fb = "Éléments techniques ou extrait de code insuffisants pour démontrer la correction."
            else:
                if has_topic_overlap and len(text_words) >= 12:
                    score_val = max_score if has_code_construct or len(text_words) >= 18 else round(max_score * 0.85)
                    passed_crit = True
                    crit_fb = "Contenu techniquement exact et structuré."
                else:
                    score_val = round(max_score * 0.4)
                    passed_crit = False
                    crit_fb = "Manque de précision technique dans la réponse."

        elif key == "reasoning_explanation":
            if len(text_words) >= 12 and has_reasoning_markers:
                score_val = max_score if len(text_words) >= 18 else round(max_score * 0.84)
                passed_crit = True
                crit_fb = "Explication claire du raisonnement et des cas traités."
            elif len(text_words) >= 10:
                score_val = round(max_score * 0.68)
                passed_crit = True
                crit_fb = "Explication recevable ; justifiez davantage le *pourquoi* et les cas limites."
            else:
                score_val = round(max_score * 0.3)
                passed_crit = False
                crit_fb = "Raisonnement non détaillé : expliquez comment vous obtenez ce résultat."

        else:
            score_val = round(max_score * 0.7) if len(text_words) >= 10 else round(max_score * 0.3)
            passed_crit = score_val >= round(max_score * 0.6)
            crit_fb = "Critère évalué."

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

    passed = (
        insufficient_reason is None
        and evidence_crit_ok
        and tech_crit_ok
        and passed_count >= 3
        and score >= threshold
    )

    if passed:
        if score >= 85 or target_level <= starting_level + 1:
            proposed_level = target_level
        else:
            proposed_level = min(target_level, starting_level + 1)
    else:
        proposed_level = starting_level

    final_mastered = explicit_mastered if explicit_mastered is not None else mastered_points
    final_gaps = explicit_gaps if explicit_gaps is not None else gaps_identified

    if explicit_remediation is not None:
        remediation = explicit_remediation
    elif not passed:
        if not evidence_crit_ok:
            remediation = (
                "Associez une preuve concrète décrivant votre exercice, code ou test exécuté, "
                "puis relancez un exercice correctif."
            )
        else:
            remediation = (
                f"Réalisez un exercice correctif ciblé sur « {skill_name} » en détaillant le raisonnement, "
                "un cas d’erreur et en joignant le code/résultat vérifié."
            )
    else:
        remediation = None

    external_warning = EXTERNAL_URL_DISCLAIMER if has_external_url else None

    if explicit_feedback:
        feedback = explicit_feedback.strip()
    else:
        verdict = (
            f"Évaluation réussie ({score}/100, seuil {threshold}/100). Niveau proposé : {proposed_level}/5."
            if passed
            else f"Évaluation non validée ({score}/100, seuil requis {threshold}/100). Le niveau reste à {starting_level}/5."
        )
        details = " · ".join(f"{c['label']} : {c['score']}/{c['max_score']}" for c in evaluated_criteria)
        feedback = f"{verdict}\nDétail : {details}."
        if external_warning:
            feedback = f"{feedback}\nNote : {external_warning}"

    return EvaluatedSubmission(
        criteria=evaluated_criteria,
        score=score,
        passed=passed,
        proposed_level=proposed_level,
        feedback=feedback,
        mastered_points=final_mastered,
        gaps_identified=final_gaps,
        remediation_recommendation=remediation,
        external_verification_warning=external_warning,
    )
