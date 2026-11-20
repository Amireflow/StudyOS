import { z } from 'zod';

export const scheduleEventFormSchema = z
  .object({
    title: z
      .string()
      .trim()
      .min(2, 'Le titre doit contenir au moins 2 caractères.')
      .max(140, 'Le titre ne doit pas dépasser 140 caractères.'),
    type: z.enum(['course', 'learning', 'project', 'personal', 'other']),
    date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'La date est obligatoire.'),
    startTime: z.string().regex(/^\d{2}:\d{2}$/, 'L’heure de début est obligatoire.'),
    endTime: z.string().regex(/^\d{2}:\d{2}$/, 'L’heure de fin est obligatoire.'),
    notes: z
      .string()
      .trim()
      .max(1000, 'Les notes ne doivent pas dépasser 1000 caractères.')
      .optional()
      .or(z.literal('')),
  })
  .refine((data) => data.endTime > data.startTime, {
    message: 'L’heure de fin doit être strictement postérieure à l’heure de début.',
    path: ['endTime'],
  });

export type ScheduleEventFormValues = z.infer<typeof scheduleEventFormSchema>;
