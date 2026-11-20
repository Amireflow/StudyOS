import { useState, type FormEvent } from 'react';
import { Cancel01Icon, CheckmarkCircle02Icon, SparklesIcon } from '@hugeicons/core-free-icons';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import type { ConversationalIntakeRecap } from '../../types/domain';

export interface ObjectivesIntakePanelProps {
  onAnalyze: (
    message: string,
    knownAnswers: Record<string, unknown>,
  ) => Promise<ConversationalIntakeRecap>;
  onConfirm: (payload: {
    recap: ConversationalIntakeRecap;
    knownAnswers: Record<string, unknown>;
  }) => Promise<void>;
  onClose: () => void;
}

export function ObjectivesIntakePanel({
  onAnalyze,
  onConfirm,
  onClose,
}: ObjectivesIntakePanelProps) {
  const [message, setMessage] = useState('');
  const [recap, setRecap] = useState<ConversationalIntakeRecap | null>(null);
  const [currentLevel, setCurrentLevel] = useState('');
  const [targetLevel, setTargetLevel] = useState('');
  const [weeklyMinutes, setWeeklyMinutes] = useState('');
  const [primaryTitle, setPrimaryTitle] = useState('');
  const [motivation, setMotivation] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buildKnownAnswers = (): Record<string, unknown> => {
    const known: Record<string, unknown> = {};
    if (currentLevel.trim() !== '') known.current_level = Number(currentLevel);
    if (targetLevel.trim() !== '') known.target_level = Number(targetLevel);
    if (weeklyMinutes.trim() !== '') known.available_time_weekly_minutes = Number(weeklyMinutes);
    if (primaryTitle.trim() !== '') known.primary_title = primaryTitle.trim();
    if (motivation.trim() !== '') known.motivation = motivation.trim();
    if (targetDate.trim() !== '') known.target_date = `${targetDate.trim()}T23:59:00Z`;
    return known;
  };

  const runAnalysis = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (message.trim().length < 2) {
      setError('Décrivez vos objectifs en quelques mots avant de lancer l’analyse.');
      return;
    }
    setError(null);
    setIsWorking(true);
    try {
      const nextRecap = await onAnalyze(message.trim(), buildKnownAnswers());
      setRecap(nextRecap);
      if (!primaryTitle && nextRecap.objectives.length === 1) {
        setPrimaryTitle(nextRecap.objectives[0].title);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de l’analyse conversationnelle.');
    } finally {
      setIsWorking(false);
    }
  };

  const handleConfirm = async () => {
    if (!recap) return;
    setIsWorking(true);
    setError(null);
    try {
      await onConfirm({
        recap,
        knownAnswers: buildKnownAnswers(),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible d’enregistrer ces objectifs.');
    } finally {
      setIsWorking(false);
    }
  };

  return (
    <section
      aria-label="Décrire mes besoins à l’IA"
      className="space-y-4 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-zinc-200/70 dark:bg-zinc-900 dark:ring-zinc-800"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          Décrire mes besoins
        </h2>
        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          <Icon icon={Cancel01Icon} size={15} />
          Fermer
        </Button>
      </div>

      <form onSubmit={runAnalysis} className="space-y-3">
        <FormField id="intake-message-input" label="Décrire vos objectifs en langage naturel">
          <Textarea
            id="intake-message-input"
            rows={3}
            value={message}
            placeholder="Ex. Continuer Python, apprendre React et créer un projet web."
            onChange={(e) => setMessage(e.target.value)}
          />
        </FormField>

        <div className="flex justify-end">
          <Button type="submit" variant="primary" size="sm" disabled={isWorking}>
            <Icon icon={SparklesIcon} size={15} />
            Analyser mes besoins
          </Button>
        </div>
      </form>

      {error && (
        <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:bg-rose-950/50 dark:text-rose-200">
          {error}
        </p>
      )}

      {recap && (
        <div className="space-y-4 rounded-xl bg-zinc-50 p-4 dark:bg-zinc-800/60">
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-400">
              Récapitulatif structuré
            </h3>
            <ul className="space-y-1 text-xs text-zinc-800 dark:text-zinc-200">
              <li>
                <strong>Objectifs extraits :</strong>{' '}
                {recap.objectives.map((o) => o.title).join(', ')}
              </li>
              <li>
                <strong>Niveau actuel :</strong>{' '}
                {recap.currentLevel !== null ? `${recap.currentLevel}/5` : 'Non renseigné'}
              </li>
              <li>
                <strong>Niveau visé :</strong>{' '}
                {recap.targetLevel !== null ? `${recap.targetLevel}/5` : 'Non renseigné'}
              </li>
              <li>
                <strong>Priorité :</strong> {recap.priority ?? 'Non précisée'}
              </li>
              <li>
                <strong>Motivation :</strong> {recap.motivation ?? 'Non renseignée'}
              </li>
              <li>
                <strong>Temps disponible :</strong>{' '}
                {recap.availableTimeWeeklyMinutes !== null
                  ? `${recap.availableTimeWeeklyMinutes} min / semaine`
                  : 'Non renseigné'}
              </li>
              <li>
                <strong>Échéance éventuelle :</strong>{' '}
                {recap.targetDate ? recap.targetDate.slice(0, 10) : 'Aucune précisée'}
              </li>
              <li>
                <strong>Livrables attendus :</strong>{' '}
                {recap.expectedDeliverables.join(' ; ') || 'À définir'}
              </li>
              <li>
                <strong>Conditions de validation :</strong>{' '}
                {recap.validationConditions.join(' ; ') || 'Preuve évaluée'}
              </li>
            </ul>
          </div>

          {recap.progressiveQuestions.length > 0 && (
            <div className="rounded-lg bg-amber-50/90 p-3 text-xs text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
              <p className="font-semibold">Informations manquantes à préciser progressivement :</p>
              <ul className="mt-1 list-disc space-y-1 pl-4">
                {recap.progressiveQuestions.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-3">
            <FormField id="intake-current-level" label="Préciser niveau actuel (0 à 5)">
              <Input
                id="intake-current-level"
                type="number"
                min={0}
                max={5}
                value={currentLevel}
                placeholder="Ex. 1"
                onChange={(e) => setCurrentLevel(e.target.value)}
              />
            </FormField>
            <FormField id="intake-target-level" label="Préciser niveau visé (1 à 5)">
              <Input
                id="intake-target-level"
                type="number"
                min={1}
                max={5}
                value={targetLevel}
                placeholder="Ex. 4"
                onChange={(e) => setTargetLevel(e.target.value)}
              />
            </FormField>
            <FormField id="intake-weekly-minutes" label="Temps disponible (min/sem.)">
              <Input
                id="intake-weekly-minutes"
                type="number"
                min={30}
                max={3000}
                value={weeklyMinutes}
                placeholder="Ex. 300"
                onChange={(e) => setWeeklyMinutes(e.target.value)}
              />
            </FormField>
            <FormField id="intake-primary-select" label="Priorité principale">
              <Select
                id="intake-primary-select"
                value={primaryTitle}
                onChange={(e) => setPrimaryTitle(e.target.value)}
              >
                <option value="">Choisir ultérieurement</option>
                {recap.objectives.map((o) => (
                  <option key={o.title} value={o.title}>
                    {o.title}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField id="intake-motivation" label="Motivation">
              <Input
                id="intake-motivation"
                value={motivation}
                placeholder="Ex. Stage ou projet personnel"
                onChange={(e) => setMotivation(e.target.value)}
              />
            </FormField>
            <FormField id="intake-target-date" label="Échéance éventuelle">
              <Input
                id="intake-target-date"
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
              />
            </FormField>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={isWorking}
              onClick={() => void runAnalysis()}
            >
              Actualiser le récapitulatif
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={isWorking}
              onClick={() => void handleConfirm()}
            >
              <Icon icon={CheckmarkCircle02Icon} size={15} />
              Confirmer et enregistrer
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
