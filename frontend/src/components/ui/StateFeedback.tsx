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

export function LoadingState({ message = 'Chargement…', className }: LoadingStateProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'ui-loading-state flex flex-col items-center justify-center gap-2.5 px-6 py-9 text-center',
        className,
      )}
    >
      <Icon icon={Loading03Icon} size={20} className="ui-loading-indicator animate-spin" />
      <p className="text-[13px] font-medium leading-[19px]">{message}</p>
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

export function EmptyState({ title, description, icon, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'ui-empty-state flex flex-col items-center justify-center gap-2.5 px-5 py-7 text-center',
        className,
      )}
    >
      <div className="ui-empty-icon flex h-10 w-10 items-center justify-center rounded-lg">
        {icon ?? <Icon icon={InboxIcon} size={18} />}
      </div>
      <div className="max-w-sm space-y-1">
        <h3 className="ui-empty-title">{title}</h3>
        {description && <p className="ui-empty-description">{description}</p>}
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
        'ui-error-state flex flex-col items-start justify-between gap-3 px-4 py-3 sm:flex-row sm:items-center',
        className,
      )}
    >
      <div className="flex items-start gap-2.5">
        <Icon icon={AlertCircleIcon} size={18} className="mt-0.5 shrink-0" />
        <div className="space-y-0.5">
          <p className="text-[13px] font-semibold leading-[19px]">{title}</p>
          <p className="text-[13px] leading-[19px]">{message}</p>
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

export function SuccessBanner({ message, onDismiss, className }: SuccessBannerProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'ui-success-banner flex items-center justify-between gap-3 px-4 py-2.5',
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <Icon icon={CheckmarkCircle02Icon} size={18} className="shrink-0" />
        <p className="text-[13px] font-medium leading-[19px]">{message}</p>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Fermer la confirmation"
          className="ui-icon-button shrink-0 transition-colors hover:bg-black/5 dark:hover:bg-white/10"
        >
          <Icon icon={Cancel01Icon} size={16} />
        </button>
      )}
    </div>
  );
}
