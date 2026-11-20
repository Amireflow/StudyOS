import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { BadgeVariant } from '../ui/Badge';
import { buttonClasses } from '../ui/Button';
import { Card, CardContent } from '../ui/Card';
import { EmptyState } from '../ui/StateFeedback';
import { PageHeader } from './PageHeader';

export interface FeatureScaffoldProps {
  title: string;
  description: string;
  badgeLabel: string;
  badgeVariant?: BadgeVariant;
  icon: ReactNode;
  emptyTitle: string;
  emptyDescription: string;
  nextStepHint?: string;
}

/**
 * Gabarit partagé pour présenter les écrans du MVP dont les données
 * et interactions seront branchées dans les lots suivants.
 */
export function FeatureScaffold({
  title,
  description,
  badgeLabel,
  badgeVariant = 'neutral',
  icon,
  emptyTitle,
  emptyDescription,
  nextStepHint,
}: FeatureScaffoldProps) {
  return (
    <div>
      <PageHeader
        title={title}
        description={description}
        badge={{ label: badgeLabel, variant: badgeVariant }}
      />

      <Card>
        <CardContent className="space-y-4 py-6">
          <EmptyState
            icon={icon}
            title={emptyTitle}
            description={emptyDescription}
            action={
              <Link to="/" className={buttonClasses('secondary', 'sm')}>
                Retour au tableau de bord
              </Link>
            }
          />
          {nextStepHint && (
            <p className="text-center text-xs text-zinc-500 dark:text-zinc-400">{nextStepHint}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
