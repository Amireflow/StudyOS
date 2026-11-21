import { useEffect, useMemo, useState } from 'react';
import { Add01Icon, Award02Icon, Search01Icon } from '@hugeicons/core-free-icons';
import { useSearchParams } from 'react-router-dom';
import { Button } from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SuccessBanner,
} from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type {
  Skill,
  SkillAssessment,
  SkillEvidence,
  SkillPedagogicalState,
} from '../../types/domain';
import { deriveSkillPedagogicalState } from './assessmentEngine';
import { SkillCard } from './SkillCard';
import { SkillForm, type SkillSubmitPayload } from './SkillForms';
import {
  SKILL_PEDAGOGICAL_STATE_META,
  type EvidenceFormValues,
} from './skillsSchema';

type QuickFilter = 'all' | 'validated' | 'unsubstantiated';

const PILL_BASE = 'inline-flex min-h-11 items-center rounded-full px-3 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400';
const PILL_ACTIVE = 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900';
const PILL_IDLE =
  'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700';

export function SkillsPage() {
  const {
    paths,
    modules,
    lessons,
    skills,
    evidence,
    assessments,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    createSkill,
    updateSkill,
    deleteSkill,
    addEvidence,
    deleteEvidence,
    createAssessment,
    revealAssessmentHint,
    submitAssessment,
    evaluateAssessment,
    validateAssessment,
    rejectAssessment,
    cancelAssessment,
  } = useLearningStore();
  const { sessions } = useStudyStore();
  const [searchParams] = useSearchParams();

  const queryPathId = searchParams.get('pathId');
  const queryModuleId = searchParams.get('moduleId');
  const queryLessonId = searchParams.get('lessonId');
  const querySkillId = searchParams.get('skillId');

  const [isSkillFormOpen, setIsSkillFormOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
  const [assessingSkillId, setAssessingSkillId] = useState<string | null>(querySkillId);
  const [historySkillId, setHistorySkillId] = useState<string | null>(null);
  const [evidenceSkillId, setEvidenceSkillId] = useState<string | null>(null);

  const [domainFilter, setDomainFilter] = useState<string>('all');
  const [stateFilter, setStateFilter] = useState<string>('all');
  const [quickFilter, setQuickFilter] = useState<QuickFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (querySkillId && skills.some((s) => s.id === querySkillId)) {
      setAssessingSkillId(querySkillId);
    } else if (
      !assessingSkillId &&
      (queryPathId || queryModuleId || queryLessonId) &&
      skills.length > 0
    ) {
      setAssessingSkillId(skills[0].id);
    }
  }, [assessingSkillId, queryLessonId, queryModuleId, queryPathId, querySkillId, skills]);

  const domains = useMemo(
    () =>
      Array.from(new Set(skills.map((s) => s.domain.trim()).filter(Boolean))).sort((a, b) =>
        a.localeCompare(b, 'fr'),
      ),
    [skills],
  );

  const evidenceBySkillId = useMemo(() => {
    const map = new Map<string, SkillEvidence[]>();
    for (const item of evidence) {
      const list = map.get(item.skillId) ?? [];
      list.push(item);
      map.set(item.skillId, list);
    }
    return map;
  }, [evidence]);

  const assessmentsBySkillId = useMemo(() => {
    const map = new Map<string, SkillAssessment[]>();
    for (const item of assessments) {
      const list = map.get(item.skillId) ?? [];
      list.push(item);
      map.set(item.skillId, list);
    }
    for (const list of map.values()) {
      list.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
    }
    return map;
  }, [assessments]);

  const sessionsCountBySkillId = useMemo(() => {
    const map = new Map<string, number>();
    for (const session of sessions) {
      if (session.skillId) {
        map.set(session.skillId, (map.get(session.skillId) ?? 0) + 1);
      }
    }
    return map;
  }, [sessions]);

  const pedagogicalStateBySkillId = useMemo(() => {
    const map = new Map<string, SkillPedagogicalState>();
    for (const skill of skills) {
      const evCount = (evidenceBySkillId.get(skill.id) ?? []).length;
      const skillAssessments = assessmentsBySkillId.get(skill.id) ?? [];
      const sessCount = sessionsCountBySkillId.get(skill.id) ?? 0;
      map.set(
        skill.id,
        deriveSkillPedagogicalState(skill, skillAssessments, evCount, sessCount),
      );
    }
    return map;
  }, [assessmentsBySkillId, evidenceBySkillId, sessionsCountBySkillId, skills]);

  const summary = useMemo(() => {
    const validatedCount = skills.filter(
      (s) => pedagogicalStateBySkillId.get(s.id) === 'validated' || s.currentLevel >= 3,
    ).length;
    const unsubstantiatedCount = skills.filter(
      (s) =>
        (s.currentLevel >= 3 && (evidenceBySkillId.get(s.id) ?? []).length === 0) ||
        pedagogicalStateBySkillId.get(s.id) === 'needs_reinforcement',
    ).length;
    return {
      totalSkills: skills.length,
      validatedCount,
      evidenceCount: evidence.length,
      unsubstantiatedCount,
    };
  }, [skills, evidence.length, evidenceBySkillId, pedagogicalStateBySkillId]);

  const visibleSkills = useMemo(() => {
    const normalizedSearch = searchQuery.trim().toLowerCase();
    return skills.filter((skill) => {
      const skillEvidence = evidenceBySkillId.get(skill.id) ?? [];
      const pedState = pedagogicalStateBySkillId.get(skill.id) ?? 'not_evaluated';

      if (
        domainFilter !== 'all' &&
        skill.domain.trim().toLowerCase() !== domainFilter.toLowerCase()
      ) {
        return false;
      }
      if (stateFilter !== 'all' && pedState !== stateFilter) {
        return false;
      }
      if (
        quickFilter === 'validated' &&
        !(pedState === 'validated' || skill.currentLevel >= 3)
      ) {
        return false;
      }
      if (
        quickFilter === 'unsubstantiated' &&
        !(
          (skill.currentLevel >= 3 && skillEvidence.length === 0) ||
          pedState === 'needs_reinforcement'
        )
      ) {
        return false;
      }
      if (!normalizedSearch) {
        return true;
      }
      const chunks = [
        skill.name,
        skill.domain,
        skill.description ?? '',
        ...skillEvidence.flatMap((e) => [e.description, e.result ?? '']),
      ];
      return chunks.some((chunk) => chunk.toLowerCase().includes(normalizedSearch));
    });
  }, [
    domainFilter,
    evidenceBySkillId,
    pedagogicalStateBySkillId,
    quickFilter,
    searchQuery,
    skills,
    stateFilter,
  ]);

  const groupedByDomain = useMemo(() => {
    const groups = new Map<string, Skill[]>();
    for (const skill of visibleSkills) {
      const key = skill.domain.trim() || 'Autre';
      const list = groups.get(key) ?? [];
      list.push(skill);
      groups.set(key, list);
    }
    return Array.from(groups.entries())
      .sort(([a], [b]) => a.localeCompare(b, 'fr'))
      .map(([domain, domainSkills]) => ({
        domain,
        domainSkills: [...domainSkills].sort((a, b) => b.currentLevel - a.currentLevel),
      }));
  }, [visibleSkills]);

  const resetFilters = () => {
    setDomainFilter('all');
    setStateFilter('all');
    setQuickFilter('all');
    setSearchQuery('');
  };

  const openCreateSkill = () => {
    setEditingSkill(null);
    setIsSkillFormOpen(true);
  };

  const openEditSkill = (skill: Skill) => {
    setEditingSkill(skill);
    setIsSkillFormOpen(true);
  };

  const handleSkillSubmit = async (payload: SkillSubmitPayload) => {
    if (editingSkill) {
      if (await updateSkill(editingSkill.id, payload)) {
        setFeedback(`Compétence « ${payload.name} » mise à jour.`);
        setIsSkillFormOpen(false);
        setEditingSkill(null);
      }
      return;
    }

    if (await createSkill(payload)) {
      setFeedback(
        `Compétence « ${payload.name} » créée au niveau 0/5 (Non évalué). Lancez une évaluation pour progresser.`,
      );
      setIsSkillFormOpen(false);
    }
  };

  const handleDeleteSkill = async (skill: Skill) => {
    if (await deleteSkill(skill.id)) {
      setFeedback(`Compétence « ${skill.name} » supprimée.`);
    }
  };

  const handleAddEvidence = async (skill: Skill, values: EvidenceFormValues) => {
    if (await addEvidence(skill.id, values)) {
      setFeedback(`Preuve ajoutée sur « ${skill.name} ».`);
      setEvidenceSkillId(null);
    }
  };

  const handleDeleteEvidence = async (skillId: string, evidenceId: string) => {
    if (await deleteEvidence(skillId, evidenceId)) {
      setFeedback('Preuve supprimée.');
    }
  };

  const pageTitle = (
    <h1 className="ui-page-title">
      Compétences
    </h1>
  );

  if (isLoading) {
    return (
      <div className="space-y-5">
        <header>{pageTitle}</header>
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <header>{pageTitle}</header>
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  return (
    <div className="space-y-3.5 sm:space-y-5">
      {/* En-tête */}
      <header className="flex flex-wrap items-center justify-between gap-2.5">
        <div>
          {pageTitle}
          {summary.totalSkills > 0 && (
            <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
              {`${summary.validatedCount}/${summary.totalSkills} validées · ${summary.evidenceCount} preuve${summary.evidenceCount > 1 ? 's' : ''}`}
            </p>
          )}
        </div>

        <Button type="button" variant="primary" size="sm" onClick={openCreateSkill}>
          <Icon icon={Add01Icon} size={15} />
          Nouvelle compétence
        </Button>
      </header>

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Tuiles KPI */}
      <section aria-label="Indicateurs de maîtrise" className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 sm:gap-3">
        <button
          type="button"
          aria-pressed={quickFilter === 'all'}
          aria-label={`Suivies (${summary.totalSkills}) — tout afficher`}
          onClick={() => setQuickFilter('all')}
          className="rounded-2xl bg-white p-3 text-left transition-colors hover:bg-zinc-50 sm:p-4 dark:bg-zinc-900 dark:hover:bg-zinc-800/80"
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Suivies</p>
          <p className="mt-0.5 text-xl font-semibold tabular-nums text-zinc-900 sm:mt-1 sm:text-2xl dark:text-zinc-50">
            {summary.totalSkills}
          </p>
        </button>

        <button
          type="button"
          aria-pressed={quickFilter === 'validated'}
          aria-label={`Validées (${summary.validatedCount}) — filtrer`}
          onClick={() => setQuickFilter((prev) => (prev === 'validated' ? 'all' : 'validated'))}
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            quickFilter === 'validated'
              ? 'bg-emerald-50 dark:bg-emerald-950/45'
              : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
            Validées / Autonome+
          </p>
          <p className="mt-0.5 text-xl font-semibold tabular-nums text-emerald-700 sm:mt-1 sm:text-2xl dark:text-emerald-400">
            {summary.validatedCount}
          </p>
        </button>

        <div className="rounded-2xl bg-white p-3 sm:p-4 dark:bg-zinc-900">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Preuves</p>
          <p className="mt-0.5 text-xl font-semibold tabular-nums text-teal-800 sm:mt-1 sm:text-2xl dark:text-teal-300">
            {summary.evidenceCount}
          </p>
        </div>

        <button
          type="button"
          aria-pressed={quickFilter === 'unsubstantiated'}
          aria-label={`À renforcer (${summary.unsubstantiatedCount}) — filtrer`}
          onClick={() =>
            setQuickFilter((prev) => (prev === 'unsubstantiated' ? 'all' : 'unsubstantiated'))
          }
          className={cn(
            'rounded-2xl p-3 text-left transition-colors sm:p-4',
            quickFilter === 'unsubstantiated'
              ? 'bg-amber-100/80 dark:bg-amber-950/60'
              : summary.unsubstantiatedCount > 0
                ? 'bg-amber-50/70 hover:bg-amber-50 dark:bg-amber-950/30 dark:hover:bg-amber-950/45'
                : 'bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80',
          )}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
            À renforcer
          </p>
          <p
            className={cn(
              'mt-0.5 text-xl font-semibold tabular-nums sm:mt-1 sm:text-2xl',
              summary.unsubstantiatedCount > 0
                ? 'text-amber-600 dark:text-amber-300'
                : 'text-zinc-900 dark:text-zinc-50',
            )}
          >
            {summary.unsubstantiatedCount}
          </p>
        </button>
      </section>

      {/* Formulaire compétence */}
      {isSkillFormOpen && (
        <SkillForm
          editingSkill={editingSkill}
          existingDomains={domains}
          onSubmit={handleSkillSubmit}
          onCancel={() => {
            setIsSkillFormOpen(false);
            setEditingSkill(null);
          }}
        />
      )}

      {/* Recherche, domaines & états */}
      {skills.length > 0 && (
        <section
          aria-label="Recherche et filtres des compétences"
          className="space-y-3 rounded-2xl bg-white p-3.5 dark:bg-zinc-900"
        >
          <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 sm:max-w-xs">
              <Icon
                icon={Search01Icon}
                size={15}
                className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-zinc-400 dark:text-zinc-500"
              />
              <Input
                aria-label="Rechercher une compétence"
                type="search"
                value={searchQuery}
                placeholder="Rechercher une compétence, un domaine ou une preuve…"
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>

            <div className="w-full sm:w-56">
              <label htmlFor="skills-state-filter" className="sr-only">
                Filtrer par état pédagogique
              </label>
              <Select
                id="skills-state-filter"
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
              >
                <option value="all">Tous les états pédagogiques</option>
                {(Object.keys(SKILL_PEDAGOGICAL_STATE_META) as SkillPedagogicalState[]).map(
                  (stateKey) => (
                    <option key={stateKey} value={stateKey}>
                      {SKILL_PEDAGOGICAL_STATE_META[stateKey].label}
                    </option>
                  ),
                )}
              </Select>
            </div>
          </div>

          <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0">
            <button
              type="button"
              onClick={() => setDomainFilter('all')}
              className={cn('shrink-0', PILL_BASE, domainFilter === 'all' ? PILL_ACTIVE : PILL_IDLE)}
            >
              Tous
            </button>
            {domains.map((domain) => (
              <button
                key={domain}
                type="button"
                onClick={() => setDomainFilter((prev) => (prev === domain ? 'all' : domain))}
                className={cn('shrink-0', PILL_BASE, domainFilter === domain ? PILL_ACTIVE : PILL_IDLE)}
              >
                {domain}
              </button>
            ))}
            {summary.unsubstantiatedCount > 0 && (
              <button
                type="button"
                onClick={() =>
                  setQuickFilter((prev) => (prev === 'unsubstantiated' ? 'all' : 'unsubstantiated'))
                }
                className={cn(
                  'shrink-0',
                  PILL_BASE,
                  quickFilter === 'unsubstantiated'
                    ? 'bg-amber-500 text-white dark:bg-amber-400 dark:text-zinc-900'
                    : 'bg-amber-50 text-amber-800 hover:bg-amber-100 dark:bg-amber-950/50 dark:text-amber-300 dark:hover:bg-amber-950/80',
                )}
              >
                À étayer
              </button>
            )}
          </div>
        </section>
      )}

      {/* Cartographie groupée par domaine */}
      {skills.length === 0 ? (
        <div className="rounded-2xl bg-white py-8 dark:bg-zinc-900">
          <EmptyState
            icon={<Icon icon={Award02Icon} size={17} className="text-teal-700 dark:text-teal-400" />}
            title="Aucune compétence enregistrée"
            action={
              <Button type="button" variant="primary" size="sm" onClick={openCreateSkill}>
                Ajouter ma première compétence
              </Button>
            }
          />
        </div>
      ) : visibleSkills.length === 0 ? (
        <EmptyState
          icon={<Icon icon={Award02Icon} size={17} />}
          title="Aucune compétence ne correspond aux filtres"
          action={
            <Button type="button" variant="secondary" size="sm" onClick={resetFilters}>
              Réinitialiser les filtres
            </Button>
          }
        />
      ) : (
        <div className="space-y-6">
          {groupedByDomain.map(({ domain, domainSkills }) => (
            <div key={domain} className="space-y-2.5">
              <div className="flex items-center gap-2 px-1">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-300">
                  {domain}
                </h2>
                <span className="rounded-full bg-zinc-200/70 px-2 py-0.5 text-[11px] font-semibold tabular-nums text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                  {domainSkills.length}
                </span>
              </div>

              <div className="space-y-3">
                {domainSkills.map((skill) => (
                  <SkillCard
                    key={skill.id}
                    skill={skill}
                    skillEvidence={evidenceBySkillId.get(skill.id) ?? []}
                    skillAssessments={assessmentsBySkillId.get(skill.id) ?? []}
                    pedState={pedagogicalStateBySkillId.get(skill.id) ?? 'not_evaluated'}
                    linkedSessionsCount={sessionsCountBySkillId.get(skill.id) ?? 0}
                    paths={paths}
                    modules={modules}
                    lessons={lessons}
                    initialPathId={queryPathId}
                    initialModuleId={queryModuleId}
                    initialLessonId={queryLessonId}
                    isPanelOpen={assessingSkillId === skill.id}
                    isHistoryOpen={historySkillId === skill.id}
                    isAddingEvidence={evidenceSkillId === skill.id}
                    onTogglePanel={(skillId) =>
                      setAssessingSkillId((prev) => (prev === skillId ? null : skillId))
                    }
                    onClosePanel={() => setAssessingSkillId(null)}
                    onToggleHistory={(skillId) =>
                      setHistorySkillId((prev) => (prev === skillId ? null : skillId))
                    }
                    onEdit={openEditSkill}
                    onDelete={handleDeleteSkill}
                    onOpenAddEvidence={(skillId) => setEvidenceSkillId(skillId)}
                    onCloseAddEvidence={() => setEvidenceSkillId(null)}
                    onAddEvidence={handleAddEvidence}
                    onDeleteEvidence={handleDeleteEvidence}
                    onStartAssessment={createAssessment}
                    onRevealHint={revealAssessmentHint}
                    onSubmitAssessment={submitAssessment}
                    onEvaluateAssessment={evaluateAssessment}
                    onValidateAssessment={validateAssessment}
                    onRejectAssessment={rejectAssessment}
                    onCancelAssessment={cancelAssessment}
                    onFeedback={setFeedback}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
