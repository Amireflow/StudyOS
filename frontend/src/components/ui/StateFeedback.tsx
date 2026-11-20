import type { ReactNode } from 'react';
import {
  AlertCircleIcon,
  Cancel01Icon,
  CheckmarkCircle02Icon,
  InboxIcon,
  Loading03Icon,
} from '@hugeicons/core-free-icons';
import { cn } from '../../lib/cn';
import { Button } from './Button';
import { Icon } from './Icon';

export interface LoadingStateProps {
  message?: string;
  className?: string;
}

/**
 * État de chargement accessible (`role="status"`).
 */
export function LoadingState({ message = 'Chargement…', className }: LoadingStateProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex flex-col items-center justify-center gap-2.5 rounded-2xl bg-white px-6 py-9 text-center dark:bg-zinc-900',
        className,
      )}
    >
      <Icon icon={Loading03Icon} size={20} className="animate-spin text-teal-700 dark:text-teal-400" />
      <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{message}</p>
    </div>
  );
}

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

/**
 * État vide épuré sans bordure pointillée ni ombre.
 */
export function EmptyState({ title, description, icon, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-2.5 rounded-xl bg-zinc-50/80 px-5 py-7 text-center dark:bg-zinc-800/50',
        className,
      )}
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
        {icon ?? <Icon icon={InboxIcon} size={17} />}
      </div>
      <div className="max-w-sm space-y-0.5">
        <h3 className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">{title}</h3>
        {description && <p className="text-xs text-zinc-500 dark:text-zinc-400">{description}</p>}
      </div>
      {action && <div className="pt-1">{action}</div>}
    </div>
  );
}

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

/**
 * État d'erreur explicite (`role="alert"`) avec possibilité de relance.
 */
export function ErrorState({
  title = 'Erreur',
  message,
  onRetry,
  retryLabel = 'Réessayer',
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-start justify-between gap-3 rounded-xl bg-rose-50 px-4 py-3 sm:flex-row sm:items-center dark:bg-rose-950/50',
        className,
      )}
    >
      <div className="flex items-start gap-2.5">
        <Icon icon={AlertCircleIcon} size={17} className="mt-0.5 shrink-0 text-rose-600 dark:text-rose-400" />
        <div className="space-y-0.5">
          <p className="text-xs font-semibold text-rose-950 dark:text-rose-200">{title}</p>
          <p className="text-xs text-rose-800 dark:text-rose-300">{message}</p>
        </div>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  );
}

export interface SuccessBannerProps {
  message: string;
  onDismiss?: () => void;
  className?: string;
}

/**
 * Bannière de confirmation visuelle sans bordure.
 */
export function SuccessBanner({ message, onDismiss, className }: SuccessBannerProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex items-center justify-between gap-3 rounded-xl bg-emerald-50 px-4 py-2.5 text-emerald-950 dark:bg-emerald-950/50 dark:text-emerald-200',
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <Icon icon={CheckmarkCircle02Icon} size={17} className="shrink-0 text-emerald-700 dark:text-emerald-400" />
        <p className="text-xs font-medium">{message}</p>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Fermer la confirmation"
          className="rounded-md p-1 text-emerald-800 transition-colors hover:bg-emerald-100 dark:text-emerald-300 dark:hover:bg-emerald-900/60 cursor-pointer"
        >
          <Icon icon={Cancel01Icon} size={14} />
        </button>
      )}
    </div>
  );
}
