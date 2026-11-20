import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Loading03Icon } from '@hugeicons/core-free-icons';
import { cn } from '../../lib/cn';
import { Icon } from './Icon';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  children: ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-zinc-900 text-white hover:bg-zinc-800 active:bg-zinc-950 dark:bg-zinc-100 dark:text-zinc-950 dark:hover:bg-zinc-200 dark:active:bg-white',
  secondary:
    'bg-zinc-100 text-zinc-800 hover:bg-zinc-200/80 active:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-700/80 dark:active:bg-zinc-700',
  ghost:
    'bg-transparent text-zinc-600 hover:bg-zinc-100/80 hover:text-zinc-900 active:bg-zinc-200/60 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100 dark:active:bg-zinc-700/60',
  danger: 'bg-rose-600 text-white hover:bg-rose-700 active:bg-rose-800 dark:hover:bg-rose-500',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'min-h-8 px-3 py-1.5 text-xs rounded-lg gap-1.5',
  md: 'min-h-10 px-4 py-2 text-sm rounded-lg gap-2',
};

export function buttonClasses(variant: ButtonVariant = 'primary', size: ButtonSize = 'md'): string {
  return cn(
    'inline-flex items-center justify-center font-medium tracking-tight transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
    variantClasses[variant],
    sizeClasses[size],
  );
}

/**
 * Bouton réutilisable sans bordure ni ombre (surfaces ton sur ton).
 */
export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  type = 'button',
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      className={cn(buttonClasses(variant, size), className)}
      {...props}
    >
      {isLoading && <Icon icon={Loading03Icon} size={16} className="animate-spin" />}
      {children}
    </button>
  );
}
