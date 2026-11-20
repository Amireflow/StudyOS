from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.common import (
    CourseLanguage,
    CourseLessonStatus,
    CourseLevelStatus,
    CourseResourceType,
    CourseStatus,
    CourseSubmissionKind,
    CourseSubmissionStatus,
    normalize_optional_text,
    validate_optional_http_url,
)


class CourseCodeExample(BaseModel):
    title: str
    language: str
    code: str
    explanation: str


class CourseExercise(BaseModel):
    id: str
    title: str
    difficulty: Literal["guide", "pratique", "defi"] = "guide"
    exercise_type: Literal["closed_quiz", "code", "open_explanation"] = "code"
    instructions_markdown: str
    starter_code: str | None = None
    choices: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    expected_concepts: list[str] = Field(default_factory=list)


class CourseLevelRegenerateRequest(BaseModel):
    focus_hint: str | None = Field(default=None, max_length=500)


class CourseRubricCriterion(BaseModel):
    key: str
    label: str
    description: str
    max_score: int


class CourseCriterionResult(BaseModel):
    key: str
    label: str
    score: int
    max_score: int
    passed: bool
    feedback: str


class CoursePreviewRequest(BaseModel):
    subject: str
    title: str | None = None
    domain: str | None = None
    language: CourseLanguage = CourseLanguage.fr
    total_levels: int = Field(default=3, ge=2, le=5)
    goal: str | None = None

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 120:
            raise ValueError("Le sujet ou langage doit contenir entre 2 et 120 caractères.")
        return cleaned

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 160)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 80)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)


class CourseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    title: str | None = None
    domain: str | None = None
    description: str | None = None
    language: CourseLanguage = CourseLanguage.fr
    total_levels: int = Field(default=3, ge=2, le=5)
    goal: str | None = None
    link_skill: bool = True

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 120:
            raise ValueError("Le sujet ou langage doit contenir entre 2 et 120 caractères.")
        return cleaned

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 160)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 80)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 2000)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)


class CourseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    language: CourseLanguage | None = None
    status: Literal[CourseStatus.active, CourseStatus.paused] | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 160:
            raise ValueError("Le titre du cours doit contenir entre 2 et 160 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 2000)


class CourseLessonProgressUpdate(BaseModel):
    status: CourseLessonStatus | None = None
    current_step_index: int | None = Field(default=None, ge=0, le=25)


class CourseTutorMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    quick_action: str | None = None
    step_index: int = 0
    follow_up_prompts: list[str] = Field(default_factory=list)
    created_at: str


class CourseLessonTutorAskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    quick_action: Literal["simplify", "example", "quiz", "custom"] | None = None
    step_index: int = Field(default=0, ge=0, le=25)
    step_title: str | None = Field(default=None, max_length=200)
    step_content: str | None = Field(default=None, max_length=6000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 1 or len(cleaned) > 3000:
            raise ValueError("Votre question au tuteur doit contenir entre 1 et 3000 caractères.")
        return cleaned


class CourseResourceCreate(BaseModel):
    title: str
    url: str
    resource_type: CourseResourceType = CourseResourceType.documentation
    language: Literal["fr", "en"] = "fr"
    is_official: bool = False
    source_name: str | None = None
    notes: str | None = None
    level_id: UUID | None = None
    lesson_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 180:
            raise ValueError("Le titre de la ressource doit contenir entre 2 et 180 caractères.")
        return cleaned

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        validated = validate_optional_http_url(value)
        if not validated:
            raise ValueError("L’URL de la ressource est obligatoire et doit être en http(s).")
        return validated

    @field_validator("source_name")
    @classmethod
    def validate_source_name(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 120)

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 400)


class CourseSubmissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_kind: CourseSubmissionKind
    lesson_id: UUID | None = None
    exercise_id: str | None = None
    title: str | None = None
    answer_text: str
    submitted_code: str | None = None
    reference_url: str | None = None

    @field_validator("exercise_id")
    @classmethod
    def validate_exercise_id(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 80)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 180)

    @field_validator("answer_text")
    @classmethod
    def validate_answer_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 1 or len(cleaned) > 8000:
            raise ValueError(
                "Votre réponse doit contenir entre 1 et 8000 caractères."
            )
        return cleaned

    @field_validator("submitted_code")
    @classmethod
    def validate_submitted_code(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 12000)

    @field_validator("reference_url")
    @classmethod
    def validate_reference_url(cls, value: str | None) -> str | None:
        return validate_optional_http_url(value)


class CourseLessonResponse(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    level_id: UUID
    position: int
    title: str
    summary: str | None = None
    estimated_minutes: int
    content_markdown: str
    code_examples: list[CourseCodeExample] = Field(default_factory=list)
    exercises: list[CourseExercise] = Field(default_factory=list)
    tutor_messages: list[CourseTutorMessage] = Field(default_factory=list)
    current_step_index: int = 0
    status: CourseLessonStatus
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CourseLessonTutorAskResponse(BaseModel):
    user_message: CourseTutorMessage
    assistant_message: CourseTutorMessage
    lesson: CourseLessonResponse


class CourseResourceResponse(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    level_id: UUID | None = None
    lesson_id: UUID | None = None
    title: str
    url: str
    resource_type: CourseResourceType
    language: Literal["fr", "en"]
    is_official: bool
    source_name: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CourseSubmissionResponse(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    level_id: UUID
    lesson_id: UUID | None = None
    submission_kind: CourseSubmissionKind
    exercise_id: str | None = None
    title: str
    answer_text: str
    submitted_code: str | None = None
    reference_url: str | None = None
    status: CourseSubmissionStatus
    score: int | None = None
    passed: bool | None = None
    criteria_results: list[CourseCriterionResult] = Field(default_factory=list)
    feedback_markdown: str | None = None
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    next_step_hint: str | None = None
    attempt_number: int = 1
    evaluation_mode: str = "static_heuristic"
    manual_review_required: bool = False
    static_analysis: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CourseLevelResponse(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    level_number: int
    title: str
    summary: str
    objectives: list[str] = Field(default_factory=list)
    status: CourseLevelStatus
    content_generated: bool
    project_title: str | None = None
    project_brief: str | None = None
    project_deliverables: list[str] = Field(default_factory=list)
    project_rubric: list[CourseRubricCriterion] = Field(default_factory=list)
    generation_source: str = "curated_track"
    revision: int = 1
    previous_versions_count: int = 0
    validated_at: datetime | None = None
    lessons: list[CourseLessonResponse] = Field(default_factory=list)
    resources: list[CourseResourceResponse] = Field(default_factory=list)
    submissions: list[CourseSubmissionResponse] = Field(default_factory=list)
    pass_threshold: int = 70
    project_passed: bool = False
    lessons_completed: bool = False
    exercises_passed_count: int = 0
    exercise_passed: bool = False
    can_validate: bool = False
    created_at: datetime
    updated_at: datetime


class CourseSummaryResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    subject: str
    domain: str
    description: str | None = None
    language: CourseLanguage
    current_level: int
    total_levels: int
    status: CourseStatus
    skill_id: UUID | None = None
    learning_path_id: UUID | None = None
    generation_source: str = "curated_track"
    generation_model: str | None = None
    completed_lessons_count: int = 0
    total_lessons_count: int = 0
    resources_count: int = 0
    created_at: datetime
    updated_at: datetime


class CourseDetailResponse(CourseSummaryResponse):
    levels: list[CourseLevelResponse] = Field(default_factory=list)
    resources: list[CourseResourceResponse] = Field(default_factory=list)


class CoursePreviewLevel(BaseModel):
    level_number: int
    title: str
    summary: str
    objectives: list[str] = Field(default_factory=list)
    project_title: str | None = None


class CoursePreviewLesson(BaseModel):
    position: int
    title: str
    summary: str | None = None
    estimated_minutes: int
    content_markdown: str
    code_examples: list[CourseCodeExample] = Field(default_factory=list)
    exercises: list[CourseExercise] = Field(default_factory=list)


class CoursePreviewResource(BaseModel):
    title: str
    url: str
    resource_type: CourseResourceType
    language: Literal["fr", "en"]
    is_official: bool
    source_name: str | None = None
    notes: str | None = None


class CoursePreviewResponse(BaseModel):
    title: str
    subject: str
    domain: str
    description: str
    language: CourseLanguage
    total_levels: int
    levels_roadmap: list[CoursePreviewLevel] = Field(default_factory=list)
    first_level_lessons: list[CoursePreviewLesson] = Field(default_factory=list)
    first_level_project_title: str
    first_level_project_brief: str
    first_level_project_deliverables: list[str] = Field(default_factory=list)
    first_level_resources: list[CoursePreviewResource] = Field(default_factory=list)
