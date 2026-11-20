# Guide Utilisateur & Déploiement Cloud — Amireflow Study OS v1.0

Ce guide synthétise l’utilisation quotidienne d’**Amireflow Study OS** (Parcours A à D du PRD v1.1) ainsi que la procédure de déploiement cloud, de sécurité et de sauvegarde/restauration (Cahier des charges §9, §12, §15).

---

## 1. Guide Utilisateur succinct (Parcours quotidiens)

### Parcours A — Démarrer sa journée (3 minutes)
1. Connectez-vous sur `/login` (compte serveur JWT/Supabase ou mode local autonome).
2. Sur le **Tableau de bord** (`/`), définissez ou vérifiez votre **Priorité principale** (liée à une tâche active ou à un projet prioritaire).
3. Consultez la colonne **Planning d’aujourd’hui** et les **5 tâches actives les plus urgentes**.
4. Optionnel : ouvrez le **Copilote IA** (`/ai-coach`) et cliquez sur **Briefing du jour**.

### Parcours B — Étudier et prouver sa progression
1. Dans **Apprentissage** (`/learning`), ouvrez votre parcours actif (ex. *Socle Python & FastAPI*), consultez le module en cours et marquez vos leçons terminées au fil de votre avancement.
   - *Rappel `LEARN-03` : terminer une leçon ne valide jamais automatiquement une compétence.*
2. Dans **Séances** (`/sessions`), lancez une séance en direct (ou enregistrez une séance passée) reliée à votre tâche, module, leçon ou compétence, puis clôturez-la en notant le **résultat concret produit**.
3. Dans **Compétences** (`/skills`), ajoutez une **preuve vérifiable** (exercice, code, projet, évaluation, livrable) et mettez à jour votre niveau sur l’échelle `0..5`.
   - *Alerte `SKILL-03` : toute compétence de niveau ≥ 3 (Autonome+) sans preuve est signalée automatiquement.*

### Parcours C — Réagir à un imprévu ou une surcharge
1. Ouvrez **Tâches** (`/tasks`) ou demandez au **Copilote IA** (`/ai-coach`) : *« Je suis en surcharge, mets une tâche secondaire au parking »*.
2. Validez la proposition `park_task` (ou cliquez sur **Parking** sur la carte d’une tâche) pour isoler les idées non prioritaires sans les perdre.

### Parcours D — Faire le bilan hebdomadaire
1. En fin de semaine, ouvrez **Copilote IA** (`/ai-coach`) et cliquez sur **Bilan hebdo**.
2. Analysez le temps réel d’étude (hors séances annulées, `SESSION-03`), les tâches achevées, les compétences ≥ 3 sans preuve et l’alerte anti-dispersion des projets (`> 3` projets actifs, `PROJ-01`).
3. Dans **Planning** (`/planning`), cliquez sur **Dupliquer vers la semaine suivante** pour reconduire vos créneaux récurrents en un clic.

---

## 2. Déploiement Cloud (Production)

### Architecture cible
- **Base de données & Auth :** Supabase (PostgreSQL managé + Supabase Auth JWKS).
- **Backend API :** Conteneur Docker Python 3.12 (`backend/Dockerfile`) déployé sur Render, Railway, Fly.io ou Google Cloud Run.
- **Frontend SPA :** Build statique Vite (`frontend/dist` + `frontend/vercel.json`) déployé sur Vercel, Netlify ou Cloudflare Pages.
- **Intégration continue (CI) :** GitHub Actions (`.github/workflows/ci.yml`) exécutant automatiquement Alembic, Pytest (25 tests), TypeScript strict, Vitest (40 tests) et le build de production.

### Étape 1 — Préparer la base PostgreSQL (Supabase)
1. Créez un projet Supabase et récupérez l’URL de connexion PostgreSQL (`postgresql+psycopg://...`), l’URL JWKS (`https://<PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`) et l’Issuer (`https://<PROJECT_REF>.supabase.co/auth/v1`).
2. Exécutez les migrations Alembic (`0001`, `0002`, `0003`) :
   ```bash
   cd backend
   DATABASE_URL="postgresql+psycopg://..." python -m alembic upgrade head
   ```
3. Appliquez les politiques Row-Level Security (défense en profondeur sur les 14 tables) dans l’éditeur SQL Supabase en exécutant [backend/alembic/rls_supabase.sql](./backend/alembic/rls_supabase.sql).

### Étape 2 — Déployer le Backend FastAPI
Configurez les variables d’environnement suivantes sur votre hébergeur (sans jamais les commiter) :
```env
APP_ENV=production
APP_SECRET_KEY=<secret-aleatoire-32-octets-minimum>
ALLOW_LOCAL_DEV_AUTH=false
DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@HOST:5432/postgres
AUTH_JWKS_URL=https://PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json
AUTH_ISSUER=https://PROJECT_REF.supabase.co/auth/v1
AUTH_AUDIENCE=authenticated
FRONTEND_ORIGIN=https://votre-domaine-frontend.app
AI_PROVIDER=local
# Optionnel : AI_PROVIDER=openai ou gemini, AI_API_KEY=..., AI_MODEL=...
```
> **Garde-fou intégré :** si `APP_ENV=production` et `ALLOW_LOCAL_DEV_AUTH=true`, le serveur refuse de démarrer afin d’empêcher toute exposition accidentelle des jetons de développement.

### Étape 3 — Déployer le Frontend React / Vite
Configurez les variables d’environnement du build frontend :
```env
VITE_API_BASE_URL=https://votre-api-backend.app/api/v1
VITE_SUPABASE_URL=https://PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=votre-cle-publique-anon-supabase
```
Commande de build : `npm ci && npm run build` (répertoire de sortie : `frontend/dist`).

---

## 3. Sauvegarde & Restauration de la base de données (CdC §9)

### Sauvegarde manuelle (avant migration majeure ou point de contrôle hebdomadaire)
```bash
pg_dump --format=custom --no-owner --no-privileges "$DATABASE_URL" --file="backup_amireflow_$(date +%Y%m%d).dump"
```

### Vérification & Restauration sur une base de secours
```bash
pg_restore --clean --if-exists --no-owner --no-privileges --dbname="$RESTORE_DATABASE_URL" "backup_amireflow_YYYYMMDD.dump"
```
Après restauration, vérifiez l’état de la révision Alembic (`python -m alembic current` → `0003_palier2_ai_copilot (head)`) et l’endpoint de santé `GET /health`.
