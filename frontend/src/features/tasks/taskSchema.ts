import { z } from 'zod';

export const taskFormSchema = z.object({
  title: z
    .string()
    .trim()
    .min(2, 'Le titre doit contenir au moins 2 caractères.')
    .max(140, 'Le titre ne doit pas dépasser 140 caractères.'),
  description: z
    .string()
    .trim()
    .max(1000, 'La description ne doit pas dépasser 1000 caractères.')
    .optional()
    .or(z.literal('')),
  priority: z.enum(['low', 'normal', 'high', 'critical']),
  status: z.enum(['todo', 'in_progress', 'done', 'cancelled', 'parked']),
  dueDate: z
    .string()
    .regex(/^(\d{4}-\d{2}-\d{2})?$/, 'Date invalide.')
    .optional()
    .or(z.literal('')),
  projectId: z.string().optional().or(z.literal('')),
  moduleId: z.string().optional().or(z.literal('')),
});

export type TaskFormValues = z.infer<typeof taskFormSchema>;
