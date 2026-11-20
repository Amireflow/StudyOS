-- Migration Supabase : Mémoire IA structurée persistante et clés d'idempotence IA

ALTER TABLE public.ai_messages
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(80);

CREATE INDEX IF NOT EXISTS ix_ai_messages_idempotency
    ON public.ai_messages (user_id, conversation_id, idempotency_key);

ALTER TABLE public.ai_action_proposals
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(80);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_ai_action_proposals_user_idem'
    ) THEN
        ALTER TABLE public.ai_action_proposals
            ADD CONSTRAINT uq_ai_action_proposals_user_idem UNIQUE (user_id, idempotency_key);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_ai_action_proposals_idempotency
    ON public.ai_action_proposals (user_id, idempotency_key);

CREATE TABLE IF NOT EXISTS public.user_ai_memory (
    user_id UUID PRIMARY KEY,
    academic_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    availability_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    learning_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    constraints JSONB NOT NULL DEFAULT '[]'::jsonb,
    long_term_goals JSONB NOT NULL DEFAULT '[]'::jsonb,
    recent_decisions JSONB NOT NULL DEFAULT '[]'::jsonb,
    execution_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    weekly_study_hours INTEGER,
    default_session_minutes INTEGER NOT NULL DEFAULT 60,
    auto_execute_simple_actions BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_user_ai_memory_weekly_hours CHECK (weekly_study_hours IS NULL OR (weekly_study_hours >= 0 AND weekly_study_hours <= 120)),
    CONSTRAINT ck_user_ai_memory_session_minutes CHECK (default_session_minutes >= 15 AND default_session_minutes <= 240)
);

ALTER TABLE public.user_ai_memory ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_ai_memory_owner_all ON public.user_ai_memory;
CREATE POLICY user_ai_memory_owner_all
    ON public.user_ai_memory
    FOR ALL
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);
