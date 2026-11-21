import { useMemo, useState } from 'react';
import {
  Add01Icon,
  Award02Icon,
  BookOpen01Icon,
  CheckmarkSquare02Icon,
  File02Icon,
  FolderKanbanIcon,
  PlayIcon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { InlineConfirm, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import { addDays, formatDayHeaderFr, formatTimeFr, toLocalDateKey } from '../../lib/date';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type { SessionFinishExtra, SessionStatus, StudySession } from '../../types/domain';
import { isActiveTaskStatus } from '../tasks/taskUtils';
import { ActiveSessionCard } from './ActiveSessionCard';
import { ManualSessionForm, StartSessionForm } from './SessionForms';
import type { ManualSessionValues, StartSessionValues } from './sessionSchema';
import {
  computeSessionSummary,
  formatDuration,
  getSessionCategoryTone,
  getSessionDurationMinutes,
  SESSION_STATUS_META,
} from './sessionUtils';

function formatJournalDayLabel(dateKey: string, todayKey: string, yesterdayKey: string): string {
  if (dateKey === todayKey) return 'Aujourd’hui';
  if (dateKey === yesterdayKey) return 'Hier';

  const [y, m, d] = dateKey.split('-').map(Number);
  if (!y || !m || !d) return dateKey;
  const label = formatDayHeaderFr(new Date(y, m - 1, d));
  return label ? label.charAt(0).toUpperCase() + label.slice(1) : dateKey;
}

export function SessionsPage() {
  const {
    sessions,
    tasks,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    startSession,
    finishSession,
    cancelSession,
    recordManualSession,
    deleteSession,
  } = useStudyStore();
  const { projects, modules, lessons, skills } = useLearningStore();

  const [formMode, setFormMode] = useState<'none' | 'start' | 'manual'>('none');
  const [statusFilter, setStatusFilter] = useState<'all' | SessionStatus>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [feedback, setFeedback] = useState<string | null>(null);

  const taskTitleById = useMemo(
    () => new Map(tasks.map((task) => [task.id, task.title])),
    [tasks],
  );
  const projectNameById = useMemo(
    () => new Map(projects.map((p) => [p.id, p.name])),
    [projects],
  );
  const moduleTitleById = useMemo(
    () => new Map(modules.map((m) => [m.id, m.title])),
    [modules],
  );
  const lessonTitleById = useMemo(
    () => new Map(lessons.map((l) => [l.id, l.title])),
    [lessons],
  );
  const skillNameById = useMemo(
    () => new Map(skills.map((s) => [s.id, s.name])),
    [skills],
  );
  const activeTasks = useMemo(
    () => tasks.filter((task) => isActiveTaskStatus(task.status)),
    [tasks],
  );
  const nonCancelledTasks = useMemo(
    () => tasks.filter((task) => task.status !== 'cancelled'),
    [tasks],
  );

  const summary = useMemo(() => computeSessionSummary(sessions), [sessions]);
  const averageMinutes =
    summary.completedCount === 0
      ? 0
      : Math.round(summary.totalCompletedMinutes / summary.completedCount);

  const inProgressSessions = useMemo(
    () => sessions.filter((session) => session.status === 'in_progress'),
    [sessions],
  );

  const availableCategories = useMemo(() => {
    const unique = new Set<string>();
    for (const session of sessions) {
      if (session.category) unique.add(session.category);
    }
    return Array.from(unique);
  }, [sessions]);

  const categoryBreakdown = useMemo(() => {
    const totals = new Map<string, number>();
    for (const session of sessions) {
      if (session.status === 'completed' && session.endedAt !== null) {
        const mins = getSessionDurationMinutes(session);
        if (mins > 0) {
          totals.set(session.category, (totals.get(session.category) ?? 0) + mins);
        }
      }
    }
    return Array.from(totals.entries())
      .map(([category, minutes]) => ({ category, minutes }))
      .sort((a, b) => b.minutes - a.minutes);
  }, [sessions]);

  const filteredSessions = useMemo(() => {
    return sessions
      .filter((session) => {
        if (statusFilter !== 'all' && session.status !== statusFilter) return false;
        if (categoryFilter !== 'all' && session.category !== categoryFilter) return false;
        return true;
      })
      .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime());
  }, [categoryFilter, sessions, statusFilter]);

  const groupedJournalDays = useMemo(() => {
    const groups = new Map<string, StudySession[]>();
    for (const session of filteredSessions) {
      const key = toLocalDateKey(session.startedAt) || 'inconnu';
      const existing = groups.get(key);
      if (existing) {
        existing.push(session);
      } else {
        groups.set(key, [session]);
      }
    }
    return Array.from(groups.entries()).map(([dateKey, daySessions]) => {
      const dayCompletedMinutes = daySessions.reduce((acc, s) => {
        if (s.status === 'completed' && s.endedAt !== null) {
          return acc + getSessionDurationMinutes(s);
        }
        return acc;
      }, 0);
      return { dateKey, daySessions, dayCompletedMinutes };
    });
  }, [filteredSessions]);

  const handleStart = async (values: StartSessionValues) => {
    if (await startSession(values)) {
      setFormMode('none');
      setFeedback(`Séance « ${values.title.trim()} » démarrée.`);
    }
  };

  const handleManualRecord = async (values: ManualSessionValues) => {
    if (await recordManualSession(values)) {
      setFormMode('none');
      setFeedback(`Séance « ${values.title.trim()} » enregistrée dans l’historique.`);
    }
  };

  const handleFinish = async (
    session: StudySession,
    result: string,
    extra?: SessionFinishExtra,
  ) => {
    if (await finishSession(session.id, result, extra)) {
      setFeedback(`Séance « ${session.title} » clôturée et ajoutée aux totaux.`);
    }
  };

  const handleCancel = async (session: StudySession) => {
    if (await cancelSession(session.id)) {
      setFeedback(`Séance « ${session.title} » annulée (exclue des séances achevées).`);
    }
  };

  const handleDelete = async (session: StudySession) => {
    if (await deleteSession(session.id)) {
      setFeedback(`Séance « ${session.title} » supprimée.`);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <header>
          <h1 className="ui-page-title">
            Séances
          </h1>
        </header>
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <header>
          <h1 className="ui-page-title">
            Séances
          </h1>
        </header>
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  const today = new Date();
  const todayKey = toLocalDateKey(today);
  const yesterdayKey = toLocalDateKey(addDays(today, -1));

  return (
    <div className="space-y-3.5 sm:space-y-5">
      {/* En-tête */}
      <header className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="ui-page-title">
            Séances
          </h1>
          {summary.completedCount > 0 && (
            <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
              {`${summary.completedCount} achevée${summary.completedCount > 1 ? 's' : ''} · ${formatDuration(summary.totalCompletedMinutes)}`}
            </p>
          )}
        </div>

        <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0">
          <Button
            type="button"
            variant="primary"
            size="sm"
            className="shrink-0"
            onClick={() => setFormMode((prev) => (prev === 'start' ? 'none' : 'start'))}
          >
            <Icon icon={PlayIcon} size={15} />
            Démarrer une séance
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="shrink-0"
            onClick={() => setFormMode((prev) => (prev === 'manual' ? 'none' : 'manual'))}
          >
            <Icon icon={Add01Icon} size={15} />
            Enregistrer une séance passée
          </Button>
        </div>
      </header>

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Ruban Focus Pulse (4 indicateurs) */}
      <section aria-label="Indicateurs de séances" className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 sm:gap-3">
        <button
          type="button"
          aria-pressed={statusFilter === 'completed'}
          aria-label={`Achevées (${summary.completedCount}) — filtrer`}
          onClick={() =>
            setStatusFilter((prev) => (prev === 'completed' ? 'all' : 'completed'))
          }
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            statusFilter === 'completed'
              ? 'bg-teal-50 dark:bg-teal-950/45'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Achevées</p>
          <p
            className="mt-0.5 text-xl font-semibold tabular-nums text-emerald-700 sm:mt-1 sm:text-2xl dark:text-emerald-400"
            data-testid="sessions-completed-count"
          >
            {summary.completedCount}
          </p>
        </button>

        <div className="rounded-2xl bg-white p-3 sm:p-4 dark:bg-zinc-900">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Temps réel</p>
          <p
            className="mt-0.5 text-xl font-semibold tabular-nums text-zinc-900 sm:mt-1 sm:text-2xl dark:text-zinc-50"
            data-testid="sessions-total-time"
          >
            {summary.completedCount === 0
              ? '0 min'
              : formatDuration(summary.totalCompletedMinutes)}
          </p>
        </div>

        <div className="rounded-2xl bg-white p-3 sm:p-4 dark:bg-zinc-900">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Durée moyenne</p>
          <p className="mt-0.5 text-xl font-semibold tabular-nums text-zinc-900 sm:mt-1 sm:text-2xl dark:text-zinc-50">
            {summary.completedCount === 0 ? '0 min' : formatDuration(averageMinutes)}
          </p>
        </div>

        <button
          type="button"
          aria-pressed={statusFilter === 'in_progress'}
          aria-label={`En cours (${summary.inProgressCount}) — filtrer`}
          onClick={() =>
            setStatusFilter((prev) => (prev === 'in_progress' ? 'all' : 'in_progress'))
          }
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            statusFilter === 'in_progress'
              ? 'bg-teal-50 dark:bg-teal-950/45'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">En cours</p>
          <p
            className="mt-0.5 text-xl font-semibold tabular-nums text-teal-800 sm:mt-1 sm:text-2xl dark:text-teal-300"
            data-testid="sessions-in-progress-count"
          >
            {summary.inProgressCount}
          </p>
        </button>
      </section>

      {/* Répartition du temps par catégorie */}
      {summary.totalCompletedMinutes > 0 && categoryBreakdown.length > 0 && (
        <section
          aria-label="Répartition par catégorie"
          className="space-y-2.5 rounded-2xl bg-white p-4 dark:bg-zinc-900"
        >
          <div className="flex h-1.5 w-full gap-0.5 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
            {categoryBreakdown.map(({ category, minutes }) => (
              <div
                key={category}
                className={cn('h-full rounded-full', getSessionCategoryTone(category).bar)}
                style={{ width: `${(minutes / summary.totalCompletedMinutes) * 100}%` }}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-600 dark:text-zinc-400">
            {categoryBreakdown.map(({ category, minutes }) => (
              <span key={category} className="inline-flex items-center gap-1.5">
                <span
                  aria-hidden="true"
                  className={cn('h-2 w-2 rounded-full', getSessionCategoryTone(category).dot)}
                />
                <span>
                  {category} · <strong className="font-medium text-zinc-900 dark:text-zinc-200">{formatDuration(minutes)}</strong>
                </span>
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Séances en cours (avec minuteur en direct) */}
      {inProgressSessions.map((session) => (
        <ActiveSessionCard
          key={session.id}
          session={session}
          linkedTaskTitle={session.taskId ? (taskTitleById.get(session.taskId) ?? null) : null}
          linkedProjectName={session.projectId ? projectNameById.get(session.projectId) : undefined}
          linkedSkillName={session.skillId ? skillNameById.get(session.skillId) : undefined}
          onFinish={handleFinish}
          onCancel={handleCancel}
        />
      ))}

      {/* Formulaires */}
      {formMode === 'start' && (
        <StartSessionForm
          activeTasks={activeTasks}
          onSubmit={handleStart}
          onCancel={() => setFormMode('none')}
        />
      )}

      {formMode === 'manual' && (
        <ManualSessionForm
          tasks={nonCancelledTasks}
          onSubmit={handleManualRecord}
          onCancel={() => setFormMode('none')}
        />
      )}

      {/* Journal chronologique groupé par jour */}
      <section
        aria-labelledby="sessions-history-heading"
        className="space-y-4 rounded-2xl bg-white p-4 sm:p-5 dark:bg-zinc-900"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2
            id="sessions-history-heading"
            className="text-base font-semibold text-zinc-900 dark:text-zinc-100"
          >
            Historique
          </h2>

          <div className="w-full sm:w-52">
            <label htmlFor="sessions-status-filter" className="sr-only">
              Filtrer l’historique
            </label>
            <Select
              id="sessions-status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as 'all' | SessionStatus)}
            >
              <option value="all">Toutes les séances</option>
              <option value="completed">Achevées</option>
              <option value="in_progress">En cours</option>
              <option value="cancelled">Annulées</option>
            </Select>
          </div>
        </div>

        {sessions.length > 0 && availableCategories.length > 0 && (
          <div role="group" aria-label="Filtrer l’historique par catégorie" className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              aria-pressed={categoryFilter === 'all'}
              onClick={() => setCategoryFilter('all')}
              className={cn(
                'inline-flex min-h-11 items-center rounded-full px-3 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400',
                categoryFilter === 'all'
                  ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                  : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700',
              )}
            >
              Toutes
            </button>
            {availableCategories.map((category) => {
              const isActive = categoryFilter === category;
              return (
                <button
                  key={category}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() =>
                    setCategoryFilter((prev) => (prev === category ? 'all' : category))
                  }
                  className={cn(
                    'inline-flex min-h-11 items-center rounded-full px-3 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400',
                    isActive
                      ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                      : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700',
                  )}
                >
                  {category}
                </button>
              );
            })}
          </div>
        )}

        {sessions.length === 0 ? (
          <EmptyState
            icon={<Icon icon={Timer02Icon} size={17} />}
            title="Aucune séance enregistrée"
            action={
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => setFormMode('start')}
              >
                Démarrer une séance
              </Button>
            }
          />
        ) : filteredSessions.length === 0 ? (
          <EmptyState
            icon={<Icon icon={Timer02Icon} size={17} />}
            title="Aucune séance pour ce filtre"
            action={
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  setStatusFilter('all');
                  setCategoryFilter('all');
                }}
              >
                Afficher toutes les séances
              </Button>
            }
          />
        ) : (
          <div className="space-y-5">
            {groupedJournalDays.map(({ dateKey, daySessions, dayCompletedMinutes }) => (
              <div key={dateKey} className="space-y-2.5">
                <div className="flex items-center justify-between gap-2 px-1">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                    {formatJournalDayLabel(dateKey, todayKey, yesterdayKey)}
                  </h3>
                  {dayCompletedMinutes > 0 && (
                    <span className="text-xs font-medium tabular-nums text-zinc-500 dark:text-zinc-400">
                      {formatDuration(dayCompletedMinutes)}
                    </span>
                  )}
                </div>

                <ul className="space-y-2">
                  {daySessions.map((session) => {
                    const statusMeta = SESSION_STATUS_META[session.status];
                    const durationMinutes = getSessionDurationMinutes(session);
                    const tone = getSessionCategoryTone(session.category);
                    const linkedTaskTitle = session.taskId
                      ? taskTitleById.get(session.taskId)
                      : undefined;
                    const linkedProjectName = session.projectId
                      ? projectNameById.get(session.projectId)
                      : undefined;
                    const linkedModuleTitle = session.moduleId
                      ? moduleTitleById.get(session.moduleId)
                      : undefined;
                    const linkedLessonTitle = session.lessonId
                      ? lessonTitleById.get(session.lessonId)
                      : undefined;
                    const linkedSkillName = session.skillId
                      ? skillNameById.get(session.skillId)
                      : undefined;

                    return (
                      <li
                        key={session.id}
                        className="flex flex-col gap-3 rounded-xl bg-zinc-50/90 p-3.5 sm:flex-row sm:items-start sm:justify-between dark:bg-zinc-800/55"
                      >
                        <div className="flex min-w-0 items-stretch gap-3">
                          <div className="w-20 shrink-0 text-right tabular-nums">
                            <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                              {session.status === 'completed'
                                ? formatDuration(durationMinutes)
                                : statusMeta.label}
                            </p>
                            <p className="mt-0.5 text-[11px] text-zinc-500 dark:text-zinc-400">
                              {formatTimeFr(session.startedAt)}
                              {session.endedAt ? `–${formatTimeFr(session.endedAt)}` : ''}
                            </p>
                          </div>

                          <span
                            aria-hidden="true"
                            className={cn(
                              'w-1 shrink-0 self-stretch rounded-full',
                              session.status === 'cancelled'
                                ? 'bg-zinc-300 dark:bg-zinc-700'
                                : tone.bar,
                            )}
                          />

                          <div className="min-w-0 flex-1 space-y-1.5">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <h4 className="line-clamp-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                                {session.title}
                              </h4>
                              <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                                {session.category}
                              </span>
                              {session.status !== 'completed' && (
                                <Badge variant={statusMeta.badgeVariant}>{statusMeta.label}</Badge>
                              )}
                            </div>

                            {session.result && (
                              <p className="line-clamp-2 text-xs leading-relaxed text-zinc-700 dark:text-zinc-300">
                                {session.result}
                              </p>
                            )}

                            {(session.deliverableSummary || session.blockers) && (
                              <div className="space-y-0.5 text-[11px] text-zinc-600 dark:text-zinc-400">
                                {session.deliverableSummary && (
                                  <p>Preuve / livrable : {session.deliverableSummary}</p>
                                )}
                                {session.blockers && <p>Difficultés : {session.blockers}</p>}
                              </div>
                            )}

                            {(linkedTaskTitle ||
                              linkedProjectName ||
                              linkedModuleTitle ||
                              linkedLessonTitle ||
                              linkedSkillName) && (
                              <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                                {linkedTaskTitle && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[11px] text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                                    <Icon icon={CheckmarkSquare02Icon} size={12} />
                                    {linkedTaskTitle}
                                  </span>
                                )}
                                {linkedProjectName && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[11px] text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                                    <Icon icon={FolderKanbanIcon} size={12} />
                                    {linkedProjectName}
                                  </span>
                                )}
                                {linkedModuleTitle && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[11px] text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                                    <Icon icon={BookOpen01Icon} size={12} />
                                    {linkedModuleTitle}
                                  </span>
                                )}
                                {linkedLessonTitle && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[11px] text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                                    <Icon icon={File02Icon} size={12} />
                                    {linkedLessonTitle}
                                  </span>
                                )}
                                {linkedSkillName && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[11px] text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                                    <Icon icon={Award02Icon} size={12} />
                                    {linkedSkillName}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="shrink-0 self-end sm:self-start">
                          <InlineConfirm
                            triggerLabel="Supprimer"
                            ariaLabel={`Supprimer ${session.title}`}
                            onConfirm={() => handleDelete(session)}
                          />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
