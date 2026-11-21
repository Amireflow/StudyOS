# 08 — Lot 1 : implémentation et vérification des fondations

> Date : 21 novembre 2026  
> Branche : `ux/audit-initial-2026-11-21`  
> Pull request : [#3 — Refonte UX/UI StudyOS](https://github.com/Amireflow/StudyOS/pull/3) (brouillon, non fusionnée)  
> Commit applicatif testé : `124f2e84e51daab894c65f163ac7edfd227d9ffa`  
> Statut : contrôles techniques verts ; inspection visuelle après modification encore nécessaire.

## 1. Périmètre réalisé

Le Lot 1 a posé une couche de tokens sémantiques et raccordé les composants partagés les plus transversaux. Les pages métier, routes, API, schémas de données, règles RLS, validations de compétences et workflows du Copilote n'ont pas été modifiés.

### Fichiers applicatifs modifiés

- `frontend/src/index.css` : palette sémantique clair/sombre, typographie, espacement, rayons, élévation, focus visible, composants CSS partagés et prise en compte de `prefers-reduced-motion`.
- `frontend/src/components/ui/Button.tsx` : six variantes sémantiques (principale, secondaire, contour, fantôme, danger, lien), tailles standard/compacte, état `aria-busy`, désactivation pendant le chargement.
- `frontend/src/components/ui/FormFields.tsx` : champs à hauteur standard 44 px, labels et aides plus lisibles, état d'erreur sémantique.
- `frontend/src/components/ui/Card.tsx` : surface et bordure partagées, hiérarchie titre/description, espacements basés sur les tokens.
- `frontend/src/components/ui/Badge.tsx` : variantes sémantiques clair/sombre et métadonnées à 12 px.
- `frontend/src/components/layout/PageHeader.tsx` : titre à l'échelle H1, description non tronquée et actions mieux espacées.
- `frontend/src/components/ui/StateFeedback.tsx` : chargement, état vide, erreur et succès raccordés aux tokens.
- `frontend/src/components/ui/DesignSystem.test.tsx` : quatre tests ciblés sur les primitives partagées.

## 2. Tokens de référence

### Couleurs

| Token | Clair | Sombre |
|---|---|---|
| Canvas | `#F5F5F3` | `#09090B` |
| Surface | `#FFFFFF` | `#18181B` |
| Surface secondaire / contrôle | `#F4F4F5` | `#27272A` |
| Texte principal | `#18181B` | `#FAFAFA` |
| Texte secondaire | `#52525B` | `#A1A1AA` |
| Bordure | `#E4E4E7` | `#3F3F46` |
| Accent | `#0F766E` | `#2DD4BF` |
| Accent doux | `#CCFBF1` | `#134E4A` |
| Succès | `#15803D` | `#4ADE80` |
| Avertissement | `#A16207` | `#FACC15` |
| Erreur | `#BE123C` | `#FDA4AF` |
| Information | `#1D4ED8` | `#93C5FD` |

### Typographie

La pile de polices ne prétend plus charger Geist, Plus Jakarta Sans ou Inter sans ressources locales. Elle s'appuie sur la pile système du navigateur et de l'appareil. Les tailles sont centralisées : H1 26/34 px, H2 20/28 px, H3 16/24 px, corps 15/24 px, corps compact 14/21 px, labels/aides 13 px et métadonnées 12/16 px.

### Espacement et géométrie

L'échelle 4 px est matérialisée de 4 à 64 px. Les rayons partagés sont 10 px pour les contrôles, 16 px pour les cartes, 20 px pour les panneaux et 9999 px pour les pills. Les contrôles standard ont une hauteur minimale de 44 px ; la taille compacte passe elle aussi à 44 px sur appareils tactiles.

## 3. Vérification du contraste des principaux couples

Les ratios suivants ont été calculés à partir des valeurs hexadécimales des tokens, et non mesurés dans un navigateur :

| Couple de couleurs | Ratio calculé |
|---|---:|
| Texte blanc sur accent clair `#0F766E` | 5,47:1 |
| Texte sombre `#042F2E` sur accent sombre `#2DD4BF` | 7,77:1 |
| Texte secondaire clair `#52525B` sur canvas `#F5F5F3` | 7,08:1 |
| Texte secondaire sombre `#A1A1AA` sur surface sombre `#18181B` | 6,91:1 |
| États de succès, avertissement, erreur et information | supérieur à 6,6:1 pour les couples définis |

Ces couples dépassent 4,5:1 pour le texte courant. Une recette navigateur reste nécessaire pour vérifier les états réels, les couleurs héritées et les exceptions de chaque écran.

## 4. Résultats CI

Exécution GitHub Actions liée au commit applicatif `124f2e84e51daab894c65f163ac7edfd227d9ffa` ([run CI final](https://github.com/Amireflow/StudyOS/actions/runs/44890912255)) :

| Contrôle | Résultat |
|---|---|
| Installation npm | réussite |
| TypeScript strict `npm run typecheck` | réussite |
| Vitest frontend | 20 fichiers, 79 tests réussis |
| Build `npm run build` | réussite |
| Alembic — migrations et réversibilité | réussite |
| Pytest backend | 133 tests réussis, 5 avertissements |

Le build final signale un chunk JavaScript minifié de 1 000,40 kB, supérieur au seuil d'avertissement de 700 kB configuré. Le build réussit ; l'optimisation du découpage du bundle est un sujet séparé et n'a pas été élargie dans ce lot.

Une première exécution CI a échoué au typecheck à cause de caractères d'échappement dans trois expressions TypeScript. Ces erreurs ont été corrigées dans le commit suivant ; la seconde exécution, sur le commit indiqué ci-dessus, est entièrement verte.

## 5. Limites et contrôles non revendiqués

- Aucun screenshot navigateur après modification n'est disponible dans ce lot.
- Aucun calcul de contraste DOM par écran, aucun audit VoiceOver/NVDA et aucun parcours clavier manuel n'ont été réalisés.
- La pile system-ui est déclarée ; la famille réellement choisie dépend de l'appareil et reste à confirmer sur navigateur.
- Le responsive réel aux largeurs 320, 360, 390, 768, 1024, 1280 et 1440 px reste à inspecter.

## 6. Décision de sortie

**Implémentation de base et CI : réussies. Lot 1 : en attente de validation visuelle.**

Avant de passer au Lot 2 :
1. déployer ou ouvrir une prévisualisation de la branche ;
2. vérifier au minimum le tableau de bord, le planning, le Copilote et les formulaires en thème clair et sombre sur mobile ;
3. confirmer l'absence de débordement, de boutons trop petits et de régression dans les formulaires.

La pull request reste en brouillon et aucune modification n'a été fusionnée dans `main`.
