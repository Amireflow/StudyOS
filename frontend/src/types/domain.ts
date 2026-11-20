/**
 * Types de domaine alignés sur le schéma Amireflow Study OS v1.1.
 * Utilisés dès le Lot 1 pour garantir la cohérence stricte entre l'UI et la future API.
 */

export type TaskStatus = 'todo' | 'in_progress' | 'done' | 'cancelled' | 'parked';

export type TaskPriority = 'low' | 'normal' | 'high' | 'critical';

export type TaskSource = 'manual' | 'ai_proposal';

export type ScheduleEventType = 'course' | 'learning' | 'project' | 'personal' | 'other';

export type ScheduleEventSource = 'manual' | 'timetable_import' | 'ai_proposal';

export type TimetableFileFormat = 'pdf' | 'image' | 'excel' | 'word';

export type TimetableImportStatus = 'pending_review' | 'validated' | 'cancelled';

export type CourseSessionSubtype = 'cours' | 'td' | 'tp' | 'examen' | 'autre';

export type TimetableAnomalyType =
  | 'missing_time'
  | 'invalid_duration'
  | 'missing_subject'
  | 'duplicate_course'
  | 'overlap_conflict'
  | 'existing_calendar_conflict'
  | 'uncertain_extraction';

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

export type EvidenceVerificationStatus =
  | 'declared'
  | 'uploaded'
  | 'inspected'
  | 'verified'
  | 'approved'
  | 'unreachable';

export type SkillEvaluationMode =
  | 'heuristic_precheck'
  | 'code_static'
  | 'project_rubric'
  | 'ai_assisted'
  | 'manual_review';

export type SkillAssessmentStatus =
  | 'pending'
  | 'submitted'
  | 'evaluated'
  | 'needs_manual_review'
  | 'approved'
  | 'rejected'
  | 'cancelled';

export type SkillAssessmentType =
  | 'quiz'
  | 'practical_exercise'
  | 'code_review'
  | 'explanation'
  | 'deliverable'
  | 'mixed';

export type SkillEvaluatorType =
  | 'pedagogical_engine'
  | 'ai_copilot'
  | 'self_rubric'
  | 'hybrid';

export type SkillPedagogicalState =
  | 'not_evaluated'
  | 'learning'
  | 'awaiting_assessment'
  | 'validated'
  | 'needs_reinforcement';

export type ProjectStatus =
  | 'planned'
  | 'active'
  | 'paused'
  | 'blocked'
  | 'completed'
  | 'archived';

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
  | 'update_task'
  | 'park_task'
  | 'create_project'
  | 'update_project'
  | 'pause_project'
  | 'create_schedule_event'
  | 'update_schedule_event'
  | 'archive_schedule_event'
  | 'create_study_session'
  | 'create_skill'
  | 'add_skill_evidence'
  | 'propose_skill_assessment'
  | 'recommend_skill_progression'
  | 'create_learning_path'
  | 'update_learning_path'
  | 'create_personal_goal'
  | 'update_personal_goal'
  | 'plan_strategic_activity'
  | 'create_course'
  | 'update_preferences'
  | 'manage_availability_rule'
  | 'generate_learning_plan'
  | 'batch_actions';

export type StrategicDecision =
  | 'ACCEPTABLE'
  | 'ACCEPTABLE_WITH_CONDITIONS'
  | 'NOT_RECOMMENDED';

export type AiReportType = 'daily_briefing' | 'weekly_review';

export type AiContextScope =
  | 'auto'
  | 'today'
  | 'tasks'
  | 'schedule'
  | 'learning'
  | 'skills'
  | 'projects'
  | 'goals'
  | 'memory'
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
  source?: ScheduleEventSource;
  importId?: string | null;
  sessionSubtype?: CourseSessionSubtype | string | null;
  teacher?: string | null;
  room?: string | null;
  groupName?: string | null;
  goalId?: string | null;
  courseId?: string | null;
  projectId?: string | null;
  taskId?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ExtractedCourseRow {
  rowId: string;
  subject: string;
  dayOfWeek: number | null;
  dayLabel: string | null;
  startTime: string | null;
  endTime: string | null;
  teacher: string | null;
  room: string | null;
  groupName: string | null;
  sessionType: CourseSessionSubtype;
  validFrom: string | null;
  validUntil: string | null;
  uncertain: boolean;
  uncertaintyReasons: string[];
  ignored: boolean;
  rawExcerpt: string | null;
}

export interface TimetableAnomaly {
  id: string;
  rowId: string | null;
  relatedRowId: string | null;
  type: TimetableAnomalyType;
  severity: 'error' | 'warning';
  message: string;
}

export interface TimetableImport {
  id: string;
  userId: string;
  filename: string;
  fileFormat: TimetableFileFormat;
  mimeType: string;
  fileSizeBytes: number;
  sourcePreviewText: string | null;
  sourceDeleted: boolean;
  status: TimetableImportStatus;
  validFrom: string | null;
  validUntil: string | null;
  extractedCourses: ExtractedCourseRow[];
  anomalies: TimetableAnomaly[];
  warnings: string[];
  blockingAnomaliesCount: number;
  createdEventsCount: number;
  skippedDuplicatesCount: number;
  replacedEventsCount: number;
  createdAt: string;
  updatedAt: string;
  validatedAt: string | null;
}

export interface TimetableImportConfirmResult {
  importRecord: TimetableImport;
  createdEvents: ScheduleEvent[];
  createdCount: number;
  skippedDuplicatesCount: number;
  replacedCount: number;
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
  plannedActivity?: string | null;
  actualActivity?: string | null;
  outcomeStatus?: string | null;
  deliverableSummary?: string | null;
  blockers?: string | null;
  nextStep?: string | null;
  taskId: string | null;
  projectId: string | null;
  goalId?: string | null;
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
  isAdmissible?: boolean;
  externalReferenceVerified?: boolean;
  verificationNote?: string | null;
  verificationStatus?: EvidenceVerificationStatus;
  inspectionMetadata?: Record<string, unknown> | null;
  inspectedAt?: string | null;
  isLocked?: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SkillAssessmentCriterion {
  key: string;
  label: string;
  description: string;
  weight: number;
  maxScore: number;
  score: number;
  passed: boolean;
  feedback: string;
}

export interface SkillAssessment {
  id: string;
  userId: string;
  skillId: string;
  pathId: string | null;
  moduleId: string | null;
  lessonId: string | null;
  assessmentType: SkillAssessmentType;
  startingLevel: SkillLevel;
  targetLevel: SkillLevel;
  proposedLevel: SkillLevel | null;
  status: SkillAssessmentStatus;
  promptTitle: string;
  promptInstructions: string;
  revealedHints: string[];
  hintsTotal: number;
  hintsRevealedCount: number;
  submissionText: string | null;
  submissionCode: string | null;
  submissionReferenceUrl: string | null;
  evidenceIds: string[];
  criteria: SkillAssessmentCriterion[];
  score: number | null;
  passed: boolean | null;
  feedback: string | null;
  masteredPoints: string[];
  gapsIdentified: string[];
  remediationRecommendation: string | null;
  externalVerificationWarning: string | null;
  evaluatorType: SkillEvaluatorType;
  evaluatorName: string | null;
  decisionReason: string | null;
  appliedLevelDelta: number | null;
  rubricVersion?: string;
  evaluatorVersion?: string;
  evaluationMode?: SkillEvaluationMode;
  manualReviewRequired?: boolean;
  reviewedBy?: string | null;
  submittedAt: string | null;
  evaluatedAt: string | null;
  validatedAt: string | null;
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
  category?: ObjectiveCategory;
  motivation?: string | null;
  startDate?: string | null;
  weeklyTargetMinutes?: number;
  steps?: Array<Record<string, unknown>>;
  successCriteria?: string[];
  progressHistory?: Array<Record<string, unknown>>;
  createdAt: string;
  updatedAt: string;
}

export interface ProposedActivitySlot {
  day_label: string;
  local_date: string;
  local_start_time: string;
  local_end_time: string;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
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
  autoExecutedCount?: number;
}

export interface AiMemoryDecisionItem {
  action_type?: string;
  summary?: string;
  decided_at?: string;
}

export interface AiMemoryExecutionItem {
  proposal_id?: string;
  action_type?: string;
  summary?: string;
  entity?: string | null;
  executed_at?: string;
}

export interface AiMemory {
  userId: string;
  academicContext: Record<string, unknown>;
  availabilityPreferences: Record<string, unknown>;
  learningPreferences: Record<string, unknown>;
  constraints: string[];
  longTermGoals: string[];
  recentDecisions: AiMemoryDecisionItem[];
  executionHistory: AiMemoryExecutionItem[];
  weeklyStudyHours: number | null;
  defaultSessionMinutes: number;
  autoExecuteSimpleActions: boolean;
  updatedAt: string;
}

export interface AiMemoryUpdate {
  academicContext?: Record<string, unknown>;
  availabilityPreferences?: Record<string, unknown>;
  learningPreferences?: Record<string, unknown>;
  constraints?: string[];
  longTermGoals?: string[];
  weeklyStudyHours?: number | null;
  defaultSessionMinutes?: number;
  autoExecuteSimpleActions?: boolean;
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

export type AiToolRiskLevel = 'read' | 'simple' | 'structuring' | 'sensitive';

export interface AiToolSpec {
  name: string;
  access: 'read' | 'proposal';
  riskLevel?: AiToolRiskLevel;
  label: string;
  description: string;
  requiresConfirmation: boolean;
  parameterKeys: string[];
}

export type AiProviderKind = 'local' | 'river' | 'openai_compatible' | 'gemini';

export interface AiProviderCatalogItem {
  id: AiProviderKind;
  label: string;
  consoleUrl: string | null;
  defaultBaseUrl: string;
  requiresApiKey: boolean;
}

export interface AiProviderModel {
  id: string;
  label: string;
  ownedBy: string | null;
  contextWindow: number | null;
}

export interface AiProviderConfig {
  provider: AiProviderKind;
  baseUrl: string;
  model: string;
  hasApiKey: boolean;
  apiKeyPreview: string | null;
  source: 'user' | 'server_env' | 'default';
  availableProviders: AiProviderCatalogItem[];
}

export type CourseLanguage = 'fr' | 'en' | 'bilingual';

export type CourseStatus = 'active' | 'paused' | 'completed';

export type CourseLevelStatus = 'locked' | 'unlocked' | 'in_progress' | 'validated';

export type CourseLessonStatus = 'not_started' | 'in_progress' | 'completed';

export type CourseResourceType =
  | 'documentation'
  | 'video'
  | 'article'
  | 'interactive'
  | 'book';

export type CourseSubmissionKind = 'exercise' | 'project';

export type CourseSubmissionStatus = 'submitted' | 'evaluated';

export interface CourseCodeExample {
  title: string;
  language: string;
  code: string;
  explanation: string;
}

export interface CourseExercise {
  id: string;
  title: string;
  difficulty: 'guide' | 'pratique' | 'defi';
  exerciseType?: 'closed_quiz' | 'code' | 'open_explanation';
  instructionsMarkdown: string;
  starterCode: string | null;
  choices?: string[];
  hints: string[];
  expectedConcepts: string[];
}

export interface CourseRubricCriterion {
  key: string;
  label: string;
  description: string;
  maxScore: number;
}

export interface CourseCriterionResult {
  key: string;
  label: string;
  score: number;
  maxScore: number;
  passed: boolean;
  feedback: string;
}

export type CourseTutorQuickAction = 'simplify' | 'example' | 'quiz' | 'custom';

export interface CourseTutorMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  quickAction?: CourseTutorQuickAction | string | null;
  stepIndex: number;
  followUpPrompts: string[];
  createdAt: string;
}

export interface CourseLesson {
  id: string;
  userId: string;
  courseId: string;
  levelId: string;
  position: number;
  title: string;
  summary: string | null;
  estimatedMinutes: number;
  contentMarkdown: string;
  codeExamples: CourseCodeExample[];
  exercises: CourseExercise[];
  tutorMessages?: CourseTutorMessage[];
  currentStepIndex?: number;
  status: CourseLessonStatus;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CourseResource {
  id: string;
  userId: string;
  courseId: string;
  levelId: string | null;
  lessonId: string | null;
  title: string;
  url: string;
  resourceType: CourseResourceType;
  language: 'fr' | 'en';
  isOfficial: boolean;
  sourceName: string | null;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CourseSubmission {
  id: string;
  userId: string;
  courseId: string;
  levelId: string;
  lessonId: string | null;
  submissionKind: CourseSubmissionKind;
  exerciseId: string | null;
  title: string;
  answerText: string;
  submittedCode: string | null;
  referenceUrl: string | null;
  status: CourseSubmissionStatus;
  score: number | null;
  passed: boolean | null;
  criteriaResults: CourseCriterionResult[];
  feedbackMarkdown: string | null;
  strengths: string[];
  improvements: string[];
  nextStepHint: string | null;
  attemptNumber?: number;
  evaluationMode?: string;
  manualReviewRequired?: boolean;
  staticAnalysis?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface CourseLevel {
  id: string;
  userId: string;
  courseId: string;
  levelNumber: number;
  title: string;
  summary: string;
  objectives: string[];
  status: CourseLevelStatus;
  contentGenerated: boolean;
  projectTitle: string | null;
  projectBrief: string | null;
  projectDeliverables: string[];
  projectRubric: CourseRubricCriterion[];
  generationSource?: string;
  revision?: number;
  previousVersionsCount?: number;
  validatedAt: string | null;
  lessons: CourseLesson[];
  resources: CourseResource[];
  submissions: CourseSubmission[];
  passThreshold: number;
  projectPassed: boolean;
  lessonsCompleted?: boolean;
  exercisesPassedCount?: number;
  exercisePassed?: boolean;
  canValidate?: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CourseSummary {
  id: string;
  userId: string;
  title: string;
  subject: string;
  domain: string;
  description: string | null;
  language: CourseLanguage;
  currentLevel: number;
  totalLevels: number;
  status: CourseStatus;
  skillId: string | null;
  learningPathId: string | null;
  generationSource?: string;
  generationModel?: string | null;
  completedLessonsCount: number;
  totalLessonsCount: number;
  resourcesCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface CourseDetail extends CourseSummary {
  levels: CourseLevel[];
  resources: CourseResource[];
}

export interface CoursePreviewLevel {
  levelNumber: number;
  title: string;
  summary: string;
  objectives: string[];
  projectTitle: string | null;
}

export interface CoursePreviewLesson {
  position: number;
  title: string;
  summary: string | null;
  estimatedMinutes: number;
  contentMarkdown: string;
  codeExamples: CourseCodeExample[];
  exercises: CourseExercise[];
}

export interface CoursePreviewResource {
  title: string;
  url: string;
  resourceType: CourseResourceType;
  language: 'fr' | 'en';
  isOfficial: boolean;
  sourceName: string | null;
  notes: string | null;
}

export interface CoursePreview {
  title: string;
  subject: string;
  domain: string;
  description: string;
  language: CourseLanguage;
  totalLevels: number;
  levelsRoadmap: CoursePreviewLevel[];
  firstLevelLessons: CoursePreviewLesson[];
  firstLevelProjectTitle: string;
  firstLevelProjectBrief: string;
  firstLevelProjectDeliverables: string[];
  firstLevelResources: CoursePreviewResource[];
}

export type ObjectiveCategory =
  | 'learning_goal'
  | 'language'
  | 'framework'
  | 'technology'
  | 'spoken_language'
  | 'skill'
  | 'project'
  | 'personal_project'
  | 'professional_project'
  | 'other';

export type ObjectiveStatus =
  | 'planned'
  | 'active'
  | 'paused'
  | 'blocked'
  | 'completed'
  | 'archived';

export interface SessionFinishExtra {
  plannedActivity?: string;
  actualActivity?: string;
  outcomeStatus?: 'completed' | 'partial' | 'blocked';
  deliverableSummary?: string;
  blockers?: string;
  nextStep?: string;
}

export interface PersonalGoal {
  id: string;
  userId: string;
  category: ObjectiveCategory;
  title: string;
  description: string | null;
  goal: string;
  currentLevel: number | null;
  targetLevel: number | null;
  priority: TaskPriority;
  isPrimary: boolean;
  motivation: string | null;
  startDate: string | null;
  targetDate: string | null;
  weeklyTargetMinutes: number;
  status: ObjectiveStatus;
  steps: Array<Record<string, unknown>>;
  deliverables: string[];
  nextAction: string;
  successCriteria: string[];
  progressHistory: Array<Record<string, unknown>>;
  skillId: string | null;
  learningPathId: string | null;
  courseId: string | null;
  completedMinutesLast7d: number;
  sessionsCount: number;
  isBehindSchedule: boolean;
  delayReason: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ObjectivesOverview {
  academicObligations: Array<Record<string, unknown>>;
  personalGoals: PersonalGoal[];
  projects: Array<Record<string, unknown>>;
  prioritySummary: Record<string, unknown>;
}

export interface ExtractedObjectiveCandidate {
  kind: 'personal_goal' | 'project';
  category: string;
  title: string;
  goal: string;
  currentLevel: number | null;
  targetLevel: number | null;
  priority: TaskPriority;
  isPrimary: boolean;
  motivation: string | null;
  weeklyTargetMinutes: number | null;
  targetDate: string | null;
  deliverables: string[];
  validationConditions: string[];
  nextAction: string;
}

export interface ConversationalIntakeRecap {
  objectives: ExtractedObjectiveCandidate[];
  currentLevel: number | string | null;
  targetLevel: number | string | null;
  priority: string | null;
  motivation: string | null;
  availableTimeWeeklyMinutes: number | null;
  targetDate: string | null;
  expectedDeliverables: string[];
  validationConditions: string[];
  missingFields: string[];
  progressiveQuestions: string[];
  requiresConfirmation: boolean;
  summaryMarkdown: string;
}

export interface UnifiedPlanSlot {
  sourceCategory:
    | 'academic_obligation'
    | 'personal_goal'
    | 'project'
    | 'revision'
    | 'evaluation'
    | 'recovery';
  isFixed: boolean;
  title: string;
  dayLabel: string;
  localDate: string;
  localStartTime: string;
  localEndTime: string;
  startsAt: string;
  endsAt: string;
  durationMinutes: number;
  expectedOutcome: string;
  linkedGoalId: string | null;
  linkedProjectId: string | null;
  linkedSkillId: string | null;
  linkedPathId: string | null;
  linkedModuleId: string | null;
  linkedLessonId: string | null;
  linkedTaskId: string | null;
}

export interface UnifiedPlanAdaptationItem {
  targetTitle: string;
  targetKind: 'personal_goal' | 'project' | 'academic';
  cause: string;
  actionTaken: string;
}

export interface UnifiedPlan {
  weekStart: string;
  primaryPriorityTitle: string | null;
  secondaryObjectives: string[];
  academicFixedSlots: UnifiedPlanSlot[];
  flexibleStudySlots: UnifiedPlanSlot[];
  recoverySlots: UnifiedPlanSlot[];
  dailyBreakdown: Record<string, UnifiedPlanSlot[]>;
  arbitrages: string[];
  adaptations: UnifiedPlanAdaptationItem[];
  displacedConflictsCount: number;
  totalAcademicMinutes: number;
  totalPersonalGoalMinutes: number;
  totalProjectMinutes: number;
  requiresValidation: boolean;
}

export interface UnifiedPlanApplyResult {
  createdEventsCount: number;
  displacedConflictsCount: number;
  linkedTasksCreatedCount: number;
  activePriorityTitle: string | null;
}
