import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Add01Icon,
  Alert02Icon,
  Calendar03Icon,
  Cancel01Icon,
  CheckmarkCircle02Icon,
  Delete02Icon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Icon } from '../../components/ui/Icon';
import { addDays, formatDateFr, formatTimeFr, toLocalDateKey } from '../../lib/date';
import {
  planningApi,
  type AvailabilityRule,
  type AvailabilityRuleType,
  type LearningPlanVersion,
  type PlannedSessionProposal,
} from '../../lib/planningApi';
import { generateId } from '../../lib/storage';
import { useAuth } from '../../state/AuthContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type { ScheduleEventType } from '../../types/domain';

const DAY_LABELS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];

const RULE_TYPE_LABELS: Record<AvailabilityRuleType, string> = {
  personal_unavailability: 'Indisponible',
  confirmed_availability: 'Disponibilité confirmée',
  recovery_time: 'Récupération',
};

function toJsDayFromMondayIndex(mondayIndex: number): number {
  return mondayIndex === 6 ? 0 : mondayIndex + 1;
}

function toMondayIndexFromDate(d: Date): number {
  const js = d.getDay();
  return js === 0 ? 6 : js - 1;
}

function hhmmToMinutes(value: string): number {
  const [h, m] = value.split(':').map((part) => Number.parseInt(part, 10));
  return (Number.isFinite(h) ? h : 0) * 60 + (Number.isFinite(m) ? m : 0);
}

export interface IntelligentPlanStudioProps {
  onClose: () => void;
  onApplied?: (message: string) => void;
}

export function IntelligentPlanStudio({ onClose, onApplied }: IntelligentPlanStudioProps) {
  const { session } = useAuth();
  const { dataMode, scheduleEvents, tasks, createScheduleEvent, retry } = useStudyStore();
  const queryClient = useQueryClient();

  const isApiMode = session?.mode === 'api' && dataMode === 'api';
  const accessToken = session?.mode === 'api' ? session.accessToken : '';

  // États formulaire de règle de disponibilité
  const [ruleLabel, setRuleLabel] = useState('Indisponibilité personnelle');
  const [ruleType, setRuleType] = useState<AvailabilityRuleType>('personal_unavailability');
  const [ruleDay, setRuleDay] = useState<number>(2); // Mercredi par défaut
  const [ruleStart, setRuleStart] = useState('14:00');
  const [ruleEnd, setRuleEnd] = useState('18:00');

  // Paramètres de génération & d'ajustement
  const [horizonDays, setHorizonDays] = useState(7);
  const [focusSubject, setFocusSubject] = useState('');
  const [weeklyHoursOverride, setWeeklyHoursOverride] = useState('');
  const [adjustInstruction, setAdjustInstruction] = useState('');

  // États démo locale (Vitest & mode démo sans serveur)
  const [localRules, setLocalRules] = useState<AvailabilityRule[]>([]);
  const [localVersions, setLocalVersions] = useState<LearningPlanVersion[]>([]);
  const [activeVersion, setActiveVersion] = useState<LearningPlanVersion | null>(null);
  const [localFeedback, setLocalFeedback] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const rulesQuery = useQuery({
    queryKey: ['availability-rules', accessToken],
    queryFn: () => planningApi.listAvailabilityRules(accessToken),
    enabled: isApiMode && Boolean(accessToken),
  });

  const versionsQuery = useQuery({
    queryKey: ['planning-versions', accessToken],
    queryFn: () => planningApi.listVersions(accessToken, 10),
    enabled: isApiMode && Boolean(accessToken),
  });

  const validityQuery = useQuery({
    queryKey: ['planning-validity', accessToken],
    queryFn: () => planningApi.checkValidity(accessToken),
    enabled: isApiMode && Boolean(accessToken),
  });

  const rules = isApiMode ? (rulesQuery.data ?? []) : localRules;
  const versions = isApiMode ? (versionsQuery.data ?? []) : localVersions;
  const currentPlan = activeVersion ?? versions[0] ?? null;

  const invalidatePlanningCaches = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['availability-rules'] }),
      queryClient.invalidateQueries({ queryKey: ['planning-versions'] }),
      queryClient.invalidateQueries({ queryKey: ['planning-validity'] }),
      queryClient.invalidateQueries({ queryKey: ['schedule'] }),
      queryClient.invalidateQueries({ queryKey: ['tasks'] }),
    ]);
  };

  const handleAddRule = async (event: React.FormEvent) => {
    event.preventDefault();
    setLocalError(null);
    setLocalFeedback(null);
    if (!ruleLabel.trim()) {
      setLocalError('Veuillez saisir un libellé pour la règle.');
      return;
    }

    if (isApiMode) {
      setIsBusy(true);
      try {
        await planningApi.createAvailabilityRule(accessToken, {
          label: ruleLabel.trim(),
          rule_type: ruleType,
          day_of_week: ruleDay,
          start_time: ruleStart,
          end_time: ruleEnd,
          recurrence: 'weekly',
        });
        await invalidatePlanningCaches();
        setLocalFeedback(`Règle « ${ruleLabel.trim()} » enregistrée.`);
      } catch (err) {
        setLocalError(err instanceof Error ? err.message : 'Erreur lors de la création.');
      } finally {
        setIsBusy(false);
      }
      return;
    }

    const nowIso = new Date().toISOString();
    const created: AvailabilityRule = {
      id: generateId(),
      user_id: 'local-user',
      label: ruleLabel.trim(),
      rule_type: ruleType,
      day_of_week: ruleDay,
      start_time: ruleStart,
      end_time: ruleEnd,
      starts_at: null,
      ends_at: null,
      timezone: 'Europe/Paris',
      recurrence: 'weekly',
      active: true,
      notes: null,
      created_at: nowIso,
      updated_at: nowIso,
    };
    setLocalRules((prev) => [...prev, created]);
    setLocalFeedback(`Règle « ${created.label} » enregistrée.`);
  };

  const handleDeleteRule = async (ruleId: string) => {
    setLocalError(null);
    if (isApiMode) {
      setIsBusy(true);
      try {
        await planningApi.deleteAvailabilityRule(accessToken, ruleId);
        await invalidatePlanningCaches();
      } catch (err) {
        setLocalError(err instanceof Error ? err.message : 'Erreur lors de la suppression.');
      } finally {
        setIsBusy(false);
      }
      return;
    }
    setLocalRules((prev) => prev.filter((r) => r.id !== ruleId));
  };

  const buildLocalPlan = (instruction?: string): LearningPlanVersion => {
    const now = new Date();
    const nextVersionNum = (localVersions[0]?.version_number ?? 0) + 1;
    const weeklyCapHours = Number.parseFloat(weeklyHoursOverride);
    const weeklyCapMinutes = Number.isFinite(weeklyCapHours) && weeklyCapHours > 0
      ? Math.round(weeklyCapHours * 60)
      : instruction && /allège|allege/i.test(instruction)
        ? 180
        : 360;

    const openTasks = tasks.filter((t) => t.status === 'todo' || t.status === 'in_progress');
    const subjectLabel = focusSubject.trim() || openTasks[0]?.title || 'React & Architecture Python';
    const sessionDuration = 60;
    const maxSessions = Math.max(1, Math.min(4, Math.floor(weeklyCapMinutes / sessionDuration)));

    const planned: PlannedSessionProposal[] = [];
    for (let dayOffset = 0; dayOffset < horizonDays && planned.length < maxSessions; dayOffset += 1) {
      const targetDay = addDays(now, dayOffset);
      const mondayIdx = toMondayIndexFromDate(targetDay);
      const dateKey = toLocalDateKey(targetDay);
      const candidateWindows = [
        { s: '09:00', e: '10:00' },
        { s: '15:00', e: '16:00' },
        { s: '18:30', e: '19:30' },
      ];
      for (const win of candidateWindows) {
        if (planned.length >= maxSessions) break;
        const wsMin = hhmmToMinutes(win.s);
        const weMin = hhmmToMinutes(win.e);
        const blockedByRule = localRules.some((r) => {
          if (r.rule_type === 'confirmed_availability' || r.day_of_week !== mondayIdx || !r.start_time || !r.end_time) {
            return false;
          }
          return wsMin < hhmmToMinutes(r.end_time) && weMin > hhmmToMinutes(r.start_time);
        });
        if (blockedByRule) continue;

        const startDt = new Date(`${dateKey}T${win.s}:00`);
        const endDt = new Date(`${dateKey}T${win.e}:00`);
        const conflictFixed = scheduleEvents.some((ev) => {
          const evS = new Date(ev.startsAt).getTime();
          const evE = new Date(ev.endsAt).getTime();
          return startDt.getTime() < evE && endDt.getTime() > evS;
        });
        if (conflictFixed) continue;

        const idx = planned.length;
        planned.push({
          slot_id: `slot-${idx + 1}`,
          title: `${subjectLabel} — Session ${idx + 1}`,
          session_type: 'learning',
          starts_at: startDt.toISOString(),
          ends_at: endDt.toISOString(),
          duration_minutes: 60,
          priority_source_type: openTasks[idx] ? 'task' : 'personal_goal',
          priority_source_id: openTasks[idx]?.id ?? null,
          priority_score: 78 - idx * 4,
          subject: subjectLabel,
          task_id: openTasks[idx]?.id ?? null,
          project_id: null,
          skill_id: null,
          course_id: null,
          lesson_id: null,
          module_id: null,
          slot_category: 'potential_availability',
          rationale: `Créneau sans conflit (${DAY_LABELS[mondayIdx]} ${win.s}–${win.e}) respectant vos indisponibilités et vos cours.`,
          pedagogical_content: {
            content_source: 'course_generator_preview',
            course_id: null,
            course_title: subjectLabel,
            level_id: null,
            level_number: 1,
            level_title: 'Niveau 1 — Fondamentaux',
            lesson_id: null,
            lesson_title: `Module pratique ${idx + 1}`,
            module_id: null,
            module_title: null,
            skill_id: null,
            skill_name: subjectLabel,
            remediation_needed: false,
            remediation_reason: null,
            blocked_prerequisites: [],
            exercises_focus: [`Exercice guidé ${idx + 1} sur ${subjectLabel}`],
            deliverables: ['Validation pratique complétée'],
            recommended_session_type: 'deep_work',
            next_step_summary: `Progression structurée sur ${subjectLabel} (étape ${idx + 1}).`,
          },
        });
        break;
      }
    }

    const totalMins = planned.reduce((acc, item) => acc + item.duration_minutes, 0);
    return {
      id: generateId(),
      user_id: 'local-user',
      version_number: nextVersionNum,
      status: 'proposed',
      horizon_days: horizonDays,
      timezone: 'Europe/Paris',
      rationale: `Programme généré (${planned.length} séance(s), ${totalMins} min) après filtrage des cours fixes et de ${localRules.length} règle(s) de disponibilité.`,
      priorities: [
        {
          source_type: 'personal_goal',
          source_id: null,
          title: subjectLabel,
          subject: subjectLabel,
          domain: 'Apprentissage',
          score: 80,
          urgency_score: 20,
          blocking_score: 15,
          strategic_score: 25,
          effort_score: 10,
          deficit_score: 10,
          deadline_at: null,
          recommended_minutes: weeklyCapMinutes,
          reasons: ['Priorité active détectée sans surcharge hebdomadaire.'],
        },
      ],
      planned_sessions: planned,
      arbitrage_items: [],
      load_summary: {
        daily_minutes: {},
        daily_cap_minutes: 240,
        weekly_planned_minutes: totalMins,
        weekly_cap_minutes: weeklyCapMinutes,
        recovery_preserved_minutes: 0,
        overloaded_days: [],
        is_overloaded: false,
      },
      availability_summary: null,
      missing_info: [],
      warnings:
        localRules.some((r) => r.rule_type === 'confirmed_availability')
          ? []
          : ['Créneaux basés sur les plages libres potentielles en attente de confirmation.'],
      applied_event_ids: [],
      applied_task_ids: [],
      applied_course_ids: [],
      parent_version_id: localVersions[0]?.id ?? null,
      applied_at: null,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
    };
  };

  const handleGenerate = async () => {
    setLocalError(null);
    setLocalFeedback(null);

    const parsedHours = Number.parseFloat(weeklyHoursOverride);
    if (isApiMode) {
      setIsBusy(true);
      try {
        const version = await planningApi.generatePlan(accessToken, {
          horizon_days: horizonDays,
          focus_subject: focusSubject.trim() || null,
          weekly_hours_override: Number.isFinite(parsedHours) && parsedHours > 0 ? parsedHours : null,
          include_potential_slots: true,
        });
        setActiveVersion(version);
        await invalidatePlanningCaches();
      } catch (err) {
        setLocalError(err instanceof Error ? err.message : 'Erreur lors de la génération.');
      } finally {
        setIsBusy(false);
      }
      return;
    }

    const version = buildLocalPlan();
    setLocalVersions((prev) => [version, ...prev]);
    setActiveVersion(version);
  };

  const handleAdjust = async () => {
    if (!adjustInstruction.trim()) return;
    setLocalError(null);
    setLocalFeedback(null);

    if (isApiMode) {
      setIsBusy(true);
      try {
        const version = await planningApi.adjustPlan(accessToken, adjustInstruction.trim());
        setActiveVersion(version);
        setAdjustInstruction('');
        await invalidatePlanningCaches();
      } catch (err) {
        setLocalError(err instanceof Error ? err.message : 'Erreur lors de l’ajustement.');
      } finally {
        setIsBusy(false);
      }
      return;
    }

    const version = buildLocalPlan(adjustInstruction.trim());
    setLocalVersions((prev) => [version, ...prev]);
    setActiveVersion(version);
    setAdjustInstruction('');
  };

  const handleApply = async () => {
    if (!currentPlan) return;
    setLocalError(null);

    if (isApiMode) {
      setIsBusy(true);
      try {
        const applied = await planningApi.applyVersion(accessToken, currentPlan.id, true);
        setActiveVersion(applied);
        await invalidatePlanningCaches();
        await retry();
        const msg = `Programme v${applied.version_number} appliqué (${applied.applied_event_ids.length} séance(s) ajoutée(s)).`;
        setLocalFeedback(msg);
        onApplied?.(msg);
      } catch (err) {
        setLocalError(err instanceof Error ? err.message : 'Conflit ou erreur lors de l’application.');
      } finally {
        setIsBusy(false);
      }
      return;
    }

    let createdCount = 0;
    for (const sess of currentPlan.planned_sessions) {
      const evType: ScheduleEventType = sess.session_type === 'project' ? 'project' : 'learning';
      const ok = await createScheduleEvent({
        title: sess.title,
        type: evType,
        date: toLocalDateKey(sess.starts_at),
        startTime: formatTimeFr(sess.starts_at),
        endTime: formatTimeFr(sess.ends_at),
        notes: sess.rationale,
      });
      if (ok) createdCount += 1;
    }
    const updated: LearningPlanVersion = {
      ...currentPlan,
      status: 'applied',
      applied_at: new Date().toISOString(),
    };
    setLocalVersions((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
    setActiveVersion(updated);
    const msg = `Programme v${updated.version_number} appliqué (${createdCount} séance(s) ajoutée(s)).`;
    setLocalFeedback(msg);
    onApplied?.(msg);
  };

  const handleReject = async () => {
    if (!currentPlan) return;
    setLocalError(null);
    if (isApiMode) {
      setIsBusy(true);
      try {
        const rejected = await planningApi.rejectVersion(accessToken, currentPlan.id);
        setActiveVersion(rejected);
        await invalidatePlanningCaches();
        setLocalFeedback(`Proposition v${rejected.version_number} rejetée sans modifier le calendrier.`);
      } catch (err) {
        setLocalError(err instanceof Error ? err.message : 'Erreur lors du rejet.');
      } finally {
        setIsBusy(false);
      }
      return;
    }
    const rejected: LearningPlanVersion = { ...currentPlan, status: 'rejected' };
    setLocalVersions((prev) => prev.map((v) => (v.id === rejected.id ? rejected : v)));
    setActiveVersion(rejected);
    setLocalFeedback(`Proposition v${rejected.version_number} rejetée sans modifier le calendrier.`);
  };

  const handleRestore = async (versionId: string) => {
    setLocalError(null);
    if (isApiMode) {
      setIsBusy(true);
      try {
        const restored = await planningApi.restoreVersion(accessToken, versionId);
        setActiveVersion(restored);
        await invalidatePlanningCaches();
        await retry();
        const msg = `Version v${restored.version_number} restaurée.`;
        setLocalFeedback(msg);
        onApplied?.(msg);
      } catch (err) {
        setLocalError(err instanceof Error ? err.message : 'Erreur lors de la restauration.');
      } finally {
        setIsBusy(false);
      }
    }
  };

  void toJsDayFromMondayIndex;

  return (
    <section
      aria-label="Moteur intelligent de planification"
      className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-200 pb-4 dark:border-zinc-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Programme intelligent d&apos;apprentissage
            </h2>
            <Badge variant="primary">Multi-sources</Badge>
          </div>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
            Analyse vos cours fixes, indisponibilités personnelles, objectifs, parcours, tâches en retard et historique sans surcharge.
          </p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          <Icon icon={Cancel01Icon} size={15} />
          Fermer
        </Button>
      </div>

      {isApiMode && validityQuery.data && !validityQuery.data.is_valid && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50/70 px-3.5 py-2.5 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
          <div className="flex items-center gap-2">
            <Icon icon={Alert02Icon} size={16} />
            <span>{validityQuery.data.recommendation}</span>
          </div>
          <Button type="button" size="sm" variant="secondary" onClick={() => void handleGenerate()} disabled={isBusy}>
            Recalculer maintenant
          </Button>
        </div>
      )}

      {localFeedback && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs font-medium text-emerald-800 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-200">
          <Icon icon={CheckmarkCircle02Icon} size={15} />
          <span>{localFeedback}</span>
        </div>
      )}

      {localError && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2 text-xs font-medium text-red-800 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-200">
          <Icon icon={Alert02Icon} size={15} />
          <span>{localError}</span>
        </div>
      )}

      {/* 1. Gestion explicite des indisponibilités & disponibilités confirmées */}
      <div className="space-y-3 rounded-xl border border-zinc-200 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/40">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-700 dark:text-zinc-300">
            Règles de disponibilité &amp; d&apos;indisponibilité
          </h3>
          <span className="text-xs text-zinc-500">{rules.length} règle(s) active(s)</span>
        </div>

        <form onSubmit={(e) => void handleAddRule(e)} className="grid grid-cols-1 gap-2 sm:grid-cols-6">
          <input
            aria-label="Libellé de disponibilité"
            type="text"
            value={ruleLabel}
            onChange={(e) => setRuleLabel(e.target.value)}
            placeholder="Ex. Indisponibilité mercredi après-midi"
            className="sm:col-span-2 rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-xs text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
          />
          <select
            aria-label="Type de règle"
            value={ruleType}
            onChange={(e) => setRuleType(e.target.value as AvailabilityRuleType)}
            className="rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-xs text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
          >
            <option value="personal_unavailability">Indisponible</option>
            <option value="confirmed_availability">Disponible confirmé</option>
            <option value="recovery_time">Récupération</option>
          </select>
          <select
            aria-label="Jour de la règle"
            value={ruleDay}
            onChange={(e) => setRuleDay(Number(e.target.value))}
            className="rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-xs text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
          >
            {DAY_LABELS.map((dayName, idx) => (
              <option key={dayName} value={idx}>
                {dayName}
              </option>
            ))}
          </select>
          <div className="flex items-center gap-1">
            <input
              aria-label="Heure début règle"
              type="time"
              value={ruleStart}
              onChange={(e) => setRuleStart(e.target.value)}
              className="w-full rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-xs text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
            />
            <input
              aria-label="Heure fin règle"
              type="time"
              value={ruleEnd}
              onChange={(e) => setRuleEnd(e.target.value)}
              className="w-full rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-xs text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
            />
          </div>
          <Button type="submit" size="sm" variant="secondary" disabled={isBusy}>
            <Icon icon={Add01Icon} size={14} />
            Ajouter la règle
          </Button>
        </form>

        {rules.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {rules.map((r) => (
              <div
                key={r.id}
                className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-2.5 py-1 text-xs dark:border-zinc-700 dark:bg-zinc-900"
              >
                <Badge
                  variant={
                    r.rule_type === 'confirmed_availability'
                      ? 'success'
                      : r.rule_type === 'recovery_time'
                        ? 'neutral'
                        : 'danger'
                  }
                >
                  {RULE_TYPE_LABELS[r.rule_type]}
                </Badge>
                <span className="font-medium text-zinc-800 dark:text-zinc-200">{r.label}</span>
                {r.day_of_week !== null && (
                  <span className="text-zinc-500">
                    {DAY_LABELS[r.day_of_week]} {r.start_time}–{r.end_time}
                  </span>
                )}
                <button
                  type="button"
                  aria-label={`Supprimer ${r.label}`}
                  onClick={() => void handleDeleteRule(r.id)}
                  className="text-zinc-400 hover:text-red-600"
                >
                  <Icon icon={Delete02Icon} size={13} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. Génération & ajustement du programme */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <select
          aria-label="Horizon de planification"
          value={horizonDays}
          onChange={(e) => setHorizonDays(Number(e.target.value))}
          className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs font-medium text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
        >
          <option value={7}>Horizon : 7 jours</option>
          <option value={14}>Horizon : 14 jours</option>
        </select>
        <input
          aria-label="Focus prioritaire optionnel"
          type="text"
          value={focusSubject}
          onChange={(e) => setFocusSubject(e.target.value)}
          placeholder="Focus optionnel (ex. React, Java)"
          className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
        />
        <input
          aria-label="Budget hebdomadaire max (h)"
          type="number"
          min="1"
          max="40"
          step="0.5"
          value={weeklyHoursOverride}
          onChange={(e) => setWeeklyHoursOverride(e.target.value)}
          placeholder="Max h/sem (ex. 8)"
          className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
        />
        <Button type="button" size="sm" onClick={() => void handleGenerate()} disabled={isBusy}>
          <Icon icon={Calendar03Icon} size={15} />
          Générer le programme
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          aria-label="Instruction d'ajustement"
          type="text"
          value={adjustInstruction}
          onChange={(e) => setAdjustInstruction(e.target.value)}
          placeholder="Ajuster en langage naturel (ex. Allège cette semaine, séances de 45 min)"
          className="min-w-0 flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
        />
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={() => void handleAdjust()}
          disabled={isBusy || !adjustInstruction.trim()}
        >
          Recalculer / Ajuster
        </Button>
      </div>

      {/* 3. Aperçu du programme généré */}
      {currentPlan && (
        <div className="space-y-4 rounded-xl border border-zinc-200 bg-zinc-50/50 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                  Version v{currentPlan.version_number}
                </span>
                <Badge variant={currentPlan.status === 'applied' || currentPlan.status === 'restored' ? 'success' : currentPlan.status === 'rejected' ? 'danger' : 'warning'}>
                  {currentPlan.status}
                </Badge>
                <span className="text-xs text-zinc-500">
                  {currentPlan.load_summary.weekly_planned_minutes} / {currentPlan.load_summary.weekly_cap_minutes} min
                </span>
              </div>
              <p className="text-xs text-zinc-700 dark:text-zinc-300">{currentPlan.rationale}</p>
            </div>

            {currentPlan.status === 'proposed' && (
              <div className="flex flex-wrap items-center gap-2">
                <Button type="button" size="sm" onClick={() => void handleApply()} disabled={isBusy || currentPlan.planned_sessions.length === 0}>
                  <Icon icon={CheckmarkCircle02Icon} size={15} />
                  Appliquer au calendrier
                </Button>
                <Button type="button" size="sm" variant="secondary" onClick={() => void handleReject()} disabled={isBusy}>
                  <Icon icon={Cancel01Icon} size={15} />
                  Rejeter sans modifier
                </Button>
              </div>
            )}
          </div>

          {currentPlan.warnings.length > 0 && (
            <div className="space-y-1 rounded-lg border border-amber-200/80 bg-amber-50/60 p-2.5 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
              {currentPlan.warnings.map((w) => (
                <p key={w}>{w}</p>
              ))}
            </div>
          )}

          {currentPlan.planned_sessions.length > 0 && (
            <div className="space-y-2">
              {currentPlan.planned_sessions.map((sess) => (
                  <div
                    key={sess.slot_id}
                    className="rounded-xl border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-900"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Icon icon={Timer02Icon} size={14} className="text-zinc-500" />
                        <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                          {sess.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={sess.slot_category === 'confirmed_availability' ? 'success' : 'neutral'}>
                          {sess.slot_category === 'confirmed_availability' ? 'Confirmé' : 'Potentiel'}
                        </Badge>
                        {sess.pedagogical_content.remediation_needed && (
                          <Badge variant="warning">Remédiation</Badge>
                        )}
                        <span className="text-xs font-medium tabular-nums text-zinc-600 dark:text-zinc-300">
                          {formatDateFr(sess.starts_at)} · {formatTimeFr(sess.starts_at)}–{formatTimeFr(sess.ends_at)}
                        </span>
                      </div>
                    </div>
                    <p className="mt-1.5 text-xs text-zinc-600 dark:text-zinc-300">{sess.rationale}</p>
                    {sess.pedagogical_content.exercises_focus.length > 0 && (
                      <p className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
                        Activités ciblées : {sess.pedagogical_content.exercises_focus.join(' · ')}
                      </p>
                    )}
                  </div>
              ))}
            </div>
          )}

          {currentPlan.arbitrage_items.length > 0 && (
            <div className="space-y-1.5 rounded-xl border border-zinc-200 bg-white p-3 text-xs dark:border-zinc-800 dark:bg-zinc-900">
              <p className="font-semibold text-zinc-800 dark:text-zinc-200">
                Arbitrages anti-surcharge &amp; reports
              </p>
              {currentPlan.arbitrage_items.map((arb) => (
                <div key={`${arb.source_type}-${arb.title}`} className="flex flex-wrap justify-between gap-2 text-zinc-600 dark:text-zinc-400">
                  <span>{arb.title} : {arb.reason}</span>
                  <span className="tabular-nums">-{arb.postponed_minutes} min reportées</span>
                </div>
              ))}
            </div>
          )}

          {versions.length > 1 && (
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
              <span className="font-medium text-zinc-500">Historique :</span>
              {versions.slice(0, 5).map((v) => (
                <Button
                  key={v.id}
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={isBusy || v.id === currentPlan.id}
                  onClick={() => (isApiMode ? void handleRestore(v.id) : setActiveVersion(v))}
                >
                  Restaurer v{v.version_number} ({v.status})
                </Button>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
