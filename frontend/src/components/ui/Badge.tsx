import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '../../lib/cn';

export type BadgeVariant = 'neutral' | 'primary' | 'success' | 'warning' | 'danger';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  children: ReactNode;
}

const badgeVariantClasses: Record<BadgeVariant, string> = {
  neutral: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300',
  primary: 'bg-teal-50 text-teal-800 dark:bg-teal-950/70 dark:text-teal-300',
  success: 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300',
  warning: 'bg-amber-50 text-amber-900 dark:bg-amber-950/70 dark:text-amber-300',
  danger: 'bg-rose-50 text-rose-800 dark:bg-rose-950/70 dark:text-rose-300',
};

/**
 * Pastille sémantique sans bordure ni ombre.
 */
export function Badge({ variant = 'neutral', className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium tracking-tight',
        badgeVariantClasses[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
