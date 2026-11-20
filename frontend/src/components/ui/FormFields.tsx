import { useState, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import { cn } from '../../lib/cn';
import { Button } from './Button';

export interface FormFieldProps {
  id: string;
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: ReactNode;
}

/**
 * Enveloppe de champ de formulaire accessible : relie le label, l'aide
 * et le message d'erreur (`role="alert"`) juste sous le contrôle.
 */
export function FormField({ id, label, required, hint, error, children }: FormFieldProps) {
  return (
    <div className="min-w-0 space-y-1.5">
      <label
        htmlFor={id}
        className="block text-xs font-medium tracking-tight text-zinc-700 sm:text-sm dark:text-zinc-300"
      >
        {label}
        {required && (
          <span className="ml-1 text-rose-600 dark:text-rose-400" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="text-xs text-zinc-500 dark:text-zinc-400">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-xs font-medium text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
    </div>
  );
}

const baseControlClasses =
  'block w-full min-w-0 max-w-full min-h-10 rounded-lg bg-zinc-100/80 px-3 py-2 text-base sm:text-sm text-zinc-900 transition-colors placeholder:text-zinc-400 focus:bg-zinc-100 focus:outline-none disabled:bg-zinc-50 disabled:text-zinc-500 dark:bg-zinc-800/80 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:focus:bg-zinc-800 dark:disabled:bg-zinc-900 dark:disabled:text-zinc-500';

function controlClasses(hasError?: boolean, className?: string): string {
  return cn(
    baseControlClasses,
    hasError && 'bg-rose-50/80 text-rose-900 dark:bg-rose-950/50 dark:text-rose-200',
    className,
  );
}

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean;
}

export function Input({ hasError, className, ...props }: InputProps) {
  return (
    <input
      aria-invalid={hasError || undefined}
      className={controlClasses(hasError, className)}
      {...props}
    />
  );
}

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  hasError?: boolean;
}

export function Textarea({ hasError, className, rows = 3, ...props }: TextareaProps) {
  return (
    <textarea
      rows={rows}
      aria-invalid={hasError || undefined}
      className={controlClasses(hasError, className)}
      {...props}
    />
  );
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  hasError?: boolean;
  children: ReactNode;
}

export function Select({ hasError, className, children, ...props }: SelectProps) {
  return (
    <select
      aria-invalid={hasError || undefined}
      className={controlClasses(hasError, className)}
      {...props}
    >
      {children}
    </select>
  );
}

export interface InlineConfirmProps {
  triggerLabel: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  size?: 'sm' | 'md';
  triggerVariant?: 'ghost' | 'secondary' | 'danger';
  ariaLabel?: string;
}

/**
 * Confirmation accessible en deux clics pour éviter toute suppression
 * ou annulation accidentelle sans recourir à `window.confirm`.
 */
export function InlineConfirm({
  triggerLabel,
  confirmLabel = 'Confirmer',
  cancelLabel = 'Annuler',
  onConfirm,
  size = 'sm',
  triggerVariant = 'ghost',
  ariaLabel,
}: InlineConfirmProps) {
  const [confirming, setConfirming] = useState(false);

  if (!confirming) {
    return (
      <Button
        variant={triggerVariant}
        size={size}
        aria-label={ariaLabel}
        onClick={() => setConfirming(true)}
        className={
          triggerVariant === 'ghost'
            ? 'text-rose-600 hover:bg-rose-50 hover:text-rose-700 dark:text-rose-400 dark:hover:bg-rose-950/50 dark:hover:text-rose-300'
            : undefined
        }
      >
        {triggerLabel}
      </Button>
    );
  }

  return (
    <div className="inline-flex items-center gap-1.5" role="group" aria-label={`Confirmation : ${triggerLabel}`}>
      <Button
        variant="danger"
        size={size}
        onClick={() => {
          setConfirming(false);
          onConfirm();
        }}
      >
        {confirmLabel}
      </Button>
      <Button variant="secondary" size={size} onClick={() => setConfirming(false)}>
        {cancelLabel}
      </Button>
    </div>
  );
}
