import type {
  PersonalGoalCreateInput,
  PersonalGoalUpdateInput,
} from '../../lib/objectivesApi';
import { addDays, getMondayOfWeek, localDateAndTimeToIso, toLocalDateKey } from '../../lib/date';
import { generateId, readFromStorage, STORAGE_KEYS, writeToStorage } from '../../lib/storage';
import type {
  ConversationalIntakeRecap,
  ExtractedObjectiveCandidate,
  ObjectiveCategory,
  PersonalGoal,
  Project,
  ScheduleEvent,
  SessionFinishExtra,
  StudySession,
  Task,
  TaskPriority,
  UnifiedPlan,
  UnifiedPlanAdaptationItem,
  UnifiedPlanSlot,
} from '../../types/domain';

const LOCAL_USER_ID = 'local-user';

const LEARNING_CATALOG: Array<{
  keywords: string[];
  title: string;
  category: ObjectiveCategory;
  goal: string;
  nextAction: string;
}> = [
  {
    keywords: ['react'],
    title: 'React',
    category: 'framework',
    goal: 'Maîtriser les composants, props, hooks et tests unitaires en React.',
    nextAction: 'Étudier les composants et props, réaliser un exercice et fournir le code',
  },
  {
    keywords: ['python'],
    title: 'Python',
    category: 'language',
    goal: 'Approfondir Python, la programmation propre et la résolution d’exercices ciblés.',
    nextAction: 'Reprendre une notion Python ciblée et réussir une série d’exercices',
  },
  {
    keywords: ['développement web', 'developpement web', 'dev web', 'web'],
    title: 'Développement web',
    category: 'technology',
    goal: 'Renforcer l’architecture web, les APIs REST et la qualité front-end et back-end.',
    nextAction: 'Concevoir un endpoint relié à une vue interactive testée',
  },
  {
    keywords: ['typescript'],
    title: 'TypeScript',
    category: 'language',
    goal: 'Fiabiliser le typage strict et la modélisation métier en TypeScript.',
    nextAction: 'Typer un module existant et vérifier la compilation stricte',
  },
  {
    keywords: ['javascript', 'js'],
    title: 'JavaScript',
    category: 'language',
    goal: 'Maîtriser l’asynchrone, les structures de données et le DOM moderne.',
    nextAction: 'Résoudre deux exercices sur Promises et manipulation de collections',
  },
  {
    keywords: ['sql', 'postgres', 'base de données'],
    title: 'SQL & Bases de données',
    category: 'technology',
    goal: 'Concevoir des requêtes SQL propres, jointures, index et contraintes fiables.',
    nextAction: 'Écrire et tester une requête analytique avec jointures et index',
  },
  {
    keywords: ['docker'],
    title: 'Docker',
    category: 'technology',
    goal: 'Conteneuriser des applications de développement reproductibles.',
    nextAction: 'Écrire un Dockerfile minimal et vérifier le lancement local',
  },
  {
    keywords: ['anglais', 'english'],
    title: 'Anglais technique',
    category: 'spoken_language',
    goal: 'Améliorer la compréhension technique et l’expression orale professionnelle.',
    nextAction: 'Lire une documentation technique et rédiger un résumé de 10 lignes',
  },
];

export function computeGoalScheduleMetrics(
  goal: PersonalGoal,
  sessions: StudySession[],
  now = new Date(),
): PersonalGoal {
  const sevenDaysAgo = now.getTime() - 7 * 24 * 60 * 60 * 1000;
  let completedMinutesLast7d = 0;
  let sessionsCount = 0;

  for (const session of sessions) {
    if (session.status !== 'completed') continue;
    const matchesGoal =
      session.goalId === goal.id ||
      (goal.skillId && session.skillId === goal.skillId) ||
      session.title.toLowerCase().includes(goal.title.toLowerCase());
    if (!matchesGoal) continue;
    sessionsCount += 1;
    const endMs = session.endedAt ? new Date(session.endedAt).getTime() : 0;
    const startMs = new Date(session.startedAt).getTime();
    if (endMs > startMs && startMs >= sevenDaysAgo) {
      completedMinutesLast7d += Math.max(1, Math.round((endMs - startMs) / 60000));
    }
  }

  let isBehindSchedule = false;
  let delayReason: string | null = null;
  if (goal.targetDate && goal.status !== 'completed') {
    const deadlineMs = new Date(goal.targetDate).getTime();
    if (!Number.isNaN(deadlineMs) && deadlineMs < now.getTime()) {
      isBehindSchedule = true;
      delayReason =
        "Échéance atteinte sans validation complète. Un objectif n'est jamais marqué accompli uniquement par sa date.";
    }
  }

  return {
    ...goal,
    completedMinutesLast7d,
    sessionsCount,
    isBehindSchedule,
    delayReason,
  };
}

export function readLocalPersonalGoals(sessions: StudySession[] = []): PersonalGoal[] {
  const raw = readFromStorage<PersonalGoal[]>(STORAGE_KEYS.objectivesState, []);
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.map((item) => computeGoalScheduleMetrics(item, sessions));
}

export function writeLocalPersonalGoals(goals: PersonalGoal[]): void {
  writeToStorage(STORAGE_KEYS.objectivesState, goals);
}

export function createLocalPersonalGoal(input: PersonalGoalCreateInput): PersonalGoal {
  const nowIso = new Date().toISOString();
  const existing = readFromStorage<PersonalGoal[]>(STORAGE_KEYS.objectivesState, []);
  const normalizedExisting = input.isPrimary
    ? existing.map((g) => ({ ...g, isPrimary: false, updatedAt: nowIso }))
    : existing;

  const created: PersonalGoal = {
    id: generateId(),
    userId: LOCAL_USER_ID,
    category: input.category ?? 'learning_goal',
    title: input.title.trim(),
    description: input.description?.trim() || null,
    goal: input.goal?.trim() || `Progresser durablement sur ${input.title.trim()}.`,
    currentLevel: input.currentLevel ?? null,
    targetLevel: input.targetLevel ?? null,
    priority: input.priority ?? 'normal',
    isPrimary: Boolean(input.isPrimary),
    motivation: input.motivation?.trim() || null,
    startDate: input.startDate ?? nowIso,
    targetDate: input.targetDate ?? null,
    weeklyTargetMinutes: input.weeklyTargetMinutes ?? 120,
    status: input.status ?? 'active',
    steps: input.steps ?? [],
    deliverables: input.deliverables ?? [],
    nextAction:
      input.nextAction?.trim() || `Planifier la première séance ciblée sur ${input.title.trim()}.`,
    successCriteria: input.successCriteria ?? [],
    progressHistory: [
      {
        date: nowIso,
        summary: 'Objectif initialisé hors emploi du temps universitaire.',
      },
    ],
    skillId: null,
    learningPathId: null,
    courseId: null,
    completedMinutesLast7d: 0,
    sessionsCount: 0,
    isBehindSchedule: false,
    delayReason: null,
    createdAt: nowIso,
    updatedAt: nowIso,
  };

  writeLocalPersonalGoals([created, ...normalizedExisting]);
  return created;
}

export function updateLocalPersonalGoal(
  goalId: string,
  patch: PersonalGoalUpdateInput,
): PersonalGoal | null {
  const nowIso = new Date().toISOString();
  const existing = readFromStorage<PersonalGoal[]>(STORAGE_KEYS.objectivesState, []);
  let updatedItem: PersonalGoal | null = null;
  const next = existing.map((goal) => {
    if (goal.id !== goalId) {
      return patch.isPrimary ? { ...goal, isPrimary: false, updatedAt: nowIso } : goal;
    }
    updatedItem = {
      ...goal,
      ...(patch.title !== undefined ? { title: patch.title.trim() } : {}),
      ...(patch.category !== undefined ? { category: patch.category } : {}),
      ...(patch.description !== undefined ? { description: patch.description } : {}),
      ...(patch.goal !== undefined && patch.goal !== null ? { goal: patch.goal } : {}),
      ...(patch.currentLevel !== undefined ? { currentLevel: patch.currentLevel } : {}),
      ...(patch.targetLevel !== undefined ? { targetLevel: patch.targetLevel } : {}),
      ...(patch.priority !== undefined ? { priority: patch.priority } : {}),
      ...(patch.isPrimary !== undefined ? { isPrimary: patch.isPrimary } : {}),
      ...(patch.motivation !== undefined ? { motivation: patch.motivation } : {}),
      ...(patch.targetDate !== undefined ? { targetDate: patch.targetDate } : {}),
      ...(patch.weeklyTargetMinutes !== undefined
        ? { weeklyTargetMinutes: patch.weeklyTargetMinutes }
        : {}),
      ...(patch.status !== undefined ? { status: patch.status } : {}),
      ...(patch.deliverables !== undefined ? { deliverables: patch.deliverables } : {}),
      ...(patch.nextAction !== undefined ? { nextAction: patch.nextAction } : {}),
      ...(patch.successCriteria !== undefined ? { successCriteria: patch.successCriteria } : {}),
      updatedAt: nowIso,
    };
    return updatedItem;
  });

  writeLocalPersonalGoals(next);
  return updatedItem;
}

export function deleteLocalPersonalGoal(goalId: string): boolean {
  const existing = readFromStorage<PersonalGoal[]>(STORAGE_KEYS.objectivesState, []);
  const next = existing.filter((goal) => goal.id !== goalId);
  if (next.length === existing.length) {
    return false;
  }
  writeLocalPersonalGoals(next);
  return true;
}

export function recordSessionFeedbackInLocalGoals(
  session: StudySession,
  extra?: SessionFinishExtra,
): void {
  const existing = readFromStorage<PersonalGoal[]>(STORAGE_KEYS.objectivesState, []);
  if (existing.length === 0) return;

  const nowIso = new Date().toISOString();
  let changed = false;
  const next = existing.map((goal) => {
    const matches =
      session.goalId === goal.id ||
      (goal.skillId && session.skillId === goal.skillId) ||
      session.title.toLowerCase().includes(goal.title.toLowerCase());
    if (!matches) return goal;
    changed = true;
    return {
      ...goal,
      nextAction: extra?.nextStep?.trim() || goal.nextAction,
      progressHistory: [
        ...(goal.progressHistory ?? []),
        {
          date: nowIso,
          summary: session.result ?? extra?.actualActivity ?? session.title,
          outcome_status: extra?.outcomeStatus ?? 'completed',
          difficulties: extra?.blockers ?? null,
          deliverable: extra?.deliverableSummary ?? null,
        },
      ],
      updatedAt: nowIso,
    };
  });

  if (changed) {
    writeLocalPersonalGoals(next);
  }
}

export function analyzeLocalConversationalIntake(
  message: string,
  knownAnswers: Record<string, unknown> = {},
): ConversationalIntakeRecap {
  const lowered = message.toLowerCase();
  const candidates: ExtractedObjectiveCandidate[] = [];

  const parsedCurrentLevel =
    typeof knownAnswers.currentLevel === 'number'
      ? knownAnswers.currentLevel
      : typeof knownAnswers.current_level === 'number'
        ? knownAnswers.current_level
        : null;
  const parsedTargetLevel =
    typeof knownAnswers.targetLevel === 'number'
      ? knownAnswers.targetLevel
      : typeof knownAnswers.target_level === 'number'
        ? knownAnswers.target_level
        : null;

  let weeklyMinutes: number | null =
    typeof knownAnswers.weeklyMinutes === 'number'
      ? knownAnswers.weeklyMinutes
      : typeof knownAnswers.available_time_weekly_minutes === 'number'
        ? knownAnswers.available_time_weekly_minutes
        : null;
  if (weeklyMinutes === null) {
    const hoursMatch = lowered.match(/(\d+(?:[.,]\d+)?)\s*(?:h|heures?)(?:\s*par\s*semaine)?/);
    if (hoursMatch) {
      const parsed = Math.round(Number(hoursMatch[1].replace(',', '.')) * 60);
      if (parsed >= 30 && parsed <= 3000) {
        weeklyMinutes = parsed;
      }
    }
  }

  let targetDate: string | null =
    typeof knownAnswers.targetDate === 'string' && knownAnswers.targetDate.trim()
      ? knownAnswers.targetDate.trim()
      : null;
  if (!targetDate) {
    const isoDateMatch = message.match(/\b(20\d{2}-\d{2}-\d{2})\b/);
    if (isoDateMatch) {
      targetDate = `${isoDateMatch[1]}T23:59:00Z`;
    }
  }

  const motivation =
    typeof knownAnswers.motivation === 'string' && knownAnswers.motivation.trim()
      ? knownAnswers.motivation.trim()
      : null;

  const knownPriority =
    typeof knownAnswers.priority === 'string' && knownAnswers.priority.trim()
      ? (knownAnswers.priority.trim() as TaskPriority)
      : null;
  const primaryTitle =
    typeof knownAnswers.primaryTitle === 'string' && knownAnswers.primaryTitle.trim()
      ? knownAnswers.primaryTitle.trim()
      : null;

  for (const item of LEARNING_CATALOG) {
    if (item.keywords.some((kw) => lowered.includes(kw))) {
      const priority: TaskPriority =
        knownPriority ?? (primaryTitle?.toLowerCase() === item.title.toLowerCase() ? 'high' : 'normal');
      candidates.push({
        kind: 'personal_goal',
        category: item.category,
        title: item.title,
        goal: item.goal,
        currentLevel: parsedCurrentLevel,
        targetLevel: parsedTargetLevel,
        priority,
        isPrimary:
          primaryTitle !== null && primaryTitle.toLowerCase() === item.title.toLowerCase(),
        motivation,
        weeklyTargetMinutes: weeklyMinutes,
        targetDate,
        deliverables: [`Exercices et code validé pour ${item.title}`],
        validationConditions: [`Évaluation pratique et preuve produite pour ${item.title}`],
        nextAction: item.nextAction,
      });
    }
  }

  if (
    /\bprojets?\b|\bapplication\b|\bportfolio\b|\bproduit\b|\bconstruire\b/.test(lowered)
  ) {
    candidates.push({
      kind: 'project',
      category: 'personal_project',
      title: 'Projet pratique d’application',
      goal: 'Construire un projet concret réutilisant les compétences visées.',
      currentLevel: parsedCurrentLevel,
      targetLevel: parsedTargetLevel,
      priority: knownPriority ?? 'high',
      isPrimary: false,
      motivation,
      weeklyTargetMinutes: weeklyMinutes,
      targetDate,
      deliverables: ['Prototype fonctionnel avec démonstration et code testable'],
      validationConditions: ['Livrable vérifié sans régression'],
      nextAction: 'Définir le périmètre minimal et le premier livrable testable',
    });
  }

  if (candidates.length === 0) {
    candidates.push({
      kind: 'personal_goal',
      category: 'learning_goal',
      title: message.trim().slice(0, 60),
      goal: 'Structurer et valider progressivement cet objectif personnel.',
      currentLevel: parsedCurrentLevel,
      targetLevel: parsedTargetLevel,
      priority: knownPriority ?? 'normal',
      isPrimary: false,
      motivation,
      weeklyTargetMinutes: weeklyMinutes,
      targetDate,
      deliverables: ['Livrable ou exercice de validation'],
      validationConditions: ['Preuve concrète soumise et évaluée'],
      nextAction: 'Préciser le niveau initial et la première étape',
    });
  }

  const missingFields: string[] = [];
  const progressiveQuestions: string[] = [];

  if (parsedCurrentLevel === null) {
    missingFields.push('niveau_actuel');
    progressiveQuestions.push(
      'Quel est votre niveau actuel sur ces sujets (de 0 débutant à 5 maîtrise), ou à quelle notion souhaitez vous reprendre ?',
    );
  }
  if (parsedTargetLevel === null) {
    missingFields.push('niveau_vise');
  }
  if (!knownPriority && !primaryTitle && candidates.length > 1) {
    missingFields.push('priorite_principale');
    progressiveQuestions.push(
      `Parmi ${candidates.map((c) => c.title).join(', ')}, quel objectif est votre priorité principale pour éviter la dispersion ?`,
    );
  }
  if (weeklyMinutes === null) {
    missingFields.push('temps_disponible');
    progressiveQuestions.push(
      'Combien de temps réel par semaine pouvez vous consacrer à ces objectifs hors cours universitaires ?',
    );
  }
  if (!motivation) {
    missingFields.push('motivation');
  }

  const expectedDeliverables = Array.from(
    new Set(candidates.flatMap((c) => c.deliverables)),
  );
  const validationConditions = Array.from(
    new Set(candidates.flatMap((c) => c.validationConditions)),
  );

  const summaryLines = [
    'Récapitulatif structuré (en attente de votre confirmation, aucune donnée non fournie n’a été inventée) :',
    `Objectifs détectés : ${candidates.map((c) => c.title).join(', ')}`,
    `Niveau actuel : ${parsedCurrentLevel !== null ? `${parsedCurrentLevel}/5` : 'Non renseigné'}`,
    `Niveau visé : ${parsedTargetLevel !== null ? `${parsedTargetLevel}/5` : 'Non renseigné'}`,
    `Priorité : ${primaryTitle ?? knownPriority ?? 'À arbitrer'}`,
    `Motivation : ${motivation ?? 'Non renseignée'}`,
    `Temps disponible hebdomadaire : ${weeklyMinutes !== null ? `${weeklyMinutes} min` : 'Non renseigné'}`,
    `Échéance éventuelle : ${targetDate ? targetDate.slice(0, 10) : 'Aucune échéance précisée'}`,
    `Livrables attendus : ${expectedDeliverables.join(' ; ')}`,
    `Conditions de validation : ${validationConditions.join(' ; ')}`,
  ];

  return {
    objectives: candidates,
    currentLevel: parsedCurrentLevel,
    targetLevel: parsedTargetLevel,
    priority: primaryTitle ?? knownPriority,
    motivation,
    availableTimeWeeklyMinutes: weeklyMinutes,
    targetDate,
    expectedDeliverables,
    validationConditions,
    missingFields,
    progressiveQuestions: progressiveQuestions.slice(0, 3),
    requiresConfirmation: true,
    summaryMarkdown: summaryLines.join('\n'),
  };
}

const DAY_NAMES_FR = [
  'Lundi',
  'Mardi',
  'Mercredi',
  'Jeudi',
  'Vendredi',
  'Samedi',
  'Dimanche',
];

function overlaps(aStart: number, aEnd: number, bStart: number, bEnd: number): boolean {
  return aStart < bEnd && bStart < aEnd;
}

export function generateLocalUnifiedPlan(params: {
  goals: PersonalGoal[];
  projects: Project[];
  tasks: Task[];
  scheduleEvents: ScheduleEvent[];
  sessions: StudySession[];
  weeklyAvailableMinutes?: number;
  primaryPriorityTitle?: string | null;
  targetWeekStart?: string;
  includeDailyRecovery?: boolean;
}): UnifiedPlan {
  const monday = params.targetWeekStart
    ? new Date(`${params.targetWeekStart}T00:00:00`)
    : getMondayOfWeek(new Date());
  const weekStartStr = toLocalDateKey(monday);
  const weekDays = Array.from({ length: 7 }, (_, index) => addDays(monday, index));
  const weekDateKeys = new Set(weekDays.map((d) => toLocalDateKey(d)));

  const activeGoals = params.goals.filter((g) => g.status === 'active');
  const activeProjects = params.projects.filter((p) => p.status === 'active');

  const resolvedPrimary =
    params.primaryPriorityTitle?.trim() ||
    activeGoals.find((g) => g.isPrimary)?.title ||
    activeGoals[0]?.title ||
    activeProjects[0]?.name ||
    null;

  const fixedAcademicSlots: UnifiedPlanSlot[] = [];
  const existingFlexibleWeekEvents: ScheduleEvent[] = [];

  for (const ev of params.scheduleEvents) {
    const localKey = toLocalDateKey(ev.startsAt);
    if (!weekDateKeys.has(localKey)) continue;
    const isAcademic = ev.type === 'course' || ev.source === 'timetable_import';
    if (isAcademic) {
      const dayIdx = (new Date(ev.startsAt).getDay() + 6) % 7;
      const startDate = new Date(ev.startsAt);
      const endDate = new Date(ev.endsAt);
      const durationMinutes = Math.max(
        30,
        Math.round((endDate.getTime() - startDate.getTime()) / 60000),
      );
      fixedAcademicSlots.push({
        sourceCategory: 'academic_obligation',
        isFixed: true,
        title: ev.title,
        dayLabel: DAY_NAMES_FR[dayIdx],
        localDate: localKey,
        localStartTime: startDate.toTimeString().slice(0, 5),
        localEndTime: endDate.toTimeString().slice(0, 5),
        startsAt: ev.startsAt,
        endsAt: ev.endsAt,
        durationMinutes,
        expectedOutcome: `Assister et assimiler les notions du cours ${ev.title}.`,
        linkedGoalId: null,
        linkedProjectId: null,
        linkedSkillId: null,
        linkedPathId: null,
        linkedModuleId: null,
        linkedLessonId: null,
        linkedTaskId: null,
      });
    } else {
      existingFlexibleWeekEvents.push(ev);
    }
  }

  const arbitrages: string[] = [];
  if (resolvedPrimary) {
    arbitrages.push(
      `Priorité principale active : ${resolvedPrimary}. Les autres objectifs restent en rythme secondaire pour éviter la dispersion.`,
    );
  }
  if (activeProjects.length > 3) {
    arbitrages.push(
      `${activeProjects.length} projets actifs détectés (maximum recommandé : 3). Seuls les 3 projets prioritaires sont planifiés cette semaine.`,
    );
  }
  const criticalTasksCount = params.tasks.filter(
    (t) => (t.status === 'todo' || t.status === 'in_progress') && t.priority === 'critical',
  ).length;
  if (criticalTasksCount > 3) {
    arbitrages.push(
      `${criticalTasksCount} tâches critiques ouvertes (limite anti dispersion : 3 simultanées).`,
    );
  }

  const adaptations: UnifiedPlanAdaptationItem[] = [];
  const blockerByTitle = new Map<string, string>();
  for (const session of params.sessions) {
    if (session.status === 'completed' && session.blockers?.trim()) {
      blockerByTitle.set(session.title.toLowerCase(), session.blockers.trim());
    }
  }
  for (const goal of activeGoals) {
    if (goal.isBehindSchedule && goal.delayReason) {
      adaptations.push({
        targetTitle: goal.title,
        targetKind: 'personal_goal',
        cause: goal.delayReason,
        actionTaken: 'Créneau de reprise planifié sans validation automatique par date.',
      });
    }
    for (const [sessTitle, blocker] of blockerByTitle.entries()) {
      if (sessTitle.includes(goal.title.toLowerCase())) {
        adaptations.push({
          targetTitle: goal.title,
          targetKind: 'personal_goal',
          cause: `Difficulté signalée en séance : ${blocker}`,
          actionTaken: `Réorienter la prochaine séance vers un exercice de consolidation sur : ${blocker}.`,
        });
      }
    }
  }

  // Construire la file de blocs flexibles à placer (objectifs personnels + projets actifs <= 3)
  interface QueueItem {
    sourceCategory: 'personal_goal' | 'project' | 'revision';
    title: string;
    durationMinutes: number;
    expectedOutcome: string;
    linkedGoalId: string | null;
    linkedProjectId: string | null;
    linkedSkillId: string | null;
    linkedPathId: string | null;
  }

  const queue: QueueItem[] = [];
  const sortedGoals = [...activeGoals].sort((a, b) => {
    const aIsPrimary =
      a.isPrimary || a.title.toLowerCase() === (resolvedPrimary ?? '').toLowerCase();
    const bIsPrimary =
      b.isPrimary || b.title.toLowerCase() === (resolvedPrimary ?? '').toLowerCase();
    if (aIsPrimary !== bIsPrimary) return aIsPrimary ? -1 : 1;
    return a.priority === 'high' || a.priority === 'critical' ? -1 : 1;
  });

  const secondaryObjectives: string[] = [];
  for (const goal of sortedGoals) {
    const isPrimary =
      goal.isPrimary || goal.title.toLowerCase() === (resolvedPrimary ?? '').toLowerCase();
    if (!isPrimary) {
      secondaryObjectives.push(goal.title);
    }
    const adaptationMatch = adaptations.find((a) => a.targetTitle === goal.title);
    const outcome = adaptationMatch
      ? `${goal.nextAction || goal.goal} (Reprise ciblée : ${adaptationMatch.cause})`
      : `${goal.nextAction || goal.goal} (Livrable : ${goal.deliverables[0] ?? 'exercice ou code validé'})`;
    const slotCount = isPrimary ? 2 : 1;
    for (let i = 0; i < slotCount; i += 1) {
      queue.push({
        sourceCategory: 'personal_goal',
        title: `${goal.title} : ${i === 0 ? 'apprentissage guidé' : 'pratique et évaluation'}`,
        durationMinutes: Math.min(90, Math.max(45, Math.round(goal.weeklyTargetMinutes / slotCount))),
        expectedOutcome: outcome,
        linkedGoalId: goal.id,
        linkedProjectId: null,
        linkedSkillId: goal.skillId,
        linkedPathId: goal.learningPathId,
      });
    }
  }

  for (const project of activeProjects.slice(0, 3)) {
    queue.push({
      sourceCategory: 'project',
      title: `Projet ${project.name}`,
      durationMinutes: Math.min(120, Math.max(60, project.weeklyTargetMinutes ?? 90)),
      expectedOutcome: `Avancer sur la prochaine action : ${project.nextAction}`,
      linkedGoalId: null,
      linkedProjectId: project.id,
      linkedSkillId: null,
      linkedPathId: null,
    });
  }

  const budgetMinutes =
    params.weeklyAvailableMinutes ??
    Math.min(
      900,
      Math.max(
        180,
        activeGoals.reduce((sum, g) => sum + (g.weeklyTargetMinutes || 90), 0) +
          activeProjects.slice(0, 3).length * 90,
      ),
    );

  const candidateWindows = [
    { start: '08:30', minutes: 90 },
    { start: '10:30', minutes: 90 },
    { start: '14:00', minutes: 90 },
    { start: '16:30', minutes: 90 },
    { start: '18:30', minutes: 60 },
  ];

  const flexibleStudySlots: UnifiedPlanSlot[] = [];
  let allocatedMinutes = 0;
  let qIndex = 0;

  for (let dayIdx = 0; dayIdx < 6 && qIndex < queue.length; dayIdx += 1) {
    const dayDate = weekDays[dayIdx];
    const dateKey = toLocalDateKey(dayDate);
    const dayFixed = fixedAcademicSlots.filter((s) => s.localDate === dateKey);

    let dayAdded = 0;
    for (const win of candidateWindows) {
      if (qIndex >= queue.length || dayAdded >= 2) break;
      const item = queue[qIndex];
      const dur = Math.min(item.durationMinutes, win.minutes);
      if (allocatedMinutes + dur > budgetMinutes && flexibleStudySlots.length > 0) {
        qIndex = queue.length;
        break;
      }

      const startIso = localDateAndTimeToIso(dateKey, win.start);
      const startMs = new Date(startIso).getTime();
      const endMs = startMs + dur * 60000;
      const endDate = new Date(endMs);

      const collidesAcademic = dayFixed.some((acad) =>
        overlaps(startMs, endMs, new Date(acad.startsAt).getTime(), new Date(acad.endsAt).getTime()),
      );
      if (collidesAcademic) continue;

      flexibleStudySlots.push({
        sourceCategory: item.sourceCategory,
        isFixed: false,
        title: item.title,
        dayLabel: DAY_NAMES_FR[dayIdx],
        localDate: dateKey,
        localStartTime: win.start,
        localEndTime: endDate.toTimeString().slice(0, 5),
        startsAt: startIso,
        endsAt: endDate.toISOString(),
        durationMinutes: dur,
        expectedOutcome: item.expectedOutcome,
        linkedGoalId: item.linkedGoalId,
        linkedProjectId: item.linkedProjectId,
        linkedSkillId: item.linkedSkillId,
        linkedPathId: item.linkedPathId,
        linkedModuleId: null,
        linkedLessonId: null,
        linkedTaskId: null,
      });

      allocatedMinutes += dur;
      dayAdded += 1;
      qIndex += 1;
    }
  }

  let displacedConflictsCount = 0;
  for (const existingFlex of existingFlexibleWeekEvents) {
    const eStart = new Date(existingFlex.startsAt).getTime();
    const eEnd = new Date(existingFlex.endsAt).getTime();
    const hitsFixedOrNew = [...fixedAcademicSlots, ...flexibleStudySlots].some((s) =>
      overlaps(eStart, eEnd, new Date(s.startsAt).getTime(), new Date(s.endsAt).getTime()),
    );
    if (hitsFixedOrNew) {
      displacedConflictsCount += 1;
    }
  }

  const recoverySlots: UnifiedPlanSlot[] = [];
  if (params.includeDailyRecovery !== false) {
    for (let dayIdx = 0; dayIdx < 7; dayIdx += 1) {
      const dayDate = weekDays[dayIdx];
      const dateKey = toLocalDateKey(dayDate);
      const startIso = localDateAndTimeToIso(dateKey, '21:00');
      const endIso = localDateAndTimeToIso(dateKey, '22:00');
      recoverySlots.push({
        sourceCategory: 'recovery',
        isFixed: false,
        title: 'Récupération et déconnexion',
        dayLabel: DAY_NAMES_FR[dayIdx],
        localDate: dateKey,
        localStartTime: '21:00',
        localEndTime: '22:00',
        startsAt: startIso,
        endsAt: endIso,
        durationMinutes: 60,
        expectedOutcome: 'Préserver la récupération cognitive et le sommeil.',
        linkedGoalId: null,
        linkedProjectId: null,
        linkedSkillId: null,
        linkedPathId: null,
        linkedModuleId: null,
        linkedLessonId: null,
        linkedTaskId: null,
      });
    }
  }

  const dailyBreakdown: Record<string, UnifiedPlanSlot[]> = {};
  for (const dayDate of weekDays) {
    const key = toLocalDateKey(dayDate);
    dailyBreakdown[key] = [
      ...fixedAcademicSlots.filter((s) => s.localDate === key),
      ...flexibleStudySlots.filter((s) => s.localDate === key),
      ...recoverySlots.filter((s) => s.localDate === key),
    ].sort((a, b) => a.startsAt.localeCompare(b.startsAt));
  }

  return {
    weekStart: weekStartStr,
    primaryPriorityTitle: resolvedPrimary,
    secondaryObjectives,
    academicFixedSlots: fixedAcademicSlots,
    flexibleStudySlots,
    recoverySlots,
    dailyBreakdown,
    arbitrages,
    adaptations,
    displacedConflictsCount,
    totalAcademicMinutes: fixedAcademicSlots.reduce((acc, s) => acc + s.durationMinutes, 0),
    totalPersonalGoalMinutes: flexibleStudySlots
      .filter((s) => s.sourceCategory === 'personal_goal')
      .reduce((acc, s) => acc + s.durationMinutes, 0),
    totalProjectMinutes: flexibleStudySlots
      .filter((s) => s.sourceCategory === 'project')
      .reduce((acc, s) => acc + s.durationMinutes, 0),
    requiresValidation: true,
  };
}
