import { useMemo, useState } from 'react';
import {
  Add01Icon,
  ArrowLeft01Icon,
  ArrowRight01Icon,
  Calendar03Icon,
  Copy01Icon,
} from '@hugeicons/core-free-icons';
import { PageHeader } from '../../components/layout/PageHeader';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { InlineConfirm } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import {
  addDays,
  formatDayHeaderFr,
  formatTimeFr,
  formatWeekRangeFr,
  getMondayOfWeek,
  toLocalDateKey,
} from '../../lib/date';
import { useStudyStore } from '../../state/StudyStoreContext';
import type { ScheduleEvent } from '../../types/domain';
import { formatDuration } from '../sessions/sessionUtils';
import { ScheduleEventForm } from './ScheduleEventForm';
import type { ScheduleEventFormValues } from './scheduleSchema';
import {
  computeWeekSummary,
  getConflictingEventIds,
  getEventDurationMinutes,
  getEventsForLocalDate,
  getEventsForWeek,
  getWeekDays,
  SCHEDULE_EVENT_TYPE_META,
} from './scheduleUtils';

function capitalizeFirst(value: string): string {
  if (!value) {
    return '';
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function PlanningPage() {
  const {
    scheduleEvents,
    dataMode,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    createScheduleEvent,
    updateScheduleEvent,
    deleteScheduleEvent,
    duplicateWeekEvents,
    loadDemoData,
  } = useStudyStore();

  const [weekStart, setWeekStart] = useState<Date>(() => getMondayOfWeek(new Date()));
  const [isCreating, setIsCreating] = useState(false);
  const [defaultFormDate, setDefaultFormDate] = useState<string>(() => toLocalDateKey(new Date()));
  const [editingEvent, setEditingEvent] = useState<ScheduleEvent | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const weekDays = useMemo(() => getWeekDays(weekStart), [weekStart]);
  const weekEvents = useMemo(
    () => getEventsForWeek(scheduleEvents, weekStart),
    [scheduleEvents, weekStart],
  );
  const summary = useMemo(() => computeWeekSummary(weekEvents), [weekEvents]);
  const conflictingIds = useMemo(() => getConflictingEventIds(weekEvents), [weekEvents]);

  const todayKey = toLocalDateKey(new Date());

  const handleOpenCreateForDate = (dateStr: string) => {
    setEditingEvent(null);
    setDefaultFormDate(dateStr);
    setIsCreating(true);
  };

  const handleFormSubmit = async (values: ScheduleEventFormValues) => {
    if (editingEvent) {
      if (await updateScheduleEvent(editingEvent.id, values)) {
        setFeedback(`Créneau « ${values.title.trim()} » mis à jour.`);
        setEditingEvent(null);
      }
      return;
    }

    if (await createScheduleEvent(values)) {
      setFeedback(`Créneau « ${values.title.trim()} » ajouté au planning.`);
      setIsCreating(false);
    }
  };

  const handleDuplicateWeek = async () => {
    const result = await duplicateWeekEvents(weekStart);
    if (!result) {
      return;
    }
    const { createdCount, skippedCount } = result;
    const nextWeekStart = addDays(weekStart, 7);
    setWeekStart(nextWeekStart);

    if (createdCount === 0) {
      setFeedback(
        'Tous les créneaux de cette semaine existaient déjà dans la semaine suivante.',
      );
      return;
    }

    if (skippedCount > 0) {
      setFeedback(
        `${createdCount} créneau${createdCount > 1 ? 'x' : ''} dupliqué${createdCount > 1 ? 's' : ''} vers la semaine suivante (${skippedCount} doublon${skippedCount > 1 ? 's' : ''} ignoré${skippedCount > 1 ? 's' : ''}).`,
      );
      return;
    }

    setFeedback(
      `${createdCount} créneau${createdCount > 1 ? 'x' : ''} dupliqué${createdCount > 1 ? 's' : ''} vers la semaine suivante.`,
    );
  };

  const handleDelete = async (event: ScheduleEvent) => {
    if (await deleteScheduleEvent(event.id)) {
      if (editingEvent?.id === event.id) {
        setEditingEvent(null);
      }
      setFeedback(`Créneau « ${event.title} » supprimé.`);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <PageHeader title="Planning" />
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <PageHeader title="Planning" />
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Planning"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              disabled={weekEvents.length === 0}
              onClick={handleDuplicateWeek}
            >
              <Icon icon={Copy01Icon} size={15} />
              Dupliquer vers la semaine suivante
            </Button>
            <Button
              variant="primary"
              onClick={() => handleOpenCreateForDate(toLocalDateKey(new Date()))}
            >
              <Icon icon={Add01Icon} size={15} />
              Nouveau créneau
            </Button>
          </div>
        }
      />

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Barre de navigation hebdomadaire et indicateurs */}
      <Card>
        <CardContent className="flex flex-col gap-3 py-3.5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              aria-label="Semaine précédente"
              onClick={() => setWeekStart((prev) => addDays(prev, -7))}
            >
              <Icon icon={ArrowLeft01Icon} size={15} />
              Précédente
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setWeekStart(getMondayOfWeek(new Date()))}
            >
              Cette semaine
            </Button>
            <Button
              variant="secondary"
              size="sm"
              aria-label="Semaine suivante"
              onClick={() => setWeekStart((prev) => addDays(prev, 7))}
            >
              Suivante
              <Icon icon={ArrowRight01Icon} size={15} />
            </Button>
            <span className="ml-1 text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              {formatWeekRangeFr(weekStart)}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs">
            <div>
              <span className="text-zinc-500 dark:text-zinc-400">Planifié : </span>
              <strong className="tabular-nums text-zinc-900 dark:text-zinc-100">
                {summary.eventCount === 0 ? '0 min' : formatDuration(summary.totalMinutes)}
              </strong>
            </div>
            <div>
              <span className="text-zinc-500 dark:text-zinc-400">Conflits : </span>
              <strong
                data-testid="planning-conflicts-count"
                className={cn(
                  'tabular-nums',
                  summary.conflictCount > 0
                    ? 'text-rose-700 dark:text-rose-400'
                    : 'text-zinc-900 dark:text-zinc-100',
                )}
              >
                {summary.conflictCount}
              </strong>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Formulaire de création / édition */}
      {(isCreating || editingEvent) && (
        <Card>
          <CardHeader>
            <CardTitle>{editingEvent ? 'Modifier le créneau' : 'Nouveau créneau'}</CardTitle>
          </CardHeader>
          <CardContent>
            <ScheduleEventForm
              initialEvent={editingEvent}
              defaultDate={defaultFormDate}
              existingEvents={scheduleEvents}
              onSubmit={handleFormSubmit}
              onCancel={() => {
                setIsCreating(false);
                setEditingEvent(null);
              }}
            />
          </CardContent>
        </Card>
      )}

      {/* Guide de démarrage si aucun créneau enregistré */}
      {scheduleEvents.length === 0 && !isCreating && !editingEvent && (
        <EmptyState
          icon={<Icon icon={Calendar03Icon} size={17} />}
          title="Planning vide"
          action={
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleOpenCreateForDate(toLocalDateKey(new Date()))}
              >
                Créer un premier créneau
              </Button>
              {dataMode === 'local_demo' && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    loadDemoData();
                    setFeedback('Données d’exemple chargées.');
                  }}
                >
                  Charger des données d’exemple
                </Button>
              )}
            </div>
          }
        />
      )}

      {/* Vue hebdomadaire */}
      <div className="space-y-2.5">
        {weekDays.map((day) => {
          const dayKey = toLocalDateKey(day);
          const dayLabel = capitalizeFirst(formatDayHeaderFr(day));
          const dayEvents = getEventsForLocalDate(weekEvents, day);
          const isToday = dayKey === todayKey;

          return (
            <Card
              key={dayKey}
              aria-label={dayLabel}
              className={cn(isToday && 'bg-teal-50/40 dark:bg-teal-950/30')}
            >
              <CardHeader className="flex-row items-center justify-between py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle className="text-sm">{dayLabel}</CardTitle>
                  {isToday && <Badge variant="primary">Aujourd’hui</Badge>}
                  <span className="text-xs text-zinc-500 dark:text-zinc-400">
                    {dayEvents.length} créneau{dayEvents.length > 1 ? 'x' : ''}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Ajouter un créneau le ${dayLabel}`}
                  onClick={() => handleOpenCreateForDate(dayKey)}
                >
                  <Icon icon={Add01Icon} size={14} />
                  Ajouter
                </Button>
              </CardHeader>

              <CardContent className="py-2.5">
                {dayEvents.length === 0 ? (
                  <p className="text-xs text-zinc-400 dark:text-zinc-500">Aucun créneau</p>
                ) : (
                  <ul className="space-y-2">
                    {dayEvents.map((event) => {
                      const typeMeta = SCHEDULE_EVENT_TYPE_META[event.type];
                      const hasConflict = conflictingIds.has(event.id);
                      const durationMinutes = getEventDurationMinutes(event);

                      return (
                        <li
                          key={event.id}
                          className="flex flex-col gap-2.5 rounded-xl bg-zinc-50/80 p-3 sm:flex-row sm:items-center sm:justify-between dark:bg-zinc-800/50"
                        >
                          <div className="space-y-0.5">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-xs font-semibold tabular-nums text-teal-800 dark:text-teal-300">
                                {formatTimeFr(event.startsAt)} – {formatTimeFr(event.endsAt)}
                              </span>
                              <span className="text-xs text-zinc-400 dark:text-zinc-500">
                                ({formatDuration(durationMinutes)})
                              </span>
                              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                                {event.title}
                              </h3>
                              <Badge variant={typeMeta.badgeVariant}>{typeMeta.label}</Badge>
                              {hasConflict && <Badge variant="danger">Conflit</Badge>}
                            </div>
                            {event.notes && (
                              <p className="text-xs text-zinc-600 dark:text-zinc-400">{event.notes}</p>
                            )}
                          </div>

                          <div className="flex shrink-0 items-center gap-1.5">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setIsCreating(false);
                                setEditingEvent(event);
                              }}
                            >
                              Modifier
                            </Button>
                            <InlineConfirm
                              triggerLabel="Supprimer"
                              ariaLabel={`Supprimer ${event.title}`}
                              onConfirm={() => handleDelete(event)}
                            />
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
