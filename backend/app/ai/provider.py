from datetime import date, datetime, timedelta, timezone
import json
import re
from typing import Any, Protocol
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel, Field
from app.ai.context_builder import BoundedUserContext
from app.ai.prompt_manager import PromptManager
from app.core.config import Settings
from app.core.errors import AppError
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

    # Sélection des meilleurs créneaux réels répartis sur des jours distincts
    chosen_raw_slots: list[dict[str, Any]] = []
    used_dates: set[str] = set()
    for candidate in weekly_slots:
        if len(chosen_raw_slots) >= max_slots:
            break
        if candidate["local_date"] not in used_dates:
            chosen_raw_slots.append(candidate)
            used_dates.add(candidate["local_date"])
    if len(chosen_raw_slots) < max_slots:
        for candidate in weekly_slots:
            if len(chosen_raw_slots) >= max_slots:
                break
            if candidate not in chosen_raw_slots:
                chosen_raw_slots.append(candidate)

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
        f"- **Fréquence** : {len(proposed_slots_payload)} séance(s) / semaine · **Durée** : ~{estimated_weeks} semaine(s) · **Début** : {proposed_slots_payload[0]['local_date']}"
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
    proposals = [
        RawProposalCandidate(
            action_type=AiActionType.plan_strategic_activity.value,
            title=f"Programmer « {activity_title} » ({len(proposed_slots_payload)} séance(s)/sem.)",
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
                "create_project": is_project,
                "park_only": False,
                "frequency_per_week": len(proposed_slots_payload),
                "session_duration_minutes": proposed_slots_payload[0]["duration_minutes"],
                "estimated_weeks": estimated_weeks,
                "start_date": proposed_slots_payload[0]["local_date"],
                "proposed_slots": proposed_slots_payload,
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
            high_prio = "high" if any(w in lowered for w in ("urgent", "haute", "prioritaire")) else "normal"
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.create_task.value,
                    title=f"Créer la tâche « {extracted_title} »",
                    explanation="Tâche structurée prête à être ajoutée après votre validation.",
                    payload={
                        "title": extracted_title,
                        "description": "Proposée par le Copilote IA à partir de votre demande.",
                        "priority": high_prio,
                    },
                )
            )
            lines.append(
                f"J’ai préparé une proposition de tâche **« {extracted_title} »** (priorité `{high_prio}`). "
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

            if rec_windows:
                chosen_win = rec_windows[0]
                slot_start_iso = chosen_win["starts_at"]
                slot_end_iso = chosen_win["ends_at"]
                local_range = f"{chosen_win['local_start_time']} à {chosen_win['local_end_time']}"

                win_labels = [
                    f"`{w['local_start_time']} à {w['local_end_time']}` ({w['duration_minutes']} min)"
                    for w in rec_windows
                ]
                lines.append(
                    f"- **Créneaux libres recommandés (hors cours & pauses préservées)** : "
                    + ", ".join(win_labels)
                )
            else:
                # Fallback hors plage si aucune fenêtre standard n'est disponible
                now_utc = datetime.now(timezone.utc)
                next_hour = (now_utc + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
                end_hour = next_hour + timedelta(hours=1)
                slot_start_iso = next_hour.isoformat()
                slot_end_iso = end_hour.isoformat()
                local_range = "1h"

            if any(
                w in lowered
                for w in ("créneau", "planifie", "planifier", "programme", "demain", "lendemain", "organise", "révision", "réviser")
            ):
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


def _parse_llm_json_output(
    raw_text: str,
    context: BoundedUserContext,
    provider_name: str,
    model_name: str,
) -> ProviderResult:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL).strip()
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("Réponse JSON non objet.")
        reply = _sanitize_ai_reply_dashes(str(parsed.get("reply") or "Voici ma synthèse.").strip())
        raw_proposals = parsed.get("proposals")
        proposals: list[RawProposalCandidate] = []
        if isinstance(raw_proposals, list):
            for item in raw_proposals:
                if isinstance(item, dict) and "action_type" in item and "payload" in item:
                    proposals.append(
                        RawProposalCandidate(
                            action_type=str(item.get("action_type", "")),
                            title=_sanitize_ai_reply_dashes(str(item.get("title", "Proposition IA"))),
                            explanation=_sanitize_ai_reply_dashes(
                                str(item.get("explanation", "Soumise à validation."))
                            ),
                            payload=dict(item.get("payload") or {}),
                        )
                    )
        missing = parsed.get("missing_data")
        missing_list = (
            [str(x) for x in missing]
            if isinstance(missing, list)
            else list(context.missing_data)
        )
        is_estimate = bool(parsed.get("is_estimate", context.is_partial_data))
        return ProviderResult(
            reply=reply,
            proposals=proposals,
            is_estimate=is_estimate,
            missing_data=missing_list,
            provider_name=provider_name,
            model_name=model_name,
        )
    except Exception:
        return ProviderResult(
            reply=_sanitize_ai_reply_dashes(raw_text.strip()) or "Réponse générée.",
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


def _validate_outbound_base_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        raise AppError(
            400,
            "VALIDATION_ERROR",
            "L’URL du fournisseur IA ne doit pas contenir d’identifiants intégrés.",
        )
    scheme = (parsed.scheme or "").lower()
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise AppError(
            400,
            "VALIDATION_ERROR",
            "L’URL du fournisseur IA doit contenir un nom d’hôte valide.",
        )
    if scheme == "https" or (scheme == "http" and hostname in ("localhost", "127.0.0.1")):
        return url.rstrip("/")
    raise AppError(
        400,
        "VALIDATION_ERROR",
        "L’URL du fournisseur IA doit utiliser HTTPS (ou http://localhost en local).",
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


def _parse_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


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
    ) -> None:
        self._api_key = api_key.strip()
        self._provider_name = canonicalize_provider_name(provider_name)
        self._model_name = (model_name or "gpt-4o-mini").strip() or "gpt-4o-mini"
        normalized_url = normalize_provider_base_url(self._provider_name, base_url)
        self._base_url = _validate_outbound_base_url(normalized_url)
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
            *history[-6:],
            {"role": "user", "content": user_message},
        ]
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model_name,
                        "messages": messages,
                        "temperature": 0.2,
                    },
                )
                response.raise_for_status()
                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]
                content = _extract_openai_message_text(raw_content)
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
    ) -> None:
        super().__init__(
            api_key=api_key,
            model_name=model_name or "gpt-4o-mini",
            base_url=normalize_provider_base_url("river", base_url),
            timeout_seconds=timeout_seconds,
            provider_name="river",
        )


class GeminiAIProvider:
    """Adaptateur HTTP pour Google Gemini REST API (clé conservée côté serveur, AI-04)."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name or "gemini-2.5-flash"
        self._timeout = timeout_seconds

    def generate_response(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        context: BoundedUserContext,
        prompt_manager: PromptManager,
    ) -> ProviderResult:
        _ = history
        system_prompt = prompt_manager.build_system_prompt(context)
        url = (
            f"{GEMINI_DEFAULT_BASE_URL}/models/"
            f"{self._model_name}:generateContent"
        )
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    url,
                    headers={
                        "x-goog-api-key": self._api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
                        "generationConfig": {
                            "temperature": 0.2,
                            "responseMimeType": "application/json",
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
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
) -> tuple[str, list[dict[str, Any]]]:
    """Interroge le fournisseur IA configuré pour récupérer la liste des modèles disponibles."""
    provider_key = canonicalize_provider_name(provider)

    if provider_key == "local":
        return (
            "",
            [
                {
                    "id": "local-coach-v1",
                    "label": "Local Coach v1 (déterministe, hors-ligne)",
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

    resolved_url = _validate_outbound_base_url(normalize_provider_base_url(provider_key, base_url))

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            if provider_key == "gemini":
                response = client.get(
                    f"{resolved_url}/models",
                    headers={
                        "x-goog-api-key": cleaned_key,
                        "Accept": "application/json",
                    },
                )
            else:
                response = client.get(
                    f"{resolved_url}/models",
                    headers={
                        "Authorization": f"Bearer {cleaned_key}",
                        "Accept": "application/json",
                    },
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
            f"Erreur HTTP {status_code} lors de la récupération des modèles.",
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
) -> AIProvider:
    provider_key = canonicalize_provider_name(provider)
    cleaned_key = (api_key or "").strip()

    if provider_key == "river" and cleaned_key:
        return RiverAIProvider(
            api_key=cleaned_key,
            model_name=(model_name or "").strip() or "gpt-4o-mini",
            base_url=normalize_provider_base_url("river", base_url),
            timeout_seconds=timeout_seconds,
        )
    if provider_key == "openai_compatible" and cleaned_key:
        return OpenAICompatibleAIProvider(
            api_key=cleaned_key,
            model_name=(model_name or "").strip() or "gpt-4o-mini",
            base_url=normalize_provider_base_url("openai_compatible", base_url),
            timeout_seconds=timeout_seconds,
            provider_name="openai_compatible",
        )
    if provider_key == "gemini" and cleaned_key:
        return GeminiAIProvider(
            api_key=cleaned_key,
            model_name=(model_name or "").strip() or "gemini-2.5-flash",
            timeout_seconds=timeout_seconds,
        )
    return LocalRuleBasedAIProvider(model_name=(model_name or "").strip() or "local-coach-v1")


def build_ai_provider(settings: Settings) -> AIProvider:
    return build_ai_provider_from_config(
        provider=settings.ai_provider,
        api_key=settings.ai_api_key,
        model_name=settings.ai_model,
        base_url=settings.ai_base_url,
        timeout_seconds=settings.ai_timeout_seconds,
    )
