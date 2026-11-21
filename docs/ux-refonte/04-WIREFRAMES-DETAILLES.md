# Wireframes fonctionnels détaillés — Amireflow Study OS

- **Date :** 21 novembre 2026
- **Branche :** `ux/audit-initial-2026-11-21`
- **Statut :** conception — à valider avant implémentation
- **Références :** `01-UX-AUDIT.md`, `02-INFORMATION-ARCHITECTURE.md`, `03-USER-FLOWS.md`

> Ce document définit la structure, l'ordre des éléments, les textes, les boutons, les comportements et les adaptations responsive. Ce ne sont pas des captures de l'application existante ni des maquettes graphiques finales. Les valeurs et contenus illustratifs sont des exemples à remplacer par les données réelles.

## 1. Règles générales de mise en page

### 1.1 Grille de contenu

- Largeur de lecture desktop : 1 120 à 1 240 px, centrée dans l'espace disponible.
- La sidebar desktop occupe environ 232 à 248 px.
- La zone de contenu ne doit pas être étirée sans raison sur un écran très large.
- Une colonne de lecture pédagogique ou conversationnelle reste plus étroite que la zone globale.
- Deux colonnes sont utilisées seulement lorsque les informations sont complémentaires.
- Sur téléphone, les pages sont mono-colonne, avec des actions prioritaires accessibles sans devoir parcourir des sections secondaires.

### 1.2 En-tête standard

Ordre desktop :
1. Breadcrumb uniquement si la page possède une profondeur.
2. Titre de page.
3. Description utile, non tronquée.
4. Action principale alignée à droite.
5. Actions secondaires dans un menu ou une zone secondaire.

Ordre mobile :
1. Breadcrumb compact si utile.
2. Titre.
3. Description sur plusieurs lignes.
4. Action principale pleine largeur ou facilement accessible.
5. Actions secondaires sous forme de menu.

Ne pas répéter le titre dans un badge et un autre titre. Ne pas afficher plusieurs titres H1.

### 1.3 Règles de hiérarchie

- Une zone fonctionnelle a une action principale visuellement dominante au maximum.
- Une page peut avoir une action principale dans son en-tête et une autre dans un formulaire modal, mais elles ne doivent pas être concurrentes à l'écran.
- Le statut, la date et les métadonnées restent visuellement secondaires.
- Les cartes ne sont utilisées que pour regrouper un sujet cohérent.
- Les grandes statistiques ne précèdent pas le contenu qui aide à agir.
- Un contenu long doit être développé et lisible ; pas de troncature systématique.
- Les actions doivent être proches des éléments qu'elles modifient.

### 1.4 Règles responsive

| Largeur indicative | Disposition |
|---|---|
| 320–639 px | Une colonne, navigation inférieure, menus en sheet/drawer |
| 640–767 px | Une colonne avec espacements adaptés |
| 768–1023 px | Deux colonnes uniquement si chaque colonne garde une largeur lisible |
| 1024–1279 px | Sidebar compacte ou complète selon l'espace, contenu organisé |
| 1280 px et plus | Sidebar persistante, contenu centré, grilles 8/4 ou 7/5 si pertinentes |

Les breakpoints doivent être ajustés en fonction du contenu réel, pas uniquement de ces valeurs.

## 2. Shell global et navigation

### Desktop — structure

```text
┌──────────────────────┬─────────────────────────────────────────────────────┐
│ AMIREFLOW STUDY OS   │                                                     │
│                      │  [Breadcrumb si nécessaire]                        │
│  ● Accueil           │  Titre de page                       [Action primaire]│
│  ○ Apprentissage     │  Description claire                                 │
│    Mes cours         │                                                     │
│    Parcours          │  ┌───────────────────────────────────────────────┐  │
│    Compétences       │  │                                               │  │
│  ○ Organisation      │  │                CONTENU                       │  │
│    Planning          │  │                                               │  │
│    Tâches            │  │                                               │  │
│    Séances           │  └───────────────────────────────────────────────┘  │
│  ○ Objectifs & projets│                                                     │
│  ○ Copilote IA       │                                                     │
│                      │                                                     │
│                      │                                                     │
│  Paramètres          │                                                     │
│  Profil / Déconnexion│                                                     │
└──────────────────────┴─────────────────────────────────────────────────────┘
```

### Mobile — structure

```text
┌────────────────────────────────────┐
│ [Logo] Amireflow             [Menu]│
├────────────────────────────────────┤
│ [Sous-section si nécessaire]       │
│ Titre de page                      │
│ Description                        │
│ [Action principale]                │
│                                    │
│ Contenu principal                  │
│                                    │
│                                    │
│                                    │
├────────────────────────────────────┤
│ Accueil Apprendre Organiser Projets│
│                     Copilote       │
└────────────────────────────────────┘
```

### Comportements

- La navigation principale desktop est persistante.
- La navigation mobile inférieure expose cinq rubriques : Accueil, Apprendre, Organiser, Projets, IA.
- Organisation affiche une sous-navigation Planning / Tâches / Séances.
- Apprentissage affiche une sous-navigation Mes cours / Parcours / Compétences.
- La rubrique active est visible par forme, contraste et libellé, pas uniquement par couleur.
- Un minuteur de séance actif peut apparaître sous le header ou au-dessus de la navigation inférieure. Il ne doit pas recouvrir le contenu ni les actions.
- Les paramètres et l'installation PWA restent dans un menu secondaire.
- Le menu mobile met le focus sur le dialogue, ferme par Échap, puis restaure le focus sur son déclencheur.

## 3. Connexion — `/login`

### Objectif
Permettre de se connecter ou de créer un compte sans distraction.

### Desktop

```text
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│                    AMIREFLOW STUDY OS                          │
│              Votre espace d'apprentissage personnel            │
│                                                               │
│             ┌─────────────────────────────────┐               │
│             │ [Se connecter] [Créer un compte] │               │
│             │                                 │               │
│             │ Adresse e-mail                  │               │
│             │ [____________________________]  │               │
│             │ Mot de passe                    │               │
│             │ [________________________] [œil]│               │
│             │                                 │               │
│             │ [             Se connecter    ] │               │
│             │                                 │               │
│             │ Mot de passe oublié ?           │               │
│             └─────────────────────────────────┘               │
└───────────────────────────────────────────────────────────────┘
```

### Textes
- Titre : **« Bienvenue dans StudyOS »**
- Description : « Retrouvez votre espace de travail et poursuivez votre progression. »
- Onglets : « Se connecter », « Créer un compte »
- Champs : « Adresse e-mail », « Mot de passe »
- CTA : « Se connecter »
- Inscription : « Créer mon compte »
- Erreur : expliquer le problème sans révéler si un compte existe lorsque cela pourrait exposer une information privée.

### Mobile
- Carte pleine largeur avec marges latérales.
- Champs sur une colonne.
- CTA pleine largeur.
- Clavier mobile adapté au type de champ.
- Aucun scroll horizontal.

### Validation
- Labels persistants, pas de placeholder utilisé comme seul label.
- Erreurs reliées au champ correspondant.
- Mot de passe masqué par défaut, bascule accessible.
- État de chargement et prévention des doubles soumissions.

## 4. Accueil — `/`

### Objectif
Faire comprendre immédiatement quoi faire aujourd'hui.

### Desktop

```text
┌───────────────────────────────────────────────────────────────────┐
│ Votre journée · Samedi 21 novembre                [Nouvelle tâche]│
│ Voici ce qui mérite votre attention aujourd'hui.      [Copilote]  │
├────────────────────────────────────────────┬──────────────────────┤
│ PRIORITÉ PRINCIPALE                         │ SÉANCE ACTIVE        │
│ Terminer le module React                    │ [Reprendre]          │
│ Résultat attendu : réaliser un composant    ├──────────────────────┤
│ pratique fonctionnel.                       │ PROCHAINS CRÉNEAUX   │
│ [Commencer ma séance]                       │ 14:00 React          │
├────────────────────────────────────────────┤ 16:00 Révision       │
│ PROCHAINES ACTIONS                          │ [Voir mon planning]  │
│ 1. Réviser les composants                   ├──────────────────────┤
│ 2. Réaliser l'exercice                      │ CETTE SEMAINE       │
│ 3. Documenter le résultat                   │ 3 séances achevées  │
│ [Voir toutes mes tâches]                    │ 2 preuves ajoutées  │
├────────────────────────────────────────────┴──────────────────────┤
│ RÉSULTATS RÉCENTS                                                  │
│ Dernière séance · Livrable · Compétence travaillée                 │
├───────────────────────────────────────────────────────────────────┤
│ BRIEFING DU COPILOTE (repliable ou secondaire)                     │
└───────────────────────────────────────────────────────────────────┘
```

### Ordre exact

1. En-tête : « Votre journée », date locale, description.
2. Boutons secondaires : « Nouvelle tâche », « Copilote ».
3. Carte Priorité principale.
4. Si une séance existe : bandeau ou mini-carte « Séance en cours » avec « Reprendre ma séance » et « Terminer la séance ».
5. Bloc « Prochaines actions » limité à trois.
6. Bloc « Prochains créneaux ».
7. Bloc « Résultats récents » et progression réelle.
8. Briefing IA et autres indicateurs secondaires.

La carte priorité peut occuper 7 à 8 colonnes et les créneaux 4 à 5 colonnes. La disposition doit respecter l'ordre de lecture et ne pas créer deux cartes visuellement concurrentes.

### Mobile

```text
┌────────────────────────────────┐
│ Votre journée                  │
│ Samedi 21 novembre             │
│                                │
│ ┌────────────────────────────┐ │
│ │ PRIORITÉ PRINCIPALE        │ │
│ │ Terminer le module React   │ │
│ │ Résultat : exercice livré  │ │
│ │ [Commencer ma séance]      │ │
│ └────────────────────────────┘ │
│                                │
│ SÉANCE EN COURS (si présente)  │
│ [Reprendre ma séance]          │
│                                │
│ PROCHAINES ACTIONS             │
│ 1. Réviser les composants      │
│ 2. Réaliser un exercice        │
│ 3. Documenter le résultat      │
│ [Voir toutes mes tâches]       │
│                                │
│ PROCHAINS CRÉNEAUX             │
│ [Voir mon planning]            │
│                                │
│ RÉSULTATS RÉCENTS              │
└────────────────────────────────┘
```

### Textes et actions
- H1 : « Votre journée »
- Description : « Voici ce qui mérite votre attention aujourd'hui. »
- Titre de carte : « Priorité principale »
- CTA : « Commencer ma séance »
- Reprise : « Reprendre ma séance »
- Section : « Prochaines actions »
- Lien secondaire : « Voir toutes mes tâches »
- Section : « Prochains créneaux »
- Lien secondaire : « Voir mon planning »
- Section : « Résultats récents »

### États
- Sans priorité : « Définissons votre priorité » + « Choisir ma priorité ».
- Sans tâche : « Vous n'avez pas encore de tâche active » + « Créer une tâche ».
- Sans planning : « Aucun créneau prévu aujourd'hui » + « Organiser ma journée ».
- Séance active : montrer la reprise avant une nouvelle création.
- Données partiellement disponibles : présenter les sections connues et signaler les sections non chargées.

## 5. Apprentissage — Mes cours — `/courses`

### Objectif
Reprendre rapidement un apprentissage ou trouver un cours.

### Desktop

```text
┌───────────────────────────────────────────────────────────────────┐
│ APPRENTISSAGE   Mes cours | Parcours | Compétences                 │
├───────────────────────────────────────────────────────────────────┤
│ Mes cours                                           [Créer un cours]│
│ Reprenez un cours ou choisissez ce que vous souhaitez apprendre.   │
├───────────────────────────────────────────────────────────────────┤
│ REPRENDRE MON APPRENTISSAGE                                        │
│ Python · Niveau 1 · Prochaine leçon : Variables                    │
│ [Continuer le cours]                                               │
├───────────────────────────────────────────────────────────────────┤
│ [Rechercher un cours...] [Statut ▾] [Tri ▾]                        │
├───────────────────────────────────────────────────────────────────┤
│ COURS ACTIFS                                                       │
│ ┌────────────────────────┐  ┌────────────────────────┐             │
│ │ Python                 │  │ React                  │             │
│ │ Niveau 1               │  │ Niveau 2               │             │
│ │ Progression réelle     │  │ Progression réelle     │             │
│ │ [Continuer le cours]   │  │ [Continuer le cours]   │             │
│ └────────────────────────┘  └────────────────────────┘             │
│ AUTRES COURS                                                       │
└───────────────────────────────────────────────────────────────────┘
```

### Mobile
1. En-tête et action « Créer un cours ».
2. Carte « Reprendre mon apprentissage ».
3. Recherche.
4. Filtres dans un panneau compact.
5. Liste verticale de cours.
6. Chaque carte montre le prochain chapitre et un seul CTA.

### Texte
- H1 : « Mes cours »
- Description : « Reprenez un cours ou choisissez ce que vous souhaitez apprendre. »
- CTA : « Créer un cours »
- Carte reprise : « Reprendre mon apprentissage »
- Bouton : « Continuer le cours » ou « Découvrir le cours »
- Recherche : « Rechercher un cours ou un sujet… »

### Carte de cours
Ordre :
1. Titre du cours.
2. Description/objectif.
3. Badge du niveau actuel et statut.
4. Progression.
5. Prochaine leçon.
6. CTA.

Ne pas afficher trop de badges de domaine, langue et nombre de ressources au même niveau que le titre.

### État vide
- Titre : « Aucun cours pour le moment »
- Description : « Décrivez ce que vous souhaitez apprendre. Le Copilote préparera un cours progressif que vous pourrez examiner avant de le créer. »
- CTA : « Créer mon premier cours »
Ne pas démarrer automatiquement un cours d'exemple.

## 6. Création d'un cours — panneau ou parcours de création

### Objectif
Demander juste assez d'informations pour générer une proposition de cours pertinente.

### Écran initial
- Titre : « Créer un cours personnalisé »
- Description : « Indiquez ce que vous souhaitez maîtriser et pourquoi. »
- Champ principal : « Quel sujet souhaitez-vous apprendre ? »
- Champ optionnel : « Quel résultat voulez-vous atteindre ? »
- Niveau de départ : auto-évalué ou « Je ne sais pas ».
- Langue du cours : valeur par défaut issue des préférences.
- Options avancées repliées : nombre de niveaux, compétence liée et autres paramètres déjà supportés.

### Actions
- Principal : « Préparer mon cours »
- Secondaire : « Annuler »
- Après l'aperçu : « Créer ce cours »
- Ajustement : « Modifier ma demande »

### Aperçu
Présenter :
- Objectif final.
- Structure des niveaux.
- Premier niveau détaillé.
- Objectifs de chaque niveau.
- Leçons, exercices et projet.
- Ressources proposées.

Si la génération échoue, conserver les champs saisis et afficher l'erreur près de l'aperçu.

## 7. Détail d'un cours — `/courses/:courseId`

### Objectif
Comprendre le niveau actuel, les jalons restants et la prochaine leçon.

### Desktop

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Apprentissage / Mes cours / Python                                  │
│ Python                                         [Reprendre] [⋯]      │
│ Objectif : automatiser des tâches avec Python                       │
│ Niveau actuel : 1 sur 3 · En cours                                   │
├─────────────────────────────────────────────────────────────────────┤
│ NIVEAUX   [1 · Fondations] ─── [2 · Intermédiaire] ─── [3 · Avancé] │
├─────────────────────────────────────────────────────────────────────┤
│ Progression du niveau :                                              │
│ Leçons 3/6 · Exercice à réaliser · Projet à valider                 │
├─────────────────────────────────────────────────────────────────────┤
│ [Leçons] [Projet & validation] [Ressources]                         │
├────────────────────────────┬────────────────────────────────────────┤
│ PROGRAMME DU NIVEAU        │ CONTENU / REPRISE                      │
│ 01 Introduction            │ Votre prochaine étape                  │
│ 02 Variables               │ Comprendre les variables               │
│ 03 Conditions              │ Résumé court                           │
│ 04 Boucles                 │ [Continuer cette leçon]                 │
│ 05 Fonctions               │                                        │
│ 06 Mini-projet             │                                        │
└────────────────────────────┴────────────────────────────────────────┘
```

### Mobile
Ordre :
1. Retour « Mes cours ».
2. Titre, niveau et statut.
3. CTA « Continuer le cours ».
4. Sélecteur de niveau horizontal, accessible au toucher.
5. Progression des jalons.
6. Onglets Leçons / Projet / Ressources.
7. Liste des leçons.
8. Détail de la leçon sélectionnée.

Le menu des leçons peut être présenté en drawer ou en accordéon pour éviter une colonne latérale trop étroite.

### Terminologie cible
- « Chapitres » peut devenir « Leçons » dans la navigation du cours, si le modèle contient bien des unités pédagogiques.
- « Projet & validation » reste explicite.
- « Docs & vidéos » devient « Ressources » ; la liste distingue ensuite les types.
- Ne jamais appeler un niveau « terminé » si le verrou pédagogique exige encore une preuve.

### Actions
- Principal : « Continuer le cours ».
- Secondaire : « Revoir le programme ».
- Actions avancées : « Mettre en pause », « Régénérer le niveau » (menu secondaire, avec explication des effets).

## 8. Lecture d'une leçon

### Objectif
Offrir une expérience de lecture confortable qui favorise la compréhension.

### Desktop
- Colonne de lecture : 680 à 780 px.
- Colonne latérale facultative : plan du chapitre et progression ; elle ne doit pas réduire la largeur du texte.
- En-tête du chapitre au-dessus du contenu.
- Progression du chapitre sous le titre.
- Contenu pédagogique dans le flux central.
- Exemples de code séparés et lisibles.
- Tuteur contextuel accessible depuis le contenu.
- Navigation précédente/suivante à la fin.

### Wireframe

```text
┌───────────────────────────────────────────────────────────────────┐
│ Python / Niveau 1 / Leçon 2                       [Poser une question]│
│ Comprendre les variables                                           │
│ Découvrez comment stocker et réutiliser une valeur.                 │
│ Étape 2 sur 5  ━━━━━●━━━━━━━━                                       │
├───────────────────────────────────────────────────────────────────┤
│ OBJECTIF DE CETTE ÉTAPE                                             │
│ Comprendre comment déclarer une variable.                           │
│                                                                     │
│ EXPLICATION                                                        │
│ Texte pédagogique complet, paragraphes aérés, titres et listes.     │
│                                                                     │
│ EXEMPLE COMMENTÉ                                                   │
│ ┌───────────────────────────────────────────────────────────────┐  │
│ │ nom = "Amireflow"                                             │  │
│ │ age = 22                                                      │  │
│ └───────────────────────────────────────────────────────────────┘  │
│ Explication de chaque ligne et résultat attendu.                    │
│                                                                     │
│ [Étape précédente]                    [J'ai compris, étape suivante]│
├───────────────────────────────────────────────────────────────────┤
│ Chapitre précédent                                      Chap. suivant│
└───────────────────────────────────────────────────────────────────┘
```

### Textes et boutons
- Titre : titre réel de la leçon.
- Progression : « Étape 2 sur 5 ».
- CTA principal : « J'ai compris, étape suivante ».
- Action secondaire : « Étape précédente ».
- Action de déploiement : « Afficher toute la leçon » au lieu de « Tout afficher ».
- Tuteur : « Poser une question au tuteur ».

### Mobile
- Une seule colonne.
- Largeur de texte adaptée.
- Code scrollable horizontalement si nécessaire, sans faire défiler toute la page.
- Barre de progression visible.
- Actions précédentes/suivantes placées en bas du bloc d'étape, sur une ou deux lignes.
- Le tuteur s'ouvre en panneau plein écran ou en section dédiée.
- Garder un accès au cours et à la progression.

### Comportements
- Ne pas marquer automatiquement la leçon comme comprise au simple scroll.
- La progression d'étape doit refléter le vrai état du lecteur.
- Ne pas masquer l'action de passer à l'exercice après la dernière étape.

## 9. Exercice

### Objectif
Permettre de comprendre l'énoncé, d'essayer, de demander un indice et de soumettre une réponse.

### Structure
1. Titre et difficulté.
2. Objectif de l'exercice.
3. Énoncé.
4. Contraintes et résultat attendu.
5. Indices progressifs.
6. Champs de réponse ou code.
7. Bouton de soumission.
8. Correction et historique des tentatives.

### Libellés
- « Afficher un indice »
- « Soumettre ma réponse »
- « Corriger mon exercice » uniquement si c'est réellement le libellé métier de l'action existante et non une fausse correction instantanée.
- « Réessayer »
- « Voir les critères de réussite »

### Après soumission
La correction affiche :
- Résultat : « Réussi », « À retravailler » ou « En attente de revue ».
- Score seulement si le backend l'a réellement calculé.
- Points réussis.
- Erreurs et explications.
- Conseils et prochaine étape.

### Mobile
- Énoncé avant les champs.
- Zone de code adaptée, clavier et orientation pris en compte.
- CTA de soumission visible à la fin du formulaire.
- Les indices restent repliés jusqu'à la demande de l'utilisateur.

## 10. Projet et validation de niveau

### Objectif
Présenter clairement ce qu'il faut livrer et comment le résultat sera évalué.

Ordre :
1. Statut de déblocage.
2. Titre du projet.
3. Brief et objectif.
4. Livrables attendus.
5. Critères d'évaluation et seuil.
6. Formulaire de soumission.
7. Historique des tentatives et corrections.

### Boutons
- Principal : « Soumettre mon projet ».
- Secondaire : « Enregistrer comme brouillon » uniquement si la persistance brouillon existe ; sinon ne pas l'afficher.
- Tertiaire : « Voir le barème ».

Avant soumission, préciser les éléments envoyés (texte, code, URL) et le fait qu'une revue manuelle peut être nécessaire.

## 11. Parcours — `/learning`

### Objectif
Donner une vue transversale des parcours d'apprentissage qui ne sont pas seulement des cours structurés.

### Structure
1. Sous-navigation Apprentissage.
2. Titre : « Mes parcours ».
3. Description : « Organisez les compétences et objectifs que vous souhaitez développer. »
4. Carte du parcours actif principal.
5. Recherche et filtres.
6. Liste des parcours.
7. Dans chaque parcours : modules, leçons, prochaine action et progression.

### Actions
- Principal : « Créer un parcours ».
- Carte active : « Reprendre le parcours ».
- Actions secondaires au niveau d'un module : « Ajouter une leçon », « Modifier le module » selon les opérations réellement disponibles.

Ne pas dupliquer artificiellement les cours déjà gérés dans le catalogue des cours. Un lien vers le cours correspondant doit clarifier la relation si les objets sont liés.

## 12. Compétences — `/skills`

### Objectif
Comprendre ce qui est maîtrisé, ce qui manque et quelles preuves existent.

### Structure
1. Sous-navigation Apprentissage.
2. Titre : « Mes compétences ».
3. Description : « Évaluez vos acquis à partir d'exercices, de projets et de réalisations concrètes. »
4. Bandeau discret : « Une compétence progresse sur la base de preuves, pas seulement du temps passé. »
5. Filtres par domaine et état pédagogique.
6. Liste groupée par domaine.
7. Carte de compétence.

### Carte
- Nom.
- Niveau actuel et niveau cible avec libellés.
- Preuves associées.
- Date de dernière évaluation.
- État : à évaluer, en progression, étayée ou validée selon les états métier disponibles.
- Bouton principal : « Évaluer cette compétence » ou « Ajouter une preuve » selon le contexte.
- Menu secondaire : historique, modification.

Ne pas employer seulement « 3/5 » sans expliquer ce que représente le niveau 3.

## 13. Organisation — Planning — `/planning`

### Objectif
Consulter et modifier facilement le temps planifié.

### Desktop

```text
┌───────────────────────────────────────────────────────────────────┐
│ ORGANISATION   Planning | Tâches | Séances                         │
├───────────────────────────────────────────────────────────────────┤
│ Mon planning                                     [Générer un planning]│
│ Consultez votre semaine et ajustez vos créneaux.      [Ajouter un créneau]│
├───────────────────────────────────────────────────────────────────┤
│ [‹] [Cette semaine] [›]         16–22 novembre      [Agenda] [Grille]│
├───────────────────────────────────────────────────────────────────┤
│ LUN 16  MAR 17  MER 18  JEU 19  VEN 20  SAM 21  DIM 22             │
├───────────────────────────────────────────────────────────────────┤
│ 09:00  Cours universitaire                                        │
│ 11:00  Révision Java                                               │
│ 14:00  Apprentissage React                                        │
│ 16:00  Temps personnel                                            │
├───────────────────────────────────────────────────────────────────┤
│ RÉSUMÉ                                                            │
│ Temps planifié · Conflits détectés · Répartition des activités      │
└───────────────────────────────────────────────────────────────────┘
```

### Actions et hiérarchie
- Principal : « Générer un planning » si aucune proposition n'est en cours.
- Secondaire : « Ajouter un créneau ».
- Menu secondaire : « Importer mon emploi du temps », « Dupliquer la semaine ».
- Navigation période : « Semaine précédente », « Cette semaine », « Semaine suivante ».
- Bascule de vue : « Agenda », « Grille ».

### Mobile
- Vue Agenda par défaut.
- Sélecteur de jour horizontal.
- Créneaux en liste chronologique.
- Bouton principal accessible : « Ajouter un créneau » ou « Générer un planning » selon le contexte.
- La grille hebdomadaire complète n'est pas imposée sur petit écran.
- Les filtres sont repliés dans un panneau dédié.
- Un conflit s'explique dans la carte du créneau, pas seulement par un point coloré.

### États
- Aucun créneau : « Votre planning est encore vide » + « Ajouter un créneau » et « Générer un planning ».
- Conflit : noms et horaires des deux événements concernés.
- Événement annulé : statut explicite.
- Semaine sans événement après filtre : proposer de retirer le filtre.

## 14. Génération intelligente du planning

### Objectif
Faire progresser l'utilisateur d'une vérification de contexte à une proposition compréhensible puis à une application confirmée.

### Stepper desktop et mobile
- Étape 1 : « Vérifier mes disponibilités »
- Étape 2 : « Définir mes préférences »
- Étape 3 : « Examiner le planning »

### Étape 1 — Vérifier mes disponibilités
Zone principale :
- Emploi du temps fixe reconnu.
- Disponibilités confirmées.
- Indisponibilités.
- Temps de récupération.
- Objectifs et cours actifs.

Actions :
- Principal : « Continuer »
- Secondaire : « Modifier mes disponibilités »

Les règles récurrentes sont présentées comme une liste lisible. L'ajout d'une règle est un formulaire secondaire, pas le premier élément de l'écran.

### Étape 2 — Définir mes préférences
- Horizon : 7 ou 14 jours.
- Focus facultatif.
- Budget hebdomadaire facultatif, avec indication de la valeur utilisée actuellement.
- Consigne libre facultative, exemple : « Allège les séances du mercredi ».

Actions :
- Principal : « Générer mon planning »
- Secondaire : « Retour »

### Étape 3 — Examiner le planning
Afficher :
1. « Proposition de planning » et numéro de version.
2. Résumé des heures et créneaux.
3. Calendrier proposé.
4. Raisons des choix et contraintes respectées.
5. Conflits, hypothèses et données manquantes.
6. Différence par rapport à la version actuellement appliquée.

Actions :
- Principal : « Appliquer ce planning »
- Secondaire : « Ajuster le planning »
- Tertiaire/destructif : « Refuser la proposition »

Un texte de confirmation doit résumer l'effet de l'application sur le calendrier avant la mutation si des créneaux futurs existants sont concernés.

### Ajustement en langage naturel
Champ : « Que souhaitez-vous modifier ? »
Exemple : « Réduis les séances à 45 minutes et garde le dimanche libre. »
Bouton : « Recalculer le planning ».

L'historique des versions et la restauration se trouvent dans une section secondaire « Historique des propositions ».

## 15. Organisation — Tâches — `/tasks`

### Objectif
Afficher une liste exploitable de tâches, avec une capture rapide.

### Desktop
1. Sous-navigation Organisation.
2. Titre « Mes tâches » et description.
3. CTA « Nouvelle tâche ».
4. Champ capture rapide : « Ajouter une action à faire… ».
5. Priorité par défaut claire, modifiable.
6. Recherche et filtres.
7. Liste groupée : En cours, À faire, Parking, Terminées.
8. Bascule Liste / Tableau en action secondaire.

Ne pas placer quatre KPI volumineux au-dessus de la liste. Les compteurs peuvent être compacts, cliquables uniquement s'ils filtrent réellement.

### Mobile
- Titre et CTA.
- Capture rapide avec bouton d'ajout.
- Filtres accessibles depuis un bouton « Filtrer ».
- Liste simple et chronologique.
- Carte de tâche sur une colonne.
- Menu secondaire pour modifier, déplacer vers Parking ou supprimer.

### Libellés
- H1 : « Mes tâches »
- Description : « Gardez une vue claire sur ce qui reste à faire et ce qui avance. »
- CTA : « Nouvelle tâche »
- Capture rapide : « Ajouter une action à faire… »
- Filtres : « Statut », « Priorité », « Échéance »
- Parking : « Mettre au parking »
- Statut : « Marquer comme terminée »
- Suppression : « Supprimer la tâche »

### Formulaire complet
Ordre :
1. « Intitulé de la tâche » — obligatoire.
2. « Pourquoi cette tâche est-elle importante ? » — description facultative.
3. « Priorité ».
4. « Échéance ».
5. « Associer à un cours ou projet ».
6. « Statut » si nécessaire en modification.
7. Boutons : « Enregistrer la tâche », « Annuler ».

Les champs facultatifs sont repliables si le formulaire devient trop long.

## 16. Organisation — Séances — `/sessions`

### Objectif
Démarrer, retrouver et clôturer les séances de travail.

### Structure
1. Sous-navigation Organisation.
2. H1 « Mes séances ».
3. Description : « Enregistrez le travail réalisé et les résultats obtenus. »
4. Si une séance est active, la carte active apparaît en premier.
5. CTA « Démarrer une séance ».
6. Action secondaire « Enregistrer une séance passée ».
7. Historique chronologique.
8. Filtres de l'historique en panneau compact.

### Carte active
- Sujet.
- Contexte lié.
- Minuteur.
- Heure de début.
- Action : « Reprendre ma séance » si la page a été quittée.
- Action principale : « Terminer la séance ».

### Clôture
Titre : « Quel résultat avez-vous obtenu ? »
Champs :
- « Travail réalisé ».
- « Livrable ou preuve obtenue ».
- « Difficulté rencontrée ».
- « Prochaine étape ».
CTA : « Enregistrer le bilan ».

Ne pas obliger à remplir quatre champs si le bilan peut être enregistré avec un résultat bref. Les champs facultatifs restent clairement indiqués.

## 17. Objectifs & projets — `/projects`

### Objectif
Distinguer les objectifs personnels et les projets actifs, tout en rendant la prochaine action évidente.

### Structure desktop
1. H1 « Objectifs et projets ».
2. Description : « Suivez les résultats que vous voulez atteindre et les projets que vous faites avancer. »
3. Action principale : « Nouveau projet ».
4. Action secondaire : « Nouvel objectif ».
5. Action Copilote : « Décrire mon objectif à l'IA » dans une hiérarchie tertiaire.
6. Vue de synthèse des objectifs personnels.
7. Section « Objectifs personnels ».
8. Section « Projets actifs ».
9. Filtres et recherche dans les sections concernées.
10. Cartes de projets.

### Carte projet
Ordre :
- Nom du projet.
- Résultat attendu.
- Statut.
- Prochaine action.
- Échéance si disponible.
- Progression fondée sur les tâches/livrables réellement enregistrés.
- Bouton « Ouvrir le projet ».

Les limites métier de projets actifs ne sont pas supprimées ; elles sont expliquées au moment de l'action qui les déclenche.

### Mobile
- Actions principales sous le titre.
- Objectifs et projets sous forme de sections repliables ou de tabs si cela réduit réellement la charge.
- Une carte par ligne.
- Prochaine action visible sans devoir ouvrir le détail.

## 18. Copilote IA — `/ai-coach`

### Objectif
Faire de la conversation l'entrée principale. L'historique, la mémoire, les outils et les rapports sont secondaires.

### Desktop

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Copilote IA                   [Nouvelle conversation] [Historique]   │
│ Votre assistant pour apprendre, organiser et avancer.                │
├─────────────────────────────────────────────────┬────────────────────┤
│ CONVERSATION                                    │ ACTIONS             │
│                                                 │                    │
│ Bonjour. Que souhaitez-vous faire ?             │ Propositions (2)   │
│                                                 │ ┌────────────────┐ │
│ [Planifier ma semaine] [Comprendre un cours]    │ │ Proposition     │ │
│                                                 │ │ Détails         │ │
│ Message utilisateur                             │ │ [Accepter]      │ │
│ Réponse structurée du Copilote                  │ │ [Modifier]      │ │
│                                                 │ │ [Refuser]       │ │
│                                                 │ └────────────────┘ │
│                                                 │                    │
│                                                 │ Synthèses          │
├─────────────────────────────────────────────────┴────────────────────┤
│ Contexte utilisé : Planning · Tâches · Cours        [Voir le contexte]│
│ [Écrivez votre demande…]                            [Envoyer]         │
└──────────────────────────────────────────────────────────────────────┘
```

### Organisation desktop
- Zone conversation principale : environ 68–72 %.
- Panneau secondaire : environ 28–32 %, repliable.
- Historique accessible depuis un bouton, pas toujours affiché.
- Mémoire et outils dans des réglages secondaires.
- Le panneau secondaire n'écrase pas la largeur de lecture.

### Mobile
- Conversation plein écran.
- En-tête compact avec titre, nouvelle conversation et accès à l'historique.
- Le panneau Actions peut être une vue secondaire.
- Les propositions importantes peuvent être intégrées directement dans le fil.
- Le champ de saisie reste au bas de la zone disponible et respecte la safe area.
- Le contexte automatique est indiqué de manière discrète, pas via un sélecteur dominant.

### Textes
- H1 : « Copilote IA »
- Description : « Décrivez votre besoin. Le Copilote s'appuie sur votre contexte pour vous aider à avancer. »
- Placeholder : « Que souhaitez-vous apprendre, organiser ou améliorer ? »
- CTA : « Envoyer »
- Nouvelle conversation : « Nouvelle conversation »
- Context label : « Contexte utilisé »
- Proposition : « Action proposée »
- Boutons : « Accepter cette proposition », « Modifier », « Refuser »

### Conversation vide
Présenter au maximum trois amorces :
- « Organiser ma journée »
- « Reprendre mon apprentissage »
- « Faire le point sur mes priorités »

Ne pas montrer six cartes d'amorces en permanence.

### Propositions
Chaque carte affiche :
1. Action proposée.
2. Pourquoi cette action.
3. Données et contraintes prises en compte.
4. Changements concrets.
5. Conséquences et risques.
6. Actions.

Les propositions de planification doivent préciser si elles ajoutent, déplacent ou remplacent des créneaux.

### Outils, mémoire et synthèses
- Outils : panneau « Capacités et autorisations ».
- Mémoire : page ou panneau « Ce que le Copilote sait de mes préférences ».
- Synthèses : briefing du jour et bilan hebdomadaire.
- Historique : conversations précédentes.
Ces fonctions sont conservées, mais ne concurrencent pas la saisie d'un message ordinaire.

## 19. Paramètres — `/settings`

### Objectif
Rendre les préférences compréhensibles et éviter un long formulaire mélangeant tous les domaines.

### Desktop
- Titre « Paramètres » et description.
- Navigation secondaire à gauche : Profil, Préférences, Disponibilités, Copilote IA, Apparence, Sécurité.
- Contenu de la section choisie à droite.
- Bouton « Enregistrer les modifications » en fin de section ou barre sticky uniquement si nécessaire.

### Mobile
- Écran d'index avec les catégories.
- Chaque catégorie ouvre un écran dédié avec bouton retour.
- Bouton d'enregistrement visible sans recouvrir les champs.
- Avertissement avant de quitter si des modifications non enregistrées seraient perdues.

### Groupes
- Profil : nom et fuseau horaire.
- Préférences : langue et options utilisateur disponibles.
- Disponibilités : jours, heures, charge quotidienne.
- Copilote IA : consignes personnelles, fournisseur et modèles dans une section technique séparée.
- Apparence : thème.
- Sécurité : compte et session.

Le panneau de fournisseur IA ne doit pas afficher les secrets en clair après leur enregistrement. Les libellés doivent expliquer ce que change le fournisseur, sans exposer les détails techniques dans l'espace quotidien.

## 20. Page introuvable — `*`

- Titre : « Cette page est introuvable »
- Description : « Le lien est peut-être incorrect ou la page a été déplacée. »
- CTA principal : « Revenir à l'accueil »
- Lien secondaire : « Ouvrir le Copilote »
Aucun bouton ne doit être décoratif ou inactif.

## 21. Matrice commune des actions

| Contexte | Action principale | Action secondaire | Action tertiaire |
|---|---|---|---|
| Accueil | Commencer ma séance | Nouvelle tâche | Ouvrir le Copilote |
| Cours actifs | Continuer le cours | Voir le programme | Modifier le cours |
| Création de cours | Créer ce cours | Modifier ma demande | Annuler |
| Leçon | Étape suivante | Étape précédente | Poser une question |
| Exercice | Soumettre ma réponse | Afficher un indice | Voir les critères |
| Projet de niveau | Soumettre mon projet | Voir le barème | Consulter l'historique |
| Planning | Générer un planning | Ajouter un créneau | Importer / Dupliquer |
| Proposition de planning | Appliquer ce planning | Ajuster | Refuser |
| Tâches | Ajouter une tâche | Filtrer | Choisir la vue |
| Séance active | Terminer la séance | Reprendre | Consulter l'historique |
| Projet | Ouvrir le projet | Modifier | Suspendre / archiver selon les règles métier |
| Copilote | Envoyer | Nouvelle conversation | Historique |
| Paramètres | Enregistrer les modifications | Annuler les changements | Réinitialiser si disponible |

Cette matrice décrit la hiérarchie, pas l'obligation d'afficher toutes ces actions au même moment.

## 22. Spécification des formulaires et boutons

### Boutons
- Action principale : libellé orienté résultat, contraste principal.
- Secondaire : variante neutre ou contour, libellé précis.
- Tertiaire : lien ou bouton ghost, uniquement pour action facultative.
- Destructif : libellé explicite, confirmation proportionnée au risque.
- Icône seule : réservé aux actions compactes universellement reconnaissables ; ajouter un nom accessible et une infobulle si le sens n'est pas évident.

### États obligatoires
- Normal.
- Survol lorsque le dispositif le supporte.
- Focus visible.
- Pressé.
- Désactivé.
- Chargement.
- Succès/échec annoncé dans le contexte.

### Formulaires
- Label visible, persistant.
- Indiquer obligatoire ou facultatif.
- Exemple dans le placeholder uniquement comme aide, jamais comme label.
- Aide placée sous le champ.
- Erreur précise sous le champ.
- Préserver la saisie en cas d'échec.
- Groupes courts et ordre de saisie logique.
- Ne pas afficher d'options rares avant les champs utiles.

## 23. Spécification des états visuels par type d'écran

### Listes
- Chargement : skeleton de cartes alignées sur la structure finale.
- Vide : titre, cause, prochaine action.
- Aucun résultat de filtre : bouton « Effacer les filtres ».
- Erreur : message local et « Réessayer ».
- Succès : confirmation non bloquante.

### Calendrier
- Chargement de semaine.
- Semaine vide.
- Conflit.
- Créneau en cours ou terminé.
- Proposition IA non appliquée.
- Planning appliqué.

### Apprentissage
- Cours en préparation.
- Aperçu généré.
- Génération échouée.
- Niveau verrouillé et raison.
- Leçon en cours.
- Exercice soumis.
- Correction en attente.
- Projet validé ou à retravailler.

### Copilote
- Conversation vide.
- Envoi en cours.
- Réponse en cours.
- Réponse disponible.
- Contexte partiel.
- Proposition en attente.
- Action exécutée.
- Action refusée.
- Action échouée.

## 24. Règles de contenu et de lisibilité

- Texte courant : viser 16 px.
- Texte secondaire essentiel : viser 14 px.
- Métadonnées uniquement : 12–13 px si le contraste reste suffisant.
- Contenu pédagogique : 16 px minimum, interligne confortable et largeur de ligne adaptée.
- Titres : hiérarchie stable ; un seul H1 par page.
- Paragraphes : éviter les blocs trop longs sans sous-titres.
- Code : police monospace lisible, taille adaptée et défilement local si nécessaire.
- Descriptions de page : ne pas tronquer sans raison.
- Boutons : verbes d'action et résultats explicites.
- Notifications : décrire le résultat réel.
- Erreurs : expliquer ce qui a échoué et comment récupérer.
- États vides : proposer une seule action principale.

## 25. Contrôles visuels à réaliser sur chaque wireframe implémenté

- [ ] Le premier écran visible présente la priorité de la page.
- [ ] Le titre répond à « Où suis-je ? ».
- [ ] La description explique l'utilité sans paraphraser le titre.
- [ ] Le bouton principal est identifiable en moins d'un regard.
- [ ] Les actions secondaires ne rivalisent pas avec la principale.
- [ ] Le positionnement suit l'ordre de lecture naturel.
- [ ] Les champs sont visibles et leurs labels restent lisibles.
- [ ] Aucun texte utile n'est tronqué.
- [ ] Les zones tactiles sont suffisamment grandes.
- [ ] Les états focus, hover, disabled et loading sont conçus.
- [ ] Le contenu tient à 320 px sans défilement horizontal global.
- [ ] La version desktop n'étire pas excessivement les lignes de texte.
- [ ] Les états vides, chargements et erreurs ont leur propre composition.
- [ ] Les données montrées sont réelles ou clairement signalées comme exemple.

## 26. Décisions à préserver pendant l'implémentation

1. Ne pas créer de données d'exemple dans les environnements utilisateur.
2. Ne pas inventer de KPI ou de progression.
3. Ne pas réduire le contenu pédagogique pour gagner artificiellement de la place.
4. Ne pas masquer une option importante dans un menu trop profond.
5. Ne pas afficher tous les paramètres d'un moteur IA sur la page de conversation.
6. Ne pas remplacer une vraie action par une simple notification visuelle.
7. Ne pas supprimer l'historique ou les propositions pour simplifier le Copilote.
8. Ne pas appliquer automatiquement un planning généré.
9. Ne pas laisser une leçon consultée valider une compétence sans preuve.
10. Ne pas commencer la migration du code avant validation du présent dossier.

## 27. Critères de validation de la phase wireframes

- [ ] Les écrans de chaque route sont couverts.
- [ ] Les dispositions desktop et mobile sont définies.
- [ ] Les textes H1, descriptions, CTA et formulaires sont proposés.
- [ ] Les actions principales, secondaires et tertiaires sont identifiées.
- [ ] Les états vides, chargements, erreurs et succès sont documentés.
- [ ] Les parcours de création de cours et de planification respectent les capacités existantes.
- [ ] Le parcours pédagogique conserve les verrous et validations métier.
- [ ] Les routes historiques sont préservées.
- [ ] Les wireframes ne requièrent aucune migration backend non justifiée.
- [ ] Une revue de conception humaine est réalisée avant l'implémentation.
