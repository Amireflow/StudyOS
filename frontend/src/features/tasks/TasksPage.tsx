import { useMemo, useState } from 'react';
import {
  Add01Icon,
  CheckmarkSquare02Icon,
  RotateLeft01Icon,
  Target02Icon,
} from '@hugeicons/core-free-icons';
import { PageHeader } from '../../components/layout/PageHeader';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { FormField, InlineConfirm, Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import { formatDateFr, formatDateTimeFr } from '../../lib/date';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type { Task, TaskPriority, TaskStatus } from '../../types/domain';
import { TaskForm } from './TaskForm';
import type { TaskFormValues } from './taskSchema';
import {
  computeTaskSummary,
  DEFAULT_TASK_FILTERS,
  filterTasks,
  isActiveTaskStatus,
  isTaskOverdue,
  sortTasksByUrgency,
  TASK_PRIORITY_META,
  TASK_STATUS_META,
  type TaskDueFilter,
  type TaskFilters,
  type TaskStatusFilter,
} from './taskUtils';

const STATUS_GROUP_ORDER: Record<TaskStatus, number> = {
  in_progress: 0,
  todo: 1,
  parked: 2,
  done: 3,
  cancelled: 4,
};

function sortTasksForDisplay(tasks: Task[]): Task[] {
  const byUrgency = sortTasksByUrgency(tasks);
  return byUrgency.sort((a, b) => STATUS_GROUP_ORDER[a.status] - STATUS_GROUP_ORDER[b.status]);
}

export function TasksPage() {
  const {
    tasks,
    activePriorityTaskId,
    dataMode,
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
    loadDemoData,
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

  const [isCreating, setIsCreating] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [filters, setFilters] = useState<TaskFilters>(DEFAULT_TASK_FILTERS);
  const [feedback, setFeedback] = useState<string | null>(null);

  const summary = useMemo(() => computeTaskSummary(tasks), [tasks]);
  const visibleTasks = useMemo(
    () => sortTasksForDisplay(filterTasks(tasks, filters)),
    [tasks, filters],
  );

  const hasActiveFilters =
    filters.status !== 'all' ||
    filters.priority !== 'all' ||
    filters.due !== 'all' ||
    filters.search.trim() !== '';

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

  const handleStatusChange = async (task: Task, nextStatus: TaskStatus) => {
    if (await setTaskStatus(task.id, nextStatus)) {
      const label = TASK_STATUS_META[nextStatus].label.toLowerCase();
      setFeedback(`Tâche « ${task.title} » marquée comme ${label}.`);
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
        <PageHeader title="Tâches" />
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <PageHeader title="Tâches" />
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Tâches"
        actions={
          <Button variant="primary" onClick={handleOpenCreate}>
            <Icon icon={Add01Icon} size={16} />
            Nouvelle tâche
          </Button>
        }
      />

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Indicateurs synthétiques */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Actives</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50" data-testid="stat-active">
              {summary.activeCount}
            </p>
          </CardContent>
        </Card>
        <Card className={summary.overdueCount > 0 ? 'bg-rose-50/70 dark:bg-rose-950/35' : undefined}>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">En retard</p>
            <p
              className={cn(
                'mt-1 text-2xl font-semibold tabular-nums',
                summary.overdueCount > 0 ? 'text-rose-700 dark:text-rose-300' : 'text-zinc-900 dark:text-zinc-50',
              )}
              data-testid="stat-overdue"
            >
              {summary.overdueCount}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Terminées</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-700 dark:text-emerald-400" data-testid="stat-done">
              {summary.doneCount}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Parking</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-amber-700 dark:text-amber-300" data-testid="stat-parked">
              {summary.parkedCount}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Formulaire de création / modification */}
      {(isCreating || editingTask) && (
        <Card>
          <CardHeader>
            <CardTitle>{editingTask ? 'Modifier la tâche' : 'Nouvelle tâche'}</CardTitle>
          </CardHeader>
          <CardContent>
            <TaskForm
              initialTask={editingTask}
              onSubmit={handleFormSubmit}
              onCancel={() => {
                setIsCreating(false);
                setEditingTask(null);
              }}
            />
          </CardContent>
        </Card>
      )}

      {/* Filtres combinables */}
      <Card>
        <CardContent className="space-y-3 py-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <FormField id="filter-search" label="Recherche">
              <Input
                id="filter-search"
                type="search"
                value={filters.search}
                placeholder="Titre ou mot-clé…"
                onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              />
            </FormField>

            <FormField id="filter-status" label="Filtrer par statut">
              <Select
                id="filter-status"
                value={filters.status}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, status: e.target.value as TaskStatusFilter }))
                }
              >
                <option value="all">Tous les statuts</option>
                <option value="active">Actives</option>
                <option value="todo">À faire</option>
                <option value="in_progress">En cours</option>
                <option value="done">Terminées</option>
                <option value="parked">Parking</option>
                <option value="cancelled">Annulées</option>
              </Select>
            </FormField>

            <FormField id="filter-priority" label="Filtrer par priorité">
              <Select
                id="filter-priority"
                value={filters.priority}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    priority: e.target.value as 'all' | TaskPriority,
                  }))
                }
              >
                <option value="all">Toutes priorités</option>
                <option value="critical">Critique</option>
                <option value="high">Haute</option>
                <option value="normal">Normale</option>
                <option value="low">Basse</option>
              </Select>
            </FormField>

            <FormField id="filter-due" label="Filtrer par échéance">
              <Select
                id="filter-due"
                value={filters.due}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, due: e.target.value as TaskDueFilter }))
                }
              >
                <option value="all">Toutes échéances</option>
                <option value="overdue">En retard</option>
                <option value="today">Aujourd’hui</option>
                <option value="upcoming">À venir</option>
                <option value="no_due">Sans échéance</option>
              </Select>
            </FormField>
          </div>

          {hasActiveFilters && (
            <div className="flex items-center justify-between pt-2 text-xs text-zinc-600 dark:text-zinc-400">
              <span>
                {visibleTasks.length} résultat{visibleTasks.length > 1 ? 's' : ''}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFilters(DEFAULT_TASK_FILTERS)}
              >
                <Icon icon={RotateLeft01Icon} size={14} />
                Réinitialiser
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Liste des tâches ou états vides */}
      {tasks.length === 0 ? (
        <EmptyState
          icon={<Icon icon={CheckmarkSquare02Icon} size={17} />}
          title="Aucune tâche pour le moment"
          action={
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Button variant="primary" size="sm" onClick={handleOpenCreate}>
                Créer une tâche
              </Button>
              {dataMode === 'local_demo' && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    loadDemoData();
                    setFeedback('Données d’exemple chargées.');
                  }}
                >
                  Charger des données d’exemple
                </Button>
              )}
            </div>
          }
        />
      ) : visibleTasks.length === 0 ? (
        <EmptyState
          icon={<Icon icon={CheckmarkSquare02Icon} size={17} />}
          title="Aucune tâche ne correspond aux filtres"
          action={
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setFilters(DEFAULT_TASK_FILTERS)}
            >
              Réinitialiser les filtres
            </Button>
          }
        />
      ) : (
        <div className="space-y-2.5">
          {visibleTasks.map((task) => {
            const statusMeta = TASK_STATUS_META[task.status];
            const priorityMeta = TASK_PRIORITY_META[task.priority];
            const overdue = isTaskOverdue(task);
            const isPrimary = activePriorityTaskId === task.id;
            const isClosed = task.status === 'done' || task.status === 'cancelled';
            const linkedProjectName = task.projectId
              ? projectNameById.get(task.projectId)
              : undefined;
            const linkedModuleTitle = task.moduleId
              ? moduleTitleById.get(task.moduleId)
              : undefined;

            return (
              <Card
                key={task.id}
                className={cn(isPrimary && 'bg-teal-50/40 dark:bg-teal-950/25')}
              >
                <article aria-label={task.title} className="p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <h2
                          className={cn(
                            'text-[15px] font-semibold tracking-tight text-zinc-900 dark:text-zinc-50',
                            isClosed && 'line-through text-zinc-400 dark:text-zinc-500',
                          )}
                        >
                          {task.title}
                        </h2>
                        <Badge variant={statusMeta.badgeVariant}>{statusMeta.label}</Badge>
                        <Badge variant={priorityMeta.badgeVariant}>{priorityMeta.label}</Badge>
                        {overdue && <Badge variant="danger">En retard</Badge>}
                        {isPrimary && <Badge variant="primary">Priorité</Badge>}
                        {linkedProjectName && (
                          <Badge variant="neutral">{linkedProjectName}</Badge>
                        )}
                        {linkedModuleTitle && (
                          <Badge variant="neutral">{linkedModuleTitle}</Badge>
                        )}
                      </div>

                      {task.description && (
                        <p className="text-xs text-zinc-600 dark:text-zinc-400">{task.description}</p>
                      )}

                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
                        {task.dueAt && <span>Échéance : {formatDateFr(task.dueAt)}</span>}
                        {task.completedAt && (
                          <span className="font-medium text-emerald-700 dark:text-emerald-400">
                            Terminée le {formatDateTimeFr(task.completedAt)}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5 sm:justify-end">
                      {isActiveTaskStatus(task.status) ? (
                        <>
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => handleStatusChange(task, 'done')}
                          >
                            Terminer
                          </Button>
                          {task.status === 'todo' && (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleStatusChange(task, 'in_progress')}
                            >
                              Démarrer
                            </Button>
                          )}
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleStatusChange(task, 'parked')}
                          >
                            Parking
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleStatusChange(task, 'cancelled')}
                          >
                            Annuler
                          </Button>
                          {!isPrimary && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={async () => {
                                if (await setActivePriority(task.title, task.id)) {
                                  setFeedback(`« ${task.title} » définie comme priorité.`);
                                }
                              }}
                            >
                              <Icon icon={Target02Icon} size={14} />
                              Priorité
                            </Button>
                          )}
                        </>
                      ) : (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleStatusChange(task, 'todo')}
                        >
                          Réouvrir
                        </Button>
                      )}

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setIsCreating(false);
                          setEditingTask(task);
                        }}
                      >
                        Modifier
                      </Button>

                      <InlineConfirm
                        triggerLabel="Supprimer"
                        ariaLabel={`Supprimer ${task.title}`}
                        onConfirm={() => handleDelete(task)}
                      />
                    </div>
                  </div>
                </article>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
