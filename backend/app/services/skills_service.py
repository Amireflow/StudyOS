from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from app.core.config import Settings
from app.core.errors import AppError
from app.repositories.learning_sql import (
    SkillAssessmentRecord,
    SkillEvidenceRecord,
    SkillRecord,
    SqlLearningRepository,
    SqlSkillRepository,
)
from app.schemas.common import (
    EvidenceVerificationStatus,
    SkillAssessmentStatus,
    SkillAssessmentType,
    SkillEvaluationMode,
    SkillEvaluatorType,
)
from app.schemas.skills import (
    SkillAssessmentCreate,
    SkillAssessmentDecision,
    SkillAssessmentEvaluate,
    SkillAssessmentResponse,
    SkillAssessmentSubmit,
    SkillCreate,
    SkillEvidenceCreate,
    SkillEvidenceResponse,
    SkillEvidenceUpdate,
    SkillResponse,
    SkillUpdate,
)
from app.services.assessment_evaluator import (
    EVALUATOR_VERSION,
    EXTERNAL_URL_DISCLAIMER,
    RUBRIC_VERSION,
    build_assessment_exercise,
    evaluate_assessment_submission,
    pass_threshold_for_level,
    validate_evidence_quality,
)
from app.services.github_inspector import inspect_github_evidence


def _to_evidence_response(record: SkillEvidenceRecord) -> SkillEvidenceResponse:
    quality = validate_evidence_quality(
        record.type,
        record.description,
        record.reference_url,
        record.result,
        verification_status=record.verification_status,
    )
    return SkillEvidenceResponse(
        id=record.id,
        user_id=record.user_id,
        skill_id=record.skill_id,
        type=record.type,
        description=record.description,
        reference_url=record.reference_url,
        result=record.result,
        observed_at=record.observed_at,
        verification_status=record.verification_status,
        inspection_metadata=dict(record.inspection_metadata or {}),
        inspected_at=record.inspected_at,
        is_locked=bool(record.is_locked),
        is_admissible=quality.admissible,
        external_reference_verified=quality.external_reference_verified,
        verification_note=quality.verification_note,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _to_assessment_response(record: SkillAssessmentRecord) -> SkillAssessmentResponse:
    revealed_count = max(0, min(record.hints_revealed_count, len(record.hints)))
    return SkillAssessmentResponse(
        id=record.id,
        user_id=record.user_id,
        skill_id=record.skill_id,
        path_id=record.path_id,
        module_id=record.module_id,
        lesson_id=record.lesson_id,
        assessment_type=record.assessment_type,
        starting_level=record.starting_level,
        target_level=record.target_level,
        proposed_level=record.proposed_level,
        status=record.status,
        prompt_title=record.prompt_title,
        prompt_instructions=record.prompt_instructions,
        revealed_hints=list(record.hints[:revealed_count]),
        hints_total=len(record.hints),
        hints_revealed_count=revealed_count,
        submission_text=record.submission_text,
        submission_code=record.submission_code,
        submission_reference_url=record.submission_reference_url,
        evidence_ids=[UUID(item) for item in record.evidence_ids],
        criteria=list(record.criteria),
        rubric_version=record.rubric_version,
        evaluator_version=record.evaluator_version,
        evaluation_mode=record.evaluation_mode,
        manual_review_required=bool(record.manual_review_required),
        rubric_snapshot=list(record.rubric_snapshot or []),
        evidence_snapshot=list(record.evidence_snapshot or []),
        reviewed_by=record.reviewed_by,
        score=record.score,
        passed=record.passed,
        feedback=record.feedback,
        mastered_points=list(record.mastered_points),
        gaps_identified=list(record.gaps_identified),
        remediation_recommendation=record.remediation_recommendation,
        external_verification_warning=record.external_verification_warning,
        evaluator_type=record.evaluator_type,
        evaluator_name=record.evaluator_name,
        decision_reason=record.decision_reason,
        applied_level_delta=record.applied_level_delta,
        submitted_at=record.submitted_at,
        evaluated_at=record.evaluated_at,
        validated_at=record.validated_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _snapshot_evidence(records: list[SkillEvidenceRecord]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(ev.id),
            "type": ev.type.value,
            "description": ev.description,
            "reference_url": ev.reference_url,
            "result": ev.result,
            "verification_status": ev.verification_status.value,
        }
        for ev in records
    ]


class SkillService:
    def __init__(
        self,
        repo: SqlSkillRepository,
        learning_repo: SqlLearningRepository | None = None,
    ) -> None:
        self._repo = repo
        self._learning_repo = learning_repo

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
        if payload.current_level != 0:
            raise AppError(
                422,
                "SKILL_INITIAL_LEVEL_LOCKED",
                "Une nouvelle compétence doit obligatoirement démarrer au niveau 0. "
                "Passez par une évaluation validée pour progresser.",
            )
        now = datetime.now(timezone.utc)
        record = SkillRecord(
            id=uuid4(),
            user_id=user_id,
            name=payload.name,
            domain=payload.domain,
            description=payload.description,
            current_level=0,
            target_level=payload.target_level,
            last_assessed_at=None,
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

        fields = payload.model_fields_set
        if "current_level" in fields:
            raise AppError(
                403,
                "SKILL_ASSESSMENT_REQUIRED",
                "La modification directe du niveau d’une compétence est interdite. "
                "Créez et validez une évaluation pour faire évoluer le niveau.",
            )

        now = datetime.now(timezone.utc)
        updates: dict[str, object] = {"updated_at": now}

        if "name" in fields and payload.name is not None:
            updates["name"] = payload.name
        if "domain" in fields and payload.domain is not None:
            updates["domain"] = payload.domain
        if "description" in fields:
            updates["description"] = payload.description
        if "target_level" in fields:
            updates["target_level"] = payload.target_level

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
        return [_to_evidence_response(item) for item in records]

    def add_evidence(
        self,
        user_id: UUID,
        skill_id: UUID,
        payload: SkillEvidenceCreate,
    ) -> SkillEvidenceResponse:
        if self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")

        quality = validate_evidence_quality(
            payload.type,
            payload.description,
            payload.reference_url,
            payload.result,
        )
        if not quality.admissible:
            raise AppError(
                422,
                "EVIDENCE_QUALITY_INSUFFICIENT",
                quality.reason or "La preuve soumise ne répond pas aux critères de qualité pédagogique.",
            )

        now = datetime.now(timezone.utc)
        record = SkillEvidenceRecord(
            id=uuid4(),
            user_id=user_id,
            skill_id=skill_id,
            type=payload.type,
            description=payload.description,
            reference_url=payload.reference_url,
            result=payload.result,
            verification_status=EvidenceVerificationStatus.declared,
            inspection_metadata={},
            inspected_at=None,
            is_locked=False,
            observed_at=payload.observed_at or now,
            created_at=now,
            updated_at=now,
        )
        saved = self._repo.save_evidence(record)
        return _to_evidence_response(saved)

    def _evidence_linked_statuses(
        self, user_id: UUID, skill_id: UUID, evidence_id: UUID
    ) -> set[SkillAssessmentStatus]:
        ev_str = str(evidence_id)
        assessments = self._repo.list_assessments(user_id, skill_id=skill_id)
        return {
            a.status
            for a in assessments
            if ev_str in {str(x) for x in (a.evidence_ids or [])}
        }

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

        linked_statuses = self._evidence_linked_statuses(user_id, skill_id, evidence_id)
        if existing.is_locked or bool(
            linked_statuses
            & {
                SkillAssessmentStatus.submitted,
                SkillAssessmentStatus.evaluated,
                SkillAssessmentStatus.needs_manual_review,
                SkillAssessmentStatus.approved,
            }
        ):
            raise AppError(
                409,
                "EVIDENCE_LOCKED",
                "Cette preuve est rattachée à une évaluation soumise ou validée et ne peut plus être modifiée.",
            )

        fields = payload.model_fields_set
        next_type = payload.type if ("type" in fields and payload.type is not None) else existing.type
        next_desc = (
            payload.description
            if ("description" in fields and payload.description is not None)
            else existing.description
        )
        next_ref = payload.reference_url if "reference_url" in fields else existing.reference_url
        next_res = payload.result if "result" in fields else existing.result

        quality = validate_evidence_quality(next_type, next_desc, next_ref, next_res)
        if not quality.admissible:
            raise AppError(
                422,
                "EVIDENCE_QUALITY_INSUFFICIENT",
                quality.reason or "La preuve modifiée reste insuffisante.",
            )

        updates: dict[str, object] = {"updated_at": datetime.now(timezone.utc)}
        if "type" in fields and payload.type is not None:
            updates["type"] = payload.type
        if "description" in fields and payload.description is not None:
            updates["description"] = payload.description
        if "reference_url" in fields:
            updates["reference_url"] = payload.reference_url
            updates["verification_status"] = EvidenceVerificationStatus.declared
            updates["inspection_metadata"] = {}
            updates["inspected_at"] = None
        if "result" in fields:
            updates["result"] = payload.result
        if "observed_at" in fields and payload.observed_at is not None:
            updates["observed_at"] = payload.observed_at

        saved = self._repo.save_evidence(existing.model_copy(update=updates))
        return _to_evidence_response(saved)

    def delete_evidence(self, user_id: UUID, skill_id: UUID, evidence_id: UUID) -> None:
        if self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        existing = self._repo.get_evidence(user_id, evidence_id)
        if existing is None or existing.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Preuve de compétence introuvable.")
        linked_statuses = self._evidence_linked_statuses(user_id, skill_id, evidence_id)
        if existing.is_locked or SkillAssessmentStatus.approved in linked_statuses:
            raise AppError(
                409,
                "EVIDENCE_LOCKED",
                "Cette preuve a servi à valider un niveau de compétence et ne peut pas être supprimée.",
            )
        self._repo.delete_evidence(user_id, evidence_id)

    def inspect_evidence(
        self,
        user_id: UUID,
        skill_id: UUID,
        evidence_id: UUID,
        *,
        expected_files: list[str] | None = None,
        settings: Settings | None = None,
    ) -> SkillEvidenceResponse:
        if self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        existing = self._repo.get_evidence(user_id, evidence_id)
        if existing is None or existing.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Preuve de compétence introuvable.")
        if not existing.reference_url:
            raise AppError(
                422,
                "VALIDATION_ERROR",
                "Aucune URL externe associée à cette preuve pour inspection.",
            )

        result = inspect_github_evidence(
            existing.reference_url,
            expected_files=expected_files,
            settings=settings,
        )
        now = datetime.now(timezone.utc)
        next_status = (
            EvidenceVerificationStatus.approved
            if existing.is_locked and result.verified
            else result.status
        )
        saved = self._repo.save_evidence(
            existing.model_copy(
                update={
                    "verification_status": next_status,
                    "inspection_metadata": result.metadata,
                    "inspected_at": result.inspected_at,
                    "updated_at": now,
                }
            )
        )
        return _to_evidence_response(saved)

    def _resolve_learning_links(
        self,
        user_id: UUID,
        path_id: UUID | None,
        module_id: UUID | None,
        lesson_id: UUID | None,
    ) -> tuple[UUID | None, UUID | None, UUID | None, str | None]:
        if path_id is None and module_id is None and lesson_id is None:
            return None, None, None, None
        if self._learning_repo is None:
            raise AppError(422, "LEARNING_LINK_UNAVAILABLE", "Liaison pédagogique indisponible.")

        resolved_path_id = path_id
        resolved_module_id = module_id
        resolved_lesson_id = lesson_id
        lesson_title: str | None = None

        if resolved_path_id is not None:
            path = self._learning_repo.get_path(user_id, resolved_path_id)
            if path is None:
                raise AppError(404, "NOT_FOUND", "Parcours d’apprentissage associé introuvable.")

        if resolved_module_id is not None:
            mod = self._learning_repo.get_module(user_id, resolved_module_id)
            if mod is None:
                raise AppError(404, "NOT_FOUND", "Module d’apprentissage associé introuvable.")
            if resolved_path_id is not None and mod.path_id != resolved_path_id:
                raise AppError(
                    422,
                    "LEARNING_HIERARCHY_MISMATCH",
                    "Le module indiqué n’appartient pas au parcours sélectionné.",
                )
            resolved_path_id = mod.path_id

        if resolved_lesson_id is not None:
            lesson = self._learning_repo.get_lesson(user_id, resolved_lesson_id)
            if lesson is None:
                raise AppError(404, "NOT_FOUND", "Leçon associée introuvable.")
            lesson_title = lesson.title
            if resolved_module_id is not None and lesson.module_id != resolved_module_id:
                raise AppError(
                    422,
                    "LEARNING_HIERARCHY_MISMATCH",
                    "La leçon indiquée n’appartient pas au module sélectionné.",
                )
            resolved_module_id = lesson.module_id
            mod = self._learning_repo.get_module(user_id, lesson.module_id)
            if mod is not None:
                if resolved_path_id is not None and mod.path_id != resolved_path_id:
                    raise AppError(
                        422,
                        "LEARNING_HIERARCHY_MISMATCH",
                        "La leçon indiquée n’appartient pas au parcours sélectionné.",
                    )
                resolved_path_id = mod.path_id

        return resolved_path_id, resolved_module_id, resolved_lesson_id, lesson_title

    def list_assessments(
        self,
        user_id: UUID,
        *,
        skill_id: UUID | None = None,
        status: SkillAssessmentStatus | None = None,
        path_id: UUID | None = None,
        module_id: UUID | None = None,
        lesson_id: UUID | None = None,
    ) -> list[SkillAssessmentResponse]:
        if skill_id is not None and self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        records = self._repo.list_assessments(
            user_id,
            skill_id=skill_id,
            status=status,
            path_id=path_id,
            module_id=module_id,
            lesson_id=lesson_id,
        )
        records.sort(key=lambda item: item.created_at, reverse=True)
        return [_to_assessment_response(item) for item in records]

    def get_assessment(
        self,
        user_id: UUID,
        skill_id: UUID,
        assessment_id: UUID,
    ) -> SkillAssessmentResponse:
        if self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        assessment = self._repo.get_assessment(user_id, assessment_id)
        if assessment is None or assessment.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Évaluation de compétence introuvable.")
        return _to_assessment_response(assessment)

    def create_assessment(
        self,
        user_id: UUID,
        skill_id: UUID,
        payload: SkillAssessmentCreate,
        *,
        internal_prompt_title: str | None = None,
        internal_prompt_instructions: str | None = None,
    ) -> SkillAssessmentResponse:
        skill = self._repo.get_skill(user_id, skill_id)
        if skill is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")

        max_allowed_target = min(5, skill.current_level + 1)
        min_allowed_target = max(1, skill.current_level)
        target_level = (
            payload.target_level
            if payload.target_level is not None
            else max_allowed_target
        )
        if (
            target_level < min_allowed_target
            or target_level > 5
            or target_level > max_allowed_target
        ):
            raise AppError(
                422,
                "INVALID_TARGET_LEVEL",
                f"Progression palier par palier obligatoire : depuis le niveau {skill.current_level}/5, "
                f"le niveau visé doit être {max_allowed_target}/5.",
            )

        path_id, module_id, lesson_id, lesson_title = self._resolve_learning_links(
            user_id,
            payload.path_id,
            payload.module_id,
            payload.lesson_id,
        )

        prior = self._repo.list_assessments(user_id, skill_id=skill_id)
        prior.sort(key=lambda item: item.created_at, reverse=True)
        previous_gaps: list[str] = []
        for item in prior:
            if item.gaps_identified and (
                item.status == SkillAssessmentStatus.rejected or item.passed is False
            ):
                previous_gaps = list(item.gaps_identified)
                break

        generated = build_assessment_exercise(
            skill_name=skill.name,
            skill_domain=skill.domain,
            skill_description=skill.description,
            current_level=skill.current_level,
            target_level=target_level,
            assessment_type=payload.assessment_type,
            previous_gaps=previous_gaps,
            lesson_title=lesson_title,
        )

        # Les critères du référentiel sont figés et strictement contrôlés par le serveur
        frozen_rubric = [dict(item) for item in generated.criteria]
        now = datetime.now(timezone.utc)
        record = SkillAssessmentRecord(
            id=uuid4(),
            user_id=user_id,
            skill_id=skill_id,
            path_id=path_id,
            module_id=module_id,
            lesson_id=lesson_id,
            assessment_type=payload.assessment_type,
            starting_level=skill.current_level,
            target_level=target_level,
            proposed_level=None,
            status=SkillAssessmentStatus.pending,
            prompt_title=(internal_prompt_title or generated.prompt_title)[:180],
            prompt_instructions=(internal_prompt_instructions or generated.prompt_instructions)[:4000],
            hints=generated.hints,
            hints_revealed_count=0,
            criteria=frozen_rubric,
            rubric_version=generated.rubric_version,
            evaluator_version=EVALUATOR_VERSION,
            evaluation_mode=SkillEvaluationMode.automated,
            manual_review_required=False,
            rubric_snapshot=frozen_rubric,
            evidence_snapshot=[],
            evaluator_type=SkillEvaluatorType.pedagogical_engine,
            created_at=now,
            updated_at=now,
        )
        saved = self._repo.save_assessment(record)
        return _to_assessment_response(saved)

    def reveal_assessment_hint(
        self,
        user_id: UUID,
        skill_id: UUID,
        assessment_id: UUID,
    ) -> SkillAssessmentResponse:
        if self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        assessment = self._repo.get_assessment(user_id, assessment_id)
        if assessment is None or assessment.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Évaluation de compétence introuvable.")
        if assessment.status != SkillAssessmentStatus.pending:
            raise AppError(
                409,
                "INVALID_ASSESSMENT_STATE",
                "Les indices ne peuvent être demandés que tant que l’évaluation est en attente.",
            )

        next_count = min(len(assessment.hints), assessment.hints_revealed_count + 1)
        saved = self._repo.save_assessment(
            assessment.model_copy(
                update={
                    "hints_revealed_count": next_count,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
        )
        return _to_assessment_response(saved)

    def _validate_owned_evidence_list(
        self,
        user_id: UUID,
        skill_id: UUID,
        evidence_ids: list[UUID],
        *,
        exclude_assessment_id: UUID | None = None,
    ) -> tuple[list[SkillEvidenceRecord], bool]:
        approved_consumed_ids: set[str] = set()
        for existing_ass in self._repo.list_assessments(user_id, skill_id=skill_id):
            if exclude_assessment_id is not None and existing_ass.id == exclude_assessment_id:
                continue
            if existing_ass.status == SkillAssessmentStatus.approved:
                for raw_id in existing_ass.evidence_ids or []:
                    approved_consumed_ids.add(str(raw_id))

        records: list[SkillEvidenceRecord] = []
        has_unverified_url = False
        for ev_id in evidence_ids:
            ev = self._repo.get_evidence(user_id, ev_id)
            if ev is None:
                raise AppError(
                    404,
                    "EVIDENCE_NOT_FOUND",
                    "Preuve de compétence introuvable ou n’appartenant pas à l’utilisateur.",
                )
            if ev.skill_id != skill_id:
                raise AppError(
                    422,
                    "EVIDENCE_SKILL_MISMATCH",
                    "Une preuve associée appartient à une autre compétence.",
                )
            if str(ev.id) in approved_consumed_ids:
                raise AppError(
                    422,
                    "EVIDENCE_ALREADY_CONSUMED",
                    "Cette preuve a déjà servi à valider un palier précédent. Produisez une nouvelle preuve pour ce niveau.",
                )
            quality = validate_evidence_quality(
                ev.type,
                ev.description,
                ev.reference_url,
                ev.result,
                verification_status=ev.verification_status,
            )
            if not quality.admissible:
                raise AppError(
                    422,
                    "EVIDENCE_QUALITY_INSUFFICIENT",
                    quality.reason or "Preuve liée non admissible pour l’évaluation.",
                )
            if ev.reference_url and not quality.external_reference_verified:
                has_unverified_url = True
            records.append(ev)
        return records, has_unverified_url

    def submit_assessment(
        self,
        user_id: UUID,
        skill_id: UUID,
        assessment_id: UUID,
        payload: SkillAssessmentSubmit,
    ) -> SkillAssessmentResponse:
        if self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        assessment = self._repo.get_assessment(user_id, assessment_id)
        if assessment is None or assessment.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Évaluation de compétence introuvable.")
        if assessment.status != SkillAssessmentStatus.pending:
            raise AppError(
                409,
                "INVALID_ASSESSMENT_STATE",
                "Cette évaluation a déjà été soumise ou clôturée.",
            )

        dedup_ids: list[UUID] = []
        seen: set[UUID] = set()
        for item_id in payload.evidence_ids:
            if item_id not in seen:
                seen.add(item_id)
                dedup_ids.append(item_id)

        attached_records, evidence_has_unverified_url = self._validate_owned_evidence_list(
            user_id,
            skill_id,
            dedup_ids,
            exclude_assessment_id=assessment.id,
        )

        if payload.new_evidence is not None:
            created_ev = self.add_evidence(user_id, skill_id, payload.new_evidence)
            if created_ev.id not in seen:
                dedup_ids.append(created_ev.id)
                seen.add(created_ev.id)
                saved_ev_rec = self._repo.get_evidence(user_id, created_ev.id)
                if saved_ev_rec is not None:
                    attached_records.append(saved_ev_rec)
            if created_ev.reference_url and not created_ev.external_reference_verified:
                evidence_has_unverified_url = True

        now = datetime.now(timezone.utc)
        has_external_url = bool(payload.submission_reference_url) or evidence_has_unverified_url
        saved = self._repo.save_assessment(
            assessment.model_copy(
                update={
                    "status": SkillAssessmentStatus.submitted,
                    "submission_text": payload.submission_text,
                    "submission_code": payload.submission_code,
                    "submission_reference_url": payload.submission_reference_url,
                    "evidence_ids": [str(item) for item in dedup_ids],
                    "evidence_snapshot": _snapshot_evidence(attached_records),
                    "external_verification_warning": (
                        EXTERNAL_URL_DISCLAIMER if has_external_url else None
                    ),
                    "submitted_at": now,
                    "updated_at": now,
                }
            )
        )
        return _to_assessment_response(saved)

    def evaluate_assessment(
        self,
        user_id: UUID,
        skill_id: UUID,
        assessment_id: UUID,
        payload: SkillAssessmentEvaluate | None = None,
    ) -> SkillAssessmentResponse:
        _ = payload
        skill = self._repo.get_skill(user_id, skill_id)
        if skill is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        assessment = self._repo.get_assessment(user_id, assessment_id)
        if assessment is None or assessment.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Évaluation de compétence introuvable.")
        if assessment.status != SkillAssessmentStatus.submitted:
            raise AppError(
                409,
                "INVALID_ASSESSMENT_STATE",
                "L’évaluation doit d’abord être soumise avant d’être corrigée.",
            )

        evidence_uuids: list[UUID] = []
        for raw_id in assessment.evidence_ids:
            try:
                evidence_uuids.append(UUID(str(raw_id)))
            except ValueError:
                continue

        # Rechargement tolérant : si une preuve a été supprimée entre-temps, elle n'est pas comptée
        evidence_records: list[SkillEvidenceRecord] = []
        for ev_id in evidence_uuids:
            ev = self._repo.get_evidence(user_id, ev_id)
            if ev is not None and ev.skill_id == skill_id:
                evidence_records.append(ev)

        rubric_base = assessment.rubric_snapshot or assessment.criteria
        evaluated = evaluate_assessment_submission(
            skill_name=skill.name,
            skill_domain=skill.domain,
            starting_level=assessment.starting_level,
            target_level=assessment.target_level,
            assessment_type=assessment.assessment_type,
            submission_text=assessment.submission_text or "",
            submission_code=assessment.submission_code,
            submission_reference_url=assessment.submission_reference_url,
            evidence_records=evidence_records,
            base_criteria=rubric_base,
            rubric_version=assessment.rubric_version or RUBRIC_VERSION,
        )

        next_status = (
            SkillAssessmentStatus.needs_manual_review
            if evaluated.manual_review_required
            else SkillAssessmentStatus.evaluated
        )
        now = datetime.now(timezone.utc)
        saved = self._repo.save_assessment(
            assessment.model_copy(
                update={
                    "status": next_status,
                    "criteria": evaluated.criteria,
                    "rubric_version": evaluated.rubric_version,
                    "evaluator_version": evaluated.evaluator_version,
                    "evaluation_mode": evaluated.evaluation_mode,
                    "manual_review_required": evaluated.manual_review_required,
                    "evidence_snapshot": _snapshot_evidence(evidence_records),
                    "score": evaluated.score,
                    "passed": evaluated.passed,
                    "proposed_level": evaluated.proposed_level,
                    "feedback": evaluated.feedback,
                    "mastered_points": evaluated.mastered_points,
                    "gaps_identified": evaluated.gaps_identified,
                    "remediation_recommendation": evaluated.remediation_recommendation,
                    "external_verification_warning": evaluated.external_verification_warning,
                    "evaluator_type": SkillEvaluatorType.pedagogical_engine,
                    "evaluator_name": "Amireflow Grader (Server)",
                    "evaluated_at": now,
                    "updated_at": now,
                }
            )
        )
        return _to_assessment_response(saved)

    def validate_assessment(
        self,
        user_id: UUID,
        skill_id: UUID,
        assessment_id: UUID,
        decision: SkillAssessmentDecision | None = None,
    ) -> SkillAssessmentResponse:
        skill = self._repo.get_skill(user_id, skill_id)
        if skill is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        assessment = self._repo.get_assessment(user_id, assessment_id)
        if assessment is None or assessment.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Évaluation de compétence introuvable.")

        if assessment.status == SkillAssessmentStatus.approved:
            raise AppError(
                409,
                "ASSESSMENT_ALREADY_APPROVED",
                "Cette évaluation a déjà été validée et ne peut pas être réutilisée.",
            )
        if assessment.status == SkillAssessmentStatus.rejected:
            raise AppError(
                409,
                "ASSESSMENT_REJECTED",
                "Une évaluation rejetée ne peut pas faire progresser la compétence.",
            )
        if assessment.status == SkillAssessmentStatus.cancelled:
            raise AppError(
                409,
                "ASSESSMENT_CANCELLED",
                "Une évaluation annulée ne peut plus être validée.",
            )
        if (
            assessment.status == SkillAssessmentStatus.needs_manual_review
            or assessment.manual_review_required
        ):
            raise AppError(
                422,
                "MANUAL_REVIEW_REQUIRED",
                "Cette évaluation nécessite une revue manuelle ou une inspection vérifiée avant validation.",
            )
        if assessment.status != SkillAssessmentStatus.evaluated:
            raise AppError(
                409,
                "ASSESSMENT_NOT_EVALUATED",
                "L’évaluation doit être soumise puis évaluée avant validation.",
            )

        # Revalidation stricte côté serveur au moment de l'approbation
        if not (assessment.submission_text and assessment.submission_text.strip()):
            raise AppError(
                422,
                "ASSESSMENT_SUBMISSION_MISSING",
                "Impossible de valider une évaluation sans production soumise.",
            )

        threshold = pass_threshold_for_level(assessment.target_level)
        if (
            assessment.passed is not True
            or assessment.score is None
            or assessment.score < threshold
        ):
            raise AppError(
                422,
                "ASSESSMENT_RESULT_INSUFFICIENT",
                f"Résultat insuffisant ({assessment.score or 0}/100, seuil {threshold}/100) : "
                "progression refusée. Réalisez un exercice correctif.",
            )

        if not assessment.evidence_ids:
            raise AppError(
                422,
                "ASSESSMENT_EVIDENCE_REQUIRED",
                "Progression refusée : au moins une preuve concrète admissible est requise.",
            )

        evidence_uuids: list[UUID] = []
        for raw_id in assessment.evidence_ids:
            try:
                evidence_uuids.append(UUID(str(raw_id)))
            except ValueError as exc:
                raise AppError(
                    422,
                    "ASSESSMENT_EVIDENCE_REQUIRED",
                    "Référence de preuve invalide.",
                ) from exc

        admissible_records, _ = self._validate_owned_evidence_list(
            user_id,
            skill_id,
            evidence_uuids,
            exclude_assessment_id=assessment.id,
        )
        if not admissible_records:
            raise AppError(
                422,
                "ASSESSMENT_EVIDENCE_REQUIRED",
                "Aucune preuve admissible n’est associée à cette évaluation.",
            )

        max_allowed = min(5, skill.current_level + 1)
        if (
            assessment.proposed_level is None
            or assessment.proposed_level < 0
            or assessment.proposed_level > 5
            or assessment.proposed_level > assessment.target_level
            or assessment.proposed_level > max_allowed
        ):
            raise AppError(
                422,
                "INVALID_PROPOSED_LEVEL",
                "Le niveau proposé pour cette évaluation est invalide.",
            )

        new_level = max(skill.current_level, assessment.proposed_level)
        applied_delta = new_level - skill.current_level
        now = datetime.now(timezone.utc)

        updated_assessment = assessment.model_copy(
            update={
                "status": SkillAssessmentStatus.approved,
                "decision_reason": (
                    decision.reason
                    if decision and decision.reason
                    else f"Progression validée de {skill.current_level}/5 à {new_level}/5."
                ),
                "applied_level_delta": applied_delta,
                "validated_at": now,
                "updated_at": now,
            }
        )
        updated_skill = skill.model_copy(
            update={
                "current_level": new_level,
                "last_assessed_at": now,
                "updated_at": now,
            }
        )
        saved_assessment, _ = self._repo.approve_assessment_and_update_skill(
            updated_assessment,
            updated_skill,
            consumed_evidence_ids=evidence_uuids,
        )
        return _to_assessment_response(saved_assessment)

    def reject_assessment(
        self,
        user_id: UUID,
        skill_id: UUID,
        assessment_id: UUID,
        decision: SkillAssessmentDecision | None = None,
    ) -> SkillAssessmentResponse:
        skill = self._repo.get_skill(user_id, skill_id)
        if skill is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        assessment = self._repo.get_assessment(user_id, assessment_id)
        if assessment is None or assessment.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Évaluation de compétence introuvable.")
        if assessment.status not in (
            SkillAssessmentStatus.submitted,
            SkillAssessmentStatus.evaluated,
            SkillAssessmentStatus.needs_manual_review,
        ):
            raise AppError(
                409,
                "INVALID_ASSESSMENT_STATE",
                "Seule une évaluation soumise ou évaluée peut être rejetée.",
            )

        now = datetime.now(timezone.utc)
        saved = self._repo.save_assessment(
            assessment.model_copy(
                update={
                    "status": SkillAssessmentStatus.rejected,
                    "proposed_level": skill.current_level,
                    "applied_level_delta": 0,
                    "decision_reason": (
                        decision.reason
                        if decision and decision.reason
                        else "Évaluation non validée : niveau conservé."
                    ),
                    "validated_at": now,
                    "updated_at": now,
                }
            )
        )
        return _to_assessment_response(saved)

    def cancel_assessment(
        self,
        user_id: UUID,
        skill_id: UUID,
        assessment_id: UUID,
        decision: SkillAssessmentDecision | None = None,
    ) -> SkillAssessmentResponse:
        if self._repo.get_skill(user_id, skill_id) is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")
        assessment = self._repo.get_assessment(user_id, assessment_id)
        if assessment is None or assessment.skill_id != skill_id:
            raise AppError(404, "NOT_FOUND", "Évaluation de compétence introuvable.")
        if assessment.status not in (
            SkillAssessmentStatus.pending,
            SkillAssessmentStatus.submitted,
            SkillAssessmentStatus.evaluated,
            SkillAssessmentStatus.needs_manual_review,
        ):
            raise AppError(
                409,
                "INVALID_ASSESSMENT_STATE",
                "Cette évaluation est déjà clôturée.",
            )

        now = datetime.now(timezone.utc)
        saved = self._repo.save_assessment(
            assessment.model_copy(
                update={
                    "status": SkillAssessmentStatus.cancelled,
                    "applied_level_delta": 0,
                    "decision_reason": (
                        decision.reason
                        if decision and decision.reason
                        else "Évaluation annulée par l’utilisateur."
                    ),
                    "updated_at": now,
                }
            )
        )
        return _to_assessment_response(saved)
