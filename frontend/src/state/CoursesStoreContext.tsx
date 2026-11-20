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
import type {
  CourseDetail,
  CourseLessonStatus,
  CoursePreview,
  CourseResource,
  CourseSubmission,
  CourseSummary,
} from '../types/domain';
import { useAuth } from './AuthContext';

export interface CoursesStoreContextValue {
  courses: CourseSummary[];
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
  const queryClient = useQueryClient();

  const isApiMode = session?.mode === 'api' && Boolean(session.accessToken);
  const accessToken = session?.mode === 'api' ? session.accessToken : '';
  const userIdKey = session?.userId ?? 'anonymous';

  const [mutationError, setMutationError] = useState<string | null>(null);

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
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return null;
      }
      try {
        return await previewCourseApi(accessToken, input);
      } catch (err) {
        setMutationError(
          err instanceof Error ? err.message : 'Impossible de générer la prévisualisation du cours.',
        );
        return null;
      }
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
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return null;
      }
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
    },
    [accessToken, isApiMode, queryClient],
  );

  const updateCourse = useCallback(
    async (courseId: string, patch: CourseUpdateInput): Promise<boolean> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }
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
    },
    [accessToken, isApiMode, queryClient, userIdKey],
  );

  const deleteCourse = useCallback(
    async (courseId: string): Promise<boolean> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }
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
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }
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
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return null;
      }
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
    },
    [accessToken, isApiMode, queryClient, userIdKey],
  );

  const deleteResource = useCallback(
    async (courseId: string, resourceId: string): Promise<boolean> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }
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
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return null;
      }
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
    },
    [accessToken, isApiMode, queryClient, userIdKey],
  );

  const validateLevel = useCallback(
    async (courseId: string, levelId: string): Promise<CourseDetail | null> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return null;
      }
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
    },
    [accessToken, isApiMode, queryClient, userIdKey],
  );

  const regenerateLevel = useCallback(
    async (
      courseId: string,
      levelId: string,
      focusHint?: string,
    ): Promise<CourseDetail | null> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return null;
      }
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
    },
    [accessToken, isApiMode, queryClient, userIdKey],
  );

  const courses = useMemo(
    () => (isApiMode ? (coursesQuery.data ?? []) : []),
    [coursesQuery.data, isApiMode],
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
  const isApiMode = session?.mode === 'api' && Boolean(session.accessToken);
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

  return {
    detail: detailQuery.data ?? null,
    isLoading: isApiMode && detailQuery.isLoading,
    error: detailQuery.error
      ? detailQuery.error instanceof Error
        ? detailQuery.error.message
        : 'Impossible de charger ce cours.'
      : null,
    retry,
  };
}
