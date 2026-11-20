import { z } from 'zod';

export const SESSION_CATEGORIES = [
  'Cours',
  'Apprentissage',
  'Exercices',
  'Projet',
  'Révision',
  'Autre',
] as const;

export const startSessionSchema = z.object({
  title: z
    .string()
    .trim()
    .min(2, 'Le titre doit contenir au moins 2 caractères.')
    .max(140, 'Le titre ne doit pas dépasser 140 caractères.'),
  category: z.string().trim().min(1, 'Veuillez choisir une catégorie.'),
  taskId: z.string().optional().or(z.literal('')),
  projectId: z.string().optional().or(z.literal('')),
  moduleId: z.string().optional().or(z.literal('')),
  lessonId: z.string().optional().or(z.literal('')),
  skillId: z.string().optional().or(z.literal('')),
});

export const finishSessionSchema = z.object({
  result: z
    .string()
    .trim()
    .min(2, 'Notez brièvement ce qui a été produit ou appris.')
    .max(1000, 'Le résultat ne doit pas dépasser 1000 caractères.'),
});

export const manualSessionSchema = z
  .object({
    title: z
      .string()
      .trim()
      .min(2, 'Le titre doit contenir au moins 2 caractères.')
      .max(140, 'Le titre ne doit pas dépasser 140 caractères.'),
    category: z.string().trim().min(1, 'Veuillez choisir une catégorie.'),
    startedAt: z.string().min(1, 'La date et l’heure de début sont obligatoires.'),
    endedAt: z.string().min(1, 'La date et l’heure de fin sont obligatoires.'),
    result: z
      .string()
      .trim()
      .min(2, 'Notez brièvement ce qui a été produit ou appris.')
      .max(1000, 'Le résultat ne doit pas dépasser 1000 caractères.'),
    taskId: z.string().optional().or(z.literal('')),
    projectId: z.string().optional().or(z.literal('')),
    moduleId: z.string().optional().or(z.literal('')),
    lessonId: z.string().optional().or(z.literal('')),
    skillId: z.string().optional().or(z.literal('')),
  })
  .refine(
    (data) => {
      const start = new Date(data.startedAt).getTime();
      const end = new Date(data.endedAt).getTime();
      return !Number.isNaN(start) && !Number.isNaN(end) && end > start;
    },
    {
      message: 'La date de fin doit être strictement postérieure au début.',
      path: ['endedAt'],
    },
  );

export type StartSessionValues = z.infer<typeof startSessionSchema>;
export type FinishSessionValues = z.infer<typeof finishSessionSchema>;
export type ManualSessionValues = z.infer<typeof manualSessionSchema>;
