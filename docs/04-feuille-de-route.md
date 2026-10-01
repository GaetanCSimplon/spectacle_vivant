# Feuille de route détaillée — SaaS « Gestion Spectacle Vivant »

> Coche les cases au fur et à mesure (Claude Code peut le faire en fin de tâche).
> Les durées sont **indicatives** pour un développeur seul, débutant en projet pro, assisté par l'IA. Prévois une marge de 30 à 50 %.

## Vue d'ensemble

| Phase | Nom | Durée indicative | Résultat |
|---|---|---|---|
| 0 | Validation métier | 1 semaine | Besoins confirmés, contrat type identifié |
| 1 | Squelette déployé | 1 à 2 semaines | Pipeline vert, application « vide » en ligne |
| 2 | PoC vertical | 2 à 3 semaines | Une date → un contrat PDF, sur staging |
| 3 | MVP | 6 à 8 semaines | Toutes les fonctionnalités MVP |
| 4 | Bêta fermée | 4 semaines | 5–10 utilisateurs réels, corrections |
| 5 | Version 1 payante | 6 à 10 semaines | Paiement, signature, Factur-X, relances… |

> Le prompt initial estimait 4–5 semaines pour la Phase 3. C'est optimiste pour un premier projet : garde-le comme objectif, planifie sur 6 à 8.

---

## Règles de fonctionnement (valables pour toutes les phases)

**Rythme de travail**
1. Choisir une tâche de la liste → 2. la demander à Claude Code **avec un plan d'abord** → 3. valider le plan → 4. coder avec les tests → 5. relire soi-même → 6. lancer `pytest` + `ruff` → 7. PR → 8. CI verte → 9. fusionner → 10. cocher la case.

**Git**
- Branche `main` protégée (toujours déployable). Une branche par tâche : `feature/gig-wizard`.
- Fusion par Pull Request, même seul : ça déclenche la CI et te force à relire.

**Définition de « terminé »** (répétée dans `CLAUDE.md`) : tests verts, lint propre, isolation testée, utilisable à 375 px, feuille de route à jour.

**Modèle de demande à Claude Code**
```
Contexte : je travaille sur <tâche> (Phase X, voir docs/04-feuille-de-route.md).
Objectif : <résultat attendu, en une phrase>.
Contraintes : respecte CLAUDE.md (lexique, isolation des tenants).
Avant de coder : propose un plan (fichiers, modèles, tests) et attends mon accord.
```

**Ce que tu relis toi-même, toujours** : migrations, requêtes ORM dans les vues (filtre par tenant ?), montants (Decimal ?), permissions.

> **Renommage du 2026-09-25** : `Organization` → `Tenant` dans tout le projet (modèle, champ FK, middleware `request.tenant`, mixin, app `organizations` → `tenants`). Les tâches déjà cochées ci-dessous utilisaient l'ancien nom au moment où elles ont été faites ; le texte a été mis à jour pour refléter le nom actuel, sans que ça change ce qui a été livré.

> **Mise à jour du 2026-09-30** : intégration de l'entretien du 28/09 avec le collègue, de sa note de cadrage technique (modèle d'abonnement à deux formules) et de sa proposition de modèle de données Projet/Spectacle. Les ajouts additifs (code APE, rôles de contact, lien EPK, idées v1/v2) sont intégrés directement ci-dessous, marqués *(28/09)*. Les décisions structurantes (modèle économique, hiérarchie Projet/Spectacle, clause TVA du contrat) sont marquées ⚠️ et **ne sont pas développées tant qu'elles ne sont pas tranchées** — voir le tableau « Décisions à prendre » et `docs/03-cahier-des-charges.md` §14 (Q8-Q13).

---

## Phase 0 — Validation métier (semaine 0, sans code)

**Objectif** : t'assurer que tu construis quelque chose d'utile, et acquérir le vocabulaire du métier.

- [ ] Lire `02-guide-metier.md`.
- [ ] Lister 10 à 15 personnes à contacter (artistes, groupes, associations, tourneurs, un comptable ou une CAE si possible) via ton réseau, réseaux sociaux, salles locales, groupes Facebook de musiciens.
- [ ] Mener **5 entretiens** de 30 min avec la trame de la section 5 du guide métier. Enregistrer (avec accord) ou prendre des notes.
- [x] Récupérer des **exemples réels** : contrat de cession, document de logique métier, modèles de données de suivi (obtenus du collègue, 2026-09-25) ; entretien complémentaire, note de cadrage technique et modèle de données Projet/Spectacle (obtenus le 2026-09-28/29).
- [ ] Repérer 2 à 3 **modèles de contrats de cession de référence** (organismes professionnels, syndicats) et vérifier **leurs conditions de réutilisation** — le modèle reçu du collègue n'a pas encore été validé par un professionnel, voir point suivant.
- [ ] Identifier **un professionnel relecteur** (juriste, expert-comptable, CAE, association d'artistes) pour valider contrat et mentions de facture.
- [ ] **Obtenir les réponses du collègue aux questions ouvertes Q1-Q13** (`docs/03-cahier-des-charges.md` §14) : CRM de prospection, types de contrat, suivi temps réel, paie des intermittents, déclarations SACEM, capitalisation, contrats multi-dates, **+ Q8-Q13 issues de l'entretien du 28/09** (clause TVA retirée par erreur possible, modèle économique à deux formules, hiérarchie Projet/Spectacle, etc.).
- [x] **Q8 tranchée (2026-10-01)** : la mention « Nécitge 2000 et non assujetti à la TVA : article 293b du CGI » n'est pas conservée ; la suppression dans le contrat est confirmée.
- [ ] Rédiger une synthèse d'une page : 3 problèmes principaux, 3 fonctionnalités les plus demandées, vocabulaire noté, prix acceptable.
- [x] Mettre à jour `03-cahier-des-charges.md` si les entretiens changent le périmètre — *mis à jour au fil des documents reçus du collègue (contrat, logique métier, tableurs de suivi, entretien du 28/09, note de cadrage) ; à revoir une fois les 5 entretiens artistes réellement menés.*
- [ ] **Décider** : go / go modifié / stop.

**Livrable** : synthèse des entretiens + 2 modèles de contrat + contact d'un relecteur.
**Critère de sortie** : au moins 3 personnes sur 5 disent qu'elles utiliseraient l'outil ou perdent réellement du temps sur ces tâches.

---

## Phase 1 — Squelette déployé (semaines 1–2)

**Objectif** : avoir une application minimale **déjà en ligne**, avec CI verte, isolation des tenants en place et génération de PDF validée en conditions réelles. Aucune fonctionnalité métier visible.

### 1.1 Poste de travail
- [ ] Installer : Python 3.12, Git, Docker Desktop, VS Code, Claude Code, Node non requis.
- [ ] Créer les comptes : GitHub, Scalingo (et plus tard : Sentry, prestataire e-mail, S3 européen).
- [ ] Créer le dépôt GitHub privé, cloner en local.
- [ ] Placer `CLAUDE.md` et le dossier `docs/` à la racine, premier commit.

### 1.2 Projet Django
- [ ] Créer l'environnement virtuel, installer Django 5.2 LTS.
- [x] Générer le projet avec le dossier `config/` et les réglages séparés `base.py`, `dev.py`, `test.py`, `prod.py`.
- [ ] Créer les fichiers `requirements/base.txt`, `dev.txt`, `prod.txt`.
- [ ] `.gitignore` (venv, `.env`, `__pycache__`, `staticfiles`, `media`).
- [x] `.env.example` documenté ; chargement via `django-environ`.
- [x] `docker-compose.yml` avec PostgreSQL 16 ; connexion Django → Postgres.
- [x] `LANGUAGE_CODE="fr"`, `TIME_ZONE="Europe/Paris"`.

### 1.3 Qualité
- [x] Configurer `ruff` (règles de base + imports) et `pre-commit`.
- [x] Configurer `pytest`, `pytest-django`, `factory_boy` ; premier test qui passe.
- [ ] Ajouter un `Makefile` ou des scripts pour les commandes courantes (facultatif).

### 1.4 Utilisateur, tenant et isolation ⚠️ *(à faire avant la première migration)*
- [x] App `accounts` : **User personnalisé** avec connexion par e-mail. **Créé avant tout `migrate`** (sinon très pénible à changer).
- [x] App `tenants` *(anciennement `organizations`)* : modèle `Tenant` *(anciennement `Organization`)* (champs minimaux : name, legal_form, plan).
- [x] Modèle `Membership` (user, tenant, role).
- [x] App `core` : `TenantOwnedModel` (abstract), middleware `request.tenant`, `TenantScopedMixin` pour les vues.
- [x] Modèle de test jetable (ex. `Note`) pour valider le mécanisme.
- [x] **Tests d'isolation** : B reçoit 404 sur un objet de A ; les listes ne mélangent pas ; création forcée dans le tenant courant.
- [x] **Test de couverture** : échoue si un modèle `TenantOwnedModel` n'a pas de test d'isolation.
- [ ] Intégrer `django-allauth` (inscription, connexion, mot de passe oublié) avec e-mails en console en dev. — inscription et connexion testées en local (OK) ; **mot de passe oublié pas encore testé**.

### 1.5 Front
- [x] `django-tailwind-cli` installé ; compilation OK.
- [x] `base.html` : Tailwind, HTMX (`django-htmx`), Alpine.js, meta viewport, structure mobile-first (en-tête + menu). — en-tête minimal en place (pas de vrai menu de navigation : aucune fonctionnalité métier à lier avant Sprint 3.1). Testé en navigateur, y compris les pages allauth qui héritent du même layout.
- [x] Une page d'accueil connectée qui affiche le nom du tenant.

### 1.6 PDF — validation précoce
- [ ] Installer WeasyPrint (+ dépendances système) en local et **dans l'image Docker** si utilisée. — fait en local (testé en navigateur) ; pas encore d'image Docker pour l'app Django à ce stade (seulement `docker-compose.yml` pour Postgres), donc **dépendances système à valider en Phase 1.7** (penser à `libharfbuzz-subset0`, requis par une prochaine version de WeasyPrint).
- [x] Vue qui génère un PDF « Bonjour » depuis un template HTML/CSS. Test automatisé qui vérifie qu'un PDF est bien renvoyé.

### 1.7 CI/CD et déploiement
- [x] GitHub Actions : `ruff`, `pytest` (avec service Postgres), contrôle qu'il n'y a pas de migration manquante (`makemigrations --check`), `manage.py check --deploy`. — validé sur GitHub via la PR de la branche `feature/django-skeleton`, CI verte.
- [x] Protéger `main` : PR obligatoire, CI verte requise.
- [ ] Scalingo : créer l'app **staging**, ajouter l'addon PostgreSQL, configurer variables d'environnement, `Procfile` (gunicorn), migrations automatiques après déploiement, `whitenoise` pour les statiques. — **en attente : pas de compte Scalingo pour l'instant.**
- [ ] Rendre WeasyPrint opérationnel sur Scalingo (installation des bibliothèques système via le buildpack apt ; **suivre la documentation Scalingo à jour**). — **en attente**, dépend du point précédent.
- [ ] Route `/health/` (renvoie 200) + moniteur d'uptime gratuit. — **en attente**, peu utile sans déploiement.
- [ ] Sentry (région UE) branché, sans données personnelles. — **en attente**, peu utile sans déploiement.
- [ ] Déploiement automatique de `main` vers staging. — **en attente**, dépend du compte Scalingo.

**Livrable** : une URL de staging avec inscription/connexion, une page connectée, un PDF de test, CI verte.
**Critère de sortie** : tu peux modifier une ligne, ouvrir une PR, voir la CI passer, fusionner, et voir la modification en ligne en moins de 10 minutes.
**Vigilance** : ne pas ajouter de fonctionnalités métier. Ne pas peaufiner le design.

> **Décision du 2026-09-22** : critère de sortie non atteint (pas de compte Scalingo). Choix assumé de passer à la Phase 2 malgré tout, avec le risque connu de découvrir un problème de déploiement tardivement. Le reste de la §1.7 (Scalingo, `/health/`, Sentry, déploiement auto) est à reprendre dès qu'un compte Scalingo existe.

---

## Phase 2 — PoC vertical (semaines 3–5)

**Objectif** : prouver **le parcours le plus précieux de bout en bout** : *un utilisateur s'inscrit, saisit une date, télécharge un contrat PDF correct.* Tout est minimal, mais réel et déployé.

### 2.1 Modèles minimaux
- [x] `Tenant` complété (adresse, SIRET, vat_regime).
- [x] `Show` (titre, durée, prix indicatif).
- [x] `Promoter` (nom, SIRET, adresse de facturation, e-mail).
- [x] `Venue` (nom, adresse).
- [x] `Gig` (show, promoter, venue, date, statut, prix HT, conditions).
- [x] `Contract` (gig, statut, pdf_file, generated_at).
- [x] Admin Django configuré pour tous les modèles (débogage).
- [x] Factories de test et **tests d'isolation pour chaque modèle**. — tests au niveau ORM (pas encore de vues CRUD, elles arrivent en §2.2/§3.2). Testé en local avec une vraie migration Postgres.

### 2.2 Wizard de création de date
- [x] Étape 1 : choisir/créer un spectacle. Étape 2 : choisir/créer un organisateur. Étape 3 : lieu. Étape 4 : date, horaires, prix. Étape 5 : récapitulatif et validation. — **horaires non inclus** : le modèle `Gig` validé en §2.1 n'a qu'un champ `date` (les horaires détaillés sont prévus dans `Roadmap`/`RoadmapSlot`, Sprint 3.6). Étape 4 = date + prix HT + conditions particulières.
- [x] Navigation HTMX entre étapes (sans rechargement complet), validation à chaque étape. — un seul conteneur `#wizard` avec `hx-boost`/`hx-select`/`hx-target`, pas de vues dupliquées fragment/page complète.
- [x] « Créer à la volée » un organisateur ou un lieu. — même mécanisme pour spectacle/organisateur/lieu (onglets Alpine « choisir » / « créer »).
- [x] Le formulaire ne propose que les objets du **tenant courant**. — querysets filtrés + re-vérification côté service (`get_object_or_404(..., tenant=...)`) à la création, y compris si l'id en session était falsifié.

### 2.3 Contrat PDF
- [x] Choisir **un** modèle de contrat validé en Phase 0. — **Phase 0 non faite** (aucun modèle récupéré, pas de relecteur). Décision assumée le 2026-09-23 : gabarit de contrat de cession provisoire (mentions courantes : parties, objet, prix, conditions particulières, résiliation), filigrané « PROJET — non relu par un professionnel » dans le PDF lui-même. **À refaire avec un vrai modèle validé et une relecture professionnelle avant la bêta (Phase 4).**
- [x] Template HTML/CSS du contrat (A4, marges, pagination, en-tête/pied de page). — `templates/documents/contract_pdf.html`, pagination via `@page { @bottom-center }`.
- [x] Service `generate_contract_pdf(gig)` avec snapshot des infos des parties. — pas de nouveaux champs de snapshot sur `Contract` : une fois généré, le PDF stocké dans `pdf_file` est figé (jamais régénéré si `status == signed`, conformément à RG-08) ; c'est le PDF lui-même qui fait office de snapshot pour le MVP.
- [x] Vue de téléchargement + aperçu. Tests : contient les bons noms, montants, dates ; formats français (date, euros). — `documents:contract-preview` / `documents:contract-download`, isolation testée (404 sur le gig d'un autre tenant).
- [x] **Mise à jour du template** avec les nouveaux champs du modèle de contrat reçu du métier (2026-09-25) : `Tenant.contract_party_label` (défaut « artiste »), `Show.group_name`/`performers`/`rider_file`, `Gig.invitations_count`/`signing_place`/`is_free`/`ticket_price`, `Contract.signatory_name`/`signatory_role`, et règle RG-12 (dans `Gig.save()`). — Le template affiche le libellé de la partie, le lieu de signature, les invitations et le signataire. **Pas encore fait** : reprendre la formulation exacte du contrat du métier (à faire avec le texte sous les yeux), afficher `group_name`/`performers` dans l'objet du contrat, et exposer ces champs dans les formulaires (wizard, Sprints 3.2/3.3/3.4 : pour l'instant seulement via l'admin).
- [x] **Template du contrat aligné sur le vrai modèle du métier** (2026-09-25, 9 articles). Nouveaux champs : `Tenant.licence_number`/`representative_name`/`representative_role`/`jurisdiction_city` (ville du tribunal, art. 8), mêmes champs de représentant et de licence sur `Promoter`, `Venue.capacity`, `Show.sacem_number`/`sacem_object_number`, `Gig.get_in_time`/`soundcheck_time`/`performance_time`/`crew_headcount`. Tout champ vide s'affiche en « …… » pour être complété à la main. Coquilles du modèle corrigées (« ORGANISTAEUR », « hébéerments », « Nécitge 2000 » retiré). ✅ **Q8 tranchée le 2026-10-01** : la mention « Nécitge 2000 » n'est pas conservée, la suppression est confirmée. Le régime de TVA « assujetti » n'est pas géré (TVA laissée en pointillés) : à traiter au Sprint 3.5. Logo de la structure non repris (Sprint 3.1). **À demander au collègue : que signifie « APA » dans « Siret / APA » ?** (on n'affiche que le SIRET en attendant — voir aussi Q11, §14, sur le champ `code_ape` distinct.)
- [x] **Formulaire « Compléter la date »** (2026-09-25) : page unique `dates/<id>/contrat/completer/` (`documents:contract-complete`), atteinte depuis l'écran « Date créée ». Un seul bouton « Enregistrer » pour 6 sections (date, spectacle, lieu, organisateur, ma structure, signature), enregistrées dans une transaction (tout ou rien). Tous les champs sont facultatifs (vide = pointillés dans le contrat). La section « Ma structure » est **réservée au rôle `owner`** ; un contrat `signé` n'est plus modifiable (RG-08). — **Provisoire** : la section « Ma structure » sera retirée de ce formulaire quand la page « Ma structure » du Sprint 3.1 existera. `rider_file` et `performers` restent pour le Sprint 3.2. **Testé à la main dans le navigateur (2026-09-25)** : rendu à 375 px, grisage du prix pour un concert gratuit, remplissage et pré-remplissage des champs, isolation entre structures, section « Ma structure » non modifiable par un `member`, contrat `signé` figé et refusé à la modification.
- [ ] Ne retirer le filigrane « gabarit provisoire » qu'une fois le contrat validé par le relecteur professionnel (Phase 0 puis confirmation en Phase 4).
- [ ] *(signalé manquant dans le point d'étape du 30/09)* Logo de la structure (`Tenant.logo`) non encore affiché sur le PDF du contrat — dépend aussi de la page « Ma structure » complète (Sprint 3.1).

### 2.4 Test utilisateur
- [ ] Déployer sur staging.
- [ ] Faire tester le parcours à **3 personnes** du milieu, sans les aider ; chronométrer, noter les blocages.
- [ ] Faire relire le PDF par le relecteur identifié en Phase 0.
- [ ] Synthétiser : ce qui est clair / confus / manquant.

**Livrable** : parcours complet fonctionnel sur staging + retours utilisateurs.
**Critères de sortie** :
- un testeur génère un contrat correct en moins de 10 minutes ;
- les tests d'isolation passent sur tous les modèles ;
- décision documentée sur ce qu'on change avant de généraliser (vocabulaire, champs, ordre des étapes).

---

## Phase 3 — MVP (semaines 6–13)

**Objectif** : compléter les fonctionnalités du périmètre MVP. Le travail est découpé en **sprints d'environ une semaine**, chacun livrant quelque chose d'utilisable et déployé.

### Sprint 3.1 — Comptes, onboarding, structure, navigation
- [x] Page « Mes dates » (`gigs:list`, `/dates/`) : dates à venir (les plus proches d'abord) puis passées, chaque ligne ouvre l'écran « Date créée ». Isolation testée (2026-09-25). Lien depuis l'accueil ; la navigation principale vient dans la PR suivante.
- [x] Navigation principale (5 entrées max) : responsive (menu bas ou burger sur mobile). — Fait (2026-09-25) : barre basse sur mobile, liens dans l'en-tête dès `sm`, lien actif marqué. 3 entrées pour l'instant (Accueil, Mes dates, Nouvelle date) ; « Ma structure » sera ajoutée avec sa page. **Mise à jour 2026-09-30** : « Nouvelle date » retiré du menu (le bouton reste dans « Mes dates » et sur l'accueil), « Contacts » ajouté (ouvre les organisateurs, avec onglets vers Lieux et Contacts) ; « Spectacles » ajouté avec le CRUD `Show` : le menu compte maintenant 5 entrées (Accueil, Mes dates, Spectacles, Contacts, Ma structure). Composant `templates/components/_nav.html`.
- [ ] Confirmation d'e-mail activée ; e-mails transactionnels via le prestataire choisi ; expéditeur et domaine configurés.
- [x] **Onboarding guidé** (2026-09-28) : un seul écran (`bienvenue/`, `tenants-onboarding`) — nom, forme juridique, régime de TVA — qui crée le `Tenant` et le `Membership(owner)`, puis redirige vers le wizard de date existant plutôt que de dupliquer ses étapes (spectacle/date restent gérés par le wizard). Tout utilisateur connecté sans structure est redirigé automatiquement vers cet écran par `OnboardingRequiredMiddleware` (exemptions : admin, allauth, statiques, l'écran lui-même). Aucun nouveau champ sur `Tenant` à cette étape : aucune migration.
- [x] Page « Ma structure » (2026-09-25) : `ma-structure/` (`tenants:profile`), 4ᵉ entrée du menu. Propriétaire = modification ; membre = lecture seule (POST refusé en 403). Section provisoire retirée du formulaire « Compléter la date » (remplacée par un lien). **Reste à faire** (avec les factures / le stockage S3) : `vat_number`, `iban`, logo, forme juridique en liste de choix, et **`code_ape`** *(nouveau champ demandé le 28/09, code INSEE, distinct de l'ancien « APA »)*.
- [ ] Gestion du régime de TVA : assujetti / franchise en base / non assujetti (mentions à valider — voir aussi Q8 et Q13, §14 du cahier des charges).
- [x] Tests : onboarding, création automatique de `Tenant` + `Membership(owner)` (2026-09-28).

### Sprint 3.2 — Carnet d'adresses et spectacles
- [x] CRUD complet : `Promoter`, `Venue`, `Contact` (avec contrainte : rattaché à l'un **ou** l'autre). — Modèle `Contact` fait (2026-09-28) : contrainte base (`CheckConstraint`) + validation (`clean()`) que le tenant du contact correspond à celui de son organisateur/lieu, test d'isolation. **CRUD `Promoter` fait** (2026-09-28) : liste, création, modification, fiche de détail (contacts + historique des dates via `Gig.promoter`), suppression bloquée si l'organisateur est utilisé par une date (`on_delete=PROTECT`, déjà en place depuis la Phase 2, message d'erreur ajouté côté vue). Au passage, correctif sur `TenantScopedMixin` : `form_valid` plantait sur `DeleteView` (son formulaire n'a pas de `.instance`), corrigé + testé. **CRUD `Venue` fait** (2026-09-28) : même principe que `Promoter` (liste, création, modification, fiche de détail avec contacts + historique via `Gig.venue`, suppression bloquée par `on_delete=PROTECT`), en réutilisant le mixin de redirection factorisé. **CRUD `Contact` fait** (2026-09-30) : création depuis la fiche de l'organisateur ou du lieu (`organisateurs/<pk>/contacts/nouveau/`, `lieux/<pk>/contacts/nouveau/` — le parent est retrouvé côté serveur dans le tenant courant, jamais choisi dans le formulaire), modification, suppression, page `/contacts/`, bandeau à 3 onglets Organisateurs / Lieux / Contacts. `Show` : voir la ligne dédiée ci-dessous.
- [x] Champs manquants de F-10/F-11 (2026-09-30, PR séparée) : `Promoter.phone`/`kind` (liste : mairie, festival, salle, association, bar, autre)/`notes`, `Venue.phone`/`access_info`/`notes`. Migration `addressbook/0004`, tous facultatifs ; visibles dans les formulaires et les fiches de détail.
- [x] Champ `role` du `Contact` : prévoir des suggestions pour les rôles usuels du métier (Accueil, Technique, Comm' — demandé le 28/09), sans figer un `enum` fermé en MVP. — `<datalist>` dans le formulaire, champ resté en texte libre (2026-09-30).
- [x] Recherche en direct HTMX sur les listes (debounce, fragment de liste). — **fait pour organisateurs, lieux et contacts** (2026-09-30) : `SearchListMixin` (`core/views.py`), champ `?q=` avec attente de 300 ms, fragment `_*_results.html` renvoyé si `request.htmx` (pas pour un lien « boosté »), formulaire GET qui marche aussi sans JavaScript. Liste des spectacles incluse (2026-09-30).
- [x] Fiches de détail : un organisateur affiche ses contacts et l'historique de ses dates. — organisateurs et lieux (2026-09-28), avec ajout/modification des contacts depuis la fiche (2026-09-30).
- [x] CRUD `Show` avec fiche technique (texte + PDF optionnel), nom du groupe distinct du titre du spectacle, distribution, rider, **lien EPK** *(demandé le 28/09)*. — Fait (2026-09-30) : liste avec recherche, création, modification, fiche de détail (historique des dates), suppression bloquée si une date l'utilise (`Gig.show` en `PROTECT`). Migration `catalog/0004` : `crew_size`, `tech_sheet_text`, `tech_sheet_file` (PDF uniquement), `epk_url`. Fichiers (fiche technique, rider) téléchargés via une vue protégée par le tenant (`catalog:show-file`, en pièce jointe), jamais par leur URL `/media/` ; en dev, `/media/` reste servi publiquement par `runserver` — à fermer avec le stockage S3 privé (Sprint 3.4). Réglage `FORMS_URLFIELD_ASSUME_HTTPS = True`.
- [x] Suppression sécurisée (empêcher de supprimer un organisateur utilisé, ou archiver). — organisateurs et lieux (`PROTECT`) ; les contacts sont supprimés avec leur parent ; `Show` (`PROTECT`) fait.
- [x] Tests (CRUD, isolation, contrainte Contact, recherche).
- [ ] *(non prévu au MVP actuel, à confirmer via Q12 §14)* Annuaire des salariés/intermittents rattaché à la structure, avec possibilité de le lier à un spectacle donné.

### Sprint 3.3 — Dates : statuts, liste, calendrier, détail
- [x] Statuts `option/confirmed/signed/cancelled` avec **transitions contrôlées** dans un service. — Fait (2026-09-30) : `gigs/services.py` (`change_status`, `reactivate_gig`, `InvalidTransition`), ligne relue sous verrou (`select_for_update`) pour qu'un double clic ne rejoue pas une transition périmée. Le passage à `signed` est autorisé par le service mais **aucun bouton n'est exposé** : il arrivera au Sprint 3.4 avec le marquage « signé » du contrat (qui fige le PDF, RG-08). Réactivation d'une date annulée = retour en `option` (RG-04).
- [x] Date de fin d'option ; mise en évidence des options qui expirent. — Fait (2026-09-30) : champ `Gig.option_expires_on` (migration `gigs/0004`, facultatif), saisi dans le wizard (étape « Détails ») et dans « Compléter la date » (seulement tant que la date est en `option`), refusé s'il dépasse la date du concert. `Gig.option_expiry` : « expire dans N jours » en orange à 7 jours ou moins, « expirée depuis N jours » en rouge, sur la liste et sur le détail. Rien n'est annulé automatiquement (relances = v1).
- [ ] Page de **détail d'une date** (tableau de bord de la date) avec blocs : infos, documents, feuille de route, paiements, dépenses, « prochaine action ». — **Commencé** (2026-09-30, `gigs:detail`) : infos, statut, « prochaine action » selon le statut, documents (contrat). L'écran provisoire « Date créée » (`documents:contract-ready`) est supprimé : le wizard et « Mes dates » mènent au détail. Les blocs feuille de route / paiements / dépenses seront ajoutés avec leurs sprints (3.6, 3.7), pas de bloc vide d'ici là.
- [x] Liste filtrable (statut, mois, spectacle) par HTMX. — Fait (2026-09-30) : `GigFilterForm`, filtres appliqués à la demande (`change`) avec `hx-push-url` pour que l'URL, le rechargement et le bouton Retour gardent les filtres ; un filtre invalide (ex. spectacle d'un autre tenant) est ignoré. Les dates annulées passent dans une section « Annulées » en bas et ne comptent plus dans « À venir ». Règle commune `wants_fragment()` (`core/views.py`) : fragment seulement pour une vraie requête HTMX, pas pour un lien « boosté » ni une restauration d'historique.
- [x] Vue calendrier mensuel. — Fait (2026-10-01) : `dates/calendrier/?mois=2026-10`, onglets Liste / Calendrier. Grille du mois (lundi en premier) générée côté serveur (`services.build_month_grid`), sans JavaScript ; une pastille colorée par date (option ambre, confirmée bleu, signée vert, annulée gris) avec une alternative texte et une légende ; la liste des dates du mois est dessous (un jour à une seule date mène à sa fiche, un jour à plusieurs mène à la liste). Navigation mois précédent / suivant, « Revenir à aujourd'hui », années 2000 à 2100 ; une valeur invalide ramène au mois courant. Les jours des mois voisins qui complètent la grille n'affichent pas leurs dates.
- [x] Annulation d'une date (avec conservation de l'historique). — Page de confirmation puis statut `cancelled` ; la date reste consultable, jamais supprimée ; bouton « Réactiver » (2026-09-30). L'exclusion des totaux à venir viendra avec les filtres de la liste.
- [x] Comptage des dates de l'année (prépare le quota freemium). — `services.count_gigs_for_year` (dates annulées exclues), affiché « N dates en 2026 » sous le titre de « Mes dates » ; aucun blocage tant que Q9 n'est pas tranchée.
- [ ] Tests : transitions valides/invalides, filtres, isolation. — transitions et isolation faites (PR statuts) ; filtres et calendrier faits.

### Sprint 3.4 — Contrats
- [x] Modèle de contrat finalisé avec **conditions particulières** éditables. — Fait (PR A) : `Gig.conditions` éditable dans « Compléter la date », affiché en « Article 10 — Conditions particulières » seulement s'il est rempli.
- [x] Formulation adaptée selon `Tenant.contract_party_label` (« producteur » vs « artiste »), invitations et lieu de signature variables (voir §2.3 pour la mise à jour du template déjà en place).
- [x] Aperçu avant génération ; historique des versions générées. — Aperçu fait (PR A) : rendu à la volée, rien n'est enregistré ; un contrat signé ou d'une date annulée affiche son PDF enregistré ; pas de génération pour une date annulée sans contrat. Historique fait (PR B) : modèle `ContractVersion` (une ligne par PDF généré, jamais écrasée), page « Contrat de cession » (`documents:contract-history`) avec « Générer une nouvelle version » et téléchargement de chaque version ; `Contract.pdf_file`/`generated_at` supprimés (migrations `documents/0003` et `0004`).
- [x] Numérotation des contrats par tenant. — Fait (PR B) : `Contract.reference` (ex. `C-2026-007`), attribuée à la première génération via `ContractSequence` (tenant + année) sous `select_for_update`, dans la transaction de création : sans trou, repart à 001 chaque année.
- [ ] Marquage « signé » : figeage du PDF, passage de la date à `signed`, upload optionnel du PDF signé.
- [ ] Stockage des PDF figés : bucket S3 européen via `django-storages` (dev = stockage local).
- [ ] Tests : contenu du PDF, immutabilité après signature, accès protégé aux fichiers (pas d'URL publique devinable).

### Sprint 3.5 — Devis et factures
- [x] **PR D1 — prérequis** (2026-10-01) : `Tenant.vat_number` et `Tenant.iban` (IBAN normalisé et contrôlé : format et clé modulo 97) dans « Ma structure » ; `Gig.deposit_percent` (30 % par défaut, modifiable à chaque date dans « Compléter la date ») ; le contrat affiche le n° de TVA pour un tenant assujetti. Migrations `tenants/0005` et `gigs/0005`.
- ⚠️ **Les PDF de facture du MVP ne remplacent pas la plateforme agréée de facturation électronique** (obligation à vérifier avec le relecteur professionnel, calendrier prévu avant 09/2027 : Phase 5). On garde des données structurées (SIRET, TVA par ligne, instantanés) pour pouvoir ajouter le format Factur-X sans refonte. L'application ne doit pas se dire « conforme » avant cette connexion.
- [ ] Modèles `Quote`, `Invoice`, `DocumentLine`, `InvoiceSequence`.
- [ ] Création depuis une date avec **suggestion** acompte/solde (selon `deposit_percent`).
- [ ] Émission : attribution du numéro dans une **transaction avec verrou** ; snapshot des infos légales ; statut `issued`.
- [ ] **Immutabilité** d'une facture émise (formulaires et vues bloqués, test qui le prouve).
- [ ] **Avoirs** liés à une facture d'origine.
- [ ] Calcul des totaux et de la TVA en `Decimal`, arrondis testés.
- [ ] Mentions légales selon le régime de TVA ; PDF de facture.
- [ ] **Relecture par le professionnel** (comptable) du PDF de facture.
- [ ] Tests : numérotation sans trou (y compris concurrence simulée), immutabilité, totaux, avoir.

### Sprint 3.6 — Feuille de route
- [ ] Modèles `Roadmap`, `RoadmapSlot`, `Lodging`, `Meal`, `GigMember`.
- [ ] Éditeur de feuille de route (ajout/suppression de créneaux en HTMX).
- [ ] **Pré-remplissage** depuis la date (lieu, contacts, heure du concert).
- [ ] **Lien secret** : génération, activation/révocation, page publique sans compte.
- [ ] Vue mobile-first (gros boutons appeler / itinéraire), testée à 375 px.
- [ ] Export PDF.
- [ ] Tests : lien valide/révoqué/inexistant, absence de fuite d'infos sensibles (prix, contrat), isolation.

### Sprint 3.7 — Finances
- [ ] `Payment` et `Expense` avec formulaires rapides (HTMX).
- [ ] Mise à jour automatique du statut de facture selon les paiements.
- [ ] Catégories de dépenses.
- [ ] Bilan par date (facturé / encaissé / dépensé / résultat) — **distinguer recette prévue (prix du contrat) / facturée / encaissée** (F-57, `docs/03-cahier-des-charges.md` §4.8, demandé le 29/09), pas un chiffre unique.
- [ ] Affichage des montants de synthèse en euros entiers arrondis, stockage et calculs au centime près (F-58, demandé le 29/09).
- [ ] Tableau de bord global : totaux annuels, factures en retard, dates sans contrat, prochaines dates.
- [ ] **Export CSV** (`;`, UTF-8 BOM) : recettes, dépenses, factures ; test d'ouverture dans Excel.
- [ ] Tests : calculs, exports, isolation, cas limites (paiement partiel, surpaiement).

### Sprint 3.8 — Légal, sécurité, finition, recette
- [ ] Pages : mentions légales, CGU, confidentialité (à faire relire).
- [ ] Export des données et suppression de compte (F-81).
- [ ] **Audit d'isolation complet** : parcourir chaque URL et chaque vue avec 2 tenants.
- [ ] Revue sécurité : en-têtes, cookies, CSRF, `check --deploy`, dépendances à jour, secrets.
- [ ] Vérifier les téléchargements de fichiers (contrôle d'accès).
- [ ] Passage d'accessibilité de base (contrastes, labels, clavier).
- [ ] Textes d'aide, tooltips, messages d'erreur en français.
- [ ] États vides (« Aucune date pour l'instant — créez la première ») et messages de succès.
- [ ] **Recette** : dérouler la liste de la section 11 du cahier des charges sur staging.
- [ ] Sauvegarde de la base + **test de restauration**.
- [ ] Déploiement en **production** (déclenchement manuel).

**Livrable** : MVP en production.
**Critère de sortie** : la recette du cahier des charges (§11) passe intégralement.

---

## Phase 4 — Bêta fermée (semaines 14–17)

**Objectif** : confronter le MVP à de vrais usages avec un petit groupe, et corriger avant d'ouvrir.

- [ ] Recruter **5 à 10 bêta-testeurs** (issus de la Phase 0 en priorité). Leur offrir un accès gratuit à vie ou prolongé.
- [ ] Préparer un guide de démarrage court (1 page) et un canal de retour direct (e-mail ou groupe de discussion).
- [ ] Observer en direct 2 ou 3 premières utilisations (visio, partage d'écran).
- [ ] Mettre en place un suivi : Sentry, uptime, nombre de comptes créés, dates créées, documents générés, abandons d'onboarding.
- [ ] Rituel hebdomadaire : trier les retours en **bugs / confusions / demandes**.
- [ ] Corriger d'abord les bugs bloquants et les confusions, **pas** les demandes de fonctionnalités.
- [ ] Faire valider définitivement contrat, factures, mentions légales par les professionnels.
- [ ] Rédiger le **registre des traitements RGPD** et vérifier les sous-traitants (hébergeur, e-mail, Sentry, S3).
- [ ] Tester une restauration de sauvegarde réelle ; vérifier les alertes.
- [ ] Mesurer : temps d'onboarding, temps pour un 1er contrat, satisfaction, intention de payer.
- [ ] Décider des priorités de la v1 **à partir des retours**, pas des idées initiales.

**Critères de sortie** :
- aucun bug bloquant ouvert ;
- au moins 60 % des testeurs génèrent un contrat sans aide ;
- au moins 5 testeurs disent qu'ils continueraient à l'utiliser ;
- aucune fuite de données constatée.

---

## Phase 5 — Version 1 payante (à partir de la semaine 18)

**Objectif** : ouvrir à un public plus large et facturer. L'**ordre** doit être revu selon les retours de la bêta.

### 5.1 Abonnement et quotas (priorité haute)
- [ ] Choisir la grille tarifaire — **⚠️ deux modèles concurrents à trancher (Q9, `docs/03-cahier-des-charges.md` §14)** : soit le freemium initial (gratuit jusqu'à 3 dates/an, puis mensuel/annuel), soit les deux formules payantes « Essentiel »/« Collectif » proposées le 29/09 (sans palier gratuit, avec matrice de fonctionnalités par formule). Ne pas développer cette section avant la décision.
- [ ] Intégrer Stripe (Checkout + webhooks), gestion de la facturation des abonnés, résiliation.
- [ ] Appliquer le quota : blocage doux à la 4ᵉ date avec message clair et invitation à s'abonner.
- [ ] Conditions générales de vente.

### 5.2 Facture électronique (échéance : 09/2027)
- [ ] Étudier les **plateformes agréées** et leurs API ; choisir l'option (génération Factur-X + envoi via une PA, ou partenariat).
- [ ] Générer des factures au format **Factur-X** ; ajouter les nouvelles mentions requises (dont SIREN du client).
- [ ] Gestion des statuts de cycle de vie côté plateforme.
- [ ] ⚠️ **Ordre de livraison proposé le 29/09 (Q14, `docs/03-cahier-des-charges.md` §14)** : Lot 1 = périmètre vendable de la formule « Essentiel » ; Lot 2 = « Collectif » **sans** la facturation électronique conforme (affichée « bientôt incluse ») ; Lot 3 = facturation électronique conforme, seulement une fois prestataire/flux/coût validés. **Ne jamais annoncer la facturation électronique comme « incluse » avant des tests réels du flux complet.**

### 5.3 Signature électronique
- [ ] Choisir un prestataire ; intégrer envoi, signature, récupération du PDF signé et du certificat.
- [ ] Passage automatique de la date à `signed`.

### 5.4 Relances et rappels
- [ ] Tâches planifiées (cron Scalingo ou `procrastinate`) : options qui expirent, contrats non signés, factures en retard.
- [ ] E-mails de relance modifiables ; désactivables ; historique des envois.
- [ ] Rappels d'échéances administratives (déclarations, AG d'association).

### 5.5 Confort et partage
- [ ] Export **iCal** (lien d'abonnement à l'agenda).
- [ ] *(idée du 28/09, à confirmer — Q12 §14)* Connexion bidirectionnelle avec Google Calendar, au-delà du simple export iCal.
- [ ] **PWA** de la feuille de route : mode hors-ligne, installation sur l'écran d'accueil.
- [ ] Invitation de membres (rôle `member`) et **invités en lecture**.
- [ ] Bibliothèque de documents types.
- [ ] Modèles de contrats supplémentaires.
- [ ] *(idée du 28/09, à confirmer — Q12 §14)* Formulaire en ligne envoyé à l'organisateur pour qu'il renseigne lui-même ses informations contractuelles (auto-remplissage), inspiré de bord-pro.base44.app.

### 5.6 Exploitation
- [ ] Supervision et alertes ; procédure d'incident ; sauvegardes surveillées.
- [ ] Support (e-mail, FAQ, tutoriels vidéo courts).
- [ ] Analytics respectueux de la vie privée (ex. solution sans cookies).
- [ ] Mises à jour régulières des dépendances et de Django.

### 5.7 Version 2 (à évaluer)
- [ ] Carte des dates et calcul des trajets (OpenStreetMap + service d'itinéraire).
- [ ] Statistiques avancées, import de données, éventuelle app mobile.
- [ ] Contrat couvrant plusieurs dates (tournée en un seul accord) — voir Q7, `docs/03-cahier-des-charges.md` §14.
- [ ] *(à arbitrer — Q10, §14)* Refonte du modèle `Show` vers une hiérarchie `Projet` → `Spectacle` → `Spectacle_version` → `Representation` avec référentiel `Personne` réutilisable, si confirmée utile au-delà du MVP actuel.

---

## Décisions à prendre (à consigner ici)

| Décision | Quand | Statut |
|---|---|---|
| Nom du produit et nom de domaine | Avant Phase 1 (Scalingo, e-mails) | ☐ |
| Modèle de contrat de cession (source, droits de réutilisation) | Phase 0 | ☑ *(reçu du collègue, 2026-09-25 ; relecture professionnelle encore à faire)* |
| Réponses du collègue aux questions ouvertes Q1-Q13 (cahier des charges §14) | Phase 0 | ☐ |
| Clause « Nécitge 2000 / article 293B » retirée du contrat (Q8) — suppression confirmée le 2026-10-01 | — | ☑ |
| Professionnel relecteur (juriste / comptable / CAE) | Phase 0 | ☐ |
| Statut juridique de **ton** activité (facturation de l'app) | Avant la v1 payante | ☐ |
| Rôles : seul le `owner` peut modifier la structure. Faut-il un rôle intermédiaire (ex. « gestionnaire ») pour des utilisateurs non propriétaires qui peuvent la modifier ? | Phase 3.1 (invitation de membres : Phase 5.5) | ☐ |
| Prestataire d'e-mails transactionnels | Phase 3.1 | ☐ |
| Navigation principale limitée à 5 entrées : où loger le carnet d'adresses et les spectacles ? | Sprint 3.2 | ☑ *(2026-09-30 : Accueil · Mes dates · Contacts · Ma structure, puis + Spectacles ; « Nouvelle date » devient un bouton dans « Mes dates »)* — menu à 5 entrées depuis le CRUD `Show` |
| Modèle économique : freemium (3 dates gratuites) ou formules Essentiel/Collectif (Q9) | Avant Phase 5.1 | ☐ |
| Adoption ou non de la hiérarchie Projet/Spectacle/Version proposée le 29/09 (Q10) | Avant toute refonte du modèle `Show` | ☐ |
| Bucket S3 européen (Scaleway, OVH…) | Phase 3.4 | ☐ |
| Politique de conservation des données | Phase 3.8 | ☐ |
| Grille tarifaire | Phase 4 | ☐ |
| Prestataire de signature électronique | Phase 5 | ☐ |
| Plateforme agréée de facturation électronique | Phase 5 (avant 09/2027) | ☐ |

---

## Indicateurs de suivi (pour t'éviter de te perdre)

- **Vélocité** : nombre de tâches terminées par semaine. Si elle est deux fois plus basse que prévu, réduis le périmètre, pas la qualité.
- **Dette** : liste des « TODO » et raccourcis acceptés, révisée à chaque fin de phase.
- **Santé technique** : CI verte, aucune migration manquante, couverture des tests d'isolation à 100 %.
- **Signal marché** : nombre d'entretiens, de testeurs actifs, de personnes prêtes à payer.

## Si tu es en retard

Coupe dans cet ordre : calendrier mensuel → dashboard avancé → export PDF de la feuille de route → devis. **Ne coupe jamais** : isolation des tenants, tests, sauvegardes, numérotation des factures.