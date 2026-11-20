from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.common import (
    EvidenceVerificationStatus,
    SkillAssessmentStatus,
    SkillAssessmentType,
    SkillEvaluationMode,
    SkillEvaluatorType,
    SkillEvidenceType,
    UtcDatetime,
    normalize_optional_text,
    validate_optional_http_url,
)


def _validate_skill_level(value: int) -> int:
    if value < 0 or value > 5:
        raise ValueError("Le niveau de compétence doit être compris entre 0 et 5.")
    return value


class SkillCreate(BaseModel):
    name: str
    domain: str
    description: str | None = None
    current_level: int = 0
    target_level: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 120:
            raise ValueError("Le nom doit contenir entre 2 et 120 caractères.")
        return cleaned

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 80:
            raise ValueError("Le domaine doit contenir entre 2 et 80 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("current_level")
    @classmethod
    def validate_current_level(cls, value: int) -> int:
        return _validate_skill_level(value)

    @field_validator("target_level")
    @classmethod
    def validate_target_level(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return _validate_skill_level(value)


class SkillUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    description: str | None = None
    current_level: int | None = None
    target_level: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Le nom ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 120:
            raise ValueError("Le nom doit contenir entre 2 et 120 caractères.")
        return cleaned

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Le domaine ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 80:
            raise ValueError("Le domaine doit contenir entre 2 et 80 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("current_level")
    @classmethod
    def validate_current_level(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return _validate_skill_level(value)

    @field_validator("target_level")
    @classmethod
    def validate_target_level(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return _validate_skill_level(value)


class SkillResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    domain: str
    description: str | None = None
    current_level: int
    target_level: int | None = None
    last_assessed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SkillEvidenceCreate(BaseModel):
    type: SkillEvidenceType = SkillEvidenceType.exercise
    description: str
    reference_url: str | None = None
    result: str | None = None
    observed_at: UtcDatetime | None = None

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 1000:
            raise ValueError("La description de la preuve doit contenir entre 2 et 1000 caractères.")
        return cleaned

    @field_validator("reference_url")
    @classmethod
    def validate_reference_url(cls, value: str | None) -> str | None:
        return validate_optional_http_url(value)

    @field_validator("result")
    @classmethod
    def validate_result(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 200)


class SkillEvidenceUpdate(BaseModel):
    type: SkillEvidenceType | None = None
    description: str | None = None
    reference_url: str | None = None
    result: str | None = None
    observed_at: UtcDatetime | None = None

    @field_validator("type")
    @classmethod
    def reject_null_type(cls, value: SkillEvidenceType | None) -> SkillEvidenceType:
        if value is None:
            raise ValueError("Le type de preuve ne peut pas être null.")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("La description de la preuve ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 1000:
            raise ValueError("La description de la preuve doit contenir entre 2 et 1000 caractères.")
        return cleaned

    @field_validator("reference_url")
    @classmethod
    def validate_reference_url(cls, value: str | None) -> str | None:
        return validate_optional_http_url(value)

    @field_validator("result")
    @classmethod
    def validate_result(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 200)

    @field_validator("observed_at")
    @classmethod
    def reject_null_observed_at(cls, value: UtcDatetime | None) -> UtcDatetime:
        if value is None:
            raise ValueError("La date d’observation ne peut pas être null.")
        return value


class SkillEvidenceInspectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_files: list[str] = Field(default_factory=list, max_length=10)


class SkillEvidenceResponse(BaseModel):
    id: UUID
    user_id: UUID
    skill_id: UUID
    type: SkillEvidenceType
    description: str
    reference_url: str | None = None
    result: str | None = None
    observed_at: datetime
    verification_status: EvidenceVerificationStatus = EvidenceVerificationStatus.declared
    inspection_metadata: dict[str, Any] = Field(default_factory=dict)
    inspected_at: datetime | None = None
    is_locked: bool = False
    is_admissible: bool = True
    external_reference_verified: bool = False
    verification_note: str | None = None
    created_at: datetime
    updated_at: datetime


class AssessmentCriterionSchema(BaseModel):
    key: str
    label: str
    description: str = ""
    weight: int = Field(default=25, ge=1, le=100)
    max_score: int = Field(default=25, ge=1, le=100)
    score: int = Field(default=0, ge=0, le=100)
    passed: bool = False
    feedback: str = ""


class SkillAssessmentCreate(BaseModel):
    """Demande d'ouverture d'évaluation : consignes, indices et critères sont strictement contrôlés côté serveur."""

    model_config = ConfigDict(extra="forbid")

    target_level: int | None = None
    assessment_type: SkillAssessmentType = SkillAssessmentType.practical_exercise
    path_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None

    @field_validator("target_level")
    @classmethod
    def validate_target_level(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 1 or value > 5:
            raise ValueError("Le niveau visé pour une évaluation doit être compris entre 1 et 5.")
        return value


class SkillAssessmentSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_text: str
    submission_code: str | None = None
    submission_reference_url: str | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    new_evidence: SkillEvidenceCreate | None = None

    @field_validator("submission_text")
    @classmethod
    def validate_submission_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 15 or len(cleaned) > 8000:
            raise ValueError(
                "La production ou réponse soumise doit contenir entre 15 et 8000 caractères."
            )
        return cleaned

    @field_validator("submission_code")
    @classmethod
    def validate_submission_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) > 12000:
            raise ValueError("L’extrait de code ne doit pas dépasser 12000 caractères.")
        return cleaned

    @field_validator("submission_reference_url")
    @classmethod
    def validate_reference_url(cls, value: str | None) -> str | None:
        return validate_optional_http_url(value)


class SkillAssessmentEvaluate(BaseModel):
    """Déclenche l'évaluation côté serveur. Toute tentative d'injection de score/critères est interdite."""

    model_config = ConfigDict(extra="forbid")

    request_ai_review: bool = False


class SkillAssessmentDecision(BaseModel):
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 500)


class SkillAssessmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    skill_id: UUID
    path_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None
    assessment_type: SkillAssessmentType
    starting_level: int
    target_level: int
    proposed_level: int | None = None
    status: SkillAssessmentStatus
    prompt_title: str
    prompt_instructions: str
    revealed_hints: list[str] = Field(default_factory=list)
    hints_total: int = 0
    hints_revealed_count: int = 0
    submission_text: str | None = None
    submission_code: str | None = None
    submission_reference_url: str | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    criteria: list[AssessmentCriterionSchema] = Field(default_factory=list)
    rubric_version: str = "rubric-v2"
    evaluator_version: str = "eval-v2"
    evaluation_mode: SkillEvaluationMode = SkillEvaluationMode.automated
    manual_review_required: bool = False
    rubric_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    evidence_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    reviewed_by: str | None = None
    score: int | None = None
    passed: bool | None = None
    feedback: str | None = None
    mastered_points: list[str] = Field(default_factory=list)
    gaps_identified: list[str] = Field(default_factory=list)
    remediation_recommendation: str | None = None
    external_verification_warning: str | None = None
    evaluator_type: SkillEvaluatorType
    evaluator_name: str | None = None
    decision_reason: str | None = None
    applied_level_delta: int | None = None
    submitted_at: datetime | None = None
    evaluated_at: datetime | None = None
    validated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
