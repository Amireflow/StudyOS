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

1. Renseigner `DATABASE_URL` (`postgresql+psycopg://...`), `APP_SECRET_KEY` (32+ caractères aléatoires), `AI_KEY_ENCRYPTION_KEY` (clé AES-256-GCM 32 octets encodée base64 ou hex pour le chiffrement des clés IA), `AUTH_JWKS_URL`, `AUTH_ISSUER`, `AUTH_AUDIENCE=authenticated`, `ALLOW_LOCAL_DEV_AUTH=false` et `ALLOW_INSECURE_LOCAL_AI_URL=false` dans `.env` (ainsi que `VITE_SUPABASE_URL` et `VITE_SUPABASE_ANON_KEY` côté frontend).
2. Exécuter `.\.venv\Scripts\python.exe -m alembic upgrade head` (applique les migrations réversibles `0001` à `0013_schedule_event_links`).
3. Appliquer les politiques idempotentes de défense en profondeur dans Supabase via [backend/alembic/rls_supabase.sql](./backend/alembic/rls_supabase.sql) (couvre les 30 tables applicatives/auth).
4. Vérifier la configuration cloud avant déploiement avec `.\.venv\Scripts\python.exe scripts/verify_cloud_config.py` et contrôler `/health` (vérifie la connectivité réelle à la base et renvoie `503` sans fuite de secret en cas de panne).

### Déploiement sur Render

Un Blueprint full-stack prêt à l'emploi ([render.yaml](./render.yaml)) déploie simultanément l'API Docker (`amireflow-study-os-api`) et le site statique SPA (`amireflow-study-os-web`). Consultez la section **Déploiement sur Render** dans [GUIDE-UTILISATEUR-ET-DEPLOIEMENT.md](./GUIDE-UTILISATEUR-ET-DEPLOIEMENT.md) pour la configuration des secrets et du Session Pooler IPv4 Supabase.

## Verrou pédagogique & Validation réelle des compétences

Le niveau d'une compétence (`current_level`, échelle `0..5`) est protégé côté serveur et côté interface :

- **Création verrouillée au niveau `0`** : toute nouvelle compétence démarre au niveau `0` (`last_assessed_at = null`). Une tentative de création directe avec `current_level > 0` est refusée par l'API (`422 SKILL_INITIAL_LEVEL_LOCKED`). Les compétences historiques déjà enregistrées conservent leur niveau.
- **Modification directe interdite** : `PATCH /api/v1/skills/{skill_id}` permet de modifier `name`, `domain`, `description` et `target_level`, mais rejette toute modification directe de `current_level` (`403 SKILL_ASSESSMENT_REQUIRED`).
- **Qualité des preuves & transparence** : les simples auto-déclarations (ex. *« j'ai compris Python »*) sont rejetées (`422 EVIDENCE_QUALITY_INSUFFICIENT`). Toute URL externe est enregistrée avec une mention explicite indiquant qu'elle n'est pas inspectée automatiquement par le serveur (`external_reference_verified: false`).
- **Cycle de vie d'une évaluation (`skill_assessments`)** :
  1. `pending` : épreuve générée (`POST /api/v1/skills/{skill_id}/assessments`) avec consignes, grille de 4 critères explicites (`/100`) et indices progressifs (`POST .../hint`).
  2. `submitted` : production réelle soumise (`POST .../submit`) avec texte explicatif, code optionnel et preuves concrètes appartenant à l'utilisateur et à la compétence.
  3. `evaluated` : correction selon les critères (`POST .../evaluate`), score, éléments maîtrisés, lacunes identifiées et recommandation d'exercice correctif si nécessaire.
  4. `approved` / `rejected` / `cancelled` : seule la validation d'une évaluation réussie (`POST .../validate`, score suffisant + preuve admissible revalidée en base) met à jour `current_level` de manière atomique et à usage unique (`409 ASSESSMENT_ALREADY_APPROVED` en cas de réutilisation).
- **Copilote IA aligné** : l'outil `update_skill_level` est supprimé de `ToolRegistry` au profit de `propose_skill_assessment` (préparation d'épreuve) et `recommend_skill_progression` (recommandation soumise à revalidation serveur complète lors de l'acceptation).

## Import intelligent de l'emploi du temps & Connexion au Copilote IA

Le module **Planning** intègre un système complet d'importation, d'extraction, de vérification et d'intégration de l'emploi du temps universitaire :

- **Formats supportés & sécurité** : PDF (`.pdf`), Images (`.png`, `.jpg`, `.jpeg`, `.webp`), Excel (`.xlsx`, `.xls`) et Word (`.docx`) avec vérification côté serveur de la taille (`<= 10 Mo`), de l'extension, du type MIME, de la signature binaire réelle (magic bytes) et limitation de fréquence.
- **Extraction intelligente sans hallucination** : détection des matières, types de séances (`cours`, `td`, `tp`, `examen`), jours, heures de début/fin, enseignants, salles, groupes et dates de validité (avec résolution des cellules fusionnées Excel/Word). Tout horaire illisible est signalé comme incertain (`uncertain: true`) sans jamais inventer de donnée.
- **Aperçu modifiable & validation explicite obligatoire** :
  - `POST /api/v1/schedule/imports/analyze` analyse le document et crée une session `pending_review` dans `timetable_imports` sans enregistrer aucun cours dans `schedule_events`.
  - Détection automatique des anomalies (`missing_time`, `invalid_duration`, `missing_subject`, `duplicate_course`, `overlap_conflict`, `existing_calendar_conflict`).
  - Modification manuelle (`PATCH /api/v1/schedule/imports/{id}`), annulation (`POST .../cancel`), validation explicite (`POST .../confirm` avec déduplication, récurrence hebdomadaire et remplacement optionnel sans perte d'historique) et suppression de l'aperçu source (`DELETE .../source`).
- **Connexion au Context Builder & Copilote IA** : le Copilote distingue les cours universitaires verrouillés des séances personnelles, calcule les disponibilités réelles avec pauses préservées (`availability.today` et `availability.tomorrow`), planifie les révisions en dehors des cours et refuse toute proposition de séance personnelle chevauchant un cours universitaire (`409 UNIVERSITY_COURSE_CONFLICT`).

## Planification conversationnelle stratégique du Copilote IA

Le Copilote IA agit comme un conseiller pédagogique et stratégique (`DISCUTER → ANALYSER → PROPOSER → VALIDER → PROGRAMMER → SUIVRE → ÉVALUER`) :

- **Analyse stratégique & protection des priorités** : avant toute programmation (`plan_strategic_activity`), le Copilote analyse les disponibilités réelles sur 7 jours (`availability.weekly_candidate_slots`), la charge hebdomadaire, les tâches critiques, l'emploi du temps universitaire et le coût d'opportunité. Toute idée risquant de détourner de la priorité principale active déclenche `STOP — DISPERSION DÉTECTÉE.` et une recommandation vers le Parking.
- **Décisions explicites** : `ACCEPTABLE`, `ACCEPTABLE SOUS CONDITIONS` (avec ajustements) ou `NON RECOMMANDÉE POUR LE MOMENT` (sans jamais inventer de disponibilités).
- **Validation, modification et suivi** : l'utilisateur peut accepter et programmer (`POST /api/v1/ai/proposals/{id}/accept`), modifier/recalculer (`PATCH /api/v1/ai/proposals/{id}`) ou refuser (`POST .../reject`). Toute dérive du calendrier entre la proposition et l'acceptation est bloquée côté serveur (`409 SCHEDULE_CONFLICT_DETECTED`), la double validation est impossible (`409 CONFLICT`), et les séances planifiées non réalisées sont détectées dans le suivi (`missed_study_blocks_count`).

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
- [x] **Verrou pédagogique & Évaluations de compétences** : table `skill_assessments` (migration Alembic `0004` + RLS Supabase), verrouillage des créations/modifications directes de niveau, contrôle qualité des preuves, flux d'évaluation complet (`pending` → `submitted` → `evaluated` → `approved`/`rejected`/`cancelled`), accompagnement Copilote IA et interface d'évaluation responsive clair/sombre
- [x] **Import intelligent de l'emploi du temps** : table `timetable_imports` et métadonnées de cours sur `schedule_events` (migration Alembic `0005` + RLS Supabase), extracteur multi-format (PDF, Images, Excel, Word), aperçu modifiable avec détection d'anomalies et de chevauchements, validation obligatoire et planification quotidienne IA sans conflit avec les cours universitaires
- [x] **Planification conversationnelle stratégique du Copilote IA** : outil `plan_strategic_activity`, analyse sur 21 jours sans surcharge, détection `STOP — DISPERSION DÉTECTÉE.`, décisions `ACCEPTABLE` / `ACCEPTABLE SOUS CONDITIONS` / `NON RECOMMANDÉE`, modification/recalcul (`PATCH /proposals/{id}`), validation atomique et suivi des séances non réalisées.
- [x] **Audit & Finalisation P0 / P1 / P2** : chiffrement AES-256-GCM des clés IA (`AI_KEY_ENCRYPTION_KEY`, rotation `AI_KEY_ENCRYPTION_FALLBACK_KEYS`), protection anti-SSRF sur les URL IA personnalisées, rafraîchissement JWT en cookie `HttpOnly` + révocation JTI, inspection GitHub contrôlée sans invention, moteur de cours structuré en 8 parties (sans lien YouTube inventé ni exécution de code non isolée), limite stricte de 3 projets actifs (statut `paused`) et 3 tâches critiques actives, dashboard 12 blocs, remplacement ciblé d'EDT avec `replace-preview`/`restore`, et `/health` SQL live (`503` sans fuite en cas de panne).
