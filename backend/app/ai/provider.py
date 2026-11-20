from datetime import datetime, timedelta, timezone
import json
import re
from typing import Protocol
import httpx
from pydantic import BaseModel, Field
from app.ai.context_builder import BoundedUserContext
from app.ai.prompt_manager import PromptManager
from app.core.config import Settings
from app.core.errors import AppError
from app.schemas.ai import RawProposalCandidate
from app.schemas.common import AiActionType


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
        _ = (history, prompt_manager)
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

        # 3. Intention : proposer un créneau dans le planning
        if any(w in lowered for w in ("créneau", "planifie", "planifier")):
            now_utc = datetime.now(timezone.utc)
            next_hour = (now_utc + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
            end_hour = next_hour + timedelta(hours=1)
            slot_title = _extract_quoted_or_after_colon(
                user_message,
                f"Bloc focus : {priority_title or 'Étude approfondie'}",
            )
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.create_schedule_event.value,
                    title=f"Planifier « {slot_title} » (1h)",
                    explanation="Créneau d’étude proposé avec vérification automatique des conflits.",
                    payload={
                        "title": slot_title,
                        "type": "learning",
                        "starts_at": next_hour.isoformat(),
                        "ends_at": end_hour.isoformat(),
                        "notes": "Créneau proposé par le Copilote IA.",
                    },
                )
            )
            lines.append(
                f"Je vous propose un créneau d’une heure **« {slot_title} »**. "
                "Vérifiez l’horaire proposé avant de confirmer."
            )

        # 4. Intention : proposer une preuve ou un niveau de compétence
        if any(w in lowered for w in ("preuve", "justifier")) and skills:
            target_skill = skills[0]
            ev_desc = _extract_quoted_or_after_colon(
                user_message,
                f"Exercice pratique validé sur {target_skill['name']}",
            )
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.add_skill_evidence.value,
                    title=f"Ajouter une preuve sur « {target_skill['name']} »",
                    explanation="Enregistre une preuve vérifiable associée à votre compétence.",
                    payload={
                        "skill_id": target_skill["id"],
                        "type": "exercise",
                        "description": ev_desc,
                        "result": "Validé en séance",
                    },
                )
            )
            lines.append(
                f"J’ai préparé une proposition de preuve pour la compétence **{target_skill['name']}**."
            )
        elif any(w in lowered for w in ("niveau", "évaluer compétence", "monter compétence")) and skills:
            target_skill = skills[0]
            next_lvl = min(5, int(target_skill["current_level"]) + 1)
            proposals.append(
                RawProposalCandidate(
                    action_type=AiActionType.update_skill_level.value,
                    title=f"Passer « {target_skill['name']} » au niveau {next_lvl}/5",
                    explanation="Mise à jour explicite du niveau de maîtrise (SKILL-01).",
                    payload={
                        "skill_id": target_skill["id"],
                        "current_level": next_lvl,
                        "target_level": target_skill.get("target_level"),
                    },
                )
            )
            lines.append(
                f"Je vous propose d’évaluer **{target_skill['name']}** au niveau **{next_lvl}/5**."
            )

        # 5. Réponse pédagogique ou synthèse quotidienne par défaut
        if not lines:
            if any(w in lowered for w in ("exercice", "quiz", "entraîne", "explique")):
                topic = (
                    learning_paths[0]["title"]
                    if learning_paths
                    else (skills[0]["name"] if skills else (priority_title or "vos études"))
                )
                lines.append(f"### Mini-exercice ciblé — {topic}")
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
                        "- **Priorité principale** : aucune priorité active définie — choisissez un objectif unique sur le Tableau de bord."
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
        reply = str(parsed.get("reply") or "Voici ma synthèse.").strip()
        raw_proposals = parsed.get("proposals")
        proposals: list[RawProposalCandidate] = []
        if isinstance(raw_proposals, list):
            for item in raw_proposals:
                if isinstance(item, dict) and "action_type" in item and "payload" in item:
                    proposals.append(
                        RawProposalCandidate(
                            action_type=str(item.get("action_type", "")),
                            title=str(item.get("title", "Proposition IA")),
                            explanation=str(item.get("explanation", "Soumise à validation.")),
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
            reply=raw_text.strip() or "Réponse générée.",
            proposals=[],
            is_estimate=context.is_partial_data,
            missing_data=context.missing_data,
            provider_name=provider_name,
            model_name=model_name,
        )


class OpenAICompatibleAIProvider:
    """Adaptateur HTTP pour fournisseur compatible OpenAI (clé conservée côté serveur, AI-04)."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 20.0,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name or "gpt-4o-mini"
        self._base_url = base_url.rstrip("/")
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
                content = data["choices"][0]["message"]["content"]
                return _parse_llm_json_output(
                    content, context, "openai_compatible", self._model_name
                )
        except Exception as exc:
            raise AppError(
                502,
                "AI_PROVIDER_ERROR",
                "Le fournisseur IA externe est temporairement indisponible.",
            ) from exc


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
            f"https://generativelanguage.googleapis.com/v1beta/models/"
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
        except Exception as exc:
            raise AppError(
                502,
                "AI_PROVIDER_ERROR",
                "Le fournisseur Gemini est temporairement indisponible.",
            ) from exc


def build_ai_provider(settings: Settings) -> AIProvider:
    provider_key = (settings.ai_provider or "local").strip().lower()
    api_key = (settings.ai_api_key or "").strip()

    if provider_key in ("openai", "openai_compatible") and api_key:
        return OpenAICompatibleAIProvider(
            api_key=api_key,
            model_name=settings.ai_model or "gpt-4o-mini",
            base_url=settings.ai_base_url or "https://api.openai.com/v1",
            timeout_seconds=settings.ai_timeout_seconds,
        )
    if provider_key == "gemini" and api_key:
        return GeminiAIProvider(
            api_key=api_key,
            model_name=settings.ai_model or "gemini-2.5-flash",
            timeout_seconds=settings.ai_timeout_seconds,
        )
    return LocalRuleBasedAIProvider(model_name=settings.ai_model or "local-coach-v1")
