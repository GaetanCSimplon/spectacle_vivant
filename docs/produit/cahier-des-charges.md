# Cahier des charges — SaaS « Gestion Spectacle Vivant »

**Version** : 1.2 — **Date** : 30/09/2026 (mise à jour : entretien du 28/09 avec le collègue, note de cadrage abonnement, modèle de données Projet/Spectacle proposé, §14 étendu à Q8-Q15 ; §9 aligné sur le code le 01/10)
**Statut** : à valider après la Phase 0 (entretiens avec de vrais utilisateurs) et après réponses du §14
**Documents liés** : `CLAUDE.md`, `docs/technique/architecture.md`, `docs/metier/guide-metier.md`, `docs/produit/feuille-de-route.md`

---

## 1. Présentation

### 1.1 Contexte
Les artistes auto-produits, petites compagnies et associations loi 1901 du spectacle vivant (musique principalement) produisent quelques dates par an, sans administrateur dédié. Ils gèrent contrats, factures, logistique et suivi financier avec des outils dispersés (Word, Excel, messageries). Les solutions existantes (Orfeo, Bob Booking) ciblent des structures plus établies et sont trop complexes.

### 1.2 Objectif
Fournir une application web **radicalement simple**, mobile-first, permettant à un artiste de gérer seul son activité de production : **de la prise de date au paiement**.

### 1.3 Proposition de valeur
> « Saisis ta date une seule fois : ton contrat, ta facture et ta feuille de route se font tout seuls. »

### 1.4 Cibles
- Artistes indépendants et groupes auto-produits
- Petites compagnies
- Associations loi 1901 produisant quelques dates par an
- Tourneurs émergents

### 1.5 Modèle économique
SaaS B2B freemium : gratuit jusqu'à **3 dates par an**, puis abonnement mensuel/annuel bas. Le paiement en ligne est prévu en v1 ; le quota est prévu dès le MVP dans le modèle de données.

⚠️ **À arbitrer (Q9, §14)** : la note de cadrage technique transmise le 29/09 par le collègue propose un modèle différent — deux formules payantes dès le départ (« Essentiel » / « Collectif », distinguées par nombre d'utilisateurs, quota de signatures, accès à la feuille de route, à la comptabilité de gestion et à la facturation électronique conforme), sans palier gratuit. Ce document ne remplace pas encore ce cahier des charges : **le modèle freemium ci-dessus reste la référence tant que le choix n'est pas confirmé**, mais la grille tarifaire (§5.1 de la feuille de route) ne doit pas être développée avant cette décision.

### 1.6 Principes directeurs
1. **Simplicité avant richesse** : prise en main en moins de 5 minutes ; onboarding en moins de 10 minutes.
2. **Vocabulaire du métier** (cession, cachet, feuille de route), sans jargon comptable ou juridique.
3. **Pas plus de 5 modules** dans la navigation principale.
4. **Assistance** : formulaires guidés (wizards), modèles pré-remplis, tooltips.
5. **Mobile-first** : la consultation en déplacement doit être impeccable sur smartphone.
6. **Fiabilité des documents** : ce qui est émis est figé et traçable.

---

## 2. Périmètre

### 2.1 MVP (v0.x)
| Réf. | Fonctionnalité |
|---|---|
| M0 | Comptes, connexion, onboarding, isolation des structures |
| M1 | Carnet d'adresses (organisateurs, lieux, contacts) |
| M2 | Spectacles |
| M3 | Dates (`Gig`) avec statuts, vue liste et calendrier |
| M4 | Contrat de cession PDF |
| M5 | Devis et factures PDF (acompte / solde) |
| M6 | Feuille de route mobile avec lien secret + PDF |
| M7 | Paiements, dépenses, tableau de bord, export CSV |
| M8 | Ma structure (infos légales) |
| M9 | Pages légales, RGPD de base |

### 2.2 Version 1
Paiement d'abonnement (Stripe) et quotas ; signature électronique (prestataire) ; facture électronique conforme (Factur-X, avant 09/2027) ; relances automatiques ; rappels d'échéances ; export iCal ; PWA de la feuille de route (hors-ligne) ; comptes « invités en lecture » ; bibliothèque de documents types.

### 2.3 Version 2
Carte des dates avec distances et temps de trajet ; import de données ; statistiques avancées.

### 2.4 Hors périmètre
Calcul de charges sociales GUSO/intermittence ; connecteur expert-comptable ou CAE ; aide au choix du statut juridique ; comptabilité générale (plan comptable, bilan, déclaration de TVA) ; billetterie ; droits SACEM ; application mobile native ; paie des artistes.

---

## 3. Utilisateurs et rôles

| Rôle | Description | MVP |
|---|---|---|
| **Owner** | Crée la structure, accès complet, gère l'abonnement | Oui |
| **Member** | Membre de la structure, accès complet aux données (sauf paramètres sensibles) | Prévu dans le modèle, invitation en v1 |
| **Lecteur invité** | Consultation d'une date ou d'une feuille de route | Via lien secret |

Un utilisateur = une structure en MVP (modèle `Membership` prêt pour plusieurs).

---

## 4. Exigences fonctionnelles

> Convention : **F-xx** = exigence, **CA** = critère d'acceptation testable.

### 4.1 Comptes et structure (M0, M8)
- **F-01 Inscription** par e-mail + mot de passe, confirmation d'e-mail. *CA : un nouvel utilisateur reçoit un e-mail et peut se connecter après confirmation.*
- **F-02 Connexion / déconnexion / mot de passe oublié.**
- **F-03 Onboarding guidé** (≤ 5 écrans) : nom de la structure, forme juridique, SIRET (optionnel), régime de TVA, premier spectacle, première date. *CA : un utilisateur de test obtient un contrat PDF en moins de 10 minutes.*
- **F-04 Fiche « Ma structure »** : nom, forme juridique (association, micro-entreprise, société, CAE, autre), adresse, SIRET, **code APE** *(demandé le 28/09)*, régime de TVA, n° de TVA, IBAN, n° de licence/récépissé (optionnel), logo. *CA : ces infos apparaissent dans les contrats et factures.*
- **F-05 Isolation** : un utilisateur ne voit et ne modifie jamais les données d'une autre structure. *CA : tests automatisés d'isolation sur chaque modèle et chaque vue.*
- **F-06 Équipe** *(demandé le 2026-10-09)* : onglet « Équipe » de « Ma structure », annuaire des artistes et de l'équipe de la structure (`Person` : nom, prénom, fonction, statut, téléphone, e-mail, cachet moyen facultatif, notes). Dans l'éditeur de feuille de route, on peut choisir une personne de l'équipe au lieu de ressaisir ses coordonnées ; chaque fiche liste ses dates et chaque date ses participants (suivi uniquement : **aucun calcul de paie**). *Gestion sociale (2026-10-27) : la fiche porte aussi la date de naissance, le numéro de sécurité sociale (visibles du seul propriétaire, pour la personne qui tient l'administratif ; jamais dans un document ni une feuille de route) et deux cases Artiste / Technicien. Usage hors de l'application pour l'instant : on réunit les informations, on ne calcule rien. Une dépense peut être faite par un membre (« à rembourser » puis « remboursée le »), voir la feuille de route, sprint 3.18.*

### 4.2 Carnet d'adresses (M1)
- **F-10** CRUD `Promoter` (nom, type, SIRET, adresse de facturation, e-mail, téléphone, notes).
- **F-11** CRUD `Venue` (nom, adresse, jauge, informations d'accès, notes).
- **F-12** CRUD `Contact` rattaché à un `Promoter` ou à un `Venue` (nom, rôle, e-mail, téléphone). *Rôles usuels suggérés (28/09) : Accueil, Technique, Comm' — texte libre en MVP.*
- **F-13** Recherche en direct (HTMX) sur les trois listes. *CA : la liste se filtre en < 500 ms après la saisie.*
- **F-14** Création à la volée depuis le formulaire d'une date (« + Nouvel organisateur »).
- **F-16** *(demandé le 2026-10-12, reprend la première idée de Q12)* **Formulaire envoyé à l'organisateur** : en plus de la saisie classique, un bouton crée un lien secret temporaire (7 jours, à usage unique, révocable) vers une page publique où l'organisateur remplit ses informations (adresse, SIRET, représentant, licence, e-mail, téléphone, un autre contact facultatif). Les réponses sont gardées en attente ; l'utilisateur les compare à la fiche et applique celles qu'il choisit, puis elles sont effacées. *CA : la page publique ne montre aucune donnée de la structure hors son nom et celui de l'organisateur.*
- **F-15** *(demandé le 2026-10-09, version légère de Q1 ; critères à choix multiple le 2026-10-13)* **Qualification des organisateurs** : étiquette de suivi (Prospect, En négociation, En signature, Client actif, Sans suite) et six critères à choix multiple (type d'organisateur, type d'évènement, esthétique / discipline, format / jauge, période habituelle, rôle dans l'évènement), jauge indicative, autres précisions, filtres sur la liste. Pas d'historique d'échanges ni de relances (v1/v2).

### 4.3 Spectacles (M2)
- **F-20** CRUD `Show` : titre, description, durée, effectif, fiche technique (texte + fichier PDF optionnel), prix habituel (indicatif), **lien EPK** *(press-kit électronique, demandé le 28/09)*.

### 4.4 Dates (M3)
- **F-30 Création guidée d'une date** (wizard) : spectacle → organisateur → lieu → date/horaires → prix et conditions → récapitulatif.
- **F-31 Statuts** : `option`, `confirmed`, `signed`, `cancelled`. Transitions autorisées : option→confirmed→signed ; option/confirmed/signed→cancelled. *« Réalisé » et « Payé » sont des indicateurs calculés (date passée, facture soldée), pas des statuts.*
- **F-32 Option** : date de fin d'option facultative, mise en évidence quand elle approche.
- **F-33 Page de détail d'une date** : résumé, statut, documents, feuille de route, paiements, dépenses, prochaines actions.
- **F-34 Liste des dates** avec filtres (statut, mois, spectacle) via HTMX.
- **F-35 Vue calendrier mensuel** (dates colorées par statut).
- **F-36 Annulation** : une date annulée est conservée (historique), exclue des totaux à venir.
- **F-37 Quota freemium** : le nombre de dates de l'année est comptabilisé ; le blocage se fait en v1. *(Voir Q9, §14 — dépend du modèle économique retenu.)*

### 4.5 Contrat de cession (M4)
- **F-40** Génération d'un PDF de contrat depuis une date (données de la structure, de l'organisateur, du lieu, de la date, prix, conditions).
- **F-41** Aperçu avant génération et possibilité d'éditer les conditions particulières (champ texte).
- **F-42** Numéro de contrat unique par structure. Historique des versions générées.
- **F-43** Marquage « signé » (manuel en MVP) : fige un PDF, fait passer la date à `signed`.
- **F-44** *(2026-10-12)* Guide « Faire signer le contrat » : la signature électronique se fait **avec le compte de l'utilisateur** chez le service de son choix ; l'application explique la marche à suivre puis récupère le PDF signé (F-43). Branchement automatique par clé d'accès de l'utilisateur : seulement si demandé ; compte partagé par l'éditeur : seulement si l'application génère du revenu.
- **F-45** *(2026-10-13)* Choix du modèle de contrat de cession parmi quatre (Modèle 1 par défaut). Le choix est libre tant que le contrat est en brouillon, chaque version générée garde son modèle, et un contrat signé ne change plus de modèle.
- *CA : le PDF est lisible, paginé, contient toutes les mentions prévues par le modèle validé.*

### 4.6 Devis et factures (M5)
- **F-50** Création de devis et de factures depuis une date (lignes : désignation, quantité, prix HT, taux de TVA).
- **F-51** Types de facture : acompte, solde, totale. Suggestion automatique de l'acompte et du solde selon les conditions de la date.
- **F-52** Numérotation séquentielle sans trou par structure et par année, attribuée à l'émission.
- **F-53** Statuts : `draft` → `issued` → `paid` ; `cancelled` par avoir uniquement. Une facture `issued` n'est plus modifiable.
- **F-54** Avoir : facture négative liée à la facture d'origine.
- **F-55** PDF avec mentions obligatoires et snapshot des infos légales à l'émission.
- **F-56** Mention de TVA selon le régime (assujetti, franchise en base, non assujetti). ⚠️ *Textes à valider par un expert-comptable — voir aussi Q13, §14.* ⚠️ **Nuance signalée par la note de cadrage du 29/09** : « sans TVA facturée » (ex. franchise en base) et « non assujetti à la TVA » (ex. association hors champ) sont **deux cas juridiquement distincts**, à ne pas confondre dans les mentions générées — impacte directement Q13.
- **F-57** *(29/09)* Distinction entre **recette prévue** (prix convenu au contrat), **recette facturée** (montant des factures émises) et **recette encaissée** (paiements reçus) : ces trois montants peuvent différer (ex. avoir, facture partielle) et doivent rester consultables séparément, pas fusionnés en un seul chiffre. Le tableau de bord (F-74) et le bilan par date (F-73) s'appuient sur cette distinction.
- **F-58** *(29/09)* Affichage des montants en **euros entiers arrondis** dans les vues de synthèse (tableau de bord, listes), mais **stockage et calculs au centime près** (`Decimal`, cohérent avec RG-10) : l'arrondi est un choix d'affichage, jamais de stockage.
- **F-59** *(2026-10-09)* **Nom de document** : un nom facultatif (interne, absent du PDF) sur les devis et les factures, pour les repérer facilement ; modifiable même après émission car sans valeur légale.

### 4.7 Feuille de route (M6)
- **F-60** Éditeur de feuille de route par date : créneaux horaires (arrivée, balances, repas, concert, départ…), contacts sur place, hébergement, repas, notes, membres de l'équipe.
- **F-61** Pré-remplissage depuis la date (lieu, adresse, contacts du lieu, horaires du concert).
- **F-62** **Lien secret** : URL non devinable, activable/révocable, sans compte requis. *CA : sans le lien, la page est inaccessible ; après révocation, l'ancien lien renvoie une 404.*
- **F-63** Affichage **mobile-first** (lisible à 375 px, gros boutons « Appeler », « Itinéraire »).
- **F-64** Export PDF.

### 4.8 Finances (M7)
- **F-70** Enregistrement de `Payment` (montant, date, mode) rattaché à une facture ; le statut de la facture se met à jour.
- **F-71** Enregistrement de `Expense` (date, montant, catégorie, libellé, justificatif optionnel) rattaché à une date.
- **F-72** Catégories : cachets, transport, hébergement, technique, communication, autres.
- **F-73** **Bilan par date** : facturé, encaissé, dépensé, résultat.
- **F-74** **Tableau de bord** : total facturé et encaissé sur l'année, factures en attente ou en retard, dates sans contrat, prochaines dates.
- **F-75** **Export CSV** (recettes, dépenses, factures), période au choix, encodage UTF-8 avec BOM et séparateur `;` (compatible Excel FR).
- **F-76** *(2026-10-09)* **Accueil enrichi** : les cartes des prochaines dates affichent acompte et solde (facturé / encaissé) ; une vue d'ensemble compare prévu, facturé, encaissé, dépensé et résultat. Un budget de dépenses prévu par date (pour mesurer les écarts de dépenses) est en attente de la réponse du métier.

### 4.9 Légal et RGPD (M9)
- **F-80** Mentions légales, CGU, politique de confidentialité.
- **F-81** Export des données de la structure (CSV/JSON) et suppression du compte sur demande.
- **F-82** Consentement pour e-mails non transactionnels si applicable.
- **F-83** *(demandé le 2026-10-16, spec `spec_popup_checklist_contractualisation.1.md`)* **Checklist contractualisation** d'une date : fenêtre modale de 16 cases à cocher en 6 sections (avant confirmation, contrat, documents techniques, facturation, intervenants / intermittents, clôture), enregistrées à chaque clic, bouton « Réinitialiser » avec confirmation. Une case est faite ou pas faite : **ni alerte, ni blocage, ni statut intermédiaire, ni barre de progression**, et aucun lien avec les devis, contrats ou paiements réels. Une checklist par date (pas de projet ni de tournée, Q10) ; bouton sur la fiche de la date et sur la page du contrat ; tout membre peut cocher ; date de dernière modification affichée, auteur conservé pour l'audit ; incluse dans l'export des données. Routes HTMX, pas d'API REST (`CLAUDE.md` §2). Évolutions prévues dans l'architecture, non codées : cases personnalisées, modèles par type de spectacle, responsable par case, échéances.
- **F-84** *(demandé le 2026-10-22)* **Site de présentation** dans l'application : page d'accueil publique (slogan, thèmes, fonctionnalités), page Fonctionnalités, page Contact avec formulaire envoyant un e-mail à l'adresse de contact (rien n'est enregistré), liens vers les pages légales. Pages sans connexion ni donnée de structure ; fermées aux moteurs de recherche tant que le contenu n'est pas prêt. *Hors périmètre de cette exigence :* page Tarifs et abonnement (Phase 4-5), liste d'attente enregistrée (nécessiterait un consentement et une durée de conservation).

---

## 5. Règles de gestion

| Réf. | Règle |
|---|---|
| RG-01 | Toute donnée métier appartient à **une** structure et n'est jamais visible d'une autre. |
| RG-02 | Un `Gig` relie obligatoirement un `Show`, un `Promoter` et une date ; le `Venue` est facultatif au statut `option`, obligatoire à `signed`. |
| RG-03 | Un `Contact` est rattaché soit à un `Promoter`, soit à un `Venue` (exactement un des deux). |
| RG-04 | Une date `cancelled` ne peut pas être remise en `option`/`confirmed` sans action explicite de réactivation. |
| RG-05 | Les numéros de facture sont uniques et **sans trou** par structure et par année. |
| RG-06 | Une facture `issued` est immuable ; toute correction passe par un avoir. |
| RG-07 | À l'émission, les infos légales de la structure et du client sont copiées dans le document. |
| RG-08 | Un contrat `signed` conserve son PDF figé. |
| RG-09 | Une facture ne peut être marquée `paid` que si la somme des paiements ≥ son total. |
| RG-10 | Les montants sont exprimés en euros, avec deux décimales (`Decimal`). |
| RG-11 | Un lien secret de feuille de route expose uniquement cette feuille de route, jamais le reste de la date (prix, contrat…). |
| RG-12 | Si `Gig.is_free` est vrai, `Gig.ticket_price` est automatiquement forcé à 0 (calculé, non modifiable manuellement dans ce cas). |

---

## 6. Exigences non fonctionnelles

### 6.1 Performance
- Pages courantes rendues en < 1 s (95e centile) avec 500 dates par structure.
- Génération d'un PDF en < 5 s.

### 6.2 Sécurité
- HTTPS obligatoire, cookies sécurisés, protection CSRF, mots de passe hachés (défaut Django), limitation des tentatives de connexion.
- Secrets hors du code. Dépendances mises à jour régulièrement.
- Journalisation sans donnée personnelle. Sentry configuré pour ne pas envoyer de PII.
- `manage.py check --deploy` sans avertissement critique avant chaque mise en production.

### 6.3 RGPD
- Hébergement des données en **France/UE**, sous-traitants UE ou clauses adaptées.
- Registre des traitements, politique de confidentialité, procédure d'export et suppression.
- Minimisation : ne collecter que ce qui est nécessaire.

### 6.4 Conservation
- ⚠️ Les documents comptables (factures) doivent être conservés plusieurs années (10 ans en pratique courante) : la suppression d'un compte doit tenir compte de cette obligation. *À valider.*

### 6.5 Sauvegardes et disponibilité
- Sauvegardes quotidiennes de la base, restauration **testée au moins une fois** avant la bêta.
- Objectif de disponibilité de 99 % pendant la bêta, avec supervision (moniteur d'uptime).

### 6.6 Compatibilité et accessibilité
- Navigateurs : versions récentes de Chrome, Safari, Firefox, Edge. Mobile : iOS Safari, Android Chrome.
- Accessibilité : contrastes suffisants, libellés de formulaires, navigation au clavier (objectif d'orientation WCAG AA).

### 6.7 Maintenabilité
- Couverture de tests sur la logique métier et l'isolation. CI obligatoire avant fusion.
- Code lisible, conventions dans `CLAUDE.md`, migrations versionnées.

---

## 7. Contraintes UX

- Navigation principale : **Dates · Spectacles · Contacts · Documents/Finances · Ma structure** (5 entrées max).
- Wizards pour les créations complexes (date, onboarding).
- Tooltips contextuels ; textes d'aide courts. Messages d'erreur en français, compréhensibles.
- Actions primaires évidentes (un bouton principal par écran).
- Tous les écrans utilisables à une main sur smartphone.

---

## 8. Architecture technique (résumé)

Monolithe modulaire Django 5.2 LTS + PostgreSQL ; HTMX + Alpine.js + Tailwind ; WeasyPrint ; `django-allauth` ; hébergement Scalingo (France) ; bucket S3 européen ; Sentry (UE).
Multi-tenant par **base partagée avec clé `tenant`**. Détails : `docs/technique/architecture.md`.

---

## 9. Modèle de données (MVP)

> Tous les modèles marqués (T) héritent de `TenantOwnedModel` (FK `tenant`).

**User** : email (login), first_name, last_name.
**Tenant** *(anciennement `Organization`)* : name, legal_form, address, siret, **code_ape** (code APE/INSEE — nouveau champ demandé le 28/09, saisi juste après le SIRET, distinct de l'ancien champ ambigu « APA », voir Q11), licence_number, representative_name, representative_role, jurisdiction_city (ville du tribunal compétent, art. 8 du contrat), vat_rate (taux de TVA par défaut, structure assujettie), vat_regime, vat_number, iban, **bic, phone, email** *(13/10, pour les modèles de contrat)*, logo, plan, created_at.
**Membership** : user, tenant, role (`owner`/`member`). Unique (user, tenant).

**Show (T)** : title, group_name (nom du groupe/artiste, distinct du titre du spectacle), description, performers (distribution, texte libre), duration_minutes (« Durée du Set »), crew_size, tech_sheet_text, tech_sheet_file, rider_file (fiche d'exigences artiste/hospitalité, distincte de la fiche technique), epk_url (lien vers le press-kit électronique — demandé le 28/09), **artists_count, technicians_count, soundcheck_minutes (durée minimale des balances), soundcheck_to_set_minutes (temps minimum entre la fin des balances et le set), analytic_code (code pour le reporting et les exports CSV)** *(13/10)*, indicative_price, sacem_number (« N° SACEM »), sacem_object_number (« N° d'objet »).
**Promoter (T)** : name, **kinds, event_types, aesthetics, formats, usual_periods, event_roles (listes), indicative_capacity, qualification_other**, siret, **code_ape, vat_number**, representative_name, representative_role, billing_address, email, phone, notes.
**Venue (T)** : name, address, capacity (« Jauge Max »), **configuration**, access_info, notes.
**Contact (T)** : name, role (rôles usuels observés côté métier : Accueil, Technique, Comm' — texte libre en MVP, pas d'`enum` fermé), email, phone, promoter (nullable) **ou** venue (nullable) — contrainte : exactement un des deux.

> **Non retenu dans ce modèle MVP** (voir Q10, §14) : le document « Refonte de la base Projet – Spectacle » du 29/09 propose de remplacer `Show` par une hiérarchie `Projet` → `Spectacle` → `Spectacle_version` → `Representation`, avec un référentiel `Personne` réutilisable et un `Distribution_type` (casting par défaut, copié — pas référencé — sur chaque représentation). C'est un modèle plus riche, pertinent pour des compagnies gérant plusieurs versions d'un même spectacle, mais il représenterait une refonte du cœur déjà développé (`Show`/`Gig`, CRUD terminé en Sprint 3.2). **Traité comme une évolution v1/v2 candidate, pas comme une modification du modèle MVP**, tant que ce n'est pas explicitement tranché. Détaillé champ par champ le 01/10 (export Excel du collègue) — voir `docs/metier/modele-spectacle.md`, qui identifie aussi quelques listes de valeurs (catégories d'équipe, types de document…) réutilisables dès maintenant, indépendamment de la décision Q10.

**Gig (T)** : show, promoter, venue (nullable), date, status, price (prix de cession HT), deposit_percent (30 % par défaut, modifiable par date ; le taux de TVA est porté par `Tenant.vat_rate`, pas par la date), option_expires_on, conditions, notes, get_in_time, soundcheck_time (« Balances »), performance_time (« Passage »), crew_headcount (« Nb Participants », pour repas/hébergement), is_free (« Concert Gratuit »), ticket_price (« Prix des places » — voir RG-12), invitations_count (nombre d'invitations dues, variable), signing_place (« Fait à … »), **event_name, performances_count (1), copies_count (2), signature_deadline_days, payment_method, deposit_due_on, balance_due_on, meals, lodging, local_transport, other_hospitality** *(13/10, rédaction du contrat ; tous facultatifs, vide = pointillés)*.
**GigMember (T)** : gig, name, role, phone, email.

**Contract (T)** : gig (OneToOne), template (`model_1` à `model_4`), reference (`C-AAAA-NNN`, attribuée à la première génération, sans trou par structure et par année via `ContractSequence`), status (`draft`/`signed`), signatory_name, signatory_role, signed_at, signed_version (version figée à la signature), signed_pdf (scan facultatif).
**ContractVersion (T)** : contract, number, template, pdf_file, created_at, created_by — un PDF par génération, jamais écrasé ni supprimé. Les conditions particulières sont `Gig.conditions`.
**Invoice (T)** : gig, number (`F-AAAA-NNNN`, attribué à l'émission), kind (`deposit`/`balance`/`full`/`credit_note`), status (`draft`/`issued`/`cancelled` ; `paid` viendra avec les paiements), issue_date, due_date, issuer_snapshot et customer_snapshot (JSON, copiés à l'émission), total_excl_tax, total_vat, total_incl_tax, credit_note_of (obligatoire pour un avoir, interdit sinon), pdf_file. Un avoir est une facture négative dans la même série de numéros.
**Quote (T)** : mêmes champs sans `kind`/`due_date`/`credit_note_of`, avec valid_until et un numéro `D-AAAA-NNNN` (série séparée).
**DocumentLine (T)** : invoice **ou** quote (exactement un des deux), position, label, quantity, unit_price_excl_tax, vat_rate.
**DocumentSequence (T)** : tenant, kind (`invoice`/`quote`), year, last_number — ligne verrouillée à l'émission. Remplace le `InvoiceSequence` prévu au départ.

**Roadmap (T)** : gig (OneToOne), token, is_published, notes.
**RoadmapSlot (T)** : roadmap, kind, time, label, note.
**Lodging (T)** / **Meal (T)** : roadmap, address / place, time, notes.

**Payment (T)** : invoice, amount, date, method.
**Expense (T)** : gig, category, label, amount, date, receipt_file.

> **Person (T)** *(prévu, F-06)* : first_name, last_name, role, status, phone, email, average_fee (facultatif), **address (+ code postal, ville, département) et guso_number — visibles du propriétaire seulement** *(13/10)*, notes ; liée à `GigMember` (FK facultative) pour savoir qui a participé à quelle date. Lien avec un `Show` non retenu pour l'instant.

---

## 10. Écrans principaux

1. Inscription / connexion / onboarding (assistant)
2. Accueil / tableau de bord
3. Liste des dates + calendrier
4. Assistant de création d'une date
5. Détail d'une date (documents, feuille de route, paiements, dépenses)
6. Aperçu et génération du contrat
7. Édition d'une facture / d'un devis
8. Éditeur de feuille de route + vue publique mobile
9. Listes et fiches : spectacles, organisateurs, lieux, contacts
10. Finances : dashboard, dépenses, export
11. Ma structure
12. Pages légales

---

## 11. Recette du MVP (critères d'acceptation globaux)

Le MVP est **livrable** quand un utilisateur de test, sans aide, peut :
- [ ] créer son compte et sa structure en < 10 min ;
- [ ] créer un organisateur, un lieu et un spectacle ;
- [ ] créer une date et la faire évoluer de `option` à `signed` ;
- [ ] générer un contrat PDF correct, le télécharger ;
- [ ] émettre une facture d'acompte puis de solde, avec numérotation correcte ;
- [ ] enregistrer un paiement et voir la facture passer à `paid` ;
- [ ] créer une feuille de route, la partager par lien, l'ouvrir sur un téléphone ;
- [ ] saisir une dépense, voir le bilan de la date et exporter un CSV ;
- [ ] et que **les tests d'isolation prouvent** qu'une autre structure ne voit rien de tout cela.

---

## 12. Risques

| Risque | Impact | Mesure |
|---|---|---|
| Produit non désiré par le marché | Élevé | Phase 0 : entretiens ; bêta fermée |
| Fuite de données entre structures | Critique | Isolation testée dès la Phase 1 |
| Contrats/factures non conformes | Élevé | Validation par un professionnel ; mentions figées |
| Facture électronique (09/2027) | Moyen | Prévue en v1 |
| Dérive du périmètre | Élevé | Liste hors périmètre ; ce cahier des charges fait foi |
| Charge de travail en solo | Moyen | Découpage en petites PR, MVP resserré |
| Dépendance à l'IA (code non compris) | Moyen | Relecture systématique, tests, plan avant code |
| WeasyPrint difficile à déployer | Moyen | Test dès la Phase 1 |

---

## 13. Livrables

Code source (dépôt Git), application déployée (staging et production), documentation (`docs/`), jeux de tests, pipeline CI/CD, modèles de documents validés.

---

## 14. Questions ouvertes (issues du document de logique métier du 2026-09-25, complétées par l'entretien du 28/09 et le point d'étape du 30/09)

Le document « Logique métier – Cycle de vie d'un spectacle » fourni par le collègue décrit un périmètre plus large que le MVP défini ci-dessus. **Tant que les réponses ci-dessous ne sont pas obtenues, le périmètre du §2 (MVP/v1/v2/hors périmètre) reste la référence pour le développement.**

| # | Sujet | Ce que décrit le document métier | Statut MVP actuel | Question à trancher |
|---|---|---|---|---|
| Q1 | CRM de prospection (Phases 1-2 du document) | Fiche de qualification, statuts `Prospect` → `En négociation` → `Client actif`, historique des échanges, canal d'entrée | ✅ **Version légère retenue (2026-10-09, F-15)** : étiquette de suivi, type d'évènement, esthétique, filtres. Historique des échanges et canal d'entrée : non prévus | Le reste (historique, relances) est à situer en v1/v2. |
| Q2 | Types de contrat | Cession (géré) / coréalisation (partage de recette + responsabilité solidaire employeur au-delà de 5000 €) / location de salle | Seule la cession est gérée (`Gig.price`, prix HT fixe) | Faut-il gérer les trois dès le MVP, ou rester sur la cession seule pour l'instant ? *(Le modèle de contrat transmis est un contrat de cession simple — cohérent avec le MVP actuel.)* ✅ **Précisé le 2026-10-13** : seule la cession est gérée, mais en **quatre modèles de rédaction** au choix (F-45). Coréalisation et location de salle : toujours non gérées. |
| Q3 | Suivi temps réel jour J (Phase 5 du document) | Check-in équipe, horaires réels vs prévus, remontée d'incidents en direct | Non prévu (feuille de route = document consultable, pas de suivi live) | Utile pour la cible « quelques dates par an » ou fonctionnalité pour un usage plus intensif (v2) ? |
| Q4 | Paie des intermittents (Phase 4 et 6 du document) | DPAE, relevés d'heures, bulletins récapitulatifs, export GUSO | **Explicitement hors périmètre** (§2.4) | Confirmation : l'app reste hors de ce périmètre (renvoi vers le GUSO/un comptable), ou attente réelle de couverture ? Risque juridique élevé à évaluer avec un professionnel si oui. |
| Q5 | Déclarations SACEM/SACD/CNM (Phase 6 du document) | Déclaration définitive et régularisation du montant réel de recette | **Explicitement hors périmètre** (§2.4) ; le contrat reçu montre que c'est **l'organisateur** qui gère ces déclarations, pas la structure de l'utilisateur | À confirmer que ça reste hors périmètre — le contrat fourni semble aller dans ce sens |
| Q6 | Capitalisation / relance (Phase 7 du document) | Historique par partenaire, qualification post-date, relance automatique programmable | Non prévu au MVP | v1/v2, à situer une fois Q1 tranché (dépend du CRM) |
| Q7 | Contrat couvrant plusieurs dates | Les tableurs de suivi (`contrat.xlsx`, `date_representation.xlsx`) montrent qu'un contrat peut lister plusieurs représentations (tournée négociée en un seul accord) | Un `Contract` est lié à **une seule** `Gig` — cohérent avec le vrai contrat déjà reçu (une seule date) | À garder en tête pour v1/v2 si des tournées multi-dates doivent être couvertes par un contrat unique ; aucun changement nécessaire pour le MVP |

**Recommandation** : traiter Q2 et Q5 en priorité (impact direct sur le modèle de données du contrat, déjà en cours de développement) ; Q4 en priorité également, car sa réponse conditionne fortement la charge de travail restante et le niveau de risque juridique du projet. Q7 ne nécessite aucune décision immédiate.

### Questions complémentaires (entretien du 28/09 et point d'étape du 30/09)

| # | Sujet | Contexte | Question à trancher |
|---|---|---|---|
| Q8 | ✅ Tranchée (2026-10-01) — Clause TVA du contrat | La mention « Nécitge 2000 et non assujetti à la TVA : article 293b du CGI » du modèle d'origine ne doit **pas** être conservée. | Décision : la suppression faite lors du nettoyage du template est confirmée. Aucune retouche à prévoir ; la mention de TVA reste gérée par F-56 / Q13. |
| Q9 | Modèle économique : freemium ou abonnement à deux formules | La note de cadrage technique du 29/09 propose deux formules payantes (« Essentiel » / « Collectif », avec une matrice de fonctionnalités par formule) au lieu du modèle « gratuit jusqu'à 3 dates/an » actuel (§1.5). | Confirmer si ce modèle remplace le freemium, et si oui figer la matrice de fonctionnalités par formule avant de développer la grille tarifaire (Phase 5.1). |
| Q10 | Modèle de données Projet/Spectacle/Version | Le document du 29/09 propose une hiérarchie `Projet` → `Spectacle` → `Spectacle_version` → `Representation` plus riche que le `Show`/`Gig` actuel (déjà développé). Détaillé champ par champ le 01/10 (export Excel) — voir `docs/metier/modele-spectacle.md`. | Adopter cette hiérarchie maintenant (refonte), la traiter comme évolution v1/v2, ou n'en reprendre que certains éléments (ex. `Personne` réutilisable, ou simplement les listes de valeurs `categorie_equipe`/`fonction`/`type_document` détaillées dans l'annexe) ? |
| Q11 | Signification exacte de « APA » | Le cahier des charges et le contrat mentionnaient un champ « Siret/APA » ambigu ; le champ a été simplifié en « SIRET » seul, et un champ `code_ape` (code INSEE) a été ajouté séparément suite à la demande du 28/09. | Confirmer que « APA » ne désignait rien d'autre que ce qui a été couvert, sinon préciser ce qui manque. |
| Q12 | Nouvelles fonctionnalités proposées le 28/09 | Auto-remplissage d'un formulaire en ligne envoyé à l'organisateur pour ses propres informations contractuelles (cf. exemple bord-pro.base44.app) ; connexion bidirectionnelle avec Google Calendar (en plus de l'export iCal déjà prévu en v1, §2.2) ; annuaire des salariés/intermittents rattaché à la structure (et éventuellement à un spectacle). ✅ **Annuaire retenu le 2026-10-09 (F-06)**, sans numéro de sécurité sociale ; ✅ **formulaire envoyé à l'organisateur retenu le 2026-10-12 (F-16)** ; ❌ **connexion Google Calendar écartée le 2026-10-31** (l'export iCal suffit, sans lien d'abonnement). | Ces trois idées sont-elles à inscrire en v1/v2 (voir feuille de route §5.7), ou certaines sont-elles prioritaires ? |
| Q13 | Questions techniques du contrat listées dans le point d'étape du 30/09 | Date du contrat vs date de signature ; l'article 293B du CGI convient-il aussi bien au cas « non assujetti » qu'au cas « franchise en base » (voir aussi F-56) ; nombre d'invitations par défaut ; ville du tribunal compétent (par structure ou fixe — voir `Tenant.jurisdiction_city`, déjà modélisé) ; qui relira le contrat avant la Phase 4. | Réponses à obtenir du collègue et/ou du futur relecteur professionnel — voir aussi Phase 0 de la feuille de route. |
| Q14 | Ordre de livraison de la v1 (note de cadrage du 29/09) | La note technique propose 3 lots : **Lot 1** = tout le périmètre vendable de la formule « Essentiel » ; **Lot 2** = « Collectif » sans la facturation électronique conforme (affichée « bientôt incluse ») ; **Lot 3** = facturation électronique conforme, seulement une fois le prestataire, le flux et le coût validés. Règle explicite : **ne jamais qualifier la facturation électronique d'« incluse » avant des tests réels du flux complet.** | À confirmer comme trame de la Phase 5 (`docs/produit/feuille-de-route.md` §5.1-5.2), dépend de Q9 (formules retenues). |
| Q15 | Sens du mot « Structure » dans l'export Excel du 01/10 | Dans `docs/metier/modele-spectacle.md`, `structure_porteuse_id` et `employeur_id` portent des identifiants `STR-…` et correspondent à **notre `Tenant`**, alors que `CLAUDE.md` §5 retient que, pour le métier, « Structure » désigne l'organisateur ou le lieu. L'export semble utiliser **un seul référentiel `STR-…`** pour toutes les organisations (la structure de l'utilisateur comme celles des organisateurs). | Confirmer avec le collègue : un référentiel unique d'organisations (impact sur Q10 : table commune à `Tenant` et `Promoter` ?) ou deux notions distinctes ? Tant que ce n'est pas tranché, le lexique du code ne change pas. |
| Q16 | Plan des lieux dans la feuille de route (demandé le 2026-10-03) | Souhait « optionnel mais très apprécié », **pour plus tard** : un plan indiquant le lieu de représentation, l'hébergement, la restauration. L'utilisateur doit pouvoir copier les adresses et les ouvrir dans l'outil de cartographie de son choix ; **pas de service de cartes externe** (ou le moins possible). Le bouton « Copier l'adresse » est fait (Sprint 3.6). | Le « plan » est-il un fichier joint (image/PDF : plan de salle, d'accès, de scène) avec aperçu, ou autre chose ? Combien par feuille de route, quels formats, quelle taille maximale ? Hors périmètre MVP (CLAUDE.md §10 : pas de carte) tant que non confirmé. |
| Q17 | RADAR de tournée (rendez-vous du 2026-10-15) | Fonction annoncée : suivi approfondi et anticipation de tournée, qui partage les données de Bòrd. spécification reçue de l'associé : `docs/produit/specification-radar.md` | **Reporté après la bêta** (2026-10-25) : rien n'est codé | Périmètre exact de RADAR et articulation avec Bòrd (spécification de l'onglet Bòrd, §3) |
| Q18 | Spécification de l'onglet Bòrd (associé, 2026-10-15) | Projets et tournées, budget initial / actualisé / engagé, subventions, rémunérations et coût employeur par affectation, alertes configurables, saison | **Non prévu** : Bòrd est construit sur les données existantes (`docs/produit/indicateurs-bord.md`) | Chacun de ces blocs, un par un : lien avec Q4 (paie, hors périmètre), Q10 (Projet/Tournée) et Q17 |
| Q19 | Priorisation fonctionnelle de la charte (2026-10-15, §7) | Pipeline de diffusion (prospecté, relancé, option, confirmé, joué, payé), CRM complet, contrats intermittents CDDU et checklist GUSO, budget prévisionnel contre réel, notes de frais, rôles et espace collaboratif, module lieux | **Non prévu** : hors de l'habillage (`docs/marque/charte-graphique.md`) ; liens avec Q1, Q4 (paie, hors périmètre), Q6, Q18 | Quels modules, dans quel ordre, après la mise en ligne |

**Recommandation complémentaire** : Q8 est tranchée (mention non conservée) ; Q9 et Q10 conditionnent des décisions structurantes (modèle de données, tarification) à ne pas prendre à la légère vu l'investissement déjà réalisé sur le MVP actuel — les traiter comme des choix produit à valider avec le collègue avant tout développement, pas comme de simples précisions ; Q11, Q13 et Q14 sont plus légères et peuvent être répondues au fil de l'eau.