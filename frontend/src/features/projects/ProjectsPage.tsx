import { useMemo, useState, type FormEvent } from 'react';
import {
  Add01Icon,
  Alert02Icon,
  FolderKanbanIcon,
  Target02Icon,
} from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { PageHeader } from '../../components/layout/PageHeader';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/Card';
import { FormField, InlineConfirm, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from '../../components/ui/StateFeedback';
import { formatDateFr, isoToDateInput } from '../../lib/date';
import { extractFieldErrors } from '../../lib/validation';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type { Project, ProjectStatus, TaskPriority } from '../../types/domain';
import { TASK_PRIORITY_META } from '../tasks/taskUtils';
import {
  parseDeliverablesText,
  PROJECT_STATUS_META,
  projectFormSchema,
  type ProjectFormValues,
} from './projectsSchema';

type ProjectField = keyof ProjectFormValues;

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
    dataMode,
  } = useStudyStore();

  const [statusFilter, setStatusFilter] = useState<'all' | ProjectStatus>('all');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [values, setValues] = useState<ProjectFormValues>({
    name: '',
    goal: '',
    description: '',
    status: 'active',
    priority: 'normal',
    nextAction: '',
    deliverablesText: '',
    targetDate: '',
  });
  const [errors, setErrors] = useState<Partial<Record<ProjectField, string>>>({});
  const [inlineWarning, setInlineWarning] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const activeProjectsCount = useMemo(
    () => projects.filter((p) => p.status === 'active').length,
    [projects],
  );
  const visibleProjects = useMemo(() => {
    if (statusFilter === 'all') return projects;
    return projects.filter((p) => p.status === statusFilter);
  }, [projects, statusFilter]);

  const openCreate = () => {
    setEditingProject(null);
    setValues({
      name: '',
      goal: '',
      description: '',
      status: 'active',
      priority: 'normal',
      nextAction: '',
      deliverablesText: '',
      targetDate: '',
    });
    setErrors({});
    setInlineWarning(null);
    setIsFormOpen(true);
  };

  const openEdit = (project: Project) => {
    setEditingProject(project);
    setValues({
      name: project.name,
      goal: project.goal,
      description: project.description ?? '',
      status: project.status,
      priority: project.priority,
      nextAction: project.nextAction,
      deliverablesText: (project.deliverables ?? []).join('\n'),
      targetDate: isoToDateInput(project.targetDate),
    });
    setErrors({});
    setInlineWarning(null);
    setIsFormOpen(true);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = projectFormSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(extractFieldErrors<ProjectField>(parsed.error));
      return;
    }
    setErrors({});

    const payload = {
      name: parsed.data.name,
      goal: parsed.data.goal,
      description: parsed.data.description,
      status: parsed.data.status,
      priority: parsed.data.priority,
      nextAction: parsed.data.nextAction,
      deliverables: parseDeliverablesText(parsed.data.deliverablesText),
      targetDate: parsed.data.targetDate,
    };

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

  return (
    <div className="space-y-5">
      <PageHeader
        title="Projets"
        actions={
          <Button variant="primary" onClick={openCreate}>
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
          <Icon icon={Alert02Icon} size={17} className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-300" />
          <p>{inlineWarning}</p>
        </div>
      )}

      {/* Avertissement anti-dispersion PROJ-01 (> 3 projets actifs) */}
      {activeProjectsCount > 3 && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl bg-amber-50 p-3.5 text-xs text-amber-950 dark:bg-amber-950/50 dark:text-amber-100"
        >
          <Icon icon={Alert02Icon} size={17} className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-300" />
          <div>
            <p className="font-semibold">
              Attention à la dispersion ({activeProjectsCount} projets actifs)
            </p>
            <p className="text-amber-900 dark:text-amber-200">
              Maximum recommandé : 3 projets actifs simultanés.
            </p>
          </div>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Actifs</p>
            <p
              className={
                activeProjectsCount > 3
                  ? 'mt-1 text-xl font-semibold tabular-nums text-amber-600 dark:text-amber-300 sm:text-2xl'
                  : 'mt-1 text-xl font-semibold tabular-nums text-teal-800 dark:text-teal-300 sm:text-2xl'
              }
            >
              {activeProjectsCount}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Total</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50 sm:text-2xl">
              {projects.length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Tâches liées</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50 sm:text-2xl">
              {tasks.filter((t) => Boolean(t.projectId)).length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Formulaire projet */}
      {isFormOpen && (
        <Card>
          <CardHeader>
            <CardTitle>{editingProject ? 'Modifier le projet' : 'Nouveau projet'}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="sm:col-span-2">
                  <FormField id="project-name" label="Nom du projet" required error={errors.name}>
                    <Input
                      id="project-name"
                      value={values.name}
                      hasError={Boolean(errors.name)}
                      placeholder="Ex. Amireflow Study OS v1"
                      onChange={(e) => {
                        setValues((prev) => ({ ...prev, name: e.target.value }));
                        if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }));
                      }}
                    />
                  </FormField>
                </div>

                <FormField id="project-status" label="Statut">
                  <Select
                    id="project-status"
                    value={values.status}
                    onChange={(e) =>
                      setValues((prev) => ({ ...prev, status: e.target.value as ProjectStatus }))
                    }
                  >
                    <option value="planned">Planifié</option>
                    <option value="active">Actif</option>
                    <option value="blocked">Bloqué</option>
                    <option value="completed">Terminé</option>
                    <option value="archived">Archivé</option>
                  </Select>
                </FormField>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <FormField id="project-goal" label="Objectif mesurable" required error={errors.goal}>
                  <Input
                    id="project-goal"
                    value={values.goal}
                    hasError={Boolean(errors.goal)}
                    placeholder="Ex. Livrer les Paliers 1 et 2 testés"
                    onChange={(e) => {
                      setValues((prev) => ({ ...prev, goal: e.target.value }));
                      if (errors.goal) setErrors((prev) => ({ ...prev, goal: undefined }));
                    }}
                  />
                </FormField>

                <FormField
                  id="project-next-action"
                  label="Prochaine action concrète"
                  required={values.status === 'active'}
                  error={errors.nextAction}
                >
                  <Input
                    id="project-next-action"
                    value={values.nextAction}
                    hasError={Boolean(errors.nextAction)}
                    placeholder="Ex. Écrire les tests d'intégration projets"
                    onChange={(e) => {
                      setValues((prev) => ({ ...prev, nextAction: e.target.value }));
                      if (errors.nextAction) {
                        setErrors((prev) => ({ ...prev, nextAction: undefined }));
                      }
                    }}
                  />
                </FormField>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <FormField id="project-priority" label="Priorité">
                  <Select
                    id="project-priority"
                    value={values.priority}
                    onChange={(e) =>
                      setValues((prev) => ({ ...prev, priority: e.target.value as TaskPriority }))
                    }
                  >
                    <option value="low">Basse</option>
                    <option value="normal">Normale</option>
                    <option value="high">Haute</option>
                    <option value="critical">Critique</option>
                  </Select>
                </FormField>

                <FormField id="project-target-date" label="Date cible (facultatif)" error={errors.targetDate}>
                  <Input
                    id="project-target-date"
                    type="date"
                    value={values.targetDate ?? ''}
                    onChange={(e) => setValues((prev) => ({ ...prev, targetDate: e.target.value }))}
                  />
                </FormField>
              </div>

              <FormField id="project-description" label="Description (facultatif)">
                <Textarea
                  id="project-description"
                  value={values.description ?? ''}
                  placeholder="Périmètre et jalons clés"
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, description: e.target.value }))
                  }
                />
              </FormField>

              <FormField
                id="project-deliverables"
                label="Livrables (un par ligne, facultatif)"
              >
                <Textarea
                  id="project-deliverables"
                  value={values.deliverablesText ?? ''}
                  placeholder={'API REST FastAPI\nInterface React complète'}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, deliverablesText: e.target.value }))
                  }
                />
              </FormField>

              <div className="flex flex-wrap justify-end gap-2">
                <Button variant="secondary" onClick={() => setIsFormOpen(false)}>
                  Annuler
                </Button>
                <Button type="submit" variant="primary">
                  {editingProject ? 'Enregistrer le projet' : 'Créer le projet'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Filtre par statut */}
      {projects.length > 0 && (
        <Card>
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-3.5">
            <div className="w-full sm:w-60">
              <FormField id="projects-status-filter" label="Filtrer par statut">
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
              </FormField>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {visibleProjects.length} projet{visibleProjects.length > 1 ? 's' : ''}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Liste des projets */}
      {projects.length === 0 ? (
        <Card>
          <CardContent className="py-8">
            <EmptyState
              icon={<Icon icon={FolderKanbanIcon} size={17} className="text-teal-700 dark:text-teal-400" />}
              title="Aucun projet enregistré"
              action={
                <Button variant="primary" onClick={openCreate}>
                  Créer mon premier projet
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {visibleProjects.map((project) => {
            const statusMeta = PROJECT_STATUS_META[project.status];
            const priorityMeta = TASK_PRIORITY_META[project.priority];
            const isFocusProject = activePriorityProjectId === project.id;
            const linkedTasks = tasks.filter((t) => t.projectId === project.id).length;
            const linkedSessions = sessions.filter((s) => s.projectId === project.id).length;

            return (
              <Card
                key={project.id}
                className={isFocusProject ? 'bg-teal-50/40 dark:bg-teal-950/25' : undefined}
              >
                <CardHeader className="sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <CardTitle>{project.name}</CardTitle>
                      <Badge variant={statusMeta.badgeVariant}>{statusMeta.label}</Badge>
                      <Badge variant={priorityMeta.badgeVariant}>{priorityMeta.label}</Badge>
                      {isFocusProject && <Badge variant="primary">Priorité</Badge>}
                    </div>
                    <CardDescription>{project.goal}</CardDescription>
                    {project.description && (
                      <p className="text-xs text-zinc-600 dark:text-zinc-400">{project.description}</p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Select
                      aria-label={`Statut du projet ${project.name}`}
                      value={project.status}
                      className="h-8 min-h-8 w-auto py-1 text-xs"
                      onChange={(e) =>
                        void handleStatusChange(project, e.target.value as ProjectStatus)
                      }
                    >
                      <option value="planned">Planifié</option>
                      <option value="active">Actif</option>
                      <option value="blocked">Bloqué</option>
                      <option value="completed">Terminé</option>
                      <option value="archived">Archivé</option>
                    </Select>

                    {!isFocusProject && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={async () => {
                          if (await setActivePriority(project.name, null, project.id)) {
                            setFeedback(
                              `Projet « ${project.name} » défini comme priorité.`,
                            );
                          }
                        }}
                      >
                        <Icon icon={Target02Icon} size={14} />
                        Définir comme priorité
                      </Button>
                    )}

                    <Button variant="ghost" size="sm" onClick={() => openEdit(project)}>
                      Modifier
                    </Button>

                    <InlineConfirm
                      triggerLabel="Supprimer"
                      ariaLabel={`Supprimer le projet ${project.name}`}
                      onConfirm={async () => {
                        if (isFocusProject && dataMode === 'local_demo') {
                          await setActivePriority(null, null, null);
                        }
                        if (await deleteProject(project.id)) {
                          setFeedback(`Projet « ${project.name} » supprimé.`);
                        }
                      }}
                    />
                  </div>
                </CardHeader>

                <CardContent className="space-y-3">
                  <div className="rounded-xl bg-zinc-50/80 p-3 dark:bg-zinc-800/60">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                      Prochaine action
                    </p>
                    <p className="mt-0.5 text-sm font-medium text-zinc-900 dark:text-zinc-100">
                      {project.nextAction || 'Aucune prochaine action définie'}
                    </p>
                  </div>

                  {project.deliverables && project.deliverables.length > 0 && (
                    <ul className="flex flex-wrap gap-1.5">
                      {project.deliverables.map((item, idx) => (
                        <li key={`${project.id}-deliv-${idx}`}>
                          <Badge variant="neutral">{item}</Badge>
                        </li>
                      ))}
                    </ul>
                  )}

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
                    {project.targetDate && (
                      <span>Cible : {formatDateFr(project.targetDate)}</span>
                    )}
                    <span>
                      Tâches :{' '}
                      <Link to="/tasks" className="font-medium text-teal-800 dark:text-teal-300 hover:underline">
                        {linkedTasks}
                      </Link>
                    </span>
                    <span>
                      Séances :{' '}
                      <Link to="/sessions" className="font-medium text-teal-800 dark:text-teal-300 hover:underline">
                        {linkedSessions}
                      </Link>
                    </span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
