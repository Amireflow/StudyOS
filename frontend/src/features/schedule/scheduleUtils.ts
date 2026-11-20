import type { BadgeVariant } from '../../components/ui/Badge';
import { addDays, toLocalDateKey } from '../../lib/date';
import type { ScheduleEvent, ScheduleEventType } from '../../types/domain';

export const SCHEDULE_EVENT_TYPE_META: Record<
  ScheduleEventType,
  { label: string; badgeVariant: BadgeVariant }
> = {
  course: { label: 'Cours', badgeVariant: 'primary' },
  learning: { label: 'Apprentissage', badgeVariant: 'success' },
  project: { label: 'Projet', badgeVariant: 'warning' },
  personal: { label: 'Personnel', badgeVariant: 'neutral' },
  other: { label: 'Autre', badgeVariant: 'neutral' },
};

export const SCHEDULE_EVENT_TONE: Record<
  ScheduleEventType,
  { bar: string; dot: string; blockBg: string; blockText: string }
> = {
  course: {
    bar: 'bg-teal-600 dark:bg-teal-400',
    dot: 'bg-teal-600 dark:bg-teal-400',
    blockBg: 'bg-teal-50/90 dark:bg-teal-950/55',
    blockText: 'text-teal-950 dark:text-teal-100',
  },
  learning: {
    bar: 'bg-emerald-600 dark:bg-emerald-400',
    dot: 'bg-emerald-600 dark:bg-emerald-400',
    blockBg: 'bg-emerald-50/90 dark:bg-emerald-950/55',
    blockText: 'text-emerald-950 dark:text-emerald-100',
  },
  project: {
    bar: 'bg-amber-500 dark:bg-amber-400',
    dot: 'bg-amber-500 dark:bg-amber-400',
    blockBg: 'bg-amber-50/90 dark:bg-amber-950/55',
    blockText: 'text-amber-950 dark:text-amber-100',
  },
  personal: {
    bar: 'bg-zinc-500 dark:bg-zinc-400',
    dot: 'bg-zinc-500 dark:bg-zinc-400',
    blockBg: 'bg-zinc-100 dark:bg-zinc-800/80',
    blockText: 'text-zinc-900 dark:text-zinc-100',
  },
  other: {
    bar: 'bg-zinc-400 dark:bg-zinc-500',
    dot: 'bg-zinc-400 dark:bg-zinc-500',
    blockBg: 'bg-zinc-100/80 dark:bg-zinc-800/60',
    blockText: 'text-zinc-800 dark:text-zinc-200',
  },
};

/**
 * Détecte un chevauchement strict entre deux intervalles horaires (`aStart < bEnd && bStart < aEnd`).
 * Deux créneaux consécutifs (ex. 10:00–12:00 et 12:00–14:00) ne sont pas en conflit.
 */
export function doEventsOverlap(
  aStartIso: string,
  aEndIso: string,
  bStartIso: string,
  bEndIso: string,
): boolean {
  const aStartMs = new Date(aStartIso).getTime();
  const aEndMs = new Date(aEndIso).getTime();
  const bStartMs = new Date(bStartIso).getTime();
  const bEndMs = new Date(bEndIso).getTime();

  if (
    Number.isNaN(aStartMs) ||
    Number.isNaN(aEndMs) ||
    Number.isNaN(bStartMs) ||
    Number.isNaN(bEndMs)
  ) {
    return false;
  }

  return aStartMs < bEndMs && bStartMs < aEndMs;
}

/**
 * Retourne les créneaux existants qui entrent en conflit avec un créneau candidat (SCHED-03).
 */
export function findConflictingEvents(
  candidate: { id?: string; startsAt: string; endsAt: string },
  events: ScheduleEvent[],
): ScheduleEvent[] {
  return events
    .filter((event) => {
      if (candidate.id && event.id === candidate.id) {
        return false;
      }
      return doEventsOverlap(candidate.startsAt, candidate.endsAt, event.startsAt, event.endsAt);
    })
    .sort((a, b) => new Date(a.startsAt).getTime() - new Date(b.startsAt).getTime());
}

/**
 * Identifie tous les créneaux impliqués dans au moins un conflit horaire.
 */
export function getConflictingEventIds(events: ScheduleEvent[]): Set<string> {
  const conflictingIds = new Set<string>();

  for (let i = 0; i < events.length; i += 1) {
    for (let j = i + 1; j < events.length; j += 1) {
      const a = events[i];
      const b = events[j];
      if (doEventsOverlap(a.startsAt, a.endsAt, b.startsAt, b.endsAt)) {
        conflictingIds.add(a.id);
        conflictingIds.add(b.id);
      }
    }
  }

  return conflictingIds;
}

export function getWeekDays(weekStart: Date): Date[] {
  return Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));
}

export function getEventsForLocalDate(events: ScheduleEvent[], targetDate: Date): ScheduleEvent[] {
  const targetKey = toLocalDateKey(targetDate);
  return events
    .filter((event) => toLocalDateKey(event.startsAt) === targetKey)
    .sort((a, b) => new Date(a.startsAt).getTime() - new Date(b.startsAt).getTime());
}

export function getEventsForWeek(events: ScheduleEvent[], weekStart: Date): ScheduleEvent[] {
  const weekKeys = new Set(getWeekDays(weekStart).map((day) => toLocalDateKey(day)));
  return events
    .filter((event) => weekKeys.has(toLocalDateKey(event.startsAt)))
    .sort((a, b) => new Date(a.startsAt).getTime() - new Date(b.startsAt).getTime());
}

export function getEventDurationMinutes(event: Pick<ScheduleEvent, 'startsAt' | 'endsAt'>): number {
  const startMs = new Date(event.startsAt).getTime();
  const endMs = new Date(event.endsAt).getTime();
  if (Number.isNaN(startMs) || Number.isNaN(endMs)) {
    return 0;
  }
  return Math.max(0, Math.round((endMs - startMs) / 60_000));
}

export interface WeekSummary {
  eventCount: number;
  totalMinutes: number;
  conflictCount: number;
}

export function computeWeekSummary(weekEvents: ScheduleEvent[]): WeekSummary {
  const conflictingIds = getConflictingEventIds(weekEvents);
  let totalMinutes = 0;

  for (const event of weekEvents) {
    totalMinutes += getEventDurationMinutes(event);
  }

  return {
    eventCount: weekEvents.length,
    totalMinutes,
    conflictCount: conflictingIds.size,
  };
}

function eventFingerprint(title: string, startsAt: string, endsAt: string): string {
  return `${title.trim().toLowerCase()}|${startsAt}|${endsAt}`;
}

/**
 * Prépare la duplication des créneaux d'une semaine vers la semaine suivante (+7 jours locaux),
 * en ignorant les doublons exacts déjà présents (SCHED-04).
 */
export function buildDuplicatedWeekEvents(
  sourceWeekEvents: ScheduleEvent[],
  allEvents: ScheduleEvent[],
  nowIso: string,
  createId: () => string,
): { created: ScheduleEvent[]; skippedCount: number } {
  const existingKeys = new Set(
    allEvents.map((event) => eventFingerprint(event.title, event.startsAt, event.endsAt)),
  );

  const created: ScheduleEvent[] = [];
  let skippedCount = 0;

  for (const event of sourceWeekEvents) {
    const nextStartsAt = addDays(new Date(event.startsAt), 7).toISOString();
    const nextEndsAt = addDays(new Date(event.endsAt), 7).toISOString();
    const key = eventFingerprint(event.title, nextStartsAt, nextEndsAt);

    if (existingKeys.has(key)) {
      skippedCount += 1;
      continue;
    }

    existingKeys.add(key);
    created.push({
      id: createId(),
      userId: event.userId,
      title: event.title,
      type: event.type,
      startsAt: nextStartsAt,
      endsAt: nextEndsAt,
      notes: event.notes,
      createdAt: nowIso,
      updatedAt: nowIso,
    });
  }

  return { created, skippedCount };
}
