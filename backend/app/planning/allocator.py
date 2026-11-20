from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.planning.availability import resolve_zoneinfo
from app.planning.collector import PlanningContextSnapshot
from app.planning.content_resolver import SessionContentResolver
from app.schemas.planning import (
    AvailabilityComputationResponse,
    LearningPriorityItem,
    PlanArbitrageItem,
    PlanLoadSummary,
    PlanMissingInfoItem,
    PlannedSessionProposal,
    SlotCategory,
    TimeSlotWindow,
)


@dataclass
class _MicroBlock:
    slot_id: str
    window: TimeSlotWindow
    start_utc: datetime
    end_utc: datetime
    duration_minutes: int


class WeeklyPlanAllocator:
    """Distribue de façon réaliste, équilibrée et explicable les priorités dans les créneaux disponibles."""

    def __init__(self, content_resolver: SessionContentResolver) -> None:
        self._content_resolver = content_resolver

    def allocate(
        self,
        *,
        snapshot: PlanningContextSnapshot,
        availability: AvailabilityComputationResponse,
        priorities: list[LearningPriorityItem],
        weekly_hours_override: float | None = None,
        daily_max_minutes: int | None = None,
        preferred_session_minutes: int | None = None,
        min_session_minutes: int = 30,
        break_minutes: int = 10,
    ) -> tuple[
        list[PlannedSessionProposal],
        list[PlanArbitrageItem],
        PlanLoadSummary,
        list[PlanMissingInfoItem],
        list[str],
    ]:
        tz, _ = resolve_zoneinfo(availability.timezone)
        history = snapshot.work_history

        prefs_merged: dict[str, object] = {}
        if snapshot.profile and isinstance(snapshot.profile.preferences, dict):
            prefs_merged.update(snapshot.profile.preferences)
            if isinstance(snapshot.profile.preferences.get("availability"), dict):
                prefs_merged.update(snapshot.profile.preferences["availability"])  # type: ignore[arg-type]
        if snapshot.ai_memory and isinstance(snapshot.ai_memory.availability_preferences, dict):
            prefs_merged.update(snapshot.ai_memory.availability_preferences)

        pref_session_raw = prefs_merged.get("preferred_session_minutes")
        pref_session_min = (
            int(pref_session_raw)
            if isinstance(pref_session_raw, (int, float)) and 30 <= int(pref_session_raw) <= 150
            else None
        )
        pref_daily_raw = prefs_merged.get("max_daily_study_minutes")
        pref_daily_cap = (
            int(pref_daily_raw)
            if isinstance(pref_daily_raw, (int, float)) and 30 <= int(pref_daily_raw) <= 600
            else None
        )

        # Durée de séance réaliste selon mémoire, préférences, demande et historique de complétion
        base_session_min = (
            preferred_session_minutes
            or pref_session_min
            or (snapshot.ai_memory.default_session_minutes if snapshot.ai_memory else None)
            or history.avg_session_minutes
            or 60
        )
        if history.completion_rate < 0.70 and preferred_session_minutes is None:
            base_session_min = max(min_session_minutes, min(base_session_min, 50))
        base_session_min = max(min_session_minutes, min(base_session_min, 150))

        # Plafonds journalier et hebdomadaire anti-surcharge
        if daily_max_minutes is not None:
            daily_cap = daily_max_minutes
        elif pref_daily_cap is not None:
            daily_cap = min(pref_daily_cap, 180) if history.completion_rate < 0.65 else pref_daily_cap
        else:
            daily_cap = 180 if history.completion_rate < 0.65 else 240

        memory_weekly_hours = (
            snapshot.ai_memory.weekly_study_hours
            if snapshot.ai_memory and snapshot.ai_memory.weekly_study_hours is not None
            else None
        )
        if weekly_hours_override is not None:
            weekly_cap = max(30, int(round(weekly_hours_override * 60)))
        elif memory_weekly_hours is not None:
            weekly_cap = max(30, int(memory_weekly_hours * 60))
        else:
            weekly_cap = min(max(availability.total_allocatable_minutes, 180), 600)

        blocks = self._slice_allocatable_blocks(
            availability.allocatable_slots,
            session_minutes=base_session_min,
            min_session_minutes=min_session_minutes,
            break_minutes=break_minutes,
            tz=tz,
        )

        # Compteurs d'allocation & diversité cognitive
        daily_minutes: dict[str, int] = {}
        day_subjects: dict[str, list[str]] = {}
        weekly_planned_minutes = 0
        used_block_indices: set[int] = set()

        planned_sessions: list[PlannedSessionProposal] = []
        arbitrage_items: list[PlanArbitrageItem] = []
        warnings: list[str] = []

        # Pré-résoudre le contenu pédagogique de chaque priorité
        resolved_by_key = {
            idx: self._content_resolver.resolve_for_priority(snapshot, item)
            for idx, item in enumerate(priorities)
        }

        # Demande restante par priorité (par ordre décroissant de score, tout en répartissant en round-robin pondéré pour la diversité)
        remaining_need: dict[int, int] = {
            idx: max(min_session_minutes, item.recommended_minutes)
            for idx, item in enumerate(priorities)
        }

        # Passes round-robin pondérées : diversité entre objectifs tout en respectant les priorités top
        ordered_indices = list(range(len(priorities)))
        max_rounds = max(6, len(blocks) + 1)
        for _round in range(max_rounds):
            made_progress = False
            for idx in ordered_indices:
                item = priorities[idx]
                need = remaining_need[idx]
                if need < min_session_minutes:
                    continue
                if weekly_planned_minutes + min_session_minutes > weekly_cap:
                    continue

                is_imminent_exam = (
                    item.source_type == "exam_revision"
                    and item.deadline_at is not None
                    and (item.deadline_at - snapshot.collected_at).total_seconds() <= 72 * 3600
                )
                subj_key = item.subject.strip().lower()

                chosen_block_idx: int | None = None
                for b_idx, blk in enumerate(blocks):
                    if b_idx in used_block_indices:
                        continue
                    if item.deadline_at is not None and blk.start_utc >= item.deadline_at:
                        # Ne jamais placer une révision d'examen APRÈS l'examen !
                        if item.source_type == "exam_revision":
                            continue
                    d_key = blk.window.local_date
                    cur_day_mins = daily_minutes.get(d_key, 0)
                    if cur_day_mins + min_session_minutes > daily_cap:
                        continue
                    # Éviter >2 séances du même sujet le même jour sauf examen imminent
                    same_subj_count = day_subjects.get(d_key, []).count(subj_key)
                    if same_subj_count >= 2 and not is_imminent_exam:
                        continue
                    chosen_block_idx = b_idx
                    break

                if chosen_block_idx is None:
                    continue

                blk = blocks[chosen_block_idx]
                allowed_left = min(
                    blk.duration_minutes,
                    daily_cap - daily_minutes.get(blk.window.local_date, 0),
                    weekly_cap - weekly_planned_minutes,
                )
                if allowed_left < min_session_minutes:
                    continue

                alloc_mins = min(allowed_left, max(min_session_minutes, min(need, base_session_min)))
                if alloc_mins < min_session_minutes:
                    continue

                used_block_indices.add(chosen_block_idx)
                s_utc = blk.start_utc
                e_utc = s_utc + timedelta(minutes=alloc_mins)

                daily_minutes[blk.window.local_date] = (
                    daily_minutes.get(blk.window.local_date, 0) + alloc_mins
                )
                day_subjects.setdefault(blk.window.local_date, []).append(subj_key)
                weekly_planned_minutes += alloc_mins
                remaining_need[idx] = max(0, remaining_need[idx] - alloc_mins)
                made_progress = True

                pedagogical = resolved_by_key[idx]
                slot_type_label = (
                    "Créneau confirmé"
                    if blk.window.category == SlotCategory.confirmed_availability
                    else "Créneau libre potentiel"
                )
                reason_head = item.reasons[0] if item.reasons else "Priorité calculée."
                rationale = (
                    f"{reason_head} {slot_type_label} ({blk.window.start_local}–{e_utc.astimezone(tz).strftime('%H:%M')}) "
                    f"sans conflit. Étape : {pedagogical.next_step_summary}"
                )

                planned_sessions.append(
                    PlannedSessionProposal(
                        slot_id=blk.slot_id,
                        title=self._session_title(item, pedagogical),
                        session_type=pedagogical.recommended_session_type,
                        starts_at=s_utc,
                        ends_at=e_utc,
                        duration_minutes=alloc_mins,
                        priority_source_type=item.source_type,
                        priority_source_id=item.source_id,
                        priority_score=item.score,
                        subject=item.subject,
                        task_id=self._uuid_or_none(item.source_id) if item.source_type == "task" else None,
                        project_id=self._uuid_or_none(item.source_id) if item.source_type == "project" else None,
                        skill_id=pedagogical.skill_id,
                        course_id=pedagogical.course_id,
                        lesson_id=pedagogical.lesson_id,
                        module_id=pedagogical.module_id,
                        slot_category=blk.window.category,
                        rationale=rationale,
                        pedagogical_content=pedagogical,
                    )
                )
            if not made_progress:
                break

        planned_sessions.sort(key=lambda s: s.starts_at)

        # Arbitrage explicite pour les items incomplets / reportés
        for idx, item in enumerate(priorities):
            needed = max(min_session_minutes, item.recommended_minutes)
            unscheduled = remaining_need[idx]
            scheduled = max(0, needed - unscheduled)
            if unscheduled >= min_session_minutes:
                reason = (
                    "Reporté faute de capacité avant l'échéance ou sous le plafond hebdomadaire/journalier protecteur."
                    if scheduled == 0
                    else "Temps partiellement alloué ; le reliquat est reporté pour éviter toute surcharge."
                )
                arbitrage_items.append(
                    PlanArbitrageItem(
                        source_type=item.source_type,
                        source_id=item.source_id,
                        title=item.title,
                        needed_minutes=needed,
                        scheduled_minutes=scheduled,
                        postponed_minutes=unscheduled,
                        reason=reason,
                        deadline_at=item.deadline_at,
                    )
                )

        if arbitrage_items:
            warnings.append(
                f"{len(arbitrage_items)} élément(s) ont fait l'objet d'un arbitrage afin de préserver votre équilibre de charge ({weekly_cap} min max/semaine)."
            )
        if availability.total_confirmed_minutes == 0 and planned_sessions:
            warnings.append(
                "Les créneaux retenus reposent sur vos plages potentielles (non encore confirmées explicitement)."
            )

        overloaded_days = [day for day, mins in daily_minutes.items() if mins > daily_cap]
        recovery_minutes = sum(w.duration_minutes for w in availability.recovery_slots)
        load_summary = PlanLoadSummary(
            daily_minutes=daily_minutes,
            daily_cap_minutes=daily_cap,
            weekly_planned_minutes=weekly_planned_minutes,
            weekly_cap_minutes=weekly_cap,
            recovery_preserved_minutes=recovery_minutes,
            overloaded_days=overloaded_days,
            is_overloaded=len(overloaded_days) > 0,
        )

        missing_info: list[PlanMissingInfoItem] = []
        if availability.total_confirmed_minutes == 0:
            missing_info.append(
                PlanMissingInfoItem(
                    field="confirmed_availability",
                    question="Quels créneaux de la semaine souhaitez-vous consacrer en priorité à votre apprentissage ?",
                    why="Distinguer les créneaux libres potentiels de vos disponibilités réellement confirmées.",
                )
            )
        if memory_weekly_hours is None and weekly_hours_override is None:
            missing_info.append(
                PlanMissingInfoItem(
                    field="weekly_study_hours",
                    question="Combien d'heures par semaine souhaitez-vous investir au total ?",
                    why="Calibrer le plafond hebdomadaire pour éviter toute surcharge.",
                )
            )

        return planned_sessions, arbitrage_items, load_summary, missing_info, warnings

    def _slice_allocatable_blocks(
        self,
        slots: list[TimeSlotWindow],
        *,
        session_minutes: int,
        min_session_minutes: int,
        break_minutes: int,
        tz: ZoneInfo,
    ) -> list[_MicroBlock]:
        blocks: list[_MicroBlock] = []
        counter = 1
        for win in slots:
            cursor = win.start_utc
            while cursor < win.end_utc:
                left = int((win.end_utc - cursor).total_seconds() // 60)
                if left < min_session_minutes:
                    break
                dur = min(session_minutes, left)
                if left - dur < min_session_minutes and left <= session_minutes + 20:
                    # Absorbe un petit reliquat (< min_session) plutôt que le perdre
                    dur = left
                end_utc = cursor + timedelta(minutes=dur)
                loc_s = cursor.astimezone(tz)
                loc_e = end_utc.astimezone(tz)
                blocks.append(
                    _MicroBlock(
                        slot_id=f"slot-{counter}",
                        window=TimeSlotWindow(
                            start_utc=cursor,
                            end_utc=end_utc,
                            local_date=loc_s.date().isoformat(),
                            start_local=loc_s.strftime("%H:%M"),
                            end_local=loc_e.strftime("%H:%M"),
                            duration_minutes=dur,
                            category=win.category,
                            label=win.label,
                            source_id=win.source_id,
                        ),
                        start_utc=cursor,
                        end_utc=end_utc,
                        duration_minutes=dur,
                    )
                )
                counter += 1
                cursor = end_utc + timedelta(minutes=break_minutes)
        return blocks

    def _session_title(self, item: LearningPriorityItem, ped) -> str:
        if ped.remediation_needed and ped.lesson_title:
            return f"Remédiation : {ped.lesson_title} ({item.subject})"[:140]
        if ped.lesson_title:
            return f"{item.subject} — {ped.lesson_title}"[:140]
        return item.title[:140]

    def _uuid_or_none(self, raw: str | None):
        if not raw:
            return None
        from uuid import UUID

        try:
            return UUID(str(raw))
        except ValueError:
            return None
