import { useMemo, useState, type FormEvent } from 'react';
import {
  Add01Icon,
  CheckmarkCircle02Icon,
  PlayIcon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { PageHeader } from '../../components/layout/PageHeader';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/Card';
import { FormField, InlineConfirm, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from '../../components/ui/StateFeedback';
import { formatDateTimeFr, formatTimeFr } from '../../lib/date';
import { extractFieldErrors } from '../../lib/validation';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type { SessionStatus, StudySession } from '../../types/domain';
import { isActiveTaskStatus } from '../tasks/taskUtils';
import { ManualSessionForm, StartSessionForm } from './SessionForms';
import { finishSessionSchema, type ManualSessionValues, type StartSessionValues } from './sessionSchema';
import {
  computeSessionSummary,
  formatDuration,
  getSessionDurationMinutes,
  SESSION_STATUS_META,
} from './sessionUtils';

interface ActiveSessionCardProps {
  session: StudySession;
  linkedTaskTitle: string | null;
  onFinish: (session: StudySession, result: string) => void;
  onCancel: (session: StudySession) => void;
}

function ActiveSessionCard({
  session,
  linkedTaskTitle,
  onFinish,
  onCancel,
}: ActiveSessionCardProps) {
  const [result, setResult] = useState('');
  const [error, setError] = useState<string | undefined>(undefined);

  const handleFinish = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = finishSessionSchema.safeParse({ result });
    if (!parsed.success) {
      const fieldErrors = extractFieldErrors<'result'>(parsed.error);
      setError(fieldErrors.result);
      return;
    }
    setError(undefined);
    onFinish(session, parsed.data.result);
  };

  return (
    <Card className="bg-teal-50/40 dark:bg-teal-950/30">
      <CardHeader className="sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="primary">En cours</Badge>
            <Badge variant="neutral">{session.category}</Badge>
          </div>
          <CardTitle>{session.title}</CardTitle>
          <CardDescription>
            Démarrée à {formatTimeFr(session.startedAt)}
            {linkedTaskTitle ? ` · ${linkedTaskTitle}` : ''}
          </CardDescription>
        </div>
        <InlineConfirm
          triggerLabel="Annuler la séance"
          triggerVariant="secondary"
          onConfirm={() => onCancel(session)}
        />
      </CardHeader>
      <CardContent>
        <form onSubmit={handleFinish} noValidate className="space-y-3">
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

          <div className="flex justify-end">
            <Button type="submit" variant="primary" size="sm">
              <Icon icon={CheckmarkCircle02Icon} size={15} />
              Terminer la séance
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

export function SessionsPage() {
  const {
    sessions,
    tasks,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    startSession,
    finishSession,
    cancelSession,
    recordManualSession,
    deleteSession,
  } = useStudyStore();
  const { projects, modules, lessons, skills } = useLearningStore();

  const [formMode, setFormMode] = useState<'none' | 'start' | 'manual'>('none');
  const [statusFilter, setStatusFilter] = useState<'all' | SessionStatus>('all');
  const [feedback, setFeedback] = useState<string | null>(null);

  const taskTitleById = useMemo(
    () => new Map(tasks.map((task) => [task.id, task.title])),
    [tasks],
  );
  const projectNameById = useMemo(
    () => new Map(projects.map((p) => [p.id, p.name])),
    [projects],
  );
  const moduleTitleById = useMemo(
    () => new Map(modules.map((m) => [m.id, m.title])),
    [modules],
  );
  const lessonTitleById = useMemo(
    () => new Map(lessons.map((l) => [l.id, l.title])),
    [lessons],
  );
  const skillNameById = useMemo(
    () => new Map(skills.map((s) => [s.id, s.name])),
    [skills],
  );
  const activeTasks = useMemo(
    () => tasks.filter((task) => isActiveTaskStatus(task.status)),
    [tasks],
  );
  const nonCancelledTasks = useMemo(
    () => tasks.filter((task) => task.status !== 'cancelled'),
    [tasks],
  );

  const summary = useMemo(() => computeSessionSummary(sessions), [sessions]);
  const inProgressSessions = useMemo(
    () => sessions.filter((session) => session.status === 'in_progress'),
    [sessions],
  );

  const filteredSessions = useMemo(() => {
    const base =
      statusFilter === 'all'
        ? sessions
        : sessions.filter((session) => session.status === statusFilter);
    return [...base].sort(
      (a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime(),
    );
  }, [sessions, statusFilter]);

  const handleStart = async (values: StartSessionValues) => {
    if (await startSession(values)) {
      setFormMode('none');
      setFeedback(`Séance « ${values.title.trim()} » démarrée.`);
    }
  };

  const handleManualRecord = async (values: ManualSessionValues) => {
    if (await recordManualSession(values)) {
      setFormMode('none');
      setFeedback(`Séance « ${values.title.trim()} » enregistrée dans l’historique.`);
    }
  };

  const handleFinish = async (session: StudySession, result: string) => {
    if (await finishSession(session.id, result)) {
      setFeedback(`Séance « ${session.title} » clôturée et ajoutée aux totaux.`);
    }
  };

  const handleCancel = async (session: StudySession) => {
    if (await cancelSession(session.id)) {
      setFeedback(`Séance « ${session.title} » annulée (exclue des séances achevées).`);
    }
  };

  const handleDelete = async (session: StudySession) => {
    if (await deleteSession(session.id)) {
      setFeedback(`Séance « ${session.title} » supprimée.`);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <PageHeader title="Séances" />
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <PageHeader title="Séances" />
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Séances"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="primary"
              onClick={() => setFormMode((prev) => (prev === 'start' ? 'none' : 'start'))}
            >
              <Icon icon={PlayIcon} size={15} />
              Démarrer une séance
            </Button>
            <Button
              variant="secondary"
              onClick={() => setFormMode((prev) => (prev === 'manual' ? 'none' : 'manual'))}
            >
              <Icon icon={Add01Icon} size={15} />
              Enregistrer une séance passée
            </Button>
          </div>
        }
      />

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Résumé réel */}
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Achevées</p>
            <p
              className="mt-1 text-xl font-semibold tabular-nums text-emerald-700 sm:text-2xl dark:text-emerald-400"
              data-testid="sessions-completed-count"
            >
              {summary.completedCount}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Temps réel</p>
            <p
              className="mt-1 text-xl font-semibold tabular-nums text-zinc-900 sm:text-2xl dark:text-zinc-50"
              data-testid="sessions-total-time"
            >
              {summary.completedCount === 0 ? '0 min' : formatDuration(summary.totalCompletedMinutes)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">En cours</p>
            <p
              className="mt-1 text-xl font-semibold tabular-nums text-teal-800 sm:text-2xl dark:text-teal-300"
              data-testid="sessions-in-progress-count"
            >
              {summary.inProgressCount}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Séances en cours */}
      {inProgressSessions.map((session) => (
        <ActiveSessionCard
          key={session.id}
          session={session}
          linkedTaskTitle={session.taskId ? (taskTitleById.get(session.taskId) ?? null) : null}
          onFinish={handleFinish}
          onCancel={handleCancel}
        />
      ))}

      {/* Formulaires */}
      {formMode === 'start' && (
        <StartSessionForm
          activeTasks={activeTasks}
          onSubmit={handleStart}
          onCancel={() => setFormMode('none')}
        />
      )}

      {formMode === 'manual' && (
        <ManualSessionForm
          tasks={nonCancelledTasks}
          onSubmit={handleManualRecord}
          onCancel={() => setFormMode('none')}
        />
      )}

      {/* Historique des séances */}
      <Card>
        <CardHeader className="sm:flex-row sm:items-center sm:justify-between">
          <CardTitle>Historique</CardTitle>
          <div className="w-full sm:w-52">
            <FormField id="sessions-status-filter" label="Filtrer l’historique">
              <Select
                id="sessions-status-filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as 'all' | SessionStatus)}
              >
                <option value="all">Toutes les séances</option>
                <option value="completed">Achevées</option>
                <option value="in_progress">En cours</option>
                <option value="cancelled">Annulées</option>
              </Select>
            </FormField>
          </div>
        </CardHeader>
        <CardContent>
          {sessions.length === 0 ? (
            <EmptyState
              icon={<Icon icon={Timer02Icon} size={17} />}
              title="Aucune séance enregistrée"
              action={
                <Button variant="primary" size="sm" onClick={() => setFormMode('start')}>
                  Démarrer une séance
                </Button>
              }
            />
          ) : filteredSessions.length === 0 ? (
            <EmptyState
              icon={<Icon icon={Timer02Icon} size={17} />}
              title="Aucune séance pour ce filtre"
              action={
                <Button variant="secondary" size="sm" onClick={() => setStatusFilter('all')}>
                  Afficher toutes les séances
                </Button>
              }
            />
          ) : (
            <ul className="space-y-2.5">
              {filteredSessions.map((session) => {
                const statusMeta = SESSION_STATUS_META[session.status];
                const durationMinutes = getSessionDurationMinutes(session);
                const linkedTaskTitle = session.taskId
                  ? taskTitleById.get(session.taskId)
                  : undefined;
                const linkedProjectName = session.projectId
                  ? projectNameById.get(session.projectId)
                  : undefined;
                const linkedModuleTitle = session.moduleId
                  ? moduleTitleById.get(session.moduleId)
                  : undefined;
                const linkedLessonTitle = session.lessonId
                  ? lessonTitleById.get(session.lessonId)
                  : undefined;
                const linkedSkillName = session.skillId
                  ? skillNameById.get(session.skillId)
                  : undefined;

                return (
                  <li key={session.id} className="rounded-xl bg-zinc-50/80 p-3.5 dark:bg-zinc-800/50">
                    <div className="flex flex-col gap-2.5 sm:flex-row sm:items-start sm:justify-between">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                            {session.title}
                          </h3>
                          <Badge variant={statusMeta.badgeVariant}>{statusMeta.label}</Badge>
                          <Badge variant="neutral">{session.category}</Badge>
                          {session.status === 'completed' && (
                            <Badge variant="primary">{formatDuration(durationMinutes)}</Badge>
                          )}
                          {linkedProjectName && (
                            <Badge variant="neutral">{linkedProjectName}</Badge>
                          )}
                          {linkedModuleTitle && (
                            <Badge variant="neutral">{linkedModuleTitle}</Badge>
                          )}
                          {linkedLessonTitle && (
                            <Badge variant="neutral">{linkedLessonTitle}</Badge>
                          )}
                          {linkedSkillName && (
                            <Badge variant="neutral">{linkedSkillName}</Badge>
                          )}
                        </div>

                        <p className="text-xs text-zinc-500 dark:text-zinc-400">
                          {formatDateTimeFr(session.startedAt)}
                          {session.endedAt ? ` → ${formatTimeFr(session.endedAt)}` : ' · En cours'}
                          {linkedTaskTitle ? ` · ${linkedTaskTitle}` : ''}
                        </p>

                        {session.result && (
                          <p className="text-xs text-zinc-700 dark:text-zinc-300">{session.result}</p>
                        )}
                      </div>

                      <div className="shrink-0">
                        <InlineConfirm
                          triggerLabel="Supprimer"
                          ariaLabel={`Supprimer ${session.title}`}
                          onConfirm={() => handleDelete(session)}
                        />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
