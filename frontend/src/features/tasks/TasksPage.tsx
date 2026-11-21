import { useMemo, useState, type FormEvent } from 'react';
import {
  Add01Icon,
  Cancel01Icon,
  CheckmarkSquare02Icon,
  GridViewIcon,
  LeftToRightListBulletIcon,
  RotateLeft01Icon,
  Search01Icon,
} from '@hugeicons/core-free-icons';
import { Button, buttonClasses } from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import { Link } from 'react-router-dom';
import type { Task, TaskPriority, TaskStatus } from '../../types/domain';
import { TaskCard } from './TaskCard';
import { TaskForm } from './TaskForm';
import type { TaskFormValues } from './taskSchema';
import {
  computeTaskSummary,
  DEFAULT_TASK_FILTERS,
  filterTasks,
  sortTasksByUrgency,
  TASK_STATUS_META,
  type TaskDueFilter,
  type TaskFilters,
  type TaskStatusFilter,
} from './taskUtils';

type ViewMode = 'list' | 'board';

const LIST_STATUS_ORDER: TaskStatus[] = ['in_progress', 'todo', 'parked', 'done', 'cancelled'];
const BOARD_BASE_STATUSES: TaskStatus[] = ['todo', 'in_progress', 'parked', 'done'];

const STATUS_GROUP_META: Record<TaskStatus, { label: string; dot: string }> = {
  in_progress: { label: 'En cours', dot: 'bg-teal-600 dark:bg-teal-400' },
  todo: { label: 'À faire', dot: 'bg-zinc-400 dark:bg-zinc-500' },
  parked: { label: 'Parking', dot: 'bg-amber-500 dark:bg-amber-400' },
  done: { label: 'Terminées', dot: 'bg-emerald-600 dark:bg-emerald-400' },
  cancelled: { label: 'Annulées', dot: 'bg-rose-500 dark:bg-rose-400' },
};

export function TasksPage() {
  const {
    tasks,
    activePriorityTaskId,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    createTask,
    updateTask,
    setTaskStatus,
    deleteTask,
    setActivePriority,
  } = useStudyStore();
  const { projects, modules } = useLearningStore();

  const projectNameById = useMemo(
    () => new Map(projects.map((p) => [p.id, p.name])),
    [projects],
  );
  const moduleTitleById = useMemo(
    () => new Map(modules.map((m) => [m.id, m.title])),
    [modules],
  );

  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [isCreating, setIsCreating] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [filters, setFilters] = useState<TaskFilters>(DEFAULT_TASK_FILTERS);
  const [feedback, setFeedback] = useState<string | null>(null);

  const [quickTitle, setQuickTitle] = useState('');
  const [quickPriority, setQuickPriority] = useState<TaskPriority>('normal');
  const [isQuickSubmitting, setIsQuickSubmitting] = useState(false);

  const summary = useMemo(() => computeTaskSummary(tasks), [tasks]);
  const visibleTasks = useMemo(
    () => sortTasksByUrgency(filterTasks(tasks, filters)),
    [tasks, filters],
  );

  const groupedByStatus = useMemo(() => {
    const groups: Record<TaskStatus, Task[]> = {
      in_progress: [],
      todo: [],
      parked: [],
      done: [],
      cancelled: [],
    };
    for (const task of visibleTasks) {
      groups[task.status].push(task);
    }
    return groups;
  }, [visibleTasks]);

  const boardStatuses = useMemo(
    () =>
      groupedByStatus.cancelled.length > 0
        ? [...BOARD_BASE_STATUSES, 'cancelled' as const]
        : BOARD_BASE_STATUSES,
    [groupedByStatus.cancelled.length],
  );

  const hasActiveFilters =
    filters.status !== 'all' ||
    filters.priority !== 'all' ||
    filters.due !== 'all' ||
    filters.search.trim() !== '';

  const isKpiActive = filters.status === 'active' && filters.due === 'all';
  const isKpiOverdue = filters.status === 'active' && filters.due === 'overdue';
  const isKpiDone = filters.status === 'done' && filters.due === 'all';
  const isKpiParked = filters.status === 'parked' && filters.due === 'all';

  const handleOpenCreate = () => {
    setEditingTask(null);
    setIsCreating(true);
  };

  const handleFormSubmit = async (values: TaskFormValues) => {
    if (editingTask) {
      if (await updateTask(editingTask.id, values)) {
        setFeedback(`Tâche « ${values.title.trim()} » mise à jour.`);
        setEditingTask(null);
      }
      return;
    }

    if (await createTask(values)) {
      setFeedback(`Tâche « ${values.title.trim()} » ajoutée.`);
      setIsCreating(false);
    }
  };

  const handleQuickAddSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = quickTitle.trim();
    if (trimmed.length < 2 || isQuickSubmitting) return;

    setIsQuickSubmitting(true);
    try {
      const ok = await createTask({
        title: trimmed,
        description: '',
        priority: quickPriority,
        status: 'todo',
        dueDate: '',
        projectId: '',
        moduleId: '',
      });
      if (ok) {
        setQuickTitle('');
        setQuickPriority('normal');
        setFeedback(`Tâche « ${trimmed} » ajoutée.`);
      }
    } finally {
      setIsQuickSubmitting(false);
    }
  };

  const handleStatusChange = async (task: Task, nextStatus: TaskStatus) => {
    if (await setTaskStatus(task.id, nextStatus)) {
      const label = TASK_STATUS_META[nextStatus].label.toLowerCase();
      setFeedback(`Tâche « ${task.title} » marquée comme ${label}.`);
    }
  };

  const handleSetPrimary = async (task: Task) => {
    if (await setActivePriority(task.title, task.id)) {
      setFeedback(`« ${task.title} » définie comme priorité.`);
    }
  };

  const handleDelete = async (task: Task) => {
    if (await deleteTask(task.id)) {
      if (editingTask?.id === task.id) {
        setEditingTask(null);
      }
      setFeedback(`Tâche « ${task.title} » supprimée.`);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <header>
          <h1 className="ui-page-title">
            Tâches
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
            Tâches
          </h1>
        </header>
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  return (
    <div className="space-y-3.5 sm:space-y-5">
      {/* En-tête */}
      <header className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="min-w-0">
          <h1 className="ui-page-title">
            Tâches
          </h1>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            {summary.activeCount} active{summary.activeCount > 1 ? 's' : ''} ·{' '}
            {summary.completionRate} % achevé
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div role="group" aria-label="Changer la vue des tâches" className="inline-flex items-center gap-1 rounded-xl bg-zinc-100 p-1 dark:bg-zinc-900">
            <button
              type="button"
              aria-pressed={viewMode === 'list'}
              onClick={() => setViewMode('list')}
              className={cn(
                'inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400 sm:px-3',
                viewMode === 'list'
                  ? 'bg-white text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100'
                  : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200',
              )}
            >
              <Icon icon={LeftToRightListBulletIcon} size={14} />
              Liste
            </button>
            <button
              type="button"
              aria-pressed={viewMode === 'board'}
              onClick={() => setViewMode('board')}
              className={cn(
                'inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400 sm:px-3',
                viewMode === 'board'
                  ? 'bg-white text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100'
                  : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200',
              )}
            >
              <Icon icon={GridViewIcon} size={14} />
              Tableau
            </button>
          </div>

          <Link
            to={"/ai-coach?prompt=" + encodeURIComponent("Analyse ma priorité active, mes échéances et ma charge actuelle. Propose les tâches concrètes nécessaires, limite les actions critiques à trois et place les idées secondaires dans le parking. Présente les tâches à valider avant toute création.")}
            className={buttonClasses('primary', 'sm')}
          >
            <Icon icon={CheckmarkSquare02Icon} size={15} />
            Demander au Copilote
          </Link>
          <details className="relative">
            <summary aria-label="Options des tâches" className="inline-flex min-h-11 cursor-pointer list-none items-center rounded-lg bg-zinc-100 px-3 text-xs font-semibold text-zinc-600 hover:bg-zinc-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 dark:focus-visible:outline-teal-400">
              Plus
            </summary>
            <div className="absolute right-0 z-30 mt-2 w-52 rounded-xl border border-zinc-200 bg-white p-2 shadow-lg dark:border-zinc-700 dark:bg-zinc-900">
              <Button type="button" variant="ghost" size="sm" className="min-h-11 w-full justify-start" onClick={handleOpenCreate}>
                <Icon icon={Add01Icon} size={14} />
                Créer manuellement
              </Button>
            </div>
          </details>
        </div>
      </header>

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Tuiles KPI cliquables comme raccourcis de filtre */}
      <section aria-label="Indicateurs des tâches" className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 sm:gap-3">
        <button
          type="button"
          aria-pressed={isKpiActive}
          aria-label={`Actives (${summary.activeCount}) — filtrer`}
          onClick={() =>
            setFilters((prev) => ({
              ...prev,
              status: isKpiActive ? 'all' : 'active',
              due: 'all',
            }))
          }
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            isKpiActive
              ? 'bg-teal-50 dark:bg-teal-950/45'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Actives</p>
          <p
            className="mt-0.5 text-xl font-semibold tabular-nums text-zinc-900 sm:mt-1 sm:text-2xl dark:text-zinc-50"
            data-testid="stat-active"
          >
            {summary.activeCount}
          </p>
        </button>

        <button
          type="button"
          aria-pressed={isKpiOverdue}
          aria-label={`En retard (${summary.overdueCount}) — filtrer`}
          onClick={() =>
            setFilters((prev) => ({
              ...prev,
              status: isKpiOverdue ? 'all' : 'active',
              due: isKpiOverdue ? 'all' : 'overdue',
            }))
          }
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            isKpiOverdue
              ? 'bg-rose-50 dark:bg-rose-950/45'
              : summary.overdueCount > 0
                ? 'bg-rose-50/60 hover:bg-rose-50 dark:bg-rose-950/30 dark:hover:bg-rose-950/45'
                : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">En retard</p>
          <p
            className={cn(
              'mt-0.5 text-xl font-semibold tabular-nums sm:mt-1 sm:text-2xl',
              summary.overdueCount > 0
                ? 'text-rose-700 dark:text-rose-300'
                : 'text-zinc-900 dark:text-zinc-50',
            )}
            data-testid="stat-overdue"
          >
            {summary.overdueCount}
          </p>
        </button>

        <button
          type="button"
          aria-pressed={isKpiDone}
          aria-label={`Terminées (${summary.doneCount}) — filtrer`}
          onClick={() =>
            setFilters((prev) => ({
              ...prev,
              status: isKpiDone ? 'all' : 'done',
              due: 'all',
            }))
          }
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            isKpiDone
              ? 'bg-teal-50 dark:bg-teal-950/45'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Terminées</p>
            <span className="text-[11px] font-medium tabular-nums text-zinc-400 dark:text-zinc-500">
              {summary.completionRate}%
            </span>
          </div>
          <p
            className="mt-0.5 text-xl font-semibold tabular-nums text-emerald-700 sm:mt-1 sm:text-2xl dark:text-emerald-400"
            data-testid="stat-done"
          >
            {summary.doneCount}
          </p>
          <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-zinc-100 sm:mt-2 dark:bg-zinc-800">
            <div
              className="h-full rounded-full bg-emerald-600 transition-all dark:bg-emerald-400"
              style={{ width: `${summary.completionRate}%` }}
            />
          </div>
        </button>

        <button
          type="button"
          aria-pressed={isKpiParked}
          aria-label={`Parking (${summary.parkedCount}) — filtrer`}
          onClick={() =>
            setFilters((prev) => ({
              ...prev,
              status: isKpiParked ? 'all' : 'parked',
              due: 'all',
            }))
          }
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            isKpiParked
              ? 'bg-teal-50 dark:bg-teal-950/45'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Parking</p>
          <p
            className="mt-0.5 text-xl font-semibold tabular-nums text-amber-700 sm:mt-1 sm:text-2xl dark:text-amber-300"
            data-testid="stat-parked"
          >
            {summary.parkedCount}
          </p>
        </button>
      </section>

      {/* Formulaire complet de création / édition */}
      {(isCreating || editingTask) && (
        <section
          aria-label={editingTask ? 'Modifier la tâche' : 'Nouvelle tâche'}
          className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
        >
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              {editingTask ? 'Modifier la tâche' : 'Nouvelle tâche'}
            </h2>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setIsCreating(false);
                setEditingTask(null);
              }}
            >
              <Icon icon={Cancel01Icon} size={15} />
              Fermer
            </Button>
          </div>

          <TaskForm
            initialTask={editingTask}
            onSubmit={handleFormSubmit}
            onCancel={() => {
              setIsCreating(false);
              setEditingTask(null);
            }}
          />
        </section>
      )}

      {/* Barre unifiée : capture rapide + recherche et filtres */}
      <section
        aria-label="Capture rapide et filtres"
        className="space-y-2.5 rounded-2xl bg-white p-3.5 sm:space-y-3 sm:p-4 dark:bg-zinc-900"
      >
        {!isCreating && !editingTask && (
          <form
            onSubmit={handleQuickAddSubmit}
            className="flex flex-col gap-2 rounded-xl bg-zinc-50 p-2 sm:flex-row sm:items-center sm:p-2.5 dark:bg-zinc-800/70"
          >
            <Input
              aria-label="Capture rapide de tâche"
              placeholder="Ajouter une tâche rapidement…"
              value={quickTitle}
              onChange={(e) => setQuickTitle(e.target.value)}
              className="min-w-0 w-full flex-1 bg-white dark:bg-zinc-900"
            />
            <div className="flex items-center gap-2 sm:contents">
              <Select
                aria-label="Priorité de la tâche rapide"
                value={quickPriority}
                onChange={(e) => setQuickPriority(e.target.value as TaskPriority)}
                className="min-w-0 flex-1 bg-white px-2.5 text-xs sm:w-32 sm:flex-none sm:px-3 sm:text-sm dark:bg-zinc-900"
              >
                <option value="normal">Normale</option>
                <option value="high">Haute</option>
                <option value="critical">Critique</option>
                <option value="low">Basse</option>
              </Select>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                className="shrink-0"
                isLoading={isQuickSubmitting}
                disabled={quickTitle.trim().length < 2 || isQuickSubmitting}
              >
                Ajouter
              </Button>
            </div>
          </form>
        )}

        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative min-w-0">
            <label htmlFor="filter-search" className="sr-only">
              Recherche
            </label>
            <Icon
              icon={Search01Icon}
              size={15}
              className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-zinc-400 dark:text-zinc-500"
            />
            <Input
              id="filter-search"
              type="search"
              value={filters.search}
              placeholder="Rechercher une tâche…"
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              className="pl-9"
            />
          </div>

          <div className="grid grid-cols-2 gap-2 sm:contents">
            <div className="min-w-0">
              <label htmlFor="filter-status" className="sr-only">
                Filtrer par statut
              </label>
              <Select
                id="filter-status"
                value={filters.status}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, status: e.target.value as TaskStatusFilter }))
                }
                className="px-2.5 text-xs sm:px-3 sm:text-sm"
              >
                <option value="all">Tous les statuts</option>
                <option value="active">Actives</option>
                <option value="todo">À faire</option>
                <option value="in_progress">En cours</option>
                <option value="done">Terminées</option>
                <option value="parked">Parking</option>
                <option value="cancelled">Annulées</option>
              </Select>
            </div>

            <div className="min-w-0">
              <label htmlFor="filter-priority" className="sr-only">
                Filtrer par priorité
              </label>
              <Select
                id="filter-priority"
                value={filters.priority}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    priority: e.target.value as 'all' | TaskPriority,
                  }))
                }
                className="px-2.5 text-xs sm:px-3 sm:text-sm"
              >
                <option value="all">Toutes priorités</option>
                <option value="critical">Critique</option>
                <option value="high">Haute</option>
                <option value="normal">Normale</option>
                <option value="low">Basse</option>
              </Select>
            </div>

            <div className="col-span-2 min-w-0 sm:col-span-1">
              <label htmlFor="filter-due" className="sr-only">
                Filtrer par échéance
              </label>
              <Select
                id="filter-due"
                value={filters.due}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, due: e.target.value as TaskDueFilter }))
                }
                className="px-2.5 text-xs sm:px-3 sm:text-sm"
              >
                <option value="all">Toutes échéances</option>
                <option value="overdue">En retard</option>
                <option value="today">Aujourd’hui</option>
                <option value="upcoming">À venir</option>
                <option value="no_due">Sans échéance</option>
              </Select>
            </div>
          </div>
        </div>

        {hasActiveFilters && (
          <div className="flex items-center justify-between pt-1 text-xs text-zinc-600 dark:text-zinc-400">
            <span>
              {visibleTasks.length} résultat{visibleTasks.length > 1 ? 's' : ''}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setFilters(DEFAULT_TASK_FILTERS)}
            >
              <Icon icon={RotateLeft01Icon} size={14} />
              Réinitialiser
            </Button>
          </div>
        )}
      </section>

      {/* Liste groupée ou Tableau Kanban */}
      {tasks.length === 0 ? (
        <EmptyState
          icon={<Icon icon={CheckmarkSquare02Icon} size={17} />}
          title="Aucune tâche pour le moment"
          action={
            <Link
              to={"/ai-coach?prompt=" + encodeURIComponent("Aide-moi à identifier la prochaine action concrète liée à ma priorité active. Propose une tâche mesurable et attends ma validation avant de la créer.")}
              className={buttonClasses('primary', 'md')}
            >
              Définir ma prochaine action avec le Copilote
            </Link>
          }
        />
      ) : visibleTasks.length === 0 ? (
        <EmptyState
          icon={<Icon icon={CheckmarkSquare02Icon} size={17} />}
          title="Aucune tâche ne correspond aux filtres"
          action={
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setFilters(DEFAULT_TASK_FILTERS)}
            >
              Réinitialiser les filtres
            </Button>
          }
        />
      ) : viewMode === 'list' ? (
        <div className="space-y-2.5">
          {LIST_STATUS_ORDER.filter((status) => groupedByStatus[status].length > 0).flatMap(
            (status, nonEmptyIdx) => {
              const groupTasks = groupedByStatus[status];
              const groupMeta = STATUS_GROUP_META[status];

              return [
                <div
                  key={`group-${status}`}
                  className={cn('flex items-center gap-2 px-1', nonEmptyIdx > 0 && 'pt-2.5')}
                >
                  <span
                    aria-hidden="true"
                    className={cn('h-2 w-2 rounded-full', groupMeta.dot)}
                  />
                  <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-300">
                    {groupMeta.label}
                  </h2>
                  <span className="rounded-full bg-zinc-200/70 px-2 py-0.5 text-[11px] font-semibold tabular-nums text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                    {groupTasks.length}
                  </span>
                </div>,
                ...groupTasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    isPrimary={activePriorityTaskId === task.id}
                    linkedProjectName={
                      task.projectId ? projectNameById.get(task.projectId) : undefined
                    }
                    linkedModuleTitle={
                      task.moduleId ? moduleTitleById.get(task.moduleId) : undefined
                    }
                    onStatusChange={handleStatusChange}
                    onSetPrimary={handleSetPrimary}
                    onEdit={(selected) => {
                      setIsCreating(false);
                      setEditingTask(selected);
                    }}
                    onDelete={handleDelete}
                  />
                )),
              ];
            },
          )}
        </div>
      ) : (
        <section
          aria-label="Tableau des tâches"
          className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4"
        >
          {boardStatuses.map((status) => {
            const colTasks = groupedByStatus[status];
            const groupMeta = STATUS_GROUP_META[status];

            return (
              <div
                key={status}
                className="flex min-w-0 flex-col gap-2.5 rounded-2xl bg-white p-4 dark:bg-zinc-900"
              >
                <div className="flex items-center justify-between gap-2 pb-1">
                  <div className="flex items-center gap-2">
                    <span
                      aria-hidden="true"
                      className={cn('h-2 w-2 rounded-full', groupMeta.dot)}
                    />
                    <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-700 dark:text-zinc-200">
                      {groupMeta.label}
                    </h2>
                  </div>
                  <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-semibold tabular-nums text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                    {colTasks.length}
                  </span>
                </div>

                {colTasks.length === 0 ? (
                  <p className="rounded-xl bg-zinc-50 px-3 py-4 text-center text-xs text-zinc-400 dark:bg-zinc-800/50 dark:text-zinc-500">
                    Aucune tâche
                  </p>
                ) : (
                  <div className="space-y-2">
                    {colTasks.map((task) => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        compact
                        isPrimary={activePriorityTaskId === task.id}
                        linkedProjectName={
                          task.projectId ? projectNameById.get(task.projectId) : undefined
                        }
                        linkedModuleTitle={
                          task.moduleId ? moduleTitleById.get(task.moduleId) : undefined
                        }
                        onStatusChange={handleStatusChange}
                        onSetPrimary={handleSetPrimary}
                        onEdit={(selected) => {
                          setIsCreating(false);
                          setEditingTask(selected);
                        }}
                        onDelete={handleDelete}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </section>
      )}
    </div>
  );
}
