import { useEffect, useState, type FormEvent } from 'react';
import {
  Award02Icon,
  CheckmarkCircle02Icon,
  CheckmarkSquare02Icon,
  FolderKanbanIcon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField, InlineConfirm, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { formatTimeFr } from '../../lib/date';
import { extractFieldErrors } from '../../lib/validation';
import type { SessionFinishExtra, StudySession } from '../../types/domain';
import { finishSessionSchema } from './sessionSchema';
import { formatElapsedTimer } from './sessionUtils';

export interface ActiveSessionCardProps {
  session: StudySession;
  linkedTaskTitle: string | null;
  linkedProjectName?: string;
  linkedSkillName?: string;
  onFinish: (session: StudySession, result: string, extra?: SessionFinishExtra) => void;
  onCancel: (session: StudySession) => void;
}

export function ActiveSessionCard({
  session,
  linkedTaskTitle,
  linkedProjectName,
  linkedSkillName,
  onFinish,
  onCancel,
}: ActiveSessionCardProps) {
  const [result, setResult] = useState('');
  const [actualActivity, setActualActivity] = useState('');
  const [outcomeStatus, setOutcomeStatus] = useState<'completed' | 'partial' | 'blocked'>('completed');
  const [deliverableSummary, setDeliverableSummary] = useState('');
  const [blockers, setBlockers] = useState('');
  const [nextStep, setNextStep] = useState('');
  const [error, setError] = useState<string | undefined>(undefined);
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    const timerId = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);
    return () => window.clearInterval(timerId);
  }, []);

  const handleFinish = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = finishSessionSchema.safeParse({ result });
    if (!parsed.success) {
      const fieldErrors = extractFieldErrors<'result'>(parsed.error);
      setError(fieldErrors.result);
      return;
    }
    setError(undefined);
    const hasExtra = Boolean(
      actualActivity.trim() ||
        deliverableSummary.trim() ||
        blockers.trim() ||
        nextStep.trim() ||
        outcomeStatus !== 'completed',
    );
    onFinish(
      session,
      parsed.data.result,
      hasExtra
        ? {
            plannedActivity: session.plannedActivity ?? undefined,
            actualActivity: actualActivity.trim() || undefined,
            outcomeStatus,
            deliverableSummary: deliverableSummary.trim() || undefined,
            blockers: blockers.trim() || undefined,
            nextStep: nextStep.trim() || undefined,
          }
        : undefined,
    );
  };

  return (
    <section
      aria-label={`Séance active : ${session.title}`}
      className="space-y-4 rounded-2xl bg-teal-50/75 p-5 sm:p-6 dark:bg-teal-950/40"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            aria-hidden="true"
            className="h-2.5 w-2.5 shrink-0 animate-pulse rounded-full bg-teal-600 dark:bg-teal-400"
          />
          <Badge variant="primary">En cours</Badge>
          <span className="rounded-full bg-white/80 px-2.5 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-900/70 dark:text-zinc-300">
            {session.category}
          </span>
        </div>

        <InlineConfirm
          triggerLabel="Annuler la séance"
          triggerVariant="secondary"
          onConfirm={() => onCancel(session)}
        />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0 space-y-1.5">
          <h2 className="text-lg font-semibold tracking-tight text-zinc-900 sm:text-xl dark:text-zinc-50">
            {session.title}
          </h2>
          <p className="text-xs text-zinc-600 dark:text-zinc-400">
            Démarrée à {formatTimeFr(session.startedAt)}
          </p>

          {(linkedTaskTitle || linkedProjectName || linkedSkillName) && (
            <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
              {linkedTaskTitle && (
                <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2.5 py-0.5 text-[11px] font-medium text-zinc-700 dark:bg-zinc-900/70 dark:text-zinc-300">
                  <Icon icon={CheckmarkSquare02Icon} size={12} />
                  {linkedTaskTitle}
                </span>
              )}
              {linkedProjectName && (
                <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2.5 py-0.5 text-[11px] font-medium text-zinc-700 dark:bg-zinc-900/70 dark:text-zinc-300">
                  <Icon icon={FolderKanbanIcon} size={12} />
                  {linkedProjectName}
                </span>
              )}
              {linkedSkillName && (
                <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2.5 py-0.5 text-[11px] font-medium text-zinc-700 dark:bg-zinc-900/70 dark:text-zinc-300">
                  <Icon icon={Award02Icon} size={12} />
                  {linkedSkillName}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="shrink-0">
          <p
            data-testid="active-session-timer"
            className="font-mono text-2xl font-semibold tracking-tight tabular-nums text-teal-900 sm:text-3xl dark:text-teal-100"
          >
            {formatElapsedTimer(session.startedAt, nowMs)}
          </p>
        </div>
      </div>

      <form
        onSubmit={handleFinish}
        noValidate
        className="space-y-3 rounded-xl bg-white/90 p-4 dark:bg-zinc-900/85"
      >
        <FormField
          id={`finish-result-${session.id}`}
          label="Résultat ou note de fin"
          required
          error={error}
        >
          <Textarea
            id={`finish-result-${session.id}`}
            rows={2}
            value={result}
            hasError={Boolean(error)}
            placeholder="Ce que vous avez produit ou appris…"
            onChange={(e) => {
              setResult(e.target.value);
              if (error) {
                setError(undefined);
              }
            }}
          />
        </FormField>

        <details className="rounded-lg bg-zinc-50/90 p-3 text-xs dark:bg-zinc-800/60">
          <summary className="cursor-pointer font-medium text-zinc-700 dark:text-zinc-300">
            Activité réelle, difficultés et preuve (facultatif)
          </summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <FormField id={`finish-actual-${session.id}`} label="Activité réellement effectuée">
              <Input
                id={`finish-actual-${session.id}`}
                value={actualActivity}
                placeholder="Ex. Composants maîtrisés, blocage sur useEffect"
                onChange={(e) => setActualActivity(e.target.value)}
              />
            </FormField>

            <FormField id={`finish-outcome-${session.id}`} label="Statut du résultat">
              <Select
                id={`finish-outcome-${session.id}`}
                value={outcomeStatus}
                onChange={(e) =>
                  setOutcomeStatus(e.target.value as 'completed' | 'partial' | 'blocked')
                }
              >
                <option value="completed">Objectif de séance atteint</option>
                <option value="partial">Avancement partiel</option>
                <option value="blocked">Bloqué / reprise nécessaire</option>
              </Select>
            </FormField>

            <FormField id={`finish-deliverable-${session.id}`} label="Preuve ou livrable produit">
              <Input
                id={`finish-deliverable-${session.id}`}
                value={deliverableSummary}
                placeholder="Ex. Composant ContactForm.tsx et tests Vitest"
                onChange={(e) => setDeliverableSummary(e.target.value)}
              />
            </FormField>

            <FormField id={`finish-blockers-${session.id}`} label="Difficultés rencontrées">
              <Input
                id={`finish-blockers-${session.id}`}
                value={blockers}
                placeholder="Ex. Dépendances useEffect"
                onChange={(e) => setBlockers(e.target.value)}
              />
            </FormField>

            <div className="sm:col-span-2">
              <FormField id={`finish-next-${session.id}`} label="Prochaine étape recommandée">
                <Input
                  id={`finish-next-${session.id}`}
                  value={nextStep}
                  placeholder="Ex. Refaire 2 exercices ciblés sur useEffect"
                  onChange={(e) => setNextStep(e.target.value)}
                />
              </FormField>
            </div>
          </div>
        </details>

        <div className="flex justify-end">
          <Button type="submit" variant="primary" size="sm">
            <Icon icon={CheckmarkCircle02Icon} size={15} />
            Terminer la séance
          </Button>
        </div>
      </form>
    </section>
  );
}
