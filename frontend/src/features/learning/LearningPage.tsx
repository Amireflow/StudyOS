import { useMemo, useState } from 'react';
import {
  Add01Icon,
  BookOpen01Icon,
  InformationCircleIcon,
  Search01Icon,
} from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { Button, buttonClasses } from '../../components/ui/Button';
import { Input } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type {
  LearningModule,
  LearningPath,
  LearningStatus,
  Lesson,
} from '../../types/domain';
import { PathForm } from './LearningForms';
import { LearningPathCard } from './LearningPathCard';
import type {
  LearningModuleFormValues,
  LearningPathFormValues,
  LessonFormValues,
} from './learningSchema';

type PathStatusFilter = 'all' | 'active' | 'paused' | 'completed';

const STATUS_FILTER_OPTIONS: Array<{ value: PathStatusFilter; label: string }> = [
  { value: 'all', label: 'Tous' },
  { value: 'active', label: 'Actifs' },
  { value: 'paused', label: 'En pause' },
  { value: 'completed', label: 'Terminés' },
];

export function LearningPage() {
  const {
    paths,
    modules,
    lessons,
    skills,
    assessments,
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
  } = useLearningStore();
  const { tasks, sessions } = useStudyStore();

  const [isPathFormOpen, setIsPathFormOpen] = useState(false);
  const [editingPath, setEditingPath] = useState<LearningPath | null>(null);
  const [activeModulePathId, setActiveModulePathId] = useState<string | null>(null);
  const [activeLessonModuleId, setActiveLessonModuleId] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<PathStatusFilter>('all');
  const [feedback, setFeedback] = useState<string | null>(null);

  const summary = useMemo(() => {
    const activePaths = paths.filter((p) => p.status === 'active').length;
    const studiedLessons = lessons.filter(
      (l) =>
        l.status === 'active' ||
        l.status === 'paused' ||
        l.status === 'completed' ||
        sessions.some((s) => s.lessonId === l.id),
    ).length;
    const completedLessons = lessons.filter((l) => l.status === 'completed').length;
    const evaluatedSkillIds = new Set(assessments.map((a) => a.skillId));
    const evaluatedSkillsCount = skills.filter(
      (s) => evaluatedSkillIds.has(s.id) || s.currentLevel > 0,
    ).length;
    const validatedSkillsCount = skills.filter(
      (s) =>
        s.currentLevel > 0 &&
        (assessments.some((a) => a.skillId === s.id && a.status === 'approved') ||
          s.lastAssessedAt !== null),
    ).length;
    const linkedTasksCount = tasks.filter((t) => Boolean(t.moduleId)).length;
    const linkedSessionsCount = sessions.filter((s) => Boolean(s.moduleId || s.lessonId)).length;
    return {
      totalPaths: paths.length,
      activePaths,
      studiedLessons,
      completedLessons,
      totalLessons: lessons.length,
      evaluatedSkillsCount,
      validatedSkillsCount,
      linkedLinksCount: linkedTasksCount + linkedSessionsCount,
    };
  }, [paths, lessons, skills, assessments, tasks, sessions]);

  const overallProgressPct =
    summary.totalLessons === 0
      ? 0
      : Math.round((summary.completedLessons / summary.totalLessons) * 100);

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

  const filteredPaths = useMemo(() => {
    const normalizedSearch = searchQuery.trim().toLowerCase();
    return paths.filter((path) => {
      if (statusFilter !== 'all' && path.status !== statusFilter) {
        return false;
      }
      if (!normalizedSearch) {
        return true;
      }
      const pathModules = modulesByPathId.get(path.id) ?? [];
      const pathLessons = pathModules.flatMap((m) => lessonsByModuleId.get(m.id) ?? []);
      const searchableChunks = [
        path.title,
        path.goal,
        path.description ?? '',
        ...pathModules.flatMap((m) => [m.title, m.description ?? '']),
        ...pathLessons.flatMap((l) => [l.title, l.content ?? '']),
      ];
      return searchableChunks.some((chunk) => chunk.toLowerCase().includes(normalizedSearch));
    });
  }, [lessonsByModuleId, modulesByPathId, paths, searchQuery, statusFilter]);

  const openCreatePath = () => {
    setEditingPath(null);
    setIsPathFormOpen(true);
  };

  const openEditPath = (path: LearningPath) => {
    setEditingPath(path);
    setIsPathFormOpen(true);
  };

  const handlePathSubmit = async (values: LearningPathFormValues) => {
    if (editingPath) {
      if (await updatePath(editingPath.id, values)) {
        setFeedback(`Parcours « ${values.title} » mis à jour.`);
        setIsPathFormOpen(false);
        setEditingPath(null);
      }
      return;
    }

    if (await createPath(values)) {
      setFeedback(`Parcours « ${values.title} » créé.`);
      setIsPathFormOpen(false);
    }
  };

  const handleCreateModule = async (pathId: string, values: LearningModuleFormValues) => {
    if (await createModule({ pathId, ...values })) {
      setFeedback(`Module « ${values.title} » ajouté.`);
      setActiveModulePathId(null);
    }
  };

  const handleUpdateModuleStatus = async (moduleId: string, status: LearningStatus) => {
    await updateModule(moduleId, { status });
  };

  const handleDeleteModule = async (mod: LearningModule) => {
    if (await deleteModule(mod.id)) {
      setFeedback(`Module « ${mod.title} » supprimé.`);
    }
  };

  const handleCreateLesson = async (moduleId: string, values: LessonFormValues) => {
    if (await createLesson({ moduleId, ...values })) {
      setFeedback(`Leçon « ${values.title} » ajoutée.`);
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

  const handleDeleteLesson = async (lesson: Lesson) => {
    if (await deleteLesson(lesson.id)) {
      setFeedback(`Leçon « ${lesson.title} » supprimée.`);
    }
  };

  const handleDeletePath = async (path: LearningPath) => {
    if (await deletePath(path.id)) {
      setFeedback(`Parcours « ${path.title} » supprimé.`);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <header>
          <h1 className="ui-page-title">
            Apprentissage
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
            Apprentissage
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
        <div>
          <h1 className="ui-page-title">
            Apprentissage
          </h1>
          {summary.totalLessons > 0 && (
            <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
              {`${summary.completedLessons}/${summary.totalLessons} leçons · ${overallProgressPct} %`}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Link
            to={"/ai-coach?prompt=" + encodeURIComponent("Analyse mes apprentissages et objectifs existants, puis propose un parcours pédagogique complet adapté à mon niveau. Structure les modules, leçons, exercices, projets et critères de validation. Ne crée rien avant ma confirmation.")}
            className={buttonClasses('primary', 'sm')}
          >
            <Icon icon={BookOpen01Icon} size={15} />
            Créer avec le Copilote
          </Link>
          <details className="relative">
            <summary className="inline-flex min-h-11 cursor-pointer list-none items-center rounded-lg bg-zinc-100 px-3 text-xs font-semibold text-zinc-600 hover:bg-zinc-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 dark:focus-visible:outline-teal-400">
              Plus
            </summary>
            <div className="absolute right-0 z-30 mt-2 w-56 rounded-xl border border-zinc-200 bg-white p-2 shadow-lg dark:border-zinc-700 dark:bg-zinc-900">
              <Button type="button" variant="ghost" size="sm" className="min-h-11 w-full justify-start" onClick={openCreatePath}>
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

      {/* Tuiles KPI synthétiques */}
      <section aria-label="Indicateurs d’apprentissage" className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 sm:gap-3">
        <button
          type="button"
          aria-pressed={statusFilter === 'all'}
          aria-label={`Parcours (${summary.totalPaths}) — afficher tous`}
          onClick={() => setStatusFilter('all')}
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            statusFilter === 'all' && paths.length > 0
              ? 'bg-teal-50/75 dark:bg-teal-950/35'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Parcours</p>
          <p className="mt-0.5 text-xl font-semibold tabular-nums text-zinc-900 sm:mt-1 sm:text-2xl dark:text-zinc-50">
            {summary.totalPaths}
          </p>
        </button>

        <button
          type="button"
          aria-pressed={statusFilter === 'active'}
          aria-label={`Actifs (${summary.activePaths}) — filtrer`}
          onClick={() => setStatusFilter((prev) => (prev === 'active' ? 'all' : 'active'))}
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            statusFilter === 'active'
              ? 'bg-teal-50 dark:bg-teal-950/45'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Actifs</p>
          <p className="mt-0.5 text-xl font-semibold tabular-nums text-teal-800 sm:mt-1 sm:text-2xl dark:text-teal-300">
            {summary.activePaths}
          </p>
        </button>

        <div className="rounded-2xl bg-white p-3 sm:p-4 dark:bg-zinc-900">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Leçons</p>
            <span className="text-[11px] font-medium tabular-nums text-zinc-400 dark:text-zinc-500">
              {overallProgressPct}%
            </span>
          </div>
          <p
            className="mt-0.5 text-xl font-semibold tabular-nums text-emerald-700 sm:mt-1 sm:text-2xl dark:text-emerald-400"
            data-testid="learning-completed-lessons"
          >
            {summary.completedLessons} / {summary.totalLessons}
          </p>
          <p
            className="mt-0.5 text-[11px] text-zinc-500 dark:text-zinc-400"
            data-testid="learning-studied-lessons"
          >
            {summary.studiedLessons} leçon{summary.studiedLessons > 1 ? 's' : ''} étudiée
            {summary.studiedLessons > 1 ? 's' : ''}
          </p>
          <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
            <div
              className="h-full rounded-full bg-emerald-600 transition-all dark:bg-emerald-400"
              style={{ width: `${overallProgressPct}%` }}
            />
          </div>
        </div>

        <div className="rounded-2xl bg-white p-3 sm:p-4 dark:bg-zinc-900">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Compétences</p>
          <p
            className="mt-0.5 text-xl font-semibold tabular-nums text-zinc-900 sm:mt-1 sm:text-2xl dark:text-zinc-50"
            data-testid="learning-validated-skills"
          >
            {summary.evaluatedSkillsCount} / {summary.validatedSkillsCount}
          </p>
          <p className="mt-0.5 text-[11px] text-zinc-500 dark:text-zinc-400">
            {summary.linkedLinksCount} lien{summary.linkedLinksCount > 1 ? 's' : ''} actif
            {summary.linkedLinksCount > 1 ? 's' : ''}
          </p>
        </div>
      </section>

      {/* Bandeau règle LEARN-03 */}
      <div
        role="note"
        className="flex flex-col gap-2.5 rounded-2xl bg-teal-50/60 px-4 py-2.5 text-xs text-zinc-700 sm:flex-row sm:items-center sm:justify-between dark:bg-teal-950/30 dark:text-zinc-300"
      >
        <div className="flex items-center gap-2">
          <Icon
            icon={InformationCircleIcon}
            size={15}
            className="shrink-0 text-teal-700 dark:text-teal-400"
          />
          <p>Terminer une leçon ne valide jamais automatiquement une compétence.</p>
        </div>
        <Link to="/skills" className={buttonClasses('secondary', 'sm')}>
          Compétences
        </Link>
      </div>

      {/* Barre recherche + filtres */}
      {paths.length > 0 && (
        <section
          aria-label="Recherche et filtres des parcours"
          className="flex flex-col gap-3 rounded-2xl bg-white p-3.5 sm:flex-row sm:items-center sm:justify-between dark:bg-zinc-900"
        >
          <div className="relative flex-1 sm:max-w-xs">
            <Icon
              icon={Search01Icon}
              size={15}
              className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-zinc-400 dark:text-zinc-500"
            />
            <Input
              aria-label="Rechercher un parcours"
              type="search"
              value={searchQuery}
              placeholder="Rechercher un parcours…"
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0">
            {STATUS_FILTER_OPTIONS.map((option) => {
              const isActive = statusFilter === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setStatusFilter(option.value)}
                  className={cn(
                    'shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors',
                    isActive
                      ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                      : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700',
                  )}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        </section>
      )}

      {/* Formulaire parcours */}
      {isPathFormOpen && (
        <PathForm
          editingPath={editingPath}
          onSubmit={handlePathSubmit}
          onCancel={() => {
            setIsPathFormOpen(false);
            setEditingPath(null);
          }}
        />
      )}

      {/* Liste des parcours ou états vides */}
      {paths.length === 0 ? (
        <div className="rounded-2xl bg-white py-8 dark:bg-zinc-900">
          <EmptyState
            icon={
              <Icon
                icon={BookOpen01Icon}
                size={17}
                className="text-teal-700 dark:text-teal-400"
              />
            }
            title="Aucun parcours d’apprentissage"
            action={
              <Link
                to={"/ai-coach?prompt=" + encodeURIComponent("Aide-moi à définir le parcours d'apprentissage le plus pertinent à partir de mes objectifs et de mes compétences actuelles. Propose le plan complet et attends ma validation avant de créer les éléments.")}
                className={buttonClasses('primary', 'md')}
              >
                Créer mon premier parcours avec le Copilote
              </Link>
            }
          />
        </div>
      ) : filteredPaths.length === 0 ? (
        <EmptyState
          icon={<Icon icon={BookOpen01Icon} size={17} />}
          title="Aucun parcours ne correspond aux filtres"
          action={
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('all');
              }}
            >
              Réinitialiser les filtres
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {filteredPaths.map((path) => (
            <LearningPathCard
              key={path.id}
              path={path}
              pathModules={modulesByPathId.get(path.id) ?? []}
              lessonsByModuleId={lessonsByModuleId}
              tasks={tasks}
              sessions={sessions}
              isAddingModule={activeModulePathId === path.id}
              activeLessonModuleId={activeLessonModuleId}
              onOpenAddModule={(pathId) => setActiveModulePathId(pathId)}
              onCloseAddModule={() => setActiveModulePathId(null)}
              onCreateModule={handleCreateModule}
              onUpdateModuleStatus={handleUpdateModuleStatus}
              onDeleteModule={handleDeleteModule}
              onOpenAddLesson={(moduleId) => setActiveLessonModuleId(moduleId)}
              onCloseAddLesson={() => setActiveLessonModuleId(null)}
              onCreateLesson={handleCreateLesson}
              onToggleLesson={handleToggleLesson}
              onDeleteLesson={handleDeleteLesson}
              onEditPath={openEditPath}
              onDeletePath={handleDeletePath}
            />
          ))}
        </div>
      )}
    </div>
  );
}
