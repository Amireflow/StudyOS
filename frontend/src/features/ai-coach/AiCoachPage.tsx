import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import {
  AiChat02Icon,
  Alert02Icon,
  ArrowUp02Icon,
  BookOpen01Icon,
  Calendar03Icon,
  CheckmarkCircle02Icon,
  CheckmarkSquare02Icon,
  File02Icon,
  HistoryIcon,
  MessageAdd01Icon,
  Settings02Icon,
  ShieldCheckIcon,
  SlidersHorizontalIcon,
  SparklesIcon,
  Target02Icon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { InlineConfirm, Input } from '../../components/ui/FormFields';
import { Icon, type IconSvgElement } from '../../components/ui/Icon';
import { ScrollArea } from '../../components/ui/ScrollArea';
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import { formatDateTimeFr, getMondayOfWeek } from '../../lib/date';
import { useAiStore } from '../../state/AiStoreContext';
import type { AiContextScope } from '../../types/domain';
import { TimetableImportPanel } from '../schedule/TimetableImportPanel';
import { MarkdownContent } from './MarkdownContent';
import { ProposalCard } from './ProposalCard';

type ProposalFilter = 'all' | 'pending' | 'executed' | 'rejected';
type RailTab = 'proposals' | 'reports';
type MobileView = 'chat' | 'rail';

const SCOPE_OPTIONS: Array<{ value: AiContextScope; label: string }> = [
  { value: 'auto', label: 'Contexte auto' },
  { value: 'today', label: 'Journée' },
  { value: 'tasks', label: 'Tâches' },
  { value: 'schedule', label: 'Planning' },
  { value: 'learning', label: 'Apprentissage' },
  { value: 'skills', label: 'Compétences' },
  { value: 'projects', label: 'Projets' },
  { value: 'weekly', label: 'Semaine (7 j)' },
];

const PROPOSAL_FILTERS: Array<{ value: ProposalFilter; label: string }> = [
  { value: 'all', label: 'Toutes' },
  { value: 'pending', label: 'En attente' },
  { value: 'executed', label: 'Exécutées' },
  { value: 'rejected', label: 'Rejetées' },
];

const STARTER_PROMPTS: Array<{
  title: string;
  subtitle: string;
  prompt: string;
  icon: IconSvgElement;
}> = [
  {
    title: 'Planifier ma journée',
    subtitle: 'Organiser les créneaux autour de ma priorité',
    prompt: 'Planifie ma journée autour de ma priorité active et de mes créneaux disponibles.',
    icon: Calendar03Icon,
  },
  {
    title: 'Prioriser mes tâches',
    subtitle: 'Classer les actions selon l’urgence et la charge',
    prompt: 'Analyse mes tâches en cours et propose un ordre de priorité réaliste.',
    icon: CheckmarkSquare02Icon,
  },
  {
    title: 'Créer une tâche ciblée',
    subtitle: 'Préparer une action structurée à valider',
    prompt: 'Crée une tâche : « Préparer la séance de révision » avec priorité normale.',
    icon: Target02Icon,
  },
  {
    title: 'Bloquer un créneau d’étude',
    subtitle: 'Réserver un bloc de travail dans le planning',
    prompt: 'Planifie un créneau d’étude de 60 minutes sur le prochain intervalle libre.',
    icon: Timer02Icon,
  },
  {
    title: 'Recommander une révision',
    subtitle: 'Cibler la compétence la plus utile maintenant',
    prompt: 'Quelle compétence devrais-je renforcer cette semaine selon mon avancement ?',
    icon: BookOpen01Icon,
  },
  {
    title: 'Apprendre une compétence',
    subtitle: 'Analyser la faisabilité et planifier sans conflit',
    prompt: 'Je voudrais apprendre le développement avec React.',
    icon: Target02Icon,
  },
];

const THINKING_STEPS: Array<{ label: string; detail: string }> = [
  {
    label: 'Analyse de votre demande',
    detail: 'Lecture de votre objectif et identification de l’intention pédagogique…',
  },
  {
    label: 'Consultation de votre contexte',
    detail: 'Croisement avec vos tâches, votre emploi du temps et vos compétences…',
  },
  {
    label: 'Vérification stratégique & verrou pédagogique',
    detail: 'Contrôle des conflits horaires, de la priorité active et des preuves…',
  },
  {
    label: 'Rédaction de la réponse & propositions',
    detail: 'Structuration de la synthèse et préparation des actions à valider…',
  },
];

const PROTOCOL_JSON_MARKER_RE =
  /"(?:reply|proposals|action_type|is_estimate|missing_data|create_missing_courses|apply_immediately|replace_future_planned)"\s*:/i;

function cleanAssistantReplyText(rawContent: string): string {
  const trimmed = (rawContent ?? '').trim();
  if (!trimmed) return '';
  if (!PROTOCOL_JSON_MARKER_RE.test(trimmed)) return trimmed;

  // 1. Si tout le message est un objet JSON (entouré ou non de ```json)
  let candidate = trimmed;
  if (candidate.startsWith('```') && candidate.endsWith('```')) {
    candidate = candidate
      .replace(/^```(?:json)?\s*/i, '')
      .replace(/\s*```$/, '')
      .trim();
  }
  if (candidate.startsWith('{')) {
    try {
      const parsed = JSON.parse(candidate) as Record<string, unknown>;
      const replyVal =
        parsed.reply ?? parsed.response ?? parsed.message ?? parsed.assistant_message;
      if (typeof replyVal === 'string' && replyVal.trim()) {
        return cleanAssistantReplyText(replyVal.trim());
      }
    } catch {
      const replyMatch =
        candidate.match(
          /"reply"\s*:\s*"([\s\S]*?)"\s*,\s*"(?:is_estimate|missing_data|proposals)"/i,
        ) ?? candidate.match(/"reply"\s*:\s*"((?:[^"\\]|\\.)*)"/i);
      if (replyMatch?.[1]) {
        return replyMatch[1]
          .replace(/\\n/g, '\n')
          .replace(/\\"/g, '"')
          .replace(/\\t/g, '\t')
          .trim();
      }
    }
  }

  // 2. Si un bloc ```json protocolaire est présent dans ou à la fin du message
  let extractedFromFence = '';
  const withoutFences = trimmed
    .replace(/```(?:json)?\s*([\s\S]*?)```/gi, (full, inner: string) => {
      if (!PROTOCOL_JSON_MARKER_RE.test(inner)) return full;
      try {
        const parsed = JSON.parse(inner.trim()) as Record<string, unknown>;
        const replyVal =
          parsed.reply ?? parsed.response ?? parsed.message ?? parsed.assistant_message;
        if (typeof replyVal === 'string' && replyVal.trim()) {
          extractedFromFence = replyVal.trim();
        }
      } catch {
        // Bloc technique malformé : on le retire de l'affichage
      }
      return '';
    })
    .trim();

  if (withoutFences && extractedFromFence && !withoutFences.includes(extractedFromFence)) {
    return `${withoutFences}\n\n${extractedFromFence}`;
  }
  return withoutFences || extractedFromFence || 'Voici ma synthèse.';
}

function StreamingAssistantContent({
  content,
  isStreaming,
  onComplete,
}: {
  content: string;
  isStreaming: boolean;
  onComplete: () => void;
}) {
  const safeContent = useMemo(() => cleanAssistantReplyText(content), [content]);
  const [revealedCount, setRevealedCount] = useState(() => (isStreaming ? 0 : safeContent.length));

  useEffect(() => {
    if (!isStreaming) {
      setRevealedCount(safeContent.length);
      return;
    }

    const total = safeContent.length;
    if (total === 0) {
      onComplete();
      return;
    }

    const stepChars = Math.max(18, Math.ceil(total / 28));
    let current = Math.min(total, stepChars);
    setRevealedCount(current);

    const timer = window.setInterval(() => {
      current = Math.min(total, current + stepChars);
      while (current < total && !/\s/.test(safeContent[current])) {
        current += 1;
      }
      setRevealedCount(current);
      if (current >= total) {
        window.clearInterval(timer);
        onComplete();
      }
    }, 24);

    return () => {
      window.clearInterval(timer);
    };
  }, [safeContent, isStreaming, onComplete]);

  if (!isStreaming || revealedCount >= safeContent.length) {
    return <MarkdownContent content={safeContent} />;
  }

  return (
    <div className="space-y-2">
      <MarkdownContent content={safeContent.slice(0, revealedCount)} />
      <div className="flex items-center justify-between gap-2 pt-0.5">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-teal-700 dark:text-teal-400">
          <span className="h-1.5 w-1.5 animate-ping rounded-full bg-teal-600 dark:bg-teal-400" />
          Rédaction en cours…
        </span>
        <button
          type="button"
          onClick={() => {
            setRevealedCount(safeContent.length);
            onComplete();
          }}
          className="text-[11px] font-medium text-zinc-500 underline hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200"
        >
          Afficher tout
        </button>
      </div>
    </div>
  );
}

export function AiCoachPage() {
  const {
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
  } = useAiStore();

  const [promptText, setPromptText] = useState('');
  const [selectedScope, setSelectedScope] = useState<AiContextScope>('auto');
  const [proposalFilter, setProposalFilter] = useState<ProposalFilter>('all');
  const [railTab, setRailTab] = useState<RailTab>('proposals');
  const [mobileView, setMobileView] = useState<MobileView>('chat');
  const [isDesktopRailDismissed, setIsDesktopRailDismissed] = useState(false);
  const [isDesktopRailForcedOpen, setIsDesktopRailForcedOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);
  const [memoryHoursDraft, setMemoryHoursDraft] = useState(
    aiMemory.weeklyStudyHours !== null ? String(aiMemory.weeklyStudyHours) : '',
  );
  const [memoryConstraintsDraft, setMemoryConstraintsDraft] = useState(
    aiMemory.constraints.join(', '),
  );
  const [memoryGoalsDraft, setMemoryGoalsDraft] = useState(aiMemory.longTermGoals.join(', '));
  const [isSavingMemory, setIsSavingMemory] = useState(false);
  const [isTimetableImportOpen, setIsTimetableImportOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    setMemoryHoursDraft(aiMemory.weeklyStudyHours !== null ? String(aiMemory.weeklyStudyHours) : '');
    setMemoryConstraintsDraft(aiMemory.constraints.join(', '));
    setMemoryGoalsDraft(aiMemory.longTermGoals.join(', '));
  }, [aiMemory.weeklyStudyHours, aiMemory.constraints, aiMemory.longTermGoals]);

  async function handleToggleAutoSimple() {
    await updateAiMemory({ autoExecuteSimpleActions: !aiMemory.autoExecuteSimpleActions });
  }

  async function handleSaveMemory(event: FormEvent) {
    event.preventDefault();
    setIsSavingMemory(true);
    try {
      const parsedHours =
        memoryHoursDraft.trim() === ''
          ? null
          : Math.max(0, Math.min(120, Number(memoryHoursDraft.trim())));
      const constraints = memoryConstraintsDraft
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      const longTermGoals = memoryGoalsDraft
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      await updateAiMemory({
        weeklyStudyHours: Number.isNaN(parsedHours as number) ? null : parsedHours,
        constraints,
        longTermGoals,
      });
    } finally {
      setIsSavingMemory(false);
    }
  }
  const currentWeekMonday = useMemo(() => getMondayOfWeek(new Date()), []);
  const [pendingUserPrompt, setPendingUserPrompt] = useState<string | null>(null);
  const [thinkingStepIndex, setThinkingStepIndex] = useState(0);
  const [thinkingElapsedSec, setThinkingElapsedSec] = useState(0);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [isGeneratingBriefing, setIsGeneratingBriefing] = useState(false);
  const [isGeneratingWeekly, setIsGeneratingWeekly] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const awaitingStreamAfterSendRef = useRef(false);
  const lastKnownAssistantIdRef = useRef<string | null>(null);

  const pendingProposalsCount = useMemo(
    () => proposals.filter((item) => item.status === 'pending').length,
    [proposals],
  );

  const filteredProposals = useMemo(() => {
    if (proposalFilter === 'all') return proposals;
    return proposals.filter((item) => item.status === proposalFilter);
  }, [proposalFilter, proposals]);

  const activeConversation = useMemo(
    () => conversations.find((item) => item.id === activeConversationId) ?? null,
    [activeConversationId, conversations],
  );

  const isDesktopRailVisible = useMemo(() => {
    if (isDesktopRailForcedOpen) return true;
    if (isDesktopRailDismissed) return false;
    return railTab === 'reports';
  }, [isDesktopRailDismissed, isDesktopRailForcedOpen, railTab]);

  const proposalsByMessageId = useMemo(() => {
    const map = new Map<string, typeof proposals>();
    const assistantMessages = messages.filter((m) => m.role === 'assistant');
    if (assistantMessages.length === 0 || proposals.length === 0) {
      return map;
    }

    const activeProposals = activeConversationId
      ? proposals.filter((p) => !p.conversationId || p.conversationId === activeConversationId)
      : proposals;
    const pool = activeProposals.length > 0 ? activeProposals : proposals;
    const byId = new Map(pool.map((p) => [p.id, p]));
    const assigned = new Set<string>();

    for (const msg of assistantMessages) {
      const ids = msg.metadata.proposalIds ?? [];
      const linked = ids
        .map((id) => byId.get(id))
        .filter((item): item is (typeof proposals)[number] => Boolean(item));
      if (linked.length > 0) {
        map.set(msg.id, linked);
        for (const item of linked) {
          assigned.add(item.id);
        }
      }
    }

    const unassigned = pool.filter((p) => !assigned.has(p.id));
    if (unassigned.length > 0) {
      const lastAssistant = assistantMessages[assistantMessages.length - 1];
      const existing = map.get(lastAssistant.id) ?? [];
      map.set(lastAssistant.id, [...existing, ...unassigned]);
    }

    return map;
  }, [activeConversationId, messages, proposals]);

  useEffect(() => {
    if (!isSending) {
      setThinkingStepIndex(0);
      setThinkingElapsedSec(0);
      return;
    }

    const startMs = Date.now();
    const interval = window.setInterval(() => {
      const elapsedMs = Date.now() - startMs;
      setThinkingElapsedSec(Math.floor(elapsedMs / 1000));
      if (elapsedMs >= 6500) {
        setThinkingStepIndex(3);
      } else if (elapsedMs >= 3600) {
        setThinkingStepIndex(2);
      } else if (elapsedMs >= 1500) {
        setThinkingStepIndex(1);
      }
    }, 300);

    return () => {
      window.clearInterval(interval);
    };
  }, [isSending]);

  useEffect(() => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant') ?? null;
    if (
      awaitingStreamAfterSendRef.current &&
      lastAssistant &&
      lastAssistant.id !== lastKnownAssistantIdRef.current
    ) {
      awaitingStreamAfterSendRef.current = false;
      lastKnownAssistantIdRef.current = lastAssistant.id;
      if (import.meta.env.MODE !== 'test') {
        setStreamingMessageId(lastAssistant.id);
      }
    } else if (lastAssistant) {
      lastKnownAssistantIdRef.current = lastAssistant.id;
    }
  }, [messages]);

  useEffect(() => {
    if (messages.length > 0 || isSending) {
      const endEl = messagesEndRef.current;
      const scrollViewport = endEl?.closest('.overflow-y-auto') as HTMLElement | null;
      if (scrollViewport && typeof scrollViewport.scrollTo === 'function') {
        scrollViewport.scrollTo({
          top: scrollViewport.scrollHeight,
          behavior: 'smooth',
        });
      }
    }
  }, [activeConversationId, isSending, messages.length, thinkingStepIndex]);

  async function submitPrompt() {
    const trimmed = promptText.trim();
    if (!trimmed || isSending) return;
    const prevAssistant = [...messages].reverse().find((m) => m.role === 'assistant') ?? null;
    lastKnownAssistantIdRef.current = prevAssistant?.id ?? null;
    awaitingStreamAfterSendRef.current = true;
    setPendingUserPrompt(trimmed);
    setPromptText('');
    setIsSending(true);
    try {
      const ok = await sendMessage(trimmed, [selectedScope]);
      if (!ok) {
        awaitingStreamAfterSendRef.current = false;
        setPromptText(trimmed);
      }
    } finally {
      setPendingUserPrompt(null);
      setIsSending(false);
    }
  }

  function handleFormSubmit(event: FormEvent) {
    event.preventDefault();
    void submitPrompt();
  }

  function handleTextareaKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void submitPrompt();
    }
  }

  function handleUseStarterPrompt(prompt: string) {
    setPromptText(prompt);
    textareaRef.current?.focus();
  }

  async function handleNewConversation() {
    const id = await createConversation();
    if (id) {
      setActiveConversationId(id);
      setMobileView('chat');
      setIsHistoryOpen(false);
      textareaRef.current?.focus();
    }
  }

  async function handleGenerateBriefing() {
    if (isGeneratingBriefing) return;
    setIsGeneratingBriefing(true);
    try {
      const ok = await generateDailyBriefing();
      if (ok) {
        setRailTab('reports');
        setMobileView('rail');
        setIsDesktopRailDismissed(false);
        setIsDesktopRailForcedOpen(true);
      }
    } finally {
      setIsGeneratingBriefing(false);
    }
  }

  async function handleGenerateWeekly() {
    if (isGeneratingWeekly) return;
    setIsGeneratingWeekly(true);
    try {
      const ok = await generateWeeklyReview();
      if (ok) {
        setRailTab('reports');
        setMobileView('rail');
        setIsDesktopRailDismissed(false);
        setIsDesktopRailForcedOpen(true);
      }
    } finally {
      setIsGeneratingWeekly(false);
    }
  }

  if (isLoading) {
    return <LoadingState message="Chargement du copilote…" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void retry()} />;
  }

  return (
    <div className="space-y-3">
      {/* Barre supérieure compacte & sans distraction */}
      <header className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-white px-3.5 py-2.5 sm:px-4 dark:bg-zinc-900">
        <div className="flex min-w-0 items-center gap-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-teal-700 text-white dark:bg-teal-600">
            <Icon icon={AiChat02Icon} size={16} />
          </div>
          <div className="flex min-w-0 items-center gap-2">
            <h1 className="ui-page-title">
              Copilote
            </h1>
            {activeConversation && (
              <span className="hidden max-w-[200px] truncate rounded-lg bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 sm:inline-block md:max-w-[260px] dark:bg-zinc-800 dark:text-zinc-400">
                {activeConversation.title}
              </span>
            )}
          </div>
        </div>

        <div className="no-scrollbar flex items-center gap-1 overflow-x-auto">
          <Button
            type="button"
            variant="primary"
            size="sm"
            className="h-8 shrink-0 px-2.5 text-xs"
            onClick={() => void handleNewConversation()}
          >
            <Icon icon={MessageAdd01Icon} size={14} />
            Nouvelle conversation
          </Button>

          {conversations.length > 0 && (
            <Button
              type="button"
              variant={isHistoryOpen ? 'primary' : 'ghost'}
              size="sm"
              className="h-8 shrink-0 px-2.5 text-xs"
              aria-label="Historique des conversations"
              aria-expanded={isHistoryOpen}
              onClick={() => {
                setIsHistoryOpen((prev) => !prev);
                setIsToolsOpen(false);
                setIsMemoryOpen(false);
              }}
            >
              <Icon icon={HistoryIcon} size={14} />
              Historique
            </Button>
          )}

          <div className="mx-0.5 hidden h-4 w-px bg-zinc-200 sm:block dark:bg-zinc-800" />

          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 shrink-0 px-2.5 text-xs"
            isLoading={isGeneratingBriefing}
            onClick={() => void handleGenerateBriefing()}
          >
            <Icon icon={File02Icon} size={14} />
            Briefing du jour
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 shrink-0 px-2.5 text-xs"
            isLoading={isGeneratingWeekly}
            onClick={() => void handleGenerateWeekly()}
          >
            <Icon icon={File02Icon} size={14} />
            Bilan hebdo
          </Button>

          <Button
            type="button"
            variant={isMemoryOpen ? 'primary' : 'ghost'}
            size="sm"
            className="h-8 shrink-0 px-2.5 text-xs"
            aria-expanded={isMemoryOpen}
            onClick={() => {
              setIsMemoryOpen((prev) => !prev);
              setIsHistoryOpen(false);
              setIsToolsOpen(false);
            }}
          >
            <Icon icon={SparklesIcon} size={14} />
            Mémoire IA
          </Button>

          <Button
            type="button"
            variant={isToolsOpen ? 'primary' : 'ghost'}
            size="sm"
            className="h-8 shrink-0 px-2.5 text-xs"
            aria-expanded={isToolsOpen}
            onClick={() => {
              setIsToolsOpen((prev) => !prev);
              setIsHistoryOpen(false);
              setIsMemoryOpen(false);
            }}
          >
            <Icon icon={SlidersHorizontalIcon} size={14} />
            Outils ({tools.length})
          </Button>

          {(proposals.length > 0 || reports.length > 0) && (
            <button
              type="button"
              onClick={() => {
                if (isDesktopRailVisible) {
                  setIsDesktopRailDismissed(true);
                  setIsDesktopRailForcedOpen(false);
                } else {
                  setIsDesktopRailDismissed(false);
                  setIsDesktopRailForcedOpen(true);
                }
              }}
              className={cn(
                'hidden h-8 shrink-0 items-center gap-1.5 rounded-xl px-2.5 text-xs font-medium transition-colors lg:inline-flex',
                isDesktopRailVisible
                  ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                  : 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300',
              )}
            >
              <span>Panneau</span>
              {pendingProposalsCount > 0 && (
                <span className="rounded-full bg-amber-400/90 px-1.5 py-0.2 text-[10px] font-bold text-zinc-950">
                  {pendingProposalsCount}
                </span>
              )}
            </button>
          )}
        </div>
      </header>

      {mutationError && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:bg-rose-950/40 dark:text-rose-200"
        >
          <div className="flex items-center gap-2">
            <Icon icon={Alert02Icon} size={16} className="shrink-0" />
            <span>{mutationError}</span>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={clearMutationError}>
            Fermer
          </Button>
        </div>
      )}

      {/* Tiroir historique */}
      {isHistoryOpen && conversations.length > 0 && (
        <section
          aria-label="Historique des conversations"
          className="rounded-2xl bg-white p-4 dark:bg-zinc-900"
        >
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Historique des conversations ({conversations.length})
            </h2>
            <Button type="button" variant="ghost" size="sm" onClick={() => setIsHistoryOpen(false)}>
              Fermer
            </Button>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {conversations.map((conversation) => {
              const isCurrent = conversation.id === activeConversationId;
              return (
                <div
                  key={conversation.id}
                  className={cn(
                    'flex items-center justify-between gap-2 rounded-xl px-3 py-2.5 transition-colors',
                    isCurrent
                      ? 'bg-teal-50 text-teal-900 dark:bg-teal-950/50 dark:text-teal-200'
                      : 'bg-zinc-50 text-zinc-800 hover:bg-zinc-100 dark:bg-zinc-800/70 dark:text-zinc-200 dark:hover:bg-zinc-800',
                  )}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setActiveConversationId(conversation.id);
                      setMobileView('chat');
                    }}
                    className="min-w-0 flex-1 text-left"
                  >
                    <p className="truncate text-xs font-semibold">{conversation.title}</p>
                    <p className="mt-0.5 text-[11px] text-zinc-500 dark:text-zinc-400">
                      {formatDateTimeFr(conversation.updatedAt)}
                    </p>
                  </button>
                  <InlineConfirm
                    triggerLabel="Supprimer"
                    ariaLabel={`Supprimer ${conversation.title}`}
                    onConfirm={() => void deleteConversation(conversation.id)}
                  />
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Inspecteur d'outils */}
      {isToolsOpen && (
        <section
          aria-label="Outils autorisés"
          className="rounded-2xl bg-white p-4 dark:bg-zinc-900"
        >
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Outils autorisés ({tools.length})
              </h2>
              <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-800 dark:bg-teal-950/50 dark:text-teal-300">
                <Icon icon={ShieldCheckIcon} size={13} />
                Validation requise
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Link
                to="/settings"
                className="inline-flex items-center gap-1.5 rounded-xl bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
              >
                <Icon icon={Settings02Icon} size={14} />
                Consignes
              </Link>
              <Button type="button" variant="ghost" size="sm" onClick={() => setIsToolsOpen(false)}>
                Fermer
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {tools.map((tool) => (
              <div
                key={tool.name}
                className="rounded-xl bg-zinc-50 p-3 dark:bg-zinc-800/70"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                    {tool.label}
                  </p>
                  <Badge variant={tool.access === 'read' ? 'neutral' : 'primary'}>
                    {tool.access === 'read' ? 'Lecture' : 'Proposition'}
                  </Badge>
                </div>
                <p className="mt-1 line-clamp-1 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
                  {tool.description}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {isMemoryOpen && (
        <section
          aria-label="Mémoire IA persistante"
          className="rounded-2xl bg-white p-4 dark:bg-zinc-900"
        >
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Mémoire IA
            </h2>
            <Button type="button" variant="ghost" size="sm" onClick={() => setIsMemoryOpen(false)}>
              Fermer
            </Button>
          </div>

          <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-zinc-50 px-3 py-2.5 dark:bg-zinc-800/70">
            <div className="space-y-0.5">
              <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                Exécution directe des actions simples
              </p>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400">
                Créations complexes et validations soumises à confirmation.
              </p>
            </div>
            <Button
              type="button"
              variant={aiMemory.autoExecuteSimpleActions ? 'primary' : 'secondary'}
              size="sm"
              role="switch"
              aria-checked={aiMemory.autoExecuteSimpleActions}
              aria-label="Actions simples automatiques"
              onClick={() => void handleToggleAutoSimple()}
            >
              {aiMemory.autoExecuteSimpleActions ? 'Activé' : 'Désactivé'}
            </Button>
          </div>

          <form onSubmit={(e) => void handleSaveMemory(e)} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label
                htmlFor="memory-weekly-hours"
                className="mb-1 block text-xs font-medium text-zinc-700 dark:text-zinc-300"
              >
                Heures disponibles / semaine
              </label>
              <Input
                id="memory-weekly-hours"
                type="number"
                min={0}
                max={120}
                placeholder="Ex : 8"
                value={memoryHoursDraft}
                onChange={(e) => setMemoryHoursDraft(e.target.value)}
              />
            </div>

            <div>
              <label
                htmlFor="memory-constraints"
                className="mb-1 block text-xs font-medium text-zinc-700 dark:text-zinc-300"
              >
                Contraintes
              </label>
              <Input
                id="memory-constraints"
                placeholder="Ex : Pas le dimanche"
                value={memoryConstraintsDraft}
                onChange={(e) => setMemoryConstraintsDraft(e.target.value)}
              />
            </div>

            <div>
              <label
                htmlFor="memory-goals"
                className="mb-1 block text-xs font-medium text-zinc-700 dark:text-zinc-300"
              >
                Objectifs long terme
              </label>
              <Input
                id="memory-goals"
                placeholder="Ex : Stage Fullstack"
                value={memoryGoalsDraft}
                onChange={(e) => setMemoryGoalsDraft(e.target.value)}
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 sm:col-span-3">
              <div className="min-w-0 flex-1 line-clamp-1 text-[11px] text-zinc-500 dark:text-zinc-400">
                {aiMemory.recentDecisions.length > 0
                  ? `Dernière décision mémorisée : ${aiMemory.recentDecisions[0]?.summary ?? ''}`
                  : 'Aucune décision récente.'}
              </div>
              <Button type="submit" variant="primary" size="sm" isLoading={isSavingMemory}>
                Enregistrer la mémoire
              </Button>
            </div>
          </form>
        </section>
      )}

      {isTimetableImportOpen && (
        <TimetableImportPanel
          weekStart={currentWeekMonday}
          onClose={() => setIsTimetableImportOpen(false)}
          onImportCancelled={() => setIsTimetableImportOpen(false)}
          onImportSuccess={(result) => {
            setIsTimetableImportOpen(false);
            void sendMessage(
              `J’ai importé et validé mon emploi du temps (${result.createdCount} cours enregistrés). Analyse mes cours et mes créneaux disponibles.`,
              ['schedule', 'today', 'tasks'],
            );
          }}
        />
      )}

      {/* Sélecteur mobile (3 onglets) */}
      <nav
        aria-label="Vues mobiles du copilote"
        className="grid grid-cols-3 gap-1 rounded-2xl bg-zinc-100 p-1 lg:hidden dark:bg-zinc-900"
      >
        <button
          type="button"
          aria-pressed={mobileView === 'chat'}
          onClick={() => setMobileView('chat')}
          className={cn(
            'min-h-11 rounded-xl px-2.5 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400',
            mobileView === 'chat'
              ? 'bg-white text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100'
              : 'text-zinc-600 dark:text-zinc-400',
          )}
        >
          Discussion
        </button>
        <button
          type="button"
          aria-pressed={mobileView === 'rail' && railTab === 'proposals'}
          onClick={() => {
            setRailTab('proposals');
            setMobileView('rail');
          }}
          className={cn(
            'flex items-center justify-center gap-1.5 min-h-11 rounded-xl px-2.5 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400',
            mobileView === 'rail' && railTab === 'proposals'
              ? 'bg-white text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100'
              : 'text-zinc-600 dark:text-zinc-400',
          )}
        >
          <span>Actions</span>
          {pendingProposalsCount > 0 && (
            <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
              {pendingProposalsCount}
            </span>
          )}
        </button>
        <button
          type="button"
          aria-pressed={mobileView === 'rail' && railTab === 'reports'}
          onClick={() => {
            setRailTab('reports');
            setMobileView('rail');
          }}
          className={cn(
            'flex items-center justify-center gap-1.5 min-h-11 rounded-xl px-2.5 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400',
            mobileView === 'rail' && railTab === 'reports'
              ? 'bg-white text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100'
              : 'text-zinc-600 dark:text-zinc-400',
          )}
        >
          <span>Synthèses</span>
          {reports.length > 0 && (
            <span className="rounded-full bg-zinc-200 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-700 dark:bg-zinc-700 dark:text-zinc-200">
              {reports.length}
            </span>
          )}
        </button>
      </nav>

      {/* Studio adaptatif : pleine largeur sans distraction par défaut, tiroir contextuel à droite si actif */}
      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-12 lg:items-start">
        {/* Flux de discussion & compositeur */}
        <section
          aria-label="Fil de discussion du copilote"
          className={cn(
            'min-w-0 flex-col overflow-hidden rounded-2xl bg-white dark:bg-zinc-900',
            isDesktopRailVisible ? 'lg:col-span-7' : 'lg:col-span-12',
            mobileView === 'chat' ? 'flex' : 'hidden lg:flex',
          )}
        >
          <ScrollArea
            className="flex-1"
            viewportClassName={cn(
              'p-4 sm:p-6',
              (messages.length > 0 || isSending) &&
                'max-h-[58dvh] sm:max-h-[65dvh] overscroll-y-contain',
            )}
          >
            {messages.length === 0 && !isSending ? (
              <div className="mx-auto flex max-w-2xl flex-col justify-center py-4 sm:py-8">
                <div className="text-center">
                  <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-400">
                    <Icon icon={SparklesIcon} size={20} />
                  </div>
                  <h2 className="text-base font-semibold tracking-tight text-zinc-900 sm:text-lg dark:text-zinc-100">
                    Que souhaitez-vous organiser ?
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                    Planification, création de cours, priorisation ou suivi de compétences.
                  </p>
                </div>

                <div className="mt-4 grid grid-cols-1 gap-1.5 sm:grid-cols-2 sm:gap-2">
                  {STARTER_PROMPTS.map((item) => (
                    <button
                      key={item.title}
                      type="button"
                      onClick={() => handleUseStarterPrompt(item.prompt)}
                      className="flex min-h-16 items-center gap-3 rounded-xl bg-zinc-50 px-3 py-2.5 text-left transition-colors hover:bg-zinc-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:bg-zinc-800/70 dark:hover:bg-zinc-800 dark:focus-visible:outline-teal-400"
                    >
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white text-teal-700 dark:bg-zinc-900 dark:text-teal-400">
                        <Icon icon={item.icon} size={16} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13px] font-semibold text-zinc-900 dark:text-zinc-100">
                          {item.title}
                        </p>
                        <p className="line-clamp-1 text-xs text-zinc-500 dark:text-zinc-400">
                          {item.subtitle}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mx-auto w-full max-w-3xl space-y-6">
                {messages.map((message) => {
                  const isUser = message.role === 'user';
                  const hasMissingData =
                    !isUser &&
                    (Boolean(message.metadata.isEstimate) ||
                      (message.metadata.missingData?.length ?? 0) > 0);

                  if (isUser) {
                    return (
                      <div key={message.id} className="flex justify-end">
                        <div className="max-w-[82%] rounded-2xl rounded-tr-sm bg-zinc-900 px-4 py-2.5 text-sm leading-relaxed text-white dark:bg-zinc-100 dark:text-zinc-900">
                          <p className="whitespace-pre-wrap">{message.content}</p>
                        </div>
                      </div>
                    );
                  }

                  const messageProposals = proposalsByMessageId.get(message.id) ?? [];

                  return (
                    <div key={message.id} className="flex items-start gap-3">
                      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-400">
                        <Icon icon={AiChat02Icon} size={15} />
                      </div>
                      <div className="min-w-0 flex-1 space-y-2.5">
                        <div className="text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">
                          <StreamingAssistantContent
                            content={message.content}
                            isStreaming={streamingMessageId === message.id}
                            onComplete={() =>
                              setStreamingMessageId((prev) => (prev === message.id ? null : prev))
                            }
                          />
                        </div>

                        {messageProposals.length > 0 && (
                          <div className="space-y-2.5 pt-1">
                            {messageProposals.map((proposal) => (
                              <ProposalCard
                                key={proposal.id}
                                proposal={proposal}
                                onAccept={acceptProposal}
                                onReject={rejectProposal}
                                onUpdate={updateProposal}
                              />
                            ))}
                          </div>
                        )}

                        <div className="flex flex-wrap items-center gap-2 pt-0.5">
                          <span className="text-[11px] text-zinc-400 dark:text-zinc-500">
                            {formatDateTimeFr(message.createdAt)}
                          </span>

                          {hasMissingData && (
                            <span
                              title={
                                (message.metadata.missingData?.length ?? 0) > 0
                                  ? message.metadata.missingData?.join(' • ')
                                  : 'Réponse calculée à titre estimatif à partir des données disponibles.'
                              }
                              className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
                            >
                              <Icon
                                icon={Alert02Icon}
                                size={12}
                                className="shrink-0 text-amber-600 dark:text-amber-400"
                              />
                              <span>Indication AI-06 · Contexte partiel</span>
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}

                {isSending &&
                  pendingUserPrompt &&
                  !messages.some((m) => m.role === 'user' && m.content === pendingUserPrompt) && (
                    <div className="flex justify-end">
                      <div className="max-w-[82%] rounded-2xl rounded-tr-sm bg-zinc-900 px-4 py-2.5 text-sm leading-relaxed text-white dark:bg-zinc-100 dark:text-zinc-900">
                        <p className="whitespace-pre-wrap">{pendingUserPrompt}</p>
                      </div>
                    </div>
                  )}

                {isSending && (
                  <div
                    role="status"
                    aria-live="polite"
                    aria-label="Le Copilote réfléchit"
                    className="flex items-start gap-3"
                  >
                    <div className="relative mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white dark:bg-teal-500 dark:text-zinc-950">
                      <span className="absolute inset-0 animate-ping rounded-xl bg-teal-400/35" />
                      <Icon icon={SparklesIcon} size={14} className="relative" />
                    </div>

                    <div className="min-w-0 flex-1 space-y-2.5 rounded-2xl bg-zinc-50 p-3.5 dark:bg-zinc-800/70">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center gap-1">
                            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-600 [animation-delay:-0.25s] dark:bg-teal-400" />
                            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-600 [animation-delay:-0.12s] dark:bg-teal-400" />
                            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-600 dark:bg-teal-400" />
                          </span>
                          <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                            {THINKING_STEPS[thinkingStepIndex].label}
                          </span>
                        </div>
                        {thinkingElapsedSec >= 1 && (
                          <span className="rounded-lg bg-white px-2 py-0.5 text-[11px] font-medium tabular-nums text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
                            {thinkingElapsedSec} s
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-zinc-600 dark:text-zinc-300">
                        {THINKING_STEPS[thinkingStepIndex].detail}
                      </p>

                      <div className="flex flex-wrap gap-1.5 pt-0.5">
                        {THINKING_STEPS.map((step, index) => {
                          const isDone = index < thinkingStepIndex;
                          const isCurrent = index === thinkingStepIndex;
                          return (
                            <div
                              key={step.label}
                              className={cn(
                                'inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] transition-colors',
                                isCurrent
                                  ? 'bg-teal-50/90 font-semibold text-teal-900 dark:bg-teal-950/50 dark:text-teal-200'
                                  : isDone
                                    ? 'bg-white/70 font-medium text-emerald-700 dark:bg-zinc-900/60 dark:text-emerald-400'
                                    : 'text-zinc-400 dark:text-zinc-500',
                              )}
                            >
                              {isDone ? (
                                <Icon icon={CheckmarkCircle02Icon} size={12} className="shrink-0" />
                              ) : isCurrent ? (
                                <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-teal-600 dark:bg-teal-400" />
                              ) : (
                                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-300 dark:bg-zinc-600" />
                              )}
                              <span className="truncate">{step.label}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </ScrollArea>

          {/* Barre mobile d'accès rapide aux validations */}
          {pendingProposalsCount > 0 && (
            <div className="mx-4 mb-2 flex items-center justify-between gap-2 rounded-xl bg-amber-50/90 px-3.5 py-2 text-xs text-amber-900 lg:hidden dark:bg-amber-950/40 dark:text-amber-200">
              <span className="font-medium">
                {pendingProposalsCount === 1
                  ? '1 action en attente de validation'
                  : `${pendingProposalsCount} actions en attente de validation`}
              </span>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  setRailTab('proposals');
                  setMobileView('rail');
                }}
              >
                Examiner
              </Button>
            </div>
          )}

          {/* Compositeur flottant centré (zéro bordure) */}
          <form onSubmit={handleFormSubmit} className="p-3 pt-1.5 sm:px-6 sm:pb-5">
            <div className="mx-auto w-full max-w-3xl rounded-2xl bg-zinc-50 p-2.5 transition-colors focus-within:bg-zinc-100/90 sm:p-3 dark:bg-zinc-800/70 dark:focus-within:bg-zinc-800">
              <label htmlFor="copilot-prompt" className="sr-only">
                Votre message au Copilote
              </label>
              <textarea
                id="copilot-prompt"
                ref={textareaRef}
                rows={2}
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                onKeyDown={handleTextareaKeyDown}
                placeholder="Demandez au Copilote d’organiser, prioriser ou planifier…"
                className="w-full resize-none bg-transparent text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none dark:text-zinc-100 dark:placeholder:text-zinc-500"
              />

              <div className="mt-2 flex items-center justify-between gap-2">
                <div className="no-scrollbar flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto">
                  <select
                    aria-label="Périmètre du contexte transmis"
                    value={selectedScope}
                    onChange={(e) => setSelectedScope(e.target.value as AiContextScope)}
                    className="min-h-7 max-w-[150px] shrink-0 truncate rounded-xl bg-white px-2.5 py-1 text-xs font-medium text-zinc-700 focus-visible:outline-2 focus-visible:outline-teal-600 sm:max-w-none dark:bg-zinc-900 dark:text-zinc-200"
                  >
                    {SCOPE_OPTIONS.map((scope) => (
                      <option key={scope.value} value={scope.value}>
                        {scope.label}
                      </option>
                    ))}
                  </select>

                  <button
                    type="button"
                    onClick={() => setIsTimetableImportOpen((prev) => !prev)}
                    className={cn(
                      'inline-flex h-7 shrink-0 items-center gap-1.5 rounded-xl px-2.5 text-xs font-medium transition-colors',
                      isTimetableImportOpen
                        ? 'bg-teal-700 text-white dark:bg-teal-500 dark:text-zinc-950'
                        : 'bg-white text-zinc-600 hover:text-zinc-900 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100',
                    )}
                  >
                    <Icon icon={Calendar03Icon} size={13} />
                    Emploi du temps
                  </button>

                  <Link
                    to="/settings"
                    className="inline-flex h-7 shrink-0 items-center gap-1.5 rounded-xl bg-white px-2.5 text-xs font-medium text-zinc-600 transition-colors hover:text-zinc-900 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
                  >
                    <Icon icon={Settings02Icon} size={13} />
                    Consignes
                  </Link>
                </div>

                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  aria-label="Envoyer au Copilote"
                  isLoading={isSending}
                  disabled={!promptText.trim() || isSending}
                  className="h-11 w-11 min-h-11 min-w-11 shrink-0 rounded-xl px-0"
                >
                  {!isSending && <Icon icon={ArrowUp02Icon} size={16} />}
                </Button>
              </div>
            </div>
          </form>
        </section>

        {/* Tiroir contextuel droit : affiché uniquement lorsqu'utile ou ouvert */}
        <aside
          aria-label="Panneau d’actions et de synthèses"
          className={cn(
            'min-w-0 flex-col gap-3.5 rounded-2xl bg-white p-4 sm:p-5 lg:col-span-5 dark:bg-zinc-900',
            mobileView === 'rail'
              ? 'flex'
              : isDesktopRailVisible
                ? 'hidden lg:flex'
                : 'hidden',
          )}
        >
          {/* Sélecteur de panneau desktop */}
          <div className="hidden items-center justify-between gap-2 lg:flex">
            <div
              role="tablist"
              aria-label="Onglets du panneau latéral"
              className="grid flex-1 grid-cols-2 gap-1 rounded-xl bg-zinc-100 p-1 dark:bg-zinc-800/80"
            >
              <button
                type="button"
                role="tab"
                aria-selected={railTab === 'proposals'}
                onClick={() => setRailTab('proposals')}
                className={cn(
                  'flex items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors',
                  railTab === 'proposals'
                    ? 'bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100'
                    : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200',
                )}
              >
                <span>Actions</span>
                {pendingProposalsCount > 0 && (
                  <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                    {pendingProposalsCount}
                  </span>
                )}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={railTab === 'reports'}
                onClick={() => setRailTab('reports')}
                className={cn(
                  'flex items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors',
                  railTab === 'reports'
                    ? 'bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100'
                    : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200',
                )}
              >
                <span>Synthèses</span>
                {reports.length > 0 && (
                  <span className="rounded-full bg-zinc-200 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-700 dark:bg-zinc-700 dark:text-zinc-200">
                    {reports.length}
                  </span>
                )}
              </button>
            </div>
            <button
              type="button"
              onClick={() => {
                setIsDesktopRailDismissed(true);
                setIsDesktopRailForcedOpen(false);
              }}
              className="rounded-xl px-2 py-1 text-xs font-medium text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
            >
              Masquer
            </button>
          </div>

          {railTab === 'proposals' ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-1.5">
                {PROPOSAL_FILTERS.map((filter) => {
                  const isActive = proposalFilter === filter.value;
                  return (
                    <button
                      key={filter.value}
                      type="button"
                      onClick={() => setProposalFilter(filter.value)}
                      className={cn(
                        'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                        isActive
                          ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                          : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700',
                      )}
                    >
                      {filter.label}
                    </button>
                  );
                })}
              </div>

              {filteredProposals.length === 0 || proposalsByMessageId.size > 0 ? (
                <EmptyState
                  icon={<Icon icon={CheckmarkSquare02Icon} size={18} className="text-zinc-500 dark:text-zinc-400" />}
                  title={
                    proposalsByMessageId.size > 0
                      ? 'Les actions proposées sont affichées directement dans la discussion'
                      : 'Aucune action dans cette vue'
                  }
                />
              ) : (
                <div className="space-y-3">
                  {filteredProposals.map((proposal) => (
                    <ProposalCard
                      key={proposal.id}
                      proposal={proposal}
                      onAccept={acceptProposal}
                      onReject={rejectProposal}
                      onUpdate={updateProposal}
                    />
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {reports.length === 0 ? (
                <EmptyState
                  icon={<Icon icon={File02Icon} size={18} className="text-zinc-500 dark:text-zinc-400" />}
                  title="Aucune synthèse générée"
                />
              ) : (
                reports.map((report) => {
                  const isDaily = report.type === 'daily_briefing';
                  const missing = report.metadata?.missingData ?? [];
                  return (
                    <article
                      key={report.id}
                      className="rounded-2xl bg-zinc-50 p-4 dark:bg-zinc-800/70"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <Badge variant={isDaily ? 'primary' : 'neutral'}>
                          {isDaily ? 'Briefing quotidien' : 'Bilan hebdomadaire'}
                        </Badge>
                        <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                          {formatDateTimeFr(report.createdAt)}
                        </span>
                      </div>

                      <MarkdownContent content={report.content} className="mt-3" />

                      {(report.metadata?.isEstimate || missing.length > 0) && missing.length > 0 && (
                        <p className="mt-2.5 rounded-xl bg-amber-50/90 px-3 py-2 text-xs text-amber-900 dark:bg-amber-950/35 dark:text-amber-200">
                          Données manquantes : {missing.join(' • ')}
                        </p>
                      )}
                    </article>
                  );
                })
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
