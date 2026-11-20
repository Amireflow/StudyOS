import { describe, expect, it } from 'vitest';
import { formatTimeInTimezone, getMondayOfWeek } from '../../lib/date';
import type { ScheduleEvent } from '../../types/domain';
import {
  buildDuplicatedWeekEvents,
  computeWeekSummary,
  doEventsOverlap,
  findConflictingEvents,
} from './scheduleUtils';

function makeEvent(overrides: Partial<ScheduleEvent> = {}): ScheduleEvent {
  return {
    id: 'ev-1',
    userId: 'local-user',
    title: 'Cours Python',
    type: 'course',
    startsAt: '2026-11-19T09:00:00.000Z',
    endsAt: '2026-11-19T11:00:00.000Z',
    notes: null,
    createdAt: '2026-11-19T08:00:00.000Z',
    updatedAt: '2026-11-19T08:00:00.000Z',
    ...overrides,
  };
}

describe('scheduleUtils', () => {
  it('détecte les chevauchements stricts sans marquer les créneaux consécutifs (SCHED-03)', () => {
    expect(
      doEventsOverlap(
        '2026-11-19T10:00:00.000Z',
        '2026-11-19T12:00:00.000Z',
        '2026-11-19T11:30:00.000Z',
        '2026-11-19T13:00:00.000Z',
      ),
    ).toBe(true);

    expect(
      doEventsOverlap(
        '2026-11-19T09:00:00.000Z',
        '2026-11-19T13:00:00.000Z',
        '2026-11-19T10:00:00.000Z',
        '2026-11-19T11:00:00.000Z',
      ),
    ).toBe(true);

    expect(
      doEventsOverlap(
        '2026-11-19T10:00:00.000Z',
        '2026-11-19T12:00:00.000Z',
        '2026-11-19T12:00:00.000Z',
        '2026-11-19T14:00:00.000Z',
      ),
    ).toBe(false);
  });

  it('ignore le créneau lui-même lors de la recherche de conflits en édition', () => {
    const existing = [
      makeEvent({
        id: 'ev-1',
        startsAt: '2026-11-19T09:00:00.000Z',
        endsAt: '2026-11-19T11:00:00.000Z',
      }),
      makeEvent({
        id: 'ev-2',
        title: 'TD SQL',
        startsAt: '2026-11-19T11:00:00.000Z',
        endsAt: '2026-11-19T13:00:00.000Z',
      }),
    ];

    expect(
      findConflictingEvents(
        {
          id: 'ev-1',
          startsAt: '2026-11-19T09:00:00.000Z',
          endsAt: '2026-11-19T11:00:00.000Z',
        },
        existing,
      ),
    ).toEqual([]);

    expect(
      findConflictingEvents(
        {
          id: 'ev-1',
          startsAt: '2026-11-19T10:30:00.000Z',
          endsAt: '2026-11-19T12:00:00.000Z',
        },
        existing,
      ).map((e) => e.id),
    ).toEqual(['ev-2']);
  });

  it('duplique une semaine vers la suivante (+7 jours) en ignorant les doublons exacts (SCHED-04)', () => {
    const ev1 = makeEvent({
      id: 'ev-1',
      title: 'Cours Python',
      startsAt: new Date(2026, 10, 19, 9, 0, 0, 0).toISOString(),
      endsAt: new Date(2026, 10, 19, 11, 0, 0, 0).toISOString(),
    });
    const ev2 = makeEvent({
      id: 'ev-2',
      title: 'Atelier React',
      startsAt: new Date(2026, 10, 20, 14, 0, 0, 0).toISOString(),
      endsAt: new Date(2026, 10, 20, 16, 0, 0, 0).toISOString(),
    });
    const alreadyNextWeek = makeEvent({
      id: 'ev-next-1',
      title: 'Cours Python',
      startsAt: new Date(2026, 10, 26, 9, 0, 0, 0).toISOString(),
      endsAt: new Date(2026, 10, 26, 11, 0, 0, 0).toISOString(),
    });

    let seq = 0;
    const result = buildDuplicatedWeekEvents(
      [ev1, ev2],
      [ev1, ev2, alreadyNextWeek],
      '2026-11-19T12:00:00.000Z',
      () => {
        seq += 1;
        return `new-${seq}`;
      },
    );

    expect(result.skippedCount).toBe(1);
    expect(result.created).toHaveLength(1);
    expect(result.created[0].title).toBe('Atelier React');
    expect(new Date(result.created[0].startsAt).getDate()).toBe(27);
    expect(new Date(result.created[0].startsAt).getHours()).toBe(14);
  });

  it('formate correctement un horaire UTC selon le fuseau horaire (Africa/Dakar et Europe/Paris) (SCHED-02)', () => {
    const utcIso = '2026-11-19T09:00:00.000Z';

    expect(formatTimeInTimezone(utcIso, 'Africa/Dakar')).toBe('09:00');
    expect(formatTimeInTimezone(utcIso, 'Europe/Paris')).toBe('10:00');
  });

  it('calcule le résumé de semaine et trouve le lundi de référence', () => {
    const thursday = new Date(2026, 10, 19, 15, 30, 0);
    const monday = getMondayOfWeek(thursday);
    expect(monday.getDay()).toBe(1);
    expect(monday.getDate()).toBe(16);

    const summary = computeWeekSummary([
      makeEvent({
        id: '1',
        startsAt: '2026-11-19T09:00:00.000Z',
        endsAt: '2026-11-19T11:00:00.000Z',
      }),
      makeEvent({
        id: '2',
        startsAt: '2026-11-19T10:00:00.000Z',
        endsAt: '2026-11-19T12:00:00.000Z',
      }),
    ]);

    expect(summary).toEqual({
      eventCount: 2,
      totalMinutes: 240,
      conflictCount: 2,
    });
  });
});
