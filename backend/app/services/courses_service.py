from __future__ import annotations

from datetime import datetime, timezone
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
    SkillEvidenceType,
)
from app.schemas.courses import (
    CourseCreate,
    CourseDetailResponse,
    CourseLessonProgressUpdate,
    CourseLessonResponse,
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


def _to_lesson_response(record: CourseLessonRecord) -> CourseLessonResponse:
    return CourseLessonResponse.model_validate(record.model_dump())


def _to_resource_response(record: CourseResourceRecord) -> CourseResourceResponse:
    return CourseResourceResponse.model_validate(record.model_dump())


def _to_submission_response(record: CourseSubmissionRecord) -> CourseSubmissionResponse:
    return CourseSubmissionResponse.model_validate(record.model_dump())


class CourseService:
    def __init__(
        self,
        *,
        repo: SqlCourseRepository,
        skill_repo: SqlSkillRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._repo = repo
        self._skill_repo = skill_repo
        self._settings = settings

    def preview_course(self, payload: CoursePreviewRequest) -> CoursePreviewResponse:
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
        )
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
                CoursePreviewLesson.model_validate(item) for item in level1["lessons"]
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
    ) -> CourseLevelRecord:
        generated = generate_level_content(
            subject=course.subject,
            language=course.language,
            level_number=level.level_number,
            total_levels=course.total_levels,
            settings=self._settings,
        )
        updated_level = self._repo.save_level(
            level.model_copy(
                update={
                    "title": generated["title"][:160],
                    "summary": generated["summary"],
                    "objectives": generated["objectives"],
                    "status": CourseLevelStatus.unlocked,
                    "content_generated": True,
                    "project_title": generated["project_title"][:180],
                    "project_brief": generated["project_brief"],
                    "project_deliverables": generated["project_deliverables"],
                    "project_rubric": generated["project_rubric"],
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

        existing_urls = {
            r.url for r in self._repo.list_resources(user_id, course_id=course.id)
        }
        for res in generated["resources"]:
            if res["url"] in existing_urls:
                continue
            existing_urls.add(res["url"])
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
            lvl_subs = submissions_by_level.get(lvl.id, [])
            threshold = pass_threshold_for_course_level(lvl.level_number)
            project_passed = any(
                s.submission_kind == CourseSubmissionKind.project
                and s.passed is True
                and (s.score or 0) >= threshold
                for s in lvl_subs
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
                    validated_at=lvl.validated_at,
                    lessons=lessons_by_level.get(lvl.id, []),
                    resources=resources_by_level.get(lvl.id, []),
                    submissions=lvl_subs,
                    pass_threshold=threshold,
                    project_passed=project_passed,
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

        if payload.lesson_id is not None:
            lesson = self._repo.get_lesson(user_id, payload.lesson_id)
            if lesson is None or lesson.level_id != level.id:
                raise AppError(404, "NOT_FOUND", "Chapitre associé introuvable.")
            if payload.exercise_id:
                matched_ex = next(
                    (
                        ex
                        for ex in lesson.exercises
                        if str(ex.get("id")) == payload.exercise_id
                    ),
                    None,
                )
                if matched_ex is not None:
                    sub_title = payload.title or str(matched_ex.get("title") or sub_title)
                    expected_concepts = list(matched_ex.get("expected_concepts") or [])
            if not expected_concepts:
                expected_concepts = [lesson.title]

        if payload.submission_kind == CourseSubmissionKind.project:
            expected_concepts.extend(level.objectives)

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

        threshold = pass_threshold_for_course_level(level.level_number)
        level_subs = self._repo.list_submissions(user_id, course_id=course.id, level_id=level.id)
        passing_project = next(
            (
                s
                for s in level_subs
                if s.submission_kind == CourseSubmissionKind.project
                and s.passed is True
                and (s.score or 0) >= threshold
            ),
            None,
        )
        if passing_project is None:
            raise AppError(
                422,
                "PROJECT_VALIDATION_REQUIRED",
                f"Verrou pédagogique : vous devez soumettre et réussir le projet du niveau {level.level_number} (score >= {threshold}/100) avant de débloquer la suite.",
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
                        result=f"Score {passing_project.score}/100",
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
