# Fonctionnalité : Navette sociale (export mensuel pour la paie)

## Objectif
Chaque mois, aider le propriétaire à vérifier le social de ses dates (écran « Vérifier mon social du mois »), puis lui remettre deux exports : un PDF « Navette sociale » (A4 paysage) et un CSV pour son prestataire de paie. Bòrd Pro ne fait ni bulletin, ni cotisation, ni déclaration ; le coût employeur est toujours une « estimation ». La Navette fait évoluer l'onglet « Social » existant (F-93).

## Documents de référence
- docs/fonctionnalites/Bord-Pro_Navette-sociale_spec.md (spécification, maquette `Bord-Pro_Navette-sociale_simulation_2026-11.pdf`)
- CLAUDE.md (§6.2, §6.3, §10)
- docs/produit/cahier-des-charges.md (F-06, F-93, Q4)
- docs/produit/feuille-de-route.md (sprint 3.18, section Radar)
- docs/marque/sources-associe/RADAR-PARATGE/02-RADAR-copilote.md et 03-PARATGE-agent.md
- docs/marque/charte-graphique.md, docs/technique/verification-visuelle.md
- Code existant : apps/tenants/social.py, apps/gigs/models.py (GigMember), apps/tenants/models.py (Person), apps/radar/rules.py

## Découpage en PR
- [ ] PR 1 — Cahier des charges et taux de repère
  - Objectif : inscrire la Navette (nouvelle fiche F-xx, offre Collectif, sans contrôle d'offre) au cahier des charges ; ajouter le taux de repère sur `Tenant` (0,45 par défaut, réglable) et la fonction unique `estimated_employer_cost(gross, rate)` dans `apps/finance/services.py`.
  - Fichiers : docs/produit/cahier-des-charges.md, apps/tenants/models.py + migration, formulaire « Ma structure », apps/finance/services.py.
  - Tests : arrondi au centime, « — » si brut vide, taux modifiable ; isolation (un tenant ne lit pas le taux d'un autre).
  - Documents à relire : 03-PARATGE-agent.md, CLAUDE.md §6.2.
  - Risques : migration (champ ajouté, rien de supprimé) ; mention « estimation » obligatoire ; plan à valider avant de coder.
- [ ] PR 2 — Heures et service `build_social_month`
  - Objectif : ajouter `hours` sur `GigMember` (techniciens) ; créer `build_social_month(tenant, year, month)` en faisant évoluer apps/tenants/social.py : regroupement par spectacle et n° d'objet, 1 cachet = 12 heures, totaux, contrôles de la section 3 (À compléter / Information / À vérifier). Une paie = un `GigMember` sur une date ; mois = `Gig.date`.
  - Fichiers : apps/gigs/models.py + migration, formulaire du membre de la date, apps/tenants/social.py.
  - Tests : mois vide, mois avec manques, date annulée, deux spectacles, conversion cachets → heures, défraiements séparés du brut ; isolation (le tenant B ne voit rien de A).
  - Documents à relire : spec Navette §3 et §6, sprint 3.18.
  - Risques : données sensibles réservées au propriétaire ; aucune donnée personnelle dans les logs ; migration.
- [ ] PR 3 — Écran « Vérifier mon social du mois »
  - Objectif : remplacer l'onglet Social par l'écran de la section 3 : liste par spectacle, état en toutes lettres, récapitulatif en haut, liens vers la fiche à corriger. Accès propriétaire seul.
  - Fichiers : apps/tenants/views.py, urls.py, templates/tenants/social*.
  - Tests : accès propriétaire seul, 404 pour le tenant B, liens de correction, fragments HTMX.
  - Documents à relire : charte graphique, verification-visuelle.md.
  - Risques : accessibilité (état jamais en couleur seule) ; contrôle visuel dans Chromium.
- [ ] PR 4 — Export CSV pour le prestataire
  - Objectif : remplacer le CSV F-93 par le CSV de la section 5 (colonnes de la spec, `reference_bordpro`, `statut_ligne`) ; garder BOM, protection contre les formules (`text()`) et nom `navette-sociale-AAAA-MM-<structure>.csv`. Le coût estimé n'y figure pas.
  - Fichiers : apps/tenants/social.py, vue d'export.
  - Tests : total CSV = total du service, caractères spéciaux, aucun n° de sécurité sociale dans les journaux ; export réservé au propriétaire ; isolation.
  - Documents à relire : spec Navette §5.
  - Risques : colonnes « à vérifier » (date de naissance, catégorie) ; format à valider avec un prestataire de paie.
- [ ] PR 5 — Export PDF « Navette sociale »
  - Objectif : PDF A4 paysage WeasyPrint (section 4) : page 1 essentielle, détail par spectacle, récap par personne, pied de page ; case « inclure les n° de sécurité sociale » décochée par défaut.
  - Fichiers : gabarit PDF et vue d'export, polices Archivo, Instrument Sans, IBM Plex Mono.
  - Tests : total PDF = total CSV, n° de sécurité sociale absent par défaut, mention « estimation » présente, nom du fichier, accès propriétaire seul, isolation.
  - Documents à relire : spec Navette §4, charte graphique, maquette PDF.
  - Risques : PDF (plan à valider avant de coder) ; confidentialité ; rendu à vérifier visuellement.
- [ ] PR 6 — Rappel Radar RAD-65 et suivi
  - Objectif : règle `rad_65` à l'affichage (à partir de J-10, au moins un engagement salarié, « à faire » ou « à compléter », fermée quand tout est complet) ; cases « Transmis à mon prestataire » / « Paie faite », historique des mois, mention « modifié depuis le dernier export ».
  - Fichiers : apps/radar/rules.py, modèle de suivi mensuel (`TenantOwnedModel`) + migration, vue d'historique, docs/produit/feuille-de-route.md.
  - Tests : avant/après J-10, mois sans engagement, alerte fermée si complet, isolation du suivi.
  - Documents à relire : 02-RADAR-copilote.md, spec Navette §2 et §6.
  - Risques : nouveau modèle (migration) ; isolation des tenants ; pas de `radar_daily` ni d'e-mail.

## Décisions prises
- 2026-11-12 — La Navette fait partie de Bòrd Pro, offre Collectif ; PDF en A4 paysage ; rappel via Radar (RAD-65), sans Celery ni Redis.
- 2026-11-18 — La Navette fait évoluer l'onglet Social existant (F-93) : l'écran et le CSV le remplacent.
- 2026-11-18 — Coût employeur estimé inclus, avec un taux de repère sur `Tenant` (0,45) et une fonction unique dans `apps/finance/services.py` (Paratge la réutilisera).
- 2026-11-18 — RAD-65 calculée à l'affichage (comme les règles V0), sans `Alert` ni `radar_daily` ; pas de contrôle « offre Collectif » avant la phase 5.1, accès propriétaire seul.
- 2026-11-18 — Une paie = un `GigMember` sur une date ; nouveau champ `hours` ; mois = `Gig.date`.
- 2026-11-18 — N° de sécurité sociale exclu du PDF par défaut (case pour l'inclure) ; format CSV livré selon la spec, à valider ensuite avec un prestataire.

## Points en suspens
- Définition d'une paie à faire confirmer par un gestionnaire de paie.
- Format CSV à valider avec un ou deux prestataires de paie du spectacle.
- Champs « à vérifier » : date de naissance, catégorie, fonction (`role`), cachets, brut par engagement : confirmés dans le code (`Person`, `GigMember`), reste `hours`.
- Engagement à cheval sur deux mois (`Gig.date` unique : sans objet tant qu'une date est un seul jour).
- RAD-54, 60 et 62 non codées : la Navette fait ses propres contrôles en attendant.
- Contrôle « offre Collectif » : à brancher avec la phase 5.1 (quotas et formules).

## Journal
- 2026-11-18 — Plan validé.
