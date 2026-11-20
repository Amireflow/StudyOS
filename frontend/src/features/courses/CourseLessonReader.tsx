import {
  ArrowLeft01Icon,
  ArrowRight01Icon,
  BookOpen02Icon,
  CheckmarkCircle02Icon,
  Rocket01Icon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Icon } from '../../components/ui/Icon';
import { MarkdownContent } from '../../components/ui/MarkdownContent';
import type { CourseSubmissionInput } from '../../lib/coursesApi';
import type {
  CourseLesson,
  CourseLevel,
  CourseSubmission,
} from '../../types/domain';
import { CourseExercisePanel } from './CourseExercisePanel';

interface CourseLessonReaderProps {
  lesson: CourseLesson;
  level: CourseLevel;
  onSelectLesson: (lessonId: string) => void;
  onToggleComplete: (lesson: CourseLesson) => Promise<void>;
  onSubmitExercise: (input: CourseSubmissionInput) => Promise<CourseSubmission | null>;
  onGoToProject: () => void;
}

export function CourseLessonReader({
  lesson,
  level,
  onSelectLesson,
  onToggleComplete,
  onSubmitExercise,
  onGoToProject,
}: CourseLessonReaderProps) {
  const ordered = [...level.lessons].sort((a, b) => a.position - b.position);
  const currentIdx = ordered.findIndex((item) => item.id === lesson.id);
  const prevLesson = currentIdx > 0 ? ordered[currentIdx - 1] : null;
  const nextLesson = currentIdx >= 0 && currentIdx < ordered.length - 1 ? ordered[currentIdx + 1] : null;
  const isCompleted = lesson.status === 'completed';

  return (
    <article className="space-y-5 rounded-2xl bg-white p-5 sm:p-6 dark:bg-zinc-900">
      <header className="space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="primary">
              Chapitre {lesson.position}/{ordered.length}
            </Badge>
            <Badge variant="neutral">{lesson.estimatedMinutes} min</Badge>
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

        <div>
          <h2 className="text-lg font-bold tracking-tight text-zinc-950 sm:text-xl dark:text-zinc-50">
            {lesson.title}
          </h2>
          {lesson.summary && (
            <p className="mt-1 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">
              {lesson.summary}
            </p>
          )}
        </div>
      </header>

      <div className="text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">
        <MarkdownContent content={lesson.contentMarkdown} />
      </div>

      {lesson.codeExamples.length > 0 && (
        <section aria-label="Exemples de code commentés" className="space-y-3">
          <h3 className="inline-flex items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            <Icon icon={BookOpen02Icon} size={16} className="text-teal-700 dark:text-teal-400" />
            Exemples commentés
          </h3>
          <div className="space-y-3">
            {lesson.codeExamples.map((example, idx) => (
              <div
                key={`${lesson.id}-ex-${idx}`}
                className="space-y-2 rounded-2xl bg-zinc-50 p-4 dark:bg-zinc-800/70"
              >
                <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                  {example.title}
                </p>
                <MarkdownContent
                  content={`\`\`\`${example.language}\n${example.code}\n\`\`\``}
                />
                <p className="text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
                  {example.explanation}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      <CourseExercisePanel
        lessonId={lesson.id}
        exercises={lesson.exercises}
        submissions={level.submissions}
        onSubmitExercise={onSubmitExercise}
      />

      <footer className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-zinc-50 p-3 dark:bg-zinc-800/60">
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
              variant="primary"
              size="sm"
              onClick={() => onSelectLesson(nextLesson.id)}
            >
              Chapitre suivant
              <Icon icon={ArrowRight01Icon} size={14} />
            </Button>
          ) : (
            <Button type="button" variant="primary" size="sm" onClick={onGoToProject}>
              <Icon icon={Rocket01Icon} size={14} />
              Passer au projet du niveau
            </Button>
          )}
        </div>
      </footer>
    </article>
  );
}
