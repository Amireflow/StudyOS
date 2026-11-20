import { useState } from 'react';
import {
  BulbIcon,
  CheckmarkCircle02Icon,
  CodeIcon,
  Rocket01Icon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { MarkdownContent } from '../../components/ui/MarkdownContent';
import type { CourseSubmissionInput } from '../../lib/coursesApi';
import type { CourseExercise, CourseSubmission } from '../../types/domain';

interface CourseExercisePanelProps {
  lessonId: string;
  exercises: CourseExercise[];
  submissions: CourseSubmission[];
  onSubmitExercise: (input: CourseSubmissionInput) => Promise<CourseSubmission | null>;
}

const DIFFICULTY_META: Record<
  CourseExercise['difficulty'],
  { label: string; variant: 'primary' | 'warning' | 'danger' }
> = {
  guide: { label: 'Guidé', variant: 'primary' },
  pratique: { label: 'Pratique', variant: 'warning' },
  defi: { label: 'Défi', variant: 'danger' },
};

function ExerciseCard({
  lessonId,
  exercise,
  attempts,
  onSubmitExercise,
}: {
  lessonId: string;
  exercise: CourseExercise;
  attempts: CourseSubmission[];
  onSubmitExercise: (input: CourseSubmissionInput) => Promise<CourseSubmission | null>;
}) {
  const isClosedQuiz =
    exercise.exerciseType === 'closed_quiz' && (exercise.choices?.length ?? 0) > 0;
  const [hintsShown, setHintsShown] = useState(0);
  const [answerText, setAnswerText] = useState('');
  const [submittedCode, setSubmittedCode] = useState(exercise.starterCode ?? '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const diff = DIFFICULTY_META[exercise.difficulty];
  const latestAttempt = attempts[0] ?? null;

  const handleSubmit = async () => {
    setLocalError(null);
    if (isClosedQuiz) {
      if (!answerText.trim()) {
        setLocalError('Sélectionnez une réponse avant de soumettre le quiz.');
        return;
      }
    } else if (answerText.trim().length < 12) {
      setLocalError('Expliquez votre démarche en au moins 12 caractères avant de soumettre.');
      return;
    }
    setIsSubmitting(true);
    try {
      await onSubmitExercise({
        submissionKind: 'exercise',
        lessonId,
        exerciseId: exercise.id,
        title: exercise.title,
        answerText: answerText.trim(),
        submittedCode: isClosedQuiz ? undefined : submittedCode.trim() || undefined,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-w-0 max-w-full overflow-hidden space-y-3.5 rounded-2xl bg-zinc-50 p-3.5 sm:p-5 dark:bg-zinc-800/70">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white text-teal-700 dark:bg-zinc-900 dark:text-teal-300">
            <Icon icon={CodeIcon} size={15} />
          </span>
          <h4 className="break-words text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            {exercise.title}
          </h4>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <Badge variant={diff.variant}>{diff.label}</Badge>
          {latestAttempt?.passed && <Badge variant="success">Réussi ({latestAttempt.score}/100)</Badge>}
        </div>
      </div>

      <MarkdownContent content={exercise.instructionsMarkdown} />

      {isClosedQuiz && exercise.starterCode && (
        <MarkdownContent content={`\`\`\`\n${exercise.starterCode}\n\`\`\``} />
      )}

      {exercise.hints.length > 0 && (
        <div className="space-y-2">
          {hintsShown < exercise.hints.length && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setHintsShown((c) => Math.min(exercise.hints.length, c + 1))}
            >
              <Icon icon={BulbIcon} size={14} />
              Afficher un indice ({hintsShown}/{exercise.hints.length})
            </Button>
          )}
          {hintsShown > 0 && (
            <ul className="space-y-1.5 rounded-xl bg-amber-50/80 p-3 text-xs text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
              {exercise.hints.slice(0, hintsShown).map((hint, hIdx) => (
                <li key={hIdx}>
                  <span className="font-semibold">Indice {hIdx + 1} :</span> {hint}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="space-y-3 rounded-xl bg-white p-3.5 dark:bg-zinc-900">
        {isClosedQuiz ? (
          <fieldset className="space-y-2">
            <legend className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
              Sélectionnez votre réponse
            </legend>
            <div className="space-y-1.5">
              {(exercise.choices ?? []).map((choice, cIdx) => {
                const inputId = `quiz-${exercise.id}-${cIdx}`;
                return (
                  <label
                    key={inputId}
                    htmlFor={inputId}
                    className="flex cursor-pointer items-start gap-2 rounded-lg bg-zinc-50 p-2.5 text-xs transition-colors hover:bg-zinc-100 dark:bg-zinc-800/70 dark:hover:bg-zinc-800"
                  >
                    <input
                      id={inputId}
                      type="radio"
                      name={`quiz-${exercise.id}`}
                      value={choice}
                      checked={answerText === choice}
                      onChange={() => setAnswerText(choice)}
                      className="mt-0.5"
                    />
                    <span className="text-zinc-800 dark:text-zinc-100">{choice}</span>
                  </label>
                );
              })}
            </div>
            {localError && <p className="text-xs text-red-600 dark:text-red-400">{localError}</p>}
          </fieldset>
        ) : (
          <>
            <FormField
              id={`ex-answer-${exercise.id}`}
              label="Votre explication technique"
              required
              error={localError ?? undefined}
            >
              <Textarea
                id={`ex-answer-${exercise.id}`}
                rows={2}
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                placeholder="Décrivez votre logique, les types employés et le cas limite géré…"
              />
            </FormField>

            <FormField id={`ex-code-${exercise.id}`} label="Code de votre solution (optionnel)">
              <Textarea
                id={`ex-code-${exercise.id}`}
                rows={4}
                value={submittedCode}
                onChange={(e) => setSubmittedCode(e.target.value)}
                className="font-mono text-xs"
                placeholder="Collez votre code ici…"
              />
            </FormField>
          </>
        )}

        <Button
          type="button"
          variant="primary"
          size="sm"
          isLoading={isSubmitting}
          onClick={() => void handleSubmit()}
        >
          <Icon icon={Rocket01Icon} size={14} />
          Corriger l’exercice
        </Button>
      </div>

      {latestAttempt && (
        <div
          className={
            latestAttempt.passed
              ? 'space-y-2 rounded-xl bg-emerald-50 p-3.5 text-xs text-emerald-950 dark:bg-emerald-950/40 dark:text-emerald-100'
              : 'space-y-2 rounded-xl bg-amber-50 p-3.5 text-xs text-amber-950 dark:bg-amber-950/40 dark:text-amber-100'
          }
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 font-semibold">
              <Icon icon={CheckmarkCircle02Icon} size={15} />
              Correction : {latestAttempt.score ?? 0}/100
              {latestAttempt.attemptNumber && latestAttempt.attemptNumber > 1
                ? ` · Tentative #${latestAttempt.attemptNumber}`
                : ''}
            </span>
            <div className="flex items-center gap-1.5">
              {latestAttempt.evaluationMode && (
                <Badge variant="neutral">{latestAttempt.evaluationMode}</Badge>
              )}
              <Badge variant={latestAttempt.passed ? 'success' : 'warning'}>
                {latestAttempt.passed ? 'Exercice validé' : 'À retravailler'}
              </Badge>
            </div>
          </div>
          {latestAttempt.nextStepHint && <p>{latestAttempt.nextStepHint}</p>}
          {latestAttempt.improvements.length > 0 && (
            <ul className="list-inside list-disc space-y-0.5">
              {latestAttempt.improvements.map((imp, i) => (
                <li key={i}>{imp}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export function CourseExercisePanel({
  lessonId,
  exercises,
  submissions,
  onSubmitExercise,
}: CourseExercisePanelProps) {
  if (exercises.length === 0) {
    return null;
  }

  return (
    <section aria-label="Exercices du chapitre" className="space-y-3">
      <h3 className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
        Exercices progressifs ({exercises.length})
      </h3>
      <div className="space-y-4">
        {exercises.map((exercise) => (
          <ExerciseCard
            key={exercise.id}
            lessonId={lessonId}
            exercise={exercise}
            attempts={submissions.filter(
              (s) => s.submissionKind === 'exercise' && s.exerciseId === exercise.id,
            )}
            onSubmitExercise={onSubmitExercise}
          />
        ))}
      </div>
    </section>
  );
}
