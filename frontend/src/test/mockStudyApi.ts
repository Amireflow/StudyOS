import { vi } from 'vitest';
import type { AuthSession } from '../state/AuthContext';

export const TEST_USER_ID = 'test-user';

export const TEST_API_SESSION: AuthSession = {
  mode: 'api',
  accessToken: 'test-access-token',
  userId: TEST_USER_ID,
  email: 'khadim@amireflow.local',
  displayName: 'Khadim',
  authProvider: 'password',
};

export interface MockProfileDto {
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

export interface MockTaskDto {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  due_at: string | null;
  completed_at: string | null;
  source: string;
  proposal_id: string | null;
  project_id: string | null;
  module_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface MockSessionDto {
  id: string;
  user_id: string;
  title: string;
  category: string;
  status: string;
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

export interface MockScheduleEventDto {
  id: string;
  user_id: string;
  title: string;
  type: string;
  starts_at: string;
  ends_at: string;
  notes: string | null;
  source?: string;
  import_id?: string | null;
  session_subtype?: string | null;
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

export interface MockSkillDto {
  id: string;
  user_id: string;
  name: string;
  domain: string;
  description: string | null;
  current_level: number;
  target_level: number | null;
  last_assessed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MockApiState {
  profile: MockProfileDto;
  tasks: MockTaskDto[];
  sessions: MockSessionDto[];
  scheduleEvents: MockScheduleEventDto[];
  timetableImports: Array<Record<string, any>>;
  availabilityRules: Array<Record<string, any>>;
  planVersions: Array<Record<string, any>>;
  paths: Array<Record<string, any>>;
  modules: Array<Record<string, any>>;
  lessons: Array<Record<string, any>>;
  skills: MockSkillDto[];
  evidence: Array<Record<string, any>>;
  assessments: Array<Record<string, any>>;
  projects: Array<Record<string, any>>;
  personalGoals: Array<Record<string, any>>;
  courses: Array<Record<string, any>>;
  conversations: Array<Record<string, any>>;
  messages: Array<Record<string, any>>;
  proposals: Array<Record<string, any>>;
  reports: Array<Record<string, any>>;
  aiMemory: Record<string, any>;
  providerConfig: Record<string, any>;
}

export interface MockStudyApiSeed {
  profile?: Partial<MockProfileDto>;
  tasks?: MockTaskDto[];
  sessions?: MockSessionDto[];
  scheduleEvents?: MockScheduleEventDto[];
  paths?: Array<Record<string, any>>;
  modules?: Array<Record<string, any>>;
  lessons?: Array<Record<string, any>>;
  skills?: MockSkillDto[];
  evidence?: Array<Record<string, any>>;
  assessments?: Array<Record<string, any>>;
  projects?: Array<Record<string, any>>;
  personalGoals?: Array<Record<string, any>>;
  courses?: Array<Record<string, any>>;
  conversations?: Array<Record<string, any>>;
  messages?: Array<Record<string, any>>;
  proposals?: Array<Record<string, any>>;
  reports?: Array<Record<string, any>>;
  aiMemory?: Record<string, any>;
  availabilityRules?: Array<Record<string, any>>;
  planVersions?: Array<Record<string, any>>;
  providerConfig?: Record<string, any>;
  externalFetch?: (url: string, init?: RequestInit) => Promise<Response>;
}

const DEFAULT_TOOLS = [
  {
    name: 'read_schedule',
    access: 'read',
    label: 'Lire le planning',
    description: 'Consulte uniquement les créneaux de l’utilisateur connecté.',
    requires_confirmation: false,
    parameter_keys: [],
  },
  {
    name: 'read_tasks',
    access: 'read',
    label: 'Lire les tâches',
    description: 'Consulte les tâches actives, en retard ou au parking.',
    requires_confirmation: false,
    parameter_keys: [],
  },
  {
    name: 'propose_skill_assessment',
    access: 'proposal',
    label: 'Proposer une évaluation de compétence',
    description: 'Propose une évaluation vérifiable sans modification directe du niveau.',
    requires_confirmation: true,
    parameter_keys: ['skill_id', 'target_level', 'assessment_type'],
  },
  {
    name: 'recommend_skill_progression',
    access: 'proposal',
    label: 'Recommander une progression vérifiée',
    description: 'Recommande la validation après preuve admissible.',
    requires_confirmation: true,
    parameter_keys: ['skill_id', 'assessment_id'],
  },
  {
    name: 'create_course',
    access: 'proposal',
    label: 'Proposer la création d’un cours complet',
    description: 'Crée un cours multi-niveaux progressif.',
    requires_confirmation: true,
    parameter_keys: ['subject', 'title', 'domain', 'language', 'total_levels'],
  },
];

const PROVIDER_CATALOG = [
  {
    id: 'river',
    label: 'River AI (console.river.ai)',
    console_url: 'https://console.river.ai',
    default_base_url: 'https://api.river.ai/v1',
    requires_api_key: true,
  },
  {
    id: 'local',
    label: 'Local (déterministe, sans clé API)',
    console_url: null,
    default_base_url: '',
    requires_api_key: false,
  },
  {
    id: 'openai_compatible',
    label: 'OpenAI / Compatible',
    console_url: 'https://platform.openai.com',
    default_base_url: 'https://api.openai.com/v1',
    requires_api_key: true,
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    console_url: 'https://aistudio.google.com',
    default_base_url: 'https://generativelanguage.googleapis.com/v1beta',
    requires_api_key: true,
  },
];

function jsonRes(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function emptyRes(status = 204): Response {
  return new Response(null, { status });
}

function errRes(status: number, code: string, message: string): Response {
  return jsonRes({ error: { code, message, request_id: 'test-req' } }, status);
}

function checkDeclarativeEvidence(description: string, result?: string | null): string | null {
  const cleaned = description.trim();
  const lowered = cleaned.toLowerCase();
  const words = cleaned.split(/\s+/).filter((w) => w.length >= 2);
  if (cleaned.length < 12 || words.length < 3) {
    return 'Preuve refusée : décrivez précisément la production réalisée.';
  }
  const declarative = [
    /\bj['’]?ai\s+(bien\s+)?compris\b/i,
    /\bje\s+ma[îi]trise\b/i,
    /\bj['’]?ai\s+(lu|vu|regard[ée]|termin[ée]|fini)\b/i,
    /\ble[çc]on\s+termin[ée]e?\b/i,
  ].some((rx) => rx.test(lowered));
  const hasConcreteKw = ['def ', 'function', 'pytest', 'vitest', 'test', 'exercice', 'script', 'endpoint', 'code', 'score'].some(
    (kw) => lowered.includes(kw),
  );
  if (declarative && !hasConcreteKw && (!result || result.trim().length < 4)) {
    return 'Preuve insuffisante : une simple affirmation ne démontre pas la compétence.';
  }
  return null;
}

function buildPythonCourseDetail(
  id: string,
  subject: string,
  title: string,
  domain: string,
  language: 'fr' | 'en',
  totalLevels: number,
  skillId: string | null,
  learningPathId: string | null,
  nowIso: string,
) {
  const mkId = (suffix: string) => `${id}-${suffix}`;
  const l1Id = mkId('lvl-1');
  const l2Id = mkId('lvl-2');
  const l3Id = mkId('lvl-3');

  const level1Lessons = [1, 2, 3, 4].map((pos) => ({
    id: mkId(`l1-ch-${pos}`),
    user_id: TEST_USER_ID,
    course_id: id,
    level_id: l1Id,
    position: pos,
    title: `Chapitre 1.${pos} — Fondamentaux ${subject}`,
    summary: `Maîtriser les bases essentielles de ${subject} (chapitre ${pos}).`,
    estimated_minutes: 30,
    content_markdown: `### Explication\nContenu structuré de niveau 1.${pos} pour ${subject}.`,
    code_examples: [
      {
        title: `Exemple ${subject} 1.${pos}`,
        language: 'python',
        code: `def classify_score(score: int) -> str:\n    if score < 0 or score > 100:\n        raise ValueError("invalide")\n    return "Acquis" if score >= 85 else "En cours"`,
        explanation: 'Validation explicite des bornes.',
      },
    ],
    exercises: [
      {
        id: mkId(`ex-1-${pos}`),
        title: `Exercice guidé 1.${pos}`,
        difficulty: 'guide',
        exercise_type: 'code',
        instructions_markdown: `Implémentez et testez la validation des entrées en ${subject}.`,
        starter_code: `def classify_score(score: int) -> str:\n    pass`,
        hints: ['Vérifiez score < 0 or score > 100 puis levez ValueError.'],
        expected_concepts: ['ValueError', 'assert', 'return'],
      },
    ],
    status: 'not_started',
    completed_at: null,
    created_at: nowIso,
    updated_at: nowIso,
  }));

  const resources = [
    {
      id: mkId('res-1'),
      user_id: TEST_USER_ID,
      course_id: id,
      level_id: l1Id,
      lesson_id: null,
      title: `Documentation officielle ${subject}`,
      url: 'https://docs.python.org/fr/3/',
      resource_type: 'documentation',
      language: 'fr',
      is_official: true,
      source_name: 'Python.org',
      notes: 'Référence officielle complète.',
      created_at: nowIso,
      updated_at: nowIso,
    },
    {
      id: mkId('res-2'),
      user_id: TEST_USER_ID,
      course_id: id,
      level_id: l1Id,
      lesson_id: null,
      title: 'Harvard CS50P — Introduction to Programming with Python',
      url: 'https://cs50.harvard.edu/python/',
      resource_type: 'interactive',
      language: 'en',
      is_official: true,
      source_name: 'Harvard University',
      notes: 'Cours universitaire complet avec exercices pratiques progressifs.',
      created_at: nowIso,
      updated_at: nowIso,
    },
  ];

  const makeLevel2Lessons = () => [
    {
      id: mkId('l2-ch-1'),
      user_id: TEST_USER_ID,
      course_id: id,
      level_id: l2Id,
      position: 1,
      title: 'Manipulation sûre de fichiers avec pathlib',
      summary: 'Manipuler chemins et fichiers de façon portable.',
      estimated_minutes: 35,
      content_markdown: '### Pathlib\nUtilisez `Path` pour éviter les chemins fragiles.',
      code_examples: [
        {
          title: 'Lecture sûre',
          language: 'python',
          code: 'from pathlib import Path\ncontent = Path("notes.txt").read_text(encoding="utf-8")',
          explanation: 'Lecture explicite UTF-8.',
        },
      ],
      exercises: [],
      status: 'not_started',
      completed_at: null,
      created_at: nowIso,
      updated_at: nowIso,
    },
    ...[2, 3, 4].map((pos) => ({
      id: mkId(`l2-ch-${pos}`),
      user_id: TEST_USER_ID,
      course_id: id,
      level_id: l2Id,
      position: pos,
      title: `Chapitre 2.${pos} — Pratique avancée ${subject}`,
      summary: `Approfondissement niveau 2.${pos}.`,
      estimated_minutes: 35,
      content_markdown: `### Niveau 2.${pos}\nContenu structuré.`,
      code_examples: [],
      exercises: [],
      status: 'not_started',
      completed_at: null,
      created_at: nowIso,
      updated_at: nowIso,
    })),
  ];

  const levels: Array<Record<string, any>> = [
    {
      id: l1Id,
      user_id: TEST_USER_ID,
      course_id: id,
      level_number: 1,
      title: `Niveau 1 : Fondamentaux ${subject}`,
      summary: `Maîtriser les bases essentielles de ${subject}.`,
      objectives: ['Types & validation', 'Tests unitaires'],
      status: 'unlocked',
      content_generated: true,
      project_title: `Projet Niveau 1 — Analyseur de sessions ${subject}`,
      project_brief: 'Implémentez `analyser_sessions` avec validation `ValueError` et assertions.',
      project_deliverables: ['Fonction typée', 'Tests assert'],
      project_rubric: [
        { key: 'code', label: 'Qualité technique', description: 'Code clair', max_score: 50 },
        { key: 'tests', label: 'Tests & limites', description: 'Gestion erreurs', max_score: 50 },
      ],
      validated_at: null,
      lessons: level1Lessons,
      resources,
      submissions: [],
      pass_threshold: 70,
      project_passed: false,
      lessons_completed: false,
      exercises_passed_count: 0,
      exercise_passed: false,
      can_validate: false,
      created_at: nowIso,
      updated_at: nowIso,
    },
  ];

  if (totalLevels >= 2) {
    levels.push({
      id: l2Id,
      user_id: TEST_USER_ID,
      course_id: id,
      level_number: 2,
      title: `Niveau 2 : Pratique intermédiaire ${subject}`,
      summary: 'Fichiers, structures avancées et robustesse.',
      objectives: ['Pathlib', 'Architecture modulaire'],
      status: 'locked',
      content_generated: false,
      project_title: 'Projet Niveau 2',
      project_brief: 'Projet intermédiaire.',
      project_deliverables: ['Module testé'],
      project_rubric: [],
      validated_at: null,
      lessons: [],
      resources: [],
      submissions: [],
      pass_threshold: 70,
      project_passed: false,
      lessons_completed: false,
      exercises_passed_count: 0,
      exercise_passed: false,
      can_validate: false,
      created_at: nowIso,
      updated_at: nowIso,
      _makeLevel2Lessons: makeLevel2Lessons,
      _makeLevel2Resources: () =>
        resources.map((r, index) => ({
          ...r,
          id: mkId(`l2-res-${index + 1}`),
          level_id: l2Id,
        })),
    });
  }
  if (totalLevels >= 3) {
    levels.push({
      id: l3Id,
      user_id: TEST_USER_ID,
      course_id: id,
      level_number: 3,
      title: `Niveau 3 : Architecture & Production ${subject}`,
      summary: 'Conception avancée et validation complète.',
      objectives: ['Qualité', 'Performance'],
      status: 'locked',
      content_generated: false,
      project_title: 'Projet Niveau 3',
      project_brief: 'Projet avancé.',
      project_deliverables: ['Application complète'],
      project_rubric: [],
      validated_at: null,
      lessons: [],
      resources: [],
      submissions: [],
      pass_threshold: 75,
      project_passed: false,
      lessons_completed: false,
      exercises_passed_count: 0,
      exercise_passed: false,
      can_validate: false,
      created_at: nowIso,
      updated_at: nowIso,
    });
  }

  return {
    id,
    user_id: TEST_USER_ID,
    title,
    subject,
    domain,
    description: `Cours progressif en ${totalLevels} niveaux pour apprendre ${subject}.`,
    language,
    current_level: 1,
    total_levels: totalLevels,
    status: 'active',
    skill_id: skillId,
    learning_path_id: learningPathId,
    completed_lessons_count: 0,
    total_lessons_count: level1Lessons.length,
    resources_count: resources.length,
    levels,
    resources,
    created_at: nowIso,
    updated_at: nowIso,
  };
}

function serializeCourseSummary(course: Record<string, any>) {
  return {
    id: course.id,
    user_id: course.user_id,
    title: course.title,
    subject: course.subject,
    domain: course.domain,
    description: course.description,
    language: course.language,
    current_level: course.current_level,
    total_levels: course.total_levels,
    status: course.status,
    skill_id: course.skill_id,
    learning_path_id: course.learning_path_id,
    completed_lessons_count: course.completed_lessons_count,
    total_lessons_count: course.total_lessons_count,
    resources_count: course.resources_count,
    created_at: course.created_at,
    updated_at: course.updated_at,
  };
}

function serializeCourseDetail(course: Record<string, any>) {
  return {
    ...serializeCourseSummary(course),
    resources: course.resources,
    levels: course.levels.map((lv: Record<string, any>) => {
      const { _makeLevel2Lessons: _ignored, ...rest } = lv;
      return rest;
    }),
  };
}

function recomputeCourseReadiness(course: Record<string, any>) {
  let completedTotal = 0;
  let allLessonsTotal = 0;
  for (const lv of course.levels as Array<Record<string, any>>) {
    const lessons = lv.lessons as Array<Record<string, any>>;
    allLessonsTotal += lessons.length;
    const completedLv = lessons.filter((l) => l.status === 'completed').length;
    completedTotal += completedLv;
    const lessonsDone = lessons.length > 0 && completedLv === lessons.length;
    const exPassedCount = (lv.submissions as Array<Record<string, any>>).filter(
      (s) => s.submission_kind === 'exercise' && s.passed,
    ).length;
    const projPassed = (lv.submissions as Array<Record<string, any>>).some(
      (s) => s.submission_kind === 'project' && s.passed,
    );
    lv.lessons_completed = lessonsDone;
    lv.exercises_passed_count = exPassedCount;
    lv.exercise_passed = exPassedCount >= 1;
    lv.project_passed = projPassed;
    lv.can_validate = lessonsDone && exPassedCount >= 1 && projPassed;
  }
  course.completed_lessons_count = completedTotal;
  course.total_lessons_count = allLessonsTotal;
  course.resources_count = course.resources.length;
}

function parsePdfTimetableLines(rawText: string) {
  const courses: Array<Record<string, any>> = [];
  const lines = rawText
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => /^(Lundi|Mardi|Mercredi|Jeudi|Vendredi|Samedi|Dimanche)/i.test(l));
  const dayMap: Record<string, number> = {
    lundi: 0,
    mardi: 1,
    mercredi: 2,
    jeudi: 3,
    vendredi: 4,
    samedi: 5,
    dimanche: 6,
  };
  const dayLabelMap = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];

  lines.forEach((line, idx) => {
    const dayMatch = line.match(/^(Lundi|Mardi|Mercredi|Jeudi|Vendredi|Samedi|Dimanche)/i);
    const dayOfWeek = dayMatch ? (dayMap[dayMatch[1].toLowerCase()] ?? 0) : 0;
    const timeMatch = line.match(/(\d{2}:\d{2}|\?\?:\?\?)\s*-\s*(\d{2}:\d{2}|\?\?:\?\?)/);
    const startTime = timeMatch && timeMatch[1] !== '??:??' ? timeMatch[1] : null;
    const endTime = timeMatch && timeMatch[2] !== '??:??' ? timeMatch[2] : null;
    let rest = timeMatch ? line.slice(line.indexOf(timeMatch[0]) + timeMatch[0].length).trim() : line;
    const parts = rest.split('-').map((p) => p.trim());
    const subject = parts[0] || '';
    const rawType = (parts[1] || 'cours').toLowerCase();
    const sessionType = rawType.includes('td')
      ? 'td'
      : rawType.includes('tp')
        ? 'tp'
        : rawType.includes('exam')
          ? 'examen'
          : 'cours';
    courses.push({
      row_id: `row_${idx + 1}`,
      subject,
      day_of_week: dayOfWeek,
      day_label: dayLabelMap[dayOfWeek],
      start_time: startTime,
      end_time: endTime,
      teacher: parts[2] || null,
      room: parts[3] || null,
      group_name: null,
      session_type: sessionType,
      valid_from: null,
      valid_until: null,
      uncertain: !startTime || !endTime || !subject,
      uncertainty_reasons: !startTime || !endTime ? ['Horaire manquant ou illisible.'] : [],
      ignored: false,
      raw_excerpt: line,
    });
  });

  return courses;
}

function toMins(hhmm: string | null): number | null {
  if (!hhmm || !/^\d{2}:\d{2}$/.test(hhmm)) return null;
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
}

function computeServerTimetableAnomalies(courses: Array<Record<string, any>>) {
  const anomalies: Array<Record<string, any>> = [];
  const active = courses.filter((c) => !c.ignored);
  let counter = 1;
  for (const row of active) {
    const s = toMins(row.start_time);
    const e = toMins(row.end_time);
    if (s === null || e === null) {
      anomalies.push({
        id: `anom_${counter++}`,
        row_id: row.row_id,
        related_row_id: null,
        type: 'missing_time',
        severity: 'error',
        message: `Horaire de début ou de fin manquant pour « ${row.subject || row.row_id} ».`,
      });
    } else if (e <= s) {
      anomalies.push({
        id: `anom_${counter++}`,
        row_id: row.row_id,
        related_row_id: null,
        type: 'invalid_duration',
        severity: 'error',
        message: `Fin <= début pour « ${row.subject} ».`,
      });
    }
    if (!String(row.subject ?? '').trim()) {
      anomalies.push({
        id: `anom_${counter++}`,
        row_id: row.row_id,
        related_row_id: null,
        type: 'missing_subject',
        severity: 'error',
        message: 'Matière manquante.',
      });
    }
  }
  for (let i = 0; i < active.length; i += 1) {
    for (let j = i + 1; j < active.length; j += 1) {
      const a = active[i];
      const b = active[j];
      const as = toMins(a.start_time);
      const ae = toMins(a.end_time);
      const bs = toMins(b.start_time);
      const be = toMins(b.end_time);
      if (
        a.day_of_week !== null &&
        a.day_of_week === b.day_of_week &&
        as !== null &&
        ae !== null &&
        bs !== null &&
        be !== null &&
        as < be &&
        bs < ae
      ) {
        anomalies.push({
          id: `anom_${counter++}`,
          row_id: b.row_id,
          related_row_id: a.row_id,
          type: 'overlap_conflict',
          severity: 'error',
          message: `Chevauchement horaire entre « ${a.subject} » et « ${b.subject} ».`,
        });
      }
    }
  }
  return anomalies;
}

export function installMockStudyApi(seed: MockStudyApiSeed = {}) {
  let seq = 1000;
  const nextId = (prefix: string) => `${prefix}-${seq++}`;
  const nowIso = () => new Date().toISOString();

  const state: MockApiState = {
    profile: {
      id: TEST_USER_ID,
      display_name: 'Khadim',
      timezone: 'Africa/Dakar',
      active_priority_title: null,
      active_priority_task_id: null,
      active_priority_project_id: null,
      preferences: {},
      ai_instructions: null,
      created_at: nowIso(),
      updated_at: nowIso(),
      ...(seed.profile ?? {}),
    },
    tasks: [...(seed.tasks ?? [])],
    sessions: [...(seed.sessions ?? [])],
    scheduleEvents: [...(seed.scheduleEvents ?? [])],
    timetableImports: [],
    availabilityRules: [...(seed.availabilityRules ?? [])],
    planVersions: [...(seed.planVersions ?? [])],
    paths: [...(seed.paths ?? [])],
    modules: [...(seed.modules ?? [])],
    lessons: [...(seed.lessons ?? [])],
    skills: [...(seed.skills ?? [])],
    evidence: [...(seed.evidence ?? [])],
    assessments: [...(seed.assessments ?? [])],
    projects: [...(seed.projects ?? [])],
    personalGoals: [...(seed.personalGoals ?? [])],
    courses: [...(seed.courses ?? [])],
    conversations: [...(seed.conversations ?? [])],
    messages: [...(seed.messages ?? [])],
    proposals: [...(seed.proposals ?? [])],
    reports: [...(seed.reports ?? [])],
    aiMemory: {
      user_id: TEST_USER_ID,
      academic_context: {},
      availability_preferences: {},
      learning_preferences: {},
      constraints: [],
      long_term_goals: [],
      recent_decisions: [],
      execution_history: [],
      weekly_study_hours: null,
      default_session_minutes: 60,
      auto_execute_simple_actions: false,
      updated_at: nowIso(),
      ...(seed.aiMemory ?? {}),
    },
    providerConfig: {
      provider: 'local',
      base_url: '',
      model: 'local-coach-v1',
      has_api_key: false,
      api_key_preview: null,
      source: 'default',
      available_providers: PROVIDER_CATALOG,
      ...(seed.providerConfig ?? {}),
    },
  };

  const requests: Array<{ url: string; method: string; body: unknown }> = [];

  const handleApiRequest = async (urlStr: string, init?: RequestInit): Promise<Response> => {
    const parsed = new URL(urlStr);
    const path = parsed.pathname.replace(/^\/api\/v1/, '') || '/';
    const method = (init?.method ?? 'GET').toUpperCase();

    let body: Record<string, any> = {};
    if (typeof init?.body === 'string' && init.body.trim()) {
      try {
        body = JSON.parse(init.body) as Record<string, any>;
      } catch {
        body = {};
      }
    }

    requests.push({ url: urlStr, method, body });

    // --- Profile & Auth ---
    if ((path === '/profile' || path === '/auth/me') && method === 'GET') {
      return jsonRes(state.profile);
    }
    if (path === '/profile' && method === 'PATCH') {
      state.profile = {
        ...state.profile,
        ...(body.display_name !== undefined ? { display_name: body.display_name } : {}),
        ...(body.timezone !== undefined ? { timezone: body.timezone } : {}),
        ...('active_priority_title' in body
          ? { active_priority_title: body.active_priority_title }
          : {}),
        ...('active_priority_task_id' in body
          ? { active_priority_task_id: body.active_priority_task_id }
          : {}),
        ...('active_priority_project_id' in body
          ? { active_priority_project_id: body.active_priority_project_id }
          : {}),
        ...(body.preferences !== undefined ? { preferences: body.preferences } : {}),
        ...('ai_instructions' in body ? { ai_instructions: body.ai_instructions } : {}),
        updated_at: nowIso(),
      };
      return jsonRes(state.profile);
    }
    if (path === '/auth/account' && method === 'GET') {
      return jsonRes({
        id: state.profile.id,
        email: TEST_API_SESSION.email,
        display_name: state.profile.display_name,
        timezone: state.profile.timezone,
        auth_provider: 'password',
        can_change_password: true,
        password_reset_mode: 'unavailable_no_mailer',
        last_login_at: nowIso(),
        created_at: nowIso(),
        profile: state.profile,
      });
    }
    if ((path === '/auth/logout' || path === '/auth/logout-all') && method === 'POST') {
      return emptyRes(204);
    }

    // --- Tasks ---
    if (path === '/tasks' && method === 'GET') {
      return jsonRes(state.tasks);
    }
    if (path === '/tasks' && method === 'POST') {
      const status = body.status ?? 'todo';
      const priority = body.priority ?? 'normal';
      const activeCritical = state.tasks.filter(
        (t) => (t.status === 'todo' || t.status === 'in_progress') && t.priority === 'critical',
      ).length;
      if ((status === 'todo' || status === 'in_progress') && priority === 'critical' && activeCritical >= 3) {
        return errRes(422, 'CRITICAL_TASK_LIMIT', 'Limite de 3 tâches critiques actives atteinte.');
      }
      const created: MockTaskDto = {
        id: nextId('task'),
        user_id: TEST_USER_ID,
        title: String(body.title ?? '').trim(),
        description: body.description ?? null,
        status,
        priority,
        due_at: body.due_at ?? null,
        completed_at: status === 'done' ? nowIso() : null,
        source: body.source ?? 'manual',
        proposal_id: body.proposal_id ?? null,
        project_id: body.project_id ?? null,
        module_id: body.module_id ?? null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.tasks.unshift(created);
      return jsonRes(created, 201);
    }
    const taskMatch = path.match(/^\/tasks\/([^/]+)$/);
    if (taskMatch && method === 'PATCH') {
      const id = taskMatch[1];
      const idx = state.tasks.findIndex((t) => t.id === id);
      if (idx === -1) return errRes(404, 'NOT_FOUND', 'Tâche introuvable.');
      const cur = state.tasks[idx];
      const nextStatus = body.status ?? cur.status;
      const nextTitle = body.title !== undefined ? String(body.title).trim() : cur.title;
      const updated: MockTaskDto = {
        ...cur,
        title: nextTitle,
        description: body.description !== undefined ? body.description : cur.description,
        status: nextStatus,
        priority: body.priority ?? cur.priority,
        due_at: body.due_at !== undefined ? body.due_at : cur.due_at,
        completed_at: nextStatus === 'done' ? (cur.completed_at ?? nowIso()) : null,
        updated_at: nowIso(),
      };
      state.tasks[idx] = updated;
      if (state.profile.active_priority_task_id === id) {
        const inactive = nextStatus !== 'todo' && nextStatus !== 'in_progress';
        state.profile = {
          ...state.profile,
          active_priority_task_id: inactive ? null : id,
          active_priority_title: inactive
            ? state.profile.active_priority_project_id === null
              ? null
              : state.profile.active_priority_title
            : nextTitle,
        };
      }
      return jsonRes(updated);
    }
    if (taskMatch && method === 'DELETE') {
      const id = taskMatch[1];
      state.tasks = state.tasks.filter((t) => t.id !== id);
      if (state.profile.active_priority_task_id === id) {
        state.profile.active_priority_task_id = null;
        state.profile.active_priority_title = null;
      }
      return emptyRes(204);
    }

    // --- Sessions ---
    if (path === '/sessions' && method === 'GET') {
      return jsonRes(state.sessions);
    }
    if (path === '/sessions' && method === 'POST') {
      const isManual = Boolean(body.ended_at);
      const created: MockSessionDto = {
        id: nextId('sess'),
        user_id: TEST_USER_ID,
        title: String(body.title ?? '').trim(),
        category: String(body.category ?? 'Étude'),
        status: isManual ? 'completed' : 'in_progress',
        started_at: body.started_at ?? nowIso(),
        ended_at: body.ended_at ?? null,
        result: body.result ?? null,
        planned_activity: body.planned_activity ?? null,
        actual_activity: body.actual_activity ?? null,
        outcome_status: body.outcome_status ?? (isManual ? 'completed' : null),
        deliverable_summary: body.deliverable_summary ?? null,
        blockers: body.blockers ?? null,
        next_step: body.next_step ?? null,
        task_id: body.task_id ?? null,
        project_id: body.project_id ?? null,
        goal_id: body.goal_id ?? null,
        module_id: body.module_id ?? null,
        lesson_id: body.lesson_id ?? null,
        skill_id: body.skill_id ?? null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.sessions.unshift(created);
      return jsonRes(created, 201);
    }
    const sessFinishMatch = path.match(/^\/sessions\/([^/]+)\/finish$/);
    if (sessFinishMatch && method === 'PATCH') {
      const id = sessFinishMatch[1];
      const idx = state.sessions.findIndex((s) => s.id === id);
      if (idx === -1) return errRes(404, 'NOT_FOUND', 'Séance introuvable.');
      const cur = state.sessions[idx];
      const updated: MockSessionDto = {
        ...cur,
        status: 'completed',
        ended_at: body.ended_at ?? nowIso(),
        result: body.result ?? cur.result,
        planned_activity: body.planned_activity ?? cur.planned_activity ?? null,
        actual_activity: body.actual_activity ?? cur.actual_activity ?? null,
        outcome_status: body.outcome_status ?? cur.outcome_status ?? 'completed',
        deliverable_summary: body.deliverable_summary ?? cur.deliverable_summary ?? null,
        blockers: body.blockers ?? cur.blockers ?? null,
        next_step: body.next_step ?? cur.next_step ?? null,
        updated_at: nowIso(),
      };
      state.sessions[idx] = updated;
      return jsonRes(updated);
    }
    const sessMatch = path.match(/^\/sessions\/([^/]+)$/);
    if (sessMatch && method === 'PATCH') {
      const id = sessMatch[1];
      const idx = state.sessions.findIndex((s) => s.id === id);
      if (idx === -1) return errRes(404, 'NOT_FOUND', 'Séance introuvable.');
      state.sessions[idx] = {
        ...state.sessions[idx],
        status: body.status ?? state.sessions[idx].status,
        ended_at: body.status === 'cancelled' ? null : state.sessions[idx].ended_at,
        updated_at: nowIso(),
      };
      return jsonRes(state.sessions[idx]);
    }
    if (sessMatch && method === 'DELETE') {
      state.sessions = state.sessions.filter((s) => s.id !== sessMatch[1]);
      return emptyRes(204);
    }

    // --- Schedule & Timetable imports ---
    if (path === '/schedule' && method === 'GET') {
      return jsonRes(state.scheduleEvents);
    }
    if (path === '/schedule' && method === 'POST') {
      const created: MockScheduleEventDto = {
        id: nextId('ev'),
        user_id: TEST_USER_ID,
        title: String(body.title ?? '').trim(),
        type: body.type ?? 'learning',
        starts_at: body.starts_at,
        ends_at: body.ends_at,
        notes: body.notes ?? null,
        source: body.source ?? 'manual',
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.scheduleEvents.push(created);
      return jsonRes(created, 201);
    }
    if (path === '/schedule/duplicate-week' && method === 'POST') {
      const weekStartStr = String(body.source_week_start ?? '');
      const weekStartMs = new Date(`${weekStartStr}T00:00:00`).getTime();
      const weekEndMs = weekStartMs + 7 * 86_400_000;
      const src = state.scheduleEvents.filter((ev) => {
        const s = new Date(ev.starts_at).getTime();
        return s >= weekStartMs && s < weekEndMs;
      });
      let createdCount = 0;
      let skippedCount = 0;
      for (const ev of src) {
        const ns = new Date(new Date(ev.starts_at).getTime() + 7 * 86_400_000).toISOString();
        const ne = new Date(new Date(ev.ends_at).getTime() + 7 * 86_400_000).toISOString();
        const dup = state.scheduleEvents.some((e) => e.title === ev.title && e.starts_at === ns && e.ends_at === ne);
        if (dup) {
          skippedCount += 1;
          continue;
        }
        state.scheduleEvents.push({
          ...ev,
          id: nextId('ev'),
          starts_at: ns,
          ends_at: ne,
          created_at: nowIso(),
          updated_at: nowIso(),
        });
        createdCount += 1;
      }
      return jsonRes({ created_count: createdCount, skipped_count: skippedCount });
    }
    if (path === '/schedule/imports/analyze' && method === 'POST') {
      const form = init?.body as FormData;
      const file = form?.get('file') as File | null;
      const text = file ? await file.text() : '';
      const courses = parsePdfTimetableLines(text);
      const anomalies = computeServerTimetableAnomalies(courses);
      const imp = {
        id: nextId('imp'),
        user_id: TEST_USER_ID,
        filename: file?.name ?? 'emploi.pdf',
        file_format: 'pdf',
        mime_type: file?.type || 'application/pdf',
        file_size_bytes: file?.size ?? text.length,
        source_preview_text: text.slice(0, 1000),
        source_deleted: false,
        status: 'pending_review',
        valid_from: null,
        valid_until: null,
        extracted_courses: courses,
        anomalies,
        warnings: [],
        blocking_anomalies_count: anomalies.filter((a) => a.severity === 'error').length,
        created_events_count: 0,
        skipped_duplicates_count: 0,
        replaced_events_count: 0,
        created_at: nowIso(),
        updated_at: nowIso(),
        validated_at: null,
      };
      state.timetableImports.push(imp);
      return jsonRes(imp, 201);
    }
    const impDraftMatch = path.match(/^\/schedule\/imports\/([^/]+)$/);
    if (impDraftMatch && method === 'PATCH') {
      const imp = state.timetableImports.find((i) => i.id === impDraftMatch[1]);
      if (!imp) return errRes(404, 'NOT_FOUND', 'Import introuvable.');
      const courses = body.courses ?? imp.extracted_courses;
      const anomalies = computeServerTimetableAnomalies(courses);
      imp.extracted_courses = courses;
      imp.anomalies = anomalies;
      imp.blocking_anomalies_count = anomalies.filter((a: any) => a.severity === 'error').length;
      imp.valid_from = body.valid_from ?? imp.valid_from;
      imp.valid_until = body.valid_until ?? imp.valid_until;
      imp.updated_at = nowIso();
      return jsonRes(imp);
    }
    const impConfirmMatch = path.match(/^\/schedule\/imports\/([^/]+)\/confirm$/);
    if (impConfirmMatch && method === 'POST') {
      const imp = state.timetableImports.find((i) => i.id === impConfirmMatch[1]);
      if (!imp) return errRes(404, 'NOT_FOUND', 'Import introuvable.');
      const courses = (body.courses ?? imp.extracted_courses) as Array<Record<string, any>>;
      const anomalies = computeServerTimetableAnomalies(courses);
      if (anomalies.some((a) => a.severity === 'error')) {
        return errRes(422, 'TIMETABLE_BLOCKING_ANOMALIES', anomalies[0].message);
      }
      const targetStr = String(body.target_week_start ?? '');
      const base = targetStr ? new Date(`${targetStr}T12:00:00`) : new Date();
      const dayOffsetMon = (base.getDay() + 6) % 7;
      const monday = new Date(base.getFullYear(), base.getMonth(), base.getDate() - dayOffsetMon);
      const weeks = Math.max(1, Number(body.recurrence_weeks ?? 1));
      const subtypeLabels: Record<string, string> = { td: 'TD', tp: 'TP', examen: 'Examen' };

      if (body.replace_existing_imported) {
        state.scheduleEvents = state.scheduleEvents.filter((ev) => ev.source !== 'timetable_import');
      }

      const createdEvents: MockScheduleEventDto[] = [];
      for (let w = 0; w < weeks; w += 1) {
        for (const row of courses.filter((c) => !c.ignored)) {
          if (row.day_of_week === null || !row.start_time || !row.end_time) continue;
          const d = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + w * 7 + Number(row.day_of_week));
          const pad = (n: number) => String(n).padStart(2, '0');
          const dKey = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
          const prefix = subtypeLabels[row.session_type] ? `[${subtypeLabels[row.session_type]}] ` : '';
          const ev: MockScheduleEventDto = {
            id: nextId('ev'),
            user_id: TEST_USER_ID,
            title: `${prefix}${String(row.subject).trim()}`,
            type: 'course',
            starts_at: new Date(`${dKey}T${row.start_time}:00`).toISOString(),
            ends_at: new Date(`${dKey}T${row.end_time}:00`).toISOString(),
            notes: null,
            source: 'timetable_import',
            import_id: imp.id,
            session_subtype: row.session_type,
            teacher: row.teacher ?? null,
            room: row.room ?? null,
            group_name: row.group_name ?? null,
            created_at: nowIso(),
            updated_at: nowIso(),
          };
          state.scheduleEvents.push(ev);
          createdEvents.push(ev);
        }
      }
      imp.status = 'validated';
      imp.validated_at = nowIso();
      imp.created_events_count = createdEvents.length;
      return jsonRes({
        import_record: imp,
        created_events: createdEvents,
        created_count: createdEvents.length,
        skipped_duplicates_count: 0,
        replaced_count: 0,
      });
    }
    const impCancelMatch = path.match(/^\/schedule\/imports\/([^/]+)\/(cancel|source)$/);
    if (impCancelMatch) {
      const imp = state.timetableImports.find((i) => i.id === impCancelMatch[1]);
      if (!imp) return errRes(404, 'NOT_FOUND', 'Import introuvable.');
      if (impCancelMatch[2] === 'cancel') imp.status = 'cancelled';
      if (impCancelMatch[2] === 'source') imp.source_deleted = true;
      return jsonRes(imp);
    }
    const evMatch = path.match(/^\/schedule\/([^/]+)$/);
    if (evMatch && method === 'PATCH') {
      const idx = state.scheduleEvents.findIndex((e) => e.id === evMatch[1]);
      if (idx === -1) return errRes(404, 'NOT_FOUND', 'Créneau introuvable.');
      state.scheduleEvents[idx] = {
        ...state.scheduleEvents[idx],
        ...body,
        updated_at: nowIso(),
      };
      return jsonRes(state.scheduleEvents[idx]);
    }
    if (evMatch && method === 'DELETE') {
      state.scheduleEvents = state.scheduleEvents.filter((e) => e.id !== evMatch[1]);
      return emptyRes(204);
    }

    // --- Intelligent Planning Engine ---
    if (path === '/planning/availability-rules' && method === 'GET') {
      return jsonRes(state.availabilityRules);
    }
    if (path === '/planning/availability-rules' && method === 'POST') {
      const rule = {
        id: nextId('rule'),
        user_id: TEST_USER_ID,
        label: body.label,
        rule_type: body.rule_type,
        day_of_week: body.day_of_week ?? null,
        start_time: body.start_time ?? null,
        end_time: body.end_time ?? null,
        starts_at: body.starts_at ?? null,
        ends_at: body.ends_at ?? null,
        timezone: state.profile.timezone,
        recurrence: body.recurrence ?? 'weekly',
        active: body.active ?? true,
        notes: body.notes ?? null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.availabilityRules.push(rule);
      return jsonRes(rule, 201);
    }
    const ruleDelMatch = path.match(/^\/planning\/availability-rules\/([^/]+)$/);
    if (ruleDelMatch && method === 'DELETE') {
      state.availabilityRules = state.availabilityRules.filter((r) => r.id !== ruleDelMatch[1]);
      return emptyRes(204);
    }
    if (path === '/planning/versions' && method === 'GET') {
      return jsonRes(state.planVersions);
    }
    if (path === '/planning/validity' && method === 'GET') {
      return jsonRes({
        is_valid: true,
        expired_event_count: 0,
        expired_task_count: 0,
        overloaded_days: [],
        missed_session_count: 0,
        conflicting_event_ids: [],
        stale_reasons: [],
        recommendation: 'Planning cohérent.',
      });
    }
    if ((path === '/planning/generate' || path === '/planning/adjust') && method === 'POST') {
      const nextNum = (state.planVersions[0]?.version_number ?? 0) + 1;
      const start = new Date();
      start.setHours(9, 0, 0, 0);
      const end = new Date(start.getTime() + 60 * 60_000);
      const subject = body.focus_subject || 'React & Architecture Python';
      const version = {
        id: nextId('planv'),
        user_id: TEST_USER_ID,
        version_number: nextNum,
        status: 'proposed',
        horizon_days: body.horizon_days ?? 7,
        timezone: state.profile.timezone,
        rationale: `Programme généré (1 séance, 60 min) après prise en compte de ${state.availabilityRules.length} règle(s).`,
        priorities: [
          {
            source_type: 'personal_goal',
            source_id: null,
            title: subject,
            subject,
            domain: 'Apprentissage',
            score: 85,
            urgency_score: 20,
            blocking_score: 15,
            strategic_score: 25,
            effort_score: 15,
            deficit_score: 10,
            deadline_at: null,
            recommended_minutes: 180,
            reasons: ['Priorité active sans surcharge.'],
          },
        ],
        planned_sessions: [
          {
            slot_id: 'slot-1',
            title: `${subject} — Session 1`,
            session_type: 'learning',
            starts_at: start.toISOString(),
            ends_at: end.toISOString(),
            duration_minutes: 60,
            priority_source_type: 'personal_goal',
            priority_source_id: null,
            priority_score: 85,
            subject,
            task_id: null,
            project_id: null,
            skill_id: null,
            course_id: null,
            lesson_id: null,
            module_id: null,
            slot_category: 'potential_availability',
            rationale: 'Créneau sans conflit.',
            pedagogical_content: {
              content_source: 'course_generator_preview',
              course_id: null,
              course_title: subject,
              level_id: null,
              level_number: 1,
              level_title: 'Niveau 1',
              lesson_id: null,
              lesson_title: 'Module 1',
              module_id: null,
              module_title: null,
              skill_id: null,
              skill_name: subject,
              remediation_needed: false,
              remediation_reason: null,
              blocked_prerequisites: [],
              exercises_focus: ['Exercice guidé'],
              deliverables: ['Validation pratique'],
              recommended_session_type: 'deep_work',
              next_step_summary: `Progression sur ${subject}.`,
            },
          },
        ],
        arbitrage_items: [],
        load_summary: {
          daily_minutes: {},
          daily_cap_minutes: 240,
          weekly_planned_minutes: 60,
          weekly_cap_minutes: 360,
          recovery_preserved_minutes: 0,
          overloaded_days: [],
          is_overloaded: false,
        },
        availability_summary: null,
        missing_info: [],
        warnings: [],
        applied_event_ids: [],
        applied_task_ids: [],
        applied_course_ids: [],
        parent_version_id: state.planVersions[0]?.id ?? null,
        applied_at: null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.planVersions.unshift(version);
      return jsonRes(version);
    }
    const planActMatch = path.match(/^\/planning\/versions\/([^/]+)\/(apply|reject|restore)$/);
    if (planActMatch && method === 'POST') {
      const ver = state.planVersions.find((v) => v.id === planActMatch[1]);
      if (!ver) return errRes(404, 'NOT_FOUND', 'Version introuvable.');
      if (planActMatch[2] === 'reject') {
        ver.status = 'rejected';
      } else {
        ver.status = planActMatch[2] === 'restore' ? 'restored' : 'applied';
        ver.applied_at = nowIso();
        const createdIds: string[] = [];
        for (const sess of ver.planned_sessions) {
          const evId = nextId('ev');
          state.scheduleEvents.push({
            id: evId,
            user_id: TEST_USER_ID,
            title: sess.title,
            type: sess.session_type === 'project' ? 'project' : 'learning',
            starts_at: sess.starts_at,
            ends_at: sess.ends_at,
            notes: sess.rationale,
            source: 'ai_plan',
            created_at: nowIso(),
            updated_at: nowIso(),
          });
          createdIds.push(evId);
        }
        ver.applied_event_ids = createdIds;
      }
      ver.updated_at = nowIso();
      return jsonRes(ver);
    }

    // --- Learning (paths, modules, lessons) ---
    if (path === '/learning/overview' && method === 'GET') {
      return jsonRes({ paths: state.paths, modules: state.modules, lessons: state.lessons });
    }
    if (path === '/learning/paths' && method === 'POST') {
      const created = {
        id: nextId('path'),
        user_id: TEST_USER_ID,
        title: String(body.title ?? '').trim(),
        description: body.description ?? null,
        goal: String(body.goal ?? '').trim(),
        status: body.status ?? 'active',
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.paths.push(created);
      return jsonRes(created, 201);
    }
    const pathMatch = path.match(/^\/learning\/paths\/([^/]+)$/);
    if (pathMatch && method === 'PATCH') {
      const item = state.paths.find((p) => p.id === pathMatch[1]);
      if (!item) return errRes(404, 'NOT_FOUND', 'Parcours introuvable.');
      Object.assign(item, body, { updated_at: nowIso() });
      return jsonRes(item);
    }
    if (pathMatch && method === 'DELETE') {
      const id = pathMatch[1];
      const modIds = new Set(state.modules.filter((m) => m.path_id === id).map((m) => m.id));
      state.paths = state.paths.filter((p) => p.id !== id);
      state.modules = state.modules.filter((m) => m.path_id !== id);
      state.lessons = state.lessons.filter((l) => !modIds.has(l.module_id));
      return emptyRes(204);
    }
    if (path === '/learning/modules' && method === 'POST') {
      const created = {
        id: nextId('mod'),
        user_id: TEST_USER_ID,
        path_id: body.path_id,
        title: String(body.title ?? '').trim(),
        description: body.description ?? null,
        position: Number(body.position ?? 1),
        status: body.status ?? 'active',
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.modules.push(created);
      return jsonRes(created, 201);
    }
    const modMatch = path.match(/^\/learning\/modules\/([^/]+)$/);
    if (modMatch && method === 'PATCH') {
      const item = state.modules.find((m) => m.id === modMatch[1]);
      if (!item) return errRes(404, 'NOT_FOUND', 'Module introuvable.');
      Object.assign(item, body, { updated_at: nowIso() });
      return jsonRes(item);
    }
    if (modMatch && method === 'DELETE') {
      const id = modMatch[1];
      state.modules = state.modules.filter((m) => m.id !== id);
      state.lessons = state.lessons.filter((l) => l.module_id !== id);
      return emptyRes(204);
    }
    if (path === '/learning/lessons' && method === 'POST') {
      const created = {
        id: nextId('lesson'),
        user_id: TEST_USER_ID,
        module_id: body.module_id,
        title: String(body.title ?? '').trim(),
        content: body.content ?? null,
        resource_url: body.resource_url ?? null,
        position: Number(body.position ?? 1),
        status: body.status ?? 'active',
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.lessons.push(created);
      return jsonRes(created, 201);
    }
    const lesMatch = path.match(/^\/learning\/lessons\/([^/]+)$/);
    if (lesMatch && method === 'PATCH') {
      const item = state.lessons.find((l) => l.id === lesMatch[1]);
      if (!item) return errRes(404, 'NOT_FOUND', 'Leçon introuvable.');
      Object.assign(item, body, { updated_at: nowIso() });
      return jsonRes(item);
    }
    if (lesMatch && method === 'DELETE') {
      state.lessons = state.lessons.filter((l) => l.id !== lesMatch[1]);
      return emptyRes(204);
    }

    // --- Skills, Evidence & Assessments ---
    if (path === '/skills' && method === 'GET') {
      return jsonRes(state.skills);
    }
    if (path === '/skills' && method === 'POST') {
      const created: MockSkillDto = {
        id: nextId('skill'),
        user_id: TEST_USER_ID,
        name: String(body.name ?? '').trim(),
        domain: String(body.domain ?? '').trim(),
        description: body.description ?? null,
        current_level: 0,
        target_level: body.target_level ?? null,
        last_assessed_at: null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.skills.push(created);
      return jsonRes(created, 201);
    }
    const skillMatch = path.match(/^\/skills\/([^/]+)$/);
    if (skillMatch && method === 'PATCH') {
      const item = state.skills.find((s) => s.id === skillMatch[1]);
      if (!item) return errRes(404, 'NOT_FOUND', 'Compétence introuvable.');
      if ('current_level' in body) {
        return errRes(403, 'SKILL_ASSESSMENT_REQUIRED', 'Modification directe interdite.');
      }
      Object.assign(item, body, { updated_at: nowIso() });
      return jsonRes(item);
    }
    if (skillMatch && method === 'DELETE') {
      const id = skillMatch[1];
      state.skills = state.skills.filter((s) => s.id !== id);
      state.evidence = state.evidence.filter((e) => e.skill_id !== id);
      state.assessments = state.assessments.filter((a) => a.skill_id !== id);
      return emptyRes(204);
    }
    if (path === '/skills/evidence' && method === 'GET') {
      return jsonRes(state.evidence);
    }
    const evCreateMatch = path.match(/^\/skills\/([^/]+)\/evidence$/);
    if (evCreateMatch && method === 'POST') {
      const errMsg = checkDeclarativeEvidence(String(body.description ?? ''), body.result);
      if (errMsg) return errRes(422, 'EVIDENCE_QUALITY_INSUFFICIENT', errMsg);
      const created = {
        id: nextId('evd'),
        user_id: TEST_USER_ID,
        skill_id: evCreateMatch[1],
        type: body.type ?? 'exercise',
        description: String(body.description ?? '').trim(),
        reference_url: body.reference_url ?? null,
        result: body.result ?? null,
        observed_at: nowIso(),
        is_admissible: true,
        external_reference_verified: false,
        verification_note: null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.evidence.unshift(created);
      return jsonRes(created, 201);
    }
    const evDelMatch = path.match(/^\/skills\/([^/]+)\/evidence\/([^/]+)$/);
    if (evDelMatch && method === 'DELETE') {
      state.evidence = state.evidence.filter((e) => e.id !== evDelMatch[2]);
      return emptyRes(204);
    }
    if (path === '/skills/assessments' && method === 'GET') {
      return jsonRes(state.assessments);
    }
    const assessCreateMatch = path.match(/^\/skills\/([^/]+)\/assessments$/);
    if (assessCreateMatch && method === 'POST') {
      const skill = state.skills.find((s) => s.id === assessCreateMatch[1]);
      if (!skill) return errRes(404, 'NOT_FOUND', 'Compétence introuvable.');
      const targetLevel = Math.min(5, Math.max(1, Number(body.target_level ?? skill.current_level + 1)));
      const hasFailedPrior = state.assessments.some(
        (a) => a.skill_id === skill.id && (a.status === 'rejected' || a.passed === false),
      );
      const prefix = hasFailedPrior ? 'Exercice correctif' : 'Évaluation';
      const created = {
        id: nextId('assess'),
        user_id: TEST_USER_ID,
        skill_id: skill.id,
        path_id: body.path_id ?? null,
        module_id: body.module_id ?? null,
        lesson_id: body.lesson_id ?? null,
        assessment_type: body.assessment_type ?? 'practical_exercise',
        starting_level: skill.current_level,
        target_level: targetLevel,
        proposed_level: null,
        status: 'pending',
        prompt_title: `${prefix} — ${skill.name} (niveau ${targetLevel}/5)`,
        prompt_instructions: `Compétence évaluée : ${skill.name} (niveau actuel vérifié : ${skill.current_level}/5 → niveau visé : ${targetLevel}/5).`,
        revealed_hints: [] as string[],
        hints_total: 3,
        hints_revealed_count: 0,
        submission_text: null,
        submission_code: null,
        submission_reference_url: null,
        evidence_ids: [] as string[],
        criteria: [
          { key: 'relevance', label: 'Pertinence', description: 'Alignement', weight: 25, max_score: 25, score: 0, passed: false, feedback: '' },
          { key: 'technical_accuracy', label: 'Correction technique', description: 'Code/concepts', weight: 30, max_score: 30, score: 0, passed: false, feedback: '' },
          { key: 'reasoning_explanation', label: 'Raisonnement', description: 'Justification', weight: 25, max_score: 25, score: 0, passed: false, feedback: '' },
          { key: 'concrete_evidence', label: 'Preuve concrète', description: 'Livrable', weight: 20, max_score: 20, score: 0, passed: false, feedback: '' },
        ],
        score: null,
        passed: null,
        feedback: null,
        mastered_points: [],
        gaps_identified: [],
        remediation_recommendation: null,
        external_verification_warning: null,
        evaluator_type: 'pedagogical_engine',
        evaluator_name: null,
        decision_reason: null,
        applied_level_delta: null,
        submitted_at: null,
        evaluated_at: null,
        validated_at: null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.assessments.unshift(created);
      return jsonRes(created, 201);
    }
    const assessActMatch = path.match(/^\/skills\/([^/]+)\/assessments\/([^/]+)\/(hint|submit|evaluate|validate|reject|cancel)$/);
    if (assessActMatch && method === 'POST') {
      const [, skillId, assessId, action] = assessActMatch;
      const skill = state.skills.find((s) => s.id === skillId);
      const a = state.assessments.find((item) => item.id === assessId && item.skill_id === skillId);
      if (!skill || !a) return errRes(404, 'NOT_FOUND', 'Évaluation introuvable.');

      if (action === 'hint') {
        const hints = [
          `Indice 1 — Cadrage : définissez clairement l’entrée et le traitement pour « ${skill.name} ».`,
          'Indice 2 — Vérification : traitez un cas nominal et un cas d’erreur.',
          'Indice 3 — Raisonnement & preuve : joignez une preuve exécutée.',
        ];
        const nextCount = Math.min(3, a.hints_revealed_count + 1);
        a.hints_revealed_count = nextCount;
        a.revealed_hints = hints.slice(0, nextCount);
      } else if (action === 'submit') {
        const evIds = new Set<string>(Array.isArray(body.evidence_ids) ? body.evidence_ids : []);
        if (body.new_evidence) {
          const errMsg = checkDeclarativeEvidence(
            String(body.new_evidence.description ?? ''),
            body.new_evidence.result,
          );
          if (errMsg) return errRes(422, 'EVIDENCE_QUALITY_INSUFFICIENT', errMsg);
          const createdEv = {
            id: nextId('evd'),
            user_id: TEST_USER_ID,
            skill_id: skillId,
            type: body.new_evidence.type ?? 'exercise',
            description: String(body.new_evidence.description ?? '').trim(),
            reference_url: body.new_evidence.reference_url ?? null,
            result: body.new_evidence.result ?? null,
            observed_at: nowIso(),
            is_admissible: true,
            external_reference_verified: false,
            verification_note: null,
            created_at: nowIso(),
            updated_at: nowIso(),
          };
          state.evidence.unshift(createdEv);
          evIds.add(createdEv.id);
        }
        a.status = 'submitted';
        a.submission_text = body.submission_text ?? '';
        a.submission_code = body.submission_code ?? null;
        a.submission_reference_url = body.submission_reference_url ?? null;
        a.evidence_ids = Array.from(evIds);
        a.submitted_at = nowIso();
      } else if (action === 'evaluate') {
        const textLower = String(a.submission_text ?? '').toLowerCase();
        const codeStr = String(a.submission_code ?? '');
        const hasFailure = /ne sais pas|incorrecte|incomplet/.test(textLower);
        const hasEvidence = a.evidence_ids.length > 0;
        const passed = !hasFailure && hasEvidence && textLower.length >= 40 && codeStr.length >= 15;
        a.status = 'evaluated';
        a.passed = passed;
        a.score = passed ? 92 : 25;
        a.proposed_level = passed ? a.target_level : skill.current_level;
        a.mastered_points = passed ? ['Pertinence (25/25)', 'Preuve concrète (20/20)'] : [];
        a.gaps_identified = passed
          ? []
          : ['Preuve concrète : Aucune preuve admissible liée', 'Raisonnement insuffisant'];
        a.feedback = passed
          ? `Évaluation réussie (${a.score}/100). Niveau proposé : ${a.proposed_level}/5.`
          : `Évaluation non validée (${a.score}/100). Le niveau reste à ${skill.current_level}/5.`;
        a.remediation_recommendation = passed ? null : 'Associez une preuve concrète et relancez un exercice correctif.';
        a.evaluated_at = nowIso();
      } else if (action === 'validate') {
        if (!a.passed) return errRes(422, 'ASSESSMENT_NOT_PASSED', 'Score insuffisant.');
        const newLevel = Math.max(skill.current_level, Number(a.proposed_level ?? a.target_level));
        a.applied_level_delta = newLevel - skill.current_level;
        skill.current_level = newLevel;
        skill.last_assessed_at = nowIso();
        skill.updated_at = nowIso();
        a.status = 'approved';
        a.validated_at = nowIso();
      } else if (action === 'reject') {
        a.status = 'rejected';
        a.decision_reason = body.reason ?? 'Rejetée';
      } else if (action === 'cancel') {
        a.status = 'cancelled';
        a.decision_reason = body.reason ?? 'Annulée';
      }
      a.updated_at = nowIso();
      return jsonRes(a);
    }

    // --- Projects ---
    if (path === '/projects' && method === 'GET') {
      return jsonRes(state.projects);
    }
    if (path === '/projects' && method === 'POST') {
      const status = body.status ?? 'planned';
      const nextAction = String(body.next_action ?? '').trim();
      if (status === 'active') {
        const activeCount = state.projects.filter((p) => p.status === 'active').length;
        if (activeCount >= 3) {
          return errRes(409, 'PROJECT_ACTIVE_LIMIT', 'Limite de 3 projets actifs atteinte : mettez un projet en pause.');
        }
        if (nextAction.length < 2) {
          return errRes(422, 'PROJECT_NEXT_ACTION_REQUIRED', 'Une prochaine action concrète est obligatoire pour un projet actif.');
        }
      }
      const created = {
        id: nextId('proj'),
        user_id: TEST_USER_ID,
        name: String(body.name ?? '').trim(),
        description: body.description ?? null,
        goal: String(body.goal ?? '').trim(),
        status,
        priority: body.priority ?? 'normal',
        next_action: nextAction,
        deliverables: body.deliverables ?? null,
        target_date: body.target_date ?? null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.projects.unshift(created);
      return jsonRes(created, 201);
    }
    const projMatch = path.match(/^\/projects\/([^/]+)$/);
    if (projMatch && method === 'PATCH') {
      const idx = state.projects.findIndex((p) => p.id === projMatch[1]);
      if (idx === -1) return errRes(404, 'NOT_FOUND', 'Projet introuvable.');
      const cur = state.projects[idx];
      const nextStatus = body.status ?? cur.status;
      if (nextStatus === 'active' && cur.status !== 'active') {
        const activeCount = state.projects.filter((p) => p.status === 'active' && p.id !== cur.id).length;
        if (activeCount >= 3) {
          return errRes(409, 'PROJECT_ACTIVE_LIMIT', 'Limite de 3 projets actifs atteinte.');
        }
      }
      const updated = { ...cur, ...body, updated_at: nowIso() };
      state.projects[idx] = updated;
      if (
        state.profile.active_priority_project_id === cur.id &&
        (nextStatus === 'paused' || nextStatus === 'completed' || nextStatus === 'archived')
      ) {
        state.profile.active_priority_project_id = null;
        state.profile.active_priority_title = null;
      }
      return jsonRes(updated);
    }
    if (projMatch && method === 'DELETE') {
      const id = projMatch[1];
      state.projects = state.projects.filter((p) => p.id !== id);
      if (state.profile.active_priority_project_id === id) {
        state.profile.active_priority_project_id = null;
        state.profile.active_priority_title = null;
      }
      return emptyRes(204);
    }

    // --- Objectives & Unified Planning ---
    if (path === '/objectives/overview' && method === 'GET') {
      const academicObligations = state.scheduleEvents
        .filter((ev) => ev.type === 'course' || ev.source === 'timetable_import')
        .map((ev) => ({ id: ev.id, title: ev.title, starts_at: ev.starts_at, ends_at: ev.ends_at }));
      return jsonRes({
        academic_obligations: academicObligations,
        personal_goals: state.personalGoals,
        projects: state.projects,
        priority_summary: {
          active_priority_title: state.profile.active_priority_title,
        },
      });
    }
    if (path === '/objectives' && method === 'GET') {
      return jsonRes(state.personalGoals);
    }
    if (path === '/objectives' && method === 'POST') {
      const goal = {
        id: nextId('goal'),
        user_id: TEST_USER_ID,
        category: body.category ?? 'learning_goal',
        title: String(body.title ?? '').trim(),
        description: body.description ?? null,
        goal: body.goal ?? `Progresser sur ${body.title}`,
        current_level: body.current_level ?? null,
        target_level: body.target_level ?? null,
        priority: body.priority ?? 'normal',
        is_primary: Boolean(body.is_primary),
        motivation: body.motivation ?? null,
        start_date: body.start_date ?? null,
        target_date: body.target_date ?? null,
        weekly_target_minutes: Number(body.weekly_target_minutes ?? 120),
        status: body.status ?? 'active',
        steps: body.steps ?? [],
        deliverables: body.deliverables ?? [],
        next_action: body.next_action ?? '',
        success_criteria: body.success_criteria ?? [],
        progress_history: [],
        skill_id: null,
        learning_path_id: null,
        course_id: null,
        completed_minutes_last_7d: 0,
        sessions_count: 0,
        is_behind_schedule: false,
        delay_reason: null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.personalGoals.unshift(goal);
      if (goal.is_primary) {
        state.profile.active_priority_title = goal.title;
      }
      return jsonRes(goal, 201);
    }
    const goalMatch = path.match(/^\/objectives\/([^/]+)$/);
    if (goalMatch && method === 'PATCH') {
      const idx = state.personalGoals.findIndex((g) => g.id === goalMatch[1]);
      if (idx === -1) return errRes(404, 'NOT_FOUND', 'Objectif introuvable.');
      state.personalGoals[idx] = { ...state.personalGoals[idx], ...body, updated_at: nowIso() };
      if (body.is_primary) {
        state.profile.active_priority_title = state.personalGoals[idx].title;
      }
      return jsonRes(state.personalGoals[idx]);
    }
    if (goalMatch && method === 'DELETE') {
      state.personalGoals = state.personalGoals.filter((g) => g.id !== goalMatch[1]);
      return emptyRes(204);
    }
    if (path === '/objectives/intake/analyze' && method === 'POST') {
      const msg = String(body.message ?? '');
      const known = (body.known_answers ?? {}) as Record<string, any>;
      const candidates: Array<Record<string, any>> = [];
      if (/react/i.test(msg)) {
        candidates.push({
          kind: 'personal_goal',
          category: 'framework',
          title: 'React',
          goal: 'Maîtriser React et ses hooks.',
          current_level: known.current_level ?? null,
          target_level: known.target_level ?? null,
          priority: 'high',
          is_primary: known.primary_title === 'React',
          motivation: known.motivation ?? null,
          weekly_target_minutes: known.available_time_weekly_minutes ?? null,
          target_date: known.target_date ?? null,
          deliverables: ['Mini-application React'],
          validation_conditions: ['Tests passants'],
          next_action: 'Pratiquer les composants',
        });
      }
      if (/python/i.test(msg)) {
        candidates.push({
          kind: 'personal_goal',
          category: 'language',
          title: 'Python',
          goal: 'Consolider Python.',
          current_level: known.current_level ?? null,
          target_level: known.target_level ?? null,
          priority: 'normal',
          is_primary: known.primary_title === 'Python',
          motivation: known.motivation ?? null,
          weekly_target_minutes: known.available_time_weekly_minutes ?? null,
          target_date: known.target_date ?? null,
          deliverables: ['Scripts Python'],
          validation_conditions: ['Tests pytest'],
          next_action: 'Résoudre 2 exercices',
        });
      }
      if (/développement web|developpement web/i.test(msg)) {
        candidates.push({
          kind: 'personal_goal',
          category: 'domain',
          title: 'Développement web',
          goal: 'Améliorer mes compétences en développement web.',
          current_level: known.current_level ?? null,
          target_level: known.target_level ?? null,
          priority: 'normal',
          is_primary: false,
          motivation: known.motivation ?? null,
          weekly_target_minutes: known.available_time_weekly_minutes ?? null,
          target_date: known.target_date ?? null,
          deliverables: ['Interface complète'],
          validation_conditions: ['Revue qualité'],
          next_action: 'Structurer la page',
        });
      }
      if (/projet/i.test(msg)) {
        candidates.push({
          kind: 'project',
          category: 'project',
          title: 'Projet web pratique',
          goal: 'Construire des projets pratiques.',
          current_level: null,
          target_level: null,
          priority: 'normal',
          is_primary: false,
          motivation: known.motivation ?? null,
          weekly_target_minutes: known.available_time_weekly_minutes ?? null,
          target_date: known.target_date ?? null,
          deliverables: ['Dépôt Git'],
          validation_conditions: ['Tests validés'],
          next_action: 'Initialiser le projet',
        });
      }
      const missingFields: string[] = [];
      if (known.current_level == null) missingFields.push('current_level');
      if (known.available_time_weekly_minutes == null) missingFields.push('available_time_weekly_minutes');

      return jsonRes({
        objectives: candidates,
        current_level: known.current_level ?? null,
        target_level: known.target_level ?? null,
        priority: known.primary_title ?? null,
        motivation: known.motivation ?? null,
        available_time_weekly_minutes: known.available_time_weekly_minutes ?? null,
        target_date: known.target_date ?? null,
        expected_deliverables: [],
        validation_conditions: [],
        missing_fields: missingFields,
        progressive_questions: missingFields.map((f) => `Précisez ${f}`),
        requires_confirmation: true,
        summary_markdown: 'Récapitulatif prêt.',
      });
    }
    if (path === '/objectives/intake/confirm' && method === 'POST') {
      const objs = (body.objectives ?? []) as Array<Record<string, any>>;
      const createdGoals: Array<Record<string, any>> = [];
      const createdProjects: Array<Record<string, any>> = [];
      for (const item of objs) {
        if (item.kind === 'project') {
          const p = {
            id: nextId('proj'),
            user_id: TEST_USER_ID,
            name: item.title,
            description: null,
            goal: item.goal,
            status: 'active',
            priority: item.priority ?? 'normal',
            next_action: item.next_action || 'Démarrer',
            deliverables: item.deliverables ?? null,
            target_date: body.target_date ?? null,
            created_at: nowIso(),
            updated_at: nowIso(),
          };
          state.projects.push(p);
          createdProjects.push(p);
        } else {
          const g = {
            id: nextId('goal'),
            user_id: TEST_USER_ID,
            category: item.category ?? 'learning_goal',
            title: item.title,
            description: null,
            goal: item.goal,
            current_level: item.current_level ?? null,
            target_level: item.target_level ?? null,
            priority: item.priority ?? 'normal',
            is_primary: body.primary_title === item.title,
            motivation: body.motivation ?? null,
            start_date: null,
            target_date: body.target_date ?? null,
            weekly_target_minutes: Number(body.available_time_weekly_minutes ?? 120),
            status: 'active',
            steps: [],
            deliverables: item.deliverables ?? [],
            next_action: item.next_action ?? '',
            success_criteria: item.validation_conditions ?? [],
            progress_history: [],
            skill_id: null,
            learning_path_id: null,
            course_id: null,
            completed_minutes_last_7d: 0,
            sessions_count: 0,
            is_behind_schedule: false,
            delay_reason: null,
            created_at: nowIso(),
            updated_at: nowIso(),
          };
          state.personalGoals.push(g);
          createdGoals.push(g);
        }
      }
      if (body.primary_title) {
        state.profile.active_priority_title = body.primary_title;
      }
      return jsonRes({
        created_goals: createdGoals,
        created_projects: createdProjects,
        active_priority_title: state.profile.active_priority_title,
      });
    }
    if (path === '/objectives/plan/generate' && method === 'POST') {
      const now = new Date();
      const dayOffsetMon = (now.getDay() + 6) % 7;
      const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - dayOffsetMon);
      const pad = (n: number) => String(n).padStart(2, '0');
      const dayNames = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];

      const academicFixed = state.scheduleEvents
        .filter((ev) => ev.type === 'course' || ev.source === 'timetable_import')
        .map((ev) => ({
          source_category: 'academic_obligation',
          is_fixed: true,
          title: ev.title,
          day_label: 'Lundi',
          local_date: ev.starts_at.slice(0, 10),
          local_start_time: '08:30',
          local_end_time: '10:30',
          starts_at: ev.starts_at,
          ends_at: ev.ends_at,
          duration_minutes: 120,
          expected_outcome: 'Cours fixe',
          linked_goal_id: null,
          linked_project_id: null,
          linked_skill_id: null,
          linked_path_id: null,
          linked_module_id: null,
          linked_lesson_id: null,
          linked_task_id: null,
        }));

      const makeSlot = (dayIdx: number, startHHMM: string, endHHMM: string, title: string, cat: string, projId: string | null) => {
        const d = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + dayIdx);
        const dateKey = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        return {
          source_category: cat,
          is_fixed: false,
          title,
          day_label: dayNames[dayIdx],
          local_date: dateKey,
          local_start_time: startHHMM,
          local_end_time: endHHMM,
          starts_at: new Date(`${dateKey}T${startHHMM}:00`).toISOString(),
          ends_at: new Date(`${dateKey}T${endHHMM}:00`).toISOString(),
          duration_minutes: 90,
          expected_outcome: `Avancer sur ${title}`,
          linked_goal_id: state.personalGoals[0]?.id ?? null,
          linked_project_id: projId,
          linked_skill_id: null,
          linked_path_id: null,
          linked_module_id: null,
          linked_lesson_id: null,
          linked_task_id: null,
        };
      };

      const flexSlots = [
        makeSlot(0, '14:00', '15:30', state.personalGoals[0]?.title ?? 'React', 'personal_goal', null),
        makeSlot(1, '14:00', '15:30', state.projects[0]?.name ?? 'Portfolio StudyOS', 'project', state.projects[0]?.id ?? null),
      ];
      const recoverySlots = dayNames.map((_, idx) => makeSlot(idx, '21:00', '22:00', 'Récupération', 'recovery', null));

      return jsonRes({
        week_start: `${monday.getFullYear()}-${pad(monday.getMonth() + 1)}-${pad(monday.getDate())}`,
        primary_priority_title: body.primary_priority_title ?? state.profile.active_priority_title,
        secondary_objectives: [],
        academic_fixed_slots: academicFixed,
        flexible_study_slots: flexSlots,
        recovery_slots: recoverySlots,
        daily_breakdown: {},
        arbitrages: [],
        adaptations: [],
        displaced_conflicts_count: 0,
        total_academic_minutes: academicFixed.length * 120,
        total_personal_goal_minutes: 90,
        total_project_minutes: 90,
        requires_validation: true,
      });
    }
    if (path === '/objectives/plan/apply' && method === 'POST') {
      const slots = (body.flexible_study_slots ?? []) as Array<Record<string, any>>;
      let evCount = 0;
      let taskCount = 0;
      for (const s of slots) {
        state.scheduleEvents.push({
          id: nextId('ev'),
          user_id: TEST_USER_ID,
          title: s.title,
          type: s.source_category === 'project' ? 'project' : 'learning',
          starts_at: s.starts_at,
          ends_at: s.ends_at,
          notes: s.expected_outcome ?? null,
          source: 'ai_plan',
          created_at: nowIso(),
          updated_at: nowIso(),
        });
        evCount += 1;
        state.tasks.push({
          id: nextId('task'),
          user_id: TEST_USER_ID,
          title: s.title,
          description: s.expected_outcome ?? null,
          status: 'todo',
          priority: 'high',
          due_at: s.ends_at,
          completed_at: null,
          source: 'ai_proposal',
          proposal_id: null,
          project_id: s.linked_project_id ?? null,
          module_id: null,
          created_at: nowIso(),
          updated_at: nowIso(),
        });
        taskCount += 1;
      }
      if (body.primary_priority_title) {
        state.profile.active_priority_title = body.primary_priority_title;
      }
      return jsonRes({
        created_events_count: evCount,
        displaced_conflicts_count: 0,
        linked_tasks_created_count: taskCount,
        active_priority_title: state.profile.active_priority_title,
      });
    }

    // --- Courses ---
    if (path === '/courses' && method === 'GET') {
      return jsonRes(state.courses.map(serializeCourseSummary));
    }
    if (path === '/courses/preview' && method === 'POST') {
      const subject = String(body.subject ?? 'Python').trim();
      const totalLevels = Number(body.total_levels ?? 3);
      const previewCourse = buildPythonCourseDetail(
        'preview',
        subject,
        body.title || subject,
        body.domain || 'Développement',
        body.language || 'fr',
        totalLevels,
        null,
        null,
        nowIso(),
      );
      return jsonRes({
        title: previewCourse.title,
        subject,
        domain: previewCourse.domain,
        description: previewCourse.description,
        language: previewCourse.language,
        total_levels: totalLevels,
        levels_roadmap: previewCourse.levels.map((lv: any) => ({
          level_number: lv.level_number,
          title: lv.title,
          summary: lv.summary,
          objectives: lv.objectives,
          project_title: lv.project_title,
        })),
        first_level_lessons: previewCourse.levels[0].lessons.map((l: any) => ({
          position: l.position,
          title: l.title,
          summary: l.summary,
          estimated_minutes: l.estimated_minutes,
          content_markdown: l.content_markdown,
          code_examples: l.code_examples,
          exercises: l.exercises,
        })),
        first_level_project_title: previewCourse.levels[0].project_title,
        first_level_project_brief: previewCourse.levels[0].project_brief,
        first_level_project_deliverables: previewCourse.levels[0].project_deliverables,
        first_level_resources: previewCourse.resources.map((r: any) => ({
          title: r.title,
          url: r.url,
          resource_type: r.resource_type,
          language: r.language,
          is_official: r.is_official,
          source_name: r.source_name,
          notes: r.notes,
        })),
      });
    }
    if (path === '/courses' && method === 'POST') {
      const subject = String(body.subject ?? 'Python').trim();
      let skillId: string | null = null;
      if (body.link_skill !== false) {
        let sk = state.skills.find((s) => s.name.toLowerCase() === subject.toLowerCase());
        if (!sk) {
          sk = {
            id: nextId('skill'),
            user_id: TEST_USER_ID,
            name: subject,
            domain: body.domain || 'Développement',
            description: `Compétence liée au cours ${subject}`,
            current_level: 0,
            target_level: Number(body.total_levels ?? 3),
            last_assessed_at: null,
            created_at: nowIso(),
            updated_at: nowIso(),
          };
          state.skills.push(sk);
        }
        skillId = sk.id;
      }
      const cId = nextId('course');
      const created = buildPythonCourseDetail(
        cId,
        subject,
        body.title || subject,
        body.domain || 'Développement',
        body.language || 'fr',
        Number(body.total_levels ?? 3),
        skillId,
        null,
        nowIso(),
      );
      recomputeCourseReadiness(created);
      state.courses.unshift(created);
      return jsonRes(serializeCourseDetail(created), 201);
    }
    const courseMatch = path.match(/^\/courses\/([^/]+)$/);
    if (courseMatch && method === 'GET') {
      const c = state.courses.find((item) => item.id === courseMatch[1]);
      if (!c) return errRes(404, 'NOT_FOUND', 'Cours introuvable.');
      return jsonRes(serializeCourseDetail(c));
    }
    if (courseMatch && method === 'DELETE') {
      state.courses = state.courses.filter((c) => c.id !== courseMatch[1]);
      return emptyRes(204);
    }
    const courseLessonMatch = path.match(/^\/courses\/([^/]+)\/lessons\/([^/]+)$/);
    if (courseLessonMatch && method === 'PATCH') {
      const c = state.courses.find((item) => item.id === courseLessonMatch[1]);
      if (!c) return errRes(404, 'NOT_FOUND', 'Cours introuvable.');
      for (const lv of c.levels) {
        const l = lv.lessons.find((x: any) => x.id === courseLessonMatch[2]);
        if (l) {
          if (body.status !== undefined) {
            l.status = body.status;
            l.completed_at = body.status === 'completed' ? nowIso() : null;
          } else if (l.status === 'not_started' && body.current_step_index !== undefined) {
            l.status = 'in_progress';
          }
          if (body.current_step_index !== undefined) {
            l.current_step_index = Number(body.current_step_index);
          }
          l.updated_at = nowIso();
          recomputeCourseReadiness(c);
          return jsonRes(l);
        }
      }
      return errRes(404, 'NOT_FOUND', 'Leçon introuvable.');
    }
    const courseLessonAskMatch = path.match(/^\/courses\/([^/]+)\/lessons\/([^/]+)\/ask$/);
    if (courseLessonAskMatch && method === 'POST') {
      const c = state.courses.find((item) => item.id === courseLessonAskMatch[1]);
      if (!c) return errRes(404, 'NOT_FOUND', 'Cours introuvable.');
      for (const lv of c.levels) {
        const l = lv.lessons.find((x: any) => x.id === courseLessonAskMatch[2]);
        if (l) {
          const stepIndex = Number(body.step_index ?? 0);
          const userMsg = {
            id: nextId('tmsg'),
            role: 'user',
            content: String(body.message ?? ''),
            quick_action: body.quick_action ?? null,
            step_index: stepIndex,
            follow_up_prompts: [],
            created_at: nowIso(),
          };
          const assistantMsg = {
            id: nextId('tmsg'),
            role: 'assistant',
            content: `### Réponse du tuteur — ${l.title}\n\nVoici une explication ciblée sur ta question.`,
            quick_action: body.quick_action ?? null,
            step_index: stepIndex,
            follow_up_prompts: ['Donne un autre exemple concret', 'Teste-moi avec une question rapide'],
            created_at: nowIso(),
          };
          l.tutor_messages = [...(l.tutor_messages ?? []), userMsg, assistantMsg];
          if (l.status === 'not_started') l.status = 'in_progress';
          l.updated_at = nowIso();
          recomputeCourseReadiness(c);
          return jsonRes({ user_message: userMsg, assistant_message: assistantMsg, lesson: l });
        }
      }
      return errRes(404, 'NOT_FOUND', 'Leçon introuvable.');
    }
    const courseResPost = path.match(/^\/courses\/([^/]+)\/resources$/);
    if (courseResPost && method === 'POST') {
      const c = state.courses.find((item) => item.id === courseResPost[1]);
      if (!c) return errRes(404, 'NOT_FOUND', 'Cours introuvable.');
      const resObj = {
        id: nextId('res'),
        user_id: TEST_USER_ID,
        course_id: c.id,
        level_id: body.level_id ?? c.levels[0]?.id ?? null,
        lesson_id: body.lesson_id ?? null,
        title: body.title,
        url: body.url,
        resource_type: body.resource_type ?? 'documentation',
        language: body.language ?? 'fr',
        is_official: Boolean(body.is_official),
        source_name: body.source_name ?? null,
        notes: body.notes ?? null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      c.resources.unshift(resObj);
      if (resObj.level_id) {
        const targetLv = c.levels.find((lv: any) => lv.id === resObj.level_id);
        if (targetLv) {
          targetLv.resources.unshift(resObj);
        }
      }
      recomputeCourseReadiness(c);
      return jsonRes(resObj, 201);
    }
    const courseResDel = path.match(/^\/courses\/([^/]+)\/resources\/([^/]+)$/);
    if (courseResDel && method === 'DELETE') {
      const c = state.courses.find((item) => item.id === courseResDel[1]);
      if (!c) return errRes(404, 'NOT_FOUND', 'Cours introuvable.');
      c.resources = c.resources.filter((r: any) => r.id !== courseResDel[2]);
      for (const lv of c.levels) {
        lv.resources = lv.resources.filter((r: any) => r.id !== courseResDel[2]);
      }
      recomputeCourseReadiness(c);
      return emptyRes(204);
    }
    const courseSubMatch = path.match(/^\/courses\/([^/]+)\/levels\/([^/]+)\/submissions$/);
    if (courseSubMatch && method === 'POST') {
      const c = state.courses.find((item) => item.id === courseSubMatch[1]);
      const lv = c?.levels.find((item: any) => item.id === courseSubMatch[2]);
      if (!c || !lv) return errRes(404, 'NOT_FOUND', 'Niveau introuvable.');
      const ansLower = String(body.answer_text ?? '').toLowerCase();
      const codeStr = String(body.submitted_code ?? '').trim();
      const isDeclarativeOnly = /bien compris|c[’']est acquis/.test(ansLower) && !codeStr;
      const passed = !isDeclarativeOnly && ansLower.length >= 25 && codeStr.length >= 20;
      const score = passed ? 88 : 30;
      const sub = {
        id: nextId('sub'),
        user_id: TEST_USER_ID,
        course_id: c.id,
        level_id: lv.id,
        lesson_id: body.lesson_id ?? null,
        submission_kind: body.submission_kind ?? 'exercise',
        exercise_id: body.exercise_id ?? null,
        title: body.title ?? 'Soumission',
        answer_text: body.answer_text ?? '',
        submitted_code: body.submitted_code ?? null,
        reference_url: body.reference_url ?? null,
        status: passed ? 'passed' : 'failed',
        score,
        passed,
        criteria_results: [],
        feedback_markdown: passed ? 'Seuil atteint : implémentation validée.' : 'Insuffisant : ajoutez du code et des tests.',
        strengths: passed ? ['Code fonctionnel et validation explicite'] : [],
        improvements: passed ? [] : ['Joindre une implémentation concrète'],
        next_step_hint: null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      lv.submissions.unshift(sub);
      recomputeCourseReadiness(c);
      return jsonRes(sub, 201);
    }
    const courseValMatch = path.match(/^\/courses\/([^/]+)\/levels\/([^/]+)\/validate$/);
    if (courseValMatch && method === 'POST') {
      const c = state.courses.find((item) => item.id === courseValMatch[1]);
      const lvIdx = c?.levels.findIndex((item: any) => item.id === courseValMatch[2]) ?? -1;
      if (!c || lvIdx === -1) return errRes(404, 'NOT_FOUND', 'Niveau introuvable.');
      const lv = c.levels[lvIdx];
      recomputeCourseReadiness(c);
      if (!lv.can_validate) {
        return errRes(422, 'COURSE_LEVEL_LOCKED', 'Complétez tous les chapitres, 1 exercice et le projet.');
      }
      lv.status = 'validated';
      lv.validated_at = nowIso();
      const nextLv = c.levels[lvIdx + 1];
      if (nextLv) {
        nextLv.status = 'unlocked';
        nextLv.content_generated = true;
        if (typeof nextLv._makeLevel2Lessons === 'function') {
          nextLv.lessons = nextLv._makeLevel2Lessons();
        }
        if (typeof nextLv._makeLevel2Resources === 'function' && nextLv.resources.length === 0) {
          const level2Resources = nextLv._makeLevel2Resources();
          nextLv.resources = level2Resources;
          c.resources.push(...level2Resources);
        }
        c.current_level = nextLv.level_number;
      }
      if (c.skill_id) {
        state.evidence.unshift({
          id: nextId('evd'),
          user_id: TEST_USER_ID,
          skill_id: c.skill_id,
          type: 'project',
          description: `Validation du niveau ${lv.level_number} du cours « ${c.title} »`,
          reference_url: null,
          result: 'Projet validé selon la grille.',
          observed_at: nowIso(),
          is_admissible: true,
          external_reference_verified: false,
          verification_note: null,
          created_at: nowIso(),
          updated_at: nowIso(),
        });
      }
      recomputeCourseReadiness(c);
      return jsonRes(serializeCourseDetail(c));
    }

    // --- AI Copilot & Provider Settings ---
    if (path === '/ai/tools' && method === 'GET') {
      return jsonRes(DEFAULT_TOOLS);
    }
    if (path === '/ai/conversations' && method === 'GET') {
      return jsonRes(state.conversations);
    }
    if (path === '/ai/conversations' && method === 'POST') {
      const conv = {
        id: nextId('conv'),
        user_id: TEST_USER_ID,
        title: String(body.title ?? 'Nouvelle conversation').trim() || 'Nouvelle conversation',
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      state.conversations.unshift(conv);
      return jsonRes(conv, 201);
    }
    const convDetailMatch = path.match(/^\/ai\/conversations\/([^/]+)$/);
    if (convDetailMatch && method === 'GET') {
      const conv = state.conversations.find((c) => c.id === convDetailMatch[1]);
      if (!conv) return errRes(404, 'NOT_FOUND', 'Conversation introuvable.');
      return jsonRes({
        conversation: conv,
        messages: state.messages.filter((m) => m.conversation_id === conv.id),
        proposals: state.proposals.filter((p) => p.conversation_id === conv.id),
      });
    }
    if (convDetailMatch && method === 'DELETE') {
      const id = convDetailMatch[1];
      state.conversations = state.conversations.filter((c) => c.id !== id);
      state.messages = state.messages.filter((m) => m.conversation_id !== id);
      state.proposals = state.proposals.filter((p) => p.conversation_id !== id);
      return emptyRes(204);
    }
    const convMsgMatch = path.match(/^\/ai\/conversations\/([^/]+)\/messages$/);
    if (convMsgMatch && method === 'POST') {
      const convId = convMsgMatch[1];
      const text = String(body.content ?? '').trim();
      const lower = text.toLowerCase();
      const userMsg = {
        id: nextId('msg'),
        user_id: TEST_USER_ID,
        conversation_id: convId,
        role: 'user',
        content: text,
        metadata: {},
        created_at: nowIso(),
      };
      state.messages.push(userMsg);

      const createdProposals: Array<Record<string, any>> = [];
      let assistantText = 'Message analysé en contexte complet StudyOS.';
      const autoExec = Boolean(body.auto_execute_simple ?? state.aiMemory.auto_execute_simple_actions);
      let autoExecutedCount = 0;

      if (/crée un cours|cree un cours|cours complet/i.test(lower)) {
        const subject = /python/i.test(text) ? 'Python' : 'React';
        const prop = {
          id: nextId('prop'),
          user_id: TEST_USER_ID,
          conversation_id: convId,
          action_type: 'create_course',
          title: `Nouveau cours complet — ${subject}`,
          explanation: `Préparer un cours progressif de ${subject}.`,
          payload: { subject, total_levels: 3, domain: 'Développement', language: 'fr', link_skill: true },
          status: 'pending',
          expires_at: null,
          execution_result: null,
          error_message: null,
          created_at: nowIso(),
          resolved_at: null,
        };
        state.proposals.unshift(prop);
        createdProposals.push(prop);
        assistantText = `Proposition de cours complet sur ${subject} prête à valider.`;
      } else if (/crée une tâche|cree une tache/i.test(lower)) {
        const m = text.match(/[«"']([^«»"']+)[»"']/);
        const title = m ? m[1].trim() : text;
        const prop: Record<string, any> = {
          id: nextId('prop'),
          user_id: TEST_USER_ID,
          conversation_id: convId,
          action_type: 'create_task',
          title: `Créer la tâche « ${title} »`,
          explanation: 'Action proposée avec validation utilisateur.',
          payload: { title, description: '', priority: 'normal' },
          status: autoExec ? 'executed' : 'pending',
          expires_at: null,
          execution_result: null,
          error_message: null,
          created_at: nowIso(),
          resolved_at: autoExec ? nowIso() : null,
        };
        if (autoExec) {
          const t: MockTaskDto = {
            id: nextId('task'),
            user_id: TEST_USER_ID,
            title,
            description: null,
            status: 'todo',
            priority: 'normal',
            due_at: null,
            completed_at: null,
            source: 'ai_proposal',
            proposal_id: prop.id,
            project_id: null,
            module_id: null,
            created_at: nowIso(),
            updated_at: nowIso(),
          };
          state.tasks.unshift(t);
          prop.execution_result = { entity: 'task', id: t.id, title };
          autoExecutedCount = 1;
        }
        state.proposals.unshift(prop);
        createdProposals.push(prop);
        assistantText = autoExec
          ? `Tâche « ${title} » exécutée automatiquement.`
          : `Voici ma proposition de tâche « ${title} ».`;
      } else if (/parking/i.test(lower)) {
        const targetTask = state.tasks[0];
        const prop = {
          id: nextId('prop'),
          user_id: TEST_USER_ID,
          conversation_id: convId,
          action_type: 'park_task',
          title: `Mettre au parking « ${targetTask?.title ?? 'Tâche'} »`,
          explanation: 'Protéger la priorité active.',
          payload: { task_id: targetTask?.id ?? '', reason: 'Report volontaire' },
          status: 'pending',
          expires_at: null,
          execution_result: null,
          error_message: null,
          created_at: nowIso(),
          resolved_at: null,
        };
        state.proposals.unshift(prop);
        createdProposals.push(prop);
        assistantText = 'Proposition de mise au parking préparée.';
      } else if (/je voudrais apprendre/i.test(lower)) {
        const subjectMatch = text.match(/apprendre\s+(?:le\s+d[ée]veloppement\s+avec\s+|la\s+|le\s+|l['’])?([^.!?\n]+)/i);
        const rawTopic = subjectMatch ? subjectMatch[1].trim() : 'Nouvel objectif';
        const topic = /react/i.test(rawTopic) ? 'React' : rawTopic;
        const activePrio = state.profile.active_priority_title;
        const isConflict = Boolean(activePrio && !rawTopic.toLowerCase().includes(activePrio.toLowerCase()));
        const slotStart = new Date(Date.now() + 2 * 3_600_000).toISOString();
        const slotEnd = new Date(Date.now() + 3 * 3_600_000).toISOString();

        const prop = {
          id: nextId('prop'),
          user_id: TEST_USER_ID,
          conversation_id: convId,
          action_type: 'plan_strategic_activity',
          title: isConflict
            ? `Placer « ${topic} » dans le Parking des idées`
            : `Programmer « ${topic} »`,
          explanation: isConflict
            ? 'Risque de dispersion par rapport à la priorité principale active.'
            : 'Créneau libre trouvé sans chevauchement.',
          payload: {
            activity_title: topic,
            category: 'learning_goal',
            goal: `Apprendre ${topic}`,
            decision: isConflict ? 'NOT_RECOMMENDED' : 'ACCEPTABLE',
            park_only: isConflict,
            create_learning_path: !isConflict,
            create_project: false,
            proposed_slots: isConflict ? [] : [{ starts_at: slotStart, ends_at: slotEnd, title: topic }],
          },
          status: 'pending',
          expires_at: null,
          execution_result: null,
          error_message: null,
          created_at: nowIso(),
          resolved_at: null,
        };
        state.proposals.unshift(prop);
        createdProposals.push(prop);
        assistantText = isConflict
          ? `STOP — DISPERSION DÉTECTÉE. Votre priorité active « ${activePrio} » risque d’être ralentie.`
          : `Voici ma proposition pour ${topic} : créneau libre identifié sans conflit.`;
      }

      const missingData: string[] = [];
      if (!state.profile.active_priority_title) missingData.push('Aucune priorité active');
      if (state.tasks.length === 0) missingData.push('Aucune tâche active');

      const assistantMsg = {
        id: nextId('msg'),
        user_id: TEST_USER_ID,
        conversation_id: convId,
        role: 'assistant',
        content: assistantText,
        metadata: {
          is_estimate: missingData.length > 0,
          missing_data: missingData,
          auto_executed_count: autoExecutedCount,
        },
        created_at: nowIso(),
      };
      state.messages.push(assistantMsg);
      return jsonRes(
        {
          user_message: userMsg,
          assistant_message: assistantMsg,
          proposals: createdProposals,
          auto_executed_count: autoExecutedCount,
        },
        201,
      );
    }
    if (path === '/ai/proposals' && method === 'GET') {
      return jsonRes(state.proposals);
    }
    const propUpdateMatch = path.match(/^\/ai\/proposals\/([^/]+)$/);
    if (propUpdateMatch && method === 'PATCH') {
      const p = state.proposals.find((item) => item.id === propUpdateMatch[1]);
      if (!p) return errRes(404, 'NOT_FOUND', 'Proposition introuvable.');
      p.payload = { ...p.payload, ...(body.payload_overrides ?? {}) };
      if (typeof p.payload.activity_title === 'string' && p.action_type === 'plan_strategic_activity') {
        p.title = p.payload.park_only
          ? `Placer « ${p.payload.activity_title} » dans le Parking des idées`
          : `Programmer « ${p.payload.activity_title} »`;
      }
      return jsonRes(p);
    }
    const propActMatch = path.match(/^\/ai\/proposals\/([^/]+)\/(accept|reject)$/);
    if (propActMatch && method === 'POST') {
      const p = state.proposals.find((item) => item.id === propActMatch[1]);
      if (!p) return errRes(404, 'NOT_FOUND', 'Proposition introuvable.');
      if (propActMatch[2] === 'reject') {
        p.status = 'rejected';
        p.error_message = body.reason ?? null;
        p.resolved_at = nowIso();
        return jsonRes(p);
      }
      const merged = { ...p.payload, ...(body.payload_overrides ?? {}) };
      if (p.action_type === 'create_task') {
        const t: MockTaskDto = {
          id: nextId('task'),
          user_id: TEST_USER_ID,
          title: String(merged.title ?? '').trim(),
          description: merged.description ?? null,
          status: 'todo',
          priority: merged.priority ?? 'normal',
          due_at: null,
          completed_at: null,
          source: 'ai_proposal',
          proposal_id: p.id,
          project_id: null,
          module_id: null,
          created_at: nowIso(),
          updated_at: nowIso(),
        };
        state.tasks.unshift(t);
        p.execution_result = { entity: 'task', id: t.id, title: t.title };
      } else if (p.action_type === 'create_course') {
        const subject = String(merged.subject ?? 'Python');
        const cId = nextId('course');
        const c = buildPythonCourseDetail(
          cId,
          subject,
          merged.title || subject,
          merged.domain || 'Développement',
          'fr',
          Number(merged.total_levels ?? 3),
          null,
          null,
          nowIso(),
        );
        state.courses.unshift(c);
        p.execution_result = { entity: 'course', id: c.id, course_id: c.id, subject };
      } else if (p.action_type === 'plan_strategic_activity') {
        const title = String(merged.activity_title ?? 'Activité');
        const pathObj = {
          id: nextId('path'),
          user_id: TEST_USER_ID,
          title,
          description: null,
          goal: merged.goal ?? title,
          status: 'active',
          created_at: nowIso(),
          updated_at: nowIso(),
        };
        state.paths.push(pathObj);
        const slots = Array.isArray(merged.proposed_slots) ? merged.proposed_slots : [];
        for (const s of slots) {
          state.scheduleEvents.push({
            id: nextId('ev'),
            user_id: TEST_USER_ID,
            title: s.title ?? title,
            type: 'learning',
            starts_at: s.starts_at,
            ends_at: s.ends_at,
            notes: null,
            source: 'ai_plan',
            created_at: nowIso(),
            updated_at: nowIso(),
          });
        }
        state.tasks.unshift({
          id: nextId('task'),
          user_id: TEST_USER_ID,
          title,
          description: null,
          status: 'todo',
          priority: 'normal',
          due_at: null,
          completed_at: null,
          source: 'ai_proposal',
          proposal_id: p.id,
          project_id: null,
          module_id: null,
          created_at: nowIso(),
          updated_at: nowIso(),
        });
        p.execution_result = { entity: 'strategic_plan', path_id: pathObj.id };
      }
      p.status = 'executed';
      p.resolved_at = nowIso();
      return jsonRes(p);
    }
    if (path === '/ai/reports' && method === 'GET') {
      return jsonRes(state.reports);
    }
    if (path === '/ai/reports/ensure' && method === 'POST') {
      return jsonRes({
        daily_briefing: state.reports[0] ?? {
          id: 'rep-auto-d',
          user_id: TEST_USER_ID,
          type: 'daily_briefing',
          period_start: nowIso(),
          period_end: nowIso(),
          content: 'Briefing',
          metadata: {},
          created_at: nowIso(),
        },
        weekly_review: state.reports[0] ?? {
          id: 'rep-auto-w',
          user_id: TEST_USER_ID,
          type: 'weekly_review',
          period_start: nowIso(),
          period_end: nowIso(),
          content: 'Bilan',
          metadata: {},
          created_at: nowIso(),
        },
        created_daily: false,
        created_weekly: false,
      });
    }
    if (path === '/ai/briefing' && method === 'POST') {
      const rep = {
        id: nextId('rep'),
        user_id: TEST_USER_ID,
        type: 'daily_briefing',
        period_start: nowIso(),
        period_end: nowIso(),
        content: `## Briefing quotidien : ${state.profile.timezone}`,
        metadata: { is_estimate: false, missing_data: [] },
        created_at: nowIso(),
      };
      state.reports.unshift(rep);
      return jsonRes(rep, 201);
    }
    if (path === '/ai/weekly-review' && method === 'POST') {
      const rep = {
        id: nextId('rep'),
        user_id: TEST_USER_ID,
        type: 'weekly_review',
        period_start: nowIso(),
        period_end: nowIso(),
        content: '## Bilan hebdomadaire (7 derniers jours)',
        metadata: { is_estimate: false, missing_data: [] },
        created_at: nowIso(),
      };
      state.reports.unshift(rep);
      return jsonRes(rep, 201);
    }
    if (path === '/ai/memory' && method === 'GET') {
      return jsonRes(state.aiMemory);
    }
    if (path === '/ai/memory' && method === 'PATCH') {
      state.aiMemory = {
        ...state.aiMemory,
        ...body,
        updated_at: nowIso(),
      };
      return jsonRes(state.aiMemory);
    }
    if (path === '/ai/provider/config' && method === 'GET') {
      return jsonRes(state.providerConfig);
    }
    if (path === '/ai/provider/config' && method === 'PUT') {
      state.providerConfig = {
        ...state.providerConfig,
        provider: body.provider ?? state.providerConfig.provider,
        base_url: body.base_url ?? '',
        model: body.model ?? state.providerConfig.model,
        has_api_key: Boolean(body.api_key) && !body.clear_api_key,
        source: 'user',
      };
      return jsonRes(state.providerConfig);
    }
    if (path === '/ai/provider/models' && method === 'POST') {
      if (seed.externalFetch) {
        return seed.externalFetch(urlStr, init);
      }
      return jsonRes({
        provider: body.provider ?? 'river',
        base_url: body.base_url || 'https://api.river.ai/v1',
        models: [
          { id: 'claude-3-7-sonnet', label: 'Claude 3.7 Sonnet', owned_by: 'anthropic', context_window: 200000 },
          { id: 'gpt-4o', label: 'gpt-4o', owned_by: 'openai', context_window: 128000 },
        ],
        count: 2,
      });
    }

    return errRes(404, 'UNHANDLED_TEST_ROUTE', `Route non gérée dans mockStudyApi: ${method} ${path}`);
  };

  const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
    const urlStr = typeof input === 'string' ? input : input instanceof Request ? input.url : String(input);
    if (urlStr.startsWith('http://localhost:8000/api/v1')) {
      return handleApiRequest(urlStr, init);
    }
    if (seed.externalFetch) {
      return seed.externalFetch(urlStr, init);
    }
    return Promise.resolve(jsonRes([]));
  });

  return { state, requests, fetchSpy };
}
