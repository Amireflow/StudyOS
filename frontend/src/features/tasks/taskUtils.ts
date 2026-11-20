import type { BadgeVariant } from '../../components/ui/Badge';
import { toLocalDateKey } from '../../lib/date';
import type { Task, TaskPriority, TaskStatus } from '../../types/domain';

export const TASK_STATUS_META: Record<TaskStatus, { label: string; badgeVariant: BadgeVariant }> = {
  todo: { label: 'À faire', badgeVariant: 'neutral' },
  in_progress: { label: 'En cours', badgeVariant: 'primary' },
  done: { label: 'Terminée', badgeVariant: 'success' },
  parked: { label: 'Parking', badgeVariant: 'warning' },
  cancelled: { label: 'Annulée', badgeVariant: 'danger' },
};

export const TASK_PRIORITY_META: Record<
  TaskPriority,
  { label: string; badgeVariant: BadgeVariant; weight: number }
> = {
  critical: { label: 'Critique', badgeVariant: 'danger', weight: 4 },
  high: { label: 'Haute', badgeVariant: 'warning', weight: 3 },
  normal: { label: 'Normale', badgeVariant: 'primary', weight: 2 },
  low: { label: 'Basse', badgeVariant: 'neutral', weight: 1 },
};

export type TaskStatusFilter = 'all' | 'active' | TaskStatus;
export type TaskDueFilter = 'all' | 'overdue' | 'today' | 'upcoming' | 'no_due';

export interface TaskFilters {
  status: TaskStatusFilter;
  priority: 'all' | TaskPriority;
  due: TaskDueFilter;
  search: string;
}

export const DEFAULT_TASK_FILTERS: TaskFilters = {
  status: 'all',
  priority: 'all',
  due: 'all',
  search: '',
};

export function isActiveTaskStatus(status: TaskStatus): boolean {
  return status === 'todo' || status === 'in_progress';
}

/**
 * Une tâche est en retard si elle est toujours active et que sa date d'échéance locale
 * est strictement antérieure au jour courant.
 */
export function isTaskOverdue(task: Task, now = new Date()): boolean {
  if (!task.dueAt || !isActiveTaskStatus(task.status)) {
    return false;
  }
  const dueKey = toLocalDateKey(task.dueAt);
  const todayKey = toLocalDateKey(now);
  return Boolean(dueKey) && dueKey < todayKey;
}

export function isTaskDueToday(task: Task, now = new Date()): boolean {
  if (!task.dueAt) {
    return false;
  }
  return toLocalDateKey(task.dueAt) === toLocalDateKey(now);
}

/**
 * Applique tous les filtres combinés sur les tâches (TASK-03).
 */
export function filterTasks(tasks: Task[], filters: TaskFilters, now = new Date()): Task[] {
  const todayKey = toLocalDateKey(now);
  const normalizedSearch = filters.search.trim().toLowerCase();

  return tasks.filter((task) => {
    if (filters.status === 'active') {
      if (!isActiveTaskStatus(task.status)) {
        return false;
      }
    } else if (filters.status !== 'all' && task.status !== filters.status) {
      return false;
    }

    if (filters.priority !== 'all' && task.priority !== filters.priority) {
      return false;
    }

    if (filters.due === 'overdue' && !isTaskOverdue(task, now)) {
      return false;
    }
    if (filters.due === 'today' && !isTaskDueToday(task, now)) {
      return false;
    }
    if (filters.due === 'upcoming') {
      const dueKey = task.dueAt ? toLocalDateKey(task.dueAt) : '';
      if (!dueKey || dueKey <= todayKey) {
        return false;
      }
    }
    if (filters.due === 'no_due' && task.dueAt !== null) {
      return false;
    }

    if (normalizedSearch) {
      const haystack = `${task.title} ${task.description ?? ''}`.toLowerCase();
      if (!haystack.includes(normalizedSearch)) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Trie par priorité décroissante, puis échéance la plus proche, puis création récente.
 */
export function sortTasksByUrgency(tasks: Task[]): Task[] {
  return [...tasks].sort((a, b) => {
    const priorityDiff =
      TASK_PRIORITY_META[b.priority].weight - TASK_PRIORITY_META[a.priority].weight;
    if (priorityDiff !== 0) {
      return priorityDiff;
    }

    if (a.dueAt && b.dueAt) {
      const dueDiff = new Date(a.dueAt).getTime() - new Date(b.dueAt).getTime();
      if (dueDiff !== 0) {
        return dueDiff;
      }
    } else if (a.dueAt || b.dueAt) {
      return a.dueAt ? -1 : 1;
    }

    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });
}

export interface TaskSummary {
  activeCount: number;
  doneCount: number;
  parkedCount: number;
  cancelledCount: number;
  overdueCount: number;
  completionRate: number;
}

/**
 * Calcule les indicateurs agrégés.
 * Les tâches annulées (`cancelled`) ne sont jamais comptées comme terminées (TASK-02).
 */
export function computeTaskSummary(tasks: Task[], now = new Date()): TaskSummary {
  let activeCount = 0;
  let doneCount = 0;
  let parkedCount = 0;
  let cancelledCount = 0;
  let overdueCount = 0;

  for (const task of tasks) {
    if (isActiveTaskStatus(task.status)) {
      activeCount += 1;
      if (isTaskOverdue(task, now)) {
        overdueCount += 1;
      }
    } else if (task.status === 'done') {
      doneCount += 1;
    } else if (task.status === 'parked') {
      parkedCount += 1;
    } else if (task.status === 'cancelled') {
      cancelledCount += 1;
    }
  }

  const denominator = activeCount + doneCount;
  const completionRate = denominator === 0 ? 0 : Math.round((doneCount / denominator) * 100);

  return {
    activeCount,
    doneCount,
    parkedCount,
    cancelledCount,
    overdueCount,
    completionRate,
  };
}
