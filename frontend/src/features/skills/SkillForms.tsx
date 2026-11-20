import { useEffect, useState, type FormEvent } from 'react';
import { Cancel01Icon, InformationCircleIcon } from '@hugeicons/core-free-icons';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { extractFieldErrors } from '../../lib/validation';
import type { Skill, SkillEvidenceType, SkillLevel } from '../../types/domain';
import {
  evidenceFormSchema,
  SKILL_LEVEL_META,
  skillFormSchema,
  type EvidenceFormValues,
  type SkillFormValues,
} from './skillsSchema';

type SkillField = keyof SkillFormValues;
type EvidenceField = keyof EvidenceFormValues;

export interface SkillSubmitPayload {
  name: string;
  domain: string;
  description?: string;
  targetLevel: SkillLevel | null;
}

export interface SkillFormProps {
  editingSkill: Skill | null;
  existingDomains: string[];
  onSubmit: (payload: SkillSubmitPayload) => Promise<void> | void;
  onCancel: () => void;
}

function getInitialSkillValues(editingSkill: Skill | null): SkillFormValues {
  if (editingSkill) {
    return {
      name: editingSkill.name,
      domain: editingSkill.domain,
      description: editingSkill.description ?? '',
      targetLevel: editingSkill.targetLevel !== null ? String(editingSkill.targetLevel) : '',
    };
  }
  return {
    name: '',
    domain: '',
    description: '',
    targetLevel: '3',
  };
}

export function SkillForm({
  editingSkill,
  existingDomains,
  onSubmit,
  onCancel,
}: SkillFormProps) {
  const [values, setValues] = useState<SkillFormValues>(() => getInitialSkillValues(editingSkill));
  const [errors, setErrors] = useState<Partial<Record<SkillField, string>>>({});

  useEffect(() => {
    setValues(getInitialSkillValues(editingSkill));
    setErrors({});
  }, [editingSkill]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = skillFormSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(extractFieldErrors<SkillField>(parsed.error));
      return;
    }
    setErrors({});
    void onSubmit({
      name: parsed.data.name,
      domain: parsed.data.domain,
      description: parsed.data.description,
      targetLevel:
        parsed.data.targetLevel === ''
          ? null
          : (Number(parsed.data.targetLevel) as SkillLevel),
    });
  };

  return (
    <section
      aria-label={editingSkill ? 'Modifier la compétence' : 'Nouvelle compétence'}
      className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
    >
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          {editingSkill ? 'Modifier la compétence' : 'Nouvelle compétence'}
        </h2>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          <Icon icon={Cancel01Icon} size={15} />
          Fermer
        </Button>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <div className="flex items-start gap-2 rounded-xl bg-teal-50/60 p-3 text-xs text-zinc-700 dark:bg-teal-950/30 dark:text-zinc-300">
          <Icon
            icon={InformationCircleIcon}
            size={16}
            className="mt-0.5 shrink-0 text-teal-700 dark:text-teal-400"
          />
          <span>
            {editingSkill
              ? `Niveau vérifié : ${editingSkill.currentLevel}/5 (évolue par évaluation).`
              : 'Niveau initial : 0/5 (Non évalué).'}
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <FormField id="skill-name" label="Nom de la compétence" required error={errors.name}>
            <Input
              id="skill-name"
              value={values.name}
              hasError={Boolean(errors.name)}
              placeholder="Ex. FastAPI & SQLAlchemy"
              onChange={(e) => {
                setValues((prev) => ({ ...prev, name: e.target.value }));
                if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }));
              }}
            />
          </FormField>

          <div className="space-y-2">
            <FormField id="skill-domain" label="Domaine" required error={errors.domain}>
              <Input
                id="skill-domain"
                value={values.domain}
                hasError={Boolean(errors.domain)}
                placeholder="Ex. Backend, Frontend…"
                onChange={(e) => {
                  setValues((prev) => ({ ...prev, domain: e.target.value }));
                  if (errors.domain) setErrors((prev) => ({ ...prev, domain: undefined }));
                }}
              />
            </FormField>
            {existingDomains.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                {existingDomains.map((domain) => {
                  const isSelected = values.domain.trim().toLowerCase() === domain.toLowerCase();
                  return (
                    <button
                      key={domain}
                      type="button"
                      onClick={() => {
                        setValues((prev) => ({ ...prev, domain }));
                        if (errors.domain) setErrors((prev) => ({ ...prev, domain: undefined }));
                      }}
                      className={cn(
                        'rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors',
                        isSelected
                          ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                          : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700',
                      )}
                    >
                      {domain}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <FormField id="skill-target" label="Niveau cible (facultatif)">
            <Select
              id="skill-target"
              value={values.targetLevel}
              onChange={(e) => setValues((prev) => ({ ...prev, targetLevel: e.target.value }))}
            >
              <option value="">Aucun niveau cible</option>
              {[1, 2, 3, 4, 5].map((lvl) => (
                <option key={lvl} value={String(lvl)}>
                  {SKILL_LEVEL_META[lvl as SkillLevel].label}
                </option>
              ))}
            </Select>
          </FormField>
        </div>

        <FormField id="skill-description" label="Critères ou périmètre (facultatif)">
          <Textarea
            id="skill-description"
            value={values.description ?? ''}
            placeholder="Critères concrets…"
            onChange={(e) => setValues((prev) => ({ ...prev, description: e.target.value }))}
          />
        </FormField>

        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onCancel}>
            Annuler
          </Button>
          <Button type="submit" variant="primary">
            {editingSkill ? 'Enregistrer la compétence' : 'Créer la compétence'}
          </Button>
        </div>
      </form>
    </section>
  );
}

export interface EvidenceFormProps {
  skillId: string;
  onSubmit: (values: EvidenceFormValues) => Promise<void> | void;
  onCancel: () => void;
}

export function EvidenceForm({ skillId, onSubmit, onCancel }: EvidenceFormProps) {
  const [values, setValues] = useState<EvidenceFormValues>({
    type: 'exercise',
    description: '',
    referenceUrl: '',
    result: '',
  });
  const [errors, setErrors] = useState<Partial<Record<EvidenceField, string>>>({});

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = evidenceFormSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(extractFieldErrors<EvidenceField>(parsed.error));
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
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField id={`ev-type-${skillId}`} label="Type de preuve">
          <Select
            id={`ev-type-${skillId}`}
            value={values.type}
            onChange={(e) =>
              setValues((prev) => ({
                ...prev,
                type: e.target.value as SkillEvidenceType,
              }))
            }
          >
            <option value="exercise">Exercice</option>
            <option value="code">Code</option>
            <option value="project">Projet</option>
            <option value="assessment">Évaluation</option>
            <option value="deliverable">Livrable</option>
            <option value="other">Autre</option>
          </Select>
        </FormField>

        <FormField
          id={`ev-result-${skillId}`}
          label="Résultat ou note (facultatif)"
          error={errors.result}
        >
          <Input
            id={`ev-result-${skillId}`}
            value={values.result ?? ''}
            placeholder="Ex. 100 % des tests validés"
            onChange={(e) => setValues((prev) => ({ ...prev, result: e.target.value }))}
          />
        </FormField>
      </div>

      <FormField
        id={`ev-desc-${skillId}`}
        label="Ce qui a été réalisé ou démontré"
        required
        error={errors.description}
      >
        <Textarea
          id={`ev-desc-${skillId}`}
          value={values.description}
          hasError={Boolean(errors.description)}
          placeholder="Ex. Implémentation de l’API CRUD FastAPI"
          onChange={(e) => {
            setValues((prev) => ({ ...prev, description: e.target.value }));
            if (errors.description) {
              setErrors((prev) => ({ ...prev, description: undefined }));
            }
          }}
        />
      </FormField>

      <FormField
        id={`ev-url-${skillId}`}
        label="Lien de référence http/https (facultatif)"
        error={errors.referenceUrl}
      >
        <Input
          id={`ev-url-${skillId}`}
          type="url"
          value={values.referenceUrl ?? ''}
          hasError={Boolean(errors.referenceUrl)}
          placeholder="https://github.com/..."
          onChange={(e) => {
            setValues((prev) => ({ ...prev, referenceUrl: e.target.value }));
            if (errors.referenceUrl) {
              setErrors((prev) => ({ ...prev, referenceUrl: undefined }));
            }
          }}
        />
      </FormField>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" variant="primary" size="sm">
          Enregistrer la preuve
        </Button>
      </div>
    </form>
  );
}
