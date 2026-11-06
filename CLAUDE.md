# CLAUDE.md — SaaS « Gestion Spectacle Vivant »

> Ce fichier est lu par Claude Code au début de chaque session. Il doit rester court et à jour.
> Documentation détaillée : `docs/` (produit, marque, technique, métier, archives : voir `docs/README.md`).

## 1. Le projet en 5 lignes

Application web SaaS (**priorité ordinateur** ; la feuille de route publique se lit sur téléphone) pour les artistes auto-produits, petites compagnies et associations loi 1901 du spectacle vivant (musique surtout). Elle permet de gérer seuls **leurs dates de concert** : contrat de cession PDF, devis/facture, feuille de route mobile, suivi des paiements et dépenses.
Objectif n°1 : **simplicité radicale** (prise en main < 5 min, vocabulaire du métier, pas de jargon comptable ou juridique).
Le développeur est seul, débutant en projet professionnel, et travaille avec toi (Claude Code). **Explique tes choix en français, simplement, et privilégie toujours la solution la plus simple.**

## 2. Stack (ne pas en changer sans me demander)

- Python 3.12, **Django 5.2 LTS** (monolithe), PostgreSQL 16
- Front : templates Django + **HTMX** + **Alpine.js** + **Tailwind CSS** (`django-tailwind-cli`, pas de Node)
- PDF : **WeasyPrint** (HTML/CSS → PDF)
- Auth : `django-allauth` (connexion par e-mail), modèle `User` personnalisé
- Config : `django-environ`, fichiers `.env` (jamais commités)
- Tests : `pytest`, `pytest-django`, `factory_boy` — Qualité : `ruff` (lint + format), `pre-commit`
- Prod : Scalingo (France), bucket S3 européen via `django-storages`, `whitenoise` + `gunicorn`, Sentry (UE)
- Dépendances : `pip` + `requirements/base.txt`, `dev.txt`, `prod.txt`

**Interdit sauf accord explicite** : React/Vue/SPA, Celery/Redis, DRF (API REST), ORM alternatif, bibliothèque JS lourde, Google Maps.

## 3. Commandes

```bash
docker compose up -d db                 # PostgreSQL local
python manage.py tailwind runserver     # serveur de dev + compilation Tailwind (1 seul terminal, recommandé)
python manage.py runserver              # serveur de dev seul (sans compilation Tailwind)
python manage.py makemigrations && python manage.py migrate
pytest                                  # tests
pytest -x -q apps/gigs                  # tests d'une app, arrêt au 1er échec
ruff check . && ruff format .           # lint + format
python manage.py check --deploy         # contrôle sécurité avant prod
```

## 4. Structure du dépôt

```
config/settings/{base,dev,test,prod}.py   # réglages séparés
config/urls.py
apps/
  accounts/       # User, Membership, inscription
  tenants/        # Tenant (la structure de l'utilisateur) + infos légales
  core/           # TenantOwnedModel, mixins de vues, utilitaires communs
  catalog/        # Show (spectacles)
  addressbook/    # Promoter, Venue, Contact
  gigs/           # Gig (la date), GigMember, calendrier
  documents/      # Contract, Quote, Invoice, génération PDF
  roadmaps/       # Roadmap, RoadmapSlot, Lodging, Meal, lien secret
  finance/        # Payment, Expense, dashboard, export CSV
templates/        # base.html + un dossier par app
static/
docs/             # produit/, marque/, technique/, metier/, archives/ (voir docs/README.md)
```

Une app = un domaine métier. Ne pas créer d'app supplémentaire sans en parler.

## 5. Lexique — À RESPECTER PARTOUT (code en anglais, interface en français)

| Code | Interface (FR) | Signification |
|---|---|---|
| `Tenant` | « Ma structure » | L'artiste, l'association ou la micro-entreprise qui **utilise l'app** (= le « PRODUCTEUR » dans le modèle de contrat fourni par le métier) |
| `Membership` | — | Lien utilisateur ↔ tenant, avec un rôle (`owner`, `member`) |
| `Show` | Spectacle | Ce que l'artiste vend (titre, durée, fiche technique, n° SACEM/objet) |
| `Promoter` | Organisateur | Le **client** qui achète le spectacle, à facturer (= « ORGANISATEUR » dans le contrat) |
| `Venue` | Lieu / Salle | L'endroit physique où a lieu la date |
| `Contact` | Contact | Personne rattachée à un `Promoter` **ou** à un `Venue` |
| `Gig` | Date | Une représentation : relie Show + Promoter + Venue + date + prix. **Objet central** |
| `Contract` | Contrat de cession | Document PDF lié à un `Gig` |
| `Quote` / `Invoice` | Devis / Facture | Documents liés à un `Gig` |
| `Roadmap` | Feuille de route | Document logistique de la date (horaires, contacts, hébergement, repas) |
| `Payment` / `Expense` | Paiement / Dépense | Argent reçu / argent dépensé pour une date |

**Le mot « Structure »**, utilisé par le métier pour désigner l'organisateur/le lieu (le partenaire externe), **ne doit jamais être utilisé dans le code** pour éviter la confusion avec `Tenant` (la structure de l'utilisateur). Dans les échanges avec le métier, traduire mentalement : leur « Structure » = notre `Promoter`/`Venue` ; leur « Producteur » = notre `Tenant`. Ne jamais utiliser `Client` dans le code. Vocabulaire UI : « cachet », « cession », « feuille de route », « organisateur ». **Pas** de « entité », « tiers », « écriture comptable ».

## 6. RÈGLES ABSOLUES

### 6.1 Isolation des tenants (priorité n°1 — une fuite de données = fin du produit)
- Tout modèle métier hérite de `core.models.TenantOwnedModel` (FK `tenant` obligatoire).
- Toute vue qui lit ou modifie des données hérite de `core.views.TenantScopedMixin` (filtre automatique sur `request.tenant`).
- **Interdit** : `Model.objects.get(pk=...)` ou `Model.objects.all()` dans une vue sans filtre sur le tenant.
- Un formulaire ne doit jamais laisser choisir le tenant ; il est posé côté serveur. Les FK vers d'autres objets (ex. `promoter` dans un `Gig`) doivent être limitées aux objets du même tenant.
- Chaque nouveau modèle métier = **au moins un test d'isolation** (le tenant B reçoit 404 sur un objet de A, et ne le voit dans aucune liste).
- Le test `apps/core/tests/test_tenant_coverage.py` échoue si un modèle `TenantOwnedModel` n'a pas de test d'isolation.

### 6.2 Documents financiers et contractuels
- Les montants sont en `DecimalField` (jamais `float`), stockés et calculés **au centime près** ; l'arrondi à l'euro entier est un choix d'affichage réservé aux vues de synthèse (tableau de bord, listes), jamais au stockage (F-58).
- Recette **prévue** (prix du contrat), **facturée** (montant émis) et **encaissée** (paiements reçus) sont trois montants distincts à garder consultables séparément, jamais fusionnés (F-57).
- Une facture **émise** est **immuable** : correction par avoir, jamais par modification.
- Numérotation des factures : séquentielle, **sans trou**, par tenant et par année, calculée dans une transaction avec verrou (`select_for_update`).
- Les infos légales (nom, SIRET, TVA, adresse…) sont **copiées dans le document au moment de l'émission** (snapshot), pas lues dynamiquement.
- Un contrat passé au statut « signé » conserve un PDF figé.

### 6.3 Sécurité
- Aucun secret dans le code ni dans Git. Tout passe par variables d'environnement.
- Liens secrets (feuille de route) : `secrets.token_urlsafe(32)`, révocables, jamais un ID séquentiel.
- Toute vue exige la connexion, sauf inscription, connexion, pages légales, feuille de route par lien secret et formulaires de complétion envoyés à un organisateur (fiche de l'organisateur, régie de tournée d'une date) : lien secret temporaire de 7 jours, à usage unique, qui ne donne accès qu'à un formulaire ; les réponses sont vérifiées par l'utilisateur avant d'être appliquées.
- Ne jamais afficher de données personnelles dans les logs ou Sentry.

### 6.4 Simplicité
- Pas de sur-ingénierie : pas d'abstraction « au cas où ». Trois lignes répétées valent mieux qu'une abstraction prématurée.
- Une fonctionnalité du prompt client non listée dans `docs/produit/cahier-des-charges.md` (MVP) **n'est pas à coder**.

## 7. Conventions de code

- Code, noms de variables, commentaires techniques : **anglais**. Textes de l'interface, messages d'erreur, e-mails : **français** (`LANGUAGE_CODE = "fr"`, `TIME_ZONE = "Europe/Paris"`), avec `gettext_lazy` dans les modèles.
- Statuts et choix : `models.TextChoices`.
- Vues : préférer les vues basées sur classes génériques de Django ; HTMX renvoie des **fragments de template** (`_partial.html`), détectés via `request.htmx`.
- Formulaires : Django Forms / ModelForms ; les wizards sont des vues HTMX en plusieurs étapes.
- Templates : **desktop-first** (Tailwind) ; les pages publiques (feuille de route, formulaire organisateur, connexion) restent lisibles à 375 px ; composants réutilisables dans `templates/components/`.
- Interface : suivre la charte (`docs/marque/charte-graphique.md`) ; les couleurs d'état ne servent jamais à décorer, le corail est réservé à l'action principale, et toute nouvelle couleur de texte doit passer le test de contraste.
- Alpine.js uniquement pour de petits états d'interface (menu, onglets, modale).
- Logique métier dans des fonctions/services (`apps/<app>/services.py`), pas dans les vues ni les templates.
- Migrations : toujours relues avant commit ; jamais éditées après avoir été appliquées en prod.
- Commits : messages courts, à l'impératif, en anglais (`Add gig status transitions`).

## 8. Tests — définition de « terminé »

Une tâche est terminée quand :
1. `pytest` passe, `ruff check .` est propre ;
2. les cas normaux **et** les cas d'erreur sont testés ;
3. l'isolation des tenants est testée si un modèle ou une vue est concerné ;
4. les pages publiques sont utilisables sur mobile (375 px) ; les écrans connectés sont conçus pour l'ordinateur ;
5. `docs/produit/feuille-de-route.md` est mis à jour (case cochée).

## 9. Méthode de travail avec moi

- **Commence par un plan** (liste d'étapes, fichiers touchés) et attends mon accord avant de coder tout ce qui touche aux **modèles, migrations, authentification, multi-tenant ou PDF**.
- Une tâche = une branche = une petite PR (`feature/<sujet>`). Ne mélange pas plusieurs sujets.
- `main` = travail, `production` = livré : on livre par avancement de `production` sur `main` (`--ff-only`), jamais de correction directe sauf urgence. Procédure : `docs/technique/livraison.md`.
- Écris les tests avec le code, pas après.
- Si une demande contredit ce fichier ou le cahier des charges, **signale-le** au lieu de l'exécuter silencieusement.
- Si tu hésites entre deux approches, présente les deux avec leurs avantages en quelques lignes.
- Ne modifie pas ce fichier sans me le dire.

## 10. Hors périmètre (ne pas coder, ne pas proposer)

Calcul de charges sociales GUSO/intermittence, carte interactive, itinéraires calculés et temps de trajet (un simple aperçu de carte OpenStreetMap, sans calcul, est autorisé depuis le 2026-10-28), connecteur expert-comptable/CAE, aide au choix du statut juridique, billetterie, gestion des droits SACEM, application mobile native. (Voir `docs/produit/cahier-des-charges.md` pour les évolutions prévues.)

## 11. État actuel

- Phase en cours : **fin du MVP, premier déploiement fait sur Scalingo (adresse temporaire), services provisoires** (voir `docs/produit/etat-du-projet.md`, page à lire en premier). Sprints 3.1 à 3.21 terminés (dont la refonte V06, la charte « blanc & contrastes francs » v1.0, l'inscription sur invitation, la gestion sociale de l'équipe, la feuille de route enrichie avec l'espace équipe, la mise en page pour ordinateur, l'annuaire de contacts à rattachements multiples avec code couleur). Branches : `main` (travail) et `production` (livré). Il reste : e-mails (Brevo), domaine `bordpro.fr`, bucket S3, Sentry, sauvegardes, recette sur la production ; relecture professionnelle des contrats et factures ; structure juridique ; « n° de compte » de la fiche Équipe (réponse de l'associé). Le produit s'appelle **Bòrd Pro** (avec l'accent, jamais « BÒRD PRO » en capitales ni « Bord Pro »). Charte : `docs/marque/charte-graphique.md`. Guide de mise en ligne : `docs/technique/guide-mise-en-ligne.md`. L'inscription est **sur invitation** (`SIGNUP_REQUIRES_INVITATION`). RADAR et carte : après le MVP (`docs/produit/specification-radar.md`). Acquis : onboarding, « Ma structure » (dont IBAN, BIC, téléphone, e-mail), équipe (adresse et n° GUSO visibles du seul propriétaire ; espace personnel par lien secret, déclaration de dépenses par l'équipe), navigation, CRUD des organisateurs (qualification à choix multiple et filtres), lieux (avec configuration), contacts et spectacles (durées de balances, nombre d'artistes et de techniciens, code analytique), dates (statuts, calendrier), contrat de cession à **quatre modèles au choix** tant qu'il est en brouillon (versions, marquage « signé », PDF figé), stockage privé, devis, factures et avoirs (IBAN et BIC affichés), feuille de route (lien secret, aperçu de carte OpenStreetMap), annuaire de contacts, paiements, dépenses, bilan, accueil, exports CSV (avec code analytique), pages légales, export et suppression de compte, audit d'isolation. Services de production : `docs/technique/services-production.md`.
- Un vrai modèle de contrat de cession et un document de logique métier ont été fournis par le métier, puis complétés par un entretien, un modèle de données plus riche (voir `docs/metier/modele-spectacle.md`) et une note de cadrage technique. **Confirmé et livré le 2026-10-13 :** quatre modèles de contrat de cession au choix (sources dans `docs/metier/modeles-contrats/`), tous des contrats de cession ; la coréalisation et la location de salle restent non gérées. Les autres extensions (CRM complet, hiérarchie Projet/Spectacle, coréalisation et location de salle, paie des intermittents, déclarations SACEM, signature électronique par prestataire) **restent hors du MVP tant qu'elles n'ont pas été explicitement confirmées** : voir `docs/produit/cahier-des-charges.md` §14 (Q1-Q16).
- Q8 tranchée (2026-10-01) : la mention « Nécitge 2000 et non assujetti à la TVA : article 293b du CGI » n'est pas conservée dans le contrat.
- Décisions ouvertes : voir la section « Décisions à prendre » de la feuille de route.