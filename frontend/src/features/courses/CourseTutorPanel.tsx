import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import {
  AiChat02Icon,
  BulbIcon,
  HelpCircleIcon,
  SentIcon,
  SparklesIcon,
} from '@hugeicons/core-free-icons';
import { Icon } from '../../components/ui/Icon';
import { MarkdownContent } from '../../components/ui/MarkdownContent';
import { cn } from '../../lib/cn';
import type { CourseLessonTutorAskInput } from '../../lib/coursesApi';
import type { CourseTutorMessage, CourseTutorQuickAction } from '../../types/domain';

interface CourseTutorPanelProps {
  lessonTitle: string;
  stepIndex: number;
  stepTitle: string;
  stepContent: string;
  messages: CourseTutorMessage[];
  onAsk: (input: CourseLessonTutorAskInput) => Promise<boolean>;
}

const QUICK_ACTIONS: Array<{
  action: CourseTutorQuickAction;
  label: string;
  prompt: string;
  icon: typeof BulbIcon;
}> = [
  {
    action: 'simplify',
    label: 'Explique plus simplement',
    prompt: 'Explique-moi cette étape plus simplement, avec une analogie.',
    icon: BulbIcon,
  },
  {
    action: 'example',
    label: 'Autre exemple',
    prompt: 'Donne-moi un autre exemple concret pour cette étape.',
    icon: SparklesIcon,
  },
  {
    action: 'quiz',
    label: 'Teste-moi',
    prompt: 'Pose-moi une question rapide pour vérifier que j’ai compris.',
    icon: HelpCircleIcon,
  },
];

export function CourseTutorPanel({
  lessonTitle,
  stepIndex,
  stepTitle,
  stepContent,
  messages,
  onAsk,
}: CourseTutorPanelProps) {
  const [draft, setDraft] = useState('');
  const [pending, setPending] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' });
  }, [messages.length, pending]);

  const send = async (message: string, quickAction: CourseTutorQuickAction = 'custom') => {
    const text = message.trim();
    if (!text || pending) return;
    setPending(text);
    setDraft('');
    const ok = await onAsk({
      message: text,
      quickAction,
      stepIndex,
      stepTitle,
      stepContent: stepContent.slice(0, 5800),
    });
    if (!ok) setDraft(text);
    setPending(null);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void send(draft);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void send(draft);
    }
  };

  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant');
  const followUps = !pending ? (lastAssistant?.followUpPrompts ?? []).slice(0, 3) : [];

  return (
    <section
      aria-label="Tuteur du chapitre"
      className="min-w-0 max-w-full space-y-3 rounded-2xl bg-zinc-50 p-3.5 sm:p-4 dark:bg-zinc-800/60"
    >
      <header className="flex items-center gap-2">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white">
          <Icon icon={AiChat02Icon} size={16} />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Tuteur du chapitre</p>
          <p className="truncate text-[11px] text-zinc-500 dark:text-zinc-400">
            Pose tes questions sur « {stepTitle || lessonTitle} »
          </p>
        </div>
      </header>

      {(messages.length > 0 || pending) && (
        <div className="max-h-[52dvh] min-w-0 space-y-2.5 overflow-y-auto overscroll-contain pr-0.5">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn('flex min-w-0', msg.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              <div
                className={cn(
                  'min-w-0 max-w-[92%] break-words rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed',
                  msg.role === 'user'
                    ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950'
                    : 'bg-white text-zinc-800 dark:bg-zinc-900 dark:text-zinc-200',
                )}
              >
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <MarkdownContent content={msg.content} />
                )}
              </div>
            </div>
          ))}
          {pending && (
            <>
              <div className="flex justify-end">
                <div className="max-w-[92%] break-words rounded-2xl bg-zinc-900 px-3.5 py-2.5 text-sm text-white dark:bg-zinc-100 dark:text-zinc-950">
                  {pending}
                </div>
              </div>
              <div className="flex justify-start" aria-live="polite">
                <div className="rounded-2xl bg-white px-3.5 py-2.5 text-xs text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
                  Le tuteur réfléchit…
                </div>
              </div>
            </>
          )}
          <div ref={endRef} />
        </div>
      )}

      <div className="no-scrollbar flex min-w-0 gap-1.5 overflow-x-auto pb-0.5">
        {(followUps.length > 0
          ? followUps.map((prompt) => ({
              key: prompt,
              label: prompt,
              icon: null as typeof BulbIcon | null,
              onClick: () => void send(prompt),
            }))
          : QUICK_ACTIONS.map((qa) => ({
              key: qa.action as string,
              label: qa.label,
              icon: qa.icon as typeof BulbIcon | null,
              onClick: () => void send(qa.prompt, qa.action),
            }))
        ).map((chip) => (
          <button
            key={chip.key}
            type="button"
            disabled={Boolean(pending)}
            onClick={chip.onClick}
            className="inline-flex shrink-0 cursor-pointer items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
          >
            {chip.icon ? <Icon icon={chip.icon} size={13} /> : null}
            {chip.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex min-w-0 items-end gap-2">
        <label htmlFor={`tutor-input-${stepIndex}`} className="sr-only">
          Question au tuteur
        </label>
        <textarea
          id={`tutor-input-${stepIndex}`}
          rows={1}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Pose une question sur cette étape…"
          className="max-h-32 min-h-[44px] min-w-0 flex-1 resize-none rounded-2xl bg-white px-3.5 py-2.5 text-base text-zinc-900 outline-none placeholder:text-zinc-400 focus:ring-2 focus:ring-teal-500/40 sm:text-sm dark:bg-zinc-900 dark:text-zinc-100"
        />
        <button
          type="submit"
          aria-label="Envoyer la question au tuteur"
          disabled={!draft.trim() || Boolean(pending)}
          className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-2xl bg-teal-600 text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Icon icon={SentIcon} size={17} />
        </button>
      </form>
    </section>
  );
}
