import type {
  LearningModule,
  LearningPath,
  LearningStatus,
  Lesson,
  Project,
  ProjectStatus,
  Skill,
  SkillAssessment,
  SkillAssessmentCriterion,
  SkillAssessmentStatus,
  SkillAssessmentType,
  SkillEvaluatorType,
  SkillEvidence,
  SkillEvidenceType,
  SkillLevel,
  TaskPriority,
} from '../types/domain';
import { apiRequest } from './api-client';
import { dateInputToDueIso } from './date';

interface ApiLearningPath {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  status: LearningStatus;
  goal: string;
  created_at: string;
  updated_at: string;
}

interface ApiLearningModule {
  id: string;
  user_id: string;
  path_id: string;
  title: string;
  description: string | null;
  position: number;
  status: LearningStatus;
  created_at: string;
  updated_at: string;
}

interface ApiLesson {
  id: string;
  user_id: string;
  module_id: string;
  title: string;
  content: string | null;
  resource_url: string | null;
  position: number;
  status: LearningStatus;
  created_at: string;
  updated_at: string;
}

interface ApiLearningOverview {
  paths: ApiLearningPath[];
  modules: ApiLearningModule[];
  lessons: ApiLesson[];
}

interface ApiSkill {
  id: string;
  user_id: string;
  name: string;
  domain: string;
  description: string | null;
  current_level: SkillLevel;
  target_level: SkillLevel | null;
  last_assessed_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiSkillEvidence {
  id: string;
  user_id: string;
  skill_id: string;
  type: SkillEvidenceType;
  description: string;
  reference_url: string | null;
  result: string | null;
  observed_at: string;
  is_admissible?: boolean;
  external_reference_verified?: boolean;
  verification_note?: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiAssessmentCriterion {
  key: string;
  label: string;
  description: string;
  weight: number;
  max_score: number;
  score: number;
  passed: boolean;
  feedback: string;
}

interface ApiSkillAssessment {
  id: string;
  user_id: string;
  skill_id: string;
  path_id: string | null;
  module_id: string | null;
  lesson_id: string | null;
  assessment_type: SkillAssessmentType;
  starting_level: SkillLevel;
  target_level: SkillLevel;
  proposed_level: SkillLevel | null;
  status: SkillAssessmentStatus;
  prompt_title: string;
  prompt_instructions: string;
  revealed_hints: string[];
  hints_total: number;
  hints_revealed_count: number;
  submission_text: string | null;
  submission_code: string | null;
  submission_reference_url: string | null;
  evidence_ids: string[];
  criteria: ApiAssessmentCriterion[];
  score: number | null;
  passed: boolean | null;
  feedback: string | null;
  mastered_points: string[];
  gaps_identified: string[];
  remediation_recommendation: string | null;
  external_verification_warning: string | null;
  evaluator_type: SkillEvaluatorType;
  evaluator_name: string | null;
  decision_reason: string | null;
  applied_level_delta: number | null;
  submitted_at: string | null;
  evaluated_at: string | null;
  validated_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiProject {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  goal: string;
  status: ProjectStatus;
  priority: TaskPriority;
  next_action: string;
  deliverables: string[] | null;
  target_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface LearningPathInput {
  title: string;
  description?: string;
  goal: string;
  status: LearningStatus;
}

export interface LearningModuleInput {
  pathId: string;
  title: string;
  description?: string;
  position: number;
  status: LearningStatus;
}

export interface LessonInput {
  moduleId: string;
  title: string;
  content?: string;
  resourceUrl?: string;
  position: number;
  status: LearningStatus;
}

export interface SkillInput {
  name: string;
  domain: string;
  description?: string;
  targetLevel: SkillLevel | null;
}

export interface SkillEvidenceInput {
  type: SkillEvidenceType;
  description: string;
  referenceUrl?: string;
  result?: string;
}

export interface SkillAssessmentCreateInput {
  targetLevel?: SkillLevel;
  assessmentType?: SkillAssessmentType;
  pathId?: string | null;
  moduleId?: string | null;
  lessonId?: string | null;
  promptTitle?: string;
  promptInstructions?: string;
}

export interface SkillAssessmentSubmitInput {
  submissionText: string;
  submissionCode?: string;
  submissionReferenceUrl?: string;
  evidenceIds?: string[];
  newEvidence?: SkillEvidenceInput;
}

export interface ProjectInput {
  name: string;
  description?: string;
  goal: string;
  status: ProjectStatus;
  priority: TaskPriority;
  nextAction: string;
  deliverables: string[];
  targetDate?: string;
}

function mapPath(dto: ApiLearningPath): LearningPath {
  return {
    id: dto.id,
    userId: dto.user_id,
    title: dto.title,
    description: dto.description,
    status: dto.status,
    goal: dto.goal,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapModule(dto: ApiLearningModule): LearningModule {
  return {
    id: dto.id,
    userId: dto.user_id,
    pathId: dto.path_id,
    title: dto.title,
    description: dto.description,
    position: dto.position,
    status: dto.status,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapLesson(dto: ApiLesson): Lesson {
  return {
    id: dto.id,
    userId: dto.user_id,
    moduleId: dto.module_id,
    title: dto.title,
    content: dto.content,
    resourceUrl: dto.resource_url,
    position: dto.position,
    status: dto.status,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapSkill(dto: ApiSkill): Skill {
  return {
    id: dto.id,
    userId: dto.user_id,
    name: dto.name,
    domain: dto.domain,
    description: dto.description,
    currentLevel: dto.current_level,
    targetLevel: dto.target_level,
    lastAssessedAt: dto.last_assessed_at,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapEvidence(dto: ApiSkillEvidence): SkillEvidence {
  return {
    id: dto.id,
    userId: dto.user_id,
    skillId: dto.skill_id,
    type: dto.type,
    description: dto.description,
    referenceUrl: dto.reference_url,
    result: dto.result,
    observedAt: dto.observed_at,
    isAdmissible: dto.is_admissible ?? true,
    externalReferenceVerified: dto.external_reference_verified ?? false,
    verificationNote: dto.verification_note ?? null,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapCriterion(dto: ApiAssessmentCriterion): SkillAssessmentCriterion {
  return {
    key: dto.key,
    label: dto.label,
    description: dto.description,
    weight: dto.weight,
    maxScore: dto.max_score,
    score: dto.score,
    passed: dto.passed,
    feedback: dto.feedback,
  };
}

function mapAssessment(dto: ApiSkillAssessment): SkillAssessment {
  return {
    id: dto.id,
    userId: dto.user_id,
    skillId: dto.skill_id,
    pathId: dto.path_id,
    moduleId: dto.module_id,
    lessonId: dto.lesson_id,
    assessmentType: dto.assessment_type,
    startingLevel: dto.starting_level,
    targetLevel: dto.target_level,
    proposedLevel: dto.proposed_level,
    status: dto.status,
    promptTitle: dto.prompt_title,
    promptInstructions: dto.prompt_instructions,
    revealedHints: dto.revealed_hints ?? [],
    hintsTotal: dto.hints_total ?? 0,
    hintsRevealedCount: dto.hints_revealed_count ?? 0,
    submissionText: dto.submission_text,
    submissionCode: dto.submission_code,
    submissionReferenceUrl: dto.submission_reference_url,
    evidenceIds: dto.evidence_ids ?? [],
    criteria: (dto.criteria ?? []).map(mapCriterion),
    score: dto.score,
    passed: dto.passed,
    feedback: dto.feedback,
    masteredPoints: dto.mastered_points ?? [],
    gapsIdentified: dto.gaps_identified ?? [],
    remediationRecommendation: dto.remediation_recommendation,
    externalVerificationWarning: dto.external_verification_warning,
    evaluatorType: dto.evaluator_type,
    evaluatorName: dto.evaluator_name,
    decisionReason: dto.decision_reason,
    appliedLevelDelta: dto.applied_level_delta,
    submittedAt: dto.submitted_at,
    evaluatedAt: dto.evaluated_at,
    validatedAt: dto.validated_at,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapProject(dto: ApiProject): Project {
  return {
    id: dto.id,
    userId: dto.user_id,
    name: dto.name,
    description: dto.description,
    goal: dto.goal,
    status: dto.status,
    priority: dto.priority,
    nextAction: dto.next_action,
    deliverables: dto.deliverables,
    targetDate: dto.target_date,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export async function fetchLearningOverviewApi(accessToken: string): Promise<{
  paths: LearningPath[];
  modules: LearningModule[];
  lessons: Lesson[];
}> {
  const dto = await apiRequest<ApiLearningOverview>('/learning/overview', { accessToken });
  return {
    paths: dto.paths.map(mapPath),
    modules: dto.modules.map(mapModule),
    lessons: dto.lessons.map(mapLesson),
  };
}

export async function createLearningPathApi(
  accessToken: string,
  input: LearningPathInput,
): Promise<LearningPath> {
  const dto = await apiRequest<ApiLearningPath>('/learning/paths', {
    method: 'POST',
    accessToken,
    body: {
      title: input.title.trim(),
      description: input.description?.trim() || null,
      goal: input.goal.trim(),
      status: input.status,
    },
  });
  return mapPath(dto);
}

export async function updateLearningPathApi(
  accessToken: string,
  id: string,
  patch: Partial<LearningPathInput>,
): Promise<LearningPath> {
  const body: Record<string, unknown> = {};
  if (patch.title !== undefined) body.title = patch.title.trim();
  if (patch.description !== undefined) body.description = patch.description.trim() || null;
  if (patch.goal !== undefined) body.goal = patch.goal.trim();
  if (patch.status !== undefined) body.status = patch.status;
  const dto = await apiRequest<ApiLearningPath>(`/learning/paths/${id}`, {
    method: 'PATCH',
    accessToken,
    body,
  });
  return mapPath(dto);
}

export async function deleteLearningPathApi(accessToken: string, id: string): Promise<void> {
  await apiRequest<void>(`/learning/paths/${id}`, { method: 'DELETE', accessToken });
}

export async function createLearningModuleApi(
  accessToken: string,
  input: LearningModuleInput,
): Promise<LearningModule> {
  const dto = await apiRequest<ApiLearningModule>('/learning/modules', {
    method: 'POST',
    accessToken,
    body: {
      path_id: input.pathId,
      title: input.title.trim(),
      description: input.description?.trim() || null,
      position: input.position,
      status: input.status,
    },
  });
  return mapModule(dto);
}

export async function updateLearningModuleApi(
  accessToken: string,
  id: string,
  patch: Partial<Omit<LearningModuleInput, 'pathId'>>,
): Promise<LearningModule> {
  const body: Record<string, unknown> = {};
  if (patch.title !== undefined) body.title = patch.title.trim();
  if (patch.description !== undefined) body.description = patch.description.trim() || null;
  if (patch.position !== undefined) body.position = patch.position;
  if (patch.status !== undefined) body.status = patch.status;
  const dto = await apiRequest<ApiLearningModule>(`/learning/modules/${id}`, {
    method: 'PATCH',
    accessToken,
    body,
  });
  return mapModule(dto);
}

export async function deleteLearningModuleApi(accessToken: string, id: string): Promise<void> {
  await apiRequest<void>(`/learning/modules/${id}`, { method: 'DELETE', accessToken });
}

export async function createLessonApi(accessToken: string, input: LessonInput): Promise<Lesson> {
  const dto = await apiRequest<ApiLesson>('/learning/lessons', {
    method: 'POST',
    accessToken,
    body: {
      module_id: input.moduleId,
      title: input.title.trim(),
      content: input.content?.trim() || null,
      resource_url: input.resourceUrl?.trim() || null,
      position: input.position,
      status: input.status,
    },
  });
  return mapLesson(dto);
}

export async function updateLessonApi(
  accessToken: string,
  id: string,
  patch: Partial<Omit<LessonInput, 'moduleId'>>,
): Promise<Lesson> {
  const body: Record<string, unknown> = {};
  if (patch.title !== undefined) body.title = patch.title.trim();
  if (patch.content !== undefined) body.content = patch.content.trim() || null;
  if (patch.resourceUrl !== undefined) body.resource_url = patch.resourceUrl.trim() || null;
  if (patch.position !== undefined) body.position = patch.position;
  if (patch.status !== undefined) body.status = patch.status;
  const dto = await apiRequest<ApiLesson>(`/learning/lessons/${id}`, {
    method: 'PATCH',
    accessToken,
    body,
  });
  return mapLesson(dto);
}

export async function deleteLessonApi(accessToken: string, id: string): Promise<void> {
  await apiRequest<void>(`/learning/lessons/${id}`, { method: 'DELETE', accessToken });
}

export async function fetchSkillsApi(accessToken: string): Promise<Skill[]> {
  const dtos = await apiRequest<ApiSkill[]>('/skills', { accessToken });
  return dtos.map(mapSkill);
}

export async function createSkillApi(accessToken: string, input: SkillInput): Promise<Skill> {
  const dto = await apiRequest<ApiSkill>('/skills', {
    method: 'POST',
    accessToken,
    body: {
      name: input.name.trim(),
      domain: input.domain.trim(),
      description: input.description?.trim() || null,
      target_level: input.targetLevel,
    },
  });
  return mapSkill(dto);
}

export async function updateSkillApi(
  accessToken: string,
  id: string,
  patch: Partial<SkillInput>,
): Promise<Skill> {
  const body: Record<string, unknown> = {};
  if (patch.name !== undefined) body.name = patch.name.trim();
  if (patch.domain !== undefined) body.domain = patch.domain.trim();
  if (patch.description !== undefined) body.description = patch.description.trim() || null;
  if ('targetLevel' in patch) body.target_level = patch.targetLevel ?? null;
  const dto = await apiRequest<ApiSkill>(`/skills/${id}`, {
    method: 'PATCH',
    accessToken,
    body,
  });
  return mapSkill(dto);
}

export async function deleteSkillApi(accessToken: string, id: string): Promise<void> {
  await apiRequest<void>(`/skills/${id}`, { method: 'DELETE', accessToken });
}

export async function fetchAllSkillEvidenceApi(accessToken: string): Promise<SkillEvidence[]> {
  const dtos = await apiRequest<ApiSkillEvidence[]>('/skills/evidence', { accessToken });
  return dtos.map(mapEvidence);
}

export async function createSkillEvidenceApi(
  accessToken: string,
  skillId: string,
  input: SkillEvidenceInput,
): Promise<SkillEvidence> {
  const dto = await apiRequest<ApiSkillEvidence>(`/skills/${skillId}/evidence`, {
    method: 'POST',
    accessToken,
    body: {
      type: input.type,
      description: input.description.trim(),
      reference_url: input.referenceUrl?.trim() || null,
      result: input.result?.trim() || null,
    },
  });
  return mapEvidence(dto);
}

export async function deleteSkillEvidenceApi(
  accessToken: string,
  skillId: string,
  evidenceId: string,
): Promise<void> {
  await apiRequest<void>(`/skills/${skillId}/evidence/${evidenceId}`, {
    method: 'DELETE',
    accessToken,
  });
}

export async function fetchAllSkillAssessmentsApi(
  accessToken: string,
): Promise<SkillAssessment[]> {
  const dtos = await apiRequest<ApiSkillAssessment[]>('/skills/assessments', { accessToken });
  return dtos.map(mapAssessment);
}

export async function createSkillAssessmentApi(
  accessToken: string,
  skillId: string,
  input: SkillAssessmentCreateInput,
): Promise<SkillAssessment> {
  const dto = await apiRequest<ApiSkillAssessment>(`/skills/${skillId}/assessments`, {
    method: 'POST',
    accessToken,
    body: {
      target_level: input.targetLevel ?? null,
      assessment_type: input.assessmentType ?? 'practical_exercise',
      path_id: input.pathId || null,
      module_id: input.moduleId || null,
      lesson_id: input.lessonId || null,
      prompt_title: input.promptTitle?.trim() || null,
      prompt_instructions: input.promptInstructions?.trim() || null,
    },
  });
  return mapAssessment(dto);
}

export async function revealAssessmentHintApi(
  accessToken: string,
  skillId: string,
  assessmentId: string,
): Promise<SkillAssessment> {
  const dto = await apiRequest<ApiSkillAssessment>(
    `/skills/${skillId}/assessments/${assessmentId}/hint`,
    {
      method: 'POST',
      accessToken,
    },
  );
  return mapAssessment(dto);
}

export async function submitSkillAssessmentApi(
  accessToken: string,
  skillId: string,
  assessmentId: string,
  input: SkillAssessmentSubmitInput,
): Promise<SkillAssessment> {
  const dto = await apiRequest<ApiSkillAssessment>(
    `/skills/${skillId}/assessments/${assessmentId}/submit`,
    {
      method: 'POST',
      accessToken,
      body: {
        submission_text: input.submissionText.trim(),
        submission_code: input.submissionCode?.trim() || null,
        submission_reference_url: input.submissionReferenceUrl?.trim() || null,
        evidence_ids: input.evidenceIds ?? [],
        new_evidence: input.newEvidence
          ? {
              type: input.newEvidence.type,
              description: input.newEvidence.description.trim(),
              reference_url: input.newEvidence.referenceUrl?.trim() || null,
              result: input.newEvidence.result?.trim() || null,
            }
          : null,
      },
    },
  );
  return mapAssessment(dto);
}

export async function evaluateSkillAssessmentApi(
  accessToken: string,
  skillId: string,
  assessmentId: string,
): Promise<SkillAssessment> {
  const dto = await apiRequest<ApiSkillAssessment>(
    `/skills/${skillId}/assessments/${assessmentId}/evaluate`,
    {
      method: 'POST',
      accessToken,
      body: {},
    },
  );
  return mapAssessment(dto);
}

export async function validateSkillAssessmentApi(
  accessToken: string,
  skillId: string,
  assessmentId: string,
  reason?: string,
): Promise<SkillAssessment> {
  const dto = await apiRequest<ApiSkillAssessment>(
    `/skills/${skillId}/assessments/${assessmentId}/validate`,
    {
      method: 'POST',
      accessToken,
      body: { reason: reason?.trim() || null },
    },
  );
  return mapAssessment(dto);
}

export async function rejectSkillAssessmentApi(
  accessToken: string,
  skillId: string,
  assessmentId: string,
  reason?: string,
): Promise<SkillAssessment> {
  const dto = await apiRequest<ApiSkillAssessment>(
    `/skills/${skillId}/assessments/${assessmentId}/reject`,
    {
      method: 'POST',
      accessToken,
      body: { reason: reason?.trim() || null },
    },
  );
  return mapAssessment(dto);
}

export async function cancelSkillAssessmentApi(
  accessToken: string,
  skillId: string,
  assessmentId: string,
  reason?: string,
): Promise<SkillAssessment> {
  const dto = await apiRequest<ApiSkillAssessment>(
    `/skills/${skillId}/assessments/${assessmentId}/cancel`,
    {
      method: 'POST',
      accessToken,
      body: { reason: reason?.trim() || null },
    },
  );
  return mapAssessment(dto);
}

export async function fetchProjectsApi(accessToken: string): Promise<Project[]> {
  const dtos = await apiRequest<ApiProject[]>('/projects', { accessToken });
  return dtos.map(mapProject);
}

export async function createProjectApi(
  accessToken: string,
  input: ProjectInput,
): Promise<Project> {
  const dto = await apiRequest<ApiProject>('/projects', {
    method: 'POST',
    accessToken,
    body: {
      name: input.name.trim(),
      description: input.description?.trim() || null,
      goal: input.goal.trim(),
      status: input.status,
      priority: input.priority,
      next_action: input.nextAction.trim(),
      deliverables: input.deliverables.length > 0 ? input.deliverables : null,
      target_date: dateInputToDueIso(input.targetDate ?? ''),
    },
  });
  return mapProject(dto);
}

export async function updateProjectApi(
  accessToken: string,
  id: string,
  patch: Partial<ProjectInput>,
): Promise<Project> {
  const body: Record<string, unknown> = {};
  if (patch.name !== undefined) body.name = patch.name.trim();
  if (patch.description !== undefined) body.description = patch.description.trim() || null;
  if (patch.goal !== undefined) body.goal = patch.goal.trim();
  if (patch.status !== undefined) body.status = patch.status;
  if (patch.priority !== undefined) body.priority = patch.priority;
  if (patch.nextAction !== undefined) body.next_action = patch.nextAction.trim();
  if (patch.deliverables !== undefined) {
    body.deliverables = patch.deliverables.length > 0 ? patch.deliverables : null;
  }
  if (patch.targetDate !== undefined) {
    body.target_date = dateInputToDueIso(patch.targetDate ?? '');
  }
  const dto = await apiRequest<ApiProject>(`/projects/${id}`, {
    method: 'PATCH',
    accessToken,
    body,
  });
  return mapProject(dto);
}

export async function deleteProjectApi(accessToken: string, id: string): Promise<void> {
  await apiRequest<void>(`/projects/${id}`, { method: 'DELETE', accessToken });
}
