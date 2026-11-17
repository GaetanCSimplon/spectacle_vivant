# Documentation — Bòrd Pro

`CLAUDE.md` (racine du dépôt) donne les règles de travail ; ce dossier contient le reste.
**Règle : un sujet, un document de référence.** Un document daté ou fourni par l'associé n'est jamais la référence : on le range dans `archives/` ou `marque/sources-associe/`.

| Dossier | Contenu | Statut |
|---|---|---|
| `produit/` | Ce qu'on construit : **`etat-du-projet.md` (page à lire en premier : en cours, à faire, bloqué)**, `informations-a-completer.md` (**informations en attente de l’associé**), `cahier-des-charges.md`, `feuille-de-route.md`, `specification-onglet-bord.md` (associé), `indicateurs-bord.md`, `specification-checklist-contractualisation.md` (associé), `specification-radar.md` (associé, reportée après la bêta), `specification-feuille-de-route-type.md` (associé, source d'inspiration : seuls F-86 à F-93 sont retenus à ce jour) | Référence, tenue à jour |
| `marque/` | `charte-graphique.md` (charte appliquée dans le code, v3) ; fichiers de l'associé v1.0 du 26/10 : `BORD_PRO_charte_visuelle.html`, `BRD_PRO_design-tokens.css` (+ `.md`) | Référence |
| `marque/sources-associe/` | Brief de marque de l'associé (15/10), intact : source du nom, du ton et du slogan ; maquette du site vitrine (05/11, design retenu, textes à corriger) ; `charte-v1.3-pack-2026-11-04/` (pack de la charte v1.3 : logo 3, volets, gimics, jetons ; provisoire, voir `charte-graphique.md` §9) | Source, à analyser avant de modifier la charte |
| `technique/` | `architecture.md`, `guide-mise-en-ligne.md` (**mise en ligne pas à pas**), `livraison.md` (**branches `main` / `production`, liste de contrôle avant livraison**), `donnees-de-demonstration.md` (**commande `seed_demo` : structure fictive pour voir l'application en usage**), `audit-accessibilite.md` (**audit axe-core : méthode, résultats, limites**), `verification-visuelle.md` (**captures dans un vrai Chromium : méthode**), `services-production.md` (déploiement : choix et variables), `cas-d-usage-et-diagrammes.md` | Référence |
| `metier/` | `guide-metier.md`, `modele-spectacle.md`, `modeles-contrats/` | Fournis par le métier |
| `archives/` | Points d'étape datés (28/09, 07/10), réunion avec l'associé du 05/11 ; `spec-devis-factures-v2/` (spécification devis et factures v2 du 13/11 et ses deux modèles, livrés en 5 PR le 17/11) ; `charte-v06/` (charte V06 remplacée le 27/10) | Obsolètes, pour l'historique seulement |
