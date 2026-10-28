# État du projet — Bòrd Pro

**Mis à jour le 2026-10-29 (tout le code des chantiers en cours est fusionné ; reste le déploiement et le hors-code).** Page à lire en premier : ce qui est en cours, ce qui bloque, ce qui reste à faire. Le détail sprint par sprint est dans `feuille-de-route.md` ; ici, une page.

**Règle de tenue** : je mets cette page à jour à chaque PR fusionnée qui change une ligne ci-dessous (la date en tête fait foi).

## Où on en est en une phrase
Les neuf critères de la recette du MVP (`cahier-des-charges.md` §11) sont couverts par du code (1856 tests) et la refonte graphique V06 est terminée. Un premier déploiement existe sur Scalingo avec des services provisoires. Il reste du durcissement, de la validation par des professionnels et la fin du déploiement, avant d'ouvrir à des testeurs.

## 1. En cours
| Sujet | État | Qui agit |
|---|---|---|
| Gestion sociale (informations d'équipe) | Faite (fiche, distribution, dépenses à rembourser) | — |
| Feuille de route enrichie, puis espace équipe (lien personnel) | Faits et fusionnés (PR 1 à 4). La déclaration de dépense par photo ne se livre qu'avec le bucket S3 ; à tester depuis un vrai téléphone | Utilisateur |
| Mise en page pour ordinateur (largeur 1440 px, deux colonnes, tableaux) | PR 1 à 4 faites (Bòrd, Accueil, Mes dates, fiche de date, listes, formulaires), PR 5 (éditeur de feuille de route avec aperçu) : fait, fusionné | — |
| Annuaire de contacts, rattachements multiples (contacts ↔ organisateurs et lieux) | Fait, fusionné ; migrations `addressbook/0013` à `0015` à appliquer à la première livraison (`migrate`) | Utilisateur |
| Code couleur de l'annuaire (contacts / organisateurs / lieux) et infobulles au survol | Fait, fusionné (PR #260) ; aucune migration | — |
| Charte graphique v1.0 (blanc & contrastes francs) | PR 1 à 4 faites ; reste la revue des pages publiques à 375 px (utilisateur) et l'audit axe | Claude |

## 2. Déploiement (Scalingo, app `bordpro`)
Branches : `main` (travail) et `production` (livré, créée le 2026-10-28, identique à `main` pour l'instant) ; procédure et liste de contrôle : `docs/technique/livraison.md`. **À faire côté Scalingo** : suivre la branche `production`. Première livraison : à décider, après sauvegarde de la base.
Guide pas à pas pour toutes les étapes ci-dessous : `docs/technique/guide-mise-en-ligne.md`.

Premier déploiement réussi le 2026-10-22 sur `bordpro.osc-fr1.scalingo.io` (adresse temporaire). Variables S3 et e-mail encore à `placeholder`.

| Étape | État | Bloqué par |
|---|---|---|
| Application en ligne, migrations automatiques | Fait | — |
| **Brevo** (e-mails de confirmation d'inscription, formulaire de contact) | **Point d'arrêt** : sans lui l'inscription renvoie une erreur 500 | DNS de `bordpro.fr` à valider par l'associé |
| Domaine `bordpro.fr` branché sur Scalingo | À faire | L'associé (DNS), puis changer les 3 variables d'adresse |
| Bucket S3 privé (fichiers, PDF figés) | À faire | Utilisateur (compte Scaleway ou OVH, région UE) |
| Sentry (UE), sauvegardes + test de restauration, surveillance de disponibilité, tâche planifiée de purge | À faire | Après Brevo et S3 |
| `check --deploy`, recette §11 sur la production | À faire | Claude, en fin de parcours |

## 3. À développer avant d'ouvrir à des testeurs
Dans cet ordre :
1. ~~Fermer l'inscription publique~~ **Fait** (2026-10-25) : liste d'invités dans `/admin/`, procédure dans `docs/technique/services-production.md`. Il faudra créer un compte administrateur sur la production.
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
- Textes définitifs du site vitrine (associé), puis `SITE_INDEXABLE=True`.
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
- Invitation de collaborateurs (aujourd'hui une seule personne par structure) : candidate n°1 après la bêta.
- Abonnement et Stripe, facturation électronique, rappels automatiques, export iCal, application installable (PWA), hiérarchie Projet/Spectacle (Q10).
