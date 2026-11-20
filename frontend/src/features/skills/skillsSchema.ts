import { z } from 'zod';
import type { BadgeVariant } from '../../components/ui/Badge';
import type { SkillEvidenceType, SkillLevel } from '../../types/domain';

export const SKILL_LEVEL_META: Record<
  SkillLevel,
  { shortLabel: string; label: string; badgeVariant: BadgeVariant }
> = {
  0: { shortLabel: '0 — Non évalué', label: '0 / 5 — Non évalué', badgeVariant: 'neutral' },
  1: { shortLabel: '1 — Découverte', label: '1 / 5 — Découverte', badgeVariant: 'neutral' },
  2: { shortLabel: '2 — Notions', label: '2 / 5 — Notions', badgeVariant: 'primary' },
  3: { shortLabel: '3 — Autonome', label: '3 / 5 — Autonome', badgeVariant: 'success' },
  4: { shortLabel: '4 — Solide', label: '4 / 5 — Solide', badgeVariant: 'success' },
  5: { shortLabel: '5 — Maîtrise', label: '5 / 5 — Maîtrise', badgeVariant: 'success' },
};

export const SKILL_EVIDENCE_TYPE_META: Record<
  SkillEvidenceType,
  { label: string; badgeVariant: BadgeVariant }
> = {
  exercise: { label: 'Exercice', badgeVariant: 'primary' },
  project: { label: 'Projet', badgeVariant: 'success' },
  code: { label: 'Code', badgeVariant: 'neutral' },
  assessment: { label: 'Évaluation', badgeVariant: 'warning' },
  deliverable: { label: 'Livrable', badgeVariant: 'success' },
  other: { label: 'Autre', badgeVariant: 'neutral' },
};

export const skillFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, 'Le nom doit contenir au moins 2 caractères.')
    .max(120, 'Le nom ne doit pas dépasser 120 caractères.'),
  domain: z
    .string()
    .trim()
    .min(2, 'Le domaine doit contenir au moins 2 caractères.')
    .max(80, 'Le domaine ne doit pas dépasser 80 caractères.'),
  description: z
    .string()
    .trim()
    .max(1000, 'La description ne doit pas dépasser 1000 caractères.')
    .optional()
    .or(z.literal('')),
  currentLevel: z.coerce.number().int().min(0).max(5),
  targetLevel: z
    .string()
    .refine(
      (value) => value === '' || ['0', '1', '2', '3', '4', '5'].includes(value),
      'Niveau cible invalide.',
    ),
});

export const evidenceFormSchema = z.object({
  type: z.enum(['exercise', 'project', 'code', 'assessment', 'deliverable', 'other']),
  description: z
    .string()
    .trim()
    .min(2, 'Décrivez la preuve concrète (min. 2 caractères).')
    .max(1000, 'La description ne doit pas dépasser 1000 caractères.'),
  referenceUrl: z
    .string()
    .trim()
    .max(500, 'L’URL ne doit pas dépasser 500 caractères.')
    .refine(
      (value) => !value || /^https?:\/\/\S+$/i.test(value),
      'L’URL doit commencer par http:// ou https://.',
    )
    .optional()
    .or(z.literal('')),
  result: z
    .string()
    .trim()
    .max(200, 'Le résultat ne doit pas dépasser 200 caractères.')
    .optional()
    .or(z.literal('')),
});

export type SkillFormValues = z.infer<typeof skillFormSchema>;
export type EvidenceFormValues = z.infer<typeof evidenceFormSchema>;
