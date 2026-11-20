import type { z } from 'zod';

/**
 * Extrait le premier message d'erreur par champ depuis une erreur Zod.
 */
export function extractFieldErrors<TField extends string>(
  error: z.ZodError,
): Partial<Record<TField, string>> {
  const fieldErrors: Partial<Record<TField, string>> = {};

  for (const issue of error.issues) {
    const fieldKey = issue.path[0];
    if (typeof fieldKey === 'string' && !(fieldKey in fieldErrors)) {
      fieldErrors[fieldKey as TField] = issue.message;
    }
  }

  return fieldErrors;
}
