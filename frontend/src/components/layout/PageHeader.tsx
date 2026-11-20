import type { ReactNode } from 'react';
import { Badge, type BadgeVariant } from '../ui/Badge';

export interface PageHeaderProps {
  title: string;
  description?: string;
  badge?: {
    label: string;
    variant?: BadgeVariant;
  };
  actions?: ReactNode;
}

/**
 * En-tête épuré sans bordure ni surcharge textuelle.
 */
export function PageHeader({ title, description, badge, actions }: PageHeaderProps) {
  return (
    <header className="mb-3 flex flex-wrap items-center justify-between gap-2.5 sm:mb-5">
      <div className="min-w-0 space-y-0.5">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 sm:text-2xl dark:text-zinc-50">
            {title}
          </h1>
          {badge && <Badge variant={badge.variant ?? 'neutral'}>{badge.label}</Badge>}
        </div>
        {description && (
          <p className="truncate text-xs text-zinc-500 dark:text-zinc-400">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="no-scrollbar flex max-w-full items-center gap-1.5 overflow-x-auto sm:shrink-0 sm:flex-wrap sm:overflow-visible">
          {actions}
        </div>
      )}
    </header>
  );
}
