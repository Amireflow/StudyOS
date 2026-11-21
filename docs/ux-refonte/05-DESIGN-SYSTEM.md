# 05 — Design System premium

> Statut : spécification proposée — à valider avant toute modification visuelle du produit.
> Périmètre : frontend React + TypeScript + Tailwind existant. Ce document définit les règles de conception ; il ne constitue pas une preuve de rendu réel.

## 1. Principes directeurs

1. **Clarté avant décoration** : une action principale par zone ; les actions secondaires restent visibles sans rivaliser.
2. **Hiérarchie stable** : mêmes rôles, espacements et comportements sur toutes les pages.
3. **Densité maîtrisée** : tableaux et vues de pilotage efficaces ; lecture pédagogique confortable et peu dense.
4. **Progression visible** : l'utilisateur sait où il se trouve, ce qui est terminé et quelle est la prochaine action.
5. **Confiance** : aucune action destructive ou modification de données par l'IA sans confirmation explicite.
6. **Responsive réel** : chaque écran doit fonctionner au tactile, au clavier et sur petit viewport.
7. **Sobriété premium** : surfaces neutres, contrastes nets, accent limité aux actions et états significatifs ; pas de gradients décoratifs systématiques, glassmorphism ou ombres lourdes.

## 2. Fondations visuelles

### 2.1 Palette de référence

Les valeurs ci-dessous sont les tokens de conception de départ. Elles doivent être contrôlées avec un outil de contraste pendant l'implémentation.

| Rôle | Clair | Sombre | Usage |
|---|---|---|---|
| Canvas | `#F5F5F3` | `#09090B` | arrière-plan global |
| Surface 1 | `#FFFFFF` | `#18181B` | cartes et panneaux |
| Surface 2 | `#F4F4F5` | `#27272A` | champs, éléments secondaires |
| Surface élevée | `#FFFFFF` | `#27272A` | menus, popovers, dialogues |
| Texte principal | `#18181B` | `#FAFAFA` | titres et contenu |
| Texte secondaire | `#52525B` | `#A1A1AA` | descriptions |
| Texte discret | `#71717A` | `#A1A1AA` | métadonnées, jamais seul pour une information essentielle |
| Bordure | `#E4E4E7` | `#3F3F46` | séparateurs et contours |
| Accent | `#0F766E` | `#2DD4BF` | action principale, lien actif, focus |
| Accent doux | `#CCFBF1` | `#134E4A` | fond accentué discret |
| Succès | `#15803D` | `#4ADE80` | réussite confirmée |
| Avertissement | `#A16207` | `#FACC15` | attention non bloquante |
| Erreur | `#BE123C` | `#FDA4AF` | erreur, suppression, danger |
| Information | `#1D4ED8` | `#93C5FD` | information neutre |

**Règles :**
- L'accent teal est réservé à l'action principale, à la navigation active et au focus ; les autres actions restent neutres.
- Une couleur d'état est toujours accompagnée d'un libellé ou d'une icône compréhensible.
- Ne pas utiliser uniquement la couleur pour signaler une erreur, un statut ou une progression.
- Les couleurs de texte et de fond doivent respecter WCAG 2.2 AA : 4,5:1 pour le texte courant, 3:1 pour le grand texte et les composants graphiques pertinents.
- Le thème sombre est conçu explicitement ; ne pas simplement inverser les couleurs du thème clair.

### 2.2 Typographie

La feuille actuelle déclare Geist, Plus Jakarta Sans et Inter sans garantir leur chargement local. Ne pas présumer qu'une police distante est disponible.

| Rôle | Taille / interligne | Graisse | Règle |
|---|---:|---:|---|
| Display de page | 30/36 px | 650–700 | rare, une fois par page |
| H1 | 26/34 px | 650 | titre principal |
| H2 | 20/28 px | 600 | section |
| H3 | 16/24 px | 600 | sous-section / carte |
| Corps | 15/24 px | 400 | lecture standard |
| Corps compact | 14/21 px | 400 | tableaux et interfaces denses |
| Label | 13/18 px | 550 | champs et contrôles |
| Aide | 13/19 px | 400 | aide, hint, description courte |
| Micro-métadonnée | 12/16 px | 500 | date, catégorie, compteur non essentiel |

- Pile recommandée : Geist si une police locale existe et est effectivement chargée ; sinon system-ui avec fallback natif. Une seule famille principale.
- Le contenu pédagogique ne descend pas sous 15 px sur mobile et desktop, hors code, légendes et métadonnées.
- Largeur de lecture des leçons : 65–75 caractères par ligne ; paragraphes de 2–5 lignes en moyenne.
- Utiliser une hauteur de ligne confortable ; ne pas compresser les explications pour gagner de la place.
- Les nombres tabulaires sont recommandés pour les durées, scores et statistiques.

### 2.3 Échelle d'espacement

Base de 4 px, avec les valeurs autorisées suivantes :

| Token | Valeur | Usage |
|---|---:|---|
| space-1 | 4 px | proximité icône/texte |
| space-2 | 8 px | éléments liés |
| space-3 | 12 px | petits groupes |
| space-4 | 16 px | espacement standard |
| space-5 | 20 px | groupes de contrôles |
| space-6 | 24 px | sections compactes |
| space-8 | 32 px | séparation de sections |
| space-10 | 40 px | grands blocs |
| space-12 | 48 px | séparation majeure |
| space-16 | 64 px | respiration de page |

- Une seule échelle cohérente ; éviter les valeurs arbitraires ajoutées sans raison.
- Les éléments qui appartiennent au même groupe sont plus proches entre eux que des groupes distincts.
- Le contenu mobile conserve 16 px de marge latérale minimale, sauf média explicitement bord à bord.

### 2.4 Rayons, bordures et élévation

- Contrôles : rayon 8–10 px.
- Cartes : rayon 14–16 px.
- Dialogues / panneaux majeurs : rayon 16–20 px.
- Pills : rayon complet, uniquement pour les statuts et filtres compacts.
- Bordure standard 1 px, contraste discret mais perceptible.
- Ombres limitées aux menus, popovers et dialogues ; les cartes reposent principalement sur le contraste des surfaces.
- Éviter d'empiler bordure + ombre + fond coloré sur chaque composant.

## 3. Grille et responsive

### 3.1 Breakpoints de travail

| Nom | Largeur | Comportement |
|---|---:|---|
| Mobile étroit | < 360 px | une colonne, actions essentielles seulement |
| Mobile | 360–639 px | navigation basse, cartes empilées |
| Tablette | 640–1023 px | navigation compacte, grilles 1–2 colonnes |
| Desktop | 1024–1279 px | sidebar et contenu principal |
| Large desktop | ≥ 1280 px | contenu centré, largeur maximale contrôlée |

Les breakpoints Tailwind du projet restent la référence technique s'ils diffèrent ; cette table décrit les comportements attendus, pas une obligation de changer la configuration.

### 3.2 Largeurs et colonnes

- Largeur de lecture standard : 720–800 px.
- Zone principale de pilotage : 960–1200 px selon la page.
- Sidebar desktop : 240–264 px ; compacte uniquement si les libellés restent accessibles.
- Planning : préserver une largeur utile aux colonnes horaires ; sur mobile, basculer vers une liste chronologique plutôt que réduire les cellules à l'illisible.
- Formulaires : largeur limitée pour faciliter le balayage visuel.
- Ne jamais créer de défilement horizontal global. Les tableaux complexes peuvent avoir un conteneur défilant identifié et utilisable.

### 3.3 Adaptation par appareil

**Mobile**
- Navigation basse à cinq entrées définies dans l'architecture.
- Cibles tactiles de 44 × 44 px minimum ; 48 px recommandés pour les actions principales.
- Actions secondaires dans un menu ou une zone repliable ; ne pas cacher l'action principale.
- Les dialogues deviennent des panneaux plein écran ou des feuilles adaptées à la hauteur disponible.
- Les formulaires ont une seule colonne ; boutons principaux pleine largeur si cela facilite la validation.
- Respecter les safe areas iOS et le clavier virtuel.

**Tablette**
- Éviter la juxtaposition de trois colonnes étroites.
- Conserver des panneaux latéraux seulement s'ils gardent une largeur lisible ; sinon les empiler ou les rendre repliables.

**Desktop**
- Navigation persistante, contenu centré et hiérarchie stable.
- Utiliser les colonnes pour comparer des informations liées, jamais pour réduire la largeur du texte pédagogique.
- Les raccourcis clavier sont complémentaires, jamais obligatoires.

## 4. Composants fondamentaux

### 4.1 Boutons

| Variante | Rôle | Exemple |
|---|---|---|
| Primary | action principale unique de la zone | Commencer la séance |
| Secondary | action utile mais non dominante | Enregistrer le brouillon |
| Outline | action neutre avec contour | Prévisualiser |
| Ghost | action discrète / navigation locale | Modifier |
| Danger | action destructive explicite | Supprimer |
| Link | navigation ou action textuelle | Voir les détails |

Tailles :
- Standard : hauteur minimale 44 px, texte 14–15 px.
- Compact : 36 px minimum, réservé aux interfaces denses desktop et jamais comme seule cible d'une action mobile.
- Icon-only : 44 × 44 px minimum, avec nom accessible explicite et infobulle sur desktop.
- État loading : conserver la largeur, désactiver les doubles soumissions et annoncer l'activité.
- État disabled : contraste suffisant pour être compris ; expliquer la raison si elle n'est pas évidente.

Règles :
- Un seul bouton primaire par bloc d'action.
- Libellés orientés résultat : « Créer le cours », « Enregistrer la séance », « Valider mon niveau ».
- Éviter « OK », « Valider » sans objet, « Soumettre » ou « Continuer » quand une formulation plus précise est possible.
- Les actions destructives ne sont jamais primaires par défaut.

### 4.2 Champs de formulaire

- Label visible persistant ; le placeholder ne remplace jamais le label.
- Hauteur standard 44–48 px ; textarea dimensionnée selon le contenu.
- Texte saisi 16 px sur mobile pour éviter le zoom automatique iOS.
- Aide sous le champ ; erreur au même endroit, reliée via `aria-describedby`.
- Validation au bon moment : ne pas afficher d'erreur avant interaction, sauf erreur serveur ou champ requis au submit.
- Conserver la saisie après une erreur serveur.
- Regrouper les champs par intention et limiter les champs facultatifs.
- Les contrôles personnalisés doivent reproduire clavier, focus, libellé et état natif.

### 4.3 Cartes et panneaux

- Une carte représente une unité cohérente : tâche, cours, progression ou résumé.
- Titre, contexte, information clé, action ; ne pas transformer chaque ligne en carte.
- Éviter les cartes imbriquées.
- Les cartes cliquables ont un focus visible, un état hover, une zone d'activation claire et un libellé accessible.
- Les actions secondaires sont séparées de la zone cliquable principale pour éviter les clics accidentels.

### 4.4 Navigation et onglets

- Libellés courts, compréhensibles sans icône.
- L'état actif utilise au moins deux indices (couleur + forme/poids/indicateur).
- Les onglets servent à changer de vue dans un même contexte ; les liens servent à changer de page.
- Ne pas placer des actions de création dans la même hiérarchie visuelle que les destinations principales.
- Conserver le retour navigateur, les URLs directes et les routes historiques documentées.

### 4.5 Badges, tags et progression

- Badge réservé à un statut, une catégorie ou un compteur utile.
- Maximum un badge dominant par élément.
- Les statuts utilisent des mots explicites : « À commencer », « En cours », « En attente », « Terminé ».
- Barre de progression toujours accompagnée d'une valeur ou d'un libellé.
- Ne jamais présenter un niveau de compétence comme acquis sans validation par preuve réelle.

### 4.6 Dialogues, menus et notifications

- Dialogue uniquement pour une décision nécessitant l'attention ; préférer une confirmation en ligne pour les actions simples.
- Titre explicite, conséquence, action primaire, annulation clairement visible.
- Focus initial pertinent, confinement du focus, fermeture Échap si non destructive, restitution du focus à l'élément déclencheur.
- Toasts courts pour une confirmation non critique ; erreurs persistantes à proximité de l'action concernée.
- Les messages d'erreur expliquent le problème et la prochaine action possible.

## 5. Modèle d'interaction et microcopy

### 5.1 Formule des libellés

- Action + objet : « Ajouter une tâche », « Générer un programme », « Reprendre le cours ».
- Résultat concret après succès : « Séance enregistrée », « Cours créé ».
- État vide : expliquer pourquoi c'est vide, ce que l'utilisateur peut faire, puis proposer une action unique.
- Erreur : décrire ce qui a échoué sans jargon, dire si les données sont conservées et proposer une récupération.
- Confirmation destructive : nommer l'objet et l'effet irréversible.

### 5.2 États obligatoires pour chaque écran

1. Chargement initial et chargement local.
2. Succès et données présentes.
3. Vide initial (aucune donnée créée).
4. Vide après filtrage (aucun résultat).
5. Erreur réseau / serveur avec reprise.
6. Permission ou session expirée.
7. Action en cours / double soumission empêchée.
8. Contenu partiel ou indisponible.
9. Mobile sans espace suffisant.

Les états doivent être dessinés et testés, pas laissés à des placeholders improvisés.

## 6. Expérience d'apprentissage profonde

L'expérience pédagogique est volontairement distincte des écrans de gestion : priorité à la concentration et à la compréhension.

### 6.1 Structure du lecteur

- En-tête : retour au cours, titre du cours, progression du module.
- Colonne principale : objectif de la leçon, contenu structuré, exemples, résumé.
- Colonne secondaire desktop : sommaire de leçon et progression ; repliable sur tablette.
- Mobile : sommaire dans un panneau ; contenu sur une seule colonne.
- Actions de bas de page : « Marquer comme compris » seulement si cela ne contourne pas les validations prévues ; sinon « Passer à l'exercice ».
- La navigation entre leçons respecte les prérequis et les verrous existants.

### 6.2 Règles de contenu

Une leçon de qualité doit, selon le sujet :
1. annoncer les objectifs mesurables ;
2. expliquer les prérequis ;
3. introduire une notion à la fois ;
4. fournir des exemples progressifs et commentés ;
5. signaler les erreurs fréquentes ;
6. proposer une mise en pratique guidée ;
7. proposer des exercices gradués avec consignes et critères ;
8. terminer par un récapitulatif et une vérification de compréhension ;
9. indiquer les ressources complémentaires pertinentes.

- Ne pas générer ou afficher tout un cursus comme un mur de contenu ; révéler le niveau et la leçon nécessaires au moment opportun.
- Le tutorat IA accompagne la leçon et pose des questions ; il ne remplace pas l'effort de l'apprenant ni les preuves.
- La correction de projet distingue critères, observations, erreurs, pistes de correction et décision de validation.
- La progression est enregistrée de façon explicite et fiable ; une simple ouverture de page ne valide pas une compétence.

### 6.3 États pédagogiques

- Non commencé : objectif et prérequis visibles.
- En cours : position de reprise claire.
- Exercice à faire : consigne et critères visibles.
- Correction disponible : retour structuré.
- Validation en attente : préciser la preuve manquante.
- Validé : montrer ce qui a été acquis et la suite déverrouillée.
- Bloqué : expliquer précisément le prérequis requis et comment l'obtenir.

## 7. Dashboard et organisation

- Le tableau de bord commence par la priorité principale active et sa prochaine action, pas par une rangée de KPI.
- Une action principale claire ; les statistiques sont secondaires.
- Planning, tâches et séances partagent les mêmes conventions de date, heure, durée et statut.
- Les cours universitaires importés restent visuellement distincts des séances personnelles et ne peuvent pas être modifiés comme de simples créneaux personnels.
- Les conflits de planning sont expliqués avant validation ; aucune proposition IA ne doit être appliquée silencieusement.
- Les vues denses proposent filtres et recherche sans multiplier les barres d'outils.

## 8. Accessibilité et ergonomie

Cible : WCAG 2.2 AA, sous réserve de tests réels.

- Navigation complète au clavier ; ordre de tabulation logique.
- Focus visible et jamais masqué par un header ou une barre fixe.
- Contraste texte 4,5:1 ; grand texte et composants graphiques 3:1.
- Cibles tactiles au moins 44 × 44 px, avec espacement suffisant.
- Chaque icône interactive possède un nom accessible ; les icônes décoratives sont ignorées par les lecteurs d'écran.
- Labels et descriptions associés aux champs ; erreurs annoncées et identifiables.
- Respect de `prefers-reduced-motion` ; aucune information uniquement animée.
- Pas de contenu qui clignote ; animations courtes et fonctionnelles.
- Zoom navigateur à 200 % et reflow à 320 px sans perte d'information ni défilement horizontal global.
- Dialogues : focus management, Échap approprié, retour du focus.
- Tests manuels avec VoiceOver sur iOS/macOS et NVDA sur Windows lors de la recette.

## 9. Mouvement et retours visuels

- Transitions fonctionnelles de 120–200 ms.
- Pas de déplacement de mise en page au chargement ; réserver les dimensions des médias.
- Hover ne doit jamais être le seul moyen de découvrir une action.
- Feedback immédiat après action : état loading, succès, erreur ou confirmation.
- Désactiver ou réduire les animations si l'utilisateur le demande dans son système.

## 10. Règles de cohérence et anti-patterns

À éviter :
- plusieurs boutons primaires côte à côte ;
- libellés vagues ou incohérents pour la même action ;
- texte courant à 11–12 px ;
- icônes sans libellé dans les zones de navigation principales ;
- champs sans label visible ;
- contrôles tactiles trop petits ;
- tableaux compressés sur mobile ;
- cartes imbriquées à répétition ;
- couleurs d'état utilisées comme décoration ;
- indicateurs de progression non reliés à des critères ;
- action IA appliquée sans validation ;
- états vides ou erreurs sans solution ;
- ajout d'un nouveau composant alors qu'un composant partagé existant peut être amélioré.

## 11. Critères d'acceptation du Design System

La spécification est prête pour l'implémentation lorsque :
- [ ] tous les tokens clair/sombre sont définis et documentés ;
- [ ] les échelles typo, espacements, rayons et tailles de contrôle sont cohérentes ;
- [ ] chaque composant partagé a variantes, tailles, états et règles d'accessibilité ;
- [ ] les règles mobile/tablette/desktop sont définies ;
- [ ] le lecteur pédagogique possède ses règles propres ;
- [ ] les microcopies des actions critiques sont explicites ;
- [ ] les états vide, erreur, chargement et succès sont couverts ;
- [ ] les règles préservent les validations métier et les verrous pédagogiques ;
- [ ] les tests de contraste et de clavier sont prévus ;
- [ ] les décisions sont approuvées avant toute migration de code.

## 12. Hypothèses à vérifier avant le code

1. Confirmer la police réellement rendue dans le navigateur et vérifier si Geist est fournie localement.
2. Mesurer les contrastes des tokens proposés dans les deux thèmes.
3. Vérifier les composants partagés et leurs usages avant de changer leurs tailles par défaut.
4. Établir des captures de référence desktop/mobile pour les parcours principaux.
5. Identifier les exceptions de densité pour planning, tableaux et outils IA.

**Décision de périmètre :** ce Design System définit la cible. Il ne demande ni réécriture globale du frontend, ni changement des API, du modèle de données ou des règles métier.
