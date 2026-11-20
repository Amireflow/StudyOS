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
import { generateId } from '../lib/storage';
import type {
  AiActionProposal,
  AiContextScope,
  AiConversation,
  AiMemory,
  AiMemoryUpdate,
  AiMessage,
  AiReport,
  AiToolSpec,
} from '../types/domain';
import { useAuth } from './AuthContext';

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

  const isApiMode = session?.mode === 'api' && Boolean(session.accessToken);
  const accessToken = session?.mode === 'api' ? session.accessToken : '';
  const userIdKey = session?.userId ?? 'anonymous';

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

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
    () => (isApiMode ? (conversationsQuery.data ?? []) : []),
    [isApiMode, conversationsQuery.data],
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
      queryClient.invalidateQueries({ queryKey: ['learning'] }),
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

  const aiMemory = useMemo<AiMemory>(
    () =>
      memoryQuery.data ?? {
        userId: userIdKey,
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
        updatedAt: new Date(0).toISOString(),
      },
    [memoryQuery.data, userIdKey],
  );

  const updateAiMemory = useCallback(
    async (patch: AiMemoryUpdate): Promise<boolean> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }
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
    },
    [accessToken, isApiMode, queryClient],
  );

  const createConversation = useCallback(
    async (title?: string): Promise<string | null> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return null;
      }
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
    },
    [accessToken, isApiMode, queryClient],
  );

  const deleteConversation = useCallback(
    async (id: string): Promise<boolean> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }
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
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }

      setMutationError(null);
      let convId = activeConversationId;
      if (!convId) {
        convId = await createConversation(trimmed.slice(0, 60));
        if (!convId) return false;
      }

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
          queryClient.invalidateQueries({ queryKey: ['ai-memory'] }),
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
    },
    [
      accessToken,
      activeConversationId,
      aiMemory.autoExecuteSimpleActions,
      createConversation,
      invalidateAllDomainCaches,
      isApiMode,
      queryClient,
      userIdKey,
    ],
  );

  const updateProposal = useCallback(
    async (
      proposalId: string,
      payloadOverrides: Record<string, unknown>,
      recalculateSlots = false,
    ): Promise<boolean> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }
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
    },
    [accessToken, isApiMode, queryClient],
  );

  const acceptProposal = useCallback(
    async (
      proposalId: string,
      payloadOverrides?: Record<string, unknown>,
    ): Promise<boolean> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }
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
    },
    [accessToken, invalidateAllDomainCaches, isApiMode, queryClient],
  );

  const rejectProposal = useCallback(
    async (proposalId: string, reason?: string): Promise<boolean> => {
      setMutationError(null);
      if (!isApiMode) {
        setMutationError('Connexion requise.');
        return false;
      }
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
    },
    [accessToken, isApiMode, queryClient],
  );

  const generateDailyBriefing = useCallback(async (): Promise<boolean> => {
    setMutationError(null);
    if (!isApiMode) {
      setMutationError('Connexion requise.');
      return false;
    }
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
  }, [accessToken, isApiMode, queryClient]);

  const generateWeeklyReview = useCallback(async (): Promise<boolean> => {
    setMutationError(null);
    if (!isApiMode) {
      setMutationError('Connexion requise.');
      return false;
    }
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
  }, [accessToken, isApiMode, queryClient]);

  const messages = useMemo(
    () => (isApiMode ? (detailQuery.data?.messages ?? []) : []),
    [detailQuery.data?.messages, isApiMode],
  );

  const proposals = useMemo(
    () => (isApiMode ? (proposalsQuery.data ?? []) : []),
    [isApiMode, proposalsQuery.data],
  );

  const reports = useMemo(
    () => (isApiMode ? (reportsQuery.data ?? []) : []),
    [isApiMode, reportsQuery.data],
  );

  const tools = useMemo(
    () => (isApiMode ? (toolsQuery.data ?? []) : []),
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
