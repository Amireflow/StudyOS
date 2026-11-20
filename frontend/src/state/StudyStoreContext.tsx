import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import type { ScheduleEventFormValues } from '../features/schedule/scheduleSchema';
import type { ManualSessionValues, StartSessionValues } from '../features/sessions/sessionSchema';
import type { TaskFormValues } from '../features/tasks/taskSchema';
import { ApiError } from '../lib/api-client';
import { toLocalDateKey } from '../lib/date';
import {
  analyzeTimetableFileApi,
  cancelSessionApi,
  cancelTimetableImportApi,
  confirmTimetableImportApi,
  createScheduleEventApi,
  createTaskApi,
  deleteScheduleEventApi,
  deleteSessionApi,
  deleteTaskApi,
  deleteTimetableImportSourceApi,
  duplicateWeekApi,
  fetchProfileApi,
  fetchScheduleEventsApi,
  fetchSessionsApi,
  fetchTasksApi,
  finishSessionApi,
  recordManualSessionApi,
  startSessionApi,
  updateProfileApi,
  updateScheduleEventApi,
  updateTaskApi,
  updateTimetableImportDraftApi,
} from '../lib/studyApi';
import type {
  ExtractedCourseRow,
  ScheduleEvent,
  SessionFinishExtra,
  StudySession,
  Task,
  TaskStatus,
  TimetableImport,
  TimetableImportConfirmResult,
} from '../types/domain';
import { useAuth } from './AuthContext';
import { useTheme, type ThemePreference } from './ThemeContext';

export interface StudyProfile {
  displayName: string;
  timezone: string;
  aiInstructions: string | null;
  preferences?: Record<string, unknown>;
}

export interface StudyState {
  profile: StudyProfile;
  activePriorityTitle: string | null;
  activePriorityTaskId: string | null;
  activePriorityProjectId: string | null;
  tasks: Task[];
  sessions: StudySession[];
  scheduleEvents: ScheduleEvent[];
}

export interface StudyStoreContextValue extends StudyState {
  isLoading: boolean;
  error: string | null;
  mutationError: string | null;
  clearMutationError: () => void;
  retry: () => void;
  updateProfile: (patch: Partial<StudyProfile>) => Promise<boolean>;
  setActivePriority: (
    title: string | null,
    taskId?: string | null,
    projectId?: string | null,
  ) => Promise<boolean>;
  createTask: (input: TaskFormValues) => Promise<boolean>;
  updateTask: (id: string, input: TaskFormValues) => Promise<boolean>;
  setTaskStatus: (id: string, status: TaskStatus) => Promise<boolean>;
  deleteTask: (id: string) => Promise<boolean>;
  startSession: (input: StartSessionValues) => Promise<boolean>;
  finishSession: (
    id: string,
    result: string,
    extra?: SessionFinishExtra,
  ) => Promise<boolean>;
  cancelSession: (id: string) => Promise<boolean>;
  recordManualSession: (input: ManualSessionValues) => Promise<boolean>;
  deleteSession: (id: string) => Promise<boolean>;
  createScheduleEvent: (values: ScheduleEventFormValues) => Promise<boolean>;
  updateScheduleEvent: (id: string, values: ScheduleEventFormValues) => Promise<boolean>;
  deleteScheduleEvent: (id: string) => Promise<boolean>;
  duplicateWeekEvents: (
    weekStart: Date,
  ) => Promise<{ createdCount: number; skippedCount: number } | null>;
  analyzeTimetableFile: (file: File) => Promise<TimetableImport | null>;
  updateTimetableImportDraft: (
    importRecord: TimetableImport,
    options: {
      courses: ExtractedCourseRow[];
      validFrom?: string | null;
      validUntil?: string | null;
    },
  ) => Promise<TimetableImport | null>;
  confirmTimetableImport: (
    importRecord: TimetableImport,
    options: {
      courses: ExtractedCourseRow[];
      validFrom?: string | null;
      validUntil?: string | null;
      targetWeekStart?: string;
      recurrenceWeeks?: number;
      replaceExistingImported?: boolean;
    },
  ) => Promise<TimetableImportConfirmResult | null>;
  cancelTimetableImport: (importId: string) => Promise<boolean>;
  deleteTimetableImportSource: (importId: string) => Promise<boolean>;
}

const StudyStoreContext = createContext<StudyStoreContextValue | null>(null);

export function StudyStoreProvider({ children }: { children: ReactNode }) {
  const { session, logout, updateSessionDisplayName } = useAuth();
  const { theme, setTheme } = useTheme();
  const queryClient = useQueryClient();

  const isApiMode = session?.mode === 'api' && Boolean(session.accessToken);
  const accessToken = session?.mode === 'api' ? session.accessToken : '';
  const userIdKey = session?.userId ?? 'anonymous';

  const [mutationError, setMutationError] = useState<string | null>(null);
  const themeSyncRef = useRef<{
    userId: string;
    pendingTarget: ThemePreference | null;
    syncedTheme: ThemePreference;
  } | null>(null);

  const profileQuery = useQuery({
    queryKey: ['profile', userIdKey],
    queryFn: () => fetchProfileApi(accessToken),
    enabled: isApiMode,
  });

  useEffect(() => {
    if (!isApiMode || !profileQuery.isSuccess || !profileQuery.data) {
      return;
    }
    const rawServerTheme = profileQuery.data.preferences?.theme;
    const serverTheme: ThemePreference =
      rawServerTheme === 'light' || rawServerTheme === 'dark' || rawServerTheme === 'system'
        ? rawServerTheme
        : 'system';

    const current = themeSyncRef.current;
    if (!current || current.userId !== userIdKey) {
      themeSyncRef.current = {
        userId: userIdKey,
        pendingTarget: theme !== serverTheme ? serverTheme : null,
        syncedTheme: serverTheme,
      };
      if (theme !== serverTheme) {
        setTheme(serverTheme);
      }
      return;
    }

    if (current.pendingTarget !== null) {
      if (theme === current.pendingTarget) {
        current.pendingTarget = null;
        current.syncedTheme = theme;
      }
      return;
    }

    if (theme !== current.syncedTheme) {
      current.syncedTheme = theme;
      const mergedPreferences = {
        ...(profileQuery.data.preferences ?? {}),
        theme,
      };
      void updateProfileApi(accessToken, { preferences: mergedPreferences })
        .then((updated) => {
          queryClient.setQueryData(['profile', userIdKey], updated);
        })
        .catch(() => {
          // Ne bloque pas l'interface si la sauvegarde réseau du thème échoue.
        });
    }
  }, [isApiMode, profileQuery.isSuccess, profileQuery.data, userIdKey, theme, setTheme, accessToken, queryClient]);

  const tasksQuery = useQuery({
    queryKey: ['tasks', userIdKey],
    queryFn: () => fetchTasksApi(accessToken),
    enabled: isApiMode,
  });

  const sessionsQuery = useQuery({
    queryKey: ['sessions', userIdKey],
    queryFn: () => fetchSessionsApi(accessToken),
    enabled: isApiMode,
  });

  const scheduleQuery = useQuery({
    queryKey: ['schedule', userIdKey],
    queryFn: () => fetchScheduleEventsApi(accessToken),
    enabled: isApiMode,
  });

  const firstQueryError =
    profileQuery.error ?? tasksQuery.error ?? sessionsQuery.error ?? scheduleQuery.error;

  useEffect(() => {
    if (!isApiMode || !firstQueryError) {
      return;
    }
    if (firstQueryError instanceof ApiError && firstQueryError.status === 401) {
      queryClient.clear();
      logout('Votre session a expiré. Veuillez vous reconnecter.');
    }
  }, [isApiMode, firstQueryError, queryClient, logout]);

  const retry = useCallback(() => {
    if (!isApiMode) {
      return;
    }
    void Promise.all([
      profileQuery.refetch(),
      tasksQuery.refetch(),
      sessionsQuery.refetch(),
      scheduleQuery.refetch(),
    ]);
  }, [isApiMode, profileQuery, tasksQuery, sessionsQuery, scheduleQuery]);

  const runApiMutation = useCallback(
    async <T,>(
      action: () => Promise<T>,
      invalidateKeys: readonly string[],
    ): Promise<{ ok: true; data: T } | { ok: false }> => {
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return { ok: false };
      }
      setMutationError(null);
      try {
        const data = await action();
        await Promise.all(
          invalidateKeys.map((key) => queryClient.invalidateQueries({ queryKey: [key, userIdKey] })),
        );
        return { ok: true, data };
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          queryClient.clear();
          logout('Votre session a expiré. Veuillez vous reconnecter.');
          return { ok: false };
        }
        setMutationError(
          err instanceof Error ? err.message : 'Une erreur est survenue lors de l’enregistrement.',
        );
        return { ok: false };
      }
    },
    [isApiMode, queryClient, userIdKey, logout],
  );

  const actions = useMemo(() => {
    const updateProfile = async (patch: Partial<StudyProfile>): Promise<boolean> => {
      const result = await runApiMutation(
        () => updateProfileApi(accessToken, patch),
        ['profile'],
      );
      if (result.ok && patch.displayName) {
        updateSessionDisplayName(result.data.displayName);
      }
      return result.ok;
    };

    const setActivePriority = async (
      title: string | null,
      taskId: string | null = null,
      projectId: string | null = null,
    ): Promise<boolean> => {
      const normalized = title?.trim() || null;
      const result = await runApiMutation(
        () =>
          updateProfileApi(accessToken, {
            activePriorityTitle: normalized,
            activePriorityTaskId: normalized ? taskId : null,
            activePriorityProjectId: normalized ? projectId : null,
          }),
        ['profile'],
      );
      return result.ok;
    };

    const createTask = async (input: TaskFormValues): Promise<boolean> => {
      const result = await runApiMutation(() => createTaskApi(accessToken, input), ['tasks']);
      return result.ok;
    };

    const updateTask = async (id: string, input: TaskFormValues): Promise<boolean> => {
      const result = await runApiMutation(
        () => updateTaskApi(accessToken, id, input),
        ['tasks', 'profile'],
      );
      return result.ok;
    };

    const setTaskStatus = async (id: string, status: TaskStatus): Promise<boolean> => {
      const result = await runApiMutation(
        () => updateTaskApi(accessToken, id, { status }),
        ['tasks', 'profile'],
      );
      return result.ok;
    };

    const deleteTask = async (id: string): Promise<boolean> => {
      const result = await runApiMutation(
        () => deleteTaskApi(accessToken, id),
        ['tasks', 'profile', 'sessions'],
      );
      return result.ok;
    };

    const startSession = async (input: StartSessionValues): Promise<boolean> => {
      const result = await runApiMutation(() => startSessionApi(accessToken, input), ['sessions']);
      return result.ok;
    };

    const finishSession = async (
      id: string,
      resultText: string,
      extra?: SessionFinishExtra,
    ): Promise<boolean> => {
      const result = await runApiMutation(
        () => finishSessionApi(accessToken, id, resultText, extra),
        ['sessions'],
      );
      return result.ok;
    };

    const cancelSession = async (id: string): Promise<boolean> => {
      const result = await runApiMutation(() => cancelSessionApi(accessToken, id), ['sessions']);
      return result.ok;
    };

    const recordManualSession = async (input: ManualSessionValues): Promise<boolean> => {
      const result = await runApiMutation(
        () => recordManualSessionApi(accessToken, input),
        ['sessions'],
      );
      return result.ok;
    };

    const deleteSession = async (id: string): Promise<boolean> => {
      const result = await runApiMutation(() => deleteSessionApi(accessToken, id), ['sessions']);
      return result.ok;
    };

    const createScheduleEvent = async (values: ScheduleEventFormValues): Promise<boolean> => {
      const result = await runApiMutation(
        () => createScheduleEventApi(accessToken, values),
        ['schedule'],
      );
      return result.ok;
    };

    const updateScheduleEvent = async (
      id: string,
      values: ScheduleEventFormValues,
    ): Promise<boolean> => {
      const result = await runApiMutation(
        () => updateScheduleEventApi(accessToken, id, values),
        ['schedule'],
      );
      return result.ok;
    };

    const deleteScheduleEvent = async (id: string): Promise<boolean> => {
      const result = await runApiMutation(
        () => deleteScheduleEventApi(accessToken, id),
        ['schedule'],
      );
      return result.ok;
    };

    const duplicateWeekEvents = async (
      weekStart: Date,
    ): Promise<{ createdCount: number; skippedCount: number } | null> => {
      const result = await runApiMutation(
        () => duplicateWeekApi(accessToken, toLocalDateKey(weekStart)),
        ['schedule'],
      );
      return result.ok ? result.data : null;
    };

    const analyzeTimetableFile = async (file: File): Promise<TimetableImport | null> => {
      const result = await runApiMutation(
        () => analyzeTimetableFileApi(accessToken, file),
        [],
      );
      return result.ok ? result.data : null;
    };

    const updateTimetableImportDraft = async (
      importRecord: TimetableImport,
      options: {
        courses: ExtractedCourseRow[];
        validFrom?: string | null;
        validUntil?: string | null;
      },
    ): Promise<TimetableImport | null> => {
      const result = await runApiMutation(
        () =>
          updateTimetableImportDraftApi(accessToken, importRecord.id, {
            courses: options.courses,
            validFrom: options.validFrom ?? importRecord.validFrom,
            validUntil: options.validUntil ?? importRecord.validUntil,
          }),
        [],
      );
      return result.ok ? result.data : null;
    };

    const confirmTimetableImport = async (
      importRecord: TimetableImport,
      options: {
        courses: ExtractedCourseRow[];
        validFrom?: string | null;
        validUntil?: string | null;
        targetWeekStart?: string;
        recurrenceWeeks?: number;
        replaceExistingImported?: boolean;
      },
    ): Promise<TimetableImportConfirmResult | null> => {
      const result = await runApiMutation(
        () =>
          confirmTimetableImportApi(accessToken, importRecord.id, {
            courses: options.courses,
            validFrom: options.validFrom ?? importRecord.validFrom,
            validUntil: options.validUntil ?? importRecord.validUntil,
            targetWeekStart: options.targetWeekStart ?? null,
            recurrenceWeeks: options.recurrenceWeeks ?? 1,
            replaceExistingImported: options.replaceExistingImported ?? false,
          }),
        ['schedule'],
      );
      return result.ok ? result.data : null;
    };

    const cancelTimetableImport = async (importId: string): Promise<boolean> => {
      const result = await runApiMutation(
        () => cancelTimetableImportApi(accessToken, importId),
        [],
      );
      return result.ok;
    };

    const deleteTimetableImportSource = async (importId: string): Promise<boolean> => {
      const result = await runApiMutation(
        () => deleteTimetableImportSourceApi(accessToken, importId),
        [],
      );
      return result.ok;
    };

    return {
      updateProfile,
      setActivePriority,
      createTask,
      updateTask,
      setTaskStatus,
      deleteTask,
      startSession,
      finishSession,
      cancelSession,
      recordManualSession,
      deleteSession,
      createScheduleEvent,
      updateScheduleEvent,
      deleteScheduleEvent,
      duplicateWeekEvents,
      analyzeTimetableFile,
      updateTimetableImportDraft,
      confirmTimetableImport,
      cancelTimetableImport,
      deleteTimetableImportSource,
    };
  }, [accessToken, runApiMutation, updateSessionDisplayName]);

  const resolvedState: StudyState = useMemo(
    () => ({
      profile: profileQuery.data
        ? {
            displayName: profileQuery.data.displayName,
            timezone: profileQuery.data.timezone,
            aiInstructions: profileQuery.data.aiInstructions,
            preferences: profileQuery.data.preferences,
          }
        : {
            displayName: session?.displayName || 'Utilisateur',
            timezone: 'Africa/Dakar',
            aiInstructions: null,
          },
      activePriorityTitle: profileQuery.data?.activePriorityTitle ?? null,
      activePriorityTaskId: profileQuery.data?.activePriorityTaskId ?? null,
      activePriorityProjectId: profileQuery.data?.activePriorityProjectId ?? null,
      tasks: tasksQuery.data ?? [],
      sessions: sessionsQuery.data ?? [],
      scheduleEvents: scheduleQuery.data ?? [],
    }),
    [
      session?.displayName,
      profileQuery.data,
      tasksQuery.data,
      sessionsQuery.data,
      scheduleQuery.data,
    ],
  );

  const isLoading =
    isApiMode &&
    (profileQuery.isLoading ||
      tasksQuery.isLoading ||
      sessionsQuery.isLoading ||
      scheduleQuery.isLoading);

  const error =
    isApiMode && firstQueryError
      ? firstQueryError instanceof Error
        ? firstQueryError.message
        : 'Impossible de charger vos données depuis le serveur.'
      : null;

  const clearMutationError = useCallback(() => {
    setMutationError(null);
  }, []);

  const value = useMemo<StudyStoreContextValue>(
    () => ({
      ...resolvedState,
      isLoading,
      error,
      mutationError,
      clearMutationError,
      retry,
      ...actions,
    }),
    [
      resolvedState,
      isLoading,
      error,
      mutationError,
      clearMutationError,
      retry,
      actions,
    ],
  );

  return <StudyStoreContext.Provider value={value}>{children}</StudyStoreContext.Provider>;
}

export function useStudyStore(): StudyStoreContextValue {
  const ctx = useContext(StudyStoreContext);
  if (!ctx) {
    throw new Error('useStudyStore doit être utilisé à l’intérieur de StudyStoreProvider.');
  }
  return ctx;
}
