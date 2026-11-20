from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from app.core.config import Settings
from app.core.crypto import (
    decrypt_api_key,
    encrypt_api_key,
    extract_api_key_last4,
    is_encrypted_api_key,
)
from app.core.errors import AppError
from app.repositories.ai_sql import (
    InMemoryAiProviderConfigRepository,
    SqlAiProviderConfigRepository,
    UserAiProviderConfigRecord,
)
from app.repositories.memory import ProfileRecord, ProfileRepository, TaskRepository
from app.schemas.common import ProjectStatus
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.tasks_service import is_active_task_status

INTERNAL_AI_CONFIG_KEY = "_ai_provider_config"


def _sanitize_public_preferences(preferences: dict[str, Any] | None) -> dict[str, Any]:
    """Supprime les clés internes (préfixées par '_') avant exposition via /profile."""
    return {k: v for k, v in (preferences or {}).items() if not str(k).startswith("_")}


def _to_public_profile_response(record: ProfileRecord) -> ProfileResponse:
    data = record.model_dump()
    data["preferences"] = _sanitize_public_preferences(record.preferences)
    return ProfileResponse.model_validate(data)


class ProfileService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        task_repo: TaskRepository,
        default_timezone: str = "Africa/Dakar",
        project_repo: Any | None = None,
        ai_config_repo: SqlAiProviderConfigRepository | InMemoryAiProviderConfigRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._profile_repo = profile_repo
        self._task_repo = task_repo
        self._default_timezone = default_timezone
        self._project_repo = project_repo
        self._ai_config_repo = ai_config_repo
        self._settings = settings

    def get_or_create_record(self, user_id: UUID) -> ProfileRecord:
        existing = self._profile_repo.get(user_id)
        if existing is not None:
            return existing

        now = datetime.now(timezone.utc)
        created = ProfileRecord(
            id=user_id,
            display_name="Utilisateur",
            timezone=self._default_timezone,
            created_at=now,
            updated_at=now,
        )
        return self._profile_repo.save(created)

    def get_profile(self, user_id: UUID) -> ProfileResponse:
        record = self.get_or_create_record(user_id)
        return _to_public_profile_response(record)

    def get_ai_provider_config(self, user_id: UUID) -> dict[str, Any] | None:
        if self._ai_config_repo is not None:
            stored = self._ai_config_repo.get(user_id)
            if stored is not None:
                decrypted_key = ""
                if stored.encrypted_api_key:
                    if self._settings is None:
                        raise AppError(
                            503,
                            "AI_ENCRYPTION_NOT_CONFIGURED",
                            "Configuration de déchiffrement IA indisponible.",
                        )
                    decrypted_key = decrypt_api_key(
                        stored.encrypted_api_key,
                        user_id,
                        self._settings,
                    )
                return {
                    "provider": stored.provider,
                    "base_url": stored.base_url,
                    "model": stored.model,
                    "api_key": decrypted_key,
                    "has_api_key": bool(stored.encrypted_api_key),
                    "api_key_last4": stored.api_key_last4,
                }

        # Repli / migration paresseuse d'éventuelles anciennes clés présentes dans profiles.preferences
        record = self.get_or_create_record(user_id)
        legacy = (record.preferences or {}).get(INTERNAL_AI_CONFIG_KEY)
        if isinstance(legacy, dict):
            raw_key = str(legacy.get("api_key") or "").strip()
            resolved_key = ""
            if raw_key:
                if self._settings is None or not (self._settings.ai_key_encryption_key or "").strip():
                    raise AppError(
                        503,
                        "AI_ENCRYPTION_NOT_CONFIGURED",
                        "Une clé IA héritée nécessite AI_KEY_ENCRYPTION_KEY pour être chiffrée et utilisée.",
                    )
                if is_encrypted_api_key(raw_key):
                    resolved_key = decrypt_api_key(raw_key, user_id, self._settings)
                else:
                    resolved_key = raw_key
                    # Migrer immédiatement vers la table dédiée chiffrée et purger profiles.preferences
                    if self._ai_config_repo is not None:
                        self.save_ai_provider_config(
                            user_id,
                            {
                                "provider": str(legacy.get("provider") or "local"),
                                "base_url": str(legacy.get("base_url") or ""),
                                "model": str(legacy.get("model") or ""),
                                "api_key": resolved_key,
                            },
                        )
            return {
                "provider": str(legacy.get("provider") or "local"),
                "base_url": str(legacy.get("base_url") or ""),
                "model": str(legacy.get("model") or ""),
                "api_key": resolved_key,
                "has_api_key": bool(resolved_key),
                "api_key_last4": extract_api_key_last4(resolved_key),
            }
        return None

    def save_ai_provider_config(self, user_id: UUID, config: dict[str, Any]) -> dict[str, Any]:
        record = self.get_or_create_record(user_id)
        plain_key = str(config.get("api_key") or "").strip()

        if plain_key:
            if self._settings is None:
                raise AppError(
                    503,
                    "AI_ENCRYPTION_NOT_CONFIGURED",
                    "Le stockage chiffré des clés API IA n’est pas configuré.",
                )
            encrypted_key: str | None = encrypt_api_key(plain_key, user_id, self._settings)
            last4 = extract_api_key_last4(plain_key)
        else:
            encrypted_key = None
            last4 = None

        if self._ai_config_repo is None:
            raise AppError(
                503,
                "AI_ENCRYPTION_NOT_CONFIGURED",
                "Le dépôt sécurisé des clés IA est indisponible.",
            )

        now = datetime.now(timezone.utc)
        existing = self._ai_config_repo.get(user_id)
        cfg_record = UserAiProviderConfigRecord(
            user_id=user_id,
            provider=str(config.get("provider") or "local")[:30],
            base_url=str(config.get("base_url") or "")[:300],
            model=str(config.get("model") or "")[:160],
            encrypted_api_key=encrypted_key,
            key_version=(existing.key_version + 1) if existing else 1,
            api_key_last4=last4,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        saved_cfg = self._ai_config_repo.save(cfg_record)

        # Supprimer systématiquement toute trace héritée dans profiles.preferences
        if INTERNAL_AI_CONFIG_KEY in (record.preferences or {}):
            cleaned_prefs = {
                k: v for k, v in (record.preferences or {}).items() if k != INTERNAL_AI_CONFIG_KEY
            }
            self._profile_repo.save(
                record.model_copy(update={"preferences": cleaned_prefs, "updated_at": now})
            )

        return {
            "provider": saved_cfg.provider,
            "base_url": saved_cfg.base_url,
            "model": saved_cfg.model,
            "api_key": plain_key,
            "has_api_key": bool(saved_cfg.encrypted_api_key),
            "api_key_last4": saved_cfg.api_key_last4,
        }

    def update_profile(self, user_id: UUID, payload: ProfileUpdate) -> ProfileResponse:
        record = self.get_or_create_record(user_id)
        fields = payload.model_fields_set
        updates: dict[str, object] = {"updated_at": datetime.now(timezone.utc)}

        if "display_name" in fields and payload.display_name is not None:
            updates["display_name"] = payload.display_name

        if "timezone" in fields and payload.timezone is not None:
            updates["timezone"] = payload.timezone

        if "preferences" in fields and payload.preferences is not None:
            sanitized_client_prefs = _sanitize_public_preferences(payload.preferences)
            preserved_internal = {
                k: v
                for k, v in (record.preferences or {}).items()
                if str(k).startswith("_") and k != INTERNAL_AI_CONFIG_KEY
            }
            updates["preferences"] = {**sanitized_client_prefs, **preserved_internal}

        if "ai_instructions" in fields:
            updates["ai_instructions"] = payload.ai_instructions

        if "active_priority_project_id" in fields:
            if payload.active_priority_project_id is None:
                updates["active_priority_project_id"] = None
            else:
                project = (
                    self._project_repo.get(user_id, payload.active_priority_project_id)
                    if self._project_repo is not None
                    else None
                )
                if self._project_repo is not None and project is None:
                    raise AppError(404, "NOT_FOUND", "Projet prioritaire introuvable.")
                if project is not None and project.status in {
                    ProjectStatus.paused,
                    ProjectStatus.completed,
                    ProjectStatus.archived,
                }:
                    raise AppError(
                        409,
                        "INACTIVE_PRIORITY_TARGET",
                        "Impossible de définir un projet en pause, terminé ou archivé comme priorité principale.",
                    )
                updates["active_priority_project_id"] = payload.active_priority_project_id
                if (
                    project is not None
                    and "active_priority_title" not in fields
                    and "active_priority_task_id" not in fields
                    and record.active_priority_task_id is None
                ):
                    updates["active_priority_title"] = project.name

        if "active_priority_task_id" in fields:
            if payload.active_priority_task_id is None:
                updates["active_priority_task_id"] = None
            else:
                task = self._task_repo.get(user_id, payload.active_priority_task_id)
                if task is None:
                    raise AppError(404, "NOT_FOUND", "Tâche prioritaire introuvable.")
                if not is_active_task_status(task.status):
                    raise AppError(
                        409,
                        "INACTIVE_PRIORITY_TARGET",
                        "Impossible de définir une tâche terminée, annulée ou au parking comme priorité principale.",
                    )
                updates["active_priority_task_id"] = task.id
                if "active_priority_title" not in fields:
                    updates["active_priority_title"] = task.title

        if "active_priority_title" in fields:
            updates["active_priority_title"] = payload.active_priority_title
            if payload.active_priority_title is None and "active_priority_task_id" not in fields:
                updates["active_priority_task_id"] = None

        updated = record.model_copy(update=updates)
        saved = self._profile_repo.save(updated)
        return _to_public_profile_response(saved)
