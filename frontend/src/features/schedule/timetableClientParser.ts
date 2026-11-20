import { addDays, getMondayOfWeek, localDateAndTimeToIso, toLocalDateKey } from '../../lib/date';
import { generateId } from '../../lib/storage';
import type {
  CourseSessionSubtype,
  ExtractedCourseRow,
  ScheduleEvent,
  TimetableAnomaly,
  TimetableFileFormat,
  TimetableImport,
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

function matchDayInText(text: string): number | null {
  const lower = text.toLowerCase();
  if (/\b(lundi|lun)\b/.test(lower)) return 0;
  if (/\b(mardi|mar)\b/.test(lower)) return 1;
  if (/\b(mercredi|mer)\b/.test(lower)) return 2;
  if (/\b(jeudi|jeu)\b/.test(lower)) return 3;
  if (/\b(vendredi|ven)\b/.test(lower)) return 4;
  if (/\b(samedi|sam)\b/.test(lower)) return 5;
  if (/\b(dimanche|dim)\b/.test(lower)) return 6;
  return null;
}

function detectSessionSubtypeClient(text: string): CourseSessionSubtype {
  const lower = text.toLowerCase();
  if (/\b(examen|partiel|contr[ôo]le|ds)\b/.test(lower)) return 'examen';
  if (/\b(tp|travaux\s+pratiques|labo)\b/.test(lower)) return 'tp';
  if (/\b(td|travaux\s+dirig[ée]s)\b/.test(lower)) return 'td';
  return 'cours';
}

export function parseTextLinesToCoursesClient(rawText: string): ExtractedCourseRow[] {
  const lines = rawText
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  const rows: ExtractedCourseRow[] = [];
  let rowIndex = 1;
  let currentDay: number | null = null;

  for (const line of lines) {
    const dayInLine = matchDayInText(line);
    const timeMatch = line.match(
      /(\d{1,2}|\?\?)\s*[hH:.]\s*(\d{2}|\?\?)?\s*(?:-|–|—|à|a|\/)\s*(\d{1,2}|\?\?)\s*[hH:.]?\s*(\d{2}|\?\?)?/i,
    );
    const hasUnreadableHint = /\?\?|illisible/i.test(line);

    if (dayInLine !== null && !timeMatch && !hasUnreadableHint && line.length <= 15) {
      currentDay = dayInLine;
      continue;
    }

    if (!timeMatch && !hasUnreadableHint && dayInLine === null) {
      continue;
    }

    const effectiveDay = dayInLine !== null ? dayInLine : currentDay;
    if (dayInLine !== null) {
      currentDay = dayInLine;
    }

    let startTime: string | null = null;
    let endTime: string | null = null;
    let unreadableTime = false;

    if (timeMatch) {
      const h1 = timeMatch[1];
      const m1 = timeMatch[2] ?? '00';
      const h2 = timeMatch[3];
      const m2 = timeMatch[4] ?? '00';
      if (h1.includes('?') || m1.includes('?')) {
        unreadableTime = true;
      } else {
        startTime = `${h1.padStart(2, '0')}:${m1.padStart(2, '0')}`;
      }
      if (h2.includes('?') || m2.includes('?')) {
        unreadableTime = true;
      } else {
        endTime = `${h2.padStart(2, '0')}:${m2.padStart(2, '0')}`;
      }
    } else if (hasUnreadableHint) {
      unreadableTime = true;
    }

    const teacherMatch = line.match(
      /\b((?:Pr\.?|Prof\.?|Dr\.?|M\.|Mme)\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ\-]+(?:\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ\-]+)?)/,
    );
    const roomMatch = line.match(/\b((?:Salle|Amphi|Labo)\s+[A-Za-z0-9\-\.]+)/i);
    const groupMatch = line.match(/\b((?:Groupe|Classe|L[123]|M[12]|TD|TP)\s*[A-Za-z0-9\-]*)/i);

    let subject = line;
    if (timeMatch) subject = subject.replace(timeMatch[0], ' ');
    if (teacherMatch) subject = subject.replace(teacherMatch[0], ' ');
    if (roomMatch) subject = subject.replace(roomMatch[0], ' ');
    if (groupMatch) subject = subject.replace(groupMatch[0], ' ');
    subject = subject
      .replace(/\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|lun|mar|mer|jeu|ven|sam|dim)\b/gi, ' ')
      .replace(/(?:^|[\s\-|/[\]()]+)(?:CM|TD|TP|Cours|Examen|Partiel)(?:$|[\s\-|/[\]()]+)/gi, ' ')
      .replace(/[|;•]+/g, ' ')
      .replace(/(?:\s*[-–—:/,]+\s*)+$/g, '')
      .replace(/^(?:\s*[-–—:/,]+\s*)+/g, '')
      .replace(/\s{2,}/g, ' ')
      .trim();

    if (['?', '??', '???', 'illisible', 'inconnu'].includes(subject.toLowerCase())) {
      subject = '';
    }

    const uncertaintyReasons: string[] = [];
    if (unreadableTime || !startTime || !endTime) {
      uncertaintyReasons.push('Horaire manquant ou partiellement illisible.');
    }
    if (effectiveDay === null) {
      uncertaintyReasons.push('Jour de la semaine non identifié.');
    }
    if (!subject) {
      uncertaintyReasons.push('Matière non identifiée.');
    }

    rows.push({
      rowId: `row_${rowIndex++}`,
      subject,
      dayOfWeek: effectiveDay,
      dayLabel: effectiveDay !== null ? DAY_LABELS_FR[effectiveDay] : null,
      startTime,
      endTime,
      teacher: teacherMatch ? teacherMatch[1].trim() : null,
      room: roomMatch ? roomMatch[1].trim() : null,
      groupName: groupMatch ? groupMatch[1].trim() : null,
      sessionType: detectSessionSubtypeClient(line),
      validFrom: null,
      validUntil: null,
      uncertain: uncertaintyReasons.length > 0,
      uncertaintyReasons,
      ignored: false,
      rawExcerpt: line.slice(0, 220),
    });
  }

  return rows;
}

export async function parseLocalTimetableFile(
  file: File,
  existingEvents: ScheduleEvent[] = [],
  userId = 'local-user',
): Promise<TimetableImport> {
  const check = validateClientTimetableFile(file);
  if (!check.ok) {
    throw new Error(check.error);
  }

  let rawText = '';
  try {
    rawText = await file.text();
  } catch {
    rawText = '';
  }

  // En mode démo local, extrait les lignes lisibles du fichier (texte brut, flux PDF, XML ou CSV/TSV)
  const printableLines = rawText
    .replace(/[^\x20-\x7E\xA0-\xFF\r\n\t]/g, ' ')
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length >= 4);

  const joinedPreview = printableLines.join('\n').slice(0, 2500);
  const extractedCourses = parseTextLinesToCoursesClient(joinedPreview);
  const warnings: string[] = [];

  if (extractedCourses.length === 0) {
    warnings.push(
      'Aucun créneau horaire n’a pu être extrait automatiquement en mode local. Vous pouvez saisir ou compléter vos cours dans le tableau ci-dessous.',
    );
  }

  const anomalies = detectClientTimetableAnomalies(extractedCourses, existingEvents);
  const blockingCount = anomalies.filter((a) => a.severity === 'error').length;
  const nowIso = new Date().toISOString();

  return {
    id: generateId(),
    userId,
    filename: file.name,
    fileFormat: check.format,
    mimeType: file.type || 'application/octet-stream',
    fileSizeBytes: file.size,
    sourcePreviewText: joinedPreview || `[Aperçu ${file.name}]`,
    sourceDeleted: false,
    status: 'pending_review',
    validFrom: toLocalDateKey(getMondayOfWeek(new Date())),
    validUntil: toLocalDateKey(addDays(getMondayOfWeek(new Date()), 84)),
    extractedCourses,
    anomalies,
    warnings,
    blockingAnomaliesCount: blockingCount,
    createdEventsCount: 0,
    skippedDuplicatesCount: 0,
    replacedEventsCount: 0,
    createdAt: nowIso,
    updatedAt: nowIso,
    validatedAt: null,
  };
}
