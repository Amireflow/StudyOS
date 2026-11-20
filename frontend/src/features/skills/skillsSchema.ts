import { z } from 'zod';
import type { BadgeVariant } from '../../components/ui/Badge';
import type {
  EvidenceVerificationStatus,
  SkillAssessmentStatus,
  SkillAssessmentType,
  SkillEvidenceType,
  SkillLevel,
  SkillPedagogicalState,
} from '../../types/domain';

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

export const SKILL_PEDAGOGICAL_STATE_META: Record<
  SkillPedagogicalState,
  { label: string; badgeVariant: BadgeVariant }
> = {
  not_evaluated: { label: 'Non évaluée', badgeVariant: 'neutral' },
  learning: { label: 'En cours d’apprentissage', badgeVariant: 'primary' },
  awaiting_assessment: { label: 'En attente d’évaluation', badgeVariant: 'warning' },
  validated: { label: 'Validée', badgeVariant: 'success' },
  needs_reinforcement: { label: 'À renforcer', badgeVariant: 'danger' },
};

export const ASSESSMENT_STATUS_META: Record<
  SkillAssessmentStatus,
  { label: string; badgeVariant: BadgeVariant }
> = {
  pending: { label: 'En attente de production', badgeVariant: 'warning' },
  submitted: { label: 'Production soumise', badgeVariant: 'primary' },
  evaluated: { label: 'Évaluée', badgeVariant: 'primary' },
  needs_manual_review: { label: 'Revue manuelle requise', badgeVariant: 'warning' },
  approved: { label: 'Validée', badgeVariant: 'success' },
  rejected: { label: 'Non validée', badgeVariant: 'danger' },
  cancelled: { label: 'Annulée', badgeVariant: 'neutral' },
};

export const EVIDENCE_VERIFICATION_META: Record<
  EvidenceVerificationStatus,
  { label: string; badgeVariant: BadgeVariant }
> = {
  declared: { label: 'Déclarée', badgeVariant: 'neutral' },
  uploaded: { label: 'Téléversée', badgeVariant: 'primary' },
  inspected: { label: 'Inspectée', badgeVariant: 'primary' },
  verified: { label: 'Vérifiée', badgeVariant: 'success' },
  approved: { label: 'Approuvée', badgeVariant: 'success' },
  unreachable: { label: 'Inaccessible', badgeVariant: 'danger' },
};

export const ASSESSMENT_TYPE_META: Record<SkillAssessmentType, { label: string }> = {
  practical_exercise: { label: 'Exercice pratique' },
  code_review: { label: 'Code & revue technique' },
  quiz: { label: 'Questions de compréhension' },
  explanation: { label: 'Explication & raisonnement' },
  deliverable: { label: 'Livrable concret' },
  mixed: { label: 'Épreuve mixte' },
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
  targetLevel: z
    .string()
    .refine(
      (value) => value === '' || ['1', '2', '3', '4', '5'].includes(value),
      'Niveau cible invalide.',
    ),
});

export const evidenceFormSchema = z.object({
  type: z.enum(['exercise', 'project', 'code', 'assessment', 'deliverable', 'other']),
  description: z
    .string()
    .trim()
    .min(12, 'Décrivez la preuve concrète réalisée (min. 12 caractères).')
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
