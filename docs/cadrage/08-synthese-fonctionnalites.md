# Synthèse des fonctionnalités réalisées

> **Situation au 2026-10-07.** Phase 3 (MVP) : Sprints 3.1 à 3.7 réalisés, et le code du Sprint 3.8 (légal, sécurité, finition) aussi. Il reste la recette, les sauvegardes et la mise en ligne, qui attendent les comptes d'hébergement (§7).
> Ce document décrit **ce qui existe dans le code** ; les intentions et le périmètre complet restent dans `docs/cadrage/03-cahier-des-charges.md` et `docs/cadrage/04-feuille-de-route.md`.
> Pour les schémas : `docs/guides/09-cas-d-usage-et-diagrammes.md`. Pour une version non technique : `docs/cadrage/10-resume-simple.md`.

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
| M7 — Finances | Paiements, dépenses, bilan par date, tableau de bord, export CSV | ✅ (ouverture des CSV dans Excel à contrôler à la main) |
| M9 — Légal et RGPD | Pages légales, export et suppression de compte | ✅ (textes légaux provisoires, à compléter et à faire relire) |

**Le parcours central fonctionne de bout en bout** : créer une date → la compléter → générer le contrat → le faire signer → facturer l'acompte puis le solde → télécharger les PDF. Il se prolonge par la feuille de route partagée par lien secret, puis par les paiements reçus, les dépenses, le bilan de la date, le tableau de bord de l'accueil et les exports CSV. La partie légale (pages, export et suppression des données) est faite, ainsi que l'audit d'isolation, les réglages de production et les pages d'erreur en français. Il ne manque au MVP que la recette complète, les sauvegardes et la mise en ligne.

---

## 2. Fonctionnalités par module

### M0 — Comptes, onboarding, isolation
- **Inscription / connexion** par e-mail (`django-allauth`), modèle `User` personnalisé.
- **Onboarding en un écran** (nom, forme juridique, régime de TVA) : crée la structure (`Tenant`) et le lien propriétaire (`Membership`). Tout utilisateur connecté sans structure y est redirigé automatiquement.
- **Isolation des structures** : chaque donnée métier appartient à une structure et n'est jamais visible d'une autre (voir §4).
- **Navigation** : 5 entrées (Accueil · Mes dates · Spectacles · Contacts · Ma structure), barre basse sur mobile, lien « Aller au contenu » pour le clavier.
- **Pages d'erreur en français** : 404, 403, 500 et formulaire expiré (CSRF).
- 🟡 Mot de passe oublié non testé à la main ; confirmation d'e-mail non activée (prestataire d'e-mails à choisir).

### M8 — Ma structure
- Nom, forme juridique, adresse, SIRET, régime de TVA (assujetti / franchise en base / non assujetti), **taux de TVA**, **numéro de TVA**, **IBAN** (normalisé et contrôlé : format et clé de contrôle), licence d'entrepreneur de spectacles, représentant légal et qualité, ville du tribunal compétent.
- Dans le contrat, la structure est **toujours** désignée « Le producteur » (plus de choix depuis le 2026-10-07).
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
- **Page de détail** : infos, statut, « prochaine action », feuille de route, paiements et dépenses (encaissé, dépensé, résultat), documents.
- **Annulation** (avec confirmation, historique conservé) et **réactivation**.
- **Compléter la date** : une page pour renseigner tout ce que les documents demandent (horaires, invitations, lieu de signature, acompte, conditions particulières, SACEM, jauge, signataire…). Un champ vide s'affiche en pointillés dans le contrat.

### M4 — Contrat de cession
- **PDF** aligné sur le modèle du métier (9 articles, plus un article « Conditions particulières » s'il est rempli). Structure toujours désignée « LE PRODUCTEUR » (« L'ARTISTE » reste utilisé à l'article 4 pour les interprètes), mention de TVA selon le régime.
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
- **Statut « Payée »** : posé automatiquement quand les paiements atteignent le total (voir M7). Une facture payée reste créditable.

### M6 — Feuille de route
- **Éditeur** (`dates/<id>/feuille-de-route/`) : programme de la journée (créneaux triés par heure : arrivée, balances, repas, concert, départ, autre), hébergement, repas, équipe (nom, fonction, téléphone, e-mail), notes. Ajout, modification, suppression en direct (HTMX), avec repli sans JavaScript.
- **Pré-remplissage** : à la première ouverture, les créneaux Arrivée, Balances et Concert sont créés d'après les horaires de la date.
- **Partage par lien secret** : « Activer le partage » crée un jeton de 43 caractères (`token_urlsafe(32)`), « Copier le lien », « Arrêter le partage » le détruit. Réactiver crée un **nouveau** lien : l'ancien reste introuvable.
- **Page publique** (`feuille-de-route/<jeton>/`, **sans compte**) : lisible à 375 px, gros boutons « Appeler » (`tel:`), « Itinéraire » (lien OpenStreetMap, pas de service de cartes intégré) et « Copier l'adresse » (lieu et hébergements), export PDF. Jeton inconnu ou partage arrêté : 404.
- **Ce qui est exposé** : seulement une liste blanche (`public_context`) : spectacle et groupe, date, lieu (nom, adresse, accès, téléphone), programme, hébergement, repas, nombre de personnes, notes, équipe et contacts du lieu (nom, fonction, téléphone). **Jamais** : prix, conditions, contrat, factures, organisateur facturé, statut de la date, e-mails.
- **Protections** : en-têtes `Cache-Control: no-store`, `X-Robots-Tag: noindex`, `Referrer-Policy: no-referrer` (le jeton est dans l'adresse).
- **PDF** de la feuille de route : généré à la volée, depuis l'éditeur ou depuis le lien, jamais stocké.
- ⬜ Plan des lieux (aperçu d'un plan joint) : idée notée pour plus tard (Q16).

### M7 — Finances
- **Paiements** (page `dates/<id>/finances/`) : montant, date, mode (virement, chèque, espèces, carte, autre) sur une facture émise. Refusés : montant nul ou négatif, dépassement du reste à payer, paiement sur un avoir, un brouillon ou une facture annulée. Modifiables et supprimables ; le statut de la facture est recalculé sous verrou (`payée` ↔ `émise`).
- **Dépenses** : catégorie (cachets, transport, hébergement, technique, communication, autres), libellé, montant, date, justificatif facultatif (PDF, JPEG ou PNG vérifié sur le contenu, 10 Mo maximum, servi par une vue protégée, supprimé avec la dépense).
- **Bilan d'une date** : prévu, facturé, encaissé, reste à encaisser, dépensé, résultat (encaissé moins dépensé). Trois montants distincts (prévu / facturé / encaissé), en TTC pour être comparables, en euros entiers à l'affichage, au centime dans les calculs.
- **Tableau de bord** (page d'accueil) : facturé et encaissé de l'année en cours, factures à encaisser (reste dû, en retard ou échéance, total), dates confirmées à venir sans contrat généré, cinq prochaines dates.
- **Exports CSV** (`exports/`) : factures et avoirs émis, recettes, dépenses, sur la période choisie ; `;`, UTF-8 avec BOM, virgule décimale, dates jj/mm/aaaa ; les textes qui commenceraient par `=`, `+`, `-` ou `@` sont neutralisés contre les formules de tableur.

### M9 — Légal et RGPD
- **Pages légales** (`infos/mentions-legales/`, `infos/cgu/`, `infos/confidentialite/`) : accessibles sans connexion. Les textes sont des **gabarits provisoires** avec des « [À compléter] » ; ils doivent être renseignés et relus avant la mise en ligne.
- **Export des données** (`ma-structure/export-donnees/`) : un ZIP contenant des CSV (spectacles, organisateurs, lieux, contacts, dates, finances) et les fichiers stockés (contrats, PDF, justificatifs…).
- **Suppression de compte** (`ma-structure/supprimer/`) : réservée au propriétaire, qui confirme avec le nom de la structure et son mot de passe. **Délai de 30 jours**, pendant lequel la suppression peut être annulée (`ma-structure/annuler-suppression/`). Passé ce délai, la commande `purge_deleted_tenants` supprime tout (données et fichiers) ; elle est **à planifier en production** (`docs/guides/06-services-production.md`).
- **Départ d'un membre** (`ma-structure/quitter/`) : un membre peut quitter la structure ; le dernier propriétaire ne peut pas, il doit la supprimer ou la confier.
- ⚠️ La suppression emporte aussi les factures émises : la conservation légale de 10 ans reste à valider avec un comptable.

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
| RG-09 « Payée » seulement si paiements ≥ total | `finance/services.py`, sous verrou ; un surpaiement est même refusé |
| RG-10 Montants en `Decimal`, deux décimales | partout ; TVA par taux, arrondi « moitié au-dessus », avoir symétrique ; contrainte en base « montant > 0 » sur paiements et dépenses |
| RG-11 Le lien secret n'expose que la feuille de route | liste blanche `public_context`, testée sur le HTML et le PDF |
| RG-12 Concert gratuit : prix des places à 0 | calculé à l'enregistrement |
| F-57 Prévu / facturé / encaissé séparés | `gig_balance` : trois montants distincts, jamais fusionnés |
| F-58 Euros entiers à l'affichage seulement | arrondi dans les gabarits de synthèse, stockage et calculs au centime |
| Suppression de compte différée | `Tenant.deletion_requested_at`, délai de 30 jours, purge en ordre explicite (liens `PROTECT`) par `purge_deleted_tenants` |

⚠️ RG-02 (lieu facultatif en option) n'est pas appliquée : `Gig.venue` est obligatoire. Écart connu, non traité.

---

## 4. Sécurité et isolation des structures

- **Principe** : toute vue qui lit ou modifie des données filtre sur la structure de l'utilisateur ; le formulaire ne laisse jamais choisir la structure.
- **Tests d'isolation** : chaque modèle métier en a au moins un ; `test_tenant_coverage.py` échoue sinon. Pour la facturation, chaque route est testée avec une autre structure (404).
- **Audit d'isolation de toutes les URL** (`test_isolation_audit.py`) : chaque route est parcourue avec deux structures ; aucune faille trouvée. Une nouvelle route à identifiant doit y être déclarée, sinon le test échoue.
- **Accès croisés** : un document n'est joignable que par sa propre date ; une ligne que par son propre document.
- **Fichiers** : contrats, PDF signés, PDF de factures, fiches techniques, riders et justificatifs de dépense sont envoyés par des vues protégées. Aucune adresse `/media/` n'est servie, même en développement. Chemins non devinables (`<dossier>/<uuid>/…`).
- **Stockage** : disque local en développement ; bucket S3 européen **privé** en production (réglage prêt, bucket à créer).
- **Sans connexion** : toutes les pages exigent la connexion, sauf inscription, connexion, les pages légales et **la page publique de la feuille de route**, qui ne s'ouvre qu'avec son jeton secret (révocable, jamais un numéro). Pas de limitation de débit sur cette page (jeton de 256 bits) : à reconsidérer à la mise en ligne.
- **Jeton dans l'adresse** : Sentry est configuré sans données personnelles et masque le jeton ; au déploiement, ne pas activer le journal d'accès de gunicorn (le jeton y apparaîtrait).
- **Réglages de production** : proxy HTTPS, WhiteNoise, origines CSRF, journaux ; `check --deploy` propre.
- **Secrets** : uniquement par variables d'environnement.

---

## 5. Qualité et outillage

| Élément | État |
|---|---|
| Tests automatisés | **833**, tous verts |
| Qualité du code | `ruff` (contrôle et format), `pre-commit` |
| Intégration continue | GitHub Actions : `ruff`, `pytest` avec PostgreSQL, absence de migration manquante, `check --deploy` |
| Branche `main` | protégée, une PR par sujet, CI verte avant fusion |
| Taille | environ 6 000 lignes de code Python applicatif, 9 300 lignes de tests et 3 100 lignes de gabarits (hors migrations) |
| Historique | 130 commits, 53 PR fusionnées entre le 21/09 et le 07/10/2026 |
| Migrations | `tenants` 7 · `catalog` 4 · `addressbook` 4 · `gigs` 6 · `documents` 7 · `roadmaps` 1 · `finance` 2 |

Aucune PR en attente : tout est fusionné dans `main`.

---

## 6. Modèle de données réalisé

`User`, `Membership`, `Tenant` · `Show`, `Promoter`, `Venue`, `Contact` · `Gig` ·
`Contract`, `ContractVersion`, `ContractSequence` · `Invoice`, `Quote`, `DocumentLine`, `DocumentSequence` ·
`Roadmap`, `RoadmapSlot`, `Lodging`, `Meal`, `GigMember` · `Payment`, `Expense`.

Schéma des relations : voir `docs/guides/09-cas-d-usage-et-diagrammes.md` §6. La description champ par champ est dans le cahier des charges §9 (aligné sur le code le 01/10).

**Écarts avec le cahier des charges initial** (déjà reportés dans le §9) : `ContractVersion` et `reference` remplacent `Contract.pdf_file`/`number` ; `DocumentSequence` remplace `InvoiceSequence` ; un avoir est un type de facture ; la TVA est portée par `Tenant.vat_rate` ; `Invoice` a un statut « payée » ; `Meal` n'a pas de champ adresse (seulement un lieu en texte).

---

## 7. Ce qui reste à faire et points d'attention

**Reste du MVP**
- Sprint 3.8, ce qui reste (bloqué par les comptes à créer) : recette complète (cahier des charges §11), sauvegarde avec test de restauration, déploiement en production, audit des dépendances (`pip-audit`, Dependabot). Fait : pages légales, export et suppression de compte, audit d'isolation, réglages de production, pages d'erreur.
- À contrôler **à la main** (non vérifié par les tests) : le rendu à 375 px des écrans de paiements, dépenses, tableau de bord, exports, suppression de compte et pages d'erreur ; l'ouverture des CSV dans Excel ; la mise en page des PDF (facture et feuille de route) ; la navigation au clavier et au lecteur d'écran. Un guide de test pas à pas existe (`11-guide-de-test.md`, pas encore commité) ; il sert à un test complet en local avant de présenter l'application à l'associé.
- Restes du 3.1 : confirmation d'e-mail, logo, code APE, forme juridique en liste.
- Textes légaux (mentions, CGU, confidentialité) à compléter et à faire relire ; conservation de 10 ans des factures à valider avant d'autoriser la suppression complète.

**Avant d'utiliser de vraies factures**
- Relecture par un professionnel (comptable) du PDF de facture et du contrat. Les PDF portent un bandeau « Modèle provisoire — non relu par un professionnel » (un seul réglage à retirer ensuite).
- Conditions de paiement (pénalités, indemnité de 40 €) à discuter avec l'associé puis à faire valider.
- Mention de TVA du cas « non assujetti » : texte provisoire (questions Q13 / F-56).
- Le bilan et le tableau de bord sont en TTC ; si la TVA concerne l'utilisateur, faire valider la présentation (résultat = encaissé − dépensé, sans distinguer la TVA).
- ⚠️ **Les PDF du MVP ne remplacent pas la plateforme agréée de facturation électronique** (obligation à vérifier, prévue en Phase 5). L'application ne doit pas se dire « conforme » avant cette connexion.

**Déploiement** (rien n'est en ligne à ce jour) : compte Scalingo, bucket S3 privé, prestataire d'e-mails, domaine, Sentry, tâche planifiée de purge des comptes supprimés, `collectstatic` au build. Liste complète : `docs/guides/06-services-production.md`.

**Questions de fond ouvertes** (cahier des charges §14) : Q9 modèle économique, Q10 hiérarchie Projet/Spectacle (détail : `docs/metier/07-modele-spectacle.md`), Q12, Q13, Q14, Q15 (sens du mot « Structure »), Q16 (plan des lieux dans la feuille de route).

**Points techniques notés** : `Gig.venue` obligatoire (RG-02) ; la mise en page des PDF de facture et de feuille de route reste à vérifier à l'œil ; un brouillon de facture n'apparaît pas sur la page des paiements (il ne peut pas être payé) ; une feuille de route n'a pas encore de plan des lieux ni d'adresse pour les repas.
