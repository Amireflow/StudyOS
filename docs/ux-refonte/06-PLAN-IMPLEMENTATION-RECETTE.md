# 06 — Plan d'implémentation et de recette UX/UI

> Statut : plan approuvé pour exécution progressive ; chaque lot conserve sa validation indépendante.
> Règle : avancer par lots verticaux vérifiables. Aucun lot ne remplace les règles métier ou les données existantes.

## 1. Objectif

Transformer progressivement la conception UX en interface cohérente, responsive et accessible, sans régression fonctionnelle. La priorité est l'expérience quotidienne : tableau de bord, navigation, apprentissage, organisation, puis Copilote et paramètres.

## 2. Garde-fous non négociables

- Travailler sur `ux/audit-initial-2026-11-21`, jamais directement sur `main`.
- Ne pas modifier les API, schémas DB, permissions, RLS, règles de validation de compétences ou workflow de propositions IA dans un lot purement visuel.
- Préserver routes, URLs profondes, historique navigateur, données et comportements actuels.
- Ne supprimer aucun contrôle métier au motif de simplifier l'écran.
- Réutiliser les composants partagés ; éviter une refonte big-bang.
- Chaque lot doit passer typecheck, tests ciblés et build avant le lot suivant.
- Capturer les parcours desktop et mobile avant/après.
- Toute différence fonctionnelle inattendue bloque le lot.

## 3. Ordre d'exécution

### Lot 0 — Référence visuelle et inventaire technique

Livrables :
- captures desktop 1440 px et mobile 390 px des parcours principaux ;
- inventaire des tokens CSS/Tailwind et composants partagés ;
- vérification de la police réellement chargée ;
- liste des variantes et usages actuels de Button, Card, FormFields, Badge, PageHeader et StateFeedback.

Validation :
- références visuelles enregistrées ;
- inventaire lié aux composants réels ;
- aucun code produit modifié.

### Lot 1 — Fondations du Design System

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

- tests responsive aux largeurs 320, 360, 390, 768, 1024, 1280 et 1440 px ;
- tests clavier, focus, lecteurs d'écran et zoom ;
- vérification contrastes WCAG 2.2 AA ;
- parcours E2E critiques ;
- comparaison des captures avant/après ;
- vérification de l'absence de scroll horizontal global ;
- vérification des états vides, chargement, erreurs et données partielles.

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

Le Design System a été validé par l'utilisateur. Le Lot 0 a produit l'inventaire source et quatre références mobiles ; la couverture visuelle restante a été acceptée comme limitation pour avancer.

Le Lot 1 porte sur les fondations et composants partagés. Il ne doit être déclaré terminé qu'après réussite des contrôles techniques et inspection visuelle du rendu sur une prévisualisation de la branche. Le Lot 2 ne commence qu'après cette validation.

