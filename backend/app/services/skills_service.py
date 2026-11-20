from datetime import datetime, timezone
from uuid import UUID, uuid4
from app.core.errors import AppError
from app.repositories.learning_sql import (
    SkillAssessmentRecord,
    SkillEvidenceRecord,
    SkillRecord,
    SqlLearningRepository,
    SqlSkillRepository,
)
from app.schemas.common import (
    SkillAssessmentStatus,
    SkillAssessmentType,
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
    EXTERNAL_URL_DISCLAIMER,
    build_assessment_exercise,
    evaluate_assessment_submission,
    pass_threshold_for_level,
    validate_evidence_quality,
)


def _to_evidence_response(record: SkillEvidenceRecord) -> SkillEvidenceResponse:
    quality = validate_evidence_quality(
        record.type,
        record.description,
        record.reference_url,
        record.result,
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
            observed_at=payload.observed_at or now,
            created_at=now,
            updated_at=now,
        )
        saved = self._repo.save_evidence(record)
        return _to_evidence_response(saved)

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
        self._repo.delete_evidence(user_id, evidence_id)

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
    ) -> SkillAssessmentResponse:
        skill = self._repo.get_skill(user_id, skill_id)
        if skill is None:
            raise AppError(404, "NOT_FOUND", "Compétence introuvable.")

        target_level = (
            payload.target_level
            if payload.target_level is not None
            else min(5, max(1, skill.current_level + 1))
        )
        if target_level < max(1, skill.current_level) or target_level > 5:
            raise AppError(
                422,
                "INVALID_TARGET_LEVEL",
                "Le niveau visé doit être au moins égal au niveau actuel vérifié (entre 1 et 5).",
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

        hints = (
            [h.strip() for h in payload.hints if h and h.strip()][:5]
            if payload.hints
            else generated.hints
        )
        criteria = (
            [c.model_dump() for c in payload.criteria]
            if payload.criteria
            else generated.criteria
        )

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
            prompt_title=payload.prompt_title or generated.prompt_title,
            prompt_instructions=payload.prompt_instructions or generated.prompt_instructions,
            hints=hints,
            hints_revealed_count=0,
            criteria=criteria,
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
    ) -> tuple[list[SkillEvidenceRecord], bool]:
        records: list[SkillEvidenceRecord] = []
        has_url = False
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
            quality = validate_evidence_quality(
                ev.type, ev.description, ev.reference_url, ev.result
            )
            if not quality.admissible:
                raise AppError(
                    422,
                    "EVIDENCE_QUALITY_INSUFFICIENT",
                    quality.reason or "Preuve liée non admissible pour l’évaluation.",
                )
            if ev.reference_url:
                has_url = True
            records.append(ev)
        return records, has_url

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

        _, evidence_has_url = self._validate_owned_evidence_list(user_id, skill_id, dedup_ids)

        if payload.new_evidence is not None:
            created_ev = self.add_evidence(user_id, skill_id, payload.new_evidence)
            if created_ev.id not in seen:
                dedup_ids.append(created_ev.id)
                seen.add(created_ev.id)
            if created_ev.reference_url:
                evidence_has_url = True

        now = datetime.now(timezone.utc)
        has_external_url = bool(payload.submission_reference_url) or evidence_has_url
        saved = self._repo.save_assessment(
            assessment.model_copy(
                update={
                    "status": SkillAssessmentStatus.submitted,
                    "submission_text": payload.submission_text,
                    "submission_code": payload.submission_code,
                    "submission_reference_url": payload.submission_reference_url,
                    "evidence_ids": [str(item) for item in dedup_ids],
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

        overrides = (
            [item.model_dump() for item in payload.criteria_evaluations]
            if payload and payload.criteria_evaluations
            else None
        )

        evaluated = evaluate_assessment_submission(
            skill_name=skill.name,
            skill_domain=skill.domain,
            starting_level=skill.current_level,
            target_level=assessment.target_level,
            assessment_type=assessment.assessment_type,
            submission_text=assessment.submission_text or "",
            submission_code=assessment.submission_code,
            submission_reference_url=assessment.submission_reference_url,
            evidence_records=evidence_records,
            base_criteria=assessment.criteria,
            criteria_overrides=overrides,
            explicit_feedback=payload.feedback if payload else None,
            explicit_mastered=payload.mastered_points if payload else None,
            explicit_gaps=payload.gaps_identified if payload else None,
            explicit_remediation=payload.remediation_recommendation if payload else None,
        )

        now = datetime.now(timezone.utc)
        saved = self._repo.save_assessment(
            assessment.model_copy(
                update={
                    "status": SkillAssessmentStatus.evaluated,
                    "criteria": evaluated.criteria,
                    "score": evaluated.score,
                    "passed": evaluated.passed,
                    "proposed_level": evaluated.proposed_level,
                    "feedback": evaluated.feedback,
                    "mastered_points": evaluated.mastered_points,
                    "gaps_identified": evaluated.gaps_identified,
                    "remediation_recommendation": evaluated.remediation_recommendation,
                    "external_verification_warning": evaluated.external_verification_warning,
                    "evaluator_type": (
                        payload.evaluator_type
                        if payload
                        else SkillEvaluatorType.pedagogical_engine
                    ),
                    "evaluator_name": payload.evaluator_name if payload else "Amireflow Grader",
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
            user_id, skill_id, evidence_uuids
        )
        if not admissible_records:
            raise AppError(
                422,
                "ASSESSMENT_EVIDENCE_REQUIRED",
                "Aucune preuve admissible n’est associée à cette évaluation.",
            )

        if (
            assessment.proposed_level is None
            or assessment.proposed_level < 0
            or assessment.proposed_level > 5
            or assessment.proposed_level > assessment.target_level
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
            updated_assessment, updated_skill
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
