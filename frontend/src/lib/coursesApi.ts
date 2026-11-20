import type {
  CourseCodeExample,
  CourseCriterionResult,
  CourseDetail,
  CourseExercise,
  CourseLanguage,
  CourseLesson,
  CourseLessonStatus,
  CourseLevel,
  CourseLevelStatus,
  CoursePreview,
  CourseResource,
  CourseResourceType,
  CourseRubricCriterion,
  CourseStatus,
  CourseSubmission,
  CourseSubmissionKind,
  CourseSubmissionStatus,
  CourseSummary,
} from '../types/domain';
import { apiRequest } from './api-client';

interface ApiCourseCodeExample {
  title: string;
  language: string;
  code: string;
  explanation: string;
}

interface ApiCourseExercise {
  id: string;
  title: string;
  difficulty: 'guide' | 'pratique' | 'defi';
  exercise_type?: 'closed_quiz' | 'code' | 'open_explanation';
  instructions_markdown: string;
  starter_code: string | null;
  choices?: string[];
  hints: string[];
  expected_concepts: string[];
}

interface ApiCourseRubricCriterion {
  key: string;
  label: string;
  description: string;
  max_score: number;
}

interface ApiCourseCriterionResult {
  key: string;
  label: string;
  score: number;
  max_score: number;
  passed: boolean;
  feedback: string;
}

interface ApiCourseLesson {
  id: string;
  user_id: string;
  course_id: string;
  level_id: string;
  position: number;
  title: string;
  summary: string | null;
  estimated_minutes: number;
  content_markdown: string;
  code_examples: ApiCourseCodeExample[];
  exercises: ApiCourseExercise[];
  status: CourseLessonStatus;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiCourseResource {
  id: string;
  user_id: string;
  course_id: string;
  level_id: string | null;
  lesson_id: string | null;
  title: string;
  url: string;
  resource_type: CourseResourceType;
  language: 'fr' | 'en';
  is_official: boolean;
  source_name: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiCourseSubmission {
  id: string;
  user_id: string;
  course_id: string;
  level_id: string;
  lesson_id: string | null;
  submission_kind: CourseSubmissionKind;
  exercise_id: string | null;
  title: string;
  answer_text: string;
  submitted_code: string | null;
  reference_url: string | null;
  status: CourseSubmissionStatus;
  score: number | null;
  passed: boolean | null;
  criteria_results: ApiCourseCriterionResult[];
  feedback_markdown: string | null;
  strengths: string[];
  improvements: string[];
  next_step_hint: string | null;
  attempt_number?: number;
  evaluation_mode?: string;
  manual_review_required?: boolean;
  static_analysis?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface ApiCourseLevel {
  id: string;
  user_id: string;
  course_id: string;
  level_number: number;
  title: string;
  summary: string;
  objectives: string[];
  status: CourseLevelStatus;
  content_generated: boolean;
  project_title: string | null;
  project_brief: string | null;
  project_deliverables: string[];
  project_rubric: ApiCourseRubricCriterion[];
  generation_source?: string;
  revision?: number;
  previous_versions_count?: number;
  validated_at: string | null;
  lessons: ApiCourseLesson[];
  resources: ApiCourseResource[];
  submissions: ApiCourseSubmission[];
  pass_threshold: number;
  project_passed: boolean;
  lessons_completed?: boolean;
  exercises_passed_count?: number;
  exercise_passed?: boolean;
  can_validate?: boolean;
  created_at: string;
  updated_at: string;
}

interface ApiCourseSummary {
  id: string;
  user_id: string;
  title: string;
  subject: string;
  domain: string;
  description: string | null;
  language: CourseLanguage;
  current_level: number;
  total_levels: number;
  status: CourseStatus;
  skill_id: string | null;
  learning_path_id: string | null;
  generation_source?: string;
  generation_model?: string | null;
  completed_lessons_count: number;
  total_lessons_count: number;
  resources_count: number;
  created_at: string;
  updated_at: string;
}

interface ApiCourseDetail extends ApiCourseSummary {
  levels: ApiCourseLevel[];
  resources: ApiCourseResource[];
}

interface ApiCoursePreviewResponse {
  title: string;
  subject: string;
  domain: string;
  description: string;
  language: CourseLanguage;
  total_levels: number;
  levels_roadmap: Array<{
    level_number: number;
    title: string;
    summary: string;
    objectives: string[];
    project_title: string | null;
  }>;
  first_level_lessons: Array<{
    position: number;
    title: string;
    summary: string | null;
    estimated_minutes: number;
    content_markdown: string;
    code_examples: ApiCourseCodeExample[];
    exercises: ApiCourseExercise[];
  }>;
  first_level_project_title: string;
  first_level_project_brief: string;
  first_level_project_deliverables: string[];
  first_level_resources: Array<{
    title: string;
    url: string;
    resource_type: CourseResourceType;
    language: 'fr' | 'en';
    is_official: boolean;
    source_name: string | null;
    notes: string | null;
  }>;
}

export interface CoursePreviewInput {
  subject: string;
  title?: string;
  domain?: string;
  language?: CourseLanguage;
  totalLevels?: number;
  goal?: string;
}

export interface CourseCreateInput {
  subject: string;
  title?: string;
  domain?: string;
  description?: string;
  language?: CourseLanguage;
  totalLevels?: number;
  goal?: string;
  linkSkill?: boolean;
}

export interface CourseUpdateInput {
  title?: string;
  description?: string | null;
  language?: CourseLanguage;
  status?: 'active' | 'paused';
}

export interface CourseResourceInput {
  title: string;
  url: string;
  resourceType: CourseResourceType;
  language: 'fr' | 'en';
  isOfficial: boolean;
  sourceName?: string;
  notes?: string;
  levelId?: string | null;
  lessonId?: string | null;
}

export interface CourseSubmissionInput {
  submissionKind: CourseSubmissionKind;
  lessonId?: string | null;
  exerciseId?: string | null;
  title?: string;
  answerText: string;
  submittedCode?: string;
  referenceUrl?: string;
}

function mapCodeExample(dto: ApiCourseCodeExample): CourseCodeExample {
  return {
    title: dto.title,
    language: dto.language,
    code: dto.code,
    explanation: dto.explanation,
  };
}

function mapExercise(dto: ApiCourseExercise): CourseExercise {
  return {
    id: dto.id,
    title: dto.title,
    difficulty: dto.difficulty,
    exerciseType: dto.exercise_type ?? 'code',
    instructionsMarkdown: dto.instructions_markdown,
    starterCode: dto.starter_code ?? null,
    choices: dto.choices ?? [],
    hints: dto.hints ?? [],
    expectedConcepts: dto.expected_concepts ?? [],
  };
}

function mapRubricCriterion(dto: ApiCourseRubricCriterion): CourseRubricCriterion {
  return {
    key: dto.key,
    label: dto.label,
    description: dto.description,
    maxScore: dto.max_score,
  };
}

function mapCriterionResult(dto: ApiCourseCriterionResult): CourseCriterionResult {
  return {
    key: dto.key,
    label: dto.label,
    score: dto.score,
    maxScore: dto.max_score,
    passed: dto.passed,
    feedback: dto.feedback,
  };
}

function mapLesson(dto: ApiCourseLesson): CourseLesson {
  return {
    id: dto.id,
    userId: dto.user_id,
    courseId: dto.course_id,
    levelId: dto.level_id,
    position: dto.position,
    title: dto.title,
    summary: dto.summary ?? null,
    estimatedMinutes: dto.estimated_minutes,
    contentMarkdown: dto.content_markdown,
    codeExamples: (dto.code_examples ?? []).map(mapCodeExample),
    exercises: (dto.exercises ?? []).map(mapExercise),
    status: dto.status,
    completedAt: dto.completed_at ?? null,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapResource(dto: ApiCourseResource): CourseResource {
  return {
    id: dto.id,
    userId: dto.user_id,
    courseId: dto.course_id,
    levelId: dto.level_id ?? null,
    lessonId: dto.lesson_id ?? null,
    title: dto.title,
    url: dto.url,
    resourceType: dto.resource_type,
    language: dto.language,
    isOfficial: dto.is_official,
    sourceName: dto.source_name ?? null,
    notes: dto.notes ?? null,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapSubmission(dto: ApiCourseSubmission): CourseSubmission {
  return {
    id: dto.id,
    userId: dto.user_id,
    courseId: dto.course_id,
    levelId: dto.level_id,
    lessonId: dto.lesson_id ?? null,
    submissionKind: dto.submission_kind,
    exerciseId: dto.exercise_id ?? null,
    title: dto.title,
    answerText: dto.answer_text,
    submittedCode: dto.submitted_code ?? null,
    referenceUrl: dto.reference_url ?? null,
    status: dto.status,
    score: dto.score ?? null,
    passed: dto.passed ?? null,
    criteriaResults: (dto.criteria_results ?? []).map(mapCriterionResult),
    feedbackMarkdown: dto.feedback_markdown ?? null,
    strengths: dto.strengths ?? [],
    improvements: dto.improvements ?? [],
    nextStepHint: dto.next_step_hint ?? null,
    attemptNumber: dto.attempt_number ?? 1,
    evaluationMode: dto.evaluation_mode ?? 'static_heuristic',
    manualReviewRequired: Boolean(dto.manual_review_required),
    staticAnalysis: dto.static_analysis ?? {},
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapLevel(dto: ApiCourseLevel): CourseLevel {
  return {
    id: dto.id,
    userId: dto.user_id,
    courseId: dto.course_id,
    levelNumber: dto.level_number,
    title: dto.title,
    summary: dto.summary,
    objectives: dto.objectives ?? [],
    status: dto.status,
    contentGenerated: dto.content_generated,
    projectTitle: dto.project_title ?? null,
    projectBrief: dto.project_brief ?? null,
    projectDeliverables: dto.project_deliverables ?? [],
    projectRubric: (dto.project_rubric ?? []).map(mapRubricCriterion),
    generationSource: dto.generation_source ?? 'curated_track',
    revision: dto.revision ?? 1,
    previousVersionsCount: dto.previous_versions_count ?? 0,
    validatedAt: dto.validated_at ?? null,
    lessons: (dto.lessons ?? []).map(mapLesson),
    resources: (dto.resources ?? []).map(mapResource),
    submissions: (dto.submissions ?? []).map(mapSubmission),
    passThreshold: dto.pass_threshold,
    projectPassed: dto.project_passed,
    lessonsCompleted: dto.lessons_completed,
    exercisesPassedCount: dto.exercises_passed_count,
    exercisePassed: dto.exercise_passed,
    canValidate: dto.can_validate,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapSummary(dto: ApiCourseSummary): CourseSummary {
  return {
    id: dto.id,
    userId: dto.user_id,
    title: dto.title,
    subject: dto.subject,
    domain: dto.domain,
    description: dto.description ?? null,
    language: dto.language,
    currentLevel: dto.current_level,
    totalLevels: dto.total_levels,
    status: dto.status,
    skillId: dto.skill_id ?? null,
    learningPathId: dto.learning_path_id ?? null,
    generationSource: dto.generation_source ?? 'curated_track',
    generationModel: dto.generation_model ?? null,
    completedLessonsCount: dto.completed_lessons_count,
    totalLessonsCount: dto.total_lessons_count,
    resourcesCount: dto.resources_count,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapDetail(dto: ApiCourseDetail): CourseDetail {
  return {
    ...mapSummary(dto),
    levels: (dto.levels ?? []).map(mapLevel),
    resources: (dto.resources ?? []).map(mapResource),
  };
}

function mapPreview(dto: ApiCoursePreviewResponse): CoursePreview {
  return {
    title: dto.title,
    subject: dto.subject,
    domain: dto.domain,
    description: dto.description,
    language: dto.language,
    totalLevels: dto.total_levels,
    levelsRoadmap: dto.levels_roadmap.map((lv) => ({
      levelNumber: lv.level_number,
      title: lv.title,
      summary: lv.summary,
      objectives: lv.objectives ?? [],
      projectTitle: lv.project_title ?? null,
    })),
    firstLevelLessons: dto.first_level_lessons.map((l) => ({
      position: l.position,
      title: l.title,
      summary: l.summary ?? null,
      estimatedMinutes: l.estimated_minutes,
      contentMarkdown: l.content_markdown,
      codeExamples: (l.code_examples ?? []).map(mapCodeExample),
      exercises: (l.exercises ?? []).map(mapExercise),
    })),
    firstLevelProjectTitle: dto.first_level_project_title,
    firstLevelProjectBrief: dto.first_level_project_brief,
    firstLevelProjectDeliverables: dto.first_level_project_deliverables ?? [],
    firstLevelResources: dto.first_level_resources.map((r) => ({
      title: r.title,
      url: r.url,
      resourceType: r.resource_type,
      language: r.language,
      isOfficial: r.is_official,
      sourceName: r.source_name ?? null,
      notes: r.notes ?? null,
    })),
  };
}

export async function fetchCoursesApi(accessToken: string): Promise<CourseSummary[]> {
  const dtos = await apiRequest<ApiCourseSummary[]>('/courses', { accessToken });
  return dtos.map(mapSummary);
}

export async function previewCourseApi(
  accessToken: string,
  input: CoursePreviewInput,
): Promise<CoursePreview> {
  const dto = await apiRequest<ApiCoursePreviewResponse>('/courses/preview', {
    method: 'POST',
    accessToken,
    body: {
      subject: input.subject.trim(),
      title: input.title?.trim() || null,
      domain: input.domain?.trim() || null,
      language: input.language ?? 'fr',
      total_levels: input.totalLevels ?? 3,
      goal: input.goal?.trim() || null,
    },
  });
  return mapPreview(dto);
}

export async function createCourseApi(
  accessToken: string,
  input: CourseCreateInput,
): Promise<CourseDetail> {
  const dto = await apiRequest<ApiCourseDetail>('/courses', {
    method: 'POST',
    accessToken,
    body: {
      subject: input.subject.trim(),
      title: input.title?.trim() || null,
      domain: input.domain?.trim() || null,
      description: input.description?.trim() || null,
      language: input.language ?? 'fr',
      total_levels: input.totalLevels ?? 3,
      goal: input.goal?.trim() || null,
      link_skill: input.linkSkill ?? true,
    },
  });
  return mapDetail(dto);
}

export async function fetchCourseDetailApi(
  accessToken: string,
  courseId: string,
): Promise<CourseDetail> {
  const dto = await apiRequest<ApiCourseDetail>(`/courses/${courseId}`, { accessToken });
  return mapDetail(dto);
}

export async function updateCourseApi(
  accessToken: string,
  courseId: string,
  patch: CourseUpdateInput,
): Promise<CourseSummary> {
  const body: Record<string, unknown> = {};
  if (patch.title !== undefined) body.title = patch.title.trim();
  if (patch.description !== undefined) body.description = patch.description?.trim() || null;
  if (patch.language !== undefined) body.language = patch.language;
  if (patch.status !== undefined) body.status = patch.status;
  const dto = await apiRequest<ApiCourseSummary>(`/courses/${courseId}`, {
    method: 'PATCH',
    accessToken,
    body,
  });
  return mapSummary(dto);
}

export async function deleteCourseApi(accessToken: string, courseId: string): Promise<void> {
  await apiRequest<void>(`/courses/${courseId}`, {
    method: 'DELETE',
    accessToken,
  });
}

export async function updateCourseLessonStatusApi(
  accessToken: string,
  courseId: string,
  lessonId: string,
  status: CourseLessonStatus,
): Promise<CourseLesson> {
  const dto = await apiRequest<ApiCourseLesson>(`/courses/${courseId}/lessons/${lessonId}`, {
    method: 'PATCH',
    accessToken,
    body: { status },
  });
  return mapLesson(dto);
}

export async function createCourseResourceApi(
  accessToken: string,
  courseId: string,
  input: CourseResourceInput,
): Promise<CourseResource> {
  const dto = await apiRequest<ApiCourseResource>(`/courses/${courseId}/resources`, {
    method: 'POST',
    accessToken,
    body: {
      title: input.title.trim(),
      url: input.url.trim(),
      resource_type: input.resourceType,
      language: input.language,
      is_official: input.isOfficial,
      source_name: input.sourceName?.trim() || null,
      notes: input.notes?.trim() || null,
      level_id: input.levelId ?? null,
      lesson_id: input.lessonId ?? null,
    },
  });
  return mapResource(dto);
}

export async function deleteCourseResourceApi(
  accessToken: string,
  courseId: string,
  resourceId: string,
): Promise<void> {
  await apiRequest<void>(`/courses/${courseId}/resources/${resourceId}`, {
    method: 'DELETE',
    accessToken,
  });
}

export async function submitCourseWorkApi(
  accessToken: string,
  courseId: string,
  levelId: string,
  input: CourseSubmissionInput,
): Promise<CourseSubmission> {
  const dto = await apiRequest<ApiCourseSubmission>(
    `/courses/${courseId}/levels/${levelId}/submissions`,
    {
      method: 'POST',
      accessToken,
      body: {
        submission_kind: input.submissionKind,
        lesson_id: input.lessonId ?? null,
        exercise_id: input.exerciseId ?? null,
        title: input.title?.trim() || null,
        answer_text: input.answerText.trim(),
        submitted_code: input.submittedCode?.trim() || null,
        reference_url: input.referenceUrl?.trim() || null,
      },
    },
  );
  return mapSubmission(dto);
}

export async function validateCourseLevelApi(
  accessToken: string,
  courseId: string,
  levelId: string,
): Promise<CourseDetail> {
  const dto = await apiRequest<ApiCourseDetail>(
    `/courses/${courseId}/levels/${levelId}/validate`,
    {
      method: 'POST',
      accessToken,
    },
  );
  return mapDetail(dto);
}

export async function regenerateCourseLevelApi(
  accessToken: string,
  courseId: string,
  levelId: string,
  focusHint?: string,
): Promise<CourseDetail> {
  const dto = await apiRequest<ApiCourseDetail>(
    `/courses/${courseId}/levels/${levelId}/regenerate`,
    {
      method: 'POST',
      accessToken,
      body: focusHint?.trim() ? { focus_hint: focusHint.trim() } : {},
    },
  );
  return mapDetail(dto);
}
