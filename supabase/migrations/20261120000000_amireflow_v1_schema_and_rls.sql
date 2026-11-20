-- =============================================================================
-- Amireflow Study OS v1.0 — Script SQL complet pour Supabase (PostgreSQL + RLS)
-- Peut être exécuté directement dans le SQL Editor de Supabase (ou via Alembic).
-- =============================================================================

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    timezone VARCHAR(80) NOT NULL DEFAULT 'Africa/Dakar',
    active_priority_title VARCHAR(200),
    active_priority_task_id UUID,
    active_priority_project_id UUID,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    ai_instructions TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(140) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'todo',
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    due_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    source VARCHAR(20) NOT NULL DEFAULT 'manual',
    proposal_id UUID,
    project_id UUID,
    module_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_tasks_status CHECK (status IN ('todo', 'in_progress', 'done', 'cancelled', 'parked')),
    CONSTRAINT ck_tasks_priority CHECK (priority IN ('low', 'normal', 'high', 'critical'))
);
CREATE INDEX IF NOT EXISTS ix_tasks_user_id ON tasks (user_id);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS ix_tasks_due_at ON tasks (due_at);

CREATE TABLE IF NOT EXISTS schedule_events (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(140) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'course',
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_schedule_events_range CHECK (ends_at > starts_at)
);
CREATE INDEX IF NOT EXISTS ix_schedule_user_id ON schedule_events (user_id);
CREATE INDEX IF NOT EXISTS ix_schedule_starts_at ON schedule_events (starts_at);

CREATE TABLE IF NOT EXISTS study_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(140) NOT NULL,
    category VARCHAR(60) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    result TEXT,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    project_id UUID,
    module_id UUID,
    lesson_id UUID,
    skill_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_study_sessions_status CHECK (status IN ('in_progress', 'completed', 'cancelled')),
    CONSTRAINT ck_study_sessions_range CHECK (ended_at IS NULL OR ended_at > started_at)
);
CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON study_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_status ON study_sessions (status);
CREATE INDEX IF NOT EXISTS ix_sessions_started_at ON study_sessions (started_at);
CREATE INDEX IF NOT EXISTS ix_sessions_task_id ON study_sessions (task_id);

CREATE TABLE IF NOT EXISTS learning_paths (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(140) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'not_started',
    goal VARCHAR(300) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_learning_paths_status CHECK (status IN ('not_started', 'active', 'paused', 'completed'))
);
CREATE INDEX IF NOT EXISTS ix_learning_paths_user_id ON learning_paths (user_id);
CREATE INDEX IF NOT EXISTS ix_learning_paths_status ON learning_paths (status);

CREATE TABLE IF NOT EXISTS learning_modules (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    path_id UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
    title VARCHAR(140) NOT NULL,
    description TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'not_started',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_learning_modules_position CHECK (position >= 0),
    CONSTRAINT ck_learning_modules_status CHECK (status IN ('not_started', 'active', 'paused', 'completed'))
);
CREATE INDEX IF NOT EXISTS ix_learning_modules_user_id ON learning_modules (user_id);
CREATE INDEX IF NOT EXISTS ix_learning_modules_path_id ON learning_modules (path_id);

CREATE TABLE IF NOT EXISTS lessons (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    module_id UUID NOT NULL REFERENCES learning_modules(id) ON DELETE CASCADE,
    title VARCHAR(140) NOT NULL,
    content TEXT,
    resource_url VARCHAR(500),
    position INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'not_started',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_lessons_position CHECK (position >= 0),
    CONSTRAINT ck_lessons_status CHECK (status IN ('not_started', 'active', 'paused', 'completed'))
);
CREATE INDEX IF NOT EXISTS ix_lessons_user_id ON lessons (user_id);
CREATE INDEX IF NOT EXISTS ix_lessons_module_id ON lessons (module_id);

CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    name VARCHAR(120) NOT NULL,
    domain VARCHAR(80) NOT NULL,
    description TEXT,
    current_level INTEGER NOT NULL DEFAULT 0,
    target_level INTEGER,
    last_assessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_skills_current_level CHECK (current_level >= 0 AND current_level <= 5),
    CONSTRAINT ck_skills_target_level CHECK (target_level IS NULL OR (target_level >= 0 AND target_level <= 5))
);
CREATE INDEX IF NOT EXISTS ix_skills_user_id ON skills (user_id);
CREATE INDEX IF NOT EXISTS ix_skills_domain ON skills (domain);

CREATE TABLE IF NOT EXISTS skill_evidence (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL DEFAULT 'exercise',
    description TEXT NOT NULL,
    reference_url VARCHAR(500),
    result VARCHAR(200),
    observed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_skill_evidence_type CHECK (type IN ('exercise', 'project', 'code', 'assessment', 'deliverable', 'other'))
);
CREATE INDEX IF NOT EXISTS ix_skill_evidence_user_id ON skill_evidence (user_id);
CREATE INDEX IF NOT EXISTS ix_skill_evidence_skill_id ON skill_evidence (skill_id);

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    name VARCHAR(140) NOT NULL,
    description TEXT,
    goal VARCHAR(300) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'planned',
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    next_action VARCHAR(240) NOT NULL DEFAULT '',
    deliverables JSONB,
    target_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_projects_status CHECK (status IN ('planned', 'active', 'blocked', 'completed', 'archived')),
    CONSTRAINT ck_projects_priority CHECK (priority IN ('low', 'normal', 'high', 'critical'))
);
CREATE INDEX IF NOT EXISTS ix_projects_user_id ON projects (user_id);
CREATE INDEX IF NOT EXISTS ix_projects_status ON projects (status);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(160) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ai_conversations_user_id ON ai_conversations (user_id);

CREATE TABLE IF NOT EXISTS ai_messages (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ai_messages_role CHECK (role IN ('user', 'assistant', 'system'))
);
CREATE INDEX IF NOT EXISTS ix_ai_messages_user_id ON ai_messages (user_id);
CREATE INDEX IF NOT EXISTS ix_ai_messages_conversation_id ON ai_messages (conversation_id);

CREATE TABLE IF NOT EXISTS ai_action_proposals (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,
    title VARCHAR(180) NOT NULL,
    explanation TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ,
    execution_result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT ck_ai_action_proposals_status CHECK (status IN ('pending', 'accepted', 'rejected', 'expired', 'executed', 'failed'))
);
CREATE INDEX IF NOT EXISTS ix_ai_action_proposals_user_id ON ai_action_proposals (user_id);
CREATE INDEX IF NOT EXISTS ix_ai_action_proposals_conversation_id ON ai_action_proposals (conversation_id);
CREATE INDEX IF NOT EXISTS ix_ai_action_proposals_status ON ai_action_proposals (status);

CREATE TABLE IF NOT EXISTS ai_reports (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    type VARCHAR(30) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ai_reports_type CHECK (type IN ('daily_briefing', 'weekly_review'))
);
CREATE INDEX IF NOT EXISTS ix_ai_reports_user_id ON ai_reports (user_id);
CREATE INDEX IF NOT EXISTS ix_ai_reports_type ON ai_reports (type);

-- Activation RLS sur les 14 tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedule_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE study_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_paths ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_action_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_reports ENABLE ROW LEVEL SECURITY;

-- Politiques propriétaires strictes (TO authenticated + initPlan (select auth.uid()))
DROP POLICY IF EXISTS "profiles_owner_all" ON profiles;
CREATE POLICY "profiles_owner_all" ON profiles FOR ALL TO authenticated USING ((select auth.uid()) = id) WITH CHECK ((select auth.uid()) = id);

DROP POLICY IF EXISTS "tasks_owner_all" ON tasks;
CREATE POLICY "tasks_owner_all" ON tasks FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "schedule_events_owner_all" ON schedule_events;
CREATE POLICY "schedule_events_owner_all" ON schedule_events FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "study_sessions_owner_all" ON study_sessions;
CREATE POLICY "study_sessions_owner_all" ON study_sessions FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "learning_paths_owner_all" ON learning_paths;
CREATE POLICY "learning_paths_owner_all" ON learning_paths FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "learning_modules_owner_all" ON learning_modules;
CREATE POLICY "learning_modules_owner_all" ON learning_modules FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "lessons_owner_all" ON lessons;
CREATE POLICY "lessons_owner_all" ON lessons FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "skills_owner_all" ON skills;
CREATE POLICY "skills_owner_all" ON skills FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "skill_evidence_owner_all" ON skill_evidence;
CREATE POLICY "skill_evidence_owner_all" ON skill_evidence FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "projects_owner_all" ON projects;
CREATE POLICY "projects_owner_all" ON projects FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "ai_conversations_owner_all" ON ai_conversations;
CREATE POLICY "ai_conversations_owner_all" ON ai_conversations FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "ai_messages_owner_all" ON ai_messages;
CREATE POLICY "ai_messages_owner_all" ON ai_messages FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "ai_action_proposals_owner_all" ON ai_action_proposals;
CREATE POLICY "ai_action_proposals_owner_all" ON ai_action_proposals FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "ai_reports_owner_all" ON ai_reports;
CREATE POLICY "ai_reports_owner_all" ON ai_reports FOR ALL TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);
