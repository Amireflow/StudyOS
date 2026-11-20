import { describe, expect, it } from 'vitest';
import type { Task } from '../../types/domain';
import {
  computeTaskSummary,
  DEFAULT_TASK_FILTERS,
  filterTasks,
  isTaskOverdue,
  sortTasksByUrgency,
} from './taskUtils';

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 't-1',
    userId: 'local-user',
    title: 'Tâche test',
    description: null,
    status: 'todo',
    priority: 'normal',
    dueAt: null,
    completedAt: null,
    source: 'manual',
    proposalId: null,
    projectId: null,
    moduleId: null,
    createdAt: '2026-11-18T10:00:00.000Z',
    updatedAt: '2026-11-18T10:00:00.000Z',
    ...overrides,
  };
}

describe('taskUtils', () => {
  const now = new Date(2026, 10, 19, 14, 0, 0); // 19 novembre 2026, 14:00 locale

  it('détecte les tâches actives en retard sans marquer celles dues aujourd’hui ou terminées', () => {
    const yesterday = new Date(2026, 10, 18, 23, 59, 0).toISOString();
    const todayMorning = new Date(2026, 10, 19, 9, 0, 0).toISOString();

    expect(isTaskOverdue(makeTask({ status: 'todo', dueAt: yesterday }), now)).toBe(true);
    expect(isTaskOverdue(makeTask({ status: 'in_progress', dueAt: yesterday }), now)).toBe(true);
    expect(isTaskOverdue(makeTask({ status: 'todo', dueAt: todayMorning }), now)).toBe(false);
    expect(isTaskOverdue(makeTask({ status: 'done', dueAt: yesterday }), now)).toBe(false);
    expect(isTaskOverdue(makeTask({ status: 'cancelled', dueAt: yesterday }), now)).toBe(false);
    expect(isTaskOverdue(makeTask({ status: 'todo', dueAt: null }), now)).toBe(false);
  });

  it('combine les filtres de statut, priorité, échéance et recherche (TASK-03)', () => {
    const yesterday = new Date(2026, 10, 18, 12, 0, 0).toISOString();
    const tomorrow = new Date(2026, 10, 20, 12, 0, 0).toISOString();

    const tasks: Task[] = [
      makeTask({
        id: '1',
        title: 'Corriger API FastAPI',
        status: 'in_progress',
        priority: 'high',
        dueAt: yesterday,
      }),
      makeTask({
        id: '2',
        title: 'Réviser Python',
        status: 'todo',
        priority: 'high',
        dueAt: tomorrow,
      }),
      makeTask({
        id: '3',
        title: 'Corriger CSS mobile',
        status: 'done',
        priority: 'high',
        dueAt: yesterday,
      }),
      makeTask({
        id: '4',
        title: 'Idée secondaire',
        status: 'parked',
        priority: 'low',
        dueAt: null,
      }),
    ];

    const filtered = filterTasks(
      tasks,
      {
        ...DEFAULT_TASK_FILTERS,
        status: 'active',
        priority: 'high',
        due: 'overdue',
        search: 'fastapi',
      },
      now,
    );

    expect(filtered.map((t) => t.id)).toEqual(['1']);
  });

  it('exclut les tâches annulées du compteur de tâches terminées (TASK-02)', () => {
    const yesterday = new Date(2026, 10, 18, 12, 0, 0).toISOString();
    const tasks: Task[] = [
      makeTask({ id: '1', status: 'todo', dueAt: yesterday }),
      makeTask({ id: '2', status: 'done', completedAt: now.toISOString() }),
      makeTask({ id: '3', status: 'cancelled' }),
      makeTask({ id: '4', status: 'parked' }),
    ];

    const summary = computeTaskSummary(tasks, now);

    expect(summary).toEqual({
      activeCount: 1,
      doneCount: 1,
      parkedCount: 1,
      cancelledCount: 1,
      overdueCount: 1,
      completionRate: 50,
    });
  });

  it('trie les tâches par urgence (retard en premier, puis priorité décroissante et échéance croissante)', () => {
    const tLow = makeTask({ id: 'low', priority: 'low', dueAt: '2026-11-18T12:00:00.000Z' });
    const tCrit = makeTask({ id: 'crit', priority: 'critical', dueAt: null });
    const tHighLater = makeTask({ id: 'high2', priority: 'high', dueAt: '2026-11-22T12:00:00.000Z' });
    const tHighSoon = makeTask({ id: 'high1', priority: 'high', dueAt: '2026-11-20T12:00:00.000Z' });

    const beforeDue = sortTasksByUrgency(
      [tLow, tHighLater, tCrit, tHighSoon],
      new Date('2026-11-17T12:00:00.000Z'),
    );
    expect(beforeDue.map((t) => t.id)).toEqual(['crit', 'high1', 'high2', 'low']);

    const afterLowOverdue = sortTasksByUrgency(
      [tLow, tHighLater, tCrit, tHighSoon],
      new Date('2026-11-20T12:00:00.000Z'),
    );
    expect(afterLowOverdue.map((t) => t.id)).toEqual(['low', 'crit', 'high1', 'high2']);
  });
});
