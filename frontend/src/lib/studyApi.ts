import type { ScheduleEventFormValues } from '../features/schedule/scheduleSchema';
import type { ManualSessionValues, StartSessionValues } from '../features/sessions/sessionSchema';
import type { TaskFormValues } from '../features/tasks/taskSchema';
import type {
  CourseSessionSubtype,
  ExtractedCourseRow,
  ScheduleEvent,
  ScheduleEventSource,
  ScheduleEventType,
  SessionFinishExtra,
  SessionStatus,
  StudySession,
  Task,
  TaskPriority,
  TaskSource,
  TaskStatus,
  TimetableAnomaly,
  TimetableAnomalyType,
  TimetableFileFormat,
  TimetableImport,
  TimetableImportConfirmResult,
  TimetableImportStatus,
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
  source?: ScheduleEventSource;
  import_id?: string | null;
  session_subtype?: CourseSessionSubtype | string | null;
  teacher?: string | null;
  room?: string | null;
  group_name?: string | null;
  goal_id?: string | null;
  course_id?: string | null;
  project_id?: string | null;
  task_id?: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiExtractedCourseRow {
  row_id: string;
  subject: string;
  day_of_week: number | null;
  day_label: string | null;
  start_time: string | null;
  end_time: string | null;
  teacher: string | null;
  room: string | null;
  group_name: string | null;
  session_type: CourseSessionSubtype;
  valid_from: string | null;
  valid_until: string | null;
  uncertain: boolean;
  uncertainty_reasons: string[];
  ignored: boolean;
  raw_excerpt: string | null;
}

interface ApiTimetableAnomaly {
  id: string;
  row_id: string | null;
  related_row_id: string | null;
  type: TimetableAnomalyType;
  severity: 'error' | 'warning';
  message: string;
}

interface ApiTimetableImport {
  id: string;
  user_id: string;
  filename: string;
  file_format: TimetableFileFormat;
  mime_type: string;
  file_size_bytes: number;
  source_preview_text: string | null;
  source_deleted: boolean;
  status: TimetableImportStatus;
  valid_from: string | null;
  valid_until: string | null;
  extracted_courses: ApiExtractedCourseRow[];
  anomalies: ApiTimetableAnomaly[];
  warnings: string[];
  blocking_anomalies_count: number;
  created_events_count: number;
  skipped_duplicates_count: number;
  replaced_events_count: number;
  created_at: string;
  updated_at: string;
  validated_at: string | null;
}

interface ApiTimetableImportConfirmResponse {
  import_record: ApiTimetableImport;
  created_events: ApiScheduleEvent[];
  created_count: number;
  skipped_duplicates_count: number;
  replaced_count: number;
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
  planned_activity?: string | null;
  actual_activity?: string | null;
  outcome_status?: string | null;
  deliverable_summary?: string | null;
  blockers?: string | null;
  next_step?: string | null;
  task_id: string | null;
  project_id: string | null;
  goal_id?: string | null;
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
  email?: string | null;
  profile: ApiProfile;
}

export interface ApiAuthAccountResponse {
  id: string;
  email: string | null;
  auth_provider: 'password' | 'external';
  has_password_account: boolean;
  email_verified?: boolean;
  can_change_password?: boolean;
  password_reset_mode?: 'external_provider' | 'unavailable_no_mailer';
  last_login_at: string | null;
  created_at: string;
  profile: ApiProfile;
}

export interface AuthAccountInfo {
  id: string;
  email: string | null;
  authProvider: 'password' | 'external';
  hasPasswordAccount: boolean;
  emailVerified: boolean;
  canChangePassword: boolean;
  passwordResetMode: 'external_provider' | 'unavailable_no_mailer';
  lastLoginAt: string | null;
  createdAt: string;
  profile: UserProfile;
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
    source: dto.source ?? 'manual',
    importId: dto.import_id ?? null,
    sessionSubtype: dto.session_subtype ?? null,
    teacher: dto.teacher ?? null,
    room: dto.room ?? null,
    groupName: dto.group_name ?? null,
    goalId: dto.goal_id ?? null,
    courseId: dto.course_id ?? null,
    projectId: dto.project_id ?? null,
    taskId: dto.task_id ?? null,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapExtractedCourseRow(dto: ApiExtractedCourseRow): ExtractedCourseRow {
  return {
    rowId: dto.row_id,
    subject: dto.subject,
    dayOfWeek: dto.day_of_week,
    dayLabel: dto.day_label,
    startTime: dto.start_time,
    endTime: dto.end_time,
    teacher: dto.teacher,
    room: dto.room,
    groupName: dto.group_name,
    sessionType: dto.session_type,
    validFrom: dto.valid_from,
    validUntil: dto.valid_until,
    uncertain: dto.uncertain,
    uncertaintyReasons: dto.uncertainty_reasons ?? [],
    ignored: dto.ignored,
    rawExcerpt: dto.raw_excerpt,
  };
}

function toApiCourseRow(row: ExtractedCourseRow): ApiExtractedCourseRow {
  return {
    row_id: row.rowId,
    subject: row.subject,
    day_of_week: row.dayOfWeek,
    day_label: row.dayLabel,
    start_time: row.startTime,
    end_time: row.endTime,
    teacher: row.teacher,
    room: row.room,
    group_name: row.groupName,
    session_type: row.sessionType,
    valid_from: row.validFrom,
    valid_until: row.validUntil,
    uncertain: row.uncertain,
    uncertainty_reasons: row.uncertaintyReasons,
    ignored: row.ignored,
    raw_excerpt: row.rawExcerpt,
  };
}

function mapTimetableAnomaly(dto: ApiTimetableAnomaly): TimetableAnomaly {
  return {
    id: dto.id,
    rowId: dto.row_id,
    relatedRowId: dto.related_row_id,
    type: dto.type,
    severity: dto.severity,
    message: dto.message,
  };
}

function mapTimetableImport(dto: ApiTimetableImport): TimetableImport {
  return {
    id: dto.id,
    userId: dto.user_id,
    filename: dto.filename,
    fileFormat: dto.file_format,
    mimeType: dto.mime_type,
    fileSizeBytes: dto.file_size_bytes,
    sourcePreviewText: dto.source_preview_text,
    sourceDeleted: dto.source_deleted,
    status: dto.status,
    validFrom: dto.valid_from,
    validUntil: dto.valid_until,
    extractedCourses: (dto.extracted_courses ?? []).map(mapExtractedCourseRow),
    anomalies: (dto.anomalies ?? []).map(mapTimetableAnomaly),
    warnings: dto.warnings ?? [],
    blockingAnomaliesCount: dto.blocking_anomalies_count ?? 0,
    createdEventsCount: dto.created_events_count ?? 0,
    skippedDuplicatesCount: dto.skipped_duplicates_count ?? 0,
    replacedEventsCount: dto.replaced_events_count ?? 0,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    validatedAt: dto.validated_at,
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
    plannedActivity: dto.planned_activity ?? null,
    actualActivity: dto.actual_activity ?? null,
    outcomeStatus: dto.outcome_status ?? null,
    deliverableSummary: dto.deliverable_summary ?? null,
    blockers: dto.blockers ?? null,
    nextStep: dto.next_step ?? null,
    taskId: dto.task_id,
    projectId: dto.project_id,
    goalId: dto.goal_id ?? null,
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
): Promise<{ accessToken: string; email: string | null; profile: UserProfile }> {
  const response = await apiRequest<ApiLocalAuthResponse>('/auth/local-login', {
    method: 'POST',
    skipAuthRefresh: true,
    body: {
      email: email.trim(),
      display_name: displayName?.trim() || null,
    },
  });
  return {
    accessToken: response.access_token,
    email: response.email ?? email.trim().toLowerCase(),
    profile: mapProfile(response.profile),
  };
}

export async function registerAccountApi(payload: {
  email: string;
  password: string;
  displayName: string;
  timezone?: string;
}): Promise<{ accessToken: string; email: string | null; profile: UserProfile }> {
  const response = await apiRequest<ApiLocalAuthResponse>('/auth/register', {
    method: 'POST',
    skipAuthRefresh: true,
    body: {
      email: payload.email.trim(),
      password: payload.password,
      display_name: payload.displayName.trim(),
      timezone: payload.timezone?.trim() || null,
    },
  });
  return {
    accessToken: response.access_token,
    email: response.email ?? payload.email.trim().toLowerCase(),
    profile: mapProfile(response.profile),
  };
}

export async function loginAccountApi(payload: {
  email: string;
  password: string;
}): Promise<{ accessToken: string; email: string | null; profile: UserProfile }> {
  const response = await apiRequest<ApiLocalAuthResponse>('/auth/login', {
    method: 'POST',
    skipAuthRefresh: true,
    body: {
      email: payload.email.trim(),
      password: payload.password,
    },
  });
  return {
    accessToken: response.access_token,
    email: response.email ?? payload.email.trim().toLowerCase(),
    profile: mapProfile(response.profile),
  };
}

export async function refreshSessionApi(): Promise<{
  accessToken: string;
  email: string | null;
  profile: UserProfile;
}> {
  const response = await apiRequest<ApiLocalAuthResponse>('/auth/refresh', {
    method: 'POST',
    skipAuthRefresh: true,
  });
  if (
    !response ||
    typeof response.access_token !== 'string' ||
    !response.profile ||
    typeof response.profile.id !== 'string'
  ) {
    throw new ApiError(401, 'UNAUTHORIZED', 'Réponse de rafraîchissement invalide.');
  }
  return {
    accessToken: response.access_token,
    email: response.email ?? null,
    profile: mapProfile(response.profile),
  };
}

export async function changePasswordApi(
  accessToken: string,
  payload: { currentPassword: string; newPassword: string },
): Promise<{ accessToken: string; email: string | null; profile: UserProfile }> {
  const response = await apiRequest<ApiLocalAuthResponse>('/auth/change-password', {
    method: 'POST',
    accessToken,
    skipAuthRefresh: true,
    body: {
      current_password: payload.currentPassword,
      new_password: payload.newPassword,
    },
  });
  return {
    accessToken: response.access_token,
    email: response.email ?? null,
    profile: mapProfile(response.profile),
  };
}

export async function logoutSessionApi(accessToken?: string): Promise<void> {
  await apiRequest<void>('/auth/logout?current_only=true', {
    method: 'POST',
    accessToken,
    skipAuthRefresh: true,
  });
}

export async function logoutAllSessionsApi(accessToken: string): Promise<void> {
  try {
    await apiRequest<void>('/auth/logout-all', {
      method: 'POST',
      accessToken,
      skipAuthRefresh: true,
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      await apiRequest<void>('/auth/logout', {
        method: 'POST',
        accessToken,
        skipAuthRefresh: true,
      });
      return;
    }
    throw err;
  }
}

export async function fetchAccountInfoApi(accessToken: string): Promise<AuthAccountInfo> {
  const dto = await apiRequest<ApiAuthAccountResponse>('/auth/account', { accessToken });
  return {
    id: dto.id,
    email: dto.email ?? null,
    authProvider: dto.auth_provider,
    hasPasswordAccount: dto.has_password_account,
    emailVerified: dto.email_verified ?? false,
    canChangePassword: dto.can_change_password ?? dto.auth_provider === 'password',
    passwordResetMode:
      dto.password_reset_mode ??
      (dto.auth_provider === 'external' ? 'external_provider' : 'unavailable_no_mailer'),
    lastLoginAt: dto.last_login_at,
    createdAt: dto.created_at,
    profile: mapProfile(dto.profile),
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
  preferences?: Record<string, unknown>;
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
  if ('preferences' in patch && patch.preferences !== undefined) {
    body.preferences = patch.preferences;
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

export async function analyzeTimetableFileApi(
  accessToken: string,
  file: File,
): Promise<TimetableImport> {
  const formData = new FormData();
  formData.append('file', file);
  const url = `${env.VITE_API_BASE_URL}/schedule/imports/analyze`;
  const response = await fetch(url, {
    method: 'POST',
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    body: formData,
  });

  if (!response.ok) {
    let payload: { error?: { code?: string; message?: string; request_id?: string } } | null = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new ApiError(
      response.status,
      payload?.error?.code ?? 'HTTP_ERROR',
      payload?.error?.message ?? `Erreur lors de l'analyse du document (${response.status}).`,
      payload?.error?.request_id,
    );
  }

  const dto = (await response.json()) as ApiTimetableImport;
  return mapTimetableImport(dto);
}

export async function updateTimetableImportDraftApi(
  accessToken: string,
  importId: string,
  payload: {
    courses: ExtractedCourseRow[];
    validFrom?: string | null;
    validUntil?: string | null;
  },
): Promise<TimetableImport> {
  const dto = await apiRequest<ApiTimetableImport>(`/schedule/imports/${importId}`, {
    method: 'PATCH',
    accessToken,
    body: {
      courses: payload.courses.map(toApiCourseRow),
      valid_from: payload.validFrom ?? null,
      valid_until: payload.validUntil ?? null,
    },
  });
  return mapTimetableImport(dto);
}

export async function confirmTimetableImportApi(
  accessToken: string,
  importId: string,
  payload: {
    courses: ExtractedCourseRow[];
    validFrom?: string | null;
    validUntil?: string | null;
    targetWeekStart?: string | null;
    recurrenceWeeks?: number;
    replaceExistingImported?: boolean;
  },
): Promise<TimetableImportConfirmResult> {
  const dto = await apiRequest<ApiTimetableImportConfirmResponse>(
    `/schedule/imports/${importId}/confirm`,
    {
      method: 'POST',
      accessToken,
      body: {
        courses: payload.courses.map(toApiCourseRow),
        valid_from: payload.validFrom ?? null,
        valid_until: payload.validUntil ?? null,
        target_week_start: payload.targetWeekStart ?? null,
        recurrence_weeks: payload.recurrenceWeeks ?? 1,
        replace_existing_imported: payload.replaceExistingImported ?? false,
      },
    },
  );
  return {
    importRecord: mapTimetableImport(dto.import_record),
    createdEvents: (dto.created_events ?? []).map(mapScheduleEvent),
    createdCount: dto.created_count,
    skippedDuplicatesCount: dto.skipped_duplicates_count,
    replacedCount: dto.replaced_count,
  };
}

export async function cancelTimetableImportApi(
  accessToken: string,
  importId: string,
): Promise<TimetableImport> {
  const dto = await apiRequest<ApiTimetableImport>(`/schedule/imports/${importId}/cancel`, {
    method: 'POST',
    accessToken,
  });
  return mapTimetableImport(dto);
}

export async function deleteTimetableImportSourceApi(
  accessToken: string,
  importId: string,
): Promise<TimetableImport> {
  const dto = await apiRequest<ApiTimetableImport>(`/schedule/imports/${importId}/source`, {
    method: 'DELETE',
    accessToken,
  });
  return mapTimetableImport(dto);
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
  extra?: SessionFinishExtra,
): Promise<StudySession> {
  const body: Record<string, unknown> = {
    result: result.trim(),
    ended_at: new Date().toISOString(),
  };
  if (extra?.plannedActivity?.trim()) body.planned_activity = extra.plannedActivity.trim();
  if (extra?.actualActivity?.trim()) body.actual_activity = extra.actualActivity.trim();
  if (extra?.outcomeStatus) body.outcome_status = extra.outcomeStatus;
  if (extra?.deliverableSummary?.trim()) body.deliverable_summary = extra.deliverableSummary.trim();
  if (extra?.blockers?.trim()) body.blockers = extra.blockers.trim();
  if (extra?.nextStep?.trim()) body.next_step = extra.nextStep.trim();

  const dto = await apiRequest<ApiSession>(`/sessions/${id}/finish`, {
    method: 'PATCH',
    accessToken,
    body,
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
