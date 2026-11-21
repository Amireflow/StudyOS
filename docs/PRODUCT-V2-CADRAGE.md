# StudyOS V2 — Vision produit et contrat fonctionnel

**Version :** 2.0  
**Date :** 21 novembre 2026  
**Statut :** Proposition de référence produit — à valider avant implémentation  
**Utilisateur initial :** un utilisateur personnel, étudiant en informatique et constructeur de produits numériques

> Ce document devient la référence produit cible. En cas de contradiction, il prime sur les anciennes formulations du PRD et du cahier des charges. Les documents précédents restent des références historiques et techniques.

## 1. Décision produit

StudyOS n'est pas un gestionnaire de tâches avec un chatbot ajouté. Ce n'est pas un tableau de bord qui demande à l'utilisateur de maintenir manuellement plusieurs bases de données.

**StudyOS est un copilote personnel qui transforme les études, les objectifs et les contraintes de l'utilisateur en un programme d'apprentissage et d'exécution concret, puis adapte ce programme à partir des résultats réellement observés.**

L'utilisateur décrit ce qu'il doit apprendre, réussir ou terminer. StudyOS :
1. comprend son contexte existant ;
2. identifie les informations réellement manquantes ;
3. construit une progression pédagogique et un programme réaliste ;
4. accompagne l'exécution et l'apprentissage ;
5. évalue les travaux soumis ;
6. adapte les actions futures selon les résultats.

Sa valeur principale : l'utilisateur sait quoi faire, peut le faire, reçoit un retour de qualité et progresse sans devoir constamment réorganiser son système.

## 2. Origine et besoins à préserver

### 2.1 Études universitaires
- Centraliser l'emploi du temps réel, les matières, les devoirs, les examens et les échéances.
- Distinguer les cours universitaires fixes des séances personnelles.
- Préparer les examens à partir du contenu réellement étudié, des échéances et du niveau de maîtrise.
- Tenir compte des changements d'emploi du temps et des indisponibilités.

### 2.2 Apprentissage approfondi
- Créer des cours complets sur demande : Python, Java, React, SQL ou autres compétences utiles.
- Construire une progression par niveaux, modules et leçons avec prérequis.
- Fournir des explications progressives, exemples commentés, exercices gradués, projets et évaluations.
- Recommander des ressources complémentaires vérifiables : documentation officielle, articles et vidéos adaptés à la langue.
- Corriger le travail soumis, expliquer les erreurs et proposer une nouvelle tentative.
- Ne débloquer un niveau que lorsque les critères de maîtrise sont satisfaits.

### 2.3 Organisation automatisée
- Analyser le planning, les disponibilités, les tâches, les échéances, les priorités et la progression.
- Générer les séances nécessaires sans demander à l'utilisateur de créer séparément une tâche, un créneau et une compétence.
- Respecter la charge réaliste, le repos, les cours fixes et les contraintes personnelles.
- Réorganiser le programme lorsqu'une séance est manquée ou lorsqu'un imprévu survient.

### 2.4 Discipline et concentration
- Maintenir une seule priorité principale active.
- Limiter les actions critiques à trois au maximum.
- Ne pas transformer chaque nouvelle idée en projet actif.
- Mettre les idées secondaires en attente et signaler leur coût d'opportunité.
- Distinguer activité, livrable et résultat.

### 2.5 Projets comme terrain d'application
Les projets personnels servent à pratiquer et démontrer des compétences. StudyOS ne devient pas un outil complet de gestion d'entreprise ou de portefeuille de projets. Les outils métier spécialisés restent responsables de la gestion détaillée de ces activités.

## 3. Proposition de valeur

> Je renseigne mes études, mes objectifs et mes contraintes. StudyOS construit un programme adapté, m'enseigne, m'entraîne, corrige mes travaux et ajuste la suite selon ma progression. Je me concentre sur l'exécution au lieu de gérer l'application.

**Règle produit : toute fonctionnalité doit réduire l'effort de décision ou améliorer directement l'apprentissage, l'exécution ou la validation d'un résultat.** Sinon, elle est masquée, reportée ou retirée du périmètre.

## 4. Expérience cible : quatre espaces seulement

| Espace | Question | Contenu |
|---|---|---|
| Aujourd'hui | Que dois-je faire maintenant ? | Priorité, prochaine séance, programme du jour, trois actions critiques maximum |
| Apprendre | Qu'est-ce que j'apprends et où en suis-je ? | Cours, niveaux, modules, leçons, exercices, projets pédagogiques, évaluations et preuves |
| Planning | Quand le travail doit-il avoir lieu ? | Cours fixes, disponibilités, séances proposées, agenda et contraintes |
| Copilote | Que veux-je demander ou changer ? | Conversation contextuelle, création et ajustement, explications, corrections et décisions |

Les paramètres sont accessibles depuis le profil. Les détails techniques de mémoire, outils, journaux, fournisseurs et actions automatiques ne sont pas dans la navigation de premier niveau.

### 4.1 Aujourd'hui
L'écran d'accueil affiche, dans cet ordre :
1. la priorité principale active et son résultat attendu ;
2. la prochaine action réalisable avec son horaire et sa durée ;
3. les autres actions critiques du jour, trois au maximum ;
4. les cours fixes à venir ;
5. un résumé de progression uniquement s'il aide à prendre une décision.

À retirer de la vue par défaut : cartes de statistiques décoratives, indicateurs redondants, grands états vides et sections qui n'aident pas à commencer. Les informations secondaires restent accessibles au besoin.

L'utilisateur doit identifier sa prochaine action en moins de 30 secondes.

### 4.2 Apprendre
Une bibliothèque pédagogique unifiée. Les notions de cours, parcours et compétences ne doivent pas apparaître comme trois systèmes concurrents.

Structure :
- Cours : objectif global et résultat attendu.
- Niveaux : progression ordonnée et critères de passage.
- Modules : regroupements cohérents de notions.
- Leçons : explication, exemples, activités et exercices.
- Projets et évaluations : preuves de mise en pratique.
- Ressources : références avec langue, type, source et justification.
- Compétences : synthèse de la maîtrise démontrée, pas un formulaire à maintenir manuellement.

À la création, l'IA produit la carte pédagogique complète : niveaux, objectifs, modules, leçons, prérequis, exercices, projets et critères d'évaluation. Le contenu détaillé doit être de haute qualité et disponible avant le démarrage du niveau concerné. Les prochains niveaux peuvent être détaillés progressivement pour préserver la cohérence et la qualité.

Une leçon doit aider à comprendre, pas simplement présenter un long texte. Elle combine explications progressives, exemples, contre-exemples, exercices et vérification de compréhension. Les solutions complètes sont révélées après une tentative ou une demande explicite d'aide.

### 4.3 Planning
Le planning sert à voir et comprendre le programme, non à obliger l'utilisateur à construire manuellement chaque bloc.

Il distingue :
- cours universitaires et événements fixes ;
- indisponibilités et temps de repos ;
- séances personnelles proposées par StudyOS ;
- séances réalisées et résultats enregistrés.

Une proposition de planning est présentée sous forme de plan consolidé, avec justification, durée, lien pédagogique et éléments non planifiés. L'utilisateur peut l'accepter, l'ajuster ou la refuser. Aucun événement n'est créé avant validation explicite d'une proposition importante.

Après un imprévu, StudyOS recalcule uniquement ce qui doit changer, protège les cours fixes et évite de transférer toute la charge manquée sur une journée déjà pleine.

### 4.4 Copilote
Un assistant conversationnel unique, utilisable depuis toutes les pages avec le contexte utile de la page courante.

Exemples :
- « Organise ma semaine selon mon emploi du temps. »
- « Crée un cours de React depuis mon niveau actuel. »
- « Explique-moi les pointeurs en C++ avec des exemples. »
- « Corrige mon exercice et montre-moi précisément mes erreurs. »
- « Je n'ai pas terminé cette séance, réorganise le reste de ma journée. »
- « Je veux ajouter cette idée ; vérifie si elle est prioritaire. »

Le Copilote réutilise les données déjà enregistrées et ne pose que les questions essentielles manquantes. Il montre ce qu'il a compris, les hypothèses prises et les actions proposées. Les détails d'outillage et de mémoire sont masqués dans l'expérience normale.

## 5. Parcours utilisateur indispensables

### A — Première configuration
1. Rechercher les données déjà disponibles.
2. Demander seulement les informations manquantes : emploi du temps, obligations, indisponibilités, objectifs actifs et préférences.
3. Permettre la saisie ou l'import du planning ; toute extraction est présentée pour correction avant enregistrement.
4. Résumer le contexte retenu et signaler les incertitudes.
5. Faire confirmer le contexte.
6. Générer la première proposition de programme.

**Critère :** configuration guidée, sans formulaires dispersés ni répétition des mêmes questions.

### B — Générer une semaine
1. Charger les cours fixes et les échéances.
2. Charger les objectifs et priorités.
3. Déterminer les prérequis et prochaines étapes des cours.
4. Calculer les créneaux réellement disponibles.
5. Prioriser et répartir le travail dans les limites de charge.
6. Afficher les séances, leurs raisons, les arbitrages et les éléments non planifiés.
7. Faire confirmer le programme.
8. Enregistrer une version du plan et les événements correspondants.

**Critère :** aucune séance ne chevauche un cours fixe ou une indisponibilité confirmée ; aucune séance générique sans objectif concret.

### C — Apprendre et être évalué
1. Ouvrir la prochaine leçon prévue.
2. Lire une explication structurée adaptée au niveau.
3. Réaliser les exercices et soumettre une réponse ou un livrable.
4. Recevoir une correction justifiée, une note ou un statut et des conseils précis.
5. Recommencer si nécessaire.
6. Valider le niveau uniquement lorsque les critères sont atteints.
7. Générer la suite et adapter le planning.

**Critère :** compétences et niveaux reposent sur des preuves vérifiables, pas sur le temps passé ou un bouton « terminé ».

### D — Gérer un imprévu
L'utilisateur explique ce qui n'a pas été fait ou ce qui a changé. StudyOS identifie les séances et échéances concernées, propose une réorganisation minimale, conserve cours fixes et repos, explique ce qui est reporté et demande confirmation.

**Critère :** pas de surcharge ni de modifications silencieuses.

### E — Nouvelle idée
Le Copilote compare l'idée à la priorité active, aux échéances et à la charge. Il explique son urgence et son coût d'opportunité, puis recommande de l'exécuter, de la réduire ou de la placer dans le parking. La priorité ne change que sur décision explicite.

**Critère :** une nouvelle idée n'interrompt pas automatiquement le programme en cours.

## 6. Hiérarchie de décision du moteur

Le moteur applique des règles déterministes aux contraintes et utilise l'IA pour raisonner sur le contenu, la pédagogie et les arbitrages.

Ordre :
1. cours universitaires, examens confirmés et obligations fixes ;
2. échéances réelles et tâches urgentes ;
3. priorité principale et objectifs confirmés ;
4. prérequis pédagogiques et niveaux non validés ;
5. disponibilités, préférences et durée réaliste ;
6. consolidation, révision et projets d'application ;
7. idées secondaires, uniquement si une capacité réelle existe.

Ne jamais inventer une date d'examen, une disponibilité, une séance réalisée ou un niveau acquis. Si le contexte est incomplet, le plan signale l'information manquante et limite ses affirmations.

### Qualité minimale d'une séance
Chaque séance doit avoir :
- un sujet précis ;
- un objectif pédagogique ou résultat concret ;
- une durée estimée et justifiée ;
- un lien vers une leçon, un exercice, un projet ou une échéance ;
- un livrable ou critère de fin lorsque pertinent ;
- une explication de sa priorité.

« Continuer le cours », « Étudier Python » ou « Travailler sur le projet » ne sont pas assez précis sans prochaine étape concrète.

## 7. Modèle fonctionnel unifié

| Concept utilisateur | Sens | Correspondance interne à vérifier |
|---|---|---|
| Priorité | Résultat principal du moment | Objectif ou projet existant |
| Cours | Programme pédagogique | Course ou LearningPath |
| Leçon | Étape à comprendre | Lesson et Module |
| Action | Travail concret à produire | Task |
| Créneau | Moment prévu | ScheduleEvent |
| Séance | Travail réellement réalisé | StudySession |
| Preuve | Travail soumis et évalué | Submission, Evidence ou modèle existant |
| Maîtrise | Compétence démontrée | Skill et historique d'évaluation |

Avant toute migration, établir la correspondance exacte entre modèles réels, relations, API, règles de propriété et tests. Ne pas dupliquer Course/LearningPath ni recréer des tables si les modèles existants conviennent.

## 8. Exigences IA et qualité

### Contexte
Le contexte du Copilote est construit à la demande et limité au besoin courant. Il peut inclure profil, cours fixes, disponibilités, objectifs, tâches, cours, progression, évaluations, séances et consignes personnelles.

Le système vérifie la fraîcheur des données et les informations absentes. Les données de mémoire ne contredisent jamais les données métier plus récentes.

### Raisonnement et orchestration
- Utiliser le fournisseur et le modèle configurés côté serveur.
- Séparer les instructions par tâche : planification, explication pédagogique, génération de cours, correction et bilan.
- Utiliser des sorties structurées et les valider côté serveur.
- Le moteur déterministe vérifie dates, disponibilités, conflits, limites et prérequis.
- Aucun accès SQL direct pour le modèle.
- Aucun outil non déclaré ne peut être exécuté.
- Toute mutation importante passe par une proposition lisible et une confirmation explicite.

StudyOS n'a pas besoin d'imiter un assistant généraliste pour tout. Il doit être excellent dans ses domaines : organisation, apprentissage, pédagogie, évaluation et progression.

### Correction pédagogique
Chaque évaluation définit avant la soumission : compétences ciblées, critères et pondération, difficulté attendue, erreurs bloquantes, seuil de validation et preuves à fournir.

La correction distingue erreur conceptuelle, erreur de méthode, erreur de syntaxe et oubli de consigne. Elle donne des indices avant la solution complète lorsque cela aide l'apprentissage.

### Ressources
Les ressources sont présentées avec titre, source, langue, type et raison de recommandation. Les liens non vérifiés ne sont jamais présentés comme fiables.

## 9. Simplification de l'expérience

| Expérience actuelle | Expérience cible |
|---|---|
| Cours + Parcours + Compétences | Apprendre |
| Tâches + Séances | Actions et résultats reliés au Planning |
| Objectifs + Projets | Priorité, objectif et livrable, sans gestion de portefeuille complète |
| Briefing + Bilan | Synthèses du Copilote |
| Mémoire, outils et configuration IA | Paramètres avancés ou détails techniques |

À retirer de la navigation quotidienne : Compétences comme page de gestion manuelle, Séances comme destination principale, gestion complète d'objectifs/projets, panneaux techniques du Copilote et statistiques décoratives.

À garder dans le parking jusqu'à preuve d'utilité : assistant vocal permanent, wake word, agents multiples, gamification avancée, collaboration multi-utilisateurs, synchronisation calendrier externe complexe, gestion complète d'entreprise, analytics avancés, application mobile native.

Masquer une rubrique ne signifie pas supprimer ses données, API ou modèles. La simplification doit commencer par l'expérience utilisateur.

## 10. Architecture et conservation

La V2 est une évolution, pas une réécriture de la pile.

À réutiliser et auditer :
- frontend React, TypeScript, Vite et composants existants ;
- backend FastAPI, SQLAlchemy et PostgreSQL ;
- authentification et isolation des données ;
- services de cours et générateur pédagogique ;
- ContextBuilder et ToolRegistry ;
- moteur de disponibilités, priorisation, allocation et planification ;
- évaluations, preuves et verrou pédagogique.

Ordre technique :
1. cartographier routes et modèles réels ;
2. identifier les responsabilités dupliquées ;
3. définir les services sources de vérité ;
4. simplifier les écrans sans supprimer routes/API ;
5. connecter les parcours principaux de bout en bout ;
6. migrer des données seulement si un doublon structurel est démontré ;
7. retirer les anciens parcours après migration vérifiée et tests de non-régression.

Aucune donnée utilisateur ne doit être supprimée pendant la simplification UX.

## 11. Plan d'exécution priorisé

| Lot | Objectif | Livrable | Condition de sortie |
|---|---|---|---|
| 0 — Contrat produit | Valider vision et règles | Ce document et carte des écarts | Décisions produit approuvées |
| 1 — Moteur de programme | Fiabiliser génération, contraintes et qualité des séances | Génération contextualisée | Scénarios réels et CI réussis |
| 2 — Navigation et Aujourd'hui | Réduire l'effort et mettre l'action au centre | Quatre espaces et accueil simplifié | Parcours quotidien en moins de 30 s |
| 3 — Onboarding et contexte | Collecter une fois et réutiliser le contexte | Configuration conversationnelle | Questions répétées supprimées |
| 4 — Apprendre | Garantir cours, leçons, exercices, projets et évaluation | Parcours pédagogique de bout en bout | Niveau validé sur preuves |
| 5 — Adaptation | Replanifier selon résultats et imprévus | Boucle de progression | Aucun doublon, conflit ou surcharge |
| 6 — Validation réelle | Mesurer l'utilité sur quatre semaines | Rapport d'usage réel | Critères d'usage et problèmes bloquants traités |

Le moteur de programme est prioritaire techniquement : il relie les données, l'expérience quotidienne et l'apprentissage. La simplification UX rend ensuite ce moteur visible et simple à utiliser.

## 12. Critères d'acceptation

### Organisation
- Prochaine action identifiable en moins de 30 secondes.
- Une seule priorité principale active.
- Trois actions critiques maximum mises en évidence par jour.
- Cours fixes jamais déplacés par le moteur.
- Aucune proposition pendant une indisponibilité confirmée.
- Raisons des éléments reportés ou non planifiés affichées.

### IA
- Une demande en langage naturel produit le bon type de proposition.
- Les informations connues ne sont pas redemandées sans raison.
- Une proposition rejetée ne crée aucune donnée.
- Une proposition acceptée ne crée que les éléments validés.
- Les séances ont un contenu concret et contextualisé.
- Les données absentes ou incertaines sont signalées.

### Apprentissage
- Chaque cours possède une progression cohérente.
- Chaque leçon contient explication, exemples et pratique.
- Exercices et projets ont des critères explicites.
- Une soumission reçoit un retour exploitable.
- Un niveau n'est débloqué que sur preuve validée.
- Le système propose révision ou nouvelle tentative avant de poursuivre si nécessaire.

### Utilité réelle
- Utilisation pendant quatre semaines.
- Au moins trois séances suivies par semaine, hypothèse initiale à mesurer.
- Pas de reconfiguration manuelle quotidienne du programme.
- Mesure des séances réalisées, livrables soumis et évaluations validées.
- Toute fonctionnalité secondaire justifiée par un usage observé.

## 13. Points techniques ouverts

1. La PR #2 corrige le routage des demandes de programme vers le moteur dédié, les plafonds de séances et l'utilisation du service de cours configuré ; elle ajoute des tests. Sa branche est basée sur un ancien commit et diverge de main. Elle doit être réintégrée ou réimplémentée proprement puis retestée sur le main actuel. Ne pas la fusionner à l'aveugle.
2. Vérifier que la planification prend réellement en compte disponibilités, cours universitaires, priorités, prérequis, charges maximales et évaluations.
3. Vérifier que le contenu détaillé utilise le fournisseur configuré et pas uniquement des plans statiques de secours.
4. Vérifier que les soumissions d'exercices et projets sont reliées à l'évaluation, aux preuves et au verrou de niveau.
5. Vérifier l'expérience desktop et mobile après simplification. Vitest/jsdom ne remplace pas les contrôles en navigateur réel.

## 14. Gouvernance anti-dispersion

- Une seule priorité principale dans le produit.
- Maximum trois actions critiques en évidence.
- Les idées nouvelles entrent dans le parking.
- Aucun nouveau module sans problème utilisateur démontré.
- Aucun polish visuel avant validation du parcours fonctionnel concerné.
- Chaque lot possède un résultat observable, une preuve et une décision de sortie.
- L'application ne doit jamais créer plus de travail de gestion qu'elle n'en retire.

---

**Décision attendue :** valider ce contrat produit V2. Après validation, commencer le Lot 1 : sécurisation et vérification du moteur de programme, avec comparaison de la PR #2 à l'état actuel de main.
