# Fonctionnalité : Refonte UX de la fiche date et des chiffres (audit du 12/11)

## Objectif
Appliquer les priorités P1 de l'audit UX/UI du 12/11/2026 et les maquettes 1 (Mes dates) et 4 (fiche date) : des chiffres qui disent la même chose partout, un seul endroit de saisie pour les cachets, une checklist qui se coche toute seule, une fiche date en volets C/B/S/R empilés, et plus de ressaisie dans « Compléter le contrat ». Les maquettes 2 (Mon équipe) et 3 (Navette sociale) reprennent l'existant : aucune refonte.

## Documents de référence
- docs/produit/sources-associees/Bord-Pro_Audit-UX-UI_2026-11-12.md
- docs/produit/sources-associees/maquettes/ (1_mes-dates, 4_fiche-date ; 2 et 3 en comparaison)
- CLAUDE.md (§6.1, §6.2, §6.3, §9, §10)
- docs/produit/cahier-des-charges.md (F-83 checklist, F-93, F-94)
- docs/produit/bord-pro-architecture-navigation.md (C1, fiche date)
- docs/fonctionnalites/bord-pro-navigation.md et navette-sociale.md
- docs/produit/specification-checklist-contractualisation.md
- docs/marque/charte-graphique.md, docs/technique/verification-visuelle.md
- docs/produit/feuille-de-route.md

## Découpage en PR
- [x] PR 1 — Libellés financiers et base HT/TTC (I1, I3, I5, UX-01)
  - Objectif : « Reste prévu » (prévu − frais) et « Reste réel » (encaissé − dépensé), toujours côte à côte, sur Accueil, Bòrd, fiche date et Paiements et dépenses. Synthèses en HT ; TTC seulement sur factures et paiements, toujours écrit. Compteur de Mes dates = cartes affichées avec les filtres.
  - Fichiers : templates/core/home.html, templates/tenants/_bord_results.html, templates/gigs/gig_detail.html, templates/finance/_body.html, apps/finance/services.py (GigBalance), liste des dates.
  - Tests : un seul calcul (`gig_balance`) pour tous les écrans ; libellés présents ; compteur = nombre de cartes avec filtres ; montants au centime.
  - Documents à relire : audit I1 à I3, I5 ; CLAUDE.md §6.2 ; maquettes 1 et 4.
  - Risques : comparer des montants sur la même base (HT/TTC) ; « Reste réel » absent de la maquette 1, à arbitrer.
- [x] PR 2 — Rattachement à la date de prestation (I2)
  - Objectif : la carte Budget de Bòrd rattache prévu et facturé à la date de prestation ; l'acompte d'une date 2027 sort du facturé 2026. La vue trésorerie reste séparée.
  - Fichiers : apps/finance, apps/tenants (agrégats du Bòrd).
  - Tests : acompte d'une date 2027 absent du facturé 2026 ; vue trésorerie inchangée ; isolation des tenants.
  - Documents à relire : audit I2 ; docs/produit/indicateurs-bord.md ; recette BRD-02/04.
  - Risques : changement de chiffres déjà affichés ; rien de stocké, aucune migration.
- [x] PR 3 — Cachets depuis Social (I4, UX-02)
  - Objectif : ligne « Cachets (depuis Social, estimé) » du budget de la date calculée depuis le brut de l'équipe, avec coût employeur estimé (`estimated_employer_cost`, mention « estimation »). Plus de saisie manuelle dans la catégorie « Cachets » pour les nouvelles dépenses ; les anciennes restent en lecture avec un avertissement, sans suppression.
  - Fichiers : formulaire de dépense, apps/finance/services.py, templates/finance/_body.html, fiche date.
  - Tests : catégorie retirée du formulaire ; ancienne dépense conservée et signalée (`fees_double_count`) ; montants au centime ; un `member` ne voit pas les cachets ; isolation.
  - Documents à relire : audit I4, UX-02 ; navette-sociale.md ; CLAUDE.md §6.1, §6.2, §10.
  - Risques : fuite des cachets vers un `member` ; aucun calcul de charges réelles.
- [x] PR 4 — Checklist automatique (I7, UX-03)
  - Objectif : service qui calcule l'état des cases d'après les données (contrat généré / signé, devis, factures émises, paiements reçus, feuille de route partagée). Les cases manuelles (DPAE, rider, fiche technique, archivage…) restent enregistrées. Une case automatique l'emporte sur l'ancienne coche manuelle. Mise à jour de F-83 dans le cahier des charges.
  - Fichiers : apps/gigs/checklist.py, docs/produit/cahier-des-charges.md.
  - Tests : date signée, facturée et payée → cases cochées ; date vide → rien ; case manuelle conservée ; isolation.
  - Documents à relire : specification-checklist-contractualisation.md ; F-83 ; audit I7.
  - Risques : vérifier si l'app sait réellement « contrat envoyé » (sinon la case reste manuelle) ; pas de migration (champ JSON).
- [x] PR 5 — Fiche date, première partie : volets C et B, « À faire maintenant »
  - Objectif : volets C · Contrats et B · Budget empilés avec la checklist intégrée, bandeau « À faire maintenant », colonne de droite (contacts, documents, dernières actions). Un seul bouton corail par écran.
  - Fichiers : templates/gigs/gig_detail.html et fragments.
  - Tests : chaque volet rend ses cases et ses liens d'action ; 404 pour le tenant B ; accès `member`.
  - Documents à relire : maquette 4 ; charte ; verification-visuelle.md ; audit UX-04.
  - Risques : plus grosse refonte de gabarit ; contrôle visuel dans Chromium à 1440 px ; liens profonds existants.
- [x] PR 6 — Fiche date, deuxième partie : volets S et R, retrait de la modale (I6, UX-04, UX-14)
  - Objectif : volet S · Social (« Équipe ajoutée », « Infos de paie complètes ») et volet R · Régie (feuille de route remplie, partagée, programme). Suppression de la modale de checklist et du bouton flottant. Lettre S partout dans l'avancement.
  - Fichiers : gig_detail.html, templates/gigs/_checklist_*.html, _volet_*.html.
  - Tests : « Infos de paie complètes » incomplète tant que adresse ou date de naissance manquent ; anciennes URL de la checklist toujours répondues.
  - Documents à relire : maquette 4 ; audit I6 ; apps/radar (liens vers la checklist).
  - Risques : liens et alertes Radar qui pointent vers la checklist.
- [ ] PR 7 — Compléter le contrat sans ressaisie (UX-05, UX-06)
  - Objectif : horaires lus dans la feuille de route ; SIRET, APE et représentant lus dans la fiche de l'organisateur, en lecture avec un lien « modifier ». Enregistrement automatique avant « Envoyer un formulaire à l'organisateur ».
  - Fichiers : GigCompletionForm et sa page (apps/documents).
  - Tests : valeurs non saisissables ; PDF du contrat inchangé pour les mêmes données ; enregistrement avant envoi ; isolation.
  - Documents à relire : docs/metier/sources-associees/03_specification_DEV_contrats_cession.md ; audit UX-05, UX-06.
  - Risques : touche à la génération du contrat (PDF) : plan de cette PR à faire valider avant de coder (CLAUDE.md §9).

## Décisions prises
- 2026-11-24 — Fiche date : volets C/B/S/R empilés comme la maquette 4, pas d'onglets (pas de fragment HTMX par onglet, sous-menu latéral conservé). Ticket C1 du doc de navigation tranché en ce sens.
- 2026-11-24 — Checklist : F-83 est modifié ; les cases que l'app sait déjà se cochent seules, les cases manuelles rejoignent leur volet, la modale disparaît.
- 2026-11-24 — Périmètre : UX-01 à UX-06 (P1) et maquettes 1 et 4 seulement ; UX-07 à UX-19 et I8 hors de cette fonctionnalité.
- 2026-11-24 — Chiffres : « Reste prévu » et « Reste réel » côte à côte ; vue activité rattachée à la date de prestation, vue trésorerie à part.
- 2026-11-24 — Cachets : calculés depuis Social ; anciennes dépenses « Cachets » gardées en lecture avec avertissement, sans suppression ni migration.
- 2026-11-24 — PR 1 : « Reste prévu » (prix HT − dépensé) et « Reste réel » (TTC encaissé − dépensé) viennent de deux fonctions uniques (`remaining_planned`, `remaining_real`, `apps/finance/services.py`). Sur Mes dates, ils sont ajoutés au bloc des chiffres. « Reste réel » reste TTC, écrit sur l'écran. Un `member` n'a pas les cachets dans ces restes.
- 2026-11-24 — PR 1 : le compteur de Mes dates compte les cartes affichées (annulées comprises) et suit les filtres ; `count_gigs_for_year` reste pour le futur quota freemium.

- 2026-11-24 — PR 3 : le coût employeur estimé (`fees_employer_cost`, taux de repère de la structure) reste une ligne d'information, jamais ajoutée à « Dépensé » ni aux « Reste ». La catégorie « Cachets » n'est plus proposée aux nouvelles dépenses ; une ancienne dépense reste modifiable et signalée.

- 2026-11-24 — PR 4 : 9 cases automatiques (`automatic_items`) ; « Devis envoyé » = devis émis (l'app ne trace pas l'envoi). L'automatique l'emporte sur l'ancienne coche manuelle (ignorée, gardée en base). L'export des checklists utilise le même calcul.
- 2026-11-25 — PR 5 : cases dans les volets C (devis, contrat, fiche technique, rider) et B (factures d'acompte et de solde) via `VOLET_ITEMS` ; la modale de la fiche (`?restantes=1`) ne liste que les autres, sans « Réinitialiser ». Les compteurs des volets restent ceux de l'avancement (Mes dates). Prix et échéances restent dans « La date ». Le bloc de droite garde le titre « Suivi de la date ».
- 2026-11-25 — PR 6 : « Infos de paie complètes » suit la règle de Bòrd › Social (`missing_items`), pas seulement l'adresse et la date de naissance. Cases de clôture dans la carte « La date ». « Réinitialiser » supprimé avec la modale. L'ancienne adresse `/checklist/` mène à la fiche date. La case « Feuille de route envoyée » n'est plus affichée (dite par « Feuille de route partagée »), elle reste dans l'export.

## Points en suspens
- Contrôle visuel dans Chromium à 1440 px des libellés longs « Reste réel (TTC encaissé − dépensé) » (PR 1, à faire à la main).
- Page vitrine `templates/site/home.html` : « Ce qu'il reste après ces frais » à aligner (marketing, hors PR 1).
- Suite de tests : 26 min. Voir `--reuse-db`, xdist et marqueur `slow` (PR à part).
- Que devient une ancienne coche manuelle sur une case devenue automatique : l'automatique l'emporte (à confirmer en recette).
- Hors fonctionnalité : I8 (« Client actif » automatique), UX-07 à UX-13, UX-15 à UX-18.
- PR 5 : les boutons flottants (Radar, checklist) recouvrent « Documents » à 1440 px et le bandeau à 375 px ; celui de la checklist est parti en PR 6, celui du Radar reste.
- PR 5 : le compteur d'un volet (0/3, 0/2) peut différer du nombre de cases affichées.
- PR 5 : le bandeau répète le même texte dans le titre et le bouton ; titres plus descriptifs possibles.
- PR 5 : « Date créée » affichait « à venir » sur une date de test (calcul non modifié, à vérifier sur une vraie date).
- `test_a_plain_member_never_sees_the_fees` a échoué une fois puis réussi : probablement instable (cherche « 145 » dans toute la page, jetons compris), à corriger à part.
- PR 6 : les cases de clôture laissent un espace large avant « Autres actions » (carte « La date »).
- PR 6 : non repris de la maquette 4 : « Envoyer le formulaire à… », « Copier le lien », « Ajouter un créneau », « Demander la régie » dans les volets.
- PR 6 : le volet S affiche 0/2 ou 1/2 pour des dates, même passées, qui étaient complètes.

## Journal
- 2026-11-24 — Plan validé.
- 2026-11-24 — PR 1 terminée : libellés « Reste prévu » / « Reste réel », base HT/TTC, compteur de Mes dates. 2942 tests verts.
- 2026-11-24 — PR 2 : déjà couverte par BRD-02/03/04 (Bòrd, vue activité rattachée à la date du concert, vue trésorerie à part). Reste : la ligne « Facturé en 2026 (caisse) » de l'Accueil suit encore la date de facture, étiquetée comme telle.
- 2026-11-24 — PR 3 terminée : cachets depuis Social, coût employeur estimé en information.
- 2026-11-24 — PR 4 terminée : checklist automatique.
- 2026-11-25 — PR 5 terminée : volets C et B, bandeau « À faire maintenant », colonne de droite. 2963 tests verts.
- 2026-11-25 — PR 6 terminée : volets S et R, modale de checklist supprimée. 2956 tests verts.
