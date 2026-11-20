import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { previewCourseLocal } from '../features/courses/courseLocalEngine';
import { isActiveTaskStatus } from '../features/tasks/taskUtils';
import { validateEvidenceQualityLocal } from '../features/skills/assessmentEngine';
import {
  acceptProposalApi,
  createConversationApi,
  deleteConversationApi,
  ensureAiReportsApi,
  fetchAiMemoryApi,
  fetchAiToolsApi,
  fetchConversationDetailApi,
  fetchConversationsApi,
  fetchProposalsApi,
  fetchReportsApi,
  generateDailyBriefingApi,
  generateWeeklyReviewApi,
  rejectProposalApi,
  sendAiMessageApi,
  updateAiMemoryApi,
  updateProposalApi,
} from '../lib/aiApi';
import { ApiError } from '../lib/api-client';
import { generateId, readFromStorage, STORAGE_KEYS, writeToStorage } from '../lib/storage';
import type {
  AiActionProposal,
  AiContextScope,
  AiConversation,
  AiMemory,
  AiMemoryUpdate,
  AiMessage,
  AiReport,
  AiToolSpec,
  CourseLanguage,
  ProposedActivitySlot,
  ScheduleEventType,
  SkillEvidenceType,
  SkillLevel,
  TaskPriority,
} from '../types/domain';
import { useAuth } from './AuthContext';
import { useCoursesStore } from './CoursesStoreContext';
import { useLearningStore } from './LearningStoreContext';
import { useStudyStore } from './StudyStoreContext';

const LOCAL_USER_ID = 'local-user';

const DEFAULT_LOCAL_TOOLS: AiToolSpec[] = [
  {
    name: 'read_schedule',
    access: 'read',
    label: 'Lire le planning',
    description: 'Consulte uniquement les créneaux de l’utilisateur connecté.',
    requiresConfirmation: false,
    parameterKeys: [],
  },
  {
    name: 'read_tasks',
    access: 'read',
    label: 'Lire les tâches',
    description: 'Consulte les tâches actives, en retard ou au parking.',
    requiresConfirmation: false,
    parameterKeys: [],
  },
  {
    name: 'read_learning_and_skills',
    access: 'read',
    label: 'Lire les parcours, compétences et évaluations',
    description: 'Consulte les parcours, modules, leçons, compétences, preuves et évaluations.',
    requiresConfirmation: false,
    parameterKeys: [],
  },
  {
    name: 'read_projects_and_sessions',
    access: 'read',
    label: 'Lire les projets et séances',
    description: 'Consulte les projets et l’historique des séances.',
    requiresConfirmation: false,
    parameterKeys: [],
  },
  {
    name: 'create_task',
    access: 'proposal',
    label: 'Proposer une tâche',
    description: 'Propose la création d’une nouvelle tâche soumise à validation.',
    requiresConfirmation: true,
    parameterKeys: ['title', 'description', 'priority', 'due_at', 'project_id', 'module_id'],
  },
  {
    name: 'park_task',
    access: 'proposal',
    label: 'Proposer de placer une tâche au parking',
    description: 'Propose de reporter une tâche non prioritaire au parking (Parcours C).',
    requiresConfirmation: true,
    parameterKeys: ['task_id', 'reason'],
  },
  {
    name: 'pause_project',
    access: 'proposal',
    label: 'Proposer de mettre un projet en pause',
    description: 'Propose de mettre un projet actif en pause pour libérer un emplacement actif (max 3).',
    requiresConfirmation: true,
    parameterKeys: ['project_id', 'reason'],
  },
  {
    name: 'create_schedule_event',
    access: 'proposal',
    label: 'Proposer un créneau',
    description: 'Propose un créneau dans le planning avec détection de conflit.',
    requiresConfirmation: true,
    parameterKeys: ['title', 'type', 'starts_at', 'ends_at', 'notes'],
  },
  {
    name: 'add_skill_evidence',
    access: 'proposal',
    label: 'Proposer une preuve de compétence',
    description: 'Propose d’enregistrer une preuve concrète sur une compétence existante.',
    requiresConfirmation: true,
    parameterKeys: ['skill_id', 'type', 'description', 'reference_url', 'result'],
  },
  {
    name: 'propose_skill_assessment',
    access: 'proposal',
    label: 'Proposer une évaluation de compétence',
    description:
      'Propose un exercice ou une évaluation structurée sur une compétence (ne modifie jamais directement le niveau).',
    requiresConfirmation: true,
    parameterKeys: [
      'skill_id',
      'target_level',
      'assessment_type',
      'prompt_title',
      'prompt_instructions',
      'path_id',
      'module_id',
      'lesson_id',
    ],
  },
  {
    name: 'recommend_skill_progression',
    access: 'proposal',
    label: 'Recommander une progression vérifiée',
    description:
      'Recommande la validation officielle d’une évaluation déjà soumise, évaluée positivement et appuyée par des preuves admissibles.',
    requiresConfirmation: true,
    parameterKeys: [
      'skill_id',
      'assessment_id',
      'proposed_level',
      'evidence_ids',
      'decision_reason',
    ],
  },
  {
    name: 'plan_strategic_activity',
    access: 'proposal',
    label: 'Planifier une activité ou un parcours validé',
    description:
      'Analyse la faisabilité stratégique et programme, uniquement après validation explicite, un nouvel apprentissage, projet ou préparation d’examen avec ses créneaux vérifiés sans conflit.',
    requiresConfirmation: true,
    parameterKeys: [
      'activity_title',
      'category',
      'goal',
      'decision',
      'conditions',
      'opportunity_cost_note',
      'create_learning_path',
      'create_project',
      'park_only',
      'frequency_per_week',
      'session_duration_minutes',
      'estimated_weeks',
      'start_date',
      'proposed_slots',
    ],
  },
  {
    name: 'read_courses',
    access: 'read',
    label: 'Lire les cours structurés',
    description:
      'Consulte uniquement les cours structurés, niveaux débloqués, chapitres et ressources officielles de l’utilisateur connecté.',
    requiresConfirmation: false,
    parameterKeys: [],
  },
  {
    name: 'create_course',
    access: 'proposal',
    label: 'Proposer la création d’un cours complet',
    description:
      'Propose un cours progressif multi-niveaux (Niveau 1 débloqué avec chapitres détaillés, exemples, exercices, projet noté et ressources officielles).',
    requiresConfirmation: true,
    parameterKeys: [
      'subject',
      'title',
      'domain',
      'language',
      'total_levels',
      'goal',
      'link_skill',
    ],
  },
  {
    name: 'manage_availability_rule',
    access: 'proposal',
    label: 'Enregistrer une règle de disponibilité ou d’indisponibilité',
    description:
      'Enregistre une indisponibilité personnelle, une disponibilité confirmée ou un temps de récupération.',
    requiresConfirmation: true,
    parameterKeys: ['label', 'rule_type', 'day_of_week', 'start_time', 'end_time'],
  },
  {
    name: 'generate_learning_plan',
    access: 'proposal',
    label: 'Générer un programme d’apprentissage personnalisé',
    description:
      'Analyse toutes vos sources StudyOS et planifie un emploi du temps réaliste sans conflit ni surcharge.',
    requiresConfirmation: true,
    parameterKeys: ['horizon_days', 'focus_subject', 'exam_title', 'weekly_hours_override'],
  },
];

const DEFAULT_LOCAL_MEMORY: AiMemory = {
  userId: LOCAL_USER_ID,
  academicContext: {},
  availabilityPreferences: {},
  learningPreferences: {},
  constraints: [],
  longTermGoals: [],
  recentDecisions: [],
  executionHistory: [],
  weeklyStudyHours: null,
  defaultSessionMinutes: 60,
  autoExecuteSimpleActions: false,
  updatedAt: '2026-11-20T00:00:00Z',
};

export interface AiLocalState {
  conversations: AiConversation[];
  messages: AiMessage[];
  proposals: AiActionProposal[];
  reports: AiReport[];
  aiMemory?: AiMemory;
}

const DEFAULT_AI_STATE: AiLocalState = {
  conversations: [],
  messages: [],
  proposals: [],
  reports: [],
  aiMemory: DEFAULT_LOCAL_MEMORY,
};

function sanitizeAiState(raw: unknown): AiLocalState {
  if (!raw || typeof raw !== 'object') {
    return DEFAULT_AI_STATE;
  }
  const c = raw as Partial<AiLocalState>;
  return {
    conversations: Array.isArray(c.conversations) ? c.conversations : [],
    messages: Array.isArray(c.messages) ? c.messages : [],
    proposals: Array.isArray(c.proposals) ? c.proposals : [],
    reports: Array.isArray(c.reports) ? c.reports : [],
    aiMemory: c.aiMemory ? { ...DEFAULT_LOCAL_MEMORY, ...c.aiMemory } : DEFAULT_LOCAL_MEMORY,
  };
}

function extractTitleFromPrompt(text: string, fallback: string): string {
  const quoted = text.match(/[«"']([^«»"']{2,120})[»"']/);
  if (quoted && quoted[1]) return quoted[1].trim();
  const colon = text.match(/:\s*(.{2,120})$/);
  if (colon && colon[1]) return colon[1].trim();
  return fallback;
}

export interface AiStoreContextValue {
  tools: AiToolSpec[];
  conversations: AiConversation[];
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  messages: AiMessage[];
  proposals: AiActionProposal[];
  reports: AiReport[];
  aiMemory: AiMemory;
  isLoading: boolean;
  error: string | null;
  mutationError: string | null;
  clearMutationError: () => void;
  retry: () => void;
  updateAiMemory: (patch: AiMemoryUpdate) => Promise<boolean>;
  createConversation: (title?: string) => Promise<string | null>;
  deleteConversation: (id: string) => Promise<boolean>;
  sendMessage: (content: string, scopes?: AiContextScope[]) => Promise<boolean>;
  updateProposal: (
    proposalId: string,
    payloadOverrides: Record<string, unknown>,
    recalculateSlots?: boolean,
  ) => Promise<boolean>;
  acceptProposal: (
    proposalId: string,
    payloadOverrides?: Record<string, unknown>,
  ) => Promise<boolean>;
  rejectProposal: (proposalId: string, reason?: string) => Promise<boolean>;
  generateDailyBriefing: () => Promise<boolean>;
  generateWeeklyReview: () => Promise<boolean>;
}

const AiStoreContext = createContext<AiStoreContextValue | null>(null);

export function AiStoreProvider({ children }: { children: ReactNode }) {
  const { session, logout } = useAuth();
  const queryClient = useQueryClient();
  const studyStore = useStudyStore();
  const learningStore = useLearningStore();
  const coursesStore = useCoursesStore();

  const isApiMode = session?.mode === 'api' && Boolean(session.accessToken);
  const accessToken = session?.mode === 'api' ? session.accessToken : '';
  const userIdKey = session?.userId ?? 'anonymous';

  const [localState, setLocalState] = useState<AiLocalState>(() =>
    sanitizeAiState(readFromStorage<AiLocalState>(STORAGE_KEYS.aiState, DEFAULT_AI_STATE)),
  );
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  useEffect(() => {
    if (!isApiMode) {
      writeToStorage(STORAGE_KEYS.aiState, localState);
    }
  }, [isApiMode, localState]);

  const toolsQuery = useQuery({
    queryKey: ['ai-tools', userIdKey],
    queryFn: () => fetchAiToolsApi(accessToken),
    enabled: isApiMode,
  });

  const conversationsQuery = useQuery({
    queryKey: ['ai-conversations', userIdKey],
    queryFn: () => fetchConversationsApi(accessToken),
    enabled: isApiMode,
  });

  const proposalsQuery = useQuery({
    queryKey: ['ai-proposals', userIdKey],
    queryFn: () => fetchProposalsApi(accessToken),
    enabled: isApiMode,
  });

  const reportsQuery = useQuery({
    queryKey: ['ai-reports', userIdKey],
    queryFn: () => fetchReportsApi(accessToken),
    enabled: isApiMode,
  });

  const memoryQuery = useQuery({
    queryKey: ['ai-memory', userIdKey],
    queryFn: () => fetchAiMemoryApi(accessToken),
    enabled: isApiMode,
  });

  const ensuredReportsUserRef = useRef<string | null>(null);
  useEffect(() => {
    if (!isApiMode || !reportsQuery.isSuccess || ensuredReportsUserRef.current === userIdKey) {
      return;
    }
    ensuredReportsUserRef.current = userIdKey;
    void ensureAiReportsApi(accessToken)
      .then((res) => {
        if (res.createdDaily || res.createdWeekly) {
          void queryClient.invalidateQueries({ queryKey: ['ai-reports', userIdKey] });
        }
      })
      .catch(() => {});
  }, [accessToken, isApiMode, queryClient, reportsQuery.isSuccess, userIdKey]);

  const conversations = useMemo(
    () => (isApiMode ? (conversationsQuery.data ?? []) : localState.conversations),
    [isApiMode, conversationsQuery.data, localState.conversations],
  );

  useEffect(() => {
    if (!activeConversationId && conversations.length > 0) {
      setActiveConversationId(conversations[0].id);
    } else if (
      activeConversationId &&
      conversations.length > 0 &&
      !conversations.some((c) => c.id === activeConversationId)
    ) {
      setActiveConversationId(conversations[0].id);
    }
  }, [activeConversationId, conversations]);

  const detailQuery = useQuery({
    queryKey: ['ai-conversation-detail', userIdKey, activeConversationId],
    queryFn: () => fetchConversationDetailApi(accessToken, activeConversationId!),
    enabled: isApiMode && Boolean(activeConversationId),
  });

  const firstQueryError =
    conversationsQuery.error ??
    proposalsQuery.error ??
    reportsQuery.error ??
    detailQuery.error;

  useEffect(() => {
    if (firstQueryError instanceof ApiError && firstQueryError.status === 401) {
      logout('Votre session a expiré. Veuillez vous reconnecter.');
    }
  }, [firstQueryError, logout]);

  const clearMutationError = useCallback(() => setMutationError(null), []);

  const invalidateAllDomainCaches = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['ai-proposals'] }),
      queryClient.invalidateQueries({ queryKey: ['ai-conversation-detail'] }),
      queryClient.invalidateQueries({ queryKey: ['ai-memory'] }),
      queryClient.invalidateQueries({ queryKey: ['tasks'] }),
      queryClient.invalidateQueries({ queryKey: ['schedule'] }),
      queryClient.invalidateQueries({ queryKey: ['sessions'] }),
      queryClient.invalidateQueries({ queryKey: ['learning-overview'] }),
      queryClient.invalidateQueries({ queryKey: ['projects'] }),
      queryClient.invalidateQueries({ queryKey: ['objectives'] }),
      queryClient.invalidateQueries({ queryKey: ['objectives-overview'] }),
      queryClient.invalidateQueries({ queryKey: ['skills'] }),
      queryClient.invalidateQueries({ queryKey: ['skill-evidence'] }),
      queryClient.invalidateQueries({ queryKey: ['skill-assessments'] }),
      queryClient.invalidateQueries({ queryKey: ['courses'] }),
      queryClient.invalidateQueries({ queryKey: ['course-detail'] }),
      queryClient.invalidateQueries({ queryKey: ['availability-rules'] }),
      queryClient.invalidateQueries({ queryKey: ['planning-versions'] }),
      queryClient.invalidateQueries({ queryKey: ['planning-validity'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      queryClient.invalidateQueries({ queryKey: ['profile'] }),
    ]);
  }, [queryClient]);

  const retry = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['ai-conversations'] });
    void queryClient.invalidateQueries({ queryKey: ['ai-proposals'] });
    void queryClient.invalidateQueries({ queryKey: ['ai-reports'] });
    void queryClient.invalidateQueries({ queryKey: ['ai-conversation-detail'] });
    void queryClient.invalidateQueries({ queryKey: ['ai-memory'] });
  }, [queryClient]);

  const aiMemory = useMemo<AiMemory>(() => {
    if (isApiMode) {
      return memoryQuery.data ?? DEFAULT_LOCAL_MEMORY;
    }
    return localState.aiMemory ?? DEFAULT_LOCAL_MEMORY;
  }, [isApiMode, localState.aiMemory, memoryQuery.data]);

  const updateAiMemory = useCallback(
    async (patch: AiMemoryUpdate): Promise<boolean> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          await updateAiMemoryApi(accessToken, patch);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['ai-memory'] }),
            queryClient.invalidateQueries({ queryKey: ['profile'] }),
          ]);
          return true;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de mettre à jour la mémoire IA.',
          );
          return false;
        }
      }
      setLocalState((prev) => {
        const cur = prev.aiMemory ?? DEFAULT_LOCAL_MEMORY;
        return {
          ...prev,
          aiMemory: {
            ...cur,
            ...patch,
            availabilityPreferences:
              patch.availabilityPreferences !== undefined
                ? { ...cur.availabilityPreferences, ...patch.availabilityPreferences }
                : cur.availabilityPreferences,
            updatedAt: new Date().toISOString(),
          },
        };
      });
      return true;
    },
    [accessToken, isApiMode, queryClient],
  );

  const createConversation = useCallback(
    async (title?: string): Promise<string | null> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          const created = await createConversationApi(accessToken, title);
          await queryClient.invalidateQueries({ queryKey: ['ai-conversations'] });
          setActiveConversationId(created.id);
          return created.id;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de créer la conversation.',
          );
          return null;
        }
      }

      const nowIso = new Date().toISOString();
      const created: AiConversation = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        title: title?.trim() || 'Nouvelle conversation',
        createdAt: nowIso,
        updatedAt: nowIso,
      };
      setLocalState((prev) => ({
        ...prev,
        conversations: [created, ...prev.conversations],
      }));
      setActiveConversationId(created.id);
      return created.id;
    },
    [accessToken, isApiMode, queryClient],
  );

  const deleteConversation = useCallback(
    async (id: string): Promise<boolean> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          await deleteConversationApi(accessToken, id);
          await queryClient.invalidateQueries({ queryKey: ['ai-conversations'] });
          await queryClient.invalidateQueries({ queryKey: ['ai-proposals'] });
          if (activeConversationId === id) {
            setActiveConversationId(null);
          }
          return true;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de supprimer la conversation.',
          );
          return false;
        }
      }

      setLocalState((prev) => ({
        ...prev,
        conversations: prev.conversations.filter((c) => c.id !== id),
        messages: prev.messages.filter((m) => m.conversationId !== id),
        proposals: prev.proposals.filter((p) => p.conversationId !== id),
      }));
      if (activeConversationId === id) {
        setActiveConversationId(null);
      }
      return true;
    },
    [accessToken, activeConversationId, isApiMode, queryClient],
  );

  const sendMessage = useCallback(
    async (content: string, scopes: AiContextScope[] = ['auto']): Promise<boolean> => {
      const trimmed = content.trim();
      if (trimmed.length < 2) {
        setMutationError('Le message doit contenir au moins 2 caractères.');
        return false;
      }

      setMutationError(null);
      let convId = activeConversationId;
      if (!convId) {
        convId = await createConversation(trimmed.slice(0, 60));
        if (!convId) return false;
      }

      if (isApiMode) {
        try {
          const turn = await sendAiMessageApi(accessToken, convId, trimmed, scopes, {
            idempotencyKey: generateId(),
            autoExecuteSimple: aiMemory.autoExecuteSimpleActions,
          });
          queryClient.setQueryData<{
            conversation: AiConversation;
            messages: AiMessage[];
            proposals: AiActionProposal[];
          }>(['ai-conversation-detail', userIdKey, convId], (old) => {
            const baseConv: AiConversation = old?.conversation ?? {
              id: convId,
              userId: turn.userMessage.userId,
              title: trimmed.slice(0, 60),
              createdAt: turn.userMessage.createdAt,
              updatedAt: turn.assistantMessage.createdAt,
            };
            const prevMsgs = (old?.messages ?? []).filter(
              (m) => m.id !== turn.userMessage.id && m.id !== turn.assistantMessage.id,
            );
            const prevProps = (old?.proposals ?? []).filter(
              (p) => !turn.proposals.some((np) => np.id === p.id),
            );
            return {
              conversation: baseConv,
              messages: [...prevMsgs, turn.userMessage, turn.assistantMessage],
              proposals: [...turn.proposals, ...prevProps],
            };
          });
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['ai-conversations'] }),
            queryClient.invalidateQueries({ queryKey: ['ai-conversation-detail'] }),
            queryClient.invalidateQueries({ queryKey: ['ai-proposals'] }),
          ]);
          if (turn.autoExecutedCount > 0) {
            await invalidateAllDomainCaches();
          }
          return true;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Erreur lors de l’envoi du message au Copilote.',
          );
          return false;
        }
      }

      // Mode local_demo déterministe (AI-01 à AI-07)
      const nowIso = new Date().toISOString();
      const expiresIso = new Date(Date.now() + 7 * 86_400_000).toISOString();
      const lowered = trimmed.toLowerCase();

      const activeTasks = studyStore.tasks.filter((t) => isActiveTaskStatus(t.status));
      const missingData: string[] = [];
      if (!studyStore.activePriorityTitle) {
        missingData.push('Aucune priorité principale active définie.');
      }
      if (activeTasks.length === 0) {
        missingData.push('Aucune tâche active enregistrée.');
      }

      const generatedProposals: AiActionProposal[] = [];
      const replyLines: string[] = [];

      if (studyStore.profile.aiInstructions) {
        replyLines.push(
          `*(Consignes personnelles prises en compte : ${studyStore.profile.aiInstructions})*`,
        );
      }

      if (
        lowered.includes('crée une tâche') ||
        lowered.includes('créer une tâche') ||
        lowered.includes('ajoute une tâche') ||
        lowered.includes('propose une tâche')
      ) {
        const defaultTitle = studyStore.activePriorityTitle
          ? `Avancer sur ${studyStore.activePriorityTitle}`
          : 'Session d’exercices pratiques';
        const title = extractTitleFromPrompt(trimmed, defaultTitle);
        const priority: TaskPriority =
          lowered.includes('urgent') || lowered.includes('haute') ? 'high' : 'normal';
        generatedProposals.push({
          id: generateId(),
          userId: LOCAL_USER_ID,
          conversationId: convId,
          actionType: 'create_task',
          title: `Créer la tâche « ${title} »`,
          explanation: 'Tâche structurée prête à être ajoutée après votre validation (AI-01).',
          payload: {
            title,
            description: 'Proposée par le Copilote IA.',
            priority,
          },
          status: 'pending',
          expiresAt: expiresIso,
          executionResult: null,
          errorMessage: null,
          createdAt: nowIso,
          resolvedAt: null,
        });
        replyLines.push(
          `J’ai préparé une proposition de tâche **« ${title} »** (priorité \`${priority}\`). Aucune tâche n’est créée tant que vous ne la validez pas.`,
        );
      }

      if (
        lowered.includes('parking') ||
        lowered.includes('surcharge') ||
        lowered.includes('reporter')
      ) {
        if (activeTasks.length > 0) {
          const target = activeTasks[activeTasks.length - 1];
          generatedProposals.push({
            id: generateId(),
            userId: LOCAL_USER_ID,
            conversationId: convId,
            actionType: 'park_task',
            title: `Placer « ${target.title} » au parking`,
            explanation: 'Allège votre journée pour protéger votre priorité principale (Parcours C).',
            payload: {
              task_id: target.id,
              task_title: target.title,
              reason: 'Protection du focus quotidien.',
            },
            status: 'pending',
            expiresAt: expiresIso,
            executionResult: null,
            errorMessage: null,
            createdAt: nowIso,
            resolvedAt: null,
          });
          replyLines.push(
            `Je vous propose de placer **« ${target.title} »** au parking après votre validation.`,
          );
        } else {
          replyLines.push('Aucune tâche active n’est disponible à placer au parking.');
        }
      }

      const isCourseCreationIntent =
        lowered.includes('crée un cours') ||
        lowered.includes('créer un cours') ||
        lowered.includes('nouveau cours') ||
        lowered.includes('cours complet') ||
        lowered.includes('génère un cours') ||
        lowered.includes('générer un cours') ||
        lowered.includes('apprendre le langage');

      if (isCourseCreationIntent) {
        const subjMatch = trimmed.match(
          /(?:cours(?:\s+complet)?\s+(?:pour\s+(?:apprendre|maîtriser)|sur|de|en|pour)|(?:pour\s+)?(?:apprendre|maîtriser))\s+(?:le\s+langage\s+|la\s+programmation\s+(?:en\s+)?|le\s+|la\s+|l['’])?([A-Za-zÀ-ÿ0-9_+#.-]{2,40})/i,
        );
        const extractedSubject = extractTitleFromPrompt(
          trimmed,
          subjMatch?.[1]?.trim() || 'Python',
        );
        const preview = previewCourseLocal({
          subject: extractedSubject,
          language: 'fr',
          totalLevels: 3,
        });
        const chapterList = preview.firstLevelLessons
          .map((item) => `- **Chapitre ${item.position}** : ${item.title}`)
          .join('\n');

        generatedProposals.push({
          id: generateId(),
          userId: LOCAL_USER_ID,
          conversationId: convId,
          actionType: 'create_course',
          title: `Créer le cours « ${preview.title} »`,
          explanation:
            'Génère le Niveau 1 complet (4 chapitres progressifs, exercices corrigés, projet à rendre et ressources officielles). Les niveaux suivants restent verrouillés jusqu’à validation.',
          payload: {
            subject: preview.subject,
            title: preview.title,
            domain: preview.domain,
            language: 'fr',
            total_levels: preview.totalLevels,
            goal: preview.description,
            link_skill: true,
          },
          status: 'pending',
          expiresAt: expiresIso,
          executionResult: null,
          errorMessage: null,
          createdAt: nowIso,
          resolvedAt: null,
        });

        replyLines.push(
          `J’ai préparé la structure du cours **« ${preview.title} »** (${preview.totalLevels} niveaux progressifs) :\n\n` +
            `### Aperçu du Niveau 1 (débloqué à la création)\n${chapterList}\n` +
            `- **Projet du niveau 1** : ${preview.firstLevelProjectTitle}\n` +
            `- **Ressources curées** : ${preview.firstLevelResources.length} documentations & vidéos\n\n` +
            'Aucun cours n’est enregistré tant que vous ne validez pas cette proposition.',
        );
      }

      const isDirectCmd =
        isCourseCreationIntent ||
        lowered.includes('crée une tâche') ||
        lowered.includes('créer une tâche') ||
        lowered.includes('ajoute une tâche') ||
        lowered.includes('propose une tâche') ||
        lowered.includes('preuve') ||
        ((lowered.includes('mets') || lowered.includes('mettre')) && lowered.includes('parking'));

      const isStrategicPlanningIntent =
        !isDirectCmd &&
        (lowered.includes('apprendre') ||
          lowered.includes('formation') ||
          lowered.includes('nouveau projet') ||
          lowered.includes('lancer un projet') ||
          lowered.includes('développer une idée') ||
          lowered.includes('préparer un examen') ||
          lowered.includes("préparer l'examen") ||
          lowered.includes('approfondir') ||
          lowered.includes('nouvelle idée') ||
          lowered.includes('ajouter une activité'));

      if (isStrategicPlanningIntent) {
        const pad2 = (n: number) => String(n).padStart(2, '0');
        const dayNamesFr = [
          'Dimanche',
          'Lundi',
          'Mardi',
          'Mercredi',
          'Jeudi',
          'Vendredi',
          'Samedi',
        ];
        const cleanMatch = trimmed.match(
          /(?:apprendre\s+(?:le\s+développement\s+avec\s+|à\s+|le\s+|la\s+|l['’])?|formation\s+(?:en\s+|sur\s+|de\s+)?|projet\s+(?:de\s+|sur\s+)?|approfondir\s+)([^.\n?!,]{2,80})/i,
        );
        const activityTitle = cleanMatch?.[1]?.trim() || extractTitleFromPrompt(trimmed, 'Nouvel apprentissage');
        const category = lowered.includes('projet') || lowered.includes('idée')
          ? 'project'
          : lowered.includes('examen')
            ? 'exam_prep'
            : 'learning';

        const activePriority = studyStore.activePriorityTitle?.trim() || null;
        const normalizeWords = (txt: string) =>
          txt
            .toLowerCase()
            .split(/[^a-zà-öø-ÿ0-9]+/)
            .filter((w) => w.length >= 4 && !['avec', 'pour', 'dans', 'voudrais', 'apprendre'].includes(w));

        const prioWords = activePriority ? normalizeWords(activePriority) : [];
        const actWords = normalizeWords(activityTitle);
        const isDispersion =
          Boolean(activePriority) &&
          category !== 'exam_prep' &&
          prioWords.length > 0 &&
          actWords.length > 0 &&
          !prioWords.some((w) => actWords.includes(w));

        if (isDispersion) {
          replyLines.push(
            'STOP — DISPERSION DÉTECTÉE.\n\n' +
              'Tu as déjà une priorité en cours. Ajouter cette activité maintenant risque de ralentir ton objectif principal. Je te recommande de la placer dans ton Parking jusqu’à la prochaine réévaluation.',
          );
          generatedProposals.push({
            id: generateId(),
            userId: LOCAL_USER_ID,
            conversationId: convId,
            actionType: 'plan_strategic_activity',
            title: `Placer « ${activityTitle} » dans le Parking des idées`,
            explanation: `Protège votre priorité active (« ${activePriority} ») contre la dispersion.`,
            payload: {
              activity_title: activityTitle,
              category,
              goal: `Explorer ${activityTitle} après achèvement de la priorité en cours.`,
              decision: 'NOT_RECOMMENDED',
              conditions: [`Avancer sur « ${activePriority} » avant d’ouvrir ce chantier.`],
              opportunity_cost_note: `Risque de dispersion par rapport à « ${activePriority} ».`,
              create_learning_path: false,
              create_project: false,
              park_only: true,
              frequency_per_week: 0,
              session_duration_minutes: 60,
              estimated_weeks: 3,
              start_date: null,
              proposed_slots: [],
            },
            status: 'pending',
            expiresAt: expiresIso,
            executionResult: null,
            errorMessage: null,
            createdAt: nowIso,
            resolvedAt: null,
          });
        } else {
          // Recherche jusqu'à 2 créneaux réels disponibles sur les 7 prochains jours hors cours & conflits
          const candidateSlots: ProposedActivitySlot[] = [];
          const nowDate = new Date();
          for (let offset = 1; offset <= 7 && candidateSlots.length < 2; offset += 1) {
            const d = new Date(
              nowDate.getFullYear(),
              nowDate.getMonth(),
              nowDate.getDate() + offset,
              0,
              0,
              0,
              0,
            );
            const dateStr = `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
            for (const h of [16, 10, 14, 15, 9]) {
              const sDt = new Date(d.getFullYear(), d.getMonth(), d.getDate(), h, 0, 0, 0);
              const eDt = new Date(sDt.getTime() + 60 * 60_000);
              const conflict = studyStore.scheduleEvents.some((ev) => {
                const evStart = new Date(ev.startsAt).getTime() - 15 * 60_000;
                const evEnd = new Date(ev.endsAt).getTime() + 15 * 60_000;
                return sDt.getTime() < evEnd && evStart < eDt.getTime();
              });
              if (!conflict) {
                candidateSlots.push({
                  day_label: dayNamesFr[sDt.getDay()],
                  local_date: dateStr,
                  local_start_time: `${pad2(h)}:00`,
                  local_end_time: `${pad2(h + 1)}:00`,
                  starts_at: sDt.toISOString(),
                  ends_at: eDt.toISOString(),
                  duration_minutes: 60,
                });
                break;
              }
            }
          }

          if (candidateSlots.length === 0) {
            replyLines.push(
              '### Analyse stratégique & Décision : **C. NON RECOMMANDÉE POUR LE MOMENT**\n' +
                'Aucun créneau disponible n’a été trouvé sur la semaine sans conflit.',
            );
            generatedProposals.push({
              id: generateId(),
              userId: LOCAL_USER_ID,
              conversationId: convId,
              actionType: 'plan_strategic_activity',
              title: `Placer « ${activityTitle} » au Parking`,
              explanation: 'Calendrier saturé sur la période.',
              payload: {
                activity_title: activityTitle,
                category,
                goal: `Maîtriser les bases de ${activityTitle} en 3 semaines.`,
                decision: 'NOT_RECOMMENDED',
                conditions: ['Libérer un créneau libre avant de démarrer.'],
                create_learning_path: false,
                create_project: false,
                park_only: true,
                frequency_per_week: 0,
                session_duration_minutes: 60,
                estimated_weeks: 3,
                proposed_slots: [],
              },
              status: 'pending',
              expiresAt: expiresIso,
              executionResult: null,
              errorMessage: null,
              createdAt: nowIso,
              resolvedAt: null,
            });
          } else {
            const goalText = `Maîtriser les fondamentaux de ${activityTitle} et réaliser un projet pratique en 3 semaines.`;
            const slotsMarkdown = candidateSlots
              .map((s) => `- ${s.day_label} (${s.local_date}) : ${s.local_start_time} à ${s.local_end_time}`)
              .join('\n');
            replyLines.push(
              `J’ai analysé ton emploi du temps. Voici ma proposition pour **${activityTitle}** :\n\n` +
                `${slotsMarkdown}\n\n` +
                `**Objectif** : ${goalText}\n\n` +
                "Cette proposition ne sera pas enregistrée tant que tu ne l'auras pas validée.",
            );
            generatedProposals.push({
              id: generateId(),
              userId: LOCAL_USER_ID,
              conversationId: convId,
              actionType: 'plan_strategic_activity',
              title: `Programmer « ${activityTitle} » (${candidateSlots.length} séance(s)/sem.)`,
              explanation: 'Créneaux vérifiés sur tes disponibilités réelles sans conflit avec tes cours.',
              payload: {
                activity_title: activityTitle,
                category,
                goal: goalText,
                decision: 'ACCEPTABLE',
                conditions: [],
                opportunity_cost_note: 'Créneaux positionnés sur vos périodes libres.',
                create_learning_path: category !== 'project',
                create_project: category === 'project',
                park_only: false,
                frequency_per_week: candidateSlots.length,
                session_duration_minutes: 60,
                estimated_weeks: 3,
                start_date: candidateSlots[0].local_date,
                proposed_slots: candidateSlots,
              },
              status: 'pending',
              expiresAt: expiresIso,
              executionResult: null,
              errorMessage: null,
              createdAt: nowIso,
              resolvedAt: null,
            });
          }
        }
      }

      if (
        !isCourseCreationIntent &&
        !isStrategicPlanningIntent &&
        (lowered.includes('créneau') ||
          lowered.includes('planifie') ||
          lowered.includes('programme') ||
          lowered.includes('emploi du temps') ||
          lowered.includes('demain') ||
          lowered.includes('journée') ||
          lowered.includes('organise'))
      ) {
        const isTomorrow = lowered.includes('demain') || lowered.includes('lendemain');
        const baseDate = new Date();
        if (isTomorrow) {
          baseDate.setDate(baseDate.getDate() + 1);
        }
        const targetYear = baseDate.getFullYear();
        const targetMonth = baseDate.getMonth();
        const targetDay = baseDate.getDate();

        const dayEvents = studyStore.scheduleEvents
          .filter((ev) => {
            const d = new Date(ev.startsAt);
            return (
              d.getFullYear() === targetYear &&
              d.getMonth() === targetMonth &&
              d.getDate() === targetDay
            );
          })
          .sort((a, b) => new Date(a.startsAt).getTime() - new Date(b.startsAt).getTime());

        const uniCourses = dayEvents.filter(
          (ev) => ev.type === 'course' || ev.source === 'timetable_import',
        );

        // Recherche d'un créneau libre d'1h hors cours universitaires et hors pause déjeuner (12h30-13h30)
        const candidateHours = [9, 10, 14, 15, 16, 11, 17, 20];
        let chosenStart = new Date(targetYear, targetMonth, targetDay, 14, 0, 0, 0);
        let chosenEnd = new Date(targetYear, targetMonth, targetDay, 15, 0, 0, 0);

        for (const h of candidateHours) {
          const cStart = new Date(targetYear, targetMonth, targetDay, h, 0, 0, 0);
          const cEnd = new Date(cStart.getTime() + 60 * 60_000);
          const overlaps = dayEvents.some((ev) => {
            const evStart = new Date(ev.startsAt).getTime() - 15 * 60_000;
            const evEnd = new Date(ev.endsAt).getTime() + 15 * 60_000;
            return cStart.getTime() < evEnd && evStart < cEnd.getTime();
          });
          if (!overlaps) {
            chosenStart = cStart;
            chosenEnd = cEnd;
            break;
          }
        }

        const slotTitle = extractTitleFromPrompt(
          trimmed,
          uniCourses.length > 0
            ? `Révision & exercices : ${uniCourses[0].title}`
            : `Bloc focus : ${studyStore.activePriorityTitle ?? 'Étude approfondie'}`,
        );

        const pad2 = (n: number) => String(n).padStart(2, '0');
        const slotRangeLabel = `${pad2(chosenStart.getHours())}:${pad2(chosenStart.getMinutes())} à ${pad2(chosenEnd.getHours())}:${pad2(chosenEnd.getMinutes())}`;

        if (uniCourses.length > 0) {
          const courseLabels = uniCourses.map((c) => {
            const cs = new Date(c.startsAt);
            const ce = new Date(c.endsAt);
            return `**${c.title}** (${pad2(cs.getHours())}:${pad2(cs.getMinutes())} à ${pad2(ce.getHours())}:${pad2(ce.getMinutes())})`;
          });
          replyLines.push(
            `- **Cours universitaires verrouillés (${uniCourses.length})** : ${courseLabels.join(', ')}`,
          );
        }

        generatedProposals.push({
          id: generateId(),
          userId: LOCAL_USER_ID,
          conversationId: convId,
          actionType: 'create_schedule_event',
          title: `Planifier « ${slotTitle} » (${slotRangeLabel})`,
          explanation:
            'Créneau positionné sur une disponibilité réelle en dehors de vos cours universitaires, avec préservation des pauses.',
          payload: {
            title: slotTitle,
            type: 'learning',
            starts_at: chosenStart.toISOString(),
            ends_at: chosenEnd.toISOString(),
            notes: 'Créneau sans conflit proposé par le Copilote IA.',
            has_conflict: false,
            conflicting_titles: [],
          },
          status: 'pending',
          expiresAt: expiresIso,
          executionResult: null,
          errorMessage: null,
          createdAt: nowIso,
          resolvedAt: null,
        });
        replyLines.push(
          `J’ai préparé une proposition de créneau **« ${slotTitle} »** sur le créneau libre **${slotRangeLabel}** (aucun chevauchement avec vos cours universitaires).`,
        );
      }

      if (lowered.includes('preuve') && learningStore.skills.length > 0) {
        const skill = learningStore.skills[0];
        const desc = extractTitleFromPrompt(trimmed, '');
        const quality = validateEvidenceQualityLocal(desc);
        if (desc && quality.admissible) {
          generatedProposals.push({
            id: generateId(),
            userId: LOCAL_USER_ID,
            conversationId: convId,
            actionType: 'add_skill_evidence',
            title: `Ajouter une preuve sur « ${skill.name} »`,
            explanation: 'Enregistre la preuve concrète décrite par l’utilisateur.',
            payload: {
              skill_id: skill.id,
              skill_name: skill.name,
              type: 'exercise',
              description: desc,
            },
            status: 'pending',
            expiresAt: expiresIso,
            executionResult: null,
            errorMessage: null,
            createdAt: nowIso,
            resolvedAt: null,
          });
          replyLines.push(`Proposition de preuve prête pour **${skill.name}**.`);
        } else {
          replyLines.push(
            `Conformément au verrou pédagogique, je ne peux pas fabriquer une preuve pour **${skill.name}**. Décrivez entre guillemets la production concrète réalisée (exercice résolu, code écrit, test exécuté) ou lancez une évaluation.`,
          );
        }
      } else if (
        !isCourseCreationIntent &&
        (lowered.includes('niveau') ||
          lowered.includes('évaluer') ||
          lowered.includes('évaluation') ||
          lowered.includes('tester') ||
          lowered.includes('réviser') ||
          lowered.includes('renforcer')) &&
        learningStore.skills.length > 0
      ) {
        const skill = learningStore.skills[0];
        const latestEvaluated = learningStore.assessments
          .filter((a) => a.skillId === skill.id && a.status === 'evaluated' && a.passed === true)
          .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())[0];

        if (latestEvaluated && latestEvaluated.evidenceIds.length > 0) {
          const propLvl = latestEvaluated.proposedLevel ?? Math.min(5, skill.currentLevel + 1);
          generatedProposals.push({
            id: generateId(),
            userId: LOCAL_USER_ID,
            conversationId: convId,
            actionType: 'recommend_skill_progression',
            title: `Valider la progression de « ${skill.name} » au niveau ${propLvl}/5`,
            explanation:
              'L’évaluation a été soumise, corrigée positivement et appuyée par une preuve vérifiée.',
            payload: {
              skill_id: skill.id,
              skill_name: skill.name,
              assessment_id: latestEvaluated.id,
              previous_level: skill.currentLevel,
              proposed_level: propLvl,
              evidence_ids: latestEvaluated.evidenceIds,
              decision_reason: `Validation recommandée après score de ${latestEvaluated.score}/100.`,
            },
            status: 'pending',
            expiresAt: expiresIso,
            executionResult: null,
            errorMessage: null,
            createdAt: nowIso,
            resolvedAt: null,
          });
          replyLines.push(
            `L’évaluation de **${skill.name}** est réussie (${latestEvaluated.score}/100). Je vous recommande de valider le passage au niveau **${propLvl}/5**.`,
          );
        } else {
          const nextLvl = Math.min(5, Math.max(1, skill.currentLevel + 1));
          generatedProposals.push({
            id: generateId(),
            userId: LOCAL_USER_ID,
            conversationId: convId,
            actionType: 'propose_skill_assessment',
            title: `Évaluer « ${skill.name} » (objectif niveau ${nextLvl}/5)`,
            explanation:
              'Le niveau d’une compétence ne peut évoluer qu’après une évaluation soumise, corrigée et appuyée par une preuve.',
            payload: {
              skill_id: skill.id,
              skill_name: skill.name,
              current_level: skill.currentLevel,
              target_level: nextLvl,
              assessment_type: 'practical_exercise',
            },
            status: 'pending',
            expiresAt: expiresIso,
            executionResult: null,
            errorMessage: null,
            createdAt: nowIso,
            resolvedAt: null,
          });
          replyLines.push(
            `Le niveau de **${skill.name}** (${skill.currentLevel}/5) est protégé par le verrou pédagogique. Je vous propose de lancer une évaluation structurée vers le niveau **${nextLvl}/5**.`,
          );
        }
      }

      if (replyLines.length === 0) {
        replyLines.push('### Synthèse & recommandations du Copilote');
        replyLines.push(
          `- **Priorité principale** : ${studyStore.activePriorityTitle ?? 'Aucune priorité définie'}`,
        );
        replyLines.push(`- **Tâches actives** : ${activeTasks.length}`);
        replyLines.push(`- **Projets actifs** : ${learningStore.projects.filter((p) => p.status === 'active').length}`);
        replyLines.push(
          '\n*Vous pouvez me demander : « crée une tâche : ... », « mets une tâche au parking » ou « planifie un créneau ».*',
        );
      }

      const autoExecSimple =
        aiMemory.autoExecuteSimpleActions &&
        generatedProposals.length === 1 &&
        generatedProposals[0].actionType === 'create_task';

      if (autoExecSimple) {
        const p0 = generatedProposals[0];
        const title = String(p0.payload.title ?? 'Nouvelle tâche').trim();
        const priority = (p0.payload.priority as TaskPriority) || 'normal';
        await studyStore.createTask(
          {
            title,
            description: String(p0.payload.description ?? ''),
            priority,
            status: 'todo',
            dueDate: '',
            projectId: '',
            moduleId: '',
          },
          { source: 'ai_proposal', proposalId: p0.id },
        );
        generatedProposals[0] = {
          ...p0,
          status: 'executed',
          executionResult: { entity: 'task', title, source: 'ai_proposal' },
          resolvedAt: nowIso,
        };
        replyLines.push(`Action exécutée directement : **${p0.title}**.`);
      }

      const userMessage: AiMessage = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        conversationId: convId,
        role: 'user',
        content: trimmed,
        metadata: { includedScopes: scopes, autoExecutedCount: autoExecSimple ? 1 : 0 },
        createdAt: nowIso,
      };

      const assistantMessage: AiMessage = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        conversationId: convId,
        role: 'assistant',
        content: replyLines.join('\n\n'),
        metadata: {
          provider: 'local',
          model: 'local-coach-v1',
          isEstimate: missingData.length > 0,
          missingData,
          includedScopes: scopes,
          proposalIds: generatedProposals.map((p) => p.id),
          autoExecutedCount: autoExecSimple ? 1 : 0,
        },
        createdAt: nowIso,
      };

      setLocalState((prev) => ({
        ...prev,
        conversations: prev.conversations.map((c) =>
          c.id === convId
            ? {
                ...c,
                title: c.title === 'Nouvelle conversation' ? trimmed.slice(0, 60) : c.title,
                updatedAt: nowIso,
              }
            : c,
        ),
        messages: [...prev.messages, userMessage, assistantMessage],
        proposals: [...generatedProposals, ...prev.proposals],
      }));
      return true;
    },
    [
      accessToken,
      activeConversationId,
      aiMemory.autoExecuteSimpleActions,
      createConversation,
      invalidateAllDomainCaches,
      isApiMode,
      learningStore.assessments,
      learningStore.projects,
      learningStore.skills,
      queryClient,
      studyStore,
    ],
  );

  const updateProposal = useCallback(
    async (
      proposalId: string,
      payloadOverrides: Record<string, unknown>,
      recalculateSlots = false,
    ): Promise<boolean> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          await updateProposalApi(accessToken, proposalId, payloadOverrides, recalculateSlots);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['ai-proposals'] }),
            queryClient.invalidateQueries({ queryKey: ['ai-conversation-detail'] }),
          ]);
          return true;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de modifier la proposition.',
          );
          return false;
        }
      }

      const target = localState.proposals.find((p) => p.id === proposalId);
      if (!target || target.status !== 'pending') {
        setMutationError('Seule une proposition en attente peut être modifiée.');
        return false;
      }
      const nextPayload = { ...target.payload, ...payloadOverrides };
      const nextTitle =
        typeof nextPayload.activity_title === 'string' && target.actionType === 'plan_strategic_activity'
          ? nextPayload.park_only
            ? `Placer « ${nextPayload.activity_title} » dans le Parking des idées`
            : `Programmer « ${nextPayload.activity_title} » (${Array.isArray(nextPayload.proposed_slots) ? nextPayload.proposed_slots.length : 0} séance(s)/sem.)`
          : target.title;

      setLocalState((prev) => ({
        ...prev,
        proposals: prev.proposals.map((p) =>
          p.id !== proposalId ? p : { ...p, title: nextTitle, payload: nextPayload },
        ),
      }));
      return true;
    },
    [accessToken, isApiMode, localState.proposals, queryClient],
  );

  const acceptProposal = useCallback(
    async (
      proposalId: string,
      payloadOverrides?: Record<string, unknown>,
    ): Promise<boolean> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          await acceptProposalApi(accessToken, proposalId, payloadOverrides, generateId());
          await invalidateAllDomainCaches();
          return true;
        } catch (err) {
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['ai-proposals'] }),
            queryClient.invalidateQueries({ queryKey: ['ai-conversation-detail'] }),
          ]);
          setMutationError(
            err instanceof Error ? err.message : 'Impossible d’exécuter la proposition.',
          );
          return false;
        }
      }

      const target = localState.proposals.find((p) => p.id === proposalId);
      if (!target || target.status !== 'pending') {
        setMutationError('Seule une proposition en attente peut être validée.');
        return false;
      }

      const merged = { ...target.payload, ...(payloadOverrides ?? {}) };
      const nowIso = new Date().toISOString();
      let execResult: Record<string, unknown> = {};

      if (target.actionType === 'create_task') {
        const title = String(merged.title ?? '').trim();
        if (title.length < 2) {
          setMutationError('Le titre de la tâche doit contenir au moins 2 caractères.');
          return false;
        }
        const priority = (merged.priority as TaskPriority) || 'normal';
        await studyStore.createTask(
          {
            title,
            description: String(merged.description ?? ''),
            priority,
            status: 'todo',
            dueDate: '',
            projectId: '',
            moduleId: '',
          },
          { source: 'ai_proposal', proposalId: target.id },
        );
        execResult = { entity: 'task', title, source: 'ai_proposal' };
      } else if (target.actionType === 'park_task') {
        const taskId = String(merged.task_id ?? '');
        await studyStore.setTaskStatus(taskId, 'parked');
        execResult = { entity: 'task', task_id: taskId, status: 'parked' };
      } else if (target.actionType === 'pause_project') {
        const projectId = String(merged.project_id ?? '');
        await learningStore.updateProject(projectId, { status: 'blocked' });
        execResult = { entity: 'project', project_id: projectId, status: 'blocked' };
      } else if (target.actionType === 'create_schedule_event') {
        const start = new Date(String(merged.starts_at ?? nowIso));
        const end = new Date(String(merged.ends_at ?? nowIso));
        const dateStr = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, '0')}-${String(start.getDate()).padStart(2, '0')}`;
        const startTime = `${String(start.getHours()).padStart(2, '0')}:${String(start.getMinutes()).padStart(2, '0')}`;
        const endTime = `${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}`;
        await studyStore.createScheduleEvent({
          title: String(merged.title ?? 'Créneau IA'),
          type: (merged.type as ScheduleEventType) || 'learning',
          date: dateStr,
          startTime,
          endTime,
          notes: String(merged.notes ?? ''),
        });
        execResult = { entity: 'schedule_event', title: merged.title };
      } else if (target.actionType === 'add_skill_evidence') {
        const skillId = String(merged.skill_id ?? '');
        const ok = await learningStore.addEvidence(skillId, {
          type: (merged.type as SkillEvidenceType) || 'exercise',
          description: String(merged.description ?? ''),
          referenceUrl: String(merged.reference_url ?? ''),
          result: String(merged.result ?? ''),
        });
        if (!ok) return false;
        execResult = { entity: 'skill_evidence', skill_id: skillId };
      } else if (target.actionType === 'propose_skill_assessment') {
        const skillId = String(merged.skill_id ?? '');
        const targetLvl = Number(merged.target_level ?? 1) as SkillLevel;
        const created = await learningStore.createAssessment(skillId, {
          targetLevel: targetLvl,
        });
        if (!created) return false;
        execResult = {
          entity: 'skill_assessment',
          assessment_id: created.id,
          skill_id: skillId,
          status: created.status,
          target_level: created.targetLevel,
        };
      } else if (target.actionType === 'recommend_skill_progression') {
        const skillId = String(merged.skill_id ?? '');
        const assessmentId = String(merged.assessment_id ?? '');
        const reason =
          typeof merged.decision_reason === 'string' ? merged.decision_reason : undefined;
        const ok = await learningStore.validateAssessment(skillId, assessmentId, reason);
        if (!ok) return false;
        execResult = {
          entity: 'skill_progression',
          skill_id: skillId,
          assessment_id: assessmentId,
          proposed_level: merged.proposed_level,
        };
      } else if (target.actionType === 'plan_strategic_activity') {
        const activityTitle = String(merged.activity_title ?? '').trim() || 'Nouvelle activité';
        const goal = String(merged.goal ?? '').trim() || `Objectif : ${activityTitle}`;
        const parkOnly = Boolean(merged.park_only);

        if (parkOnly) {
          await studyStore.createTask(
            {
              title: activityTitle,
              description: `Idée placée au Parking par le Copilote IA. Objectif : ${goal}`,
              priority: 'low',
              status: 'parked',
              dueDate: '',
              projectId: '',
              moduleId: '',
            },
            { source: 'ai_proposal', proposalId: target.id },
          );
          execResult = {
            entity: 'parked_idea',
            activity_title: activityTitle,
            created_events_count: 0,
          };
        } else {
          const slots = Array.isArray(merged.proposed_slots)
            ? (merged.proposed_slots as ProposedActivitySlot[])
            : [];
          if (slots.length === 0) {
            setMutationError('Au moins un créneau disponible est requis pour programmer cette activité.');
            return false;
          }
          // Re-vérifier les conflits avec le calendrier actuel avant programmation
          for (const slot of slots) {
            const sMs = new Date(slot.starts_at).getTime();
            const eMs = new Date(slot.ends_at).getTime();
            const conflict = studyStore.scheduleEvents.find(
              (ev) => sMs < new Date(ev.endsAt).getTime() && new Date(ev.startsAt).getTime() < eMs,
            );
            if (conflict) {
              setMutationError(
                `Conflit détecté avec « ${conflict.title} » sur le créneau ${slot.day_label} ${slot.local_start_time} à ${slot.local_end_time}. Modifiez la proposition avant de valider.`,
              );
              return false;
            }
          }

          if (merged.create_project) {
            await learningStore.createProject({
              name: activityTitle,
              description: `Projet planifié via le Copilote IA`,
              goal,
              status: 'active',
              priority: 'normal',
              nextAction: `Démarrer la première séance : ${activityTitle}`,
              deliverables: [],
              targetDate: '',
            });
          } else if (merged.create_learning_path !== false) {
            await learningStore.createPath({
              title: activityTitle,
              description: `Parcours planifié avec le Copilote IA.`,
              goal,
              status: 'active',
            });
          }

          await studyStore.createTask(
            {
              title: `Objectif : ${activityTitle}`,
              description: goal,
              priority: 'normal',
              status: 'todo',
              dueDate: '',
              projectId: '',
              moduleId: '',
            },
            { source: 'ai_proposal', proposalId: target.id },
          );

          const eventType: ScheduleEventType = merged.create_project ? 'project' : 'learning';
          for (const slot of slots) {
            await studyStore.createScheduleEvent({
              title: activityTitle,
              type: eventType,
              date: slot.local_date,
              startTime: slot.local_start_time,
              endTime: slot.local_end_time,
              notes: `Objectif : ${goal}`,
            });
          }

          execResult = {
            entity: 'strategic_activity',
            activity_title: activityTitle,
            created_events_count: slots.length,
          };
        }
      } else if (target.actionType === 'create_course') {
        const subject = String(merged.subject ?? '').trim();
        if (subject.length < 2) {
          setMutationError('Le sujet du cours doit contenir au moins 2 caractères.');
          return false;
        }
        const totalLevelsRaw = Number(merged.total_levels ?? 3);
        const totalLevels = Number.isFinite(totalLevelsRaw)
          ? Math.min(5, Math.max(2, totalLevelsRaw))
          : 3;
        const lang = (
          merged.language === 'fr' || merged.language === 'en' || merged.language === 'bilingual'
            ? merged.language
            : 'fr'
        ) as CourseLanguage;
        const created = await coursesStore.createCourse({
          subject,
          title: typeof merged.title === 'string' ? merged.title : undefined,
          domain: typeof merged.domain === 'string' ? merged.domain : undefined,
          language: lang,
          totalLevels,
          goal: typeof merged.goal === 'string' ? merged.goal : undefined,
          linkSkill: merged.link_skill !== false,
        });
        if (!created) return false;
        execResult = {
          entity: 'course',
          course_id: created.id,
          title: created.title,
          subject: created.subject,
          current_level: created.currentLevel,
          total_levels: created.totalLevels,
          confirmation: `Cours « ${created.title} » créé au Niveau 1/${created.totalLevels}.`,
        };
      } else {
        setMutationError(
          'Action refusée : aucune modification directe de niveau n’est autorisée sans évaluation.',
        );
        return false;
      }

      setLocalState((prev) => ({
        ...prev,
        proposals: prev.proposals.map((p) =>
          p.id !== proposalId
            ? p
            : {
                ...p,
                payload: merged,
                status: 'executed',
                executionResult: execResult,
                resolvedAt: nowIso,
              },
        ),
      }));
      return true;
    },
    [
      accessToken,
      coursesStore,
      invalidateAllDomainCaches,
      isApiMode,
      learningStore,
      localState.proposals,
      queryClient,
      studyStore,
    ],
  );

  const rejectProposal = useCallback(
    async (proposalId: string, reason?: string): Promise<boolean> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          await rejectProposalApi(accessToken, proposalId, reason);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['ai-proposals'] }),
            queryClient.invalidateQueries({ queryKey: ['ai-conversation-detail'] }),
          ]);
          return true;
        } catch (err) {
          setMutationError(
            err instanceof Error ? err.message : 'Impossible de rejeter la proposition.',
          );
          return false;
        }
      }

      const nowIso = new Date().toISOString();
      setLocalState((prev) => ({
        ...prev,
        proposals: prev.proposals.map((p) =>
          p.id !== proposalId
            ? p
            : {
                ...p,
                status: 'rejected',
                errorMessage: reason?.trim() || null,
                resolvedAt: nowIso,
              },
        ),
      }));
      return true;
    },
    [accessToken, isApiMode, queryClient],
  );

  const generateDailyBriefing = useCallback(async (): Promise<boolean> => {
    setMutationError(null);
    if (isApiMode) {
      try {
        await generateDailyBriefingApi(accessToken);
        await queryClient.invalidateQueries({ queryKey: ['ai-reports'] });
        return true;
      } catch (err) {
        setMutationError(
          err instanceof Error ? err.message : 'Impossible de générer le briefing quotidien.',
        );
        return false;
      }
    }

    const now = new Date();
    const nowIso = now.toISOString();
    const activeTasks = studyStore.tasks.filter((t) => isActiveTaskStatus(t.status));
    const missingData: string[] = [];
    if (!studyStore.activePriorityTitle) {
      missingData.push('Aucune priorité principale active définie.');
    }
    if (activeTasks.length === 0) {
      missingData.push('Aucune tâche active enregistrée.');
    }

    const contentLines = [
      `## Briefing quotidien : ${studyStore.profile.timezone}`,
      `- **Priorité principale active** : ${studyStore.activePriorityTitle ?? 'Non définie'}`,
      `- **Tâches actives** : ${activeTasks.length}`,
      ...activeTasks.slice(0, 3).map((t) => `  - [${t.priority}] **${t.title}**`),
    ];
    if (missingData.length > 0) {
      contentLines.push(`\n> **Note AI-06 (données partielles)** : ${missingData.join(' ; ')}`);
    }

    const report: AiReport = {
      id: generateId(),
      userId: LOCAL_USER_ID,
      type: 'daily_briefing',
      periodStart: nowIso,
      periodEnd: nowIso,
      content: contentLines.join('\n'),
      metadata: {
        isEstimate: missingData.length > 0,
        missingData,
      },
      createdAt: nowIso,
    };

    setLocalState((prev) => ({
      ...prev,
      reports: [report, ...prev.reports],
    }));
    return true;
  }, [
    accessToken,
    isApiMode,
    queryClient,
    studyStore.activePriorityTitle,
    studyStore.profile.timezone,
    studyStore.tasks,
  ]);

  const generateWeeklyReview = useCallback(async (): Promise<boolean> => {
    setMutationError(null);
    if (isApiMode) {
      try {
        await generateWeeklyReviewApi(accessToken);
        await queryClient.invalidateQueries({ queryKey: ['ai-reports'] });
        return true;
      } catch (err) {
        setMutationError(
          err instanceof Error ? err.message : 'Impossible de générer le bilan hebdomadaire.',
        );
        return false;
      }
    }

    const now = new Date();
    const nowIso = now.toISOString();
    const weekAgoIso = new Date(now.getTime() - 7 * 86_400_000).toISOString();
    const completedSessions = studyStore.sessions.filter(
      (s) => s.status === 'completed' && s.endedAt !== null,
    );
    const doneTasks = studyStore.tasks.filter((t) => t.status === 'done');
    const activeProjects = learningStore.projects.filter((p) => p.status === 'active');
    const missingData: string[] = [];
    if (completedSessions.length === 0) {
      missingData.push('Aucune séance d’étude terminée sur les 7 derniers jours.');
    }

    const contentLines = [
      '## Bilan hebdomadaire (7 derniers jours)',
      `- **Séances terminées** : ${completedSessions.length}`,
      `- **Tâches terminées** : ${doneTasks.length}`,
      `- **Projets actifs** : ${activeProjects.length}`,
    ];
    if (missingData.length > 0) {
      contentLines.push(
        `\n> **Note AI-06 (estimation / données manquantes)** : ${missingData.join(' ; ')}`,
      );
    }

    const report: AiReport = {
      id: generateId(),
      userId: LOCAL_USER_ID,
      type: 'weekly_review',
      periodStart: weekAgoIso,
      periodEnd: nowIso,
      content: contentLines.join('\n'),
      metadata: {
        isEstimate: missingData.length > 0,
        missingData,
      },
      createdAt: nowIso,
    };

    setLocalState((prev) => ({
      ...prev,
      reports: [report, ...prev.reports],
    }));
    return true;
  }, [
    accessToken,
    isApiMode,
    learningStore.projects,
    queryClient,
    studyStore.sessions,
    studyStore.tasks,
  ]);

  const messages = useMemo(() => {
    if (isApiMode) {
      return detailQuery.data?.messages ?? [];
    }
    if (!activeConversationId) return [];
    return localState.messages.filter((m) => m.conversationId === activeConversationId);
  }, [activeConversationId, detailQuery.data?.messages, isApiMode, localState.messages]);

  const proposals = useMemo(
    () => (isApiMode ? (proposalsQuery.data ?? []) : localState.proposals),
    [isApiMode, localState.proposals, proposalsQuery.data],
  );

  const reports = useMemo(
    () => (isApiMode ? (reportsQuery.data ?? []) : localState.reports),
    [isApiMode, localState.reports, reportsQuery.data],
  );

  const tools = useMemo(
    () => (isApiMode ? (toolsQuery.data ?? DEFAULT_LOCAL_TOOLS) : DEFAULT_LOCAL_TOOLS),
    [isApiMode, toolsQuery.data],
  );

  const isLoading =
    isApiMode &&
    (conversationsQuery.isLoading || proposalsQuery.isLoading || reportsQuery.isLoading);

  const error =
    isApiMode && firstQueryError
      ? firstQueryError instanceof Error
        ? firstQueryError.message
        : 'Impossible de charger le Copilote IA.'
      : null;

  const value = useMemo<AiStoreContextValue>(
    () => ({
      tools,
      conversations,
      activeConversationId,
      setActiveConversationId,
      messages,
      proposals,
      reports,
      aiMemory,
      isLoading,
      error,
      mutationError,
      clearMutationError,
      retry,
      updateAiMemory,
      createConversation,
      deleteConversation,
      sendMessage,
      updateProposal,
      acceptProposal,
      rejectProposal,
      generateDailyBriefing,
      generateWeeklyReview,
    }),
    [
      tools,
      conversations,
      activeConversationId,
      messages,
      proposals,
      reports,
      aiMemory,
      isLoading,
      error,
      mutationError,
      clearMutationError,
      retry,
      updateAiMemory,
      createConversation,
      deleteConversation,
      sendMessage,
      updateProposal,
      acceptProposal,
      rejectProposal,
      generateDailyBriefing,
      generateWeeklyReview,
    ],
  );

  return <AiStoreContext.Provider value={value}>{children}</AiStoreContext.Provider>;
}

export function useAiStore(): AiStoreContextValue {
  const ctx = useContext(AiStoreContext);
  if (!ctx) {
    throw new Error('useAiStore doit être utilisé à l’intérieur de AiStoreProvider.');
  }
  return ctx;
}
