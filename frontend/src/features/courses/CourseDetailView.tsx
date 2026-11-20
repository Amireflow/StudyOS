import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft01Icon,
  Award02Icon,
  BookOpen01Icon,
  CheckmarkCircle02Icon,
  LockIcon,
  SquareUnlock02Icon,
} from '@hugeicons/core-free-icons';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { InlineConfirm } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SuccessBanner,
} from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import type { CourseResourceInput, CourseSubmissionInput } from '../../lib/coursesApi';
import { useCourseDetail, useCoursesStore } from '../../state/CoursesStoreContext';
import type { CourseLesson } from '../../types/domain';
import { CourseLessonReader } from './CourseLessonReader';
import { CourseProjectPanel } from './CourseProjectPanel';
import { CourseResourcesPanel } from './CourseResourcesPanel';

type DetailTab = 'chapters' | 'project' | 'resources';

interface CourseDetailViewProps {
  courseId: string;
}

export function CourseDetailView({ courseId }: CourseDetailViewProps) {
  const navigate = useNavigate();
  const { detail, isLoading, error, retry } = useCourseDetail(courseId);
  const {
    mutationError,
    clearMutationError,
    updateCourse,
    deleteCourse,
    updateLessonStatus,
    addResource,
    deleteResource,
    submitWork,
    validateLevel,
    regenerateLevel,
  } = useCoursesStore();

  const [selectedLevelNumber, setSelectedLevelNumber] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<DetailTab>('chapters');
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (detail) {
      setSelectedLevelNumber(detail.currentLevel);
    }
  }, [detail?.currentLevel, detail?.id]);

  const orderedLevels = useMemo(
    () => (detail ? [...detail.levels].sort((a, b) => a.levelNumber - b.levelNumber) : []),
    [detail],
  );

  const activeLevel = useMemo(
    () =>
      orderedLevels.find((lv) => lv.levelNumber === selectedLevelNumber) ??
      orderedLevels.find((lv) => lv.levelNumber === detail?.currentLevel) ??
      orderedLevels[0] ??
      null,
    [detail?.currentLevel, orderedLevels, selectedLevelNumber],
  );

  const orderedLessons = useMemo(
    () =>
      activeLevel
        ? [...activeLevel.lessons].sort((a, b) => a.position - b.position)
        : [],
    [activeLevel],
  );

  useEffect(() => {
    if (orderedLessons.length === 0) {
      setSelectedLessonId(null);
      return;
    }
    if (!selectedLessonId || !orderedLessons.some((l) => l.id === selectedLessonId)) {
      const firstUnread = orderedLessons.find((l) => l.status !== 'completed');
      setSelectedLessonId(firstUnread?.id ?? orderedLessons[0].id);
    }
  }, [orderedLessons, selectedLessonId]);

  const activeLesson = useMemo(
    () => orderedLessons.find((l) => l.id === selectedLessonId) ?? orderedLessons[0] ?? null,
    [orderedLessons, selectedLessonId],
  );

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Link
          to="/courses"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
        >
          <Icon icon={ArrowLeft01Icon} size={14} />
          Retour aux cours
        </Link>
        <LoadingState message="Chargement du cours…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link
          to="/courses"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
        >
          <Icon icon={ArrowLeft01Icon} size={14} />
          Retour aux cours
        </Link>
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="space-y-4">
        <Link
          to="/courses"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
        >
          <Icon icon={ArrowLeft01Icon} size={14} />
          Retour aux cours
        </Link>
        <EmptyState
          title="Cours introuvable"
          description="Ce cours n’existe pas ou a été supprimé."
          action={
            <Button variant="primary" size="sm" onClick={() => navigate('/courses')}>
              Voir tous les cours
            </Button>
          }
        />
      </div>
    );
  }

  const handleTogglePause = async () => {
    const nextStatus = detail.status === 'paused' ? 'active' : 'paused';
    if (await updateCourse(detail.id, { status: nextStatus })) {
      setFeedback(nextStatus === 'paused' ? 'Cours mis en pause.' : 'Cours réactivé.');
    }
  };

  const handleDeleteCourse = async () => {
    if (await deleteCourse(detail.id)) {
      navigate('/courses');
    }
  };

  const handleToggleLesson = async (lesson: CourseLesson) => {
    const nextStatus = lesson.status === 'completed' ? 'not_started' : 'completed';
    if (await updateLessonStatus(detail.id, lesson.id, nextStatus)) {
      setFeedback(
        nextStatus === 'completed'
          ? `Chapitre « ${lesson.title} » marqué lu.`
          : `Chapitre « ${lesson.title} » rouvert.`,
      );
    }
  };

  const handleSubmitWork = async (input: CourseSubmissionInput) => {
    if (!activeLevel) return null;
    clearMutationError();
    return submitWork(detail.id, activeLevel.id, input);
  };

  const handleValidateLevel = async () => {
    if (!activeLevel) return;
    clearMutationError();
    const updated = await validateLevel(detail.id, activeLevel.id);
    if (updated) {
      const nextNum = Math.min(updated.totalLevels, activeLevel.levelNumber + 1);
      if (activeLevel.levelNumber < updated.totalLevels) {
        setFeedback(`Niveau ${activeLevel.levelNumber} validé : le Niveau ${nextNum} est débloqué !`);
        setSelectedLevelNumber(nextNum);
        setActiveTab('chapters');
      } else {
        setFeedback('Félicitations ! Vous avez validé tous les niveaux de ce cours.');
      }
    }
  };

  const handleRegenerateLevel = async () => {
    if (!activeLevel) return;
    clearMutationError();
    const updated = await regenerateLevel(detail.id, activeLevel.id);
    if (updated) {
      setFeedback(`Niveau ${activeLevel.levelNumber} régénéré (révision ${(activeLevel.revision ?? 1) + 1}).`);
    }
  };

  const handleAddResource = async (input: CourseResourceInput) => {
    clearMutationError();
    const created = await addResource(detail.id, input);
    if (created) {
      setFeedback(`Ressource « ${created.title} » ajoutée.`);
    }
    return created;
  };

  const handleDeleteResource = async (resourceId: string) => {
    clearMutationError();
    const ok = await deleteResource(detail.id, resourceId);
    if (ok) {
      setFeedback('Ressource supprimée.');
    }
    return ok;
  };

  const combinedResources = activeLevel
    ? [...activeLevel.resources, ...detail.resources.filter((r) => r.levelId === null)]
    : detail.resources;

  return (
    <div className="space-y-3.5 sm:space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Link
          to="/courses"
          className="inline-flex items-center gap-1.5 rounded-lg bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
        >
          <Icon icon={ArrowLeft01Icon} size={14} />
          Retour aux cours
        </Link>

        <div className="flex flex-wrap items-center gap-2">
          {activeLevel &&
            (activeLevel.status === 'unlocked' || activeLevel.status === 'in_progress') && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => void handleRegenerateLevel()}
              >
                Régénérer le niveau
              </Button>
            )}
          {detail.status !== 'completed' && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void handleTogglePause()}
            >
              {detail.status === 'paused' ? 'Reprendre le cours' : 'Mettre en pause'}
            </Button>
          )}
          <InlineConfirm
            triggerLabel="Supprimer le cours"
            confirmLabel="Confirmer la suppression"
            onConfirm={() => void handleDeleteCourse()}
          />
        </div>
      </div>

      <header className="rounded-2xl bg-white p-4 sm:p-6 dark:bg-zinc-900">
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          <Badge variant="primary">{detail.subject}</Badge>
          <Badge variant="neutral">{detail.domain}</Badge>
          <Badge variant={detail.status === 'completed' ? 'success' : 'neutral'}>
            Niveau {detail.currentLevel}/{detail.totalLevels}
          </Badge>
          {activeLevel?.generationSource && (
            <Badge variant="neutral">
              {activeLevel.generationSource} · Rev. {activeLevel.revision ?? 1}
            </Badge>
          )}
          {detail.status === 'paused' && <Badge variant="warning">En pause</Badge>}
        </div>

        <h1 className="mt-2 line-clamp-1 text-lg font-bold tracking-tight text-zinc-950 sm:mt-2.5 sm:text-2xl dark:text-zinc-50">
          {detail.title}
        </h1>
        {detail.description && (
          <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
            {detail.description}
          </p>
        )}
      </header>

      {feedback && (
        <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />
      )}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Progression par niveaux */}
      <nav
        aria-label="Niveaux du cours"
        className="no-scrollbar flex gap-2 overflow-x-auto pb-0.5 sm:grid sm:grid-cols-3 sm:gap-2.5 sm:overflow-visible sm:pb-0 lg:grid-cols-5"
      >
        {orderedLevels.map((lv) => {
          const isSelected = activeLevel?.id === lv.id;
          const isLocked = lv.status === 'locked';
          const isValidated = lv.status === 'validated';
          const statusIcon = isValidated
            ? CheckmarkCircle02Icon
            : isLocked
              ? LockIcon
              : SquareUnlock02Icon;

          return (
            <button
              key={lv.id}
              type="button"
              aria-pressed={isSelected}
              aria-label={`Niveau ${lv.levelNumber} : ${lv.title}`}
              onClick={() => setSelectedLevelNumber(lv.levelNumber)}
              className={cn(
                'flex min-w-[148px] shrink-0 flex-col items-start gap-1 rounded-2xl p-3 text-left transition-colors sm:min-w-0 sm:gap-1.5 sm:p-3.5 cursor-pointer',
                isSelected
                  ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950'
                  : isLocked
                    ? 'bg-zinc-100/70 text-zinc-500 hover:bg-zinc-100 dark:bg-zinc-900/60 dark:text-zinc-400 dark:hover:bg-zinc-800/80'
                    : 'bg-white text-zinc-800 hover:bg-zinc-50 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800',
              )}
            >
              <div className="flex w-full items-center justify-between gap-2 text-xs font-semibold">
                <span>Niveau {lv.levelNumber}</span>
                <Icon
                  icon={statusIcon}
                  size={15}
                  className={
                    isValidated
                      ? isSelected
                        ? 'text-emerald-300 dark:text-emerald-700'
                        : 'text-emerald-600 dark:text-emerald-400'
                      : isLocked
                        ? 'opacity-70'
                        : isSelected
                          ? 'text-teal-300 dark:text-teal-700'
                          : 'text-teal-600 dark:text-teal-400'
                  }
                />
              </div>
              <p className="line-clamp-1 text-[11px] font-medium opacity-90 sm:line-clamp-2">{lv.title}</p>
            </button>
          );
        })}
      </nav>

      {activeLevel && activeLevel.status === 'locked' && (
        <section className="rounded-2xl bg-white p-6 text-center dark:bg-zinc-900">
          <div className="mx-auto flex max-w-md flex-col items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
              <Icon icon={LockIcon} size={20} />
            </span>
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              Niveau {activeLevel.levelNumber} verrouillé : {activeLevel.title}
            </h2>
            <p className="text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
              {activeLevel.summary} Validez d’abord le projet du Niveau {detail.currentLevel} (seuil {activeLevel.levelNumber - 1 >= 4 ? 75 : 70}/100) pour débloquer et générer ce niveau.
            </p>
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => {
                setSelectedLevelNumber(detail.currentLevel);
                setActiveTab('project');
              }}
            >
              <Icon icon={Award02Icon} size={15} />
              Aller au projet du Niveau {detail.currentLevel}
            </Button>
          </div>
        </section>
      )}

      {activeLevel && activeLevel.status !== 'locked' && (
        <div className="space-y-3.5 sm:space-y-4">
          <div
            role="tablist"
            aria-label="Sections du niveau"
            className="grid grid-cols-3 gap-1 rounded-2xl bg-white p-1.5 sm:flex sm:flex-wrap sm:items-center sm:gap-2 sm:p-2 dark:bg-zinc-900"
          >
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'chapters'}
              onClick={() => setActiveTab('chapters')}
              className={cn(
                'truncate rounded-xl px-2.5 py-1.5 text-xs font-semibold transition-colors sm:px-4 sm:py-2 cursor-pointer',
                activeTab === 'chapters'
                  ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950'
                  : 'text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800',
              )}
            >
              Chapitres ({orderedLessons.length})
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'project'}
              onClick={() => setActiveTab('project')}
              className={cn(
                'truncate rounded-xl px-2.5 py-1.5 text-xs font-semibold transition-colors sm:px-4 sm:py-2 cursor-pointer',
                activeTab === 'project'
                  ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950'
                  : 'text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800',
              )}
            >
              Projet & validation
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'resources'}
              onClick={() => setActiveTab('resources')}
              className={cn(
                'truncate rounded-xl px-2.5 py-1.5 text-xs font-semibold transition-colors sm:px-4 sm:py-2 cursor-pointer',
                activeTab === 'resources'
                  ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950'
                  : 'text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800',
              )}
            >
              Docs & vidéos
            </button>
          </div>

          {activeTab === 'chapters' && (
            <div className="grid gap-3.5 sm:gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
              <aside className="space-y-1.5 rounded-2xl bg-white p-3 lg:self-start lg:space-y-2 lg:p-3.5 dark:bg-zinc-900">
                <p className="px-1.5 py-0.5 text-xs font-semibold text-zinc-500 dark:text-zinc-400">
                  Programme du niveau {activeLevel.levelNumber}
                </p>
                <div className="no-scrollbar flex gap-2 overflow-x-auto pb-0.5 lg:flex-col lg:space-y-1.5 lg:overflow-visible lg:pb-0">
                  {orderedLessons.map((lesson) => {
                    const selected = activeLesson?.id === lesson.id;
                    const done = lesson.status === 'completed';
                    return (
                      <button
                        key={lesson.id}
                        type="button"
                        onClick={() => setSelectedLessonId(lesson.id)}
                        className={cn(
                          'flex min-w-[165px] shrink-0 items-start gap-2 rounded-xl px-3 py-2 text-left text-xs transition-colors lg:w-full lg:min-w-0 lg:py-2.5 cursor-pointer',
                          selected
                            ? 'bg-teal-50 text-teal-950 dark:bg-teal-950/60 dark:text-teal-100'
                            : 'bg-zinc-50/70 text-zinc-700 hover:bg-zinc-100 dark:bg-zinc-800/50 dark:text-zinc-300 dark:hover:bg-zinc-800',
                        )}
                      >
                        <Icon
                          icon={done ? CheckmarkCircle02Icon : BookOpen01Icon}
                          size={15}
                          className={
                            done
                              ? 'mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400'
                              : 'mt-0.5 shrink-0 opacity-70'
                          }
                        />
                        <div className="min-w-0">
                          <p className="font-semibold">
                            Ch. {lesson.position}
                          </p>
                          <p className="line-clamp-1 text-[11px] opacity-90 lg:line-clamp-2">{lesson.title}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </aside>

              <div>
                {activeLesson ? (
                  <CourseLessonReader
                    lesson={activeLesson}
                    level={activeLevel}
                    onSelectLesson={setSelectedLessonId}
                    onToggleComplete={handleToggleLesson}
                    onSubmitExercise={handleSubmitWork}
                    onGoToProject={() => setActiveTab('project')}
                  />
                ) : (
                  <EmptyState title="Aucun chapitre disponible" />
                )}
              </div>
            </div>
          )}

          {activeTab === 'project' && (
            <CourseProjectPanel
              level={activeLevel}
              isFinalLevel={activeLevel.levelNumber === detail.totalLevels}
              onSubmitProject={handleSubmitWork}
              onValidateLevel={handleValidateLevel}
            />
          )}

          {activeTab === 'resources' && (
            <CourseResourcesPanel
              resources={combinedResources}
              activeLevelId={activeLevel.id}
              onAddResource={handleAddResource}
              onDeleteResource={handleDeleteResource}
            />
          )}
        </div>
      )}
    </div>
  );
}
