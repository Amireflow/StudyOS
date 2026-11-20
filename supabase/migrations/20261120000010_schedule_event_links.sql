-- Migration Supabase : Liens relationnels optionnels des créneaux de planning vers objectif, cours, projet ou tâche

ALTER TABLE public.schedule_events
    ADD COLUMN IF NOT EXISTS goal_id UUID REFERENCES public.personal_goals(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS course_id UUID REFERENCES public.courses(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS task_id UUID REFERENCES public.tasks(id) ON DELETE SET NULL;
