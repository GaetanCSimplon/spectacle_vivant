# CLAUDE.md — SaaS « Gestion Spectacle Vivant »

> Ce fichier est lu par Claude Code au début de chaque session. Il doit rester court et à jour.
> Documentation détaillée : `docs/` (cahier des charges, feuille de route, guides).

## 1. Le projet en 5 lignes

Application web SaaS (mobile-first) pour les artistes auto-produits, petites compagnies et associations loi 1901 du spectacle vivant (musique surtout). Elle permet de gérer seuls **leurs dates de concert** : contrat de cession PDF, devis/facture, feuille de route mobile, suivi des paiements et dépenses.
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
docs/
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
- Toute vue exige la connexion, sauf inscription, connexion, pages légales, feuille de route par lien secret et formulaire de complétion envoyé à un organisateur (lien secret temporaire de 7 jours, à usage unique, qui ne donne accès qu'à un formulaire ; les réponses sont vérifiées par l'utilisateur avant d'être appliquées).
- Ne jamais afficher de données personnelles dans les logs ou Sentry.

### 6.4 Simplicité
- Pas de sur-ingénierie : pas d'abstraction « au cas où ». Trois lignes répétées valent mieux qu'une abstraction prématurée.
- Une fonctionnalité du prompt client non listée dans `docs/cadrage/03-cahier-des-charges.md` (MVP) **n'est pas à coder**.

## 7. Conventions de code

- Code, noms de variables, commentaires techniques : **anglais**. Textes de l'interface, messages d'erreur, e-mails : **français** (`LANGUAGE_CODE = "fr"`, `TIME_ZONE = "Europe/Paris"`), avec `gettext_lazy` dans les modèles.
- Statuts et choix : `models.TextChoices`.
- Vues : préférer les vues basées sur classes génériques de Django ; HTMX renvoie des **fragments de template** (`_partial.html`), détectés via `request.htmx`.
- Formulaires : Django Forms / ModelForms ; les wizards sont des vues HTMX en plusieurs étapes.
- Templates : mobile-first (Tailwind), composants réutilisables dans `templates/components/`.
- Alpine.js uniquement pour de petits états d'interface (menu, onglets, modale).
- Logique métier dans des fonctions/services (`apps/<app>/services.py`), pas dans les vues ni les templates.
- Migrations : toujours relues avant commit ; jamais éditées après avoir été appliquées en prod.
- Commits : messages courts, à l'impératif, en anglais (`Add gig status transitions`).

## 8. Tests — définition de « terminé »

Une tâche est terminée quand :
1. `pytest` passe, `ruff check .` est propre ;
2. les cas normaux **et** les cas d'erreur sont testés ;
3. l'isolation des tenants est testée si un modèle ou une vue est concerné ;
4. la page est utilisable sur mobile (largeur 375 px) ;
5. `docs/cadrage/04-feuille-de-route.md` est mis à jour (case cochée).

## 9. Méthode de travail avec moi

- **Commence par un plan** (liste d'étapes, fichiers touchés) et attends mon accord avant de coder tout ce qui touche aux **modèles, migrations, authentification, multi-tenant ou PDF**.
- Une tâche = une branche = une petite PR (`feature/<sujet>`). Ne mélange pas plusieurs sujets.
- Écris les tests avec le code, pas après.
- Si une demande contredit ce fichier ou le cahier des charges, **signale-le** au lieu de l'exécuter silencieusement.
- Si tu hésites entre deux approches, présente les deux avec leurs avantages en quelques lignes.
- Ne modifie pas ce fichier sans me le dire.

## 10. Hors périmètre (ne pas coder, ne pas proposer)

Calcul de charges sociales GUSO/intermittence, carte et temps de trajet, connecteur expert-comptable/CAE, aide au choix du statut juridique, billetterie, gestion des droits SACEM, application mobile native. (Voir `docs/cadrage/03-cahier-des-charges.md` pour les évolutions prévues.)

## 11. État actuel

- Phase en cours : **Phase 3, fin du MVP, produit testé en local et pas encore déployé** (voir `docs/cadrage/04-feuille-de-route.md`). Les Sprints 3.1 à 3.10 sont terminés (dont : retours de l'associé, nouvel accueil, design « Scène », formulaire envoyé à l'organisateur, rendu mobile). Le **Sprint 3.11 est en cours** : quatre modèles de contrat de cession au choix (PR 1 faite : choix du modèle ; à venir : champs communs, puis Modèles 2, 3 et 4). Du Sprint 3.8 restent : sauvegardes et test de restauration, recette, déploiement. Le produit s'appelle **BÒRD PRO**. Acquis : onboarding, « Ma structure », équipe, navigation, CRUD des organisateurs, lieux, contacts et spectacles, dates (statuts, calendrier), contrat de cession (versions, marquage « signé », PDF figé, choix du modèle), stockage privé, devis, factures et avoirs, feuille de route (lien secret), paiements, dépenses, bilan, accueil, exports CSV, pages légales, export et suppression de compte, audit d'isolation. Déploiement bloqué par le choix du nom de domaine ; services à prévoir : `docs/guides/06-services-production.md`.
- Un vrai modèle de contrat de cession et un document de logique métier ont été fournis par le métier, puis complétés par un entretien, un modèle de données plus riche (voir `docs/metier/07-modele-spectacle.md`) et une note de cadrage technique. **Confirmé le 2026-10-13 :** quatre modèles de contrat de cession au choix (sources dans `docs/modeles-contrats/`). Les autres extensions (CRM complet, hiérarchie Projet/Spectacle, coréalisation et location de salle, paie des intermittents, déclarations SACEM, signature électronique par prestataire) **restent hors du MVP tant qu'elles n'ont pas été explicitement confirmées** : voir `docs/cadrage/03-cahier-des-charges.md` §14 (Q1-Q16).
- Q8 tranchée (2026-10-01) : la mention « Nécitge 2000 et non assujetti à la TVA : article 293b du CGI » n'est pas conservée dans le contrat.
- Décisions ouvertes : voir la section « Décisions à prendre » de la feuille de route.