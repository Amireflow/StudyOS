# Audit UX/UI initial — Amireflow Study OS

- **Date :** 21 novembre 2026
- **Dépôt :** `Amireflow/StudyOS`
- **Branche source :** `main`
- **Commit source audité :** `c77e293228afe20986a1674e208e85d57a95c500`
- **Branche de travail :** `ux/audit-initial-2026-11-21`
- **Statut :** étape 0 — audit du code source terminé ; aucune modification de l'interface de production dans cette étape.

## 1. Résumé exécutif

StudyOS possède déjà une base fonctionnelle sérieuse : navigation responsive, composants UI partagés, parcours de cours avec verrou pédagogique, exercices, tuteur IA, planning, tâches, séances, copilote et tests automatisés.

Le principal chantier UX n'est donc pas de reconstruire l'application. Il consiste à rendre plus cohérente et plus lisible une expérience qui a grandi par fonctionnalités.

Les problèmes les plus structurants sont :

1. Les espaces Cours, Apprentissage et Compétences sont présentés comme des destinations séparées alors qu'ils participent à un même parcours pédagogique.
2. Le tableau de bord présente quatre indicateurs avant la priorité principale : la hiérarchie actuelle ne met pas immédiatement l'action au premier plan.
3. Plusieurs composants partagés utilisent des tailles compactes : bouton sm à 32 px de hauteur, bouton md à 40 px, labels de champs souvent en 12 px et badges en 11 px.
4. Les pages Planning et Copilote exposent de nombreuses capacités en même temps. Il faut utiliser la divulgation progressive plutôt que supprimer leurs fonctionnalités.
5. Les textes et les actions ne suivent pas encore une règle éditoriale et une hiérarchie de boutons suffisamment centralisées.
6. Les tests frontend sont exécutés dans jsdom. Ils valident des interactions React mais ne remplacent pas des tests visuels dans de vrais navigateurs et à plusieurs largeurs d'écran.

**Décision :** commencer par la conception de l'architecture UX et des wireframes. Ne pas lancer une réécriture visuelle globale avant cette validation.

## 2. Périmètre et méthode

### Éléments inspectés

- Arborescence GitHub et commit courant.
- Routes et navigation.
- Shell desktop/mobile.
- Composants UI partagés : Button, FormFields, Card, Badge, StateFeedback, PageHeader.
- CSS global, HTML d'entrée et configuration frontend.
- Pages Dashboard, Tasks, Planning, Sessions, Courses, Learning, Skills, Projects, AI Coach et Settings.
- Détail de cours, lecture de leçon, exercices, projet de niveau, ressources, tuteur de chapitre.
- Tests frontend et configuration CI.

### Limites de l'audit

- L'URL Render `https://amireflow-study-os.onrender.com` n'a pas été accessible à l'outil de navigation pendant cette revue.
- Il n'a donc pas été possible de faire une inspection visuelle fiable de chaque page réellement rendue en production, ni de capturer des screenshots de référence.
- Les constats ci-dessous reposent sur le code source du commit indiqué. Les points visuels doivent être confirmés lors d'une inspection navigateur.
- Les tests n'ont pas été exécutés dans un environnement local pendant cette étape. Leur présence et leur configuration ont été inspectées, pas leur résultat d'exécution.

## 3. Inventaire des routes

| Route | Écran | Composant |
|---|---|---|
| `/login` | Connexion | LoginPage |
| `/` | Tableau de bord | DashboardPage |
| `/planning` | Planning | PlanningPage |
| `/tasks` | Tâches | TasksPage |
| `/sessions` | Séances | SessionsPage |
| `/courses` | Catalogue des cours | CoursesPage |
| `/courses/:courseId` | Détail d'un cours | CoursesPage / vue détaillée |
| `/learning` | Parcours d'apprentissage | LearningPage |
| `/skills` | Compétences | SkillsPage |
| `/projects` | Objectifs et projets | ProjectsPage |
| `/objectives` | Alias vers objectifs et projets | ProjectsPage |
| `/ai-coach` | Copilote IA | AiCoachPage |
| `/settings` | Paramètres | SettingsPage |
| `*` | Page inconnue | NotFoundPage |

La route `/objectives` rend le même composant que `/projects`. Lors de la refonte, conserver la compatibilité de l'ancienne route ou la rediriger proprement ; ne pas casser de lien existant.

## 4. Constats détaillés

### UX-01 — Navigation trop plate et parcours pédagogiques fragmentés

**Preuve dans le code :**
- `navigation.ts` définit neuf éléments du groupe principal, plus Paramètres.
- Cours, Apprentissage et Compétences sont des destinations distinctes.
- La barre mobile expose cinq destinations : Accueil, Planning, Tâches, Séances et Copilote.
- Projets est marqué P1 dans les métadonnées de navigation, mais reste dans le groupe principal.
- `/objectives` et `/projects` rendent le même écran.

**Impact UX probable :**
- L'utilisateur doit comprendre la différence entre plusieurs espaces voisins.
- Le parcours cours → leçon → exercice → validation de compétence n'est pas reflété par l'organisation principale.
- Des fonctions importantes pour apprendre sont moins directement visibles sur mobile que les séances.

**Décision de conception :**
- Regrouper Cours, Parcours, Leçons, Exercices et Compétences dans un espace Apprentissage.
- Regrouper Planning, Tâches et Séances dans Organisation.
- Conserver Objectifs et projets comme espace distinct.
- Préserver les routes historiques pendant la migration.
- Revoir la barre mobile à partir des tâches réellement les plus fréquentes ; ne pas figer sa composition avant les wireframes et les scénarios d'usage.

**Priorité : P0.**

### UX-02 — Le tableau de bord ne met pas encore la priorité en premier

**Preuve dans le code :**
- `DashboardPage.tsx` affiche un ruban de quatre KPI avant la grille contenant `PriorityHero`.
- L'en-tête propose déjà Nouvelle tâche et Copilote.
- Les tâches, séances, créneaux, statistiques, rapports et propositions IA sont ensuite présentés sur le même écran.

**Impact UX probable :**
- Les statistiques peuvent prendre visuellement le dessus sur l'action principale.
- L'utilisateur doit parcourir plusieurs blocs avant de décider quoi commencer.
- Les informations de suivi risquent de concurrencer la priorité du jour.

**Décision de conception :**
- Placer la priorité principale immédiatement après l'en-tête.
- Afficher une prochaine action concrète et un bouton principal clairement identifié.
- Limiter la zone initiale à trois actions ou éléments prioritaires maximum.
- Déplacer les KPI, bilans et données secondaires plus bas.
- Afficher les états vides avec une seule prochaine action pertinente.

**Priorité : P0.**

### UX-03 — Hiérarchie des boutons et cibles tactiles trop compactes

**Preuve dans le code :**
- `Button.tsx` définit `sm` en `min-h-8` (32 px) et `md` en `min-h-10` (40 px).
- Le composant partagé ne définit pas de taille tactile dédiée.
- Plusieurs pages et composants emploient fréquemment `size="sm"`, y compris dans les parcours de cours, les actions de page et les états d'erreur.
- Le shell mobile utilise aussi des commandes compactes.

**Impact UX probable :**
- Certaines actions importantes peuvent être difficiles à toucher sur téléphone.
- La différence entre action principale, secondaire et tertiaire peut manquer de constance.
- Le texte des boutons en taille compacte est parfois moins lisible.

**Décision de conception :**
- Définir des tailles et variantes officielles : primary, secondary, tertiary/ghost, destructive et icon.
- Viser une cible tactile de 44 × 44 px pour les actions mobiles importantes ; les contrôles secondaires peuvent être adaptés au contexte.
- Conserver des boutons compacts uniquement pour les actions secondaires ou denses, avec une zone interactive suffisante.
- Définir tous les états : default, hover, focus-visible, pressed, disabled, loading et feedback après exécution.
- Utiliser des libellés orientés résultat : « Appliquer ce planning », « Soumettre mon exercice », « Terminer ma séance » plutôt que « Valider » ou « OK » lorsque le contexte n'est pas explicite.

**Priorité : P0 pour les actions principales ; P1 pour l'harmonisation exhaustive.**

### UX-04 — Typographie et textes secondaires trop petits dans plusieurs contextes

**Preuve dans le code :**
- `FormField.tsx` emploie un label `text-xs` sur petit écran et `sm:text-sm` à partir du breakpoint sm.
- `Badge.tsx` utilise 11 px.
- `PageHeader.tsx` affiche sa description en 12 px et applique `truncate`.
- `StateFeedback.tsx` utilise souvent 12 px pour chargement, descriptions d'états vides et erreurs.
- `CourseLessonReader.tsx`, `CourseExercisePanel.tsx` et `CourseProjectPanel.tsx` emploient du 12 px pour plusieurs informations pédagogiques et explications.
- Les textes de code et métadonnées sont parfois également en très petite taille.

**Impact UX probable :**
- Lecture fatigante, surtout sur mobile et dans les longues sessions d'étude.
- Des consignes pédagogiques importantes peuvent ressembler à des métadonnées secondaires.
- Les descriptions de page peuvent être tronquées alors qu'elles contiennent le contexte utile.

**Décision de conception :**
- Standardiser les styles de texte : display, page title, section title, body, secondary, caption et code.
- Viser 16 px pour le corps courant et le contenu pédagogique ; réserver 12–13 px aux métadonnées non essentielles.
- Ne pas tronquer les descriptions utiles par défaut. Autoriser le retour à la ligne ou prévoir une expansion explicite.
- Améliorer interligne, largeur de lecture et séparation des paragraphes.
- Maintenir une taille adaptée pour les labels et les erreurs de formulaire.

**Priorité : P0 pour le contenu pédagogique et les descriptions importantes ; P1 pour les métadonnées.**

### UX-05 — Les en-têtes de page manquent d'une règle uniforme de composition

**Preuve dans le code :**
- `PageHeader.tsx` applique une disposition commune, mais plusieurs pages composent leur propre en-tête avec des classes locales.
- La description commune est tronquée en une seule ligne.
- Les actions sont affichées dans un conteneur horizontal défilant sur petits écrans.

**Impact UX probable :**
- Les titres, descriptions et actions ne sont pas toujours organisés de la même façon.
- Une action principale peut se retrouver repoussée ou difficile à trouver sur mobile.
- Les pages perdent en prévisibilité.

**Décision de conception :**
- Adopter un en-tête standard : titre et description à gauche ; action principale à droite sur desktop.
- Sur mobile : titre, description lisible, puis action principale pleine largeur ou clairement alignée.
- Définir des règles pour les breadcrumbs, badges de statut et actions secondaires.
- Migrer les pages vers le composant commun progressivement, sans forcer les écrans spécialisés dans un gabarit inadapté.

**Priorité : P1.**

### UX-06 — La planification expose trop d'opérations au même niveau

**Preuve dans le code :**
- `PlanningPage.tsx` présente les actions Nouveau créneau, Importer mon emploi du temps, Programme intelligent et Dupliquer vers la semaine suivante.
- La page combine navigation de semaine, Agenda/Grille, charge planifiée, conflits, catégories, filtres, jours et formulaires.
- `IntelligentPlanStudio.tsx` réunit gestion des disponibilités, réglages de génération, ajustement, historique de versions, prévisualisation, application, rejet et restauration.

**Impact UX probable :**
- L'utilisateur doit choisir entre plusieurs opérations avant de voir son planning.
- Les paramètres avancés peuvent masquer le parcours principal.
- Les statuts proposé, appliqué, rejeté et restauré doivent rester parfaitement distincts.

**Décision de conception :**
- Faire du calendrier la vue principale.
- Présenter « Générer un planning » comme un parcours guidé séparé.
- Placer les disponibilités avancées dans une section de réglages dédiée.
- Afficher la proposition sous forme d'aperçu compréhensible avant application.
- Séparer visuellement « Proposition IA » et « Planning enregistré ».
- Garder import, duplication et réglages dans des actions secondaires.

**Priorité : P0.**

### UX-07 — Le copilote concentre trop de modes et d'outils dans une même expérience

**Preuve dans le code :**
- `AiCoachPage.tsx` contient 1 453 lignes.
- L'interface comporte six amorces de conversation, un sélecteur de contexte, l'historique, des propositions, des rapports, la mémoire, un inspecteur d'outils et des imports.
- Sur mobile, l'interface expose les vues Discussion, Actions et Synthèses.
- Le panneau latéral contient plusieurs modes et filtres.

**Impact UX probable :**
- Le copilote peut être perçu comme une console de commandes plutôt que comme une conversation naturelle.
- Le choix du contexte peut constituer une décision superflue au démarrage.
- Les outils avancés risquent de concurrencer le champ de conversation.

**Décision de conception :**
- Faire de la conversation l'interface par défaut.
- Activer le contexte automatique avec indicateur discret des données utilisées.
- Garder les options avancées dans un panneau secondaire.
- Présenter les propositions dans le fil de conversation ou dans un espace latéral clairement annoncé.
- N'afficher les amorces que dans une conversation vide, avec un nombre limité et des exemples contextualisés.
- Conserver l'approbation explicite des mutations et l'inspection des permissions.

**Priorité : P0.**

### UX-08 — L'espace Apprentissage doit devenir le parcours pédagogique de référence

**Preuve dans le code :**
- `CoursesPage.tsx` gère le catalogue des cours.
- `CourseDetailView.tsx` présente les niveaux et les onglets Chapitres, Projet & validation, Docs & vidéos.
- `CourseLessonReader.tsx` présente des étapes progressives et des exemples commentés.
- `CourseExercisePanel.tsx` gère les exercices et tentatives.
- `CourseProjectPanel.tsx` gère les projets, livrables, corrections et seuils.
- `CourseTutorPanel.tsx` propose un tuteur de chapitre.
- `LearningPage.tsx` gère séparément parcours, modules et leçons.
- `SkillsPage.tsx` gère les évaluations et les preuves de compétences.

**Points positifs à préserver :**
- Lecture progressive des étapes.
- Exercices et tentatives.
- Tuteur IA contextualisé.
- Projet pratique de niveau.
- Verrou pédagogique avant passage au niveau suivant.
- Distinction entre leçon terminée et compétence validée.

**Décision de conception :**
- Faire de l'espace Apprentissage le point d'entrée unique.
- Unifier la navigation entre cours, parcours, modules, leçons, exercices, projets de niveau, ressources et compétences.
- Ne pas supprimer les vues spécialisées existantes ; les rendre accessibles depuis le parcours naturel.
- Conserver le principe de progression contrôlée par les validations, et non par la simple consultation d'un contenu.
- Ne pas obliger l'étudiant à choisir entre plusieurs rubriques avant de reprendre son apprentissage.

**Priorité : P0.**

### UX-09 — Les paramètres rassemblent plusieurs sujets hétérogènes

**Preuve dans le code :**
- `SettingsPage.tsx` regroupe profil, fuseau horaire, consignes IA, disponibilités, fournisseur IA, sécurité, apparence, espace de travail et connexions.

**Décision de conception :**
- Structurer les paramètres par catégories avec un sommaire clair.
- Séparer les préférences personnelles des réglages avancés de fournisseur IA et des informations techniques.
- Rendre les états « modifié », « enregistré » et « erreur » visibles.
- Ne pas afficher les informations techniques sensibles si elles ne sont pas nécessaires à l'utilisateur.

**Priorité : P1.**

### UX-10 — Gestion des dialogues et navigation clavier à compléter

**Preuve dans le code :**
- Le tiroir mobile de `AppShell.tsx` utilise `role="dialog"` et `aria-modal="true"`.
- Il se ferme à Échap et au clic sur l'arrière-plan.
- Le composant inspecté ne met pas en évidence de gestion dédiée du focus initial, du piège de focus et de la restitution du focus au déclencheur.

**Décision de conception :**
- Mettre le focus dans le dialogue à l'ouverture.
- Garder le focus dans le dialogue tant qu'il est ouvert.
- Restaurer le focus sur le bouton déclencheur à la fermeture.
- Empêcher le contenu sous-jacent d'être utilisé pendant un dialogue modal.
- Vérifier aussi les confirmations, drawers et modales des pages.

**Priorité : P1.**

### UX-11 — Le système visuel est partiellement partagé, mais les conventions restent dispersées

**Preuve dans le code :**
- Des composants communs existent : Button, Card, FormFields, Badge, StateFeedback, Icon et ThemeToggle.
- Les styles de pages contiennent encore de nombreuses classes Tailwind directes et des valeurs de couleurs répétées.
- Les tailles et densités textuelles varient suivant les composants.
- `index.css` nomme Geist, Plus Jakarta Sans et Inter dans la pile de polices, mais aucun fichier de police n'est présent dans l'arborescence inspectée et `index.html` ne charge pas de police externe.

**Décision de conception :**
- Créer des tokens centralisés pour couleurs, typographie, espacements, rayons, ombres, largeurs et états.
- Vérifier la police réellement rendue avant de la standardiser ; charger une police seulement si nécessaire et de manière maîtrisée.
- Garder une palette claire et un mode sombre explicite.
- Éviter de réécrire toutes les classes d'un seul coup : migrer par composant et par page.

**Priorité : P1.**

### UX-12 — Les tests valident des interactions, mais pas encore le rendu réel multi-écrans

**Preuve dans le code :**
- `vitest.config.ts` utilise l'environnement `jsdom`.
- `E2eAcceptance.test.tsx` utilise React Testing Library et `createMemoryRouter`.
- Le package frontend ne déclare ni Playwright ni Cypress.
- Le workflow CI exécute typecheck, Vitest et build frontend ; aucun test navigateur responsive n'apparaît dans le workflow inspecté.

**Impact :**
- Les tests existants sont utiles pour les interactions et la non-régression métier.
- Ils ne démontrent pas à eux seuls la qualité du placement, des dimensions, du rendu ou du comportement dans Safari iOS, Chrome Android et différents viewports.

**Décision de conception :**
- Conserver et étendre les tests Vitest.
- Ajouter une suite navigateur ciblée pour les parcours essentiels et les viewports desktop/tablette/mobile.
- Tester visuellement les états vides, erreurs, menus, formulaires, contenus longs et modales.
- Automatiser les vérifications d'accessibilité lorsque possible.

**Priorité : P1 avant livraison finale.**

## 5. Atouts existants à préserver

- Design clair, mode sombre et thème synchronisé à l'initialisation.
- Skip link vers le contenu principal.
- Focus visible global.
- Navigation mobile inférieure et tiroir complet.
- Correction du zoom automatique iOS grâce à des champs de 16 px sur appareils tactiles.
- Composants de chargement, succès, erreur et états vides.
- Labels de champs reliés par `htmlFor`.
- Rôles d'accessibilité `status` et `alert` sur les feedbacks partagés.
- Tests de parcours pour tâches, apprentissage, cours, planning, copilote et paramètres.
- Parcours de cours déjà structuré avec exercices, corrections, ressources et validation.
- Séparation entre les propositions IA et les mutations nécessitant une validation.

La refonte doit améliorer ces fondations, pas les remplacer sans raison.

## 6. Priorisation globale

| Priorité | Chantier | Motif |
|---|---|---|
| P0 | Architecture de navigation | Réduit la fragmentation des espaces |
| P0 | Tableau de bord | Met la priorité et l'action au premier plan |
| P0 | Parcours Apprentissage | Unifie le parcours central de l'étudiant |
| P0 | Planning intelligent | Réduit la complexité de décision |
| P0 | Copilote IA | Rend la conversation naturelle et les outils secondaires |
| P0 | Textes et boutons critiques | Améliore compréhension et exécution |
| P1 | Design system et tokens | Stabilise la cohérence visuelle |
| P1 | Responsive et tailles tactiles | Améliore l'usage téléphone/tablette |
| P1 | Accessibilité des dialogues | Fiabilise le clavier et les technologies d'assistance |
| P1 | Paramètres et projets | Clarifie les espaces secondaires |
| P1 | Tests navigateur | Valide le rendu réel |
| P2 | Finitions visuelles | Détails de transitions, micro-interactions et densité |

## 7. Règles de migration

1. Travailler sur une branche dédiée ; ne pas pousser directement sur `main`.
2. Ne pas modifier le backend, les schémas SQL, les politiques Supabase ou les contrats API pour une raison purement visuelle.
3. Conserver les routes historiques pendant la transition.
4. Conserver le fonctionnement des composants métier et les tests existants.
5. Créer les tokens et composants partagés avant de dupliquer les styles dans les pages.
6. Refaire et valider une page à la fois.
7. Chaque action visible doit avoir un résultat et un feedback réels.
8. Ne pas supprimer une fonctionnalité pour simplifier artificiellement l'écran ; la replacer dans une hiérarchie plus claire.
9. Distinguer les données réellement calculées des estimations et des contenus vides.
10. Ne pas considérer un rendu visuellement réussi comme validé tant que le parcours fonctionnel et le responsive ne sont pas testés.

## 8. Critères de validation de l'étape 0

- [x] Routes et espaces principaux recensés.
- [x] Principaux composants partagés inspectés.
- [x] Pages et parcours prioritaires inspectés.
- [x] Tests frontend et pipeline CI inspectés.
- [x] Forces existantes et risques de régression documentés.
- [x] Limites de l'audit visuel explicitées.
- [x] Ordre de priorité établi.
- [ ] Revue humaine du rapport et validation de l'architecture cible.

## 9. Étape suivante proposée — Phase 1

Après validation de cet audit, produire les wireframes détaillés et l'architecture d'information :

1. Navigation desktop et mobile.
2. Tableau de bord.
3. Accueil Apprentissage et détail d'un cours.
4. Lecture de leçon et exercices.
5. Planning et parcours de génération intelligente.
6. Copilote IA et cartes de propositions.
7. Tâches, séances et projets.
8. Paramètres.

Chaque wireframe spécifiera les textes, l'ordre des blocs, la position de chaque bouton, les états, les variantes desktop/mobile et les interactions.

**Aucune modification visuelle majeure du frontend n'est incluse dans ce premier livrable.**
