import {
  Add01Icon,
  Calendar03Icon,
  CheckmarkCircle02Icon,
  Clock01Icon,
  PencilEdit02Icon,
  Target02Icon,
} from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { InlineConfirm, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { formatDateFr } from '../../lib/date';
import type { Project, ProjectStatus, StudySession, Task } from '../../types/domain';
import { formatDuration, getSessionDurationMinutes } from '../sessions/sessionUtils';
import { TASK_PRIORITY_META } from '../tasks/taskUtils';
import { PROJECT_STATUS_META } from './projectsSchema';

export interface ProjectCardProps {
  project: Project;
  isFocusProject: boolean;
  projectTasks: Task[];
  projectSessions: StudySession[];
  compact?: boolean;
  onStatusChange: (project: Project, nextStatus: ProjectStatus) => Promise<void> | void;
  onSetPriority: (project: Project) => Promise<void> | void;
  onEdit: (project: Project) => void;
  onDelete: (project: Project) => Promise<void> | void;
  onConvertNextActionToTask: (project: Project) => Promise<void> | void;
}

export function ProjectCard({
  project,
  isFocusProject,
  projectTasks,
  projectSessions,
  compact = false,
  onStatusChange,
  onSetPriority,
  onEdit,
  onDelete,
  onConvertNextActionToTask,
}: ProjectCardProps) {
  const statusMeta = PROJECT_STATUS_META[project.status];
  const priorityMeta = TASK_PRIORITY_META[project.priority];

  const activeOrDoneTasks = projectTasks.filter((t) => t.status !== 'cancelled');
  const doneTasksCount = activeOrDoneTasks.filter((t) => t.status === 'done').length;
  const totalTasksCount = activeOrDoneTasks.length;
  const tasksProgressPct =
    totalTasksCount > 0 ? Math.round((doneTasksCount / totalTasksCount) * 100) : 0;

  const completedSessions = projectSessions.filter(
    (s) => s.status === 'completed' && s.endedAt !== null,
  );
  const totalStudyMinutes = completedSessions.reduce(
    (sum, s) => sum + getSessionDurationMinutes(s),
    0,
  );

  const normalizedNextAction = project.nextAction.trim().toLowerCase();
  const hasNextActionTask =
    normalizedNextAction.length >= 2 &&
    projectTasks.some(
      (t) =>
        t.status !== 'cancelled' && t.title.trim().toLowerCase() === normalizedNextAction,
    );

  return (
    <article
      aria-label={project.name}
      className={cn(
        'space-y-3.5 rounded-2xl transition-colors',
        compact ? 'p-4' : 'p-5',
        isFocusProject
          ? 'bg-teal-50/55 dark:bg-teal-950/30'
          : project.status === 'blocked'
            ? 'bg-amber-50/40 dark:bg-amber-950/20'
            : 'bg-white dark:bg-zinc-900',
      )}
    >
      {/* En-tête : titre, badges, objectif et contrôles */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <h3 className="line-clamp-1 text-sm font-semibold text-zinc-900 sm:text-base dark:text-zinc-50">
              {project.name}
            </h3>
            <Badge variant={statusMeta.badgeVariant}>{statusMeta.label}</Badge>
            <Badge variant={priorityMeta.badgeVariant}>{priorityMeta.label}</Badge>
            {isFocusProject && <Badge variant="primary">Priorité</Badge>}
          </div>

          <p className="line-clamp-1 text-xs font-medium text-zinc-700 dark:text-zinc-300">
            {project.goal}
          </p>

          {project.description && (
            <p className="line-clamp-2 text-xs text-zinc-500 dark:text-zinc-400">
              {project.description}
            </p>
          )}
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
          <Select
            aria-label={`Statut du projet ${project.name}`}
            value={project.status}
            className="h-8 min-h-8 w-auto py-1 text-xs"
            onChange={(e) => void onStatusChange(project, e.target.value as ProjectStatus)}
          >
            <option value="planned">Planifié</option>
            <option value="active">Actif</option>
            <option value="paused">En pause</option>
            <option value="blocked">Bloqué</option>
            <option value="completed">Terminé</option>
            <option value="archived">Archivé</option>
          </Select>

          {project.status === 'active' && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => void onStatusChange(project, 'paused')}
            >
              Mettre en attente
            </Button>
          )}

          {project.status === 'paused' && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void onStatusChange(project, 'active')}
            >
              Reprendre
            </Button>
          )}

          {!isFocusProject && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void onSetPriority(project)}
            >
              <Icon icon={Target02Icon} size={14} />
              Définir comme priorité
            </Button>
          )}

          <Button type="button" variant="ghost" size="sm" onClick={() => onEdit(project)}>
            <Icon icon={PencilEdit02Icon} size={14} />
            Modifier
          </Button>

          <InlineConfirm
            triggerLabel="Supprimer"
            ariaLabel={`Supprimer le projet ${project.name}`}
            onConfirm={() => void onDelete(project)}
          />
        </div>
      </div>

      {/* Bloc Prochaine action concrète + conversion 1-clic en tâche */}
      <div className="flex flex-col gap-2.5 rounded-xl bg-zinc-50/90 p-3 sm:flex-row sm:items-center sm:justify-between dark:bg-zinc-800/60">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Prochaine action
          </p>
          <p className="mt-0.5 line-clamp-2 text-sm font-medium text-zinc-900 dark:text-zinc-100">
            {project.nextAction || 'Aucune prochaine action définie'}
          </p>
        </div>

        {project.nextAction.trim().length >= 2 && (
          <div className="shrink-0">
            {hasNextActionTask ? (
              <span className="inline-flex items-center gap-1 rounded-lg bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                <Icon icon={CheckmarkCircle02Icon} size={13} />
                Tâche liée
              </span>
            ) : (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                aria-label={`Convertir la prochaine action de ${project.name} en tâche`}
                onClick={() => void onConvertNextActionToTask(project)}
              >
                <Icon icon={Add01Icon} size={13} />
                Convertir en tâche
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Livrables */}
      {project.deliverables && project.deliverables.length > 0 && (
        <ul aria-label={`Livrables de ${project.name}`} className="flex flex-wrap gap-1.5">
          {project.deliverables.map((item, idx) => (
            <li key={`${project.id}-deliv-${idx}`}>
              <Badge variant="neutral">{item}</Badge>
            </li>
          ))}
        </ul>
      )}

      {/* Barre de progression des tâches liées (si le projet possède des tâches) */}
      {totalTasksCount > 0 && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
            <span>Avancement des tâches</span>
            <span className="font-medium tabular-nums text-zinc-700 dark:text-zinc-300">
              {doneTasksCount}/{totalTasksCount} ({tasksProgressPct}%)
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
            <div
              className="h-full rounded-full bg-teal-600 transition-all dark:bg-teal-400"
              style={{ width: `${tasksProgressPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Pied de carte : date cible, tâches et séances liées */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-zinc-500 dark:text-zinc-400">
        {project.targetDate && (
          <span className="inline-flex items-center gap-1">
            <Icon icon={Calendar03Icon} size={13} />
            Cible : {formatDateFr(project.targetDate)}
          </span>
        )}
        <span>
          Tâches :{' '}
          <Link
            to="/tasks"
            className="font-medium text-teal-800 hover:underline dark:text-teal-300"
          >
            {projectTasks.length}
          </Link>
        </span>
        <span>
          Séances :{' '}
          <Link
            to="/sessions"
            className="font-medium text-teal-800 hover:underline dark:text-teal-300"
          >
            {projectSessions.length}
          </Link>
        </span>
        {totalStudyMinutes > 0 && (
          <span className="inline-flex items-center gap-1 text-zinc-600 dark:text-zinc-300">
            <Icon icon={Clock01Icon} size={13} />
            {formatDuration(totalStudyMinutes)}
          </span>
        )}
      </div>
    </article>
  );
}
