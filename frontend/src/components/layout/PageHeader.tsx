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
 * En-tête de page avec titre stable et description non tronquée.
 */
export function PageHeader({ title, description, badge, actions }: PageHeaderProps) {
  return (
    <header className="mb-4 flex flex-wrap items-start justify-between gap-3 sm:mb-6">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="ui-page-title">{title}</h1>
          {badge && <Badge variant={badge.variant ?? 'neutral'}>{badge.label}</Badge>}
        </div>
        {description && <p className="ui-page-description">{description}</p>}
      </div>
      {actions && (
        <div className="no-scrollbar flex max-w-full items-center gap-2 overflow-x-auto sm:shrink-0 sm:flex-wrap sm:overflow-visible">
          {actions}
        </div>
      )}
    </header>
  );
}
