-- Migration Supabase : Comptes utilisateurs authentifiés (table users avec RLS strict)

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    token_version INTEGER NOT NULL DEFAULT 1,
    last_login_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_users_token_version CHECK (token_version >= 1)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- RLS activée sans politique pour `authenticated` : aucun accès direct client à password_hash.
-- Seul le backend / service_role manipule la table users.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
