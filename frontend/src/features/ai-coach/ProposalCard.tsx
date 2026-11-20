import { useState } from 'react';
import {
  Alert02Icon,
  Award02Icon,
  Calendar03Icon,
  CancelCircleIcon,
  CheckmarkCircle02Icon,
  CheckmarkSquare02Icon,
  Mortarboard02Icon,
  PencilEdit02Icon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { Badge, type BadgeVariant } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select } from '../../components/ui/FormFields';
import { Icon, type IconSvgElement } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { formatDateTimeFr, formatTimeFr } from '../../lib/date';
import type {
  AiActionProposal,
  ProposalStatus,
  ProposedActivitySlot,
  StrategicDecision,
  TaskPriority,
} from '../../types/domain';
import { TASK_PRIORITY_META } from '../tasks/taskUtils';

const ACTION_META: Record<string, { label: string; icon: IconSvgElement }> = {
  create_task: { label: 'Nouvelle tâche', icon: CheckmarkSquare02Icon },
  update_task: { label: 'Mise à jour de tâche', icon: CheckmarkSquare02Icon },
  park_task: { label: 'Mise au parking', icon: Timer02Icon },
  create_project: { label: 'Nouveau projet', icon: CheckmarkSquare02Icon },
  update_project: { label: 'Mise à jour de projet', icon: CheckmarkSquare02Icon },
  pause_project: { label: 'Mise en pause de projet', icon: Timer02Icon },
  create_schedule_event: { label: 'Créneau planning', icon: Calendar03Icon },
  update_schedule_event: { label: 'Reprogrammation créneau', icon: Calendar03Icon },
  archive_schedule_event: { label: 'Annulation créneau', icon: Calendar03Icon },
  create_study_session: { label: 'Nouvelle séance d’étude', icon: Timer02Icon },
  create_skill: { label: 'Nouvelle compétence', icon: Award02Icon },
  add_skill_evidence: { label: 'Preuve de compétence', icon: Award02Icon },
  propose_skill_assessment: { label: 'Évaluation de compétence', icon: Award02Icon },
  recommend_skill_progression: { label: 'Validation de progression', icon: Award02Icon },
  create_learning_path: { label: 'Nouveau parcours', icon: Mortarboard02Icon },
  update_learning_path: { label: 'Mise à jour de parcours', icon: Mortarboard02Icon },
  create_personal_goal: { label: 'Nouvel objectif personnel', icon: Award02Icon },
  update_personal_goal: { label: 'Mise à jour d’objectif', icon: Award02Icon },
  plan_strategic_activity: { label: 'Planification stratégique', icon: Calendar03Icon },
  create_course: { label: 'Nouveau cours complet', icon: Mortarboard02Icon },
  update_preferences: { label: 'Mise à jour disponibilités', icon: Timer02Icon },
  manage_availability_rule: { label: 'Règle de disponibilité', icon: Calendar03Icon },
  generate_learning_plan: { label: 'Programme intelligent', icon: Calendar03Icon },
  batch_actions: { label: 'Plan multi-actions coordonné', icon: CheckmarkSquare02Icon },
};

const STRATEGIC_DECISION_META: Record<
  StrategicDecision,
  { label: string; variant: BadgeVariant }
> = {
  ACCEPTABLE: { label: 'Acceptable', variant: 'success' },
  ACCEPTABLE_WITH_CONDITIONS: { label: 'Sous conditions', variant: 'warning' },
  NOT_RECOMMENDED: { label: 'Non recommandée (Parking)', variant: 'danger' },
};

const PROPOSAL_STATUS_META: Record<ProposalStatus, { label: string; variant: BadgeVariant }> = {
  pending: { label: 'En attente de validation', variant: 'warning' },
  accepted: { label: 'Acceptée', variant: 'primary' },
  executed: { label: 'Exécutée', variant: 'success' },
  rejected: { label: 'Rejetée', variant: 'danger' },
  expired: { label: 'Expirée', variant: 'neutral' },
  failed: { label: 'Échec', variant: 'danger' },
};

interface ProposalCardProps {
  proposal: AiActionProposal;
  onAccept: (proposalId: string, payloadOverrides?: Record<string, unknown>) => Promise<boolean>;
  onReject: (proposalId: string) => Promise<boolean>;
  onUpdate?: (
    proposalId: string,
    payloadOverrides: Record<string, unknown>,
    recalculateSlots?: boolean,
  ) => Promise<boolean>;
}

function isTaskPriority(value: unknown): value is TaskPriority {
  return value === 'low' || value === 'normal' || value === 'high' || value === 'critical';
}

export function ProposalCard({ proposal, onAccept, onReject, onUpdate }: ProposalCardProps) {
  const payload = proposal.payload ?? {};
  const actionMeta = ACTION_META[proposal.actionType] ?? {
    label: 'Action suggérée',
    icon: CheckmarkSquare02Icon,
  };
  const statusMeta = PROPOSAL_STATUS_META[proposal.status];

  const isPending = proposal.status === 'pending';
  const isStrategicPlan = proposal.actionType === 'plan_strategic_activity';
  const isCourseCreate = proposal.actionType === 'create_course';
  const supportsTitleEdit =
    proposal.actionType === 'create_task' ||
    proposal.actionType === 'create_schedule_event' ||
    isCourseCreate;
  const supportsPriorityEdit = proposal.actionType === 'create_task';
  const supportsAdjustment = supportsTitleEdit || isStrategicPlan;

  const initialTitle = isStrategicPlan
    ? typeof payload.activity_title === 'string' && payload.activity_title.trim()
      ? payload.activity_title
      : proposal.title
    : typeof payload.title === 'string' && payload.title.trim()
      ? payload.title
      : proposal.title;
  const initialPriority: TaskPriority = isTaskPriority(payload.priority)
    ? payload.priority
    : 'normal';
  const initialGoal = typeof payload.goal === 'string' ? payload.goal : '';
  const initialFreq =
    typeof payload.frequency_per_week === 'number' ? payload.frequency_per_week : 2;

  const [isEditing, setIsEditing] = useState(false);
  const [adjustedTitle, setAdjustedTitle] = useState(initialTitle);
  const [adjustedPriority, setAdjustedPriority] = useState<TaskPriority>(initialPriority);
  const [adjustedGoal, setAdjustedGoal] = useState(initialGoal);
  const [adjustedFreq, setAdjustedFreq] = useState(initialFreq);
  const [pendingSubmit, setPendingSubmit] = useState<'accept' | 'reject' | 'update' | null>(null);

  const priorityMeta = isTaskPriority(payload.priority)
    ? TASK_PRIORITY_META[payload.priority]
    : null;
  const startsAt = typeof payload.starts_at === 'string' ? payload.starts_at : null;
  const endsAt = typeof payload.ends_at === 'string' ? payload.ends_at : null;
  const skillName = typeof payload.skill_name === 'string' ? payload.skill_name : null;
  const previousLevel =
    typeof payload.previous_level === 'number'
      ? payload.previous_level
      : typeof payload.current_level === 'number'
        ? payload.current_level
        : null;
  const nextLevel =
    typeof payload.proposed_level === 'number'
      ? payload.proposed_level
      : typeof payload.target_level === 'number'
        ? payload.target_level
        : null;
  const parkedTaskTitle = typeof payload.task_title === 'string' ? payload.task_title : null;
  const hasConflict = Boolean(payload.has_conflict);
  const conflictingTitles = Array.isArray(payload.conflicting_titles)
    ? payload.conflicting_titles.filter((item): item is string => typeof item === 'string')
    : [];

  const strategicDecision =
    typeof payload.decision === 'string' && payload.decision in STRATEGIC_DECISION_META
      ? STRATEGIC_DECISION_META[payload.decision as StrategicDecision]
      : null;
  const isParkOnly = Boolean(payload.park_only);
  const strategicConditions = Array.isArray(payload.conditions)
    ? payload.conditions.filter((item): item is string => typeof item === 'string')
    : [];
  const proposedSlots = Array.isArray(payload.proposed_slots)
    ? (payload.proposed_slots as ProposedActivitySlot[])
    : [];
  const strategicWeeks =
    typeof payload.estimated_weeks === 'number' ? payload.estimated_weeks : null;
  const courseSubject = typeof payload.subject === 'string' ? payload.subject : null;
  const courseTotalLevels =
    typeof payload.total_levels === 'number' ? payload.total_levels : null;
  const courseLanguage = typeof payload.language === 'string' ? payload.language : null;
  const executedCourseId =
    proposal.executionResult && typeof proposal.executionResult.course_id === 'string'
      ? proposal.executionResult.course_id
      : null;
  const executionConfirmation =
    proposal.executionResult && typeof proposal.executionResult.confirmation === 'string'
      ? proposal.executionResult.confirmation
      : null;

  function openAdjustment() {
    setAdjustedTitle(initialTitle);
    setAdjustedPriority(initialPriority);
    setAdjustedGoal(initialGoal);
    setAdjustedFreq(initialFreq);
    setIsEditing(true);
  }

  function cancelAdjustment() {
    setIsEditing(false);
    setAdjustedTitle(initialTitle);
    setAdjustedPriority(initialPriority);
    setAdjustedGoal(initialGoal);
    setAdjustedFreq(initialFreq);
  }

  async function handleSaveModification() {
    if (!onUpdate || !isStrategicPlan) return;
    setPendingSubmit('update');
    try {
      const overrides: Record<string, unknown> = {};
      if (adjustedTitle.trim()) overrides.activity_title = adjustedTitle.trim();
      if (adjustedGoal.trim()) overrides.goal = adjustedGoal.trim();
      if (!isParkOnly) overrides.frequency_per_week = adjustedFreq;
      const ok = await onUpdate(proposal.id, overrides, !isParkOnly && adjustedFreq !== initialFreq);
      if (ok) {
        setIsEditing(false);
      }
    } finally {
      setPendingSubmit(null);
    }
  }

  async function handleAccept() {
    setPendingSubmit('accept');
    try {
      let overrides: Record<string, unknown> | undefined;
      if (isEditing) {
        overrides = {};
        if (isStrategicPlan) {
          if (adjustedTitle.trim()) overrides.activity_title = adjustedTitle.trim();
          if (adjustedGoal.trim()) overrides.goal = adjustedGoal.trim();
        } else {
          if (supportsTitleEdit && adjustedTitle.trim()) {
            overrides.title = adjustedTitle.trim();
          }
          if (supportsPriorityEdit) {
            overrides.priority = adjustedPriority;
          }
        }
      }
      const ok = await onAccept(proposal.id, overrides);
      if (ok) {
        setIsEditing(false);
      }
    } finally {
      setPendingSubmit(null);
    }
  }

  async function handleReject() {
    setPendingSubmit('reject');
    try {
      await onReject(proposal.id);
    } finally {
      setPendingSubmit(null);
    }
  }

  return (
    <article
      className={cn(
        'rounded-2xl p-4 transition-colors',
        isPending
          ? 'bg-amber-50/75 dark:bg-amber-950/30'
          : 'bg-zinc-50 dark:bg-zinc-800/70',
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2 text-xs font-medium text-zinc-600 dark:text-zinc-300">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-white text-teal-700 dark:bg-zinc-900 dark:text-teal-400">
            <Icon icon={actionMeta.icon} size={15} />
          </span>
          <span className="truncate">{actionMeta.label}</span>
        </div>
        <Badge variant={statusMeta.variant}>{statusMeta.label}</Badge>
      </div>

      <h4 className="mt-2.5 text-sm font-semibold leading-snug text-zinc-900 dark:text-zinc-100">
        {proposal.title}
      </h4>

      {proposal.explanation && (
        <p className="mt-1 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
          {proposal.explanation}
        </p>
      )}

      {(priorityMeta ||
        (startsAt && endsAt) ||
        skillName ||
        parkedTaskTitle ||
        (isCourseCreate && courseSubject)) && (
        <div className="mt-2.5 flex flex-wrap items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400">
          {priorityMeta && (
            <Badge variant={priorityMeta.badgeVariant}>Priorité : {priorityMeta.label}</Badge>
          )}
          {startsAt && endsAt && (
            <span className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-0.5 font-medium text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
              <Icon icon={Calendar03Icon} size={13} />
              {formatDateTimeFr(startsAt)} – {formatTimeFr(endsAt)}
            </span>
          )}
          {skillName && (
            <span className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-0.5 font-medium text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
              {skillName}
              {previousLevel !== null && nextLevel !== null
                ? ` · niveau ${previousLevel} → ${nextLevel}/5`
                : ''}
            </span>
          )}
          {parkedTaskTitle && (
            <span className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-0.5 font-medium text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
              Tâche : {parkedTaskTitle}
            </span>
          )}
          {isCourseCreate && courseSubject && (
            <>
              <Badge variant="primary">{courseSubject}</Badge>
              {courseTotalLevels !== null && (
                <Badge variant="neutral">{courseTotalLevels} niveaux</Badge>
              )}
              {courseLanguage && (
                <Badge variant="neutral">{courseLanguage.toUpperCase()}</Badge>
              )}
            </>
          )}
        </div>
      )}

      {hasConflict && (
        <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-100/80 px-3 py-2 text-xs text-amber-900 dark:bg-amber-950/60 dark:text-amber-200">
          <Icon icon={Alert02Icon} size={15} className="mt-0.5 shrink-0" />
          <span>
            Chevauchement détecté sur ce créneau
            {conflictingTitles.length > 0 ? ` (${conflictingTitles.join(', ')})` : '.'}
          </span>
        </div>
      )}

      {isStrategicPlan && (
        <div className="mt-3 space-y-2.5 rounded-xl bg-white/90 p-3 text-xs dark:bg-zinc-900/90">
          <div className="flex flex-wrap items-center gap-2">
            {strategicDecision && (
              <Badge variant={strategicDecision.variant}>{strategicDecision.label}</Badge>
            )}
            {strategicWeeks !== null && (
              <span className="text-zinc-500 dark:text-zinc-400">
                Horizon estimé : {strategicWeeks} semaine{strategicWeeks > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {initialGoal && (
            <p className="text-zinc-700 dark:text-zinc-300">
              <strong className="font-semibold">Objectif :</strong> {initialGoal}
            </p>
          )}

          {proposedSlots.length > 0 && (
            <ul className="space-y-1">
              {proposedSlots.map((slot, sIdx) => (
                <li
                  key={`${slot.local_date}-${slot.local_start_time}-${sIdx}`}
                  className="inline-flex w-full items-center justify-between gap-2 rounded-lg bg-zinc-50 px-2.5 py-1.5 text-[11px] font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                >
                  <span>
                    {slot.day_label} ({slot.local_date})
                  </span>
                  <span className="tabular-nums text-teal-700 dark:text-teal-300">
                    {slot.local_start_time}–{slot.local_end_time} ({slot.duration_minutes} min)
                  </span>
                </li>
              ))}
            </ul>
          )}

          {strategicConditions.length > 0 && (
            <div className="rounded-lg bg-amber-50/80 px-2.5 py-2 text-[11px] text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              <p className="font-semibold">Conditions / alertes stratégiques :</p>
              <ul className="mt-0.5 list-inside list-disc">
                {strategicConditions.map((cond, cIdx) => (
                  <li key={cIdx}>{cond}</li>
                ))}
              </ul>
            </div>
          )}

          {isPending && (
            <p className="text-[11px] italic text-zinc-500 dark:text-zinc-400">
              Cette proposition ne sera pas enregistrée tant que tu ne l’auras pas validée.
            </p>
          )}
        </div>
      )}

      {proposal.actionType === 'batch_actions' &&
        Array.isArray(payload.steps) &&
        payload.steps.length > 0 && (
          <div className="mt-3 rounded-xl bg-white/90 p-3 text-xs dark:bg-zinc-900/90">
            <p className="font-semibold text-zinc-800 dark:text-zinc-200">
              Actions coordonnées ({payload.steps.length} étapes) :
            </p>
            <ul className="mt-1.5 list-inside list-disc space-y-1 text-zinc-600 dark:text-zinc-300">
              {payload.steps.map((step, sIdx) => {
                const sObj =
                  step && typeof step === 'object' ? (step as Record<string, unknown>) : {};
                const sType = String(sObj.action_type ?? '');
                const sMeta = ACTION_META[sType]?.label ?? sType;
                const sPayload =
                  sObj.payload && typeof sObj.payload === 'object'
                    ? (sObj.payload as Record<string, unknown>)
                    : {};
                const sLabel = String(sPayload.title ?? sPayload.name ?? sPayload.goal ?? '');
                return (
                  <li key={sIdx}>
                    {sMeta}
                    {sLabel ? ` : ${sLabel}` : ''}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

      {proposal.status === 'executed' &&
        (() => {
          const entity =
            proposal.executionResult && typeof proposal.executionResult.entity === 'string'
              ? proposal.executionResult.entity
              : null;
          const navTarget: { to: string; label: string } | null = executedCourseId
            ? { to: `/courses/${executedCourseId}`, label: 'Ouvrir le cours' }
            : entity === 'task' || entity === 'parked_idea'
              ? { to: '/tasks', label: 'Voir dans Tâches' }
              : entity === 'project'
                ? { to: '/projects', label: 'Voir dans Projets' }
                : entity === 'personal_goal'
                  ? { to: '/objectives', label: 'Voir dans Objectifs' }
                  : entity === 'skill' || entity === 'skill_evidence' || entity === 'skill_assessment' || entity === 'skill_progression'
                    ? { to: '/skills', label: 'Voir dans Compétences' }
                    : entity === 'schedule_event' || entity === 'schedule_event_archived'
                      ? { to: '/planning', label: 'Voir dans Planning' }
                      : entity === 'study_session'
                        ? { to: '/sessions', label: 'Voir dans Séances' }
                        : entity === 'learning_path' || entity === 'strategic_activity'
                          ? { to: '/learning', label: 'Voir dans Apprentissage' }
                          : entity === 'preferences'
                            ? { to: '/settings', label: 'Voir dans Paramètres' }
                            : null;
          const summaryText =
            executionConfirmation ??
            (executedCourseId
              ? 'Cours créé avec le Niveau 1 débloqué.'
              : 'Opération enregistrée dans votre espace StudyOS.');
          if (!summaryText && !navTarget) return null;
          return (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-xs text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
              <span>{summaryText}</span>
              {navTarget && (
                <Link
                  to={navTarget.to}
                  className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-2.5 py-1 text-[11px] font-medium text-white transition-colors hover:bg-emerald-700 dark:bg-emerald-500 dark:text-zinc-950 dark:hover:bg-emerald-400"
                >
                  {navTarget.label}
                </Link>
              )}
            </div>
          );
        })()}

      {proposal.status === 'failed' && proposal.errorMessage && (
        <div className="mt-3 space-y-1 rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:bg-rose-950/40 dark:text-rose-200">
          <p>{proposal.errorMessage}</p>
          {Boolean(proposal.executionResult?.rolled_back) && (
            <p className="font-medium">
              Compensation automatique appliquée : aucune création partielle conservée.
            </p>
          )}
        </div>
      )}

      {isPending && isEditing && (
        <div className="mt-3 space-y-3 rounded-xl bg-white p-3 dark:bg-zinc-900">
          {(supportsTitleEdit || isStrategicPlan) && (
            <FormField
              label={
                isStrategicPlan
                  ? 'Modifier le titre de l’activité'
                  : 'Ajuster le titre avant validation'
              }
              id={`proposal-title-${proposal.id}`}
            >
              <Input
                id={`proposal-title-${proposal.id}`}
                value={adjustedTitle}
                onChange={(e) => setAdjustedTitle(e.target.value)}
              />
            </FormField>
          )}

          {isStrategicPlan && (
            <>
              <FormField
                label="Modifier l’objectif mesurable"
                id={`proposal-goal-${proposal.id}`}
              >
                <Input
                  id={`proposal-goal-${proposal.id}`}
                  value={adjustedGoal}
                  onChange={(e) => setAdjustedGoal(e.target.value)}
                />
              </FormField>

              {!isParkOnly && (
                <FormField
                  label="Fréquence hebdomadaire"
                  id={`proposal-freq-${proposal.id}`}
                >
                  <Select
                    id={`proposal-freq-${proposal.id}`}
                    value={String(adjustedFreq)}
                    onChange={(e) => setAdjustedFreq(Number(e.target.value))}
                  >
                    <option value="1">1 séance / semaine</option>
                    <option value="2">2 séances / semaine</option>
                    <option value="3">3 séances / semaine</option>
                  </Select>
                </FormField>
              )}

              {onUpdate && (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  isLoading={pendingSubmit === 'update'}
                  disabled={pendingSubmit !== null}
                  onClick={() => void handleSaveModification()}
                >
                  Recalculer & enregistrer la modification
                </Button>
              )}
            </>
          )}

          {supportsPriorityEdit && (
            <FormField
              label="Ajuster la priorité"
              id={`proposal-priority-${proposal.id}`}
            >
              <Select
                id={`proposal-priority-${proposal.id}`}
                value={adjustedPriority}
                onChange={(e) => setAdjustedPriority(e.target.value as TaskPriority)}
              >
                <option value="low">Basse</option>
                <option value="normal">Normale</option>
                <option value="high">Haute</option>
                <option value="critical">Critique</option>
              </Select>
            </FormField>
          )}
        </div>
      )}

      {isPending && (
        <div className="mt-3.5 flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="primary"
            size="sm"
            isLoading={pendingSubmit === 'accept'}
            disabled={pendingSubmit !== null}
            onClick={() => void handleAccept()}
          >
            <Icon icon={CheckmarkCircle02Icon} size={15} />
            {isStrategicPlan
              ? isParkOnly
                ? 'Placer au Parking'
                : 'Accepter et programmer'
              : 'Valider et exécuter'}
          </Button>

          {supportsAdjustment && !isEditing && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={pendingSubmit !== null}
              onClick={openAdjustment}
            >
              <Icon icon={PencilEdit02Icon} size={15} />
              {isStrategicPlan ? 'Modifier la proposition' : 'Ajuster'}
            </Button>
          )}

          {isEditing && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={pendingSubmit !== null}
              onClick={cancelAdjustment}
            >
              Annuler
            </Button>
          )}

          <Button
            type="button"
            variant="ghost"
            size="sm"
            isLoading={pendingSubmit === 'reject'}
            disabled={pendingSubmit !== null}
            onClick={() => void handleReject()}
            className="text-rose-700 hover:bg-rose-50 hover:text-rose-800 dark:text-rose-400 dark:hover:bg-rose-950/40 dark:hover:text-rose-300"
          >
            <Icon icon={CancelCircleIcon} size={15} />
            {isStrategicPlan ? 'Refuser' : 'Rejeter'}
          </Button>
        </div>
      )}
    </article>
  );
}
