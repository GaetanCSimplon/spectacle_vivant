# Recette n°1 : résumé des changements, ticket par ticket

Source des retours : [bord-pro-retours-recette-1.md](../marque/sources-associe/bord-pro-retours-recette-1.md) (44 retours de l'associé, 2026-11-05, plus ORG-07 et DAT-08 ajoutés le 10/11). Suivi détaillé et décisions : [feuille-de-route.md](feuille-de-route.md), section « Retours de la recette n°1 ». Ce résumé est écrit à la fin de la journée du 2026-11-12 ; les numéros sont ceux des PR fusionnées dans `main`.

« Migration » = ajout additif (colonne ou table vide), à appliquer par l'utilisateur. Aucune livraison en production n'a été faite.

## 1. Les 46 retours, ticket par ticket

### Navigation (NAV)
| Ticket | Ce qui a changé | PR |
|---|---|---|
| NAV-01 | Icône devant chaque entrée du menu. | #324 |
| NAV-02 | Accès permanent aux « Informations de la structure » (icône dans la barre du haut, lien en pied de la colonne de gauche). | #324 |
| NAV-03 | Fil d'Ariane « Mes dates › la date › la page » et bouton de retour. | #325 |
| NAV-04 | Filtre d'année de l'accueil étendu aux années à venir et à « Toutes ». | #324 |

### Structure (STR)
| Ticket | Ce qui a changé | PR |
|---|---|---|
| STR-01, STR-05, STR-06 | Forme juridique et qualité du représentant en listes (avec « Autre ») ; nom et prénom du représentant séparés. Migration `tenants/0015`. | #327 |
| STR-02 | Après l'onboarding, message qui indique où compléter les informations légales. | #327 |
| STR-03 | SIRET affiché en 3-3-3-5, stocké sans espaces, clé de contrôle vérifiée. | #327 |
| STR-04 | Code APE en liste du spectacle et de l'animation (NAF rév. 2) avec saisie libre ; préremplissage par SIRET. La NAF 2025 reste à traiter en janvier 2027. | #332 |
| STR-07 | Logo de la structure (PNG ou JPEG, 2 Mo au plus, privé), copié sur les devis, factures émises et contrats. Migration `tenants/0016`. | #353 |
| STR-08 | **Sans objet** : l'associé a décidé le 2026-11-12 d'aller vers un seul modèle de contrat personnalisable. Rien n'a été codé. | — |
| STR-09 | Régime de TVA de la structure, qui pilote la mention légale des devis et factures. | #329 |

### Organisateurs (ORG)
| Ticket | Ce qui a changé | PR |
|---|---|---|
| ORG-01, ORG-02 | « Retrouver par SIRET ou par nom » (API publique de l'État) sur l'organisateur et la structure ; communes proposées à partir du code postal. | #332 |
| ORG-03 | Période habituelle en plages de dates récurrentes (jusqu'à 3). Migration `addressbook/0018`. | #345 |
| ORG-04, ORG-05 | Formulaire de l'organisateur : jusqu'à 4 contacts avec rôle, puis suite avec les informations du contrat de la date. Migration `addressbook/0016`. | #339 |
| ORG-06 | « Envoyer par e-mail » (`mailto:`), « Copier le message », « Copier le lien ». | #338 |
| ORG-07 | Formulaire en ligne pour un contact ou un membre de l'équipe (lien secret de 7 jours, vérification avant application). Migration `addressbook/0017`. | #340 |

### Dates (DAT)
| Ticket | Ce qui a changé | PR |
|---|---|---|
| DAT-01, DAT-02 | Nom de l'évènement à la création ; titre des cartes « Lieu, Ville, Spectacle » (ou nom de l'évènement). | #325, #336 |
| DAT-03 | Fenêtre « Envoyer le formulaire à l'organisateur ? » après la création d'une date. | #336 |
| DAT-04, DAT-05, DAT-08 | Frise des étapes datées, bloc Documents, bloc Contacts sur la page d'une date. | #336 |
| DAT-06 | Bande Prévisionnel / Signé / Facturé / Encaissé en tête de « Mes dates ». | #350 |
| DAT-07 (et CTR-09) | « Alertes et rappels » de l'accueil : contrat envoyé et non signé depuis 7 jours, bouton « Relancer » (e-mail B3). | #349 |

### Spectacles (SPE)
| Ticket | Ce qui a changé | PR |
|---|---|---|
| SPE-01 | Ajout d'une personne à la distribution avec fonction, téléphone et e-mail. | #351 |
| SPE-02 | N° d'objet au format `22-3-P-513447-57`, contrôlé dans la fiche du spectacle et dans « Compléter le contrat » (format à confirmer officiellement). | #344 |
| SPE-03 | Couleur par spectacle (palette de 8, provisoire, à faire valider par le graphiste). Migration `catalog/0007`. | #352 |

### Devis, contrats, factures (CTR)
| Ticket | Ce qui a changé | PR |
|---|---|---|
| CTR-01 | Logo en en-tête des devis, factures, avoirs et des quatre contrats. | #353 |
| CTR-02 | Mentions de TVA du devis et de la facture reprises de la source unique (écran et PDF). Relecture comptable toujours requise. | #329 |
| CTR-03 | **Partiel** : les quatre e-mails (formulaire, contrat, relance, contact ou équipe) sont modifiables dans « Modèles de messages ». Les modèles de contrat, de devis et de facture (mentions, pied de page, numérotation) ne sont pas faits. Migration `tenants/0017`. | #354 |
| CTR-04 | Retour direct à la date après validation d'un devis. | #325 |
| CTR-05, CTR-06 | Échéances d'acompte et de solde en listes ; « Compléter le contrat » en blocs Contrat, Budget, Feuille de route. Migration `gigs/0012`. | #333 |
| CTR-07 | « Pris en charge par », nombre et précisions pour les repas et l'hébergement. Migration `gigs/0013`. | #335 |
| CTR-08 | Écran « Contrat et versions » avec envoi par e-mail ; lien de téléchargement secret de 7 jours dans le message. Migration `documents/0012`. | #338 |
| CTR-10 | Bloc « Rappel de la commande » sur les factures (devis, total signé, acompte, solde), copié à l'émission. Migration `documents/0011`. | #331 |

### Bord (BRD)
| Ticket | Ce qui a changé | PR |
|---|---|---|
| BRD-01, BRD-03 | Libellé « Prévisionnel » ; explication quand des factures sont émises hors de la période. Le cas de l'associé n'était pas un calcul faux : date encore en option et factures émises en 2026. | #323 |
| BRD-02, BRD-04 | Deux lectures : « Ce que rapportent mes dates » (par date du concert) et « Argent reçu et à recevoir » (par date de l'argent). Relecture comptable requise. | #342 |

### Feuille de route (FDR)
| Ticket | Ce qui a changé | PR |
|---|---|---|
| FDR-01 | **Spécification seulement** : règle R1 du Radar (aucun élément avant l'arrivée), avertissement sans blocage. Rien n'est codé. | #343 |
| FDR-02, FDR-03 | Feuille de route sur plusieurs jours (créneau, repas et hébergement ont leur jour) ; pièces jointes de créneau dans l'espace équipe. Migration `roadmaps/0009`. | #341 |
| FDR-04 | Repas et hébergement repris dans le programme. | #335, #341 |

## 2. Retours de l'utilisateur du 2026-11-12 (ergonomie, hors du document de l'associé)

Ces demandes ne figurent pas dans le document source ; elles prolongent la note « ergonomie et agencement des pages ».

| Demande | Ce qui a changé | PR |
|---|---|---|
| Liens « Voir… » en boutons | Boutons secondaires de taille réduite partout. | #355 |
| Contenu sur toute la largeur | Largeur par défaut de l'ordinateur ; seules les pages à une seule question restent étroites. | #355 |
| Filtres derrière un bouton | « Filtres » sur Mes dates, organisateurs, contacts, documents et Bord ; les deux lectures du Bord restent à part. | #356 |
| Bord > Tableau de bord | Rubriques dépliables ; « À traiter maintenant » avec l'en-tête d'« Alertes et rappels » ; boutons en bas de page. | #357 |
| Calendrier | Cartes de la Liste ; « Ce que rapportent ces dates » en bleu nuit (ajouté au calendrier). | #358 |
| Page d'une date | Titre « Organisateur · Lieu, Ville » ; « La date » et « Contacts » côte à côte ; carte « Prochaine action » et « Suivi de la date » ; volets inchangés. | #359 |
| Boutons blancs sur blanc | Les boutons gardent leurs couleurs dans les blocs colorés. | #360 |

## 3. Ce qui reste ou à confirmer

- **Radar** : à coder après réception des documents de l'associé ; règle R1 déjà spécifiée (FDR-01).
- **CTR-03, partie documents** : modèles de contrat, devis et facture ; à reprendre avec la décision « un seul contrat personnalisable ».
- **Relecture professionnelle** : mentions de TVA (annexe C2), échéances (annexe A4), chiffres du Bord.
- **NAF 2025** : changement des codes APE au 1er janvier 2027.
- **N° d'objet** : confirmer le format officiel.
- **Palette des spectacles** : validation par le graphiste.
- **Revue d'ergonomie** : à poursuivre avec des captures et l'associé (aération de la page d'une date, libellés des deux lectures du Bord).
- **Migrations à appliquer par vous** : `tenants/0015`, `0016`, `0017` ; `documents/0011`, `0012` ; `gigs/0012`, `0013` ; `addressbook/0016` à `0018` ; `roadmaps/0009` ; `catalog/0007` (celles déjà appliquées en local sont notées dans la feuille de route).
