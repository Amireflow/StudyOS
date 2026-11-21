# 07 — Lot 0 : état de référence et inventaire technique

> Date d'inspection : 21 novembre 2026
> Branche inspectée : `ux/audit-initial-2026-11-21`
> Référence de comparaison : `main` au commit `c77e293228afe20986a1674e208e85d57a95c500`
> Statut : inventaire source réalisé ; captures visuelles navigateur non réalisées dans cet environnement.
> Garantie : aucun fichier applicatif frontend/backend n'a été modifié pendant ce lot.

## 1. Objectif du lot

Établir une référence vérifiable avant la migration visuelle :
- repérer les fondations CSS et la typographie ;
- inventorier les composants partagés et leurs dimensions ;
- documenter la navigation et le gabarit responsive ;
- identifier les outils de test disponibles ;
- distinguer les constats source des vérifications qui nécessitent un navigateur réel.

## 2. Sources inspectées

| Fichier | Éléments vérifiés |
|---|---|
| `frontend/package.json` | scripts, dépendances, absence de Playwright/Cypress |
| `frontend/index.html` | viewport, métadonnées PWA, thème initial, chargement des polices |
| `frontend/src/main.tsx` | montage React, import de la feuille globale |
| `frontend/src/index.css` | police déclarée, couleurs de base, focus, scrollbar, safe areas, iOS |
| `frontend/src/components/layout/AppShell.tsx` | sidebar, header mobile, tiroir, barre basse, largeur de contenu |
| `frontend/src/components/layout/navigation.ts` | destinations, groupes, libellés et barre mobile |
| `frontend/src/app/router.tsx` | routes, alias, structure protégée |
| `frontend/src/components/layout/PageHeader.tsx` | hiérarchie de titre, description et actions |
| `frontend/src/components/ui/Button.tsx` | variantes, tailles, états |
| `frontend/src/components/ui/FormFields.tsx` | labels, champs, erreurs, dimensions |
| `frontend/src/components/ui/Card.tsx` | surfaces, rayons, espacements |
| `frontend/src/components/ui/Badge.tsx` | taille de texte, variantes sémantiques |
| `frontend/src/components/ui/StateFeedback.tsx` | chargement, vide, erreur et succès |
| `frontend/src/features/dashboard/DashboardPage.tsx` | composition et contenus du tableau de bord |
| `frontend/src/features/courses/CourseLessonReader.tsx` | structure de lecture et progression étape par étape |
| `frontend/vitest.config.ts` et `frontend/src/test/setup.ts` | environnement et configuration des tests |

## 3. Inventaire des fondations visuelles actuelles

### 3.1 Couleurs et thèmes

- Fond clair global : `#f5f5f3`.
- Fond sombre global : `#09090b`.
- Texte clair principal : `#18181b`.
- Texte sombre principal : `#f4f4f5`.
- Accent de focus clair : `#0f766e`.
- Accent de focus sombre : `#2dd4bf`.
- Le thème est initialisé avant le montage React depuis le stockage local et la préférence système.
- Les composants emploient principalement des classes zinc, teal, emerald, amber et rose, avec plusieurs valeurs arbitraires directement dans le JSX.

**Constat :** les deux thèmes existent déjà et doivent être conservés. Les couleurs sont partiellement sémantisées par composant, mais il n'existe pas encore de couche complète de tokens sémantiques partagés.

### 3.2 Typographie et chargement de police

La pile CSS déclarée est :
`Geist → Plus Jakarta Sans → Inter → ui-sans-serif → system-ui → polices système`.

Vérifications effectuées :
- aucune déclaration `@font-face` dans le fichier CSS inspecté ;
- aucun `link rel="preload"` ou chargement de police dans `index.html` ;
- aucune dépendance de police dédiée dans `frontend/package.json`.

**Conclusion prudente :** le dépôt ne démontre pas que Geist, Plus Jakarta Sans ou Inter sont effectivement chargées. En l'absence de ces polices, le navigateur utilise un fallback système. La police réellement rendue reste à confirmer par inspection navigateur de `getComputedStyle` et des ressources réseau.

### 3.3 Composants partagés

| Composant | État actuel observé | Écart / point de contrôle |
|---|---|---|
| Button | variantes primary, secondary, ghost, danger ; tailles sm et md | sm = 32 px min., md = 40 px min. ; cible tactile de 44 px à atteindre selon contexte |
| FormFields | label, hint, erreur, Input, Textarea, Select | label mobile 12 px ; aide et erreur 12 px ; champ min. 40 px |
| Card | surface blanche/zinc, rayon 16 px | description 12 px ; styles majoritairement utilitaires |
| Badge | 5 variantes sémantiques | texte 11 px ; à réserver aux métadonnées |
| PageHeader | titre, description, badge, actions | description en 12 px et tronquée ; actions horizontales scrollables sur petit écran |
| StateFeedback | chargement, vide, erreur, succès | plusieurs messages principaux en 12 px ; vérifier lisibilité et densité |
| AppShell | sidebar desktop, header mobile, drawer et bottom nav | drawer annoncé comme modal ; gestion du focus à vérifier au clavier et lecteur d'écran |

Les composants partagés sont une base utile : il faut les faire évoluer progressivement plutôt que réécrire chaque page indépendamment.

### 3.4 Gabarit et responsive

Constats dans `AppShell.tsx` :
- sidebar desktop à partir de `lg`, largeur `w-60` (240 px) ;
- contenu principal limité à `max-w-5xl` ;
- marges horizontales mobiles de 14 px environ, puis 24 px et 32 px selon breakpoint ;
- header mobile sticky ;
- navigation basse à cinq destinations ;
- tiroir mobile pleine hauteur avec largeur 288 px et maximum 85vw ;
- prise en compte des safe areas et du mode PWA standalone ;
- champ mobile forcé à 16 px pour éviter le zoom automatique iOS.

**Points à vérifier visuellement :**
- densité de la navigation basse à 320–360 px ;
- place disponible pour les actions dans les PageHeader ;
- recouvrement éventuel du contenu par la barre basse ;
- comportement du tiroir avec clavier virtuel et lecteur d'écran ;
- scroll horizontal des tableaux et plannings ;
- largeur effective du lecteur pédagogique et longueur des lignes.

### 3.5 Navigation et routes

Le tableau de navigation contient dix entrées :
- Tableau de bord ;
- Planning ;
- Tâches ;
- Séances ;
- Cours ;
- Apprentissage ;
- Compétences ;
- Mes objectifs et projets ;
- Copilote IA ;
- Paramètres.

Les routes existantes couvrent également `/objectives` comme alias de `/projects`, et `/courses/:courseId`.

**Écart avec la décision approuvée :** les groupes Apprentissage et Organisation ne sont pas encore matérialisés dans la navigation. Le changement devra préserver toutes les routes et tous les accès directs.

### 3.6 Apprentissage

Le lecteur `CourseLessonReader` possède déjà :
- découpage du contenu Markdown en étapes ;
- révélation progressive des étapes ;
- progression et reprise à l'étape enregistrée ;
- navigation entre leçons ;
- exercices et tutorat associés.

**Décision de migration :** conserver ce comportement métier et améliorer d'abord la lisibilité, le rythme, la hiérarchie, la navigation et la mise en page.

## 4. Inventaire des outils de qualité

| Outil | Présence dans le dépôt |
|---|---|
| TypeScript | oui |
| Vitest | oui |
| jsdom | oui |
| Testing Library | oui |
| Script typecheck | oui |
| Script tests | oui |
| Script build | oui |
| Playwright | non trouvé dans les dépendances inspectées |
| Cypress | non trouvé dans les dépendances inspectées |
| Test navigateur responsive automatisé | non établi |

Les scripts définis sont :
- `npm run typecheck`
- `npm run test`
- `npm run build`

**Limite d'exécution :** l'inspection de ce lot a été effectuée à partir des fichiers GitHub. Aucun checkout local ni environnement Node connecté au dépôt n'était disponible ici ; les scripts ne sont donc pas déclarés exécutés ou réussis.

## 5. Référence visuelle navigateur — statut

L'URL de production est connue : `https://amireflow-study-os.onrender.com`.

La tentative d'ouverture de cette URL via l'outil de consultation web a renvoyé une erreur d'accès. Aucun navigateur graphique interactif ou moteur de capture Playwright n'est disponible dans cet environnement.

Par conséquent :
- aucune capture d'écran réelle desktop ou mobile n'est jointe ;
- aucune mesure de pixels calculée depuis le DOM n'est revendiquée ;
- la police réellement rendue et les contrastes calculés ne sont pas certifiés ;
- aucun parcours visuel connecté n'a été simulé.

**Pour compléter la référence visuelle**, il faudra disposer de captures de l'application ouverte et authentifiée, ou d'un environnement navigateur permettant de consulter l'application. Captures souhaitées :
1. Dashboard — desktop 1440 px ;
2. Dashboard — mobile 390 px ;
3. Index des cours — desktop et mobile ;
4. Lecteur de leçon — desktop et mobile ;
5. Planning — desktop et mobile ;
6. Copilote IA — desktop et mobile ;
7. Paramètres — mobile ;
8. thème clair et thème sombre pour les écrans clés.

Ne pas utiliser des maquettes comme substitut à des captures réelles de la version actuelle.

## 6. Registre des écarts de référence

| ID | Écart / risque | Priorité | Lot concerné |
|---|---|---|---|
| REF-01 | Bouton sm 32 px et md 40 px ; plusieurs actions risquent d'être trop petites au tactile | P1 | Lot 1 |
| REF-02 | Texte d'aide, erreur, description et badge souvent en 11–12 px | P1 | Lot 1 |
| REF-03 | Police déclarée mais chargement local non démontré | P1 | Lot 1 |
| REF-04 | Couleurs définies en partie directement dans les composants | P1 | Lot 1 |
| REF-05 | Description du PageHeader tronquée | P1 | Lot 1 |
| REF-06 | Navigation sans groupes Apprentissage / Organisation | P1 | Lot 2 |
| REF-07 | Focus trap et restitution du focus du drawer/dialogue non démontrés | P1 | Lot 1–6 |
| REF-08 | Pas de test visuel navigateur automatisé établi | P1 | Lot 6 |
| REF-09 | Référence de captures desktop/mobile manquante | Bloquant pour comparaison visuelle | Lot 0 |
| REF-10 | Lecteur pédagogique à inspecter visuellement avant/après | P1 | Lot 3 |

## 7. Checklist de validation du Lot 0

- [x] Branche de travail dédiée confirmée dans le contexte GitHub.
- [x] Fichiers racine frontend et composants partagés inspectés.
- [x] Fondations de couleur et thèmes inventoriées.
- [x] Déclaration et chargement de police vérifiés dans les fichiers inspectés.
- [x] Tailles des boutons et textes partagés relevées dans le code.
- [x] Navigation, routes et gabarit responsive inventoriés.
- [x] Outils de tests déclarés dans le dépôt inventoriés.
- [ ] Captures réelles de l'application desktop/mobile.
- [ ] Vérification navigateur de la police calculée et des ressources chargées.
- [ ] Mesures réelles de contraste et inspection clavier/lecteur d'écran.
- [ ] Exécution locale typecheck, tests et build.

## 8. Conclusion et décision

L'inventaire source est terminé et révèle une base déjà fonctionnelle (thèmes clair/sombre, navigation responsive, composants partagés, lecteur progressif), mais les captures et mesures navigateur restent à compléter.

**Lot 0 : partiellement terminé.** La partie code/inventaire est validée ; la référence visuelle réelle reste bloquée par l'absence d'accès navigateur à l'application authentifiée.

**Aucune modification applicative n'a été faite.** Les seuls changements de ce lot sont ce rapport de référence et son lien dans le README.

**Étape suivante après validation :** compléter les captures réelles, puis ouvrir le Lot 1 (tokens et fondations du Design System), avec tests de non-régression.
