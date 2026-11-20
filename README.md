# Amireflow Study OS

Espace personnel de pilotage des études, de l'apprentissage par preuves et des projets, avec copilote IA contrôlé.

## Documentation de référence (v1.1)

- [PRD — Amireflow Study OS](./PRD-Amireflow-Study-OS.md)
- [Cahier des charges — Amireflow Study OS](./Cahier-des-charges-Amireflow-Study-OS.md)
- [Guide Utilisateur & Déploiement Cloud](./GUIDE-UTILISATEUR-ET-DEPLOIEMENT.md)

## Structure du dépôt

- `frontend/` : application web React + TypeScript strict + Vite + Tailwind CSS + TanStack Query
- `backend/` : API Python / FastAPI + SQLAlchemy 2 + Alembic + Auth JWT/JWKS + suite Pytest

## Lancer le frontend en local (Windows PowerShell)

> Note : si l'exécution de scripts PowerShell bloque `npm`, utilisez `npm.cmd`.

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

### Vérifications locales frontend

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
```

## Lancer le backend en local (Windows PowerShell)

> Note : sous Windows avec blocage de scripts PowerShell, invoquez directement `.\.venv\Scripts\python.exe` sans exécuter `Activate.ps1`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Documentation Swagger locale : `http://localhost:8000/docs`

### Bascule vers Supabase / PostgreSQL

1. Renseigner `DATABASE_URL` (`postgresql+psycopg://...`), `AUTH_JWKS_URL`, `AUTH_ISSUER` et `AUTH_AUDIENCE=authenticated` dans `.env` (ainsi que `VITE_SUPABASE_URL` et `VITE_SUPABASE_ANON_KEY` côté frontend).
2. Exécuter `.\.venv\Scripts\python.exe -m alembic upgrade head`.
3. Appliquer les politiques de défense en profondeur dans Supabase via [backend/alembic/rls_supabase.sql](./backend/alembic/rls_supabase.sql).

## Avancement des lots

### Palier 1 — Socle quotidien utilisable
- [x] **Lot 1 — Fondations UI** : initialisation React/TS/Vite/Tailwind, design system minimal, navigation FR responsive et tests de socle
- [x] **Lot 2 — Tableau de bord + Tâches + Séances** : priorité principale active, CRUD/filtres/parking des tâches, journal des séances et persistance `localStorage`
- [x] **Lot 3 — Planning hebdomadaire** : vue semaine, CRUD créneaux, conflits horaires, duplication et planning du jour sur le Dashboard
- [x] **Lot 4 — Backend Python / FastAPI** : API REST `/api/v1` (profil, dashboard, planning, tâches, séances), OpenAPI, format d'erreur uniforme et tests Pytest
- [x] **Lot 5 — PostgreSQL + Auth + Connexion Front/Back** : SQLAlchemy 2, migrations Alembic, politiques RLS Supabase, JWT/JWKS, `RequireAuth`, TanStack Query et Paramètres P0

### Palier 2 — Apprentissage, Projets, IA & Cloud
- [x] **Lot 6 — Apprentissage + Compétences/Preuves + Projets (P1)** : parcours/modules/leçons (`LEARN-01`–`LEARN-04`), compétences 0–5 et preuves vérifiables (`SKILL-01`–`SKILL-03`), projets avec prochaine action obligatoire et alerte anti-dispersion (`PROJ-01`–`PROJ-03`), migration Alembic `0002` et politiques RLS
- [x] **Lot 7 — Copilote IA contrôlé + Briefing/Bilan (P1)** : `ContextBuilder`, `PromptManager`, `AIProvider` (local + OpenAI-compatible + Gemini), `ToolRegistry`, `ActionValidator`, `AIOrchestrator` (`AI-01`–`AI-07`), propositions validables/ajustables/rejetables, briefing quotidien et bilan hebdomadaire, migration Alembic `0003` et politiques RLS
- [x] **Lot 8 — Stabilisation, Tests E2E & Déploiement cloud** : scénarios d'acceptation de bout en bout (`E2E-01` à `E2E-04`) backend & frontend, pipeline CI GitHub Actions (`.github/workflows/ci.yml`), `Dockerfile` backend non-root, garde-fous de sécurité de production, configuration SPA cloud (`frontend/vercel.json`) et guide utilisateur/déploiement/sauvegarde
