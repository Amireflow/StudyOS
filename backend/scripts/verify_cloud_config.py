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
from app.core.database import Base, create_db_engine  # noqa: E402

EXPECTED_TABLES = set(Base.metadata.tables.keys())


def main() -> int:
    settings = get_settings()
    is_postgres = settings.database_url.startswith("postgresql")
    print(f"[1/4] Environnement : APP_ENV={settings.app_env}")
    print(f"[2/4] Moteur BDD   : {'PostgreSQL (Cloud)' if is_postgres else 'SQLite (Local)'}")

    if settings.app_env.lower() == "production":
        if settings.allow_local_dev_auth:
            print("ERREUR : ALLOW_LOCAL_DEV_AUTH doit être false en production.")
            return 1
        if settings.allow_insecure_local_ai_url:
            print("ERREUR : ALLOW_INSECURE_LOCAL_AI_URL doit être false en production.")
            return 1
        if len((settings.app_secret_key or "").strip()) < 32:
            print("ERREUR : APP_SECRET_KEY doit contenir au moins 32 caractères en production.")
            return 1
        if not settings.auth_jwks_url or not settings.auth_issuer:
            print("ERREUR : AUTH_JWKS_URL et AUTH_ISSUER sont requis en production.")
            return 1

    if settings.ai_key_encryption_key.strip():
        try:
            _parse_key_entry(settings.ai_key_encryption_key, default_key_id="v1")
        except Exception as exc:
            print(f"ERREUR : AI_KEY_ENCRYPTION_KEY invalide ({exc}).")
            return 1
    elif settings.app_env.lower() == "production":
        print("AVERTISSEMENT : AI_KEY_ENCRYPTION_KEY non défini (stockage de clés API IA utilisateurs désactivé).")

    _ = _decode_raw_32byte_key  # vérifie l'import de l'utilitaire crypto

    engine = create_db_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            inspector = inspect(conn)
            present_tables = set(inspector.get_table_names())
            missing = sorted(EXPECTED_TABLES - present_tables)
            print(
                f"[3/4] Tables BDD   : {len(EXPECTED_TABLES) - len(missing)}/{len(EXPECTED_TABLES)} présentes"
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
