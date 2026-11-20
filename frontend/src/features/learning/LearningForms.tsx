import { useEffect, useState, type FormEvent } from 'react';
import { Cancel01Icon } from '@hugeicons/core-free-icons';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { extractFieldErrors } from '../../lib/validation';
import type { LearningPath, LearningStatus } from '../../types/domain';
import {
  learningModuleSchema,
  learningPathSchema,
  lessonSchema,
  type LearningModuleFormValues,
  type LearningPathFormValues,
  type LessonFormValues,
} from './learningSchema';

type PathField = keyof LearningPathFormValues;
type ModuleField = keyof LearningModuleFormValues;
type LessonField = keyof LessonFormValues;

export interface PathFormProps {
  editingPath: LearningPath | null;
  onSubmit: (values: LearningPathFormValues) => Promise<void> | void;
  onCancel: () => void;
}

export function PathForm({ editingPath, onSubmit, onCancel }: PathFormProps) {
  const [values, setValues] = useState<LearningPathFormValues>(() =>
    editingPath
      ? {
          title: editingPath.title,
          goal: editingPath.goal,
          description: editingPath.description ?? '',
          status: editingPath.status,
        }
      : {
          title: '',
          goal: '',
          description: '',
          status: 'active',
        },
  );
  const [errors, setErrors] = useState<Partial<Record<PathField, string>>>({});

  useEffect(() => {
    setValues(
      editingPath
        ? {
            title: editingPath.title,
            goal: editingPath.goal,
            description: editingPath.description ?? '',
            status: editingPath.status,
          }
        : {
            title: '',
            goal: '',
            description: '',
            status: 'active',
          },
    );
    setErrors({});
  }, [editingPath]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = learningPathSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(extractFieldErrors<PathField>(parsed.error));
      return;
    }
    setErrors({});
    void onSubmit(parsed.data);
  };

  return (
    <section
      aria-label={editingPath ? 'Modifier le parcours' : 'Nouveau parcours'}
      className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
    >
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          {editingPath ? 'Modifier le parcours' : 'Nouveau parcours'}
        </h2>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          <Icon icon={Cancel01Icon} size={15} />
          Fermer
        </Button>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id="path-title" label="Titre du parcours" required error={errors.title}>
            <Input
              id="path-title"
              value={values.title}
              hasError={Boolean(errors.title)}
              placeholder="Ex. Architecture Backend Python"
              onChange={(e) => {
                setValues((prev) => ({ ...prev, title: e.target.value }));
                if (errors.title) setErrors((prev) => ({ ...prev, title: undefined }));
              }}
            />
          </FormField>

          <FormField id="path-status" label="Statut" error={errors.status}>
            <Select
              id="path-status"
              value={values.status}
              onChange={(e) =>
                setValues((prev) => ({
                  ...prev,
                  status: e.target.value as LearningStatus,
                }))
              }
            >
              <option value="not_started">Non démarré</option>
              <option value="active">Actif</option>
              <option value="paused">En pause</option>
              <option value="completed">Terminé</option>
            </Select>
          </FormField>
        </div>

        <FormField id="path-goal" label="Objectif mesurable" required error={errors.goal}>
          <Input
            id="path-goal"
            value={values.goal}
            hasError={Boolean(errors.goal)}
            placeholder="Ex. Concevoir une API FastAPI testée de bout en bout"
            onChange={(e) => {
              setValues((prev) => ({ ...prev, goal: e.target.value }));
              if (errors.goal) setErrors((prev) => ({ ...prev, goal: undefined }));
            }}
          />
        </FormField>

        <FormField id="path-description" label="Description (facultatif)" error={errors.description}>
          <Textarea
            id="path-description"
            value={values.description ?? ''}
            placeholder="Contexte ou prérequis…"
            onChange={(e) => setValues((prev) => ({ ...prev, description: e.target.value }))}
          />
        </FormField>

        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onCancel}>
            Annuler
          </Button>
          <Button type="submit" variant="primary">
            {editingPath ? 'Enregistrer le parcours' : 'Créer le parcours'}
          </Button>
        </div>
      </form>
    </section>
  );
}

export interface ModuleFormProps {
  pathId: string;
  defaultPosition: number;
  onSubmit: (values: LearningModuleFormValues) => Promise<void> | void;
  onCancel: () => void;
}

export function ModuleForm({ pathId, defaultPosition, onSubmit, onCancel }: ModuleFormProps) {
  const [values, setValues] = useState<LearningModuleFormValues>({
    title: '',
    description: '',
    position: defaultPosition,
    status: 'active',
  });
  const [errors, setErrors] = useState<Partial<Record<ModuleField, string>>>({});

  useEffect(() => {
    setValues({
      title: '',
      description: '',
      position: defaultPosition,
      status: 'active',
    });
    setErrors({});
  }, [pathId, defaultPosition]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = learningModuleSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(extractFieldErrors<ModuleField>(parsed.error));
      return;
    }
    setErrors({});
    void onSubmit(parsed.data);
  };

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="space-y-3 rounded-xl bg-zinc-50 p-4 dark:bg-zinc-800/70"
    >
      <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Nouveau module</p>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="sm:col-span-2">
          <FormField
            id={`module-title-${pathId}`}
            label="Titre du module"
            required
            error={errors.title}
          >
            <Input
              id={`module-title-${pathId}`}
              value={values.title}
              hasError={Boolean(errors.title)}
              placeholder="Ex. Authentification JWT & Permissions"
              onChange={(e) => {
                setValues((prev) => ({ ...prev, title: e.target.value }));
                if (errors.title) setErrors((prev) => ({ ...prev, title: undefined }));
              }}
            />
          </FormField>
        </div>

        <FormField id={`module-pos-${pathId}`} label="Ordre" error={errors.position}>
          <Input
            id={`module-pos-${pathId}`}
            type="number"
            min={0}
            value={values.position}
            onChange={(e) =>
              setValues((prev) => ({
                ...prev,
                position: Number(e.target.value),
              }))
            }
          />
        </FormField>
      </div>

      <FormField
        id={`module-desc-${pathId}`}
        label="Description (facultatif)"
        error={errors.description}
      >
        <Input
          id={`module-desc-${pathId}`}
          value={values.description ?? ''}
          placeholder="Notions abordées"
          onChange={(e) => setValues((prev) => ({ ...prev, description: e.target.value }))}
        />
      </FormField>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" variant="primary" size="sm">
          Enregistrer le module
        </Button>
      </div>
    </form>
  );
}

export interface LessonFormProps {
  moduleId: string;
  defaultPosition: number;
  onSubmit: (values: LessonFormValues) => Promise<void> | void;
  onCancel: () => void;
}

export function LessonForm({ moduleId, defaultPosition, onSubmit, onCancel }: LessonFormProps) {
  const [values, setValues] = useState<LessonFormValues>({
    title: '',
    content: '',
    resourceUrl: '',
    position: defaultPosition,
    status: 'not_started',
  });
  const [errors, setErrors] = useState<Partial<Record<LessonField, string>>>({});

  useEffect(() => {
    setValues({
      title: '',
      content: '',
      resourceUrl: '',
      position: defaultPosition,
      status: 'not_started',
    });
    setErrors({});
  }, [moduleId, defaultPosition]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = lessonSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(extractFieldErrors<LessonField>(parsed.error));
      return;
    }
    setErrors({});
    void onSubmit(parsed.data);
  };

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="mt-3 space-y-3 rounded-xl bg-white p-4 dark:bg-zinc-900"
    >
      <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-50">Nouvelle leçon</p>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="sm:col-span-2">
          <FormField
            id={`lesson-title-${moduleId}`}
            label="Titre de la leçon"
            required
            error={errors.title}
          >
            <Input
              id={`lesson-title-${moduleId}`}
              value={values.title}
              hasError={Boolean(errors.title)}
              placeholder="Ex. Valider les schémas Pydantic"
              onChange={(e) => {
                setValues((prev) => ({ ...prev, title: e.target.value }));
                if (errors.title) setErrors((prev) => ({ ...prev, title: undefined }));
              }}
            />
          </FormField>
        </div>

        <FormField id={`lesson-pos-${moduleId}`} label="Ordre" error={errors.position}>
          <Input
            id={`lesson-pos-${moduleId}`}
            type="number"
            min={0}
            value={values.position}
            onChange={(e) =>
              setValues((prev) => ({
                ...prev,
                position: Number(e.target.value),
              }))
            }
          />
        </FormField>
      </div>

      <FormField
        id={`lesson-url-${moduleId}`}
        label="Ressource (URL http/https facultative)"
        error={errors.resourceUrl}
      >
        <Input
          id={`lesson-url-${moduleId}`}
          type="url"
          value={values.resourceUrl ?? ''}
          hasError={Boolean(errors.resourceUrl)}
          placeholder="https://docs.python.org/3/"
          onChange={(e) => {
            setValues((prev) => ({ ...prev, resourceUrl: e.target.value }));
            if (errors.resourceUrl) setErrors((prev) => ({ ...prev, resourceUrl: undefined }));
          }}
        />
      </FormField>

      <FormField
        id={`lesson-content-${moduleId}`}
        label="Notes / objectifs de la leçon"
        error={errors.content}
      >
        <Textarea
          id={`lesson-content-${moduleId}`}
          value={values.content ?? ''}
          placeholder="Points clés ou exercice associé"
          onChange={(e) => setValues((prev) => ({ ...prev, content: e.target.value }))}
        />
      </FormField>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" variant="primary" size="sm">
          Enregistrer la leçon
        </Button>
      </div>
    </form>
  );
}
