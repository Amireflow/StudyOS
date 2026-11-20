import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '../../lib/cn';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function Card({ className, children, ...props }: CardProps) {
  return (
    <section
      className={cn('rounded-2xl bg-white dark:bg-zinc-900', className)}
      {...props}
    >
      {children}
    </section>
  );
}

export function CardHeader({ className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-1 px-4 pt-4 pb-2 sm:px-5 sm:pt-5 sm:pb-2.5',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  children: ReactNode;
}

export function CardTitle({ className, children, ...props }: CardTitleProps) {
  return (
    <h2
      className={cn('text-[15px] font-semibold tracking-tight text-zinc-900 dark:text-zinc-50', className)}
      {...props}
    >
      {children}
    </h2>
  );
}

export interface CardDescriptionProps extends HTMLAttributes<HTMLParagraphElement> {
  children: ReactNode;
}

export function CardDescription({ className, children, ...props }: CardDescriptionProps) {
  return (
    <p className={cn('text-xs text-zinc-500 dark:text-zinc-400', className)} {...props}>
      {children}
    </p>
  );
}

export function CardContent({ className, children, ...props }: CardProps) {
  return (
    <div className={cn('px-4 pb-4 pt-2 sm:px-5 sm:pb-5 sm:pt-2.5', className)} {...props}>
      {children}
    </div>
  );
}
