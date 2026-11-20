r"""Script de diagnostic avant déploiement cloud (Supabase PostgreSQL, JWKS & variables d'environnement).

Usage :
  cd backend
  .\.venv\Scripts\python.exe scripts/verify_cloud_config.py
"""

from pathlib import Path
import sys
from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401,E402 - enregistre toutes les tables ORM dans Base.metadata
from app.core.config import get_settings  # noqa: E402
from app.core.crypto import _decode_raw_32byte_key, _parse_key_entry  # noqa: E402
from app.core.database import Base, create_db_engine, normalize_database_url  # noqa: E402

EXPECTED_TABLES = set(Base.metadata.tables.keys())
_DEFAULT_SECRETS = {
    "",
    "local-dev-secret-key-change-me-32bytes",
    "change-me-in-local-env",
}


def main() -> int:
    settings = get_settings()
    normalized_db_url = normalize_database_url(settings.database_url.strip())
    is_postgres = normalized_db_url.startswith("postgresql")
    is_prod = settings.app_env.strip().lower() == "production"
    spa_dist = (
        Path(settings.frontend_dist_dir.strip())
        if settings.frontend_dist_dir.strip()
        else None
    )
    has_spa_dist = bool(spa_dist and (spa_dist / "index.html").is_file())

    print(f"[1/4] Environnement : APP_ENV={settings.app_env}")
    print(f"[2/4] Moteur BDD   : {'PostgreSQL (Cloud)' if is_postgres else 'SQLite (Local)'}")
    if has_spa_dist:
        print(f"      Mode unifié  : Frontend SPA servi depuis {spa_dist}")

    if is_prod:
        if settings.allow_local_dev_auth:
            print("ERREUR : ALLOW_LOCAL_DEV_AUTH doit être false en production.")
            return 1
        if settings.allow_insecure_local_ai_url:
            print("ERREUR : ALLOW_INSECURE_LOCAL_AI_URL doit être false en production.")
            return 1
        secret = (settings.app_secret_key or "").strip()
        if secret in _DEFAULT_SECRETS or len(secret) < 32:
            print(
                "ERREUR : APP_SECRET_KEY doit contenir au moins 32 caractères non par défaut en production."
            )
            return 1
        if "*" in settings.cors_origins:
            print("ERREUR : FRONTEND_ORIGIN ne doit pas autoriser '*' en production.")
            return 1
        if (not has_spa_dist or settings.frontend_origin.strip()) and any(
            "localhost" in origin or "127.0.0.1" in origin for origin in settings.cors_origins
        ):
            print(
                "AVERTISSEMENT : FRONTEND_ORIGIN contient localhost/127.0.0.1 en production "
                f"({', '.join(settings.cors_origins)})."
            )
        if settings.database_url.strip() == "sqlite:///./amireflow_local.db":
            print("ERREUR : DATABASE_URL SQLite par défaut interdit en production.")
            return 1
        if not settings.auth_jwks_url or not settings.auth_issuer:
            print("ERREUR : AUTH_JWKS_URL et AUTH_ISSUER sont requis en production.")
            return 1
        if ".supabase.co:5432" in normalized_db_url and "@db." in normalized_db_url:
            print(
                "AVERTISSEMENT : l'hôte direct Supabase (@db.*.supabase.co:5432) est IPv6-first ; "
                "sur Render (egress IPv4), utilisez le Supabase Session/Transaction Pooler (*.pooler.supabase.com)."
            )

    if settings.ai_key_encryption_key.strip():
        try:
            _parse_key_entry(settings.ai_key_encryption_key, default_key_id="k1")
        except Exception as exc:
            print(f"ERREUR : AI_KEY_ENCRYPTION_KEY invalide ({exc}).")
            return 1
    elif is_prod:
        print("AVERTISSEMENT : AI_KEY_ENCRYPTION_KEY non défini (stockage de clés API IA utilisateurs désactivé).")

    if settings.ai_key_encryption_fallback_keys.strip():
        for idx, item in enumerate(settings.ai_key_encryption_fallback_keys.split(","), start=2):
            cleaned = item.strip()
            if not cleaned:
                continue
            try:
                _parse_key_entry(cleaned, default_key_id=f"k{idx}")
            except Exception as exc:
                print(f"ERREUR : AI_KEY_ENCRYPTION_FALLBACK_KEYS invalide ({exc}).")
                return 1

    _ = _decode_raw_32byte_key  # vérifie l'import de l'utilitaire crypto

    engine = create_db_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            inspector = inspect(conn)
            present_tables = set(inspector.get_table_names())
            missing = sorted(EXPECTED_TABLES - present_tables)
            alembic_rev = "non initialisée"
            if "alembic_version" in present_tables:
                rev_row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
                if rev_row:
                    alembic_rev = str(rev_row)
            print(
                f"[3/4] Tables BDD   : {len(EXPECTED_TABLES) - len(missing)}/{len(EXPECTED_TABLES)} présentes "
                f"(révision Alembic : {alembic_rev})"
            )
            if missing:
                print(f"      Tables manquantes (exécutez `alembic upgrade head`) : {', '.join(missing)}")
                return 1
    finally:
        engine.dispose()

    print(
        f"[4/4] Copilote IA  : fournisseur={settings.ai_provider or 'local'} · modèle={settings.ai_model}"
    )
    print("Diagnostic réussi : la base et la configuration sont prêtes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
