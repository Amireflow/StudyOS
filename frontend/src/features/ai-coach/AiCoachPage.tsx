import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import {
  AiChat02Icon,
  Alert02Icon,
  ArrowUp02Icon,
  BookOpen01Icon,
  Calendar03Icon,
  CheckmarkSquare02Icon,
  File02Icon,
  HistoryIcon,
  MessageAdd01Icon,
  Settings02Icon,
  ShieldCheckIcon,
  SlidersHorizontalIcon,
  Target02Icon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { InlineConfirm } from '../../components/ui/FormFields';
import { Icon, type IconSvgElement } from '../../components/ui/Icon';
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/StateFeedback';
import { cn } from '../../lib/cn';
import { formatDateTimeFr } from '../../lib/date';
import { useAiStore } from '../../state/AiStoreContext';
import type { AiContextScope } from '../../types/domain';
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
];

export function AiCoachPage() {
  const {
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
  } = useAiStore();

  const [promptText, setPromptText] = useState('');
  const [selectedScope, setSelectedScope] = useState<AiContextScope>('auto');
  const [proposalFilter, setProposalFilter] = useState<ProposalFilter>('all');
  const [railTab, setRailTab] = useState<RailTab>('proposals');
  const [mobileView, setMobileView] = useState<MobileView>('chat');
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isGeneratingBriefing, setIsGeneratingBriefing] = useState(false);
  const [isGeneratingWeekly, setIsGeneratingWeekly] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

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

  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
    }
  }, [activeConversationId, messages.length]);

  async function submitPrompt() {
    const trimmed = promptText.trim();
    if (!trimmed || isSending) return;
    setIsSending(true);
    try {
      const ok = await sendMessage(trimmed, [selectedScope]);
      if (ok) {
        setPromptText('');
        setRailTab('proposals');
      }
    } finally {
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
    <div className="space-y-5">
      {/* En-tête studio */}
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-teal-700 text-white dark:bg-teal-600">
              <Icon icon={AiChat02Icon} size={18} />
            </div>
            <div className="min-w-0">
              <h1 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
                Copilote
              </h1>
              <p className="truncate text-xs text-zinc-500 dark:text-zinc-400">
                {activeConversation ? activeConversation.title : 'Planification, arbitrage et synthèses'}
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {conversations.length > 0 && (
            <Button
              type="button"
              variant={isHistoryOpen ? 'primary' : 'secondary'}
              size="sm"
              aria-label="Historique des conversations"
              aria-expanded={isHistoryOpen}
              onClick={() => {
                setIsHistoryOpen((prev) => !prev);
                setIsToolsOpen(false);
              }}
            >
              <Icon icon={HistoryIcon} size={15} />
              Historique
            </Button>
          )}

          <Button
            type="button"
            variant="secondary"
            size="sm"
            isLoading={isGeneratingBriefing}
            onClick={() => void handleGenerateBriefing()}
          >
            <Icon icon={File02Icon} size={15} />
            Briefing du jour
          </Button>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            isLoading={isGeneratingWeekly}
            onClick={() => void handleGenerateWeekly()}
          >
            <Icon icon={File02Icon} size={15} />
            Bilan hebdo
          </Button>

          <Button
            type="button"
            variant={isToolsOpen ? 'primary' : 'ghost'}
            size="sm"
            aria-expanded={isToolsOpen}
            onClick={() => {
              setIsToolsOpen((prev) => !prev);
              setIsHistoryOpen(false);
            }}
          >
            <Icon icon={SlidersHorizontalIcon} size={15} />
            Outils ({tools.length})
          </Button>

          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => void handleNewConversation()}
          >
            <Icon icon={MessageAdd01Icon} size={15} />
            Nouvelle conversation
          </Button>
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
                Validation requise avant toute action
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
                <p className="mt-1 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
                  {tool.description}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Sélecteur mobile (3 onglets) */}
      <nav
        aria-label="Vues mobiles du copilote"
        className="grid grid-cols-3 gap-1 rounded-2xl bg-zinc-100 p-1 lg:hidden dark:bg-zinc-900"
      >
        <button
          type="button"
          onClick={() => setMobileView('chat')}
          className={cn(
            'rounded-xl px-3 py-2 text-xs font-semibold transition-colors',
            mobileView === 'chat'
              ? 'bg-white text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100'
              : 'text-zinc-600 dark:text-zinc-400',
          )}
        >
          Discussion
        </button>
        <button
          type="button"
          onClick={() => {
            setRailTab('proposals');
            setMobileView('rail');
          }}
          className={cn(
            'flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold transition-colors',
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
          onClick={() => {
            setRailTab('reports');
            setMobileView('rail');
          }}
          className={cn(
            'flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold transition-colors',
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

      {/* Studio 2 colonnes : flux de conversation + panneau latéral unique */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 lg:items-start">
        {/* Colonne gauche : fil de discussion & compositeur */}
        <section
          aria-label="Fil de discussion du copilote"
          className={cn(
            'flex-col overflow-hidden rounded-2xl bg-white lg:col-span-7 lg:min-h-[600px] dark:bg-zinc-900',
            mobileView === 'chat' ? 'flex' : 'hidden lg:flex',
          )}
        >
          <div className="flex-1 space-y-5 p-4 sm:p-6">
            {messages.length === 0 ? (
              <div className="py-4 sm:py-6">
                <div className="max-w-lg">
                  <h2 className="text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
                    Que souhaitez-vous organiser ?
                  </h2>
                  <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                    Décrivez votre objectif du moment ou démarrez avec une demande rapide.
                  </p>
                </div>

                <div className="mt-5 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                  {STARTER_PROMPTS.map((item) => (
                    <button
                      key={item.title}
                      type="button"
                      onClick={() => handleUseStarterPrompt(item.prompt)}
                      className="flex items-start gap-3 rounded-2xl bg-zinc-50 p-3.5 text-left transition-colors hover:bg-zinc-100 dark:bg-zinc-800/70 dark:hover:bg-zinc-800"
                    >
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white text-teal-700 dark:bg-zinc-900 dark:text-teal-400">
                        <Icon icon={item.icon} size={16} />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                          {item.title}
                        </span>
                        <span className="mt-0.5 block text-xs text-zinc-500 dark:text-zinc-400">
                          {item.subtitle}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-5">
                {messages.map((message) => {
                  const isUser = message.role === 'user';
                  const hasMissingData =
                    !isUser &&
                    (Boolean(message.metadata.isEstimate) ||
                      (message.metadata.missingData?.length ?? 0) > 0);

                  if (isUser) {
                    return (
                      <div key={message.id} className="flex justify-end">
                        <div className="max-w-[85%] rounded-2xl bg-zinc-900 px-4 py-3 text-sm leading-relaxed text-white dark:bg-zinc-100 dark:text-zinc-900">
                          <p className="whitespace-pre-wrap">{message.content}</p>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div key={message.id} className="flex items-start gap-3">
                      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700 dark:bg-teal-950/50 dark:text-teal-400">
                        <Icon icon={AiChat02Icon} size={15} />
                      </div>
                      <div className="min-w-0 flex-1 space-y-2.5">
                        <MarkdownContent content={message.content} />

                        {hasMissingData && (
                          <div className="flex items-start gap-2 rounded-xl bg-amber-50/90 px-3 py-2 text-xs leading-relaxed text-amber-900 dark:bg-amber-950/35 dark:text-amber-200">
                            <Icon icon={Alert02Icon} size={15} className="mt-0.5 shrink-0" />
                            <div>
                              <span className="font-semibold">Indication AI-06 — Données partielles :</span>{' '}
                              {(message.metadata.missingData?.length ?? 0) > 0
                                ? message.metadata.missingData?.join(' • ')
                                : 'Réponse calculée à titre estimatif à partir des données disponibles.'}
                            </div>
                          </div>
                        )}

                        <p className="text-[11px] text-zinc-400 dark:text-zinc-500">
                          {formatDateTimeFr(message.createdAt)}
                        </p>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

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

          {/* Compositeur intégré */}
          <form onSubmit={handleFormSubmit} className="p-4 pt-2 sm:px-6 sm:pb-6">
            <div className="rounded-2xl bg-zinc-50 p-3 transition-colors focus-within:bg-zinc-100/90 dark:bg-zinc-800/70 dark:focus-within:bg-zinc-800">
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

              <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    aria-label="Périmètre du contexte transmis"
                    value={selectedScope}
                    onChange={(e) => setSelectedScope(e.target.value as AiContextScope)}
                    className="h-8 rounded-xl bg-white px-2.5 text-xs font-medium text-zinc-700 focus-visible:outline-2 focus-visible:outline-teal-600 dark:bg-zinc-900 dark:text-zinc-200"
                  >
                    {SCOPE_OPTIONS.map((scope) => (
                      <option key={scope.value} value={scope.value}>
                        {scope.label}
                      </option>
                    ))}
                  </select>

                  <Link
                    to="/settings"
                    className="inline-flex h-8 items-center gap-1.5 rounded-xl bg-white px-2.5 text-xs font-medium text-zinc-600 transition-colors hover:text-zinc-900 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
                  >
                    <Icon icon={Settings02Icon} size={14} />
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
                  className="h-8 w-8 rounded-xl px-0"
                >
                  {!isSending && <Icon icon={ArrowUp02Icon} size={16} />}
                </Button>
              </div>
            </div>
          </form>
        </section>

        {/* Colonne droite : actions proposées et synthèses (DOM unique) */}
        <aside
          aria-label="Panneau d’actions et de synthèses"
          className={cn(
            'flex-col gap-4 rounded-2xl bg-white p-4 sm:p-5 lg:col-span-5 dark:bg-zinc-900',
            mobileView === 'rail' ? 'flex' : 'hidden lg:flex',
          )}
        >
          {/* Sélecteur de panneau desktop */}
          <div
            role="tablist"
            aria-label="Onglets du panneau latéral"
            className="hidden grid-cols-2 gap-1 rounded-xl bg-zinc-100 p-1 lg:grid dark:bg-zinc-800/80"
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

              {filteredProposals.length === 0 ? (
                <EmptyState
                  icon={<Icon icon={CheckmarkSquare02Icon} size={18} className="text-zinc-500 dark:text-zinc-400" />}
                  title="Aucune action dans cette vue"
                  description="Les actions suggérées par le Copilote attendent toujours votre validation ici."
                />
              ) : (
                <div className="space-y-3">
                  {filteredProposals.map((proposal) => (
                    <ProposalCard
                      key={proposal.id}
                      proposal={proposal}
                      onAccept={acceptProposal}
                      onReject={rejectProposal}
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
                  description="Utilisez Briefing du jour ou Bilan hebdo en haut de l’écran pour créer un rapport."
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
