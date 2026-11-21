import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Add01Icon,
  Alert02Icon,
  BookOpen01Icon,
  Calendar03Icon,
  FolderKanbanIcon,
  GridViewIcon,
  ListViewIcon,
  PencilEdit02Icon,
  Search01Icon,
  SparklesIcon,
  Target02Icon,
} from '@hugeicons/core-free-icons';
import { PageHeader } from '../../components/layout/PageHeader';
import { Button } from '../../components/ui/Button';
import { InlineConfirm, Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SuccessBanner,
} from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import { isoToDateInput } from '../../lib/date';
import {
  analyzeObjectivesIntakeApi,
  applyUnifiedPlanApi,
  confirmObjectivesIntakeApi,
  createPersonalGoalApi,
  deletePersonalGoalApi,
  fetchObjectivesOverviewApi,
  generateUnifiedPlanApi,
  updatePersonalGoalApi,
  type PersonalGoalCreateInput,
} from '../../lib/objectivesApi';
import { useAuth } from '../../state/AuthContext';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type {
  ConversationalIntakeRecap,
  PersonalGoal,
  Project,
  ProjectStatus,
  StudySession,
  Task,
  UnifiedPlan,
} from '../../types/domain';
import { ObjectivesIntakePanel } from './ObjectivesIntakePanel';
import { PersonalGoalForm } from './PersonalGoalForm';
import { ProjectCard } from './ProjectCard';
import { ProjectForm, type ProjectSubmitPayload } from './ProjectForm';
import { PROJECT_STATUS_META } from './projectsSchema';
import { UnifiedPlanPanel } from './UnifiedPlanPanel';

type ViewMode = 'list' | 'board';

const STATUS_FILTER_PILLS: Array<{ value: 'all' | ProjectStatus; label: string }> = [
  { value: 'all', label: 'Tous' },
  { value: 'active', label: 'Actifs' },
  { value: 'paused', label: 'En pause' },
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

const PILL_BASE = 'inline-flex min-h-11 items-center rounded-full px-3 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400';
const PILL_ACTIVE = 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900';
const PILL_IDLE =
  'bg-zinc-100 text-zinc-600 hover:bg-zinc-200/70 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700';

const OBJECTIVE_STATUS_LABELS: Record<string, string> = {
  active: 'Actif',
  paused: 'En pause',
  planned: 'Planifié',
  blocked: 'Bloqué',
  completed: 'Validé',
  archived: 'Archivé',
};

const OBJECTIVE_CATEGORY_LABELS: Record<string, string> = {
  learning_goal: 'Apprentissage',
  language: 'Langage',
  framework: 'Framework',
  technology: 'Technologie',
  spoken_language: 'Langue vivante',
  skill: 'Compétence',
  project: 'Projet',
  personal_project: 'Projet personnel',
  professional_project: 'Projet professionnel',
  other: 'Objectif',
};

export function ProjectsPage() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  const isApiMode = session?.mode === 'api' && Boolean(session.accessToken);
  const accessToken = session?.mode === 'api' ? session.accessToken : '';

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
    activePriorityTitle,
    activePriorityProjectId,
    setActivePriority,
    createTask,
  } = useStudyStore();

  const [statusFilter, setStatusFilter] = useState<'all' | ProjectStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [isGoalFormOpen, setIsGoalFormOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState<PersonalGoal | null>(null);
  const [isIntakeOpen, setIsIntakeOpen] = useState(false);
  const [isUnifiedPlanOpen, setIsUnifiedPlanOpen] = useState(false);
  const [inlineWarning, setInlineWarning] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const overviewQuery = useQuery({
    queryKey: ['objectives-overview', session?.userId ?? 'anon'],
    queryFn: () => fetchObjectivesOverviewApi(accessToken),
    enabled: isApiMode,
  });

  const personalGoals = useMemo(
    () => (isApiMode ? (overviewQuery.data?.personalGoals ?? []) : []),
    [isApiMode, overviewQuery.data],
  );

  const academicObligationsCount = useMemo(
    () => (isApiMode ? (overviewQuery.data?.academicObligations.length ?? 0) : 0),
    [isApiMode, overviewQuery.data],
  );

  const refreshObjectivesQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['objectives-overview'] }),
      queryClient.invalidateQueries({ queryKey: ['skills'] }),
      queryClient.invalidateQueries({ queryKey: ['learning'] }),
      queryClient.invalidateQueries({ queryKey: ['projects'] }),
      queryClient.invalidateQueries({ queryKey: ['profile'] }),
      queryClient.invalidateQueries({ queryKey: ['schedule'] }),
      queryClient.invalidateQueries({ queryKey: ['tasks'] }),
    ]);
  };

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
        if (
          activePriorityProjectId === editingProject.id &&
          payload.status !== 'paused' &&
          payload.status !== 'completed' &&
          payload.status !== 'archived'
        ) {
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

  const openGoalCreate = () => {
    setEditingGoal(null);
    setInlineWarning(null);
    setIsGoalFormOpen(true);
  };

  const openGoalEdit = (goal: PersonalGoal) => {
    setEditingGoal(goal);
    setInlineWarning(null);
    setIsGoalFormOpen(true);
  };

  const handleGoalSubmit = async (payload: PersonalGoalCreateInput) => {
    if (!isApiMode) {
      throw new Error('Connexion requise.');
    }
    if (editingGoal) {
      await updatePersonalGoalApi(accessToken, editingGoal.id, payload);
      setFeedback(`Objectif « ${payload.title} » mis à jour.`);
    } else {
      await createPersonalGoalApi(accessToken, payload);
      setFeedback(`Objectif « ${payload.title} » créé et relié aux parcours.`);
    }
    await refreshObjectivesQueries();
    setIsGoalFormOpen(false);
    setEditingGoal(null);
  };

  const handleToggleGoalPause = async (goal: PersonalGoal) => {
    if (!isApiMode) {
      setInlineWarning('Connexion requise.');
      return;
    }
    const nextStatus = goal.status === 'paused' ? 'active' : 'paused';
    await updatePersonalGoalApi(accessToken, goal.id, { status: nextStatus });
    await refreshObjectivesQueries();
    setFeedback(
      nextStatus === 'paused'
        ? `Objectif « ${goal.title} » suspendu.`
        : `Objectif « ${goal.title} » réactivé.`,
    );
  };

  const handleSetGoalPriority = async (goal: PersonalGoal) => {
    if (!isApiMode) {
      setInlineWarning('Connexion requise.');
      return;
    }
    await updatePersonalGoalApi(accessToken, goal.id, { isPrimary: true });
    await refreshObjectivesQueries();
    setFeedback(`Objectif « ${goal.title} » défini comme priorité principale.`);
  };

  const handleDeleteGoal = async (goal: PersonalGoal) => {
    if (!isApiMode) {
      setInlineWarning('Connexion requise.');
      return;
    }
    await deletePersonalGoalApi(accessToken, goal.id);
    await refreshObjectivesQueries();
    setFeedback(`Objectif « ${goal.title} » supprimé.`);
  };

  const handleAnalyzeIntake = async (
    message: string,
    knownAnswers: Record<string, unknown>,
  ): Promise<ConversationalIntakeRecap> => {
    if (!isApiMode) {
      throw new Error('Connexion requise.');
    }
    return analyzeObjectivesIntakeApi(accessToken, { message, knownAnswers });
  };

  const handleConfirmIntake = async ({
    recap,
    knownAnswers,
  }: {
    recap: ConversationalIntakeRecap;
    knownAnswers: Record<string, unknown>;
  }) => {
    if (!isApiMode) {
      throw new Error('Connexion requise.');
    }
    const res = await confirmObjectivesIntakeApi(accessToken, {
      objectives: recap.objectives,
      availableTimeWeeklyMinutes:
        typeof knownAnswers.available_time_weekly_minutes === 'number'
          ? knownAnswers.available_time_weekly_minutes
          : recap.availableTimeWeeklyMinutes,
      motivation:
        typeof knownAnswers.motivation === 'string'
          ? knownAnswers.motivation
          : recap.motivation,
      targetDate:
        typeof knownAnswers.target_date === 'string'
          ? knownAnswers.target_date
          : recap.targetDate,
      primaryTitle:
        typeof knownAnswers.primary_title === 'string'
          ? knownAnswers.primary_title
          : null,
    });
    await refreshObjectivesQueries();
    setFeedback(
      `${res.createdGoals.length} objectif(s) et ${res.createdProjects.length} projet(s) enregistrés après confirmation.`,
    );
    setIsIntakeOpen(false);
  };

  const handleGeneratePlan = async (params: {
    weeklyAvailableMinutes: number;
    primaryPriorityTitle: string | null;
  }): Promise<UnifiedPlan> => {
    if (!isApiMode) {
      throw new Error('Connexion requise.');
    }
    return generateUnifiedPlanApi(accessToken, {
      weeklyAvailableMinutes: params.weeklyAvailableMinutes,
      primaryPriorityTitle: params.primaryPriorityTitle,
      includeDailyRecovery: true,
    });
  };

  const handleApplyPlan = async (plan: UnifiedPlan) => {
    if (!isApiMode) {
      throw new Error('Connexion requise.');
    }
    const res = await applyUnifiedPlanApi(accessToken, {
      flexibleStudySlots: plan.flexibleStudySlots,
      primaryPriorityTitle: plan.primaryPriorityTitle,
      replaceExistingFlexibleWeek: true,
      weekStart: plan.weekStart,
    });
    await refreshObjectivesQueries();
    setFeedback(
      `Programme validé : ${res.createdEventsCount} séance(s) planifiée(s) et ${res.linkedTasksCreatedCount} tâche(s) liée(s).`,
    );
    setIsUnifiedPlanOpen(false);
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <PageHeader title="Mes objectifs et projets" />
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <PageHeader title="Objectifs & Projets" />
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  const headerSubtitle =
    projects.length > 0 || personalGoals.length > 0
      ? `${personalGoals.length} objectif${personalGoals.length > 1 ? 's' : ''} · ${summary.activeCount}/3 actifs`
      : undefined;

  return (
    <div className="space-y-3.5 sm:space-y-5">
      <PageHeader
        title="Objectifs & Projets"
        description={headerSubtitle}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="secondary" size="sm" onClick={openGoalCreate}>
              <Icon icon={BookOpen01Icon} size={15} />
              Nouvel objectif
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setIsIntakeOpen((prev) => !prev)}
            >
              <Icon icon={SparklesIcon} size={15} />
              Décrire à l’IA
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setIsUnifiedPlanOpen((prev) => !prev)}
            >
              <Icon icon={Calendar03Icon} size={15} />
              Programme unifié
            </Button>
            <Button type="button" variant="primary" size="sm" onClick={openCreate}>
              <Icon icon={Add01Icon} size={15} />
              Nouveau projet
            </Button>
          </div>
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

      {/* Capacité et garde-fou anti-dispersion PROJ-01 (3 projets actifs maximum) */}
      {summary.activeCount >= 3 && (
        <div
          role="status"
          className={cn(
            'flex items-start gap-2.5 rounded-xl p-3.5 text-xs',
            summary.activeCount > 3
              ? 'bg-amber-50 text-amber-950 dark:bg-amber-950/50 dark:text-amber-100'
              : 'bg-zinc-100/90 text-zinc-800 dark:bg-zinc-800/70 dark:text-zinc-200',
          )}
        >
          <Icon
            icon={Alert02Icon}
            size={17}
            className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-300"
          />
          <div>
            <p className="font-semibold">
              {summary.activeCount > 3
                ? `Attention à la dispersion (${summary.activeCount} projets actifs)`
                : 'Capacité maximale atteinte (3/3 projets actifs)'}
            </p>
            <p className="text-zinc-600 dark:text-zinc-300">
              Maximum 3 projets actifs. Mettez-en un en pause ou terminez-le pour en activer un autre.
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

      {/* Bandeau de séparation des 3 sources indépendantes */}
      <section
        aria-label="Séparation des trois sources"
        className="grid gap-2.5 sm:grid-cols-3"
      >
        <div className="min-w-0 rounded-2xl bg-white p-3.5 dark:bg-zinc-900">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            1. Académique
          </p>
          <p className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            {academicObligationsCount} cours ou examen{academicObligationsCount > 1 ? 's' : ''} fixe{academicObligationsCount > 1 ? 's' : ''}
          </p>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            Emploi du temps fixe isolé.
          </p>
        </div>

        <div className="min-w-0 rounded-2xl bg-white p-3.5 dark:bg-zinc-900">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            2. Objectifs
          </p>
          <p className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            {personalGoals.length} objectif{personalGoals.length > 1 ? 's' : ''} d’apprentissage
          </p>
          <p className="mt-0.5 line-clamp-1 break-words text-xs text-zinc-500 dark:text-zinc-400">
            {activePriorityTitle
              ? `Priorité : ${activePriorityTitle}`
              : 'Créneaux flexibles.'}
          </p>
        </div>

        <div className="min-w-0 rounded-2xl bg-white p-3.5 dark:bg-zinc-900">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            3. Projets
          </p>
          <p className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            {summary.activeCount}/3 projet{summary.activeCount > 1 ? 's' : ''} actif{summary.activeCount > 1 ? 's' : ''}
          </p>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            Livrables et prochaines actions.
          </p>
        </div>
      </section>

      {isIntakeOpen && (
        <ObjectivesIntakePanel
          onAnalyze={handleAnalyzeIntake}
          onConfirm={handleConfirmIntake}
          onClose={() => setIsIntakeOpen(false)}
        />
      )}

      {isUnifiedPlanOpen && (
        <UnifiedPlanPanel
          goals={personalGoals}
          projects={projects}
          currentPriorityTitle={activePriorityTitle}
          onGenerate={handleGeneratePlan}
          onApply={handleApplyPlan}
          onClose={() => setIsUnifiedPlanOpen(false)}
        />
      )}

      {isGoalFormOpen && (
        <PersonalGoalForm
          editingGoal={editingGoal}
          onSubmit={handleGoalSubmit}
          onCancel={() => {
            setIsGoalFormOpen(false);
            setEditingGoal(null);
          }}
        />
      )}

      {personalGoals.length > 0 && (
        <section aria-label="Mes objectifs personnels" className="space-y-3">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Objectifs personnels ({personalGoals.length})
          </h2>
          <div className="grid gap-3 md:grid-cols-2">
            {personalGoals.map((goal) => (
              <article
                key={goal.id}
                aria-label={`Objectif ${goal.title}`}
                className="space-y-2.5 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-zinc-200/70 dark:bg-zinc-900 dark:ring-zinc-800"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <h3 className="line-clamp-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {goal.title}
                    </h3>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">
                      {OBJECTIVE_CATEGORY_LABELS[goal.category] ?? goal.category} ·{' '}
                      {OBJECTIVE_STATUS_LABELS[goal.status] ?? goal.status}
                      {goal.isPrimary ? ' · Priorité principale' : ''}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {!goal.isPrimary && goal.status === 'active' && (
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        aria-label={`Définir ${goal.title} comme priorité principale`}
                        onClick={() => void handleSetGoalPriority(goal)}
                      >
                        <Icon icon={Target02Icon} size={13} />
                        Priorité
                      </Button>
                    )}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      aria-label={`${goal.status === 'paused' ? 'Reprendre' : 'Suspendre'} ${goal.title}`}
                      onClick={() => void handleToggleGoalPause(goal)}
                    >
                      {goal.status === 'paused' ? 'Reprendre' : 'Suspendre'}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      aria-label={`Modifier l’objectif ${goal.title}`}
                      onClick={() => openGoalEdit(goal)}
                    >
                      <Icon icon={PencilEdit02Icon} size={13} />
                      Modifier
                    </Button>
                    <InlineConfirm
                      triggerLabel="Supprimer"
                      ariaLabel={`Supprimer l’objectif ${goal.title}`}
                      onConfirm={() => void handleDeleteGoal(goal)}
                    />
                  </div>
                </div>

                <p className="line-clamp-2 text-xs text-zinc-700 dark:text-zinc-300">{goal.goal}</p>

                <div className="flex flex-wrap gap-3 text-[11px] text-zinc-500 dark:text-zinc-400">
                  {goal.currentLevel !== null && (
                    <span>
                      Niveau : {goal.currentLevel}/5
                      {goal.targetLevel !== null ? ` vers ${goal.targetLevel}/5` : ''}
                    </span>
                  )}
                  <span>Temps cible : {goal.weeklyTargetMinutes} min/sem.</span>
                  <span>
                    Progression : {goal.sessionsCount} séance(s) ({goal.completedMinutesLast7d} min / 7 j)
                  </span>
                </div>

                {goal.nextAction && (
                  <p className="line-clamp-2 rounded-lg bg-zinc-50 px-2.5 py-1.5 text-xs text-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-300">
                    <strong>Prochaine action :</strong> {goal.nextAction}
                  </p>
                )}

                {goal.isBehindSchedule && goal.delayReason && (
                  <p className="rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
                    {goal.delayReason}
                  </p>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

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
              <div className="min-w-[130px] flex-1 sm:w-44 sm:flex-none">
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
                  <option value="paused">En pause</option>
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
            <div
              role="group"
              aria-label="Filtrer les projets par statut"
              className="no-scrollbar flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0"
            >
              {STATUS_FILTER_PILLS.map((pill) => (
                <button
                  key={pill.value}
                  type="button"
                  aria-pressed={statusFilter === pill.value}
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
