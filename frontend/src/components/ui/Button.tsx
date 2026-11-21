import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Loading03Icon } from '@hugeicons/core-free-icons';
import { cn } from '../../lib/cn';
import { Icon } from './Icon';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'link';
export type ButtonSize = 'sm' | 'md';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  children: ReactNode;
}

export function buttonClasses(variant: ButtonVariant = 'primary', size: ButtonSize = 'md'): string {
  return cn('ui-button', 'ui-button--' + variant, 'ui-button--' + size);
}

/**
 * Bouton partagé basé sur les tokens du Design System.
 * La taille compacte est portée à 44px sur les appareils tactiles.
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
      aria-busy={isLoading || undefined}
      className={cn(buttonClasses(variant, size), className)}
      {...props}
    >
      {isLoading && <Icon icon={Loading03Icon} size={16} className="animate-spin" />}
      {children}
    </button>
  );
}
