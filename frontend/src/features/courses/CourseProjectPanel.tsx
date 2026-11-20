import { useState, type FormEvent } from 'react';
import {
  Award02Icon,
  CheckmarkCircle02Icon,
  LockIcon,
  Rocket01Icon,
  SquareUnlock02Icon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { MarkdownContent } from '../../components/ui/MarkdownContent';
import type { CourseSubmissionInput } from '../../lib/coursesApi';
import type { CourseLevel, CourseSubmission } from '../../types/domain';

interface CourseProjectPanelProps {
  level: CourseLevel;
  isFinalLevel: boolean;
  onSubmitProject: (input: CourseSubmissionInput) => Promise<CourseSubmission | null>;
  onValidateLevel: () => Promise<void>;
}

export function CourseProjectPanel({
  level,
  isFinalLevel,
  onSubmitProject,
  onValidateLevel,
}: CourseProjectPanelProps) {
  const [answerText, setAnswerText] = useState('');
  const [submittedCode, setSubmittedCode] = useState('');
  const [referenceUrl, setReferenceUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const projectSubmissions = level.submissions.filter((s) => s.submissionKind === 'project');
  const isValidated = level.status === 'validated';
  const lessonsDone =
    level.lessonsCompleted ??
    (level.lessons.length > 0 && level.lessons.every((l) => l.status === 'completed'));
  const hasExercises = level.lessons.some((l) => l.exercises.length > 0);
  const exerciseDone =
    level.exercisePassed ??
    (!hasExercises || level.submissions.some((s) => s.submissionKind === 'exercise' && s.passed));
  const canValidate = level.canValidate ?? (lessonsDone && exerciseDone && level.projectPassed);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (answerText.trim().length < 12) {
      setFormError('Votre explication technique doit contenir au moins 12 caractères.');
      return;
    }
    if (referenceUrl.trim() && !/^https?:\/\/\S+$/i.test(referenceUrl.trim())) {
      setFormError('Le lien externe doit commencer par http:// ou https://.');
      return;
    }
    setIsSubmitting(true);
    try {
      await onSubmitProject({
        submissionKind: 'project',
        title: level.projectTitle || `Projet Niveau ${level.levelNumber}`,
        answerText: answerText.trim(),
        submittedCode: submittedCode.trim() || undefined,
        referenceUrl: referenceUrl.trim() || undefined,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleValidate = async () => {
    setIsValidating(true);
    try {
      await onValidateLevel();
    } finally {
      setIsValidating(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Bandeau de déblocage du niveau en haut pour une visibilité immédiate */}
      <section className="rounded-2xl bg-white p-4 sm:p-5 dark:bg-zinc-900">
        {isValidated ? (
          <div className="flex items-start gap-3 rounded-xl bg-emerald-50 p-3.5 text-xs text-emerald-950 dark:bg-emerald-950/40 dark:text-emerald-100">
            <Icon icon={Award02Icon} size={18} className="mt-0.5 shrink-0 text-emerald-700 dark:text-emerald-300" />
            <div>
              <p className="font-semibold">Niveau {level.levelNumber} validé</p>
              <p className="mt-0.5">
                {isFinalLevel
                  ? 'Félicitations ! Tous les niveaux de ce cours ont été validés avec succès.'
                  : `Le niveau ${level.levelNumber + 1} a été débloqué avec ses chapitres, exercices et ressources.`}
              </p>
            </div>
          </div>
        ) : !canValidate ? (
          <div className="flex flex-col gap-3 rounded-xl bg-zinc-50 p-3.5 sm:flex-row sm:items-center sm:justify-between dark:bg-zinc-800/70">
            <div className="flex items-start gap-2.5 text-xs text-zinc-700 dark:text-zinc-300">
              <Icon icon={LockIcon} size={16} className="mt-0.5 shrink-0 text-zinc-500" />
              <div className="space-y-1">
                <p className="font-semibold text-zinc-900 dark:text-zinc-100">
                  Verrou pédagogique du Niveau {level.levelNumber}
                </p>
                <ul className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-zinc-600 dark:text-zinc-400">
                  <li>
                    {lessonsDone ? '✓' : '○'} Tous les chapitres du niveau marqués lus
                  </li>
                  <li>
                    {exerciseDone ? '✓' : '○'} Au moins un exercice du niveau réussi
                  </li>
                  <li>
                    {level.projectPassed ? '✓' : '○'} Projet vérifiable réussi (score &gt;= {level.passThreshold}/100)
                  </li>
                </ul>
              </div>
            </div>
            <Button type="button" variant="secondary" size="sm" disabled className="shrink-0">
              {isFinalLevel
                ? 'Valider le niveau final et terminer le cours'
                : `Valider le niveau ${level.levelNumber} et débloquer le niveau ${level.levelNumber + 1}`}
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-3 rounded-xl bg-teal-50/75 p-3.5 sm:flex-row sm:items-center sm:justify-between dark:bg-teal-950/40">
            <div className="flex items-start gap-2.5 text-xs text-teal-950 dark:text-teal-100">
              <Icon icon={SquareUnlock02Icon} size={17} className="mt-0.5 shrink-0 text-teal-700 dark:text-teal-300" />
              <p>
                Chapitres lus, exercice validé et projet au-dessus du seuil ({level.passThreshold}/100). Vous pouvez débloquer la suite.
              </p>
            </div>
            <Button
              type="button"
              variant="primary"
              size="sm"
              className="shrink-0"
              isLoading={isValidating}
              onClick={() => void handleValidate()}
            >
              <Icon icon={Award02Icon} size={15} />
              {isFinalLevel
                ? 'Valider le niveau final et terminer le cours'
                : `Valider le niveau ${level.levelNumber} et débloquer le niveau ${level.levelNumber + 1}`}
            </Button>
          </div>
        )}
      </section>

      <section className="space-y-4 rounded-2xl bg-white p-5 sm:p-6 dark:bg-zinc-900">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-xs font-medium text-teal-700 dark:text-teal-400">
              Projet du niveau {level.levelNumber}
            </p>
            <h2 className="mt-0.5 text-lg font-bold tracking-tight text-zinc-950 dark:text-zinc-50">
              {level.projectTitle ?? `Mini-projet Niveau ${level.levelNumber}`}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="neutral">Seuil requis : {level.passThreshold}/100</Badge>
            <Badge
              variant={
                isValidated ? 'success' : level.projectPassed ? 'primary' : 'warning'
              }
            >
              {isValidated
                ? 'Niveau validé'
                : level.projectPassed
                  ? 'Projet réussi'
                  : 'En attente de validation'}
            </Badge>
          </div>
        </div>

        {level.projectBrief && (
          <div className="rounded-xl bg-zinc-50 p-4 dark:bg-zinc-800/60">
            <MarkdownContent content={level.projectBrief} />
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          {level.projectDeliverables.length > 0 && (
            <div className="space-y-2 rounded-xl bg-zinc-50 p-3.5 dark:bg-zinc-800/50">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                Livrables attendus
              </h3>
              <ul className="space-y-1.5 text-xs text-zinc-700 dark:text-zinc-300">
                {level.projectDeliverables.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <Icon
                      icon={CheckmarkCircle02Icon}
                      size={14}
                      className="mt-0.5 shrink-0 text-teal-600 dark:text-teal-400"
                    />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {level.projectRubric.length > 0 && (
            <div className="space-y-2 rounded-xl bg-zinc-50 p-3.5 dark:bg-zinc-800/50">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                Grille d’évaluation (100 points)
              </h3>
              <div className="grid gap-2 sm:grid-cols-2">
                {level.projectRubric.map((crit) => (
                  <div
                    key={crit.key}
                    className="rounded-lg bg-white p-2.5 text-xs dark:bg-zinc-900"
                  >
                    <div className="flex items-center justify-between gap-2 font-semibold text-zinc-900 dark:text-zinc-100">
                      <span>{crit.label}</span>
                      <span className="tabular-nums text-teal-700 dark:text-teal-400">
                        /{crit.maxScore}
                      </span>
                    </div>
                    <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-zinc-500 dark:text-zinc-400">
                      {crit.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="space-y-4 rounded-2xl bg-white p-5 sm:p-6 dark:bg-zinc-900">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          Rendre votre projet pour correction
        </h3>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <FormField
            id={`project-answer-${level.id}`}
            label="Explication technique et démarche"
            required
            error={formError ?? undefined}
          >
            <Textarea
              id={`project-answer-${level.id}`}
              rows={4}
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              placeholder="Décrivez votre architecture, les types/structures choisis, les cas d’erreur gérés et vos vérifications…"
            />
          </FormField>

          <FormField
            id={`project-code-${level.id}`}
            label="Code ou extrait livrable"
            hint="Joignez les fonctions clés et un exemple de test pour maximiser le score technique."
          >
            <Textarea
              id={`project-code-${level.id}`}
              rows={6}
              value={submittedCode}
              onChange={(e) => setSubmittedCode(e.target.value)}
              className="font-mono text-xs"
              placeholder="Collez votre code ou vos requêtes ici…"
            />
          </FormField>

          <FormField
            id={`project-url-${level.id}`}
            label="Lien de dépôt ou démo (optionnel)"
            hint="Lien http(s) conservé pour référence (non inspecté automatiquement lors de la correction)."
          >
            <Input
              id={`project-url-${level.id}`}
              type="url"
              value={referenceUrl}
              onChange={(e) => setReferenceUrl(e.target.value)}
              placeholder="https://github.com/..."
            />
          </FormField>

          <Button type="submit" variant="primary" size="md" isLoading={isSubmitting}>
            <Icon icon={Rocket01Icon} size={15} />
            Soumettre le projet pour correction
          </Button>
        </form>
      </section>

      {projectSubmissions.length > 0 && (
        <section aria-label="Corrections du projet" className="space-y-3">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Historique des corrections ({projectSubmissions.length})
          </h3>
          {projectSubmissions.map((sub) => (
            <article
              key={sub.id}
              className="space-y-3 rounded-2xl bg-white p-5 dark:bg-zinc-900"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-bold text-zinc-950 dark:text-zinc-50">
                  Score : {sub.score ?? 0}/100
                  {sub.attemptNumber && sub.attemptNumber > 1 ? ` · Tentative #${sub.attemptNumber}` : ''}
                </span>
                <div className="flex flex-wrap items-center gap-1.5">
                  {sub.manualReviewRequired && (
                    <Badge variant="warning">Revue manuelle requise</Badge>
                  )}
                  <Badge variant={sub.passed ? 'success' : 'danger'}>
                    {sub.passed ? 'Seuil atteint' : 'Insuffisant'}
                  </Badge>
                </div>
              </div>

              {sub.feedbackMarkdown && <MarkdownContent content={sub.feedbackMarkdown} />}

              {sub.criteriaResults.length > 0 && (
                <div className="grid gap-2 sm:grid-cols-2">
                  {sub.criteriaResults.map((cr) => (
                    <div
                      key={cr.key}
                      className="rounded-xl bg-zinc-50 p-3 text-xs dark:bg-zinc-800/60"
                    >
                      <div className="flex items-center justify-between font-semibold text-zinc-900 dark:text-zinc-100">
                        <span>{cr.label}</span>
                        <span className="tabular-nums">
                          {cr.score}/{cr.maxScore}
                        </span>
                      </div>
                      <p className="mt-1 text-[11px] text-zinc-600 dark:text-zinc-400">
                        {cr.feedback}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {sub.improvements.length > 0 && (
                <div className="rounded-xl bg-amber-50/80 p-3 text-xs text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
                  <p className="font-semibold">Points à améliorer :</p>
                  <ul className="mt-1 list-inside list-disc space-y-0.5">
                    {sub.improvements.map((imp, idx) => (
                      <li key={idx}>{imp}</li>
                    ))}
                  </ul>
                </div>
              )}

              {sub.nextStepHint && (
                <p className="text-xs font-medium text-teal-800 dark:text-teal-300">
                  {sub.nextStepHint}
                </p>
              )}
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
