# Architecture de l'information et navigation — Amireflow Study OS

- **Date :** 21 novembre 2026
- **Dépôt :** `Amireflow/StudyOS`
- **Branche :** `ux/audit-initial-2026-11-21`
- **Statut :** proposition de conception — à valider avant implémentation
- **Référence :** `01-UX-AUDIT.md`

## 1. Décisions de conception

Cette architecture regroupe les écrans sans reconstruire le modèle métier.

- Les routes métier existantes sont conservées.
- Les pages proches partagent une navigation de section.
- Les anciennes URL restent accessibles et ne sont pas redirigées vers une page qui ferait perdre leur contexte.
- La navigation principale présente des espaces compréhensibles, pas la liste des tables ou des fonctions internes.
- Les pages spécialisées restent accessibles en profondeur.
- Aucun écran-hub vide n'est créé uniquement pour regrouper des liens.

## 2. Navigation principale cible

### Desktop — sidebar

Ordre proposé :

1. **Accueil** — `/`
2. **Apprentissage** — espace regroupant Cours, Parcours et Compétences ; entrée principale `/courses`
3. **Organisation** — espace regroupant Planning, Tâches et Séances ; entrée principale `/planning`
4. **Objectifs & projets** — `/projects`
5. **Copilote IA** — `/ai-coach`

En bas de la sidebar :
- Paramètres — `/settings`
- Profil et déconnexion
- Contrôle du thème, à conserver dans un emplacement stable et prévisible.

La sidebar conserve les états actif, survol, focus clavier et réduit. Lorsqu'elle est réduite, les icônes doivent disposer de noms accessibles et d'infobulles.

### Sous-navigation Apprentissage

La même sous-navigation doit être visible dans les pages appartenant à cet espace :

| Libellé | Route actuelle | Rôle |
|---|---|---|
| Mes cours | `/courses` | Catalogue et reprise des cours |
| Parcours | `/learning` | Parcours, modules et leçons transversaux |
| Compétences | `/skills` | Évaluations, preuves et maîtrise |

Sur la fiche d'un cours (`/courses/:courseId`), la sous-navigation générale reste discrète ou se replie au profit de la navigation du cours. Il ne faut pas afficher deux barres de navigation concurrentes.

La route Apprentissage principale ouvre Mes cours, car le cours structuré est actuellement le parcours pédagogique le plus complet.

### Sous-navigation Organisation

| Libellé | Route actuelle | Rôle |
|---|---|---|
| Planning | `/planning` | Agenda, grille, créneaux et programme intelligent |
| Tâches | `/tasks` | Actions à faire, en cours, parking et terminées |
| Séances | `/sessions` | Séance active, démarrage et historique |

Les trois pages doivent partager un même repère de section. Le passage de Planning à Tâches ou Séances doit être direct et préserver le filtre/contexte lorsque cela est raisonnable.

### Objectifs & projets

La route `/projects` conserve l'espace actuel réunissant objectifs personnels, plan unifié et projets. L'interface doit distinguer visuellement ces trois notions sans les éclater en destinations principales.

La route historique `/objectives` doit continuer à fonctionner. La décision entre conserver son alias ou rediriger vers `/projects` sera prise après vérification des liens internes et des éventuels liens externes ; aucune URL historique ne doit devenir une page 404.

### Copilote IA

Le Copilote conserve `/ai-coach`. L'historique, les propositions, les rapports, la mémoire et les outils sont des vues ou panneaux secondaires du Copilote, pas cinq destinations de navigation indépendantes.

### Paramètres

`/settings` reste dans le pied de la sidebar et dans le menu mobile. Les groupes de paramètres sont accessibles par navigation interne à la page, sans ajouter une multitude d'entrées à la navigation générale.

## 3. Mobile — navigation inférieure

Cinq entrées proposées :

| Position | Libellé | Route | Règle |
|---|---|---|---|
| 1 | Accueil | `/` | Point de départ |
| 2 | Apprendre | `/courses` | Reprendre un cours ou un parcours |
| 3 | Organiser | `/planning` | Planning avec accès direct à Tâches et Séances |
| 4 | Projets | `/projects` | Objectifs et projets actifs |
| 5 | IA | `/ai-coach` | Conversation |

Les pages Planning, Tâches et Séances afficheront une sous-navigation compacte commune. Les pages Cours, Parcours et Compétences feront de même. Cette organisation évite de sacrifier une destination mobile à forte valeur tout en gardant les cinq emplacements inférieurs.

Règles mobile :
- Barre inférieure fixe, respect des safe areas iOS.
- Libellé court toujours visible sous l'icône.
- État actif reconnaissable sans dépendre uniquement de la couleur.
- Cible tactile visée : 44 × 44 px au minimum pour l'action principale de navigation.
- Le menu secondaire donne accès aux Paramètres et aux options moins fréquentes.
- L'installation PWA ne doit pas concurrencer la navigation principale ; la conserver dans le menu secondaire ou dans un état d'installation pertinent.

## 4. Correspondance routes ↔ architecture cible

| Route actuelle | Espace cible | Sous-espace |
|---|---|---|
| `/login` | Authentification | Connexion / inscription |
| `/` | Accueil | Vue du jour |
| `/courses` | Apprentissage | Mes cours |
| `/courses/:courseId` | Apprentissage | Détail du cours |
| `/learning` | Apprentissage | Parcours |
| `/skills` | Apprentissage | Compétences |
| `/planning` | Organisation | Planning |
| `/tasks` | Organisation | Tâches |
| `/sessions` | Organisation | Séances |
| `/projects` | Objectifs & projets | Objectifs et projets |
| `/objectives` | Objectifs & projets | Alias historique |
| `/ai-coach` | Copilote IA | Conversation et outils secondaires |
| `/settings` | Paramètres | Préférences et configuration |
| `*` | Système | Page introuvable |

## 5. Règles de navigation et de comportement

1. Une seule destination principale est visuellement active à la fois.
2. Les routes imbriquées activent correctement leur parent : `/courses/:courseId` active Apprentissage ; `/tasks` et `/sessions` activent Organisation.
3. Un utilisateur peut ouvrir directement chaque ancienne URL, y compris depuis un favori.
4. Le fil d'Ariane est réservé aux profondeurs où il aide réellement, notamment le détail d'un cours et certaines vues de projet.
5. Un lien de navigation change de page ; une action modifie les données. Ne pas employer un bouton pour naviguer ni un lien pour exécuter une mutation.
6. Le retour navigateur doit fonctionner.
7. Sur mobile, changer de rubrique ferme le tiroir ou panneau ouvert et place le focus de façon prévisible.
8. Les menus et sous-menus sont utilisables au clavier et exposent correctement leur état accessible.
9. Les badges de nombre ne sont affichés que s'ils déclenchent une action ou signalent un élément important, par exemple des propositions IA en attente.
10. Les labels courts du mobile ne doivent pas rendre les concepts ambigus.

## 6. Principes de regroupement

- **Cours / Parcours / Compétences :** même intention utilisateur — apprendre et démontrer une maîtrise.
- **Planning / Tâches / Séances :** même intention — organiser et exécuter le travail.
- **Objectifs / Projets :** même intention — atteindre un résultat et livrer quelque chose.
- **Copilote / Historique / Propositions / Rapports :** même intention — demander de l'aide et examiner les actions proposées.
- **Paramètres :** espace transversal séparé du travail quotidien.

Le regroupement est d'abord navigationnel. Les stores, API, modèles et composants métier ne doivent pas être fusionnés automatiquement.

## 7. Critères d'acceptation

- [ ] Les cinq espaces principaux sont compréhensibles sans connaître le vocabulaire technique.
- [ ] Les pages de chaque section partagent une sous-navigation cohérente.
- [ ] La navigation mobile ne dépasse pas cinq entrées inférieures.
- [ ] Les anciennes routes restent fonctionnelles.
- [ ] Les routes imbriquées affichent le bon état actif.
- [ ] Le changement de page est accessible au clavier.
- [ ] Les tests de navigation sont mis à jour sans perdre les tests existants.
- [ ] Aucune fonctionnalité n'est supprimée au nom de la simplification.

## 8. Décision non négociable

Ne pas ajouter une page `/organization` ou un hub intermédiaire vide. `/planning` sert de première page de la section Organisation ; les sous-rubriques sont accessibles par la navigation de section commune.

Cette décision limite le périmètre de développement et préserve le travail déjà réalisé.
