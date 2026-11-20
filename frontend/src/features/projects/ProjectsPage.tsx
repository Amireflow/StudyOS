import { useMemo, useState } from 'react';
import {
  Add01Icon,
  Alert02Icon,
  FolderKanbanIcon,
  GridViewIcon,
  ListViewIcon,
  Search01Icon,
} from '@hugeicons/core-free-icons';
import { PageHeader } from '../../components/layout/PageHeader';
import { Button } from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SuccessBanner,
} from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import { isoToDateInput } from '../../lib/date';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type { Project, ProjectStatus, StudySession, Task } from '../../types/domain';
import { ProjectCard } from './ProjectCard';
import { ProjectForm, type ProjectSubmitPayload } from './ProjectForm';
import { PROJECT_STATUS_META } from './projectsSchema';

type ViewMode = 'list' | 'board';

const STATUS_FILTER_PILLS: Array<{ value: 'all' | ProjectStatus; label: string }> = [
  { value: 'all', label: 'Tous' },
  { value: 'active', label: 'Actifs' },
  { value: 'planned', label: 'Planifiés' },
  { value: 'blocked', label: 'Bloqués' },
  { value: 'completed', label: 'Terminés' },
  { value: 'archived', label: 'Archivés' },
];

const BOARD_COLUMNS: Array<{ status: ProjectStatus; title: string }> = [
  { status: 'planned', title: 'Planifiés' },
  { status: 'active', title: 'Actifs' },
  { status: 'blocked', title: 'Bloqués' },
  { status: 'completed', title: 'Terminés' },
];

const PILL_BASE = 'rounded-full px-3 py-1 text-xs font-medium transition-colors';
const PILL_ACTIVE = 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900';
const PILL_IDLE =
  'bg-zinc-100 text-zinc-600 hover:bg-zinc-200/70 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700';

export function ProjectsPage() {
  const {
    projects,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    createProject,
    updateProject,
    setProjectStatus,
    deleteProject,
  } = useLearningStore();
  const {
    tasks,
    sessions,
    activePriorityProjectId,
    setActivePriority,
    createTask,
    dataMode,
  } = useStudyStore();

  const [statusFilter, setStatusFilter] = useState<'all' | ProjectStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [inlineWarning, setInlineWarning] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const summary = useMemo(() => {
    let activeCount = 0;
    let blockedCount = 0;
    let completedCount = 0;

    for (const project of projects) {
      if (project.status === 'active') activeCount += 1;
      else if (project.status === 'blocked') blockedCount += 1;
      else if (project.status === 'completed') completedCount += 1;
    }

    const linkedTasksCount = tasks.filter((t) => Boolean(t.projectId)).length;

    return {
      totalCount: projects.length,
      activeCount,
      blockedCount,
      completedCount,
      linkedTasksCount,
    };
  }, [projects, tasks]);

  const tasksByProjectId = useMemo(() => {
    const map = new Map<string, Task[]>();
    for (const task of tasks) {
      if (!task.projectId) continue;
      const list = map.get(task.projectId) ?? [];
      list.push(task);
      map.set(task.projectId, list);
    }
    return map;
  }, [tasks]);

  const sessionsByProjectId = useMemo(() => {
    const map = new Map<string, StudySession[]>();
    for (const session of sessions) {
      if (!session.projectId) continue;
      const list = map.get(session.projectId) ?? [];
      list.push(session);
      map.set(session.projectId, list);
    }
    return map;
  }, [sessions]);

  const visibleProjects = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return projects.filter((project) => {
      if (statusFilter !== 'all' && project.status !== statusFilter) {
        return false;
      }
      if (!query) {
        return true;
      }
      const inName = project.name.toLowerCase().includes(query);
      const inGoal = project.goal.toLowerCase().includes(query);
      const inDesc = (project.description ?? '').toLowerCase().includes(query);
      const inNextAction = project.nextAction.toLowerCase().includes(query);
      const inDeliverables = (project.deliverables ?? []).some((d) =>
        d.toLowerCase().includes(query),
      );
      return inName || inGoal || inDesc || inNextAction || inDeliverables;
    });
  }, [projects, statusFilter, searchQuery]);

  const openCreate = () => {
    setEditingProject(null);
    setInlineWarning(null);
    setIsFormOpen(true);
  };

  const openEdit = (project: Project) => {
    setEditingProject(project);
    setInlineWarning(null);
    setIsFormOpen(true);
  };

  const handleProjectSubmit = async (payload: ProjectSubmitPayload) => {
    if (editingProject) {
      if (await updateProject(editingProject.id, payload)) {
        if (activePriorityProjectId === editingProject.id) {
          await setActivePriority(payload.name.trim(), null, editingProject.id);
        }
        setFeedback(`Projet « ${payload.name} » mis à jour.`);
        setIsFormOpen(false);
        setEditingProject(null);
      }
      return;
    }

    if (await createProject(payload)) {
      setFeedback(`Projet « ${payload.name} » créé.`);
      setIsFormOpen(false);
    }
  };

  const handleStatusChange = async (project: Project, nextStatus: ProjectStatus) => {
    setInlineWarning(null);
    if (nextStatus === 'active' && project.nextAction.trim().length < 2) {
      setInlineWarning(
        `Le projet « ${project.name} » doit définir une prochaine action concrète avant de passer au statut Actif.`,
      );
      openEdit({ ...project, status: 'active' });
      return;
    }
    if (await setProjectStatus(project.id, nextStatus)) {
      const label = PROJECT_STATUS_META[nextStatus].label.toLowerCase();
      setFeedback(`Projet « ${project.name} » passé à ${label}.`);
    }
  };

  const handleSetPriority = async (project: Project) => {
    if (await setActivePriority(project.name, null, project.id)) {
      setFeedback(`Projet « ${project.name} » défini comme priorité.`);
    }
  };

  const handleDeleteProject = async (project: Project) => {
    if (activePriorityProjectId === project.id && dataMode === 'local_demo') {
      await setActivePriority(null, null, null);
    }
    if (await deleteProject(project.id)) {
      setFeedback(`Projet « ${project.name} » supprimé.`);
    }
  };

  const handleConvertNextActionToTask = async (project: Project) => {
    const actionTitle = project.nextAction.trim();
    if (actionTitle.length < 2) return;

    const ok = await createTask({
      title: actionTitle,
      description: `Prochaine action du projet « ${project.name} »`,
      priority: project.priority,
      status: 'todo',
      dueDate: isoToDateInput(project.targetDate),
      projectId: project.id,
      moduleId: '',
    });

    if (ok) {
      setFeedback(`Tâche « ${actionTitle} » créée et liée au projet « ${project.name} ».`);
    }
  };

  const resetFilters = () => {
    setStatusFilter('all');
    setSearchQuery('');
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <PageHeader title="Projets" />
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <PageHeader title="Projets" />
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  const headerSubtitle =
    projects.length > 0
      ? `${summary.activeCount} actif${summary.activeCount > 1 ? 's' : ''} · ${summary.linkedTasksCount} tâche${summary.linkedTasksCount > 1 ? 's' : ''} liée${summary.linkedTasksCount > 1 ? 's' : ''}`
      : undefined;

  return (
    <div className="space-y-3.5 sm:space-y-5">
      <PageHeader
        title="Projets"
        description={headerSubtitle}
        actions={
          <Button type="button" variant="primary" size="sm" onClick={openCreate}>
            <Icon icon={Add01Icon} size={15} />
            Nouveau projet
          </Button>
        }
      />

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}
      {inlineWarning && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl bg-amber-50 p-3.5 text-xs text-amber-950 dark:bg-amber-950/50 dark:text-amber-100"
        >
          <Icon
            icon={Alert02Icon}
            size={17}
            className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-300"
          />
          <p>{inlineWarning}</p>
        </div>
      )}

      {/* Avertissement anti-dispersion PROJ-01 (> 3 projets actifs) */}
      {summary.activeCount > 3 && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl bg-amber-50 p-3.5 text-xs text-amber-950 dark:bg-amber-950/50 dark:text-amber-100"
        >
          <Icon
            icon={Alert02Icon}
            size={17}
            className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-300"
          />
          <div>
            <p className="font-semibold">
              Attention à la dispersion ({summary.activeCount} projets actifs)
            </p>
            <p className="text-amber-900 dark:text-amber-200">
              Maximum recommandé : 3 projets actifs simultanés.
            </p>
          </div>
        </div>
      )}

      {/* Tuiles KPI interactives */}
      <section aria-label="Indicateurs des projets" className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 sm:gap-3">
        <button
          type="button"
          aria-pressed={statusFilter === 'active'}
          onClick={() => setStatusFilter((prev) => (prev === 'active' ? 'all' : 'active'))}
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            statusFilter === 'active'
              ? 'bg-teal-50/80 dark:bg-teal-950/40'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Actifs</p>
          <p
            className={cn(
              'mt-0.5 text-xl font-semibold tabular-nums sm:mt-1 sm:text-2xl',
              summary.activeCount > 3
                ? 'text-amber-600 dark:text-amber-300'
                : 'text-teal-800 dark:text-teal-300',
            )}
          >
            {summary.activeCount}
          </p>
        </button>

        <button
          type="button"
          aria-pressed={statusFilter === 'blocked'}
          onClick={() => setStatusFilter((prev) => (prev === 'blocked' ? 'all' : 'blocked'))}
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            statusFilter === 'blocked'
              ? 'bg-amber-100/70 dark:bg-amber-950/50'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Bloqués</p>
          <p
            className={cn(
              'mt-0.5 text-xl font-semibold tabular-nums sm:mt-1 sm:text-2xl',
              summary.blockedCount > 0
                ? 'text-amber-600 dark:text-amber-300'
                : 'text-zinc-900 dark:text-zinc-50',
            )}
          >
            {summary.blockedCount}
          </p>
        </button>

        <button
          type="button"
          aria-pressed={statusFilter === 'completed'}
          onClick={() => setStatusFilter((prev) => (prev === 'completed' ? 'all' : 'completed'))}
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            statusFilter === 'completed'
              ? 'bg-emerald-50/80 dark:bg-emerald-950/40'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Terminés</p>
          <p className="mt-0.5 text-xl font-semibold tabular-nums text-emerald-700 sm:mt-1 sm:text-2xl dark:text-emerald-400">
            {summary.completedCount}
          </p>
        </button>

        <div className="rounded-2xl bg-white p-3 sm:p-4 dark:bg-zinc-900">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Tâches liées</p>
          <p className="mt-0.5 text-xl font-semibold tabular-nums text-zinc-900 sm:mt-1 sm:text-2xl dark:text-zinc-50">
            {summary.linkedTasksCount}
          </p>
        </div>
      </section>

      {/* Formulaire projet */}
      {isFormOpen && (
        <ProjectForm
          editingProject={editingProject}
          onSubmit={handleProjectSubmit}
          onCancel={() => {
            setIsFormOpen(false);
            setEditingProject(null);
          }}
        />
      )}

      {/* Barre de recherche, filtres de statut et bascule Liste / Tableau */}
      {projects.length > 0 && (
        <section
          aria-label="Recherche et filtres des projets"
          className="space-y-3 rounded-2xl bg-white p-3.5 dark:bg-zinc-900"
        >
          <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 sm:max-w-xs">
              <Icon
                icon={Search01Icon}
                size={15}
                className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-zinc-400 dark:text-zinc-500"
              />
              <Input
                aria-label="Rechercher un projet"
                type="search"
                value={searchQuery}
                placeholder="Rechercher un projet, objectif ou livrable…"
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="w-40 sm:w-44">
                <label htmlFor="projects-status-filter" className="sr-only">
                  Filtrer par statut
                </label>
                <Select
                  id="projects-status-filter"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as 'all' | ProjectStatus)}
                >
                  <option value="all">Tous les statuts</option>
                  <option value="active">Actifs</option>
                  <option value="planned">Planifiés</option>
                  <option value="blocked">Bloqués</option>
                  <option value="completed">Terminés</option>
                  <option value="archived">Archivés</option>
                </Select>
              </div>

              <div
                role="group"
                aria-label="Mode d'affichage des projets"
                className="inline-flex rounded-xl bg-zinc-100 p-1 dark:bg-zinc-800"
              >
                <button
                  type="button"
                  onClick={() => setViewMode('list')}
                  aria-pressed={viewMode === 'list'}
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors',
                    viewMode === 'list'
                      ? 'bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50'
                      : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100',
                  )}
                >
                  <Icon icon={ListViewIcon} size={14} />
                  Liste
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('board')}
                  aria-pressed={viewMode === 'board'}
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors',
                    viewMode === 'board'
                      ? 'bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50'
                      : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100',
                  )}
                >
                  <Icon icon={GridViewIcon} size={14} />
                  Tableau
                </button>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between gap-2">
            <div className="no-scrollbar flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0">
              {STATUS_FILTER_PILLS.map((pill) => (
                <button
                  key={pill.value}
                  type="button"
                  onClick={() => setStatusFilter(pill.value)}
                  className={cn(
                    'shrink-0',
                    PILL_BASE,
                    statusFilter === pill.value ? PILL_ACTIVE : PILL_IDLE,
                  )}
                >
                  {pill.label}
                </button>
              ))}
            </div>
            <p className="shrink-0 text-xs text-zinc-500 dark:text-zinc-400">
              {visibleProjects.length} projet{visibleProjects.length > 1 ? 's' : ''}
            </p>
          </div>
        </section>
      )}

      {/* Liste ou Tableau des projets */}
      {projects.length === 0 ? (
        <div className="rounded-2xl bg-white py-8 dark:bg-zinc-900">
          <EmptyState
            icon={
              <Icon
                icon={FolderKanbanIcon}
                size={17}
                className="text-teal-700 dark:text-teal-400"
              />
            }
            title="Aucun projet enregistré"
            action={
              <Button type="button" variant="primary" size="sm" onClick={openCreate}>
                Créer mon premier projet
              </Button>
            }
          />
        </div>
      ) : visibleProjects.length === 0 ? (
        <EmptyState
          icon={<Icon icon={FolderKanbanIcon} size={17} />}
          title="Aucun projet ne correspond aux filtres"
          action={
            <Button type="button" variant="secondary" size="sm" onClick={resetFilters}>
              Réinitialiser les filtres
            </Button>
          }
        />
      ) : viewMode === 'list' ? (
        <div className="space-y-3">
          {visibleProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              isFocusProject={activePriorityProjectId === project.id}
              projectTasks={tasksByProjectId.get(project.id) ?? []}
              projectSessions={sessionsByProjectId.get(project.id) ?? []}
              onStatusChange={handleStatusChange}
              onSetPriority={handleSetPriority}
              onEdit={openEdit}
              onDelete={handleDeleteProject}
              onConvertNextActionToTask={handleConvertNextActionToTask}
            />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {BOARD_COLUMNS.map((col) => {
            const columnProjects = visibleProjects.filter((p) => p.status === col.status);
            return (
              <div
                key={col.status}
                className="space-y-2.5 rounded-2xl bg-zinc-100/70 p-3 dark:bg-zinc-900/50"
              >
                <div className="flex items-center justify-between px-1">
                  <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-300">
                    {col.title}
                  </h2>
                  <span className="rounded-full bg-zinc-200/70 px-2 py-0.5 text-[11px] font-semibold tabular-nums text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                    {columnProjects.length}
                  </span>
                </div>

                {columnProjects.length === 0 ? (
                  <p className="rounded-xl bg-white/60 px-3 py-4 text-center text-xs text-zinc-400 dark:bg-zinc-900/40 dark:text-zinc-500">
                    Aucun projet
                  </p>
                ) : (
                  <div className="space-y-2.5">
                    {columnProjects.map((project) => (
                      <ProjectCard
                        key={project.id}
                        project={project}
                        compact
                        isFocusProject={activePriorityProjectId === project.id}
                        projectTasks={tasksByProjectId.get(project.id) ?? []}
                        projectSessions={sessionsByProjectId.get(project.id) ?? []}
                        onStatusChange={handleStatusChange}
                        onSetPriority={handleSetPriority}
                        onEdit={openEdit}
                        onDelete={handleDeleteProject}
                        onConvertNextActionToTask={handleConvertNextActionToTask}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
