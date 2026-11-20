import { useMemo, useState, type FormEvent } from 'react';
import {
  Add01Icon,
  BookOpen01Icon,
  CheckmarkCircle02Icon,
  ExternalLinkIcon,
  GroupLayersIcon,
  InformationCircleIcon,
} from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { PageHeader } from '../../components/layout/PageHeader';
import { Badge } from '../../components/ui/Badge';
import { Button, buttonClasses } from '../../components/ui/Button';
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
import { extractFieldErrors } from '../../lib/validation';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type { LearningModule, LearningPath, LearningStatus, Lesson } from '../../types/domain';
import {
  LEARNING_STATUS_META,
  learningModuleSchema,
  learningPathSchema,
  lessonSchema,
  type LearningModuleFormValues,
  type LearningPathFormValues,
  type LessonFormValues,
} from './learningSchema';

type PathField = keyof LearningPathFormValues;
type ModuleField = keyof LearningModuleFormValues;
type LessonField = keyof LessonFormValues;

export function LearningPage() {
  const {
    paths,
    modules,
    lessons,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    createPath,
    updatePath,
    deletePath,
    createModule,
    updateModule,
    deleteModule,
    createLesson,
    setLessonStatus,
    deleteLesson,
    seedStarterPaths,
  } = useLearningStore();
  const { tasks, sessions } = useStudyStore();

  const [isPathFormOpen, setIsPathFormOpen] = useState(false);
  const [editingPath, setEditingPath] = useState<LearningPath | null>(null);
  const [pathValues, setPathValues] = useState<LearningPathFormValues>({
    title: '',
    goal: '',
    description: '',
    status: 'active',
  });
  const [pathErrors, setPathErrors] = useState<Partial<Record<PathField, string>>>({});

  const [activeModulePathId, setActiveModulePathId] = useState<string | null>(null);
  const [moduleValues, setModuleValues] = useState<LearningModuleFormValues>({
    title: '',
    description: '',
    position: 1,
    status: 'active',
  });
  const [moduleErrors, setModuleErrors] = useState<Partial<Record<ModuleField, string>>>({});

  const [activeLessonModuleId, setActiveLessonModuleId] = useState<string | null>(null);
  const [lessonValues, setLessonValues] = useState<LessonFormValues>({
    title: '',
    content: '',
    resourceUrl: '',
    position: 1,
    status: 'not_started',
  });
  const [lessonErrors, setLessonErrors] = useState<Partial<Record<LessonField, string>>>({});

  const [feedback, setFeedback] = useState<string | null>(null);

  const summary = useMemo(() => {
    const activePaths = paths.filter((p) => p.status === 'active').length;
    const completedLessons = lessons.filter((l) => l.status === 'completed').length;
    const linkedTasksCount = tasks.filter((t) => Boolean(t.moduleId)).length;
    const linkedSessionsCount = sessions.filter((s) => Boolean(s.moduleId || s.lessonId)).length;
    return {
      totalPaths: paths.length,
      activePaths,
      completedLessons,
      totalLessons: lessons.length,
      linkedLinksCount: linkedTasksCount + linkedSessionsCount,
    };
  }, [paths, lessons, tasks, sessions]);

  const modulesByPathId = useMemo(() => {
    const map = new Map<string, LearningModule[]>();
    for (const mod of modules) {
      const list = map.get(mod.pathId) ?? [];
      list.push(mod);
      map.set(mod.pathId, list);
    }
    for (const list of map.values()) {
      list.sort((a, b) => a.position - b.position);
    }
    return map;
  }, [modules]);

  const lessonsByModuleId = useMemo(() => {
    const map = new Map<string, Lesson[]>();
    for (const lesson of lessons) {
      const list = map.get(lesson.moduleId) ?? [];
      list.push(lesson);
      map.set(lesson.moduleId, list);
    }
    for (const list of map.values()) {
      list.sort((a, b) => a.position - b.position);
    }
    return map;
  }, [lessons]);

  const openCreatePath = () => {
    setEditingPath(null);
    setPathValues({ title: '', goal: '', description: '', status: 'active' });
    setPathErrors({});
    setIsPathFormOpen(true);
  };

  const openEditPath = (path: LearningPath) => {
    setEditingPath(path);
    setPathValues({
      title: path.title,
      goal: path.goal,
      description: path.description ?? '',
      status: path.status,
    });
    setPathErrors({});
    setIsPathFormOpen(true);
  };

  const handlePathSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = learningPathSchema.safeParse(pathValues);
    if (!parsed.success) {
      setPathErrors(extractFieldErrors<PathField>(parsed.error));
      return;
    }
    setPathErrors({});
    if (editingPath) {
      if (await updatePath(editingPath.id, parsed.data)) {
        setFeedback(`Parcours « ${parsed.data.title} » mis à jour.`);
        setIsPathFormOpen(false);
        setEditingPath(null);
      }
      return;
    }
    if (await createPath(parsed.data)) {
      setFeedback(`Parcours « ${parsed.data.title} » créé.`);
      setIsPathFormOpen(false);
    }
  };

  const openAddModule = (pathId: string) => {
    const existingCount = (modulesByPathId.get(pathId) ?? []).length;
    setActiveModulePathId(pathId);
    setModuleValues({
      title: '',
      description: '',
      position: existingCount + 1,
      status: 'active',
    });
    setModuleErrors({});
  };

  const handleModuleSubmit = async (event: FormEvent<HTMLFormElement>, pathId: string) => {
    event.preventDefault();
    const parsed = learningModuleSchema.safeParse(moduleValues);
    if (!parsed.success) {
      setModuleErrors(extractFieldErrors<ModuleField>(parsed.error));
      return;
    }
    setModuleErrors({});
    if (await createModule({ pathId, ...parsed.data })) {
      setFeedback(`Module « ${parsed.data.title} » ajouté.`);
      setActiveModulePathId(null);
    }
  };

  const openAddLesson = (moduleId: string) => {
    const existingCount = (lessonsByModuleId.get(moduleId) ?? []).length;
    setActiveLessonModuleId(moduleId);
    setLessonValues({
      title: '',
      content: '',
      resourceUrl: '',
      position: existingCount + 1,
      status: 'not_started',
    });
    setLessonErrors({});
  };

  const handleLessonSubmit = async (event: FormEvent<HTMLFormElement>, moduleId: string) => {
    event.preventDefault();
    const parsed = lessonSchema.safeParse(lessonValues);
    if (!parsed.success) {
      setLessonErrors(extractFieldErrors<LessonField>(parsed.error));
      return;
    }
    setLessonErrors({});
    if (await createLesson({ moduleId, ...parsed.data })) {
      setFeedback(`Leçon « ${parsed.data.title} » ajoutée.`);
      setActiveLessonModuleId(null);
    }
  };

  const handleToggleLesson = async (lesson: Lesson) => {
    const nextStatus: LearningStatus = lesson.status === 'completed' ? 'active' : 'completed';
    if (await setLessonStatus(lesson.id, nextStatus)) {
      setFeedback(
        nextStatus === 'completed'
          ? `Leçon « ${lesson.title} » marquée terminée (aucune compétence validée automatiquement).`
          : `Leçon « ${lesson.title} » rouverte.`,
      );
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <PageHeader title="Apprentissage" />
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <PageHeader title="Apprentissage" />
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Apprentissage"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {paths.length === 0 && (
              <Button
                variant="secondary"
                onClick={async () => {
                  if (await seedStarterPaths()) {
                    setFeedback('Parcours modèle « Socle Python & FastAPI » chargé.');
                  }
                }}
              >
                <Icon icon={BookOpen01Icon} size={15} />
                Charger un parcours exemple
              </Button>
            )}
            <Button variant="primary" onClick={openCreatePath}>
              <Icon icon={Add01Icon} size={15} />
              Nouveau parcours
            </Button>
          </div>
        }
      />

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Note concise LEARN-03 */}
      <div
        role="note"
        className="flex flex-col gap-2.5 rounded-2xl bg-white p-3.5 text-xs text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300 sm:flex-row sm:items-center sm:justify-between"
      >
        <div className="flex items-center gap-2">
          <Icon icon={InformationCircleIcon} size={16} className="shrink-0 text-teal-700 dark:text-teal-400" />
          <p>
            Terminer une leçon ne valide jamais automatiquement une compétence sans preuve.
          </p>
        </div>
        <Link to="/skills" className={buttonClasses('secondary', 'sm')}>
          Compétences
        </Link>
      </div>

      {/* Synthèse rapide */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Parcours</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
              {summary.totalPaths}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Actifs</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-teal-800 dark:text-teal-300">
              {summary.activePaths}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Leçons terminées</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-700 dark:text-emerald-400">
              {summary.completedLessons} / {summary.totalLessons}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Liens actifs</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
              {summary.linkedLinksCount}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Formulaire parcours */}
      {isPathFormOpen && (
        <Card>
          <CardHeader>
            <CardTitle>
              {editingPath ? 'Modifier le parcours' : 'Nouveau parcours'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePathSubmit} noValidate className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField id="path-title" label="Titre du parcours" required error={pathErrors.title}>
                  <Input
                    id="path-title"
                    value={pathValues.title}
                    hasError={Boolean(pathErrors.title)}
                    placeholder="Ex. Architecture Backend Python"
                    onChange={(e) => {
                      setPathValues((prev) => ({ ...prev, title: e.target.value }));
                      if (pathErrors.title) setPathErrors((prev) => ({ ...prev, title: undefined }));
                    }}
                  />
                </FormField>

                <FormField id="path-status" label="Statut" error={pathErrors.status}>
                  <Select
                    id="path-status"
                    value={pathValues.status}
                    onChange={(e) =>
                      setPathValues((prev) => ({
                        ...prev,
                        status: e.target.value as LearningStatus,
                      }))
                    }
                  >
                    <option value="not_started">Non démarré</option>
                    <option value="active">Actif</option>
                    <option value="paused">En pause</option>
                    <option value="completed">Terminé</option>
                  </Select>
                </FormField>
              </div>

              <FormField id="path-goal" label="Objectif mesurable" required error={pathErrors.goal}>
                <Input
                  id="path-goal"
                  value={pathValues.goal}
                  hasError={Boolean(pathErrors.goal)}
                  placeholder="Ex. Concevoir une API FastAPI testée de bout en bout"
                  onChange={(e) => {
                    setPathValues((prev) => ({ ...prev, goal: e.target.value }));
                    if (pathErrors.goal) setPathErrors((prev) => ({ ...prev, goal: undefined }));
                  }}
                />
              </FormField>

              <FormField id="path-description" label="Description (facultatif)" error={pathErrors.description}>
                <Textarea
                  id="path-description"
                  value={pathValues.description ?? ''}
                  placeholder="Contexte ou prérequis…"
                  onChange={(e) =>
                    setPathValues((prev) => ({ ...prev, description: e.target.value }))
                  }
                />
              </FormField>

              <div className="flex flex-wrap justify-end gap-2">
                <Button variant="secondary" onClick={() => setIsPathFormOpen(false)}>
                  Annuler
                </Button>
                <Button type="submit" variant="primary">
                  {editingPath ? 'Enregistrer le parcours' : 'Créer le parcours'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Liste des parcours */}
      {paths.length === 0 ? (
        <Card>
          <CardContent className="py-8">
            <EmptyState
              icon={<Icon icon={BookOpen01Icon} size={17} className="text-teal-700 dark:text-teal-400" />}
              title="Aucun parcours d’apprentissage"
              action={
                <Button variant="primary" onClick={openCreatePath}>
                  Créer mon premier parcours
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {paths.map((path) => {
            const pathModules = modulesByPathId.get(path.id) ?? [];
            const pathLessons = pathModules.flatMap((m) => lessonsByModuleId.get(m.id) ?? []);
            const doneLessonsCount = pathLessons.filter((l) => l.status === 'completed').length;
            const progressPct =
              pathLessons.length === 0
                ? 0
                : Math.round((doneLessonsCount / pathLessons.length) * 100);
            const pathMeta = LEARNING_STATUS_META[path.status];

            return (
              <Card key={path.id}>
                <CardHeader className="sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <CardTitle>{path.title}</CardTitle>
                      <Badge variant={pathMeta.badgeVariant}>{pathMeta.label}</Badge>
                      <Badge variant="neutral">
                        {doneLessonsCount}/{pathLessons.length} leçon{pathLessons.length > 1 ? 's' : ''} ({progressPct}%)
                      </Badge>
                    </div>
                    <CardDescription>{path.goal}</CardDescription>
                    {path.description && (
                      <p className="text-xs text-zinc-600 dark:text-zinc-400">{path.description}</p>
                    )}
                    <div className="mt-1.5 h-1.5 w-full max-w-md overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                      <div
                        className="h-full rounded-full bg-teal-700 dark:bg-teal-500 transition-all"
                        style={{ width: `${progressPct}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Button variant="secondary" size="sm" onClick={() => openAddModule(path.id)}>
                      <Icon icon={Add01Icon} size={14} />
                      Ajouter un module
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => openEditPath(path)}>
                      Modifier
                    </Button>
                    <InlineConfirm
                      triggerLabel="Supprimer"
                      ariaLabel={`Supprimer le parcours ${path.title}`}
                      onConfirm={async () => {
                        if (await deletePath(path.id)) {
                          setFeedback(`Parcours « ${path.title} » supprimé.`);
                        }
                      }}
                    />
                  </div>
                </CardHeader>

                <CardContent className="space-y-3">
                  {/* Formulaire d'ajout de module dans ce parcours */}
                  {activeModulePathId === path.id && (
                    <form
                      onSubmit={(e) => handleModuleSubmit(e, path.id)}
                      noValidate
                      className="space-y-3 rounded-xl bg-zinc-50 p-4 dark:bg-zinc-800/70"
                    >
                      <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                        Nouveau module
                      </p>
                      <div className="grid gap-3 sm:grid-cols-3">
                        <div className="sm:col-span-2">
                          <FormField
                            id={`module-title-${path.id}`}
                            label="Titre du module"
                            required
                            error={moduleErrors.title}
                          >
                            <Input
                              id={`module-title-${path.id}`}
                              value={moduleValues.title}
                              hasError={Boolean(moduleErrors.title)}
                              placeholder="Ex. Authentification JWT & Permissions"
                              onChange={(e) => {
                                setModuleValues((prev) => ({ ...prev, title: e.target.value }));
                                if (moduleErrors.title) {
                                  setModuleErrors((prev) => ({ ...prev, title: undefined }));
                                }
                              }}
                            />
                          </FormField>
                        </div>

                        <FormField
                          id={`module-pos-${path.id}`}
                          label="Ordre"
                          error={moduleErrors.position}
                        >
                          <Input
                            id={`module-pos-${path.id}`}
                            type="number"
                            min={0}
                            value={moduleValues.position}
                            onChange={(e) =>
                              setModuleValues((prev) => ({
                                ...prev,
                                position: Number(e.target.value),
                              }))
                            }
                          />
                        </FormField>
                      </div>

                      <FormField
                        id={`module-desc-${path.id}`}
                        label="Description (facultatif)"
                        error={moduleErrors.description}
                      >
                        <Input
                          id={`module-desc-${path.id}`}
                          value={moduleValues.description ?? ''}
                          placeholder="Notions abordées"
                          onChange={(e) =>
                            setModuleValues((prev) => ({ ...prev, description: e.target.value }))
                          }
                        />
                      </FormField>

                      <div className="flex justify-end gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setActiveModulePathId(null)}
                        >
                          Annuler
                        </Button>
                        <Button type="submit" variant="primary" size="sm">
                          Enregistrer le module
                        </Button>
                      </div>
                    </form>
                  )}

                  {pathModules.length === 0 ? (
                    <p className="rounded-xl bg-zinc-50/80 p-3.5 text-xs text-zinc-500 dark:bg-zinc-800/60 dark:text-zinc-400">
                      Aucun module dans ce parcours.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {pathModules.map((mod) => {
                        const modLessons = lessonsByModuleId.get(mod.id) ?? [];
                        const linkedModuleTasks = tasks.filter((t) => t.moduleId === mod.id).length;
                        const linkedModuleSessions = sessions.filter(
                          (s) => s.moduleId === mod.id,
                        ).length;

                        return (
                          <div
                            key={mod.id}
                            className="rounded-xl bg-zinc-50/80 p-4 dark:bg-zinc-800/60"
                          >
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                              <div className="space-y-1">
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge variant="neutral">
                                    <Icon icon={GroupLayersIcon} size={12} className="mr-1" />
                                    Module {mod.position}
                                  </Badge>
                                  <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                                    {mod.title}
                                  </h3>
                                  <Badge variant={LEARNING_STATUS_META[mod.status].badgeVariant}>
                                    {LEARNING_STATUS_META[mod.status].label}
                                  </Badge>
                                </div>
                                {mod.description && (
                                  <p className="text-xs text-zinc-600 dark:text-zinc-400">{mod.description}</p>
                                )}
                                {(linkedModuleTasks > 0 || linkedModuleSessions > 0) && (
                                  <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400">
                                    <span>
                                      Tâches :{' '}
                                      <Link
                                        to="/tasks"
                                        className="font-medium text-teal-800 dark:text-teal-300 hover:underline"
                                      >
                                        {linkedModuleTasks}
                                      </Link>
                                    </span>
                                    <span>
                                      Séances :{' '}
                                      <Link
                                        to="/sessions"
                                        className="font-medium text-teal-800 dark:text-teal-300 hover:underline"
                                      >
                                        {linkedModuleSessions}
                                      </Link>
                                    </span>
                                  </div>
                                )}
                              </div>

                              <div className="flex flex-wrap items-center gap-2">
                                <Select
                                  aria-label={`Statut du module ${mod.title}`}
                                  value={mod.status}
                                  className="h-8 min-h-8 w-auto py-1 text-xs"
                                  onChange={(e) =>
                                    void updateModule(mod.id, {
                                      status: e.target.value as LearningStatus,
                                    })
                                  }
                                >
                                  <option value="not_started">Non démarré</option>
                                  <option value="active">Actif</option>
                                  <option value="paused">En pause</option>
                                  <option value="completed">Terminé</option>
                                </Select>
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  onClick={() => openAddLesson(mod.id)}
                                >
                                  <Icon icon={Add01Icon} size={14} />
                                  Ajouter une leçon
                                </Button>
                                <InlineConfirm
                                  triggerLabel="Supprimer"
                                  ariaLabel={`Supprimer le module ${mod.title}`}
                                  onConfirm={async () => {
                                    if (await deleteModule(mod.id)) {
                                      setFeedback(`Module « ${mod.title} » supprimé.`);
                                    }
                                  }}
                                />
                              </div>
                            </div>

                            {/* Formulaire d'ajout de leçon */}
                            {activeLessonModuleId === mod.id && (
                              <form
                                onSubmit={(e) => handleLessonSubmit(e, mod.id)}
                                noValidate
                                className="mt-3 space-y-3 rounded-xl bg-white p-3.5 dark:bg-zinc-900"
                              >
                                <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-50">
                                  Nouvelle leçon
                                </p>
                                <div className="grid gap-3 sm:grid-cols-3">
                                  <div className="sm:col-span-2">
                                    <FormField
                                      id={`lesson-title-${mod.id}`}
                                      label="Titre de la leçon"
                                      required
                                      error={lessonErrors.title}
                                    >
                                      <Input
                                        id={`lesson-title-${mod.id}`}
                                        value={lessonValues.title}
                                        hasError={Boolean(lessonErrors.title)}
                                        placeholder="Ex. Valider les schémas Pydantic"
                                        onChange={(e) => {
                                          setLessonValues((prev) => ({
                                            ...prev,
                                            title: e.target.value,
                                          }));
                                          if (lessonErrors.title) {
                                            setLessonErrors((prev) => ({
                                              ...prev,
                                              title: undefined,
                                            }));
                                          }
                                        }}
                                      />
                                    </FormField>
                                  </div>

                                  <FormField
                                    id={`lesson-pos-${mod.id}`}
                                    label="Ordre"
                                    error={lessonErrors.position}
                                  >
                                    <Input
                                      id={`lesson-pos-${mod.id}`}
                                      type="number"
                                      min={0}
                                      value={lessonValues.position}
                                      onChange={(e) =>
                                        setLessonValues((prev) => ({
                                          ...prev,
                                          position: Number(e.target.value),
                                        }))
                                      }
                                    />
                                  </FormField>
                                </div>

                                <FormField
                                  id={`lesson-url-${mod.id}`}
                                  label="Ressource (URL http/https facultative)"
                                  error={lessonErrors.resourceUrl}
                                >
                                  <Input
                                    id={`lesson-url-${mod.id}`}
                                    type="url"
                                    value={lessonValues.resourceUrl ?? ''}
                                    hasError={Boolean(lessonErrors.resourceUrl)}
                                    placeholder="https://docs.python.org/3/"
                                    onChange={(e) => {
                                      setLessonValues((prev) => ({
                                        ...prev,
                                        resourceUrl: e.target.value,
                                      }));
                                      if (lessonErrors.resourceUrl) {
                                        setLessonErrors((prev) => ({
                                          ...prev,
                                          resourceUrl: undefined,
                                        }));
                                      }
                                    }}
                                  />
                                </FormField>

                                <FormField
                                  id={`lesson-content-${mod.id}`}
                                  label="Notes / objectifs de la leçon"
                                  error={lessonErrors.content}
                                >
                                  <Textarea
                                    id={`lesson-content-${mod.id}`}
                                    value={lessonValues.content ?? ''}
                                    placeholder="Points clés ou exercice associé"
                                    onChange={(e) =>
                                      setLessonValues((prev) => ({
                                        ...prev,
                                        content: e.target.value,
                                      }))
                                    }
                                  />
                                </FormField>

                                <div className="flex justify-end gap-2">
                                  <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => setActiveLessonModuleId(null)}
                                  >
                                    Annuler
                                  </Button>
                                  <Button type="submit" variant="primary" size="sm">
                                    Enregistrer la leçon
                                  </Button>
                                </div>
                              </form>
                            )}

                            {/* Leçons du module */}
                            {modLessons.length > 0 && (
                              <ul className="mt-3 space-y-1.5">
                                {modLessons.map((lesson) => {
                                  const isCompleted = lesson.status === 'completed';
                                  const linkedLessonSessions = sessions.filter(
                                    (s) => s.lessonId === lesson.id,
                                  ).length;

                                  return (
                                    <li
                                      key={lesson.id}
                                      className="flex flex-col gap-2 rounded-xl bg-white px-3.5 py-2.5 dark:bg-zinc-900 sm:flex-row sm:items-center sm:justify-between"
                                    >
                                      <div className="space-y-0.5">
                                        <div className="flex flex-wrap items-center gap-2">
                                          <span className="text-xs font-medium tabular-nums text-zinc-400 dark:text-zinc-500">
                                            #{lesson.position}
                                          </span>
                                          <span
                                            className={
                                              isCompleted
                                                ? 'text-sm font-medium text-zinc-400 dark:text-zinc-500 line-through'
                                                : 'text-sm font-medium text-zinc-900 dark:text-zinc-100'
                                            }
                                          >
                                            {lesson.title}
                                          </span>
                                          <Badge
                                            variant={LEARNING_STATUS_META[lesson.status].badgeVariant}
                                          >
                                            {LEARNING_STATUS_META[lesson.status].label}
                                          </Badge>
                                          {linkedLessonSessions > 0 && (
                                            <Badge variant="neutral">
                                              {linkedLessonSessions} séance
                                              {linkedLessonSessions > 1 ? 's' : ''}
                                            </Badge>
                                          )}
                                        </div>
                                        {lesson.content && (
                                          <p className="text-xs text-zinc-600 dark:text-zinc-400">{lesson.content}</p>
                                        )}
                                        {lesson.resourceUrl && (
                                          <a
                                            href={lesson.resourceUrl}
                                            target="_blank"
                                            rel="noreferrer noopener"
                                            className="inline-flex items-center gap-1 text-xs font-medium text-teal-800 dark:text-teal-300 hover:underline"
                                          >
                                            Ressource externe
                                            <Icon icon={ExternalLinkIcon} size={12} />
                                          </a>
                                        )}
                                      </div>

                                      <div className="flex flex-wrap items-center gap-2">
                                        <Button
                                          variant={isCompleted ? 'secondary' : 'primary'}
                                          size="sm"
                                          onClick={() => void handleToggleLesson(lesson)}
                                        >
                                          <Icon icon={CheckmarkCircle02Icon} size={14} />
                                          {isCompleted ? 'Rouvrir' : 'Marquer terminée'}
                                        </Button>
                                        <InlineConfirm
                                          triggerLabel="Supprimer"
                                          ariaLabel={`Supprimer la leçon ${lesson.title}`}
                                          onConfirm={async () => {
                                            if (await deleteLesson(lesson.id)) {
                                              setFeedback(`Leçon « ${lesson.title} » supprimée.`);
                                            }
                                          }}
                                        />
                                      </div>
                                    </li>
                                  );
                                })}
                              </ul>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
