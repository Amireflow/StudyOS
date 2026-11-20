import { z } from 'zod';
import type { BadgeVariant } from '../../components/ui/Badge';
import type { ProjectStatus } from '../../types/domain';

export const PROJECT_STATUS_META: Record<
  ProjectStatus,
  { label: string; badgeVariant: BadgeVariant }
> = {
  planned: { label: 'Planifié', badgeVariant: 'neutral' },
  active: { label: 'Actif', badgeVariant: 'primary' },
  paused: { label: 'En pause', badgeVariant: 'neutral' },
  blocked: { label: 'Bloqué', badgeVariant: 'warning' },
  completed: { label: 'Terminé', badgeVariant: 'success' },
  archived: { label: 'Archivé', badgeVariant: 'neutral' },
};

export const projectFormSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(2, 'Le nom du projet doit contenir au moins 2 caractères.')
      .max(140, 'Le nom ne doit pas dépasser 140 caractères.'),
    goal: z
      .string()
      .trim()
      .min(2, 'L’objectif doit contenir au moins 2 caractères.')
      .max(300, 'L’objectif ne doit pas dépasser 300 caractères.'),
    description: z
      .string()
      .trim()
      .max(2000, 'La description ne doit pas dépasser 2000 caractères.')
      .optional()
      .or(z.literal('')),
    status: z.enum(['planned', 'active', 'paused', 'blocked', 'completed', 'archived']),
    priority: z.enum(['low', 'normal', 'high', 'critical']),
    nextAction: z
      .string()
      .trim()
      .max(240, 'La prochaine action ne doit pas dépasser 240 caractères.'),
    deliverablesText: z.string().optional().or(z.literal('')),
    targetDate: z
      .string()
      .regex(/^(\d{4}-\d{2}-\d{2})?$/, 'Date cible invalide.')
      .optional()
      .or(z.literal('')),
  })
  .refine((data) => data.status !== 'active' || data.nextAction.trim().length >= 2, {
    message: 'Une prochaine action concrète est obligatoire pour un projet actif.',
    path: ['nextAction'],
  });

export type ProjectFormValues = z.infer<typeof projectFormSchema>;

export function parseDeliverablesText(raw: string | undefined): string[] {
  if (!raw) return [];
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}
