import type {
  ConversationalIntakeRecap,
  ExtractedObjectiveCandidate,
  ObjectiveCategory,
  ObjectivesOverview,
  ObjectiveStatus,
  PersonalGoal,
  TaskPriority,
  UnifiedPlan,
  UnifiedPlanAdaptationItem,
  UnifiedPlanApplyResult,
  UnifiedPlanSlot,
} from '../types/domain';
import { apiRequest } from './api-client';

interface ApiPersonalGoal {
  id: string;
  user_id: string;
  category: ObjectiveCategory;
  title: string;
  description: string | null;
  goal: string;
  current_level: number | null;
  target_level: number | null;
  priority: TaskPriority;
  is_primary: boolean;
  motivation: string | null;
  start_date: string | null;
  target_date: string | null;
  weekly_target_minutes: number;
  status: ObjectiveStatus;
  steps: Array<Record<string, unknown>>;
  deliverables: string[];
  next_action: string;
  success_criteria: string[];
  progress_history: Array<Record<string, unknown>>;
  skill_id: string | null;
  learning_path_id: string | null;
  course_id: string | null;
  completed_minutes_last_7d: number;
  sessions_count: number;
  is_behind_schedule: boolean;
  delay_reason: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiExtractedObjectiveCandidate {
  kind: 'personal_goal' | 'project';
  category: string;
  title: string;
  goal: string;
  current_level: number | null;
  target_level: number | null;
  priority: TaskPriority;
  is_primary: boolean;
  motivation: string | null;
  weekly_target_minutes: number | null;
  target_date: string | null;
  deliverables: string[];
  validation_conditions: string[];
  next_action: string;
}

interface ApiConversationalIntakeResponse {
  objectives: ApiExtractedObjectiveCandidate[];
  current_level: number | string | null;
  target_level: number | string | null;
  priority: string | null;
  motivation: string | null;
  available_time_weekly_minutes: number | null;
  target_date: string | null;
  expected_deliverables: string[];
  validation_conditions: string[];
  missing_fields: string[];
  progressive_questions: string[];
  requires_confirmation: boolean;
  summary_markdown: string;
}

interface ApiConfirmIntakeResponse {
  created_goals: ApiPersonalGoal[];
  created_projects: Array<Record<string, unknown>>;
  active_priority_title: string | null;
}

interface ApiUnifiedPlanSlot {
  source_category: UnifiedPlanSlot['sourceCategory'];
  is_fixed: boolean;
  title: string;
  day_label: string;
  local_date: string;
  local_start_time: string;
  local_end_time: string;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  expected_outcome: string;
  linked_goal_id: string | null;
  linked_project_id: string | null;
  linked_skill_id: string | null;
  linked_path_id: string | null;
  linked_module_id: string | null;
  linked_lesson_id: string | null;
  linked_task_id: string | null;
}

interface ApiUnifiedPlanAdaptationItem {
  target_title: string;
  target_kind: 'personal_goal' | 'project' | 'academic';
  cause: string;
  action_taken: string;
}

interface ApiUnifiedPlanResponse {
  week_start: string;
  primary_priority_title: string | null;
  secondary_objectives: string[];
  academic_fixed_slots: ApiUnifiedPlanSlot[];
  flexible_study_slots: ApiUnifiedPlanSlot[];
  recovery_slots: ApiUnifiedPlanSlot[];
  daily_breakdown: Record<string, ApiUnifiedPlanSlot[]>;
  arbitrages: string[];
  adaptations: ApiUnifiedPlanAdaptationItem[];
  displaced_conflicts_count: number;
  total_academic_minutes: number;
  total_personal_goal_minutes: number;
  total_project_minutes: number;
  requires_validation: boolean;
}

interface ApiUnifiedPlanApplyResponse {
  created_events_count: number;
  displaced_conflicts_count: number;
  linked_tasks_created_count: number;
  active_priority_title: string | null;
}

interface ApiObjectivesOverviewResponse {
  academic_obligations: Array<Record<string, unknown>>;
  personal_goals: ApiPersonalGoal[];
  projects: Array<Record<string, unknown>>;
  priority_summary: Record<string, unknown>;
}

export interface PersonalGoalCreateInput {
  title: string;
  category?: ObjectiveCategory;
  description?: string | null;
  goal?: string | null;
  currentLevel?: number | null;
  targetLevel?: number | null;
  priority?: TaskPriority;
  isPrimary?: boolean;
  motivation?: string | null;
  startDate?: string | null;
  targetDate?: string | null;
  weeklyTargetMinutes?: number;
  status?: ObjectiveStatus;
  steps?: Array<Record<string, unknown>>;
  deliverables?: string[];
  nextAction?: string;
  successCriteria?: string[];
  createLinkedEntities?: boolean;
}

export interface PersonalGoalUpdateInput {
  title?: string;
  category?: ObjectiveCategory;
  description?: string | null;
  goal?: string | null;
  currentLevel?: number | null;
  targetLevel?: number | null;
  priority?: TaskPriority;
  isPrimary?: boolean;
  motivation?: string | null;
  startDate?: string | null;
  targetDate?: string | null;
  weeklyTargetMinutes?: number;
  status?: ObjectiveStatus;
  steps?: Array<Record<string, unknown>>;
  deliverables?: string[];
  nextAction?: string;
  successCriteria?: string[];
}

function mapPersonalGoal(dto: ApiPersonalGoal): PersonalGoal {
  return {
    id: dto.id,
    userId: dto.user_id,
    category: dto.category,
    title: dto.title,
    description: dto.description,
    goal: dto.goal,
    currentLevel: dto.current_level,
    targetLevel: dto.target_level,
    priority: dto.priority,
    isPrimary: Boolean(dto.is_primary),
    motivation: dto.motivation,
    startDate: dto.start_date,
    targetDate: dto.target_date,
    weeklyTargetMinutes: dto.weekly_target_minutes,
    status: dto.status,
    steps: dto.steps ?? [],
    deliverables: dto.deliverables ?? [],
    nextAction: dto.next_action ?? '',
    successCriteria: dto.success_criteria ?? [],
    progressHistory: dto.progress_history ?? [],
    skillId: dto.skill_id,
    learningPathId: dto.learning_path_id,
    courseId: dto.course_id,
    completedMinutesLast7d: dto.completed_minutes_last_7d ?? 0,
    sessionsCount: dto.sessions_count ?? 0,
    isBehindSchedule: Boolean(dto.is_behind_schedule),
    delayReason: dto.delay_reason ?? null,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapCandidateFromApi(dto: ApiExtractedObjectiveCandidate): ExtractedObjectiveCandidate {
  return {
    kind: dto.kind,
    category: dto.category,
    title: dto.title,
    goal: dto.goal,
    currentLevel: dto.current_level,
    targetLevel: dto.target_level,
    priority: dto.priority,
    isPrimary: Boolean(dto.is_primary),
    motivation: dto.motivation,
    weeklyTargetMinutes: dto.weekly_target_minutes,
    targetDate: dto.target_date,
    deliverables: dto.deliverables ?? [],
    validationConditions: dto.validation_conditions ?? [],
    nextAction: dto.next_action ?? '',
  };
}

function mapCandidateToApi(candidate: ExtractedObjectiveCandidate): ApiExtractedObjectiveCandidate {
  return {
    kind: candidate.kind,
    category: candidate.category,
    title: candidate.title,
    goal: candidate.goal,
    current_level: candidate.currentLevel,
    target_level: candidate.targetLevel,
    priority: candidate.priority,
    is_primary: candidate.isPrimary,
    motivation: candidate.motivation,
    weekly_target_minutes: candidate.weeklyTargetMinutes,
    target_date: candidate.targetDate,
    deliverables: candidate.deliverables,
    validation_conditions: candidate.validationConditions,
    next_action: candidate.nextAction,
  };
}

function mapPlanSlotFromApi(dto: ApiUnifiedPlanSlot): UnifiedPlanSlot {
  return {
    sourceCategory: dto.source_category,
    isFixed: dto.is_fixed,
    title: dto.title,
    dayLabel: dto.day_label,
    localDate: dto.local_date,
    localStartTime: dto.local_start_time,
    localEndTime: dto.local_end_time,
    startsAt: dto.starts_at,
    endsAt: dto.ends_at,
    durationMinutes: dto.duration_minutes,
    expectedOutcome: dto.expected_outcome,
    linkedGoalId: dto.linked_goal_id,
    linkedProjectId: dto.linked_project_id,
    linkedSkillId: dto.linked_skill_id,
    linkedPathId: dto.linked_path_id,
    linkedModuleId: dto.linked_module_id,
    linkedLessonId: dto.linked_lesson_id,
    linkedTaskId: dto.linked_task_id,
  };
}

function mapPlanSlotToApi(slot: UnifiedPlanSlot): ApiUnifiedPlanSlot {
  return {
    source_category: slot.sourceCategory,
    is_fixed: slot.isFixed,
    title: slot.title,
    day_label: slot.dayLabel,
    local_date: slot.localDate,
    local_start_time: slot.localStartTime,
    local_end_time: slot.localEndTime,
    starts_at: slot.startsAt,
    ends_at: slot.endsAt,
    duration_minutes: slot.durationMinutes,
    expected_outcome: slot.expectedOutcome,
    linked_goal_id: slot.linkedGoalId,
    linked_project_id: slot.linkedProjectId,
    linked_skill_id: slot.linkedSkillId,
    linked_path_id: slot.linkedPathId,
    linked_module_id: slot.linkedModuleId,
    linked_lesson_id: slot.linkedLessonId,
    linked_task_id: slot.linkedTaskId,
  };
}

function mapAdaptationFromApi(dto: ApiUnifiedPlanAdaptationItem): UnifiedPlanAdaptationItem {
  return {
    targetTitle: dto.target_title,
    targetKind: dto.target_kind,
    cause: dto.cause,
    actionTaken: dto.action_taken,
  };
}

export async function fetchObjectivesOverviewApi(
  accessToken: string,
): Promise<ObjectivesOverview> {
  const dto = await apiRequest<ApiObjectivesOverviewResponse>('/objectives/overview', {
    accessToken,
  });
  return {
    academicObligations: dto.academic_obligations ?? [],
    personalGoals: (dto.personal_goals ?? []).map(mapPersonalGoal),
    projects: dto.projects ?? [],
    prioritySummary: dto.priority_summary ?? {},
  };
}

export async function listPersonalGoalsApi(
  accessToken: string,
  status?: ObjectiveStatus,
): Promise<PersonalGoal[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  const dtos = await apiRequest<ApiPersonalGoal[]>(`/objectives${query}`, { accessToken });
  return dtos.map(mapPersonalGoal);
}

export async function createPersonalGoalApi(
  accessToken: string,
  input: PersonalGoalCreateInput,
): Promise<PersonalGoal> {
  const dto = await apiRequest<ApiPersonalGoal>('/objectives', {
    method: 'POST',
    accessToken,
    body: {
      title: input.title.trim(),
      category: input.category ?? 'learning_goal',
      description: input.description ?? null,
      goal: input.goal ?? null,
      current_level: input.currentLevel ?? null,
      target_level: input.targetLevel ?? null,
      priority: input.priority ?? 'normal',
      is_primary: Boolean(input.isPrimary),
      motivation: input.motivation ?? null,
      start_date: input.startDate ?? null,
      target_date: input.targetDate ?? null,
      weekly_target_minutes: input.weeklyTargetMinutes ?? 120,
      status: input.status ?? 'active',
      steps: input.steps ?? [],
      deliverables: input.deliverables ?? [],
      next_action: input.nextAction ?? '',
      success_criteria: input.successCriteria ?? [],
      create_linked_entities: input.createLinkedEntities ?? true,
    },
  });
  return mapPersonalGoal(dto);
}

export async function updatePersonalGoalApi(
  accessToken: string,
  goalId: string,
  patch: PersonalGoalUpdateInput,
): Promise<PersonalGoal> {
  const body: Record<string, unknown> = {};
  if (patch.title !== undefined) body.title = patch.title.trim();
  if (patch.category !== undefined) body.category = patch.category;
  if (patch.description !== undefined) body.description = patch.description;
  if (patch.goal !== undefined) body.goal = patch.goal;
  if (patch.currentLevel !== undefined) body.current_level = patch.currentLevel;
  if (patch.targetLevel !== undefined) body.target_level = patch.targetLevel;
  if (patch.priority !== undefined) body.priority = patch.priority;
  if (patch.isPrimary !== undefined) body.is_primary = patch.isPrimary;
  if (patch.motivation !== undefined) body.motivation = patch.motivation;
  if (patch.startDate !== undefined) body.start_date = patch.startDate;
  if (patch.targetDate !== undefined) body.target_date = patch.targetDate;
  if (patch.weeklyTargetMinutes !== undefined) body.weekly_target_minutes = patch.weeklyTargetMinutes;
  if (patch.status !== undefined) body.status = patch.status;
  if (patch.steps !== undefined) body.steps = patch.steps;
  if (patch.deliverables !== undefined) body.deliverables = patch.deliverables;
  if (patch.nextAction !== undefined) body.next_action = patch.nextAction;
  if (patch.successCriteria !== undefined) body.success_criteria = patch.successCriteria;

  const dto = await apiRequest<ApiPersonalGoal>(`/objectives/${goalId}`, {
    method: 'PATCH',
    accessToken,
    body,
  });
  return mapPersonalGoal(dto);
}

export async function deletePersonalGoalApi(accessToken: string, goalId: string): Promise<void> {
  await apiRequest<void>(`/objectives/${goalId}`, {
    method: 'DELETE',
    accessToken,
  });
}

export async function analyzeObjectivesIntakeApi(
  accessToken: string,
  payload: {
    message: string;
    history?: Array<{ role: string; content: string }>;
    knownAnswers?: Record<string, unknown>;
  },
): Promise<ConversationalIntakeRecap> {
  const dto = await apiRequest<ApiConversationalIntakeResponse>('/objectives/intake/analyze', {
    method: 'POST',
    accessToken,
    body: {
      message: payload.message,
      history: payload.history ?? [],
      known_answers: payload.knownAnswers ?? {},
    },
  });
  return {
    objectives: (dto.objectives ?? []).map(mapCandidateFromApi),
    currentLevel: dto.current_level,
    targetLevel: dto.target_level,
    priority: dto.priority,
    motivation: dto.motivation,
    availableTimeWeeklyMinutes: dto.available_time_weekly_minutes,
    targetDate: dto.target_date,
    expectedDeliverables: dto.expected_deliverables ?? [],
    validationConditions: dto.validation_conditions ?? [],
    missingFields: dto.missing_fields ?? [],
    progressiveQuestions: dto.progressive_questions ?? [],
    requiresConfirmation: Boolean(dto.requires_confirmation),
    summaryMarkdown: dto.summary_markdown ?? '',
  };
}

export async function confirmObjectivesIntakeApi(
  accessToken: string,
  payload: {
    objectives: ExtractedObjectiveCandidate[];
    availableTimeWeeklyMinutes?: number | null;
    motivation?: string | null;
    targetDate?: string | null;
    primaryTitle?: string | null;
  },
): Promise<{
  createdGoals: PersonalGoal[];
  createdProjects: Array<Record<string, unknown>>;
  activePriorityTitle: string | null;
}> {
  const dto = await apiRequest<ApiConfirmIntakeResponse>('/objectives/intake/confirm', {
    method: 'POST',
    accessToken,
    body: {
      objectives: payload.objectives.map(mapCandidateToApi),
      available_time_weekly_minutes: payload.availableTimeWeeklyMinutes ?? null,
      motivation: payload.motivation ?? null,
      target_date: payload.targetDate ?? null,
      primary_title: payload.primaryTitle ?? null,
    },
  });
  return {
    createdGoals: (dto.created_goals ?? []).map(mapPersonalGoal),
    createdProjects: dto.created_projects ?? [],
    activePriorityTitle: dto.active_priority_title ?? null,
  };
}

export async function generateUnifiedPlanApi(
  accessToken: string,
  payload: {
    weeklyAvailableMinutes?: number | null;
    primaryPriorityTitle?: string | null;
    targetWeekStart?: string | null;
    includeDailyRecovery?: boolean;
  },
): Promise<UnifiedPlan> {
  const dto = await apiRequest<ApiUnifiedPlanResponse>('/objectives/plan/generate', {
    method: 'POST',
    accessToken,
    body: {
      weekly_available_minutes: payload.weeklyAvailableMinutes ?? null,
      primary_priority_title: payload.primaryPriorityTitle ?? null,
      target_week_start: payload.targetWeekStart ?? null,
      include_daily_recovery: payload.includeDailyRecovery ?? true,
    },
  });
  const dailyBreakdown: Record<string, UnifiedPlanSlot[]> = {};
  for (const [dayKey, slots] of Object.entries(dto.daily_breakdown ?? {})) {
    dailyBreakdown[dayKey] = slots.map(mapPlanSlotFromApi);
  }
  return {
    weekStart: dto.week_start,
    primaryPriorityTitle: dto.primary_priority_title,
    secondaryObjectives: dto.secondary_objectives ?? [],
    academicFixedSlots: (dto.academic_fixed_slots ?? []).map(mapPlanSlotFromApi),
    flexibleStudySlots: (dto.flexible_study_slots ?? []).map(mapPlanSlotFromApi),
    recoverySlots: (dto.recovery_slots ?? []).map(mapPlanSlotFromApi),
    dailyBreakdown,
    arbitrages: dto.arbitrages ?? [],
    adaptations: (dto.adaptations ?? []).map(mapAdaptationFromApi),
    displacedConflictsCount: dto.displaced_conflicts_count ?? 0,
    totalAcademicMinutes: dto.total_academic_minutes ?? 0,
    totalPersonalGoalMinutes: dto.total_personal_goal_minutes ?? 0,
    totalProjectMinutes: dto.total_project_minutes ?? 0,
    requiresValidation: Boolean(dto.requires_validation),
  };
}

export async function applyUnifiedPlanApi(
  accessToken: string,
  payload: {
    flexibleStudySlots: UnifiedPlanSlot[];
    primaryPriorityTitle?: string | null;
    replaceExistingFlexibleWeek?: boolean;
    weekStart?: string | null;
  },
): Promise<UnifiedPlanApplyResult> {
  const dto = await apiRequest<ApiUnifiedPlanApplyResponse>('/objectives/plan/apply', {
    method: 'POST',
    accessToken,
    body: {
      flexible_study_slots: payload.flexibleStudySlots.map(mapPlanSlotToApi),
      primary_priority_title: payload.primaryPriorityTitle ?? null,
      replace_existing_flexible_week: payload.replaceExistingFlexibleWeek ?? true,
      week_start: payload.weekStart ?? null,
    },
  });
  return {
    createdEventsCount: dto.created_events_count,
    displacedConflictsCount: dto.displaced_conflicts_count,
    linkedTasksCreatedCount: dto.linked_tasks_created_count,
    activePriorityTitle: dto.active_priority_title,
  };
}
