-- Migration Supabase P0 : Sécurité, intégrité pédagogique, clés IA chiffrées, sessions & RLS durci

CREATE TABLE IF NOT EXISTS user_ai_provider_configs (
    user_id UUID PRIMARY KEY,
    provider VARCHAR(30) NOT NULL DEFAULT 'local',
    base_url VARCHAR(300) NOT NULL DEFAULT '',
    model VARCHAR(160) NOT NULL DEFAULT '',
    encrypted_api_key TEXT NULL,
    key_version INTEGER NOT NULL DEFAULT 1,
    api_key_last4 VARCHAR(8) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_refresh_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(128) NOT NULL,
    token_version INTEGER NOT NULL DEFAULT 1,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    replaced_by_id UUID NULL,
    user_agent VARCHAR(255) NULL,
    ip_hash VARCHAR(64) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_auth_refresh_sessions_user_id ON auth_refresh_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_auth_refresh_sessions_expires_at ON auth_refresh_sessions (expires_at);
CREATE UNIQUE INDEX IF NOT EXISTS ix_auth_refresh_sessions_token_hash ON auth_refresh_sessions (token_hash);

CREATE TABLE IF NOT EXISTS auth_login_attempts (
    id UUID PRIMARY KEY,
    scope VARCHAR(30) NOT NULL,
    account_key_hash VARCHAR(64) NULL,
    client_ip_hash VARCHAR(64) NOT NULL,
    succeeded BOOLEAN NOT NULL DEFAULT FALSE,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_auth_login_attempts_scope CHECK (scope IN ('login', 'register', 'change_password', 'models_probe'))
);

CREATE INDEX IF NOT EXISTS ix_auth_login_attempts_scope_account_ts ON auth_login_attempts (scope, account_key_hash, attempted_at);
CREATE INDEX IF NOT EXISTS ix_auth_login_attempts_scope_ip_ts ON auth_login_attempts (scope, client_ip_hash, attempted_at);

CREATE TABLE IF NOT EXISTS auth_token_revocations (
    user_id UUID PRIMARY KEY,
    revoked_before TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ NULL;

ALTER TABLE skill_evidence
    ADD COLUMN IF NOT EXISTS verification_status VARCHAR(30) NOT NULL DEFAULT 'declared',
    ADD COLUMN IF NOT EXISTS inspection_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS inspected_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE skill_evidence DROP CONSTRAINT IF EXISTS ck_skill_evidence_verification_status;
ALTER TABLE skill_evidence
    ADD CONSTRAINT ck_skill_evidence_verification_status
    CHECK (verification_status IN ('declared', 'uploaded', 'inspected', 'verified', 'approved', 'unreachable', 'rejected'));

ALTER TABLE skill_assessments
    ADD COLUMN IF NOT EXISTS rubric_version VARCHAR(32) NOT NULL DEFAULT 'rubric-v2',
    ADD COLUMN IF NOT EXISTS evaluator_version VARCHAR(32) NOT NULL DEFAULT 'eval-v2',
    ADD COLUMN IF NOT EXISTS evaluation_mode VARCHAR(30) NOT NULL DEFAULT 'automated',
    ADD COLUMN IF NOT EXISTS manual_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS rubric_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS evidence_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(120) NULL;

ALTER TABLE skill_assessments DROP CONSTRAINT IF EXISTS ck_skill_assessments_status;
ALTER TABLE skill_assessments
    ADD CONSTRAINT ck_skill_assessments_status
    CHECK (status IN ('pending', 'submitted', 'evaluated', 'needs_manual_review', 'approved', 'rejected', 'cancelled'));

ALTER TABLE skill_assessments DROP CONSTRAINT IF EXISTS ck_skill_assessments_eval_mode;
ALTER TABLE skill_assessments
    ADD CONSTRAINT ck_skill_assessments_eval_mode
    CHECK (evaluation_mode IN ('automated', 'ai_assisted', 'manual_review'));

CREATE INDEX IF NOT EXISTS ix_sessions_task_id ON study_sessions (task_id);
CREATE INDEX IF NOT EXISTS ix_courses_learning_path_id ON courses (learning_path_id);
CREATE INDEX IF NOT EXISTS ix_course_resources_lesson_id ON course_resources (lesson_id);
CREATE INDEX IF NOT EXISTS ix_course_submissions_lesson_id ON course_submissions (lesson_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_course_levels_course_num'
    ) THEN
        ALTER TABLE course_levels ADD CONSTRAINT uq_course_levels_course_num UNIQUE (course_id, level_number);
    END IF;
END $$;

-- Tables sensibles backend-only : RLS activée sans politique client + révocation des privilèges anon/authenticated
ALTER TABLE user_ai_provider_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_refresh_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_login_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_token_revocations ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE users FROM anon, authenticated;
REVOKE ALL ON TABLE user_ai_provider_configs FROM anon, authenticated;
REVOKE ALL ON TABLE auth_refresh_sessions FROM anon, authenticated;
REVOKE ALL ON TABLE auth_login_attempts FROM anon, authenticated;
REVOKE ALL ON TABLE auth_token_revocations FROM anon, authenticated;
