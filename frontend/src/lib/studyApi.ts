import type { ScheduleEventFormValues } from '../features/schedule/scheduleSchema';
import type { ManualSessionValues, StartSessionValues } from '../features/sessions/sessionSchema';
import type { TaskFormValues } from '../features/tasks/taskSchema';
import type {
  ScheduleEvent,
  ScheduleEventType,
  SessionStatus,
  StudySession,
  Task,
  TaskPriority,
  TaskSource,
  TaskStatus,
  UserProfile,
} from '../types/domain';
import { ApiError, apiRequest } from './api-client';
import { dateInputToDueIso, localDateAndTimeToIso } from './date';
import { env } from './env';

interface ApiProfile {
  id: string;
  display_name: string;
  timezone: string;
  active_priority_title: string | null;
  active_priority_task_id: string | null;
  active_priority_project_id: string | null;
  preferences: Record<string, unknown>;
  ai_instructions: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiTask {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_at: string | null;
  completed_at: string | null;
  source: TaskSource;
  proposal_id: string | null;
  project_id: string | null;
  module_id: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiScheduleEvent {
  id: string;
  user_id: string;
  title: string;
  type: ScheduleEventType;
  starts_at: string;
  ends_at: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiSession {
  id: string;
  user_id: string;
  title: string;
  category: string;
  status: SessionStatus;
  started_at: string;
  ended_at: string | null;
  result: string | null;
  task_id: string | null;
  project_id: string | null;
  module_id: string | null;
  lesson_id: string | null;
  skill_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiLocalAuthResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  profile: ApiProfile;
}

interface ApiDuplicateWeekResponse {
  created: ApiScheduleEvent[];
  created_count: number;
  skipped_count: number;
}

function mapProfile(dto: ApiProfile): UserProfile {
  return {
    id: dto.id,
    displayName: dto.display_name,
    timezone: dto.timezone,
    activePriorityTitle: dto.active_priority_title,
    activePriorityTaskId: dto.active_priority_task_id,
    activePriorityProjectId: dto.active_priority_project_id,
    preferences: dto.preferences ?? {},
    aiInstructions: dto.ai_instructions,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapTask(dto: ApiTask): Task {
  return {
    id: dto.id,
    userId: dto.user_id,
    title: dto.title,
    description: dto.description,
    status: dto.status,
    priority: dto.priority,
    dueAt: dto.due_at,
    completedAt: dto.completed_at,
    source: dto.source,
    proposalId: dto.proposal_id,
    projectId: dto.project_id,
    moduleId: dto.module_id,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapScheduleEvent(dto: ApiScheduleEvent): ScheduleEvent {
  return {
    id: dto.id,
    userId: dto.user_id,
    title: dto.title,
    type: dto.type,
    startsAt: dto.starts_at,
    endsAt: dto.ends_at,
    notes: dto.notes,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapSession(dto: ApiSession): StudySession {
  return {
    id: dto.id,
    userId: dto.user_id,
    title: dto.title,
    category: dto.category,
    status: dto.status,
    startedAt: dto.started_at,
    endedAt: dto.ended_at,
    result: dto.result,
    taskId: dto.task_id,
    projectId: dto.project_id,
    moduleId: dto.module_id,
    lessonId: dto.lesson_id,
    skillId: dto.skill_id,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export async function loginLocalApi(
  email: string,
  displayName?: string,
): Promise<{ accessToken: string; profile: UserProfile }> {
  const response = await apiRequest<ApiLocalAuthResponse>('/auth/local-login', {
    method: 'POST',
    body: {
      email: email.trim(),
      display_name: displayName?.trim() || null,
    },
  });
  return {
    accessToken: response.access_token,
    profile: mapProfile(response.profile),
  };
}

export async function loginSupabasePasswordApi(
  email: string,
  password: string,
): Promise<{ accessToken: string; profile: UserProfile }> {
  const supabaseUrl = env.VITE_SUPABASE_URL.replace(/\/+$/, '');
  const response = await fetch(`${supabaseUrl}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      apikey: env.VITE_SUPABASE_ANON_KEY,
    },
    body: JSON.stringify({ email: email.trim(), password }),
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      'SUPABASE_AUTH_ERROR',
      'Identifiants Supabase invalides ou service indisponible.',
    );
  }

  const data = (await response.json()) as { access_token?: string };
  if (!data.access_token) {
    throw new ApiError(401, 'SUPABASE_AUTH_ERROR', 'Jeton d’accès manquant dans la réponse Supabase.');
  }

  const profile = await fetchMeApi(data.access_token);
  return {
    accessToken: data.access_token,
    profile,
  };
}

export async function fetchMeApi(accessToken: string): Promise<UserProfile> {
  const dto = await apiRequest<ApiProfile>('/auth/me', { accessToken });
  return mapProfile(dto);
}

export async function fetchProfileApi(accessToken: string): Promise<UserProfile> {
  const dto = await apiRequest<ApiProfile>('/profile', { accessToken });
  return mapProfile(dto);
}

export interface ProfilePatchPayload {
  displayName?: string;
  timezone?: string;
  activePriorityTitle?: string | null;
  activePriorityTaskId?: string | null;
  activePriorityProjectId?: string | null;
  aiInstructions?: string | null;
}

export async function updateProfileApi(
  accessToken: string,
  patch: ProfilePatchPayload,
): Promise<UserProfile> {
  const body: Record<string, unknown> = {};
  if ('displayName' in patch) body.display_name = patch.displayName;
  if ('timezone' in patch) body.timezone = patch.timezone;
  if ('activePriorityTitle' in patch) body.active_priority_title = patch.activePriorityTitle;
  if ('activePriorityTaskId' in patch) body.active_priority_task_id = patch.activePriorityTaskId;
  if ('activePriorityProjectId' in patch) {
    body.active_priority_project_id = patch.activePriorityProjectId;
  }
  if ('aiInstructions' in patch) body.ai_instructions = patch.aiInstructions;

  const dto = await apiRequest<ApiProfile>('/profile', {
    method: 'PATCH',
    accessToken,
    body,
  });
  return mapProfile(dto);
}

export async function fetchTasksApi(accessToken: string): Promise<Task[]> {
  const dtos = await apiRequest<ApiTask[]>('/tasks', { accessToken });
  return dtos.map(mapTask);
}

export async function createTaskApi(accessToken: string, values: TaskFormValues): Promise<Task> {
  const dto = await apiRequest<ApiTask>('/tasks', {
    method: 'POST',
    accessToken,
    body: {
      title: values.title.trim(),
      description: values.description?.trim() || null,
      status: values.status,
      priority: values.priority,
      due_at: dateInputToDueIso(values.dueDate ?? ''),
      project_id: values.projectId?.trim() || null,
      module_id: values.moduleId?.trim() || null,
    },
  });
  return mapTask(dto);
}

export async function updateTaskApi(
  accessToken: string,
  id: string,
  patch: Partial<TaskFormValues> & { status?: TaskStatus },
): Promise<Task> {
  const body: Record<string, unknown> = {};
  if (patch.title !== undefined) body.title = patch.title.trim();
  if (patch.description !== undefined) body.description = patch.description?.trim() || null;
  if (patch.priority !== undefined) body.priority = patch.priority;
  if (patch.status !== undefined) body.status = patch.status;
  if (patch.dueDate !== undefined) body.due_at = dateInputToDueIso(patch.dueDate ?? '');
  if (patch.projectId !== undefined) body.project_id = patch.projectId?.trim() || null;
  if (patch.moduleId !== undefined) body.module_id = patch.moduleId?.trim() || null;

  const dto = await apiRequest<ApiTask>(`/tasks/${id}`, {
    method: 'PATCH',
    accessToken,
    body,
  });
  return mapTask(dto);
}

export async function deleteTaskApi(accessToken: string, id: string): Promise<void> {
  await apiRequest<void>(`/tasks/${id}`, {
    method: 'DELETE',
    accessToken,
  });
}

export async function fetchScheduleEventsApi(accessToken: string): Promise<ScheduleEvent[]> {
  const dtos = await apiRequest<ApiScheduleEvent[]>('/schedule', { accessToken });
  return dtos.map(mapScheduleEvent);
}

export async function createScheduleEventApi(
  accessToken: string,
  values: ScheduleEventFormValues,
): Promise<ScheduleEvent> {
  const dto = await apiRequest<ApiScheduleEvent>('/schedule', {
    method: 'POST',
    accessToken,
    body: {
      title: values.title.trim(),
      type: values.type,
      starts_at: localDateAndTimeToIso(values.date, values.startTime),
      ends_at: localDateAndTimeToIso(values.date, values.endTime),
      notes: values.notes?.trim() || null,
    },
  });
  return mapScheduleEvent(dto);
}

export async function updateScheduleEventApi(
  accessToken: string,
  id: string,
  values: ScheduleEventFormValues,
): Promise<ScheduleEvent> {
  const dto = await apiRequest<ApiScheduleEvent>(`/schedule/${id}`, {
    method: 'PATCH',
    accessToken,
    body: {
      title: values.title.trim(),
      type: values.type,
      starts_at: localDateAndTimeToIso(values.date, values.startTime),
      ends_at: localDateAndTimeToIso(values.date, values.endTime),
      notes: values.notes?.trim() || null,
    },
  });
  return mapScheduleEvent(dto);
}

export async function deleteScheduleEventApi(accessToken: string, id: string): Promise<void> {
  await apiRequest<void>(`/schedule/${id}`, {
    method: 'DELETE',
    accessToken,
  });
}

export async function duplicateWeekApi(
  accessToken: string,
  sourceWeekStart: string,
): Promise<{ createdCount: number; skippedCount: number }> {
  const dto = await apiRequest<ApiDuplicateWeekResponse>('/schedule/duplicate-week', {
    method: 'POST',
    accessToken,
    body: { source_week_start: sourceWeekStart },
  });
  return {
    createdCount: dto.created_count,
    skippedCount: dto.skipped_count,
  };
}

export async function fetchSessionsApi(accessToken: string): Promise<StudySession[]> {
  const dtos = await apiRequest<ApiSession[]>('/sessions', { accessToken });
  return dtos.map(mapSession);
}

export async function startSessionApi(
  accessToken: string,
  values: StartSessionValues,
): Promise<StudySession> {
  const dto = await apiRequest<ApiSession>('/sessions', {
    method: 'POST',
    accessToken,
    body: {
      title: values.title.trim(),
      category: values.category.trim(),
      started_at: new Date().toISOString(),
      task_id: values.taskId?.trim() || null,
      project_id: values.projectId?.trim() || null,
      module_id: values.moduleId?.trim() || null,
      lesson_id: values.lessonId?.trim() || null,
      skill_id: values.skillId?.trim() || null,
    },
  });
  return mapSession(dto);
}

export async function recordManualSessionApi(
  accessToken: string,
  values: ManualSessionValues,
): Promise<StudySession> {
  const dto = await apiRequest<ApiSession>('/sessions', {
    method: 'POST',
    accessToken,
    body: {
      title: values.title.trim(),
      category: values.category.trim(),
      started_at: new Date(values.startedAt).toISOString(),
      ended_at: new Date(values.endedAt).toISOString(),
      result: values.result.trim(),
      task_id: values.taskId?.trim() || null,
      project_id: values.projectId?.trim() || null,
      module_id: values.moduleId?.trim() || null,
      lesson_id: values.lessonId?.trim() || null,
      skill_id: values.skillId?.trim() || null,
    },
  });
  return mapSession(dto);
}

export async function finishSessionApi(
  accessToken: string,
  id: string,
  result: string,
): Promise<StudySession> {
  const dto = await apiRequest<ApiSession>(`/sessions/${id}/finish`, {
    method: 'PATCH',
    accessToken,
    body: {
      result: result.trim(),
      ended_at: new Date().toISOString(),
    },
  });
  return mapSession(dto);
}

export async function cancelSessionApi(accessToken: string, id: string): Promise<StudySession> {
  const dto = await apiRequest<ApiSession>(`/sessions/${id}`, {
    method: 'PATCH',
    accessToken,
    body: { status: 'cancelled' },
  });
  return mapSession(dto);
}

export async function deleteSessionApi(accessToken: string, id: string): Promise<void> {
  await apiRequest<void>(`/sessions/${id}`, {
    method: 'DELETE',
    accessToken,
  });
}
