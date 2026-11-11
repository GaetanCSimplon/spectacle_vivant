# Bòrd Pro — Retours d'expérience utilisateur (recette n°1)

2026-11-05

## Mode d'emploi

Ce document regroupe les retours de la première session de test de Bòrd Pro (app.bordpro.fr), classés par module. Il sera complété à chaque nouvelle session de test.

- **Identifiant** : chaque retour a un code (ex. DAT-03) à reprendre dans les issues GitHub et les messages de commit.
- **Type** : Bug = comportement incorrect · UX = ergonomie, libellé, organisation d'écran · Feature = nouvelle fonctionnalité.
- **Priorité** : P1 = bloquant, ou risque légal ou financier · P2 = gain d'usage important · P3 = confort. Les priorités sont une proposition, à valider.
- **Annexes** : listes de valeurs, modèles d'e-mails, API publiques et points réglementaires, prêts à intégrer.
- Les chemins d'URL (ex. /dates/2/contrat/completer/) sont ceux observés pendant le test ; l'identifiant numérique varie.

## Synthèse : les P1 à traiter en premier

Onze retours ont été classés P1, dont FDR-01 qui passe après le MVP (voir Cadrage) : deux bugs sur les chiffres du Bord, cinq points qui touchent aux mentions légales et financières des documents, et quatre manques fonctionnels qui bloquent un usage réel.

| ID | Type | Module | Résumé |
|---|---|---|---|
| BRD-02 | Bug | Bord | Un acompte facturé en 2026 pour une date 2027 disparaît de la vue 2027 |
| BRD-03 | Bug | Bord | Le solde d'une date n'apparaît pas sans filtre |
| BRD-04 | Feature | Bord | Séparer « Produits d'activité » et « Trésorerie » |
| CTR-02 | Feature | Devis / factures | Mention TVA paramétrable selon le régime fiscal de la structure - A afficher dans tout document (contrat, facture, devis). |
| CTR-05 | UX | Contrat | Échéances d'acompte et de solde en listes prédéfinies |
| CTR-10 | Feature | Factures | Reprendre n° de devis, date de validation, total signé, acompte et solde restant |
| ORG-01 | Feature | Organisateurs | Remplissage automatique des données légales via le SIRET |
| DAT-01 | Feature | Dates | Champ « Nom de l'événement » |
| FDR-01 | Feature | Radar | Contrôle de cohérence des horaires de la feuille de route - Création d'un creneau avec date + heure (possibilité de "programmer" un événement à une date autre que la date de spectacle) |
| FDR-02 | Feature | Feuille de route | Feuille de route sur plusieurs jours (aller, prestation, retour) |
| STR-09 | Feature | Structure | Champ « Régime TVA » qui pilote la mention légale (lié à CTR-02) |

À surveiller hors de ce test : la facturation électronique obligatoire et la nouvelle nomenclature NAF au 1er janvier 2027 (voir Annexe C).

## Cadrage avec le dépôt (CLAUDE.md)

Relus contre CLAUDE.md et docs/README.md du dépôt : un retour est hors MVP (Radar), cinq portent sur des fonctions déjà livrées à étendre, et quatre demandent une vigilance sur les règles du projet. Règle de base du dépôt : une fonction absente de docs/produit/cahier-des-charges.md n'est pas à coder. Chaque retour doit donc d'abord être validé contre ce cahier des charges, que je n'ai pas pu lire.

### Ce qui existe déjà (à étendre, pas à recréer)

| Retour | Existant selon CLAUDE.md | Ce qui change |
|---|---|---|
| STR-08 | Quatre modèles de contrat de cession au choix (pas trois), tant que le contrat est en brouillon | Ajouter seulement un choix de modèle par défaut dans « Ma structure », proposé à la fin de l'onboarding |
| ORG-04, ORG-05 | Formulaire de complétion organisateur : lien secret de 7 jours, à usage unique, réponses vérifiées avant application | Ajouter des contacts et les champs du contrat au formulaire existant. Option la plus simple : des étapes supplémentaires dans le même formulaire, plutôt qu'un second lien |
| SPE-01 | Gestion de l'équipe et annuaire de contacts à rattachements multiples | La distribution d'un spectacle s'appuie sur les membres d'équipe existants, pas sur une nouvelle liste |
| SPE-02 | Champ « n° SACEM/objet » déjà présent sur Show | Le besoin porte sur l'affichage et le contrôle du format, pas sur un nouveau champ |
| CTR-08 | Versions du contrat, marquage « signé », PDF figé | Refonte de l'écran des versions + envoi par e-mail ; le fonctionnement des versions ne change pas |

### Conflits ou règles à respecter

| Retour | Règle du dépôt | Conséquence |
|---|---|---|
| FDR-01 | Le Radar est prévu après le MVP (docs/produit/specification-radar.md) | À noter dans la spécification Radar, pas à coder maintenant. Passe de P1 à « après MVP » |
| CTR-02 | Q8 tranchée le 01/10 : la mention 293 B n'est pas conservée dans le contrat | CTR-02 vise uniquement devis et factures, pas le contrat de cession. Pas de contradiction, mais à préciser |
| BRD-04 | Pas de jargon comptable dans l'interface ; F-57 impose déjà trois montants distincts (prévu, facturé, encaissé) | Libellés d'interface à revoir (voir « Bord »). BRD-02 et BRD-03 sont peut-être des écarts à F-57 déjà spécifié |
| CTR-06, SPE-03 | Charte : les couleurs d'état ne décorent jamais, le corail est réservé à l'action principale | Les couleurs de blocs et de spectacles doivent venir d'une palette validée par la charte, contraste testé |
| CTR-10 | Une facture émise est immuable, ses infos sont copiées à l'émission | N° de devis, total signé, acompte et solde sont copiés dans la facture au moment de l'émission, jamais recalculés ensuite |

### Autres points pour le développeur

- **Vocabulaire** : dans ce document, « structure » désigne toujours la structure de l'utilisateur, soit Tenant (« Ma structure »). L'organisateur est Promoter, le lieu Venue. Le nom du produit s'écrit Bòrd Pro.
- **API SIRET et communes** (ORG-01, ORG-02) : appel côté serveur dans un service (apps/addressbook/services.py), réponse renvoyée en fragment HTMX. Aucune bibliothèque JS, aucune API REST à créer : compatible avec la stack imposée.
- **Plan avant code** : CLAUDE.md exige un plan validé avant tout travail sur modèles, migrations, multi-tenant ou PDF. La colonne « Plan » du tableau suivant signale ces retours.
- **Spécifications de l'associé à relire avant de coder** : specification-onglet-bord.md et indicateurs-bord.md (BRD-xx), specification-checklist-contractualisation.md (DAT-04, DAT-07), specification-feuille-de-route-type.md (FDR-02, FDR-03 : seuls F-86 à F-93 sont retenus). Je n'ai pas accès à ces fichiers : ils peuvent déjà couvrir certains retours.

## Correspondance tickets ↔ code

App et modèles déduits de la structure du dépôt décrite dans CLAUDE.md, sans avoir lu le code : à confirmer par le développeur. « Plan : oui » = touche aux modèles, migrations ou PDF, donc plan à valider avant de coder.

| ID | App | Modèle(s) ou zone | Plan |
|---|---|---|---|
| NAV-01 | templates | base.html (menu) | non |
| NAV-02 | templates, tenants | base.html, lien vers « Ma structure » | non |
| NAV-03 | templates | templates/components/ (fil d'Ariane) | non |
| NAV-04 | gigs | Accueil, filtre d'année | non |
| STR-01 | tenants | Tenant (forme juridique en TextChoices) | oui |
| STR-02 | accounts, tenants | Parcours d'onboarding | non |
| STR-03 | tenants | Affichage et validation du SIRET | non |
| STR-04 | tenants | Tenant (code APE + version de nomenclature) | oui |
| STR-05 | tenants | Tenant (représentant : nom et prénom séparés) | oui |
| STR-06 | tenants | Tenant (qualité du représentant) | oui |
| STR-07 | tenants, documents | Tenant (logo, stockage privé) + gabarits PDF | oui |
| STR-08 | tenants, documents | Tenant (modèle de contrat par défaut) | oui |
| STR-09 | tenants | Tenant (régime TVA) | oui |
| ORG-01 | addressbook | Promoter + services.py (appel API) | oui |
| ORG-02 | addressbook | Promoter, Venue (code postal → commune) | non |
| ORG-03 | addressbook | Promoter (période habituelle en plages de dates) | oui |
| ORG-04 | addressbook | Contact + formulaire de complétion | oui |
| ORG-05 | addressbook, documents | Formulaire de complétion + Contract | oui |
| ORG-06 | addressbook | Bouton d'envoi (mailto) | non |
| DAT-01 | gigs | Gig (nom de l'événement) | oui |
| DAT-02 | gigs | Pastilles du calendrier et de la liste | non |
| DAT-03 | gigs | Modale après enregistrement (Alpine.js) | non |
| DAT-04 | gigs, documents | Dates des étapes (historique) | oui |
| DAT-05 | gigs, documents | Bloc « Documents » de la fiche date | non |
| DAT-06 | gigs, finance | Mini-vue chiffrée de la liste des dates | non |
| DAT-07 | gigs, documents | Liste « À faire » + rappels | oui |
| SPE-01 | catalog, accounts | Show + équipe (distribution) | oui |
| SPE-02 | catalog | Show (format du n° d'objet) | non |
| SPE-03 | catalog | Show (couleur) | oui |
| CTR-01 | documents | Gabarits PDF (WeasyPrint) | oui |
| CTR-02 | documents, tenants | Quote, Invoice (mention TVA copiée à l'émission) | oui |
| CTR-03 | documents | Paramétrage des gabarits | oui |
| CTR-04 | documents | Redirection après validation du devis | non |
| CTR-05 | documents | Contract (échéances d'acompte et de solde) | oui |
| CTR-06 | documents | Page « compléter le contrat » | non |
| CTR-07 | documents, roadmaps | Contract, Meal, Lodging (pris en charge par) | oui |
| CTR-08 | documents | Écran des versions du contrat | non |
| CTR-09 | — | Fusionné avec DAT-07 | — |
| CTR-10 | documents | Invoice (copie devis, total, acompte, solde) | oui |
| BRD-01 | finance | Libellé du bilan | non |
| BRD-02 | finance | Requête du filtre d'année | non |
| BRD-03 | finance | Calcul du solde | non |
| BRD-04 | finance | Payment, vues du bilan | oui |
| FDR-01 | roadmaps | Radar | après MVP |
| FDR-02 | roadmaps | RoadmapSlot (date propre à chaque créneau) | oui |
| FDR-03 | roadmaps | RoadmapSlot (pièces jointes, stockage privé) | oui |
| FDR-04 | roadmaps | Affichage de Meal et Lodging dans le programme | non |
| ORG-07 | addressbook, accounts | Formulaire de complétion étendu à Contact et à l'équipe (lien secret, vérification avant application) | oui |
| DAT-08 | gigs, addressbook | Onglet Contacts de la fiche date (Contacts du Promoter et du Venue) | non |

Tous les retours qui ajoutent un modèle ou une vue doivent inclure le test d'isolation des tenants exigé par CLAUDE.md (§ 6.1). Pour DAT-07 : Celery et Redis sont interdits. La liste « À faire » se calcule donc à l'affichage ; un e-mail de rappel automatique demanderait une tâche planifiée, à discuter.

## Découpage proposé en petites PR

CLAUDE.md impose une tâche par branche et par petite PR. Je propose de commencer par les bugs du Bord : ce sont des corrections sans migration. Un lot = un sujet, donc une branche feature/&lt;sujet&gt; et une ou plusieurs PR.

1. **Bugs du Bord** : BRD-02, BRD-03, puis BRD-01. Commencer par écrire le test du cas décrit dans la section Bord, qui doit échouer, puis corriger. Pas de plan requis.
2. **Navigation et libellés** : NAV-01 à NAV-04, DAT-02, CTR-04. Templates uniquement.
3. **Fiche « Ma structure »** : STR-01, STR-03, STR-05, STR-06, STR-09. Une seule migration sur Tenant, plan à valider.
4. **Mentions légales des factures** : CTR-02, CTR-10. Plan à valider (PDF, copie à l'émission). À faire relire par un expert-comptable, comme prévu dans « État actuel ».
5. **Remplissage automatique** : ORG-01, ORG-02, puis STR-04 (APE).
6. **Page « compléter le contrat »** : CTR-05, CTR-06, CTR-07, FDR-04.
7. **Fiche date** : DAT-01, DAT-03, DAT-04, DAT-05.
8. **Formulaire organisateur et e-mails** : ORG-04, ORG-05, ORG-06, CTR-08 (modèles de l'Annexe B).
9. **Feuille de route sur plusieurs jours** : FDR-02, FDR-03, après vérification contre F-86 à F-93.
10. **Logo et modèles de documents** : STR-07, CTR-01, CTR-03, STR-08.
11. **Reste, selon le cahier des charges** : DAT-06, DAT-07, SPE-01 à SPE-03, ORG-03, BRD-04. FDR-01 rejoint la spécification Radar.

## 1. Navigation et interface globale

Quatre améliorations transverses, valables sur toutes les pages.

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| NAV-01 | UX | P3 | Le menu principal n'a que du texte. | Ajouter une icône devant chaque entrée du menu (Accueil, Dates, Spectacles, Organisateurs, Bord…). |
| NAV-02 | UX | P2 | La page Informations de la structure (/bord/informations/) n'est accessible qu'à un endroit. | Icône permanente dans l'en-tête de toutes les pages, qui ouvre cette page. |
| NAV-03 | UX | P2 | Dans certains parcours, aucun moyen de revenir en arrière (ex. après validation d'un devis, pas de retour direct à la date). | Barre de navigation ou fil d'Ariane en haut de page : Dates › [Date] › Devis. |
| NAV-04 | Feature | P2 | La page d'accueil ne montre que l'année en cours ou passée. | Filtre d'année incluant les années à venir (N+1, N+2), et une option « Toutes ». |

## 2. Onboarding et fiche structure

Objectif : qu'une structure ait toutes ses informations légales complètes dès la fin de l'inscription, avec un minimum de saisie libre.

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| STR-01 | UX | P2 | Forme juridique en saisie libre (première page). | Liste déroulante préconfigurée (Annexe A1). |
| STR-02 | UX | P2 | Après la création de la fiche entreprise, l'utilisateur ne sait pas où compléter les infos légales. | En fin de création, ouvrir directement la fiche structure (ou proposer un bouton « Compléter mes informations légales »). |
| STR-03 | UX | P2 | SIRET affiché sans espaces, difficile à relire. | Affichage au format 111 222 333 00012 (3-3-3-5). Stockage sans espaces. Contrôle de validité (clé de Luhn) à la saisie. |
| STR-04 | UX | P2 | Code APE en saisie libre. | Liste prédéfinie des codes du spectacle et de l'animation (Annexe A2), saisie libre en dernier recours. Prévoir le passage à la NAF 2025 (Annexe C). |
| STR-05 | UX | P2 | Représentant légal : un seul champ. | Deux champs : Nom et Prénom. |
| STR-06 | UX | P2 | Qualité du représentant en saisie libre. | Liste déroulante (Annexe A3) + « Autre » avec champ libre. |
| STR-07 | Feature | P2 | Pas de logo de structure. | Upload du logo dans les paramètres de la structure, repris sur devis, contrats et factures. |
| STR-08 | Feature | P2 | Le modèle de contrat de cession n'est pas choisi à l'inscription. | Dernière étape de l'onboarding : aperçu des 4 modèles de contrat de cession déjà livrés, choix d'un modèle par défaut (modifiable ensuite). |
| STR-09 | Feature | P1 | Le régime de TVA n'est pas demandé. | Champ « Régime TVA » dans la fiche structure, qui pilote la mention légale des devis et factures (voir CTR-02). |

## 3. Organisateurs

Le gain principal : récupérer automatiquement les données légales connues de l'État à partir du SIRET, gratuitement (Annexe C).

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| ORG-01 | Feature | P1 | Dans /dates/nouvelle/ › Organisateur et dans la fiche organisateur, tout est saisi à la main. | Saisie du SIRET (ou recherche par nom) → remplissage automatique : raison sociale, adresse, code postal, ville, code APE, forme juridique, n° TVA intracommunautaire calculé. Les champs restent modifiables. |
| ORG-02 | Feature | P2 | La ville est saisie à la main. | Après saisie du code postal, proposer la liste des communes correspondantes. |
| ORG-03 | UX | P3 | /organisateurs/{id}/modifier/ : « Période habituelle » en texte libre. | Pouvoir saisir une ou plusieurs plages de dates (ex. du 10/07 au 25/07), récurrentes chaque année. |
| ORG-04 | Feature | P2 | Le formulaire envoyé à l'organisateur n'accepte qu'un contact. | Permettre d'ajouter plusieurs contacts, chacun avec un rôle : direction, programmation, administration, comptabilité, régie technique, accueil. |
| ORG-05 | Feature | P2 | Un seul formulaire (infos légales). | À la validation du formulaire 1, enchaîner sur un formulaire 2 qui collecte les infos de /dates/{id}/contrat/completer/ (horaires, repas, hébergement, jauge, contacts techniques…). |
| ORG-06 | Feature | P2 | L'envoi du formulaire ne passe pas par la messagerie de l'utilisateur. | Bouton « Envoyer par e-mail » en mailto: qui ouvre le logiciel de messagerie de l'ordinateur avec destinataire, objet et message type pré-remplis, lien inclus (Annexe B1). Prévoir aussi un bouton « Copier le lien ». |
| ORG-07 | Feature | P2 | Ajout du 10/11. À chaque nouvelle fiche (organisateur, contact, membre d'équipe), il faut tout saisir soi-même. | À la création d'une fiche Organisateur, Contact ou Équipe, proposer « Envoyer un formulaire en ligne » : la personne remplit ses propres informations, l'utilisateur les vérifie avant de les appliquer. Étendre le formulaire de complétion organisateur et l'espace personnel équipe déjà existants (lien secret), sans nouveau mécanisme. Modèles de mail : Annexe B. |

## 4. Dates

La fiche date doit devenir le point central : on y voit où en est la date, ses documents et ses chiffres.

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| DAT-01 | Feature | P1 | Pas de champ pour le nom de l'événement (festival, saison…). | Champ « Nom de l'événement » dans /dates/nouvelle/, facultatif. |
| DAT-02 | UX | P2 | Le titre des pastilles de /dates/ n'indique pas l'événement. | Titre de la pastille = Nom de l'événement ; à défaut, nom de l'organisateur ou ville. |
| DAT-03 | Feature | P2 | Après l'enregistrement d'une date, rien n'invite à collecter les infos de l'organisateur. | Pop-up en fin d'enregistrement : « Envoyer le formulaire à l'organisateur ? » avec boutons Envoyer (voir ORG-06) et Plus tard. |
| DAT-04 | Feature | P2 | On ne voit pas où en est la date. | Dans /dates/{id}/, frise des étapes datées : formulaire envoyé / reçu, devis envoyé / validé le, contrat généré le, marqué signé le, facture d'acompte émise / payée, facture de solde émise / payée. |
| DAT-05 | Feature | P2 | Les documents liés à une date sont dispersés. | Bloc « Documents » dans /dates/{id}/ : devis, versions du contrat, factures, feuille de route, pièces jointes. |
| DAT-06 | Feature | P3 | /dates/ ne montre aucun chiffre. | Mini-vue du Bord en tête de /dates/ : total prévisionnel, signé, facturé, encaissé pour la sélection affichée. |
| DAT-07 | Feature | P2 | Aucun rappel sur les contrats de cession à revoir ou non signés. | Alerte ou rappel automatique (ex. contrat envoyé et non signé après 7 jours, délai paramétrable) + liste « À faire » sur l'accueil. |
| DAT-08 | Feature | P2 | Ajout du 10/11. Dans la page d'une date, les contacts de l'organisateur ne sont pas visibles. | Onglet « Contacts » dans /dates/{id}/ qui reprend les contacts rattachés à l'organisateur (et au lieu) de la date : nom, rôle, téléphone, e-mail cliquables. Lecture seule, avec un lien vers la fiche contact pour modifier. |

## 5. Spectacles

Trois ajouts dans la fiche spectacle (/spectacles/{id}/modifier/).

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| SPE-01 | Feature | P2 | Distribution : impossible d'ajouter une personne. | Bouton « Ajouter une personne » : nom, prénom, rôle (artiste / technicien·ne / autre), fonction, contact. Idéalement lié au fichier contacts pour la réutiliser. |
| SPE-02 | Feature | P2 | Pas de champ « Numéro d'objet ». | Champ texte avec masque basé sur l'exemple fourni : 223P51344757 (3 chiffres, 1 lettre, 8 chiffres). Format exact à confirmer avant d'imposer un contrôle strict. |
| SPE-03 | Feature | P3 | Les spectacles ne se distinguent pas visuellement. | Couleur assignable à chaque spectacle, reprise dans toutes les vues de dates (pastilles, calendrier, listes). |

## 6. Devis, contrats de cession, factures

La gestion des contrats de cession est le chantier le plus attendu : paramétrage des modèles, page de saisie lisible, envoi direct, et cohérence devis → contrat → factures.

### Devis et paramétrage des documents

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| CTR-01 | Feature | P2 | Pas de logo sur les devis. | Logo de la structure (STR-07) en en-tête des devis, contrats et factures. |
| CTR-02 | Feature | P1 | « TVA non applicable » en bas du devis, sans article de loi. | Mention générée selon le régime TVA choisi dans la structure (STR-09). Ex. franchise : « TVA non applicable, article 293 B du CGI ». Liste des cas en Annexe C, à valider par un expert-comptable. |
| CTR-03 | Feature | P2 | Modèles non configurables. | Paramétrage séparé des modèles : contrat de cession, devis, facture (mentions, conditions de paiement, pied de page, numérotation). |
| CTR-04 | UX | P2 | Après validation d'un devis, pas de retour direct à la date. | Barre de navigation en haut (voir NAV-03) + redirection vers la fiche date après validation. |

### Page /dates/{id}/contrat/completer/

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| CTR-05 | UX | P1 | « Acompte à régler le » et « Solde à régler le » attendent une date libre. | Listes d'échéances prédéfinies (Annexe A4), avec « Date précise » en dernier choix. La date réelle est calculée et affichée. |
| CTR-06 | UX | P2 | Contrat, budget et feuille de route sont mélangés sur la page. | Réorganiser en 3 blocs distincts, chacun avec sa couleur : Contrat, Budget, Feuille de route. Même code couleur dans toute l'app. |
| CTR-07 | UX | P2 | « Repas pris en charge » et « Hébergement pris en charge » : on ne sait pas quoi répondre (par qui ? oui/non ?). | Pour chaque poste : « Pris en charge par » = Organisateur / Producteur / Partagé / Non concerné (Annexe A5), + nombre de personnes, de repas ou de nuits, + précisions. |

### Versions et envoi du contrat

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| CTR-08 | UX | P2 | /dates/{id}/contrat/versions/ : mise en page peu lisible, pas d'envoi direct. | Pop-up d'aperçu du PDF avec bouton « Envoyer » : mailto pré-rempli avec l'e-mail de l'organisateur, objet et message type (Annexe B2). |
| CTR-09 | Feature | P2 | Pas de suivi des contrats à relire. | Voir DAT-07 (rappel automatique). |

### Factures

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| CTR-10 | Feature | P1 | La facture ne reprend pas l'historique commercial. | Afficher sur la facture : n° de devis et « validé le [date] », total signé au contrat, montant de l'acompte (facturé ou déjà réglé), solde restant dû. |

## 7. Bord (tableau de bord financier)

Les deux bugs viennent d'une même cause probable : le Bord mélange le chiffre d'affaires d'une date et l'argent encaissé. Il faut deux lectures séparées.

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| BRD-01 | UX | P3 | Sous « Ce que les concerts doivent rapporter », le premier libellé est « Prévu HT ». | Renommer en « Prévisionnel ». |
| BRD-02 | Bug | P1 | Date en 2027, acompte facturé en 2026 : en vue 2027, l'acompte n'apparaît plus. | Dans la vue activité, le filtre d'année se rattache à la date de prestation, pas à la date de paiement. |
| BRD-03 | Bug | P1 | Le solde d'une date n'apparaît pas sans filtre. | Le solde apparaît dans toutes les vues, filtre ou non. Ajouter un test automatisé sur ce cas. |
| BRD-04 | Feature | P1 | Le programme ne distingue pas produit d'activité et trésorerie. | Deux onglets ou un sélecteur, décrits ci-dessous. |

**Modèle proposé pour BRD-04** (proposition de Claude, à valider avec un expert-comptable) :

- **Produits d'activité** : chaque date compte pour son montant total dans l'année et le mois de la prestation. Colonnes : Prévisionnel, Signé, Facturé.
- **Trésorerie** : chaque échéance (acompte, solde) compte à sa date d'encaissement, réelle ou prévue. Colonnes : Encaissé, À encaisser, En retard.
- **Données** : une date porte un montant contractuel ; chaque échéance porte une date d'échéance, une date de facture et une date d'encaissement. Les deux vues lisent les mêmes données, avec une date de référence différente.
- **Cas de test** : date le 15/03/2027, 3 000 € HT, acompte de 900 € facturé et encaissé le 10/11/2026. Vue activité 2027 = 3 000 € ; vue trésorerie 2026 = 900 € encaissés ; vue trésorerie 2027 = 2 100 € à encaisser.

**Libellés d'interface** (le dépôt interdit le jargon comptable) : « Ce que rapportent mes dates » pour les produits d'activité, « Argent reçu et à recevoir » pour la trésorerie. Ce modèle prolonge la règle F-57 (prévu, facturé, encaissé toujours séparés) et F-58 (montants au centime, arrondi seulement à l'affichage). À confronter à specification-onglet-bord.md avant de coder.

## 8. Feuille de route et Radar

La feuille de route doit couvrir tout le déplacement, pas seulement le jour de prestation, et le Radar doit repérer les horaires impossibles.

| ID | Type | Prio | Constat | Attendu |
|---|---|---|---|---|
| FDR-01 | Feature | P1 | On peut programmer un repas avant l'heure d'arrivée sans alerte. Radar prévu après le MVP : à ajouter à sa spécification. | Règle Radar : aucun créneau du programme ne peut commencer avant l'heure d'arrivée. Alerte visible dans le Radar et sur la feuille de route. |
| FDR-02 | Feature | P1 | La date de la feuille de route est bloquée au jour de prestation (je joue le 27, je rentre le 28). | Pouvoir ajouter des jours précis (veille, lendemain, autre) ; chaque créneau porte sa propre date. |
| FDR-03 | Feature | P2 | Pas de pièce jointe sur un créneau. | Ajouter des pièces jointes à un créneau (plan d'accès, billets, fiche technique, réservation d'hôtel). |
| FDR-04 | Bug | P2 | Les infos repas et hébergement saisies ailleurs n'apparaissent pas dans « Programme de la journée ». | Reprendre automatiquement repas et hébergement (CTR-07) dans le programme. |

Autres règles Radar suggérées (propositions de Claude, non demandées) : fin de créneau avant son début, créneaux qui se chevauchent, aucun repas prévu sur une journée longue, départ le soir même sans hébergement.

## Annexe A : listes de référence

Valeurs prêtes à intégrer dans les listes déroulantes. Toutes gardent une option « Autre » avec champ libre.

### A1. Formes juridiques (STR-01)

| Libellé affiché | Code catégorie juridique INSEE (indicatif) |
|---|---|
| Particulier (personne physique, sans activité professionnelle) | — |
| Entrepreneur individuel / micro-entrepreneur | 1000 |
| Association loi 1901 | 9220 |
| Association de droit local (Alsace-Moselle) | 9230 |
| SARL / EURL | 5499 |
| SAS / SASU | 5710 |
| SA | 5599 |
| Coopérative (SCOP, SCIC) | — |
| Commune | 7210 |
| Autre collectivité (département, région, intercommunalité) | — |
| Établissement public (EPCC, EPIC…) | — |
| Fondation / fonds de dotation | — |

Les codes INSEE sont cités de mémoire, à vérifier dans la nomenclature officielle. Intérêt : l'API SIRET (ORG-01) renvoie ce code, ce qui permet de pré-sélectionner la forme juridique.

### A2. Codes APE du spectacle et de l'animation (STR-04)

Nomenclature en vigueur jusqu'au 31/12/2026 (NAF rév. 2) :

- 90.01Z — Arts du spectacle vivant
- 90.02Z — Activités de soutien au spectacle vivant
- 90.03A — Création artistique relevant des arts plastiques
- 90.03B — Autre création artistique
- 90.04Z — Gestion de salles de spectacles
- 59.20Z — Enregistrement sonore et édition musicale
- 74.90B — Activités spécialisées, scientifiques et techniques diverses (souvent utilisé par les agences artistiques, à vérifier)
- 79.90Z — Autres services de réservation et activités connexes (billetterie)
- 82.30Z — Organisation de foires, salons professionnels et congrès
- 85.52Z — Enseignement culturel
- 93.29Z — Autres activités récréatives et de loisirs (animation)
- 94.99Z — Autres organisations fonctionnant par adhésion volontaire

À partir du 1er janvier 2027, les codes changent (NAF 2025) : la liste doit gérer les deux versions et une table de correspondance (Annexe C).

### A3. Qualité du représentant légal (STR-06)

- Associations : Président·e, Co-président·e, Vice-président·e, Secrétaire, Trésorier·ère
- Sociétés : Gérant·e, Co-gérant·e, Président·e (SAS), Directeur·rice général·e
- Lieux et institutions : Directeur·rice, Co-directeur·rice, Administrateur·rice, Directeur·rice délégué·e
- Collectivités : Maire, Adjoint·e à la culture, Président·e (département, région, intercommunalité)
- Entrepreneur individuel : Exploitant·e
- Option : case « Signe par délégation » + nom du délégataire

### A4. Échéances de paiement (CTR-05)

| Acompte à régler | Solde à régler |
|---|---|
| À la signature du contrat | Le jour de la prestation |
| 10 jours après signature | À l'issue de la prestation, sur facture |
| 30 jours après signature | 15 jours après la prestation |
| Fin du mois de signature | 30 jours après la prestation |
| X jours avant la prestation (X paramétrable) | Fin du mois suivant la prestation |
| Date précise | Date précise |

Point de vigilance non vérifié dans cette passe : les délais légaux maximums de paiement entre professionnels et avec les acheteurs publics. Le logiciel pourrait alerter si l'échéance choisie les dépasse.

### A5. Prise en charge repas / hébergement / transport (CTR-07)

| Pris en charge par | Compléments |
|---|---|
| Organisateur | Nombre de personnes, de repas ou de nuits, lieu, régime alimentaire |
| Producteur (nous) | Montant prévu au budget, défraiement éventuel |
| Partagé | Répartition en texte libre |
| Non concerné | — |

## Annexe B : modèles d'e-mails

Les variables entre crochets sont remplacées automatiquement. Chaque modèle doit être modifiable dans les paramètres (CTR-03).

**Format d'objet commun** : [Titre du spectacle] – [Nom du groupe] – [Date(s)] – [Statut] – [Objet du message]. Statut = Option, Confirmé, Annulé.

### B1. Envoi du formulaire organisateur (ORG-06)

```markdown
Objet : [Titre du spectacle] – [Nom du groupe] – [Date] – [Statut] – Informations organisateur

Bonjour [Prénom],

Suite à nos échanges au sujet de [Titre du spectacle] ([Nom du groupe]) le [Date] à [Ville], je vous remercie de compléter ce formulaire en ligne :

[Lien du formulaire]

Il nous permettra d'établir le contrat de cession et la feuille de route. Comptez environ 5 minutes. Seront demandés : coordonnées légales de votre structure (SIRET, adresse, représentant légal, licence d'entrepreneur de spectacles) et vos contacts (administration, technique, accueil).

Je reste à votre disposition pour toute question.

Bien cordialement,
[Signature]
```

### B2. Envoi du contrat de cession (CTR-08)

```markdown
Objet : [Titre du spectacle] – [Nom du groupe] – [Date] – Confirmé – Contrat de cession

Bonjour [Prénom],

Vous trouverez ci-joint le contrat de cession pour [Titre du spectacle] le [Date] à [Ville].

Merci de nous le retourner signé avant le [Date limite]. L'acompte de [Montant acompte] est à régler [Échéance acompte].

Bien cordialement,
[Signature]
```

### B3. Relance contrat non signé (DAT-07)

```markdown
Objet : [Titre du spectacle] – [Nom du groupe] – [Date] – Relance contrat de cession

Bonjour [Prénom],

Sauf erreur de ma part, nous n'avons pas encore reçu le contrat signé pour [Titre du spectacle] le [Date], envoyé le [Date d'envoi]. Pourriez-vous nous le retourner dès que possible ?

Bien cordialement,
[Signature]
```

**Note technique mailto:** une URL mailto ne peut pas joindre de fichier : pour B2, mettre un lien de téléchargement du PDF dans le message, ou proposer l'envoi depuis l'app. Encoder objet et corps (encodeURIComponent) et rester sous environ 2 000 caractères, limite de certains clients de messagerie. Toujours offrir « Copier le message » en secours.

## Annexe C : API publiques et points réglementaires

Les deux besoins d'autocomplétion (ORG-01, ORG-02) sont couverts par des API de l'État gratuites et sans clé. Trois sujets réglementaires touchent directement les devis, factures et fiches structure.

### C1. API à utiliser (faits sourcés)

| Besoin | API | Points clés |
|---|---|---|
| SIRET → données légales (ORG-01) | [API Recherche d'entreprises](https://github.com/annuaire-entreprises-data-gouv-fr/search-api) — recherche-entreprises.api.gouv.fr | Recherche par nom, SIREN, SIRET, adresse, code NAF. Gratuite, sans authentification pour les volumes courants ([Lido](https://www.lido.app/fr/validation-siret-siren)). Environ 7 appels par seconde ([Packagist](https://packagist.org/packages/omnistate/annuaire-entreprises)). Un nouveau SIRET peut mettre 1 à 3 jours à apparaître ([Lookuptax](https://lookuptax.com/docs/fr/comment-verifier/verification-siret-france)). |
| Gros volumes | API Sirene de l'INSEE (portail-api.insee.fr) | Clé gratuite requise, limite de débit d'environ 30 requêtes par minute ([Lookuptax](https://lookuptax.com/docs/fr/comment-verifier/verification-siret-france)). |
| Code postal → communes (ORG-02) | [API Découpage administratif](https://api.gouv.fr/guides/autocompleter-geo) — geo.api.gouv.fr | Exemple : geo.api.gouv.fr/communes?codePostal=78000 ([guide data.gouv](https://guides.data.gouv.fr/~/revisions/5wMYUxr1xSI4cw0Rc0V2/reutiliser-des-donnees/utiliser-les-api-geographiques/utiliser-lapi-decoupage-administratif)). Mettre en cache les appels lourds. |

### C2. Mentions TVA sur devis et factures (CTR-02)

| Régime de la structure | Mention ou taux | Source |
|---|---|---|
| Franchise en base | « TVA non applicable, article 293 B du CGI », obligatoire sur chaque facture | [BOFiP](https://bofip.impots.gouv.fr/export/pdf/1182) |
| Assujetti, contrat de cession d'un spectacle visé au F de l'art. 278-0 bis CGI | 5,5 % ; une vente au forfait sans cession du droit d'exploitation relève du taux normal | [ma-facture-electronique.org](https://ma-facture-electronique.org/?p=2900) |
| Assujetti, billetterie des 140 premières représentations d'une création | 2,10 % (art. 281 quater CGI), décompte poursuivi en tournée | [BOFiP via thetradehub](https://www.thetradehub.eu/en/reglementation/france/doctrine/bofip/bofip-boi-tva-liq-40-20) |
| Association non soumise aux impôts commerciaux | « Association exonérée des impôts commerciaux » | [AC-RA, 2021](https://www.ac-ra.eu/wp-content/uploads/2022/09/facturation-janvier-21.pdf) |

Seuils de franchise 2026 : 37 500 € pour les prestations de services (seuil majoré 41 250 €) et 85 000 € pour les ventes ; la réforme du seuil unique à 25 000 € a été abandonnée ([Hayot Expertise](https://hayot-expertise.fr/blog/reforme-franchise-tva-2026-seuil-25000-euros)). Les artistes-interprètes ont un seuil propre de 50 000 € ([Sparkreceipt](https://sparkreceipt.com/fr-fr/blog/franchise-en-base-de-tva/)). Recommandation : le logiciel peut alerter quand le CA approche du seuil. Le tableau ci-dessus est à faire valider par un expert-comptable avant mise en production.

### C3. Nouvelle nomenclature NAF 2025 au 1er janvier 2027 (STR-04)

- La NAF 2025 devient la référence pour l'attribution des codes APE au 1er janvier 2027 ; pendant 2026, sirene.gouv.fr montre aux entreprises leur futur code ([INSEE](https://www.insee.fr/fr/information/8181066)).
- Base légale : décret n° 2025-736 du 31 juillet 2025 ; l'ancienne NAF rév. 2 est abrogée à la même date ([Lefebvre Dalloz](https://formation.lefebvre-dalloz.fr/actualite/evolution-de-la-nomenclature-francaise-des-activites-en-2027-impact-sur-les-codes-ape-des-entreprises)).
- Impact app : stocker la version de nomenclature avec le code, importer la table de correspondance de l'INSEE, rafraîchir les codes via l'API SIRET en 2027. Les nouveaux codes de la division 90 n'ont pas été relevés dans cette passe.

### C4. Facturation électronique (module factures)

- Une compagnie en franchise en base reste assujettie, donc dans le périmètre de la réforme ([ma-facture-electronique.org](https://ma-facture-electronique.org/par-secteur/culture-spectacle/)).
- Selon la même source, la réception de factures électroniques est obligatoire depuis septembre 2026, et l'émission le devient ensuite pour les PME. Calendrier exact à confirmer sur impots.gouv.fr.
- Impact app : prévoir l'export en format structuré ou la connexion à une plateforme agréée. À inscrire à la feuille de route produit 2027, hors périmètre de ce test.

Paie des intermittents : aucun retour de ce test ne la concerne ; pas de veille faite sur ce point ici.

## Questions ouvertes

Points à trancher avant développement :

- [ ] **Tribunal compétent** (bloc « Représentant et tribunal ») : liste déroulante, champ libre, ou déduction depuis l'adresse du siège ?
- [ ] **Numéro d'objet** (SPE-02) : confirmer le format officiel avant d'imposer un contrôle de saisie.
- [ ] **Modèles de contrat de cession** (STR-08) : déjà livrés (quatre modèles) ; reste à décider si un modèle par défaut est utile.
- [ ] **Radar** (FDR-01) : une incohérence d'horaire doit-elle bloquer l'enregistrement, ou seulement avertir ?
- [ ] **Priorités** : valider ou modifier le classement P1 / P2 / P3 proposé.
- [ ] **TVA et échéances** : faire valider l'Annexe C2 et les délais de l'Annexe A4 par un expert-comptable.
- [ ] **Benchmark** : comparer ces points avec Orféo et Bob Booking (non fait dans cette passe).

À trancher avec le développeur, après lecture du dépôt :

- [ ] **Cahier des charges** : lesquels de ces retours figurent déjà dans docs/produit/cahier-des-charges.md, et lesquels faut-il y ajouter avant de les coder ?
- [ ] **Spécifications de l'associé** : BRD-xx, DAT-04, DAT-07, FDR-02 et FDR-03 sont-ils déjà couverts par les spécifications Bord, checklist de contractualisation et feuille de route type ?
- [ ] **Rappels automatiques** (DAT-07) : liste « À faire » seule, ou aussi un e-mail planifié (sans Celery) ?
- [ ] **Formulaire organisateur** (ORG-05) : étapes supplémentaires dans le formulaire existant, ou second lien ?
