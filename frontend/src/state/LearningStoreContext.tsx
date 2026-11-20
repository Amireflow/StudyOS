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
import { ApiError } from '../lib/api-client';
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
} from '../types/domain';
import { useAuth } from './AuthContext';

export interface LearningStateSnapshot {
  paths: LearningPath[];
  modules: LearningModule[];
  lessons: Lesson[];
  skills: Skill[];
  evidence: SkillEvidence[];
  assessments: SkillAssessment[];
  projects: Project[];
}

export interface LearningStoreContextValue extends LearningStateSnapshot {
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

  const [mutationError, setMutationError] = useState<string | null>(null);

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
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }
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
    [isApiMode, logout, queryClient],
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
    const createPath = async (input: LearningPathInput): Promise<boolean> =>
      runApiMutation(() => createLearningPathApi(accessToken, input), ['learning']);

    const updatePath = async (id: string, patch: Partial<LearningPathInput>): Promise<boolean> =>
      runApiMutation(() => updateLearningPathApi(accessToken, id, patch), ['learning']);

    const deletePath = async (id: string): Promise<boolean> =>
      runApiMutation(
        () => deleteLearningPathApi(accessToken, id),
        ['learning', 'tasks', 'sessions', 'skill-assessments'],
      );

    const createModule = async (input: LearningModuleInput): Promise<boolean> =>
      runApiMutation(() => createLearningModuleApi(accessToken, input), ['learning']);

    const updateModule = async (
      id: string,
      patch: Partial<Omit<LearningModuleInput, 'pathId'>>,
    ): Promise<boolean> =>
      runApiMutation(() => updateLearningModuleApi(accessToken, id, patch), ['learning']);

    const deleteModule = async (id: string): Promise<boolean> =>
      runApiMutation(
        () => deleteLearningModuleApi(accessToken, id),
        ['learning', 'tasks', 'sessions', 'skill-assessments'],
      );

    const createLesson = async (input: LessonInput): Promise<boolean> =>
      runApiMutation(() => createLessonApi(accessToken, input), ['learning']);

    const updateLesson = async (
      id: string,
      patch: Partial<Omit<LessonInput, 'moduleId'>>,
    ): Promise<boolean> =>
      runApiMutation(() => updateLessonApi(accessToken, id, patch), ['learning']);

    const setLessonStatus = (id: string, status: LearningStatus) => updateLesson(id, { status });

    const deleteLesson = async (id: string): Promise<boolean> =>
      runApiMutation(
        () => deleteLessonApi(accessToken, id),
        ['learning', 'sessions', 'skill-assessments'],
      );

    const createSkill = async (input: SkillInput): Promise<boolean> =>
      runApiMutation(() => createSkillApi(accessToken, input), ['skills']);

    const updateSkill = async (id: string, patch: Partial<SkillInput>): Promise<boolean> =>
      runApiMutation(() => updateSkillApi(accessToken, id, patch), ['skills']);

    const deleteSkill = async (id: string): Promise<boolean> =>
      runApiMutation(
        () => deleteSkillApi(accessToken, id),
        ['skills', 'skill-evidence', 'skill-assessments', 'sessions'],
      );

    const addEvidence = async (skillId: string, input: SkillEvidenceInput): Promise<boolean> =>
      runApiMutation(() => createSkillEvidenceApi(accessToken, skillId, input), ['skill-evidence']);

    const deleteEvidence = async (skillId: string, evidenceId: string): Promise<boolean> =>
      runApiMutation(
        () => deleteSkillEvidenceApi(accessToken, skillId, evidenceId),
        ['skill-evidence'],
      );

    const createAssessment = async (
      skillId: string,
      input: SkillAssessmentCreateInput = {},
    ): Promise<SkillAssessment | null> => {
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return null;
      }
      setMutationError(null);
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
    };

    const revealAssessmentHint = async (
      skillId: string,
      assessmentId: string,
    ): Promise<boolean> =>
      runApiMutation(
        () => revealAssessmentHintApi(accessToken, skillId, assessmentId),
        ['skill-assessments'],
      );

    const submitAssessment = async (
      skillId: string,
      assessmentId: string,
      input: SkillAssessmentSubmitInput,
    ): Promise<boolean> =>
      runApiMutation(
        () => submitSkillAssessmentApi(accessToken, skillId, assessmentId, input),
        ['skill-assessments', 'skill-evidence'],
      );

    const evaluateAssessment = async (
      skillId: string,
      assessmentId: string,
    ): Promise<boolean> =>
      runApiMutation(
        () => evaluateSkillAssessmentApi(accessToken, skillId, assessmentId),
        ['skill-assessments'],
      );

    const validateAssessment = async (
      skillId: string,
      assessmentId: string,
      reason?: string,
    ): Promise<boolean> =>
      runApiMutation(
        () => validateSkillAssessmentApi(accessToken, skillId, assessmentId, reason),
        ['skills', 'skill-assessments', 'skill-evidence'],
      );

    const rejectAssessment = async (
      skillId: string,
      assessmentId: string,
      reason?: string,
    ): Promise<boolean> =>
      runApiMutation(
        () => rejectSkillAssessmentApi(accessToken, skillId, assessmentId, reason),
        ['skill-assessments'],
      );

    const cancelAssessment = async (
      skillId: string,
      assessmentId: string,
      reason?: string,
    ): Promise<boolean> =>
      runApiMutation(
        () => cancelSkillAssessmentApi(accessToken, skillId, assessmentId, reason),
        ['skill-assessments'],
      );

    const createProject = async (input: ProjectInput): Promise<boolean> =>
      runApiMutation(() => createProjectApi(accessToken, input), ['projects']);

    const updateProject = async (id: string, patch: Partial<ProjectInput>): Promise<boolean> =>
      runApiMutation(() => updateProjectApi(accessToken, id, patch), ['projects', 'profile']);

    const setProjectStatus = (id: string, status: ProjectStatus) => updateProject(id, { status });

    const deleteProject = async (id: string): Promise<boolean> =>
      runApiMutation(
        () => deleteProjectApi(accessToken, id),
        ['projects', 'tasks', 'sessions', 'profile'],
      );

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
  }, [accessToken, isApiMode, queryClient, runApiMutation]);

  const resolvedState: LearningStateSnapshot = useMemo(
    () => ({
      paths: overviewQuery.data?.paths ?? [],
      modules: overviewQuery.data?.modules ?? [],
      lessons: overviewQuery.data?.lessons ?? [],
      skills: skillsQuery.data ?? [],
      evidence: evidenceQuery.data ?? [],
      assessments: assessmentsQuery.data ?? [],
      projects: projectsQuery.data ?? [],
    }),
    [
      overviewQuery.data,
      skillsQuery.data,
      evidenceQuery.data,
      assessmentsQuery.data,
      projectsQuery.data,
    ],
  );

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
