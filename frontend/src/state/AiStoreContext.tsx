import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { isActiveTaskStatus } from '../features/tasks/taskUtils';
import {
  acceptProposalApi,
  createConversationApi,
  deleteConversationApi,
  fetchAiToolsApi,
  fetchConversationDetailApi,
  fetchConversationsApi,
  fetchProposalsApi,
  fetchReportsApi,
  generateDailyBriefingApi,
  generateWeeklyReviewApi,
  rejectProposalApi,
  sendAiMessageApi,
} from '../lib/aiApi';
import { ApiError } from '../lib/api-client';
import { generateId, readFromStorage, STORAGE_KEYS, writeToStorage } from '../lib/storage';
import type {
  AiActionProposal,
  AiContextScope,
  AiConversation,
  AiMessage,
  AiReport,
  AiToolSpec,
  ScheduleEventType,
  SkillEvidenceType,
  SkillLevel,
  TaskPriority,
} from '../types/domain';
import { useAuth } from './AuthContext';
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
    label: 'Lire les parcours et compétences',
    description: 'Consulte les parcours, modules, leçons, compétences et preuves.',
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
    description: 'Propose d’enregistrer une preuve sur une compétence existante.',
    requiresConfirmation: true,
    parameterKeys: ['skill_id', 'type', 'description', 'reference_url', 'result'],
  },
  {
    name: 'update_skill_level',
    access: 'proposal',
    label: 'Proposer un niveau de compétence',
    description: 'Propose une réévaluation du niveau 0..5 d’une compétence.',
    requiresConfirmation: true,
    parameterKeys: ['skill_id', 'current_level', 'target_level'],
  },
];

export interface AiLocalState {
  conversations: AiConversation[];
  messages: AiMessage[];
  proposals: AiActionProposal[];
  reports: AiReport[];
}

const DEFAULT_AI_STATE: AiLocalState = {
  conversations: [],
  messages: [],
  proposals: [],
  reports: [],
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
  isLoading: boolean;
  error: string | null;
  mutationError: string | null;
  clearMutationError: () => void;
  retry: () => void;
  createConversation: (title?: string) => Promise<string | null>;
  deleteConversation: (id: string) => Promise<boolean>;
  sendMessage: (content: string, scopes?: AiContextScope[]) => Promise<boolean>;
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

  const retry = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['ai-conversations'] });
    void queryClient.invalidateQueries({ queryKey: ['ai-proposals'] });
    void queryClient.invalidateQueries({ queryKey: ['ai-reports'] });
    void queryClient.invalidateQueries({ queryKey: ['ai-conversation-detail'] });
  }, [queryClient]);

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
          await sendAiMessageApi(accessToken, convId, trimmed, scopes);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['ai-conversations'] }),
            queryClient.invalidateQueries({ queryKey: ['ai-conversation-detail'] }),
            queryClient.invalidateQueries({ queryKey: ['ai-proposals'] }),
          ]);
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

      if (lowered.includes('créneau') || lowered.includes('planifie')) {
        const start = new Date(Date.now() + 2 * 3600_000);
        start.setMinutes(0, 0, 0);
        const end = new Date(start.getTime() + 3600_000);
        const slotTitle = extractTitleFromPrompt(
          trimmed,
          `Bloc focus : ${studyStore.activePriorityTitle ?? 'Étude approfondie'}`,
        );
        generatedProposals.push({
          id: generateId(),
          userId: LOCAL_USER_ID,
          conversationId: convId,
          actionType: 'create_schedule_event',
          title: `Planifier « ${slotTitle} » (1h)`,
          explanation: 'Créneau d’étude soumis à votre confirmation.',
          payload: {
            title: slotTitle,
            type: 'learning',
            starts_at: start.toISOString(),
            ends_at: end.toISOString(),
            notes: 'Créneau proposé par le Copilote IA.',
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
        replyLines.push(`J’ai préparé une proposition de créneau **« ${slotTitle} »**.`);
      }

      if (lowered.includes('preuve') && learningStore.skills.length > 0) {
        const skill = learningStore.skills[0];
        const desc = extractTitleFromPrompt(
          trimmed,
          `Exercice pratique validé sur ${skill.name}`,
        );
        generatedProposals.push({
          id: generateId(),
          userId: LOCAL_USER_ID,
          conversationId: convId,
          actionType: 'add_skill_evidence',
          title: `Ajouter une preuve sur « ${skill.name} »`,
          explanation: 'Enregistre une preuve vérifiable sur votre compétence.',
          payload: {
            skill_id: skill.id,
            skill_name: skill.name,
            type: 'exercise',
            description: desc,
            result: 'Validé',
          },
          status: 'pending',
          expiresAt: expiresIso,
          executionResult: null,
          errorMessage: null,
          createdAt: nowIso,
          resolvedAt: null,
        });
        replyLines.push(`Proposition de preuve prête pour **${skill.name}**.`);
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

      const userMessage: AiMessage = {
        id: generateId(),
        userId: LOCAL_USER_ID,
        conversationId: convId,
        role: 'user',
        content: trimmed,
        metadata: { includedScopes: scopes },
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
      createConversation,
      isApiMode,
      learningStore.projects,
      learningStore.skills,
      queryClient,
      studyStore.activePriorityTitle,
      studyStore.profile.aiInstructions,
      studyStore.tasks,
    ],
  );

  const acceptProposal = useCallback(
    async (
      proposalId: string,
      payloadOverrides?: Record<string, unknown>,
    ): Promise<boolean> => {
      setMutationError(null);
      if (isApiMode) {
        try {
          await acceptProposalApi(accessToken, proposalId, payloadOverrides);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['ai-proposals'] }),
            queryClient.invalidateQueries({ queryKey: ['ai-conversation-detail'] }),
            queryClient.invalidateQueries({ queryKey: ['tasks'] }),
            queryClient.invalidateQueries({ queryKey: ['schedule'] }),
            queryClient.invalidateQueries({ queryKey: ['skills'] }),
            queryClient.invalidateQueries({ queryKey: ['skill-evidence'] }),
            queryClient.invalidateQueries({ queryKey: ['profile'] }),
          ]);
          return true;
        } catch (err) {
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
        await learningStore.addEvidence(skillId, {
          type: (merged.type as SkillEvidenceType) || 'exercise',
          description: String(merged.description ?? 'Preuve validée'),
          referenceUrl: String(merged.reference_url ?? ''),
          result: String(merged.result ?? ''),
        });
        execResult = { entity: 'skill_evidence', skill_id: skillId };
      } else if (target.actionType === 'update_skill_level') {
        const skillId = String(merged.skill_id ?? '');
        const lvl = Number(merged.current_level ?? 1) as SkillLevel;
        await learningStore.updateSkill(skillId, { currentLevel: lvl });
        execResult = { entity: 'skill', skill_id: skillId, current_level: lvl };
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
    [accessToken, isApiMode, learningStore, localState.proposals, queryClient, studyStore],
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
      `## Briefing quotidien — ${studyStore.profile.timezone}`,
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
      isLoading,
      error,
      mutationError,
      clearMutationError,
      retry,
      createConversation,
      deleteConversation,
      sendMessage,
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
      isLoading,
      error,
      mutationError,
      clearMutationError,
      retry,
      createConversation,
      deleteConversation,
      sendMessage,
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
