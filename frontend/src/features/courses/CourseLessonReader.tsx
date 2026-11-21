import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowLeft01Icon,
  ArrowRight01Icon,
  BookOpen02Icon,
  CheckmarkCircle02Icon,
  Rocket01Icon,
  ViewIcon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Icon } from '../../components/ui/Icon';
import { MarkdownContent } from '../../components/ui/MarkdownContent';
import { cn } from '../../lib/cn';
import type { CourseLessonTutorAskInput, CourseSubmissionInput } from '../../lib/coursesApi';
import type {
  CourseLesson,
  CourseLevel,
  CourseSubmission,
} from '../../types/domain';
import { CourseExercisePanel } from './CourseExercisePanel';
import { CourseTutorPanel } from './CourseTutorPanel';

interface CourseLessonReaderProps {
  lesson: CourseLesson;
  level: CourseLevel;
  onSelectLesson: (lessonId: string) => void;
  onToggleComplete: (lesson: CourseLesson) => Promise<void>;
  onSubmitExercise: (input: CourseSubmissionInput) => Promise<CourseSubmission | null>;
  onGoToProject: () => void;
  onStepChange?: (lesson: CourseLesson, stepIndex: number) => Promise<void> | void;
  onAskTutor?: (lesson: CourseLesson, input: CourseLessonTutorAskInput) => Promise<boolean>;
}

interface LessonStep {
  title: string;
  markdown: string;
}

/** Découpe le chapitre en étapes digestes sur les titres `## ` (hors blocs de code). */
export function splitLessonIntoSteps(markdown: string, fallbackTitle: string): LessonStep[] {
  const lines = (markdown || '').split(/\r?\n/);
  const steps: LessonStep[] = [];
  let intro: string[] = [];
  let current: LessonStep | null = null;
  let buffer: string[] = [];
  let inFence = false;

  for (const line of lines) {
    if (/^\s*(```|~~~)/.test(line)) inFence = !inFence;
    const heading = !inFence ? line.match(/^##\s+(.+?)\s*#*\s*$/) : null;
    if (heading) {
      if (current) {
        current.markdown = buffer.join('\n').trim();
        steps.push(current);
      } else {
        intro = buffer;
      }
      current = { title: heading[1].replace(/^\d+[.)]\s*/, '').trim(), markdown: '' };
      buffer = [];
    } else {
      buffer.push(line);
    }
  }

  if (current) {
    current.markdown = buffer.join('\n').trim();
    steps.push(current);
  } else {
    return [{ title: fallbackTitle, markdown: (markdown || '').trim() }];
  }

  const introText = intro.join('\n').trim();
  if (introText && steps.length > 0) {
    steps[0] = { ...steps[0], markdown: `${introText}\n\n${steps[0].markdown}`.trim() };
  }
  return steps.filter((s) => s.markdown.length > 0 || s.title.length > 0);
}

export function CourseLessonReader({
  lesson,
  level,
  onSelectLesson,
  onToggleComplete,
  onSubmitExercise,
  onGoToProject,
  onStepChange,
  onAskTutor,
}: CourseLessonReaderProps) {
  const ordered = [...level.lessons].sort((a, b) => a.position - b.position);
  const currentIdx = ordered.findIndex((item) => item.id === lesson.id);
  const prevLesson = currentIdx > 0 ? ordered[currentIdx - 1] : null;
  const nextLesson = currentIdx >= 0 && currentIdx < ordered.length - 1 ? ordered[currentIdx + 1] : null;
  const isCompleted = lesson.status === 'completed';
  const extraCodeExamples = lesson.codeExamples.filter(
    (example) => !lesson.contentMarkdown.includes(example.code.trim()),
  );

  const steps = useMemo(
    () => splitLessonIntoSteps(lesson.contentMarkdown, lesson.title),
    [lesson.contentMarkdown, lesson.title],
  );
  const lastStepIndex = Math.max(0, steps.length - 1);

  const [stepIndex, setStepIndex] = useState(() =>
    Math.min(lastStepIndex, Math.max(0, lesson.currentStepIndex ?? 0)),
  );
  const [showAll, setShowAll] = useState(false);
  const stepRefs = useRef<Array<HTMLElement | null>>([]);
  const didMount = useRef(false);

  useEffect(() => {
    // A new lesson starts at its own persisted step, never at the previous lesson's local position.
    setStepIndex(Math.min(lastStepIndex, Math.max(0, lesson.currentStepIndex ?? 0)));
    setShowAll(false);
  }, [lesson.id, lesson.currentStepIndex, lastStepIndex]);

  useEffect(() => {
    if (!didMount.current) {
      didMount.current = true;
      return;
    }
    stepRefs.current[stepIndex]?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  }, [stepIndex]);

  const fullyRevealed = showAll || isCompleted || stepIndex >= lastStepIndex;
  const visibleCount = fullyRevealed ? steps.length : stepIndex + 1;
  const activeStep = steps[Math.min(stepIndex, lastStepIndex)];
  const progressPct = Math.round(((fullyRevealed ? steps.length : stepIndex + 1) / steps.length) * 100);
  const isMultiStep = steps.length > 1;

  const goNextStep = () => {
    const next = Math.min(lastStepIndex, stepIndex + 1);
    setStepIndex(next);
    void onStepChange?.(lesson, next);
  };

  const tutorMessages = lesson.tutorMessages ?? [];

  return (
    <article
      aria-label={`Lecture : ${lesson.title}`}
      className="mx-auto min-w-0 max-w-4xl overflow-hidden space-y-6 rounded-2xl border border-zinc-200/80 bg-white p-4 sm:space-y-7 sm:p-7 dark:border-zinc-800 dark:bg-zinc-900"
    >
      <header className="space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="primary">
              Chapitre {lesson.position}/{ordered.length}
            </Badge>
            <Badge variant="neutral">{lesson.estimatedMinutes} min</Badge>
            {isMultiStep && (
              <Badge variant="neutral">
                Étape {fullyRevealed ? steps.length : stepIndex + 1}/{steps.length}
              </Badge>
            )}
            {isCompleted && <Badge variant="success">Lu</Badge>}
          </div>

          <Button
            type="button"
            variant={isCompleted ? 'secondary' : 'primary'}
            size="sm"
            onClick={() => void onToggleComplete(lesson)}
          >
            <Icon icon={CheckmarkCircle02Icon} size={15} />
            {isCompleted ? 'Marquer non lu' : 'Marquer lu'}
          </Button>
        </div>

        <div className="min-w-0">
          <h2 className="break-words text-xl font-bold leading-tight tracking-tight text-zinc-950 sm:text-2xl dark:text-zinc-50">
            {lesson.title}
          </h2>
          {lesson.summary && (
            <p className="mt-2 max-w-[72ch] break-words text-sm leading-6 text-zinc-600 dark:text-zinc-300">
              {lesson.summary}
            </p>
          )}
        </div>

        {isMultiStep && (
          <div className="flex items-center gap-3">
            <div
              className="h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800"
              role="progressbar"
              aria-label="Progression dans le chapitre"
              aria-valuenow={progressPct}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full rounded-full bg-teal-600 transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            {!fullyRevealed && (
              <button
                type="button"
                onClick={() => setShowAll(true)}
                aria-label="Afficher toutes les étapes de cette leçon"
                className="inline-flex min-h-11 shrink-0 cursor-pointer items-center gap-1 rounded-lg px-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800 dark:hover:text-zinc-50"
              >
                <Icon icon={ViewIcon} size={13} />
                Tout afficher
              </button>
            )}
          </div>
        )}
      </header>

      <div className="min-w-0 max-w-full space-y-4">
        {steps.slice(0, visibleCount).map((step, idx) => {
          const isActive = !fullyRevealed && idx === stepIndex;
          return (
            <section
              key={`${lesson.id}-step-${idx}`}
              ref={(el) => {
                stepRefs.current[idx] = el;
              }}
              aria-label={isMultiStep ? `Étape ${idx + 1} : ${step.title}` : undefined}
              className="min-w-0 max-w-[76ch] scroll-mt-24 text-[15px] leading-7 text-zinc-800 dark:text-zinc-200"
            >
              {isMultiStep && (
                <div className="mb-2 flex items-center gap-2">
                  <span
                    className={cn(
                      'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold',
                      isActive
                        ? 'bg-teal-600 text-white'
                        : 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300',
                    )}
                  >
                    {idx + 1}
                  </span>
                  <h3 className="min-w-0 break-words text-lg font-semibold leading-7 text-zinc-900 dark:text-zinc-100">
                    {step.title}
                  </h3>
                </div>
              )}
              <MarkdownContent content={step.markdown} />
            </section>
          );
        })}
      </div>

      {fullyRevealed && extraCodeExamples.length > 0 && (
        <section aria-label="Exemples de code commentés" className="min-w-0 max-w-full space-y-3">
          <h3 className="inline-flex items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            <Icon icon={BookOpen02Icon} size={16} className="text-teal-700 dark:text-teal-400" />
            Exemples commentés
          </h3>
          <div className="space-y-3">
            {extraCodeExamples.map((example, idx) => (
              <div
                key={`${lesson.id}-ex-${idx}`}
                className="min-w-0 max-w-full overflow-hidden space-y-2 rounded-2xl bg-zinc-50 p-3.5 sm:p-4 dark:bg-zinc-800/70"
              >
                <p className="break-words text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                  {example.title}
                </p>
                <MarkdownContent
                  content={`\`\`\`${example.language}\n${example.code}\n\`\`\``}
                />
                <p className="break-words text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
                  {example.explanation}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {onAskTutor && activeStep && (
        <CourseTutorPanel
          lessonTitle={lesson.title}
          stepIndex={fullyRevealed ? lastStepIndex : stepIndex}
          stepTitle={fullyRevealed && !isMultiStep ? lesson.title : activeStep.title}
          stepContent={activeStep.markdown}
          messages={tutorMessages}
          onAsk={(input) => onAskTutor(lesson, input)}
        />
      )}

      {!fullyRevealed && (
        <div className="flex flex-col gap-3 rounded-xl border border-teal-200/80 bg-teal-50 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-teal-900 dark:bg-teal-950/40">
          <p className="max-w-[62ch] text-sm leading-6 text-teal-900 dark:text-teal-100">
            Prends le temps de bien comprendre cette étape. Une question ? Demande au tuteur ci-dessus.
          </p>
          <Button type="button" variant="primary" size="sm" onClick={goNextStep}>
            J’ai compris, étape suivante
            <Icon icon={ArrowRight01Icon} size={14} />
          </Button>
        </div>
      )}

      {fullyRevealed && (
        <CourseExercisePanel
          lessonId={lesson.id}
          exercises={lesson.exercises}
          submissions={level.submissions}
          onSubmitExercise={onSubmitExercise}
        />
      )}

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-200 pt-4 dark:border-zinc-800">
        <div>
          {prevLesson && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => onSelectLesson(prevLesson.id)}
            >
              <Icon icon={ArrowLeft01Icon} size={14} />
              Chapitre précédent
            </Button>
          )}
        </div>
        <div>
          {nextLesson ? (
            <Button
              type="button"
              variant={fullyRevealed ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => onSelectLesson(nextLesson.id)}
            >
              Chapitre suivant
              <Icon icon={ArrowRight01Icon} size={14} />
            </Button>
          ) : (
            <Button
              type="button"
              variant={fullyRevealed ? 'primary' : 'secondary'}
              size="sm"
              onClick={onGoToProject}
            >
              <Icon icon={Rocket01Icon} size={14} />
              Passer au projet du niveau
            </Button>
          )}
        </div>
      </footer>
    </article>
  );
}
