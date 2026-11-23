# Fonctionnalité : Refonte de la navigation Bòrd Pro

## Objectif
Remplacer le menu actuel par 5 entrées de travail quotidien (Accueil · Bord · Dates · Social · Contacts) et ranger tout le paramétrage dans un seul espace « Ma structure » (`/structure/`). Réduire les clics sur les tâches fréquentes et ajouter les confirmations d'actions qui manquent. Aucune nouvelle app Django, aucune migration.

## Documents de référence
- docs/produit/bord-pro-architecture-navigation.md (v1.2, source de vérité)
- docs/produit/cahier-des-charges.md (ligne 227 à mettre à jour)
- docs/marque/charte-graphique.md (navigation, contrastes)
- docs/technique/verification-visuelle.md
- docs/produit/feuille-de-route.md

## Découpage en PR
- [x] PR 0 — Confirmations des actions (`feature/confirmations-actions`)
  - Objectif : chaque action qui crée, modifie, supprime ou change un statut affiche un message de succès, y compris l'espace équipe (lien secret) et les réponses HTMX (volet Social de la date). Pas de modale « êtes-vous sûr ».
  - Fichiers : apps/finance/views.py, apps/finance/team_views.py, apps/gigs/views.py, apps/documents/billing_views.py, apps/roadmaps/views.py, apps/catalog/views.py, templates/base.html, un fragment de messages pour HTMX, relevé des actions dans ce fichier.
  - Tests : un test par action confirmée ; test HTMX sur l'ajout de dépense depuis le volet Social ; cas d'erreur inchangés ; pas de message sur les actions anodines.
  - Documents à relire : charte (messages d'état), feuille-de-route.
  - Risques : message perdu ou doublé dans une réponse HTMX ; aucune donnée personnelle ni lien secret dans les textes (CLAUDE.md §6.3).
- [x] PR 1 + PR 2 — Menu à 5 entrées, nouvelles URL et « Ma structure » (`feature/nav-menu-urls` puis `feature/nav-ma-structure`, **livrées ensemble en production**)
  - Objectif PR 1 : menu Accueil · Bord · Dates · Social · Contacts, `active_menu` (R7), pied de menu « Ma structure » + nom de la structure, nouvelles URL (`/bord/depenses/`, `/bord/documents/` avec documents émis, `/social/`, `/contacts/?type=organisateurs|lieux|personnes`), redirections 301 définitives, mise à jour du cahier des charges ligne 227. `/radar/` reste accessible hors menu.
  - Objectif PR 2 : `/structure/` avec onglets verticaux (Fiche, Équipe, Spectacles, Paratge en explication seule, Documents, Compte et offre), droits NAV-D4, redirections de `/bord/informations/`, `/bord/equipe/`, `/spectacles/`, indicateur de complétude en toutes lettres.
  - Fichiers : templates/components/_nav.html, _sidebar.html, _header.html, _breadcrumb.html ; config/urls.py ; apps/core (active_menu) ; vues de tenants, catalog, documents, addressbook, finance (listes en lecture) ; gabarit à onglets de Ma structure ; docs/produit/cahier-des-charges.md.
  - Tests : chaque ancienne URL répond 301 vers la nouvelle ; une seule entrée active par page ; liens secrets publics inchangés ; isolation des tenants sur les nouvelles listes ; `member` : 403 sur Fiche, Documents, Compte, Paratge, lecture de Équipe, lecture et modification de Spectacles ; `member` voit l'entrée Social avec un message d'explication.
  - Documents à relire : doc de navigation §2, §3, §6 ; charte ; verification-visuelle.md.
  - Risques : nombreuses anciennes URL et liens d'e-mail (garder les noms de routes stables, chercher tous les `{% url %}`) ; Spectacles et Ma structure disparaissent du menu tant que la PR 2 n'est pas livrée (d'où la livraison groupée) ; droits déplacés, pas ajoutés (tester propriétaire, membre, autre tenant) ; vérifier le rendu dans un vrai navigateur.
- [ ] PR 3 — Cachet de référence (`feature/nav-cachet-reference`)
  - Objectif : `Person.average_fee` devient « cachet de référence (brut) », visible et modifiable par le propriétaire seul, repris en copie sur les dates (sans recalcul des dates existantes).
  - Fichiers : formulaire et gabarits de la fiche équipe (apps/tenants), reprise dans GigMember (lire l'existant avant).
  - Tests : un `member` ne voit pas le champ ; modifier la référence ne change pas les dates déjà saisies ; montant au centime.
  - Documents à relire : doc de navigation §3 (cachet), CLAUDE.md §6.2 et §10.
  - Risques : fuite du montant vers un membre ou une feuille de route ; aucun calcul de paie ; aucune migration (libellé seulement).
- [ ] PR 4 — Fil d'Ariane et relevé des clics (`feature/nav-fil-ariane`)
  - Objectif : fil d'Ariane sur toutes les pages de niveau 2 ou plus (R8) ; relevé du nombre de clics des 13 tâches du §5.
  - Fichiers : templates/components/_breadcrumb.html et gabarits de niveau 2 ; tableau de relevé dans ce fichier.
  - Tests : présence et liens du fil d'Ariane sur les pages principales ; contrôle visuel dans un navigateur.
  - Documents à relire : doc de navigation §4 et §5, charte.
  - Risques : libellés incohérents avec le lexique (CLAUDE.md §5).

## Décisions prises
- 2026-11-23 — Cachet de référence : réutiliser `Person.average_fee`, aucune migration (le champ existe déjà).
- 2026-11-23 — `/radar/` gardé, hors menu, accessible par le bouton Radar.
- 2026-11-23 — Social : déplacer l'existant tel quel (propriétaire seul), aucune refonte.
- 2026-11-23 — Structure d'abord ; « + Créer », recherche, « À faire », C1, tournées et refonte de Social hors chantier.
- 2026-11-23 — Cahier des charges ligne 227 mis à jour dans la PR 1.
- 2026-11-23 — `/bord/depenses/` et la liste des documents émis sont de nouvelles vues en lecture, dans la PR 1.
- 2026-11-23 — Annuaire : une page `/contacts/` avec filtre `?type=`, qui réutilise les listes existantes (pas de liste unique). « Personnes » = `Contact` d'organisateurs et de lieux ; l'équipe (`Person`) reste dans Ma structure.
- 2026-11-23 — Redirections 301 définitives, sans date de fin.
- 2026-11-23 — PR 1 et PR 2 livrées ensemble en production, pour ne pas faire vivre deux menus différents.
- 2026-11-23 — PR 0 inclut l'espace équipe par lien secret.
- 2026-11-23 — `/contacts/` sans `?type=` affiche les organisateurs ; les fiches et formulaires gardent leurs chemins.
- 2026-11-23 — Ma structure : Documents = modèles de messages (pour l'instant) ; Compte et offre = exports, suppression, texte « pas d'offre payante » ; Paratge = texte d'explication.
- 2026-11-23 — NAV-D4 appliqué strictement : un `member` lit l'Équipe (plus de modification), gère les Spectacles, reçoit 403 sur Fiche, Documents, Compte, Paratge ; Social lui affiche une explication.
- 2026-11-23 — « Quitter cette structure » placé sur la page Équipe pour un `member`.

## Points en suspens
- Alertes Radar et contrôles de contrat qui pointent vers `tenants:settings` : un `member` qui clique reçoit 403 (à revoir si gênant).
- Lien d'export ZIP absent de l'interface pour un `member` (adresse toujours ouverte).
- Reprise du cachet de référence sur les dates : lire d'abord `GigMember.cachet_amount` (PR 3).
- Les tickets A4, A6, C1 et le « doc 07 » cités dans le doc de navigation sont absents du dépôt.

## Relevé des actions (PR 0)
Message de succès ajouté (`templates/components/_messages.html`, inclus dans `base.html`, `base_public.html` et les fragments `finance/_body`, `roadmaps/_body`, `documents/_document_lines`) :
- Finance : paiement ajouté, modifié, supprimé ; dépense ajoutée, modifiée, supprimée ; remboursement marqué ou annulé ; proposition acceptée ou refusée.
- Espace équipe (lien secret) : proposition envoyée, modifiée, retirée.
- Feuille de route : notes, élément ajouté, modifié, supprimé ; personne ajoutée depuis l'équipe ; contact de lieu ajouté, supprimé.
- Devis et factures : brouillon de devis ou de facture créé, brouillon d'avoir créé ; ligne ajoutée, modifiée, supprimée.
- Spectacles : suppression.
Déjà confirmées avant : dates (création, statut, prix, échéances, équipe, cachet, suppression), spectacles (création, modification), émission, acceptation, suppression de brouillon, partage de la feuille de route, tournées, documents joints, contacts et organisateurs.
Volontairement sans message : cases de la checklist d'une date, aperçus, téléchargements, formulaires invalides (leurs erreurs restent affichées dans le formulaire).

## Journal
- 2026-11-23 — Plan validé.
- 2026-11-23 — PR 0 implémentée (branche `feature/confirmations-actions`).
- 2026-11-23 — PR 1 (étape A) implémentée sur `feature/nav-menu-urls` : menu à 5 entrées, `active_menu`, `/social/`, `/bord/documents/`, `/bord/depenses/`, annuaire `/contacts/?type=`, redirections 301. Étape B (Ma structure) à faire sur la même branche.
- 2026-11-23 — PR 2 (étape B) implémentée sur la même branche : `/structure/` et ses six onglets, droits NAV-D4, redirections 301. Écarts : `member` ne modifie plus l'Équipe (lecture seule, comme NAV-D4) ; « Quitter cette structure » est sur la page Équipe pour un `member` ; Compte et offre regroupe exports, suppression et un texte « pas d'offre payante » ; onglet Documents = modèles de messages.
- 2026-11-23 — PR 1 + PR 2 terminées (tests, ruff, contrôle visuel 1440 et 375 px). Prêtes pour commit et PR.
