-- =============================================================================
-- Amireflow Study OS — Migration Verrou Pédagogique (skill_assessments + RLS)
-- À exécuter après 20261120000000_amireflow_v1_schema_and_rls.sql
-- Préserve intégralement les compétences et preuves existantes.
-- =============================================================================

CREATE TABLE IF NOT EXISTS skill_assessments (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    path_id UUID REFERENCES learning_paths(id) ON DELETE SET NULL,
    module_id UUID REFERENCES learning_modules(id) ON DELETE SET NULL,
    lesson_id UUID REFERENCES lessons(id) ON DELETE SET NULL,
    assessment_type VARCHAR(30) NOT NULL DEFAULT 'practical_exercise',
    starting_level INTEGER NOT NULL,
    target_level INTEGER NOT NULL,
    proposed_level INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    prompt_title VARCHAR(180) NOT NULL,
    prompt_instructions TEXT NOT NULL,
    hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    hints_revealed_count INTEGER NOT NULL DEFAULT 0,
    submission_text TEXT,
    submission_code TEXT,
    submission_reference_url VARCHAR(500),
    evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
    score INTEGER,
    passed BOOLEAN,
    feedback TEXT,
    mastered_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    gaps_identified JSONB NOT NULL DEFAULT '[]'::jsonb,
    remediation_recommendation TEXT,
    external_verification_warning TEXT,
    evaluator_type VARCHAR(30) NOT NULL DEFAULT 'pedagogical_engine',
    evaluator_name VARCHAR(80),
    decision_reason TEXT,
    applied_level_delta INTEGER,
    submitted_at TIMESTAMPTZ,
    evaluated_at TIMESTAMPTZ,
    validated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_skill_assessments_starting_level CHECK (starting_level >= 0 AND starting_level <= 5),
    CONSTRAINT ck_skill_assessments_target_level CHECK (target_level >= 1 AND target_level <= 5),
    CONSTRAINT ck_skill_assessments_proposed_level CHECK (proposed_level IS NULL OR (proposed_level >= 0 AND proposed_level <= 5)),
    CONSTRAINT ck_skill_assessments_score CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
    CONSTRAINT ck_skill_assessments_hints_revealed CHECK (hints_revealed_count >= 0),
    CONSTRAINT ck_skill_assessments_status CHECK (status IN ('pending', 'submitted', 'evaluated', 'approved', 'rejected', 'cancelled')),
    CONSTRAINT ck_skill_assessments_type CHECK (assessment_type IN ('quiz', 'practical_exercise', 'code_review', 'explanation', 'deliverable', 'mixed'))
);

CREATE INDEX IF NOT EXISTS ix_skill_assessments_user_id ON skill_assessments (user_id);
CREATE INDEX IF NOT EXISTS ix_skill_assessments_skill_id ON skill_assessments (skill_id);
CREATE INDEX IF NOT EXISTS ix_skill_assessments_status ON skill_assessments (status);
CREATE INDEX IF NOT EXISTS ix_skill_assessments_user_skill ON skill_assessments (user_id, skill_id);
CREATE INDEX IF NOT EXISTS ix_skill_assessments_path_id ON skill_assessments (path_id);
CREATE INDEX IF NOT EXISTS ix_skill_assessments_module_id ON skill_assessments (module_id);
CREATE INDEX IF NOT EXISTS ix_skill_assessments_lesson_id ON skill_assessments (lesson_id);

ALTER TABLE skill_assessments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "skill_assessments_owner_all" ON skill_assessments;
CREATE POLICY "skill_assessments_owner_all"
ON skill_assessments
FOR ALL
TO authenticated
USING ((select auth.uid()) = user_id)
WITH CHECK ((select auth.uid()) = user_id);
