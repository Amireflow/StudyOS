import { useMemo, useState, type FormEvent } from 'react';
import {
  Add01Icon,
  Alert02Icon,
  Award02Icon,
  ExternalLinkIcon,
} from '@hugeicons/core-free-icons';
import { PageHeader } from '../../components/layout/PageHeader';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/Card';
import { FormField, InlineConfirm, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from '../../components/ui/StateFeedback';
import { formatDateTimeFr } from '../../lib/date';
import { extractFieldErrors } from '../../lib/validation';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import type { Skill, SkillEvidence, SkillEvidenceType, SkillLevel } from '../../types/domain';
import {
  evidenceFormSchema,
  SKILL_EVIDENCE_TYPE_META,
  SKILL_LEVEL_META,
  skillFormSchema,
  type EvidenceFormValues,
  type SkillFormValues,
} from './skillsSchema';

type SkillField = keyof SkillFormValues;
type EvidenceField = keyof EvidenceFormValues;

export function SkillsPage() {
  const {
    skills,
    evidence,
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
  } = useLearningStore();
  const { sessions } = useStudyStore();

  const [domainFilter, setDomainFilter] = useState<string>('all');
  const [isSkillFormOpen, setIsSkillFormOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
  const [skillValues, setSkillValues] = useState<SkillFormValues>({
    name: '',
    domain: '',
    description: '',
    currentLevel: 0,
    targetLevel: '',
  });
  const [skillErrors, setSkillErrors] = useState<Partial<Record<SkillField, string>>>({});

  const [evidenceSkillId, setEvidenceSkillId] = useState<string | null>(null);
  const [evidenceValues, setEvidenceValues] = useState<EvidenceFormValues>({
    type: 'exercise',
    description: '',
    referenceUrl: '',
    result: '',
  });
  const [evidenceErrors, setEvidenceErrors] = useState<Partial<Record<EvidenceField, string>>>({});
  const [feedback, setFeedback] = useState<string | null>(null);

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

  const visibleSkills = useMemo(() => {
    if (domainFilter === 'all') return skills;
    return skills.filter((s) => s.domain.toLowerCase() === domainFilter.toLowerCase());
  }, [skills, domainFilter]);

  const summary = useMemo(() => {
    const autonomousCount = skills.filter((s) => s.currentLevel >= 3).length;
    const unsubstantiatedCount = skills.filter(
      (s) => s.currentLevel >= 3 && (evidenceBySkillId.get(s.id) ?? []).length === 0,
    ).length;
    return {
      totalSkills: skills.length,
      autonomousCount,
      evidenceCount: evidence.length,
      unsubstantiatedCount,
    };
  }, [skills, evidence, evidenceBySkillId]);

  const openCreateSkill = () => {
    setEditingSkill(null);
    setSkillValues({
      name: '',
      domain: '',
      description: '',
      currentLevel: 0,
      targetLevel: '3',
    });
    setSkillErrors({});
    setIsSkillFormOpen(true);
  };

  const openEditSkill = (skill: Skill) => {
    setEditingSkill(skill);
    setSkillValues({
      name: skill.name,
      domain: skill.domain,
      description: skill.description ?? '',
      currentLevel: skill.currentLevel,
      targetLevel: skill.targetLevel !== null ? String(skill.targetLevel) : '',
    });
    setSkillErrors({});
    setIsSkillFormOpen(true);
  };

  const handleSkillSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = skillFormSchema.safeParse(skillValues);
    if (!parsed.success) {
      setSkillErrors(extractFieldErrors<SkillField>(parsed.error));
      return;
    }
    setSkillErrors({});

    const payload = {
      name: parsed.data.name,
      domain: parsed.data.domain,
      description: parsed.data.description,
      currentLevel: parsed.data.currentLevel as SkillLevel,
      targetLevel:
        parsed.data.targetLevel === ''
          ? null
          : (Number(parsed.data.targetLevel) as SkillLevel),
    };

    if (editingSkill) {
      if (await updateSkill(editingSkill.id, payload)) {
        setFeedback(`Compétence « ${payload.name} » mise à jour.`);
        setIsSkillFormOpen(false);
        setEditingSkill(null);
      }
      return;
    }

    if (await createSkill(payload)) {
      setFeedback(`Compétence « ${payload.name} » ajoutée.`);
      setIsSkillFormOpen(false);
    }
  };

  const openAddEvidence = (skillId: string) => {
    setEvidenceSkillId(skillId);
    setEvidenceValues({ type: 'exercise', description: '', referenceUrl: '', result: '' });
    setEvidenceErrors({});
  };

  const handleEvidenceSubmit = async (event: FormEvent<HTMLFormElement>, skill: Skill) => {
    event.preventDefault();
    const parsed = evidenceFormSchema.safeParse(evidenceValues);
    if (!parsed.success) {
      setEvidenceErrors(extractFieldErrors<EvidenceField>(parsed.error));
      return;
    }
    setEvidenceErrors({});
    if (await addEvidence(skill.id, parsed.data)) {
      setFeedback(`Preuve ajoutée sur « ${skill.name} ».`);
      setEvidenceSkillId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <PageHeader title="Compétences" />
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <PageHeader title="Compétences" />
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Compétences"
        actions={
          <Button variant="primary" onClick={openCreateSkill}>
            <Icon icon={Add01Icon} size={15} />
            Nouvelle compétence
          </Button>
        }
      />

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Indicateurs de maîtrise & couverture de preuves */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Suivies</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
              {summary.totalSkills}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Autonome+ (≥ 3)</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-700 dark:text-emerald-400">
              {summary.autonomousCount}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Preuves</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-teal-800 dark:text-teal-300">
              {summary.evidenceCount}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3.5">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Sans preuve (≥ 3)</p>
            <p
              className={
                summary.unsubstantiatedCount > 0
                  ? 'mt-1 text-2xl font-semibold tabular-nums text-amber-600 dark:text-amber-300'
                  : 'mt-1 text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50'
              }
            >
              {summary.unsubstantiatedCount}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Formulaire compétence */}
      {isSkillFormOpen && (
        <Card>
          <CardHeader>
            <CardTitle>
              {editingSkill ? 'Modifier la compétence' : 'Nouvelle compétence'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSkillSubmit} noValidate className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField id="skill-name" label="Nom de la compétence" required error={skillErrors.name}>
                  <Input
                    id="skill-name"
                    value={skillValues.name}
                    hasError={Boolean(skillErrors.name)}
                    placeholder="Ex. FastAPI & SQLAlchemy"
                    onChange={(e) => {
                      setSkillValues((prev) => ({ ...prev, name: e.target.value }));
                      if (skillErrors.name) setSkillErrors((prev) => ({ ...prev, name: undefined }));
                    }}
                  />
                </FormField>

                <FormField id="skill-domain" label="Domaine" required error={skillErrors.domain}>
                  <Input
                    id="skill-domain"
                    value={skillValues.domain}
                    hasError={Boolean(skillErrors.domain)}
                    placeholder="Ex. Backend, Frontend…"
                    onChange={(e) => {
                      setSkillValues((prev) => ({ ...prev, domain: e.target.value }));
                      if (skillErrors.domain) {
                        setSkillErrors((prev) => ({ ...prev, domain: undefined }));
                      }
                    }}
                  />
                </FormField>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <FormField id="skill-level" label="Niveau actuel (0 à 5)">
                  <Select
                    id="skill-level"
                    value={String(skillValues.currentLevel)}
                    onChange={(e) =>
                      setSkillValues((prev) => ({
                        ...prev,
                        currentLevel: Number(e.target.value) as SkillLevel,
                      }))
                    }
                  >
                    {[0, 1, 2, 3, 4, 5].map((lvl) => (
                      <option key={lvl} value={String(lvl)}>
                        {SKILL_LEVEL_META[lvl as SkillLevel].label}
                      </option>
                    ))}
                  </Select>
                </FormField>

                <FormField id="skill-target" label="Niveau cible (facultatif)">
                  <Select
                    id="skill-target"
                    value={skillValues.targetLevel}
                    onChange={(e) =>
                      setSkillValues((prev) => ({ ...prev, targetLevel: e.target.value }))
                    }
                  >
                    <option value="">Aucun niveau cible</option>
                    {[1, 2, 3, 4, 5].map((lvl) => (
                      <option key={lvl} value={String(lvl)}>
                        {SKILL_LEVEL_META[lvl as SkillLevel].label}
                      </option>
                    ))}
                  </Select>
                </FormField>
              </div>

              <FormField id="skill-description" label="Critères ou périmètre (facultatif)">
                <Textarea
                  id="skill-description"
                  value={skillValues.description ?? ''}
                  placeholder="Critères concrets…"
                  onChange={(e) =>
                    setSkillValues((prev) => ({ ...prev, description: e.target.value }))
                  }
                />
              </FormField>

              <div className="flex flex-wrap justify-end gap-2">
                <Button variant="secondary" onClick={() => setIsSkillFormOpen(false)}>
                  Annuler
                </Button>
                <Button type="submit" variant="primary">
                  {editingSkill ? 'Enregistrer la compétence' : 'Créer la compétence'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Filtre par domaine */}
      {domains.length > 0 && (
        <Card>
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-3.5">
            <div className="w-full sm:w-64">
              <FormField id="skills-domain-filter" label="Filtrer par domaine">
                <Select
                  id="skills-domain-filter"
                  value={domainFilter}
                  onChange={(e) => setDomainFilter(e.target.value)}
                >
                  <option value="all">Tous les domaines</option>
                  {domains.map((domain) => (
                    <option key={domain} value={domain}>
                      {domain}
                    </option>
                  ))}
                </Select>
              </FormField>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {visibleSkills.length} compétence{visibleSkills.length > 1 ? 's' : ''}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Liste des compétences + preuves associées */}
      {skills.length === 0 ? (
        <Card>
          <CardContent className="py-8">
            <EmptyState
              icon={<Icon icon={Award02Icon} size={17} className="text-teal-700 dark:text-teal-400" />}
              title="Aucune compétence enregistrée"
              action={
                <Button variant="primary" onClick={openCreateSkill}>
                  Ajouter ma première compétence
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {visibleSkills.map((skill) => {
            const skillEvidence = evidenceBySkillId.get(skill.id) ?? [];
            const levelMeta = SKILL_LEVEL_META[skill.currentLevel];
            const needsEvidenceWarning = skill.currentLevel >= 3 && skillEvidence.length === 0;
            const linkedSessionsCount = sessions.filter((s) => s.skillId === skill.id).length;

            return (
              <Card key={skill.id}>
                <CardHeader className="sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <CardTitle>{skill.name}</CardTitle>
                      <Badge variant="neutral">{skill.domain}</Badge>
                      <Badge variant={levelMeta.badgeVariant}>{levelMeta.label}</Badge>
                      {skill.targetLevel !== null && (
                        <Badge variant="neutral">Cible : {skill.targetLevel}/5</Badge>
                      )}
                      {linkedSessionsCount > 0 && (
                        <Badge variant="neutral">
                          {linkedSessionsCount} séance{linkedSessionsCount > 1 ? 's' : ''}
                        </Badge>
                      )}
                    </div>
                    {skill.description && (
                      <CardDescription>{skill.description}</CardDescription>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Select
                      aria-label={`Niveau actuel de ${skill.name}`}
                      value={String(skill.currentLevel)}
                      className="h-8 min-h-8 w-auto py-1 text-xs"
                      onChange={async (e) => {
                        const nextLvl = Number(e.target.value) as SkillLevel;
                        if (await updateSkill(skill.id, { currentLevel: nextLvl })) {
                          setFeedback(`Niveau de « ${skill.name} » passé à ${nextLvl}/5.`);
                        }
                      }}
                    >
                      {[0, 1, 2, 3, 4, 5].map((lvl) => (
                        <option key={lvl} value={String(lvl)}>
                          {SKILL_LEVEL_META[lvl as SkillLevel].shortLabel}
                        </option>
                      ))}
                    </Select>
                    <Button variant="ghost" size="sm" onClick={() => openEditSkill(skill)}>
                      Modifier
                    </Button>
                    <InlineConfirm
                      triggerLabel="Supprimer"
                      ariaLabel={`Supprimer la compétence ${skill.name}`}
                      onConfirm={async () => {
                        if (await deleteSkill(skill.id)) {
                          setFeedback(`Compétence « ${skill.name} » supprimée.`);
                        }
                      }}
                    />
                  </div>
                </CardHeader>

                <CardContent className="space-y-3">
                  {/* Avertissement SKILL-03 : niveau >= 3 sans aucune preuve */}
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
                        <strong>Alerte SKILL-03 :</strong> niveau {skill.currentLevel}/5 déclaré sans preuve associée.
                      </p>
                    </div>
                  )}

                  {/* Section preuves directement consultable sur la compétence */}
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">
                      Preuves ({skillEvidence.length})
                    </h3>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => openAddEvidence(skill.id)}
                    >
                      <Icon icon={Add01Icon} size={14} />
                      Ajouter une preuve
                    </Button>
                  </div>

                  {evidenceSkillId === skill.id && (
                    <form
                      onSubmit={(e) => handleEvidenceSubmit(e, skill)}
                      noValidate
                      className="space-y-3 rounded-xl bg-zinc-50 p-4 dark:bg-zinc-800/70"
                    >
                      <div className="grid gap-3 sm:grid-cols-2">
                        <FormField id={`ev-type-${skill.id}`} label="Type de preuve">
                          <Select
                            id={`ev-type-${skill.id}`}
                            value={evidenceValues.type}
                            onChange={(e) =>
                              setEvidenceValues((prev) => ({
                                ...prev,
                                type: e.target.value as SkillEvidenceType,
                              }))
                            }
                          >
                            <option value="exercise">Exercice</option>
                            <option value="project">Projet</option>
                            <option value="code">Code</option>
                            <option value="assessment">Évaluation</option>
                            <option value="deliverable">Livrable</option>
                            <option value="other">Autre</option>
                          </Select>
                        </FormField>

                        <FormField
                          id={`ev-url-${skill.id}`}
                          label="Lien vérifiable (http/https facultatif)"
                          error={evidenceErrors.referenceUrl}
                        >
                          <Input
                            id={`ev-url-${skill.id}`}
                            type="url"
                            value={evidenceValues.referenceUrl ?? ''}
                            hasError={Boolean(evidenceErrors.referenceUrl)}
                            placeholder="https://github.com/..."
                            onChange={(e) => {
                              setEvidenceValues((prev) => ({
                                ...prev,
                                referenceUrl: e.target.value,
                              }));
                              if (evidenceErrors.referenceUrl) {
                                setEvidenceErrors((prev) => ({
                                  ...prev,
                                  referenceUrl: undefined,
                                }));
                              }
                            }}
                          />
                        </FormField>
                      </div>

                      <FormField
                        id={`ev-desc-${skill.id}`}
                        label="Ce qui a été réalisé ou démontré"
                        required
                        error={evidenceErrors.description}
                      >
                        <Textarea
                          id={`ev-desc-${skill.id}`}
                          value={evidenceValues.description}
                          hasError={Boolean(evidenceErrors.description)}
                          placeholder="Ex. Implémentation de l'API CRUD FastAPI"
                          onChange={(e) => {
                            setEvidenceValues((prev) => ({
                              ...prev,
                              description: e.target.value,
                            }));
                            if (evidenceErrors.description) {
                              setEvidenceErrors((prev) => ({
                                ...prev,
                                description: undefined,
                              }));
                            }
                          }}
                        />
                      </FormField>

                      <FormField
                        id={`ev-result-${skill.id}`}
                        label="Résultat ou verdict (facultatif)"
                        error={evidenceErrors.result}
                      >
                        <Input
                          id={`ev-result-${skill.id}`}
                          value={evidenceValues.result ?? ''}
                          placeholder="Ex. 100 % des tests validés"
                          onChange={(e) =>
                            setEvidenceValues((prev) => ({ ...prev, result: e.target.value }))
                          }
                        />
                      </FormField>

                      <div className="flex justify-end gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setEvidenceSkillId(null)}
                        >
                          Annuler
                        </Button>
                        <Button type="submit" variant="primary" size="sm">
                          Enregistrer la preuve
                        </Button>
                      </div>
                    </form>
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
                            className="flex flex-col gap-2 rounded-xl bg-zinc-50/80 px-3.5 py-2.5 dark:bg-zinc-800/60 sm:flex-row sm:items-start sm:justify-between"
                          >
                            <div className="space-y-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <Badge variant={typeMeta.badgeVariant}>{typeMeta.label}</Badge>
                                <span className="text-xs text-zinc-500 dark:text-zinc-400">
                                  {formatDateTimeFr(item.observedAt)}
                                </span>
                                {item.result && (
                                  <Badge variant="success">{item.result}</Badge>
                                )}
                              </div>
                              <p className="text-sm text-zinc-800 dark:text-zinc-100">{item.description}</p>
                              {item.referenceUrl && (
                                <a
                                  href={item.referenceUrl}
                                  target="_blank"
                                  rel="noreferrer noopener"
                                  className="inline-flex items-center gap-1 text-xs font-medium text-teal-800 dark:text-teal-300 hover:underline"
                                >
                                  Consulter la preuve
                                  <Icon icon={ExternalLinkIcon} size={12} />
                                </a>
                              )}
                            </div>

                            <InlineConfirm
                              triggerLabel="Retirer"
                              ariaLabel={`Supprimer la preuve ${item.description}`}
                              onConfirm={async () => {
                                if (await deleteEvidence(skill.id, item.id)) {
                                  setFeedback('Preuve supprimée.');
                                }
                              }}
                            />
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
