import { apiRequest } from './api-client';

export type AvailabilityRuleType =
  | 'personal_unavailability'
  | 'confirmed_availability'
  | 'recovery_time';

export type AvailabilityRecurrence = 'once' | 'weekly' | 'daily';

export type SlotCategory =
  | 'fixed_commitment'
  | 'personal_unavailability'
  | 'confirmed_availability'
  | 'potential_availability'
  | 'recovery_time';

export type PlanVersionStatus =
  | 'proposed'
  | 'applied'
  | 'rejected'
  | 'superseded'
  | 'restored';

export interface AvailabilityRule {
  id: string;
  user_id: string;
  label: string;
  rule_type: AvailabilityRuleType;
  day_of_week: number | null;
  start_time: string | null;
  end_time: string | null;
  starts_at: string | null;
  ends_at: string | null;
  timezone: string;
  recurrence: AvailabilityRecurrence;
  active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface AvailabilityRuleCreatePayload {
  label: string;
  rule_type: AvailabilityRuleType;
  day_of_week?: number | null;
  start_time?: string | null;
  end_time?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  timezone?: string;
  recurrence?: AvailabilityRecurrence;
  active?: boolean;
  notes?: string | null;
}

export interface TimeSlotWindow {
  start_utc: string;
  end_utc: string;
  local_date: string;
  start_local: string;
  end_local: string;
  duration_minutes: number;
  category: SlotCategory;
  label: string;
  source_id: string | null;
}

export interface AvailabilityComputation {
  timezone: string;
  range_start: string;
  range_end: string;
  fixed_events: TimeSlotWindow[];
  unavailable_slots: TimeSlotWindow[];
  confirmed_slots: TimeSlotWindow[];
  potential_slots: TimeSlotWindow[];
  recovery_slots: TimeSlotWindow[];
  allocatable_slots: TimeSlotWindow[];
  total_confirmed_minutes: number;
  total_potential_minutes: number;
  total_allocatable_minutes: number;
  missing_availability_info: string[];
  summary: string;
}

export interface LearningPriorityItem {
  source_type: string;
  source_id: string | null;
  title: string;
  subject: string;
  domain: string;
  score: number;
  urgency_score: number;
  blocking_score: number;
  strategic_score: number;
  effort_score: number;
  deficit_score: number;
  deadline_at: string | null;
  recommended_minutes: number;
  reasons: string[];
}

export interface PedagogicalStepPayload {
  content_source: string;
  course_id: string | null;
  course_title: string | null;
  level_id: string | null;
  level_number: number | null;
  level_title: string | null;
  lesson_id: string | null;
  lesson_title: string | null;
  module_id: string | null;
  module_title: string | null;
  skill_id: string | null;
  skill_name: string | null;
  remediation_needed: boolean;
  remediation_reason: string | null;
  blocked_prerequisites: string[];
  exercises_focus: string[];
  deliverables: string[];
  recommended_session_type: string;
  next_step_summary: string;
}

export interface PlannedSessionProposal {
  slot_id: string;
  title: string;
  session_type: string;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  priority_source_type: string;
  priority_source_id: string | null;
  priority_score: number;
  subject: string;
  task_id: string | null;
  project_id: string | null;
  skill_id: string | null;
  course_id: string | null;
  lesson_id: string | null;
  module_id: string | null;
  slot_category: SlotCategory;
  rationale: string;
  pedagogical_content: PedagogicalStepPayload;
}

export interface PlanArbitrageItem {
  source_type: string;
  source_id: string | null;
  title: string;
  needed_minutes: number;
  scheduled_minutes: number;
  postponed_minutes: number;
  reason: string;
  deadline_at: string | null;
}

export interface PlanLoadSummary {
  daily_minutes: Record<string, number>;
  daily_cap_minutes: number;
  weekly_planned_minutes: number;
  weekly_cap_minutes: number;
  recovery_preserved_minutes: number;
  overloaded_days: string[];
  is_overloaded: boolean;
}

export interface PlanMissingInfoItem {
  field: string;
  question: string;
  why: string;
}

export interface LearningPlanVersion {
  id: string;
  user_id: string;
  version_number: number;
  status: PlanVersionStatus;
  horizon_days: number;
  timezone: string;
  rationale: string;
  priorities: LearningPriorityItem[];
  planned_sessions: PlannedSessionProposal[];
  arbitrage_items: PlanArbitrageItem[];
  load_summary: PlanLoadSummary;
  availability_summary: AvailabilityComputation | null;
  missing_info: PlanMissingInfoItem[];
  warnings: string[];
  applied_event_ids: string[];
  applied_task_ids: string[];
  applied_course_ids: string[];
  parent_version_id: string | null;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LearningPlanGeneratePayload {
  horizon_days?: number;
  range_start?: string;
  timezone?: string;
  focus_subject?: string | null;
  exam_title?: string | null;
  exam_at?: string | null;
  weekly_hours_override?: number | null;
  daily_max_minutes?: number | null;
  preferred_session_minutes?: number | null;
  include_potential_slots?: boolean;
  create_missing_courses?: boolean;
  note?: string | null;
}

export interface ScheduleValidity {
  is_valid: boolean;
  expired_event_count: number;
  expired_task_count: number;
  overloaded_days: string[];
  missed_session_count: number;
  conflicting_event_ids: string[];
  stale_reasons: string[];
  recommendation: string;
}

export const planningApi = {
  listAvailabilityRules: (accessToken: string) =>
    apiRequest<AvailabilityRule[]>('/planning/availability-rules', {
      accessToken,
    }),

  createAvailabilityRule: (accessToken: string, payload: AvailabilityRuleCreatePayload) =>
    apiRequest<AvailabilityRule>('/planning/availability-rules', {
      method: 'POST',
      accessToken,
      body: payload,
    }),

  deleteAvailabilityRule: (accessToken: string, ruleId: string) =>
    apiRequest<void>(`/planning/availability-rules/${ruleId}`, {
      method: 'DELETE',
      accessToken,
    }),

  computeAvailability: (accessToken: string, horizonDays = 7, includePotential = true) =>
    apiRequest<AvailabilityComputation>(
      `/planning/availability/compute?horizon_days=${horizonDays}&include_potential=${includePotential}`,
      { accessToken },
    ),

  generatePlan: (
    accessToken: string,
    payload: LearningPlanGeneratePayload,
    idempotencyKey?: string,
  ) =>
    apiRequest<LearningPlanVersion>('/planning/generate', {
      method: 'POST',
      accessToken,
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
      body: payload,
    }),

  adjustPlan: (accessToken: string, instruction: string, idempotencyKey?: string) =>
    apiRequest<LearningPlanVersion>('/planning/adjust', {
      method: 'POST',
      accessToken,
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
      body: { instruction },
    }),

  listVersions: (accessToken: string, limit = 10) =>
    apiRequest<LearningPlanVersion[]>(`/planning/versions?limit=${limit}`, {
      accessToken,
    }),

  applyVersion: (accessToken: string, versionId: string, replaceFuturePlanned = true) =>
    apiRequest<LearningPlanVersion>(`/planning/versions/${versionId}/apply`, {
      method: 'POST',
      accessToken,
      body: { replace_future_planned: replaceFuturePlanned },
    }),

  rejectVersion: (accessToken: string, versionId: string) =>
    apiRequest<LearningPlanVersion>(`/planning/versions/${versionId}/reject`, {
      method: 'POST',
      accessToken,
    }),

  restoreVersion: (accessToken: string, versionId: string) =>
    apiRequest<LearningPlanVersion>(`/planning/versions/${versionId}/restore`, {
      method: 'POST',
      accessToken,
    }),

  checkValidity: (accessToken: string) =>
    apiRequest<ScheduleValidity>('/planning/validity', {
      accessToken,
    }),
};
