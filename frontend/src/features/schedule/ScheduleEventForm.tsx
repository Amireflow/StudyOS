import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Alert02Icon, Clock01Icon } from '@hugeicons/core-free-icons';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import {
  formatTimeFr,
  isoToDateInput,
  isoToTimeInput,
  localDateAndTimeToIso,
} from '../../lib/date';
import { extractFieldErrors } from '../../lib/validation';
import type { ScheduleEvent, ScheduleEventType } from '../../types/domain';
import { formatDuration } from '../sessions/sessionUtils';
import { scheduleEventFormSchema, type ScheduleEventFormValues } from './scheduleSchema';
import { findConflictingEvents } from './scheduleUtils';

export interface ScheduleEventFormProps {
  initialEvent?: ScheduleEvent | null;
  defaultDate: string;
  existingEvents: ScheduleEvent[];
  onSubmit: (values: ScheduleEventFormValues) => void;
  onCancel: () => void;
}

type ScheduleField = keyof ScheduleEventFormValues;

const DURATION_PRESETS = [
  { minutes: 30, label: '30 min' },
  { minutes: 60, label: '1 h' },
  { minutes: 90, label: '1 h 30' },
  { minutes: 120, label: '2 h' },
];

function parseTimeToMinutes(value: string): number | null {
  const match = /^(\d{2}):(\d{2})$/.exec(value.trim());
  if (!match) return null;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) return null;
  return hours * 60 + minutes;
}

function addMinutesToTime(startTime: string, minutesToAdd: number): string {
  const base = parseTimeToMinutes(startTime);
  if (base === null) return startTime;
  const clamped = Math.min(23 * 60 + 59, base + minutesToAdd);
  const hours = String(Math.floor(clamped / 60)).padStart(2, '0');
  const minutes = String(clamped % 60).padStart(2, '0');
  return `${hours}:${minutes}`;
}

function diffTimeMinutes(startTime: string, endTime: string): number {
  const start = parseTimeToMinutes(startTime);
  const end = parseTimeToMinutes(endTime);
  if (start === null || end === null || end <= start) return 0;
  return end - start;
}

function getInitialValues(
  initialEvent: ScheduleEvent | null | undefined,
  defaultDate: string,
): ScheduleEventFormValues {
  if (initialEvent) {
    return {
      title: initialEvent.title,
      type: initialEvent.type,
      date: isoToDateInput(initialEvent.startsAt),
      startTime: isoToTimeInput(initialEvent.startsAt),
      endTime: isoToTimeInput(initialEvent.endsAt),
      notes: initialEvent.notes ?? '',
    };
  }

  return {
    title: '',
    type: 'course',
    date: defaultDate,
    startTime: '09:00',
    endTime: '11:00',
    notes: '',
  };
}

/**
 * Formulaire de création/modification de créneau avec détection de conflits
 * en temps réel avant enregistrement (SCHED-01, SCHED-03).
 */
export function ScheduleEventForm({
  initialEvent,
  defaultDate,
  existingEvents,
  onSubmit,
  onCancel,
}: ScheduleEventFormProps) {
  const [values, setValues] = useState<ScheduleEventFormValues>(() =>
    getInitialValues(initialEvent, defaultDate),
  );
  const [errors, setErrors] = useState<Partial<Record<ScheduleField, string>>>({});

  useEffect(() => {
    setValues(getInitialValues(initialEvent, defaultDate));
    setErrors({});
  }, [initialEvent, defaultDate]);

  const currentDurationMinutes = useMemo(
    () => diffTimeMinutes(values.startTime, values.endTime),
    [values.startTime, values.endTime],
  );

  const conflicts = useMemo(() => {
    if (!values.date || !values.startTime || !values.endTime || values.endTime <= values.startTime) {
      return [];
    }
    const startsAt = localDateAndTimeToIso(values.date, values.startTime);
    const endsAt = localDateAndTimeToIso(values.date, values.endTime);
    if (!startsAt || !endsAt) {
      return [];
    }
    return findConflictingEvents({ id: initialEvent?.id, startsAt, endsAt }, existingEvents);
  }, [values.date, values.startTime, values.endTime, initialEvent?.id, existingEvents]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = scheduleEventFormSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(extractFieldErrors<ScheduleField>(parsed.error));
      return;
    }

    setErrors({});
    onSubmit(parsed.data);
  };

  const submitLabel =
    conflicts.length > 0
      ? 'Enregistrer malgré le conflit'
      : initialEvent
        ? 'Enregistrer les modifications'
        : 'Ajouter le créneau';

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField id="schedule-title" label="Titre" required error={errors.title}>
          <Input
            id="schedule-title"
            value={values.title}
            hasError={Boolean(errors.title)}
            placeholder="Ex. Cours de systèmes d’exploitation"
            onChange={(e) => {
              setValues((prev) => ({ ...prev, title: e.target.value }));
              if (errors.title) {
                setErrors((prev) => ({ ...prev, title: undefined }));
              }
            }}
          />
        </FormField>

        <FormField id="schedule-type" label="Type" error={errors.type}>
          <Select
            id="schedule-type"
            value={values.type}
            onChange={(e) =>
              setValues((prev) => ({ ...prev, type: e.target.value as ScheduleEventType }))
            }
          >
            <option value="course">Cours</option>
            <option value="learning">Apprentissage</option>
            <option value="project">Projet</option>
            <option value="personal">Personnel</option>
            <option value="other">Autre</option>
          </Select>
        </FormField>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <FormField id="schedule-date" label="Date" required error={errors.date}>
          <Input
            id="schedule-date"
            type="date"
            value={values.date}
            hasError={Boolean(errors.date)}
            onChange={(e) => {
              setValues((prev) => ({ ...prev, date: e.target.value }));
              if (errors.date) {
                setErrors((prev) => ({ ...prev, date: undefined }));
              }
            }}
          />
        </FormField>

        <FormField id="schedule-start-time" label="Début" required error={errors.startTime}>
          <Input
            id="schedule-start-time"
            type="time"
            value={values.startTime}
            hasError={Boolean(errors.startTime)}
            onChange={(e) => {
              setValues((prev) => ({ ...prev, startTime: e.target.value }));
              if (errors.startTime) {
                setErrors((prev) => ({ ...prev, startTime: undefined }));
              }
            }}
          />
        </FormField>

        <FormField id="schedule-end-time" label="Fin" required error={errors.endTime}>
          <Input
            id="schedule-end-time"
            type="time"
            value={values.endTime}
            hasError={Boolean(errors.endTime)}
            onChange={(e) => {
              setValues((prev) => ({ ...prev, endTime: e.target.value }));
              if (errors.endTime) {
                setErrors((prev) => ({ ...prev, endTime: undefined }));
              }
            }}
          />
        </FormField>
      </div>

      {/* Raccourcis de durée */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-zinc-50 px-3 py-2 dark:bg-zinc-800/70">
        <div className="flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-300">
          <Icon icon={Clock01Icon} size={14} className="text-zinc-400 dark:text-zinc-500" />
          <span>
            {currentDurationMinutes > 0
              ? `Durée : ${formatDuration(currentDurationMinutes)}`
              : 'Raccourcis de durée'}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {DURATION_PRESETS.map((preset) => {
            const isActive = currentDurationMinutes === preset.minutes;
            return (
              <button
                key={preset.minutes}
                type="button"
                onClick={() => {
                  const nextEndTime = addMinutesToTime(values.startTime, preset.minutes);
                  setValues((prev) => ({ ...prev, endTime: nextEndTime }));
                  if (errors.endTime) {
                    setErrors((prev) => ({ ...prev, endTime: undefined }));
                  }
                }}
                className={cn(
                  'rounded-full px-2.5 py-1 text-xs font-medium transition-colors',
                  isActive
                    ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                    : 'bg-white text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-700',
                )}
              >
                {preset.label}
              </button>
            );
          })}
        </div>
      </div>

      {conflicts.length > 0 && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl bg-amber-50 px-4 py-3 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200"
        >
          <Icon
            icon={Alert02Icon}
            size={18}
            className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400"
          />
          <div className="space-y-1 text-xs">
            <p className="font-semibold">
              Conflit horaire détecté ({conflicts.length}) :
            </p>
            <ul className="list-disc pl-4 text-amber-800 dark:text-amber-300">
              {conflicts.map((conflict) => (
                <li key={conflict.id}>
                  <strong>{conflict.title}</strong> ({formatTimeFr(conflict.startsAt)} –{' '}
                  {formatTimeFr(conflict.endsAt)})
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <FormField id="schedule-notes" label="Notes" error={errors.notes}>
        <Textarea
          id="schedule-notes"
          rows={2}
          value={values.notes ?? ''}
          hasError={Boolean(errors.notes)}
          placeholder="Salle, lien de cours ou objectif du créneau (facultatif)"
          onChange={(e) => setValues((prev) => ({ ...prev, notes: e.target.value }))}
        />
      </FormField>

      <div className="flex flex-wrap justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" variant="primary">
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
