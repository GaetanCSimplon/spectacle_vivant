# Bòrd Pro — Architecture de navigation (pour le dev)

19/11/2026 · Version 1.2 (23/11/2026) · décisions NAV-D1 à NAV-D5 validées le 19/11/2026 · v1.2 : zéro migration, PR de confirmations ajoutée

> Document de cadrage. Rien n'est à coder avant validation du plan (CLAUDE.md §9). Les points marqués **À trancher** ne sont pas des décisions prises.

## 0. En bref

1. **Le menu de gauche ne contient que le travail de tous les jours**, en 5 entrées : **Accueil · Bord · Dates · Social · Contacts**.
2. **Tout ce qu'on règle une fois** (fiche de la structure, équipe, spectacles, Paratge, réglages des documents) est rangé dans **un seul espace : « Ma structure »**, placé en pied de menu, hors des 5 entrées.
3. **Règle des clics** : toute tâche fréquente se fait en **2 clics au plus depuis l'Accueil**, **3 clics au plus depuis n'importe quelle page**.
4. C'est une refonte de **navigation, d'URL et de gabarits**. **Aucune nouvelle app Django. Aucune migration** : le cachet de référence réutilise le champ existant `Person.average_fee` (« cachet moyen »), renommé dans l'interface et réservé au propriétaire (décision du 23/11/2026).
5. **Une PR de confirmations** (PR 0) précède la refonte : chaque action qui crée, modifie, supprime ou change un statut affiche un message de succès (Dépenses, paiements, espace équipe par lien secret compris), y compris quand la réponse est un fragment HTMX.

## Organigramme

*[Diagramme intégré : « Navigation Bòrd Pro · 5 entrées de menu, 7 onglets de réglage » — non reproductible en Markdown]*

Le menu de gauche ne change jamais. Tout ce qui se règle une fois vit dans Ma structure ; une info manquante est demandée sur place, sans quitter la tâche (R5).

## 1. Principe directeur

| On travaille (chaque jour) | On paramètre (une fois, puis rarement) |
|---|---|
| Menu de gauche | « Ma structure » |
| Accueil, Bord, Dates, Social, Contacts | Fiche structure, Équipe, Spectacles, Paratge, Documents, Compte et offre |
| Pages d'action : listes, fiches, boutons | Pages de réglage : formulaires, modèles |

**Conséquence pour le code :** une information de paramétrage ne doit jamais obliger l'utilisateur à quitter sa tâche. Si elle manque, on la demande **sur place** (règle R5).

## 2. Le menu de gauche (5 entrées)

| Entrée | URL | Contenu | Apps concernées |
|---|---|---|---|
| **Accueil** | `/` | Liste **« À faire »** : tâches et invitations à agir (alertes Radar), chacune cliquable vers l'action exacte (NAV-D2) ; prochaine date ; 3 chiffres clés renvoyant au Bord | `core`, `gigs`, `finance` (puis Radar) |
| **Bord** | `/bord/` | Prévu / Facturé / Encaissé / Reste, paiements, dépenses, **liste des documents émis** (devis, factures, avoirs) (NAV-D3), exports CSV | `finance`, `documents` |
| **Dates** | `/dates/` | Calendrier + liste ; **fiche date en onglets** : Contrat / Budget / Régie / Social / Contacts / Documents (ticket C1) | `gigs`, `documents`, `roadmaps` |
| **Social** | `/social/` | L'équipe **date par date** : cachets et heures saisis, frais déclarés à valider, Navette sociale (offre Collectif) | `gigs` (GigMember), `finance` (Expense) |
| **Contacts** | `/contacts/` | Annuaire unique, filtres **Organisateurs / Lieux / Personnes**, code couleur existant | `addressbook` |

En pied de menu, séparés des 5 entrées : **Ma structure**, puis le nom de la structure (compte, abonnement, déconnexion).

**Distinction Social / Équipe** (pour éviter les doublons) :

- **Ma structure › Équipe** = *qui* sont les personnes (fiche, statut artiste/technicien, adresse, n° GUSO à transmettre aux organisateurs).
- **Social** = *ce qu'il y a à faire* pour elles sur les dates (cachets, heures, frais, déclarations).

### Précisions du 19/11 (relecture de l'arborescence)

Arborescence visuelle à jour : [Whiteboard « Bòrd Pro — Arborescence de l'app »](https://claude.ai/artifact/HA8jMSUQPKmoRffbNFEye8). Ce document reste la référence pour le code.

1. **Équipe : une seule donnée, trois vues.** Menu Social = toutes les dates ; onglet Social de la fiche date = la même donnée filtrée sur cette date ; Ma structure › Équipe = les fiches des personnes. **Pas trois modèles ni trois logiques** : mêmes vues filtrées, mêmes services (`services.py`).
2. **Frais : un seul objet `Expense`, deux étapes.** Social affiche les frais déclarés par l'équipe **à valider** ; une fois validés, ils apparaissent dans Bord › **Toutes les dépenses**, avec les dépenses saisies directement. Un frais n'est jamais saisi deux fois.
3. **Tournées ajoutées dans Dates** : une tournée = une période de dates (décision D3), affichée comme regroupement ou filtre dans Dates, avant la fiche date. **À vérifier par le développeur** : ce qui existe déjà dans `gigs`.
4. **Pages publiques à faire figurer dans l'arborescence**, hors menu, ouvertes par lien secret : feuille de route, formulaire organisateur (7 jours, usage unique), Bòrd Artiste (équipe, sur téléphone). Elles restent lisibles à 375 px (CLAUDE.md §8) et leurs adresses **ne changent pas** avec la refonte.
5. **Spectacles dans Ma structure : à tester en recette.** Adapté à un artiste avec peu de spectacles ; une compagnie ou un tourneur qui envoie souvent une fiche technique risque d'y aller chaque semaine. Si c'est le cas, Spectacles remonte dans le menu. La recherche « / » compense en attendant.

## 3. « Ma structure » (un seul sous-menu de paramétrage)

**URL racine :** `/structure/`. Navigation interne par **onglets verticaux** à gauche du contenu, une URL par onglet. Libellé d'interface : **« Ma structure »** (lexique CLAUDE.md §5 ; ne jamais écrire « Structure » seul).

Droits (NAV-D4) : **propriétaire** (`owner`) = tout ; **membre** (`member`) = Équipe en lecture, Spectacles en lecture et modification.

| Onglet | URL | Contenu | Existe déjà ? | Accès |
|---|---|---|---|---|
| 3.1 **Fiche structure** | `/structure/` | Identité, forme juridique, SIRET, régime de TVA, représentant, adresse, IBAN/BIC, logo, téléphone, e-mail | Oui (enrichie au ticket A4) | Propriétaire |
| 3.2 **Équipe** | `/structure/equipe/` | Membres, artiste ou technicien, n° GUSO (information à transmettre aux organisateurs, visible du seul propriétaire, NAV-D8), **cachet de référence** saisi sur la fiche de chaque artiste, visible du seul propriétaire (NAV-D1), invitation des utilisateurs | Oui | Propriétaire ; lecture pour les membres |
| 3.3 **Spectacles** | `/structure/spectacles/` | Catalogue : titre, durée, balances, nombre d'artistes et de techniciens, fiche technique, n° d'objet, code analytique | Oui (`catalog`) — **sort du menu principal** | Tous |
| 3.4 **Paratge** | `/structure/paratge/` | Outil de configuration du **modèle économique** de la structure : « Mon modèle », réglages repères, financements (spécification `spec-paratge-agent.md`). À garder absolument (NAV-D6) | **Non** — module Paratge, construit après le MVP (D12) | Propriétaire · offre Collectif (visible avec explication, NAV-D5) |
| 3.5 **Documents** | `/structure/documents/` | Réglages des devis, factures, avoirs, contrats : modèle de contrat par défaut (4 au choix), délais, mentions, numérotation (affichage seul), conditions générales | En partie dans `Tenant` | Propriétaire |
| 3.6 **Compte et offre** | `/structure/compte/` | Offre Stripe, export et suppression du compte | Oui | Propriétaire |

**Liens secrets** (la page Partage est supprimée, NAV-D7) : chaque lien se crée et se révoque **là où il sert** — feuille de route dans fiche date › Régie ; espace équipe / Bòrd Artiste dans Ma structure › Équipe ; abonnement agenda dans Bòrd Artiste. Rôles des utilisateurs : Ma structure › Équipe.

**Règles :**

- Aucun onglet de « Ma structure » ne contient de travail quotidien. Si un écran sert chaque semaine, il va dans le menu de gauche.
- Les documents **émis** ne sont **pas** ici : ils sont dans la fiche date et dans le Bord (NAV-D3). Ici, on règle seulement **comment** ils sont produits.
- Un indicateur de complétude (« Fiche structure : 2 champs manquants pour émettre une facture ») s'affiche sur l'onglet concerné, écrit en toutes lettres, jamais signalé par la couleur seule (charte).

### Cachet de référence, sur la fiche de chaque artiste (NAV-D1, modifiée le 19/11)

- On **enregistre des montants saisis**, rien d'autre. **Aucun calcul** de charges, de net ni de paie (hors périmètre, CLAUDE.md §10).
- Montants en `DecimalField`, au centime (CLAUDE.md §6.2), libellés « brut ».
- Un cachet de référence **par artiste**, saisi un à un sur sa fiche (Ma structure › Équipe). Pas de barème par rôle, pas de page dédiée.
- Sur une date, le montant repris est une **copie** : modifier la référence ensuite ne change pas les dates déjà saisies.
- On **réutilise `Person.average_fee`** (« cachet moyen (€) », `DecimalField`, déjà sur le modèle des membres de l'équipe) : libellé changé en « cachet de référence (brut) », **aucune migration**, pas de nouveau modèle. **Visible et modifiable par le seul propriétaire** (validé le 19/11) : test d'accès à ajouter (un `member` ne le voit pas).
- **À vérifier par le développeur :** ce qui existe déjà dans la gestion sociale de l'équipe (brut par date et par membre ?), pour réutiliser plutôt que dupliquer.

## 4. Règles pour réduire les clics

| N° | Règle | Mise en œuvre (stack existante) |
|---|---|---|
| **R1** | Tâche fréquente : **≤ 2 clics depuis l'Accueil, ≤ 3 depuis n'importe où** | Critère de recette pour chaque écran (§5) |
| **R2** | Bouton **« + Créer »** toujours visible en haut : Nouvelle date, Nouveau contact, Déclarer une dépense, Nouveau devis | Menu Alpine.js ; chaque choix ouvre une **modale HTMX**, sans changer de page |
| **R3** | **Recherche globale** (raccourci `/`) : dates, contacts, spectacles, documents | Champ HTMX `hx-trigger="keyup changed delay:300ms"`, vue filtrée par tenant (`TenantScopedMixin`) |
| **R4** | **Chaque tâche ou alerte mène à l'action exacte** | Lien profond `/dates/<id>/?onglet=contrat#champ-echeance` ; **retour automatique** après enregistrement (paramètre `next`, contrôlé par `url_has_allowed_host_and_scheme`) |
| **R5** | **Paramétrage « juste à temps »** : info manquante de Ma structure demandée dans une modale, enregistrée dans Ma structure, puis l'action reprend | Fragment HTMX du formulaire réduit aux seuls champs manquants. Jamais « Allez dans les paramètres » |
| **R6** | **Actions sur la ligne** : statut, encaissé, valider un frais, sans ouvrir la fiche | Boutons HTMX qui renvoient la ligne mise à jour (`_row.html`) |
| **R7** | **Le menu ne change jamais**, ni selon la page ni selon l'offre ; l'entrée active est soulignée et en gras | `base.html` + variable de contexte `active_menu` |
| **R8** | **Fil d'Ariane** sur toute page de niveau 2 ou plus | Ticket A6 |

**Fonctions d'une offre supérieure (NAV-D5) :** elles restent **visibles**. À la place du contenu, une phrase explique ce que fait la fonction, avec un lien vers l'offre. On ne cache jamais une entrée du menu ni un onglet.

## 5. Tâches fréquentes : chemin cible et nombre de clics

Critères de recette. Le nombre de clics actuel est **à relever par le développeur** avant la refonte, pour comparer.

| Tâche | Chemin cible | Clics max |
|---|---|---|
| Créer une date | « + Créer » › Nouvelle date | 2 |
| Envoyer le contrat d'une date | Accueil › « Contrat à envoyer » › Envoyer | 2 |
| Émettre une facture | Fiche date › onglet Documents › Émettre | 3 |
| Marquer un paiement reçu | Accueil › « Paiement attendu » › Marquer encaissé | 2 |
| Valider un frais déclaré par l'équipe | Social › ligne du frais › Valider | 2 |
| Saisir les cachets d'une date | Fiche date › onglet Social › saisie sur la ligne (pré-remplie depuis la fiche de l'artiste) | 3 |
| Partager la feuille de route | Fiche date › onglet Régie › Partager | 3 |
| Appeler l'organisateur d'une date | Fiche date › onglet Contacts › numéro cliquable | 2 |
| Retrouver une facture émise | Bord › Documents émis › ligne | 2 |
| Trouver n'importe quoi | `/` › taper › résultat | 2 |
| Modifier l'IBAN | Ma structure › Fiche structure | 2 |
| Ajouter un membre de l'équipe | Ma structure › Équipe › Ajouter | 3 (rare) |
| Révoquer un lien secret | Là où le lien est créé (ex. fiche date › Régie) › Révoquer | 3 (rare) |

## 6. Plan d'URL et impact sur le code

```
/                          Accueil
/bord/                     Bord (+ /bord/documents/, /bord/depenses/)
/dates/                    Calendrier, liste, tournées
/dates/<id>/               Fiche date (?onglet=contrat|budget|regie|social|contacts|documents)
/social/                   Social
/contacts/                 Annuaire (?type=organisateurs|lieux|personnes)
/structure/                Ma structure › Fiche
/structure/equipe/         (fiche de chaque membre, avec son cachet de référence)
/structure/spectacles/
/structure/paratge/
/structure/documents/
/structure/compte/
/recherche/                Recherche globale (fragment HTMX)
```

- **Pas de nouvelle app** : les vues de `/structure/` restent dans leurs apps (`tenants`, `accounts`, `catalog`, `documents`) ; seul `config/urls.py` les regroupe. Le modèle des cachets de référence va dans l'app qui porte déjà l'équipe (**à confirmer par le développeur**).
- **Redirections 301** des anciennes URL (ex. `/spectacles/` → `/structure/spectacles/`). Les liens secrets publics (feuille de route, formulaire organisateur) **ne changent pas**.
- **Isolation des tenants** : recherche globale et Paratge → `TenantScopedMixin` + **test d'isolation** (CLAUDE.md §6.1).
- **Droits** (NAV-D4) : Fiche structure, Paratge, Documents, Compte et le cachet de référence (fiche Équipe) réservés à `owner` (test : un `member` reçoit 403) ; Équipe en lecture seule pour un `member`.

**Taille indicative** (à corriger par le développeur) : M pour le menu, « Ma structure » et les redirections ; S pour la recherche ; S pour « + Créer » ; XS pour le cachet de référence (libellé et droits seulement) ; S pour les confirmations d'actions.

**Découpage retenu (23/11/2026)** : PR 0 confirmations des actions (finance, gigs, billing, roadmaps, catalog, espace équipe ; cas HTMX) · PR 1 menu à 5 entrées, `active_menu`, nouvelles URL et redirections 301 · PR 2 Ma structure et droits NAV-D4 · PR 3 cachet de référence et liens secrets là où ils servent · PR 4 fil d'Ariane et relevé des clics (§5). Hors de ce chantier : « + Créer », recherche `/`, liens profonds, « À faire », fiche date en onglets (C1), tournées, refonte de Social. `/radar/` reste accessible hors menu ; Social est déplacé tel quel.

**Place dans l'ordre de travail** (doc 07) : avec A6 (fil d'Ariane) et avant C1 (fiche date en onglets) — **À trancher** par Jeff.

## 7. Décisions prises (19/11/2026)

| N° | Décision |
|---|---|
| **NAV-D1** | Cachet brut de référence **saisi un à un sur la fiche de chaque artiste** (Ma structure › Équipe), repris par défaut sur les dates (modifié le 19/11 : ni page Salaires, ni barème par rôle). Saisie seule, aucun calcul de paie. |
| **NAV-D2** | Les « invitations à agir » = les tâches et alertes Radar de la liste « À faire » de l'Accueil. |
| **NAV-D3** | Les documents émis sont listés dans le Bord et dans la fiche date. Pas d'entrée de menu séparée. |
| **NAV-D4** | Ma structure : propriétaire = tout ; membre = Équipe en lecture, Spectacles en lecture et modification. |
| **NAV-D5** | Les fonctions d'une offre supérieure restent visibles, avec une explication et un lien vers l'offre. |
| NAV-D6 | Paratge, outil de configuration du modèle économique de la structure, a sa place dans Ma structure. À garder absolument. |
| NAV-D7 | Pas de page Partage : chaque lien secret se crée et se révoque là où il sert. |
| NAV-D8 | GUSO : l'app s'adresse à des professionnels, donc plus de GUSO dans Social ni dans aucune question de paie ou de déclaration. Le champ « n° GUSO » reste sur la fiche de chaque artiste (Ma structure › Équipe), visible du seul propriétaire, comme simple information à transmettre à un organisateur qui en aurait besoin. Pas de migration. |

## 8. Comparaison avec la concurrence

| | Orféo | Bob Booking | Bòrd Pro |
|---|---|---|---|
| Logique du menu | Par **modules** : planning, production, administration ; modules pour orchestres, opéras, lieux | Par **modules** : contacts, tournées, tâches, budget | Par **usage quotidien** : 5 entrées fixes + un seul espace de paramétrage |
| Tâches / à faire | Non relevé | Oui : tâches créées et attribuées (appli mobile) | Liste « À faire » sur l'Accueil, alimentée par les dates et Radar |

**Faits sourcés :** Orféo s'articule en trois grands modules (plannings, budgets de production, tâches administratives) avec des modules avancés pour orchestres, opéras et lieux ([logiciels.pro](https://www.logiciels.pro/orfeo/), [appvizer](https://www.appvizer.fr/marketing/evenementiel/orfeo)). Bob Booking se décrit comme modulaire ; son appli mobile couvre contacts, agenda des dates et tâches attribuables ([GetApp](https://www.getapp.fr/software/2056006/bob-booking), [App Store](https://apps.apple.com/br/app/bob-booking/id1209436338)).

**Déduction (non vérifiée) :** un menu par modules convient aux structures à plusieurs métiers, mais multiplie les entrées pour un artiste seul. À tester en recette avec 2 ou 3 utilisateurs.

## 9. Réglementation à garder en tête

- **Facture électronique** : émission obligatoire pour les PME et micro-entreprises au **01/09/2027**. L'onglet **Ma structure › Documents** accueillera les réglages liés (catégorie d'opération, choix de plateforme agréée).
- **Cachet de référence (fiche Équipe)** : uniquement des montants bruts saisis. Tout calcul (charges, net, paie) reste hors périmètre tant qu'il n'est pas confirmé dans le cahier des charges.
