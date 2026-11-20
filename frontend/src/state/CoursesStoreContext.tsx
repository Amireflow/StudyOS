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
  createCourseApi,
  createCourseResourceApi,
  deleteCourseApi,
  deleteCourseResourceApi,
  fetchCourseDetailApi,
  fetchCoursesApi,
  previewCourseApi,
  regenerateCourseLevelApi,
  submitCourseWorkApi,
  updateCourseApi,
  updateCourseLessonStatusApi,
  validateCourseLevelApi,
  type CourseCreateInput,
  type CoursePreviewInput,
  type CourseResourceInput,
  type CourseSubmissionInput,
  type CourseUpdateInput,
} from '../lib/coursesApi';
import { generateId, readFromStorage, STORAGE_KEYS, writeToStorage } from '../lib/storage';
import type {
  CourseDetail,
  CourseLessonStatus,
  CoursePreview,
  CourseResource,
  CourseSubmission,
  CourseSummary,
  SkillLevel,
} from '../types/domain';
import {
  createCourseDetailLocal,
  evaluateCourseSubmissionLocal,
  previewCourseLocal,
  regenerateCourseLevelLocal,
  summarizeCourse,
  validateCourseLevelLocal,
  withComputedLevelReadiness,
} from '../features/courses/courseLocalEngine';
import { useAuth } from './AuthContext';
import { useLearningStore } from './LearningStoreContext';

const LOCAL_USER_ID = 'local-user';

interface CoursesLocalState {
  courses: CourseDetail[];
}

const DEFAULT_COURSES_STATE: CoursesLocalState = {
  courses: [],
};

function sanitizeCoursesState(raw: unknown): CoursesLocalState {
  if (!raw || typeof raw !== 'object') {
    return DEFAULT_COURSES_STATE;
  }
  const c = raw as Partial<CoursesLocalState>;
  return {
    courses: Array.isArray(c.courses) ? c.courses : [],
  };
}

export interface CoursesStoreContextValue {
  courses: CourseSummary[];
  localDetails: CourseDetail[];
  isApiMode: boolean;
  isLoading: boolean;
  error: string | null;
  mutationError: string | null;
  clearMutationError: () => void;
  retry: () => void;
  previewCourse: (input: CoursePreviewInput) => Promise<CoursePreview | null>;
  createCourse: (input: CourseCreateInput) => Promise<CourseDetail | null>;
  updateCourse: (courseId: string, patch: CourseUpdateInput) => Promise<boolean>;
  deleteCourse: (courseId: string) => Promise<boolean>;
  updateLessonStatus: (
    courseId: string,
    lessonId: string,
    status: CourseLessonStatus,
  ) => Promise<boolean>;
  addResource: (courseId: string, input: CourseResourceInput) => Promise<CourseResource | null>;
  deleteResource: (courseId: string, resourceId: string) => Promise<boolean>;
  submitWork: (
    courseId: string,
    levelId: string,
    input: CourseSubmissionInput,
  ) => Promise<CourseSubmission | null>;
  validateLevel: (courseId: string, levelId: string) => Promise<CourseDetail | null>;
  regenerateLevel: (
    courseId: string,
    levelId: string,
    focusHint?: string,
  ) => Promise<CourseDetail | null>;
}

const CoursesStoreContext = createContext<CoursesStoreContextValue | null>(null);

export function CoursesStoreProvider({ children }: { children: ReactNode }) {
  const { session, logout } = useAuth();
  const learningStore = useLearningStore();
  const queryClient = useQueryClient();

  const isApiMode = session?.mode === 'api' && Boolean(session.accessToken);
  const accessToken = session?.mode === 'api' ? session.accessToken : '';
  const userIdKey = session?.userId ?? 'anonymous';

  const [localState, setLocalState] = useState<CoursesLocalState>(() =>
    sanitizeCoursesState(
      readFromStorage<CoursesLocalState>(STORAGE_KEYS.coursesState, DEFAULT_COURSES_STATE),
    ),
  );
  const [mutationError, setMutationError] = useState<string | null>(null);

  useEffect(() => {
    if (!isApiMode) {
      writeToStorage(STORAGE_KEYS.coursesState, localState);
    }
  }, [isApiMode, localState]);

  const coursesQuery = useQuery({
    queryKey: ['courses', userIdKey],
    queryFn: () => fetchCoursesApi(accessToken),
    enabled: isApiMode,
  });

  useEffect(() => {
    if (coursesQuery.error instanceof ApiError && coursesQuery.error.status === 401) {
      logout('Votre session a expiré. Veuillez vous reconnecter.');
    }
  }, [coursesQuery.error, logout]);

  const clearMutationError = useCallback(() => setMutationError(null), []);

  const retry = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['courses'] });
    void queryClient.invalidateQueries({ queryKey: ['course-detail'] });
  }, [queryClient]);

  const previewCourse = useCallback(
    async (input: CoursePreviewInput): Promise<CoursePreview | null> => {
      setMutationError(null);
      if (input.subject.trim().length < 2) {
        setMutationError('Veuillez saisir un langage ou sujet d’au moins 2 caractères.');
        return null;
      }
      if (isApiMode) {
        try {
          return await previewCourseApi(accessToken, input);
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de générer la prévisualisation du cours.',
          );
          return null;
        }
      }
      return previewCourseLocal(input);
    },
    [accessToken, isApiMode],
  );

  const createCourse = useCallback(
    async (input: CourseCreateInput): Promise<CourseDetail | null> => {
      setMutationError(null);
      if (input.subject.trim().length < 2) {
        setMutationError('Le sujet du cours doit contenir au moins 2 caractères.');
        return null;
      }

      if (isApiMode) {
        try {
          const created = await createCourseApi(accessToken, input);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['courses'] }),
            queryClient.invalidateQueries({ queryKey: ['skills'] }),
            queryClient.invalidateQueries({ queryKey: ['learning'] }),
          ]);
          return created;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de créer ce cours.',
          );
          return null;
        }
      }

      let linkedSkillId: string | null = null;
      const existingSkill = learningStore.skills.find(
        (s) => s.name.trim().toLowerCase() === input.subject.trim().toLowerCase(),
      );
      if (input.linkSkill !== false) {
        if (existingSkill) {
          linkedSkillId = existingSkill.id;
        } else {
          await learningStore.createSkill({
            name: input.subject.trim(),
            domain: input.domain?.trim() || 'Développement & Études',
            description: `Compétence associée au cours structuré « ${input.title?.trim() || input.subject.trim()} ».`,
            targetLevel: Math.min(5, Math.max(2, input.totalLevels ?? 3)) as SkillLevel,
          });
        }
      }

      const created = createCourseDetailLocal(LOCAL_USER_ID, input, linkedSkillId);
      setLocalState((prev) => ({
        ...prev,
        courses: [created, ...prev.courses],
      }));
      return created;
    },
    [accessToken, isApiMode, learningStore, queryClient],
  );

  const updateCourse = useCallback(
    async (courseId: string, patch: CourseUpdateInput): Promise<boolean> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          await updateCourseApi(accessToken, courseId, patch);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['courses'] }),
            queryClient.invalidateQueries({ queryKey: ['course-detail', userIdKey, courseId] }),
          ]);
          return true;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de mettre à jour le cours.',
          );
          return false;
        }
      }

      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        courses: prev.courses.map((course) =>
          course.id !== courseId
            ? course
            : {
                ...course,
                title: patch.title !== undefined ? patch.title.trim() : course.title,
                description:
                  patch.description !== undefined
                    ? patch.description?.trim() || null
                    : course.description,
                language: patch.language ?? course.language,
                status: patch.status ?? course.status,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    },
    [accessToken, isApiMode, queryClient, userIdKey],
  );

  const deleteCourse = useCallback(
    async (courseId: string): Promise<boolean> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          await deleteCourseApi(accessToken, courseId);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['courses'] }),
            queryClient.invalidateQueries({ queryKey: ['course-detail', userIdKey, courseId] }),
          ]);
          return true;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de supprimer le cours.',
          );
          return false;
        }
      }

      setLocalState((prev) => ({
        ...prev,
        courses: prev.courses.filter((c) => c.id !== courseId),
      }));
      return true;
    },
    [accessToken, isApiMode, queryClient, userIdKey],
  );

  const updateLessonStatus = useCallback(
    async (
      courseId: string,
      lessonId: string,
      status: CourseLessonStatus,
    ): Promise<boolean> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          await updateCourseLessonStatusApi(accessToken, courseId, lessonId, status);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['courses'] }),
            queryClient.invalidateQueries({ queryKey: ['course-detail', userIdKey, courseId] }),
          ]);
          return true;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de mettre à jour la progression du chapitre.',
          );
          return false;
        }
      }

      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        courses: prev.courses.map((course) => {
          if (course.id !== courseId) return course;
          const nextLevels = course.levels.map((lv) =>
            withComputedLevelReadiness({
              ...lv,
              lessons: lv.lessons.map((l) =>
                l.id !== lessonId
                  ? l
                  : {
                      ...l,
                      status,
                      completedAt: status === 'completed' ? nowIso : null,
                      updatedAt: nowIso,
                    },
              ),
            }),
          );
          const allLessons = nextLevels.flatMap((lv) => lv.lessons);
          return {
            ...course,
            levels: nextLevels,
            completedLessonsCount: allLessons.filter((l) => l.status === 'completed').length,
            totalLessonsCount: allLessons.length,
            updatedAt: nowIso,
          };
        }),
      }));
      return true;
    },
    [accessToken, isApiMode, queryClient, userIdKey],
  );

  const addResource = useCallback(
    async (courseId: string, input: CourseResourceInput): Promise<CourseResource | null> => {
      setMutationError(null);
      if (input.title.trim().length < 2 || !/^https?:\/\/\S+$/i.test(input.url.trim())) {
        setMutationError('Saisissez un titre et une URL valide commençant par http:// ou https://.');
        return null;
      }
      if (isApiMode) {
        try {
          const created = await createCourseResourceApi(accessToken, courseId, input);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['courses'] }),
            queryClient.invalidateQueries({ queryKey: ['course-detail', userIdKey, courseId] }),
          ]);
          return created;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible d’ajouter la ressource.',
          );
          return null;
        }
      }

      const nowIso = new Date().toISOString();
      const created: CourseResource = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        courseId,
        levelId: input.levelId ?? null,
        lessonId: input.lessonId ?? null,
        title: input.title.trim(),
        url: input.url.trim(),
        resourceType: input.resourceType,
        language: input.language,
        isOfficial: input.isOfficial,
        sourceName: input.sourceName?.trim() || null,
        notes: input.notes?.trim() || null,
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({
        ...prev,
        courses: prev.courses.map((course) => {
          if (course.id !== courseId) return course;
          const nextResources = [created, ...course.resources];
          return {
            ...course,
            resources: nextResources,
            resourcesCount: nextResources.length,
            levels: course.levels.map((lv) =>
              lv.id === created.levelId
                ? { ...lv, resources: [created, ...lv.resources] }
                : lv,
            ),
            updatedAt: nowIso,
          };
        }),
      }));
      return created;
    },
    [accessToken, isApiMode, queryClient, userIdKey],
  );

  const deleteResource = useCallback(
    async (courseId: string, resourceId: string): Promise<boolean> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          await deleteCourseResourceApi(accessToken, courseId, resourceId);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['courses'] }),
            queryClient.invalidateQueries({ queryKey: ['course-detail', userIdKey, courseId] }),
          ]);
          return true;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de supprimer la ressource.',
          );
          return false;
        }
      }

      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        courses: prev.courses.map((course) => {
          if (course.id !== courseId) return course;
          const nextResources = course.resources.filter((r) => r.id !== resourceId);
          return {
            ...course,
            resources: nextResources,
            resourcesCount: nextResources.length,
            levels: course.levels.map((lv) => ({
              ...lv,
              resources: lv.resources.filter((r) => r.id !== resourceId),
            })),
            updatedAt: nowIso,
          };
        }),
      }));
      return true;
    },
    [accessToken, isApiMode, queryClient, userIdKey],
  );

  const submitWork = useCallback(
    async (
      courseId: string,
      levelId: string,
      input: CourseSubmissionInput,
    ): Promise<CourseSubmission | null> => {
      setMutationError(null);
      if (input.answerText.trim().length < 1) {
        setMutationError('Veuillez saisir ou sélectionner une réponse.');
        return null;
      }

      if (isApiMode) {
        try {
          const submission = await submitCourseWorkApi(accessToken, courseId, levelId, input);
          await queryClient.invalidateQueries({
            queryKey: ['course-detail', userIdKey, courseId],
          });
          return submission;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible d’évaluer la soumission.',
          );
          return null;
        }
      }

      const targetCourse = localState.courses.find((c) => c.id === courseId);
      const targetLevel = targetCourse?.levels.find((lv) => lv.id === levelId);
      if (!targetCourse || !targetLevel) {
        setMutationError('Cours ou niveau introuvable.');
        return null;
      }
      if (targetLevel.status === 'locked') {
        setMutationError('Ce niveau est verrouillé : validez d’abord le niveau précédent.');
        return null;
      }

      const evaluated = evaluateCourseSubmissionLocal({
        course: targetCourse,
        level: targetLevel,
        submissionKind: input.submissionKind,
        input,
      });

      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        courses: prev.courses.map((course) => {
          if (course.id !== courseId) return course;
          return {
            ...course,
            levels: course.levels.map((lv) => {
              if (lv.id !== levelId) return lv;
              const nextSubs = [evaluated, ...lv.submissions];
              return withComputedLevelReadiness({
                ...lv,
                submissions: nextSubs,
                updatedAt: nowIso,
              });
            }),
            updatedAt: nowIso,
          };
        }),
      }));

      return evaluated;
    },
    [accessToken, isApiMode, localState.courses, queryClient, userIdKey],
  );

  const validateLevel = useCallback(
    async (courseId: string, levelId: string): Promise<CourseDetail | null> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          const updated = await validateCourseLevelApi(accessToken, courseId, levelId);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['courses'] }),
            queryClient.invalidateQueries({ queryKey: ['course-detail', userIdKey, courseId] }),
            queryClient.invalidateQueries({ queryKey: ['skills'] }),
            queryClient.invalidateQueries({ queryKey: ['skill-evidence'] }),
          ]);
          return updated;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de valider ce niveau.',
          );
          return null;
        }
      }

      const existing = localState.courses.find((c) => c.id === courseId);
      if (!existing) {
        setMutationError('Cours introuvable.');
        return null;
      }

      const { updated, error: validationErr } = validateCourseLevelLocal(existing, levelId);
      if (validationErr) {
        setMutationError(validationErr);
        return null;
      }

      const matchedSkill =
        learningStore.skills.find((s) => s.id === updated.skillId) ??
        learningStore.skills.find(
          (s) => s.name.trim().toLowerCase() === updated.subject.trim().toLowerCase(),
        );
      if (matchedSkill) {
        const validatedLevel = updated.levels.find((lv) => lv.id === levelId);
        updated.skillId = matchedSkill.id;
        await learningStore.addEvidence(matchedSkill.id, {
          type: 'project',
          description: `Validation du niveau ${validatedLevel?.levelNumber ?? ''} du cours « ${updated.title} » : ${validatedLevel?.projectTitle ?? 'Projet pratique'}`,
          result: 'Projet validé selon la grille de correction.',
        });
      }

      setLocalState((prev) => ({
        ...prev,
        courses: prev.courses.map((c) => (c.id === courseId ? updated : c)),
      }));
      return updated;
    },
    [accessToken, isApiMode, learningStore, localState.courses, queryClient, userIdKey],
  );

  const regenerateLevel = useCallback(
    async (
      courseId: string,
      levelId: string,
      focusHint?: string,
    ): Promise<CourseDetail | null> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          const updated = await regenerateCourseLevelApi(accessToken, courseId, levelId, focusHint);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['courses'] }),
            queryClient.invalidateQueries({ queryKey: ['course-detail', userIdKey, courseId] }),
          ]);
          return updated;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de régénérer ce niveau.',
          );
          return null;
        }
      }

      const existing = localState.courses.find((c) => c.id === courseId);
      if (!existing) {
        setMutationError('Cours introuvable.');
        return null;
      }
      const { updated, error: regenErr } = regenerateCourseLevelLocal(existing, levelId);
      if (regenErr) {
        setMutationError(regenErr);
        return null;
      }
      setLocalState((prev) => ({
        ...prev,
        courses: prev.courses.map((c) => (c.id === courseId ? updated : c)),
      }));
      return updated;
    },
    [accessToken, isApiMode, localState.courses, queryClient, userIdKey],
  );

  const courses = useMemo(
    () =>
      isApiMode
        ? (coursesQuery.data ?? [])
        : localState.courses.map((c) => summarizeCourse(c)),
    [coursesQuery.data, isApiMode, localState.courses],
  );

  const isLoading = isApiMode && coursesQuery.isLoading;
  const error =
    isApiMode && coursesQuery.error
      ? coursesQuery.error instanceof Error
        ? coursesQuery.error.message
        : 'Impossible de charger vos cours.'
      : null;

  const value = useMemo<CoursesStoreContextValue>(
    () => ({
      courses,
      localDetails: localState.courses,
      isApiMode,
      isLoading,
      error,
      mutationError,
      clearMutationError,
      retry,
      previewCourse,
      createCourse,
      updateCourse,
      deleteCourse,
      updateLessonStatus,
      addResource,
      deleteResource,
      submitWork,
      validateLevel,
      regenerateLevel,
    }),
    [
      courses,
      localState.courses,
      isApiMode,
      isLoading,
      error,
      mutationError,
      clearMutationError,
      retry,
      previewCourse,
      createCourse,
      updateCourse,
      deleteCourse,
      updateLessonStatus,
      addResource,
      deleteResource,
      submitWork,
      validateLevel,
      regenerateLevel,
    ],
  );

  return <CoursesStoreContext.Provider value={value}>{children}</CoursesStoreContext.Provider>;
}

export function useCoursesStore(): CoursesStoreContextValue {
  const ctx = useContext(CoursesStoreContext);
  if (!ctx) {
    throw new Error('useCoursesStore doit être utilisé à l’intérieur de CoursesStoreProvider.');
  }
  return ctx;
}

export function useCourseDetail(courseId: string | undefined): {
  detail: CourseDetail | null;
  isLoading: boolean;
  error: string | null;
  retry: () => void;
} {
  const { session, logout } = useAuth();
  const queryClient = useQueryClient();
  const { localDetails, isApiMode } = useCoursesStore();
  const accessToken = session?.mode === 'api' ? session.accessToken : '';
  const userIdKey = session?.userId ?? 'anonymous';

  const detailQuery = useQuery({
    queryKey: ['course-detail', userIdKey, courseId],
    queryFn: () => fetchCourseDetailApi(accessToken, courseId!),
    enabled: isApiMode && Boolean(courseId),
  });

  useEffect(() => {
    if (detailQuery.error instanceof ApiError && detailQuery.error.status === 401) {
      logout('Votre session a expiré. Veuillez vous reconnecter.');
    }
  }, [detailQuery.error, logout]);

  const retry = useCallback(() => {
    if (courseId) {
      void queryClient.invalidateQueries({ queryKey: ['course-detail', userIdKey, courseId] });
    }
  }, [courseId, queryClient, userIdKey]);

  if (!courseId) {
    return { detail: null, isLoading: false, error: null, retry };
  }

  if (isApiMode) {
    return {
      detail: detailQuery.data ?? null,
      isLoading: detailQuery.isLoading,
      error: detailQuery.error
        ? detailQuery.error instanceof Error
          ? detailQuery.error.message
          : 'Impossible de charger ce cours.'
        : null,
      retry,
    };
  }

  const localMatch = localDetails.find((c) => c.id === courseId) ?? null;
  return {
    detail: localMatch,
    isLoading: false,
    error: null,
    retry,
  };
}
