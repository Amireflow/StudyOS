# 09 — Lots 2 à 6 : implémentation, validation CI et recette restante

> Date : 21 novembre 2026  
> Branche cible : `main`  
> PR initiale : [#3 — Refonte UX/UI StudyOS](https://github.com/Amireflow/StudyOS/pull/3), fusionnée  
> Commit applicatif soumis à la CI finale des Lots 2 à 5 et du code-splitting : `f78e20d9f5c44d8ab3f521908b1968f4e44fd942`  
> Commit de mise en place du chargement par route : `506e9a6d34607b8c7f28a4d6175ca40567382cac`  
> Commit applicatif final testé : `f78e20d9f5c44d8ab3f521908b1968f4e44fd942`  
> Run CI : [44893071433](https://github.com/Amireflow/StudyOS/actions/runs/44893071433)  
> Statut : Lots 2 à 5 implémentés ; CI frontend/backend verte ; optimisation du bundle validée ; recette navigateur manuelle restante.

## 1. Résumé d'exécution

Après intégration de la conception et des fondations du Design System dans `main`, les lots d'interface ont été réalisés directement sur cette branche, comme demandé par l'utilisateur.

Aucun changement de schéma DB, API, RLS, règles d'évaluation des compétences, contraintes de projets/tâches ou workflow métier de propositions du Copilote n'a été introduit dans cette refonte UX/UI.

## 2. Lot 2 — Shell, navigation et Dashboard

### Changements
- Navigation desktop organisée autour des domaines Apprentissage et Organisation, avec sections Projets et Assistance.
- Barre mobile maintenue à cinq accès : Accueil, Apprendre, Organiser, Projets, IA.
- Sous-navigation de domaine affichée sur les écrans Cours/Parcours/Compétences et Planning/Tâches/Séances ; les URLs existantes sont conservées.
- États actifs de la navigation mobile alignés sur le domaine, y compris Tâches/Séances et Parcours/Compétences.
- Tiroir mobile doté d'un rôle dialog, aria-modal, verrouillage du scroll arrière-plan, focus trap Tab/Shift+Tab, fermeture Échap et restitution du focus au déclencheur.
- Dashboard : la priorité principale et son état vide passent avant le ruban de statistiques ; le bloc vide affiche une consigne et une action directe.

### Fichiers principaux
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/navigation.ts`
- `frontend/src/components/layout/WorkspaceSectionNavigation.tsx`
- `frontend/src/features/dashboard/DashboardPage.tsx`
- `frontend/src/features/dashboard/PriorityHero.tsx`
- `frontend/src/app/AppNavigation.test.tsx`

## 3. Lot 3 — Apprentissage

### Changements
- Lecteur de leçon recentré sur une largeur de lecture maîtrisée, typographie 15 px et interligne 28 px pour le contenu principal, titres et espacements renforcés.
- Blocs Markdown, listes et contrôles de code harmonisés avec une meilleure lisibilité.
- Correction du reset d'état lors du passage d'une leçon à une autre : l'étape affichée repart de la position enregistrée pour la nouvelle leçon et le mode « afficher tout » est réinitialisé.
- Sélecteur de niveau et onglets du niveau plus faciles à toucher et avec focus visible.
- Intitulé « Parcours » harmonisé avec la navigation.

### Fichiers principaux
- `frontend/src/features/courses/CourseLessonReader.tsx`
- `frontend/src/features/courses/CourseLessonReader.test.ts`
- `frontend/src/components/ui/MarkdownContent.tsx`
- `frontend/src/features/courses/CourseDetailView.tsx`
- `frontend/src/features/courses/CoursesPage.tsx`
- `frontend/src/features/learning/LearningPage.tsx`
- `frontend/src/features/skills/SkillsPage.tsx`

Les règles de prérequis, preuves, progression et déverrouillage côté serveur restent inchangées.

## 4. Lot 4 — Organisation

### Changements
- Bandeau des sept jours du planning rendu défilable horizontalement sur les petits écrans ; cibles d'au moins 44 px conservées.
- Chaque jour possède un nom accessible et un état `aria-pressed`.
- Filtres de type et contrôles de vue du planning exposés comme groupes nommés avec état sélectionné.
- Semaine précédente/suivante et filtres tactiles élargis.
- Filtres des tâches et séances harmonisés avec la même hauteur minimale et les mêmes focus rings.
- Filtres des séances et projets exposent leurs états sélectionnés ; groupes de filtres nommés.

### Fichiers principaux
- `frontend/src/features/schedule/PlanningPage.tsx`
- `frontend/src/features/schedule/PlanningPage.test.tsx`
- `frontend/src/features/tasks/TasksPage.tsx`
- `frontend/src/features/sessions/SessionsPage.tsx`
- `frontend/src/features/sessions/SessionsPage.test.tsx`
- `frontend/src/features/projects/ProjectsPage.tsx`
- `frontend/src/features/projects/ProjectsPage.test.tsx`

La détection de conflits, l'import EDT, la confirmation avant application et la protection des cours universitaires n'ont pas été modifiés.

## 5. Lot 5 — Projets, Copilote et Paramètres

### Changements
- Filtres de projets exposés comme groupe de boutons à état pressé, avec cibles tactiles et focus visible.
- Copilote : suggestions de l'état vide plus compactes ; vues mobiles Discussion/Actions/Synthèses avec états `aria-pressed` exclusifs ; bouton d'envoi 44 × 44 px.
- Paramètres : navigation interne par intention vers Profil, Fournisseur IA, Sécurité (si session API), Apparence, Espace de travail et Connexions ; ancres stables et cibles de défilement.
- Presets de fuseaux horaires et de style IA exposent leur état sélectionné.
- En-têtes Cours, Détails du cours et Compétences alignés sur le style de titre partagé.

### Fichiers principaux
- `frontend/src/features/projects/ProjectsPage.tsx`
- `frontend/src/features/ai-coach/AiCoachPage.tsx`
- `frontend/src/features/ai-coach/AiCoachPage.test.tsx`
- `frontend/src/features/settings/SettingsPage.tsx`
- `frontend/src/features/settings/SettingsPage.test.tsx`
- `frontend/src/features/courses/CoursesPage.tsx`
- `frontend/src/features/courses/CourseDetailView.tsx`
- `frontend/src/features/skills/SkillsPage.tsx`

Les propositions IA restent sans mutation immédiate ; toute action conserve son parcours de confirmation déjà existant.

## 6. Lot 6 — Tests et validation automatique

### Résultats CI du commit f6732d6f

Run GitHub Actions : [44893071433](https://github.com/Amireflow/StudyOS/actions/runs/44893071433)

| Contrôle | Résultat |
|---|---|
| Installation frontend | réussite |
| TypeScript strict | réussite |
| Vitest frontend | 21 fichiers, 87 tests réussis |
| Build production Vite | réussite |
| Migrations Alembic et réversibilité | réussite |
| Pytest backend | 133 tests réussis, 5 avertissements |

Ces tests couvrent notamment les routes et la navigation, le focus trap du tiroir mobile, la lecture progressive, les états de sélection du Copilote, les filtres du planning/projets/séances, les liens d'ancrage des paramètres et les parcours métier d'acceptation.

### Optimisation du chargement — résultat mesuré

Le routeur charge les pages métier à la demande via `React.lazy` et `Suspense`, tout en gardant Connexion, Dashboard et 404 dans le chargement initial. Les contrôles finaux sur le commit `f78e20d9f5c44d8ab3f521908b1968f4e44fd942` confirment :

| Bundle JavaScript | Avant | Après |
|---|---:|---:|
| Entrée principale | 1 000,40 kB | 353,06 kB |
| Entrée gzip | 261,33 kB | 102,34 kB |

Le chargement initial JavaScript baisse donc d'environ 64,7 % en taille brute. Les pages métier sont séparées en chunks entre 26 et 68 kB chacun pour les routes principales. Le build ne signale plus de chunk dépassant le seuil de 700 kB.

## 7. Limites restantes — recette visuelle manuelle

Les contrôles suivants ne sont pas attestés par la CI jsdom et restent à effectuer dans un vrai navigateur/appareil :
- captures après modification (mobile et desktop) ;
- largeurs 320, 360, 390, 768, 1024, 1280 et 1440 px ;
- thèmes clair et sombre ;
- navigation tactile réelle, clavier, VoiceOver iOS et NVDA ;
- vérification des couleurs calculées et contrastes réels par écran ;
- absence de scroll horizontal global et de contenu caché sous les barres fixes.

La prévisualisation ou le site déployé n'a pas pu être ouvert par l'outil navigateur disponible dans cette session. Aucune capture après refonte ni mesure de rendu réel n'est donc revendiquée.

## 8. Conclusion

**Implémentation des lots 2 à 5 et CI du commit f78e20d : validées.**  
**Optimisation du code-splitting : validée, bundle d'entrée réduit à 353,06 kB.**  
**Lot 6 : validation automatique réussie ; inspection navigateur manuelle encore ouverte.**

Aucun changement n'a été fusionné en dehors de `main` après la PR #3 ; le code final reste à valider visuellement avant de déclarer la refonte totalement terminée.
