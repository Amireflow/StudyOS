import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  buildLocalAssessmentExercise,
  evaluateLocalSubmission,
  EXTERNAL_URL_DISCLAIMER,
  passThresholdForLevel,
  validateEvidenceQualityLocal,
} from '../features/skills/assessmentEngine';
import { ApiError } from '../lib/api-client';
import { dateInputToDueIso } from '../lib/date';
import {
  cancelSkillAssessmentApi,
  createLearningModuleApi,
  createLearningPathApi,
  createLessonApi,
  createProjectApi,
  createSkillApi,
  createSkillAssessmentApi,
  createSkillEvidenceApi,
  deleteLearningModuleApi,
  deleteLearningPathApi,
  deleteLessonApi,
  deleteProjectApi,
  deleteSkillApi,
  deleteSkillEvidenceApi,
  evaluateSkillAssessmentApi,
  fetchAllSkillAssessmentsApi,
  fetchAllSkillEvidenceApi,
  fetchLearningOverviewApi,
  fetchProjectsApi,
  fetchSkillsApi,
  rejectSkillAssessmentApi,
  revealAssessmentHintApi,
  submitSkillAssessmentApi,
  updateLearningModuleApi,
  updateLearningPathApi,
  updateLessonApi,
  updateProjectApi,
  updateSkillApi,
  validateSkillAssessmentApi,
  type LearningModuleInput,
  type LearningPathInput,
  type LessonInput,
  type ProjectInput,
  type SkillAssessmentCreateInput,
  type SkillAssessmentSubmitInput,
  type SkillEvidenceInput,
  type SkillInput,
} from '../lib/learningApi';
import { generateId, readFromStorage, STORAGE_KEYS, writeToStorage } from '../lib/storage';
import type {
  LearningModule,
  LearningPath,
  LearningStatus,
  Lesson,
  Project,
  ProjectStatus,
  Skill,
  SkillAssessment,
  SkillEvidence,
  SkillLevel,
} from '../types/domain';
import { useAuth } from './AuthContext';

const LOCAL_USER_ID = 'local-user';

export interface LearningLocalState {
  paths: LearningPath[];
  modules: LearningModule[];
  lessons: Lesson[];
  skills: Skill[];
  evidence: SkillEvidence[];
  assessments: SkillAssessment[];
  projects: Project[];
}

const DEFAULT_LEARNING_STATE: LearningLocalState = {
  paths: [],
  modules: [],
  lessons: [],
  skills: [],
  evidence: [],
  assessments: [],
  projects: [],
};

function sanitizeLearningState(raw: unknown): LearningLocalState {
  if (!raw || typeof raw !== 'object') {
    return DEFAULT_LEARNING_STATE;
  }
  const c = raw as Partial<LearningLocalState>;
  return {
    paths: Array.isArray(c.paths) ? c.paths : [],
    modules: Array.isArray(c.modules) ? c.modules : [],
    lessons: Array.isArray(c.lessons) ? c.lessons : [],
    skills: Array.isArray(c.skills) ? c.skills : [],
    evidence: Array.isArray(c.evidence) ? c.evidence : [],
    assessments: Array.isArray(c.assessments) ? c.assessments : [],
    projects: Array.isArray(c.projects) ? c.projects : [],
  };
}

export interface LearningStoreContextValue extends LearningLocalState {
  isLoading: boolean;
  error: string | null;
  mutationError: string | null;
  clearMutationError: () => void;
  retry: () => void;
  createPath: (input: LearningPathInput) => Promise<boolean>;
  updatePath: (id: string, patch: Partial<LearningPathInput>) => Promise<boolean>;
  deletePath: (id: string) => Promise<boolean>;
  createModule: (input: LearningModuleInput) => Promise<boolean>;
  updateModule: (id: string, patch: Partial<Omit<LearningModuleInput, 'pathId'>>) => Promise<boolean>;
  deleteModule: (id: string) => Promise<boolean>;
  createLesson: (input: LessonInput) => Promise<boolean>;
  updateLesson: (id: string, patch: Partial<Omit<LessonInput, 'moduleId'>>) => Promise<boolean>;
  deleteLesson: (id: string) => Promise<boolean>;
  setLessonStatus: (id: string, status: LearningStatus) => Promise<boolean>;
  seedStarterPaths: () => Promise<boolean>;
  createSkill: (input: SkillInput) => Promise<boolean>;
  updateSkill: (id: string, patch: Partial<SkillInput>) => Promise<boolean>;
  deleteSkill: (id: string) => Promise<boolean>;
  addEvidence: (skillId: string, input: SkillEvidenceInput) => Promise<boolean>;
  deleteEvidence: (skillId: string, evidenceId: string) => Promise<boolean>;
  createAssessment: (
    skillId: string,
    input?: SkillAssessmentCreateInput,
  ) => Promise<SkillAssessment | null>;
  revealAssessmentHint: (skillId: string, assessmentId: string) => Promise<boolean>;
  submitAssessment: (
    skillId: string,
    assessmentId: string,
    input: SkillAssessmentSubmitInput,
  ) => Promise<boolean>;
  evaluateAssessment: (skillId: string, assessmentId: string) => Promise<boolean>;
  validateAssessment: (
    skillId: string,
    assessmentId: string,
    reason?: string,
  ) => Promise<boolean>;
  rejectAssessment: (
    skillId: string,
    assessmentId: string,
    reason?: string,
  ) => Promise<boolean>;
  cancelAssessment: (
    skillId: string,
    assessmentId: string,
    reason?: string,
  ) => Promise<boolean>;
  createProject: (input: ProjectInput) => Promise<boolean>;
  updateProject: (id: string, patch: Partial<ProjectInput>) => Promise<boolean>;
  setProjectStatus: (id: string, status: ProjectStatus) => Promise<boolean>;
  deleteProject: (id: string) => Promise<boolean>;
}

const LearningStoreContext = createContext<LearningStoreContextValue | null>(null);

export function LearningStoreProvider({ children }: { children: ReactNode }) {
  const { session, logout } = useAuth();
  const queryClient = useQueryClient();
  const isApiMode = session?.mode === 'api' && Boolean(session.accessToken);
  const accessToken = session?.mode === 'api' ? session.accessToken : '';
  const userIdKey = session?.userId ?? 'anonymous';

  const [localState, setLocalState] = useState<LearningLocalState>(() =>
    sanitizeLearningState(
      readFromStorage<LearningLocalState>(STORAGE_KEYS.learningState, DEFAULT_LEARNING_STATE),
    ),
  );
  const [mutationError, setMutationError] = useState<string | null>(null);

  useEffect(() => {
    if (!isApiMode) {
      writeToStorage(STORAGE_KEYS.learningState, localState);
    }
  }, [isApiMode, localState]);

  const overviewQuery = useQuery({
    queryKey: ['learning', userIdKey],
    queryFn: () => fetchLearningOverviewApi(accessToken),
    enabled: isApiMode,
  });

  const skillsQuery = useQuery({
    queryKey: ['skills', userIdKey],
    queryFn: () => fetchSkillsApi(accessToken),
    enabled: isApiMode,
  });

  const evidenceQuery = useQuery({
    queryKey: ['skill-evidence', userIdKey],
    queryFn: () => fetchAllSkillEvidenceApi(accessToken),
    enabled: isApiMode,
  });

  const assessmentsQuery = useQuery({
    queryKey: ['skill-assessments', userIdKey],
    queryFn: () => fetchAllSkillAssessmentsApi(accessToken),
    enabled: isApiMode,
  });

  const projectsQuery = useQuery({
    queryKey: ['projects', userIdKey],
    queryFn: () => fetchProjectsApi(accessToken),
    enabled: isApiMode,
  });

  const firstQueryError =
    overviewQuery.error ??
    skillsQuery.error ??
    evidenceQuery.error ??
    assessmentsQuery.error ??
    projectsQuery.error;

  useEffect(() => {
    if (firstQueryError instanceof ApiError && firstQueryError.status === 401) {
      logout('Votre session a expiré. Veuillez vous reconnecter.');
    }
  }, [firstQueryError, logout]);

  const runApiMutation = useCallback(
    async <T,>(
      fn: () => Promise<T>,
      invalidateRoots: Array<
        | 'learning'
        | 'skills'
        | 'skill-evidence'
        | 'skill-assessments'
        | 'projects'
        | 'tasks'
        | 'sessions'
        | 'profile'
      >,
    ): Promise<boolean> => {
      setMutationError(null);
      try {
        await fn();
        await Promise.all(
          invalidateRoots.map((root) => queryClient.invalidateQueries({ queryKey: [root] })),
        );
        return true;
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          logout('Votre session a expiré. Veuillez vous reconnecter.');
          return false;
        }
        setMutationError(
          err instanceof Error ? err.message : 'Erreur lors de la synchronisation serveur.',
        );
        return false;
      }
    },
    [logout, queryClient],
  );

  const retry = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['learning'] });
    void queryClient.invalidateQueries({ queryKey: ['skills'] });
    void queryClient.invalidateQueries({ queryKey: ['skill-evidence'] });
    void queryClient.invalidateQueries({ queryKey: ['skill-assessments'] });
    void queryClient.invalidateQueries({ queryKey: ['projects'] });
  }, [queryClient]);

  const clearMutationError = useCallback(() => setMutationError(null), []);

  const actions = useMemo(() => {
    const createPath = async (input: LearningPathInput): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(() => createLearningPathApi(accessToken, input), ['learning']);
      }
      const nowIso = new Date().toISOString();
      const created: LearningPath = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: input.title.trim(),
        description: input.description?.trim() || null,
        goal: input.goal.trim(),
        status: input.status,
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({ ...prev, paths: [...prev.paths, created] }));
      return true;
    };

    const updatePath = async (id: string, patch: Partial<LearningPathInput>): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(() => updateLearningPathApi(accessToken, id, patch), ['learning']);
      }
      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        paths: prev.paths.map((item) =>
          item.id !== id
            ? item
            : {
                ...item,
                title: patch.title !== undefined ? patch.title.trim() : item.title,
                description:
                  patch.description !== undefined
                    ? patch.description.trim() || null
                    : item.description,
                goal: patch.goal !== undefined ? patch.goal.trim() : item.goal,
                status: patch.status ?? item.status,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const deletePath = async (id: string): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => deleteLearningPathApi(accessToken, id),
          ['learning', 'tasks', 'sessions', 'skill-assessments'],
        );
      }
      setLocalState((prev) => {
        const removedModuleIds = new Set(
          prev.modules.filter((m) => m.pathId === id).map((m) => m.id),
        );
        const removedLessonIds = new Set(
          prev.lessons.filter((l) => removedModuleIds.has(l.moduleId)).map((l) => l.id),
        );
        return {
          ...prev,
          paths: prev.paths.filter((p) => p.id !== id),
          modules: prev.modules.filter((m) => m.pathId !== id),
          lessons: prev.lessons.filter((l) => !removedModuleIds.has(l.moduleId)),
          assessments: prev.assessments.map((a) => ({
            ...a,
            pathId: a.pathId === id ? null : a.pathId,
            moduleId: a.moduleId && removedModuleIds.has(a.moduleId) ? null : a.moduleId,
            lessonId: a.lessonId && removedLessonIds.has(a.lessonId) ? null : a.lessonId,
          })),
        };
      });
      return true;
    };

    const createModule = async (input: LearningModuleInput): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(() => createLearningModuleApi(accessToken, input), ['learning']);
      }
      const nowIso = new Date().toISOString();
      const created: LearningModule = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        pathId: input.pathId,
        title: input.title.trim(),
        description: input.description?.trim() || null,
        position: input.position,
        status: input.status,
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({ ...prev, modules: [...prev.modules, created] }));
      return true;
    };

    const updateModule = async (
      id: string,
      patch: Partial<Omit<LearningModuleInput, 'pathId'>>,
    ): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(() => updateLearningModuleApi(accessToken, id, patch), ['learning']);
      }
      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        modules: prev.modules.map((item) =>
          item.id !== id
            ? item
            : {
                ...item,
                title: patch.title !== undefined ? patch.title.trim() : item.title,
                description:
                  patch.description !== undefined
                    ? patch.description.trim() || null
                    : item.description,
                position: patch.position ?? item.position,
                status: patch.status ?? item.status,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const deleteModule = async (id: string): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => deleteLearningModuleApi(accessToken, id),
          ['learning', 'tasks', 'sessions', 'skill-assessments'],
        );
      }
      setLocalState((prev) => {
        const removedLessonIds = new Set(
          prev.lessons.filter((l) => l.moduleId === id).map((l) => l.id),
        );
        return {
          ...prev,
          modules: prev.modules.filter((m) => m.id !== id),
          lessons: prev.lessons.filter((l) => l.moduleId !== id),
          assessments: prev.assessments.map((a) => ({
            ...a,
            moduleId: a.moduleId === id ? null : a.moduleId,
            lessonId: a.lessonId && removedLessonIds.has(a.lessonId) ? null : a.lessonId,
          })),
        };
      });
      return true;
    };

    const createLesson = async (input: LessonInput): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(() => createLessonApi(accessToken, input), ['learning']);
      }
      const nowIso = new Date().toISOString();
      const created: Lesson = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        moduleId: input.moduleId,
        title: input.title.trim(),
        content: input.content?.trim() || null,
        resourceUrl: input.resourceUrl?.trim() || null,
        position: input.position,
        status: input.status,
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({ ...prev, lessons: [...prev.lessons, created] }));
      return true;
    };

    const updateLesson = async (
      id: string,
      patch: Partial<Omit<LessonInput, 'moduleId'>>,
    ): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(() => updateLessonApi(accessToken, id, patch), ['learning']);
      }
      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        lessons: prev.lessons.map((item) =>
          item.id !== id
            ? item
            : {
                ...item,
                title: patch.title !== undefined ? patch.title.trim() : item.title,
                content:
                  patch.content !== undefined ? patch.content.trim() || null : item.content,
                resourceUrl:
                  patch.resourceUrl !== undefined
                    ? patch.resourceUrl.trim() || null
                    : item.resourceUrl,
                position: patch.position ?? item.position,
                status: patch.status ?? item.status,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const setLessonStatus = (id: string, status: LearningStatus) => updateLesson(id, { status });

    const deleteLesson = async (id: string): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => deleteLessonApi(accessToken, id),
          ['learning', 'sessions', 'skill-assessments'],
        );
      }
      setLocalState((prev) => ({
        ...prev,
        lessons: prev.lessons.filter((l) => l.id !== id),
        assessments: prev.assessments.map((a) => ({
          ...a,
          lessonId: a.lessonId === id ? null : a.lessonId,
        })),
      }));
      return true;
    };

    const seedStarterPaths = async (): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(async () => {
          const pythonPath = await createLearningPathApi(accessToken, {
            title: 'Socle Python & FastAPI',
            goal: 'Concevoir et tester une API REST typée avec persistance SQL',
            status: 'active',
            description: 'Parcours progressif axé sur la pratique et les tests automatisés.',
          });
          const mod1 = await createLearningModuleApi(accessToken, {
            pathId: pythonPath.id,
            title: 'Fondamentaux Python & Pydantic',
            description: 'Typage strict, validation d’entrées et gestion des erreurs.',
            position: 1,
            status: 'active',
          });
          await createLessonApi(accessToken, {
            moduleId: mod1.id,
            title: 'Schémas Pydantic v2 & validateurs',
            content: 'Normaliser les textes, dates UTC et URLs avant persistance.',
            resourceUrl: 'https://docs.pydantic.dev/latest/',
            position: 1,
            status: 'completed',
          });
          await createLessonApi(accessToken, {
            moduleId: mod1.id,
            title: 'Requêtes SQLAlchemy 2 & isolation user_id',
            content: 'Construire des dépôts filtrés systématiquement par utilisateur.',
            position: 2,
            status: 'active',
          });
        }, ['learning']);
      }

      const nowIso = new Date().toISOString();
      const pathId = generateId();
      const modId = generateId();
      setLocalState((prev) => ({
        ...prev,
        paths: [
          ...prev.paths,
          {
            id: pathId,
            userId: LOCAL_USER_ID,
            title: 'Socle Python & FastAPI',
            description: 'Parcours progressif axé sur la pratique et les tests automatisés.',
            goal: 'Concevoir et tester une API REST typée avec persistance SQL',
            status: 'active',
            createdAt: nowIso,
            updatedAt: nowIso,
          },
        ],
        modules: [
          ...prev.modules,
          {
            id: modId,
            userId: LOCAL_USER_ID,
            pathId,
            title: 'Fondamentaux Python & Pydantic',
            description: 'Typage strict, validation d’entrées et gestion des erreurs.',
            position: 1,
            status: 'active',
            createdAt: nowIso,
            updatedAt: nowIso,
          },
        ],
        lessons: [
          ...prev.lessons,
          {
            id: generateId(),
            userId: LOCAL_USER_ID,
            moduleId: modId,
            title: 'Schémas Pydantic v2 & validateurs',
            content: 'Normaliser les textes, dates UTC et URLs avant persistance.',
            resourceUrl: 'https://docs.pydantic.dev/latest/',
            position: 1,
            status: 'completed',
            createdAt: nowIso,
            updatedAt: nowIso,
          },
          {
            id: generateId(),
            userId: LOCAL_USER_ID,
            moduleId: modId,
            title: 'Requêtes SQLAlchemy 2 & isolation user_id',
            content: 'Construire des dépôts filtrés systématiquement par utilisateur.',
            resourceUrl: null,
            position: 2,
            status: 'active',
            createdAt: nowIso,
            updatedAt: nowIso,
          },
        ],
      }));
      return true;
    };

    const createSkill = async (input: SkillInput): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(() => createSkillApi(accessToken, input), ['skills']);
      }
      setMutationError(null);
      const nowIso = new Date().toISOString();
      const created: Skill = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        name: input.name.trim(),
        domain: input.domain.trim(),
        description: input.description?.trim() || null,
        currentLevel: 0,
        targetLevel: input.targetLevel,
        lastAssessedAt: null,
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({ ...prev, skills: [...prev.skills, created] }));
      return true;
    };

    const updateSkill = async (id: string, patch: Partial<SkillInput>): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(() => updateSkillApi(accessToken, id, patch), ['skills']);
      }
      setMutationError(null);
      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        skills: prev.skills.map((skill) => {
          if (skill.id !== id) return skill;
          return {
            ...skill,
            name: patch.name !== undefined ? patch.name.trim() : skill.name,
            domain: patch.domain !== undefined ? patch.domain.trim() : skill.domain,
            description:
              patch.description !== undefined
                ? patch.description.trim() || null
                : skill.description,
            targetLevel: 'targetLevel' in patch ? (patch.targetLevel ?? null) : skill.targetLevel,
            updatedAt: nowIso,
          };
        }),
      }));
      return true;
    };

    const deleteSkill = async (id: string): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => deleteSkillApi(accessToken, id),
          ['skills', 'skill-evidence', 'skill-assessments', 'sessions'],
        );
      }
      setLocalState((prev) => ({
        ...prev,
        skills: prev.skills.filter((s) => s.id !== id),
        evidence: prev.evidence.filter((e) => e.skillId !== id),
        assessments: prev.assessments.filter((a) => a.skillId !== id),
      }));
      return true;
    };

    const addEvidence = async (skillId: string, input: SkillEvidenceInput): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => createSkillEvidenceApi(accessToken, skillId, input),
          ['skill-evidence'],
        );
      }
      setMutationError(null);
      const quality = validateEvidenceQualityLocal(
        input.description,
        input.referenceUrl,
        input.result,
      );
      if (!quality.admissible) {
        setMutationError(
          quality.reason ??
            'Preuve refusée : décrivez concrètement la production réalisée et le résultat.',
        );
        return false;
      }
      const nowIso = new Date().toISOString();
      const created: SkillEvidence = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        skillId,
        type: input.type,
        description: input.description.trim(),
        referenceUrl: input.referenceUrl?.trim() || null,
        result: input.result?.trim() || null,
        observedAt: nowIso,
        isAdmissible: true,
        externalReferenceVerified: false,
        verificationNote: quality.verificationNote,
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({ ...prev, evidence: [created, ...prev.evidence] }));
      return true;
    };

    const deleteEvidence = async (skillId: string, evidenceId: string): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => deleteSkillEvidenceApi(accessToken, skillId, evidenceId),
          ['skill-evidence'],
        );
      }
      setLocalState((prev) => ({
        ...prev,
        evidence: prev.evidence.filter((e) => e.id !== evidenceId),
      }));
      return true;
    };

    const createAssessment = async (
      skillId: string,
      input: SkillAssessmentCreateInput = {},
    ): Promise<SkillAssessment | null> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          const created = await createSkillAssessmentApi(accessToken, skillId, input);
          await queryClient.invalidateQueries({ queryKey: ['skill-assessments'] });
          return created;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de créer l’évaluation.',
          );
          return null;
        }
      }

      const skill = localState.skills.find((s) => s.id === skillId);
      if (!skill) {
        setMutationError('Compétence introuvable.');
        return null;
      }

      const targetLevel = (input.targetLevel ??
        Math.min(5, Math.max(1, skill.currentLevel + 1))) as SkillLevel;
      if (targetLevel < Math.max(1, skill.currentLevel) || targetLevel > 5) {
        setMutationError(
          'Le niveau visé doit être au moins égal au niveau actuel vérifié (entre 1 et 5).',
        );
        return null;
      }

      const priorForSkill = localState.assessments
        .filter((a) => a.skillId === skillId)
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      const failedPrior = priorForSkill.find(
        (a) => a.gapsIdentified.length > 0 && (a.status === 'rejected' || a.passed === false),
      );
      const linkedLesson = input.lessonId
        ? localState.lessons.find((l) => l.id === input.lessonId)
        : undefined;
      const linkedModule = input.moduleId
        ? localState.modules.find((m) => m.id === input.moduleId)
        : linkedLesson
          ? localState.modules.find((m) => m.id === linkedLesson.moduleId)
          : undefined;
      const resolvedPathId = input.pathId ?? linkedModule?.pathId ?? null;
      const resolvedModuleId = input.moduleId ?? linkedLesson?.moduleId ?? null;

      const assessmentType = input.assessmentType ?? 'practical_exercise';
      const generated = buildLocalAssessmentExercise({
        skill,
        targetLevel,
        assessmentType,
        previousGaps: failedPrior?.gapsIdentified ?? [],
        lessonTitle: linkedLesson?.title ?? null,
      });

      const nowIso = new Date().toISOString();
      const created: SkillAssessment = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        skillId,
        pathId: resolvedPathId,
        moduleId: resolvedModuleId,
        lessonId: input.lessonId ?? null,
        assessmentType,
        startingLevel: skill.currentLevel,
        targetLevel,
        proposedLevel: null,
        status: 'pending',
        promptTitle: input.promptTitle?.trim() || generated.promptTitle,
        promptInstructions: input.promptInstructions?.trim() || generated.promptInstructions,
        revealedHints: [],
        hintsTotal: generated.hints.length,
        hintsRevealedCount: 0,
        submissionText: null,
        submissionCode: null,
        submissionReferenceUrl: null,
        evidenceIds: [],
        criteria: generated.criteria,
        score: null,
        passed: null,
        feedback: null,
        masteredPoints: [],
        gapsIdentified: [],
        remediationRecommendation: null,
        externalVerificationWarning: null,
        evaluatorType: 'pedagogical_engine',
        evaluatorName: null,
        decisionReason: null,
        appliedLevelDelta: null,
        submittedAt: null,
        evaluatedAt: null,
        validatedAt: null,
        createdAt: nowIso,
        updatedAt: nowIso,
      };

      setLocalState((prev) => ({
        ...prev,
        assessments: [created, ...prev.assessments],
      }));
      return created;
    };

    const revealAssessmentHint = async (
      skillId: string,
      assessmentId: string,
    ): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => revealAssessmentHintApi(accessToken, skillId, assessmentId),
          ['skill-assessments'],
        );
      }
      setMutationError(null);
      const skill = localState.skills.find((s) => s.id === skillId);
      const assessment = localState.assessments.find(
        (a) => a.id === assessmentId && a.skillId === skillId,
      );
      if (!skill || !assessment || assessment.status !== 'pending') {
        setMutationError('Indice disponible uniquement sur une évaluation en attente.');
        return false;
      }

      const generated = buildLocalAssessmentExercise({
        skill,
        targetLevel: assessment.targetLevel,
        assessmentType: assessment.assessmentType,
      });
      const nextCount = Math.min(generated.hints.length, assessment.hintsRevealedCount + 1);
      const nowIso = new Date().toISOString();

      setLocalState((prev) => ({
        ...prev,
        assessments: prev.assessments.map((a) =>
          a.id !== assessmentId
            ? a
            : {
                ...a,
                hintsRevealedCount: nextCount,
                revealedHints: generated.hints.slice(0, nextCount),
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const submitAssessment = async (
      skillId: string,
      assessmentId: string,
      input: SkillAssessmentSubmitInput,
    ): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => submitSkillAssessmentApi(accessToken, skillId, assessmentId, input),
          ['skill-assessments', 'skill-evidence'],
        );
      }
      setMutationError(null);
      const assessment = localState.assessments.find(
        (a) => a.id === assessmentId && a.skillId === skillId,
      );
      if (!assessment || assessment.status !== 'pending') {
        setMutationError('Cette évaluation a déjà été soumise ou clôturée.');
        return false;
      }

      const trimmedText = input.submissionText.trim();
      if (trimmedText.length < 15) {
        setMutationError('La production soumise doit contenir au moins 15 caractères.');
        return false;
      }

      const selectedIds = Array.from(new Set(input.evidenceIds ?? []));
      let hasExternalUrl = Boolean(input.submissionReferenceUrl?.trim());
      for (const eid of selectedIds) {
        const ev = localState.evidence.find((item) => item.id === eid);
        if (!ev || ev.skillId !== skillId) {
          setMutationError('Une preuve sélectionnée est introuvable ou liée à une autre compétence.');
          return false;
        }
        const q = validateEvidenceQualityLocal(ev.description, ev.referenceUrl, ev.result);
        if (!q.admissible) {
          setMutationError(q.reason ?? 'Preuve liée non admissible.');
          return false;
        }
        if (ev.referenceUrl) hasExternalUrl = true;
      }

      const nowIso = new Date().toISOString();
      let createdEvidence: SkillEvidence | null = null;
      if (input.newEvidence) {
        const q = validateEvidenceQualityLocal(
          input.newEvidence.description,
          input.newEvidence.referenceUrl,
          input.newEvidence.result,
        );
        if (!q.admissible) {
          setMutationError(
            q.reason ?? 'La nouvelle preuve fournie ne respecte pas les critères de qualité.',
          );
          return false;
        }
        createdEvidence = {
          id: generateId(),
          userId: LOCAL_USER_ID,
          skillId,
          type: input.newEvidence.type,
          description: input.newEvidence.description.trim(),
          referenceUrl: input.newEvidence.referenceUrl?.trim() || null,
          result: input.newEvidence.result?.trim() || null,
          observedAt: nowIso,
          isAdmissible: true,
          externalReferenceVerified: false,
          verificationNote: q.verificationNote,
          createdAt: nowIso,
          updatedAt: nowIso,
        };
        selectedIds.push(createdEvidence.id);
        if (createdEvidence.referenceUrl) hasExternalUrl = true;
      }

      setLocalState((prev) => ({
        ...prev,
        evidence: createdEvidence ? [createdEvidence, ...prev.evidence] : prev.evidence,
        assessments: prev.assessments.map((a) =>
          a.id !== assessmentId
            ? a
            : {
                ...a,
                status: 'submitted',
                submissionText: trimmedText,
                submissionCode: input.submissionCode?.trim() || null,
                submissionReferenceUrl: input.submissionReferenceUrl?.trim() || null,
                evidenceIds: selectedIds,
                externalVerificationWarning: hasExternalUrl ? EXTERNAL_URL_DISCLAIMER : null,
                submittedAt: nowIso,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const evaluateAssessment = async (
      skillId: string,
      assessmentId: string,
    ): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => evaluateSkillAssessmentApi(accessToken, skillId, assessmentId),
          ['skill-assessments'],
        );
      }
      setMutationError(null);
      const skill = localState.skills.find((s) => s.id === skillId);
      const assessment = localState.assessments.find(
        (a) => a.id === assessmentId && a.skillId === skillId,
      );
      if (!skill || !assessment || assessment.status !== 'submitted') {
        setMutationError('L’évaluation doit d’abord être soumise avant d’être corrigée.');
        return false;
      }

      const linkedEvidences = localState.evidence.filter(
        (ev) => ev.skillId === skillId && assessment.evidenceIds.includes(ev.id),
      );
      const evaluated = evaluateLocalSubmission({
        skill,
        assessment,
        linkedEvidences,
      });
      const nowIso = new Date().toISOString();

      setLocalState((prev) => ({
        ...prev,
        assessments: prev.assessments.map((a) =>
          a.id !== assessmentId
            ? a
            : {
                ...a,
                status: 'evaluated',
                criteria: evaluated.criteria,
                score: evaluated.score,
                passed: evaluated.passed,
                proposedLevel: evaluated.proposedLevel,
                feedback: evaluated.feedback,
                masteredPoints: evaluated.masteredPoints,
                gapsIdentified: evaluated.gapsIdentified,
                remediationRecommendation: evaluated.remediationRecommendation,
                externalVerificationWarning: evaluated.externalVerificationWarning,
                evaluatorType: 'pedagogical_engine',
                evaluatorName: 'Amireflow Grader',
                evaluatedAt: nowIso,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const validateAssessment = async (
      skillId: string,
      assessmentId: string,
      reason?: string,
    ): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => validateSkillAssessmentApi(accessToken, skillId, assessmentId, reason),
          ['skills', 'skill-assessments', 'skill-evidence'],
        );
      }
      setMutationError(null);
      const skill = localState.skills.find((s) => s.id === skillId);
      const assessment = localState.assessments.find(
        (a) => a.id === assessmentId && a.skillId === skillId,
      );
      if (!skill || !assessment) {
        setMutationError('Évaluation introuvable.');
        return false;
      }
      if (assessment.status === 'approved') {
        setMutationError('Cette évaluation a déjà été validée et ne peut pas être réutilisée.');
        return false;
      }
      if (assessment.status !== 'evaluated') {
        setMutationError('Seule une évaluation corrigée peut être validée.');
        return false;
      }
      const threshold = passThresholdForLevel(assessment.targetLevel);
      if (!assessment.passed || (assessment.score ?? 0) < threshold) {
        setMutationError(
          'Résultat insuffisant pour faire progresser cette compétence. Lancez un exercice correctif.',
        );
        return false;
      }
      const validEvidences = localState.evidence.filter(
        (ev) =>
          ev.skillId === skillId &&
          assessment.evidenceIds.includes(ev.id) &&
          validateEvidenceQualityLocal(ev.description, ev.referenceUrl, ev.result).admissible,
      );
      if (validEvidences.length === 0) {
        setMutationError('Au moins une preuve concrète admissible est requise pour valider ce niveau.');
        return false;
      }

      const proposed = assessment.proposedLevel ?? skill.currentLevel;
      const newLevel = Math.max(skill.currentLevel, proposed) as SkillLevel;
      const delta = newLevel - skill.currentLevel;
      const nowIso = new Date().toISOString();

      setLocalState((prev) => ({
        ...prev,
        skills: prev.skills.map((s) =>
          s.id !== skillId
            ? s
            : {
                ...s,
                currentLevel: newLevel,
                lastAssessedAt: nowIso,
                updatedAt: nowIso,
              },
        ),
        assessments: prev.assessments.map((a) =>
          a.id !== assessmentId
            ? a
            : {
                ...a,
                status: 'approved',
                appliedLevelDelta: delta,
                decisionReason:
                  reason?.trim() ||
                  `Progression validée de ${skill.currentLevel}/5 à ${newLevel}/5.`,
                validatedAt: nowIso,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const rejectAssessment = async (
      skillId: string,
      assessmentId: string,
      reason?: string,
    ): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => rejectSkillAssessmentApi(accessToken, skillId, assessmentId, reason),
          ['skill-assessments'],
        );
      }
      setMutationError(null);
      const skill = localState.skills.find((s) => s.id === skillId);
      const assessment = localState.assessments.find(
        (a) => a.id === assessmentId && a.skillId === skillId,
      );
      if (
        !skill ||
        !assessment ||
        (assessment.status !== 'submitted' && assessment.status !== 'evaluated')
      ) {
        setMutationError('Seule une évaluation soumise ou évaluée peut être rejetée.');
        return false;
      }
      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        assessments: prev.assessments.map((a) =>
          a.id !== assessmentId
            ? a
            : {
                ...a,
                status: 'rejected',
                proposedLevel: skill.currentLevel,
                appliedLevelDelta: 0,
                decisionReason: reason?.trim() || 'Évaluation non validée : niveau conservé.',
                validatedAt: nowIso,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const cancelAssessment = async (
      skillId: string,
      assessmentId: string,
      reason?: string,
    ): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => cancelSkillAssessmentApi(accessToken, skillId, assessmentId, reason),
          ['skill-assessments'],
        );
      }
      setMutationError(null);
      const assessment = localState.assessments.find(
        (a) => a.id === assessmentId && a.skillId === skillId,
      );
      if (
        !assessment ||
        assessment.status === 'approved' ||
        assessment.status === 'rejected' ||
        assessment.status === 'cancelled'
      ) {
        setMutationError('Cette évaluation est déjà clôturée.');
        return false;
      }
      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        assessments: prev.assessments.map((a) =>
          a.id !== assessmentId
            ? a
            : {
                ...a,
                status: 'cancelled',
                appliedLevelDelta: 0,
                decisionReason: reason?.trim() || 'Évaluation annulée par l’utilisateur.',
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const createProject = async (input: ProjectInput): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(() => createProjectApi(accessToken, input), ['projects']);
      }
      if (input.status === 'active' && input.nextAction.trim().length < 2) {
        setMutationError('Une prochaine action concrète est obligatoire pour un projet actif.');
        return false;
      }
      const nowIso = new Date().toISOString();
      const created: Project = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        name: input.name.trim(),
        description: input.description?.trim() || null,
        goal: input.goal.trim(),
        status: input.status,
        priority: input.priority,
        nextAction: input.nextAction.trim(),
        deliverables: input.deliverables.length > 0 ? input.deliverables : null,
        targetDate: dateInputToDueIso(input.targetDate ?? ''),
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({ ...prev, projects: [created, ...prev.projects] }));
      return true;
    };

    const updateProject = async (id: string, patch: Partial<ProjectInput>): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(() => updateProjectApi(accessToken, id, patch), ['projects']);
      }
      const existing = localState.projects.find((p) => p.id === id);
      if (!existing) return false;
      const nextStatus = patch.status ?? existing.status;
      const nextAction = patch.nextAction !== undefined ? patch.nextAction.trim() : existing.nextAction;
      if (nextStatus === 'active' && nextAction.length < 2) {
        setMutationError('Une prochaine action concrète est obligatoire pour un projet actif.');
        return false;
      }
      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        projects: prev.projects.map((p) =>
          p.id !== id
            ? p
            : {
                ...p,
                name: patch.name !== undefined ? patch.name.trim() : p.name,
                description:
                  patch.description !== undefined
                    ? patch.description.trim() || null
                    : p.description,
                goal: patch.goal !== undefined ? patch.goal.trim() : p.goal,
                status: nextStatus,
                priority: patch.priority ?? p.priority,
                nextAction,
                deliverables:
                  patch.deliverables !== undefined
                    ? patch.deliverables.length > 0
                      ? patch.deliverables
                      : null
                    : p.deliverables,
                targetDate:
                  patch.targetDate !== undefined
                    ? dateInputToDueIso(patch.targetDate ?? '')
                    : p.targetDate,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const setProjectStatus = (id: string, status: ProjectStatus) => updateProject(id, { status });

    const deleteProject = async (id: string): Promise<boolean> => {
      if (isApiMode) {
        return runApiMutation(
          () => deleteProjectApi(accessToken, id),
          ['projects', 'tasks', 'sessions', 'profile'],
        );
      }
      setLocalState((prev) => ({
        ...prev,
        projects: prev.projects.filter((p) => p.id !== id),
      }));
      return true;
    };

    return {
      createPath,
      updatePath,
      deletePath,
      createModule,
      updateModule,
      deleteModule,
      createLesson,
      updateLesson,
      deleteLesson,
      setLessonStatus,
      seedStarterPaths,
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
      createProject,
      updateProject,
      setProjectStatus,
      deleteProject,
    };
  }, [
    accessToken,
    isApiMode,
    localState.assessments,
    localState.evidence,
    localState.lessons,
    localState.modules,
    localState.projects,
    localState.skills,
    queryClient,
    runApiMutation,
  ]);

  const resolvedState: LearningLocalState = useMemo(() => {
    if (!isApiMode) {
      return localState;
    }
    return {
      paths: overviewQuery.data?.paths ?? [],
      modules: overviewQuery.data?.modules ?? [],
      lessons: overviewQuery.data?.lessons ?? [],
      skills: skillsQuery.data ?? [],
      evidence: evidenceQuery.data ?? [],
      assessments: assessmentsQuery.data ?? [],
      projects: projectsQuery.data ?? [],
    };
  }, [
    isApiMode,
    localState,
    overviewQuery.data,
    skillsQuery.data,
    evidenceQuery.data,
    assessmentsQuery.data,
    projectsQuery.data,
  ]);

  const isLoading =
    isApiMode &&
    (overviewQuery.isLoading ||
      skillsQuery.isLoading ||
      evidenceQuery.isLoading ||
      assessmentsQuery.isLoading ||
      projectsQuery.isLoading);

  const error =
    isApiMode && firstQueryError
      ? firstQueryError instanceof Error
        ? firstQueryError.message
        : 'Impossible de charger les données d’apprentissage et projets.'
      : null;

  const value = useMemo<LearningStoreContextValue>(
    () => ({
      ...resolvedState,
      isLoading,
      error,
      mutationError,
      clearMutationError,
      retry,
      ...actions,
    }),
    [resolvedState, isLoading, error, mutationError, clearMutationError, retry, actions],
  );

  return <LearningStoreContext.Provider value={value}>{children}</LearningStoreContext.Provider>;
}

export function useLearningStore(): LearningStoreContextValue {
  const ctx = useContext(LearningStoreContext);
  if (!ctx) {
    throw new Error('useLearningStore doit être utilisé à l’intérieur de LearningStoreProvider.');
  }
  return ctx;
}
