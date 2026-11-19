# Fonctionnalité : Ajustements avant la mise en production

## Objectif
Trois ajustements demandés avant le passage en production : aide à la saisie (bouton « ? ») et messages IBAN plus précis ; cachets de l'équipe visibles dans le Budget d'une date ; ligne « Total » (débit, crédit, solde) dans les « Opérations récentes » du Bord. Aucune migration dans ces trois PR (la migration `tenants/0021` de la Navette partira avec la prochaine livraison).

## Documents de référence
- CLAUDE.md (§6.2 : une seule fonction de solde, montants au centime, arrondi réservé à l'affichage)
- docs/produit/cahier-des-charges.md (F-57, F-58, F-93)
- docs/marque/charte-graphique.md (couleurs d'état jamais seules), docs/technique/verification-visuelle.md
- Code : apps/tenants/validators.py, templates/components/_field_p.html, templates/components/_sectioned_form.html, apps/finance/services.py (`gig_balance`), apps/finance/bord.py (`operations`), templates/tenants/_bord_results.html, templates/gigs/gig_detail.html, templates/gigs/_team.html

## Découpage en PR
- [x] PR 1 — Bouton « ? » d'aide à la saisie et messages IBAN
  - Objectif : composant `templates/components/_format_help.html` (bouton « ? », bulle avec la règle et un exemple, Alpine, `aria-expanded`, clavier) branché dans le rendu commun des champs ; champs : IBAN, BIC, SIRET, n° de TVA, code APE, n° de sécurité sociale, n° d'objet SACEM, code postal. IBAN : tirets et points acceptés comme séparateurs, messages précis (longueur attendue, vérifier chaque caractère O/0 et I/1), clé de contrôle toujours bloquante.
  - Fichiers : templates/components/, `_field_p.html`, `_sectioned_form.html`, apps/tenants/validators.py, formulaires concernés.
  - Tests : IBAN avec et sans espaces, avec tirets, clé fausse, longueur fausse ; présence du « ? » sur chaque champ listé.
  - Risques : rendu à vérifier dans un navigateur (bulle, clavier, mobile 375 px sur les pages publiques éventuelles).
- [x] PR 2 — Cachets visibles dans le Budget de la date
  - Objectif : `gig_balance` reçoit un champ `fees` (somme des « Montant brut » des membres de l'équipe de la date, dates annulées exclues) ; le volet Budget affiche « Dépensé » avec « dont dépenses saisies » et « dont cachets (équipe) », « Résultat » en tient compte ; avertissement (sans blocage) si une dépense « Cachets » est aussi saisie à la main sur la date.
  - Fichiers : apps/finance/services.py, templates/gigs/gig_detail.html, vue de la date.
  - Tests : cachets comptés, aucun cachet, date sans équipe, double compte signalé, isolation.
  - Risques : double compte ; montants exacts au centime.
- [ ] PR 3 — Bord : débit aligné et ligne « Total »
  - Objectif : la colonne « Débit » des « Opérations récentes » inclut les cachets (même calcul que PR 2) ; le tableau de bord et les exports CSV sont alignés sur cette définition ; ligne « Total » (débit, crédit, solde crédit − débit) sur toutes les dates de la période (pas seulement les 20 affichées), solde écrit « Excédent », « À l'équilibre » ou « Déficit » (jamais en couleur seule), version mobile incluse.
  - Fichiers : apps/finance/bord.py, templates/tenants/_bord_results.html, exports CSV, tableau de bord.
  - Tests : excédent, équilibre, déficit, période vide, filtre « dépense faite par », plus de 20 dates, isolation.
  - Risques : écart d'un euro possible entre le total et la somme des lignes arrondies (arrondi à l'affichage seulement) ; tests existants du Bord à adapter.

## Décisions prises
- 2026-11-19 — « Dépense Social absente du Budget » = le « Montant brut » des membres de l'équipe d'une date : il est calculé et ajouté à « Dépensé » (sans créer de dépense, sans migration), affiché en deux lignes.
- 2026-11-19 — Le Bord, le tableau de bord et les CSV adoptent la même définition du débit (PR 3), pour ne jamais afficher deux chiffres différents.
- 2026-11-19 — IBAN : la clé de contrôle reste bloquante ; l'erreur vue par l'utilisateur est « erreur de saisie » (clé fausse), pas un problème de format.
- 2026-11-19 — Champs avec bouton « ? » : IBAN, BIC, SIRET, n° de TVA, code APE, n° de sécurité sociale, n° d'objet SACEM, code postal.

- 2026-11-19 — Le « ? » est branché dans `_field_p.html` : il apparaît dans les formulaires à sections (structure, organisateur, lieu, équipe, spectacle). Les formulaires en `form.as_p` (onboarding, formulaires publics) n'ont pas l'aide.
- 2026-11-19 — Les cachets restent privés au propriétaire : `gig_balance(gig, with_fees=…)` ne les compte ni ne les affiche pour un membre simple (sinon il les déduirait du « Dépensé »). Le Budget d'un membre et celui du propriétaire peuvent donc différer.
- 2026-11-19 — La page « Paiements et dépenses » affiche la même ventilation que le Budget de la date.

## Points en suspens
- Bulle du « ? » non vérifiée dans un navigateur (affichage, clavier Échap) ; test de présence limité aux champs de « Ma structure ».
- « ? » absent des formulaires en `form.as_p` (onboarding, formulaires publics) : à ajouter ou non ?
- L'IBAN refusé est-il un IBAN d'exemple ou une faute de frappe ? Non reproduit avec un IBAN valide.
- PR 3 : reprendre la règle propriétaire / membre pour le débit du Bord, l'accueil (`overview.spent`) et les CSV.
- Rendu de la PR 2 (lignes en retrait, avertissement) non vérifié dans un navigateur.
- Total du Bord : écart d'arrondi possible d'un euro avec la somme des lignes.

## Journal
- 2026-11-19 — Plan validé.
- 2026-11-19 — PR 1 terminée : bouton « ? » et messages IBAN (tirets et points acceptés, longueur saisie indiquée).
- 2026-11-19 — PR 2 terminée : cachets de l'équipe comptés dans « Dépensé » du Budget (propriétaire seulement), avertissement de double compte.
