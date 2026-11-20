import { useEffect, useState, type FormEvent } from 'react';
import { Cancel01Icon } from '@hugeicons/core-free-icons';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { addDays, isoToDateInput, toLocalDateKey } from '../../lib/date';
import { extractFieldErrors } from '../../lib/validation';
import type { Project, ProjectStatus, TaskPriority } from '../../types/domain';
import {
  parseDeliverablesText,
  projectFormSchema,
  type ProjectFormValues,
} from './projectsSchema';

type ProjectField = keyof ProjectFormValues;

export interface ProjectSubmitPayload {
  name: string;
  goal: string;
  description?: string;
  status: ProjectStatus;
  priority: TaskPriority;
  nextAction: string;
  deliverables: string[];
  targetDate?: string;
}

export interface ProjectFormProps {
  editingProject: Project | null;
  initialStatus?: ProjectStatus;
  onSubmit: (payload: ProjectSubmitPayload) => Promise<void> | void;
  onCancel: () => void;
}

const TARGET_DATE_PRESETS: Array<{ label: string; daysOffset: number }> = [
  { label: '+7 j', daysOffset: 7 },
  { label: '+14 j', daysOffset: 14 },
  { label: '+30 j', daysOffset: 30 },
];

function getInitialValues(
  editingProject: Project | null,
  initialStatus: ProjectStatus = 'active',
): ProjectFormValues {
  if (editingProject) {
    return {
      name: editingProject.name,
      goal: editingProject.goal,
      description: editingProject.description ?? '',
      status: editingProject.status,
      priority: editingProject.priority,
      nextAction: editingProject.nextAction,
      deliverablesText: (editingProject.deliverables ?? []).join('\n'),
      targetDate: isoToDateInput(editingProject.targetDate),
    };
  }
  return {
    name: '',
    goal: '',
    description: '',
    status: initialStatus,
    priority: 'normal',
    nextAction: '',
    deliverablesText: '',
    targetDate: '',
  };
}

export function ProjectForm({
  editingProject,
  initialStatus = 'active',
  onSubmit,
  onCancel,
}: ProjectFormProps) {
  const [values, setValues] = useState<ProjectFormValues>(() =>
    getInitialValues(editingProject, initialStatus),
  );
  const [errors, setErrors] = useState<Partial<Record<ProjectField, string>>>({});

  useEffect(() => {
    setValues(getInitialValues(editingProject, initialStatus));
    setErrors({});
  }, [editingProject, initialStatus]);

  const applyTargetDateOffset = (daysOffset: number) => {
    const dateKey = toLocalDateKey(addDays(new Date(), daysOffset));
    setValues((prev) => ({ ...prev, targetDate: dateKey }));
    if (errors.targetDate) {
      setErrors((prev) => ({ ...prev, targetDate: undefined }));
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = projectFormSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(extractFieldErrors<ProjectField>(parsed.error));
      return;
    }
    setErrors({});
    void onSubmit({
      name: parsed.data.name,
      goal: parsed.data.goal,
      description: parsed.data.description,
      status: parsed.data.status,
      priority: parsed.data.priority,
      nextAction: parsed.data.nextAction,
      deliverables: parseDeliverablesText(parsed.data.deliverablesText),
      targetDate: parsed.data.targetDate,
    });
  };

  return (
    <section
      aria-label={editingProject ? 'Modifier le projet' : 'Nouveau projet'}
      className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
    >
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          {editingProject ? 'Modifier le projet' : 'Nouveau projet'}
        </h2>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          <Icon icon={Cancel01Icon} size={15} />
          Fermer
        </Button>
      </div>

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
              <option value="paused">En pause</option>
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
              placeholder="Ex. Livrer les lots 1 et 2 testés"
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

          <div className="space-y-2">
            <FormField
              id="project-target-date"
              label="Date cible (facultatif)"
              error={errors.targetDate}
            >
              <Input
                id="project-target-date"
                type="date"
                value={values.targetDate ?? ''}
                onChange={(e) => setValues((prev) => ({ ...prev, targetDate: e.target.value }))}
              />
            </FormField>
            <div className="flex flex-wrap items-center gap-1.5">
              {TARGET_DATE_PRESETS.map((preset) => {
                const presetDate = toLocalDateKey(addDays(new Date(), preset.daysOffset));
                const isSelected = values.targetDate === presetDate;
                return (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => applyTargetDateOffset(preset.daysOffset)}
                    className={cn(
                      'rounded-lg px-2 py-0.5 text-[11px] font-medium transition-colors',
                      isSelected
                        ? 'bg-teal-700 text-white dark:bg-teal-500 dark:text-zinc-950'
                        : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200/80 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700',
                    )}
                  >
                    {preset.label}
                  </button>
                );
              })}
              {values.targetDate && (
                <button
                  type="button"
                  onClick={() => setValues((prev) => ({ ...prev, targetDate: '' }))}
                  className="rounded-lg bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-500 transition-colors hover:bg-zinc-200/80 dark:bg-zinc-800 dark:text-zinc-400"
                >
                  Effacer
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id="project-description" label="Description (facultatif)">
            <Textarea
              id="project-description"
              rows={3}
              value={values.description ?? ''}
              placeholder="Périmètre et jalons clés"
              onChange={(e) => setValues((prev) => ({ ...prev, description: e.target.value }))}
            />
          </FormField>

          <FormField id="project-deliverables" label="Livrables (un par ligne, facultatif)">
            <Textarea
              id="project-deliverables"
              rows={3}
              value={values.deliverablesText ?? ''}
              placeholder={'API REST FastAPI\nInterface React complète'}
              onChange={(e) =>
                setValues((prev) => ({ ...prev, deliverablesText: e.target.value }))
              }
            />
          </FormField>
        </div>

        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onCancel}>
            Annuler
          </Button>
          <Button type="submit" variant="primary">
            {editingProject ? 'Enregistrer le projet' : 'Créer le projet'}
          </Button>
        </div>
      </form>
    </section>
  );
}
