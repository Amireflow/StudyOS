import {
  Add01Icon,
  Alert02Icon,
  Award02Icon,
  LinkSquare02Icon,
  PencilEdit02Icon,
  ShieldCheckIcon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { InlineConfirm } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { cn } from '../../lib/cn';
import { formatDateTimeFr } from '../../lib/date';
import type {
  SkillAssessmentCreateInput,
  SkillAssessmentSubmitInput,
} from '../../lib/learningApi';
import type {
  LearningModule,
  LearningPath,
  Lesson,
  Skill,
  SkillAssessment,
  SkillEvidence,
  SkillPedagogicalState,
} from '../../types/domain';
import { getRecommendedNextAction } from './assessmentEngine';
import { SkillAssessmentPanel } from './SkillAssessmentPanel';
import { EvidenceForm } from './SkillForms';
import {
  ASSESSMENT_STATUS_META,
  ASSESSMENT_TYPE_META,
  SKILL_EVIDENCE_TYPE_META,
  SKILL_LEVEL_META,
  SKILL_PEDAGOGICAL_STATE_META,
  type EvidenceFormValues,
} from './skillsSchema';

export interface SkillCardProps {
  skill: Skill;
  skillEvidence: SkillEvidence[];
  skillAssessments: SkillAssessment[];
  pedState: SkillPedagogicalState;
  linkedSessionsCount: number;
  paths: LearningPath[];
  modules: LearningModule[];
  lessons: Lesson[];
  initialPathId?: string | null;
  initialModuleId?: string | null;
  initialLessonId?: string | null;
  isPanelOpen: boolean;
  isHistoryOpen: boolean;
  isAddingEvidence: boolean;
  onTogglePanel: (skillId: string) => void;
  onClosePanel: () => void;
  onToggleHistory: (skillId: string) => void;
  onEdit: (skill: Skill) => void;
  onDelete: (skill: Skill) => Promise<void>;
  onOpenAddEvidence: (skillId: string) => void;
  onCloseAddEvidence: () => void;
  onAddEvidence: (skill: Skill, values: EvidenceFormValues) => Promise<void>;
  onDeleteEvidence: (skillId: string, evidenceId: string) => Promise<void>;
  onStartAssessment: (
    skillId: string,
    input: SkillAssessmentCreateInput,
  ) => Promise<SkillAssessment | null>;
  onRevealHint: (skillId: string, assessmentId: string) => Promise<boolean>;
  onSubmitAssessment: (
    skillId: string,
    assessmentId: string,
    input: SkillAssessmentSubmitInput,
  ) => Promise<boolean>;
  onEvaluateAssessment: (skillId: string, assessmentId: string) => Promise<boolean>;
  onValidateAssessment: (
    skillId: string,
    assessmentId: string,
    reason?: string,
  ) => Promise<boolean>;
  onRejectAssessment: (
    skillId: string,
    assessmentId: string,
    reason?: string,
  ) => Promise<boolean>;
  onCancelAssessment: (
    skillId: string,
    assessmentId: string,
    reason?: string,
  ) => Promise<boolean>;
  onFeedback: (message: string) => void;
}

export function SkillCard({
  skill,
  skillEvidence,
  skillAssessments,
  pedState,
  linkedSessionsCount,
  paths,
  modules,
  lessons,
  initialPathId = null,
  initialModuleId = null,
  initialLessonId = null,
  isPanelOpen,
  isHistoryOpen,
  isAddingEvidence,
  onTogglePanel,
  onClosePanel,
  onToggleHistory,
  onEdit,
  onDelete,
  onOpenAddEvidence,
  onCloseAddEvidence,
  onAddEvidence,
  onDeleteEvidence,
  onStartAssessment,
  onRevealHint,
  onSubmitAssessment,
  onEvaluateAssessment,
  onValidateAssessment,
  onRejectAssessment,
  onCancelAssessment,
  onFeedback,
}: SkillCardProps) {
  const levelMeta = SKILL_LEVEL_META[skill.currentLevel];
  const pedMeta = SKILL_PEDAGOGICAL_STATE_META[pedState];
  const hasEvidence = skillEvidence.length > 0;
  const needsEvidenceWarning = skill.currentLevel >= 3 && !hasEvidence;
  const isSubstantiated = skill.currentLevel >= 3 && hasEvidence;
  const target = skill.targetLevel ?? 0;

  const activeAssessment =
    skillAssessments.find(
      (a) =>
        a.status === 'pending' || a.status === 'submitted' || a.status === 'evaluated',
    ) ?? null;
  const latestAssessment = skillAssessments[0] ?? null;

  const nextActionText = getRecommendedNextAction(
    skill,
    pedState,
    skillAssessments,
    skillEvidence.length,
  );

  const filledClass = isSubstantiated
    ? 'bg-emerald-600 dark:bg-emerald-400'
    : needsEvidenceWarning
      ? 'bg-amber-500 dark:bg-amber-400'
      : 'bg-teal-600 dark:bg-teal-400';

  return (
    <article
      aria-label={skill.name}
      className="space-y-4 rounded-2xl bg-white p-5 dark:bg-zinc-900"
    >
      {/* En-tête & jauge 0–5 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 space-y-2.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <h3 className="line-clamp-1 text-sm font-semibold text-zinc-900 sm:text-base dark:text-zinc-50">
              {skill.name}
            </h3>
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
              {skill.domain}
            </span>
            <Badge variant={levelMeta.badgeVariant}>
              Niveau vérifié : {levelMeta.label}
            </Badge>
            <Badge variant={pedMeta.badgeVariant}>{pedMeta.label}</Badge>
            {isSubstantiated && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                <Icon icon={ShieldCheckIcon} size={12} />
                Étayée
              </span>
            )}
            {linkedSessionsCount > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                <Icon icon={Timer02Icon} size={12} />
                {linkedSessionsCount} séance{linkedSessionsCount > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {skill.description && (
            <p className="line-clamp-2 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
              {skill.description}
            </p>
          )}

          <div className="space-y-1.5">
            <div aria-hidden="true" className="flex max-w-xs items-center gap-1.5">
              {[1, 2, 3, 4, 5].map((segment) => (
                <span
                  key={segment}
                  className={cn(
                    'h-2 flex-1 rounded-full',
                    segment <= skill.currentLevel
                      ? filledClass
                      : segment <= target
                        ? 'bg-teal-100 dark:bg-teal-950/60'
                        : 'bg-zinc-100 dark:bg-zinc-800',
                  )}
                />
              ))}
            </div>
            {skill.targetLevel !== null && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Cible : {skill.targetLevel}/5
              </p>
            )}
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => onTogglePanel(skill.id)}
          >
            <Icon icon={Award02Icon} size={14} />
            Évaluer cette compétence
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => onEdit(skill)}>
            <Icon icon={PencilEdit02Icon} size={14} />
            Modifier
          </Button>
          <InlineConfirm
            triggerLabel="Supprimer"
            ariaLabel={`Supprimer la compétence ${skill.name}`}
            onConfirm={() => void onDelete(skill)}
          />
        </div>
      </div>

      {/* Prochaine action recommandée & dernière évaluation */}
      <div className="flex flex-col gap-2 rounded-xl bg-zinc-50/90 p-3 text-xs sm:flex-row sm:items-center sm:justify-between dark:bg-zinc-800/55">
        <div className="min-w-0 space-y-0.5">
          <p className="line-clamp-1 font-medium text-zinc-900 dark:text-zinc-100">
            Prochaine étape :{' '}
            <span className="font-normal text-zinc-600 dark:text-zinc-300">
              {nextActionText}
            </span>
          </p>
          <p className="line-clamp-1 text-zinc-500 dark:text-zinc-400">
            {latestAssessment
              ? `${ASSESSMENT_STATUS_META[latestAssessment.status].label}${
                  latestAssessment.score !== null ? ` (${latestAssessment.score}/100)` : ''
                } · ${formatDateTimeFr(latestAssessment.createdAt)}`
              : 'Aucune évaluation réalisée'}
          </p>
        </div>

        {skillAssessments.length > 0 && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onToggleHistory(skill.id)}
          >
            {isHistoryOpen
              ? 'Masquer l’historique'
              : `Historique des évaluations (${skillAssessments.length})`}
          </Button>
        )}
      </div>

      {/* Alerte SKILL-03 */}
      {needsEvidenceWarning && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950/50 dark:text-amber-200"
        >
          <Icon
            icon={Alert02Icon}
            size={16}
            className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-300"
          />
          <p>
            <strong>Alerte SKILL-03 :</strong> niveau {skill.currentLevel}/5 déclaré sans preuve
            associée.
          </p>
        </div>
      )}

      {/* Panneau d'évaluation interactif */}
      {isPanelOpen && (
        <SkillAssessmentPanel
          skill={skill}
          activeAssessment={activeAssessment}
          skillEvidence={skillEvidence}
          paths={paths}
          modules={modules}
          lessons={lessons}
          initialPathId={initialPathId}
          initialModuleId={initialModuleId}
          initialLessonId={initialLessonId}
          onStartAssessment={onStartAssessment}
          onRevealHint={onRevealHint}
          onSubmitAssessment={onSubmitAssessment}
          onEvaluateAssessment={onEvaluateAssessment}
          onValidateAssessment={onValidateAssessment}
          onRejectAssessment={onRejectAssessment}
          onCancelAssessment={onCancelAssessment}
          onFeedback={onFeedback}
          onClose={onClosePanel}
        />
      )}

      {/* Historique des évaluations */}
      {isHistoryOpen && skillAssessments.length > 0 && (
        <div className="space-y-2 rounded-xl bg-zinc-50 p-3.5 text-xs dark:bg-zinc-800/70">
          <h4 className="font-semibold text-zinc-900 dark:text-zinc-100">
            Historique des évaluations ({skillAssessments.length})
          </h4>
          <ul className="space-y-2">
            {skillAssessments.map((item) => {
              const itemStatus = ASSESSMENT_STATUS_META[item.status];
              const itemType = ASSESSMENT_TYPE_META[item.assessmentType];
              return (
                <li
                  key={item.id}
                  className="space-y-1 rounded-xl bg-white p-3 dark:bg-zinc-900"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                        {item.promptTitle}
                      </span>
                      <Badge variant={itemStatus.badgeVariant}>{itemStatus.label}</Badge>
                      <Badge variant="neutral">{itemType.label}</Badge>
                      {item.score !== null && (
                        <Badge variant={item.passed ? 'success' : 'danger'}>
                          Score : {item.score}/100
                        </Badge>
                      )}
                    </div>
                    <span className="text-zinc-500 dark:text-zinc-400">
                      {formatDateTimeFr(item.createdAt)}
                    </span>
                  </div>
                  {item.feedback && (
                    <p className="whitespace-pre-line text-zinc-600 dark:text-zinc-300">
                      {item.feedback}
                    </p>
                  )}
                  {item.decisionReason && (
                    <p className="text-zinc-500 dark:text-zinc-400">
                      Décision : {item.decisionReason}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Section Preuves */}
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Preuves ({skillEvidence.length})
          </h4>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => onOpenAddEvidence(skill.id)}
          >
            <Icon icon={Add01Icon} size={14} />
            Ajouter une preuve
          </Button>
        </div>

        {isAddingEvidence && (
          <EvidenceForm
            skillId={skill.id}
            onSubmit={(values) => onAddEvidence(skill, values)}
            onCancel={onCloseAddEvidence}
          />
        )}

        {skillEvidence.length === 0 ? (
          <p className="rounded-xl bg-zinc-50/80 p-3 text-xs text-zinc-500 dark:bg-zinc-800/60 dark:text-zinc-400">
            Aucune preuve enregistrée.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {skillEvidence.map((item) => {
              const typeMeta = SKILL_EVIDENCE_TYPE_META[item.type];
              return (
                <li
                  key={item.id}
                  className="flex flex-col gap-2 rounded-xl bg-zinc-50/90 px-3.5 py-2.5 sm:flex-row sm:items-start sm:justify-between dark:bg-zinc-800/55"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={typeMeta.badgeVariant}>{typeMeta.label}</Badge>
                      <span className="text-xs text-zinc-500 dark:text-zinc-400">
                        {formatDateTimeFr(item.observedAt)}
                      </span>
                      {item.result && <Badge variant="success">{item.result}</Badge>}
                    </div>
                    <p className="text-sm text-zinc-800 dark:text-zinc-100">{item.description}</p>
                    {item.referenceUrl && (
                      <div className="space-y-0.5">
                        <a
                          href={item.referenceUrl}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="inline-flex items-center gap-1 text-xs font-medium text-teal-800 hover:underline dark:text-teal-300"
                        >
                          Consulter la preuve
                          <Icon icon={LinkSquare02Icon} size={12} />
                        </a>
                        {item.verificationNote && (
                          <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                            {item.verificationNote}
                          </p>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="shrink-0 self-end sm:self-start">
                    <InlineConfirm
                      triggerLabel="Retirer"
                      ariaLabel={`Supprimer la preuve ${item.description}`}
                      onConfirm={() => void onDeleteEvidence(skill.id, item.id)}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </article>
  );
}
