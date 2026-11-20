import type { BadgeVariant } from '../../components/ui/Badge';
import type { SessionStatus, StudySession } from '../../types/domain';

export const SESSION_STATUS_META: Record<
  SessionStatus,
  { label: string; badgeVariant: BadgeVariant }
> = {
  in_progress: { label: 'En cours', badgeVariant: 'primary' },
  completed: { label: 'Achevée', badgeVariant: 'success' },
  cancelled: { label: 'Annulée', badgeVariant: 'danger' },
};

/**
 * Calcule la durée réelle d'une séance en minutes à partir des horodatages (SESSION-01).
 */
export function getSessionDurationMinutes(session: StudySession, now = new Date()): number {
  const startMs = new Date(session.startedAt).getTime();
  if (Number.isNaN(startMs)) {
    return 0;
  }

  if (session.endedAt) {
    const endMs = new Date(session.endedAt).getTime();
    if (Number.isNaN(endMs)) {
      return 0;
    }
    return Math.max(0, Math.round((endMs - startMs) / 60_000));
  }

  if (session.status === 'in_progress') {
    return Math.max(0, Math.round((now.getTime() - startMs) / 60_000));
  }

  return 0;
}

export function formatDuration(minutes: number): string {
  if (minutes <= 0) {
    return '< 1 min';
  }
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (remainingMinutes === 0) {
    return `${hours} h`;
  }
  return `${hours} h ${String(remainingMinutes).padStart(2, '0')}`;
}

export interface SessionSummary {
  completedCount: number;
  totalCompletedMinutes: number;
  inProgressCount: number;
  cancelledCount: number;
}

/**
 * Agrège les séances.
 * Les séances annulées ou en cours ne sont jamais incluses comme achevées (SESSION-03).
 */
export function computeSessionSummary(sessions: StudySession[]): SessionSummary {
  let completedCount = 0;
  let totalCompletedMinutes = 0;
  let inProgressCount = 0;
  let cancelledCount = 0;

  for (const session of sessions) {
    if (session.status === 'completed' && session.endedAt !== null) {
      completedCount += 1;
      totalCompletedMinutes += getSessionDurationMinutes(session);
    } else if (session.status === 'in_progress') {
      inProgressCount += 1;
    } else if (session.status === 'cancelled') {
      cancelledCount += 1;
    }
  }

  return {
    completedCount,
    totalCompletedMinutes,
    inProgressCount,
    cancelledCount,
  };
}

export const SESSION_CATEGORY_TONE: Record<string, { bar: string; dot: string }> = {
  Cours: {
    bar: 'bg-teal-600 dark:bg-teal-400',
    dot: 'bg-teal-600 dark:bg-teal-400',
  },
  Apprentissage: {
    bar: 'bg-emerald-600 dark:bg-emerald-400',
    dot: 'bg-emerald-600 dark:bg-emerald-400',
  },
  Exercices: {
    bar: 'bg-sky-600 dark:bg-sky-400',
    dot: 'bg-sky-600 dark:bg-sky-400',
  },
  Projet: {
    bar: 'bg-amber-500 dark:bg-amber-400',
    dot: 'bg-amber-500 dark:bg-amber-400',
  },
  Révision: {
    bar: 'bg-cyan-600 dark:bg-cyan-400',
    dot: 'bg-cyan-600 dark:bg-cyan-400',
  },
  Autre: {
    bar: 'bg-zinc-400 dark:bg-zinc-500',
    dot: 'bg-zinc-400 dark:bg-zinc-500',
  },
};

export function getSessionCategoryTone(category: string): { bar: string; dot: string } {
  return SESSION_CATEGORY_TONE[category] ?? SESSION_CATEGORY_TONE.Autre;
}

export function formatElapsedTimer(startedAtIso: string, nowMs = Date.now()): string {
  const startMs = new Date(startedAtIso).getTime();
  if (Number.isNaN(startMs)) {
    return '00:00';
  }
  const totalSeconds = Math.max(0, Math.floor((nowMs - startMs) / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}
