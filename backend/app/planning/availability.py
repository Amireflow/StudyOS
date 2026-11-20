from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from app.planning.collector import PlanningContextSnapshot, _ensure_utc
from app.repositories.planning_sql import UserAvailabilityRuleRecord
from app.schemas.planning import (
    AvailabilityComputationResponse,
    AvailabilityRecurrence,
    AvailabilityRuleType,
    SlotCategory,
    TimeSlotWindow,
)

DAY_NAMES_FR = {
    0: "lundi",
    1: "mardi",
    2: "mercredi",
    3: "jeudi",
    4: "vendredi",
    5: "samedi",
    6: "dimanche",
}

FR_DAY_NAME_TO_INT = {
    "lundi": 0,
    "monday": 0,
    "mardi": 1,
    "tuesday": 1,
    "mercredi": 2,
    "wednesday": 2,
    "jeudi": 3,
    "thursday": 3,
    "vendredi": 4,
    "friday": 4,
    "samedi": 5,
    "saturday": 5,
    "dimanche": 6,
    "sunday": 6,
}


def resolve_zoneinfo(timezone_name: str | None) -> tuple[ZoneInfo, str]:
    candidate = (timezone_name or "Europe/Paris").strip() or "Europe/Paris"
    try:
        return ZoneInfo(candidate), candidate
    except ZoneInfoNotFoundError:
        return ZoneInfo("Europe/Paris"), "Europe/Paris"


def _parse_hhmm(raw: str | None, default_time: time) -> time:
    if not raw:
        return default_time
    parts = raw.strip().split(":")
    if len(parts) != 2:
        return default_time
    try:
        return time(hour=int(parts[0]), minute=int(parts[1]))
    except ValueError:
        return default_time


def _merge_intervals(
    intervals: list[tuple[datetime, datetime, str, str | None]],
) -> list[tuple[datetime, datetime, str, str | None]]:
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda item: (item[0], item[1]))
    merged: list[tuple[datetime, datetime, str, str | None]] = [ordered[0]]
    for start, end, label, source_id in ordered[1:]:
        prev_start, prev_end, prev_label, prev_source = merged[-1]
        if start <= prev_end:
            new_label = prev_label if prev_label == label else f"{prev_label} / {label}".strip(" /")
            merged[-1] = (prev_start, max(prev_end, end), new_label, prev_source or source_id)
        else:
            merged.append((start, end, label, source_id))
    return merged


def _subtract_blockers(
    base_intervals: list[tuple[datetime, datetime, str, str | None]],
    blockers: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime, str, str | None]]:
    if not base_intervals or not blockers:
        return base_intervals
    ordered_blockers = sorted((b[0], b[1]) for b in blockers if b[1] > b[0])
    result: list[tuple[datetime, datetime, str, str | None]] = []
    for base_start, base_end, label, src_id in base_intervals:
        fragments = [(base_start, base_end)]
        for blk_start, blk_end in ordered_blockers:
            next_fragments: list[tuple[datetime, datetime]] = []
            for frag_start, frag_end in fragments:
                if blk_end <= frag_start or blk_start >= frag_end:
                    next_fragments.append((frag_start, frag_end))
                else:
                    if blk_start > frag_start:
                        next_fragments.append((frag_start, blk_start))
                    if blk_end < frag_end:
                        next_fragments.append((blk_end, frag_end))
            fragments = next_fragments
            if not fragments:
                break
        for frag_start, frag_end in fragments:
            if frag_end > frag_start:
                result.append((frag_start, frag_end, label, src_id))
    return result


class AvailabilityEngine:
    """Calcule de façon déterministe les 5 catégories de créneaux en UTC/fuseau local."""

    def compute(
        self,
        snapshot: PlanningContextSnapshot,
        *,
        range_start: datetime | None = None,
        horizon_days: int = 7,
        timezone_name: str | None = None,
        min_session_minutes: int = 30,
        buffer_minutes: int = 10,
        include_potential: bool = True,
        excluded_event_ids: set[str] | None = None,
    ) -> AvailabilityComputationResponse:
        tz, tz_label = resolve_zoneinfo(timezone_name or snapshot.timezone)
        anchor_utc = _ensure_utc(range_start) or snapshot.collected_at
        anchor_local = anchor_utc.astimezone(tz)
        first_day = anchor_local.date()

        horizon_start_local = datetime.combine(first_day, time(0, 0), tzinfo=tz)
        horizon_end_local = datetime.combine(
            first_day + timedelta(days=horizon_days), time(0, 0), tzinfo=tz
        )
        horizon_start_utc = horizon_start_local.astimezone(timezone.utc)
        horizon_end_utc = horizon_end_local.astimezone(timezone.utc)
        effective_min_start = max(anchor_utc, horizon_start_utc)

        # Extraire préférences mémoire/profil
        rest_days, preferred_hours, memory_unavail = self._extract_profile_preferences(snapshot)

        # 1. Engagements fixes
        fixed_windows: list[TimeSlotWindow] = []
        fixed_blockers: list[tuple[datetime, datetime]] = []
        excluded = excluded_event_ids or set()
        for ev in snapshot.fixed_events:
            if str(ev.id) in excluded:
                continue
            ev_s = _ensure_utc(ev.starts_at)
            ev_e = _ensure_utc(ev.ends_at)
            if ev_s is None or ev_e is None or ev_e <= horizon_start_utc or ev_s >= horizon_end_utc:
                continue
            clipped_s = max(ev_s, horizon_start_utc)
            clipped_e = min(ev_e, horizon_end_utc)
            fixed_windows.extend(
                self._split_utc_interval_by_local_day(
                    clipped_s, clipped_e, tz, SlotCategory.fixed_commitment, ev.title, str(ev.id)
                )
            )
            blk_s = max(horizon_start_utc, clipped_s - timedelta(minutes=buffer_minutes))
            blk_e = min(horizon_end_utc, clipped_e + timedelta(minutes=buffer_minutes))
            fixed_blockers.append((blk_s, blk_e))

        # Aussi inclure les séances planifiées déjà conservées si keep_existing_applied
        for ev in snapshot.planned_learning_events:
            if str(ev.id) in excluded:
                continue
            ev_s = _ensure_utc(ev.starts_at)
            ev_e = _ensure_utc(ev.ends_at)
            if ev_s is None or ev_e is None or ev_e <= horizon_start_utc or ev_s >= horizon_end_utc:
                continue
            clipped_s = max(ev_s, horizon_start_utc)
            clipped_e = min(ev_e, horizon_end_utc)
            fixed_windows.extend(
                self._split_utc_interval_by_local_day(
                    clipped_s, clipped_e, tz, SlotCategory.fixed_commitment, ev.title, str(ev.id)
                )
            )
            fixed_blockers.append((clipped_s, clipped_e))

        # 2. Indisponibilités personnelles + 5. Temps de récupération + 3. Disponibilités confirmées
        unavail_raw: list[tuple[datetime, datetime, str, str | None]] = []
        recovery_raw: list[tuple[datetime, datetime, str, str | None]] = []
        confirmed_raw: list[tuple[datetime, datetime, str, str | None]] = []

        for rule in snapshot.availability_rules:
            expanded = self._expand_rule(rule, first_day, horizon_days, tz)
            for iv_s, iv_e in expanded:
                clipped_s = max(iv_s, horizon_start_utc)
                clipped_e = min(iv_e, horizon_end_utc)
                if clipped_e <= clipped_s:
                    continue
                if rule.rule_type == AvailabilityRuleType.personal_unavailability:
                    unavail_raw.append((clipped_s, clipped_e, rule.label, str(rule.id)))
                elif rule.rule_type == AvailabilityRuleType.recovery_time:
                    recovery_raw.append((clipped_s, clipped_e, rule.label, str(rule.id)))
                elif rule.rule_type == AvailabilityRuleType.confirmed_availability:
                    confirmed_raw.append((clipped_s, clipped_e, rule.label, str(rule.id)))

        # Jours de repos & indisponibilités déclarés en mémoire/profil
        for offset in range(horizon_days):
            local_day = first_day + timedelta(days=offset)
            day_s_utc = datetime.combine(local_day, time(0, 0), tzinfo=tz).astimezone(timezone.utc)
            day_e_utc = datetime.combine(
                local_day + timedelta(days=1), time(0, 0), tzinfo=tz
            ).astimezone(timezone.utc)
            if local_day.weekday() in rest_days:
                recovery_raw.append(
                    (day_s_utc, day_e_utc, f"Jour de récupération ({DAY_NAMES_FR[local_day.weekday()]})", None)
                )
            for mem_dow, s_t, e_t, label in memory_unavail:
                if mem_dow is None or mem_dow == local_day.weekday():
                    iv_s, iv_e = self._local_window_to_utc(local_day, s_t, e_t, tz)
                    if iv_e > horizon_start_utc and iv_s < horizon_end_utc:
                        unavail_raw.append((max(iv_s, horizon_start_utc), min(iv_e, horizon_end_utc), label, None))

        # Si préférence horaire explicite (ex: soir / matin) dans mémoire -> ajoute fenêtres potentielles/confirmées ciblées
        # Note: une préférence textuelle reste potentielle tant qu'il n'y a pas une règle explicite confirmée,
        # sauf si explicit_preferred_windows fourni.
        unavail_merged = _merge_intervals(unavail_raw)
        recovery_merged = _merge_intervals(recovery_raw)

        # Bloqueurs totaux empêchant toute planification
        hard_blockers = (
            fixed_blockers
            + [(s, e) for s, e, _, _ in unavail_merged]
            + [(s, e) for s, e, _, _ in recovery_merged]
            + [(horizon_start_utc, effective_min_start)]
        )

        # 3. Créneaux confirmés nets (après soustraction strictes des fixe/indispos/récup/passé)
        confirmed_net = _subtract_blockers(_merge_intervals(confirmed_raw), hard_blockers)
        confirmed_windows: list[TimeSlotWindow] = []
        for s_u, e_u, lbl, src_id in confirmed_net:
            if int((e_u - s_u).total_seconds() // 60) >= min_session_minutes:
                confirmed_windows.extend(
                    self._split_utc_interval_by_local_day(
                        s_u, e_u, tz, SlotCategory.confirmed_availability, lbl, src_id
                    )
                )

        # 4. Créneaux potentiels (08:00..22:00 heure locale moins bloqueurs ET moins créneaux confirmés)
        potential_windows: list[TimeSlotWindow] = []
        if include_potential:
            day_start_t, day_end_t = preferred_hours
            potential_base: list[tuple[datetime, datetime, str, str | None]] = []
            for offset in range(horizon_days):
                local_day = first_day + timedelta(days=offset)
                iv_s, iv_e = self._local_window_to_utc(local_day, day_start_t, day_end_t, tz)
                potential_base.append((iv_s, iv_e, "Créneau libre potentiel", None))

            all_pot_blockers = hard_blockers + [(s, e) for s, e, _, _ in confirmed_net]
            potential_net = _subtract_blockers(potential_base, all_pot_blockers)
            for s_u, e_u, lbl, src_id in potential_net:
                if int((e_u - s_u).total_seconds() // 60) >= min_session_minutes:
                    potential_windows.extend(
                        self._split_utc_interval_by_local_day(
                            s_u, e_u, tz, SlotCategory.potential_availability, lbl, src_id
                        )
                    )

        unavail_windows = [
            w
            for s_u, e_u, lbl, src_id in unavail_merged
            for w in self._split_utc_interval_by_local_day(
                s_u, e_u, tz, SlotCategory.personal_unavailability, lbl, src_id
            )
        ]
        recovery_windows = [
            w
            for s_u, e_u, lbl, src_id in recovery_merged
            for w in self._split_utc_interval_by_local_day(
                s_u, e_u, tz, SlotCategory.recovery_time, lbl, src_id
            )
        ]

        # Confirmés d'abord, puis potentiels si demandés
        allocatable = sorted(
            confirmed_windows + (potential_windows if include_potential else []),
            key=lambda w: (0 if w.category == SlotCategory.confirmed_availability else 1, w.start_utc),
        )

        total_conf = sum(w.duration_minutes for w in confirmed_windows)
        total_pot = sum(w.duration_minutes for w in potential_windows)
        missing_info: list[str] = []
        if total_conf == 0:
            missing_info.append(
                "Aucune disponibilité confirmée explicite n'est enregistrée : les créneaux proposés proviennent des plages libres potentielles."
            )
        if not snapshot.ai_memory or snapshot.ai_memory.weekly_study_hours is None:
            missing_info.append(
                "Votre budget horaire hebdomadaire d'apprentissage personnel n'est pas encore défini."
            )

        summary = (
            f"{total_conf} min confirmées et {total_pot} min potentielles exploitables sur {horizon_days} jours "
            f"(fuseau {tz_label}, {len(fixed_windows)} événements fixes, {len(unavail_windows)} plages indisponibles)."
        )

        return AvailabilityComputationResponse(
            timezone=tz_label,
            range_start=horizon_start_utc,
            range_end=horizon_end_utc,
            fixed_events=fixed_windows,
            unavailable_slots=unavail_windows,
            confirmed_slots=confirmed_windows,
            potential_slots=potential_windows,
            recovery_slots=recovery_windows,
            allocatable_slots=allocatable,
            total_confirmed_minutes=total_conf,
            total_potential_minutes=total_pot,
            total_allocatable_minutes=total_conf + (total_pot if include_potential else 0),
            missing_availability_info=missing_info,
            summary=summary,
        )

    def _local_window_to_utc(
        self,
        local_day: date,
        start_t: time,
        end_t: time,
        tz: ZoneInfo,
    ) -> tuple[datetime, datetime]:
        start_local = datetime.combine(local_day, start_t, tzinfo=tz)
        end_day = local_day + timedelta(days=1) if end_t <= start_t else local_day
        end_local = datetime.combine(end_day, end_t, tzinfo=tz)
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

    def _expand_rule(
        self,
        rule: UserAvailabilityRuleRecord,
        first_day: date,
        horizon_days: int,
        origin_tz: ZoneInfo,
    ) -> list[tuple[datetime, datetime]]:
        rule_tz, _ = resolve_zoneinfo(rule.timezone)
        if rule.recurrence == AvailabilityRecurrence.once and rule.starts_at and rule.ends_at:
            s_u = _ensure_utc(rule.starts_at)
            e_u = _ensure_utc(rule.ends_at)
            return [(s_u, e_u)] if s_u and e_u and e_u > s_u else []

        s_t = _parse_hhmm(rule.start_time, time(14, 0))
        e_t = _parse_hhmm(rule.end_time, time(18, 0))
        windows: list[tuple[datetime, datetime]] = []

        # Décaler d'un jour avant pour capter une règle de la veille qui traverse minuit !
        for offset in range(-1, horizon_days + 1):
            local_day = first_day + timedelta(days=offset)
            if rule.recurrence == AvailabilityRecurrence.daily:
                windows.append(self._local_window_to_utc(local_day, s_t, e_t, rule_tz))
            elif rule.recurrence == AvailabilityRecurrence.weekly:
                if rule.day_of_week is None or local_day.weekday() == rule.day_of_week:
                    windows.append(self._local_window_to_utc(local_day, s_t, e_t, rule_tz))
            elif rule.recurrence == AvailabilityRecurrence.once:
                if rule.day_of_week is None or local_day.weekday() == rule.day_of_week:
                    if 0 <= offset < horizon_days:
                        windows.append(self._local_window_to_utc(local_day, s_t, e_t, rule_tz))
        return windows

    def _split_utc_interval_by_local_day(
        self,
        start_utc: datetime,
        end_utc: datetime,
        tz: ZoneInfo,
        category: SlotCategory,
        label: str,
        source_id: str | None,
    ) -> list[TimeSlotWindow]:
        if end_utc <= start_utc:
            return []
        result: list[TimeSlotWindow] = []
        cursor_local = start_utc.astimezone(tz)
        end_local = end_utc.astimezone(tz)

        current_date = cursor_local.date()
        last_date = end_local.date()
        # Si end_local est exactement 00:00 du lendemain, ne pas créer une tranche vide de 0 minute sur last_date
        while current_date <= last_date:
            day_start_utc = datetime.combine(current_date, time(0, 0), tzinfo=tz).astimezone(
                timezone.utc
            )
            day_end_utc = datetime.combine(
                current_date + timedelta(days=1), time(0, 0), tzinfo=tz
            ).astimezone(timezone.utc)
            seg_s = max(start_utc, day_start_utc)
            seg_e = min(end_utc, day_end_utc)
            if seg_e > seg_s:
                mins = int((seg_e - seg_s).total_seconds() // 60)
                if mins > 0:
                    s_loc = seg_s.astimezone(tz)
                    e_loc = seg_e.astimezone(tz)
                    end_hhmm = "24:00" if e_loc.date() > current_date and e_loc.time() == time(0, 0) else e_loc.strftime("%H:%M")
                    result.append(
                        TimeSlotWindow(
                            start_utc=seg_s,
                            end_utc=seg_e,
                            local_date=current_date.isoformat(),
                            start_local=s_loc.strftime("%H:%M"),
                            end_local=end_hhmm,
                            duration_minutes=mins,
                            category=category,
                            label=label,
                            source_id=source_id,
                        )
                    )
            current_date = current_date + timedelta(days=1)
        return result

    def _extract_profile_preferences(
        self,
        snapshot: PlanningContextSnapshot,
    ) -> tuple[set[int], tuple[time, time], list[tuple[int | None, time, time, str]]]:
        rest_days: set[int] = set()
        day_start = time(8, 0)
        day_end = time(22, 0)
        memory_unavail: list[tuple[int | None, time, time, str]] = []

        prefs: dict[str, object] = {}
        if snapshot.profile and isinstance(snapshot.profile.preferences, dict):
            prefs.update(snapshot.profile.preferences)
        if snapshot.ai_memory and isinstance(snapshot.ai_memory.availability_preferences, dict):
            prefs.update(snapshot.ai_memory.availability_preferences)

        raw_rest = prefs.get("rest_days") or prefs.get("unavailable_days")
        if isinstance(raw_rest, list):
            for entry in raw_rest:
                if isinstance(entry, int) and 0 <= entry <= 6:
                    rest_days.add(entry)
                else:
                    mapped = FR_DAY_NAME_TO_INT.get(str(entry).strip().lower())
                    if mapped is not None:
                        rest_days.add(mapped)

        if prefs.get("prefer_morning") and not prefs.get("prefer_evening"):
            day_start = time(7, 30)
        if prefs.get("prefer_evening"):
            day_end = time(22, 30)

        raw_blocks = prefs.get("blocked_windows")
        if isinstance(raw_blocks, list):
            for blk in raw_blocks:
                if not isinstance(blk, dict):
                    continue
                dow_raw = blk.get("day_of_week")
                dow = int(dow_raw) if isinstance(dow_raw, int) and 0 <= dow_raw <= 6 else None
                s_t = _parse_hhmm(str(blk.get("start_time") or ""), time(12, 0))
                e_t = _parse_hhmm(str(blk.get("end_time") or ""), time(13, 30))
                lbl = str(blk.get("label") or "Indisponibilité mémorisée")
                memory_unavail.append((dow, s_t, e_t, lbl))

        return rest_days, (day_start, day_end), memory_unavail
