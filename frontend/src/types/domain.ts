/**
 * Types de domaine alignés sur le schéma Amireflow Study OS v1.1.
 * Utilisés dès le Lot 1 pour garantir la cohérence stricte entre l'UI et la future API.
 */

export type TaskStatus = 'todo' | 'in_progress' | 'done' | 'cancelled' | 'parked';

export type TaskPriority = 'low' | 'normal' | 'high' | 'critical';

export type TaskSource = 'manual' | 'ai_proposal';

export type ScheduleEventType = 'course' | 'learning' | 'project' | 'personal' | 'other';

export type SessionStatus = 'in_progress' | 'completed' | 'cancelled';

export type LearningStatus = 'not_started' | 'active' | 'paused' | 'completed';

/** Échelle standard : 0 = Non évalué, 1 = Découverte, 2 = Notions, 3 = Autonome, 4 = Solide, 5 = Maîtrise */
export type SkillLevel = 0 | 1 | 2 | 3 | 4 | 5;

export type SkillEvidenceType =
  | 'exercise'
  | 'project'
  | 'code'
  | 'assessment'
  | 'deliverable'
  | 'other';

export type ProjectStatus = 'planned' | 'active' | 'blocked' | 'completed' | 'archived';

export type ProposalStatus =
  | 'pending'
  | 'accepted'
  | 'rejected'
  | 'expired'
  | 'executed'
  | 'failed';

export type AiMessageRole = 'user' | 'assistant' | 'system';

export type AiActionType =
  | 'create_task'
  | 'park_task'
  | 'create_schedule_event'
  | 'add_skill_evidence'
  | 'update_skill_level';

export type AiReportType = 'daily_briefing' | 'weekly_review';

export type AiContextScope =
  | 'auto'
  | 'today'
  | 'tasks'
  | 'schedule'
  | 'learning'
  | 'skills'
  | 'projects'
  | 'weekly';

export interface UserProfile {
  id: string;
  displayName: string;
  timezone: string;
  activePriorityTitle: string | null;
  activePriorityTaskId: string | null;
  activePriorityProjectId: string | null;
  preferences: Record<string, unknown>;
  aiInstructions: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface Task {
  id: string;
  userId: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  dueAt: string | null;
  completedAt: string | null;
  source: TaskSource;
  proposalId: string | null;
  projectId: string | null;
  moduleId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ScheduleEvent {
  id: string;
  userId: string;
  title: string;
  type: ScheduleEventType;
  startsAt: string;
  endsAt: string;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface StudySession {
  id: string;
  userId: string;
  title: string;
  category: string;
  status: SessionStatus;
  startedAt: string;
  endedAt: string | null;
  result: string | null;
  taskId: string | null;
  projectId: string | null;
  moduleId: string | null;
  lessonId: string | null;
  skillId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface LearningPath {
  id: string;
  userId: string;
  title: string;
  description: string | null;
  status: LearningStatus;
  goal: string;
  createdAt: string;
  updatedAt: string;
}

export interface LearningModule {
  id: string;
  userId: string;
  pathId: string;
  title: string;
  description: string | null;
  position: number;
  status: LearningStatus;
  createdAt: string;
  updatedAt: string;
}

export interface Lesson {
  id: string;
  userId: string;
  moduleId: string;
  title: string;
  content: string | null;
  resourceUrl: string | null;
  position: number;
  status: LearningStatus;
  createdAt: string;
  updatedAt: string;
}

export interface Skill {
  id: string;
  userId: string;
  name: string;
  domain: string;
  description: string | null;
  currentLevel: SkillLevel;
  targetLevel: SkillLevel | null;
  lastAssessedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SkillEvidence {
  id: string;
  userId: string;
  skillId: string;
  type: SkillEvidenceType;
  description: string;
  referenceUrl: string | null;
  result: string | null;
  observedAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface Project {
  id: string;
  userId: string;
  name: string;
  description: string | null;
  goal: string;
  status: ProjectStatus;
  priority: TaskPriority;
  nextAction: string;
  deliverables: string[] | null;
  targetDate: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AiActionProposal {
  id: string;
  userId: string;
  conversationId: string;
  actionType: string;
  title: string;
  explanation: string;
  payload: Record<string, unknown>;
  status: ProposalStatus;
  expiresAt: string | null;
  executionResult: Record<string, unknown> | null;
  errorMessage: string | null;
  createdAt: string;
  resolvedAt: string | null;
}

export interface AiConversation {
  id: string;
  userId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface AiMessageMetadata {
  provider?: string;
  model?: string;
  isEstimate?: boolean;
  missingData?: string[];
  includedScopes?: string[];
  proposalIds?: string[];
  rejectedProposalsCount?: number;
}

export interface AiMessage {
  id: string;
  userId: string;
  conversationId: string;
  role: AiMessageRole;
  content: string;
  metadata: AiMessageMetadata;
  createdAt: string;
}

export interface AiReport {
  id: string;
  userId: string;
  type: AiReportType;
  periodStart: string;
  periodEnd: string;
  content: string;
  metadata: {
    isEstimate?: boolean;
    missingData?: string[];
    stats?: Record<string, unknown>;
  };
  createdAt: string;
}

export interface AiToolSpec {
  name: string;
  access: 'read' | 'proposal';
  label: string;
  description: string;
  requiresConfirmation: boolean;
  parameterKeys: string[];
}
