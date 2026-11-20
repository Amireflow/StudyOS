# Cahier des charges — Amireflow Study OS

**Version :** 1.1  
**Date :** 19 novembre 2026  
**Statut :** Référence consolidée — prête pour le développement (Lot 1)  
**Référence produit :** `PRD-Amireflow-Study-OS.md`

---

## 1. Objet du document

Ce document décrit les exigences fonctionnelles, techniques, de données, de sécurité et de validation pour construire le MVP d’Amireflow Study OS.

L’application est un outil web personnel, hébergé dans le cloud, qui regroupe le planning, les tâches, les parcours d’apprentissage, les compétences, les projets et un copilote IA. Le développement sert également de parcours pratique pour apprendre React, TypeScript et Python.

## 2. Périmètre et hypothèses

### 2.1 Périmètre obligatoire

- Application web responsive.
- Un utilisateur principal.
- Interface en français au lancement.
- Fuseau horaire configurable, valeur initiale : `Africa/Dakar`.
- Frontend React + TypeScript.
- Backend Python avec FastAPI.
- Base de données PostgreSQL managée.
- Authentification gérée par un fournisseur spécialisé, avec Supabase Auth comme option de référence.
- IA appelée depuis le backend, jamais directement depuis le navigateur avec une clé secrète.

### 2.2 Hypothèses à ne pas confondre avec des décisions définitives

- Hébergement frontend envisagé : Vercel ou équivalent.
- Hébergement backend : service cloud compatible avec une application Python persistante ou serverless adaptée.
- Base PostgreSQL envisagée : Supabase ou fournisseur équivalent.
- Fournisseur IA non choisi à ce stade ; l’application doit isoler son intégration derrière une interface commune.
- Voix non requise pour le MVP.
- Toute mutation demandée par l’IA nécessite une confirmation explicite.

## 3. Architecture cible

```text
Navigateur
   |
   v
Frontend React + TypeScript
   |  HTTPS / API REST
   v
Backend Python / FastAPI
   |------------------------------|
   |                              |
   v                              v
Services métier               AI Orchestrator
   |                              |
   v                              v
PostgreSQL                 Adaptateur fournisseur IA
   |                              |
   |                              v
   |                       Modèle IA externe
   |
   v
Authentification / contrôle d'accès
```

### 3.1 Responsabilités du frontend

- Afficher les écrans et les états de l’application.
- Gérer les formulaires et la validation ergonomique.
- Appeler l’API via HTTPS.
- Afficher les réponses et propositions IA.
- Demander une confirmation avant une action d’écriture proposée par l’IA.
- Ne jamais embarquer de secret de base de données ou de fournisseur IA.

### 3.2 Responsabilités du backend

- Authentifier l’utilisateur et contrôler chaque requête.
- Appliquer les règles métier et les validations.
- Lire et écrire les données dans PostgreSQL.
- Construire le contexte utile envoyé au modèle IA.
- Exposer à l’IA uniquement des outils métier autorisés.
- Vérifier les propositions IA avant exécution.
- Journaliser les opérations importantes et gérer les erreurs.

### 3.3 Modules backend recommandés

```text
app/
  main.py
  api/
    routes/
      auth.py
      dashboard.py
      schedule.py
      tasks.py
      learning.py
      skills.py
      projects.py
      sessions.py
      ai.py
  core/
    config.py
    security.py
    database.py
  models/
  schemas/
  repositories/
  services/
  ai/
    orchestrator.py
    context_builder.py
    provider_interface.py
    providers/
    tool_registry.py
    action_validator.py
  tests/
```

Les noms sont une proposition d’organisation. Le projet doit conserver une structure compréhensible et ne pas multiplier les couches sans besoin réel.

### 3.4 Modules frontend recommandés

```text
src/
  app/
  components/
    ui/
    layout/
  features/
    auth/
    dashboard/
    schedule/
    tasks/
    learning/
    skills/
    projects/
    sessions/
    ai-coach/
    settings/
  lib/
    api-client.ts
    auth.ts
  types/
  routes/
```

## 4. Exigences fonctionnelles détaillées

### 4.1 Authentification et profil

**AUTH-01 — Connexion**  
L’utilisateur doit pouvoir se connecter et se déconnecter de manière sécurisée.

**AUTH-02 — Session**  
Les routes privées doivent être inaccessibles sans session valide.

**AUTH-03 — Profil**  
Le profil contient au minimum un nom d’affichage, un fuseau horaire, la **priorité principale active**, les préférences d’affichage et les consignes personnelles nécessaires au copilote IA.

**Critères d’acceptation :**
- Une session valide permet d’accéder aux écrans privés.
- Une session expirée renvoie vers la connexion ou déclenche un renouvellement sécurisé.
- Le backend identifie l’utilisateur à partir du jeton vérifié, jamais à partir d’un `user_id` librement fourni par le navigateur.

### 4.2 Tableau de bord

Le tableau de bord présente :

- la priorité principale active ;
- les événements planifiés pour aujourd’hui ;
- les tâches dues ou prioritaires ;
- les prochaines actions ;
- un résumé de progression récent ;
- un accès au copilote IA.

**DASH-01 :** les données sont calculées à partir des données enregistrées.  
**DASH-02 :** un état vide guide l’utilisateur lorsqu’il n’a pas encore créé de planning ou de tâches.  
**DASH-03 :** l’interface distingue clairement ce qui est planifié de ce qui est terminé.

### 4.3 Planning

Chaque élément du planning contient :

- titre ;
- type (cours, apprentissage, projet, personnel ou autre) ;
- date et heure de début ;
- date et heure de fin ;
- éventuelle récurrence simple, si elle est retenue dans le MVP ;
- notes facultatives.

Fonctions : créer, consulter, modifier et supprimer un créneau ; afficher la semaine ; naviguer entre les semaines ; dupliquer une semaine vers la suivante ; afficher les conflits horaires.

**SCHED-01 :** début et fin sont obligatoires et la fin doit être postérieure au début.  
**SCHED-02 :** les dates sont stockées de manière cohérente en base et affichées selon le fuseau horaire du profil.  
**SCHED-03 :** un conflit est signalé avant l’enregistrement, sans empêcher une décision explicite de l’utilisateur.  
**SCHED-04 :** aucune récurrence complexe (type RRULE) n’est requise pour le MVP ; une action **« Dupliquer vers la semaine suivante »** est incluse pour éviter la ressaisie hebdomadaire des cours.

### 4.4 Gestion des tâches

Champs :

- titre ;
- description facultative ;
- statut (`todo`, `in_progress`, `done`, `cancelled`, `parked` pour le parking d’idées) ;
- priorité (`low`, `normal`, `high`, `critical`) ;
- date d’échéance facultative ;
- date d’achèvement (`completed_at`) conservée lors du passage à `done` ;
- origine (`source` : `manual` ou `ai_proposal`) et `proposal_id` facultatif ;
- date de création et de mise à jour ;
- lien facultatif vers un projet, un module d’apprentissage ou une séance.

Fonctions : créer, modifier, terminer, annuler, filtrer par statut/priorité/échéance et consulter les tâches en retard.

**TASK-01 :** une tâche terminée conserve son historique de dates.  
**TASK-02 :** une tâche annulée n’est pas comptée comme terminée.  
**TASK-03 :** les filtres doivent pouvoir être combinés.  
**TASK-04 :** une tâche créée par l’IA doit afficher son origine et être validée par l’utilisateur avant persistance.

### 4.5 Parcours d’apprentissage

Un parcours regroupe des modules. Un module contient des leçons ou exercices ordonnés.

Données minimales :

- nom et description du parcours ;
- objectif ;
- statut (`not_started`, `active`, `paused`, `completed`) ;
- modules associés ;
- titre, contenu ou ressources d’une leçon ;
- statut de progression de chaque module et leçon.

Exemples de parcours de départ :
- consolidation Python ;
- JavaScript moderne et React ;
- matières du cursus universitaire.

Ces parcours sont du contenu de départ modifiable, pas des formations complètes générées automatiquement.

**LEARN-01 :** l’utilisateur peut créer ou modifier un parcours.  
**LEARN-02 :** l’utilisateur peut marquer une leçon comme commencée ou terminée.  
**LEARN-03 :** une leçon terminée ne signifie pas automatiquement que la compétence correspondante est acquise.  
**LEARN-04 :** l’utilisateur peut associer une tâche ou une séance à un module.

### 4.6 Compétences et preuves

Une compétence possède :

- nom ;
- domaine ;
- description ;
- niveau actuel estimé (échelle standard `0` à `5` : `0 = Non évalué`, `1 = Découverte`, `2 = Notions`, `3 = Autonome`, `4 = Solide`, `5 = Maîtrise`) ;
- niveau cible éventuel (`0` à `5`) ;
- date de dernière évaluation.

Une preuve possède :

- type (exercice, projet, code, évaluation, livrable ou autre) ;
- description ;
- lien ou référence facultative ;
- date ;
- compétence associée ;
- appréciation ou résultat facultatif.

**SKILL-01 :** le niveau peut être modifié par l’utilisateur ou suggéré par l’IA, mais une suggestion ne devient pas une donnée officielle sans validation.  
**SKILL-02 :** une preuve doit être consultable depuis la compétence.  
**SKILL-03 :** l’application doit éviter de présenter une compétence comme maîtrisée uniquement sur la base du temps consacré.

### 4.7 Projets

Un projet contient :

- nom ;
- description ;
- objectif mesurable ;
- statut (`planned`, `active`, `blocked`, `completed`, `archived`) ;
- priorité ;
- prochaine action ;
- date cible facultative ;
- livrables facultatifs.

**PROJ-01 :** l’utilisateur peut maintenir une liste courte de projets actifs.  
**PROJ-02 :** chaque projet actif doit afficher une prochaine action.  
**PROJ-03 :** le dashboard met en évidence la priorité principale, sans traiter tous les projets comme également urgents.

### 4.8 Journal des séances

Une séance représente une période réelle de travail ou d’apprentissage.

Champs :
- titre ;
- catégorie ;
- statut (`in_progress`, `completed`, `cancelled`) ;
- date et heure de début ;
- date et heure de fin (`ended_at`, vide tant que la séance est en cours) ;
- durée calculée ;
- tâche, module, compétence ou projet associé, facultatif ;
- résultat ou note de fin.

Fonctions : démarrer ou enregistrer une séance, la terminer, l’annuler, ajouter un résultat et consulter l’historique.

**SESSION-01 :** la durée est calculée à partir des heures, pas saisie comme preuve unique.  
**SESSION-02 :** une séance doit permettre d’enregistrer ce qui a été produit ou appris.  
**SESSION-03 :** les séances annulées (`cancelled`) ou en cours (`in_progress`, `ended_at` vide) ne sont pas incluses comme séances achevées.

### 4.9 Copilote IA

#### Fonctionnement général

Le frontend envoie un message au backend. Le backend vérifie la session, récupère les données autorisées, construit un contexte limité et appelle le fournisseur IA configuré.

Le copilote peut :
- résumer les tâches et événements de la journée ;
- proposer une priorité et un ordre de travail ;
- expliquer une notion ;
- produire un exercice adapté à un parcours ;
- commenter une réponse ou un extrait de code fourni ;
- produire un bilan à partir des données réelles ;
- créer une proposition structurée d’action.

#### Propositions d’actions

Une proposition contient :
- type d’action autorisé ;
- titre et explication ;
- paramètres validés par un schéma ;
- données concernées ;
- date de création et date d’expiration éventuelle ;
- état (`pending`, `accepted`, `rejected`, `expired`, `executed`, `failed`).

Flux obligatoire :

1. L’IA formule une proposition.
2. Le backend valide le type et les paramètres.
3. Le frontend affiche le détail à l’utilisateur.
4. L’utilisateur accepte (avec ajustement éventuel des paramètres autorisés) ou rejette.
5. En cas d’acceptation, le backend revalide les données et exécute l’action autorisée.
6. Le résultat est enregistré et présenté à l’utilisateur.

**AI-01 :** aucune mutation ne peut être exécutée à partir du texte libre d’un modèle sans validation backend.  
**AI-02 :** le modèle n’a jamais d’accès SQL direct.  
**AI-03 :** l’IA ne peut appeler que les outils explicitement enregistrés dans le `Tool Registry`.  
**AI-04 :** les clés API sont conservées côté serveur.  
**AI-05 :** le contexte transmis est limité aux informations nécessaires à la requête.  
**AI-06 :** l’interface indique lorsque la réponse est une estimation ou lorsque des données manquent.  
**AI-07 :** les propositions acceptées, rejetées et exécutées sont traçables.

#### Outils métier autorisés au MVP

| Outil | Accès | Règle |
|---|---|---|
| Lire le planning | Lecture | Données de l’utilisateur connecté uniquement |
| Lire les tâches | Lecture | Données de l’utilisateur connecté uniquement |
| Lire les parcours et compétences | Lecture | Données de l’utilisateur connecté uniquement |
| Lire les projets et séances | Lecture | Données de l’utilisateur connecté uniquement |
| Proposer une tâche | Proposition | Validation utilisateur obligatoire |
| Proposer de placer une tâche au parking | Proposition | Validation utilisateur obligatoire (Parcours C) |
| Proposer un créneau | Proposition | Vérifier les conflits et demander confirmation |
| Proposer une preuve de compétence | Proposition | Validation utilisateur obligatoire |
| Proposer un niveau de compétence | Proposition | Validation utilisateur obligatoire (`SKILL-01`) |
| Proposer un bilan | Proposition de contenu | Ne modifie aucune donnée sans accord |

Les fonctions de suppression et les actions externes sont exclues du MVP.

### 4.10 Paramètres

- Nom d’affichage.
- Fuseau horaire.
- Préférences d’affichage essentielles.
- Consignes de l’utilisateur pour le copilote : niveau d’explication, objectifs actifs et règles de travail.
- Choix du fournisseur IA réservé à la configuration serveur ou à un écran administrateur local ultérieur ; aucune clé API ne doit être saisie et stockée en clair dans le navigateur.

## 5. Exigences d’interface et navigation

### 5.1 Navigation principale

- Tableau de bord (`/`)
- Planning (`/planning`)
- Tâches (`/tasks`)
- Séances (`/sessions`)
- Apprentissage (`/learning`)
- Compétences (`/skills`)
- Projets (`/projects`, P1)
- Copilote IA (`/ai-coach`)
- Paramètres (`/settings`)

### 5.2 Règles d’ergonomie

- Navigation cohérente entre les écrans.
- Formulaires courts et validations près des champs concernés.
- Actions destructrices confirmées.
- Retour visuel après chaque sauvegarde.
- Pagination ou chargement progressif si une liste devient longue.
- Interface adaptée aux petits écrans sans sacrifier la lisibilité.
- Respect des états `loading`, `empty`, `error` et `success`.
- Éviter les graphiques qui ne déclenchent aucune décision utile.

## 6. Modèle de données initial

Le schéma ci-dessous est une base de conception. Les champs exacts et les contraintes seront affinés lors des migrations.

### 6.1 Tables

| Table | Rôle | Champs principaux |
|---|---|---|
| `profiles` | Profil utilisateur | `id`, `display_name`, `timezone`, `active_priority_title`, `active_priority_task_id`, `active_priority_project_id`, `preferences`, `ai_instructions`, `created_at`, `updated_at` |
| `schedule_events` | Créneaux du planning | `id`, `user_id`, `title`, `type`, `starts_at`, `ends_at`, `notes`, `created_at`, `updated_at` |
| `tasks` | Tâches | `id`, `user_id`, `title`, `description`, `status`, `priority`, `due_at`, `completed_at`, `source`, `proposal_id`, `project_id`, `module_id`, `created_at`, `updated_at` |
| `learning_paths` | Parcours | `id`, `user_id`, `title`, `description`, `status`, `goal`, `created_at`, `updated_at` |
| `learning_modules` | Modules | `id`, `user_id`, `path_id`, `title`, `description`, `position`, `status`, `created_at`, `updated_at` |
| `lessons` | Leçons / exercices | `id`, `user_id`, `module_id`, `title`, `content`, `resource_url`, `position`, `status`, `created_at`, `updated_at` |
| `skills` | Compétences | `id`, `user_id`, `name`, `domain`, `description`, `current_level`, `target_level`, `last_assessed_at`, `created_at`, `updated_at` |
| `skill_evidence` | Preuves de compétence | `id`, `user_id`, `skill_id`, `type`, `description`, `reference_url`, `result`, `observed_at`, `created_at`, `updated_at` |
| `projects` | Projets *(P1)* | `id`, `user_id`, `name`, `description`, `goal`, `status`, `priority`, `next_action`, `deliverables`, `target_date`, `created_at`, `updated_at` |
| `study_sessions` | Séances réelles | `id`, `user_id`, `title`, `category`, `status`, `started_at`, `ended_at`, `result`, `task_id`, `project_id`, `module_id`, `lesson_id`, `skill_id`, `created_at`, `updated_at` |
| `ai_conversations` | Conversations IA | `id`, `user_id`, `title`, `created_at`, `updated_at` |
| `ai_messages` | Messages IA | `id`, `user_id`, `conversation_id`, `role`, `content`, `metadata`, `created_at` |
| `ai_action_proposals` | Actions proposées par l’IA | `id`, `user_id`, `conversation_id`, `action_type`, `title`, `explanation`, `payload`, `status`, `expires_at`, `execution_result`, `error_message`, `created_at`, `resolved_at` |
| `ai_reports` | Briefings et bilans IA *(P1)* | `id`, `user_id`, `type`, `period_start`, `period_end`, `content`, `created_at` |

### 6.2 Relations principales

- `profiles.id` correspond à l’identifiant utilisateur fourni par le système d’authentification.
- Chaque donnée privée appartient à un `user_id`.
- `learning_paths` possède plusieurs `learning_modules`.
- `learning_modules` possède plusieurs `lessons`.
- `skills` possède plusieurs `skill_evidence`.
- Un `project` peut regrouper plusieurs `tasks` et `study_sessions`.
- Une conversation possède plusieurs messages et propositions d’action.

### 6.3 Règles de données

- Utiliser des identifiants UUID.
- Ajouter `created_at` et `updated_at` aux entités modifiables.
- Stocker toutes les dates et heures en `TIMESTAMPTZ` (UTC) et écrire des tests avec un fuseau horaire non-UTC (ex. `Europe/Paris`), car `Africa/Dakar` (UTC+0 permanent) peut masquer les erreurs de conversion.
- Inclure `user_id` sur les tables enfants pour simplifier le filtrage propriétaire côté backend et les politiques RLS PostgreSQL.
- Contraindre `current_level` et `target_level` sur l’intervalle `0..5`.
- Utiliser des contraintes SQL pour les statuts, les dates et les relations.
- Indexer les colonnes utilisées pour filtrer : `user_id`, `status`, `due_at`, `starts_at`.
- Prévoir les suppressions avec prudence ; appliquer des règles de cascade uniquement après analyse des conséquences.
- Ne pas conserver de secret fournisseur IA dans les tables métier.

## 7. API REST proposée

Préfixe : `/api/v1`

| Méthode | Route | Fonction |
|---|---|---|
| GET | `/dashboard` | Données agrégées du tableau de bord |
| GET/POST | `/schedule` | Lister / créer des créneaux |
| POST | `/schedule/duplicate-week` | Dupliquer les créneaux d’une semaine vers la semaine suivante |
| GET/PATCH/DELETE | `/schedule/{id}` | Consulter / modifier / supprimer un créneau |
| GET/POST | `/tasks` | Lister / créer des tâches |
| GET/PATCH/DELETE | `/tasks/{id}` | Consulter / modifier / supprimer une tâche |
| GET/POST | `/learning/paths` | Lister / créer des parcours |
| GET/PATCH | `/learning/paths/{id}` | Consulter / modifier un parcours |
| POST | `/learning/paths/{id}/modules` | Ajouter un module à un parcours |
| PATCH/DELETE | `/learning/modules/{id}` | Modifier / supprimer un module |
| POST | `/learning/modules/{id}/lessons` | Ajouter une leçon ou un exercice à un module |
| PATCH/DELETE | `/learning/lessons/{id}` | Modifier / supprimer une leçon |
| POST/PATCH | `/learning/lessons/{id}/progress` | Mettre à jour la progression d’une leçon |
| GET/POST | `/skills` | Lister / créer des compétences |
| GET/PATCH/DELETE | `/skills/{id}` | Consulter / modifier / supprimer une compétence |
| POST | `/skills/{id}/evidence` | Ajouter une preuve |
| DELETE | `/skills/{id}/evidence/{evidence_id}` | Supprimer une preuve |
| GET/POST | `/projects` | Lister / créer des projets *(P1)* |
| GET/PATCH/DELETE | `/projects/{id}` | Consulter / modifier / supprimer un projet *(P1)* |
| GET/POST | `/sessions` | Lister / créer une séance |
| PATCH/DELETE | `/sessions/{id}` | Modifier ou annuler une séance |
| PATCH | `/sessions/{id}/finish` | Terminer une séance |
| GET/POST | `/ai/conversations` | Lister l’historique / créer une conversation |
| GET | `/ai/conversations/{id}` | Lire une conversation |
| POST | `/ai/conversations/{id}/messages` | Envoyer un message et recevoir une réponse |
| GET | `/ai/proposals` | Lister les propositions (filtrables par statut) |
| GET | `/ai/proposals/{id}` | Lire une proposition |
| POST | `/ai/proposals/{id}/accept` | Valider et exécuter une proposition autorisée (corps optionnel pour ajuster les paramètres validés) |
| POST | `/ai/proposals/{id}/reject` | Rejeter une proposition |
| POST | `/ai/briefing` | Générer un briefing quotidien *(P1)* |
| POST | `/ai/weekly-review` | Générer un bilan hebdomadaire *(P1)* |
| GET/PATCH | `/profile` | Lire / modifier le profil, la priorité principale et les préférences |

Les routes DELETE sont fournies pour les opérations utilisateur explicites, mais elles ne doivent jamais être exposées comme outil autonome au modèle IA.

### 7.1 Format de réponse

Les réponses suivent le format JSON direct idiomatique de FastAPI (modèle Pydantic retourné directement avec le code HTTP approprié : `200`, `201`, `204`), documenté automatiquement par OpenAPI. Exemple de succès (`201 Created`) :

```json
{
  "id": "uuid",
  "title": "Réviser les dictionnaires Python",
  "status": "todo",
  "priority": "high"
}
```

En cas d’erreur (`4xx`/`5xx`), l’API retourne un format uniforme avec code HTTP adapté, code d’erreur métier, message compréhensible et identifiant de corrélation :

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "La date de fin doit être postérieure à la date de début.",
    "request_id": "req_..."
  }
}
```

Ne jamais retourner de stack trace ou de secret au navigateur.

## 8. Exigences techniques

### 8.1 Frontend

- React.
- TypeScript en mode strict.
- Vite.
- Tailwind CSS ou système de composants cohérent.
- React Router pour les routes.
- TanStack Query ou solution équivalente pour le cache et les requêtes serveur.
- Validation de formulaires avec une bibliothèque de schémas, par exemple Zod.
- Tests de composants et de parcours essentiels.

### 8.2 Backend

- Python 3, version stable supportée par les dépendances retenues au démarrage du projet.
- FastAPI.
- Pydantic pour valider les entrées et sorties.
- SQLAlchemy 2 pour l’accès aux données.
- Alembic pour les migrations.
- PostgreSQL.
- Pytest pour les tests.
- Gestion des paramètres par variables d’environnement et secrets de la plateforme d’hébergement.

### 8.3 Authentification et autorisation

- Supabase Auth ou fournisseur équivalent.
- Vérifier côté backend la signature, l’émetteur, l’audience et l’expiration du jeton.
- Déduire `user_id` du jeton vérifié.
- Appliquer le filtre propriétaire sur chaque requête métier.
- Si Supabase PostgreSQL est retenu, activer des politiques RLS comme défense supplémentaire ; elles ne remplacent pas les contrôles métier du backend.

### 8.4 Couche IA

Créer une interface fournisseur indépendante, par exemple :

- `generate_response(messages, context, tools)` ;
- normalisation de la réponse ;
- gestion des erreurs et délais d’attente ;
- journalisation des métadonnées non sensibles ;
- limites de taille de contexte et de fréquence.

Composants logiques :

1. `ContextBuilder` : sélectionne les données utiles.
2. `PromptManager` : construit les instructions et formats de réponse.
3. `AIProvider` : interface du fournisseur.
4. `ToolRegistry` : liste blanche des outils métier.
5. `ActionValidator` : valide les paramètres et permissions.
6. `AIOrchestrator` : coordonne le flux.

Ne pas introduire une architecture multi-agents dans le MVP.

## 9. Sécurité, confidentialité et fiabilité

Exigences minimales :

- HTTPS obligatoire en production.
- Secrets uniquement côté serveur.
- Validation de toutes les entrées côté backend.
- Contrôle d’autorisation sur chaque ressource.
- Protection contre les accès croisés entre utilisateurs, même si le produit commence avec un seul compte.
- Limitation de taille des messages et des requêtes IA.
- Gestion des erreurs sans exposition de données sensibles.
- Journalisation sans enregistrer les jetons ou clés secrètes.
- Sauvegardes régulières de la base et procédure de restauration vérifiée.
- Protection contre les injections de prompt : les données enregistrées ne peuvent pas remplacer les règles système ni autoriser un outil non déclaré.
- Politique de conservation des conversations à définir avant une utilisation prolongée.

## 10. Exigences non fonctionnelles

| Domaine | Exigence MVP |
|---|---|
| Responsive | Utilisable sur desktop, tablette et mobile |
| Performance | Les écrans courants doivent rester réactifs avec un volume personnel de données |
| Disponibilité | Hébergement cloud avec surveillance des erreurs de base |
| Maintenabilité | Code typé, formaté, structuré et documenté |
| Évolutivité | Possibilité de changer de fournisseur IA sans réécrire les fonctions métier |
| Accessibilité | Contrastes lisibles, navigation clavier de base, labels explicites |
| Observabilité | Logs backend utiles et suivi des erreurs frontend/backend |
| Portabilité | Migrations SQL versionnées et configuration décrite par environnement |

Les objectifs chiffrés de performance et de disponibilité seront fixés après le premier déploiement et les premières mesures.

## 11. Tests et critères de validation

### 11.1 Tests backend

- Tests unitaires des règles métier.
- Tests API des opérations CRUD.
- Tests des contrôles d’accès et de propriété des données.
- Tests des validations de dates, statuts et paramètres.
- Tests de rejet d’une proposition IA invalide.
- Tests garantissant qu’une proposition n’est pas exécutée sans acceptation.

### 11.2 Tests frontend

- Affichage des états de chargement, vide, erreur et succès.
- Création et modification d’une tâche.
- Création d’un créneau et affichage d’un conflit.
- Progression d’une leçon.
- Ajout d’une preuve de compétence.
- Acceptation et rejet d’une proposition IA.
- Parcours responsive sur une largeur mobile.

### 11.3 Scénarios d’acceptation de bout en bout

**E2E-01 — Planifier et terminer une tâche**
1. Se connecter.
2. Créer une tâche prioritaire.
3. La voir sur le dashboard.
4. La marquer terminée.
5. Vérifier qu’elle apparaît dans l’historique comme terminée.

**E2E-02 — Suivre un apprentissage**
1. Ouvrir le parcours Python.
2. Accéder à un module.
3. Terminer une leçon.
4. Enregistrer une séance.
5. Ajouter une preuve à une compétence.
6. Vérifier que la preuve apparaît dans la fiche de compétence.

**E2E-03 — Utiliser le copilote**
1. Envoyer une demande de planification.
2. Vérifier que l’IA reçoit uniquement les données autorisées.
3. Recevoir une proposition de tâche.
4. Rejeter la proposition et vérifier qu’aucune tâche n’est créée.
5. Générer une autre proposition et l’accepter.
6. Vérifier qu’une seule tâche conforme est créée.

**E2E-04 — Isolation des données**
1. Simuler un jeton invalide ou un autre utilisateur.
2. Tenter de lire une ressource appartenant au compte principal.
3. Vérifier que l’accès est refusé.

## 12. Déploiement et environnements

### Environnements

Au démarrage d’un projet personnel solo, un dispositif **Local + CI + Production** (avec aperçus frontend sur branches si l’hébergeur le propose) suffit et évite la maintenance inutile de trois environnements permanents :

- **Local :** développement frontend, backend et base de données PostgreSQL de test.
- **CI (Intégration continue) :** exécution automatique des tests, du typage et des vérifications de build à chaque changement.
- **Production :** application personnelle cloud.
- **Staging (optionnel) :** environnement intermédiaire si nécessaire avant une migration majeure.

### Variables de configuration indicatives

```env
APP_ENV=
APP_SECRET_KEY=
DATABASE_URL=
AUTH_JWKS_URL=
AUTH_ISSUER=
AI_PROVIDER=
AI_API_KEY=
AI_MODEL=
FRONTEND_ORIGIN=
VITE_API_BASE_URL=
```

Les noms exacts pourront être adaptés. Les valeurs secrètes ne doivent jamais être commitées dans Git.

### Déploiement

1. Construire et tester le frontend.
2. Déployer le backend et configurer ses secrets.
3. Exécuter les migrations de base.
4. Configurer l’authentification et les URL autorisées.
5. Tester les parcours essentiels (en local/CI puis sur l’environnement déployé).
6. Déployer en production.
7. Vérifier les logs, l’accès et la sauvegarde.

## 13. Plan de développement pédagogique

Le projet doit enseigner les concepts au moment où ils sont nécessaires. Il ne faut pas générer toute l’application d’un seul bloc sans compréhension du code. Chaque étape ci-dessous s’aligne sur les lots de la section 14 :

### Étape 1 — React et interface (Lots 1 à 3)

**À apprendre :** composants, JSX, props, state, événements, formulaires, hooks, routage et validation client.  
**À construire :** navigation FR et design system (Lot 1), Dashboard, Tâches et Séances en état local (Lot 2), Planning hebdomadaire avec détection de conflits et duplication de semaine (Lot 3).  
**Preuve :** créer et terminer une tâche, clôturer une séance et dupliquer une semaine sans backend.

### Étape 2 — Python et API (Lot 4)

**À apprendre :** modules, environnements virtuels, fonctions, Pydantic, FastAPI, routes, exceptions et tests Pytest.  
**À construire :** API REST `/api/v1` pour profil, dashboard, planning, tâches et séances avec stockage de test.  
**Preuve :** exécuter les requêtes et tests API avec documentation OpenAPI.

### Étape 3 — Base de données et connexion frontend/backend (Lot 5)

**À apprendre :** SQL, relations, clés étrangères, SQLAlchemy 2, migrations Alembic (`TIMESTAMPTZ`), `fetch`/TanStack Query, gestion d’erreurs et authentification JWT/JWKS.  
**À construire :** persistance PostgreSQL, isolation `user_id` et connexion réelle des écrans du Palier 1 à l’API.  
**Preuve :** créer, lire et modifier une tâche ou une séance depuis le navigateur ; données conservées après redémarrage et isolées par utilisateur.

### Étape 4 — Apprentissage, preuves et projets (Lot 6)

**À apprendre :** relations de données multi-niveaux, schémas, formulaires complexes et tests d’intégration.  
**À construire :** Learning, Skills (échelle 0–5 et preuves), Paramètres complets et Projets légers (P1).  
**Preuve :** une séance ou un module aboutit à une preuve consultable sur une compétence.

### Étape 5 — IA contrôlée et briefing/bilan (Lot 7)

**À apprendre :** appels API serveur, JSON structuré, validation, contexte limité, prompts, liste blanche d’outils et permissions.  
**À construire :** AI Coach, `ContextBuilder`, `ToolRegistry`, propositions d’actions validables et Briefing/Bilan (P1).  
**Preuve :** une proposition rejetée ne modifie aucune donnée ; une proposition acceptée (ou ajustée) ne déclenche que l’action autorisée.

### Étape 6 — Stabilisation et mise en production (Lot 8)

**À apprendre :** tests de bout en bout, CI, configuration d’environnement cloud et observabilité de base.  
**À construire :** suite E2E-01 à E2E-04, documentation finale et déploiement cloud.  
**Preuve :** tous les critères de fin de projet sont validés en production.

### Règle pédagogique

Pour chaque nouvelle notion : comprendre le concept, réaliser un petit exercice sans copier-coller intégralement une solution, l’intégrer au projet, puis expliquer ce qui a été construit. L’assistant de développement peut aider, mais le code doit rester compréhensible par le propriétaire du projet.

## 14. Ordre de réalisation recommandé

Le plan unifié (identique au PRD §11) est découpé en **2 paliers** pour livrer un socle quotidien utile dès la fin du Lot 5 :

### Palier 1 — Socle quotidien utilisable (Lots 1 à 5)

| Ordre | Lot | Contenu | Condition pour passer au lot suivant |
|---:|---|---|---|
| 1 | Fondations UI | Initialisation React, TypeScript strict, Vite, Tailwind, navigation FR, design system minimal, responsive | Navigation, états UI et parcours responsive validés par tests |
| 2 | Dashboard + Tâches + Séances | Données locales (`localStorage`), priorité active, parking (`parked`), filtres et journal de séances | Créer, filtrer, terminer une tâche et clôturer une séance |
| 3 | Planning | Vue semaine, créneaux, détection de conflits et duplication de semaine | Créer et dupliquer un planning sans incohérence de dates |
| 4 | Backend Python | FastAPI, schémas Pydantic et routes `/api/v1` (profil, dashboard, planning, tâches, séances) | API documentée et tests Pytest réussis |
| 5 | PostgreSQL + Auth + Connexion | SQLAlchemy 2, Alembic (`TIMESTAMPTZ`), authentification JWT/JWKS et branchement TanStack Query du front | Accès privé, persistance et isolation vérifiés de bout en bout |

### Palier 2 — Apprentissage, Projets, IA & Cloud (Lots 6 à 8)

| Ordre | Lot | Contenu | Condition pour passer au lot suivant |
|---:|---|---|---|
| 6 | Learning + Skills + Projets (P1) | Parcours, modules, leçons, compétences (0–5), preuves, paramètres avancés et projets légers | Une progression est enregistrable jusqu’à une preuve de compétence |
| 7 | Copilote IA + Briefing/Bilan (P1) | Adaptateur fournisseur, contexte contrôlé, chat, propositions acceptables/modifiables/rejetables, briefing/bilan | Flux d’approbation sécurisé et isolation des outils testés |
| 8 | Stabilisation | Tests E2E (E2E-01 à E2E-04), CI, déploiement cloud, documentation et 1 semaine d’usage réel | Critères de sortie du MVP satisfaits |

## 15. Livrables attendus

- Code source frontend.
- Code source backend.
- Migrations de base de données.
- Fichier `.env.example` sans secret.
- Documentation d’installation locale.
- Documentation des routes API (OpenAPI générée et instructions utiles).
- Tests unitaires et tests de parcours essentiels.
- Déploiement cloud fonctionnel.
- Guide utilisateur succinct.
- PRD et cahier des charges versionnés dans le dépôt Git.

## 16. Critères de fin de projet

Le MVP est accepté lorsque tous les critères suivants sont démontrés :

- connexion et déconnexion fiables ;
- planning, tâches et dashboard opérationnels ;
- parcours d’apprentissage, compétences, preuves et séances utilisables ;
- données persistées dans le cloud ;
- accès isolé et sécurisé ;
- IA utilisable en texte avec contexte contrôlé ;
- aucune action d’écriture IA sans validation explicite ;
- tests des scénarios E2E essentiels réussis ;
- documentation permettant de lancer le projet localement ;
- utilisation réelle pendant au moins une semaine avec retour sur les problèmes observés.

## 17. Décisions techniques à confirmer

1. Fournisseur d’authentification et de base PostgreSQL : Supabase ou alternative.
2. Hébergeur frontend et backend.
3. Fournisseur et modèle IA initiaux.
4. Limites d’usage et budget mensuel des appels IA.
5. Politique de conservation et de suppression des conversations.
6. Validation définitive du choix « texte d’abord, voix plus tard ».

---

**Règle d’exécution :** construire dans l’ordre des lots, prouver le fonctionnement de chaque lot et ne pas ajouter de fonctionnalité hors périmètre tant que les critères du MVP ne sont pas satisfaits.
