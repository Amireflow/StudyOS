import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '../../lib/cn';

export type BadgeVariant = 'neutral' | 'primary' | 'success' | 'warning' | 'danger';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  children: ReactNode;
}

/**
 * Badge sémantique : statut, catégorie ou compteur secondaire.
 */
export function Badge({ variant = 'neutral', className, children, ...props }: BadgeProps) {
  return (
    <span className={cn('ui-badge', 'ui-badge--' + variant, className)} {...props}>
      {children}
    </span>
  );
}
