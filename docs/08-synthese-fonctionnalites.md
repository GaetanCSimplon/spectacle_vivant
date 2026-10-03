# Synthèse des fonctionnalités réalisées

> **Situation au 2026-10-01.** Phase 3 (MVP), Sprints 3.1 à 3.5 réalisés, hors quelques restes listés au §7.
> Ce document décrit **ce qui existe dans le code** ; les intentions et le périmètre complet restent dans `03-cahier-des-charges.md` et `04-feuille-de-route.md`.
> Pour les schémas : `09-cas-d-usage-et-diagrammes.md`. Pour une version non technique : `10-resume-simple.md`.

Légende : ✅ fait · 🟡 partiel · ⬜ pas encore fait.

---

## 1. Vue d'ensemble

| Module (cahier des charges) | Contenu | État |
|---|---|---|
| M0 — Comptes et onboarding | Inscription, connexion, création de la structure, isolation des données | ✅ (confirmation d'e-mail 🟡) |
| M8 — Ma structure | Informations légales de l'utilisateur | ✅ (logo, code APE ⬜) |
| M1 — Carnet d'adresses | Organisateurs, lieux, contacts | ✅ |
| M2 — Spectacles | Fiche spectacle, fiche technique, rider, lien EPK | ✅ |
| M3 — Dates | Création guidée, statuts, option, liste, calendrier, annulation | ✅ |
| M4 — Contrat de cession | Génération PDF, versions, numérotation, signature, PDF signé | ✅ |
| M5 — Devis et factures | Devis, factures (acompte, solde, totale), avoirs, PDF | ✅ (relecture professionnelle ⬜) |
| M6 — Feuille de route | Créneaux, lien secret, vue mobile, PDF | ✅ (test à 375 px et rendu du PDF à contrôler à la main) |
| M7 — Finances | Paiements, dépenses, tableau de bord, export CSV | ✅ (ouverture des CSV dans Excel à contrôler à la main) |
| M9 — Légal et RGPD | Pages légales, export et suppression de compte | ⬜ (Sprint 3.8) |

**Le parcours central fonctionne de bout en bout** : créer une date → la compléter → générer le contrat → le faire signer → facturer l'acompte puis le solde → télécharger les PDF. Il s'y ajoute la feuille de route partagée par lien secret ; le maillon suivant (paiements) n'est pas encore là.

---

## 2. Fonctionnalités par module

### M0 — Comptes, onboarding, isolation
- **Inscription / connexion** par e-mail (`django-allauth`), modèle `User` personnalisé.
- **Onboarding en un écran** (nom, forme juridique, régime de TVA) : crée la structure (`Tenant`) et le lien propriétaire (`Membership`). Tout utilisateur connecté sans structure y est redirigé automatiquement.
- **Isolation des structures** : chaque donnée métier appartient à une structure et n'est jamais visible d'une autre (voir §4).
- **Navigation** : 5 entrées (Accueil · Mes dates · Spectacles · Contacts · Ma structure), barre basse sur mobile.
- 🟡 Mot de passe oublié non testé à la main ; confirmation d'e-mail non activée (prestataire d'e-mails à choisir).

### M8 — Ma structure
- Nom, forme juridique, adresse, SIRET, régime de TVA (assujetti / franchise en base / non assujetti), **taux de TVA**, **numéro de TVA**, **IBAN** (normalisé et contrôlé : format et clé de contrôle), licence d'entrepreneur de spectacles, représentant légal et qualité, ville du tribunal compétent, désignation dans le contrat (« L'artiste » ou « Le producteur »).
- Le propriétaire modifie ; un simple membre consulte seulement.
- ⬜ Logo, code APE, forme juridique en liste de choix.

### M1 — Carnet d'adresses
- **Organisateurs** (le client à facturer), **lieux** et **contacts** : création, modification, fiche de détail, suppression.
- Un contact est rattaché **soit** à un organisateur, **soit** à un lieu (contrainte en base).
- La fiche d'un organisateur ou d'un lieu montre ses contacts et l'historique de ses dates.
- **Recherche en direct** (HTMX, sans rechargement) sur les trois listes.
- Suppression **bloquée** si l'organisateur ou le lieu est utilisé par une date.

### M2 — Spectacles
- Titre, nom du groupe, distribution, durée, effectif, numéros SACEM et d'objet, **fiche technique** (texte et PDF), **rider**, **lien EPK**.
- Les fichiers ne sont jamais accessibles par leur adresse directe : ils passent par une vue qui contrôle la structure.
- Suppression bloquée si une date utilise le spectacle.

### M3 — Dates
- **Assistant de création en 5 étapes** (spectacle → organisateur → lieu → détails → récapitulatif), avec création « à la volée » d'un spectacle, d'un organisateur ou d'un lieu.
- **Statuts** : option → confirmée → signée, et annulée. Les changements passent par un service qui vérifie la transition, sous verrou (un double clic ne rejoue rien).
- **Fin d'option** : alerte orange à 7 jours ou moins, rouge si expirée. Rien n'est annulé automatiquement.
- **Liste** filtrable (statut, mois, spectacle) en direct, avec section « Annulées » et comptage « N dates en 2026 » (annulées exclues).
- **Calendrier mensuel** : grille côté serveur, pastilles colorées par statut, navigation de mois en mois.
- **Page de détail** : infos, statut, « prochaine action », documents.
- **Annulation** (avec confirmation, historique conservé) et **réactivation**.
- **Compléter la date** : une page pour renseigner tout ce que les documents demandent (horaires, invitations, lieu de signature, acompte, conditions particulières, SACEM, jauge, signataire…). Un champ vide s'affiche en pointillés dans le contrat.

### M4 — Contrat de cession
- **PDF** aligné sur le modèle du métier (9 articles, plus un article « Conditions particulières » s'il est rempli). Formulation adaptée (« l'artiste » ou « le producteur »), mention de TVA selon le régime.
- **Aperçu** à tout moment, sans rien enregistrer.
- **Versions** : « Générer une nouvelle version » ajoute un PDF, les anciens sont conservés et téléchargeables.
- **Référence** de contrat unique, sans trou, par structure et par année (`C-2026-007`).
- **Marquage « signé »** : la signature se fait hors de l'application ; l'écran de confirmation fige la dernière version, passe le contrat et la date à « signée ». **PDF signé facultatif** (vrai PDF, 10 Mo maximum), ajoutable ensuite une seule fois.
- Un contrat signé ne peut plus être régénéré, modifié ni re-signé. Une date signée, annulée puis réactivée revient à « signée ».
- Une date annulée garde son contrat consultable mais n'en génère plus.

### M5 — Devis, factures, avoirs
- **Page « Devis et factures » d'une date** : prix prévu, déjà facturé, reste à facturer.
- **Création** d'une facture d'acompte (30 % par défaut, modifiable par date), de solde (le reste à facturer), totale, ou d'un devis, avec ligne suggérée.
- **Brouillon éditable** : lignes ajoutées, modifiées, supprimées en direct, totaux recalculés. Le champ TVA n'apparaît que pour une structure assujettie.
- **Contrôle avant émission** : liste de ce qu'il manque (adresse, SIRET, numéro et taux de TVA, adresse de facturation de l'organisateur).
- **Émission** (écran de confirmation) : numéro `F-2026-0001` sans trou, informations légales **copiées** dans le document, PDF créé et stocké. Un document émis est **immuable**.
- **Avoirs** : négatifs, liés à la facture d'origine, jamais plus que son montant ; un avoir total marque la facture « Annulée par avoir ». Même série de numéros que les factures.
- **Devis** : série de numéros séparée (`D-2026-0001`), validité 30 jours, cadre « Bon pour accord ».
- **PDF** : mentions légales (voir réserves au §7), TVA par taux, IBAN, conditions de paiement sur les factures.

---

## 3. Règles de gestion appliquées

| Règle | Où elle est garantie |
|---|---|
| RG-01 Données propres à une structure | `TenantOwnedModel` + `TenantScopedMixin` + test de couverture |
| RG-03 Contact : un parent, pas deux | contrainte en base + validation |
| RG-04 Une date annulée ne revient pas toute seule | `reactivate_gig` explicite |
| RG-05 Numéros sans trou | `select_for_update` sur la séquence, dans la transaction d'émission ; un échec rend le numéro |
| RG-06 Facture émise immuable | refus au niveau du modèle (document et lignes), pas seulement dans l'interface |
| RG-07 Données légales figées à l'émission | `issuer_snapshot` / `customer_snapshot`, PDF construit depuis ces copies |
| RG-08 Contrat signé : PDF figé | `signed_version` protégée contre la suppression, génération refusée |
| RG-10 Montants en `Decimal`, deux décimales | partout ; TVA par taux, arrondi « moitié au-dessus », avoir symétrique |
| RG-12 Concert gratuit : prix des places à 0 | calculé à l'enregistrement |

⚠️ RG-02 (lieu facultatif en option) n'est pas appliquée : `Gig.venue` est obligatoire. Écart connu, non traité.

---

## 4. Sécurité et isolation des structures

- **Principe** : toute vue qui lit ou modifie des données filtre sur la structure de l'utilisateur ; le formulaire ne laisse jamais choisir la structure.
- **Tests d'isolation** : chaque modèle métier en a au moins un ; `test_tenant_coverage.py` échoue sinon. Pour la facturation, chaque route est testée avec une autre structure (404).
- **Accès croisés** : un document n'est joignable que par sa propre date ; une ligne que par son propre document.
- **Fichiers** : contrats, PDF signés, PDF de factures, fiches techniques et riders sont envoyés par des vues protégées. Aucune adresse `/media/` n'est servie, même en développement. Chemins non devinables (`<dossier>/<uuid>/…`).
- **Stockage** : disque local en développement ; bucket S3 européen **privé** en production (réglage prêt, bucket à créer).
- **Sans connexion** : toutes les pages exigent la connexion (sauf inscription et connexion).
- **Secrets** : uniquement par variables d'environnement.

---

## 5. Qualité et outillage

| Élément | État |
|---|---|
| Tests automatisés | **535** (471 sur `main` + ceux des PR en attente), tous verts |
| Qualité du code | `ruff` (contrôle et format), `pre-commit` |
| Intégration continue | GitHub Actions : `ruff`, `pytest` avec PostgreSQL, absence de migration manquante, `check --deploy` |
| Branche `main` | protégée, une PR par sujet, CI verte avant fusion |
| Taille | environ 3 750 lignes de code applicatif et 6 200 lignes de tests (hors migrations) |
| Historique | 94 commits, 34 PR fusionnées entre le 21/09 et le 01/10/2026 |
| Migrations | `tenants` 5 · `catalog` 4 · `addressbook` 4 · `gigs` 5 · `documents` 6 |

PR en attente de fusion : **#112** (écrans de facturation) et **#113** (PDF de facture), cette dernière empilée sur la première.

---

## 6. Modèle de données réalisé

`User`, `Membership`, `Tenant` · `Show`, `Promoter`, `Venue`, `Contact` · `Gig` ·
`Contract`, `ContractVersion`, `ContractSequence` · `Invoice`, `Quote`, `DocumentLine`, `DocumentSequence`.

Schéma des relations : voir `09-cas-d-usage-et-diagrammes.md` §6. La description champ par champ est dans le cahier des charges §9 (aligné sur le code le 01/10).

**Écarts avec le cahier des charges initial** (déjà reportés dans le §9) : `ContractVersion` et `reference` remplacent `Contract.pdf_file`/`number` ; `DocumentSequence` remplace `InvoiceSequence` ; un avoir est un type de facture ; la TVA est portée par `Tenant.vat_rate`.

---

## 7. Ce qui reste à faire et points d'attention

**Reste du MVP**
- Sprint 3.8 — Pages légales, export et suppression de compte, audit d'isolation complet, sauvegardes, recette.
- Restes du 3.1 : confirmation d'e-mail, logo, code APE.

**Avant d'utiliser de vraies factures**
- Relecture par un professionnel (comptable) du PDF de facture et du contrat. Les PDF portent un bandeau « Modèle provisoire — non relu par un professionnel » (un seul réglage à retirer ensuite).
- Conditions de paiement (pénalités, indemnité de 40 €) à discuter avec l'associé puis à faire valider.
- Mention de TVA du cas « non assujetti » : texte provisoire (questions Q13 / F-56).
- ⚠️ **Les PDF du MVP ne remplacent pas la plateforme agréée de facturation électronique** (obligation à vérifier, prévue en Phase 5). L'application ne doit pas se dire « conforme » avant cette connexion.

**Déploiement** (rien n'est en ligne à ce jour) : compte Scalingo, bucket S3 privé, prestataire d'e-mails, domaine, Sentry. Liste complète : `06-services-production.md`.

**Questions de fond ouvertes** (cahier des charges §14) : Q9 modèle économique, Q10 hiérarchie Projet/Spectacle (détail : `07-modele-spectacle.md`), Q12, Q13, Q14, Q15 (sens du mot « Structure »).

**Points techniques notés** : `Gig.venue` obligatoire (RG-02) ; un test de liste de dates utilise `date.today()` au lieu de `timezone.localdate()` (risque de test instable passé minuit UTC) ; avertissement de dépréciation Django 6 sur `FORMS_URLFIELD_ASSUME_HTTPS` (sans effet sous Django 5.2) ; la mise en page des PDF de facture reste à vérifier à l'œil.
