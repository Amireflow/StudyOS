import type {
  LearningModule,
  LearningPath,
  LearningStatus,
  Lesson,
  Project,
  ProjectStatus,
  Skill,
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
  currentLevel: SkillLevel;
  targetLevel: SkillLevel | null;
}

export interface SkillEvidenceInput {
  type: SkillEvidenceType;
  description: string;
  referenceUrl?: string;
  result?: string;
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
      current_level: input.currentLevel,
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
  if (patch.currentLevel !== undefined) body.current_level = patch.currentLevel;
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
