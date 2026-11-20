import { useMemo, useState, type FormEvent } from 'react';
import { Cancel01Icon, Clock01Icon } from '@hugeicons/core-free-icons';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { toDateTimeLocalValue } from '../../lib/date';
import { extractFieldErrors } from '../../lib/validation';
import { useLearningStore } from '../../state/LearningStoreContext';
import type { Task } from '../../types/domain';
import {
  manualSessionSchema,
  SESSION_CATEGORIES,
  startSessionSchema,
  type ManualSessionValues,
  type StartSessionValues,
} from './sessionSchema';
import { formatDuration } from './sessionUtils';

const MANUAL_DURATION_PRESETS = [
  { minutes: 30, label: '30 min' },
  { minutes: 45, label: '45 min' },
  { minutes: 60, label: '1 h' },
  { minutes: 90, label: '1 h 30' },
  { minutes: 120, label: '2 h' },
];

export interface StartSessionFormProps {
  activeTasks: Task[];
  onSubmit: (values: StartSessionValues) => void;
  onCancel: () => void;
}

type StartField = keyof StartSessionValues;

interface SessionLearningLinksProps {
  prefix: string;
  projectId: string;
  moduleId: string;
  lessonId: string;
  skillId: string;
  onChange: (patch: {
    projectId?: string;
    moduleId?: string;
    lessonId?: string;
    skillId?: string;
  }) => void;
}

function SessionLearningLinks({
  prefix,
  projectId,
  moduleId,
  lessonId,
  skillId,
  onChange,
}: SessionLearningLinksProps) {
  const { projects, modules, lessons, skills } = useLearningStore();
  if (projects.length === 0 && modules.length === 0 && skills.length === 0) {
    return null;
  }

  const visibleLessons = moduleId ? lessons.filter((l) => l.moduleId === moduleId) : lessons;

  return (
    <div className="grid gap-4 rounded-xl bg-zinc-50 p-3.5 sm:grid-cols-2 dark:bg-zinc-800/60">
      {projects.length > 0 && (
        <FormField id={`${prefix}-project`} label="Projet associé (facultatif)">
          <Select
            id={`${prefix}-project`}
            value={projectId}
            onChange={(e) => onChange({ projectId: e.target.value })}
          >
            <option value="">Aucun projet lié</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
        </FormField>
      )}

      {modules.length > 0 && (
        <FormField id={`${prefix}-module`} label="Module d’apprentissage (facultatif)">
          <Select
            id={`${prefix}-module`}
            value={moduleId}
            onChange={(e) => onChange({ moduleId: e.target.value, lessonId: '' })}
          >
            <option value="">Aucun module lié</option>
            {modules.map((m) => (
              <option key={m.id} value={m.id}>
                {m.title}
              </option>
            ))}
          </Select>
        </FormField>
      )}

      {visibleLessons.length > 0 && (
        <FormField id={`${prefix}-lesson`} label="Leçon associée (facultatif)">
          <Select
            id={`${prefix}-lesson`}
            value={lessonId}
            onChange={(e) => onChange({ lessonId: e.target.value })}
          >
            <option value="">Aucune leçon liée</option>
            {visibleLessons.map((l) => (
              <option key={l.id} value={l.id}>
                {l.title}
              </option>
            ))}
          </Select>
        </FormField>
      )}

      {skills.length > 0 && (
        <FormField id={`${prefix}-skill`} label="Compétence travaillée (facultatif)">
          <Select
            id={`${prefix}-skill`}
            value={skillId}
            onChange={(e) => onChange({ skillId: e.target.value })}
          >
            <option value="">Aucune compétence liée</option>
            {skills.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.domain})
              </option>
            ))}
          </Select>
        </FormField>
      )}
    </div>
  );
}

export function StartSessionForm({ activeTasks, onSubmit, onCancel }: StartSessionFormProps) {
  const { projects, modules, skills } = useLearningStore();
  const hasLearningLinks = projects.length > 0 || modules.length > 0 || skills.length > 0;

  const [values, setValues] = useState<StartSessionValues>({
    title: '',
    category: SESSION_CATEGORIES[1],
    taskId: '',
    projectId: '',
    moduleId: '',
    lessonId: '',
    skillId: '',
  });
  const [errors, setErrors] = useState<Partial<Record<StartField, string>>>({});
  const [showLinks, setShowLinks] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = startSessionSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(extractFieldErrors<StartField>(parsed.error));
      return;
    }
    setErrors({});
    onSubmit(parsed.data);
  };

  return (
    <section
      aria-label="Démarrer une séance"
      className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
    >
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          Démarrer une séance
        </h2>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          <Icon icon={Cancel01Icon} size={15} />
          Fermer
        </Button>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id="start-session-title" label="Titre de la séance" required error={errors.title}>
            <Input
              id="start-session-title"
              value={values.title}
              hasError={Boolean(errors.title)}
              placeholder="Ex. Exercices FastAPI et schémas Pydantic"
              onChange={(e) => {
                setValues((prev) => ({ ...prev, title: e.target.value }));
                if (errors.title) {
                  setErrors((prev) => ({ ...prev, title: undefined }));
                }
              }}
            />
          </FormField>

          <FormField id="start-session-category" label="Catégorie" error={errors.category}>
            <Select
              id="start-session-category"
              value={values.category}
              onChange={(e) => setValues((prev) => ({ ...prev, category: e.target.value }))}
            >
              {SESSION_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </Select>
          </FormField>
        </div>

        <FormField id="start-session-task" label="Tâche associée (facultatif)">
          <Select
            id="start-session-task"
            value={values.taskId ?? ''}
            onChange={(e) => {
              const selectedTaskId = e.target.value;
              const selectedTask = activeTasks.find((t) => t.id === selectedTaskId);
              setValues((prev) => ({
                ...prev,
                taskId: selectedTaskId,
                title:
                  prev.title.trim() === '' && selectedTask
                    ? selectedTask.title
                    : prev.title,
              }));
              if (selectedTask && errors.title) {
                setErrors((prev) => ({ ...prev, title: undefined }));
              }
            }}
          >
            <option value="">Aucune tâche liée</option>
            {activeTasks.map((task) => (
              <option key={task.id} value={task.id}>
                {task.title}
              </option>
            ))}
          </Select>
        </FormField>

        {hasLearningLinks && (
          <div className="space-y-3">
            <button
              type="button"
              aria-expanded={showLinks}
              onClick={() => setShowLinks((prev) => !prev)}
              className="text-xs font-medium text-teal-700 hover:text-teal-800 dark:text-teal-400 dark:hover:text-teal-300"
            >
              {showLinks
                ? 'Masquer les liens projet / module / compétence'
                : 'Lier à un projet, module ou compétence'}
            </button>

            {showLinks && (
              <SessionLearningLinks
                prefix="start-session"
                projectId={values.projectId ?? ''}
                moduleId={values.moduleId ?? ''}
                lessonId={values.lessonId ?? ''}
                skillId={values.skillId ?? ''}
                onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))}
              />
            )}
          </div>
        )}

        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onCancel}>
            Annuler
          </Button>
          <Button type="submit" variant="primary">
            Lancer la séance
          </Button>
        </div>
      </form>
    </section>
  );
}

export interface ManualSessionFormProps {
  tasks: Task[];
  onSubmit: (values: ManualSessionValues) => void;
  onCancel: () => void;
}

type ManualField = keyof ManualSessionValues;

function getDefaultManualRange(): { startedAt: string; endedAt: string } {
  const now = new Date();
  const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
  return {
    startedAt: toDateTimeLocalValue(oneHourAgo),
    endedAt: toDateTimeLocalValue(now),
  };
}

export function ManualSessionForm({ tasks, onSubmit, onCancel }: ManualSessionFormProps) {
  const { projects, modules, skills } = useLearningStore();
  const hasLearningLinks = projects.length > 0 || modules.length > 0 || skills.length > 0;

  const defaults = useMemo(() => getDefaultManualRange(), []);
  const [values, setValues] = useState<ManualSessionValues>({
    title: '',
    category: SESSION_CATEGORIES[1],
    startedAt: defaults.startedAt,
    endedAt: defaults.endedAt,
    result: '',
    taskId: '',
    projectId: '',
    moduleId: '',
    lessonId: '',
    skillId: '',
  });
  const [errors, setErrors] = useState<Partial<Record<ManualField, string>>>({});
  const [showLinks, setShowLinks] = useState(false);

  const previewDuration = useMemo(() => {
    const startMs = new Date(values.startedAt).getTime();
    const endMs = new Date(values.endedAt).getTime();
    if (Number.isNaN(startMs) || Number.isNaN(endMs) || endMs <= startMs) {
      return null;
    }
    return Math.round((endMs - startMs) / 60_000);
  }, [values.startedAt, values.endedAt]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = manualSessionSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(extractFieldErrors<ManualField>(parsed.error));
      return;
    }
    setErrors({});
    onSubmit(parsed.data);
  };

  return (
    <section
      aria-label="Enregistrer une séance passée"
      className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
    >
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          Enregistrer une séance passée
        </h2>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          <Icon icon={Cancel01Icon} size={15} />
          Fermer
        </Button>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id="manual-session-title" label="Titre de la séance" required error={errors.title}>
            <Input
              id="manual-session-title"
              value={values.title}
              hasError={Boolean(errors.title)}
              placeholder="Ex. TD Algèbre linéaire"
              onChange={(e) => {
                setValues((prev) => ({ ...prev, title: e.target.value }));
                if (errors.title) {
                  setErrors((prev) => ({ ...prev, title: undefined }));
                }
              }}
            />
          </FormField>

          <FormField id="manual-session-category" label="Catégorie" error={errors.category}>
            <Select
              id="manual-session-category"
              value={values.category}
              onChange={(e) => setValues((prev) => ({ ...prev, category: e.target.value }))}
            >
              {SESSION_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </Select>
          </FormField>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id="manual-session-start" label="Début" required error={errors.startedAt}>
            <Input
              id="manual-session-start"
              type="datetime-local"
              value={values.startedAt}
              hasError={Boolean(errors.startedAt)}
              onChange={(e) => setValues((prev) => ({ ...prev, startedAt: e.target.value }))}
            />
          </FormField>

          <FormField id="manual-session-end" label="Fin" required error={errors.endedAt}>
            <Input
              id="manual-session-end"
              type="datetime-local"
              value={values.endedAt}
              hasError={Boolean(errors.endedAt)}
              onChange={(e) => {
                setValues((prev) => ({ ...prev, endedAt: e.target.value }));
                if (errors.endedAt) {
                  setErrors((prev) => ({ ...prev, endedAt: undefined }));
                }
              }}
            />
          </FormField>
        </div>

        {/* Raccourcis de durée & aperçu */}
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-zinc-50 px-3 py-2 dark:bg-zinc-800/70">
          <div className="flex items-center gap-1.5 text-xs font-medium text-teal-800 dark:text-teal-300">
            <Icon icon={Clock01Icon} size={14} />
            <span>
              {previewDuration !== null
                ? `Durée calculée : ${formatDuration(previewDuration)}`
                : 'La date de fin doit être postérieure au début pour calculer la durée.'}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {MANUAL_DURATION_PRESETS.map((preset) => {
              const isActive = previewDuration === preset.minutes;
              return (
                <button
                  key={preset.minutes}
                  type="button"
                  onClick={() => {
                    const startMs = new Date(values.startedAt).getTime();
                    if (Number.isNaN(startMs)) return;
                    const nextEndedAt = toDateTimeLocalValue(
                      new Date(startMs + preset.minutes * 60_000),
                    );
                    setValues((prev) => ({ ...prev, endedAt: nextEndedAt }));
                    if (errors.endedAt) {
                      setErrors((prev) => ({ ...prev, endedAt: undefined }));
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

        <FormField id="manual-session-task" label="Tâche associée (facultatif)">
          <Select
            id="manual-session-task"
            value={values.taskId ?? ''}
            onChange={(e) => setValues((prev) => ({ ...prev, taskId: e.target.value }))}
          >
            <option value="">Aucune tâche liée</option>
            {tasks.map((task) => (
              <option key={task.id} value={task.id}>
                {task.title}
              </option>
            ))}
          </Select>
        </FormField>

        {hasLearningLinks && (
          <div className="space-y-3">
            <button
              type="button"
              aria-expanded={showLinks}
              onClick={() => setShowLinks((prev) => !prev)}
              className="text-xs font-medium text-teal-700 hover:text-teal-800 dark:text-teal-400 dark:hover:text-teal-300"
            >
              {showLinks
                ? 'Masquer les liens projet / module / compétence'
                : 'Lier à un projet, module ou compétence'}
            </button>

            {showLinks && (
              <SessionLearningLinks
                prefix="manual-session"
                projectId={values.projectId ?? ''}
                moduleId={values.moduleId ?? ''}
                lessonId={values.lessonId ?? ''}
                skillId={values.skillId ?? ''}
                onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))}
              />
            )}
          </div>
        )}

        <FormField
          id="manual-session-result"
          label="Résultat ou note de fin"
          required
          error={errors.result}
        >
          <Textarea
            id="manual-session-result"
            value={values.result}
            hasError={Boolean(errors.result)}
            placeholder="Décrivez ce qui a été produit, résolu ou appris."
            onChange={(e) => {
              setValues((prev) => ({ ...prev, result: e.target.value }));
              if (errors.result) {
                setErrors((prev) => ({ ...prev, result: undefined }));
              }
            }}
          />
        </FormField>

        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onCancel}>
            Annuler
          </Button>
          <Button type="submit" variant="primary">
            Enregistrer la séance
          </Button>
        </div>
      </form>
    </section>
  );
}
