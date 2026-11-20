import { useMemo, useState, type FormEvent } from 'react';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
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
    <div className="grid gap-4 sm:grid-cols-2">
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
    <Card>
      <CardHeader>
        <CardTitle>Démarrer une séance</CardTitle>
      </CardHeader>
      <CardContent>
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
              onChange={(e) => setValues((prev) => ({ ...prev, taskId: e.target.value }))}
            >
              <option value="">Aucune tâche liée</option>
              {activeTasks.map((task) => (
                <option key={task.id} value={task.id}>
                  {task.title}
                </option>
              ))}
            </Select>
          </FormField>

          <SessionLearningLinks
            prefix="start-session"
            projectId={values.projectId ?? ''}
            moduleId={values.moduleId ?? ''}
            lessonId={values.lessonId ?? ''}
            skillId={values.skillId ?? ''}
            onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))}
          />

          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="secondary" onClick={onCancel}>
              Annuler
            </Button>
            <Button type="submit" variant="primary">
              Lancer la séance
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
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
    <Card>
      <CardHeader>
        <CardTitle>Enregistrer une séance passée</CardTitle>
      </CardHeader>
      <CardContent>
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

          <p className="text-xs font-medium text-teal-800 dark:text-teal-300">
            {previewDuration !== null
              ? `Durée calculée : ${formatDuration(previewDuration)}`
              : 'La date de fin doit être postérieure au début pour calculer la durée.'}
          </p>

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

          <SessionLearningLinks
            prefix="manual-session"
            projectId={values.projectId ?? ''}
            moduleId={values.moduleId ?? ''}
            lessonId={values.lessonId ?? ''}
            skillId={values.skillId ?? ''}
            onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))}
          />

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
            <Button variant="secondary" onClick={onCancel}>
              Annuler
            </Button>
            <Button type="submit" variant="primary">
              Enregistrer la séance
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
