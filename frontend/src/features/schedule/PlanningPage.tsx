import { useMemo, useState } from 'react';
import {
  Add01Icon,
  ArrowLeft01Icon,
  ArrowRight01Icon,
  Calendar03Icon,
  Cancel01Icon,
  Copy01Icon,
  File02Icon,
  GridViewIcon,
  LeftToRightListBulletIcon,
  PencilEdit02Icon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
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
import type { ScheduleEvent, ScheduleEventType } from '../../types/domain';
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
  SCHEDULE_EVENT_TONE,
  SCHEDULE_EVENT_TYPE_META,
} from './scheduleUtils';
import { IntelligentPlanStudio } from './IntelligentPlanStudio';
import { TimetableImportPanel } from './TimetableImportPanel';
import { WeekTimeGrid } from './WeekTimeGrid';

type ViewMode = 'agenda' | 'grid';
type TypeFilter = 'all' | ScheduleEventType;

const EVENT_TYPES: ScheduleEventType[] = ['course', 'learning', 'project', 'personal', 'other'];

function capitalizeFirst(value: string): string {
  if (!value) {
    return '';
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function PlanningPage() {
  const {
    scheduleEvents,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    createScheduleEvent,
    updateScheduleEvent,
    deleteScheduleEvent,
    duplicateWeekEvents,
  } = useStudyStore();

  const [weekStart, setWeekStart] = useState<Date>(() => getMondayOfWeek(new Date()));
  const [viewMode, setViewMode] = useState<ViewMode>('agenda');
  const [selectedDayKey, setSelectedDayKey] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [conflictsOnly, setConflictsOnly] = useState(false);

  const [isCreating, setIsCreating] = useState(false);
  const [isImportingTimetable, setIsImportingTimetable] = useState(false);
  const [isIntelligentPlanOpen, setIsIntelligentPlanOpen] = useState(false);
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

  const filteredWeekEvents = useMemo(() => {
    return weekEvents.filter((event) => {
      if (typeFilter !== 'all' && event.type !== typeFilter) {
        return false;
      }
      if (conflictsOnly && !conflictingIds.has(event.id)) {
        return false;
      }
      return true;
    });
  }, [conflictingIds, conflictsOnly, typeFilter, weekEvents]);

  const categoryBreakdown = useMemo(() => {
    const totals: Record<ScheduleEventType, number> = {
      course: 0,
      learning: 0,
      project: 0,
      personal: 0,
      other: 0,
    };
    for (const event of weekEvents) {
      totals[event.type] += getEventDurationMinutes(event);
    }
    return EVENT_TYPES.filter((type) => totals[type] > 0).map((type) => ({
      type,
      minutes: totals[type],
    }));
  }, [weekEvents]);

  const todayKey = toLocalDateKey(new Date());

  const visibleDays = useMemo(
    () =>
      selectedDayKey
        ? weekDays.filter((day) => toLocalDateKey(day) === selectedDayKey)
        : weekDays,
    [selectedDayKey, weekDays],
  );

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
    setSelectedDayKey(null);
    setTypeFilter('all');
    setConflictsOnly(false);

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

  const navigateWeek = (nextMonday: Date) => {
    setWeekStart(nextMonday);
    setSelectedDayKey(null);
  };

  const resetFilters = () => {
    setTypeFilter('all');
    setConflictsOnly(false);
    setSelectedDayKey(null);
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <header>
          <h1 className="ui-page-title">
            Planning
          </h1>
        </header>
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <header>
          <h1 className="ui-page-title">
            Planning
          </h1>
        </header>
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  return (
    <div className="space-y-3.5 sm:space-y-5">
      {/* En-tête */}
      <header className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="ui-page-title">
            Planning
          </h1>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            {formatWeekRangeFr(weekStart)}
          </p>
        </div>

        <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0">
          <Button
            type="button"
            variant="primary"
            size="sm"
            className="shrink-0"
            onClick={() => {
              setIsImportingTimetable(false);
              handleOpenCreateForDate(selectedDayKey ?? toLocalDateKey(new Date()));
            }}
          >
            <Icon icon={Add01Icon} size={15} />
            Nouveau créneau
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="shrink-0"
            onClick={() => {
              setIsCreating(false);
              setEditingEvent(null);
              setIsImportingTimetable((prev) => !prev);
            }}
          >
            <Icon icon={File02Icon} size={15} />
            Importer mon emploi du temps
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="shrink-0"
            onClick={() => {
              setIsIntelligentPlanOpen((prev) => !prev);
              setIsImportingTimetable(false);
              setIsCreating(false);
            }}
          >
            <Icon icon={Calendar03Icon} size={15} />
            Programme intelligent
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="shrink-0"
            disabled={weekEvents.length === 0}
            onClick={() => void handleDuplicateWeek()}
          >
            <Icon icon={Copy01Icon} size={15} />
            Dupliquer vers la semaine suivante
          </Button>
        </div>
      </header>

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {isIntelligentPlanOpen && (
        <IntelligentPlanStudio
          onClose={() => setIsIntelligentPlanOpen(false)}
          onApplied={(msg) => setFeedback(msg)}
        />
      )}

      {isImportingTimetable && (
        <TimetableImportPanel
          weekStart={weekStart}
          onClose={() => setIsImportingTimetable(false)}
          onImportCancelled={() => {
            setIsImportingTimetable(false);
            setFeedback('Importation annulée : aucun cours n’a été enregistré.');
          }}
          onImportSuccess={(result) => {
            setIsImportingTimetable(false);
            const dupNote =
              result.skippedDuplicatesCount > 0
                ? ` (${result.skippedDuplicatesCount} doublon${result.skippedDuplicatesCount > 1 ? 's' : ''} ignoré${result.skippedDuplicatesCount > 1 ? 's' : ''})`
                : '';
            setFeedback(
              `Emploi du temps validé : ${result.createdCount} cours enregistré${result.createdCount > 1 ? 's' : ''} dans votre calendrier${dupNote}.`,
            );
          }}
        />
      )}

      {/* Barre de pilotage hebdomadaire */}
      <section
        aria-label="Pilotage de la semaine"
        className="space-y-3.5 rounded-2xl bg-white p-3.5 sm:space-y-4 sm:p-5 dark:bg-zinc-900"
      >
        {/* Ligne 1 : Navigation semaine + bascule Agenda / Grille */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="inline-flex min-w-0 max-w-full items-center gap-0.5 rounded-xl bg-zinc-100 p-1 sm:gap-1 dark:bg-zinc-800/80">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label="Semaine précédente"
              className="px-2 sm:px-3"
              onClick={() => navigateWeek(addDays(weekStart, -7))}
            >
              <Icon icon={ArrowLeft01Icon} size={15} />
              <span className="hidden sm:inline">Précédente</span>
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="px-2.5 sm:px-3"
              onClick={() => navigateWeek(getMondayOfWeek(new Date()))}
            >
              Cette semaine
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label="Semaine suivante"
              className="px-2 sm:px-3"
              onClick={() => navigateWeek(addDays(weekStart, 7))}
            >
              <span className="hidden sm:inline">Suivante</span>
              <Icon icon={ArrowRight01Icon} size={15} />
            </Button>
          </div>

          <div className="inline-flex items-center gap-1 rounded-xl bg-zinc-100 p-1 dark:bg-zinc-800/80">
            <button
              type="button"
              aria-pressed={viewMode === 'agenda'}
              onClick={() => setViewMode('agenda')}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors',
                viewMode === 'agenda'
                  ? 'bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100'
                  : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200',
              )}
            >
              <Icon icon={LeftToRightListBulletIcon} size={14} />
              Agenda
            </button>
            <button
              type="button"
              aria-pressed={viewMode === 'grid'}
              onClick={() => {
                setViewMode('grid');
                setSelectedDayKey(null);
              }}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors',
                viewMode === 'grid'
                  ? 'bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100'
                  : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200',
              )}
            >
              <Icon icon={GridViewIcon} size={14} />
              Grille
            </button>
          </div>
        </div>

        {/* Ligne 2 : Charge planifiée & répartition par type */}
        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <span className="text-zinc-500 dark:text-zinc-400">Planifié : </span>
                <strong className="tabular-nums text-zinc-900 dark:text-zinc-100">
                  {summary.eventCount === 0 ? '0 min' : formatDuration(summary.totalMinutes)}
                </strong>
                <span className="ml-1 text-zinc-400 dark:text-zinc-500">
                  ({summary.eventCount} créneau{summary.eventCount > 1 ? 'x' : ''})
                </span>
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

            {categoryBreakdown.length > 0 && (
              <div className="hidden flex-wrap items-center gap-3 text-[11px] text-zinc-500 sm:flex dark:text-zinc-400">
                {categoryBreakdown.map(({ type, minutes }) => (
                  <span key={type} className="inline-flex items-center gap-1.5">
                    <span
                      aria-hidden="true"
                      className={cn('h-2 w-2 rounded-full', SCHEDULE_EVENT_TONE[type].dot)}
                    />
                    {SCHEDULE_EVENT_TYPE_META[type].label} ({formatDuration(minutes)})
                  </span>
                ))}
              </div>
            )}
          </div>

          {summary.totalMinutes > 0 && (
            <div className="flex h-1.5 w-full gap-0.5 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
              {categoryBreakdown.map(({ type, minutes }) => (
                <div
                  key={type}
                  className={cn('h-full rounded-full', SCHEDULE_EVENT_TONE[type].bar)}
                  style={{ width: `${(minutes / summary.totalMinutes) * 100}%` }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Ligne 3 : Bandeau interactif des 7 jours */}
        <div className="grid grid-cols-7 gap-1 sm:gap-1.5">
          {weekDays.map((day) => {
            const dayKey = toLocalDateKey(day);
            const isToday = dayKey === todayKey;
            const isSelected = selectedDayKey === dayKey;
            const dayEvents = getEventsForLocalDate(weekEvents, day);
            const hasDayConflict = dayEvents.some((ev) => conflictingIds.has(ev.id));
            const shortWeekday = new Intl.DateTimeFormat('fr-FR', { weekday: 'short' })
              .format(day)
              .replace('.', '');
            const weekdayLabel =
              shortWeekday.charAt(0).toUpperCase() + shortWeekday.slice(1, 3);

            return (
              <button
                key={dayKey}
                type="button"
                aria-pressed={isSelected}
                onClick={() => {
                  setViewMode('agenda');
                  setSelectedDayKey((prev) => (prev === dayKey ? null : dayKey));
                }}
                className={cn(
                  'flex min-w-0 flex-col items-center justify-center rounded-xl px-0.5 py-2 transition-colors',
                  isSelected
                    ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                    : isToday
                      ? 'bg-teal-50 text-teal-900 hover:bg-teal-100/80 dark:bg-teal-950/50 dark:text-teal-200 dark:hover:bg-teal-950/80'
                      : 'bg-zinc-50 text-zinc-700 hover:bg-zinc-100 dark:bg-zinc-800/70 dark:text-zinc-300 dark:hover:bg-zinc-800',
                )}
              >
                <span className="text-[10px] font-medium uppercase tracking-wide opacity-75">
                  {weekdayLabel}
                </span>
                <span className="mt-0.5 text-sm font-semibold tabular-nums">{day.getDate()}</span>
                <div className="mt-1 flex h-1.5 items-center gap-0.5">
                  {hasDayConflict ? (
                    <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-rose-500" />
                  ) : (
                    dayEvents.slice(0, 3).map((ev) => (
                      <span
                        key={ev.id}
                        aria-hidden="true"
                        className={cn(
                          'h-1.5 w-1.5 rounded-full',
                          isSelected
                            ? 'bg-white dark:bg-zinc-900'
                            : SCHEDULE_EVENT_TONE[ev.type].dot,
                        )}
                      />
                    ))
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Ligne 4 : Filtres par catégorie */}
        {(weekEvents.length > 0 || selectedDayKey !== null) && (
          <div className="flex items-center justify-between gap-2">
            <div className="no-scrollbar flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0">
              {weekEvents.length > 0 && (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setTypeFilter('all');
                      setConflictsOnly(false);
                    }}
                    className={cn(
                      'shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors',
                      typeFilter === 'all' && !conflictsOnly
                        ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                        : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700',
                    )}
                  >
                    Tous
                  </button>
                  {EVENT_TYPES.map((type) => {
                    const isActive = typeFilter === type;
                    return (
                      <button
                        key={type}
                        type="button"
                        onClick={() => {
                          setTypeFilter((prev) => (prev === type ? 'all' : type));
                          setConflictsOnly(false);
                        }}
                        className={cn(
                          'shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors',
                          isActive
                            ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                            : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700',
                        )}
                      >
                        {SCHEDULE_EVENT_TYPE_META[type].label}
                      </button>
                    );
                  })}
                  {summary.conflictCount > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        setConflictsOnly((prev) => !prev);
                        setTypeFilter('all');
                      }}
                      className={cn(
                        'shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors',
                        conflictsOnly
                          ? 'bg-rose-600 text-white dark:bg-rose-500'
                          : 'bg-rose-50 text-rose-700 hover:bg-rose-100 dark:bg-rose-950/50 dark:text-rose-300 dark:hover:bg-rose-950/80',
                      )}
                    >
                      Conflits
                    </button>
                  )}
                </>
              )}
            </div>

            {selectedDayKey && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setSelectedDayKey(null)}
              >
                Toute la semaine
              </Button>
            )}
          </div>
        )}
      </section>

      {/* Formulaire de création / édition */}
      {(isCreating || editingEvent) && (
        <section
          aria-label={editingEvent ? 'Modifier le créneau' : 'Nouveau créneau'}
          className="rounded-2xl bg-white p-5 dark:bg-zinc-900"
        >
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              {editingEvent ? 'Modifier le créneau' : 'Nouveau créneau'}
            </h2>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setIsCreating(false);
                setEditingEvent(null);
              }}
            >
              <Icon icon={Cancel01Icon} size={15} />
              Fermer
            </Button>
          </div>

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
        </section>
      )}

      {/* État vide global */}
      {scheduleEvents.length === 0 && !isCreating && !editingEvent && !isImportingTimetable && (
        <EmptyState
          icon={<Icon icon={Calendar03Icon} size={17} />}
          title="Planning vide"
          action={
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => handleOpenCreateForDate(toLocalDateKey(new Date()))}
              >
                Créer un premier créneau
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setIsImportingTimetable(true)}
              >
                Importer mon emploi du temps
              </Button>
            </div>
          }
        />
      )}

      {/* Vue Grille ou Agenda */}
      {viewMode === 'grid' ? (
        <WeekTimeGrid
          weekDays={weekDays}
          events={filteredWeekEvents}
          todayKey={todayKey}
          conflictingIds={conflictingIds}
          onAddForDate={handleOpenCreateForDate}
          onEditEvent={(event) => {
            setIsCreating(false);
            setEditingEvent(event);
          }}
        />
      ) : (typeFilter !== 'all' || conflictsOnly) &&
        weekEvents.length > 0 &&
        filteredWeekEvents.length === 0 ? (
        <EmptyState
          icon={<Icon icon={Calendar03Icon} size={17} />}
          title="Aucun créneau pour ce filtre"
          action={
            <Button type="button" variant="secondary" size="sm" onClick={resetFilters}>
              Réinitialiser les filtres
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {visibleDays.map((day) => {
            const dayKey = toLocalDateKey(day);
            const dayLabel = capitalizeFirst(formatDayHeaderFr(day));
            const dayEvents = getEventsForLocalDate(filteredWeekEvents, day);
            const isToday = dayKey === todayKey;

            if (dayEvents.length === 0) {
              return (
                <section
                  key={dayKey}
                  aria-label={dayLabel}
                  className={cn(
                    'flex items-center justify-between gap-3 rounded-2xl px-4 py-3',
                    isToday
                      ? 'bg-teal-50/70 dark:bg-teal-950/35'
                      : 'bg-white/80 dark:bg-zinc-900/70',
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {dayLabel}
                    </h2>
                    {isToday && <Badge variant="primary">Aujourd’hui</Badge>}
                    <span className="text-xs text-zinc-400 dark:text-zinc-500">Libre</span>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label={`Ajouter un créneau le ${dayLabel}`}
                    onClick={() => handleOpenCreateForDate(dayKey)}
                  >
                    <Icon icon={Add01Icon} size={14} />
                    Ajouter
                  </Button>
                </section>
              );
            }

            const dayMinutes = dayEvents.reduce(
              (acc, ev) => acc + getEventDurationMinutes(ev),
              0,
            );

            return (
              <section
                key={dayKey}
                aria-label={dayLabel}
                className={cn(
                  'rounded-2xl p-4 sm:p-5',
                  isToday ? 'bg-teal-50/50 dark:bg-teal-950/30' : 'bg-white dark:bg-zinc-900',
                )}
              >
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {dayLabel}
                    </h2>
                    {isToday && <Badge variant="primary">Aujourd’hui</Badge>}
                    <span className="text-xs text-zinc-500 dark:text-zinc-400">
                      {dayEvents.length} créneau{dayEvents.length > 1 ? 'x' : ''} ·{' '}
                      {formatDuration(dayMinutes)}
                    </span>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label={`Ajouter un créneau le ${dayLabel}`}
                    onClick={() => handleOpenCreateForDate(dayKey)}
                  >
                    <Icon icon={Add01Icon} size={14} />
                    Ajouter
                  </Button>
                </div>

                <ul className="space-y-2.5">
                  {dayEvents.map((event) => {
                    const typeMeta = SCHEDULE_EVENT_TYPE_META[event.type];
                    const tone = SCHEDULE_EVENT_TONE[event.type];
                    const hasConflict = conflictingIds.has(event.id);
                    const durationMinutes = getEventDurationMinutes(event);
                    const includeGroup =
                      Boolean(event.groupName) &&
                      !event.title.toLowerCase().includes((event.groupName ?? '').toLowerCase());
                    const metaSubtitle = [
                      event.room,
                      event.teacher,
                      includeGroup ? event.groupName : null,
                    ]
                      .filter(Boolean)
                      .join(' · ');
                    const cleanUserNote =
                      event.notes && !/^Type\s*:/i.test(event.notes.trim())
                        ? event.notes.trim()
                        : null;
                    const secondaryLine = [metaSubtitle, cleanUserNote].filter(Boolean).join(' · ');

                    return (
                      <li
                        key={event.id}
                        className="flex flex-col gap-3 rounded-xl bg-zinc-50/90 p-3.5 sm:flex-row sm:items-center sm:justify-between dark:bg-zinc-800/55"
                      >
                        <div className="flex min-w-0 items-stretch gap-3">
                          <div className="w-14 shrink-0 text-right tabular-nums">
                            <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                              {formatTimeFr(event.startsAt)}
                            </p>
                            <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                              {formatTimeFr(event.endsAt)}
                            </p>
                            <p className="mt-0.5 text-[10px] text-zinc-400 dark:text-zinc-500">
                              {formatDuration(durationMinutes)}
                            </p>
                          </div>

                          <span
                            aria-hidden="true"
                            className={cn(
                              'w-1 shrink-0 self-stretch rounded-full',
                              hasConflict ? 'bg-rose-500' : tone.bar,
                            )}
                          />

                          <div className="min-w-0 flex-1 space-y-0.5">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="line-clamp-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                                {event.title}
                              </h3>
                              <Badge variant={typeMeta.badgeVariant}>{typeMeta.label}</Badge>
                              {hasConflict && <Badge variant="danger">Conflit</Badge>}
                            </div>
                            {secondaryLine && (
                              <p className="line-clamp-1 text-xs text-zinc-500 dark:text-zinc-400">
                                {secondaryLine}
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="flex shrink-0 items-center gap-1.5 self-end sm:self-center">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setIsCreating(false);
                              setEditingEvent(event);
                            }}
                          >
                            <Icon icon={PencilEdit02Icon} size={14} />
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
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
