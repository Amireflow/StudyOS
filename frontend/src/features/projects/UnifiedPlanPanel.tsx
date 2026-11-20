import { useState } from 'react';
import { Calendar03Icon, Cancel01Icon, CheckmarkCircle02Icon } from '@hugeicons/core-free-icons';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import type { PersonalGoal, Project, UnifiedPlan } from '../../types/domain';

export interface UnifiedPlanPanelProps {
  goals: PersonalGoal[];
  projects: Project[];
  currentPriorityTitle: string | null;
  onGenerate: (params: {
    weeklyAvailableMinutes: number;
    primaryPriorityTitle: string | null;
  }) => Promise<UnifiedPlan>;
  onApply: (plan: UnifiedPlan) => Promise<void>;
  onClose: () => void;
}

const SOURCE_LABELS: Record<string, string> = {
  academic_obligation: 'Obligation académique fixe',
  personal_goal: 'Objectif personnel',
  project: 'Projet',
  revision: 'Révision',
  evaluation: 'Évaluation',
  recovery: 'Récupération',
};

export function UnifiedPlanPanel({
  goals,
  projects,
  currentPriorityTitle,
  onGenerate,
  onApply,
  onClose,
}: UnifiedPlanPanelProps) {
  const [weeklyMinutes, setWeeklyMinutes] = useState('420');
  const [priorityTitle, setPriorityTitle] = useState(currentPriorityTitle ?? '');
  const [plan, setPlan] = useState<UnifiedPlan | null>(null);
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const priorityCandidates = Array.from(
    new Set([
      ...goals.filter((g) => g.status === 'active').map((g) => g.title),
      ...projects.filter((p) => p.status === 'active').map((p) => p.name),
    ]),
  );

  const handleGenerate = async () => {
    setIsWorking(true);
    setError(null);
    try {
      const minutes = Math.max(60, Math.min(3000, Number(weeklyMinutes) || 420));
      const generated = await onGenerate({
        weeklyAvailableMinutes: minutes,
        primaryPriorityTitle: priorityTitle.trim() || null,
      });
      setPlan(generated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la génération du programme.');
    } finally {
      setIsWorking(false);
    }
  };

  const handleApply = async () => {
    if (!plan) return;
    setIsWorking(true);
    setError(null);
    try {
      await onApply(plan);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible d’appliquer le programme.');
    } finally {
      setIsWorking(false);
    }
  };

  return (
    <section
      aria-label="Programme unifié hors et dans emploi du temps"
      className="space-y-4 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-zinc-200/70 dark:bg-zinc-900 dark:ring-zinc-800"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
            Moteur de planification unifiée (3 sources)
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            Combine emploi du temps universitaire fixe, objectifs personnels et projets actifs sans
            conflit et avec récupération quotidienne.
          </p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          <Icon icon={Cancel01Icon} size={15} />
          Fermer
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-3 sm:items-end">
        <FormField id="plan-weekly-minutes" label="Budget temps hebdomadaire flexible (min)">
          <Input
            id="plan-weekly-minutes"
            type="number"
            min={60}
            max={3000}
            value={weeklyMinutes}
            onChange={(e) => setWeeklyMinutes(e.target.value)}
          />
        </FormField>

        <FormField id="plan-primary-priority" label="Priorité principale active">
          <Select
            id="plan-primary-priority"
            value={priorityTitle}
            onChange={(e) => setPriorityTitle(e.target.value)}
          >
            <option value="">Automatique selon vos priorités</option>
            {priorityCandidates.map((title) => (
              <option key={title} value={title}>
                {title}
              </option>
            ))}
          </Select>
        </FormField>

        <div className="flex justify-end sm:justify-start">
          <Button
            type="button"
            variant="primary"
            size="sm"
            disabled={isWorking}
            onClick={() => void handleGenerate()}
          >
            <Icon icon={Calendar03Icon} size={15} />
            Générer le programme unifié
          </Button>
        </div>
      </div>

      {error && (
        <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:bg-rose-950/50 dark:text-rose-200">
          {error}
        </p>
      )}

      {plan && (
        <div className="space-y-4 rounded-xl bg-zinc-50 p-4 dark:bg-zinc-800/60">
          <div className="grid gap-2 text-xs sm:grid-cols-4">
            <div className="rounded-lg bg-white p-2.5 dark:bg-zinc-900">
              <p className="text-zinc-500 dark:text-zinc-400">Cours universitaires fixes</p>
              <p className="mt-0.5 font-semibold text-zinc-900 dark:text-zinc-100">
                {plan.academicFixedSlots.length} créneaux ({plan.totalAcademicMinutes} min)
              </p>
            </div>
            <div className="rounded-lg bg-white p-2.5 dark:bg-zinc-900">
              <p className="text-zinc-500 dark:text-zinc-400">Objectifs personnels</p>
              <p className="mt-0.5 font-semibold text-zinc-900 dark:text-zinc-100">
                {plan.totalPersonalGoalMinutes} min
              </p>
            </div>
            <div className="rounded-lg bg-white p-2.5 dark:bg-zinc-900">
              <p className="text-zinc-500 dark:text-zinc-400">Projets actifs</p>
              <p className="mt-0.5 font-semibold text-zinc-900 dark:text-zinc-100">
                {plan.totalProjectMinutes} min
              </p>
            </div>
            <div className="rounded-lg bg-white p-2.5 dark:bg-zinc-900">
              <p className="text-zinc-500 dark:text-zinc-400">Récupération</p>
              <p className="mt-0.5 font-semibold text-zinc-900 dark:text-zinc-100">
                {plan.recoverySlots.length} plages protégées
              </p>
            </div>
          </div>

          {plan.arbitrages.length > 0 && (
            <div className="space-y-1 rounded-lg bg-white p-3 text-xs text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
              <p className="font-semibold text-zinc-900 dark:text-zinc-100">
                Arbitrages anti dispersion
              </p>
              <ul className="list-disc space-y-0.5 pl-4">
                {plan.arbitrages.map((arb) => (
                  <li key={arb}>{arb}</li>
                ))}
              </ul>
            </div>
          )}

          {plan.adaptations.length > 0 && (
            <div className="space-y-1 rounded-lg bg-amber-50 p-3 text-xs text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
              <p className="font-semibold">Adaptations suite aux résultats et échéances</p>
              <ul className="list-disc space-y-1 pl-4">
                {plan.adaptations.map((ad, idx) => (
                  <li key={`${ad.targetTitle}-${idx}`}>
                    <strong>{ad.targetTitle}</strong> : {ad.cause} ({ad.actionTaken})
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-400">
              Créneaux combinés de la semaine ({plan.weekStart})
            </h3>
            <ul className="space-y-2">
              {[...plan.academicFixedSlots, ...plan.flexibleStudySlots].map((slot, index) => (
                <li
                  key={`${slot.startsAt}-${slot.title}-${index}`}
                  className="rounded-lg bg-white p-3 text-xs dark:bg-zinc-900"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      {slot.dayLabel} {slot.localStartTime} à {slot.localEndTime} : {slot.title}
                    </span>
                    <span className="text-[11px] font-medium text-teal-700 dark:text-teal-300">
                      {SOURCE_LABELS[slot.sourceCategory] ?? slot.sourceCategory}
                    </span>
                  </div>
                  <p className="mt-1 text-zinc-600 dark:text-zinc-400">
                    Résultat attendu : {slot.expectedOutcome}
                  </p>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {plan.displacedConflictsCount > 0
                ? `${plan.displacedConflictsCount} ancien(s) créneau(x) flexible(s) en conflit seront remplacé(s) à la validation.`
                : 'Aucun empiétement sur vos cours universitaires fixes.'}
            </p>
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={isWorking || plan.flexibleStudySlots.length === 0}
              onClick={() => void handleApply()}
            >
              <Icon icon={CheckmarkCircle02Icon} size={15} />
              Valider et appliquer au planning
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
