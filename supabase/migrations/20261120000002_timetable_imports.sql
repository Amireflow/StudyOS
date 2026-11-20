-- Migration Supabase : Import intelligent de l'emploi du temps (timetable_imports + colonnes schedule_events + RLS)

CREATE TABLE IF NOT EXISTS timetable_imports (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_format VARCHAR(20) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    file_sha256 VARCHAR(64) NOT NULL,
    source_preview_text TEXT NULL,
    source_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending_review',
    valid_from VARCHAR(10) NULL,
    valid_until VARCHAR(10) NULL,
    extracted_courses JSONB NOT NULL DEFAULT '[]'::jsonb,
    anomalies JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_events_count INTEGER NOT NULL DEFAULT 0,
    skipped_duplicates_count INTEGER NOT NULL DEFAULT 0,
    replaced_events_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    validated_at TIMESTAMPTZ NULL,
    CONSTRAINT ck_timetable_imports_status CHECK (status IN ('pending_review', 'validated', 'cancelled')),
    CONSTRAINT ck_timetable_imports_format CHECK (file_format IN ('pdf', 'image', 'excel', 'word')),
    CONSTRAINT ck_timetable_imports_size CHECK (file_size_bytes > 0)
);

CREATE INDEX IF NOT EXISTS ix_timetable_imports_user_id ON timetable_imports (user_id);
CREATE INDEX IF NOT EXISTS ix_timetable_imports_status ON timetable_imports (status);
CREATE INDEX IF NOT EXISTS ix_timetable_imports_created_at ON timetable_imports (created_at);

ALTER TABLE schedule_events
    ADD COLUMN IF NOT EXISTS source VARCHAR(30) NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS import_id UUID NULL REFERENCES timetable_imports(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS session_subtype VARCHAR(20) NULL,
    ADD COLUMN IF NOT EXISTS teacher VARCHAR(120) NULL,
    ADD COLUMN IF NOT EXISTS room VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS group_name VARCHAR(100) NULL;

CREATE INDEX IF NOT EXISTS ix_schedule_import_id ON schedule_events (import_id);

ALTER TABLE timetable_imports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "timetable_imports_owner_all" ON timetable_imports;
CREATE POLICY "timetable_imports_owner_all"
ON timetable_imports
FOR ALL
TO authenticated
USING ((select auth.uid()) = user_id)
WITH CHECK ((select auth.uid()) = user_id);
