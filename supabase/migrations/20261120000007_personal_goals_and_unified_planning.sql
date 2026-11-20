-- Migration Supabase : Objectifs personnels hors emploi du temps, projets enrichis et suivi de séance (RLS)

CREATE TABLE IF NOT EXISTS public.personal_goals (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    category VARCHAR(40) NOT NULL DEFAULT 'learning_goal',
    title VARCHAR(140) NOT NULL,
    description TEXT,
    goal VARCHAR(300) NOT NULL,
    current_level INTEGER,
    target_level INTEGER,
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    motivation TEXT,
    start_date TIMESTAMPTZ,
    target_date TIMESTAMPTZ,
    weekly_target_minutes INTEGER NOT NULL DEFAULT 120,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    deliverables JSONB NOT NULL DEFAULT '[]'::jsonb,
    next_action VARCHAR(240) NOT NULL DEFAULT '',
    success_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
    progress_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    skill_id UUID REFERENCES public.skills(id) ON DELETE SET NULL,
    learning_path_id UUID REFERENCES public.learning_paths(id) ON DELETE SET NULL,
    course_id UUID REFERENCES public.courses(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_personal_goals_status CHECK (status IN ('planned', 'active', 'paused', 'blocked', 'completed', 'archived')),
    CONSTRAINT ck_personal_goals_priority CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    CONSTRAINT ck_personal_goals_current_level CHECK (current_level IS NULL OR (current_level >= 0 AND current_level <= 5)),
    CONSTRAINT ck_personal_goals_target_level CHECK (target_level IS NULL OR (target_level >= 1 AND target_level <= 5)),
    CONSTRAINT ck_personal_goals_weekly_minutes CHECK (weekly_target_minutes >= 0)
);

CREATE INDEX IF NOT EXISTS ix_personal_goals_user_id ON public.personal_goals (user_id);
CREATE INDEX IF NOT EXISTS ix_personal_goals_status ON public.personal_goals (status);
CREATE INDEX IF NOT EXISTS ix_personal_goals_skill_id ON public.personal_goals (skill_id);
CREATE INDEX IF NOT EXISTS ix_personal_goals_path_id ON public.personal_goals (learning_path_id);
CREATE INDEX IF NOT EXISTS ix_personal_goals_course_id ON public.personal_goals (course_id);

ALTER TABLE public.personal_goals ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS personal_goals_owner_isolation ON public.personal_goals;
CREATE POLICY personal_goals_owner_isolation
    ON public.personal_goals
    FOR ALL
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS category VARCHAR(40) NOT NULL DEFAULT 'project';
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS motivation TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS start_date TIMESTAMPTZ;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS weekly_target_minutes INTEGER NOT NULL DEFAULT 180;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS steps JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS success_criteria JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS progress_history JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE public.study_sessions ADD COLUMN IF NOT EXISTS planned_activity VARCHAR(240);
ALTER TABLE public.study_sessions ADD COLUMN IF NOT EXISTS actual_activity TEXT;
ALTER TABLE public.study_sessions ADD COLUMN IF NOT EXISTS goal_id UUID;
