import { useState } from 'react';
import {
  Alert02Icon,
  Award02Icon,
  Calendar03Icon,
  CancelCircleIcon,
  CheckmarkCircle02Icon,
  CheckmarkSquare02Icon,
  PencilEdit02Icon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { Badge, type BadgeVariant } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select } from '../../components/ui/FormFields';
import { Icon, type IconSvgElement } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { formatDateTimeFr, formatTimeFr } from '../../lib/date';
import type { AiActionProposal, ProposalStatus, TaskPriority } from '../../types/domain';
import { TASK_PRIORITY_META } from '../tasks/taskUtils';

const ACTION_META: Record<string, { label: string; icon: IconSvgElement }> = {
  create_task: { label: 'Nouvelle tâche', icon: CheckmarkSquare02Icon },
  park_task: { label: 'Mise au parking', icon: Timer02Icon },
  create_schedule_event: { label: 'Créneau planning', icon: Calendar03Icon },
  add_skill_evidence: { label: 'Preuve de compétence', icon: Award02Icon },
  update_skill_level: { label: 'Niveau de compétence', icon: Award02Icon },
};

const PROPOSAL_STATUS_META: Record<ProposalStatus, { label: string; variant: BadgeVariant }> = {
  pending: { label: 'En attente de validation', variant: 'warning' },
  accepted: { label: 'Acceptée', variant: 'primary' },
  executed: { label: 'Exécutée', variant: 'success' },
  rejected: { label: 'Rejetée', variant: 'danger' },
  expired: { label: 'Expirée', variant: 'neutral' },
  failed: { label: 'Échec', variant: 'danger' },
};

const SKILL_LEVEL_OPTIONS = [
  { value: '0', label: '0 — Non évalué' },
  { value: '1', label: '1 — Découverte' },
  { value: '2', label: '2 — Notions' },
  { value: '3', label: '3 — Autonome' },
  { value: '4', label: '4 — Solide' },
  { value: '5', label: '5 — Maîtrise' },
];

interface ProposalCardProps {
  proposal: AiActionProposal;
  onAccept: (proposalId: string, payloadOverrides?: Record<string, unknown>) => Promise<boolean>;
  onReject: (proposalId: string) => Promise<boolean>;
}

function isTaskPriority(value: unknown): value is TaskPriority {
  return value === 'low' || value === 'normal' || value === 'high' || value === 'critical';
}

export function ProposalCard({ proposal, onAccept, onReject }: ProposalCardProps) {
  const payload = proposal.payload ?? {};
  const actionMeta = ACTION_META[proposal.actionType] ?? {
    label: 'Action suggérée',
    icon: CheckmarkSquare02Icon,
  };
  const statusMeta = PROPOSAL_STATUS_META[proposal.status];

  const isPending = proposal.status === 'pending';
  const supportsTitleEdit =
    proposal.actionType === 'create_task' || proposal.actionType === 'create_schedule_event';
  const supportsPriorityEdit = proposal.actionType === 'create_task';
  const supportsSkillLevelEdit = proposal.actionType === 'update_skill_level';
  const supportsAdjustment = supportsTitleEdit || supportsSkillLevelEdit;

  const initialTitle =
    typeof payload.title === 'string' && payload.title.trim() ? payload.title : proposal.title;
  const initialPriority: TaskPriority = isTaskPriority(payload.priority)
    ? payload.priority
    : 'normal';
  const initialLevel =
    typeof payload.current_level === 'number' ? String(payload.current_level) : '1';

  const [isEditing, setIsEditing] = useState(false);
  const [adjustedTitle, setAdjustedTitle] = useState(initialTitle);
  const [adjustedPriority, setAdjustedPriority] = useState<TaskPriority>(initialPriority);
  const [adjustedLevel, setAdjustedLevel] = useState(initialLevel);
  const [pendingSubmit, setPendingSubmit] = useState<'accept' | 'reject' | null>(null);

  const priorityMeta = isTaskPriority(payload.priority)
    ? TASK_PRIORITY_META[payload.priority]
    : null;
  const startsAt = typeof payload.starts_at === 'string' ? payload.starts_at : null;
  const endsAt = typeof payload.ends_at === 'string' ? payload.ends_at : null;
  const skillName = typeof payload.skill_name === 'string' ? payload.skill_name : null;
  const previousLevel = typeof payload.previous_level === 'number' ? payload.previous_level : null;
  const nextLevel = typeof payload.current_level === 'number' ? payload.current_level : null;
  const parkedTaskTitle = typeof payload.task_title === 'string' ? payload.task_title : null;
  const hasConflict = Boolean(payload.has_conflict);
  const conflictingTitles = Array.isArray(payload.conflicting_titles)
    ? payload.conflicting_titles.filter((item): item is string => typeof item === 'string')
    : [];

  function openAdjustment() {
    setAdjustedTitle(initialTitle);
    setAdjustedPriority(initialPriority);
    setAdjustedLevel(initialLevel);
    setIsEditing(true);
  }

  function cancelAdjustment() {
    setIsEditing(false);
    setAdjustedTitle(initialTitle);
    setAdjustedPriority(initialPriority);
    setAdjustedLevel(initialLevel);
  }

  async function handleAccept() {
    setPendingSubmit('accept');
    try {
      let overrides: Record<string, unknown> | undefined;
      if (isEditing) {
        overrides = {};
        if (supportsTitleEdit && adjustedTitle.trim()) {
          overrides.title = adjustedTitle.trim();
        }
        if (supportsPriorityEdit) {
          overrides.priority = adjustedPriority;
        }
        if (supportsSkillLevelEdit) {
          overrides.current_level = Number(adjustedLevel);
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

      {(priorityMeta || (startsAt && endsAt) || skillName || parkedTaskTitle) && (
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

      {proposal.status === 'failed' && proposal.errorMessage && (
        <div className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:bg-rose-950/40 dark:text-rose-200">
          {proposal.errorMessage}
        </div>
      )}

      {isPending && isEditing && (
        <div className="mt-3 space-y-3 rounded-xl bg-white p-3 dark:bg-zinc-900">
          {supportsTitleEdit && (
            <FormField
              label="Ajuster le titre avant validation"
              id={`proposal-title-${proposal.id}`}
            >
              <Input
                id={`proposal-title-${proposal.id}`}
                value={adjustedTitle}
                onChange={(e) => setAdjustedTitle(e.target.value)}
              />
            </FormField>
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

          {supportsSkillLevelEdit && (
            <FormField
              label="Niveau validé (0 à 5)"
              id={`proposal-level-${proposal.id}`}
            >
              <Select
                id={`proposal-level-${proposal.id}`}
                value={adjustedLevel}
                onChange={(e) => setAdjustedLevel(e.target.value)}
              >
                {SKILL_LEVEL_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
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
            Valider et exécuter
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
              Ajuster
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
            Rejeter
          </Button>
        </div>
      )}
    </article>
  );
}
