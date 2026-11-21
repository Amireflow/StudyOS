# 06 — Plan d'implémentation et de recette UX/UI

> Statut : plan approuvé pour exécution progressive ; chaque lot conserve sa validation indépendante.
> Règle : avancer par lots verticaux vérifiables. Aucun lot ne remplace les règles métier ou les données existantes.

## 1. Objectif

Transformer progressivement la conception UX en interface cohérente, responsive et accessible, sans régression fonctionnelle. La priorité est l'expérience quotidienne : tableau de bord, navigation, apprentissage, organisation, puis Copilote et paramètres.

## 2. Garde-fous non négociables

- À la demande explicite de l'utilisateur, la refonte a été intégrée dans `main` via la Pull Request #3 ; les lots de continuation sont également commités sur `main`.
- Ne pas modifier les API, schémas DB, permissions, RLS, règles de validation de compétences ou workflow de propositions IA dans un lot purement visuel.
- Préserver routes, URLs profondes, historique navigateur, données et comportements actuels.
- Ne supprimer aucun contrôle métier au motif de simplifier l'écran.
- Réutiliser les composants partagés ; éviter une refonte big-bang.
- Chaque lot doit passer typecheck, tests ciblés et build avant le lot suivant.
- Capturer les parcours desktop et mobile avant/après.
- Toute différence fonctionnelle inattendue bloque le lot.

## 3. Ordre d'exécution

### Lot 0 — Référence visuelle et inventaire technique

<badge>Statut documentaire : partiel accepté pour poursuivre</badge>

Livrables réalisés :
- inventaire des tokens, composants partagés, navigation, routes et scripts de qualité ;
- inspection de quatre captures mobiles : tableau de bord, planning, accueil Copilote et tiroir.

Limites acceptées par l'utilisateur pour ne pas bloquer l'exécution :
- absence de captures desktop, index des cours, lecteur pédagogique, paramètres et thème clair ;
- police réellement rendue et contrôles navigateur non mesurés ;
- aucun test manuel VoiceOver/NVDA ni relevé de contraste calculé depuis le DOM.

La limitation et les observations sont conservées dans `07-LOT-0-ETAT-REFERENCE.md`. Le Lot 0 reste partiel au sens strict ; aucune vérification manquante n'est déclarée réussie.

### Lot 1 — Fondations du Design System

<badge color="success">Implémentation et CI réussies</badge>

Périmètre :
- tokens CSS sémantiques clair/sombre ;
- typographie, espacements, rayons, focus ;
- boutons, champs, cartes, badges et feedback ;
- tailles tactiles et états disabled/loading.

Risques :
- changement global de hauteur/espacement qui casse les formulaires ;
- contraste insuffisant en thème sombre ;
- surcharge de classes Tailwind concurrentes.

Tests :
- tests unitaires des variantes et états ;
- captures visuelles de composants ;
- contrastes automatisés et vérification manuelle.

Critère de sortie :
- composants cohérents sur les pages principales ;
- aucune régression de formulaire ou de navigation ;
- typecheck, tests et build verts.

### Lot 2 — Shell, navigation et Dashboard

<badge color="success">Implémenté sur main</badge>

Périmètre :
- groupes Apprentissage et Organisation ;
- navigation desktop/mobile et état actif ;
- header de page harmonisé ;
- priorité et prochaine action avant les statistiques ;
- adaptation responsive.

Critère de sortie :
- accès à toutes les routes historiques ;
- navigation clavier et tactile ;
- aucune perte de contexte au changement de section.

### Lot 3 — Apprentissage

<badge color="success">Implémenté sur main</badge>

Périmètre :
- index des cours et parcours ;
- détails de cours ;
- lecteur de leçon immersif ;
- exercices, projets, ressources et tutorat ;
- progression et états de verrouillage.

Critère de sortie :
- un utilisateur peut reprendre exactement là où il s'était arrêté ;
- les prérequis et validations serveur restent actifs ;
- lecture confortable à 320 px, 390 px et desktop ;
- aucune validation de niveau sans preuve conforme.

### Lot 4 — Organisation

<badge color="success">Implémenté sur main</badge>

Périmètre :
- planning hebdomadaire et liste mobile ;
- studio de programme intelligent en étapes ;
- tâches et séances ;
- conflits, import de calendrier et confirmation.

Critère de sortie :
- cours universitaires visuellement distincts et protégés ;
- conflits clairement expliqués ;
- aucune programmation sans consentement explicite ;
- vues utilisables sur petit écran.

### Lot 5 — Projets, Copilote et Paramètres

<badge color="success">Implémenté sur main</badge>

Périmètre :
- projets et objectifs ;
- interface conversationnelle du Copilote ;
- propositions et historique secondaires ;
- paramètres regroupés par intention.

Critère de sortie :
- toutes les actions proposées par l'IA restent contrôlées ;
- l'utilisateur comprend le contexte, l'impact et les options avant acceptation ;
- configuration existante conservée.

### Lot 6 — Recette transversale et stabilisation

<badge color="warning">Partiellement terminé — inspection navigateur restante</badge>

Déjà vérifié automatiquement :
- TypeScript strict ;
- suite Vitest avec tests de navigation, lecteur, planning, projets, Copilote, paramètres et parcours d'acceptation ;
- build production ;
- migrations Alembic et tests backend ;
- état accessible des contrôles (aria-pressed, groupes nommés), tests du tiroir mobile avec focus trap/Échap/restauration.

Encore à réaliser avant de déclarer la refonte entièrement terminée :
- inspection visuelle réelle sur mobile et desktop (320, 360, 390, 768, 1024, 1280, 1440 px) ;
- test tactile au vrai appareil, contraste calculé depuis le DOM et parcours manuel VoiceOver/NVDA ;
- capture avant/après et confirmation de l'absence de scroll horizontal global ;
- inspection du rendu déployé sur l'environnement de prévisualisation ou production.

Les tests jsdom/Vitest sont une preuve de comportement DOM simulé ; ils ne remplacent pas les vérifications navigateur et lecteur d'écran.

## 4. Matrice de recette minimale

| Parcours | Résultat attendu | Preuve |
|---|---|---|
| Connexion | accès sécurisé, erreurs compréhensibles | test E2E + capture |
| Dashboard | priorité et prochaine action immédiatement visibles | capture desktop/mobile |
| Reprise d'un cours | retour au bon module/à la bonne leçon | test E2E |
| Exercice | consigne, réponse et correction utilisables | test E2E |
| Validation compétence | preuve et critères requis, verrou serveur intact | test backend + UI |
| Création tâche | création, édition et statut conservés | test E2E |
| Planning | conflit détecté avant confirmation | test E2E |
| Import emploi du temps | aperçu modifiable avant intégration | test E2E |
| Proposition IA | aucune mutation avant acceptation | test E2E |
| Paramètres | préférences conservées après rechargement | test E2E |

## 5. Définition de « terminé »

Un lot n'est terminé que si :
1. le périmètre annoncé est implémenté ;
2. les critères d'acceptation passent ;
3. typecheck, tests et build passent ;
4. les parcours desktop et mobile ont été inspectés ;
5. aucune régression métier n'est identifiée ;
6. les changements sont commités sur la branche dédiée ;
7. le bilan mentionne les fichiers modifiés, preuves et limites restantes.

## 6. Mesures de succès UX

Mesurer avant/après sur les parcours identiques :
- temps et nombre d'actions pour reprendre un cours ;
- temps pour créer une tâche et planifier une séance ;
- taux d'abandon des formulaires ;
- erreurs de navigation et retours arrière ;
- taux de réussite des parcours clavier ;
- nombre de défauts responsive et d'accessibilité bloquants.

Ne pas présenter une amélioration comme acquise sans mesures comparables. Les métriques doivent être collectées sans introduire de suivi intrusif ou de données personnelles non nécessaires.

## 7. État d'avancement et prochaine validation

- Le Design System a été approuvé et ses fondations sont implémentées dans `main`.
- Les Lots 2 à 5 sont implémentés sur `main` : navigation, dashboard, expérience de cours/lecture, organisation, projets, Copilote et Paramètres.
- Le Lot 0 reste partiel avec acceptation explicite de la couverture visuelle manquante.
- Les vérifications CI du commit `f6732d6f7f2d4732f8a9b4bee00428922efee854` sont vertes : frontend (21 fichiers / 87 tests, typecheck et build) ; backend (133 tests et migrations réversibles).
- Une optimisation supplémentaire du chargement par route est en cours au commit `506e9a6d34607b8c7f28a4d6175ca40567382cac` ; sa CI doit confirmer le gain et l'absence de régression.

Le dernier verrou du Lot 6 est l'acceptation visuelle réelle. Aucune capture après modification ni mesure navigateur n'est revendiquée à ce stade.

