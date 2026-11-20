-- Migration Supabase : Règles de disponibilité personnelle et versions du programme d'apprentissage

CREATE TABLE IF NOT EXISTS public.user_availability_rules (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    label VARCHAR(120) NOT NULL,
    rule_type VARCHAR(32) NOT NULL,
    day_of_week INTEGER,
    start_time VARCHAR(5),
    end_time VARCHAR(5),
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Paris',
    recurrence VARCHAR(24) NOT NULL DEFAULT 'weekly',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_user_availability_rules_type CHECK (rule_type IN ('personal_unavailability', 'confirmed_availability', 'recovery_time')),
    CONSTRAINT ck_user_availability_rules_recurrence CHECK (recurrence IN ('once', 'weekly', 'daily')),
    CONSTRAINT ck_user_availability_rules_dow CHECK (day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6))
);

CREATE INDEX IF NOT EXISTS ix_user_availability_rules_user_id
    ON public.user_availability_rules (user_id);

CREATE INDEX IF NOT EXISTS ix_user_availability_rules_active
    ON public.user_availability_rules (user_id, active);

ALTER TABLE public.user_availability_rules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_availability_rules_owner_all ON public.user_availability_rules;
CREATE POLICY user_availability_rules_owner_all
    ON public.user_availability_rules
    FOR ALL
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE TABLE IF NOT EXISTS public.learning_plan_versions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(24) NOT NULL DEFAULT 'proposed',
    horizon_days INTEGER NOT NULL DEFAULT 7,
    timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Paris',
    idempotency_key VARCHAR(80),
    rationale TEXT NOT NULL DEFAULT '',
    plan_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    applied_event_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    applied_task_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    applied_course_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    replaced_event_snapshots JSONB NOT NULL DEFAULT '[]'::jsonb,
    parent_version_id UUID REFERENCES public.learning_plan_versions(id) ON DELETE SET NULL,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_learning_plan_versions_status CHECK (status IN ('proposed', 'applied', 'rejected', 'superseded', 'restored')),
    CONSTRAINT ck_learning_plan_versions_num CHECK (version_number >= 1),
    CONSTRAINT ck_learning_plan_versions_horizon CHECK (horizon_days >= 1 AND horizon_days <= 30),
    CONSTRAINT uq_learning_plan_versions_user_idem UNIQUE (user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_learning_plan_versions_user_id
    ON public.learning_plan_versions (user_id);

CREATE INDEX IF NOT EXISTS ix_learning_plan_versions_status
    ON public.learning_plan_versions (user_id, status);

CREATE INDEX IF NOT EXISTS ix_learning_plan_versions_idem
    ON public.learning_plan_versions (user_id, idempotency_key);

ALTER TABLE public.learning_plan_versions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS learning_plan_versions_owner_all ON public.learning_plan_versions;
CREATE POLICY learning_plan_versions_owner_all
    ON public.learning_plan_versions
    FOR ALL
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);
