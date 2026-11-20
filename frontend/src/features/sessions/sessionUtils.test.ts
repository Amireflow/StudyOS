import { describe, expect, it } from 'vitest';
import type { StudySession } from '../../types/domain';
import {
  computeSessionSummary,
  formatDuration,
  getSessionDurationMinutes,
} from './sessionUtils';

function makeSession(overrides: Partial<StudySession> = {}): StudySession {
  return {
    id: 's-1',
    userId: 'local-user',
    title: 'Séance test',
    category: 'Apprentissage',
    status: 'completed',
    startedAt: '2026-11-19T10:00:00.000Z',
    endedAt: '2026-11-19T11:00:00.000Z',
    result: 'Exercice terminé.',
    taskId: null,
    projectId: null,
    moduleId: null,
    lessonId: null,
    skillId: null,
    createdAt: '2026-11-19T10:00:00.000Z',
    updatedAt: '2026-11-19T11:00:00.000Z',
    ...overrides,
  };
}

describe('sessionUtils', () => {
  it('calcule la durée depuis les heures et formate lisiblement', () => {
    const session95 = makeSession({
      startedAt: '2026-11-19T10:00:00.000Z',
      endedAt: '2026-11-19T11:35:00.000Z',
    });

    expect(getSessionDurationMinutes(session95)).toBe(95);
    expect(formatDuration(0)).toBe('< 1 min');
    expect(formatDuration(45)).toBe('45 min');
    expect(formatDuration(60)).toBe('1 h');
    expect(formatDuration(95)).toBe('1 h 35');
  });

  it('exclut les séances annulées et en cours du total des séances achevées (SESSION-03)', () => {
    const sessions: StudySession[] = [
      makeSession({
        id: '1',
        status: 'completed',
        startedAt: '2026-11-19T08:00:00.000Z',
        endedAt: '2026-11-19T08:45:00.000Z',
      }),
      makeSession({
        id: '2',
        status: 'cancelled',
        startedAt: '2026-11-19T09:00:00.000Z',
        endedAt: '2026-11-19T09:50:00.000Z',
      }),
      makeSession({
        id: '3',
        status: 'in_progress',
        startedAt: '2026-11-19T10:00:00.000Z',
        endedAt: null,
        result: null,
      }),
    ];

    expect(computeSessionSummary(sessions)).toEqual({
      completedCount: 1,
      totalCompletedMinutes: 45,
      inProgressCount: 1,
      cancelledCount: 1,
    });
  });
});
