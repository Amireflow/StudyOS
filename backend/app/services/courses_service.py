from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from app.core.config import Settings
from app.core.errors import AppError
from app.repositories.courses_sql import (
    CourseLessonRecord,
    CourseLevelRecord,
    CourseRecord,
    CourseResourceRecord,
    CourseSubmissionRecord,
    SqlCourseRepository,
)
from app.repositories.learning_sql import (
    SkillEvidenceRecord,
    SkillRecord,
    SqlSkillRepository,
)
from app.schemas.common import (
    CourseLessonStatus,
    CourseLevelStatus,
    CourseResourceType,
    CourseStatus,
    CourseSubmissionKind,
    CourseSubmissionStatus,
    EvidenceVerificationStatus,
    SkillEvidenceType,
)
from app.schemas.courses import (
    CourseCreate,
    CourseDetailResponse,
    CourseLessonProgressUpdate,
    CourseLessonResponse,
    CourseLevelRegenerateRequest,
    CourseLevelResponse,
    CoursePreviewLesson,
    CoursePreviewLevel,
    CoursePreviewRequest,
    CoursePreviewResponse,
    CoursePreviewResource,
    CourseResourceCreate,
    CourseResourceResponse,
    CourseSubmissionCreate,
    CourseSubmissionResponse,
    CourseSummaryResponse,
    CourseUpdate,
)
from app.services.course_generator import (
    build_course_blueprint,
    evaluate_course_submission,
    generate_level_content,
    pass_threshold_for_course_level,
)
from app.services.profile_service import ProfileService


def _sanitize_exercises_for_client(exercises: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for item in exercises or []:
        if not isinstance(item, dict):
            continue
        clean = {k: v for k, v in item.items() if k != "expected_answer"}
        sanitized.append(clean)
    return sanitized


def _to_lesson_response(record: CourseLessonRecord) -> CourseLessonResponse:
    data = record.model_dump()
    data["exercises"] = _sanitize_exercises_for_client(data.get("exercises"))
    return CourseLessonResponse.model_validate(data)


def _to_resource_response(record: CourseResourceRecord) -> CourseResourceResponse:
    return CourseResourceResponse.model_validate(record.model_dump())


def _to_submission_response(record: CourseSubmissionRecord) -> CourseSubmissionResponse:
    data = record.model_dump()
    data["static_analysis"] = data.get("static_analysis") or {}
    return CourseSubmissionResponse.model_validate(data)


class CourseService:
    def __init__(
        self,
        *,
        repo: SqlCourseRepository,
        skill_repo: SqlSkillRepository | None = None,
        profile_service: ProfileService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._repo = repo
        self._skill_repo = skill_repo
        self._profile_service = profile_service
        self._settings = settings

    def _safe_user_ai_config(self, user_id: UUID | None) -> dict[str, Any] | None:
        if user_id is None or self._profile_service is None:
            return None
        try:
            return self._profile_service.get_ai_provider_config(user_id)
        except Exception:
            return None

    def preview_course(
        self,
        payload: CoursePreviewRequest,
        *,
        user_id: UUID | None = None,
    ) -> CoursePreviewResponse:
        blueprint = build_course_blueprint(
            subject=payload.subject,
            title=payload.title,
            domain=payload.domain,
            language=payload.language,
            total_levels=payload.total_levels,
            goal=payload.goal,
        )
        level1 = generate_level_content(
            subject=blueprint["subject"],
            language=payload.language,
            level_number=1,
            total_levels=payload.total_levels,
            settings=self._settings,
            user_ai_config=self._safe_user_ai_config(user_id),
        )
        sanitized_lessons = [
            {**item, "exercises": _sanitize_exercises_for_client(item.get("exercises"))}
            for item in level1["lessons"]
        ]
        return CoursePreviewResponse(
            title=blueprint["title"],
            subject=blueprint["subject"],
            domain=blueprint["domain"],
            description=blueprint["description"],
            language=payload.language,
            total_levels=payload.total_levels,
            levels_roadmap=[
                CoursePreviewLevel.model_validate(item) for item in blueprint["levels_roadmap"]
            ],
            first_level_lessons=[
                CoursePreviewLesson.model_validate(item) for item in sanitized_lessons
            ],
            first_level_project_title=level1["project_title"],
            first_level_project_brief=level1["project_brief"],
            first_level_project_deliverables=level1["project_deliverables"],
            first_level_resources=[
                CoursePreviewResource.model_validate(item) for item in level1["resources"]
            ],
        )

    def _populate_level_artifacts(
        self,
        *,
        user_id: UUID,
        course: CourseRecord,
        level: CourseLevelRecord,
        now: datetime,
        focus_hint: str | None = None,
    ) -> CourseLevelRecord:
        generated = generate_level_content(
            subject=course.subject,
            language=course.language,
            level_number=level.level_number,
            total_levels=course.total_levels,
            settings=self._settings,
            user_ai_config=self._safe_user_ai_config(user_id),
            focus_hint=focus_hint,
        )
        updated_level = self._repo.save_level(
            level.model_copy(
                update={
                    "title": generated["title"][:160],
                    "summary": generated["summary"],
                    "objectives": generated["objectives"],
                    "status": (
                        CourseLevelStatus.in_progress
                        if level.status == CourseLevelStatus.in_progress
                        else CourseLevelStatus.unlocked
                    ),
                    "content_generated": True,
                    "project_title": generated["project_title"][:180],
                    "project_brief": generated["project_brief"],
                    "project_deliverables": generated["project_deliverables"],
                    "project_rubric": generated["project_rubric"],
                    "generation_source": generated["generation_source"],
                    "updated_at": now,
                }
            )
        )
        if level.level_number == 1 or generated.get("generation_source") in {"user_ai", "server_ai"}:
            self._repo.save_course(
                course.model_copy(
                    update={
                        "generation_source": generated["generation_source"],
                        "generation_model": generated.get("generation_model"),
                        "updated_at": now,
                    }
                )
            )

        for item in generated["lessons"]:
            self._repo.save_lesson(
                CourseLessonRecord(
                    id=uuid4(),
                    user_id=user_id,
                    course_id=course.id,
                    level_id=updated_level.id,
                    position=int(item["position"]),
                    title=str(item["title"])[:160],
                    summary=str(item.get("summary") or "")[:300] or None,
                    estimated_minutes=int(item.get("estimated_minutes") or 25),
                    content_markdown=str(item["content_markdown"]),
                    code_examples=list(item.get("code_examples") or []),
                    exercises=list(item.get("exercises") or []),
                    status=CourseLessonStatus.not_started,
                    created_at=now,
                    updated_at=now,
                )
            )

        existing_level_urls = {
            r.url
            for r in self._repo.list_resources(user_id, course_id=course.id)
            if r.level_id == updated_level.id
        }
        for res in generated["resources"]:
            if res["url"] in existing_level_urls:
                continue
            existing_level_urls.add(res["url"])
            self._repo.save_resource(
                CourseResourceRecord(
                    id=uuid4(),
                    user_id=user_id,
                    course_id=course.id,
                    level_id=updated_level.id,
                    lesson_id=None,
                    title=str(res["title"])[:180],
                    url=str(res["url"])[:500],
                    resource_type=CourseResourceType(res["resource_type"]),
                    language=str(res.get("language", "fr")),
                    is_official=bool(res.get("is_official", False)),
                    source_name=res.get("source_name"),
                    notes=res.get("notes"),
                    created_at=now,
                    updated_at=now,
                )
            )

        return updated_level

    def create_course(self, user_id: UUID, payload: CourseCreate) -> CourseDetailResponse:
        blueprint = build_course_blueprint(
            subject=payload.subject,
            title=payload.title,
            domain=payload.domain,
            description=payload.description,
            language=payload.language,
            total_levels=payload.total_levels,
            goal=payload.goal,
        )
        now = datetime.now(timezone.utc)

        linked_skill_id: UUID | None = None
        if payload.link_skill and self._skill_repo is not None:
            existing_skills = self._skill_repo.list_skills(user_id)
            match = next(
                (
                    s
                    for s in existing_skills
                    if s.name.strip().lower() == blueprint["subject"].strip().lower()
                ),
                None,
            )
            if match is not None:
                linked_skill_id = match.id
            else:
                new_skill = self._skill_repo.save_skill(
                    SkillRecord(
                        id=uuid4(),
                        user_id=user_id,
                        name=blueprint["subject"][:120],
                        domain=blueprint["domain"][:80],
                        description=blueprint["description"],
                        current_level=0,
                        target_level=min(5, payload.total_levels),
                        last_assessed_at=None,
                        created_at=now,
                        updated_at=now,
                    )
                )
                linked_skill_id = new_skill.id

        course = self._repo.save_course(
            CourseRecord(
                id=uuid4(),
                user_id=user_id,
                title=blueprint["title"],
                subject=blueprint["subject"],
                domain=blueprint["domain"],
                description=blueprint["description"],
                language=payload.language,
                current_level=1,
                total_levels=payload.total_levels,
                status=CourseStatus.active,
                skill_id=linked_skill_id,
                learning_path_id=None,
                created_at=now,
                updated_at=now,
            )
        )

        for lvl_spec in blueprint["levels_roadmap"]:
            lvl_num = int(lvl_spec["level_number"])
            level_record = self._repo.save_level(
                CourseLevelRecord(
                    id=uuid4(),
                    user_id=user_id,
                    course_id=course.id,
                    level_number=lvl_num,
                    title=str(lvl_spec["title"])[:160],
                    summary=str(lvl_spec["summary"]),
                    objectives=list(lvl_spec.get("objectives") or []),
                    status=(
                        CourseLevelStatus.unlocked if lvl_num == 1 else CourseLevelStatus.locked
                    ),
                    content_generated=False,
                    project_title=lvl_spec.get("project_title"),
                    created_at=now,
                    updated_at=now,
                )
            )
            if lvl_num == 1:
                self._populate_level_artifacts(
                    user_id=user_id,
                    course=course,
                    level=level_record,
                    now=now,
                )

        return self.get_course_detail(user_id, course.id)

    def _build_summary(
        self,
        course: CourseRecord,
        lessons: list[CourseLessonRecord],
        resources: list[CourseResourceRecord],
    ) -> CourseSummaryResponse:
        completed_count = sum(1 for item in lessons if item.status == CourseLessonStatus.completed)
        return CourseSummaryResponse(
            id=course.id,
            user_id=course.user_id,
            title=course.title,
            subject=course.subject,
            domain=course.domain,
            description=course.description,
            language=course.language,
            current_level=course.current_level,
            total_levels=course.total_levels,
            status=course.status,
            skill_id=course.skill_id,
            learning_path_id=course.learning_path_id,
            generation_source=course.generation_source,
            generation_model=course.generation_model,
            completed_lessons_count=completed_count,
            total_lessons_count=len(lessons),
            resources_count=len(resources),
            created_at=course.created_at,
            updated_at=course.updated_at,
        )

    def list_courses(self, user_id: UUID) -> list[CourseSummaryResponse]:
        courses = self._repo.list_courses(user_id)
        all_lessons = self._repo.list_lessons(user_id)
        all_resources = self._repo.list_resources(user_id)

        lessons_by_course: dict[UUID, list[CourseLessonRecord]] = {}
        for lesson in all_lessons:
            lessons_by_course.setdefault(lesson.course_id, []).append(lesson)

        resources_by_course: dict[UUID, list[CourseResourceRecord]] = {}
        for res in all_resources:
            resources_by_course.setdefault(res.course_id, []).append(res)

        return [
            self._build_summary(
                course,
                lessons_by_course.get(course.id, []),
                resources_by_course.get(course.id, []),
            )
            for course in courses
        ]

    def get_course_detail(self, user_id: UUID, course_id: UUID) -> CourseDetailResponse:
        course = self._repo.get_course(user_id, course_id)
        if course is None:
            raise AppError(404, "NOT_FOUND", "Cours introuvable.")

        levels = self._repo.list_levels(user_id, course_id=course.id)
        lessons = self._repo.list_lessons(user_id, course_id=course.id)
        resources = self._repo.list_resources(user_id, course_id=course.id)
        submissions = self._repo.list_submissions(user_id, course_id=course.id)

        lessons_by_level: dict[UUID, list[CourseLessonResponse]] = {}
        for item in lessons:
            lessons_by_level.setdefault(item.level_id, []).append(_to_lesson_response(item))

        resources_by_level: dict[UUID, list[CourseResourceResponse]] = {}
        for res in resources:
            if res.level_id is not None:
                resources_by_level.setdefault(res.level_id, []).append(_to_resource_response(res))

        submissions_by_level: dict[UUID, list[CourseSubmissionResponse]] = {}
        for sub in submissions:
            submissions_by_level.setdefault(sub.level_id, []).append(_to_submission_response(sub))

        level_responses: list[CourseLevelResponse] = []
        for lvl in levels:
            lvl_lessons = lessons_by_level.get(lvl.id, [])
            lvl_subs = submissions_by_level.get(lvl.id, [])
            threshold = pass_threshold_for_course_level(lvl.level_number)
            lessons_completed = bool(lvl_lessons) and all(
                item.status == CourseLessonStatus.completed for item in lvl_lessons
            )
            passed_exercise_keys = {
                (s.lesson_id, s.exercise_id or s.title)
                for s in lvl_subs
                if s.submission_kind == CourseSubmissionKind.exercise and s.passed is True
            }
            has_exercises = any(bool(item.exercises) for item in lvl_lessons)
            exercises_passed_count = len(passed_exercise_keys)
            exercise_passed = True if not has_exercises else exercises_passed_count >= 1
            project_passed = any(
                s.submission_kind == CourseSubmissionKind.project
                and s.passed is True
                and not s.manual_review_required
                and (s.score or 0) >= threshold
                for s in lvl_subs
            )
            can_validate = (
                lvl.status in {CourseLevelStatus.unlocked, CourseLevelStatus.in_progress}
                and lessons_completed
                and exercise_passed
                and project_passed
            )
            level_responses.append(
                CourseLevelResponse(
                    id=lvl.id,
                    user_id=lvl.user_id,
                    course_id=lvl.course_id,
                    level_number=lvl.level_number,
                    title=lvl.title,
                    summary=lvl.summary,
                    objectives=list(lvl.objectives),
                    status=lvl.status,
                    content_generated=lvl.content_generated,
                    project_title=lvl.project_title,
                    project_brief=lvl.project_brief,
                    project_deliverables=list(lvl.project_deliverables),
                    project_rubric=lvl.project_rubric,
                    generation_source=lvl.generation_source,
                    revision=lvl.revision,
                    previous_versions_count=len(lvl.previous_versions),
                    validated_at=lvl.validated_at,
                    lessons=lvl_lessons,
                    resources=resources_by_level.get(lvl.id, []),
                    submissions=lvl_subs,
                    pass_threshold=threshold,
                    project_passed=project_passed,
                    lessons_completed=lessons_completed,
                    exercises_passed_count=exercises_passed_count,
                    exercise_passed=exercise_passed,
                    can_validate=can_validate,
                    created_at=lvl.created_at,
                    updated_at=lvl.updated_at,
                )
            )

        summary = self._build_summary(course, lessons, resources)
        return CourseDetailResponse(
            **summary.model_dump(),
            levels=level_responses,
            resources=[_to_resource_response(r) for r in resources],
        )

    def update_course(
        self,
        user_id: UUID,
        course_id: UUID,
        payload: CourseUpdate,
    ) -> CourseSummaryResponse:
        existing = self._repo.get_course(user_id, course_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Cours introuvable.")

        updated_status = existing.status
        if payload.status is not None and existing.status != CourseStatus.completed:
            updated_status = payload.status

        now = datetime.now(timezone.utc)
        saved = self._repo.save_course(
            existing.model_copy(
                update={
                    "title": payload.title if payload.title is not None else existing.title,
                    "description": (
                        payload.description
                        if payload.description is not None
                        else existing.description
                    ),
                    "language": (
                        payload.language if payload.language is not None else existing.language
                    ),
                    "status": updated_status,
                    "updated_at": now,
                }
            )
        )
        lessons = self._repo.list_lessons(user_id, course_id=saved.id)
        resources = self._repo.list_resources(user_id, course_id=saved.id)
        return self._build_summary(saved, lessons, resources)

    def delete_course(self, user_id: UUID, course_id: UUID) -> None:
        if not self._repo.delete_course(user_id, course_id):
            raise AppError(404, "NOT_FOUND", "Cours introuvable.")

    def update_lesson_progress(
        self,
        user_id: UUID,
        course_id: UUID,
        lesson_id: UUID,
        payload: CourseLessonProgressUpdate,
    ) -> CourseLessonResponse:
        course = self._repo.get_course(user_id, course_id)
        if course is None:
            raise AppError(404, "NOT_FOUND", "Cours introuvable.")
        lesson = self._repo.get_lesson(user_id, lesson_id)
        if lesson is None or lesson.course_id != course.id:
            raise AppError(404, "NOT_FOUND", "Chapitre de cours introuvable.")
        level = self._repo.get_level(user_id, lesson.level_id)
        if level is None:
            raise AppError(404, "NOT_FOUND", "Niveau introuvable.")
        if level.status == CourseLevelStatus.locked:
            raise AppError(409, "LEVEL_LOCKED", "Ce niveau est encore verrouillé.")

        now = datetime.now(timezone.utc)
        completed_at = (
            now
            if payload.status == CourseLessonStatus.completed
            else None
        )
        saved_lesson = self._repo.save_lesson(
            lesson.model_copy(
                update={
                    "status": payload.status,
                    "completed_at": completed_at,
                    "updated_at": now,
                }
            )
        )

        # Met le niveau à "in_progress" sans jamais le valider automatiquement
        if level.status == CourseLevelStatus.unlocked:
            self._repo.save_level(
                level.model_copy(
                    update={"status": CourseLevelStatus.in_progress, "updated_at": now}
                )
            )
        self._repo.save_course(course.model_copy(update={"updated_at": now}))
        return _to_lesson_response(saved_lesson)

    def add_resource(
        self,
        user_id: UUID,
        course_id: UUID,
        payload: CourseResourceCreate,
    ) -> CourseResourceResponse:
        course = self._repo.get_course(user_id, course_id)
        if course is None:
            raise AppError(404, "NOT_FOUND", "Cours introuvable.")
        if payload.level_id is not None:
            lvl = self._repo.get_level(user_id, payload.level_id)
            if lvl is None or lvl.course_id != course.id:
                raise AppError(404, "NOT_FOUND", "Niveau cible introuvable.")
        if payload.lesson_id is not None:
            lesson = self._repo.get_lesson(user_id, payload.lesson_id)
            if lesson is None or lesson.course_id != course.id:
                raise AppError(404, "NOT_FOUND", "Chapitre cible introuvable.")
            if payload.level_id is not None and lesson.level_id != payload.level_id:
                raise AppError(
                    422,
                    "LEARNING_HIERARCHY_MISMATCH",
                    "Le chapitre cible n'appartient pas au niveau indiqué.",
                )

        now = datetime.now(timezone.utc)
        saved = self._repo.save_resource(
            CourseResourceRecord(
                id=uuid4(),
                user_id=user_id,
                course_id=course.id,
                level_id=payload.level_id,
                lesson_id=payload.lesson_id,
                title=payload.title,
                url=payload.url,
                resource_type=payload.resource_type,
                language=payload.language,
                is_official=payload.is_official,
                source_name=payload.source_name,
                notes=payload.notes,
                created_at=now,
                updated_at=now,
            )
        )
        return _to_resource_response(saved)

    def delete_resource(self, user_id: UUID, course_id: UUID, resource_id: UUID) -> None:
        resource = self._repo.get_resource(user_id, resource_id)
        if resource is None or resource.course_id != course_id:
            raise AppError(404, "NOT_FOUND", "Ressource introuvable.")
        self._repo.delete_resource(user_id, resource_id)

    def submit_work(
        self,
        user_id: UUID,
        course_id: UUID,
        level_id: UUID,
        payload: CourseSubmissionCreate,
    ) -> CourseSubmissionResponse:
        course = self._repo.get_course(user_id, course_id)
        if course is None:
            raise AppError(404, "NOT_FOUND", "Cours introuvable.")
        level = self._repo.get_level(user_id, level_id)
        if level is None or level.course_id != course.id:
            raise AppError(404, "NOT_FOUND", "Niveau de cours introuvable.")
        if level.status == CourseLevelStatus.locked:
            raise AppError(
                409,
                "LEVEL_LOCKED",
                "Ce niveau est verrouillé. Validez d'abord le niveau précédent.",
            )

        expected_concepts: list[str] = []
        sub_title = payload.title or (
            level.project_title or f"Projet Niveau {level.level_number}"
        )
        ex_type: str | None = None
        expected_answer: str | None = None
        choices: list[str] | None = None
        starter_code: str | None = None

        if payload.lesson_id is not None:
            lesson = self._repo.get_lesson(user_id, payload.lesson_id)
            if lesson is None or lesson.level_id != level.id:
                raise AppError(404, "NOT_FOUND", "Chapitre associé introuvable.")
            matched_ex = None
            if payload.exercise_id:
                matched_ex = next(
                    (
                        ex
                        for ex in lesson.exercises
                        if str(ex.get("id")) == payload.exercise_id
                    ),
                    None,
                )
            elif lesson.exercises and payload.submission_kind == CourseSubmissionKind.exercise:
                matched_ex = lesson.exercises[0]
            if matched_ex is not None:
                sub_title = payload.title or str(matched_ex.get("title") or sub_title)
                expected_concepts = list(matched_ex.get("expected_concepts") or [])
                ex_type = matched_ex.get("exercise_type")
                expected_answer = matched_ex.get("expected_answer")
                choices = list(matched_ex.get("choices") or [])
                starter_code = matched_ex.get("starter_code")
            if not expected_concepts:
                expected_concepts = [lesson.title]

        if payload.submission_kind == CourseSubmissionKind.project:
            expected_concepts.extend(level.objectives)

        prior_subs = self._repo.list_submissions(user_id, course_id=course.id, level_id=level.id)
        attempt_number = 1 + sum(
            1
            for s in prior_subs
            if s.submission_kind == payload.submission_kind
            and (
                payload.submission_kind != CourseSubmissionKind.exercise
                or (s.lesson_id == payload.lesson_id and s.exercise_id == payload.exercise_id)
            )
        )

        graded = evaluate_course_submission(
            subject=course.subject,
            level_number=level.level_number,
            kind=payload.submission_kind,
            title=sub_title,
            answer_text=payload.answer_text,
            submitted_code=payload.submitted_code,
            reference_url=payload.reference_url,
            expected_concepts=expected_concepts,
            deliverables=level.project_deliverables
            if payload.submission_kind == CourseSubmissionKind.project
            else None,
            exercise_type=ex_type,
            expected_answer=expected_answer,
            choices=choices,
            starter_code=starter_code,
            attempt_number=attempt_number,
            settings=self._settings,
        )

        now = datetime.now(timezone.utc)
        saved = self._repo.save_submission(
            CourseSubmissionRecord(
                id=uuid4(),
                user_id=user_id,
                course_id=course.id,
                level_id=level.id,
                lesson_id=payload.lesson_id,
                submission_kind=payload.submission_kind,
                exercise_id=payload.exercise_id,
                title=sub_title[:180],
                answer_text=payload.answer_text,
                submitted_code=payload.submitted_code,
                reference_url=payload.reference_url,
                status=CourseSubmissionStatus.evaluated,
                score=graded["score"],
                passed=graded["passed"],
                criteria_results=graded["criteria_results"],
                feedback_markdown=graded["feedback_markdown"],
                strengths=graded["strengths"],
                improvements=graded["improvements"],
                next_step_hint=graded["next_step_hint"],
                attempt_number=attempt_number,
                evaluation_mode=graded["evaluation_mode"],
                manual_review_required=graded["manual_review_required"],
                static_analysis=graded["static_analysis"],
                created_at=now,
                updated_at=now,
            )
        )

        if level.status == CourseLevelStatus.unlocked:
            self._repo.save_level(
                level.model_copy(
                    update={"status": CourseLevelStatus.in_progress, "updated_at": now}
                )
            )
        self._repo.save_course(course.model_copy(update={"updated_at": now}))
        return _to_submission_response(saved)

    def validate_level(
        self,
        user_id: UUID,
        course_id: UUID,
        level_id: UUID,
    ) -> CourseDetailResponse:
        course = self._repo.get_course(user_id, course_id)
        if course is None:
            raise AppError(404, "NOT_FOUND", "Cours introuvable.")
        level = self._repo.get_level(user_id, level_id)
        if level is None or level.course_id != course.id:
            raise AppError(404, "NOT_FOUND", "Niveau introuvable.")

        if level.status == CourseLevelStatus.locked:
            raise AppError(
                409,
                "LEVEL_LOCKED",
                "Impossible de valider un niveau encore verrouillé.",
            )
        if level.status == CourseLevelStatus.validated:
            raise AppError(
                409,
                "LEVEL_ALREADY_VALIDATED",
                "Ce niveau a déjà été validé.",
            )

        level_lessons = [
            l for l in self._repo.list_lessons(user_id, course_id=course.id) if l.level_id == level.id
        ]
        completed_count = sum(
            1 for item in level_lessons if item.status == CourseLessonStatus.completed
        )
        if not level_lessons or completed_count < len(level_lessons):
            raise AppError(
                422,
                "LESSONS_COMPLETION_REQUIRED",
                f"Verrou pédagogique : terminez d'abord tous les chapitres du niveau {level.level_number} "
                f"({completed_count}/{len(level_lessons)} terminé(s)).",
            )

        threshold = pass_threshold_for_course_level(level.level_number)
        level_subs = self._repo.list_submissions(user_id, course_id=course.id, level_id=level.id)

        has_exercises = any(bool(item.exercises) for item in level_lessons)
        passing_exercise = next(
            (
                s
                for s in level_subs
                if s.submission_kind == CourseSubmissionKind.exercise and s.passed is True
            ),
            None,
        )
        if has_exercises and passing_exercise is None:
            raise AppError(
                422,
                "EXERCISE_VALIDATION_REQUIRED",
                f"Verrou pédagogique : réussissez au moins un exercice du niveau {level.level_number} avant sa validation.",
            )

        passing_project = next(
            (
                s
                for s in level_subs
                if s.submission_kind == CourseSubmissionKind.project
                and s.passed is True
                and not s.manual_review_required
                and (s.score or 0) >= threshold
            ),
            None,
        )
        if passing_project is None:
            raise AppError(
                422,
                "PROJECT_VALIDATION_REQUIRED",
                f"Verrou pédagogique : vous devez soumettre et réussir le projet vérifiable du niveau {level.level_number} (score >= {threshold}/100 sans revue manuelle bloquante) avant de débloquer la suite.",
            )

        now = datetime.now(timezone.utc)
        self._repo.save_level(
            level.model_copy(
                update={
                    "status": CourseLevelStatus.validated,
                    "validated_at": now,
                    "updated_at": now,
                }
            )
        )

        # Associe une preuve concrète sur la compétence liée sans jamais contourner son verrou
        if course.skill_id is not None and self._skill_repo is not None:
            linked_skill = self._skill_repo.get_skill(user_id, course.skill_id)
            if linked_skill is not None:
                verification = (
                    EvidenceVerificationStatus.verified
                    if passing_project.evaluation_mode in {"static_ast", "github_verified"}
                    else EvidenceVerificationStatus.inspected
                )
                self._skill_repo.save_evidence(
                    SkillEvidenceRecord(
                        id=uuid4(),
                        user_id=user_id,
                        skill_id=linked_skill.id,
                        type=SkillEvidenceType.project,
                        description=(
                            f"Projet niveau {level.level_number}/{course.total_levels} du cours "
                            f"« {course.title} » validé ({passing_project.title})."
                        ),
                        reference_url=passing_project.reference_url,
                        result=f"Score {passing_project.score}/100 ({passing_project.evaluation_mode})",
                        verification_status=verification,
                        inspection_metadata={
                            "evaluation_mode": passing_project.evaluation_mode,
                            "score": passing_project.score,
                            "course_id": str(course.id),
                            "level_number": level.level_number,
                        },
                        inspected_at=now,
                        observed_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                )

        if level.level_number < course.total_levels:
            all_levels = self._repo.list_levels(user_id, course_id=course.id)
            next_level = next(
                (item for item in all_levels if item.level_number == level.level_number + 1),
                None,
            )
            if next_level is not None and not next_level.content_generated:
                self._populate_level_artifacts(
                    user_id=user_id,
                    course=course,
                    level=next_level,
                    now=now,
                )
            elif next_level is not None and next_level.status == CourseLevelStatus.locked:
                self._repo.save_level(
                    next_level.model_copy(
                        update={"status": CourseLevelStatus.unlocked, "updated_at": now}
                    )
                )
            self._repo.save_course(
                course.model_copy(
                    update={
                        "current_level": level.level_number + 1,
                        "updated_at": now,
                    }
                )
            )
        else:
            self._repo.save_course(
                course.model_copy(
                    update={
                        "status": CourseStatus.completed,
                        "updated_at": now,
                    }
                )
            )

        return self.get_course_detail(user_id, course.id)

    def regenerate_level(
        self,
        user_id: UUID,
        course_id: UUID,
        level_id: UUID,
        payload: CourseLevelRegenerateRequest | None = None,
    ) -> CourseDetailResponse:
        course = self._repo.get_course(user_id, course_id)
        if course is None:
            raise AppError(404, "NOT_FOUND", "Cours introuvable.")
        level = self._repo.get_level(user_id, level_id)
        if level is None or level.course_id != course.id:
            raise AppError(404, "NOT_FOUND", "Niveau introuvable.")
        if level.status == CourseLevelStatus.locked:
            raise AppError(
                409,
                "LEVEL_LOCKED",
                "Impossible de régénérer un niveau encore verrouillé.",
            )
        if level.status == CourseLevelStatus.validated:
            raise AppError(
                409,
                "LEVEL_ALREADY_VALIDATED",
                "Un niveau déjà validé ne peut pas être régénéré afin de préserver vos preuves.",
            )

        now = datetime.now(timezone.utc)
        current_lessons = [
            l for l in self._repo.list_lessons(user_id, course_id=course.id) if l.level_id == level.id
        ]
        snapshot = {
            "revision": level.revision,
            "title": level.title,
            "summary": level.summary,
            "objectives": list(level.objectives),
            "project_title": level.project_title,
            "generation_source": level.generation_source,
            "archived_at": now.isoformat(),
            "lessons_titles": [l.title for l in current_lessons],
        }
        archived_versions = (list(level.previous_versions) + [snapshot])[-10:]

        # Préserver l'historique des soumissions mais remplacer les chapitres du niveau
        self._repo.delete_lessons_for_level(user_id, level.id)
        bumped = self._repo.save_level(
            level.model_copy(
                update={
                    "revision": level.revision + 1,
                    "previous_versions": archived_versions,
                    "updated_at": now,
                }
            )
        )
        focus_hint = payload.focus_hint if payload is not None else None
        self._populate_level_artifacts(
            user_id=user_id,
            course=course,
            level=bumped,
            now=now,
            focus_hint=focus_hint,
        )
        return self.get_course_detail(user_id, course.id)
