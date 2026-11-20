import { useEffect, useState, type FormEvent } from 'react';
import { Cancel01Icon } from '@hugeicons/core-free-icons';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { dateInputToDueIso, isoToDateInput } from '../../lib/date';
import type { PersonalGoalCreateInput } from '../../lib/objectivesApi';
import type {
  ObjectiveCategory,
  ObjectiveStatus,
  PersonalGoal,
  TaskPriority,
} from '../../types/domain';

export interface PersonalGoalFormProps {
  editingGoal: PersonalGoal | null;
  onSubmit: (payload: PersonalGoalCreateInput) => Promise<void> | void;
  onCancel: () => void;
}

const CATEGORY_OPTIONS: Array<{ value: ObjectiveCategory; label: string }> = [
  { value: 'learning_goal', label: 'Apprentissage personnel' },
  { value: 'language', label: 'Langage informatique (Python, TypeScript...)' },
  { value: 'framework', label: 'Framework ou bibliothèque (React, FastAPI...)' },
  { value: 'technology', label: 'Technologie / architecture' },
  { value: 'spoken_language', label: 'Langue vivante' },
  { value: 'skill', label: 'Compétence transversale' },
];

export function PersonalGoalForm({ editingGoal, onSubmit, onCancel }: PersonalGoalFormProps) {
  const [title, setTitle] = useState(editingGoal?.title ?? '');
  const [category, setCategory] = useState<ObjectiveCategory>(
    editingGoal?.category ?? 'learning_goal',
  );
  const [goalText, setGoalText] = useState(editingGoal?.goal ?? '');
  const [priority, setPriority] = useState<TaskPriority>(editingGoal?.priority ?? 'normal');
  const [isPrimary, setIsPrimary] = useState<boolean>(editingGoal?.isPrimary ?? false);
  const [weeklyTargetMinutes, setWeeklyTargetMinutes] = useState<string>(
    String(editingGoal?.weeklyTargetMinutes ?? 120),
  );
  const [currentLevel, setCurrentLevel] = useState<string>(
    editingGoal?.currentLevel !== null && editingGoal?.currentLevel !== undefined
      ? String(editingGoal.currentLevel)
      : '',
  );
  const [targetLevel, setTargetLevel] = useState<string>(
    editingGoal?.targetLevel !== null && editingGoal?.targetLevel !== undefined
      ? String(editingGoal.targetLevel)
      : '',
  );
  const [targetDate, setTargetDate] = useState<string>(
    isoToDateInput(editingGoal?.targetDate ?? null),
  );
  const [motivation, setMotivation] = useState(editingGoal?.motivation ?? '');
  const [nextAction, setNextAction] = useState(editingGoal?.nextAction ?? '');
  const [deliverablesText, setDeliverablesText] = useState(
    (editingGoal?.deliverables ?? []).join('\n'),
  );
  const [criteriaText, setCriteriaText] = useState(
    (editingGoal?.successCriteria ?? []).join('\n'),
  );
  const [status, setStatus] = useState<ObjectiveStatus>(editingGoal?.status ?? 'active');
  const [titleError, setTitleError] = useState<string | undefined>(undefined);

  useEffect(() => {
    setTitle(editingGoal?.title ?? '');
    setCategory(editingGoal?.category ?? 'learning_goal');
    setGoalText(editingGoal?.goal ?? '');
    setPriority(editingGoal?.priority ?? 'normal');
    setIsPrimary(editingGoal?.isPrimary ?? false);
    setWeeklyTargetMinutes(String(editingGoal?.weeklyTargetMinutes ?? 120));
    setCurrentLevel(
      editingGoal?.currentLevel !== null && editingGoal?.currentLevel !== undefined
        ? String(editingGoal.currentLevel)
        : '',
    );
    setTargetLevel(
      editingGoal?.targetLevel !== null && editingGoal?.targetLevel !== undefined
        ? String(editingGoal.targetLevel)
        : '',
    );
    setTargetDate(isoToDateInput(editingGoal?.targetDate ?? null));
    setMotivation(editingGoal?.motivation ?? '');
    setNextAction(editingGoal?.nextAction ?? '');
    setDeliverablesText((editingGoal?.deliverables ?? []).join('\n'));
    setCriteriaText((editingGoal?.successCriteria ?? []).join('\n'));
    setStatus(editingGoal?.status ?? 'active');
    setTitleError(undefined);
  }, [editingGoal]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleanedTitle = title.trim();
    if (cleanedTitle.length < 2) {
      setTitleError('Le titre de l’objectif doit contenir au moins 2 caractères.');
      return;
    }
    setTitleError(undefined);

    const parsedMinutes = Number(weeklyTargetMinutes);
    const weeklyMinutes =
      Number.isFinite(parsedMinutes) && parsedMinutes >= 0
        ? Math.min(2400, Math.round(parsedMinutes))
        : 120;

    const parsedCurrent =
      currentLevel.trim() === '' ? null : Math.max(0, Math.min(5, Number(currentLevel)));
    const parsedTarget =
      targetLevel.trim() === '' ? null : Math.max(1, Math.min(5, Number(targetLevel)));

    const deliverables = deliverablesText
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);
    const successCriteria = criteriaText
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);

    void onSubmit({
      title: cleanedTitle,
      category,
      goal: goalText.trim() || null,
      priority,
      isPrimary,
      weeklyTargetMinutes: weeklyMinutes,
      currentLevel: Number.isNaN(parsedCurrent as number) ? null : parsedCurrent,
      targetLevel: Number.isNaN(parsedTarget as number) ? null : parsedTarget,
      targetDate: targetDate ? dateInputToDueIso(targetDate) : null,
      motivation: motivation.trim() || null,
      nextAction: nextAction.trim(),
      deliverables,
      successCriteria,
      status,
      createLinkedEntities: true,
    });
  };

  return (
    <section
      aria-label={editingGoal ? 'Modifier l’objectif personnel' : 'Nouvel objectif personnel'}
      className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-zinc-200/70 dark:bg-zinc-900 dark:ring-zinc-800"
    >
      <div className="mb-4 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
            {editingGoal ? 'Modifier l’objectif personnel' : 'Nouvel objectif personnel'}
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            Configuration guidée progressive : seul le titre est obligatoire au départ.
          </p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          <Icon icon={Cancel01Icon} size={15} />
          Fermer
        </Button>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <FormField id="goal-title-input" label="Titre de l’objectif" required error={titleError}>
            <Input
              id="goal-title-input"
              value={title}
              hasError={Boolean(titleError)}
              placeholder="Ex. React, Python, Anglais technique"
              onChange={(e) => {
                setTitle(e.target.value);
                if (titleError) setTitleError(undefined);
              }}
            />
          </FormField>

          <FormField id="goal-category-select" label="Catégorie d’objectif">
            <Select
              id="goal-category-select"
              value={category}
              onChange={(e) => setCategory(e.target.value as ObjectiveCategory)}
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
          </FormField>
        </div>

        <FormField id="goal-outcome-input" label="Objectif final (facultatif)">
          <Input
            id="goal-outcome-input"
            value={goalText}
            placeholder="Ex. Maîtriser composants, hooks et tests unitaires"
            onChange={(e) => setGoalText(e.target.value)}
          />
        </FormField>

        <div className="grid gap-3 sm:grid-cols-3">
          <FormField id="goal-priority-select" label="Priorité">
            <Select
              id="goal-priority-select"
              value={priority}
              onChange={(e) => setPriority(e.target.value as TaskPriority)}
            >
              <option value="low">Secondaire (faible)</option>
              <option value="normal">Normale</option>
              <option value="high">Élevée</option>
              <option value="critical">Critique</option>
            </Select>
          </FormField>

          <FormField id="goal-weekly-minutes-input" label="Temps hebdomadaire souhaité (min)">
            <Input
              id="goal-weekly-minutes-input"
              type="number"
              min={0}
              max={2400}
              value={weeklyTargetMinutes}
              onChange={(e) => setWeeklyTargetMinutes(e.target.value)}
            />
          </FormField>

          <FormField id="goal-status-select" label="Statut">
            <Select
              id="goal-status-select"
              value={status}
              onChange={(e) => setStatus(e.target.value as ObjectiveStatus)}
            >
              <option value="active">Actif</option>
              <option value="paused">En pause</option>
              <option value="planned">Planifié</option>
              <option value="completed">Validé</option>
            </Select>
          </FormField>
        </div>

        <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300">
          <input
            type="checkbox"
            checked={isPrimary}
            onChange={(e) => setIsPrimary(e.target.checked)}
            className="h-4 w-4 rounded border-zinc-300 text-teal-600 focus:ring-teal-500"
          />
          Définir comme priorité principale active
        </label>

        <details className="rounded-xl bg-zinc-50 p-3.5 dark:bg-zinc-800/60">
          <summary className="cursor-pointer text-xs font-medium text-zinc-700 dark:text-zinc-300">
            Préciser niveau, échéance et livrables (facultatif)
          </summary>
          <div className="mt-3 space-y-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <FormField id="goal-current-level-input" label="Niveau actuel (0 à 5)">
                <Input
                  id="goal-current-level-input"
                  type="number"
                  min={0}
                  max={5}
                  value={currentLevel}
                  placeholder="Non précisé"
                  onChange={(e) => setCurrentLevel(e.target.value)}
                />
              </FormField>
              <FormField id="goal-target-level-input" label="Niveau visé (1 à 5)">
                <Input
                  id="goal-target-level-input"
                  type="number"
                  min={1}
                  max={5}
                  value={targetLevel}
                  placeholder="Non précisé"
                  onChange={(e) => setTargetLevel(e.target.value)}
                />
              </FormField>
              <FormField id="goal-target-date-input" label="Échéance facultative">
                <Input
                  id="goal-target-date-input"
                  type="date"
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                />
              </FormField>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <FormField id="goal-motivation-input" label="Motivation">
                <Input
                  id="goal-motivation-input"
                  value={motivation}
                  placeholder="Pourquoi cet objectif compte pour vous"
                  onChange={(e) => setMotivation(e.target.value)}
                />
              </FormField>
              <FormField id="goal-next-action-input" label="Prochaine action concrète">
                <Input
                  id="goal-next-action-input"
                  value={nextAction}
                  placeholder="Ex. Étudier props et coder un exercice"
                  onChange={(e) => setNextAction(e.target.value)}
                />
              </FormField>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <FormField id="goal-deliverables-input" label="Livrables attendus (un par ligne)">
                <Textarea
                  id="goal-deliverables-input"
                  rows={2}
                  value={deliverablesText}
                  placeholder="Mini application testée"
                  onChange={(e) => setDeliverablesText(e.target.value)}
                />
              </FormField>
              <FormField id="goal-criteria-input" label="Critères de réussite (un par ligne)">
                <Textarea
                  id="goal-criteria-input"
                  rows={2}
                  value={criteriaText}
                  placeholder="Tests unitaires verts et explication claire"
                  onChange={(e) => setCriteriaText(e.target.value)}
                />
              </FormField>
            </div>
          </div>
        </details>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
            Annuler
          </Button>
          <Button type="submit" variant="primary" size="sm">
            {editingGoal ? 'Enregistrer l’objectif' : 'Créer l’objectif'}
          </Button>
        </div>
      </form>
    </section>
  );
}
