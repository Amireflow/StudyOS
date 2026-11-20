import { addDays, getMondayOfWeek, localDateAndTimeToIso, toLocalDateKey } from '../../lib/date';
import type {
  CourseSessionSubtype,
  ExtractedCourseRow,
  ScheduleEvent,
  TimetableAnomaly,
  TimetableFileFormat,
} from '../../types/domain';
import { doEventsOverlap } from './scheduleUtils';

export const MAX_TIMETABLE_FILE_BYTES = 10 * 1024 * 1024; // 10 Mo

export const DAY_LABELS_FR: Record<number, string> = {
  0: 'Lundi',
  1: 'Mardi',
  2: 'Mercredi',
  3: 'Jeudi',
  4: 'Vendredi',
  5: 'Samedi',
  6: 'Dimanche',
};

export const SUBTYPE_LABELS_FR: Record<CourseSessionSubtype, string> = {
  cours: 'Cours',
  td: 'TD',
  tp: 'TP',
  examen: 'Examen',
  autre: 'Autre',
};

const EXTENSION_TO_FORMAT: Record<string, TimetableFileFormat> = {
  '.pdf': 'pdf',
  '.png': 'image',
  '.jpg': 'image',
  '.jpeg': 'image',
  '.webp': 'image',
  '.xlsx': 'excel',
  '.xls': 'excel',
  '.docx': 'word',
};

export function validateClientTimetableFile(
  file: File,
  maxBytes = MAX_TIMETABLE_FILE_BYTES,
): { ok: true; format: TimetableFileFormat } | { ok: false; error: string } {
  const name = (file.name || '').trim();
  if (!name) {
    return { ok: false, error: 'Le nom du fichier est manquant.' };
  }
  if (file.size === 0) {
    return { ok: false, error: 'Le fichier sélectionné est vide.' };
  }
  if (file.size > maxBytes) {
    const maxMb = Math.round(maxBytes / (1024 * 1024));
    return {
      ok: false,
      error: `Le fichier dépasse la taille maximale autorisée (${maxMb} Mo).`,
    };
  }

  const lower = name.toLowerCase();
  const ext = lower.includes('.') ? `.${lower.split('.').pop()}` : '';
  const format = EXTENSION_TO_FORMAT[ext];
  if (!format) {
    return {
      ok: false,
      error:
        'Format non pris en charge. Formats acceptés : PDF (.pdf), Images (.png, .jpg, .jpeg, .webp), Excel (.xlsx, .xls) et Word (.docx).',
    };
  }
  return { ok: true, format };
}

function timeToMinutes(value: string | null): number | null {
  if (!value || !/^\d{2}:\d{2}$/.test(value)) {
    return null;
  }
  const [hStr, mStr] = value.split(':');
  const h = Number(hStr);
  const m = Number(mStr);
  if (Number.isNaN(h) || Number.isNaN(m) || h < 0 || h > 23 || m < 0 || m > 59) {
    return null;
  }
  return h * 60 + m;
}

export function detectClientTimetableAnomalies(
  courses: ExtractedCourseRow[],
  existingEvents: ScheduleEvent[] = [],
  targetWeekStart?: string,
): TimetableAnomaly[] {
  const anomalies: TimetableAnomaly[] = [];
  const activeRows = courses.filter((row) => !row.ignored);
  let counter = 1;

  const pushAnomaly = (
    type: TimetableAnomaly['type'],
    severity: 'error' | 'warning',
    message: string,
    rowId: string | null = null,
    relatedRowId: string | null = null,
  ) => {
    anomalies.push({
      id: `anom_${counter++}`,
      rowId,
      relatedRowId,
      type,
      severity,
      message,
    });
  };

  const validTimed: Array<{ row: ExtractedCourseRow; startMin: number; endMin: number }> = [];

  for (const row of activeRows) {
    const label = row.subject.trim() || `Ligne ${row.rowId}`;
    if (row.subject.trim().length < 2) {
      pushAnomaly(
        'missing_subject',
        'error',
        `Matière non identifiée sur la ligne (${row.rawExcerpt || row.rowId}).`,
        row.rowId,
      );
    }

    const startMin = timeToMinutes(row.startTime);
    const endMin = timeToMinutes(row.endTime);

    if (row.dayOfWeek === null || row.dayOfWeek < 0 || row.dayOfWeek > 6) {
      pushAnomaly(
        'missing_time',
        'error',
        `Jour de la semaine manquant ou illisible pour « ${label} ».`,
        row.rowId,
      );
    }

    if (startMin === null || endMin === null) {
      pushAnomaly(
        'missing_time',
        'error',
        `Horaire de début ou de fin manquant/illisible pour « ${label} ».`,
        row.rowId,
      );
    } else if (endMin <= startMin) {
      pushAnomaly(
        'invalid_duration',
        'error',
        `Durée invalide pour « ${label} » (${row.startTime} – ${row.endTime}) : la fin doit être postérieure au début.`,
        row.rowId,
      );
    } else if (endMin - startMin < 15 || endMin - startMin > 600) {
      pushAnomaly(
        'invalid_duration',
        'error',
        `Durée atypique ou invalide pour « ${label} » (${endMin - startMin} min).`,
        row.rowId,
      );
    } else if (row.dayOfWeek !== null && row.dayOfWeek >= 0 && row.dayOfWeek <= 6) {
      validTimed.push({ row, startMin, endMin });
    }

    if (row.uncertain && startMin !== null && endMin !== null && row.subject.trim().length >= 2) {
      pushAnomaly(
        'uncertain_extraction',
        'warning',
        `Information à vérifier sur « ${label} » : ${row.uncertaintyReasons.join(' ') || 'Extraction partiellement ambiguë.'}`,
        row.rowId,
      );
    }
  }

  for (let i = 0; i < validTimed.length; i += 1) {
    const a = validTimed[i];
    const dayName = DAY_LABELS_FR[a.row.dayOfWeek ?? 0] ?? 'Jour';
    for (let j = i + 1; j < validTimed.length; j += 1) {
      const b = validTimed[j];
      if (a.row.dayOfWeek !== b.row.dayOfWeek) {
        continue;
      }
      const sameSubject =
        a.row.subject.trim().toLowerCase() === b.row.subject.trim().toLowerCase() &&
        a.row.subject.trim().length > 0;
      if (sameSubject && a.startMin === b.startMin && a.endMin === b.endMin) {
        pushAnomaly(
          'duplicate_course',
          'warning',
          `Doublon possible détecté le ${dayName} (${a.row.startTime}–${a.row.endTime}) pour « ${a.row.subject} ».`,
          b.row.rowId,
          a.row.rowId,
        );
      } else if (a.startMin < b.endMin && b.startMin < a.endMin) {
        pushAnomaly(
          'overlap_conflict',
          'warning',
          `Chevauchement horaire le ${dayName} entre « ${a.row.subject || a.row.rowId} » (${a.row.startTime}–${a.row.endTime}) et « ${b.row.subject || b.row.rowId} » (${b.row.startTime}–${b.row.endTime}).`,
          b.row.rowId,
          a.row.rowId,
        );
      }
    }
  }

  if (existingEvents.length > 0) {
    const monday = targetWeekStart
      ? getMondayOfWeek(new Date(`${targetWeekStart}T12:00:00`))
      : getMondayOfWeek(new Date());

    for (const item of validTimed) {
      const dayOffset = item.row.dayOfWeek ?? 0;
      const dateStr = toLocalDateKey(addDays(monday, dayOffset));
      const candidateStartIso = localDateAndTimeToIso(dateStr, item.row.startTime!);
      const candidateEndIso = localDateAndTimeToIso(dateStr, item.row.endTime!);

      for (const ev of existingEvents) {
        if (doEventsOverlap(candidateStartIso, candidateEndIso, ev.startsAt, ev.endsAt)) {
          if (
            ev.title.toLowerCase().includes(item.row.subject.trim().toLowerCase()) &&
            ev.startsAt === candidateStartIso &&
            ev.endsAt === candidateEndIso
          ) {
            continue;
          }
          pushAnomaly(
            'existing_calendar_conflict',
            'warning',
            `Chevauchement avec le créneau existant « ${ev.title} » le ${DAY_LABELS_FR[dayOffset]}.`,
            item.row.rowId,
          );
          break;
        }
      }
    }
  }

  return anomalies;
}

