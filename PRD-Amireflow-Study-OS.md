# PRD — Amireflow Study OS

**Version :** 1.1  
**Date :** 19 novembre 2026  
**Statut :** Référence consolidée — prête pour le développement (Lot 1)  
**Type de produit :** Application web personnelle, cloud, responsive et assistée par IA

---

## 1. Résumé exécutif

**Amireflow Study OS** est un espace de pilotage personnel des études, de l’apprentissage et des projets. L’application aide son utilisateur à savoir quoi faire, à organiser son temps, à suivre ses apprentissages et à vérifier ses progrès à partir de résultats concrets.

L’IA est intégrée au cœur de l’expérience : elle comprend le contexte de travail, aide à planifier, explique les notions, prépare des exercices, analyse les résultats et signale les écarts entre les objectifs et le travail réellement accompli. Elle doit guider l’utilisateur sans prendre le contrôle de son organisation ni encourager la multiplication des projets.

Le produit démarre comme un outil personnel pour un seul utilisateur. Le MVP doit rester suffisamment petit pour être construit, utilisé et amélioré dans un délai maîtrisé, tout en constituant un projet pédagogique réel pour apprendre **React et Python**.

## 2. Vision produit

Créer un copilote d’apprentissage qui transforme les objectifs en actions quotidiennes, puis les actions en preuves de progression.

### Proposition de valeur

> Un seul endroit pour décider quoi apprendre, planifier le travail, passer à l’action et mesurer ce qui a réellement été acquis — avec une IA qui aide à garder le cap.

### Principes directeurs

1. **L’action avant la planification :** chaque écran doit faciliter une prochaine action claire.
2. **Une priorité principale :** l’application doit rendre visible la priorité active et limiter la dispersion.
3. **Les preuves avant les déclarations :** une compétence progresse à partir d’exercices, de livrables ou d’évaluations, pas simplement parce qu’une tâche a été cochée.
4. **Une IA utile et contrôlée :** elle explique, conseille et propose ; toute modification importante des données nécessite une validation explicite.
5. **Un MVP terminé vaut mieux qu’un système complexe :** pas de fonctionnalités secondaires sans preuve de leur utilité.
6. **Un outil pédagogique :** le développement doit permettre d’apprendre progressivement React, TypeScript, Python, les API et les bases de données.

## 3. Problème à résoudre

L’utilisateur doit gérer simultanément les cours universitaires, les apprentissages complémentaires, les exercices, les projets et les échéances. Sans système central, il existe un risque de :

- perdre la visibilité sur les priorités et les tâches importantes ;
- passer trop de temps à réfléchir ou réorganiser le travail ;
- commencer plusieurs apprentissages ou projets sans les terminer ;
- confondre temps passé, tâches terminées et compétences réellement acquises ;
- ne pas savoir quelle est la prochaine action utile.

Amireflow Study OS répond à ces problèmes par une organisation centrale, un suivi des résultats et un copilote IA contextualisé.

## 4. Utilisateur cible et contexte

### Utilisateur initial

- Un utilisateur principal : le créateur de l’application.
- Étudiant en informatique, avec des cours universitaires et des exercices pratiques.
- Apprenant de Python et de React, en parallèle de son cursus.
- Utilise des projets personnels comme terrain d’application des compétences.
- A besoin d’un système simple, exigeant et adapté à un emploi du temps qui peut évoluer.

### Extension future

Une éventuelle version multi-utilisateur n’est pas incluse dans le MVP. Le modèle de données peut conserver un identifiant utilisateur pour sécuriser les données, sans construire dès maintenant des fonctions de collaboration ou d’administration multi-comptes.

## 5. Objectifs et indicateurs de succès

Les indicateurs doivent mesurer des résultats d’apprentissage et d’exécution, pas seulement l’activité dans l’application.

| Objectif | Indicateur | Signal de réussite du MVP |
|---|---|---|
| Clarifier les priorités | Priorité principale renseignée et visible | Une priorité active affichée sur le tableau de bord |
| Passer à l’action | Taux de tâches terminées / tâches prévues | Mesure hebdomadaire consultable |
| Mieux utiliser le temps | Séances réalisées et durée réelle | Historique des séances consultable |
| Progresser en compétences | Éléments de preuve associés aux compétences | Une compétence peut être documentée par un exercice ou un livrable |
| Utiliser l’IA utilement | Propositions IA acceptées, rejetées ou ignorées | Les propositions sont traçables et évaluables |
| Assurer une utilisation durable | Jours d’utilisation avec au moins une action réelle | Bilan hebdomadaire fondé sur les données enregistrées |

**Objectif d’usage initial à tester :** utiliser l’application pendant quatre semaines consécutives et réaliser au moins trois séances d’apprentissage ou de travail suivies par semaine. Ce seuil est une hypothèse de validation, pas une garantie de résultat.

## 6. Périmètre du produit

### 6.1 Inclus dans le MVP

1. Authentification sécurisée pour l’utilisateur principal.
2. Tableau de bord quotidien avec priorité, prochaines tâches et progression.
3. Planning hebdomadaire manuel : cours, séances et activités, avec duplication rapide d’une semaine vers la suivante (utile pour les cours réguliers).
4. Gestion des tâches : créer, modifier, terminer, filtrer et prioriser, incluant un statut *parking* pour les idées non prioritaires.
5. Parcours d’apprentissage : modules, leçons, objectifs et état d’avancement.
6. Suivi des compétences avec niveau estimé et preuves concrètes.
7. Gestion légère des projets : objectif, statut, prochaine action et livrables.
8. Journal des séances de travail ou d’apprentissage.
9. Copilote IA textuel, contextualisé par les données de l’utilisateur.
10. Briefing quotidien et bilan hebdomadaire générés à la demande.
11. Suggestions d’actions IA avec approbation avant toute écriture dans les données.
12. Paramètres de base : fuseau horaire, préférences et consignes personnelles.

### 6.2 Hors périmètre du MVP

- Application mobile native iOS ou Android.
- Mode multi-utilisateur, équipes, partage ou réseau social.
- Paiement, abonnement ou marketplace.
- Synchronisation automatique Google Calendar ou Outlook.
- Publication automatique de contenu ou exécution de commandes sur l’ordinateur.
- Agents IA autonomes multiples ou architecture multi-agents.
- Import automatique de tous les cours, fichiers ou historiques personnels.
- Gamification avancée, classements, badges ou récompenses complexes.
- Voix en temps réel, wake word et assistant vocal permanent.
- Intégrations complexes avec GitHub, LMS ou autres services externes.
- Application hors ligne complète.

Ces éléments vont dans le **parking produit** et ne doivent pas retarder le MVP.

## 7. Parcours utilisateur principaux

### Parcours A — Démarrer sa journée

1. L’utilisateur ouvre le tableau de bord.
2. Il voit sa priorité principale, ses événements du jour et ses tâches importantes.
3. Il consulte le briefing IA.
4. L’IA recommande une action réaliste en fonction du temps disponible.
5. L’utilisateur accepte, modifie ou ignore la proposition.
6. Il réalise une séance et enregistre le résultat.

**Résultat attendu :** l’utilisateur sait quelle action commencer sans devoir replanifier toute sa semaine.

### Parcours B — Apprendre une notion

1. L’utilisateur ouvre un parcours (ex. Python ou React).
2. Il sélectionne le module et l’objectif de la séance.
3. L’IA explique la notion au niveau demandé.
4. L’utilisateur réalise un exercice sans recevoir immédiatement la solution complète.
5. Il soumet sa réponse ou décrit son résultat.
6. L’IA donne un retour et propose une preuve de progression à enregistrer.

**Résultat attendu :** une notion est travaillée par la pratique et la progression repose sur une preuve.

### Parcours C — Protéger la priorité

1. L’utilisateur ajoute une nouvelle idée ou une nouvelle tâche.
2. L’IA vérifie son urgence, son importance et son coût d’opportunité.
3. Si elle n’est pas prioritaire, elle recommande de la placer dans le parking.
4. L’utilisateur garde ou modifie la priorité principale.

**Résultat attendu :** les nouvelles idées ne remplacent pas automatiquement le travail déjà engagé.

### Parcours D — Faire le bilan

1. L’utilisateur ouvre le bilan de la semaine.
2. Il consulte les tâches prévues et réalisées, les séances et les preuves ajoutées.
3. L’IA distingue les activités des résultats.
4. Elle identifie un blocage principal et recommande au maximum trois actions critiques pour la semaine suivante.

**Résultat attendu :** une décision d’amélioration concrète, fondée sur les données réelles.

## 8. Fonctionnalités et priorités

| ID | Fonctionnalité | Priorité | Définition de terminé |
|---|---|---:|---|
| F-01 | Authentification | P0 | L’utilisateur peut se connecter et ses données restent privées |
| F-02 | Tableau de bord | P0 | Priorité, tâches du jour, événements et progression sont visibles |
| F-03 | Planning hebdomadaire | P0 | L’utilisateur peut créer, modifier, consulter ses créneaux et dupliquer une semaine |
| F-04 | Gestion des tâches | P0 | CRUD, priorité, échéance et statuts (y compris `parked`) fonctionnent |
| F-05 | Parcours d’apprentissage | P0 | Les modules et leçons sont consultables et leur état peut évoluer |
| F-06 | Compétences et preuves | P0 | Une preuve peut être associée à une compétence |
| F-07 | Projets personnels | P1 | Un projet affiche son objectif, son statut et sa prochaine action (Lot 6, après validation P0) |
| F-08 | Journal de séances | P0 | Une séance peut être créée, clôturée et consultée |
| F-09 | Copilote IA textuel | P0 | L’IA répond en utilisant un contexte autorisé et explicite |
| F-10 | Propositions d’actions IA | P0 | Une proposition peut être acceptée, ajustée ou rejetée avant exécution |
| F-11 | Briefing et bilan IA | P1 | L’IA produit un résumé fondé sur les données disponibles (Lot 7, après validation P0) |
| F-12 | Paramètres | P0 (minimal) / P1 | Profil, fuseau horaire, priorité principale et consignes IA de base en P0 ; préférences avancées en P1 |

P0 = indispensable au premier MVP utilisable. P1 = à inclure aux Lots 6–7 seulement si les fonctionnalités P0 correspondantes sont stables et validées.

## 9. Expérience et interface

### Direction visuelle

- Design premium, sobre, moderne et orienté productivité.
- Interface responsive, conçue d’abord pour ordinateur mais utilisable sur mobile.
- Hiérarchie visuelle nette : priorité principale, prochaine action, puis informations secondaires.
- Navigation persistante simple.
- Éviter les tableaux de bord surchargés, les graphiques décoratifs et les animations inutiles.
- États de chargement, erreurs, absence de données et confirmations clairement visibles.

### Écrans du MVP

1. **Connexion** (`/login`) — authentification.
2. **Tableau de bord** (`/`) — priorité principale active, vue du jour, tâches prioritaires, progression et accès au copilote.
3. **Planning** (`/planning`) — vue hebdomadaire, gestion des créneaux, conflits et duplication de semaine.
4. **Tâches** (`/tasks`) — liste, filtres combinés, parking d’idées et formulaire de tâche.
5. **Séances** (`/sessions`) — démarrage, clôture, résultat et historique des séances de travail.
6. **Apprentissage** (`/learning`) — parcours, modules, leçons et exercices.
7. **Compétences** (`/skills`) — compétences (échelle 0–5), niveau estimé, preuves et historique.
8. **Projets** (`/projects`, P1) — liste de projets, statut, prochaine action et livrables.
9. **Copilote IA** (`/ai-coach`) — conversations, contexte utilisé et propositions d’actions validables.
10. **Paramètres** (`/settings`) — profil, priorité principale, fuseau horaire et consignes IA.

## 10. Rôle de l’IA

L’IA est un copilote transversal, pas un chatbot isolé.

### Capacités prévues au MVP

- Lire les tâches, le planning, les parcours, les compétences et les projets autorisés.
- Résumer la situation du jour ou de la semaine.
- Aider à définir une priorité réaliste.
- Décomposer un objectif en tâches limitées.
- Expliquer une notion à un niveau débutant ou intermédiaire.
- Générer un exercice, donner des indices et corriger une réponse fournie.
- Distinguer activité, livrable et résultat.
- Détecter des signes de dispersion à partir des données disponibles.
- Proposer une action structurée pouvant être acceptée, modifiée ou rejetée.

### Limites et règles de sécurité

- L’IA ne doit pas inventer des séances, tâches terminées ou compétences acquises.
- Elle doit signaler quand les données sont insuffisantes.
- Elle ne doit jamais supprimer de données ni modifier une priorité de manière silencieuse.
- Toute action d’écriture passe par une proposition structurée et une confirmation explicite.
- Les outils disponibles à l’IA sont limités à des opérations métier contrôlées par le backend.
- Aucun accès SQL direct, aucune exécution de code arbitraire et aucun accès général au système de fichiers.
- Le contenu utilisateur est traité comme une donnée, pas comme une instruction système.

### Décisions IA encore à confirmer

| Décision | Valeur de référence pour le MVP | Statut |
|---|---|---|
| Fournisseur du modèle | Architecture interchangeable via un adaptateur ; fournisseur non figé | À confirmer |
| Interaction | Texte pour le MVP ; voix éventuellement dans une version ultérieure | À confirmer |
| Autonomie | L’IA propose ; l’utilisateur approuve avant toute modification | Valeur prudente proposée |

Le MVP ne doit pas attendre ces choix pour concevoir une interface de fournisseur interchangeable et une couche d’orchestration indépendante du modèle.

## 11. Stratégie de réalisation

Le développement est organisé en **8 lots regroupés en 2 paliers** afin de livrer rapidement un socle utilisable au quotidien avant d’ajouter les modules complémentaires et l’IA.

### Palier 1 — Socle quotidien utilisable (Lots 1 à 5)

| Lot | Contenu | Preuve de validation |
|---:|---|---|
| 1. Fondations UI | Initialisation React, TypeScript strict, Vite, Tailwind, navigation FR, design system minimal, responsive | Navigation, états UI et parcours responsive validés par tests |
| 2. Tableau de bord + Tâches + Séances | État local (`localStorage`), priorité active, parking (`parked`), filtres et journal de séances | Créer, filtrer, terminer une tâche et clôturer une séance sans backend |
| 3. Planning hebdomadaire | Vue semaine, créneaux, détection de conflits et duplication de semaine | Planifier une semaine et dupliquer les créneaux sans incohérence de dates |
| 4. Backend Python / FastAPI | API REST `/api/v1` (profil, tableau de bord, planning, tâches, séances) et tests Pytest | Opérations CRUD et validations testées via API et OpenAPI |
| 5. PostgreSQL, Auth & Connexion | SQLAlchemy 2, Alembic (`TIMESTAMPTZ`), JWT/JWKS, isolation `user_id`, TanStack Query | Accès privé, persistance cloud et isolation des données vérifiés de bout en bout |

### Palier 2 — Apprentissage, Projets, IA & Cloud (Lots 6 à 8)

| Lot | Contenu | Preuve de validation |
|---:|---|---|
| 6. Apprentissage, Compétences & Projets (P1) | Parcours/modules/leçons, compétences (0–5) et preuves, projets légers, paramètres avancés | Un parcours peut être suivi jusqu’à une preuve de compétence persistée |
| 7. Copilote IA & Briefing/Bilan (P1) | Adaptateur fournisseur, contexte contrôlé, outils en liste blanche, propositions acceptables/modifiables/rejetables, briefing/bilan | Une réponse s’appuie sur les données autorisées et aucune mutation n’a lieu sans validation |
| 8. Stabilisation & Déploiement | Tests E2E (E2E-01 à E2E-04), CI, déploiement cloud, documentation et usage réel | Critères de sortie satisfaits en environnement cloud après au moins 1 semaine d’usage |

### Règle de progression

Ne pas commencer le lot suivant simplement parce que le code du lot précédent existe. Un lot est terminé uniquement lorsque sa preuve de validation est obtenue.

## 12. Risques produit

| Risque | Conséquence | Réponse prévue |
|---|---|---|
| Périmètre trop large | MVP jamais terminé | Maintenir les fonctionnalités hors périmètre dans le parking |
| Trop de temps sur le design | Retard sans validation d’usage | Valider une interface simple avant le polissage |
| IA trop autonome | Actions erronées ou perte de confiance | Propositions et confirmation obligatoire |
| Données saisies non mises à jour | Recommandations IA peu pertinentes | Rappels sobres et saisie rapide |
| Mesure de progression superficielle | Fausse impression d’apprentissage | Associer les compétences à des preuves |
| Projet utilisé pour éviter les apprentissages | L’application devient une fin en soi | Limiter le temps de développement et l’utiliser chaque semaine |

## 13. Critères de sortie du MVP

Le MVP est considéré comme utilisable lorsque :

- l’utilisateur peut se connecter depuis un navigateur ;
- ses données sont persistées dans le cloud et protégées ;
- il peut organiser une semaine et gérer ses tâches ;
- il peut suivre un parcours d’apprentissage et documenter une compétence ;
- il peut enregistrer une séance et consulter son historique ;
- l’IA peut consulter uniquement le contexte autorisé ;
- l’IA peut proposer une action, mais aucune écriture n’est réalisée sans confirmation ;
- les parcours essentiels sont testés ;
- l’application a été utilisée pendant au moins une semaine réelle et les problèmes bloquants ont été corrigés.

## 14. Décisions ouvertes

### Décisions actées en v1.1

- Interface et libellés de navigation intégralement en français, incluant l’écran **Séances** (`F-08`, P0).
- Action « Dupliquer vers la semaine suivante » sur le planning pour éviter la ressaisie hebdomadaire des cours sans recourir à des règles de récurrence complexes.
- Statut `parked` sur les tâches pour isoler les idées non prioritaires (Parcours C).
- Format d’API FastAPI idiomatique (réponses JSON directes + format d’erreur uniforme sur 4xx/5xx).

### Décisions à confirmer avant les Lots 5 et 7

1. Choisir le fournisseur Auth + PostgreSQL managée (Supabase ou alternative) et l’hébergement du frontend et du backend (avant Lot 5).
2. Choisir le fournisseur IA initial et définir le budget/plafond mensuel, sans supprimer la possibilité d’en changer (avant Lot 7).
3. Définir la politique de conservation et de suppression des conversations IA (avant Lot 7).
4. Confirmer le maintien du report de la voix après le MVP (validation définitive de « texte d’abord »).

---

**Règle de gouvernance :** toute nouvelle fonctionnalité doit démontrer qu’elle améliore directement l’organisation, l’apprentissage ou la validation des résultats. Sinon, elle reste dans le parking.
