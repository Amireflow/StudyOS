-- Pédagogie v2, résultats de séance structurés, projets en pause et snapshot d'import (Supabase PostgreSQL)

ALTER TABLE public.courses
    ADD COLUMN IF NOT EXISTS generation_source VARCHAR(32) NOT NULL DEFAULT 'curated_local',
    ADD COLUMN IF NOT EXISTS generation_model VARCHAR(120) NULL;

ALTER TABLE public.course_levels
    ADD COLUMN IF NOT EXISTS previous_versions JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS generation_source VARCHAR(32) NOT NULL DEFAULT 'curated_local';

ALTER TABLE public.course_submissions
    ADD COLUMN IF NOT EXISTS attempt_number INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS evaluation_mode VARCHAR(32) NOT NULL DEFAULT 'deterministic',
    ADD COLUMN IF NOT EXISTS manual_review_required BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS static_analysis JSONB NULL;

ALTER TABLE public.study_sessions
    ADD COLUMN IF NOT EXISTS outcome_status VARCHAR(32) NULL,
    ADD COLUMN IF NOT EXISTS deliverable_summary TEXT NULL,
    ADD COLUMN IF NOT EXISTS blockers TEXT NULL,
    ADD COLUMN IF NOT EXISTS next_step TEXT NULL;

ALTER TABLE public.timetable_imports
    ADD COLUMN IF NOT EXISTS replaced_snapshot JSONB NULL;

ALTER TABLE public.projects
    DROP CONSTRAINT IF EXISTS ck_projects_status;

ALTER TABLE public.projects
    ADD CONSTRAINT ck_projects_status
    CHECK (status IN ('planned', 'active', 'paused', 'blocked', 'completed', 'archived'));
