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
 * Enveloppe de champ : label visible, aide et erreur au même emplacement.
 */
export function FormField({ id, label, required, hint, error, children }: FormFieldProps) {
  return (
    <div className="min-w-0 space-y-1.5">
      <label htmlFor={id} className="ui-field-label block">
        {label}
        {required && (
          <span className="ml-1 text-rose-600 dark:text-rose-400" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {children}
      {hint && !error && (
        <p id={\`\${id}-hint\`} className="ui-field-help">
          {hint}
        </p>
      )}
      {error && (
        <p id={\`\${id}-error\`} role="alert" className="ui-field-error">
          {error}
        </p>
      )}
    </div>
  );
}

const baseControlClasses = 'ui-form-control block w-full min-w-0 max-w-full';

function controlClasses(hasError?: boolean, className?: string): string {
  return cn(baseControlClasses, hasError && 'ui-form-control--error', className);
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
 * ou annulation accidentelle sans recourir à window.confirm.
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
    <div className="inline-flex items-center gap-1.5" role="group" aria-label={\`Confirmation : \${triggerLabel}\`}>
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
