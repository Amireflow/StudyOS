# Parcours utilisateurs — Amireflow Study OS

- **Date :** 21 novembre 2026
- **Branche :** `ux/audit-initial-2026-11-21`
- **Statut :** conception — à valider avant développement
- **Documents liés :** `01-UX-AUDIT.md`, `02-INFORMATION-ARCHITECTURE.md`

## 1. Méthode

Chaque parcours décrit :
- L'intention utilisateur.
- Le point d'entrée.
- Les préconditions.
- Le chemin nominal.
- Les décisions et variantes.
- Les retours de l'interface.
- Le résultat réel attendu.
- Les preuves de validation.

La réussite n'est pas mesurée au nombre de pages visitées. Elle se mesure à l'obtention du résultat attendu sans confusion ni action non voulue.

## 2. Parcours A — Ouvrir StudyOS et décider quoi faire

### Intention
Commencer une journée de travail en identifiant une action réaliste, sans refaire tout le planning.

### Point d'entrée
Route `/` — Accueil.

### Chemin nominal
1. L'utilisateur ouvre StudyOS.
2. L'en-tête affiche la date locale et un titre explicite : **« Votre journée »**.
3. Si une séance est déjà active, un bandeau persistant indique son sujet, sa durée et l'action **« Reprendre ma séance »**.
4. La carte Priorité principale affiche une seule priorité active.
5. Une action principale permet de commencer ou de reprendre le travail.
6. La zone Prochaine action affiche au maximum trois actions ordonnées.
7. L'agenda du jour indique les créneaux et les conflits éventuels.
8. Les résultats et les statistiques de progression apparaissent plus bas.

### Variantes
- **Aucune priorité définie :** titre « Définissons votre priorité » ; action « Choisir ma priorité ». Ne pas inventer une priorité à la place de l'utilisateur.
- **Aucune tâche active :** proposer « Créer une tâche » ou « Demander une recommandation au Copilote ».
- **Aucune donnée de planning :** indiquer « Votre journée n'est pas encore planifiée » et proposer d'ajouter un créneau ou d'ouvrir le planning.
- **Séance active :** ne pas créer une deuxième séance par inadvertance ; proposer de reprendre ou de terminer la séance existante.
- **Données en chargement :** conserver la structure de page avec skeletons.
- **Erreur de récupération :** garder les données déjà disponibles si possible et afficher une erreur localisée avec « Réessayer ».

### Résultat attendu
L'utilisateur sait quoi commencer et peut démarrer une séance sans traverser plusieurs pages.

### Critères de validation
- La priorité est visible avant les KPI.
- Le bouton principal décrit l'action.
- Une séance déjà active est impossible à manquer.
- Aucune statistique ou recommandation ne prétend refléter une donnée indisponible.

## 3. Parcours B — Reprendre un cours et progresser

### Intention
Reprendre un cours à l'endroit exact où l'utilisateur s'est arrêté et progresser par étapes.

### Point d'entrée
Accueil > carte Reprendre mon apprentissage, ou Apprentissage > Mes cours.

### Chemin nominal
1. La liste Mes cours affiche d'abord les cours actifs, puis les autres statuts.
2. Chaque carte montre le titre, l'objectif, le niveau courant, la progression réelle, la dernière activité et le prochain chapitre.
3. L'action principale est **« Continuer le cours »** pour un cours déjà commencé et **« Découvrir le cours »** pour un cours non commencé.
4. La fiche du cours présente le niveau actif et les jalons : chapitres, exercice, projet/validation.
5. L'utilisateur ouvre le prochain chapitre.
6. La lecture présente une seule étape explicative à la fois lorsque le contenu est découpé en étapes.
7. L'utilisateur peut afficher tout le contenu, revenir à l'étape précédente ou poser une question au tuteur.
8. Après la leçon, l'utilisateur passe à un exercice.
9. Il consulte l'énoncé, les contraintes et les critères de réussite.
10. Il peut demander un indice progressif avant de soumettre.
11. Il soumet sa réponse.
12. La correction explique ce qui est réussi, ce qui est incorrect et pourquoi.
13. L'utilisateur peut réessayer.
14. Après les chapitres et exercices requis, il ouvre le projet du niveau.
15. Il consulte les livrables et la grille d'évaluation.
16. Il soumet son projet.
17. La correction expose le score, les critères, les points à améliorer et l'étape suivante.
18. Si le seuil et les préconditions sont satisfaits, le niveau suivant est débloqué.
19. La progression de compétence est mise à jour uniquement par les preuves et validations prévues par les règles métier.

### Variantes
- **Niveau verrouillé :** expliquer clairement la condition exacte et fournir un lien vers l'action qui manque. Ne pas afficher un simple « Verrouillé » sans solution.
- **Leçon terminée :** proposer « Revoir la leçon » et « Passer à l'exercice ».
- **Exercice échoué :** conserver la tentative, expliquer les lacunes et proposer un indice ou une nouvelle tentative.
- **Correction en attente :** afficher l'état réel et ne pas annoncer une réussite.
- **Projet nécessitant une revue manuelle :** l'indiquer clairement ; ne pas prétendre qu'une validation automatique a eu lieu.
- **Ressource externe indisponible :** conserver la fiche de ressource et indiquer que l'ouverture a échoué.

### Résultat attendu
L'utilisateur progresse sans perdre son contexte. Le passage au niveau suivant dépend des critères pédagogiques réels.

### Critères de validation
- Le cours et le niveau actifs restent identifiables.
- Le point de reprise est explicite.
- Les actions de navigation entre les leçons sont prévisibles.
- Les indices ne révèlent pas automatiquement la solution complète.
- Une leçon consultée ne valide jamais automatiquement une compétence.
- Toute validation repose sur une preuve enregistrée.

## 4. Parcours C — Créer un cours avec l'IA

### Intention
Décrire ce que l'utilisateur souhaite apprendre, puis comprendre le programme avant sa création.

### Point d'entrée
Apprentissage > Mes cours > **« Créer un cours »**, ou Copilote IA.

### Chemin nominal
1. L'utilisateur saisit le sujet ou le langage.
2. Il peut préciser son objectif, son niveau de départ, sa langue et un contexte personnel.
3. Les options secondaires restent facultatives et repliées par défaut.
4. L'IA génère une proposition de cours.
5. L'aperçu présente le titre, la promesse pédagogique, les niveaux, le premier niveau détaillé, les projets et les ressources.
6. L'utilisateur peut demander une amélioration ou modifier les informations disponibles.
7. L'action principale est **« Créer ce cours »**.
8. Après création, l'utilisateur arrive dans la fiche du cours, avec l'action **« Commencer le niveau 1 »**.

### Variantes
- **Sujet trop vague :** l'IA demande une précision ciblée ou formule une hypothèse explicite.
- **Génération échouée :** garder le formulaire et permettre de réessayer sans perdre la saisie.
- **Aperçu incomplet :** signaler les sections manquantes et ne pas présenter le programme comme complet.
- **Utilisateur venant du Copilote :** ne pas créer le cours sans confirmation explicite.

### Résultat attendu
Un cours personnalisé est créé après inspection et validation de son aperçu.

## 5. Parcours D — Organiser une semaine

### Intention
Générer un programme réaliste à partir de l'emploi du temps, des disponibilités, des priorités et des contraintes déjà connues.

### Point d'entrée
Organisation > Planning > **« Générer un planning »**.

### Principe
Le parcours doit progresser dans un ordre compréhensible. Les règles de disponibilité sont consultables et modifiables dans une section secondaire. Ne pas obliger l'utilisateur à ressaisir des données déjà enregistrées.

### Étape 1 — Vérifier le contexte
L'écran montre :
- Emploi du temps fixe connu.
- Disponibilités confirmées.
- Indisponibilités.
- Temps de récupération.
- Objectifs et cours actifs.
- Contraintes ou données manquantes.

Actions :
- Principale : **« Continuer »**.
- Secondaire : **« Modifier mes disponibilités »**.

Si une donnée manque, expliquer son impact et demander uniquement l'information nécessaire.

### Étape 2 — Définir les préférences
Afficher les options réellement utiles :
- Horizon de planification (7 ou 14 jours, selon capacités existantes).
- Focus facultatif (ex. matière prioritaire).
- Budget hebdomadaire facultatif si l'utilisateur souhaite le modifier.
- Instruction en langage naturel facultative.

Les paramètres avancés ne doivent pas être affichés au même niveau que les informations essentielles.

Action principale : **« Générer mon planning »**.

### Étape 3 — Examiner la proposition
Présenter :
- Résumé de charge.
- Répartition du temps.
- Créneaux proposés.
- Temps de récupération.
- Conflits détectés.
- Hypothèses et informations manquantes.
- Changements par rapport au planning déjà appliqué.

Actions :
- Principale : **« Appliquer ce planning »**.
- Secondaire : **« Ajuster avec le Copilote »**.
- Tertiaire : **« Refuser cette proposition »**.

L'action appliquer doit préciser si des créneaux existants seront remplacés ou conservés. Ne jamais masquer ce risque dans un texte secondaire.

### Après application
1. Le système confirme le nombre réel de créneaux ajoutés ou modifiés.
2. L'utilisateur revient à son planning.
3. Les créneaux enregistrés sont visibles dans le calendrier.
4. Une erreur ou un conflit laisse la proposition consultable et permet une nouvelle tentative.

### Variantes
- **Données non valides :** afficher les contraintes à corriger.
- **Aucune disponibilité :** ne pas générer un planning impossible ; demander une disponibilité ou un horizon adapté.
- **Proposition vide :** expliquer pourquoi aucun créneau n'a été retenu.
- **Conflit détecté :** mettre en évidence les deux créneaux concernés et proposer des choix.
- **Rejet :** confirmer que le calendrier n'a pas été modifié.
- **Ancienne version :** restaurer avec une confirmation et un résumé des effets.

### Résultat attendu
Un planning compréhensible, vérifiable et effectivement enregistré après accord explicite.

## 6. Parcours E — Créer et gérer une tâche

### Intention
Capturer rapidement une action sans devoir remplir un formulaire long.

### Points d'entrée
- Accueil > **« Nouvelle tâche »**.
- Organisation > Tâches > **« Nouvelle tâche »**.
- Copilote IA > proposition à valider.

### Capture rapide
Champs visibles :
- Intitulé.
- Priorité, avec valeur par défaut raisonnable.
- Action : **« Ajouter la tâche »**.

Les détails (description, échéance, projet, module) restent disponibles dans un formulaire complet.

### Gestion
La liste affiche les tâches actives par ordre de pertinence. Les filtres et la vue Tableau sont secondaires.

Chaque tâche présente :
- Intitulé.
- Statut.
- Priorité.
- Échéance si elle existe.
- Lien éventuel avec un cours ou un projet.
- Action rapide liée à son statut.

### Parking
Une idée non prioritaire peut être placée dans le Parking. Cette action doit expliquer que l'élément est conservé mais retiré du flux actif.

### Résultat attendu
Une tâche est capturée, priorisée et retrouvable sans confusion.

## 7. Parcours F — Démarrer et terminer une séance

### Intention
Enregistrer le travail réellement effectué.

### Point d'entrée
- Priorité du tableau de bord.
- Prochaine action.
- Page Séances.
- Une leçon ou une tâche.

### Chemin nominal
1. L'utilisateur clique **« Démarrer ma séance »** depuis une tâche, un cours ou la priorité.
2. L'application reprend le contexte lié (titre, cours, tâche ou projet) sans ressaisie.
3. Un écran ou panneau de focus montre l'objectif, le minuteur et l'heure de début.
4. Le minuteur reste accessible après navigation.
5. L'utilisateur termine sa séance.
6. L'application demande un résultat concret : notion comprise, exercice réalisé, livrable produit ou blocage rencontré.
7. L'utilisateur enregistre le bilan.
8. La séance apparaît dans l'historique avec sa durée réelle.

### Variantes
- **Séance déjà active :** proposer de la reprendre plutôt que d'en créer une deuxième.
- **Clôture sans résultat renseigné :** demander un résultat bref ou permettre d'indiquer explicitement qu'aucun livrable n'a été produit.
- **Fermeture de la page :** préserver l'état de la séance selon la persistance actuelle.
- **Durée anormale :** laisser l'utilisateur corriger une donnée si le modèle métier l'autorise, avec traçabilité.

### Résultat attendu
Une séance terminée documente une activité et, lorsque disponible, le résultat obtenu.

## 8. Parcours G — Demander de l'aide au Copilote

### Intention
Exprimer naturellement un besoin sans devoir connaître les outils internes.

### Point d'entrée
Copilote IA, ou action contextuelle depuis une leçon, une tâche, un projet ou le planning.

### Chemin nominal
1. L'utilisateur ouvre le Copilote.
2. Le champ de message est immédiatement disponible.
3. Le contexte automatique autorisé est utilisé par défaut.
4. L'interface indique discrètement les catégories de données prises en compte.
5. L'utilisateur pose une question en langage naturel.
6. Le Copilote répond avec une structure lisible.
7. Si une mutation est nécessaire, il présente une proposition structurée.
8. La proposition indique ce qu'elle va modifier et pourquoi.
9. L'utilisateur peut accepter, modifier ou refuser.
10. Après acceptation, l'interface attend le résultat réel du backend.
11. Le statut de la proposition et l'écran concerné sont mis à jour.

### Variantes
- **Données manquantes :** poser une question ciblée.
- **Contexte partiel :** l'indiquer clairement.
- **Réponse sans action :** ne pas afficher de carte de proposition vide.
- **Action refusée :** ne rien muter.
- **Action échouée :** conserver la proposition et afficher l'erreur avec une option de réessai.
- **Conversation longue :** garder l'historique accessible sans réduire la largeur de lecture.

### Résultat attendu
Une conversation naturelle aboutit à une réponse exploitable ou à une action validée, sans mutation silencieuse.

## 9. Parcours H — Consulter ses objectifs et projets

### Intention
Comprendre les résultats attendus et la prochaine action de chaque projet actif.

### Chemin nominal
1. Ouvrir Objectifs & projets.
2. Consulter les objectifs personnels et projets actifs.
3. Distinguer objectifs, projets et tâches liées.
4. Ouvrir une fiche.
5. Vérifier le résultat attendu, le statut, la prochaine action et les livrables.
6. Mettre à jour le statut ou la prochaine action.
7. Revenir à l'accueil pour faire apparaître la priorité pertinente, sans transformer automatiquement chaque projet en priorité principale.

### Résultat attendu
Chaque projet actif possède un objectif compréhensible et une prochaine action.

## 10. Parcours I — Modifier ses préférences

### Intention
Modifier un paramètre sans craindre de perdre les autres changements.

### Chemin nominal
1. Ouvrir Paramètres.
2. Choisir une catégorie : Profil, Préférences, Disponibilités, Copilote IA, Apparence ou Sécurité.
3. Modifier les champs nécessaires.
4. L'interface indique clairement les changements non enregistrés.
5. L'utilisateur enregistre.
6. L'interface confirme la réussite ou indique le champ en erreur.
7. En cas de navigation avec changements non enregistrés, demander une confirmation de sortie lorsque la perte serait réelle.

### Résultat attendu
Les paramètres sont sauvegardés explicitement et l'utilisateur comprend leur portée.

## 11. États transversaux obligatoires

Pour tous les parcours :
- Chargement initial.
- Mise à jour en cours.
- Succès.
- Erreur réseau.
- Données absentes.
- Résultat vide après filtre.
- Confirmation avant action destructive.
- Prévention des doubles soumissions.
- Récupération d'une saisie après erreur lorsque possible.
- Focus clavier et annonces accessibles.

## 12. Matrice de validation

| Parcours | Résultat observable | Preuve technique attendue |
|---|---|---|
| A — Journée | Priorité et prochaine action visibles | Test dashboard et navigation |
| B — Apprendre | Progression et validation correctement enregistrées | Tests cours, leçons, exercices et projet |
| C — Créer cours | Cours créé après aperçu accepté | Test création et proposition IA |
| D — Planifier | Créneaux réellement appliqués | Test génération, rejet, application et conflit |
| E — Tâche | Tâche créée et statut mis à jour | Test CRUD et parking |
| F — Séance | Séance active puis clôturée avec bilan | Test start/complete et historique |
| G — Copilote | Proposition exécutée uniquement après consentement | Tests Copilote et actions |
| H — Projet | Objectif et prochaine action consultables | Tests projets |
| I — Paramètres | Préférences enregistrées et persistées | Tests Settings |

## 13. Critères d'acceptation de la phase

- [ ] Chaque parcours a un point d'entrée clair.
- [ ] Chaque parcours comporte un résultat mesurable.
- [ ] Les états alternatifs et erreurs sont prévus.
- [ ] Aucune action de mutation IA n'est implicite.
- [ ] Les étapes pédagogiques existantes sont préservées.
- [ ] Le planning est appliqué uniquement après confirmation.
- [ ] Les séances documentent le travail réellement réalisé.
- [ ] Les tests existants sont associés aux parcours correspondants.
