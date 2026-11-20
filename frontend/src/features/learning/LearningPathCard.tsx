import { useMemo, useState } from 'react';
import {
  Add01Icon,
  ArrowDown01Icon,
  ArrowUp01Icon,
  CheckmarkCircle02Icon,
  LinkSquare02Icon,
  PencilEdit02Icon,
  PlayIcon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { InlineConfirm, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import type {
  LearningModule,
  LearningPath,
  LearningStatus,
  Lesson,
  StudySession,
  Task,
} from '../../types/domain';
import { LessonForm, ModuleForm } from './LearningForms';
import {
  LEARNING_STATUS_META,
  type LearningModuleFormValues,
  type LessonFormValues,
} from './learningSchema';

export interface LearningPathCardProps {
  path: LearningPath;
  pathModules: LearningModule[];
  lessonsByModuleId: Map<string, Lesson[]>;
  tasks: Task[];
  sessions: StudySession[];
  isAddingModule: boolean;
  activeLessonModuleId: string | null;
  onOpenAddModule: (pathId: string) => void;
  onCloseAddModule: () => void;
  onCreateModule: (pathId: string, values: LearningModuleFormValues) => Promise<void>;
  onUpdateModuleStatus: (moduleId: string, status: LearningStatus) => Promise<void>;
  onDeleteModule: (mod: LearningModule) => Promise<void>;
  onOpenAddLesson: (moduleId: string) => void;
  onCloseAddLesson: () => void;
  onCreateLesson: (moduleId: string, values: LessonFormValues) => Promise<void>;
  onToggleLesson: (lesson: Lesson) => Promise<void>;
  onDeleteLesson: (lesson: Lesson) => Promise<void>;
  onEditPath: (path: LearningPath) => void;
  onDeletePath: (path: LearningPath) => Promise<void>;
}

export function LearningPathCard({
  path,
  pathModules,
  lessonsByModuleId,
  tasks,
  sessions,
  isAddingModule,
  activeLessonModuleId,
  onOpenAddModule,
  onCloseAddModule,
  onCreateModule,
  onUpdateModuleStatus,
  onDeleteModule,
  onOpenAddLesson,
  onCloseAddLesson,
  onCreateLesson,
  onToggleLesson,
  onDeleteLesson,
  onEditPath,
  onDeletePath,
}: LearningPathCardProps) {
  const [collapsedModuleIds, setCollapsedModuleIds] = useState<Set<string>>(() => new Set());

  const pathLessons = useMemo(
    () => pathModules.flatMap((m) => lessonsByModuleId.get(m.id) ?? []),
    [lessonsByModuleId, pathModules],
  );
  const doneLessonsCount = pathLessons.filter((l) => l.status === 'completed').length;
  const progressPct =
    pathLessons.length === 0 ? 0 : Math.round((doneLessonsCount / pathLessons.length) * 100);
  const pathMeta = LEARNING_STATUS_META[path.status];

  const nextLessonInfo = useMemo(() => {
    if (path.status === 'completed') return null;
    for (const mod of pathModules) {
      const modLessons = lessonsByModuleId.get(mod.id) ?? [];
      const pending = modLessons.find((lesson) => lesson.status !== 'completed');
      if (pending) {
        return { module: mod, lesson: pending };
      }
    }
    return null;
  }, [lessonsByModuleId, path.status, pathModules]);

  const toggleModuleCollapse = (moduleId: string) => {
    setCollapsedModuleIds((prev) => {
      const next = new Set(prev);
      if (next.has(moduleId)) {
        next.delete(moduleId);
      } else {
        next.add(moduleId);
      }
      return next;
    });
  };

  const handleOpenAddLesson = (moduleId: string) => {
    setCollapsedModuleIds((prev) => {
      if (!prev.has(moduleId)) return prev;
      const next = new Set(prev);
      next.delete(moduleId);
      return next;
    });
    onOpenAddLesson(moduleId);
  };

  return (
    <article
      aria-label={path.title}
      className="space-y-4 rounded-2xl bg-white p-5 sm:p-6 dark:bg-zinc-900"
    >
      {/* En-tête du parcours */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="line-clamp-1 text-base font-semibold tracking-tight text-zinc-900 sm:text-lg dark:text-zinc-50">
              {path.title}
            </h2>
            <Badge variant={pathMeta.badgeVariant}>{pathMeta.label}</Badge>
            <Badge variant="neutral">
              {doneLessonsCount}/{pathLessons.length} leçon{pathLessons.length > 1 ? 's' : ''} (
              {progressPct}%)
            </Badge>
          </div>

          <p className="line-clamp-1 text-xs font-medium text-zinc-700 dark:text-zinc-300">
            {path.goal}
          </p>

          {path.description && (
            <p className="line-clamp-2 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">
              {path.description}
            </p>
          )}

          <div className="h-1.5 w-full max-w-md overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
            <div
              className="h-full rounded-full bg-teal-600 transition-all dark:bg-teal-400"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => onOpenAddModule(path.id)}
          >
            <Icon icon={Add01Icon} size={14} />
            Ajouter un module
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => onEditPath(path)}>
            <Icon icon={PencilEdit02Icon} size={14} />
            Modifier
          </Button>
          <InlineConfirm
            triggerLabel="Supprimer"
            ariaLabel={`Supprimer le parcours ${path.title}`}
            onConfirm={() => void onDeletePath(path)}
          />
        </div>
      </div>

      {/* Prochaine leçon recommandée */}
      {nextLessonInfo && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-teal-50/75 px-4 py-3 dark:bg-teal-950/35">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-white text-teal-700 dark:bg-zinc-900 dark:text-teal-400">
              <Icon icon={PlayIcon} size={14} />
            </span>
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-teal-800 dark:text-teal-300">
                Prochaine leçon
              </p>
              <p className="truncate text-xs font-medium text-zinc-900 dark:text-zinc-100">
                {`${nextLessonInfo.module.title} — ${nextLessonInfo.lesson.title}`}
              </p>
            </div>
          </div>

          {nextLessonInfo.lesson.resourceUrl && (
            <a
              href={nextLessonInfo.lesson.resourceUrl}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-white px-2.5 py-1 text-xs font-medium text-teal-800 hover:bg-zinc-100 dark:bg-zinc-900 dark:text-teal-300 dark:hover:bg-zinc-800"
            >
              Ouvrir la ressource
              <Icon icon={LinkSquare02Icon} size={12} />
            </a>
          )}
        </div>
      )}

      {/* Formulaire d'ajout de module */}
      {isAddingModule && (
        <ModuleForm
          pathId={path.id}
          defaultPosition={pathModules.length + 1}
          onSubmit={(values) => onCreateModule(path.id, values)}
          onCancel={onCloseAddModule}
        />
      )}

      {/* Liste des modules */}
      {pathModules.length === 0 ? (
        <p className="rounded-xl bg-zinc-50/80 p-3.5 text-xs text-zinc-500 dark:bg-zinc-800/60 dark:text-zinc-400">
          Aucun module dans ce parcours.
        </p>
      ) : (
        <div className="space-y-3">
          {pathModules.map((mod) => {
            const modLessons = lessonsByModuleId.get(mod.id) ?? [];
            const modDone = modLessons.filter((l) => l.status === 'completed').length;
            const isCollapsed = collapsedModuleIds.has(mod.id);
            const linkedModuleTasks = tasks.filter((t) => t.moduleId === mod.id).length;
            const linkedModuleSessions = sessions.filter((s) => s.moduleId === mod.id).length;

            return (
              <div
                key={mod.id}
                className="rounded-xl bg-zinc-50/90 p-4 dark:bg-zinc-800/55"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex min-w-0 items-start gap-2.5">
                    <button
                      type="button"
                      aria-expanded={!isCollapsed}
                      aria-label={`Replier ou déplier le module ${mod.title}`}
                      onClick={() => toggleModuleCollapse(mod.id)}
                      className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white text-zinc-600 transition-colors hover:bg-zinc-100 hover:text-zinc-900 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    >
                      <Icon icon={isCollapsed ? ArrowDown01Icon : ArrowUp01Icon} size={15} />
                    </button>

                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-zinc-400 tabular-nums dark:text-zinc-500">
                          {String(mod.position).padStart(2, '0')}
                        </span>
                        <h3 className="line-clamp-1 text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                          {mod.title}
                        </h3>
                        <Badge variant={LEARNING_STATUS_META[mod.status].badgeVariant}>
                          {LEARNING_STATUS_META[mod.status].label}
                        </Badge>
                        {modLessons.length > 0 && (
                          <span className="text-[11px] font-medium tabular-nums text-zinc-500 dark:text-zinc-400">
                            {modDone}/{modLessons.length}
                          </span>
                        )}
                      </div>

                      {mod.description && (
                        <p className="line-clamp-2 text-xs text-zinc-600 dark:text-zinc-400">
                          {mod.description}
                        </p>
                      )}

                      {(linkedModuleTasks > 0 || linkedModuleSessions > 0) && (
                        <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400">
                          {linkedModuleTasks > 0 && (
                            <span>
                              Tâches :{' '}
                              <Link
                                to="/tasks"
                                className="font-medium text-teal-800 hover:underline dark:text-teal-300"
                              >
                                {linkedModuleTasks}
                              </Link>
                            </span>
                          )}
                          {linkedModuleSessions > 0 && (
                            <span>
                              Séances :{' '}
                              <Link
                                to="/sessions"
                                className="font-medium text-teal-800 hover:underline dark:text-teal-300"
                              >
                                {linkedModuleSessions}
                              </Link>
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 pl-9 sm:pl-0">
                    <Select
                      aria-label={`Statut du module ${mod.title}`}
                      value={mod.status}
                      className="h-8 min-h-8 w-auto bg-white py-1 text-xs dark:bg-zinc-900"
                      onChange={(e) =>
                        void onUpdateModuleStatus(mod.id, e.target.value as LearningStatus)
                      }
                    >
                      <option value="not_started">Non démarré</option>
                      <option value="active">Actif</option>
                      <option value="paused">En pause</option>
                      <option value="completed">Terminé</option>
                    </Select>

                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => handleOpenAddLesson(mod.id)}
                    >
                      <Icon icon={Add01Icon} size={14} />
                      Ajouter une leçon
                    </Button>

                    <InlineConfirm
                      triggerLabel="Supprimer"
                      ariaLabel={`Supprimer le module ${mod.title}`}
                      onConfirm={() => void onDeleteModule(mod)}
                    />
                  </div>
                </div>

                {!isCollapsed && (
                  <>
                    {activeLessonModuleId === mod.id && (
                      <LessonForm
                        moduleId={mod.id}
                        defaultPosition={modLessons.length + 1}
                        onSubmit={(values) => onCreateLesson(mod.id, values)}
                        onCancel={onCloseAddLesson}
                      />
                    )}

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
                              className="flex flex-col gap-2 rounded-xl bg-white px-3.5 py-2.5 sm:flex-row sm:items-center sm:justify-between dark:bg-zinc-900"
                            >
                              <div className="flex min-w-0 items-start gap-2.5">
                                {isCompleted ? (
                                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400">
                                    <Icon icon={CheckmarkCircle02Icon} size={14} />
                                  </span>
                                ) : (
                                  <span className="mt-0.5 flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-zinc-100 px-1 font-mono text-[11px] font-medium text-zinc-500 tabular-nums dark:bg-zinc-800 dark:text-zinc-400">
                                    #{lesson.position}
                                  </span>
                                )}

                                <div className="min-w-0 space-y-0.5">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span
                                      className={cn(
                                        'line-clamp-1 text-sm font-medium',
                                        isCompleted
                                          ? 'line-through text-zinc-400 dark:text-zinc-500'
                                          : 'text-zinc-900 dark:text-zinc-100',
                                      )}
                                    >
                                      {lesson.title}
                                    </span>
                                    {!isCompleted && (
                                      <Badge variant={LEARNING_STATUS_META[lesson.status].badgeVariant}>
                                        {LEARNING_STATUS_META[lesson.status].label}
                                      </Badge>
                                    )}
                                    {linkedLessonSessions > 0 && (
                                      <span className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                                        <Icon icon={Timer02Icon} size={11} />
                                        {linkedLessonSessions} séance
                                        {linkedLessonSessions > 1 ? 's' : ''}
                                      </span>
                                    )}
                                  </div>

                                  {lesson.content && (
                                    <p className="line-clamp-2 text-xs text-zinc-600 dark:text-zinc-400">
                                      {lesson.content}
                                    </p>
                                  )}

                                  {lesson.resourceUrl && (
                                    <a
                                      href={lesson.resourceUrl}
                                      target="_blank"
                                      rel="noreferrer noopener"
                                      className="inline-flex items-center gap-1 text-xs font-medium text-teal-800 hover:underline dark:text-teal-300"
                                    >
                                      Ressource externe
                                      <Icon icon={LinkSquare02Icon} size={12} />
                                    </a>
                                  )}
                                </div>
                              </div>

                              <div className="flex shrink-0 flex-wrap items-center gap-2 pl-7 sm:pl-0">
                                <Button
                                  type="button"
                                  variant={isCompleted ? 'secondary' : 'primary'}
                                  size="sm"
                                  onClick={() => void onToggleLesson(lesson)}
                                >
                                  <Icon icon={CheckmarkCircle02Icon} size={14} />
                                  {isCompleted ? 'Rouvrir' : 'Marquer terminée'}
                                </Button>
                                <InlineConfirm
                                  triggerLabel="Supprimer"
                                  ariaLabel={`Supprimer la leçon ${lesson.title}`}
                                  onConfirm={() => void onDeleteLesson(lesson)}
                                />
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </article>
  );
}
