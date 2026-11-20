from datetime import date, datetime, timedelta, timezone
import json
import re
import time
from typing import Any, Protocol
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel, Field
from app.ai.context_builder import BoundedUserContext
from app.ai.prompt_manager import PromptManager
from app.core.config import Settings
from app.core.errors import AppError
from app.core.ssrf import (
    MAX_AI_RESPONSE_BYTES,
    safe_http_request,
    validate_model_identifier,
    validate_outbound_url,
)
from app.schemas.ai import RawProposalCandidate
from app.schemas.common import AiActionType, CourseLanguage, StrategicDecision
from app.services.assessment_evaluator import validate_evidence_quality
from app.services.course_generator import build_course_blueprint, generate_level_content


class ProviderResult(BaseModel):
    reply: str
    proposals: list[RawProposalCandidate] = Field(default_factory=list)
    is_estimate: bool = False
    missing_data: list[str] = Field(default_factory=list)
    provider_name: str
    model_name: str


class AIProvider(Protocol):
    def generate_response(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        context: BoundedUserContext,
        prompt_manager: PromptManager,
    ) -> ProviderResult: ...


def _extract_quoted_or_after_colon(message: str, fallback: str) -> str:
    quoted = re.search(r"[«\"']([^«»\"']{2,120})[»\"']", message)
    if quoted:
        return quoted.group(1).strip()
    after_colon = re.search(r":\s*(.{2,120})$", message.strip())
    if after_colon:
        return after_colon.group(1).strip()
    return fallback


STRATEGIC_PLANNING_TRIGGERS: tuple[str, ...] = (
    "apprendre",
    "formation",
    "développer une idée",
    "développer un projet",
    "nouveau projet",
    "lancer un projet",
    "mon idée",
    "préparer un examen",
    "préparer l'examen",
    "préparer l’examen",
    "préparer mon examen",
    "approfondir",
    "ajouter une activité",
    "nouvelle activité",
    "nouvelle idée",
    "voudrais maîtriser",
    "suivi de mon activité",
    "suivi de mes activités",
    "séances manquées",
    "séances non réalisées",
    "j'ai manqué",
    "j’ai manqué",
)

STOPWORDS_FR: set[str] = {
    "avec",
    "pour",
    "dans",
    "sans",
    "sur",
    "sous",
    "vers",
    "mon",
    "mes",
    "ton",
    "tes",
    "une",
    "des",
    "les",
    "aux",
    "cette",
    "voudrais",
    "veux",
    "apprendre",
    "faire",
    "projet",
    "formation",
    "examen",
    "objectif",
    "semaine",
    "semaines",
    "heure",
    "heures",
}

DAY_INDEX_BY_TOKEN: dict[str, int] = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}


def _meaningful_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[a-zà-öø-ÿ0-9]{3,}", (text or "").lower())
    return {t for t in tokens if t not in STOPWORDS_FR}


def _extract_activity_topic(message: str) -> tuple[str, str]:
    """Retourne (activity_title, category) à partir du message."""
    lowered = message.lower()
    category = "learning"
    if any(w in lowered for w in ("examen", "partiel", "contrôle", "controle")):
        category = "exam_prep"
    elif any(w in lowered for w in ("projet", "application", "prototype", "idée")):
        category = "project"
    elif any(w in lowered for w in ("approfondir", "matière universitaire")):
        category = "university_deepening"
    elif any(w in lowered for w in ("activité personnelle", "sport", "lecture", "personnel")):
        category = "personal"

    quoted = re.search(r"[«\"']([^«»\"']{2,100})[»\"']", message)
    if quoted:
        return quoted.group(1).strip(), category

    patterns = (
        r"(?:apprendre\s+(?:le\s+développement\s+avec\s+|à\s+|le\s+|la\s+|les\s+|l['’])?)([^\n\.\?\!,;]{2,80})",
        r"(?:suivre\s+une\s+formation\s+(?:en\s+|sur\s+|de\s+)?|formation\s+(?:en\s+|sur\s+|de\s+)?)([^\n\.\?\!,;]{2,80})",
        r"(?:développer\s+(?:une\s+idée|un\s+projet)\s*(?:de|sur|d['’]|:)?\s*)([^\n\.\?\!,;]{2,80})",
        r"(?:lancer\s+un\s+projet\s*(?:de|sur|d['’]|:)?\s*)([^\n\.\?\!,;]{2,80})",
        r"(?:préparer\s+(?:un|l['’]|mon)\s+examen\s*(?:de|d['’]|en|sur)?\s*)([^\n\.\?\!,;]{2,80})",
        r"(?:approfondir\s+(?:la\s+matière\s+|le\s+|la\s+|les\s+|l['’])?)([^\n\.\?\!,;]{2,80})",
        r"(?:ajouter\s+une\s+activité\s*(?:de|personnelle\s*:|:)?\s*)([^\n\.\?\!,;]{2,80})",
    )
    for pat in patterns:
        m = re.search(pat, message, re.IGNORECASE)
        if m and m.group(1).strip():
            raw_subj = re.split(
                r"\s+(?:en\s+\d+\s+semaines?|avec\s+\d+\s*(?:h|séance)|sur\s+\d+\s+semaines?|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|aujourd['’]hui|demain)\b",
                m.group(1).strip(),
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip(" :,-")
            if len(raw_subj) >= 2:
                if category == "exam_prep" and not raw_subj.lower().startswith("examen"):
                    return f"Préparation examen : {raw_subj}"[:140], category
                if category == "project" and not any(
                    w in raw_subj.lower() for w in ("projet", "app", "prototype")
                ):
                    return f"Projet : {raw_subj}"[:140], category
                return raw_subj[:140], category

    if any(w in lowered for w in ("suivi", "séances manquées", "manqué")):
        return "Réajustement du programme d’étude", "learning"

    fallback = _extract_quoted_or_after_colon(message, "Nouvel objectif d’étude")
    return fallback[:140], category


def _extract_requested_time_constraint(message: str) -> tuple[int | None, str | None, int | None, int | None]:
    """Détecte si l'utilisateur demande un jour et/ou une plage horaire précise (ex. 'lundi de 18h à 21h')."""
    lowered = message.lower()
    day_idx: int | None = None
    day_token: str | None = None
    for tok, idx in DAY_INDEX_BY_TOKEN.items():
        if re.search(rf"\b{tok}\b", lowered):
            day_idx = idx
            day_token = tok
            break
    if day_token is None:
        if "aujourd'hui" in lowered or "aujourd’hui" in lowered:
            day_token = "today"
        elif "demain" in lowered:
            day_token = "tomorrow"

    time_m = re.search(
        r"(\d{1,2})\s*[hH:]\s*(\d{2})?\s*(?:-|–|à|au)\s*(\d{1,2})\s*[hH:]?\s*(\d{2})?",
        lowered,
    )
    if not time_m:
        return day_idx, day_token, None, None

    h1 = int(time_m.group(1))
    m1 = int(time_m.group(2) or 0)
    h2 = int(time_m.group(3))
    m2 = int(time_m.group(4) or 0)
    if not (0 <= h1 <= 23 and 0 <= m1 <= 59 and 0 <= h2 <= 23 and 0 <= m2 <= 59):
        return day_idx, day_token, None, None
    return day_idx, day_token, h1 * 60 + m1, h2 * 60 + m2


def _hhmm_to_min(hhmm: str) -> int:
    h_s, m_s = hhmm.split(":")
    return int(h_s) * 60 + int(m_s)


def _handle_conversational_strategic_planning(
    *,
    user_message: str,
    history: list[dict[str, str]],
    context: BoundedUserContext,
    model_name: str,
) -> ProviderResult | None:
    lowered = user_message.lower()
    is_direct_command = any(
        cmd in lowered
        for cmd in (
            "crée une tâche",
            "créer une tâche",
            "ajoute une tâche",
            "propose une tâche",
            "nouvelle tâche",
            "crée un cours",
            "créer un cours",
            "nouveau cours",
            "cours complet",
            "génère un cours",
            "générer un cours",
            "apprendre le langage",
            "preuve",
            "justifier",
            "monter compétence",
            "valider compétence",
        )
    ) or (
        any(w in lowered for w in ("mets ", "mettre ", "place "))
        and "parking" in lowered
    )
    if is_direct_command:
        return None

    last_assistant = next(
        (m["content"] for m in reversed(history) if m.get("role") == "assistant"),
        "",
    )
    in_strategic_followup = (
        "Cette proposition ne sera pas enregistrée tant que tu ne l'auras pas validée"
        in last_assistant
        or "Analyse stratégique & Proposition" in last_assistant
    ) and any(
        w in lowered
        for w in (
            "objectif",
            "niveau",
            "débutant",
            "intermédiaire",
            "avancé",
            "semaine",
            "heure",
            "séance",
            "mois",
            "échéance",
            "plutôt",
            "oui",
        )
    )

    if not (
        any(trigger in lowered for trigger in STRATEGIC_PLANNING_TRIGGERS)
        or in_strategic_followup
    ):
        return None

    # Fusionner avec le premier message utilisateur du fil stratégique s'il s'agit d'un suivi multi-tour
    combined_user_text = user_message
    topic_source_message = user_message
    if in_strategic_followup:
        prior_user_msgs = [m["content"] for m in history if m.get("role") == "user"]
        if prior_user_msgs:
            topic_source_message = prior_user_msgs[0]
            combined_user_text = " ".join(prior_user_msgs) + " " + user_message
    elif history:
        prior_user_msgs = [m["content"] for m in history if m.get("role") == "user"]
        if prior_user_msgs and not any(t in lowered for t in STRATEGIC_PLANNING_TRIGGERS):
            combined_user_text = " ".join(prior_user_msgs) + " " + user_message

    activity_title, category = _extract_activity_topic(topic_source_message)
    if activity_title == "Nouvel objectif d’étude" and topic_source_message != user_message:
        activity_title, category = _extract_activity_topic(user_message)

    combined_lower = combined_user_text.lower()
    sa = context.strategic_analysis or {}
    priority_title = context.profile.get("active_priority_title")
    weekly_slots = list((context.availability or {}).get("weekly_candidate_slots") or [])
    uni_courses = list(context.university_courses or [])
    critical_tasks_count = int(sa.get("critical_tasks_count", 0))
    overdue_tasks_count = int(sa.get("overdue_tasks_count", 0))
    weekly_scheduled_minutes = int(sa.get("weekly_scheduled_minutes", 0))
    missed_count = int(sa.get("missed_study_blocks_count", 0))
    missed_titles = list(sa.get("missed_block_titles") or [])

    # 1. Réutiliser les connaissances déjà présentes dans le profil/compétences
    activity_tokens = _meaningful_tokens(activity_title)
    matched_skill = next(
        (
            s
            for s in context.skills
            if (
                s["name"].lower() in combined_lower
                or bool(activity_tokens & _meaningful_tokens(s["name"]))
            )
        ),
        None,
    )
    stated_level_match = re.search(
        r"\b(débutant|intermédiaire|avancé|niveau\s*[0-5])\b",
        combined_lower,
    )

    # Extraire objectif, échéance, fréquence et durée
    goal_match = re.search(
        r"(?:objectif\s*[:\-]?\s*|pour\s+|afin\s+de\s+)([^\n\.]{4,140})",
        combined_user_text,
        re.IGNORECASE,
    )
    estimated_weeks = 3
    weeks_m = re.search(r"(\d+)\s*semaines?", combined_lower)
    months_m = re.search(r"(\d+)\s*mois", combined_lower)
    if weeks_m:
        estimated_weeks = max(1, min(52, int(weeks_m.group(1))))
    elif months_m:
        estimated_weeks = max(1, min(52, int(months_m.group(1)) * 4))

    freq_per_week = 2
    freq_m = re.search(r"(\d+)\s*(?:séances?|créneaux?|fois)\s*(?:par\s+semaine|/semaine)?", combined_lower)
    if freq_m:
        freq_per_week = max(1, min(5, int(freq_m.group(1))))

    session_minutes = 60
    dur_m = re.search(r"(\d+)\s*(?:h|heures?)\b", combined_lower)
    min_m = re.search(r"(\d{2,3})\s*min", combined_lower)
    if min_m:
        session_minutes = max(30, min(120, int(min_m.group(1))))
    elif dur_m and not freq_m:
        hours_val = int(dur_m.group(1))
        if hours_val in (1, 2):
            session_minutes = hours_val * 60
        elif hours_val >= 3:
            freq_per_week = min(4, max(2, hours_val))
            session_minutes = 60

    if goal_match:
        goal_text = goal_match.group(1).strip()[:300]
    else:
        goal_text = f"Maîtriser les fondamentaux et livrer un exercice concret sur « {activity_title} » en {estimated_weeks} semaine(s)."

    # Questions de clarification uniquement si manquantes (Étape 1)
    missing_questions: list[str] = []
    if not goal_match:
        missing_questions.append("Quel est le résultat concret recherché ?")
    if matched_skill is None and not stated_level_match:
        missing_questions.append("Quel est ton niveau actuel sur ce sujet ?")
    if not weeks_m and not months_m:
        missing_questions.append("Quelle est l’échéance souhaitée ?")
    if not freq_m and not dur_m and not min_m:
        missing_questions.append("Combien de temps par semaine peux-tu y consacrer ?")

    # 2. Analyse des conflits avec un créneau explicitement demandé (Test 3)
    req_day_idx, req_day_tok, req_start_min, req_end_min = _extract_requested_time_constraint(
        user_message
    )
    conflicting_course_title: str | None = None
    if req_start_min is not None and req_end_min is not None:
        for ev in uni_courses:
            ev_local_date = date.fromisoformat(ev["local_date"])
            ev_weekday = ev_local_date.weekday()
            day_matches = True
            if req_day_tok == "today":
                day_matches = bool(ev.get("is_today"))
            elif req_day_tok == "tomorrow":
                day_matches = bool(ev.get("is_tomorrow"))
            elif req_day_idx is not None:
                day_matches = ev_weekday == req_day_idx
            if not day_matches:
                continue
            ev_s_min = _hhmm_to_min(ev["local_start_time"])
            ev_e_min = _hhmm_to_min(ev["local_end_time"])
            if req_start_min < ev_e_min and ev_s_min < req_end_min:
                conflicting_course_title = f"{ev['title']} ({ev['local_start_time']} à {ev['local_end_time']})"
                break

    # 3. Vérification des règles de priorité et de dispersion (Test 5)
    is_missed_followup_request = any(
        w in lowered
        for w in (
            "suivi de mon activité",
            "suivi de mes activités",
            "séances manquées",
            "séances non réalisées",
            "j'ai manqué",
            "j’ai manqué",
        )
    )
    is_dispersion = False
    if priority_title and category != "exam_prep" and not is_missed_followup_request:
        prio_tokens = _meaningful_tokens(priority_title)
        if prio_tokens and activity_tokens and not (prio_tokens & activity_tokens):
            # Pas d'alignement avec la priorité principale active
            is_also_uni_course = any(
                bool(activity_tokens & _meaningful_tokens(c["title"])) for c in uni_courses
            )
            if not is_also_uni_course:
                is_dispersion = True

    lines: list[str] = []
    ai_instructions = context.profile.get("ai_instructions")
    if ai_instructions:
        lines.append(f"*(Consignes personnelles prises en compte : {ai_instructions})*")

    if matched_skill is not None:
        lines.append(
            f"*(Profil réutilisé : niveau actuel **{matched_skill['current_level']}/5** déjà enregistré sur **{matched_skill['name']}**, aucune redondance nécessaire.)*"
        )

    # Cas A : STOP — DISPERSION DÉTECTÉE (Test 5)
    if is_dispersion:
        lines.append(
            "STOP — DISPERSION DÉTECTÉE.\n\n"
            "Tu as déjà une priorité en cours. Ajouter cette activité maintenant risque de ralentir ton objectif principal. "
            "Je te recommande de la placer dans ton Parking jusqu'à la prochaine réévaluation."
        )
        lines.append(
            f"- **Priorité active protégée** : {priority_title}\n"
            f"- **Décision stratégique** : **C. NON RECOMMANDÉE POUR LE MOMENT**\n"
            f"- **Coût d’opportunité** : disperser ton attention réduirait ton avance sur « {priority_title} ».\n"
            "- *Cette proposition ne sera pas enregistrée tant que tu ne l'auras pas validée.*"
        )
        proposals = [
            RawProposalCandidate(
                action_type=AiActionType.plan_strategic_activity.value,
                title=f"Placer « {activity_title} » dans le Parking des idées",
                explanation=(
                    f"Protège votre priorité active (« {priority_title} ») contre la dispersion "
                    "et conserve l’idée au Parking sans programmer de séance."
                ),
                payload={
                    "activity_title": activity_title,
                    "category": category,
                    "goal": goal_text,
                    "decision": StrategicDecision.not_recommended.value,
                    "conditions": [f"Terminer ou avancer significativement sur « {priority_title} » avant démarrage."],
                    "opportunity_cost_note": f"Risque de ralentissement de la priorité active ({priority_title}).",
                    "create_learning_path": False,
                    "create_project": False,
                    "park_only": True,
                    "frequency_per_week": 0,
                    "session_duration_minutes": 60,
                    "estimated_weeks": estimated_weeks,
                    "start_date": context.profile.get("local_date"),
                    "proposed_slots": [],
                },
            )
        ]
        return ProviderResult(
            reply="\n\n".join(lines),
            proposals=proposals,
            is_estimate=context.is_partial_data,
            missing_data=context.missing_data,
            provider_name="local",
            model_name=model_name,
        )

    # Cas B : Suivi des séances acceptées mais non réalisées (Section 4, Test 11)
    if is_missed_followup_request or missed_count >= 2:
        if missed_count > 0:
            lines.append(
                f"### Suivi stratégique & exécution réelle\n"
                f"- **Attention** : une activité programmée n’est pas considérée comme terminée sans séance réalisée. "
                f"**{missed_count} séance(s) planifiée(s) ces 7 derniers jours n’ont pas été effectuées** : "
                f"{', '.join(missed_titles[:4])}."
            )
        else:
            lines.append(
                "### Suivi stratégique & exécution réelle\n"
                "- Aucune séance manquée sur les 7 derniers jours : vos créneaux planifiés sont en phase avec vos séances réalisées."
            )
        if is_missed_followup_request and missed_count >= 2:
            # Proposer un réajustement léger plutôt qu'accumuler des tâches
            light_slots = []
            if weekly_slots:
                s0 = weekly_slots[0]
                light_slots.append(
                    {
                        "day_label": s0["day_label"],
                        "local_date": s0["local_date"],
                        "local_start_time": s0["local_start_time"],
                        "local_end_time": s0["local_end_time"],
                        "starts_at": s0["starts_at"],
                        "ends_at": s0["ends_at"],
                        "duration_minutes": s0["duration_minutes"],
                    }
                )
            lines.append(
                "Plutôt que d’accumuler de nouvelles tâches, je te recommande un **ajustement du rythme** : "
                "replanifier une unique séance de reprise réaliste cette semaine avant d’ajouter autre chose.\n"
                "Cette proposition ne sera pas enregistrée tant que tu ne l'auras pas validée."
            )
            proposals: list[RawProposalCandidate] = []
            if light_slots:
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.plan_strategic_activity.value,
                        title="Réajuster le planning (1 séance de reprise ciblée)",
                        explanation="Réduit la cadence après des séances manquées afin d’éviter l’accumulation.",
                        payload={
                            "activity_title": f"Reprise ciblée : {missed_titles[0] if missed_titles else activity_title}",
                            "category": "learning",
                            "goal": "Finaliser la séance manquée et consigner un résultat concret avant toute nouvelle charge.",
                            "decision": StrategicDecision.acceptable_with_conditions.value,
                            "conditions": [
                                "Réaliser d’abord cette séance de rattrapage et enregistrer son résultat.",
                                "Ne pas empiler de nouvelles activités tant que le retard persiste.",
                            ],
                            "opportunity_cost_note": f"{missed_count} séance(s) manquée(s) récemment : priorité à la régularité.",
                            "create_learning_path": False,
                            "create_project": False,
                            "park_only": False,
                            "frequency_per_week": 1,
                            "session_duration_minutes": light_slots[0]["duration_minutes"],
                            "estimated_weeks": 1,
                            "start_date": light_slots[0]["local_date"],
                            "proposed_slots": light_slots,
                        },
                    )
                )
            return ProviderResult(
                reply="\n\n".join(lines),
                proposals=proposals,
                is_estimate=context.is_partial_data,
                missing_data=context.missing_data,
                provider_name="local",
                model_name=model_name,
            )

    # Cas C : Aucun créneau disponible sur 7 jours (Test 2)
    if not weekly_slots:
        lines.append(
            "### Analyse stratégique & Décision : **C. NON RECOMMANDÉE POUR LE MOMENT**\n"
            "J’ai analysé ton emploi du temps : **aucun créneau raisonnable disponible** n’a été trouvé "
            "cette semaine sans empiéter sur tes cours, tes pauses ou surcharger tes journées.\n"
            "Je n’invente aucune disponibilité artificielle. Je te propose de placer cette idée dans ton Parking "
            "ou de reporter son démarrage après allègement de ta semaine.\n"
            "Cette proposition ne sera pas enregistrée tant que tu ne l'auras pas validée."
        )
        proposals = [
            RawProposalCandidate(
                action_type=AiActionType.plan_strategic_activity.value,
                title=f"Placer « {activity_title} » au Parking (calendrier complet)",
                explanation="Aucun créneau libre disponible cette semaine sans conflit ou surcharge.",
                payload={
                    "activity_title": activity_title,
                    "category": category,
                    "goal": goal_text,
                    "decision": StrategicDecision.not_recommended.value,
                    "conditions": ["Libérer au moins un créneau hebdomadaire ou attendre la semaine suivante."],
                    "opportunity_cost_note": "Calendrier hebdomadaire saturé.",
                    "create_learning_path": False,
                    "create_project": False,
                    "park_only": True,
                    "frequency_per_week": 0,
                    "session_duration_minutes": session_minutes,
                    "estimated_weeks": estimated_weeks,
                    "start_date": context.profile.get("local_date"),
                    "proposed_slots": [],
                },
            )
        ]
        return ProviderResult(
            reply="\n\n".join(lines),
            proposals=proposals,
            is_estimate=context.is_partial_data,
            missing_data=context.missing_data,
            provider_name="local",
            model_name=model_name,
        )

    # Cas D : Surcharge sévère (Test 4) vs Conditions vs Acceptable
    conditions: list[str] = []
    decision = StrategicDecision.acceptable
    max_slots = min(freq_per_week, 3)

    if weekly_scheduled_minutes >= 1800 or critical_tasks_count > 3:
        lines.append(
            "### Analyse stratégique & Décision : **C. NON RECOMMANDÉE POUR LE MOMENT**\n"
            f"Ta semaine est déjà fortement chargée (**{round(weekly_scheduled_minutes / 60, 1)} h planifiées**, "
            f"**{critical_tasks_count} tâche(s) critique(s)**).\n"
            "Ajouter une nouvelle activité maintenant provoquerait une surcharge excessive. "
            "Je te recommande de placer cette activité au Parking ou de réduire d’abord ta charge critique.\n"
            "Cette proposition ne sera pas enregistrée tant que tu ne l'auras pas validée."
        )
        proposals = [
            RawProposalCandidate(
                action_type=AiActionType.plan_strategic_activity.value,
                title=f"Différer « {activity_title} » au Parking (surcharge hebdomadaire)",
                explanation="Charge hebdomadaire déjà élevée ou trop de tâches critiques en cours.",
                payload={
                    "activity_title": activity_title,
                    "category": category,
                    "goal": goal_text,
                    "decision": StrategicDecision.not_recommended.value,
                    "conditions": ["Réduire le nombre de tâches critiques (≤ 3) et alléger la semaine."],
                    "opportunity_cost_note": f"Semaine surchargée ({weekly_scheduled_minutes} min planifiées).",
                    "create_learning_path": False,
                    "create_project": False,
                    "park_only": True,
                    "frequency_per_week": 0,
                    "session_duration_minutes": session_minutes,
                    "estimated_weeks": estimated_weeks,
                    "start_date": context.profile.get("local_date"),
                    "proposed_slots": [],
                },
            )
        ]
        return ProviderResult(
            reply="\n\n".join(lines),
            proposals=proposals,
            is_estimate=context.is_partial_data,
            missing_data=context.missing_data,
            provider_name="local",
            model_name=model_name,
        )

    if conflicting_course_title:
        decision = StrategicDecision.acceptable_with_conditions
        conditions.append(
            f"Conflit détecté avec le cours universitaire « {conflicting_course_title} » : le créneau demandé a été écarté et remplacé par une disponibilité libre."
        )

    if weekly_scheduled_minutes >= 1200 or critical_tasks_count == 3 or overdue_tasks_count >= 1 or missed_count >= 2:
        decision = StrategicDecision.acceptable_with_conditions
        max_slots = min(max_slots, 2)
        if weekly_scheduled_minutes >= 1200:
            conditions.append(
                f"Semaine chargée ({round(weekly_scheduled_minutes / 60, 1)} h déjà prévues) : cadence limitée à {max_slots} séance(s)/semaine pour éviter le surmenage."
            )
        if critical_tasks_count >= 3 or overdue_tasks_count >= 1:
            conditions.append(
                f"Traiter en priorité les tâches urgentes/critiques ({critical_tasks_count} critique(s), {overdue_tasks_count} en retard) avant d’étendre le rythme."
            )
        if missed_count >= 2:
            conditions.append(
                f"Réajuster la régularité suite aux {missed_count} séance(s) précédente(s) non réalisée(s)."
            )

    # Sélection des meilleurs créneaux réels répartis sur plusieurs semaines (jusqu'à 3 semaines)
    multi_week_pool = list(
        (context.availability or {}).get("multi_week_candidate_slots") or weekly_slots
    )
    target_weeks = max(1, min(3, estimated_weeks))
    chosen_raw_slots: list[dict[str, Any]] = []
    week0_count = 0
    for wk in range(target_weeks):
        wk_candidates = [
            c for c in multi_week_pool if int(c.get("week_index", 0)) == wk
        ]
        if not wk_candidates and wk == 0:
            wk_candidates = list(weekly_slots)
        wk_selected: list[dict[str, Any]] = []
        used_dates: set[str] = set()
        for candidate in wk_candidates:
            if len(wk_selected) >= max_slots:
                break
            if candidate["local_date"] not in used_dates:
                wk_selected.append(candidate)
                used_dates.add(candidate["local_date"])
        if len(wk_selected) < max_slots:
            for candidate in wk_candidates:
                if len(wk_selected) >= max_slots:
                    break
                if candidate not in wk_selected:
                    wk_selected.append(candidate)
        if wk == 0:
            week0_count = len(wk_selected)
        chosen_raw_slots.extend(wk_selected)

    if not chosen_raw_slots:
        for candidate in weekly_slots[:max_slots]:
            chosen_raw_slots.append(candidate)
        week0_count = len(chosen_raw_slots)

    effective_freq = max(1, min(7, week0_count or max_slots))

    proposed_slots_payload: list[dict[str, Any]] = []
    for slot in chosen_raw_slots:
        start_dt = datetime.fromisoformat(slot["starts_at"])
        actual_duration = min(int(slot["duration_minutes"]), session_minutes)
        if actual_duration < 30:
            actual_duration = int(slot["duration_minutes"])
        end_dt = start_dt + timedelta(minutes=actual_duration)
        # Re-calcul heure locale via diff depuis local_start_time
        sh, sm = [int(p) for p in slot["local_start_time"].split(":")]
        end_tot_min = sh * 60 + sm + actual_duration
        local_end_str = f"{end_tot_min // 60:02d}:{end_tot_min % 60:02d}"
        proposed_slots_payload.append(
            {
                "day_label": slot["day_label"],
                "local_date": slot["local_date"],
                "local_start_time": slot["local_start_time"],
                "local_end_time": local_end_str,
                "starts_at": start_dt.isoformat(),
                "ends_at": end_dt.isoformat(),
                "duration_minutes": actual_duration,
            }
        )

    decision_label = (
        "B. ACCEPTABLE SOUS CONDITIONS"
        if decision == StrategicDecision.acceptable_with_conditions
        else "A. ACCEPTABLE"
    )
    slot_lines = "\n".join(
        f"- {s['day_label']} ({s['local_date']}) : {s['local_start_time']} à {s['local_end_time']} ({s['duration_minutes']} min)"
        for s in proposed_slots_payload
    )
    lines.append(
        f"### Analyse stratégique & Proposition ({decision_label})\n"
        f"J’ai analysé ton emploi du temps ({len(uni_courses)} cours universitaire(s), "
        f"{round(weekly_scheduled_minutes / 60, 1)} h planifiées cette semaine). "
        f"Voici ma proposition pour **{activity_title}** :"
    )
    lines.append(slot_lines)
    lines.append(
        f"**Objectif mesurable** : {goal_text}\n"
        f"- **Fréquence** : {effective_freq} séance(s) / semaine · **Créneaux générés** : {len(proposed_slots_payload)} · **Durée** : ~{estimated_weeks} semaine(s) · **Début** : {proposed_slots_payload[0]['local_date']}"
    )
    if conditions:
        lines.append("**Conditions recommandées** :\n" + "\n".join(f"- {c}" for c in conditions))
    if missing_questions:
        lines.append(
            "**Pour affiner encore davantage (facultatif avant validation)** :\n"
            + "\n".join(f"- {q}" for q in missing_questions)
        )
    lines.append(
        "Cette proposition ne sera pas enregistrée tant que tu ne l'auras pas validée."
    )

    is_project = category == "project"
    active_projects_list = [p for p in context.projects if p.get("status") == "active"]
    can_create_project = is_project and len(active_projects_list) < 3
    proposals = [
        RawProposalCandidate(
            action_type=AiActionType.plan_strategic_activity.value,
            title=f"Programmer « {activity_title} » ({effective_freq} séance(s)/sem.)",
            explanation=(
                "Proposition stratégique vérifiée contre ton emploi du temps universitaire et tes disponibilités réelles."
            ),
            payload={
                "activity_title": activity_title,
                "category": category,
                "goal": goal_text,
                "decision": decision.value,
                "conditions": conditions,
                "opportunity_cost_note": f"Charge hebdomadaire actuelle : {weekly_scheduled_minutes} min.",
                "create_learning_path": not is_project,
                "create_project": can_create_project,
                "park_only": False,
                "frequency_per_week": effective_freq,
                "session_duration_minutes": proposed_slots_payload[0]["duration_minutes"],
                "estimated_weeks": estimated_weeks,
                "start_date": proposed_slots_payload[0]["local_date"],
                "proposed_slots": proposed_slots_payload,
            },
        )
    ]
    if is_project and len(active_projects_list) >= 3:
        candidate_to_pause = active_projects_list[-1]
        proposals.append(
            RawProposalCandidate(
                action_type=AiActionType.pause_project.value,
                title=f"Mettre en pause le projet « {candidate_to_pause['name']} »",
                explanation="Vous avez déjà 3 projets actifs (limite maximale). Mettez un projet en pause pour libérer un créneau actif.",
                payload={
                    "project_id": candidate_to_pause["id"],
                    "reason": f"Libérer un slot de projet actif pour « {activity_title} ».",
                },
            )
        )
    return ProviderResult(
        reply="\n\n".join(lines),
        proposals=proposals,
        is_estimate=context.is_partial_data,
        missing_data=context.missing_data,
        provider_name="local",
        model_name=model_name,
    )


_FR_NUMBER_WORDS: dict[str, int] = {
    "un": 1,
    "une": 1,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "six": 6,
}


def _extract_count_word(lowered: str, default: int = 2) -> int:
    digit_m = re.search(r"\b(\d+)\s*(?:séances?|sessions?|créneaux?|blocs?)\b", lowered)
    if digit_m:
        return max(1, min(7, int(digit_m.group(1))))
    for word, val in _FR_NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s+(?:séances?|sessions?|créneaux?|blocs?)\b", lowered):
            return val
    return default


def _extract_clean_entity_name(message: str, prefixes: tuple[str, ...], fallback: str, max_len: int = 120) -> str:
    quoted = re.search(r"[«\"']([^«»\"']{2,120})[»\"']", message)
    if quoted:
        return quoted.group(1).strip()[:max_len]
    after_colon = re.search(r":\s*(.{2,140})$", message.strip())
    if after_colon:
        cand = after_colon.group(1).strip().rstrip(".")
        if cand:
            return cand[:max_len]
    for pat in prefixes:
        m = re.search(pat, message, re.IGNORECASE)
        if m and m.group(1).strip():
            cand = m.group(1).strip().rstrip(".")
            cand = re.split(r"\s+(?:pour\s+mettre\s+en|dans\s+le\s+cadre|pendant\s+\d+)\b", cand, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            if len(cand) >= 2:
                return cand[:max_len]
    return fallback[:max_len]


def _match_by_name_or_tokens(query: str, items: list[dict[str, Any]], key: str = "title") -> dict[str, Any] | None:
    q_lower = query.lower()
    q_tokens = _meaningful_tokens(query)
    best: dict[str, Any] | None = None
    best_score = 0
    for item in items:
        label = str(item.get(key) or item.get("name") or item.get("title") or "").strip()
        if not label:
            continue
        l_lower = label.lower()
        if l_lower in q_lower:
            score = len(l_lower) + 100
        else:
            overlap = q_tokens & _meaningful_tokens(label + " " + str(item.get("goal") or ""))
            score = len(overlap) * 10
        if score > best_score:
            best_score = score
            best = item
    return best if best_score > 0 else None


def _handle_ai_first_intents(
    *,
    user_message: str,
    context: BoundedUserContext,
    model_name: str,
) -> ProviderResult | None:
    lowered = user_message.lower()
    proposals: list[RawProposalCandidate] = []
    lines: list[str] = []

    learning_paths = list((context.learning or {}).get("paths") or [])
    personal_goals = list(context.personal_goals or [])
    projects = list(context.projects or [])
    skills = list(context.skills or [])
    active_tasks = list(context.tasks or [])
    weekly_slots = list((context.availability or {}).get("weekly_candidate_slots") or [])
    avail_prefs = dict((context.availability or {}).get("preferences") or {})
    memory = dict(context.personal_memory or {})

    # 0. Règles explicites d'indisponibilité / disponibilité confirmée / récupération
    avail_rule_match = any(
        p in lowered
        for p in (
            "indisponible",
            "pas disponible",
            "ne suis pas disponible",
            "pas libre",
            "disponibilité confirmée",
            "disponibilite confirmee",
            "jour de repos",
            "temps de récupération",
            "temps de recuperation",
        )
    )
    if avail_rule_match:
        matched_day_name: str | None = None
        matched_day_idx: int | None = None
        for tok, idx in DAY_INDEX_BY_TOKEN.items():
            if re.search(rf"\b{tok}\b", lowered):
                matched_day_name = tok
                matched_day_idx = idx
                break
        if matched_day_idx is not None:
            start_t = "14:00"
            end_t = "18:00"
            t_match = re.search(
                r"(\d{1,2})\s*[hH:]\s*(\d{2})?\s*(?:à|au|-|et)\s*(\d{1,2})\s*[hH:]\s*(\d{2})?",
                lowered,
            )
            if t_match:
                sh = max(0, min(23, int(t_match.group(1))))
                sm = int(t_match.group(2) or "0")
                eh = max(0, min(23, int(t_match.group(3))))
                em = int(t_match.group(4) or "0")
                start_t = f"{sh:02d}:{sm:02d}"
                end_t = f"{eh:02d}:{em:02d}"
            elif "matin" in lowered:
                start_t, end_t = "08:30", "12:30"
            elif "après-midi" in lowered or "apres-midi" in lowered or "aprem" in lowered:
                start_t, end_t = "14:00", "18:00"
            elif "soir" in lowered:
                start_t, end_t = "18:00", "22:00"
            elif "toute la journée" in lowered or "toute la journee" in lowered or "jour de repos" in lowered:
                start_t, end_t = "08:00", "22:00"

            rule_type = "personal_unavailability"
            label_prefix = "Indisponibilité"
            if "disponibilité confirmée" in lowered or "disponibilite confirmee" in lowered:
                rule_type = "confirmed_availability"
                label_prefix = "Disponibilité confirmée"
            elif "récupération" in lowered or "recuperation" in lowered or "jour de repos" in lowered:
                rule_type = "recovery_time"
                label_prefix = "Temps de récupération"

            tz_name = str((context.profile or {}).get("timezone") or "Europe/Paris")
            day_label = matched_day_name.capitalize() if matched_day_name else "Jour"
            rule_label = f"{label_prefix} {day_label} ({start_t} à {end_t})"
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.manage_availability_rule.value,
                    title=f"Enregistrer : {rule_label}",
                    explanation="Cette règle sera prise en compte par le moteur de disponibilité lors de chaque planification.",
                    payload={
                        "label": rule_label,
                        "rule_type": rule_type,
                        "day_of_week": matched_day_idx,
                        "start_time": start_t,
                        "end_time": end_t,
                        "timezone": tz_name,
                        "recurrence": "weekly",
                    },
                )
            )
            lines.append(
                f"J'ai préparé l'enregistrement de votre règle **« {rule_label} »** afin que le moteur de planification respecte strictement ce créneau."
            )
            return ProviderResult(
                reply="\n\n".join(lines),
                proposals=proposals,
                is_estimate=False,
                missing_data=context.missing_data,
                provider_name="local",
                model_name=model_name,
            )

    # 1. Mise à jour des disponibilités / préférences en langage naturel
    explicit_pref_intent = any(
        p in lowered
        for p in (
            "je dispose de",
            "j'ai maintenant",
            "j’ai maintenant",
            "modifie mes disponibilités",
            "modifier mes disponibilités",
            "mets à jour mes disponibilités",
            "mettre à jour mes disponibilités",
            "mes nouvelles disponibilités",
            "mes disponibilités sont",
            "préférences horaires",
            "changer mes horaires",
            "change mes horaires",
        )
    ) or (
        ("disponible" in lowered or "disponibilités" in lowered)
        and bool(
            re.search(
                r"(\d{1,3})\s*(?:h|heures?)\s*(?:par\s+semaine|/sem)|(\d{1,2})\s*[hH]\s*(?:à|-)\s*(\d{1,2})\s*[hH]",
                lowered,
            )
        )
        and "apprendre" not in lowered
    )
    if explicit_pref_intent:
        pref_payload: dict[str, Any] = {}
        wh_m = re.search(
            r"(?:dispose\s+de|disposant\s+de|avec|à)\s+(\d{1,3})\s*(?:h|heures?)(?:\s+par\s+semaine)?|(\d{1,3})\s*(?:h|heures?)\s*(?:par\s+semaine|/sem|hebdo)",
            lowered,
        )
        if wh_m:
            hours_val = int(wh_m.group(1) or wh_m.group(2))
            pref_payload["weekly_study_hours"] = max(1, min(100, hours_val))
        range_m = re.search(r"(\d{1,2})\s*[hH:]\s*\d{0,2}\s*(?:à|au|-|et)\s*(\d{1,2})\s*[hH:]?", lowered)
        if range_m:
            s_h = max(5, min(20, int(range_m.group(1))))
            e_h = max(s_h + 1, min(23, int(range_m.group(2))))
            pref_payload["study_start_hour"] = s_h
            pref_payload["study_end_hour"] = e_h
        excluded_found: list[int] = []
        for tok, day_idx in DAY_INDEX_BY_TOKEN.items():
            if re.search(rf"(?:pas\s+le|hors|exclure\s+le|sans\s+le|jamais\s+le)\s+{tok}\b", lowered):
                excluded_found.append(day_idx)
        if excluded_found:
            pref_payload["excluded_days"] = sorted(set(excluded_found))
        dur_pref_m = re.search(r"séances?\s+de\s+(\d{2,3})\s*min", lowered)
        if dur_pref_m:
            pref_payload["preferred_session_minutes"] = max(30, min(180, int(dur_pref_m.group(1))))
        if pref_payload:
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.update_preferences.value,
                    title="Mettre à jour vos préférences et disponibilités",
                    explanation="Enregistre durablement vos contraintes horaires dans votre profil et votre mémoire IA.",
                    payload=pref_payload,
                )
            )
            lines.append(
                "J'ai préparé la mise à jour de vos disponibilités et contraintes dans votre contexte personnel persistant."
            )
            return ProviderResult(
                reply="\n\n".join(lines),
                proposals=proposals,
                is_estimate=False,
                missing_data=context.missing_data,
                provider_name="local",
                model_name=model_name,
            )

    # 2. Suspendre / mettre en pause un apprentissage, un objectif ou un projet nommé
    if any(w in lowered for w in ("suspendre", "mettre en pause", "suspend ")) or re.search(
        r"\b(?:met(?:s|tre)|pass(?:e|er)|plac(?:e|er))\b.*\ben\s+pause\b", lowered
    ):
        matched_goal = _match_by_name_or_tokens(user_message, personal_goals, key="title")
        matched_path = _match_by_name_or_tokens(user_message, learning_paths, key="title")
        matched_proj = _match_by_name_or_tokens(user_message, projects, key="name")
        if matched_goal or matched_path:
            steps: list[dict[str, Any]] = []
            target_label = (matched_goal or matched_path or {}).get("title", "cet objectif")
            if matched_goal and matched_goal.get("status") != "paused":
                steps.append(
                    {
                        "action_type": AiActionType.update_personal_goal.value,
                        "payload": {"goal_id": matched_goal["id"], "status": "paused"},
                    }
                )
            if matched_path and matched_path.get("status") != "paused":
                steps.append(
                    {
                        "action_type": AiActionType.update_learning_path.value,
                        "payload": {"path_id": matched_path["id"], "status": "paused"},
                    }
                )
            if len(steps) == 1:
                proposals.append(
                    RawProposalCandidate(
                        action_type=steps[0]["action_type"],
                        title=f"Suspendre « {target_label} »",
                        explanation="Passe l'élément en pause sans supprimer sa progression.",
                        payload=steps[0]["payload"],
                    )
                )
            elif len(steps) > 1:
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.batch_actions.value,
                        title=f"Suspendre l'apprentissage de « {target_label} »",
                        explanation="Met en pause l'objectif et le parcours associés de manière coordonnée.",
                        payload={"summary": f"Mise en pause de {target_label}", "steps": steps, "compensate_on_failure": True},
                    )
                )
            if proposals:
                lines.append(
                    f"J'ai préparé la mise en pause de **{target_label}** tout en conservant votre progression."
                )
                return ProviderResult(
                    reply="\n\n".join(lines),
                    proposals=proposals,
                    is_estimate=context.is_partial_data,
                    missing_data=context.missing_data,
                    provider_name="local",
                    model_name=model_name,
                )
        if matched_proj and matched_proj.get("status") not in ("paused", "completed", "archived"):
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.pause_project.value,
                    title=f"Mettre en pause le projet « {matched_proj['name']} »",
                    explanation="Suspend le projet sans perte de données.",
                    payload={"project_id": matched_proj["id"], "reason": "Suspension demandée en conversation."},
                )
            )
            lines.append(f"Je propose de mettre le projet **{matched_proj['name']}** en pause.")
            return ProviderResult(
                reply="\n\n".join(lines),
                proposals=proposals,
                is_estimate=context.is_partial_data,
                missing_data=context.missing_data,
                provider_name="local",
                model_name=model_name,
            )

    # 2b. Ajustement du temps hebdomadaire consacré à un objectif existant
    if any(
        w in lowered
        for w in (
            "augmente le temps",
            "augmenter le temps",
            "plus de temps",
            "réduis le temps",
            "reduis le temps",
            "moins de temps",
        )
    ):
        matched_goal = _match_by_name_or_tokens(user_message, personal_goals, key="title")
        if matched_goal is not None:
            current_mins = int(matched_goal.get("weekly_target_minutes") or 120)
            explicit_h = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:h|heures?)", lowered)
            if explicit_h:
                next_mins = max(30, min(1200, int(round(float(explicit_h.group(1).replace(",", ".")) * 60))))
            elif any(w in lowered for w in ("réduis", "reduis", "moins de temps")):
                next_mins = max(30, current_mins - 60)
            else:
                next_mins = min(1200, current_mins + 60)
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.update_personal_goal.value,
                    title=f"Ajuster le volume hebdo de « {matched_goal['title']} » ({next_mins} min/sem.)",
                    explanation="Met à jour l'objectif existant sans créer de doublon.",
                    payload={
                        "goal_id": matched_goal["id"],
                        "weekly_target_minutes": next_mins,
                    },
                )
            )
            lines.append(
                f"J'ai retrouvé votre objectif **{matched_goal['title']}** et préparé l'ajustement à **{next_mins} min/semaine**."
            )
            return ProviderResult(
                reply="\n\n".join(lines),
                proposals=proposals,
                is_estimate=context.is_partial_data,
                missing_data=context.missing_data,
                provider_name="local",
                model_name=model_name,
            )

    # 3. Continuer un parcours existant (tout en apprenant éventuellement un nouveau sujet) sans doublon
    if any(w in lowered for w in ("continuer", "continuant", "reprendre", "poursuivre")) and "suivi" not in lowered:
        matched_path = _match_by_name_or_tokens(user_message, learning_paths, key="title")
        matched_goal = _match_by_name_or_tokens(user_message, personal_goals, key="title")
        learn_m = re.search(
            r"(?:apprendre|débuter|maîtriser)\s+(?:le\s+|la\s+|l['’])?([A-Za-zÀ-ÿ0-9_+#.-]{2,40})",
            user_message,
            re.IGNORECASE,
        )
        new_topic = learn_m.group(1).strip(" .,?!") if learn_m else None
        existing_label = (
            (matched_path or {}).get("title") or (matched_goal or {}).get("title") or ""
        )
        already_same = bool(new_topic and existing_label and new_topic.lower() in existing_label.lower())
        if matched_path or matched_goal:
            steps: list[dict[str, Any]] = []
            if matched_path:
                steps.append(
                    {
                        "action_type": AiActionType.update_learning_path.value,
                        "payload": {
                            "path_id": matched_path["id"],
                            "status": "active",
                            "goal": matched_path.get("goal") or f"Poursuivre et approfondir {matched_path['title']}",
                        },
                    }
                )
            elif matched_goal:
                steps.append(
                    {
                        "action_type": AiActionType.update_personal_goal.value,
                        "payload": {
                            "goal_id": matched_goal["id"],
                            "status": "active",
                        },
                    }
                )
            if new_topic and not already_same:
                existing_goal_new = next(
                    (g for g in personal_goals if new_topic.lower() in g["title"].lower()),
                    None,
                )
                if existing_goal_new is None:
                    steps.append(
                        {
                            "action_type": AiActionType.create_personal_goal.value,
                            "payload": {
                                "title": new_topic,
                                "category": "learning_goal",
                                "goal": f"Apprendre et pratiquer {new_topic}",
                                "current_level": 0,
                                "target_level": 3,
                                "priority": "high",
                                "weekly_target_minutes": 180,
                                "next_action": f"Démarrer les fondamentaux de {new_topic}",
                                "create_linked_entities": True,
                            },
                        }
                    )
            if len(steps) == 1:
                only_step = steps[0]
                proposals.append(
                    RawProposalCandidate(
                        action_type=only_step["action_type"],
                        title=f"Poursuivre « {existing_label} » sans doublon",
                        explanation="Réutilise et maintient actif votre parcours existant.",
                        payload=only_step["payload"],
                    )
                )
                lines.append(
                    f"J'ai retrouvé votre suivi existant **{existing_label}** : je propose de le mettre à jour sans créer de doublon."
                )
            elif len(steps) > 1:
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.batch_actions.value,
                        title=f"Apprendre « {new_topic} » tout en continuant « {existing_label} »",
                        explanation="Met à jour votre parcours existant sans doublon et crée le nouvel objectif demandé.",
                        payload={
                            "summary": f"Continuer {existing_label} et lancer {new_topic}",
                            "steps": steps,
                            "compensate_on_failure": True,
                        },
                    )
                )
                lines.append(
                    f"J'ai retrouvé votre parcours existant **{existing_label}** (mis à jour sans doublon) "
                    f"et préparé l'ajout de votre nouvel objectif **{new_topic}**."
                )
            if proposals:
                return ProviderResult(
                    reply="\n\n".join(lines),
                    proposals=proposals,
                    is_estimate=context.is_partial_data,
                    missing_data=context.missing_data,
                    provider_name="local",
                    model_name=model_name,
                )

    # 4. Création d'une compétence (rattachée au bon objectif / parcours)
    if any(
        w in lowered
        for w in (
            "ajoute une compétence",
            "ajouter une compétence",
            "nouvelle compétence",
            "crée une compétence",
            "créer une compétence",
        )
    ):
        skill_name = _extract_clean_entity_name(
            user_message,
            (
                r"compétence\s+(?:liée\s+(?:à\s+(?:la\s+maîtrise\s+(?:de\s+|des\s+|d['’])?)?|aux?\s+)|sur\s+|en\s+|pour\s+)([^\n\.]{2,100})",
                r"compétence\s+([^\n\.]{2,100})",
            ),
            "Nouvelle compétence",
            max_len=120,
        )
        matched_goal = _match_by_name_or_tokens(user_message + " " + skill_name, personal_goals, key="title")
        matched_path = _match_by_name_or_tokens(user_message + " " + skill_name, learning_paths, key="title")
        skill_payload: dict[str, Any] = {
            "name": skill_name,
            "domain": (matched_goal or {}).get("title") or "Développement",
            "description": f"Compétence ajoutée depuis la conversation : {skill_name}.",
            "target_level": 3,
        }
        if matched_goal:
            skill_payload["goal_id"] = matched_goal["id"]
        if matched_path:
            skill_payload["learning_path_id"] = matched_path["id"]
        proposals.append(
            RawProposalCandidate(
                action_type=AiActionType.create_skill.value,
                title=f"Ajouter la compétence « {skill_name} »",
                explanation="Crée la compétence au niveau initial 0 et la rattache à votre objectif existant.",
                payload=skill_payload,
            )
        )
        link_note = f" rattachée à **{matched_goal['title']}**" if matched_goal else ""
        lines.append(
            f"J'ai préparé l'ajout de la compétence **{skill_name}** (niveau initial 0 verrouillé){link_note}."
        )
        return ProviderResult(
            reply="\n\n".join(lines),
            proposals=proposals,
            is_estimate=context.is_partial_data,
            missing_data=context.missing_data,
            provider_name="local",
            model_name=model_name,
        )

    # 5. Création directe d'un projet concret avec objectif et prochaine action
    if any(
        w in lowered
        for w in (
            "crée un projet",
            "créer un projet",
            "crée-moi un projet",
            "cree-moi un projet",
            "crée moi un projet",
            "fais-moi un projet",
            "nouveau projet",
            "ajoute un projet",
            "ajouter un projet",
        )
    ):
        matched_goal = _match_by_name_or_tokens(user_message, personal_goals, key="title")
        fallback_proj_name = (
            f"Projet pratique : {matched_goal['title']}"
            if matched_goal
            else "Projet d'application pratique"
        )
        proj_name = _extract_clean_entity_name(
            user_message,
            (
                r"projet\s+(?:pour\s+(?:pratiquer|mettre\s+en\s+pratique)\s+|pour\s+|sur\s+|de\s+|intitulé\s+|nommé\s+)([^\n\.]{2,110})",
            ),
            fallback_proj_name,
            max_len=140,
        )
        if proj_name.lower().startswith("mettre en pratique"):
            proj_name = (
                f"Application pratique : {matched_goal['title']}"
                if matched_goal
                else "Projet de mise en pratique"
            )
        elif matched_goal and proj_name.strip().lower() == matched_goal["title"].strip().lower():
            proj_name = f"Projet pratique : {matched_goal['title']}"
        active_projs_cnt = sum(1 for p in projects if p.get("status") == "active")
        proj_status = "planned" if active_projs_cnt >= 3 else "active"
        proj_payload: dict[str, Any] = {
            "name": proj_name,
            "category": "project",
            "goal": f"Mettre en pratique concrètement {matched_goal['title'] if matched_goal else proj_name}",
            "status": proj_status,
            "priority": "normal",
            "weekly_target_minutes": 180,
            "next_action": f"Initialiser le dépôt et la structure minimale pour {proj_name}",
        }
        if matched_goal:
            proj_payload["goal_id"] = matched_goal["id"]
        proposals.append(
            RawProposalCandidate(
                action_type=AiActionType.create_project.value,
                title=f"Créer le projet « {proj_name} »",
                explanation="Crée le projet avec son objectif et sa prochaine action concrète.",
                payload=proj_payload,
            )
        )
        lines.append(
            f"J'ai préparé la création du projet **{proj_name}** avec son objectif et sa prochaine action concrète."
        )
        return ProviderResult(
            reply="\n\n".join(lines),
            proposals=proposals,
            is_estimate=context.is_partial_data,
            missing_data=context.missing_data,
            provider_name="local",
            model_name=model_name,
        )

    # 5b. Modification / changement de priorité d'une tâche existante
    if any(
        w in lowered
        for w in (
            "passe la tâche",
            "passer la tâche",
            "modifie la tâche",
            "modifier la tâche",
            "mets la tâche",
            "mettre la tâche",
            "change la priorité",
            "changer la priorité",
            "priorité de la tâche",
        )
    ) and active_tasks:
        matched_task = _match_by_name_or_tokens(user_message, active_tasks, key="title") or active_tasks[0]
        upd_payload: dict[str, Any] = {"task_id": matched_task["id"]}
        if "critique" in lowered or "critical" in lowered:
            upd_payload["priority"] = "critical"
        elif any(k in lowered for k in ("haute", "haut", "urgent", "prioritaire")):
            upd_payload["priority"] = "high"
        elif "normale" in lowered:
            upd_payload["priority"] = "normal"
        elif any(k in lowered for k in ("basse", "faible")):
            upd_payload["priority"] = "low"
        if any(k in lowered for k in ("termine", "terminée", "fini")):
            upd_payload["status"] = "done"
        elif "en cours" in lowered:
            upd_payload["status"] = "in_progress"
        elif "parking" in lowered:
            upd_payload["status"] = "parked"
        if len(upd_payload) > 1:
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.update_task.value,
                    title=f"Mettre à jour « {matched_task['title']} »",
                    explanation="Met à jour la tâche existante sans créer de doublon.",
                    payload=upd_payload,
                )
            )
            lines.append(
                f"J'ai préparé la mise à jour de votre tâche **{matched_task['title']}**."
            )
            return ProviderResult(
                reply="\n\n".join(lines),
                proposals=proposals,
                is_estimate=context.is_partial_data,
                missing_data=context.missing_data,
                provider_name="local",
                model_name=model_name,
            )

    # 6. Réorganisation des tâches non terminées / journée en retard
    if any(
        w in lowered
        for w in (
            "pas terminé mes tâches",
            "pas fini mes tâches",
            "réorganise ma journée",
            "réorganiser ma journée",
            "réorganise mon planning",
        )
    ):
        steps = []
        target_tasks = [t for t in active_tasks if t.get("is_overdue")] or active_tasks[:2]
        today_windows = ((context.availability or {}).get("today") or {}).get("recommended_study_windows") or []
        chosen_slot = today_windows[0] if today_windows else (weekly_slots[0] if weekly_slots else None)
        ref_due = chosen_slot["ends_at"] if chosen_slot else (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
        for t in target_tasks[:2]:
            steps.append(
                {
                    "action_type": AiActionType.update_task.value,
                    "payload": {
                        "task_id": t["id"],
                        "due_at": ref_due,
                        "priority": "high",
                    },
                }
            )
        if chosen_slot:
            steps.append(
                {
                    "action_type": AiActionType.create_schedule_event.value,
                    "payload": {
                        "title": f"Rattrapage : {target_tasks[0]['title']}" if target_tasks else "Session de réorganisation du jour",
                        "type": "learning",
                        "starts_at": chosen_slot["starts_at"],
                        "ends_at": chosen_slot["ends_at"],
                        "notes": "Réorganisation proposée par le Copilote IA en dehors des cours.",
                    },
                }
            )
        if steps:
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.batch_actions.value,
                    title="Réorganiser la journée et reporter les tâches restantes",
                    explanation="Met à jour vos échéances et bloque un créneau libre hors cours universitaires.",
                    payload={"summary": "Réorganisation de journée", "steps": steps, "compensate_on_failure": True},
                )
            )
            lines.append(
                f"J'ai préparé la réorganisation de votre journée ({len(target_tasks[:2])} tâche(s) replacée(s) et créneau libre vérifié)."
            )
            return ProviderResult(
                reply="\n\n".join(lines),
                proposals=proposals,
                is_estimate=context.is_partial_data,
                missing_data=context.missing_data,
                provider_name="local",
                model_name=model_name,
            )

    # 6b. Déplacement / report d'une séance existante dans l'agenda
    if any(
        w in lowered
        for w in (
            "déplace ma séance",
            "deplace ma seance",
            "déplacer ma séance",
            "décale ma séance",
            "decale ma seance",
            "déplace le créneau",
            "décale le créneau",
            "reprogramme ma séance",
        )
    ):
        sched_events = list(context.schedule_events or [])
        movable = [ev for ev in sched_events if not ev.get("is_university_course")]
        candidates = (
            [ev for ev in movable if ev.get("is_tomorrow")]
            if "demain" in lowered
            else []
        ) or [ev for ev in movable if not ev.get("is_past")] or movable
        if candidates:
            target_ev = candidates[0]
            try:
                old_s = datetime.fromisoformat(str(target_ev["starts_at"]).replace("Z", "+00:00"))
                old_e = datetime.fromisoformat(str(target_ev["ends_at"]).replace("Z", "+00:00"))
            except ValueError:
                old_s = datetime.now(timezone.utc) + timedelta(days=1)
                old_e = old_s + timedelta(hours=1)
            dur_td = max(timedelta(minutes=30), old_e - old_s)

            # Choisir un autre créneau disponible sans chevauchement
            new_s: datetime | None = None
            new_e: datetime | None = None
            for slot in weekly_slots:
                try:
                    slot_s = datetime.fromisoformat(str(slot["starts_at"]).replace("Z", "+00:00"))
                    slot_e = datetime.fromisoformat(str(slot["ends_at"]).replace("Z", "+00:00"))
                except ValueError:
                    continue
                if abs((slot_s - old_s).total_seconds()) < 1800:
                    continue
                if slot_e - slot_s >= dur_td:
                    new_s = slot_s
                    new_e = slot_s + dur_td
                    break
            if new_s is None or new_e is None:
                new_s = old_s + timedelta(hours=2)
                new_e = new_s + dur_td

            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.update_schedule_event.value,
                    title=f"Déplacer « {target_ev['title']} »",
                    explanation="Déplace la séance sur un autre créneau libre tout en préservant vos cours universitaires.",
                    payload={
                        "event_id": target_ev["id"],
                        "starts_at": new_s.isoformat(),
                        "ends_at": new_e.isoformat(),
                        "reason": "Déplacement demandé en conversation.",
                    },
                )
            )
            lines.append(
                f"J'ai préparé le déplacement de votre séance **{target_ev['title']}** vers un nouveau créneau sans conflit."
            )
            return ProviderResult(
                reply="\n\n".join(lines),
                proposals=proposals,
                is_estimate=context.is_partial_data,
                missing_data=context.missing_data,
                provider_name="local",
                model_name=model_name,
            )

    # 7. Planification de N séances cette semaine (respectant disponibilités + cours + volume hebdo)
    multi_session_m = re.search(
        r"(?:programme|planifie|organise|prévois|ajoute)\s+(?:[2-7]|deux|trois|quatre|cinq|six|plusieurs|des)\s+(?:séances|sessions|créneaux)\b",
        lowered,
    )
    if multi_session_m or re.search(
        r"\b(?:deux|trois|quatre|cinq|six|[2-7])\s+(?:séances|sessions|créneaux)\s+(?:cette\s+semaine|sur\s+la\s+semaine)\b",
        lowered,
    ):
        count = _extract_count_word(lowered, default=3)
        weekly_budget_min = avail_prefs.get("max_weekly_study_minutes")
        existing_personal_min = int((context.strategic_analysis or {}).get("weekly_personal_minutes", 0))
        # Sélectionner des créneaux distincts par jour en priorité dans weekly_candidate_slots
        selected_slots: list[dict[str, Any]] = []
        used_dates: set[str] = set()
        accumulated_min = existing_personal_min
        for slot in weekly_slots:
            if len(selected_slots) >= count:
                break
            if slot["local_date"] in used_dates:
                continue
            if weekly_budget_min is not None and (accumulated_min + int(slot["duration_minutes"])) > int(weekly_budget_min):
                continue
            selected_slots.append(slot)
            used_dates.add(slot["local_date"])
            accumulated_min += int(slot["duration_minutes"])
        for slot in weekly_slots:
            if len(selected_slots) >= count:
                break
            if slot in selected_slots:
                continue
            if weekly_budget_min is not None and (accumulated_min + int(slot["duration_minutes"])) > int(weekly_budget_min):
                continue
            selected_slots.append(slot)
            accumulated_min += int(slot["duration_minutes"])

        if selected_slots:
            primary_focus = (
                (personal_goals[0]["title"] if personal_goals else None)
                or context.profile.get("active_priority_title")
                or (projects[0]["name"] if projects else "Travail personnel")
            )
            steps = [
                {
                    "action_type": AiActionType.create_schedule_event.value,
                    "payload": {
                        "title": f"Séance {idx + 1} : {primary_focus}",
                        "type": "learning",
                        "starts_at": slot["starts_at"],
                        "ends_at": slot["ends_at"],
                        "notes": f"Planifié selon vos disponibilités ({slot['day_label']} {slot['local_start_time']} à {slot['local_end_time']}).",
                    },
                }
                for idx, slot in enumerate(selected_slots)
            ]
            if len(steps) == 1:
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.create_schedule_event.value,
                        title=f"Planifier 1 séance ({primary_focus})",
                        explanation="Créneau sans conflit conforme à vos disponibilités.",
                        payload=steps[0]["payload"],
                    )
                )
            else:
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.batch_actions.value,
                        title=f"Programmer {len(steps)} séances cette semaine ({primary_focus})",
                        explanation="Respecte vos cours universitaires, jours exclus et contraintes mémorisées.",
                        payload={
                            "summary": f"{len(steps)} séances hebdomadaires pour {primary_focus}",
                            "steps": steps,
                            "compensate_on_failure": True,
                        },
                    )
                )
            slot_desc = ", ".join(
                f"{s['day_label']} {s['local_start_time']} à {s['local_end_time']}" for s in selected_slots
            )
            budget_note = (
                f" (budget hebdo {avail_prefs.get('weekly_study_hours')}h respecté)"
                if avail_prefs.get("weekly_study_hours") is not None
                else ""
            )
            course_entries: list[str] = []
            for c in (context.university_courses or [])[:3]:
                title_str = str(c.get("title", "")).strip()
                if not title_str:
                    continue
                st = str(c.get("local_start_time") or "").strip()
                et = str(c.get("local_end_time") or "").strip()
                course_entries.append(f"{title_str} ({st} à {et})" if st and et else title_str)
            course_note = (
                f" (cours respectés : {', '.join(course_entries)})" if course_entries else ""
            )
            lines.append(
                f"J'ai sélectionné **{len(selected_slots)} séance(s)** disponibles{budget_note} sans chevaucher vos cours{course_note} : {slot_desc}."
            )
            return ProviderResult(
                reply="\n\n".join(lines),
                proposals=proposals,
                is_estimate=context.is_partial_data,
                missing_data=context.missing_data,
                provider_name="local",
                model_name=model_name,
            )

    # 7b. Génération ou recalcul du programme d'apprentissage intelligent multi-sources
    if any(
        p in lowered
        for p in (
            "programme d'apprentissage",
            "programme d’apprentissage",
            "programme d apprentissage",
            "emploi du temps d'apprentissage",
            "emploi du temps d’apprentissage",
            "génère mon programme",
            "genere mon programme",
            "crée-moi un programme",
            "cree-moi un programme",
            "programme mes séances",
            "planifie mes séances",
            "organise mes séances",
            "prépare mes révisions",
            "prepare mes revisions",
            "préparer mes révisions",
            "révisions pour l'examen",
            "révisions pour l’examen",
            "organise mes révisions",
            "organise mes revisions",
            "recalcule mon programme",
            "allège mon programme",
            "allege mon programme",
        )
    ):
        plan_payload: dict[str, Any] = {
            "horizon_days": 7,
            "include_potential_slots": True,
            "apply_immediately": True,
            "replace_future_planned": True,
        }
        if any(k in lowered for k in ("recalcule", "allège", "allege")):
            plan_payload["instruction"] = user_message.strip()[:450]

        exam_m = re.search(
            r"(?:examen|partiel|contrôle)\s+(?:de|d['’]|en|sur)?\s*([A-Za-zÀ-ÿ0-9_+#.-]{2,40})",
            user_message,
            re.IGNORECASE,
        )
        missing_exam_date_note = ""
        if exam_m:
            ex_subj = exam_m.group(1).strip()
            plan_payload["exam_title"] = f"Examen {ex_subj}"
            plan_payload["focus_subject"] = ex_subj

            resolved_exam_at: str | None = None
            iso_date_m = re.search(r"\b(20\d{2}-\d{2}-\d{2})(?:[T\s](\d{1,2})[:h](\d{2}))?\b", user_message)
            fr_date_m = re.search(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})(?:\s+(?:à\s+)?(\d{1,2})[:h](\d{2}))?\b", user_message)
            if iso_date_m:
                try:
                    dt_d = date.fromisoformat(iso_date_m.group(1))
                    hr = int(iso_date_m.group(2)) if iso_date_m.group(2) is not None else 9
                    mn = int(iso_date_m.group(3)) if iso_date_m.group(3) is not None else 0
                    resolved_exam_at = datetime(dt_d.year, dt_d.month, dt_d.day, hr, mn, tzinfo=timezone.utc).isoformat()
                except ValueError:
                    resolved_exam_at = None
            elif fr_date_m:
                try:
                    day_i, month_i, year_i = int(fr_date_m.group(1)), int(fr_date_m.group(2)), int(fr_date_m.group(3))
                    hr = int(fr_date_m.group(4)) if fr_date_m.group(4) is not None else 9
                    mn = int(fr_date_m.group(5)) if fr_date_m.group(5) is not None else 0
                    resolved_exam_at = datetime(year_i, month_i, day_i, hr, mn, tzinfo=timezone.utc).isoformat()
                except ValueError:
                    resolved_exam_at = None

            if resolved_exam_at is None:
                ex_subj_low = ex_subj.lower()
                for ev in context.schedule_events:
                    ev_title = str(ev.get("title") or "").lower()
                    ev_cat = str(ev.get("type") or ev.get("category") or "").lower()
                    if ex_subj_low in ev_title and ("exam" in ev_cat or "exam" in ev_title or "partiel" in ev_title or "contrôle" in ev_title):
                        resolved_exam_at = str(ev.get("starts_at") or "")
                        plan_payload["exam_title"] = str(ev.get("title") or plan_payload["exam_title"])
                        break
            if resolved_exam_at is None:
                ex_subj_low = ex_subj.lower()
                for uc in context.university_courses:
                    uc_title = str(uc.get("title") or "").lower()
                    if ex_subj_low in uc_title and ("exam" in uc_title or "partiel" in uc_title or "contrôle" in uc_title):
                        resolved_exam_at = str(uc.get("starts_at") or "")
                        plan_payload["exam_title"] = str(uc.get("title") or plan_payload["exam_title"])
                        break

            if resolved_exam_at is not None:
                plan_payload["exam_at"] = resolved_exam_at
            else:
                missing_exam_date_note = (
                    f" Aucune date ou heure d'examen réelle n'étant enregistrée pour **{ex_subj}**, "
                    "je n'ai pas inventé de date d'examen et j'ai priorisé vos révisions sur vos créneaux disponibles."
                )
        else:
            focus_m = re.search(
                r"(?:priorité\s+(?:sur|à)|focus\s+sur|centré\s+sur)\s+([A-Za-zÀ-ÿ0-9_+#.-]{2,40})",
                user_message,
                re.IGNORECASE,
            )
            if focus_m:
                plan_payload["focus_subject"] = focus_m.group(1).strip()

        wh_m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:h|heures?)\s*(?:par\s+semaine|/sem|hebdo)", lowered)
        if wh_m:
            plan_payload["weekly_hours_override"] = max(
                1.0, min(60.0, float(wh_m.group(1).replace(",", ".")))
            )

        proposals.append(
            RawProposalCandidate(
                action_type=AiActionType.generate_learning_plan.value,
                title="Générer et appliquer votre programme d'apprentissage personnalisé",
                explanation=(
                    "Croise vos cours fixes, indisponibilités personnelles, objectifs, parcours, "
                    "tâches en retard et historique pour planifier sans conflit ni surcharge."
                ),
                payload=plan_payload,
            )
        )
        lines.append(
            "J'ai préparé votre **programme d'apprentissage intelligent** en croisant votre emploi du temps fixe, "
            "vos règles de disponibilité, vos objectifs actifs, vos tâches et votre historique de travail."
            + missing_exam_date_note
            + " Validez ci-dessous pour l'appliquer au calendrier."
        )
        return ProviderResult(
            reply="\n\n".join(lines),
            proposals=proposals,
            is_estimate=context.is_partial_data,
            missing_data=context.missing_data,
            provider_name="local",
            model_name=model_name,
        )

    # 8. Consultation / vérification des éléments existants (même créés manuellement)
    if any(
        w in lowered
        for w in (
            "quels sont mes",
            "quelles sont mes",
            "retrouve",
            "liste mes",
            "résume ma mémoire",
            "ce que tu sais sur moi",
            "tu vois",
            "vois-tu",
            "trouves-tu",
        )
    ):
        parts: list[str] = ["### Éléments actuels dans votre espace StudyOS"]
        if personal_goals:
            parts.append("- **Objectifs** : " + ", ".join(f"{g['title']} ({g['status']})" for g in personal_goals[:6]))
        if projects:
            parts.append("- **Projets** : " + ", ".join(f"{p['name']} ({p['status']})" for p in projects[:6]))
        if active_tasks:
            parts.append("- **Tâches actives** : " + ", ".join(f"{t['title']} ({t['priority']})" for t in active_tasks[:8]))
        if skills:
            parts.append("- **Compétences** : " + ", ".join(f"{s['name']} ({s['current_level']}/5)" for s in skills[:8]))
        if learning_paths:
            parts.append("- **Parcours** : " + ", ".join(f"{lp['title']} ({lp['status']})" for lp in learning_paths[:6]))
        if context.courses:
            parts.append("- **Cours** : " + ", ".join(f"{c['title']} ({c['status']})" for c in context.courses[:5]))
        if memory.get("weekly_study_hours") is not None:
            parts.append(f"- **Mémoire personnelle** : {memory['weekly_study_hours']}h/semaine disponibles.")
        if len(parts) == 1:
            parts.append("Aucun élément enregistré pour le moment dans ces rubriques.")
        return ProviderResult(
            reply="\n".join(parts),
            proposals=[],
            is_estimate=context.is_partial_data,
            missing_data=context.missing_data,
            provider_name="local",
            model_name=model_name,
        )

    return None


class LocalRuleBasedAIProvider:
    """Adaptateur local déterministe sans clé externe, respectant AI-01 à AI-07."""

    def __init__(self, model_name: str = "local-coach-v1") -> None:
        self._model_name = model_name

    def generate_response(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        context: BoundedUserContext,
        prompt_manager: PromptManager,
    ) -> ProviderResult:
        _ = prompt_manager
        ai_first_result = _handle_ai_first_intents(
            user_message=user_message,
            context=context,
            model_name=self._model_name,
        )
        if ai_first_result is not None:
            return ai_first_result

        strategic_result = _handle_conversational_strategic_planning(
            user_message=user_message,
            history=history,
            context=context,
            model_name=self._model_name,
        )
        if strategic_result is not None:
            return strategic_result

        lowered = user_message.lower()
        proposals: list[RawProposalCandidate] = []
        lines: list[str] = []

        priority_title = context.profile.get("active_priority_title")
        ai_instructions = context.profile.get("ai_instructions")
        active_tasks = context.tasks
        projects = context.projects
        skills = context.skills
        learning_paths = context.learning.get("paths", []) if context.learning else []

        if ai_instructions:
            lines.append(f"*(Consignes personnelles prises en compte : {ai_instructions})*")

        # 0. Intention : création d'un cours complet multi-niveaux (create_course)
        if any(
            w in lowered
            for w in (
                "crée un cours",
                "créer un cours",
                "nouveau cours",
                "cours complet",
                "génère un cours",
                "générer un cours",
                "apprendre le langage",
            )
        ):
            subj_match = re.search(
                r"(?:cours(?:\s+complet)?\s+(?:pour\s+(?:apprendre|maîtriser)|sur|de|en|pour)|(?:pour\s+)?(?:apprendre|maîtriser))\s+(?:le\s+langage\s+|la\s+programmation\s+(?:en\s+)?|le\s+|la\s+|l['’])?([A-Za-zÀ-ÿ0-9_+#.-]{2,40})",
                user_message,
                re.IGNORECASE,
            )
            extracted_subject = _extract_quoted_or_after_colon(
                user_message,
                subj_match.group(1).strip() if subj_match else "Python",
            )
            blueprint = build_course_blueprint(
                subject=extracted_subject,
                language=CourseLanguage.fr,
                total_levels=3,
            )
            lvl1 = generate_level_content(
                subject=blueprint["subject"],
                language=CourseLanguage.fr,
                level_number=1,
                total_levels=3,
            )
            chapter_list = "\n".join(
                f"- **Chapitre {item['position']}** : {item['title']}"
                for item in lvl1["lessons"]
            )
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.create_course.value,
                    title=f"Créer le cours « {blueprint['title']} »",
                    explanation=(
                        "Génère le Niveau 1 complet (4 chapitres progressifs, exercices corrigés, "
                        "projet à rendre et ressources officielles). Les niveaux suivants restent verrouillés jusqu'à validation."
                    ),
                    payload={
                        "subject": blueprint["subject"],
                        "title": blueprint["title"],
                        "domain": blueprint["domain"],
                        "language": CourseLanguage.fr.value,
                        "total_levels": 3,
                        "goal": blueprint["description"],
                    },
                )
            )
            lines.append(
                f"### Aperçu du cours proposé : {blueprint['title']}\n\n"
                f"{chapter_list}\n\n"
                f"- **Projet du Niveau 1** : {lvl1['project_title']}\n"
                f"- **Docs & Vidéos sélectionnées** : {len(lvl1['resources'])} ressource(s) vérifiée(s).\n\n"
                "Ce cours ne sera enregistré qu’après votre validation explicite ci-dessous."
            )
            return ProviderResult(
                reply="\n\n".join(lines),
                proposals=proposals,
                is_estimate=context.is_partial_data,
                missing_data=context.missing_data,
                provider_name="local",
                model_name=self._model_name,
            )

        # 1. Intention : mettre une tâche au parking (Parcours C)
        if any(w in lowered for w in ("parking", "reporter", "reporte", "surcharge", "secondaire")):
            if active_tasks:
                target_task = active_tasks[-1]
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.park_task.value,
                        title=f"Placer « {target_task['title']} » au parking",
                        explanation=(
                            "Allège votre charge immédiate pour protéger votre priorité principale "
                            "(aucune modification sans votre validation)."
                        ),
                        payload={
                            "task_id": target_task["id"],
                            "reason": "Protection du focus quotidien (Parcours C).",
                        },
                    )
                )
                lines.append(
                    f"Pour réduire la surcharge, je vous propose de placer la tâche "
                    f"**« {target_task['title']} »** au parking afin de vous concentrer sur "
                    f"**{priority_title or active_tasks[0]['title']}**."
                )
            else:
                lines.append(
                    "Vous n’avez aucune tâche active à placer au parking pour le moment."
                )

        # 1b. Intention : mettre un projet en pause (pause_project)
        if any(
            w in lowered
            for w in (
                "pause le projet",
                "mettre en pause",
                "suspendre le projet",
                "projet en pause",
            )
        ):
            active_projs = [p for p in projects if p.get("status") == "active"]
            if active_projs:
                target_proj = active_projs[-1]
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.pause_project.value,
                        title=f"Mettre en pause le projet « {target_proj['name']} »",
                        explanation="Libère un emplacement de projet actif (maximum 3 projets actifs simultanés).",
                        payload={
                            "project_id": target_proj["id"],
                            "reason": "Réduction de la dispersion sur les projets actifs.",
                        },
                    )
                )
                lines.append(
                    f"Je vous propose de mettre le projet **« {target_proj['name']} »** en pause après votre validation."
                )
            else:
                lines.append("Vous n’avez aucun projet actif à mettre en pause.")

        # 2. Intention : proposer la création d'une tâche
        if any(
            w in lowered
            for w in ("crée une tâche", "créer une tâche", "ajoute une tâche", "propose une tâche", "nouvelle tâche")
        ):
            default_title = (
                f"Avancer sur {priority_title}"
                if priority_title
                else "Session d’exercices pratiques"
            )
            extracted_title = _extract_quoted_or_after_colon(user_message, default_title)
            if extracted_title == default_title:
                t_m = re.search(
                    r"tâche\s+(?:liée\s+au\s+projet\s+[^:,\.]+(?:\s*[:\-]\s*|\s+pour\s+)|pour\s+)(.+)$",
                    user_message,
                    re.IGNORECASE,
                )
                if t_m and len(t_m.group(1).strip()) >= 2:
                    extracted_title = t_m.group(1).strip().rstrip(".")[:140]
            high_prio = "high" if any(w in lowered for w in ("urgent", "haute", "prioritaire")) else "normal"
            matched_proj = _match_by_name_or_tokens(user_message, projects, key="name")
            if (
                matched_proj is None
                and projects
                and any(
                    w in lowered
                    for w in (
                        "ce projet",
                        "du projet",
                        "au projet",
                        "à mon projet",
                        "a mon projet",
                        "sur mon projet",
                        "mon projet",
                        "lié au projet",
                        "liée à ce projet",
                    )
                )
            ):
                active_projs = [p for p in projects if p.get("status") == "active"]
                matched_proj = active_projs[0] if active_projs else projects[0]
            if matched_proj is not None and extracted_title == default_title:
                extracted_title = f"Prochaine étape : {matched_proj['name']}"[:140]
            task_payload: dict[str, Any] = {
                "title": extracted_title,
                "description": "Proposée par le Copilote IA à partir de votre demande.",
                "priority": high_prio,
            }
            if matched_proj is not None:
                task_payload["project_id"] = matched_proj["id"]
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.create_task.value,
                    title=f"Créer la tâche « {extracted_title} »",
                    explanation="Tâche structurée prête à être ajoutée après votre validation.",
                    payload=task_payload,
                )
            )
            proj_note = (
                f" et rattachée au projet **{matched_proj['name']}**"
                if matched_proj is not None
                else ""
            )
            lines.append(
                f"J’ai préparé une proposition de tâche **« {extracted_title} »** (priorité `{high_prio}`){proj_note}. "
                "Vous pouvez ajuster ses paramètres ou la valider ci-dessous."
            )

        # 3. Intention : proposer un créneau dans le planning / organiser la journée ou le lendemain
        if any(
            w in lowered
            for w in (
                "créneau",
                "planifie",
                "planifier",
                "programme",
                "emploi du temps",
                "demain",
                "lendemain",
                "journée",
                "disponibilité",
                "libre",
                "organise",
            )
        ):
            is_tomorrow = any(w in lowered for w in ("demain", "lendemain"))
            day_key = "tomorrow" if is_tomorrow else "today"
            day_label = "demain" if is_tomorrow else "aujourd’hui"
            day_plan = (context.availability or {}).get(day_key) or {}
            uni_courses = day_plan.get("university_courses") or []
            personal_blocks = day_plan.get("personal_blocks") or []
            rec_windows = day_plan.get("recommended_study_windows") or []
            target_date_str = day_plan.get("date") or context.profile.get("local_date", "")

            lines.append(f"### Organisation & Disponibilités pour {day_label} ({target_date_str})")

            if uni_courses:
                course_summaries = [
                    f"**{c['title']}** ({c['local_start_time']} à {c['local_end_time']})"
                    + (f", Salle {c['room']}" if c.get("room") else "")
                    for c in uni_courses
                ]
                lines.append(
                    f"- **Cours universitaires verrouillés ({len(uni_courses)})** : "
                    + ", ".join(course_summaries)
                )
            else:
                lines.append(f"- **Cours universitaires** : aucun cours universitaire enregistré pour {day_label}.")

            if personal_blocks:
                personal_summaries = [
                    f"**{b['title']}** ({b['local_start_time']} à {b['local_end_time']})"
                    for b in personal_blocks
                ]
                lines.append(
                    f"- **Séances personnelles déjà planifiées ({len(personal_blocks)})** : "
                    + ", ".join(personal_summaries)
                )

            # Détermination de l'objectif prioritaire (retards > lacunes compétences > projets > priorité active)
            overdue_tasks = [t for t in active_tasks if t.get("is_overdue")]
            skills_with_gaps = [s for s in skills if s.get("latest_gaps")]
            active_projects = [p for p in projects if p.get("status") == "active"]

            default_slot_type = "learning"
            if any(w in lowered for w in ("projet", "livrable")) and active_projects:
                default_title = f"Avancement projet : {active_projects[0]['name']}"
                default_slot_type = "project"
            elif overdue_tasks:
                default_title = f"Rattrapage prioritaire : {overdue_tasks[0]['title']}"
            elif skills_with_gaps:
                default_title = f"Révision ciblée : {skills_with_gaps[0]['name']}"
            elif uni_courses:
                default_title = f"Révision & exercices : {uni_courses[0]['title']}"
            elif active_projects:
                default_title = f"Travail projet : {active_projects[0]['name']}"
                default_slot_type = "project"
            else:
                default_title = f"Bloc focus : {priority_title or 'Étude approfondie'}"

            slot_title = _extract_quoted_or_after_colon(user_message, default_title)

            chosen_win: dict[str, Any] | None = None
            if rec_windows:
                chosen_win = rec_windows[0]
                win_labels = [
                    f"`{w['local_start_time']} à {w['local_end_time']}` ({w['duration_minutes']} min)"
                    for w in rec_windows
                ]
                lines.append(
                    f"- **Créneaux libres recommandés (hors cours & pauses préservées)** : "
                    + ", ".join(win_labels)
                )
            else:
                weekly_fallback = (context.availability or {}).get("weekly_candidate_slots") or []
                if weekly_fallback:
                    chosen_win = weekly_fallback[0]
                    lines.append(
                        f"- **Aucun créneau libre sur {day_label}** : report proposé sur le prochain créneau disponible "
                        f"**{chosen_win['day_label']} ({chosen_win['local_date']}) de {chosen_win['local_start_time']} à {chosen_win['local_end_time']}**."
                    )
                else:
                    lines.append(
                        "- **Aucune disponibilité libre détectée** sur la période sans conflit avec vos cours ou événements existants."
                    )

            if chosen_win is not None and any(
                w in lowered
                for w in ("créneau", "planifie", "planifier", "programme", "demain", "lendemain", "organise", "révision", "réviser")
            ):
                slot_start_iso = chosen_win["starts_at"]
                slot_end_iso = chosen_win["ends_at"]
                local_range = f"{chosen_win['local_start_time']} à {chosen_win['local_end_time']}"
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.create_schedule_event.value,
                        title=f"Planifier « {slot_title} » ({local_range})",
                        explanation=(
                            "Créneau positionné sur une disponibilité réelle en dehors de vos cours "
                            "universitaires, avec préservation des pauses."
                        ),
                        payload={
                            "title": slot_title,
                            "type": default_slot_type,
                            "starts_at": slot_start_iso,
                            "ends_at": slot_end_iso,
                            "notes": "Créneau sans conflit proposé par le Copilote IA.",
                        },
                    )
                )
                lines.append(
                    f"Je vous propose de planifier **« {slot_title} »** sur le créneau libre "
                    f"**{local_range}** (aucun chevauchement avec vos cours universitaires)."
                )

        # 4. Intention : preuve concrète (sans fabrication IA) ou évaluation pédagogique
        if any(w in lowered for w in ("preuve", "justifier")) and skills:
            target_skill = skills[0]
            ev_desc = _extract_quoted_or_after_colon(user_message, "")
            quality = validate_evidence_quality("exercise", ev_desc, None, None)
            if ev_desc and quality.admissible:
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.add_skill_evidence.value,
                        title=f"Ajouter une preuve sur « {target_skill['name']} »",
                        explanation="Enregistre la preuve concrète décrite par l’utilisateur.",
                        payload={
                            "skill_id": target_skill["id"],
                            "type": "exercise",
                            "description": ev_desc,
                        },
                    )
                )
                lines.append(
                    f"J’ai préparé l’enregistrement de votre preuve sur **{target_skill['name']}**."
                )
            else:
                lines.append(
                    f"Conformément au verrou pédagogique, je ne peux pas fabriquer une preuve pour **{target_skill['name']}**. "
                    "Indiquez entre guillemets la production concrète réalisée (code écrit, exercice résolu, test exécuté) "
                    "ou lancez une évaluation."
                )
        elif (
            any(
                w in lowered
                for w in (
                    "niveau",
                    "évaluer",
                    "évaluation",
                    "monter compétence",
                    "valider compétence",
                    "tester",
                    "réviser",
                    "révision",
                    "renforcer",
                    "lacune",
                )
            )
            and skills
        ):
            # Privilégie une compétence ayant des lacunes récentes si demande de révision
            target_skill = next(
                (s for s in skills if s.get("latest_gaps")),
                skills[0],
            )
            latest_status = target_skill.get("latest_assessment_status")
            latest_passed = target_skill.get("latest_assessment_passed")
            latest_id = target_skill.get("latest_assessment_id")
            latest_proposed = target_skill.get("latest_assessment_proposed_level")
            latest_ev_ids = target_skill.get("latest_assessment_evidence_ids") or []
            latest_gaps = target_skill.get("latest_gaps") or []

            if (
                latest_status == "evaluated"
                and latest_passed is True
                and latest_id
                and latest_proposed is not None
                and len(latest_ev_ids) > 0
            ):
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.recommend_skill_progression.value,
                        title=(
                            f"Valider la progression de « {target_skill['name']} » "
                            f"au niveau {latest_proposed}/5"
                        ),
                        explanation=(
                            "L’évaluation a été soumise, évaluée positivement selon la grille "
                            "et appuyée par une preuve vérifiée."
                        ),
                        payload={
                            "skill_id": target_skill["id"],
                            "assessment_id": latest_id,
                            "proposed_level": int(latest_proposed),
                            "evidence_ids": latest_ev_ids,
                            "decision_reason": (
                                f"Validation recommandée après score de "
                                f"{target_skill.get('latest_assessment_score')}/100."
                            ),
                        },
                    )
                )
                lines.append(
                    f"L’évaluation de **{target_skill['name']}** est réussie "
                    f"({target_skill.get('latest_assessment_score')}/100). "
                    f"Je vous recommande de valider le passage au niveau **{latest_proposed}/5**."
                )
            else:
                curr_lvl = int(target_skill.get("current_level", 0))
                next_lvl = min(5, max(1, curr_lvl + 1))
                is_remediation = len(latest_gaps) > 0
                proposals.append(
                    RawProposalCandidate(
                        action_type=AiActionType.propose_skill_assessment.value,
                        title=(
                            f"{'Exercice correctif' if is_remediation else 'Évaluer'} "
                            f"« {target_skill['name']} » (objectif niveau {next_lvl}/5)"
                        ),
                        explanation=(
                            "Le niveau d’une compétence ne peut évoluer qu’après une évaluation "
                            "soumise, corrigée selon critères et appuyée par une preuve admissible."
                        ),
                        payload={
                            "skill_id": target_skill["id"],
                            "target_level": next_lvl,
                            "assessment_type": "practical_exercise",
                        },
                    )
                )
                if is_remediation:
                    lines.append(
                        f"Vos résultats précédents sur **{target_skill['name']}** (niveau actuel {curr_lvl}/5) "
                        f"montrent des points à renforcer : *{'; '.join(latest_gaps[:2])}*. "
                        f"Je vous propose une révision ciblée suivie d’un exercice correctif pour viser le niveau **{next_lvl}/5**."
                    )
                else:
                    lines.append(
                        f"Le niveau de **{target_skill['name']}** (actuellement **{curr_lvl}/5**) est protégé par le verrou pédagogique. "
                        f"Je vous propose de lancer une évaluation structurée vers le niveau **{next_lvl}/5** "
                        "(avec indices progressifs sans révéler la solution)."
                    )

        # 5. Réponse pédagogique ou synthèse quotidienne par défaut
        if not lines:
            if any(w in lowered for w in ("exercice", "quiz", "entraîne", "explique")):
                topic = (
                    learning_paths[0]["title"]
                    if learning_paths
                    else (skills[0]["name"] if skills else (priority_title or "vos études"))
                )
                lines.append(f"### Mini-exercice ciblé : {topic}")
                lines.append(
                    "1. **Question de synthèse** : reformulez en 3 lignes le problème concret que résout ce sujet.\n"
                    "2. **Mise en pratique (25 min)** : écrivez un cas minimal reproductible et testez un cas d’erreur.\n"
                    "3. **Trace de preuve** : notez le résultat obtenu dans votre journal de séance ou vos preuves de compétences."
                )
            else:
                lines.append("### Synthèse & ordre de travail recommandé")
                if priority_title:
                    lines.append(f"- **Priorité principale à protéger** : {priority_title}")
                else:
                    lines.append(
                        "- **Priorité principale** : aucune priorité active définie, choisissez un objectif unique sur le Tableau de bord."
                    )

                if active_tasks:
                    top_titles = ", ".join(
                        f"**{t['title']}** (`{t['priority']}`)" for t in active_tasks[:3]
                    )
                    lines.append(
                        f"- **Tâches actives prioritaires ({len(active_tasks)})** : {top_titles}"
                    )
                else:
                    lines.append("- **Tâches actives** : aucune tâche active enregistrée.")

                if projects:
                    active_proj = [p for p in projects if p["status"] == "active"]
                    if active_proj:
                        p0 = active_proj[0]
                        lines.append(
                            f"- **Projet actif** : **{p0['name']}** → prochaine action : *{p0['next_action']}*"
                        )

                lines.append(
                    "\n*Astuce : demandez-moi « crée une tâche : ... », « mets une tâche au parking » ou « planifie un créneau » pour générer une proposition validable.*"
                )

        return ProviderResult(
            reply="\n\n".join(lines),
            proposals=proposals,
            is_estimate=context.is_partial_data,
            missing_data=context.missing_data,
            provider_name="local",
            model_name=self._model_name,
        )


def _sanitize_ai_reply_dashes(text: str) -> str:
    """Supprime les tirets typographiques et d'incise en prose tout en préservant le code et les listes Markdown."""
    if not text:
        return text

    marker = "\x00STOP_DISPERSION\x00"
    parts = re.split(r"(```[\s\S]*?```|`[^`\n]+`)", text)
    for idx in range(0, len(parts), 2):
        seg = parts[idx]
        if not seg:
            continue
        seg = seg.replace("STOP — DISPERSION DÉTECTÉE.", marker)
        seg = re.sub(
            r"(\b\d{1,2}(?::\d{2}|h\d{0,2}))\s*[–—]\s*(\d{1,2}(?::\d{2}|h\d{0,2})\b)",
            r"\1 à \2",
            seg,
        )
        seg = re.sub(r"(\b\d+)\s*[–—]\s*(\d+\b)", r"\1 à \2", seg)
        seg = re.sub(r"(\*\*[^*\n]+?:\s*\*\*)\s*[—–-]\s+", r"\1 ", seg)
        seg = re.sub(r"(\*\*[^*\n]*?[^:*\s]\*\*)\s*[—–-]\s+", r"\1 : ", seg)
        seg = re.sub(r"(?m)^(#{1,6}\s+[^\n]+?)\s+[—–-]\s+", r"\1 : ", seg)
        seg = re.sub(r"(?m)^([ \t]*)[—–]\s+", r"\1- ", seg)
        seg = re.sub(r"\s+[—–]\s+([^—–\n]+?)\s+[—–]\s+", r", \1, ", seg)
        seg = re.sub(r"\s*[—–]\s*", ", ", seg)
        seg = re.sub(
            r"(?<=[A-Za-zÀ-ÖØ-öø-ÿ»)\]])\s+-\s+(?=[A-Za-zÀ-ÖØ-öø-ÿ«(])",
            ", ",
            seg,
        )
        seg = re.sub(r"([,;:])\s*,\s*", r"\1 ", seg)
        seg = re.sub(r"[ \t]+,", ",", seg)
        seg = seg.replace(marker, "STOP — DISPERSION DÉTECTÉE.")
        parts[idx] = seg
    return "".join(parts)


_PROTOCOL_JSON_KEYS: frozenset[str] = frozenset(
    {
        "reply",
        "response",
        "message",
        "assistant_message",
        "proposals",
        "actions",
        "action_type",
        "is_estimate",
        "missing_data",
    }
)

_PROTOCOL_JSON_MARKERS_RE = re.compile(
    r'"(?:reply|proposals|action_type|is_estimate|missing_data|create_missing_courses|apply_immediately|replace_future_planned)"\s*:',
    re.IGNORECASE,
)


def _try_load_json_any(snippet: str) -> Any | None:
    candidate = (snippet or "").strip()
    if not candidate:
        return None
    attempts = [
        candidate,
        re.sub(r",\s*([}\]])", r"\1", candidate),
    ]
    for attempt in attempts:
        try:
            return json.loads(attempt, strict=False)
        except Exception:
            continue
    return None


def _is_protocol_dict(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return bool(set(value.keys()) & _PROTOCOL_JSON_KEYS)


def _coerce_to_protocol_dict(value: Any) -> dict[str, Any] | None:
    if _is_protocol_dict(value):
        return value
    if isinstance(value, list) and value and all(
        isinstance(item, dict)
        and any(k in item for k in ("action_type", "action", "tool", "payload"))
        for item in value
    ):
        return {"proposals": value}
    return None


def _extract_candidates_from_dict(parsed: dict[str, Any]) -> list[RawProposalCandidate]:
    raw_proposals = parsed.get("proposals")
    if not isinstance(raw_proposals, list):
        raw_proposals = parsed.get("actions")
    if not isinstance(raw_proposals, list):
        if any(k in parsed for k in ("action_type", "action", "tool")):
            raw_proposals = [parsed]
        else:
            raw_proposals = []

    proposals: list[RawProposalCandidate] = []
    for item in raw_proposals:
        if not isinstance(item, dict):
            continue
        action_type = str(
            item.get("action_type")
            or item.get("action")
            or item.get("tool")
            or item.get("name")
            or ""
        ).strip()
        if not action_type:
            continue

        if isinstance(item.get("payload"), dict):
            raw_payload = dict(item["payload"])
        elif isinstance(item.get("parameters"), dict):
            raw_payload = dict(item["parameters"])
        elif isinstance(item.get("arguments"), dict):
            raw_payload = dict(item["arguments"])
        else:
            raw_payload = {
                k: v
                for k, v in item.items()
                if k
                not in (
                    "action_type",
                    "action",
                    "tool",
                    "name",
                    "title",
                    "label",
                    "explanation",
                    "description",
                    "reason",
                    "payload",
                    "parameters",
                    "arguments",
                )
            }

        cleaned_payload = {k: v for k, v in raw_payload.items() if v is not None}
        raw_title = str(item.get("title") or item.get("label") or "").strip()
        if len(raw_title) < 2:
            raw_title = "Proposition IA"
        raw_explanation = str(
            item.get("explanation") or item.get("description") or item.get("reason") or ""
        ).strip()
        if len(raw_explanation) < 2:
            raw_explanation = "Soumise à validation."

        proposals.append(
            RawProposalCandidate(
                action_type=action_type,
                title=_sanitize_ai_reply_dashes(raw_title[:180]),
                explanation=_sanitize_ai_reply_dashes(raw_explanation[:1000]),
                payload=cleaned_payload,
            )
        )
    return proposals


def _strip_residual_protocol_json(text: str) -> str:
    """Supprime tout bloc de code JSON résiduel ou objet JSON technique du texte affiché."""
    if not text:
        return ""

    def _replace_fence(match: re.Match[str]) -> str:
        inner = match.group(1) or ""
        if _PROTOCOL_JSON_MARKERS_RE.search(inner):
            return ""
        return match.group(0)

    cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)```", _replace_fence, text, flags=re.IGNORECASE)
    # Si un bloc ```json non refermé (tronqué) contenant des clés protocolaires subsiste en fin de message
    unclosed_m = re.search(r"```(?:json)?\s*([\s\S]*)$", cleaned, flags=re.IGNORECASE)
    if unclosed_m and _PROTOCOL_JSON_MARKERS_RE.search(unclosed_m.group(1)):
        cleaned = cleaned[: unclosed_m.start()]
    return cleaned.strip()


def _parse_llm_json_output(
    raw_text: str,
    context: BoundedUserContext,
    provider_name: str,
    model_name: str,
) -> ProviderResult:
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return ProviderResult(
            reply="Réponse générée.",
            proposals=[],
            is_estimate=context.is_partial_data,
            missing_data=context.missing_data,
            provider_name=provider_name,
            model_name=model_name,
        )

    parsed_dict: dict[str, Any] | None = None
    surrounding_prose = ""

    # 1. Essai direct sur la totalité (avec ou sans fence englobant)
    whole_candidate = cleaned
    if whole_candidate.startswith("```") and whole_candidate.endswith("```"):
        whole_candidate = re.sub(
            r"^```(?:json)?\s*|\s*```$", "", whole_candidate, flags=re.DOTALL | re.IGNORECASE
        ).strip()
    parsed_dict = _coerce_to_protocol_dict(_try_load_json_any(whole_candidate))

    # 2. Recherche de blocs ```json ... ``` intégrés au milieu ou à la fin d'un texte en prose
    if parsed_dict is None:
        fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
        matches = list(fence_pattern.finditer(cleaned))
        for m in reversed(matches):
            cand_dict = _coerce_to_protocol_dict(_try_load_json_any(m.group(1)))
            if cand_dict is not None:
                parsed_dict = cand_dict
                surrounding_prose = (cleaned[: m.start()] + "\n\n" + cleaned[m.end() :]).strip()
                break

    # 3. Recherche d'un objet JSON non entouré de ``` dans le texte via raw_decode(strict=False)
    if parsed_dict is None:
        decoder = json.JSONDecoder(strict=False)
        for m in re.finditer(r"[\{\[]", cleaned):
            start_idx = m.start()
            snippet = cleaned[start_idx:]
            if not _PROTOCOL_JSON_MARKERS_RE.search(snippet):
                continue
            try:
                obj, end_offset = decoder.raw_decode(snippet)
            except Exception:
                try:
                    fixed_snippet = re.sub(r",\s*([}\]])", r"\1", snippet)
                    obj, end_offset = decoder.raw_decode(fixed_snippet)
                except Exception:
                    continue
            cand_dict = _coerce_to_protocol_dict(obj)
            if cand_dict is not None:
                parsed_dict = cand_dict
                end_idx = start_idx + end_offset
                before = re.sub(r"```(?:json)?\s*$", "", cleaned[:start_idx], flags=re.IGNORECASE)
                after = re.sub(r"^\s*```", "", cleaned[end_idx:])
                surrounding_prose = (before + "\n\n" + after).strip()
                break

    # 4. Récupération de secours si le JSON est malformé ou tronqué (ex. guillemets non échappés dans "reply")
    if parsed_dict is None and _PROTOCOL_JSON_MARKERS_RE.search(cleaned):
        recovered_dict: dict[str, Any] = {}
        reply_m = re.search(
            r'"reply"\s*:\s*"([\s\S]*?)"\s*,\s*"(?:is_estimate|missing_data|proposals)"',
            cleaned,
        )
        if not reply_m:
            reply_m = re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned)
        if reply_m:
            raw_reply_val = reply_m.group(1)
            try:
                recovered_dict["reply"] = json.loads(f'"{raw_reply_val}"', strict=False)
            except Exception:
                recovered_dict["reply"] = (
                    raw_reply_val.replace("\\n", "\n").replace('\\"', '"').replace("\\t", "\t")
                )

        prop_m = re.search(r'"proposals"\s*:\s*(\[[\s\S]*\])', cleaned)
        if prop_m:
            decoder = json.JSONDecoder(strict=False)
            arr_text = prop_m.group(1)
            for candidate_arr in (arr_text, re.sub(r",\s*([}\]])", r"\1", arr_text)):
                try:
                    arr_obj, _ = decoder.raw_decode(candidate_arr)
                    if isinstance(arr_obj, list):
                        recovered_dict["proposals"] = arr_obj
                        break
                except Exception:
                    continue

        if recovered_dict:
            parsed_dict = recovered_dict
            first_json_pos = cleaned.find("```")
            if first_json_pos == -1:
                first_json_pos = cleaned.find("{")
            if first_json_pos > 0:
                surrounding_prose = cleaned[:first_json_pos].strip()

    if parsed_dict is not None:
        json_reply = str(
            parsed_dict.get("reply")
            or parsed_dict.get("response")
            or parsed_dict.get("message")
            or parsed_dict.get("assistant_message")
            or ""
        ).strip()

        proposals = _extract_candidates_from_dict(parsed_dict)

        # Si "reply" contenait lui-même un bloc JSON de propositions imbriqué
        if json_reply and _PROTOCOL_JSON_MARKERS_RE.search(json_reply):
            nested_fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", json_reply, re.IGNORECASE)
            if nested_fence:
                nested_dict = _coerce_to_protocol_dict(_try_load_json_any(nested_fence.group(1)))
                if nested_dict is not None and not proposals:
                    proposals = _extract_candidates_from_dict(nested_dict)
            json_reply = _strip_residual_protocol_json(json_reply)

        clean_surrounding = _strip_residual_protocol_json(surrounding_prose)
        if clean_surrounding and json_reply:
            if json_reply in clean_surrounding:
                combined_reply = clean_surrounding
            elif clean_surrounding in json_reply:
                combined_reply = json_reply
            else:
                combined_reply = f"{clean_surrounding}\n\n{json_reply}"
        else:
            combined_reply = json_reply or clean_surrounding or "Voici ma synthèse."

        reply = _sanitize_ai_reply_dashes(combined_reply.strip() or "Voici ma synthèse.")
        missing = parsed_dict.get("missing_data")
        missing_list = (
            [str(x) for x in missing]
            if isinstance(missing, list)
            else list(context.missing_data)
        )
        is_estimate = bool(parsed_dict.get("is_estimate", context.is_partial_data))
        return ProviderResult(
            reply=reply,
            proposals=proposals,
            is_estimate=is_estimate,
            missing_data=missing_list,
            provider_name=provider_name,
            model_name=model_name,
        )

    fallback_reply = _strip_residual_protocol_json(cleaned)
    return ProviderResult(
        reply=_sanitize_ai_reply_dashes(fallback_reply) or "Voici ma synthèse.",
        proposals=[],
        is_estimate=context.is_partial_data,
        missing_data=context.missing_data,
        provider_name=provider_name,
        model_name=model_name,
    )


RIVER_DEFAULT_BASE_URL = "https://api.river.ai/v1"
OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"
GEMINI_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def canonicalize_provider_name(provider: str | None) -> str:
    cleaned = (provider or "local").strip().lower()
    if cleaned in ("river", "river_ai", "river-ai", "riverai", "console.river.ai", "api.river.ai"):
        return "river"
    if cleaned in ("openai", "openai_compatible", "openai-compatible"):
        return "openai_compatible"
    if cleaned in ("gemini", "google"):
        return "gemini"
    return "local"


def normalize_provider_base_url(provider: str, base_url: str | None = None) -> str:
    provider_key = canonicalize_provider_name(provider)
    cleaned = (base_url or "").strip()

    if provider_key == "local":
        return ""

    if provider_key == "gemini":
        if not cleaned:
            return GEMINI_DEFAULT_BASE_URL
        if "://" not in cleaned:
            cleaned = f"https://{cleaned}"
        return cleaned.rstrip("/")

    if provider_key == "river":
        if not cleaned:
            return RIVER_DEFAULT_BASE_URL
        if "://" not in cleaned:
            cleaned = f"https://{cleaned}"
        parsed = urlparse(cleaned)
        host = (parsed.hostname or "").lower()
        path = parsed.path.rstrip("/")
        if host in ("console.river.ai", "river.ai", "www.river.ai"):
            return RIVER_DEFAULT_BASE_URL
        if host == "api.river.ai" and path in ("", "/"):
            return RIVER_DEFAULT_BASE_URL
        return cleaned.rstrip("/")

    if not cleaned:
        return OPENAI_DEFAULT_BASE_URL
    if "://" not in cleaned:
        cleaned = f"https://{cleaned}"
    return cleaned.rstrip("/")


def _validate_outbound_base_url(
    url: str,
    *,
    settings: Settings | None = None,
    verify_dns: bool = True,
) -> str:
    return validate_outbound_url(
        url,
        settings=settings,
        allow_http_local=True,
        verify_dns=verify_dns,
    )


def _extract_openai_message_text(raw_content: Any) -> str:
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        chunks: list[str] = []
        for part in raw_content:
            if isinstance(part, str):
                chunks.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
        return "\n".join(chunks)
    return str(raw_content or "")


def _extract_responses_output_text(payload: dict[str, Any]) -> str:
    """Extrait uniquement les segments texte finaux d'une réponse Responses API."""
    chunks: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        if item.get("role") != "assistant":
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "output_text":
                value = part.get("text")
                if isinstance(value, str) and value.strip():
                    chunks.append(value)
    return "\n".join(chunks).strip()


def _parse_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def _request_with_transient_retry(
    method: str,
    url: str,
    *,
    settings: Settings | None,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
    timeout_seconds: float = 20.0,
    max_bytes: int = MAX_AI_RESPONSE_BYTES,
    max_attempts: int = 2,
) -> httpx.Response:
    """Exécute un appel HTTP sortant vers un LLM avec nouvelle tentative bornée sur erreur transitoire (502/503/504/timeout)."""
    last_exc: Exception | None = None
    for attempt in range(1, max(1, max_attempts) + 1):
        try:
            response = safe_http_request(
                method,
                url,
                settings=settings,
                headers=headers,
                json_body=json_body,
                timeout_seconds=timeout_seconds,
                max_bytes=max_bytes,
            )
            if getattr(response, "status_code", 200) in (502, 503, 504) and attempt < max_attempts:
                time.sleep(0.15 * attempt)
                continue
            response.raise_for_status()
            return response
        except httpx.TimeoutException as exc:
            last_exc = exc
            if attempt < max_attempts:
                time.sleep(0.15 * attempt)
                continue
            raise AppError(
                504,
                "AI_PROVIDER_TIMEOUT",
                "Le délai d'attente du fournisseur IA est dépassé. Réessayez.",
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else 502
            if status_code in (502, 503, 504) and attempt < max_attempts:
                last_exc = exc
                time.sleep(0.15 * attempt)
                continue
            raise
        except httpx.TransportError as exc:
            last_exc = exc
            if attempt < max_attempts:
                time.sleep(0.15 * attempt)
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise AppError(502, "AI_PROVIDER_ERROR", "Le fournisseur IA externe est temporairement indisponible.")


class OpenAICompatibleAIProvider:
    """Adaptateur HTTP pour fournisseur compatible OpenAI (clé conservée côté serveur, AI-04)."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        base_url: str = OPENAI_DEFAULT_BASE_URL,
        timeout_seconds: float = 20.0,
        provider_name: str = "openai_compatible",
        settings: Settings | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._provider_name = canonicalize_provider_name(provider_name)
        normalized_url = normalize_provider_base_url(self._provider_name, base_url)
        default_model = (
            "gpt-6.2-sol"
            if normalized_url.rstrip("/") == OPENAI_DEFAULT_BASE_URL.rstrip("/")
            else "gpt-4o-mini"
        )
        self._model_name = validate_model_identifier(
            (model_name or default_model).strip() or default_model
        )
        self._settings = settings
        self._base_url = _validate_outbound_base_url(
            normalized_url, settings=settings, verify_dns=False
        )
        self._timeout = timeout_seconds

    def generate_response(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        context: BoundedUserContext,
        prompt_manager: PromptManager,
    ) -> ProviderResult:
        system_prompt = prompt_manager.build_system_prompt(context)
        messages = [
            {"role": "system", "content": system_prompt},
            *history[-12:],
            {"role": "user", "content": user_message},
        ]
        try:
            use_responses_api = (
                self._base_url.rstrip("/") == OPENAI_DEFAULT_BASE_URL.rstrip("/")
                and self._model_name.startswith("gpt-6")
            )
            if use_responses_api:
                request_url = f"{self._base_url}/responses"
                request_body = {
                    "model": self._model_name,
                    "input": messages,
                    "reasoning": {"effort": "medium"},
                    "store": False,
                    "max_output_tokens": 8000,
                }
            else:
                request_url = f"{self._base_url}/chat/completions"
                request_body = {
                    "model": self._model_name,
                    "messages": messages,
                    "temperature": 0.2,
                }
            response = _request_with_transient_retry(
                "POST",
                request_url,
                settings=self._settings,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json_body=request_body,
                timeout_seconds=max(self._timeout, 45.0) if use_responses_api else self._timeout,
                max_bytes=MAX_AI_RESPONSE_BYTES,
            )
            data = response.json()
            if not isinstance(data, dict):
                raise AppError(502, "AI_PROVIDER_EMPTY_RESPONSE", "Le fournisseur IA a retourné une réponse invalide.")
            if use_responses_api:
                content = _extract_responses_output_text(data)
            else:
                choices = data.get("choices")
                if not isinstance(choices, list) or not choices:
                    raise AppError(
                        502,
                        "AI_PROVIDER_EMPTY_RESPONSE",
                        "Le fournisseur IA a retourné une réponse vide.",
                    )
                raw_content = (choices[0].get("message") or {}).get("content")
                content = _extract_openai_message_text(raw_content).strip()
            if not content:
                raise AppError(
                    502,
                    "AI_PROVIDER_EMPTY_RESPONSE",
                    "Le fournisseur IA a retourné un contenu vide.",
                )
            return _parse_llm_json_output(
                content, context, self._provider_name, self._model_name
            )
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else 502
            if status_code in (401, 403):
                raise AppError(
                    401,
                    "AI_INVALID_API_KEY",
                    "Clé API refusée par le fournisseur IA. Vérifiez votre clé dans Paramètres.",
                ) from exc
            if status_code == 429:
                raise AppError(
                    429,
                    "AI_PROVIDER_RATE_LIMITED",
                    "Le fournisseur IA limite temporairement les requêtes. Réessayez dans un instant.",
                ) from exc
            raise AppError(
                502,
                "AI_PROVIDER_ERROR",
                "Le fournisseur IA externe est temporairement indisponible.",
            ) from exc
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                502,
                "AI_PROVIDER_ERROR",
                "Le fournisseur IA externe est temporairement indisponible.",
            ) from exc


class RiverAIProvider(OpenAICompatibleAIProvider):
    """Adaptateur HTTP dédié à River AI (console.river.ai / api.river.ai/v1)."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        base_url: str = RIVER_DEFAULT_BASE_URL,
        timeout_seconds: float = 20.0,
        settings: Settings | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model_name=model_name or "gpt-4o-mini",
            base_url=normalize_provider_base_url("river", base_url),
            timeout_seconds=timeout_seconds,
            provider_name="river",
            settings=settings,
        )


class GeminiAIProvider:
    """Adaptateur HTTP pour Google Gemini REST API (clé conservée côté serveur, AI-04)."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        base_url: str = GEMINI_DEFAULT_BASE_URL,
        timeout_seconds: float = 20.0,
        settings: Settings | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_name = validate_model_identifier(
            (model_name or "gemini-2.5-flash").strip() or "gemini-2.5-flash"
        )
        normalized_url = normalize_provider_base_url("gemini", base_url)
        self._settings = settings
        self._base_url = _validate_outbound_base_url(
            normalized_url, settings=settings, verify_dns=False
        )
        self._timeout = timeout_seconds

    def generate_response(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        context: BoundedUserContext,
        prompt_manager: PromptManager,
    ) -> ProviderResult:
        system_prompt = prompt_manager.build_system_prompt(context)
        url = (
            f"{self._base_url}/models/"
            f"{self._model_name}:generateContent"
        )
        contents: list[dict[str, Any]] = []
        for msg in history[-12:]:
            msg_text = str(msg.get("content") or "").strip()
            if not msg_text:
                continue
            raw_role = str(msg.get("role") or "user").strip().lower()
            gemini_role = "model" if raw_role in ("assistant", "model") else "user"
            contents.append({"role": gemini_role, "parts": [{"text": msg_text}]})
        contents.append({"role": "user", "parts": [{"text": user_message}]})

        try:
            response = _request_with_transient_retry(
                "POST",
                url,
                settings=self._settings,
                headers={
                    "x-goog-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json_body={
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json",
                    },
                },
                timeout_seconds=self._timeout,
                max_bytes=MAX_AI_RESPONSE_BYTES,
            )
            data = response.json()
            candidates = data.get("candidates") if isinstance(data, dict) else None
            if not isinstance(candidates, list) or not candidates:
                block_reason = (
                    (data.get("promptFeedback") or {}).get("blockReason")
                    if isinstance(data, dict)
                    else None
                )
                if block_reason:
                    raise AppError(
                        502,
                        "AI_PROVIDER_SAFETY_BLOCKED",
                        f"La requête a été filtrée par les règles de sécurité Gemini ({block_reason}).",
                    )
                raise AppError(
                    502,
                    "AI_PROVIDER_EMPTY_RESPONSE",
                    "Le fournisseur Gemini n'a retourné aucun candidat de réponse.",
                )
            first_cand = candidates[0] if isinstance(candidates[0], dict) else {}
            parts = ((first_cand.get("content") or {}).get("parts")) or []
            content = str(parts[0].get("text") or "").strip() if parts and isinstance(parts[0], dict) else ""
            if not content:
                finish_reason = first_cand.get("finishReason")
                if finish_reason == "SAFETY":
                    raise AppError(
                        502,
                        "AI_PROVIDER_SAFETY_BLOCKED",
                        "La réponse Gemini a été bloquée par un filtre de sécurité.",
                    )
                raise AppError(
                    502,
                    "AI_PROVIDER_EMPTY_RESPONSE",
                    "Le fournisseur Gemini a retourné un contenu vide.",
                )
            return _parse_llm_json_output(content, context, "gemini", self._model_name)
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else 502
            if status_code in (401, 403):
                raise AppError(
                    401,
                    "AI_INVALID_API_KEY",
                    "Clé API Gemini refusée. Vérifiez votre clé dans Paramètres.",
                ) from exc
            if status_code == 429:
                raise AppError(
                    429,
                    "AI_PROVIDER_RATE_LIMITED",
                    "Le fournisseur Gemini limite temporairement les requêtes.",
                ) from exc
            raise AppError(
                502,
                "AI_PROVIDER_ERROR",
                "Le fournisseur Gemini est temporairement indisponible.",
            ) from exc
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                502,
                "AI_PROVIDER_ERROR",
                "Le fournisseur Gemini est temporairement indisponible.",
            ) from exc


def fetch_provider_models(
    *,
    provider: str,
    api_key: str,
    base_url: str | None = None,
    timeout_seconds: float = 15.0,
    settings: Settings | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Interroge le fournisseur IA configuré pour récupérer la liste des modèles disponibles."""
    provider_key = canonicalize_provider_name(provider)

    if provider_key == "local":
        return (
            "",
            [
                {
                    "id": "local-coach-v1",
                    "label": "Moteur local déterministe v1 (règles métier hors-ligne, sans LLM)",
                    "owned_by": "study-os",
                    "context_window": None,
                }
            ],
        )

    cleaned_key = (api_key or "").strip()
    if not cleaned_key:
        raise AppError(
            400,
            "AI_API_KEY_REQUIRED",
            "Veuillez saisir une clé API pour récupérer les modèles disponibles.",
        )

    resolved_url = _validate_outbound_base_url(
        normalize_provider_base_url(provider_key, base_url),
        settings=settings,
        verify_dns=True,
    )

    try:
        headers = (
            {
                "x-goog-api-key": cleaned_key,
                "Accept": "application/json",
            }
            if provider_key == "gemini"
            else {
                "Authorization": f"Bearer {cleaned_key}",
                "Accept": "application/json",
            }
        )
        response = safe_http_request(
            "GET",
            f"{resolved_url}/models",
            settings=settings,
            headers=headers,
            timeout_seconds=timeout_seconds,
            max_bytes=MAX_AI_RESPONSE_BYTES,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        if status_code in (401, 403):
            msg = (
                "Clé API refusée par River AI (console.river.ai). Vérifiez votre clé API."
                if provider_key == "river"
                else "Clé API refusée par le fournisseur IA. Vérifiez votre clé API."
            )
            raise AppError(401, "AI_INVALID_API_KEY", msg) from exc
        if status_code == 429:
            raise AppError(
                429,
                "AI_PROVIDER_RATE_LIMITED",
                "Limite de requêtes atteinte auprès du fournisseur IA. Réessayez dans un instant.",
            ) from exc
        raise AppError(
            502,
            "AI_PROVIDER_ERROR",
            "Le fournisseur IA n'a pas retourné une liste de modèles exploitable.",
        ) from exc
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            502,
            "AI_PROVIDER_ERROR",
            "Impossible de contacter le fournisseur IA pour récupérer les modèles.",
        ) from exc

    models_by_id: dict[str, dict[str, Any]] = {}

    if provider_key == "gemini":
        raw_items = payload.get("models") if isinstance(payload, dict) else []
        if isinstance(raw_items, list):
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                methods = item.get("supportedGenerationMethods")
                if isinstance(methods, list) and "generateContent" not in methods:
                    continue
                raw_name = str(item.get("name") or "").strip()
                if not raw_name:
                    continue
                model_id = raw_name.removeprefix("models/").strip()
                if not model_id or model_id in models_by_id:
                    continue
                label = str(item.get("displayName") or model_id).strip() or model_id
                models_by_id[model_id] = {
                    "id": model_id,
                    "label": label,
                    "owned_by": "google",
                    "context_window": _parse_int_or_none(item.get("inputTokenLimit")),
                }
    else:
        raw_items: Any = []
        if isinstance(payload, list):
            raw_items = payload
        elif isinstance(payload, dict):
            if isinstance(payload.get("data"), list):
                raw_items = payload["data"]
            elif isinstance(payload.get("models"), list):
                raw_items = payload["models"]

        if isinstance(raw_items, list):
            for item in raw_items:
                if isinstance(item, str):
                    model_id = item.strip()
                    if not model_id or model_id in models_by_id:
                        continue
                    models_by_id[model_id] = {
                        "id": model_id,
                        "label": model_id,
                        "owned_by": "river" if provider_key == "river" else None,
                        "context_window": None,
                    }
                    continue
                if not isinstance(item, dict):
                    continue
                model_id = str(item.get("id") or item.get("name") or "").strip()
                if not model_id or model_id in models_by_id:
                    continue
                label = (
                    str(item.get("display_name") or item.get("label") or model_id).strip()
                    or model_id
                )
                owned_by_raw = item.get("owned_by")
                owned_by = str(owned_by_raw).strip() if owned_by_raw else None
                context_window = (
                    _parse_int_or_none(item.get("context_window"))
                    or _parse_int_or_none(item.get("context_length"))
                    or _parse_int_or_none(item.get("max_context_length"))
                    or _parse_int_or_none(item.get("input_token_limit"))
                )
                models_by_id[model_id] = {
                    "id": model_id,
                    "label": label,
                    "owned_by": owned_by,
                    "context_window": context_window,
                }

    sorted_models = sorted(models_by_id.values(), key=lambda m: (m["id"].lower(), m["id"]))
    return resolved_url, sorted_models


def build_ai_provider_from_config(
    *,
    provider: str | None,
    api_key: str | None,
    model_name: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float = 20.0,
    settings: Settings | None = None,
    require_api_key_for_remote: bool = False,
) -> AIProvider:
    provider_key = canonicalize_provider_name(provider)
    cleaned_key = (api_key or "").strip()

    if provider_key in ("river", "openai_compatible", "gemini") and not cleaned_key:
        if require_api_key_for_remote:
            raise AppError(
                400,
                "AI_API_KEY_REQUIRED",
                f"Aucune clé API configurée pour le fournisseur « {provider_key} ». "
                "Enregistrez une clé API dans Paramètres ou sélectionnez explicitement le moteur Local déterministe.",
            )

    if provider_key == "river" and cleaned_key:
        return RiverAIProvider(
            api_key=cleaned_key,
            model_name=(model_name or "").strip() or "gpt-4o-mini",
            base_url=normalize_provider_base_url("river", base_url),
            timeout_seconds=timeout_seconds,
            settings=settings,
        )
    if provider_key == "openai_compatible" and cleaned_key:
        resolved_base_url = normalize_provider_base_url("openai_compatible", base_url)
        default_model = (
            "gpt-6.2-sol"
            if resolved_base_url.rstrip("/") == OPENAI_DEFAULT_BASE_URL.rstrip("/")
            else "gpt-4o-mini"
        )
        return OpenAICompatibleAIProvider(
            api_key=cleaned_key,
            model_name=(model_name or "").strip() or default_model,
            base_url=resolved_base_url,
            timeout_seconds=timeout_seconds,
            provider_name="openai_compatible",
            settings=settings,
        )
    if provider_key == "gemini" and cleaned_key:
        return GeminiAIProvider(
            api_key=cleaned_key,
            model_name=(model_name or "").strip() or "gemini-2.5-flash",
            base_url=normalize_provider_base_url("gemini", base_url),
            timeout_seconds=timeout_seconds,
            settings=settings,
        )
    return LocalRuleBasedAIProvider(model_name=(model_name or "").strip() or "local-coach-v1")


def build_ai_provider(settings: Settings) -> AIProvider:
    return build_ai_provider_from_config(
        provider=settings.ai_provider,
        api_key=settings.ai_api_key,
        model_name=settings.ai_model,
        base_url=settings.ai_base_url,
        timeout_seconds=settings.ai_timeout_seconds,
        settings=settings,
    )
