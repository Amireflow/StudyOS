from datetime import datetime, timezone
from uuid import UUID, uuid4
from app.core.errors import AppError
from app.repositories.learning_sql import (
    SkillEvidenceRecord,
    SkillRecord,
    SqlSkillRepository,
)
from app.schemas.skills import (
    SkillCreate,
    SkillEvidenceCreate,
    SkillEvidenceResponse,
    SkillEvidenceUpdate,
    SkillResponse,
    SkillUpdate,
)


class SkillService:
    def __init__(self, repo: SqlSkillRepository) -> None:
        self._repo = repo

    def list_skills(
        self,
        user_id: UUID,
        *,
        domain: str | None = None,
    ) -> list[SkillResponse]:
        records = self._repo.list_skills(user_id)
        if domain:
            normalized = domain.strip().lower()
            records = [item for item in records if item.domain.lower() == normalized]
        records.sort(key=lambda item: (item.domain.lower(), item.name.lower()))
        return [SkillResponse.model_validate(item.model_dump()) for item in records]

    def get_skill(self, user_id: UUID, skill_id: UUID) -> SkillResponse:
        record = self._repo.get_skill(user_id, skill_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        return SkillResponse.model_validate(record.model_dump())

    def create_skill(self, user_id: UUID, payload: SkillCreate) -> SkillResponse:
        now = datetime.now(timezone.utc)
        record = SkillRecord(
            id=uuid4(),
            user_id=user_id,
            name=payload.name,
            domain=payload.domain,
            description=payload.description,
            current_level=payload.current_level,
            target_level=payload.target_level,
            last_assessed_at=now if payload.current_level > 0 else None,
            created_at=now,
            updated_at=now,
        )
        saved = self._repo.save_skill(record)
        return SkillResponse.model_validate(saved.model_dump())

    def update_skill(
        self,
        user_id: UUID,
        skill_id: UUID,
        payload: SkillUpdate,
    ) -> SkillResponse:
        existing = self._repo.get_skill(user_id, skill_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")

        now = datetime.now(timezone.utc)
        fields = payload.model_fields_set
        updates: dict[str, object] = {"updated_at": now}

        if "name" in fields and payload.name is not None:
            updates["name"] = payload.name
        if "domain" in fields and payload.domain is not None:
            updates["domain"] = payload.domain
        if "description" in fields:
            updates["description"] = payload.description
        if "target_level" in fields:
            updates["target_level"] = payload.target_level

        if "current_level" in fields and payload.current_level is not None:
            updates["current_level"] = payload.current_level
            if payload.current_level == 0:
                updates["last_assessed_at"] = None
            elif (
                payload.current_level != existing.current_level
                or existing.last_assessed_at is None
            ):
                updates["last_assessed_at"] = now

        saved = self._repo.save_skill(existing.model_copy(update=updates))
        return SkillResponse.model_validate(saved.model_dump())

    def delete_skill(self, user_id: UUID, skill_id: UUID) -> None:
        if not self._repo.delete_skill(user_id, skill_id):
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")

    def list_evidence(
        self,
        user_id: UUID,
        *,
        skill_id: UUID | None = None,
    ) -> list[SkillEvidenceResponse]:
        if skill_id is not None and self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        records = self._repo.list_evidence(user_id, skill_id=skill_id)
        records.sort(key=lambda item: item.observed_at, reverse=True)
        return [SkillEvidenceResponse.model_validate(item.model_dump()) for item in records]

    def add_evidence(
        self,
        user_id: UUID,
        skill_id: UUID,
        payload: SkillEvidenceCreate,
    ) -> SkillEvidenceResponse:
        if self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        now = datetime.now(timezone.utc)
        record = SkillEvidenceRecord(
            id=uuid4(),
            user_id=user_id,
            skill_id=skill_id,
            type=payload.type,
            description=payload.description,
            reference_url=payload.reference_url,
            result=payload.result,
            observed_at=payload.observed_at or now,
            created_at=now,
            updated_at=now,
        )
        saved = self._repo.save_evidence(record)
        return SkillEvidenceResponse.model_validate(saved.model_dump())

    def update_evidence(
        self,
        user_id: UUID,
        skill_id: UUID,
        evidence_id: UUID,
        payload: SkillEvidenceUpdate,
    ) -> SkillEvidenceResponse:
        if self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        existing = self._repo.get_evidence(user_id, evidence_id)
        if existing is None or existing.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Preuve de compétence introuvable.")

        fields = payload.model_fields_set
        updates: dict[str, object] = {"updated_at": datetime.now(timezone.utc)}
        if "type" in fields and payload.type is not None:
            updates["type"] = payload.type
        if "description" in fields and payload.description is not None:
            updates["description"] = payload.description
        if "reference_url" in fields:
            updates["reference_url"] = payload.reference_url
        if "result" in fields:
            updates["result"] = payload.result
        if "observed_at" in fields and payload.observed_at is not None:
            updates["observed_at"] = payload.observed_at

        saved = self._repo.save_evidence(existing.model_copy(update=updates))
        return SkillEvidenceResponse.model_validate(saved.model_dump())

    def delete_evidence(self, user_id: UUID, skill_id: UUID, evidence_id: UUID) -> None:
        if self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        existing = self._repo.get_evidence(user_id, evidence_id)
        if existing is None or existing.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Preuve de compétence introuvable.")
        self._repo.delete_evidence(user_id, evidence_id)
