import { useState, type FormEvent } from 'react';
import {
  Alert02Icon,
  Award02Icon,
  CancelCircleIcon,
  CheckmarkCircle02Icon,
  InformationCircleIcon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
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
  SkillAssessmentType,
  SkillEvidence,
  SkillEvidenceType,
  SkillLevel,
} from '../../types/domain';
import { validateEvidenceQualityLocal } from './assessmentEngine';
import {
  ASSESSMENT_STATUS_META,
  ASSESSMENT_TYPE_META,
  SKILL_EVIDENCE_TYPE_META,
  SKILL_LEVEL_META,
} from './skillsSchema';

export interface SkillAssessmentPanelProps {
  skill: Skill;
  activeAssessment: SkillAssessment | null;
  skillEvidence: SkillEvidence[];
  paths: LearningPath[];
  modules: LearningModule[];
  lessons: Lesson[];
  initialPathId?: string | null;
  initialModuleId?: string | null;
  initialLessonId?: string | null;
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
  onClose: () => void;
}

export function SkillAssessmentPanel({
  skill,
  activeAssessment,
  skillEvidence,
  paths,
  modules,
  lessons,
  initialPathId = null,
  initialModuleId = null,
  initialLessonId = null,
  onStartAssessment,
  onRevealHint,
  onSubmitAssessment,
  onEvaluateAssessment,
  onValidateAssessment,
  onRejectAssessment,
  onCancelAssessment,
  onFeedback,
  onClose,
}: SkillAssessmentPanelProps) {
  const defaultTargetLevel = Math.min(5, Math.max(1, skill.currentLevel + 1)) as SkillLevel;
  const [targetLevel, setTargetLevel] = useState<SkillLevel>(defaultTargetLevel);
  const [assessmentType, setAssessmentType] =
    useState<SkillAssessmentType>('practical_exercise');
  const [selectedPathId, setSelectedPathId] = useState<string>(initialPathId ?? '');
  const [selectedModuleId, setSelectedModuleId] = useState<string>(initialModuleId ?? '');
  const [selectedLessonId, setSelectedLessonId] = useState<string>(initialLessonId ?? '');

  const [submissionText, setSubmissionText] = useState('');
  const [submissionCode, setSubmissionCode] = useState('');
  const [submissionReferenceUrl, setSubmissionReferenceUrl] = useState('');
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<string[]>(() =>
    skillEvidence.slice(0, 1).map((ev) => ev.id),
  );
  const [createInlineEvidence, setCreateInlineEvidence] = useState<boolean>(
    skillEvidence.length === 0,
  );
  const [inlineEvidenceType, setInlineEvidenceType] =
    useState<SkillEvidenceType>('exercise');
  const [inlineEvidenceDesc, setInlineEvidenceDesc] = useState('');
  const [inlineEvidenceResult, setInlineEvidenceResult] = useState('');
  const [localFormError, setLocalFormError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const availableTargetLevels = ([1, 2, 3, 4, 5] as SkillLevel[]).filter(
    (lvl) => lvl >= Math.max(1, skill.currentLevel),
  );

  const filteredModules = selectedPathId
    ? modules.filter((m) => m.pathId === selectedPathId)
    : modules;
  const filteredLessons = selectedModuleId
    ? lessons.filter((l) => l.moduleId === selectedModuleId)
    : lessons;

  const toggleEvidenceId = (id: string) => {
    setSelectedEvidenceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const handleStart = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalFormError(null);
    setIsBusy(true);
    try {
      const created = await onStartAssessment(skill.id, {
        targetLevel,
        assessmentType,
        pathId: selectedPathId || null,
        moduleId: selectedModuleId || null,
        lessonId: selectedLessonId || null,
      });
      if (created) {
        onFeedback(
          `Évaluation « ${created.promptTitle} » ouverte pour « ${skill.name} ».`,
        );
      }
    } finally {
      setIsBusy(false);
    }
  };

  const handleSubmitProduction = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!activeAssessment) return;
    setLocalFormError(null);

    const trimmedText = submissionText.trim();
    if (trimmedText.length < 15) {
      setLocalFormError(
        'Votre réponse et explication du raisonnement doivent contenir au moins 15 caractères.',
      );
      return;
    }

    const trimmedRef = submissionReferenceUrl.trim();
    if (trimmedRef && !/^https?:\/\/\S+$/i.test(trimmedRef)) {
      setLocalFormError('L’URL de référence doit commencer par http:// ou https://.');
      return;
    }

    let newEvidencePayload: SkillAssessmentSubmitInput['newEvidence'];
    if (createInlineEvidence && inlineEvidenceDesc.trim()) {
      const q = validateEvidenceQualityLocal(
        inlineEvidenceDesc,
        trimmedRef || null,
        inlineEvidenceResult,
      );
      if (!q.admissible) {
        setLocalFormError(
          q.reason ??
            'La preuve associée est trop vague. Décrivez l’exercice, le code ou le résultat obtenu.',
        );
        return;
      }
      newEvidencePayload = {
        type: inlineEvidenceType,
        description: inlineEvidenceDesc.trim(),
        referenceUrl: trimmedRef || undefined,
        result: inlineEvidenceResult.trim() || undefined,
      };
    }

    setIsBusy(true);
    try {
      const ok = await onSubmitAssessment(skill.id, activeAssessment.id, {
        submissionText: trimmedText,
        submissionCode: submissionCode.trim() || undefined,
        submissionReferenceUrl: trimmedRef || undefined,
        evidenceIds: selectedEvidenceIds,
        newEvidence: newEvidencePayload,
      });
      if (ok) {
        onFeedback(`Production soumise pour « ${skill.name} ». Lancez maintenant la correction.`);
      }
    } finally {
      setIsBusy(false);
    }
  };

  const handleRunEvaluation = async () => {
    if (!activeAssessment) return;
    setLocalFormError(null);
    setIsBusy(true);
    try {
      const ok = await onEvaluateAssessment(skill.id, activeAssessment.id);
      if (ok) {
        onFeedback(`Correction terminée pour « ${skill.name} ».`);
      }
    } finally {
      setIsBusy(false);
    }
  };

  const handleValidate = async () => {
    if (!activeAssessment) return;
    setLocalFormError(null);
    setIsBusy(true);
    try {
      const ok = await onValidateAssessment(skill.id, activeAssessment.id);
      if (ok) {
        onFeedback(
          `Progression validée : « ${skill.name} » passe au niveau ${activeAssessment.proposedLevel ?? activeAssessment.targetLevel}/5.`,
        );
        onClose();
      }
    } finally {
      setIsBusy(false);
    }
  };

  const handleReject = async () => {
    if (!activeAssessment) return;
    setLocalFormError(null);
    setIsBusy(true);
    try {
      const ok = await onRejectAssessment(
        skill.id,
        activeAssessment.id,
        'Évaluation clôturée sans progression de niveau.',
      );
      if (ok) {
        onFeedback(`Évaluation non validée : le niveau de « ${skill.name} » reste à ${skill.currentLevel}/5.`);
      }
    } finally {
      setIsBusy(false);
    }
  };

  const handleStartRemediation = async () => {
    if (!activeAssessment) return;
    setLocalFormError(null);
    setIsBusy(true);
    try {
      if (
        activeAssessment.status === 'evaluated' ||
        activeAssessment.status === 'submitted' ||
        activeAssessment.status === 'needs_manual_review'
      ) {
        await onRejectAssessment(
          skill.id,
          activeAssessment.id,
          'Passage à un exercice correctif ciblé sur les lacunes.',
        );
      }
      const next = await onStartAssessment(skill.id, {
        targetLevel: activeAssessment.targetLevel,
        assessmentType: activeAssessment.assessmentType,
        pathId: activeAssessment.pathId,
        moduleId: activeAssessment.moduleId,
        lessonId: activeAssessment.lessonId,
      });
      if (next) {
        setSubmissionText('');
        setSubmissionCode('');
        setSubmissionReferenceUrl('');
        setInlineEvidenceDesc('');
        setInlineEvidenceResult('');
        setCreateInlineEvidence(true);
        onFeedback(`Exercice correctif prêt pour « ${skill.name} ».`);
      }
    } finally {
      setIsBusy(false);
    }
  };

  const handleCancel = async () => {
    if (!activeAssessment) return;
    setLocalFormError(null);
    setIsBusy(true);
    try {
      const ok = await onCancelAssessment(skill.id, activeAssessment.id);
      if (ok) {
        onFeedback(`Évaluation annulée pour « ${skill.name} ».`);
        onClose();
      }
    } finally {
      setIsBusy(false);
    }
  };

  // Vue 1 : Configuration d'une nouvelle évaluation
  if (!activeAssessment) {
    return (
      <section
        aria-label={`Nouvelle évaluation pédagogique — ${skill.name}`}
        className="space-y-4 rounded-2xl bg-teal-50/50 p-4 dark:bg-teal-950/20"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Icon icon={Award02Icon} size={17} className="text-teal-700 dark:text-teal-400" />
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
              Nouvelle évaluation pédagogique — {skill.name}
            </h3>
          </div>
          <Badge variant="neutral">Niveau actuel vérifié : {skill.currentLevel}/5</Badge>
        </div>

        <form onSubmit={handleStart} noValidate className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField id={`assess-target-${skill.id}`} label="Niveau visé">
              <Select
                id={`assess-target-${skill.id}`}
                value={String(targetLevel)}
                onChange={(e) => setTargetLevel(Number(e.target.value) as SkillLevel)}
              >
                {availableTargetLevels.map((lvl) => (
                  <option key={lvl} value={String(lvl)}>
                    {SKILL_LEVEL_META[lvl].label}
                  </option>
                ))}
              </Select>
            </FormField>

            <FormField id={`assess-type-${skill.id}`} label="Type d’épreuve">
              <Select
                id={`assess-type-${skill.id}`}
                value={assessmentType}
                onChange={(e) => setAssessmentType(e.target.value as SkillAssessmentType)}
              >
                {(Object.keys(ASSESSMENT_TYPE_META) as SkillAssessmentType[]).map((typeKey) => (
                  <option key={typeKey} value={typeKey}>
                    {ASSESSMENT_TYPE_META[typeKey].label}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>

          {paths.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-3">
              <FormField id={`assess-path-${skill.id}`} label="Parcours associé (facultatif)">
                <Select
                  id={`assess-path-${skill.id}`}
                  value={selectedPathId}
                  onChange={(e) => {
                    setSelectedPathId(e.target.value);
                    setSelectedModuleId('');
                    setSelectedLessonId('');
                  }}
                >
                  <option value="">Aucun parcours</option>
                  {paths.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title}
                    </option>
                  ))}
                </Select>
              </FormField>

              <FormField id={`assess-mod-${skill.id}`} label="Module associé (facultatif)">
                <Select
                  id={`assess-mod-${skill.id}`}
                  value={selectedModuleId}
                  onChange={(e) => {
                    setSelectedModuleId(e.target.value);
                    setSelectedLessonId('');
                  }}
                >
                  <option value="">Aucun module</option>
                  {filteredModules.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.title}
                    </option>
                  ))}
                </Select>
              </FormField>

              <FormField id={`assess-lesson-${skill.id}`} label="Leçon associée (facultatif)">
                <Select
                  id={`assess-lesson-${skill.id}`}
                  value={selectedLessonId}
                  onChange={(e) => setSelectedLessonId(e.target.value)}
                >
                  <option value="">Aucune leçon</option>
                  {filteredLessons.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.title}
                    </option>
                  ))}
                </Select>
              </FormField>
            </div>
          )}

          <div className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="secondary" size="sm" onClick={onClose}>
              Fermer
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isBusy}>
              Générer l’épreuve
            </Button>
          </div>
        </form>
      </section>
    );
  }

  const statusMeta = ASSESSMENT_STATUS_META[activeAssessment.status];
  const typeMeta = ASSESSMENT_TYPE_META[activeAssessment.assessmentType];

  return (
    <section
      aria-label={`Évaluation en cours pour ${skill.name}`}
      className="space-y-4 rounded-2xl bg-zinc-50 p-4 dark:bg-zinc-800/70"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
              {activeAssessment.promptTitle}
            </h3>
            <Badge variant={statusMeta.badgeVariant}>{statusMeta.label}</Badge>
            <Badge variant="neutral">{typeMeta.label}</Badge>
            <Badge variant="primary">
              Niveau {activeAssessment.startingLevel}/5 → {activeAssessment.targetLevel}/5
            </Badge>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Créée le {formatDateTimeFr(activeAssessment.createdAt)}
          </p>
        </div>

        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          Masquer
        </Button>
      </div>

      {/* Énoncé et critères */}
      <div className="space-y-2.5 rounded-xl bg-white p-3.5 text-xs dark:bg-zinc-900">
        <p className="font-semibold text-zinc-900 dark:text-zinc-100">Consignes de l’épreuve</p>
        <p className="whitespace-pre-line leading-relaxed text-zinc-700 dark:text-zinc-300">
          {activeAssessment.promptInstructions}
        </p>

        <div className="pt-1">
          <p className="font-semibold text-zinc-800 dark:text-zinc-200">
            Grille de critères explicites (100 points) :
          </p>
          <ul className="mt-1 grid gap-1.5 sm:grid-cols-2">
            {activeAssessment.criteria.map((c) => (
              <li
                key={c.key}
                className="rounded-lg bg-zinc-50 px-2.5 py-1.5 text-zinc-600 dark:bg-zinc-800/70 dark:text-zinc-300"
              >
                <span className="font-medium text-zinc-900 dark:text-zinc-100">{c.label}</span> (
                {c.maxScore} pts) — {c.description}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {localFormError && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-xl bg-rose-50 p-3 text-xs text-rose-800 dark:bg-rose-950/40 dark:text-rose-200"
        >
          <Icon icon={Alert02Icon} size={15} className="mt-0.5 shrink-0" />
          <span>{localFormError}</span>
        </div>
      )}

      {/* Étape PENDING : Indices progressifs & formulaire de soumission */}
      {activeAssessment.status === 'pending' && (
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
                Accompagnement progressif ({activeAssessment.hintsRevealedCount}/
                {activeAssessment.hintsTotal} indice(s) dévoilé(s))
              </span>
              {activeAssessment.hintsRevealedCount < activeAssessment.hintsTotal && (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void onRevealHint(skill.id, activeAssessment.id)}
                >
                  Afficher un indice ({activeAssessment.hintsRevealedCount + 1}/
                  {activeAssessment.hintsTotal})
                </Button>
              )}
            </div>

            {activeAssessment.revealedHints.length > 0 && (
              <ul className="space-y-1.5">
                {activeAssessment.revealedHints.map((hint, idx) => (
                  <li
                    key={`${activeAssessment.id}-hint-${idx}`}
                    className="rounded-xl bg-teal-50/70 px-3 py-2 text-xs text-teal-950 dark:bg-teal-950/40 dark:text-teal-200"
                  >
                    {hint}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <form onSubmit={handleSubmitProduction} noValidate className="space-y-3">
            <FormField
              id={`sub-text-${activeAssessment.id}`}
              label="Votre production et explication du raisonnement"
              required
            >
              <Textarea
                id={`sub-text-${activeAssessment.id}`}
                value={submissionText}
                placeholder="Expliquez votre solution, le raisonnement (« parce que… »), les cas nominaux et les cas d’erreur vérifiés…"
                onChange={(e) => setSubmissionText(e.target.value)}
              />
            </FormField>

            <FormField
              id={`sub-code-${activeAssessment.id}`}
              label="Code source, requête ou commande exécutée (facultatif)"
            >
              <Textarea
                id={`sub-code-${activeAssessment.id}`}
                value={submissionCode}
                className="font-mono text-xs"
                placeholder="def exemple(): ..."
                onChange={(e) => setSubmissionCode(e.target.value)}
              />
            </FormField>

            <FormField
              id={`sub-url-${activeAssessment.id}`}
              label="Référence vers un dépôt ou document externe (facultatif)"
            >
              <Input
                id={`sub-url-${activeAssessment.id}`}
                type="url"
                value={submissionReferenceUrl}
                placeholder="https://github.com/..."
                onChange={(e) => setSubmissionReferenceUrl(e.target.value)}
              />
            </FormField>

            {/* Association de preuves */}
            <div className="space-y-2.5 rounded-xl bg-white p-3.5 dark:bg-zinc-900">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                  Preuves concrètes associées à cette évaluation
                </p>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setCreateInlineEvidence((prev) => !prev)}
                >
                  {createInlineEvidence
                    ? 'Masquer la création de preuve'
                    : 'Créer une nouvelle preuve'}
                </Button>
              </div>

              {skillEvidence.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    Sélectionnez parmi vos preuves existantes sur « {skill.name} » :
                  </p>
                  {skillEvidence.map((ev) => (
                    <label
                      key={ev.id}
                      className="flex cursor-pointer items-start gap-2 rounded-lg bg-zinc-50 px-3 py-2 text-xs dark:bg-zinc-800/70"
                    >
                      <input
                        type="checkbox"
                        checked={selectedEvidenceIds.includes(ev.id)}
                        onChange={() => toggleEvidenceId(ev.id)}
                        className="mt-0.5"
                      />
                      <span className="text-zinc-800 dark:text-zinc-200">
                        <strong>{SKILL_EVIDENCE_TYPE_META[ev.type].label}</strong> —{' '}
                        {ev.description}
                        {ev.result ? ` (${ev.result})` : ''}
                      </span>
                    </label>
                  ))}
                </div>
              )}

              {createInlineEvidence && (
                <div className="space-y-2.5 pt-1">
                  <div className="grid gap-2.5 sm:grid-cols-2">
                    <FormField id={`inline-ev-type-${activeAssessment.id}`} label="Type de preuve">
                      <Select
                        id={`inline-ev-type-${activeAssessment.id}`}
                        value={inlineEvidenceType}
                        onChange={(e) =>
                          setInlineEvidenceType(e.target.value as SkillEvidenceType)
                        }
                      >
                        {(Object.keys(SKILL_EVIDENCE_TYPE_META) as SkillEvidenceType[]).map(
                          (typeKey) => (
                            <option key={typeKey} value={typeKey}>
                              {SKILL_EVIDENCE_TYPE_META[typeKey].label}
                            </option>
                          ),
                        )}
                      </Select>
                    </FormField>

                    <FormField
                      id={`inline-ev-res-${activeAssessment.id}`}
                      label="Résultat mesurable (facultatif)"
                    >
                      <Input
                        id={`inline-ev-res-${activeAssessment.id}`}
                        value={inlineEvidenceResult}
                        placeholder="Ex. 4 tests Pytest passants"
                        onChange={(e) => setInlineEvidenceResult(e.target.value)}
                      />
                    </FormField>
                  </div>

                  <FormField
                    id={`inline-ev-desc-${activeAssessment.id}`}
                    label="Description concrète de la preuve produite"
                  >
                    <Input
                      id={`inline-ev-desc-${activeAssessment.id}`}
                      value={inlineEvidenceDesc}
                      placeholder="Ex. Implémentation de la fonction avec tests unitaires sur cas limites"
                      onChange={(e) => setInlineEvidenceDesc(e.target.value)}
                    />
                  </FormField>
                </div>
              )}
            </div>

            <div className="flex flex-wrap justify-between gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => void handleCancel()}
              >
                Abandonner l’évaluation
              </Button>
              <Button type="submit" variant="primary" size="sm" isLoading={isBusy}>
                Soumettre ma production
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Étape SUBMITTED : Production enregistrée, prête pour évaluation */}
      {activeAssessment.status === 'submitted' && (
        <div className="space-y-3">
          <div className="space-y-2 rounded-xl bg-white p-3.5 text-xs dark:bg-zinc-900">
            <p className="font-semibold text-zinc-900 dark:text-zinc-100">Production soumise</p>
            <p className="whitespace-pre-line text-zinc-700 dark:text-zinc-300">
              {activeAssessment.submissionText}
            </p>
            {activeAssessment.submissionCode && (
              <pre className="overflow-x-auto rounded-lg bg-zinc-900 p-2.5 font-mono text-[11px] text-zinc-100">
                {activeAssessment.submissionCode}
              </pre>
            )}
            <p className="text-zinc-500 dark:text-zinc-400">
              Preuves associées : {activeAssessment.evidenceIds.length}
            </p>
          </div>

          {activeAssessment.externalVerificationWarning && (
            <div className="flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              <Icon icon={InformationCircleIcon} size={15} className="mt-0.5 shrink-0" />
              <span>{activeAssessment.externalVerificationWarning}</span>
            </div>
          )}

          <div className="flex flex-wrap justify-between gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => void handleCancel()}>
              Abandonner l’évaluation
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              isLoading={isBusy}
              onClick={() => void handleRunEvaluation()}
            >
              Évaluer ma soumission
            </Button>
          </div>
        </div>
      )}

      {/* Étape EVALUATED / NEEDS_MANUAL_REVIEW : Résultat détaillé, critères & décision finale */}
      {(activeAssessment.status === 'evaluated' ||
        activeAssessment.status === 'needs_manual_review') && (
        <div className="space-y-3">
          <div className="rounded-xl bg-white p-3.5 text-xs dark:bg-zinc-900">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant={
                    activeAssessment.status === 'needs_manual_review'
                      ? 'warning'
                      : activeAssessment.passed
                        ? 'success'
                        : 'danger'
                  }
                >
                  {activeAssessment.status === 'needs_manual_review'
                    ? 'Revue manuelle ou preuve vérifiée requise'
                    : activeAssessment.passed
                      ? 'Niveau visé atteint'
                      : 'Niveau non atteint — renforcement requis'}
                </Badge>
                <span className="text-sm font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
                  Score : {activeAssessment.score ?? 0} / 100
                </span>
              </div>
              <Badge variant="primary">
                Niveau proposé : {activeAssessment.proposedLevel ?? skill.currentLevel} / 5
              </Badge>
            </div>

            {activeAssessment.feedback && (
              <p className="mt-2 whitespace-pre-line leading-relaxed text-zinc-700 dark:text-zinc-300">
                {activeAssessment.feedback}
              </p>
            )}

            {/* Détail par critère */}
            <div className="mt-3 space-y-1.5">
              <p className="font-semibold text-zinc-900 dark:text-zinc-100">
                Détail des critères d’évaluation :
              </p>
              {activeAssessment.criteria.map((c) => (
                <div
                  key={c.key}
                  className="flex flex-col gap-1 rounded-lg bg-zinc-50 px-3 py-2 sm:flex-row sm:items-center sm:justify-between dark:bg-zinc-800/70"
                >
                  <div>
                    <span className="font-medium text-zinc-900 dark:text-zinc-100">{c.label}</span>
                    {c.feedback && (
                      <p className="text-[11px] text-zinc-600 dark:text-zinc-400">{c.feedback}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="font-semibold tabular-nums text-zinc-800 dark:text-zinc-200">
                      {c.score}/{c.maxScore}
                    </span>
                    <Badge variant={c.passed ? 'success' : 'danger'}>
                      {c.passed ? 'Critère validé' : 'Critère non validé'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>

            {activeAssessment.masteredPoints.length > 0 && (
              <div className="mt-3">
                <p className="font-semibold text-emerald-700 dark:text-emerald-400">
                  Éléments maîtrisés :
                </p>
                <ul className="mt-1 list-inside list-disc text-zinc-700 dark:text-zinc-300">
                  {activeAssessment.masteredPoints.map((pt, i) => (
                    <li key={`mastered-${i}`}>{pt}</li>
                  ))}
                </ul>
              </div>
            )}

            {activeAssessment.gapsIdentified.length > 0 && (
              <div className="mt-3">
                <p className="font-semibold text-rose-700 dark:text-rose-400">
                  Lacunes identifiées :
                </p>
                <ul className="mt-1 list-inside list-disc text-zinc-700 dark:text-zinc-300">
                  {activeAssessment.gapsIdentified.map((gap, i) => (
                    <li key={`gap-${i}`}>{gap}</li>
                  ))}
                </ul>
              </div>
            )}

            {activeAssessment.remediationRecommendation && (
              <div className="mt-3 rounded-lg bg-amber-50 p-2.5 text-amber-950 dark:bg-amber-950/40 dark:text-amber-200">
                <strong>Prochaine étape recommandée :</strong>{' '}
                {activeAssessment.remediationRecommendation}
              </div>
            )}
          </div>

          {activeAssessment.externalVerificationWarning && (
            <div className="flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              <Icon icon={InformationCircleIcon} size={15} className="mt-0.5 shrink-0" />
              <span>{activeAssessment.externalVerificationWarning}</span>
            </div>
          )}

          {activeAssessment.status === 'needs_manual_review' ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-amber-50 p-3 dark:bg-amber-950/40">
              <span className="text-xs font-medium text-amber-900 dark:text-amber-200">
                Validation automatique verrouillée : une revue manuelle ou une preuve inspectée et
                vérifiée est requise avant de valider cette évaluation.
              </span>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  isLoading={isBusy}
                  onClick={() => void handleReject()}
                >
                  Clôturer comme non validée
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  isLoading={isBusy}
                  onClick={() => void handleStartRemediation()}
                >
                  Faire un exercice correctif
                </Button>
              </div>
            </div>
          ) : activeAssessment.passed ? (
            <div className="flex flex-wrap items-center justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                isLoading={isBusy}
                onClick={() => void handleReject()}
              >
                <Icon icon={CancelCircleIcon} size={14} />
                Rejeter cette évaluation
              </Button>
              <Button
                type="button"
                variant="primary"
                size="sm"
                isLoading={isBusy}
                onClick={() => void handleValidate()}
              >
                <Icon icon={CheckmarkCircle02Icon} size={14} />
                Valider et appliquer le niveau {activeAssessment.proposedLevel}/5
              </Button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-medium text-rose-700 dark:text-rose-300">
                Verrou actif : le niveau actuel reste à {skill.currentLevel}/5 tant que les
                critères et preuves ne sont pas réunis.
              </span>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  isLoading={isBusy}
                  onClick={() => void handleReject()}
                >
                  Clôturer comme non validée
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  isLoading={isBusy}
                  onClick={() => void handleStartRemediation()}
                >
                  Faire un exercice correctif
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
