# État du projet — Bòrd Pro

**Mis à jour le 2026-11-05 (tout le code des chantiers en cours est fusionné et livré ; e-mails, stockage et domaine sont branchés ; restent Sentry, sauvegardes et le hors-code).** Page à lire en premier : ce qui est en cours, ce qui bloque, ce qui reste à faire. Le détail sprint par sprint est dans `feuille-de-route.md` ; ici, une page.

**Règle de tenue** : je mets cette page à jour à chaque PR fusionnée qui change une ligne ci-dessous (la date en tête fait foi).

## Où on en est en une phrase
Les neuf critères de la recette du MVP (`cahier-des-charges.md` §11) sont couverts par du code (1964 tests) et la refonte graphique V06 est terminée. L'application tourne sur Scalingo avec ses vrais services (e-mails Brevo, bucket Scaleway, adresse `app.bordpro.fr`). Il reste Sentry, les sauvegardes, de la validation par des professionnels et la recette, avant d'ouvrir à des testeurs.

## 1. En cours
| Sujet | État | Qui agit |
|---|---|---|
| Gestion sociale (informations d'équipe) | Faite (fiche, distribution, dépenses à rembourser) | — |
| Feuille de route enrichie, puis espace équipe (lien personnel) | Faits et fusionnés (PR 1 à 4). La déclaration de dépense par photo ne se livre qu'avec le bucket S3 ; à tester depuis un vrai téléphone | Utilisateur |
| Mise en page pour ordinateur (largeur 1440 px, deux colonnes, tableaux) | PR 1 à 4 faites (Bòrd, Accueil, Mes dates, fiche de date, listes, formulaires), PR 5 (éditeur de feuille de route avec aperçu) : fait, fusionné | — |
| Annuaire de contacts, rattachements multiples (contacts ↔ organisateurs et lieux) | Fait, fusionné ; migrations `addressbook/0013` à `0015` à appliquer à la première livraison (`migrate`) | Utilisateur |
| Code couleur de l'annuaire (contacts / organisateurs / lieux) et infobulles au survol | Fait, fusionné (PR #260) ; aucune migration | — |
| Annuaire : export et import CSV (demande de l'associé) | Faits, fusionnés ; aucune migration | — |
| Export iCal des dates (#271) | Fait, fusionné (2026-10-31) : fichier `.ics` pour une date ou toutes les dates à venir, sans aucun montant ; pas de lien d'abonnement ni de Google Agenda (Q12 écartée) ; aucune migration. Livré le 2026-11-01 (`v2026-11-01`) | — |
| CI sur `ubuntu-24.04` (#272) | Fait, fusionné : l'ancien `ubuntu-latest` ne trouvait plus un paquet de WeasyPrint | — |
| Onglet « Documents » (F-85, demande de l'associé) | Fait, fusionné (#275) et livré le 2026-11-02 (`v2026-11-02`) : documents émis, filtres type / période / spectacles ; aucune migration | — |
| Refonte visuelle des cartes de date (pastilles d'icône, couleurs de la charte) | Fait, fusionné (#277) et livré le 2026-11-02 (`v2026-11-02`) ; aucune migration | — |
| Raccourci « Feuille de route » et état du partage dans « Mes dates » | Fait, fusionné (#276) et livré le 2026-11-02 (`v2026-11-02`) : lien et interrupteur d'état (lecture seule) ; aucune migration | — |
| Retrait de la vue jetable `pdf-test/` | Fait (2026-11-01) : vue, route, gabarit et test supprimés ; les vrais PDF restent testés dans `documents` ; aucune migration | — |
| Charte v1.3 (logos, gimics, volets C/B/S/R) | Logos, puces de navigation, états vides, moment « Contrat signé », pastilles de volet, avancement de la date et tableau de bord en quatre blocs (page Bòrd) faits ; icônes de volet faites (Social et Régie à valider) ; page d'une date refondue en quatre volets (PR 1 et 2 sur 3 : page d'une date et icônes sur « Mes dates » ; suit le menu de navigation d'une date) ; restent le filigrane des PDF et l'icône RADAR ; aucune migration | Associé (icônes Social/Régie, fichier RADAR) |
| Charte graphique v1.0 (blanc & contrastes francs) | PR 1 à 4 faites ; audit axe relancé le 2026-10-29 (0 violation, `docs/technique/audit-accessibilite.md`) ; reste la revue des pages publiques à 375 px et les vérifications manuelles (clavier, lecteur d'écran, zoom 200 %) | Utilisateur |
| Demandes de la réunion du 2026-11-05 (retour, libellé, gestion d'équipe, formulaires organisateur et régie de tournée, documents pour l'artiste, gestion sociale par artiste, site vitrine) | Documentées (F-86 à F-93), une PR à la fois : liste dans `feuille-de-route.md`. **Faits** : F-86 retour, F-87 libellé, F-89 envoi du formulaire, F-92 notes et contacts, F-88 équipe de la date et cachets par date (migration `gigs/0011`, livrée avec `v2026-11-06`). F-93 onglet « Social » et export CSV pour la paie. F-90 régie de tournée (migration `roadmaps/0006`, livrée avec `v2026-11-06b`). Correction de sécurité (2026-11-06) : le jeton de l'espace personnel d'un membre (`/equipe/<jeton>/`) est maintenant masqué dans Sentry comme les autres liens secrets. F-91 documents pour l'artiste (documents téléversés et contrat signé montré à l'équipe ; livrés avec `v2026-11-06b`). Site vitrine en cours (2026-11-08 : page d'accueil refaite d'après la maquette, page Fonctionnalités refaite aussi ; page Contact refaite (demande d'invitation), les trois PR du site sont faites, puis style repris de la maquette de l'associé (`static/css/vitrine.css`) ; toujours fermé aux moteurs de recherche) | Claude, après accord sur chaque plan |


## 2. Déploiement (Scalingo, app `bordpro`)
Branches : `main` (travail) et `production` (livré). **Dernière livraison : `v2026-11-06b`** (2026-11-06, commit `2504df4`, migrations `roadmaps/0006` à `0008`), après `v2026-11-02`, `v2026-11-01` et `v2026-10-29` ; historique : `docs/technique/livraison.md`. Scalingo se déploie à la main depuis la branche **`production`** (jamais `main`). Aucune migration en attente (`roadmaps/0006` à `0008` s'appliquent au déploiement de `v2026-11-06b`).
Guide pas à pas pour toutes les étapes ci-dessous : `docs/technique/guide-mise-en-ligne.md`. Ce que la mise en place a appris : `docs/technique/services-production.md`.

Adresse de l'application : **`https://app.bordpro.fr`** (début novembre 2026). `bordpro.fr` reste libre pour le futur site vitrine. L'ancienne adresse `bordpro.osc-fr1.scalingo.io` répond encore.

| Étape | État | Bloqué par |
|---|---|---|
| Application en ligne, migrations automatiques | Fait | — |
| **Brevo** (e-mails de confirmation, mot de passe oublié, contact) | **Fait** : domaine authentifié (méthode manuelle chez OVH), clé SMTP sans expiration ; inscription et mot de passe oublié testés de bout en bout | — |
| Domaine sur Scalingo | **Fait** : `app.bordpro.fr`, certificat automatique, 3 variables d'adresse mises à jour | — |
| Bucket S3 privé (fichiers, PDF figés) | **Fait** : Scaleway, Paris (`fr-par`), projet dédié, application IAM `bordpro-app` ; PDF généré, contrat signé listé dans « Documents », bucket refusant l'accès direct | — |
| Compte administrateur | Fait, via la ligne de commande Scalingo | — |
| Sauvegardes de la base + test de restauration | **Fait** : quotidiennes (7 jours) et hebdomadaires (4 semaines) automatiques chez Scalingo, restauration d'une sauvegarde manuelle testée en local (PostgreSQL 17 en production, 16 en local). Reste, avant l'ouverture au public : une copie hors de Scalingo | — |
| Sentry (UE) | **Fait** : projet `bordpro`, hébergement UE, « Error monitoring » seul (les autres produits décochés), événement de test reçu sans donnée personnelle | — |
| Surveillance de disponibilité (UptimeRobot sur `https://app.bordpro.fr/`), tâche planifiée de purge | **Fait** : contrôle toutes les 5 minutes avec alerte par e-mail ; tâche `purge_deleted_tenants` à 3 h, lue par Scalingo dans `cron.json` (section « Tâches planifiées », en lecture seule dans l'interface) | — |
| `check --deploy` | **Fait** : aucun avertissement ; en-têtes (HSTS, X-Frame-Options, nosniff…), redirection HTTPS et cookie `Secure` vérifiés sur `app.bordpro.fr`. Pas de `Content-Security-Policy` (à étudier plus tard, réglage délicat avec HTMX et Alpine) | — |
| Recette §11 sur la production | **À faire** : grille dans `docs/technique/recette-production.md` | Utilisateur et associé |

**Il ne reste côté services que le contrôle final** (ci-dessous). Le lien d'espace équipe peut maintenant être donné (le bucket existe). La déclaration de dépense par photo est utilisable.

## 3. À développer avant d'ouvrir à des testeurs
Dans cet ordre :
1. ~~Fermer l'inscription publique~~ **Fait** (2026-10-25) : liste d'invités dans `/admin/`, procédure dans `docs/technique/services-production.md`. Compte administrateur créé sur la production.
2. ~~Erreur claire quand l'e-mail de confirmation échoue~~ **Fait** (2026-10-29).
3. ~~Mot de passe oublié : tester de bout en bout~~ **Fait** (2026-10-29), un défaut corrigé (e-mail d'invitation à s'inscrire envoyé aux adresses inconnues).
4. ~~Contrôle d'accès des téléchargements~~ **Fait** (2026-10-29) : aucun défaut, test dédié.
5. ~~Régime de TVA~~ **Fait** (2026-10-29) : un défaut corrigé (contrat n°1, « non assujetti » citait l'article 293 B). Les textes restent à faire valider par le comptable.
6. **Logo de la structure sur le PDF du contrat** : à confirmer avec l'associé que c'est voulu pour le MVP.

Rappels de l'Accueil regroupés à partir de trois du même genre (2026-10-29).

## 4. Hors code, mais conditionne le lancement
- Relecture professionnelle (comptable, juriste) des 4 modèles de contrat et des factures : **le point le plus sensible**.
- Structure juridique, CGU, registre RGPD.
- Recette réelle sur la production, puis 3 testeurs sans aide.
- Textes définitifs du site vitrine (associé), puis `SITE_INDEXABLE=True`. Maquette reçue le 2026-11-05 (`docs/marque/sources-associe/maquette-site-vitrine.html`) : design retenu, textes limités à ce qui existe ; page Tarifs plus tard (trois formules).
- Questions à l'associé : « n° de compte » de la fiche Équipe ; Q9 (modèle économique, bloque l'abonnement mais pas la bêta).
- Logo officiel (`LOGO_2.pdf`, vectoriel) et favicon simplifié 16 px : en attente du graphiste.

## 5. Après le MVP (décidé : rien n'est codé)
Choisi à partir des retours de la bêta (principe de la feuille de route, Phase 4).
- **RADAR de tournée et carte** (spécification : `specification-radar.md`). Proposition d'implémentation, à rediscuter le moment venu :
  1. Un seul moteur de règles qui alimente le panneau RADAR et le bloc « À traiter maintenant » de Bòrd (alertes recalculées, non stockées) ; sans migration.
  2. « Ignorer / marquer traité », prochaine action sur la date, dépenses prévues contre réelles (indicateur sur la dépense, pas de nouvelle table de lignes de budget).
  3. Tournée (modèle dédié) et vue chronologique.
  4. Géographie sans service externe : table locale des communes françaises, distances à vol d'oiseau étiquetées « indicatives », carte schématique ; demande de modifier `CLAUDE.md` §10.
  5. Plus tard : synthèse de tournée en PDF ou CSV, lien de partage, contacts à proximité.
  Points à trancher : modèle « tournée » tout de suite ou non, nouvelle app `radar` (à valider, `CLAUDE.md` §4), sens de « ignorée » et « traitée ».
- **Annuaire en vue carte** (demande de l'associé, 2026-10-29) : liste à gauche (contacts, lieux, organisateurs), plan à droite avec la position de chacun, les filtres de la liste changeant le plan. Décision : **après le MVP**, avec le RADAR. À prévoir : point géographique et géocodage des organisateurs (migration), un contact étant placé à l'endroit de son organisateur ou de son lieu ; bibliothèque de carte légère et tuiles OpenStreetMap (confidentialité et conditions d'usage à vérifier) ; modification de `CLAUDE.md` §10 sur accord.
- Invitation de collaborateurs (aujourd'hui une seule personne par structure) : candidate n°1 après la bêta.
- Abonnement et Stripe, facturation électronique (note de cadrage : `note-facture-electronique.md`), rappels automatiques, application installable (PWA), hiérarchie Projet/Spectacle (Q10).
