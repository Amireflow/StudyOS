-- Migration Supabase : Module Cours intelligent (tables, index et politiques RLS)

CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(160) NOT NULL,
    subject VARCHAR(120) NOT NULL,
    domain VARCHAR(80) NOT NULL,
    description TEXT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'fr',
    current_level INTEGER NOT NULL DEFAULT 1,
    total_levels INTEGER NOT NULL DEFAULT 3,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    skill_id UUID NULL REFERENCES skills(id) ON DELETE SET NULL,
    learning_path_id UUID NULL REFERENCES learning_paths(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_courses_language CHECK (language IN ('fr', 'en', 'bilingual')),
    CONSTRAINT ck_courses_current_level CHECK (current_level >= 1 AND current_level <= 5),
    CONSTRAINT ck_courses_total_levels CHECK (total_levels >= 1 AND total_levels <= 5),
    CONSTRAINT ck_courses_level_bounds CHECK (current_level <= total_levels),
    CONSTRAINT ck_courses_status CHECK (status IN ('draft', 'active', 'paused', 'completed'))
);

CREATE INDEX IF NOT EXISTS ix_courses_user_id ON courses (user_id);
CREATE INDEX IF NOT EXISTS ix_courses_status ON courses (status);
CREATE INDEX IF NOT EXISTS ix_courses_skill_id ON courses (skill_id);

CREATE TABLE IF NOT EXISTS course_levels (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    level_number INTEGER NOT NULL,
    title VARCHAR(160) NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    objectives JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'locked',
    content_generated BOOLEAN NOT NULL DEFAULT FALSE,
    project_title VARCHAR(180) NULL,
    project_brief TEXT NULL,
    project_deliverables JSONB NOT NULL DEFAULT '[]'::jsonb,
    project_rubric JSONB NOT NULL DEFAULT '[]'::jsonb,
    validated_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_course_levels_number CHECK (level_number >= 1 AND level_number <= 5),
    CONSTRAINT ck_course_levels_status CHECK (status IN ('locked', 'unlocked', 'in_progress', 'validated'))
);

CREATE INDEX IF NOT EXISTS ix_course_levels_user_id ON course_levels (user_id);
CREATE INDEX IF NOT EXISTS ix_course_levels_course_id ON course_levels (course_id);
CREATE INDEX IF NOT EXISTS ix_course_levels_course_num ON course_levels (course_id, level_number);

CREATE TABLE IF NOT EXISTS course_lessons (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    level_id UUID NOT NULL REFERENCES course_levels(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 1,
    title VARCHAR(160) NOT NULL,
    summary VARCHAR(300) NULL,
    estimated_minutes INTEGER NOT NULL DEFAULT 25,
    content_markdown TEXT NOT NULL,
    code_examples JSONB NOT NULL DEFAULT '[]'::jsonb,
    exercises JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'not_started',
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_course_lessons_position CHECK (position >= 1),
    CONSTRAINT ck_course_lessons_minutes CHECK (estimated_minutes >= 5 AND estimated_minutes <= 240),
    CONSTRAINT ck_course_lessons_status CHECK (status IN ('not_started', 'in_progress', 'completed'))
);

CREATE INDEX IF NOT EXISTS ix_course_lessons_user_id ON course_lessons (user_id);
CREATE INDEX IF NOT EXISTS ix_course_lessons_course_id ON course_lessons (course_id);
CREATE INDEX IF NOT EXISTS ix_course_lessons_level_id ON course_lessons (level_id);

CREATE TABLE IF NOT EXISTS course_resources (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    level_id UUID NULL REFERENCES course_levels(id) ON DELETE CASCADE,
    lesson_id UUID NULL REFERENCES course_lessons(id) ON DELETE SET NULL,
    title VARCHAR(180) NOT NULL,
    url VARCHAR(500) NOT NULL,
    resource_type VARCHAR(20) NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'fr',
    is_official BOOLEAN NOT NULL DEFAULT FALSE,
    source_name VARCHAR(120) NULL,
    notes VARCHAR(400) NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_course_resources_type CHECK (resource_type IN ('documentation', 'video', 'article', 'book', 'interactive')),
    CONSTRAINT ck_course_resources_language CHECK (language IN ('fr', 'en'))
);

CREATE INDEX IF NOT EXISTS ix_course_resources_user_id ON course_resources (user_id);
CREATE INDEX IF NOT EXISTS ix_course_resources_course_id ON course_resources (course_id);
CREATE INDEX IF NOT EXISTS ix_course_resources_level_id ON course_resources (level_id);

CREATE TABLE IF NOT EXISTS course_submissions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    level_id UUID NOT NULL REFERENCES course_levels(id) ON DELETE CASCADE,
    lesson_id UUID NULL REFERENCES course_lessons(id) ON DELETE SET NULL,
    submission_kind VARCHAR(20) NOT NULL,
    exercise_id VARCHAR(80) NULL,
    title VARCHAR(180) NOT NULL,
    answer_text TEXT NOT NULL,
    submitted_code TEXT NULL,
    reference_url VARCHAR(500) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'evaluated',
    score INTEGER NULL,
    passed BOOLEAN NULL,
    criteria_results JSONB NOT NULL DEFAULT '[]'::jsonb,
    feedback_markdown TEXT NULL,
    strengths JSONB NOT NULL DEFAULT '[]'::jsonb,
    improvements JSONB NOT NULL DEFAULT '[]'::jsonb,
    next_step_hint TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_course_submissions_kind CHECK (submission_kind IN ('exercise', 'project')),
    CONSTRAINT ck_course_submissions_status CHECK (status IN ('submitted', 'evaluated')),
    CONSTRAINT ck_course_submissions_score CHECK (score IS NULL OR (score >= 0 AND score <= 100))
);

CREATE INDEX IF NOT EXISTS ix_course_submissions_user_id ON course_submissions (user_id);
CREATE INDEX IF NOT EXISTS ix_course_submissions_course_id ON course_submissions (course_id);
CREATE INDEX IF NOT EXISTS ix_course_submissions_level_id ON course_submissions (level_id);

ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_submissions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "courses_owner_all" ON courses;
CREATE POLICY "courses_owner_all"
ON courses FOR ALL TO authenticated
USING ((select auth.uid()) = user_id)
WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "course_levels_owner_all" ON course_levels;
CREATE POLICY "course_levels_owner_all"
ON course_levels FOR ALL TO authenticated
USING ((select auth.uid()) = user_id)
WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "course_lessons_owner_all" ON course_lessons;
CREATE POLICY "course_lessons_owner_all"
ON course_lessons FOR ALL TO authenticated
USING ((select auth.uid()) = user_id)
WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "course_resources_owner_all" ON course_resources;
CREATE POLICY "course_resources_owner_all"
ON course_resources FOR ALL TO authenticated
USING ((select auth.uid()) = user_id)
WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "course_submissions_owner_all" ON course_submissions;
CREATE POLICY "course_submissions_owner_all"
ON course_submissions FOR ALL TO authenticated
USING ((select auth.uid()) = user_id)
WITH CHECK ((select auth.uid()) = user_id);
