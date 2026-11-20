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
import { buildDuplicatedWeekEvents, getEventsForWeek } from '../features/schedule/scheduleUtils';
import type { ManualSessionValues, StartSessionValues } from '../features/sessions/sessionSchema';
import type { TaskFormValues } from '../features/tasks/taskSchema';
import { ApiError } from '../lib/api-client';
import {
  addDays,
  dateInputToDueIso,
  localDateAndTimeToIso,
  toLocalDateKey,
} from '../lib/date';
import { generateId, readFromStorage, STORAGE_KEYS, writeToStorage } from '../lib/storage';
import {
  cancelSessionApi,
  createScheduleEventApi,
  createTaskApi,
  deleteScheduleEventApi,
  deleteSessionApi,
  deleteTaskApi,
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
} from '../lib/studyApi';
import type { ScheduleEvent, StudySession, Task, TaskStatus } from '../types/domain';
import { useAuth } from './AuthContext';

const LOCAL_USER_ID = 'local-user';

export interface LocalProfile {
  displayName: string;
  timezone: string;
  aiInstructions: string | null;
}

export interface StudyState {
  profile: LocalProfile;
  activePriorityTitle: string | null;
  activePriorityTaskId: string | null;
  activePriorityProjectId: string | null;
  tasks: Task[];
  sessions: StudySession[];
  scheduleEvents: ScheduleEvent[];
}

const DEFAULT_LOCAL_PROFILE: LocalProfile = {
  displayName: 'Utilisateur',
  timezone: 'Africa/Dakar',
  aiInstructions: null,
};

const DEFAULT_STUDY_STATE: StudyState = {
  profile: DEFAULT_LOCAL_PROFILE,
  activePriorityTitle: null,
  activePriorityTaskId: null,
  activePriorityProjectId: null,
  tasks: [],
  sessions: [],
  scheduleEvents: [],
};

function sanitizeStoredState(raw: unknown): StudyState {
  if (!raw || typeof raw !== 'object') {
    return DEFAULT_STUDY_STATE;
  }
  const candidate = raw as Partial<StudyState>;
  const rawProfile =
    candidate.profile && typeof candidate.profile === 'object' ? candidate.profile : null;

  return {
    profile: {
      displayName:
        rawProfile && typeof rawProfile.displayName === 'string' && rawProfile.displayName.trim()
          ? rawProfile.displayName.trim()
          : DEFAULT_LOCAL_PROFILE.displayName,
      timezone:
        rawProfile && typeof rawProfile.timezone === 'string' && rawProfile.timezone.trim()
          ? rawProfile.timezone.trim()
          : DEFAULT_LOCAL_PROFILE.timezone,
      aiInstructions:
        rawProfile && typeof rawProfile.aiInstructions === 'string'
          ? rawProfile.aiInstructions
          : null,
    },
    activePriorityTitle:
      typeof candidate.activePriorityTitle === 'string' && candidate.activePriorityTitle.trim()
        ? candidate.activePriorityTitle
        : null,
    activePriorityTaskId:
      typeof candidate.activePriorityTaskId === 'string' ? candidate.activePriorityTaskId : null,
    activePriorityProjectId:
      typeof candidate.activePriorityProjectId === 'string'
        ? candidate.activePriorityProjectId
        : null,
    tasks: Array.isArray(candidate.tasks) ? candidate.tasks : [],
    sessions: Array.isArray(candidate.sessions) ? candidate.sessions : [],
    scheduleEvents: Array.isArray(candidate.scheduleEvents) ? candidate.scheduleEvents : [],
  };
}

function buildDemoState(now = new Date()): StudyState {
  const nowIso = now.toISOString();
  const todayDue = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
    23,
    59,
    0,
    0,
  ).toISOString();
  const tomorrowDue = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() + 1,
    23,
    59,
    0,
    0,
  ).toISOString();
  const yesterdayIso = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();

  const primaryTaskId = generateId();
  const secondTaskId = generateId();
  const doneTaskId = generateId();
  const parkedTaskId = generateId();

  const session1Start = new Date(now.getTime() - 5 * 60 * 60 * 1000);
  const session1End = new Date(session1Start.getTime() + 75 * 60 * 1000);
  const session2Start = new Date(now.getTime() - 26 * 60 * 60 * 1000);
  const session2End = new Date(session2Start.getTime() + 50 * 60 * 1000);

  return {
    profile: DEFAULT_LOCAL_PROFILE,
    activePriorityTitle: 'Consolider les formulaires React et la validation Zod',
    activePriorityTaskId: primaryTaskId,
    activePriorityProjectId: null,
    tasks: [
      {
        id: primaryTaskId,
        userId: LOCAL_USER_ID,
        title: 'Consolider les formulaires React et la validation Zod',
        description: 'Implémenter et tester les formulaires Tâches et Séances du Lot 2.',
        status: 'in_progress',
        priority: 'critical',
        dueAt: todayDue,
        completedAt: null,
        source: 'manual',
        proposalId: null,
        projectId: null,
        moduleId: null,
        createdAt: yesterdayIso,
        updatedAt: nowIso,
      },
      {
        id: secondTaskId,
        userId: LOCAL_USER_ID,
        title: 'Préparer les exercices sur les dictionnaires Python',
        description: 'Revoir les compréhensions de dictionnaires avant le module Backend.',
        status: 'todo',
        priority: 'high',
        dueAt: tomorrowDue,
        completedAt: null,
        source: 'manual',
        proposalId: null,
        projectId: null,
        moduleId: null,
        createdAt: yesterdayIso,
        updatedAt: yesterdayIso,
      },
      {
        id: doneTaskId,
        userId: LOCAL_USER_ID,
        title: 'Mettre en place la navigation responsive React Router',
        description: 'Barre latérale desktop et tiroir mobile accessible validés.',
        status: 'done',
        priority: 'normal',
        dueAt: yesterdayIso,
        completedAt: yesterdayIso,
        source: 'manual',
        proposalId: null,
        projectId: null,
        moduleId: null,
        createdAt: yesterdayIso,
        updatedAt: yesterdayIso,
      },
      {
        id: parkedTaskId,
        userId: LOCAL_USER_ID,
        title: 'Explorer un thème sombre optionnel après le MVP',
        description: 'Idée mise au parking pour protéger la priorité principale.',
        status: 'parked',
        priority: 'low',
        dueAt: null,
        completedAt: null,
        source: 'manual',
        proposalId: null,
        projectId: null,
        moduleId: null,
        createdAt: yesterdayIso,
        updatedAt: yesterdayIso,
      },
    ],
    sessions: [
      {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: 'Atelier composants UI et accessibilité',
        category: 'Apprentissage',
        status: 'completed',
        startedAt: session1Start.toISOString(),
        endedAt: session1End.toISOString(),
        result: '4 états visuels (loading, empty, error, success) implémentés et testés.',
        taskId: doneTaskId,
        projectId: null,
        moduleId: null,
        lessonId: null,
        skillId: null,
        createdAt: session1End.toISOString(),
        updatedAt: session1End.toISOString(),
      },
      {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: 'Révision algorithmique — structures de données',
        category: 'Cours',
        status: 'completed',
        startedAt: session2Start.toISOString(),
        endedAt: session2End.toISOString(),
        result: '3 exercices résolus sur les tables de hachage et complexité O(1).',
        taskId: null,
        projectId: null,
        moduleId: null,
        lessonId: null,
        skillId: null,
        createdAt: session2End.toISOString(),
        updatedAt: session2End.toISOString(),
      },
    ],
    scheduleEvents: [
      {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: 'Cours d’algorithmique',
        type: 'course',
        startsAt: localDateAndTimeToIso(toLocalDateKey(now), '09:00'),
        endsAt: localDateAndTimeToIso(toLocalDateKey(now), '11:00'),
        notes: 'Complexité et arbres binaires.',
        createdAt: nowIso,
        updatedAt: nowIso,
      },
      {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: 'Atelier React & TypeScript',
        type: 'learning',
        startsAt: localDateAndTimeToIso(toLocalDateKey(now), '15:00'),
        endsAt: localDateAndTimeToIso(toLocalDateKey(now), '16:30'),
        notes: 'Pratique hooks et typage strict.',
        createdAt: nowIso,
        updatedAt: nowIso,
      },
      {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: 'Travail sur Amireflow Study OS',
        type: 'project',
        startsAt: localDateAndTimeToIso(toLocalDateKey(addDays(now, 1)), '10:00'),
        endsAt: localDateAndTimeToIso(toLocalDateKey(addDays(now, 1)), '12:00'),
        notes: 'Préparation du backend Python (Lot 4).',
        createdAt: nowIso,
        updatedAt: nowIso,
      },
    ],
  };
}

export interface StudyStoreContextValue extends StudyState {
  dataMode: 'api' | 'local_demo';
  isLoading: boolean;
  error: string | null;
  mutationError: string | null;
  clearMutationError: () => void;
  retry: () => void;
  updateProfile: (patch: Partial<LocalProfile>) => Promise<boolean>;
  setActivePriority: (
    title: string | null,
    taskId?: string | null,
    projectId?: string | null,
  ) => Promise<boolean>;
  createTask: (
    input: TaskFormValues,
    meta?: { source?: 'manual' | 'ai_proposal'; proposalId?: string | null },
  ) => Promise<boolean>;
  updateTask: (id: string, input: TaskFormValues) => Promise<boolean>;
  setTaskStatus: (id: string, status: TaskStatus) => Promise<boolean>;
  deleteTask: (id: string) => Promise<boolean>;
  startSession: (input: StartSessionValues) => Promise<boolean>;
  finishSession: (id: string, result: string) => Promise<boolean>;
  cancelSession: (id: string) => Promise<boolean>;
  recordManualSession: (input: ManualSessionValues) => Promise<boolean>;
  deleteSession: (id: string) => Promise<boolean>;
  createScheduleEvent: (values: ScheduleEventFormValues) => Promise<boolean>;
  updateScheduleEvent: (id: string, values: ScheduleEventFormValues) => Promise<boolean>;
  deleteScheduleEvent: (id: string) => Promise<boolean>;
  duplicateWeekEvents: (
    weekStart: Date,
  ) => Promise<{ createdCount: number; skippedCount: number } | null>;
  loadDemoData: () => void;
  clearAllData: () => void;
}

const StudyStoreContext = createContext<StudyStoreContextValue | null>(null);

export function StudyStoreProvider({ children }: { children: ReactNode }) {
  const { session, logout, updateSessionDisplayName } = useAuth();
  const queryClient = useQueryClient();

  const isApiMode = session?.mode === 'api' && Boolean(session.accessToken);
  const accessToken = session?.mode === 'api' ? session.accessToken : '';
  const userIdKey = session?.userId ?? 'anonymous';

  const [localState, setLocalState] = useState<StudyState>(() =>
    sanitizeStoredState(readFromStorage<unknown>(STORAGE_KEYS.studyState, DEFAULT_STUDY_STATE)),
  );
  const [mutationError, setMutationError] = useState<string | null>(null);
  const scheduleEventsRef = useRef(localState.scheduleEvents);
  scheduleEventsRef.current = localState.scheduleEvents;

  useEffect(() => {
    writeToStorage(STORAGE_KEYS.studyState, localState);
  }, [localState]);

  const profileQuery = useQuery({
    queryKey: ['profile', userIdKey],
    queryFn: () => fetchProfileApi(accessToken),
    enabled: isApiMode,
  });

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
    [queryClient, userIdKey, logout],
  );

  const actions = useMemo(() => {
    const updateProfile = async (patch: Partial<LocalProfile>): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(
          () => updateProfileApi(accessToken, patch),
          ['profile'],
        );
        if (result.ok && patch.displayName) {
          updateSessionDisplayName(result.data.displayName);
        }
        return result.ok;
      }

      setLocalState((prev) => ({
        ...prev,
        profile: {
          ...prev.profile,
          ...patch,
          displayName: patch.displayName?.trim() || prev.profile.displayName,
        },
      }));
      if (patch.displayName) {
        updateSessionDisplayName(patch.displayName);
      }
      return true;
    };

    const setActivePriority = async (
      title: string | null,
      taskId: string | null = null,
      projectId: string | null = null,
    ): Promise<boolean> => {
      const normalized = title?.trim() || null;
      if (isApiMode) {
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
      }

      setLocalState((prev) => ({
        ...prev,
        activePriorityTitle: normalized,
        activePriorityTaskId: normalized ? taskId : null,
        activePriorityProjectId: normalized ? projectId : null,
      }));
      return true;
    };

    const createTask = async (
      input: TaskFormValues,
      meta?: { source?: 'manual' | 'ai_proposal'; proposalId?: string | null },
    ): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(() => createTaskApi(accessToken, input), ['tasks']);
        return result.ok;
      }

      const nowIso = new Date().toISOString();
      const newTask: Task = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: input.title.trim(),
        description: input.description?.trim() || null,
        status: input.status,
        priority: input.priority,
        dueAt: dateInputToDueIso(input.dueDate ?? ''),
        completedAt: input.status === 'done' ? nowIso : null,
        source: meta?.source ?? 'manual',
        proposalId: meta?.proposalId ?? null,
        projectId: input.projectId?.trim() || null,
        moduleId: input.moduleId?.trim() || null,
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({ ...prev, tasks: [newTask, ...prev.tasks] }));
      return true;
    };

    const updateTask = async (id: string, input: TaskFormValues): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(
          () => updateTaskApi(accessToken, id, input),
          ['tasks', 'profile'],
        );
        return result.ok;
      }

      const nowIso = new Date().toISOString();
      const nextTitle = input.title.trim();
      setLocalState((prev) => ({
        ...prev,
        activePriorityTitle:
          prev.activePriorityTaskId === id ? nextTitle : prev.activePriorityTitle,
        tasks: prev.tasks.map((task) =>
          task.id !== id
            ? task
            : {
                ...task,
                title: nextTitle,
                description: input.description?.trim() || null,
                priority: input.priority,
                status: input.status,
                dueAt: dateInputToDueIso(input.dueDate ?? ''),
                completedAt: input.status === 'done' ? (task.completedAt ?? nowIso) : null,
                projectId:
                  input.projectId !== undefined
                    ? input.projectId.trim() || null
                    : task.projectId,
                moduleId:
                  input.moduleId !== undefined
                    ? input.moduleId.trim() || null
                    : task.moduleId,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const setTaskStatus = async (id: string, status: TaskStatus): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(
          () => updateTaskApi(accessToken, id, { status }),
          ['tasks'],
        );
        return result.ok;
      }

      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        tasks: prev.tasks.map((task) =>
          task.id !== id
            ? task
            : {
                ...task,
                status,
                completedAt: status === 'done' ? (task.completedAt ?? nowIso) : null,
                updatedAt: nowIso,
              },
        ),
      }));
      return true;
    };

    const deleteTask = async (id: string): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(
          () => deleteTaskApi(accessToken, id),
          ['tasks', 'profile', 'sessions'],
        );
        return result.ok;
      }

      setLocalState((prev) => ({
        ...prev,
        activePriorityTitle: prev.activePriorityTaskId === id ? null : prev.activePriorityTitle,
        activePriorityTaskId: prev.activePriorityTaskId === id ? null : prev.activePriorityTaskId,
        tasks: prev.tasks.filter((task) => task.id !== id),
        sessions: prev.sessions.map((s) => (s.taskId === id ? { ...s, taskId: null } : s)),
      }));
      return true;
    };

    const startSession = async (input: StartSessionValues): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(() => startSessionApi(accessToken, input), ['sessions']);
        return result.ok;
      }

      const nowIso = new Date().toISOString();
      const created: StudySession = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: input.title.trim(),
        category: input.category.trim(),
        status: 'in_progress',
        startedAt: nowIso,
        endedAt: null,
        result: null,
        taskId: input.taskId?.trim() || null,
        projectId: input.projectId?.trim() || null,
        moduleId: input.moduleId?.trim() || null,
        lessonId: input.lessonId?.trim() || null,
        skillId: input.skillId?.trim() || null,
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({ ...prev, sessions: [created, ...prev.sessions] }));
      return true;
    };

    const finishSession = async (id: string, resultText: string): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(
          () => finishSessionApi(accessToken, id, resultText),
          ['sessions'],
        );
        return result.ok;
      }

      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        sessions: prev.sessions.map((s) =>
          s.id === id
            ? {
                ...s,
                status: 'completed',
                endedAt: nowIso,
                result: resultText.trim(),
                updatedAt: nowIso,
              }
            : s,
        ),
      }));
      return true;
    };

    const cancelSession = async (id: string): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(() => cancelSessionApi(accessToken, id), ['sessions']);
        return result.ok;
      }

      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        sessions: prev.sessions.map((s) =>
          s.id === id
            ? { ...s, status: 'cancelled', endedAt: null, updatedAt: nowIso }
            : s,
        ),
      }));
      return true;
    };

    const recordManualSession = async (input: ManualSessionValues): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(
          () => recordManualSessionApi(accessToken, input),
          ['sessions'],
        );
        return result.ok;
      }

      const nowIso = new Date().toISOString();
      const created: StudySession = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: input.title.trim(),
        category: input.category.trim(),
        status: 'completed',
        startedAt: new Date(input.startedAt).toISOString(),
        endedAt: new Date(input.endedAt).toISOString(),
        result: input.result.trim(),
        taskId: input.taskId?.trim() || null,
        projectId: input.projectId?.trim() || null,
        moduleId: input.moduleId?.trim() || null,
        lessonId: input.lessonId?.trim() || null,
        skillId: input.skillId?.trim() || null,
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({ ...prev, sessions: [created, ...prev.sessions] }));
      return true;
    };

    const deleteSession = async (id: string): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(() => deleteSessionApi(accessToken, id), ['sessions']);
        return result.ok;
      }

      setLocalState((prev) => ({
        ...prev,
        sessions: prev.sessions.filter((s) => s.id !== id),
      }));
      return true;
    };

    const createScheduleEvent = async (values: ScheduleEventFormValues): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(
          () => createScheduleEventApi(accessToken, values),
          ['schedule'],
        );
        return result.ok;
      }

      const nowIso = new Date().toISOString();
      const event: ScheduleEvent = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: values.title.trim(),
        type: values.type,
        startsAt: localDateAndTimeToIso(values.date, values.startTime),
        endsAt: localDateAndTimeToIso(values.date, values.endTime),
        notes: values.notes?.trim() || null,
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({ ...prev, scheduleEvents: [...prev.scheduleEvents, event] }));
      return true;
    };

    const updateScheduleEvent = async (
      id: string,
      values: ScheduleEventFormValues,
    ): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(
          () => updateScheduleEventApi(accessToken, id, values),
          ['schedule'],
        );
        return result.ok;
      }

      const nowIso = new Date().toISOString();
      const startsAt = localDateAndTimeToIso(values.date, values.startTime);
      const endsAt = localDateAndTimeToIso(values.date, values.endTime);
      setLocalState((prev) => ({
        ...prev,
        scheduleEvents: prev.scheduleEvents.map((ev) =>
          ev.id === id
            ? {
                ...ev,
                title: values.title.trim(),
                type: values.type,
                startsAt,
                endsAt,
                notes: values.notes?.trim() || null,
                updatedAt: nowIso,
              }
            : ev,
        ),
      }));
      return true;
    };

    const deleteScheduleEvent = async (id: string): Promise<boolean> => {
      if (isApiMode) {
        const result = await runApiMutation(
          () => deleteScheduleEventApi(accessToken, id),
          ['schedule'],
        );
        return result.ok;
      }

      setLocalState((prev) => ({
        ...prev,
        scheduleEvents: prev.scheduleEvents.filter((ev) => ev.id !== id),
      }));
      return true;
    };

    const duplicateWeekEvents = async (
      weekStart: Date,
    ): Promise<{ createdCount: number; skippedCount: number } | null> => {
      if (isApiMode) {
        const result = await runApiMutation(
          () => duplicateWeekApi(accessToken, toLocalDateKey(weekStart)),
          ['schedule'],
        );
        return result.ok ? result.data : null;
      }

      const currentEvents = scheduleEventsRef.current;
      const sourceWeekEvents = getEventsForWeek(currentEvents, weekStart);
      const nowIso = new Date().toISOString();
      const { created, skippedCount } = buildDuplicatedWeekEvents(
        sourceWeekEvents,
        currentEvents,
        nowIso,
        generateId,
      );
      if (created.length > 0) {
        setLocalState((prev) => ({
          ...prev,
          scheduleEvents: [...prev.scheduleEvents, ...created],
        }));
      }
      return { createdCount: created.length, skippedCount };
    };

    const loadDemoData = () => {
      setLocalState(buildDemoState());
    };

    const clearAllData = () => {
      setLocalState(DEFAULT_STUDY_STATE);
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
      loadDemoData,
      clearAllData,
    };
  }, [isApiMode, accessToken, runApiMutation, updateSessionDisplayName]);

  const resolvedState: StudyState = useMemo(() => {
    if (!isApiMode) {
      return localState;
    }
    return {
      profile: profileQuery.data
        ? {
            displayName: profileQuery.data.displayName,
            timezone: profileQuery.data.timezone,
            aiInstructions: profileQuery.data.aiInstructions,
          }
        : DEFAULT_LOCAL_PROFILE,
      activePriorityTitle: profileQuery.data?.activePriorityTitle ?? null,
      activePriorityTaskId: profileQuery.data?.activePriorityTaskId ?? null,
      activePriorityProjectId: profileQuery.data?.activePriorityProjectId ?? null,
      tasks: tasksQuery.data ?? [],
      sessions: sessionsQuery.data ?? [],
      scheduleEvents: scheduleQuery.data ?? [],
    };
  }, [
    isApiMode,
    localState,
    profileQuery.data,
    tasksQuery.data,
    sessionsQuery.data,
    scheduleQuery.data,
  ]);

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
      dataMode: isApiMode ? 'api' : 'local_demo',
      isLoading,
      error,
      mutationError,
      clearMutationError,
      retry,
      ...actions,
    }),
    [
      resolvedState,
      isApiMode,
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
