import { useMemo } from 'react';
import { Add01Icon } from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { formatDayHeaderFr, formatTimeFr, toLocalDateKey } from '../../lib/date';
import type { ScheduleEvent } from '../../types/domain';
import { getEventsForLocalDate, SCHEDULE_EVENT_TONE } from './scheduleUtils';

const HOUR_HEIGHT = 48;

export interface WeekTimeGridProps {
  weekDays: Date[];
  events: ScheduleEvent[];
  todayKey: string;
  conflictingIds: Set<string>;
  onAddForDate: (dateKey: string) => void;
  onEditEvent: (event: ScheduleEvent) => void;
}

function getLocalMinutes(iso: string): number {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return 0;
  }
  return date.getHours() * 60 + date.getMinutes();
}

function formatHourLabel(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`;
}

export function WeekTimeGrid({
  weekDays,
  events,
  todayKey,
  conflictingIds,
  onAddForDate,
  onEditEvent,
}: WeekTimeGridProps) {
  const { startHour, endHour } = useMemo(() => {
    let minHour = 7;
    let maxHour = 22;

    for (const event of events) {
      const startMin = getLocalMinutes(event.startsAt);
      const endMin = getLocalMinutes(event.endsAt);
      minHour = Math.min(minHour, Math.floor(startMin / 60));
      if (endMin > startMin) {
        maxHour = Math.max(maxHour, Math.ceil(endMin / 60));
      }
    }

    return {
      startHour: Math.max(0, minHour),
      endHour: Math.min(24, Math.max(minHour + 1, maxHour)),
    };
  }, [events]);

  const hours = useMemo(
    () => Array.from({ length: endHour - startHour }, (_, idx) => startHour + idx),
    [endHour, startHour],
  );
  const gridHeight = (endHour - startHour) * HOUR_HEIGHT;

  return (
    <section
      aria-label="Grille hebdomadaire"
      className="overflow-x-auto rounded-2xl bg-white p-4 dark:bg-zinc-900"
    >
      <div className="min-w-[700px]">
        {/* En-têtes des 7 jours */}
        <div className="mb-3 flex items-center gap-2">
          <div className="w-12 shrink-0" />
          <div className="grid flex-1 grid-cols-7 gap-1.5">
            {weekDays.map((day) => {
              const dayKey = toLocalDateKey(day);
              const isToday = dayKey === todayKey;
              const shortWeekday = new Intl.DateTimeFormat('fr-FR', { weekday: 'short' })
                .format(day)
                .replace('.', '');
              const capitalizedWeekday =
                shortWeekday.charAt(0).toUpperCase() + shortWeekday.slice(1);
              const fullDayLabel = formatDayHeaderFr(day);
              const capitalizedFullLabel =
                fullDayLabel.charAt(0).toUpperCase() + fullDayLabel.slice(1);

              return (
                <div
                  key={dayKey}
                  className={cn(
                    'flex items-center justify-between gap-1 rounded-xl px-2.5 py-1.5',
                    isToday
                      ? 'bg-teal-700 text-white dark:bg-teal-600'
                      : 'bg-zinc-50 text-zinc-800 dark:bg-zinc-800/70 dark:text-zinc-200',
                  )}
                >
                  <span className="truncate text-xs font-semibold">
                    {capitalizedWeekday} {day.getDate()}
                  </span>
                  <button
                    type="button"
                    aria-label={`Ajouter un créneau le ${capitalizedFullLabel}`}
                    onClick={() => onAddForDate(dayKey)}
                    className={cn(
                      'flex h-5 w-5 shrink-0 items-center justify-center rounded-lg transition-colors',
                      isToday
                        ? 'text-teal-100 hover:bg-teal-600 hover:text-white dark:hover:bg-teal-500'
                        : 'text-zinc-400 hover:bg-zinc-200 hover:text-zinc-700 dark:text-zinc-500 dark:hover:bg-zinc-700 dark:hover:text-zinc-200',
                    )}
                  >
                    <Icon icon={Add01Icon} size={13} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Corps horaire */}
        <div className="flex gap-2">
          {/* Colonne des heures */}
          <div className="relative w-12 shrink-0 select-none" style={{ height: `${gridHeight}px` }}>
            {hours.map((hour, index) => (
              <div
                key={hour}
                className="absolute right-1 text-right font-mono text-[11px] leading-none text-zinc-400 tabular-nums dark:text-zinc-500"
                style={{ top: `${index * HOUR_HEIGHT}px` }}
              >
                {formatHourLabel(hour)}
              </div>
            ))}
          </div>

          {/* 7 colonnes de créneaux */}
          <div className="grid flex-1 grid-cols-7 gap-1.5">
            {weekDays.map((day) => {
              const dayKey = toLocalDateKey(day);
              const isToday = dayKey === todayKey;
              const dayEvents = getEventsForLocalDate(events, day);

              return (
                <div
                  key={dayKey}
                  className={cn(
                    'relative overflow-hidden rounded-xl',
                    isToday
                      ? 'bg-teal-50/35 dark:bg-teal-950/20'
                      : 'bg-zinc-50/70 dark:bg-zinc-800/35',
                  )}
                  style={{ height: `${gridHeight}px` }}
                >
                  {/* Lignes de repère horaires sans bordure */}
                  {hours.map((hour, idx) => (
                    <div
                      key={hour}
                      aria-hidden="true"
                      className="pointer-events-none absolute inset-x-0 h-px bg-zinc-100 dark:bg-zinc-800/80"
                      style={{ top: `${idx * HOUR_HEIGHT}px` }}
                    />
                  ))}

                  {/* Créneaux positionnés */}
                  {dayEvents.map((event) => {
                    const startMinutes = getLocalMinutes(event.startsAt);
                    const rawEndMinutes = getLocalMinutes(event.endsAt);
                    const endMinutes =
                      rawEndMinutes > startMinutes ? rawEndMinutes : 24 * 60;
                    const offsetMinutes = Math.max(0, startMinutes - startHour * 60);
                    const durationMinutes = Math.max(15, endMinutes - startMinutes);

                    const topPx = (offsetMinutes / 60) * HOUR_HEIGHT;
                    const heightPx = Math.max(30, (durationMinutes / 60) * HOUR_HEIGHT);
                    const hasConflict = conflictingIds.has(event.id);
                    const tone = SCHEDULE_EVENT_TONE[event.type];

                    return (
                      <button
                        key={event.id}
                        type="button"
                        onClick={() => onEditEvent(event)}
                        style={{
                          top: `${topPx}px`,
                          height: `${heightPx}px`,
                        }}
                        className={cn(
                          'absolute inset-x-1 flex overflow-hidden rounded-xl p-1.5 text-left transition-opacity hover:opacity-90',
                          hasConflict
                            ? 'bg-rose-50/95 text-rose-950 dark:bg-rose-950/70 dark:text-rose-100'
                            : cn(tone.blockBg, tone.blockText),
                        )}
                      >
                        <span
                          aria-hidden="true"
                          className={cn(
                            'mr-1.5 w-1 shrink-0 self-stretch rounded-full',
                            hasConflict ? 'bg-rose-500' : tone.bar,
                          )}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-1">
                            <h3 className="truncate text-[11px] font-semibold leading-tight">
                              {event.title}
                            </h3>
                            {hasConflict && (
                              <Badge variant="danger" className="shrink-0 px-1 py-0 text-[9px]">
                                Conflit
                              </Badge>
                            )}
                          </div>
                          <p className="mt-0.5 truncate text-[10px] tabular-nums opacity-75">
                            {formatTimeFr(event.startsAt)} – {formatTimeFr(event.endsAt)}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
