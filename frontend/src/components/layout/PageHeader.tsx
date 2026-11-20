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
    <header className="mb-4 flex flex-col gap-3 sm:mb-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="space-y-0.5">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 sm:text-2xl dark:text-zinc-50">
            {title}
          </h1>
          {badge && <Badge variant={badge.variant ?? 'neutral'}>{badge.label}</Badge>}
        </div>
        {description && (
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2 sm:shrink-0">{actions}</div>
      )}
    </header>
  );
}
