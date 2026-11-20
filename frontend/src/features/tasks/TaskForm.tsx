import { useEffect, useState, type FormEvent } from 'react';
import { Calendar03Icon } from '@hugeicons/core-free-icons';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { addDays, isoToDateInput, toLocalDateKey } from '../../lib/date';
import { extractFieldErrors } from '../../lib/validation';
import { useLearningStore } from '../../state/LearningStoreContext';
import type { Task, TaskPriority, TaskStatus } from '../../types/domain';
import { taskFormSchema, type TaskFormValues } from './taskSchema';

export interface TaskFormProps {
  initialTask?: Task | null;
  onSubmit: (values: TaskFormValues) => void;
  onCancel: () => void;
}

type TaskFormField = keyof TaskFormValues;

function getInitialValues(task?: Task | null): TaskFormValues {
  return {
    title: task?.title ?? '',
    description: task?.description ?? '',
    priority: task?.priority ?? 'normal',
    status: task?.status ?? 'todo',
    dueDate: isoToDateInput(task?.dueAt ?? null),
    projectId: task?.projectId ?? '',
    moduleId: task?.moduleId ?? '',
  };
}

/**
 * Formulaire de création et d'édition d'une tâche avec validation Zod par champ.
 */
export function TaskForm({ initialTask, onSubmit, onCancel }: TaskFormProps) {
  const { projects, modules, paths } = useLearningStore();
  const [values, setValues] = useState<TaskFormValues>(() => getInitialValues(initialTask));
  const [errors, setErrors] = useState<Partial<Record<TaskFormField, string>>>({});

  useEffect(() => {
    setValues(getInitialValues(initialTask));
    setErrors({});
  }, [initialTask]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = taskFormSchema.safeParse(values);

    if (!parsed.success) {
      setErrors(extractFieldErrors<TaskFormField>(parsed.error));
      return;
    }

    setErrors({});
    onSubmit(parsed.data);
  };

  const today = new Date();
  const duePresets = [
    { label: 'Aujourd’hui', value: toLocalDateKey(today) },
    { label: 'Demain', value: toLocalDateKey(addDays(today, 1)) },
    { label: '+7 jours', value: toLocalDateKey(addDays(today, 7)) },
    { label: 'Aucune', value: '' },
  ];

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <FormField id="task-title" label="Titre" required error={errors.title}>
        <Input
          id="task-title"
          value={values.title}
          hasError={Boolean(errors.title)}
          aria-describedby={errors.title ? 'task-title-error' : undefined}
          placeholder="Ex. Réviser les jointures SQL"
          onChange={(e) => {
            setValues((prev) => ({ ...prev, title: e.target.value }));
            if (errors.title) {
              setErrors((prev) => ({ ...prev, title: undefined }));
            }
          }}
        />
      </FormField>

      <FormField id="task-description" label="Description" error={errors.description}>
        <Textarea
          id="task-description"
          value={values.description ?? ''}
          hasError={Boolean(errors.description)}
          placeholder="Détails, critères de réussite ou ressources utiles (facultatif)"
          onChange={(e) => setValues((prev) => ({ ...prev, description: e.target.value }))}
        />
      </FormField>

      <div className="grid gap-4 sm:grid-cols-3">
        <FormField id="task-priority" label="Priorité" error={errors.priority}>
          <Select
            id="task-priority"
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

        <FormField id="task-status" label="Statut" error={errors.status}>
          <Select
            id="task-status"
            value={values.status}
            onChange={(e) =>
              setValues((prev) => ({ ...prev, status: e.target.value as TaskStatus }))
            }
          >
            <option value="todo">À faire</option>
            <option value="in_progress">En cours</option>
            <option value="done">Terminée</option>
            <option value="parked">Parking</option>
            <option value="cancelled">Annulée</option>
          </Select>
        </FormField>

        <FormField id="task-due-date" label="Échéance" error={errors.dueDate}>
          <Input
            id="task-due-date"
            type="date"
            value={values.dueDate ?? ''}
            hasError={Boolean(errors.dueDate)}
            onChange={(e) => setValues((prev) => ({ ...prev, dueDate: e.target.value }))}
          />
        </FormField>
      </div>

      {/* Raccourcis d'échéance */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-zinc-50 px-3 py-2 dark:bg-zinc-800/70">
        <div className="flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-300">
          <Icon icon={Calendar03Icon} size={14} className="text-zinc-400 dark:text-zinc-500" />
          <span>Raccourcis d’échéance</span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {duePresets.map((preset) => {
            const isActive = (values.dueDate ?? '') === preset.value;
            return (
              <button
                key={preset.label}
                type="button"
                onClick={() => {
                  setValues((prev) => ({ ...prev, dueDate: preset.value }));
                  if (errors.dueDate) {
                    setErrors((prev) => ({ ...prev, dueDate: undefined }));
                  }
                }}
                className={cn(
                  'rounded-full px-2.5 py-1 text-xs font-medium transition-colors',
                  isActive
                    ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                    : 'bg-white text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-700',
                )}
              >
                {preset.label}
              </button>
            );
          })}
        </div>
      </div>

      {(projects.length > 0 || modules.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {projects.length > 0 && (
            <FormField id="task-project" label="Projet associé (facultatif)">
              <Select
                id="task-project"
                value={values.projectId ?? ''}
                onChange={(e) => setValues((prev) => ({ ...prev, projectId: e.target.value }))}
              >
                <option value="">Aucun projet lié</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </Select>
            </FormField>
          )}

          {modules.length > 0 && (
            <FormField id="task-module" label="Module d’apprentissage (facultatif)">
              <Select
                id="task-module"
                value={values.moduleId ?? ''}
                onChange={(e) => setValues((prev) => ({ ...prev, moduleId: e.target.value }))}
              >
                <option value="">Aucun module lié</option>
                {modules.map((mod) => {
                  const pathTitle = paths.find((p) => p.id === mod.pathId)?.title;
                  return (
                    <option key={mod.id} value={mod.id}>
                      {pathTitle ? `${pathTitle} — ${mod.title}` : mod.title}
                    </option>
                  );
                })}
              </Select>
            </FormField>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" variant="primary">
          {initialTask ? 'Enregistrer les modifications' : 'Ajouter la tâche'}
        </Button>
      </div>
    </form>
  );
}
