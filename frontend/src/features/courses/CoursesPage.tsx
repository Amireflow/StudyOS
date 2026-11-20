import { useMemo, useState } from 'react';
import {
  Add01Icon,
  ArrowRight01Icon,
  BookOpen01Icon,
  Mortarboard02Icon,
  Search01Icon,
} from '@hugeicons/core-free-icons';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SuccessBanner,
} from '../../components/ui/StateFeedback';
import type { CourseCreateInput } from '../../lib/coursesApi';
import { useCoursesStore } from '../../state/CoursesStoreContext';
import type { CourseStatus } from '../../types/domain';
import { CourseCreatorPanel } from './CourseCreatorPanel';
import { CourseDetailView } from './CourseDetailView';

type CourseStatusFilter = 'all' | CourseStatus;

const FILTER_OPTIONS: Array<{ value: CourseStatusFilter; label: string }> = [
  { value: 'all', label: 'Tous' },
  { value: 'active', label: 'Actifs' },
  { value: 'paused', label: 'En pause' },
  { value: 'completed', label: 'Terminés' },
];

export function CoursesPage() {
  const { courseId } = useParams<{ courseId?: string }>();
  const navigate = useNavigate();

  const {
    courses,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    previewCourse,
    createCourse,
  } = useCoursesStore();

  const [isCreatorOpen, setIsCreatorOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<CourseStatusFilter>('all');
  const [feedback, setFeedback] = useState<string | null>(null);

  const stats = useMemo(() => {
    const activeCount = courses.filter((c) => c.status === 'active').length;
    const completedLessons = courses.reduce((acc, c) => acc + c.completedLessonsCount, 0);
    const totalResources = courses.reduce((acc, c) => acc + c.resourcesCount, 0);
    return { activeCount, completedLessons, totalResources };
  }, [courses]);

  const filteredCourses = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return courses.filter((course) => {
      if (statusFilter !== 'all' && course.status !== statusFilter) {
        return false;
      }
      if (!q) return true;
      return (
        course.title.toLowerCase().includes(q) ||
        course.subject.toLowerCase().includes(q) ||
        course.domain.toLowerCase().includes(q)
      );
    });
  }, [courses, searchQuery, statusFilter]);

  if (courseId) {
    return <CourseDetailView courseId={courseId} />;
  }

  const handleCreateCourse = async (input: CourseCreateInput) => {
    setIsCreating(true);
    clearMutationError();
    try {
      const created = await createCourse(input);
      if (created) {
        setIsCreatorOpen(false);
        navigate(`/courses/${created.id}`);
      }
    } finally {
      setIsCreating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <header>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 sm:text-2xl dark:text-zinc-50">
            Cours
          </h1>
        </header>
        <LoadingState message="Chargement des cours…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <header>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 sm:text-2xl dark:text-zinc-50">
            Cours
          </h1>
        </header>
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  return (
    <div className="space-y-3.5 sm:space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-2.5">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 sm:text-2xl dark:text-zinc-50">
            Cours
          </h1>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            {stats.activeCount} actif{stats.activeCount > 1 ? 's' : ''} · {stats.completedLessons} chapitres lus · {stats.totalResources} ressources
          </p>
        </div>

        <Button
          type="button"
          variant={isCreatorOpen ? 'secondary' : 'primary'}
          size="sm"
          onClick={() => setIsCreatorOpen((open) => !open)}
        >
          <Icon icon={Add01Icon} size={15} />
          {isCreatorOpen ? 'Fermer' : 'Nouveau cours'}
        </Button>
      </header>

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {isCreatorOpen && (
        <CourseCreatorPanel
          onPreview={previewCourse}
          onCreate={handleCreateCourse}
          onCancel={() => setIsCreatorOpen(false)}
          isSubmitting={isCreating}
        />
      )}

      <div className="flex flex-col gap-2.5 rounded-2xl bg-white p-3.5 sm:flex-row sm:items-center sm:justify-between sm:p-4 dark:bg-zinc-900">
        <div className="relative flex-1">
          <Icon
            icon={Search01Icon}
            size={15}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"
          />
          <Input
            aria-label="Rechercher un cours"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Rechercher un langage, un domaine ou un cours…"
            className="pl-9"
          />
        </div>

        <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0" role="group" aria-label="Filtrer par statut">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              aria-pressed={statusFilter === opt.value}
              onClick={() => setStatusFilter(opt.value)}
              className={
                statusFilter === opt.value
                  ? 'shrink-0 rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white dark:bg-zinc-100 dark:text-zinc-950 cursor-pointer'
                  : 'shrink-0 rounded-lg bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 cursor-pointer'
              }
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {filteredCourses.length === 0 ? (
        <EmptyState
          title={courses.length === 0 ? 'Aucun cours créé' : 'Aucun cours ne correspond au filtre'}
          description={
            courses.length === 0
              ? 'Générez un cours complet progressif avec chapitres détaillés, exercices, projets corrigés et documentation.'
              : 'Modifiez votre recherche ou réinitialisez les filtres.'
          }
          icon={<Icon icon={Mortarboard02Icon} size={18} />}
          action={
            courses.length === 0 ? (
              <div className="flex flex-wrap items-center justify-center gap-2">
                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  onClick={() => void handleCreateCourse({ subject: 'Python', language: 'fr', totalLevels: 3, linkSkill: true })}
                >
                  <Icon icon={BookOpen01Icon} size={14} />
                  Démarrer Python
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleCreateCourse({ subject: 'TypeScript', language: 'fr', totalLevels: 3, linkSkill: true })}
                >
                  Démarrer TypeScript
                </Button>
              </div>
            ) : undefined
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filteredCourses.map((course) => {
            const pct =
              course.totalLessonsCount > 0
                ? Math.round((course.completedLessonsCount / course.totalLessonsCount) * 100)
                : 0;
            return (
              <article
                key={course.id}
                className="flex flex-col justify-between gap-4 rounded-2xl bg-white p-5 transition-colors hover:bg-zinc-50/90 dark:bg-zinc-900 dark:hover:bg-zinc-800/80"
              >
                <div className="space-y-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge variant="primary">{course.subject}</Badge>
                      <Badge variant="neutral">
                        Niveau {course.currentLevel}/{course.totalLevels}
                      </Badge>
                    </div>
                    {course.status === 'completed' ? (
                      <Badge variant="success">Terminé</Badge>
                    ) : course.status === 'paused' ? (
                      <Badge variant="warning">En pause</Badge>
                    ) : null}
                  </div>

                  <div>
                    <h2 className="line-clamp-1 text-base font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
                      {course.title}
                    </h2>
                    {course.description && (
                      <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
                        {course.description}
                      </p>
                    )}
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-zinc-500 dark:text-zinc-400">
                      <span>
                        {course.completedLessonsCount}/{course.totalLessonsCount} chapitres lus
                      </span>
                      <span className="tabular-nums font-medium">{pct} %</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                      <div
                        className="h-full rounded-full bg-teal-600 transition-all dark:bg-teal-400"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                      {course.resourcesCount} ressources curées
                    </span>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => navigate(`/courses/${course.id}`)}
                    >
                      Ouvrir le cours
                      <Icon icon={ArrowRight01Icon} size={14} />
                    </Button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
