import {
  BookOpen01Icon,
  Calendar03Icon,
  Cancel01Icon,
  CheckmarkCircle02Icon,
  FolderKanbanIcon,
  PauseIcon,
  PencilEdit02Icon,
  PlayIcon,
  Target02Icon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { InlineConfirm } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { formatDateFr, formatDateTimeFr } from '../../lib/date';
import type { Task, TaskPriority, TaskStatus } from '../../types/domain';
import { isActiveTaskStatus, isTaskOverdue, TASK_PRIORITY_META } from './taskUtils';

const PRIORITY_BAR_CLASS: Record<TaskPriority, string> = {
  critical: 'bg-rose-500',
  high: 'bg-amber-500',
  normal: 'bg-teal-600 dark:bg-teal-400',
  low: 'bg-zinc-400',
};

const SECONDARY_ACTION_CLASS =
  'inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100';

export interface TaskCardProps {
  task: Task;
  isPrimary: boolean;
  linkedProjectName?: string;
  linkedModuleTitle?: string;
  compact?: boolean;
  onStatusChange: (task: Task, nextStatus: TaskStatus) => Promise<void>;
  onSetPrimary: (task: Task) => Promise<void>;
  onEdit: (task: Task) => void;
  onDelete: (task: Task) => Promise<void>;
}

export function TaskCard({
  task,
  isPrimary,
  linkedProjectName,
  linkedModuleTitle,
  compact = false,
  onStatusChange,
  onSetPrimary,
  onEdit,
  onDelete,
}: TaskCardProps) {
  const priorityMeta = TASK_PRIORITY_META[task.priority];
  const overdue = isTaskOverdue(task);
  const isActive = isActiveTaskStatus(task.status);
  const isClosed = task.status === 'done' || task.status === 'cancelled';

  return (
    <article
      aria-label={task.title}
      className={cn(
        'flex items-stretch gap-3 rounded-2xl transition-colors',
        compact ? 'p-3.5' : 'p-4',
        isPrimary
          ? 'bg-teal-50/60 dark:bg-teal-950/30'
          : compact
            ? 'bg-zinc-50/90 dark:bg-zinc-800/60'
            : isClosed
              ? 'bg-white/75 dark:bg-zinc-900/70'
              : 'bg-white dark:bg-zinc-900',
      )}
    >
      {/* Barre verticale d'accentuation de priorité */}
      <span
        aria-hidden="true"
        className={cn(
          'w-1 shrink-0 self-stretch rounded-full',
          isClosed ? 'bg-zinc-300 dark:bg-zinc-700' : PRIORITY_BAR_CLASS[task.priority],
        )}
      />

      <div
        className={cn(
          'flex min-w-0 flex-1 flex-col gap-3',
          !compact && 'sm:flex-row sm:items-start sm:justify-between',
        )}
      >
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <h3
              className={cn(
                'text-sm font-semibold leading-snug text-zinc-900 dark:text-zinc-50',
                isClosed && 'line-through text-zinc-400 dark:text-zinc-500',
              )}
            >
              {task.title}
            </h3>
            <Badge variant={priorityMeta.badgeVariant}>{priorityMeta.label}</Badge>
            {overdue && <Badge variant="danger">En retard</Badge>}
            {isPrimary && <Badge variant="primary">Priorité</Badge>}
            {linkedProjectName && (
              <span className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                <Icon icon={FolderKanbanIcon} size={12} />
                {linkedProjectName}
              </span>
            )}
            {linkedModuleTitle && (
              <span className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                <Icon icon={BookOpen01Icon} size={12} />
                {linkedModuleTitle}
              </span>
            )}
          </div>

          {task.description && (
            <p className="line-clamp-2 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
              {task.description}
            </p>
          )}

          {(task.dueAt || task.completedAt) && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
              {task.dueAt && (
                <span
                  className={cn(
                    'inline-flex items-center gap-1',
                    overdue
                      ? 'font-medium text-rose-700 dark:text-rose-400'
                      : 'text-zinc-500 dark:text-zinc-400',
                  )}
                >
                  <Icon icon={Calendar03Icon} size={13} />
                  Échéance : {formatDateFr(task.dueAt)}
                </span>
              )}
              {task.completedAt && (
                <span className="font-medium text-emerald-700 dark:text-emerald-400">
                  Terminée le {formatDateTimeFr(task.completedAt)}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Hiérarchie d'actions apaisée */}
        <div
          className={cn(
            'flex flex-wrap items-center gap-1.5',
            !compact && 'sm:shrink-0 sm:justify-end',
          )}
        >
          {isActive ? (
            <>
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => void onStatusChange(task, 'done')}
              >
                <Icon icon={CheckmarkCircle02Icon} size={14} />
                Terminer
              </Button>
              {task.status === 'todo' && (
                <button
                  type="button"
                  onClick={() => void onStatusChange(task, 'in_progress')}
                  className={SECONDARY_ACTION_CLASS}
                >
                  <Icon icon={PlayIcon} size={13} />
                  Démarrer
                </button>
              )}
              <button
                type="button"
                onClick={() => void onStatusChange(task, 'parked')}
                className={SECONDARY_ACTION_CLASS}
              >
                <Icon icon={PauseIcon} size={13} />
                Parking
              </button>
              {!isPrimary && (
                <button
                  type="button"
                  onClick={() => void onSetPrimary(task)}
                  className={SECONDARY_ACTION_CLASS}
                >
                  <Icon icon={Target02Icon} size={13} />
                  Priorité
                </button>
              )}
              <button
                type="button"
                onClick={() => void onStatusChange(task, 'cancelled')}
                className={SECONDARY_ACTION_CLASS}
              >
                <Icon icon={Cancel01Icon} size={13} />
                Annuler
              </button>
            </>
          ) : (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void onStatusChange(task, 'todo')}
            >
              Réouvrir
            </Button>
          )}

          <button
            type="button"
            onClick={() => onEdit(task)}
            className={SECONDARY_ACTION_CLASS}
          >
            <Icon icon={PencilEdit02Icon} size={13} />
            Modifier
          </button>

          <InlineConfirm
            triggerLabel="Supprimer"
            ariaLabel={`Supprimer ${task.title}`}
            onConfirm={() => onDelete(task)}
          />
        </div>
      </div>
    </article>
  );
}
