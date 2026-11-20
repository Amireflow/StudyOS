import { z } from 'zod';
import type { BadgeVariant } from '../../components/ui/Badge';
import type { LearningStatus } from '../../types/domain';

export const LEARNING_STATUS_META: Record<
  LearningStatus,
  { label: string; badgeVariant: BadgeVariant }
> = {
  not_started: { label: 'Non démarré', badgeVariant: 'neutral' },
  active: { label: 'Actif', badgeVariant: 'primary' },
  paused: { label: 'En pause', badgeVariant: 'warning' },
  completed: { label: 'Terminé', badgeVariant: 'success' },
};

const optionalHttpUrlSchema = z
  .string()
  .trim()
  .max(500, 'L’URL ne doit pas dépasser 500 caractères.')
  .refine(
    (value) => !value || /^https?:\/\/\S+$/i.test(value),
    'L’URL doit commencer par http:// ou https://.',
  )
  .optional()
  .or(z.literal(''));

export const learningPathSchema = z.object({
  title: z
    .string()
    .trim()
    .min(2, 'Le titre doit contenir au moins 2 caractères.')
    .max(140, 'Le titre ne doit pas dépasser 140 caractères.'),
  goal: z
    .string()
    .trim()
    .min(2, 'L’objectif doit contenir au moins 2 caractères.')
    .max(300, 'L’objectif ne doit pas dépasser 300 caractères.'),
  description: z
    .string()
    .trim()
    .max(1000, 'La description ne doit pas dépasser 1000 caractères.')
    .optional()
    .or(z.literal('')),
  status: z.enum(['not_started', 'active', 'paused', 'completed']),
});

export const learningModuleSchema = z.object({
  title: z
    .string()
    .trim()
    .min(2, 'Le titre du module doit contenir au moins 2 caractères.')
    .max(140, 'Le titre ne doit pas dépasser 140 caractères.'),
  description: z
    .string()
    .trim()
    .max(1000, 'La description ne doit pas dépasser 1000 caractères.')
    .optional()
    .or(z.literal('')),
  position: z.coerce
    .number()
    .int('La position doit être un entier.')
    .min(0, 'La position minimale est 0.')
    .max(1000, 'La position maximale est 1000.'),
  status: z.enum(['not_started', 'active', 'paused', 'completed']),
});

export const lessonSchema = z.object({
  title: z
    .string()
    .trim()
    .min(2, 'Le titre de la leçon doit contenir au moins 2 caractères.')
    .max(140, 'Le titre ne doit pas dépasser 140 caractères.'),
  content: z
    .string()
    .trim()
    .max(4000, 'Le contenu ne doit pas dépasser 4000 caractères.')
    .optional()
    .or(z.literal('')),
  resourceUrl: optionalHttpUrlSchema,
  position: z.coerce
    .number()
    .int('La position doit être un entier.')
    .min(0, 'La position minimale est 0.')
    .max(1000, 'La position maximale est 1000.'),
  status: z.enum(['not_started', 'active', 'paused', 'completed']),
});

export type LearningPathFormValues = z.infer<typeof learningPathSchema>;
export type LearningModuleFormValues = z.infer<typeof learningModuleSchema>;
export type LessonFormValues = z.infer<typeof lessonSchema>;
