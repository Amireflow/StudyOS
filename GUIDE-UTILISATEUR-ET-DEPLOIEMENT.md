# Guide Utilisateur & Déploiement Cloud — Amireflow Study OS v1.0

Ce guide synthétise l’utilisation quotidienne d’**Amireflow Study OS** (Parcours A à D du PRD v1.1) ainsi que la procédure de déploiement cloud, de sécurité et de sauvegarde/restauration (Cahier des charges §9, §12, §15).

---

## 1. Guide Utilisateur succinct (Parcours quotidiens)

### Parcours A — Démarrer sa journée (3 minutes)
1. Connectez-vous ou créez votre compte sur `/login`.
2. Sur le **Tableau de bord** (`/`), définissez ou vérifiez votre **Priorité principale** (liée à une tâche active ou à un projet prioritaire).
3. Consultez la colonne **Planning d’aujourd’hui** et les **5 tâches actives les plus urgentes**.
4. Optionnel : ouvrez le **Copilote IA** (`/ai-coach`) et cliquez sur **Briefing du jour**.

### Parcours B — Étudier et prouver sa progression
1. Dans **Apprentissage** (`/learning`), ouvrez votre parcours actif (ex. *Socle Python & FastAPI*), consultez le module en cours et marquez vos leçons terminées au fil de votre avancement.
   - *Rappel `LEARN-03` : terminer une leçon ne valide jamais automatiquement une compétence.*
2. Dans **Séances** (`/sessions`), lancez une séance en direct (ou enregistrez une séance passée) reliée à votre tâche, module, leçon ou compétence, puis clôturez-la en notant le **résultat concret produit**.
3. Dans **Compétences** (`/skills`), cliquez sur **Évaluer cette compétence** pour lancer une épreuve adaptée à votre niveau visé (`1..5`), utilisez les indices progressifs si besoin, soumettez votre production réelle accompagnée d’une **preuve concrète** (exercice, code, projet, livrable), lancez la correction selon les 4 critères pédagogiques puis validez le passage de niveau.
   - *Verrou pédagogique : toute nouvelle compétence démarre au niveau 0 et aucune modification directe du niveau n’est possible sans évaluation validée et preuve admissible.*
   - *Alerte `SKILL-03` : toute compétence historique de niveau ≥ 3 (Autonome+) sans preuve est signalée automatiquement.*

### Parcours C — Réagir à un imprévu ou une surcharge
1. Ouvrez **Tâches** (`/tasks`) ou demandez au **Copilote IA** (`/ai-coach`) : *« Je suis en surcharge, mets une tâche secondaire au parking »*.
2. Validez la proposition `park_task` (ou cliquez sur **Parking** sur la carte d’une tâche) pour isoler les idées non prioritaires sans les perdre.

### Parcours D — Faire le bilan hebdomadaire & importer son emploi du temps
1. En début de semestre ou de semaine, ouvrez **Planning** (`/planning`) et cliquez sur **Importer mon emploi du temps**.
2. Glissez-déposez votre fichier (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.xlsx`, `.xls`, `.docx`), vérifiez le tableau d’aperçu modifiable et les anomalies éventuelles (horaires manquants, chevauchements, doublons), puis cliquez sur **Enregistrer mon emploi du temps**.
3. Le **Copilote IA** (`/ai-coach`) connaît alors vos cours universitaires verrouillés et planifie vos séances de révision, devoirs et projets uniquement sur vos périodes libres (avec préservation des pauses).
4. En fin de semaine, ouvrez **Copilote IA** (`/ai-coach`) et cliquez sur **Bilan hebdo**.
5. Analysez le temps réel d’étude (hors séances annulées, `SESSION-03`), les tâches achevées, les compétences ≥ 3 sans preuve et l’alerte anti-dispersion des projets (`> 3` projets actifs, `PROJ-01`).
6. Dans **Planning** (`/planning`), cliquez sur **Dupliquer vers la semaine suivante** pour reconduire vos créneaux récurrents en un clic.

---

## 2. Déploiement Cloud (Production)

### Architecture cible
- **Base de données & Auth :** Supabase (PostgreSQL managé + Supabase Auth JWKS).
- **Backend API :** Conteneur Docker Python 3.12 (`backend/Dockerfile`) déployé sur Render, Railway, Fly.io ou Google Cloud Run.
- **Frontend SPA :** Build statique Vite (`frontend/dist`) déployé sur Render Static Site (via `render.yaml`), Vercel (`frontend/vercel.json`), Netlify (`netlify.toml`) ou Cloudflare Pages.
- **Intégration continue (CI) :** GitHub Actions (`.github/workflows/ci.yml`) exécutant automatiquement Alembic (`upgrade head`, réversibilité `downgrade base -> upgrade head`), Pytest, TypeScript strict, Vitest et le build de production.

### Étape 1 — Préparer la base PostgreSQL (Supabase)
1. Créez un projet Supabase et récupérez l’URL de connexion PostgreSQL (`postgresql+psycopg://...`), l’URL JWKS (`https://<PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`) et l’Issuer (`https://<PROJECT_REF>.supabase.co/auth/v1`).
   - *Important pour Render :* Render émet ses connexions sortantes uniquement en **IPv4**. Avec Supabase, utilisez l’URL **Session Pooler** (port `5432`, hôte `*.pooler.supabase.com`) ou **Transaction Pooler** (port `6543`) plutôt que l’hôte direct `db.<ref>.supabase.co:5432` (IPv6-first).
2. Exécutez les migrations Alembic (`0001` à `0013_schedule_event_links`) :
   ```bash
   cd backend
   DATABASE_URL="postgresql+psycopg://..." python -m alembic upgrade head
   ```
3. Appliquez les politiques Row-Level Security idempotentes (couvrant les 30 tables applicatives/auth) dans l’éditeur SQL Supabase en exécutant [backend/alembic/rls_supabase.sql](./backend/alembic/rls_supabase.sql) ou les migrations incrémentales dans [supabase/migrations/](./supabase/migrations/).
4. Vérifiez l’état de préparation avant bascule :
   ```bash
   cd backend
   python scripts/verify_cloud_config.py
   ```

### Étape 2 — Déployer le Backend FastAPI
Configurez les variables d’environnement suivantes sur votre hébergeur (sans jamais les commiter) :
```env
APP_ENV=production
APP_SECRET_KEY=<secret-aleatoire-32-octets-minimum>
AI_KEY_ENCRYPTION_KEY=<cle-aes256-32-octets-base64-ou-hex>
# Optionnel pour rotation sans coupure : AI_KEY_ENCRYPTION_FALLBACK_KEYS=k0:<ancienne_cle>
ALLOW_LOCAL_DEV_AUTH=false
ALLOW_INSECURE_LOCAL_AI_URL=false
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:PASSWORD@aws-0-eu-west-3.pooler.supabase.com:5432/postgres
AUTH_JWKS_URL=https://PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json
AUTH_ISSUER=https://PROJECT_REF.supabase.co/auth/v1
AUTH_AUDIENCE=authenticated
# Utilisez "none" si frontend et backend sont sur des domaines distincts (*.onrender.com), ou "lax" sur le même domaine racine
AUTH_COOKIE_SAMESITE=none
FRONTEND_ORIGIN=https://votre-domaine-frontend.app
AI_PROVIDER=local
# Optionnel : AI_PROVIDER=openai ou gemini, AI_API_KEY=..., AI_MODEL=...
```
> **Garde-fous intégrés :** si `APP_ENV=production` et `ALLOW_LOCAL_DEV_AUTH=true`, `ALLOW_INSECURE_LOCAL_AI_URL=true`, `APP_SECRET_KEY` < 32 caractères ou `FRONTEND_ORIGIN=*`, le serveur refuse de démarrer. Le stockage de clés API IA utilisateur échoue de façon sûre (`503`) si `AI_KEY_ENCRYPTION_KEY` est absent. Le conteneur Docker embarque `tesseract-ocr` (`fra`/`eng`) et un `HEALTHCHECK` interrogeant `GET /health`.

### Étape 3 — Déployer le Frontend React / Vite
Configurez les variables d’environnement du build frontend :
```env
VITE_API_BASE_URL=https://votre-api-backend.app/api/v1
VITE_SUPABASE_URL=https://PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=votre-cle-publique-anon-supabase
```
Commande de build : `npm ci && npm run build` (répertoire de sortie : `frontend/dist`).

### Étape 4 — Déploiement sur Render (Blueprint `render.yaml`)
Le fichier [render.yaml](./render.yaml) provisionne en une fois les deux services :
- `amireflow-study-os-api` (Web Service Docker, région `frankfurt`, `rootDir: backend`, `healthCheckPath: /health`).
- `amireflow-study-os-web` (Static Site CDN, `rootDir: frontend`, Node `22`, réécriture SPA `/* -> /index.html`).

1. **Créer le Blueprint** : dans Render Dashboard, cliquez sur **New → Blueprint**, sélectionnez le dépôt GitHub `AmireflowStudyOS` (branche `main`) et laissez Render détecter [render.yaml](./render.yaml).
2. **Renseigner les variables synchronisées manuellement (`sync: false`)** :
   - Générer une clé AES-256-GCM 32 octets pour `AI_KEY_ENCRYPTION_KEY` :
     ```bash
     python -c "import secrets; print('k1:' + secrets.token_hex(32))"
     ```
   - Sur `amireflow-study-os-api` : `DATABASE_URL` (Session/Transaction Pooler Supabase en IPv4 ou PostgreSQL Render managé), `AI_KEY_ENCRYPTION_KEY`, `FRONTEND_ORIGIN` (laissez une URL temporaire si besoin au 1er déploiement puis mettez l’URL finale exacte du frontend sans slash final).
   - Sur `amireflow-study-os-web` : `VITE_API_BASE_URL` = `<URL_HTTPS_API>/api/v1` (ex. `https://amireflow-study-os-api.onrender.com/api/v1`). *Note : `VITE_*` est injecté au build — relancez **Manual Deploy** sur `amireflow-study-os-web` si vous modifiez `VITE_API_BASE_URL` après le premier déploiement.*
3. **Finaliser le câblage CORS** : vérifiez que `FRONTEND_ORIGIN` sur l’API correspond exactement à l’URL HTTPS publique du Static Site (et inversement que `VITE_API_BASE_URL` pointe vers l’API publique), sans slash final.
4. **Spécificités du plan Render Free** :
   - *Mise en veille (cold start)* : le service Docker Free se met en veille après ~15 min d’inactivité et redémarre en ~30–50 s à la première requête HTTP.
   - *Migrations Alembic* : le plan Free ne supporte pas `preDeployCommand` ; `backend/Dockerfile` exécute `python -m alembic upgrade head` automatiquement au démarrage du conteneur avant Uvicorn.
   - *Cookies de session (`refresh_token` HttpOnly)* : `AUTH_COOKIE_SAMESITE=none` + `Secure` est configuré dans `render.yaml` pour les sous-domaines distincts `*.onrender.com`. Pour éviter tout blocage des cookies tiers sur Safari/Brave, associez un domaine personnalisé commun (ex. `app.votredomaine.com` et `api.votredomaine.com`) puis passez `AUTH_COOKIE_SAMESITE=lax`.
5. **Checklist de validation post-déploiement** :
   - `GET https://<votre-api>.onrender.com/` → `200` `{"service": "Amireflow Study OS API", "status": "ok", "health": "/health"}`.
   - `GET https://<votre-api>.onrender.com/health` → `200` `{"status": "ok", "env": "production", "database": "ok"}`.
   - Dans le Shell Render du service API : `python scripts/verify_cloud_config.py` → révision Alembic `0013_schedule_event_links` et `30/30` tables.
   - Ouvrir `https://<votre-web>.onrender.com/login` (et tester un rechargement direct sur `/tasks` ou `/planning` pour valider le rewrite SPA), créer/connecter un compte, puis rafraîchir la page (`F5`).

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
Après restauration, vérifiez l’état de la révision Alembic (`python -m alembic current` → `0013_schedule_event_links (head)`) et l’endpoint de santé `GET /health` (`database: ok`).
