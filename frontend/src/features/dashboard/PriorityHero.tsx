import { useState, type FormEvent } from 'react';
import {
  CheckmarkCircle02Icon,
  PencilEdit02Icon,
  PlayIcon,
  Target02Icon,
} from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button, buttonClasses } from '../../components/ui/Button';
import { FormField, Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState } from '../../components/ui/StateFeedback';
import { formatDateFr } from '../../lib/date';
import type { Project, Task } from '../../types/domain';
import { isActiveTaskStatus, TASK_STATUS_META } from '../tasks/taskUtils';

export interface PriorityHeroProps {
  activePriorityTitle: string | null;
  activePriorityTaskId: string | null;
  activePriorityProjectId: string | null;
  activeTasks: Task[];
  activeProjects: Project[];
  linkedPriorityTask: Task | null;
  linkedPriorityProject: Project | null;
  hasInProgressSession: boolean;
  onSavePriority: (
    title: string | null,
    taskId?: string | null,
    projectId?: string | null,
  ) => Promise<boolean>;
  onCompleteLinkedTask: (task: Task) => Promise<void>;
  onStartFocusSession: () => Promise<void>;
  onFeedback: (message: string) => void;
}

export function PriorityHero({
  activePriorityTitle,
  activePriorityTaskId,
  activePriorityProjectId,
  activeTasks,
  activeProjects,
  linkedPriorityTask,
  linkedPriorityProject,
  hasInProgressSession,
  onSavePriority,
  onCompleteLinkedTask,
  onStartFocusSession,
  onFeedback,
}: PriorityHeroProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [priorityDraftTitle, setPriorityDraftTitle] = useState('');
  const [priorityDraftTaskId, setPriorityDraftTaskId] = useState('');
  const [priorityDraftProjectId, setPriorityDraftProjectId] = useState('');
  const [priorityError, setPriorityError] = useState<string | undefined>(undefined);
  const [isStartingSession, setIsStartingSession] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const openEditor = () => {
    setPriorityDraftTitle(activePriorityTitle ?? '');
    setPriorityDraftTaskId(activePriorityTaskId ?? '');
    setPriorityDraftProjectId(activePriorityProjectId ?? '');
    setPriorityError(undefined);
    setIsEditing(true);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = priorityDraftTitle.trim();
    if (trimmed.length < 2) {
      setPriorityError('Saisissez un intitulé d’au moins 2 caractères.');
      return;
    }

    setIsSaving(true);
    try {
      if (
        await onSavePriority(
          trimmed,
          priorityDraftTaskId || null,
          priorityDraftProjectId || null,
        )
      ) {
        setIsEditing(false);
        setPriorityError(undefined);
        onFeedback('Priorité principale mise à jour.');
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleStartFocus = async () => {
    if (isStartingSession) return;
    setIsStartingSession(true);
    try {
      await onStartFocusSession();
    } finally {
      setIsStartingSession(false);
    }
  };

  return (
    <section
      aria-labelledby="dashboard-priority-heading"
      className="rounded-2xl bg-white p-5 sm:p-6 dark:bg-zinc-900"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-teal-700 text-white dark:bg-teal-600">
            <Icon icon={Target02Icon} size={17} />
          </div>
          <div>
            <h2
              id="dashboard-priority-heading"
              className="text-sm font-semibold text-zinc-900 dark:text-zinc-100"
            >
              Priorité principale
            </h2>
          </div>
        </div>

        {activePriorityTitle && !isEditing && (
          <Button type="button" variant="secondary" size="sm" onClick={openEditor}>
            <Icon icon={PencilEdit02Icon} size={14} />
            Modifier
          </Button>
        )}
      </div>

      {isEditing ? (
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {activeTasks.length > 0 && (
            <FormField id="priority-task-select" label="Lier à une tâche active">
              <Select
                id="priority-task-select"
                value={priorityDraftTaskId}
                onChange={(e) => {
                  const selectedId = e.target.value;
                  setPriorityDraftTaskId(selectedId);
                  if (selectedId) {
                    setPriorityDraftProjectId('');
                  }
                  const found = activeTasks.find((t) => t.id === selectedId);
                  if (found) {
                    setPriorityDraftTitle(found.title);
                    setPriorityError(undefined);
                  }
                }}
              >
                <option value="">Saisie libre</option>
                {activeTasks.map((task) => (
                  <option key={task.id} value={task.id}>
                    {task.title}
                  </option>
                ))}
              </Select>
            </FormField>
          )}

          {activeProjects.length > 0 && (
            <FormField id="priority-project-select" label="Lier à un projet actif">
              <Select
                id="priority-project-select"
                value={priorityDraftProjectId}
                onChange={(e) => {
                  const selectedId = e.target.value;
                  setPriorityDraftProjectId(selectedId);
                  if (selectedId) {
                    setPriorityDraftTaskId('');
                  }
                  const found = activeProjects.find((p) => p.id === selectedId);
                  if (found) {
                    setPriorityDraftTitle(found.name);
                    setPriorityError(undefined);
                  }
                }}
              >
                <option value="">Aucun projet lié</option>
                {activeProjects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </Select>
            </FormField>
          )}

          <FormField
            id="priority-title-input"
            label="Intitulé de la priorité principale"
            required
            error={priorityError}
          >
            <Input
              id="priority-title-input"
              value={priorityDraftTitle}
              hasError={Boolean(priorityError)}
              placeholder="Ex. Terminer la fiche d’exercices Python"
              onChange={(e) => {
                setPriorityDraftTitle(e.target.value);
                if (priorityError) {
                  setPriorityError(undefined);
                }
              }}
            />
          </FormField>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              {activePriorityTitle && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={isSaving}
                  onClick={async () => {
                    if (await onSavePriority(null, null, null)) {
                      setIsEditing(false);
                      onFeedback('Priorité effacée.');
                    }
                  }}
                >
                  Effacer
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={isSaving}
                onClick={() => setIsEditing(false)}
              >
                Annuler
              </Button>
              <Button type="submit" variant="primary" size="sm" isLoading={isSaving}>
                Enregistrer la priorité
              </Button>
            </div>
          </div>
        </form>
      ) : activePriorityTitle ? (
        <div className="rounded-2xl bg-teal-50/70 p-4 sm:p-5 dark:bg-teal-950/35">
          <div className="space-y-2">
            <p className="line-clamp-2 text-lg font-semibold tracking-tight text-zinc-900 sm:text-xl dark:text-zinc-50">
              {activePriorityTitle}
            </p>

            {linkedPriorityTask && (
              <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400">
                <Badge variant={TASK_STATUS_META[linkedPriorityTask.status].badgeVariant}>
                  {TASK_STATUS_META[linkedPriorityTask.status].label}
                </Badge>
                {linkedPriorityTask.dueAt && (
                  <span>Échéance : {formatDateFr(linkedPriorityTask.dueAt)}</span>
                )}
              </div>
            )}

            {linkedPriorityProject && (
              <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400">
                <Badge variant="primary">{linkedPriorityProject.name}</Badge>
                {linkedPriorityProject.nextAction && (
                  <span>{linkedPriorityProject.nextAction}</span>
                )}
              </div>
            )}
          </div>

          {(Boolean(linkedPriorityTask && isActiveTaskStatus(linkedPriorityTask.status)) ||
            !hasInProgressSession ||
            Boolean(linkedPriorityProject)) && (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              {linkedPriorityTask && isActiveTaskStatus(linkedPriorityTask.status) && (
                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  onClick={() => void onCompleteLinkedTask(linkedPriorityTask)}
                >
                  <Icon icon={CheckmarkCircle02Icon} size={15} />
                  Terminer cette tâche
                </Button>
              )}

              {!hasInProgressSession && (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  isLoading={isStartingSession}
                  onClick={() => void handleStartFocus()}
                >
                  <Icon icon={PlayIcon} size={15} />
                  Lancer une séance
                </Button>
              )}

              {linkedPriorityProject && (
                <Link to="/projects" className={buttonClasses('secondary', 'sm')}>
                  Projet
                </Link>
              )}
            </div>
          )}
        </div>
      ) : (
        <EmptyState
          icon={<Icon icon={Target02Icon} size={17} className="text-teal-700 dark:text-teal-400" />}
          title="Aucune priorité principale active"
          action={
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Button type="button" variant="primary" size="sm" onClick={openEditor}>
                Définir une priorité
              </Button>
              <Link to="/tasks" className={buttonClasses('secondary', 'sm')}>
                Tâches
              </Link>
            </div>
          }
        />
      )}
    </section>
  );
}
