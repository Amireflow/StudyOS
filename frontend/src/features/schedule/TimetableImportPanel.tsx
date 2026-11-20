import { useEffect, useMemo, useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import {
  Add01Icon,
  Alert02Icon,
  Calendar03Icon,
  Cancel01Icon,
  CheckmarkCircle02Icon,
  Delete02Icon,
  File02Icon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { toLocalDateKey } from '../../lib/date';
import { generateId } from '../../lib/storage';
import { useStudyStore } from '../../state/StudyStoreContext';
import type {
  CourseSessionSubtype,
  ExtractedCourseRow,
  TimetableImport,
  TimetableImportConfirmResult,
} from '../../types/domain';
import {
  DAY_LABELS_FR,
  detectClientTimetableAnomalies,
  SUBTYPE_LABELS_FR,
  validateClientTimetableFile,
} from './timetableClientParser';

export interface TimetableImportPanelProps {
  weekStart: Date;
  onClose: () => void;
  onImportSuccess: (result: TimetableImportConfirmResult) => void;
  onImportCancelled: () => void;
}

const ACCEPTED_EXTENSIONS_ATTR = '.pdf,.png,.jpg,.jpeg,.webp,.xlsx,.xls,.docx';

const FORMAT_LABELS: Record<string, string> = {
  pdf: 'PDF (.pdf)',
  image: 'Image (.png, .jpg, .webp)',
  excel: 'Excel (.xlsx, .xls)',
  word: 'Word (.docx)',
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} Mo`;
}

export function TimetableImportPanel({
  weekStart,
  onClose,
  onImportSuccess,
  onImportCancelled,
}: TimetableImportPanelProps) {
  const {
    scheduleEvents,
    analyzeTimetableFile,
    updateTimetableImportDraft,
    confirmTimetableImport,
    cancelTimetableImport,
    deleteTimetableImportSource,
  } = useStudyStore();

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [draftNotice, setDraftNotice] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (imagePreviewUrl && typeof URL !== 'undefined' && URL.revokeObjectURL) {
        URL.revokeObjectURL(imagePreviewUrl);
      }
    };
  }, [imagePreviewUrl]);

  const [importSession, setImportSession] = useState<TimetableImport | null>(null);
  const [courses, setCourses] = useState<ExtractedCourseRow[]>([]);
  const [validFrom, setValidFrom] = useState<string>(() => toLocalDateKey(weekStart));
  const [validUntil, setValidUntil] = useState<string>('');
  const [recurrenceWeeks, setRecurrenceWeeks] = useState<number>(1);
  const [replaceExistingImported, setReplaceExistingImported] = useState<boolean>(false);

  const liveAnomalies = useMemo(() => {
    if (!importSession) return [];
    return detectClientTimetableAnomalies(
      courses,
      scheduleEvents,
      toLocalDateKey(weekStart),
    );
  }, [courses, importSession, scheduleEvents, weekStart]);

  const blockingAnomalies = useMemo(
    () => liveAnomalies.filter((a) => a.severity === 'error'),
    [liveAnomalies],
  );
  const warningAnomalies = useMemo(
    () => liveAnomalies.filter((a) => a.severity === 'warning'),
    [liveAnomalies],
  );
  const activeCoursesCount = useMemo(
    () => courses.filter((c) => !c.ignored).length,
    [courses],
  );

  const handleProcessFile = async (file: File) => {
    setLocalError(null);
    const check = validateClientTimetableFile(file);
    if (!check.ok) {
      setLocalError(check.error);
      return;
    }

    if (check.format === 'image' && typeof URL !== 'undefined' && URL.createObjectURL) {
      try {
        setImagePreviewUrl(URL.createObjectURL(file));
      } catch {
        setImagePreviewUrl(null);
      }
    } else {
      setImagePreviewUrl(null);
    }

    setIsAnalyzing(true);
    setAnalysisStep(35);
    const analyzed = await analyzeTimetableFile(file);
    setAnalysisStep(100);
    setIsAnalyzing(false);

    if (!analyzed) {
      setLocalError(
        'L’analyse du document a échoué. Vérifiez que le fichier n’est pas corrompu ou protégé par mot de passe.',
      );
      return;
    }

    setImportSession(analyzed);
    setCourses(analyzed.extractedCourses);
    setValidFrom(analyzed.validFrom ?? toLocalDateKey(weekStart));
    setValidUntil(analyzed.validUntil ?? '');
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      void handleProcessFile(file);
    }
    event.target.value = '';
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) {
      void handleProcessFile(file);
    }
  };

  const updateRow = (rowId: string, patch: Partial<ExtractedCourseRow>) => {
    setCourses((prev) =>
      prev.map((row) => {
        if (row.rowId !== rowId) return row;
        const next = { ...row, ...patch };
        if ('dayOfWeek' in patch) {
          next.dayLabel =
            next.dayOfWeek !== null && next.dayOfWeek !== undefined
              ? (DAY_LABELS_FR[next.dayOfWeek] ?? null)
              : null;
        }
        if (
          next.subject.trim().length >= 2 &&
          next.dayOfWeek !== null &&
          next.startTime &&
          next.endTime &&
          next.endTime > next.startTime
        ) {
          next.uncertain = false;
          next.uncertaintyReasons = [];
        }
        return next;
      }),
    );
  };

  const handleAddRow = () => {
    const newRow: ExtractedCourseRow = {
      rowId: `row_${generateId().slice(0, 8)}`,
      subject: '',
      dayOfWeek: 0,
      dayLabel: 'Lundi',
      startTime: '08:00',
      endTime: '10:00',
      teacher: null,
      room: null,
      groupName: null,
      sessionType: 'cours',
      validFrom: validFrom || null,
      validUntil: validUntil || null,
      uncertain: false,
      uncertaintyReasons: [],
      ignored: false,
      rawExcerpt: 'Ajouté manuellement',
    };
    setCourses((prev) => [...prev, newRow]);
  };

  const handleRemoveRow = (rowId: string) => {
    setCourses((prev) => prev.filter((row) => row.rowId !== rowId));
  };

  const handleDeleteSourcePreview = async () => {
    if (!importSession) return;
    const ok = await deleteTimetableImportSource(importSession.id);
    if (ok) {
      setImportSession((prev) =>
        prev ? { ...prev, sourcePreviewText: null, sourceDeleted: true } : null,
      );
      setImagePreviewUrl(null);
    }
  };

  const handleCancelImport = async () => {
    if (importSession) {
      await cancelTimetableImport(importSession.id);
    }
    onImportCancelled();
  };

  const handleSaveDraft = async () => {
    if (!importSession) return;
    setLocalError(null);
    setDraftNotice(null);
    setIsSavingDraft(true);
    const updated = await updateTimetableImportDraft(importSession, {
      courses,
      validFrom: validFrom || null,
      validUntil: validUntil || null,
    });
    setIsSavingDraft(false);
    if (updated) {
      setImportSession(updated);
      setCourses(updated.extractedCourses);
      setDraftNotice('Brouillon de corrections enregistré.');
    }
  };

  const handleConfirmImport = async () => {
    if (!importSession) return;
    setLocalError(null);

    if (activeCoursesCount === 0) {
      setLocalError('Aucun cours actif à enregistrer. Activez ou ajoutez au moins une ligne.');
      return;
    }

    if (blockingAnomalies.length > 0) {
      setLocalError(
        `Veuillez corriger ou ignorer les lignes comportant une anomalie bloquante : ${blockingAnomalies[0].message}`,
      );
      return;
    }

    setIsSubmitting(true);
    const result = await confirmTimetableImport(importSession, {
      courses,
      validFrom: validFrom || null,
      validUntil: validUntil || null,
      targetWeekStart: toLocalDateKey(weekStart),
      recurrenceWeeks,
      replaceExistingImported,
    });
    setIsSubmitting(false);

    if (result) {
      onImportSuccess(result);
    }
  };

  return (
    <section
      aria-label="Importer mon emploi du temps"
      className="space-y-4 rounded-2xl bg-white p-4 sm:space-y-5 sm:p-5 dark:bg-zinc-900"
    >
      {/* En-tête du panneau */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-teal-50 text-teal-700 dark:bg-teal-950/70 dark:text-teal-300">
            <Icon icon={Calendar03Icon} size={17} />
          </span>
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
            Importer mon emploi du temps
          </h2>
        </div>

        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          <Icon icon={Cancel01Icon} size={15} />
          Fermer
        </Button>
      </div>

      {localError && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl bg-rose-50/90 p-3 text-xs text-rose-800 dark:bg-rose-950/50 dark:text-rose-200"
        >
          <Icon icon={Alert02Icon} size={16} className="mt-0.5 shrink-0 text-rose-600 dark:text-rose-400" />
          <p className="flex-1">{localError}</p>
        </div>
      )}

      {/* Étape 1 : Zone de glisser-déposer et sélection de fichier */}
      {!importSession && !isAnalyzing && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={cn(
            'flex flex-col items-center justify-center rounded-2xl p-6 text-center transition-colors',
            isDragging
              ? 'bg-teal-50/80 dark:bg-teal-950/40'
              : 'bg-zinc-50/80 hover:bg-zinc-100/80 dark:bg-zinc-800/50 dark:hover:bg-zinc-800',
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS_ATTR}
            onChange={handleFileChange}
            aria-label="Fichier d'emploi du temps"
            data-testid="timetable-file-input"
            className="sr-only"
          />

          <div className="mb-2.5 flex h-11 w-11 items-center justify-center rounded-2xl bg-teal-100/80 text-teal-800 dark:bg-teal-950/80 dark:text-teal-300">
            <Icon icon={File02Icon} size={20} />
          </div>

          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Glissez-déposez votre fichier ici
          </p>

          <div className="mt-3">
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
            >
              Sélectionner un fichier
            </Button>
          </div>

          <div className="mt-3.5 flex flex-wrap items-center justify-center gap-1.5 text-[11px] text-zinc-500 dark:text-zinc-400">
            <Badge variant="neutral">PDF</Badge>
            <Badge variant="neutral">Image</Badge>
            <Badge variant="neutral">Excel</Badge>
            <Badge variant="neutral">Word</Badge>
            <span>· 10 Mo max</span>
          </div>
        </div>
      )}

      {/* État d'analyse en cours avec indicateur de progression */}
      {isAnalyzing && (
        <div
          role="status"
          aria-live="polite"
          className="space-y-2.5 rounded-2xl bg-zinc-50 p-5 text-center dark:bg-zinc-800/60"
        >
          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Analyse en cours…
          </p>
          <div className="mx-auto h-2 w-full max-w-md overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
            <div
              className="h-full rounded-full bg-teal-600 transition-all duration-300 dark:bg-teal-400"
              style={{ width: `${analysisStep}%` }}
            />
          </div>
        </div>
      )}

      {/* Étape 2 : Aperçu du document, anomalies et tableau modifiable */}
      {importSession && !isAnalyzing && (
        <div className="space-y-5">
          {/* Carte d'aperçu du document importé et paramètres de validité */}
          <div className="grid gap-4 rounded-xl bg-zinc-50 p-4 lg:grid-cols-2 dark:bg-zinc-800/60">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="primary">
                    {FORMAT_LABELS[importSession.fileFormat] ?? importSession.fileFormat.toUpperCase()}
                  </Badge>
                  <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                    {importSession.filename}
                  </span>
                  <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    ({formatFileSize(importSession.fileSizeBytes)})
                  </span>
                </div>

                <div className="flex items-center gap-1.5">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setImportSession(null);
                      setCourses([]);
                      setLocalError(null);
                    }}
                  >
                    Changer de fichier
                  </Button>
                  {!importSession.sourceDeleted && importSession.sourcePreviewText && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => void handleDeleteSourcePreview()}
                    >
                      Supprimer l’aperçu source
                    </Button>
                  )}
                </div>
              </div>

              {imagePreviewUrl && (
                <div className="overflow-hidden rounded-lg bg-white p-2 dark:bg-zinc-900">
                  <img
                    src={imagePreviewUrl}
                    alt={`Aperçu de ${importSession.filename}`}
                    className="max-h-36 w-auto rounded object-contain"
                  />
                </div>
              )}

              {importSession.sourceDeleted ? (
                <p className="text-[11px] italic text-zinc-500 dark:text-zinc-400">
                  Aperçu source supprimé.
                </p>
              ) : (
                importSession.sourcePreviewText && (
                  <div className="max-h-24 overflow-y-auto rounded-lg bg-white p-2 font-mono text-[11px] leading-relaxed text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                    <pre className="whitespace-pre-wrap break-words">
                      {importSession.sourcePreviewText}
                    </pre>
                  </div>
                )
              )}
            </div>

            {/* Dates de validité, récurrence et option de remplacement */}
            <div className="space-y-3 rounded-xl bg-white p-3.5 dark:bg-zinc-900">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <label className="block space-y-1 text-xs">
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">
                    Début de validité
                  </span>
                  <input
                    type="date"
                    aria-label="Début de validité"
                    value={validFrom}
                    onChange={(e) => setValidFrom(e.target.value)}
                    className="w-full rounded-lg bg-zinc-100/80 px-2.5 py-1.5 text-xs text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                  />
                </label>

                <label className="block space-y-1 text-xs">
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">
                    Fin de validité
                  </span>
                  <input
                    type="date"
                    aria-label="Fin de validité"
                    value={validUntil}
                    onChange={(e) => setValidUntil(e.target.value)}
                    className="w-full rounded-lg bg-zinc-100/80 px-2.5 py-1.5 text-xs text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                  />
                </label>

                <label className="block space-y-1 text-xs">
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">
                    Semaines à générer
                  </span>
                  <select
                    aria-label="Semaines à générer"
                    value={recurrenceWeeks}
                    onChange={(e) => setRecurrenceWeeks(Number(e.target.value))}
                    className="w-full rounded-lg bg-zinc-100/80 px-2.5 py-1.5 text-xs text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                  >
                    <option value={1}>1 semaine</option>
                    <option value={2}>2 semaines</option>
                    <option value={4}>4 semaines</option>
                    <option value={8}>8 semaines</option>
                    <option value={12}>12 semaines</option>
                  </select>
                </label>
              </div>

              <label className="flex items-center gap-2 pt-1 text-xs text-zinc-700 dark:text-zinc-300">
                <input
                  type="checkbox"
                  checked={replaceExistingImported}
                  onChange={(e) => setReplaceExistingImported(e.target.checked)}
                  className="rounded accent-teal-600"
                />
                <span>Remplacer l’emploi du temps importé précédent</span>
              </label>
            </div>
          </div>

          {/* Avertissements généraux d'extraction */}
          {importSession.warnings.length > 0 && (
            <div className="rounded-xl bg-amber-50/80 p-3 text-xs text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              {importSession.warnings.map((w, idx) => (
                <p key={idx}>{w}</p>
              ))}
            </div>
          )}

          {/* Panneau des anomalies et conflits détectés en temps réel */}
          {liveAnomalies.length > 0 ? (
            <div
              role="region"
              aria-label="Anomalies détectées"
              data-testid="timetable-anomalies-panel"
              className={cn(
                'space-y-1.5 rounded-xl p-3 text-xs',
                blockingAnomalies.length > 0
                  ? 'bg-rose-50/80 text-rose-900 dark:bg-rose-950/40 dark:text-rose-200'
                  : 'bg-amber-50/80 text-amber-900 dark:bg-amber-950/40 dark:text-amber-200',
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold">
                  {blockingAnomalies.length > 0
                    ? `${blockingAnomalies.length} anomalie(s) à corriger`
                    : `${warningAnomalies.length} avertissement(s)`}
                </p>
                <div className="flex items-center gap-1.5">
                  {blockingAnomalies.length > 0 && (
                    <Badge variant="danger">{blockingAnomalies.length} erreur(s)</Badge>
                  )}
                  {warningAnomalies.length > 0 && (
                    <Badge variant="warning">{warningAnomalies.length} alerte(s)</Badge>
                  )}
                </div>
              </div>
              <ul className="list-inside list-disc space-y-0.5">
                {liveAnomalies.map((anom) => (
                  <li key={anom.id}>{anom.message}</li>
                ))}
              </ul>
            </div>
          ) : (
            activeCoursesCount > 0 && (
              <div className="flex items-center gap-2 rounded-xl bg-emerald-50/80 px-3 py-2 text-xs text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
                <Icon icon={CheckmarkCircle02Icon} size={15} className="text-emerald-600 dark:text-emerald-400" />
                <strong>{activeCoursesCount} cours prêts à enregistrer</strong>
              </div>
            )
          )}

          {/* Tableau modifiable des cours détectés */}
          <div className="space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Cours détectés ({activeCoursesCount}/{courses.length})
              </h3>
              <Button type="button" variant="secondary" size="sm" onClick={handleAddRow}>
                <Icon icon={Add01Icon} size={14} />
                Ajouter un cours
              </Button>
            </div>

            <div className="overflow-x-auto rounded-xl bg-zinc-50 dark:bg-zinc-800/60">
              <table className="w-full min-w-[820px] text-left text-xs">
                <thead>
                  <tr className="bg-zinc-100/90 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                    <th className="px-2.5 py-2.5">Inclure</th>
                    <th className="px-2.5 py-2.5">Matière *</th>
                    <th className="px-2.5 py-2.5">Type</th>
                    <th className="px-2.5 py-2.5">Jour *</th>
                    <th className="px-2.5 py-2.5">Début *</th>
                    <th className="px-2.5 py-2.5">Fin *</th>
                    <th className="px-2.5 py-2.5">Enseignant</th>
                    <th className="px-2.5 py-2.5">Salle</th>
                    <th className="px-2.5 py-2.5">Groupe</th>
                    <th className="px-2.5 py-2.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {courses.map((row, idx) => {
                    const rowAnomalies = liveAnomalies.filter((a) => a.rowId === row.rowId);
                    const hasRowError = rowAnomalies.some((a) => a.severity === 'error');
                    const hasRowWarning = rowAnomalies.some((a) => a.severity === 'warning');

                    return (
                      <tr
                        key={row.rowId}
                        data-testid={`timetable-course-row-${idx}`}
                        className={cn(
                          'transition-colors',
                          row.ignored
                            ? 'bg-zinc-50/60 opacity-50 dark:bg-zinc-900/40'
                            : hasRowError
                              ? 'bg-rose-50/40 dark:bg-rose-950/20'
                              : hasRowWarning
                                ? 'bg-amber-50/30 dark:bg-amber-950/15'
                                : 'bg-white dark:bg-zinc-900',
                        )}
                      >
                        <td className="px-2.5 py-2">
                          <input
                            type="checkbox"
                            aria-label={`Inclure la ligne ${idx + 1}`}
                            checked={!row.ignored}
                            onChange={(e) => updateRow(row.rowId, { ignored: !e.target.checked })}
                            className="rounded accent-teal-600"
                          />
                        </td>

                        <td className="px-2.5 py-2">
                          <input
                            type="text"
                            aria-label={`Matière ligne ${idx + 1}`}
                            value={row.subject}
                            placeholder="Ex. Programmation Java"
                            onChange={(e) => updateRow(row.rowId, { subject: e.target.value })}
                            className={cn(
                              'w-44 rounded-lg px-2 py-1 text-xs text-zinc-900 dark:text-zinc-100',
                              !row.ignored && row.subject.trim().length < 2
                                ? 'bg-rose-50 dark:bg-rose-950/50'
                                : 'bg-zinc-100/80 dark:bg-zinc-800',
                            )}
                          />
                        </td>

                        <td className="px-2.5 py-2">
                          <select
                            aria-label={`Type ligne ${idx + 1}`}
                            value={row.sessionType}
                            onChange={(e) =>
                              updateRow(row.rowId, {
                                sessionType: e.target.value as CourseSessionSubtype,
                              })
                            }
                            className="rounded-lg bg-zinc-100/80 px-2 py-1 text-xs text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                          >
                            {(Object.keys(SUBTYPE_LABELS_FR) as CourseSessionSubtype[]).map(
                              (st) => (
                                <option key={st} value={st}>
                                  {SUBTYPE_LABELS_FR[st]}
                                </option>
                              ),
                            )}
                          </select>
                        </td>

                        <td className="px-2.5 py-2">
                          <select
                            aria-label={`Jour ligne ${idx + 1}`}
                            value={row.dayOfWeek !== null ? String(row.dayOfWeek) : ''}
                            onChange={(e) =>
                              updateRow(row.rowId, {
                                dayOfWeek: e.target.value === '' ? null : Number(e.target.value),
                              })
                            }
                            className={cn(
                              'rounded-lg px-2 py-1 text-xs text-zinc-900 dark:text-zinc-100',
                              !row.ignored && row.dayOfWeek === null
                                ? 'bg-rose-50 dark:bg-rose-950/50'
                                : 'bg-zinc-100/80 dark:bg-zinc-800',
                            )}
                          >
                            <option value="">Jour…</option>
                            {Object.entries(DAY_LABELS_FR).map(([dIdx, label]) => (
                              <option key={dIdx} value={dIdx}>
                                {label}
                              </option>
                            ))}
                          </select>
                        </td>

                        <td className="px-2.5 py-2">
                          <input
                            type="time"
                            aria-label={`Heure de début ligne ${idx + 1}`}
                            value={row.startTime ?? ''}
                            onChange={(e) =>
                              updateRow(row.rowId, { startTime: e.target.value || null })
                            }
                            className={cn(
                              'rounded-lg px-2 py-1 text-xs tabular-nums text-zinc-900 dark:text-zinc-100',
                              !row.ignored && !row.startTime
                                ? 'bg-rose-50 dark:bg-rose-950/50'
                                : 'bg-zinc-100/80 dark:bg-zinc-800',
                            )}
                          />
                        </td>

                        <td className="px-2.5 py-2">
                          <input
                            type="time"
                            aria-label={`Heure de fin ligne ${idx + 1}`}
                            value={row.endTime ?? ''}
                            onChange={(e) =>
                              updateRow(row.rowId, { endTime: e.target.value || null })
                            }
                            className={cn(
                              'rounded-lg px-2 py-1 text-xs tabular-nums text-zinc-900 dark:text-zinc-100',
                              !row.ignored &&
                                (!row.endTime || (row.startTime && row.endTime <= row.startTime))
                                ? 'bg-rose-50 dark:bg-rose-950/50'
                                : 'bg-zinc-100/80 dark:bg-zinc-800',
                            )}
                          />
                        </td>

                        <td className="px-2.5 py-2">
                          <input
                            type="text"
                            aria-label={`Enseignant ligne ${idx + 1}`}
                            value={row.teacher ?? ''}
                            placeholder="Enseignant"
                            onChange={(e) =>
                              updateRow(row.rowId, { teacher: e.target.value || null })
                            }
                            className="w-28 rounded-lg bg-zinc-100/80 px-2 py-1 text-xs text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                          />
                        </td>

                        <td className="px-2.5 py-2">
                          <input
                            type="text"
                            aria-label={`Salle ligne ${idx + 1}`}
                            value={row.room ?? ''}
                            placeholder="Salle / Amphi"
                            onChange={(e) =>
                              updateRow(row.rowId, { room: e.target.value || null })
                            }
                            className="w-24 rounded-lg bg-zinc-100/80 px-2 py-1 text-xs text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                          />
                        </td>

                        <td className="px-2.5 py-2">
                          <input
                            type="text"
                            aria-label={`Groupe ligne ${idx + 1}`}
                            value={row.groupName ?? ''}
                            placeholder="Groupe"
                            onChange={(e) =>
                              updateRow(row.rowId, { groupName: e.target.value || null })
                            }
                            className="w-20 rounded-lg bg-zinc-100/80 px-2 py-1 text-xs text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                          />
                        </td>

                        <td className="px-2.5 py-2 text-right">
                          <button
                            type="button"
                            aria-label={`Supprimer la ligne ${idx + 1}`}
                            onClick={() => handleRemoveRow(row.rowId)}
                            className="inline-flex items-center justify-center rounded-lg p-1.5 text-zinc-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/50 dark:hover:text-rose-400"
                          >
                            <Icon icon={Delete02Icon} size={14} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Actions de validation obligatoire ou d'annulation (Section 6) */}
          {draftNotice && (
            <p role="status" className="text-right text-xs font-medium text-teal-700 dark:text-teal-300">
              {draftNotice}
            </p>
          )}
          <div className="flex flex-wrap items-center justify-end gap-2 pt-3">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={isSubmitting || isSavingDraft}
              onClick={() => void handleCancelImport()}
            >
              Annuler l’importation
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              isLoading={isSavingDraft}
              disabled={isSubmitting}
              onClick={() => void handleSaveDraft()}
            >
              Enregistrer le brouillon
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              disabled={isSavingDraft || activeCoursesCount === 0 || blockingAnomalies.length > 0}
              onClick={() => void handleConfirmImport()}
            >
              Enregistrer mon emploi du temps
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
