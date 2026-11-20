import { useMemo, useState, type FormEvent } from 'react';
import {
  Add01Icon,
  AiChat02Icon,
  ArrowRight01Icon,
  Award02Icon,
  BookOpen01Icon,
  Calendar03Icon,
  CheckmarkSquare02Icon,
  File02Icon,
  FolderKanbanIcon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button, buttonClasses } from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import { formatDateFr, formatDateTimeFr, formatTimeFr } from '../../lib/date';
import { useAiStore } from '../../state/AiStoreContext';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type { ScheduleEventType, TaskPriority } from '../../types/domain';
import {
  getConflictingEventIds,
  getEventsForLocalDate,
  SCHEDULE_EVENT_TYPE_META,
} from '../schedule/scheduleUtils';
import {
  computeSessionSummary,
  formatDuration,
  getSessionDurationMinutes,
} from '../sessions/sessionUtils';
import {
  computeTaskSummary,
  isActiveTaskStatus,
  isTaskOverdue,
  sortTasksByUrgency,
  TASK_PRIORITY_META,
} from '../tasks/taskUtils';
import { PriorityHero } from './PriorityHero';

const PRIORITY_DOT_CLASS: Record<TaskPriority, string> = {
  critical: 'bg-rose-500',
  high: 'bg-amber-500',
  normal: 'bg-teal-600 dark:bg-teal-400',
  low: 'bg-zinc-400',
};

const EVENT_ACCENT_BAR: Record<ScheduleEventType, string> = {
  course: 'bg-teal-600 dark:bg-teal-400',
  learning: 'bg-emerald-600 dark:bg-emerald-400',
  project: 'bg-amber-500 dark:bg-amber-400',
  personal: 'bg-zinc-400 dark:bg-zinc-500',
  other: 'bg-zinc-300 dark:bg-zinc-600',
};

function formatTodayHeading(date = new Date()): string {
  const formatted = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(date);
  return formatted.charAt(0).toUpperCase() + formatted.slice(1);
}

/**
 * Tableau de bord quotidien : vue d'ensemble mobile-first orientée action
 * autour de la priorité active, des tâches, des créneaux du jour et du copilote.
 */
export function DashboardPage() {
  const {
    profile,
    activePriorityTitle,
    activePriorityTaskId,
    activePriorityProjectId,
    tasks,
    sessions,
    scheduleEvents,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    setActivePriority,
    setTaskStatus,
    createTask,
    startSession,
  } = useStudyStore();
  const { paths, lessons, skills, projects } = useLearningStore();
  const { proposals, reports } = useAiStore();

  const [feedback, setFeedback] = useState<string | null>(null);
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
  const [quickTaskTitle, setQuickTaskTitle] = useState('');
  const [quickTaskPriority, setQuickTaskPriority] = useState<TaskPriority>('normal');
  const [isCreatingTask, setIsCreatingTask] = useState(false);

  const pendingAiProposals = useMemo(
    () => proposals.filter((p) => p.status === 'pending'),
    [proposals],
  );
  const pendingAiProposalsCount = pendingAiProposals.length;
  const latestAiReport = useMemo(() => reports[0] ?? null, [reports]);

  const taskSummary = useMemo(() => computeTaskSummary(tasks), [tasks]);
  const sessionSummary = useMemo(() => computeSessionSummary(sessions), [sessions]);
  const todayEvents = useMemo(
    () => getEventsForLocalDate(scheduleEvents, new Date()),
    [scheduleEvents],
  );
  const todayConflictingIds = useMemo(() => getConflictingEventIds(todayEvents), [todayEvents]);

  const activeTasks = useMemo(
    () => sortTasksByUrgency(tasks.filter((task) => isActiveTaskStatus(task.status))),
    [tasks],
  );
  const topActiveTasks = useMemo(() => activeTasks.slice(0, 5), [activeTasks]);

  const linkedPriorityTask = useMemo(
    () =>
      activePriorityTaskId
        ? (tasks.find((task) => task.id === activePriorityTaskId) ?? null)
        : null,
    [tasks, activePriorityTaskId],
  );

  const activeProjects = useMemo(
    () => projects.filter((p) => p.status === 'active'),
    [projects],
  );

  const linkedPriorityProject = useMemo(
    () =>
      activePriorityProjectId
        ? (projects.find((project) => project.id === activePriorityProjectId) ?? null)
        : null,
    [projects, activePriorityProjectId],
  );

  const inProgressSessions = useMemo(
    () => sessions.filter((session) => session.status === 'in_progress'),
    [sessions],
  );

  const recentCompletedSessions = useMemo(
    () =>
      sessions
        .filter((session) => session.status === 'completed' && session.endedAt !== null)
        .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
        .slice(0, 3),
    [sessions],
  );

  const completedLessonsCount = useMemo(
    () => lessons.filter((lesson) => lesson.status === 'completed').length,
    [lessons],
  );
  const learningProgressPct =
    lessons.length > 0 ? Math.round((completedLessonsCount / lessons.length) * 100) : 0;

  const hasLearningOverview =
    paths.length > 0 || activeProjects.length > 0 || skills.length > 0;

  const todayLabel = formatTodayHeading();
  const displaySubtitle =
    profile.displayName && profile.displayName !== 'Utilisateur'
      ? `${profile.displayName} · ${todayLabel}`
      : todayLabel;

  const handleQuickAddSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = quickTaskTitle.trim();
    if (trimmed.length < 2 || isCreatingTask) return;

    setIsCreatingTask(true);
    try {
      const ok = await createTask({
        title: trimmed,
        description: '',
        priority: quickTaskPriority,
        status: 'todo',
        dueDate: '',
        projectId: '',
        moduleId: '',
      });
      if (ok) {
        setQuickTaskTitle('');
        setQuickTaskPriority('normal');
        setIsQuickAddOpen(false);
        setFeedback(`Tâche « ${trimmed} » ajoutée.`);
      }
    } finally {
      setIsCreatingTask(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <header>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 sm:text-2xl dark:text-zinc-50">
            Tableau de bord
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
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 sm:text-2xl dark:text-zinc-50">
            Tableau de bord
          </h1>
        </header>
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  const activeSession = inProgressSessions[0] ?? null;
  const nowMs = Date.now();

  return (
    <div className="space-y-3.5 sm:space-y-5">
      {/* En-tête temporel */}
      <header className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 sm:text-2xl dark:text-zinc-50">
            Tableau de bord
          </h1>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{displaySubtitle}</p>
        </div>

        <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0">
          <Button
            type="button"
            variant={isQuickAddOpen ? 'primary' : 'secondary'}
            size="sm"
            className="shrink-0"
            onClick={() => setIsQuickAddOpen((prev) => !prev)}
          >
            <Icon icon={Add01Icon} size={15} />
            Nouvelle tâche
          </Button>

          <Link to="/ai-coach" className={cn(buttonClasses('ghost', 'sm'), 'shrink-0')}>
            <Icon icon={AiChat02Icon} size={15} />
            <span>Copilote</span>
            {pendingAiProposalsCount > 0 && (
              <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                {pendingAiProposalsCount}
              </span>
            )}
          </Link>
        </div>
      </header>

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Bandeau séance en cours */}
      {activeSession && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-teal-50 px-4 py-3 text-sm text-teal-950 dark:bg-teal-950/50 dark:text-teal-100">
          <div className="flex min-w-0 items-center gap-2.5">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 shrink-0 animate-pulse rounded-full bg-teal-600 dark:bg-teal-400"
            />
            <span className="truncate">
              Séance en cours : <strong>{activeSession.title}</strong> ·{' '}
              <span className="tabular-nums text-teal-800 dark:text-teal-300">
                {formatDuration(getSessionDurationMinutes(activeSession))}
              </span>
            </span>
          </div>
          <Link
            to="/sessions"
            className="shrink-0 text-xs font-semibold text-teal-800 underline dark:text-teal-300"
          >
            Clôturer
          </Link>
        </div>
      )}

      {/* Ruban d'indicateurs quotidiens */}
      <section aria-label="Indicateurs du jour" className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 sm:gap-3">
        <div className="rounded-2xl bg-white p-3 sm:p-4 dark:bg-zinc-900">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Avancement</p>
          <p
            className="mt-0.5 text-lg font-semibold tabular-nums text-zinc-900 sm:mt-1 sm:text-xl dark:text-zinc-50"
            data-testid="dashboard-completion-rate"
          >
            {taskSummary.completionRate} %
          </p>
          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100 sm:mt-2 dark:bg-zinc-800">
            <div
              className="h-full rounded-full bg-teal-600 transition-all dark:bg-teal-400"
              style={{ width: `${taskSummary.completionRate}%` }}
            />
          </div>
          <p className="mt-1 text-[11px] text-zinc-500 sm:mt-1.5 dark:text-zinc-400">
            {taskSummary.doneCount}/{taskSummary.activeCount + taskSummary.doneCount} tâches
          </p>
        </div>

        <div className="rounded-2xl bg-white p-3 sm:p-4 dark:bg-zinc-900">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Temps étudié</p>
          <p
            className="mt-0.5 text-lg font-semibold tabular-nums text-zinc-900 sm:mt-1 sm:text-xl dark:text-zinc-50"
            data-testid="dashboard-sessions-time"
          >
            {sessionSummary.completedCount === 0
              ? '0 min'
              : formatDuration(sessionSummary.totalCompletedMinutes)}
          </p>
          <p className="mt-1.5 text-[11px] text-zinc-500 sm:mt-3.5 dark:text-zinc-400">Temps réel achevé</p>
        </div>

        <div className="rounded-2xl bg-white p-3 sm:p-4 dark:bg-zinc-900">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Séances</p>
          <p
            className="mt-0.5 text-lg font-semibold tabular-nums text-emerald-700 sm:mt-1 sm:text-xl dark:text-emerald-400"
            data-testid="dashboard-sessions-count"
          >
            {sessionSummary.completedCount}
          </p>
          <p className="mt-1.5 text-[11px] text-zinc-500 sm:mt-3.5 dark:text-zinc-400">
            {inProgressSessions.length > 0
              ? `${inProgressSessions.length} en cours`
              : 'Achevées'}
          </p>
        </div>

        <div className="rounded-2xl bg-white p-3 sm:p-4 dark:bg-zinc-900">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Aujourd’hui</p>
          <p className="mt-0.5 text-lg font-semibold tabular-nums text-zinc-900 sm:mt-1 sm:text-xl dark:text-zinc-50">
            {todayEvents.length}
          </p>
          <p className="mt-1.5 text-[11px] text-zinc-500 sm:mt-3.5 dark:text-zinc-400">
            {todayConflictingIds.size > 0
              ? `${todayConflictingIds.size} conflit(s)`
              : todayEvents.length > 1
                ? 'Créneaux planifiés'
                : 'Créneau planifié'}
          </p>
        </div>
      </section>

      {/* Grille asymétrique 12 colonnes */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 lg:items-start">
        {/* Colonne principale */}
        <div className="min-w-0 space-y-5 lg:col-span-7">
          <PriorityHero
            activePriorityTitle={activePriorityTitle}
            activePriorityTaskId={activePriorityTaskId}
            activePriorityProjectId={activePriorityProjectId}
            activeTasks={activeTasks}
            activeProjects={activeProjects}
            linkedPriorityTask={linkedPriorityTask}
            linkedPriorityProject={linkedPriorityProject}
            hasInProgressSession={inProgressSessions.length > 0}
            onSavePriority={setActivePriority}
            onCompleteLinkedTask={async (task) => {
              if (await setTaskStatus(task.id, 'done')) {
                setFeedback(`« ${task.title} » terminée.`);
              }
            }}
            onStartFocusSession={async () => {
              if (!activePriorityTitle) return;
              const ok = await startSession({
                title: activePriorityTitle,
                category: linkedPriorityProject ? 'Projet' : 'Apprentissage',
                taskId: linkedPriorityTask?.id ?? '',
                projectId: linkedPriorityProject?.id ?? '',
                moduleId: '',
                lessonId: '',
                skillId: '',
              });
              if (ok) {
                setFeedback(`Séance lancée pour « ${activePriorityTitle} ».`);
              }
            }}
            onFeedback={setFeedback}
          />

          {/* Tâches prioritaires + capture rapide */}
          <section
            aria-labelledby="dashboard-tasks-heading"
            className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <h2
                  id="dashboard-tasks-heading"
                  className="text-sm font-semibold text-zinc-900 dark:text-zinc-100"
                >
                  Tâches prioritaires
                </h2>
                <span className="text-xs text-zinc-500 dark:text-zinc-400">
                  {taskSummary.activeCount} active{taskSummary.activeCount > 1 ? 's' : ''}
                </span>
                {taskSummary.overdueCount > 0 && (
                  <Badge variant="danger">{taskSummary.overdueCount} en retard</Badge>
                )}
              </div>

              <div className="flex items-center gap-1.5">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsQuickAddOpen((prev) => !prev)}
                >
                  <Icon icon={Add01Icon} size={14} />
                  Rapide
                </Button>
                <Link to="/tasks" className={buttonClasses('ghost', 'sm')}>
                  Tout voir
                </Link>
              </div>
            </div>

            {isQuickAddOpen && (
              <form
                onSubmit={handleQuickAddSubmit}
                className="mb-4 flex flex-col gap-2 rounded-xl bg-zinc-50 p-3 sm:flex-row sm:items-center dark:bg-zinc-800/70"
              >
                <Input
                  aria-label="Nouvelle tâche rapide"
                  placeholder="Ajouter une tâche…"
                  value={quickTaskTitle}
                  onChange={(e) => setQuickTaskTitle(e.target.value)}
                  className="flex-1 bg-white dark:bg-zinc-900"
                />
                <Select
                  aria-label="Priorité de la tâche rapide"
                  value={quickTaskPriority}
                  onChange={(e) => setQuickTaskPriority(e.target.value as TaskPriority)}
                  className="bg-white sm:w-32 dark:bg-zinc-900"
                >
                  <option value="normal">Normale</option>
                  <option value="high">Haute</option>
                  <option value="critical">Critique</option>
                  <option value="low">Basse</option>
                </Select>
                <div className="flex items-center gap-2">
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={isCreatingTask}
                    disabled={quickTaskTitle.trim().length < 2 || isCreatingTask}
                  >
                    Ajouter
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsQuickAddOpen(false)}
                  >
                    Fermer
                  </Button>
                </div>
              </form>
            )}

            {tasks.length === 0 ? (
              <EmptyState
                icon={<Icon icon={CheckmarkSquare02Icon} size={17} />}
                title="Aucune tâche enregistrée"
                action={
                  <Link to="/tasks" className={buttonClasses('secondary', 'sm')}>
                    Gérer les tâches
                  </Link>
                }
              />
            ) : topActiveTasks.length === 0 ? (
              <EmptyState
                icon={
                  <Icon
                    icon={CheckmarkSquare02Icon}
                    size={17}
                    className="text-emerald-700 dark:text-emerald-400"
                  />
                }
                title="Aucune tâche active en attente"
                action={
                  <Link to="/tasks" className={buttonClasses('secondary', 'sm')}>
                    Ouvrir les tâches
                  </Link>
                }
              />
            ) : (
              <ul className="space-y-2">
                {topActiveTasks.map((task) => {
                  const priorityMeta = TASK_PRIORITY_META[task.priority];
                  const overdue = isTaskOverdue(task);
                  return (
                    <li
                      key={task.id}
                      className="flex items-center justify-between gap-3 rounded-xl bg-zinc-50/80 px-3.5 py-2.5 dark:bg-zinc-800/60"
                    >
                      <div className="flex min-w-0 items-start gap-2.5">
                        <span
                          aria-hidden="true"
                          className={cn(
                            'mt-1.5 h-2 w-2 shrink-0 rounded-full',
                            PRIORITY_DOT_CLASS[task.priority],
                          )}
                        />
                        <div className="min-w-0 space-y-1">
                          <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
                            {task.title}
                          </p>
                          <div className="flex flex-wrap items-center gap-1.5">
                            <Badge variant={priorityMeta.badgeVariant}>{priorityMeta.label}</Badge>
                            {overdue && <Badge variant="danger">En retard</Badge>}
                            {task.dueAt && (
                              <span className="text-xs text-zinc-500 dark:text-zinc-400">
                                {formatDateFr(task.dueAt)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        aria-label={`Terminer ${task.title}`}
                        onClick={async () => {
                          if (await setTaskStatus(task.id, 'done')) {
                            setFeedback(`« ${task.title} » terminée.`);
                          }
                        }}
                      >
                        Terminer
                      </Button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {/* Séances récentes */}
          <section
            aria-labelledby="dashboard-sessions-heading"
            className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
          >
            <div className="mb-4 flex items-center justify-between gap-2">
              <h2
                id="dashboard-sessions-heading"
                className="text-sm font-semibold text-zinc-900 dark:text-zinc-100"
              >
                Séances récentes
              </h2>
              <Link to="/sessions" className={buttonClasses('ghost', 'sm')}>
                Séances
              </Link>
            </div>

            {recentCompletedSessions.length === 0 ? (
              <EmptyState
                icon={<Icon icon={Timer02Icon} size={17} />}
                title="Aucune séance achevée"
                action={
                  <Link to="/sessions" className={buttonClasses('secondary', 'sm')}>
                    Ouvrir les séances
                  </Link>
                }
              />
            ) : (
              <ul className="space-y-2">
                {recentCompletedSessions.map((session) => (
                  <li
                    key={session.id}
                    className="rounded-xl bg-zinc-50/80 px-3.5 py-2.5 dark:bg-zinc-800/60"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
                        {session.title}
                      </p>
                      <Badge variant="primary">
                        {formatDuration(getSessionDurationMinutes(session))}
                      </Badge>
                    </div>
                    <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                      {session.category} · {formatDateTimeFr(session.startedAt)}
                    </p>
                    {session.result && (
                      <p className="mt-1 line-clamp-1 text-xs text-zinc-600 dark:text-zinc-300">
                        {session.result}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        {/* Colonne secondaire */}
        <div className="min-w-0 space-y-5 lg:col-span-5">
          {/* Planning d'aujourd'hui */}
          <section
            aria-labelledby="dashboard-today-heading"
            className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
          >
            <div className="mb-4 flex items-center justify-between gap-2">
              <div>
                <h2
                  id="dashboard-today-heading"
                  className="text-sm font-semibold text-zinc-900 dark:text-zinc-100"
                >
                  Aujourd’hui
                </h2>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {todayEvents.length} créneau{todayEvents.length > 1 ? 'x' : ''}
                </p>
              </div>
              <Link to="/planning" className={buttonClasses('ghost', 'sm')}>
                Planning
              </Link>
            </div>

            {todayEvents.length === 0 ? (
              <EmptyState
                icon={<Icon icon={Calendar03Icon} size={17} />}
                title="Aucun créneau planifié aujourd’hui"
                action={
                  <Link to="/planning" className={buttonClasses('secondary', 'sm')}>
                    Voir le planning
                  </Link>
                }
              />
            ) : (
              <ul className="space-y-2.5">
                {todayEvents.map((event) => {
                  const typeMeta = SCHEDULE_EVENT_TYPE_META[event.type];
                  const hasConflict = todayConflictingIds.has(event.id);
                  const startMs = new Date(event.startsAt).getTime();
                  const endMs = new Date(event.endsAt).getTime();
                  const isOngoing = nowMs >= startMs && nowMs <= endMs;

                  return (
                    <li
                      key={event.id}
                      className="flex items-stretch gap-3 rounded-xl bg-zinc-50/80 px-3 py-2.5 dark:bg-zinc-800/60"
                    >
                      <div className="w-12 shrink-0 text-right tabular-nums">
                        <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                          {formatTimeFr(event.startsAt)}
                        </p>
                        <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                          {formatTimeFr(event.endsAt)}
                        </p>
                      </div>

                      <span
                        aria-hidden="true"
                        className={cn(
                          'w-1 shrink-0 self-stretch rounded-full',
                          EVENT_ACCENT_BAR[event.type],
                        )}
                      />

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
                          {event.title}
                        </p>
                        <div className="mt-1 flex flex-wrap items-center gap-1.5">
                          <Badge variant={typeMeta.badgeVariant}>{typeMeta.label}</Badge>
                          {isOngoing && <Badge variant="success">En cours</Badge>}
                          {hasConflict && <Badge variant="danger">Conflit</Badge>}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {/* Copilote */}
          <section
            aria-labelledby="dashboard-copilot-heading"
            className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
          >
            <div className="mb-4 flex items-center justify-between gap-2">
              <div>
                <h2
                  id="dashboard-copilot-heading"
                  className="text-sm font-semibold text-zinc-900 dark:text-zinc-100"
                >
                  Copilote
                </h2>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  Briefing, bilan et propositions
                </p>
              </div>
              {pendingAiProposalsCount > 0 && (
                <Badge variant="warning">{pendingAiProposalsCount} en attente</Badge>
              )}
            </div>

            {pendingAiProposals.length > 0 ? (
              <div className="rounded-xl bg-amber-50/80 p-3.5 dark:bg-amber-950/35">
                <p className="text-xs font-medium text-amber-800 dark:text-amber-300">
                  {pendingAiProposals.length === 1
                    ? '1 action attend votre validation'
                    : `${pendingAiProposals.length} actions attendent votre validation`}
                </p>
                <p className="mt-1 truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                  {pendingAiProposals[0].title}
                </p>
                <div className="mt-3">
                  <Link to="/ai-coach" className={buttonClasses('primary', 'sm')}>
                    Examiner
                  </Link>
                </div>
              </div>
            ) : latestAiReport ? (
              <div className="flex items-start justify-between gap-3 rounded-xl bg-zinc-50 p-3.5 dark:bg-zinc-800/70">
                <div className="flex min-w-0 items-start gap-2.5">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700 dark:bg-teal-950/50 dark:text-teal-400">
                    <Icon icon={File02Icon} size={16} />
                  </div>
                  <div className="min-w-0">
                    <Badge variant={latestAiReport.type === 'daily_briefing' ? 'primary' : 'neutral'}>
                      {latestAiReport.type === 'daily_briefing'
                        ? 'Briefing quotidien'
                        : 'Bilan hebdomadaire'}
                    </Badge>
                    <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                      Généré le {formatDateTimeFr(latestAiReport.createdAt)}
                    </p>
                  </div>
                </div>
                <Link to="/ai-coach" className={buttonClasses('secondary', 'sm')}>
                  Consulter
                </Link>
              </div>
            ) : (
              <EmptyState
                icon={
                  <Icon
                    icon={AiChat02Icon}
                    size={17}
                    className="text-teal-700 dark:text-teal-400"
                  />
                }
                title="Assistant de planification"
                action={
                  <Link to="/ai-coach" className={buttonClasses('secondary', 'sm')}>
                    Ouvrir le copilote
                  </Link>
                }
              />
            )}
          </section>

          {/* Cap & apprentissage (conditionnel) */}
          {hasLearningOverview && (
            <section
              aria-labelledby="dashboard-learning-heading"
              className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
            >
              <h2
                id="dashboard-learning-heading"
                className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100"
              >
                Cap &amp; apprentissage
              </h2>

              <div className="space-y-2.5">
                {paths.length > 0 && (
                  <Link
                    to="/learning"
                    className="block rounded-xl bg-zinc-50 p-3.5 transition-colors hover:bg-zinc-100 dark:bg-zinc-800/70 dark:hover:bg-zinc-800"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                        <Icon
                          icon={BookOpen01Icon}
                          size={15}
                          className="text-teal-700 dark:text-teal-400"
                        />
                        <span>Parcours</span>
                      </div>
                      <Icon
                        icon={ArrowRight01Icon}
                        size={14}
                        className="text-zinc-400 dark:text-zinc-500"
                      />
                    </div>
                    <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
                      {completedLessonsCount}/{lessons.length} leçon{lessons.length > 1 ? 's' : ''}{' '}
                      terminée{completedLessonsCount > 1 ? 's' : ''}
                    </p>
                    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
                      <div
                        className="h-full rounded-full bg-teal-600 dark:bg-teal-400"
                        style={{ width: `${learningProgressPct}%` }}
                      />
                    </div>
                  </Link>
                )}

                {activeProjects.length > 0 && (
                  <Link
                    to="/projects"
                    className="block rounded-xl bg-zinc-50 p-3.5 transition-colors hover:bg-zinc-100 dark:bg-zinc-800/70 dark:hover:bg-zinc-800"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                        <Icon
                          icon={FolderKanbanIcon}
                          size={15}
                          className="text-teal-700 dark:text-teal-400"
                        />
                        <span>
                          {activeProjects.length} projet{activeProjects.length > 1 ? 's' : ''} actif
                          {activeProjects.length > 1 ? 's' : ''}
                        </span>
                      </div>
                      <Icon
                        icon={ArrowRight01Icon}
                        size={14}
                        className="text-zinc-400 dark:text-zinc-500"
                      />
                    </div>
                    {activeProjects[0].nextAction && (
                      <p className="mt-1 truncate text-xs text-zinc-600 dark:text-zinc-400">
                        Prochaine action : {activeProjects[0].nextAction}
                      </p>
                    )}
                  </Link>
                )}

                {skills.length > 0 && (
                  <Link
                    to="/skills"
                    className="flex items-center justify-between gap-2 rounded-xl bg-zinc-50 p-3.5 transition-colors hover:bg-zinc-100 dark:bg-zinc-800/70 dark:hover:bg-zinc-800"
                  >
                    <div className="flex items-center gap-2 text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                      <Icon
                        icon={Award02Icon}
                        size={15}
                        className="text-teal-700 dark:text-teal-400"
                      />
                      <span>
                        {skills.length} compétence{skills.length > 1 ? 's' : ''} suivie
                        {skills.length > 1 ? 's' : ''}
                      </span>
                    </div>
                    <Icon
                      icon={ArrowRight01Icon}
                      size={14}
                      className="text-zinc-400 dark:text-zinc-500"
                    />
                  </Link>
                )}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
