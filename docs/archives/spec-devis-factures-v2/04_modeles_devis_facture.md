# Bòrd Pro — Modèles de devis et de facture (spécification DEV)

Version 1 — 13 novembre 2026  
Statut : modèle de travail, à valider avant mise en production. Complète les documents 01 à 03 (contrats de cession) et reprend leur vocabulaire.

Sources : structure des devis et factures émis par HopHopHop via Crealead (devis n° 20262429, facture n° 2503590), adaptée au spectacle vivant ; retour de recette CTR-10 ; mentions obligatoires en vigueur au 13/11/2026.

## 0. Cadrage avec l'existant

### 0.1. Ce qui existe déjà dans Bòrd Pro

Devis, factures d'acompte, de solde et totale, avoirs, numérotation `D-AAAA-NNNN` / `F-AAAA-NNNN`, IBAN et BIC affichés, facture émise immuable (correction par avoir), informations légales copiées à l'émission (CLAUDE.md § 6.2). Ce document ne change pas ces règles : il fixe le **contenu** et la **mise en page** des PDF.

### 0.2. Vocabulaire

| Dans ce document | Dans le code | À l'écran |
|---|---|---|
| Émetteur, producteur | `Tenant` | Ma structure — Informations de la structure (`/bord/informations/`) |
| Client, organisateur | `Promoter` | Organisateur |
| Devis | `Quote` | Devis |
| Facture, avoir | `Invoice` | Facture, avoir |
| Date, représentation | `Gig` | Date |
| Spectacle | `Show` | Spectacle |
| Instantané fiscal | `fiscalite_snapshot` (même règle que le contrat, doc 03 § 2.3) | — |

Règle CLAUDE.md : ne jamais écrire `Client` dans le code. « Client » n'apparaît que sur le PDF, comme intitulé du bloc destinataire.

### 0.3. Ce que ces modèles ajoutent par rapport à l'existant

| # | Ajout | Origine |
|---|---|---|
| A1 | Lignes détaillées : désignation courte + description longue, quantité, unité, prix unitaire HT, montant HT, montant TTC, taux de TVA | Modèles Crealead |
| A2 | Remise commerciale en ligne négative (en % ou en montant) | Devis Crealead |
| A3 | Récapitulatif de TVA par taux (base HT, taux, montant TVA, TTC) | Modèles Crealead |
| A4 | Sur la facture : référence du devis accepté (numéro, date, montant), pièces déjà émises (factures d'acompte), acompte déduit en ligne négative, reste à payer | Facture Crealead + retour CTR-10 |
| A5 | Devis : date de validité, mention « Bon pour accord », zone de signature | Devis Crealead |
| A6 | Logo de la structure en en-tête | Retour CTR-01 |
| A7 | Mentions fiscales issues du profil fiscal de la structure (avec ou sans TVA), comme le contrat | Doc 03 § 2 + retour CTR-02 |
| A8 | Nouvelles mentions de la facturation électronique : SIREN du client, catégorie d'opération, option TVA sur les débits | Réforme 2026 (§ 6) |
| A9 | Bloc « structure portée par une coopérative » (CAE), facultatif | Modèles Crealead |
| A10 | Bloc médiation de la consommation quand le client est un particulier | Modèles Crealead + décision D2 du doc 03 (organisateur particulier) |

## 1. Modèle — Devis

```markdown
[logo {{producteur.logo}}]

# Devis n° {{devis.numero}}

Date : {{devis.date_emission}}  
Valable jusqu'au : {{devis.date_validite}}  
{{#si producteur.cae}}Activité : {{producteur.cae.code_activite}}{{/si}}

| Émetteur | Client |
|---|---|
| {{producteur.denomination_juridique}} | {{organisateur.denomination_juridique}} |
| {{producteur.adresse_complete}} | {{organisateur.contact_nom}} |
| SIRET {{producteur.siret}} | {{organisateur.adresse_complete}} |
| N° de licence : {{producteur.mention_licence_ou_dispense}} | {{#si organisateur.siren}}SIREN {{organisateur.siren}}{{/si}} |
| {{producteur.contact_email}} — {{producteur.contact_telephone}} | {{#si organisateur.numero_tva}}N° de TVA : {{organisateur.numero_tva}}{{/si}} |

Objet : {{devis.objet}}  
Représentation : {{gig.spectacle_titre}} — {{gig.date_representation}} — {{gig.lieu_nom}}, {{gig.lieu_commune}}

| N° | Désignation | Qté | Unité | Prix unitaire HT | Montant HT | TVA | Montant TTC |
|---|---|---:|---|---:|---:|---:|---:|
| {{#pour ligne in devis.lignes}} |
| {{ligne.numero}} | **{{ligne.designation}}**<br>{{ligne.description}} | {{ligne.quantite}} | {{ligne.unite}} | {{ligne.prix_unitaire_ht}} € | {{ligne.montant_ht}} € | {{ligne.taux_tva}} | {{ligne.montant_ttc}} € |
| {{/pour}} |

{{#si fiscalite_snapshot.facture_tva}}
| Taux de TVA | Base HT | Montant TVA | Montant TTC |
|---|---:|---:|---:|
| {{#pour taux in devis.recap_tva}}{{taux.libelle}} | {{taux.base_ht}} € | {{taux.montant_tva}} € | {{taux.montant_ttc}} €{{/pour}} |
| **Total** | **{{devis.total_ht}} €** | **{{devis.total_tva}} €** | **{{devis.total_ttc}} €** |

{{fiscalite_snapshot.mention_tva}}
{{sinon}}
**Total net de TVA : {{devis.total_net}} €**

{{fiscalite_snapshot.mention_absence_tva}} ({{fiscalite_snapshot.reference_legale_absence_tva}})
{{/si}}

Conditions de paiement proposées : {{devis.echeancier_resume}}  
Catégorie d'opération : prestation de services

Pour accepter ce devis, merci de le renvoyer daté et signé avec la mention « Bon pour accord ».

| Pour le client |
|---|
| Date : |
| Nom et qualité : |
| Signature précédée de « Bon pour accord » : |

{{> pied_de_page}}
```

## 2. Modèle — Facture (acompte, solde ou totale)

```markdown
[logo {{producteur.logo}}]

# {{facture.type_libelle}} n° {{facture.numero}}

Date d'émission : {{facture.date_emission}}  
Date de la prestation : {{gig.date_representation}}  
Échéance : {{facture.date_echeance}}  
{{#si organisateur.reference_client}}Réf. client : {{organisateur.reference_client}}{{/si}}  
{{#si facture.bon_de_commande}}Bon de commande : {{facture.bon_de_commande}}{{/si}}  
{{#si producteur.cae}}Activité : {{producteur.cae.code_activite}}{{/si}}

| Émetteur | Client |
|---|---|
| {{producteur.denomination_juridique}} | {{organisateur.denomination_juridique}} |
| {{producteur.adresse_complete}} | {{organisateur.contact_nom}} |
| SIRET {{producteur.siret}} | {{organisateur.adresse_facturation}} |
| N° de licence : {{producteur.mention_licence_ou_dispense}} | {{#si organisateur.siren}}SIREN {{organisateur.siren}}{{/si}} |
| {{#si fiscalite_snapshot.numero_tva_intracommunautaire}}N° de TVA : {{fiscalite_snapshot.numero_tva_intracommunautaire}}{{/si}} | {{#si organisateur.numero_tva}}N° de TVA : {{organisateur.numero_tva}}{{/si}} |

{{#si facture.devis}}
Référence du devis : n° {{facture.devis.numero}} du {{facture.devis.date_emission}}, accepté le {{facture.devis.date_acceptation}} ({{facture.devis.total_ttc}} € TTC).
{{/si}}
{{#si facture.contrat}}
Contrat de cession : n° {{facture.contrat.reference}}, signé le {{facture.contrat.date_signature}}.
{{/si}}

{{#si facture.pieces_precedentes}}
Pièces déjà émises pour cette date :
{{#pour piece in facture.pieces_precedentes}}
- {{piece.type_libelle}} n° {{piece.numero}} du {{piece.date_emission}} ({{piece.total_ttc}} € TTC){{/pour}}
{{/si}}

| N° | Désignation | Qté | Unité | Prix unitaire HT | Montant HT | TVA | Montant TTC |
|---|---|---:|---|---:|---:|---:|---:|
| {{#pour ligne in facture.lignes}} |
| {{ligne.numero}} | **{{ligne.designation}}**<br>{{ligne.description}} | {{ligne.quantite}} | {{ligne.unite}} | {{ligne.prix_unitaire_ht}} € | {{ligne.montant_ht}} € | {{ligne.taux_tva}} | {{ligne.montant_ttc}} € |
| {{/pour}} |

{{#si fiscalite_snapshot.facture_tva}}
| Taux de TVA | Base HT | Montant TVA | Montant TTC |
|---|---:|---:|---:|
| {{#pour taux in facture.recap_tva}}{{taux.libelle}} | {{taux.base_ht}} € | {{taux.montant_tva}} € | {{taux.montant_ttc}} €{{/pour}} |
| **Total de cette facture** | **{{facture.total_ht}} €** | **{{facture.total_tva}} €** | **{{facture.total_ttc}} €** |

{{fiscalite_snapshot.mention_tva}}
{{#si fiscalite_snapshot.option_debits}}Option pour le paiement de la taxe d'après les débits.{{/si}}
{{sinon}}
**Total de cette facture, net de TVA : {{facture.total_net}} €**

{{fiscalite_snapshot.mention_absence_tva}} ({{fiscalite_snapshot.reference_legale_absence_tva}})
{{/si}}

{{#si facture.est_solde}}
| Récapitulatif de la date | Montant |
|---|---:|
| Prix total convenu (contrat ou devis) | {{facture.total_convenu}} € |
| Déjà facturé (acomptes) | {{facture.deja_facture}} € |
| Montant de cette facture | {{facture.total_a_payer}} € |
| Reste à facturer après cette facture | {{facture.reste_a_facturer}} € |
{{/si}}

Catégorie d'opération : prestation de services  
**Montant à payer : {{facture.total_a_payer}} € — avant le {{facture.date_echeance}}, par {{facture.mode_paiement}}{{#si producteur.cae}} à l'ordre de {{producteur.cae.denomination}}{{/si}}.**

{{#si organisateur.est_professionnel}}
En cas de retard de paiement : pénalités au taux de {{producteur.taux_penalites_retard}} et indemnité forfaitaire pour frais de recouvrement de 40 €. Aucun escompte n'est accordé pour paiement anticipé.
{{/si}}

{{> pied_de_page}}
```

### 2.1. Lignes types d'une facture de spectacle

| Cas | Désignation | Description (exemple) | Qté | Unité |
|---|---|---|---:|---|
| Cession | Cession du droit d'exploitation du spectacle | « La Route » — 30/11/2026 — Le Sonambule, Gignac | 1 | forfait |
| Acompte (facture d'acompte) | Acompte sur cession | 30 % du prix convenu au contrat n° C-2026-002 | 1 | forfait |
| Acompte déduit (facture de solde) | Acompte déjà facturé | Facture d'acompte n° F-2026-0003 du 05/11/2026 | -1 | forfait |
| Frais convenus | Frais de transport / hébergement / repas | Selon article 4 du contrat | n | forfait, km, nuit |
| Remise | Remise commerciale | 10 % sur la cession | -n | % ou € |

La ligne « Acompte déjà facturé » reprend le montant HT et le taux de la facture d'acompte, en négatif, pour que le récapitulatif de TVA de la facture de solde soit juste.

## 3. Pied de page commun (`pied_de_page`)

```markdown
{{producteur.denomination_juridique}} — {{producteur.forme_juridique}} — SIRET {{producteur.siret}}{{#si producteur.code_ape}} — APE {{producteur.code_ape}}{{/si}}
{{producteur.adresse_complete}} — {{producteur.contact_email}} — {{producteur.contact_telephone}}
Paiement par virement : IBAN {{producteur.iban}} — BIC {{producteur.bic}} — {{producteur.banque}}

{{#si producteur.cae}}
Activité hébergée par {{producteur.cae.denomination}}, {{producteur.cae.forme_juridique}}, {{producteur.cae.adresse}} — SIREN {{producteur.cae.siren}} — N° de TVA {{producteur.cae.numero_tva}}.
{{/si}}

{{#si organisateur.est_particulier}}
Médiation de la consommation : en cas de litige, le client peut saisir gratuitement le médiateur {{producteur.mediateur.nom}}, {{producteur.mediateur.coordonnees}}, après une réclamation écrite restée sans réponse satisfaisante.
{{/si}}

Page {{page}} sur {{pages}}
```

## 4. Provenance des données

| Bloc | Source | Remarque |
|---|---|---|
| Émetteur, logo, IBAN, BIC, banque | Informations de la structure (`/bord/informations/`) | Copié à l'émission (instantané) |
| Profil fiscal, mentions TVA, option débits | Informations de la structure, profil fiscal (doc 03 § 2.2) | Même instantané que le contrat |
| Bloc CAE | Informations de la structure, nouvelle section facultative « Je facture via une coopérative » | Dénomination, forme, adresse, SIREN, n° TVA, code activité |
| Médiateur de la consommation | Informations de la structure | Requis seulement si la structure facture un particulier |
| Client | Fiche organisateur (`Promoter`) | SIREN = 9 premiers chiffres du SIRET, calculé |
| Représentation | Date (`Gig`) et spectacle (`Show`) | |
| Prix, frais, échéances, acompte | Fiche « Contrat » de la date (doc 03 § 8), sinon devis accepté | Le contrat signé prime sur le devis |
| Pièces précédentes, reste à facturer | Factures déjà émises pour la date | Calculé, jamais saisi |

## 5. Règles de calcul et de contrôle

| Règle | Niveau |
|---|---|
| Montants en `Decimal`, arrondis au centime par ligne, puis totaux = somme des lignes (F-58) | BLOCAGE si écart |
| Pas de taux 0 % affiché quand la structure ne facture pas la TVA : bloc « net de TVA » + mention et fondement (doc 03 § 2.2) | BLOCAGE |
| Facture de solde : total des factures émises pour la date = prix total convenu | BLOCAGE si dépassement ; AVERTISSEMENT si le total reste inférieur |
| Facture d'acompte : montant ≤ prix convenu | BLOCAGE |
| Acompte déduit = montant exact d'une facture d'acompte existante et non annulée par avoir | BLOCAGE |
| Client professionnel : SIRET ou SIREN renseigné | BLOCAGE (sauf client particulier) |
| Client particulier : médiateur renseigné dans Informations de la structure | BLOCAGE |
| Devis : date de validité postérieure à la date d'émission | BLOCAGE |
| Prix d'un devis différent du prix du contrat signé de la même date | AVERTISSEMENT |
| Facture émise : immuable, correction par avoir (CLAUDE.md § 6.2) | — |
| Plusieurs taux de TVA sur une même facture | Le récapitulatif par taux le permet ; à aligner sur la règle V1 du contrat (doc 03 § 8 : un seul régime pour le prix principal) |

## 6. Réglementaire (sourcé)

| Fait | Effet sur les modèles |
|---|---|
| La réforme de la facturation électronique ajoute quatre mentions : SIREN du client, adresse de livraison si différente de l'adresse de facturation, catégorie d'opération, option pour le paiement de la TVA d'après les débits ([swim.legal, 06/11/2026](https://www.swim.legal/blog/tva-nouvelles-mentions-obligatoires-factures)) | SIREN client, « Catégorie d'opération : prestation de services », option débits si cochée. L'adresse de livraison ne concerne pas une prestation de spectacle. |
| Réception des factures électroniques obligatoire pour toutes les entreprises depuis le 1er septembre 2026 ; émission au 1er septembre 2027 pour les PME et micro-entreprises ([abby.fr](https://abby.fr/guide/facturation-electronique/quelles-informations-doivent-apparaitre-sur-une-facture-electronique)) | Le PDF reste valable pour les structures de notre cible jusqu'en septembre 2027. Après, il faudra un format structuré via une plateforme agréée : chantier séparé. |
| La plateforme agréée lit les données dans le fichier structuré, pas la ligne imprimée ([ma-facture-electronique.org](https://ma-facture-electronique.org/reforme-2026/nouvelles-mentions-obligatoires/option-tva-debits/)) | Stocker chaque mention comme une donnée (champ), pas seulement comme du texte du PDF. |

Les autres mentions (pénalités, indemnité de 40 €, absence d'escompte, médiation) sont reprises des modèles Crealead. Elles sont à faire relire par l'expert-comptable ou le juriste qui relira les contrats.

## 7. Questions ouvertes

- [ ] **CAE** : faut-il prévoir dès la V1 le bloc « structure portée par une coopérative » (cas de Jeff via Crealead, fréquent chez les artistes) ? Dans ce cas, le n° de facture est-il celui de la coopérative ou celui de Bòrd Pro ?
- [ ] **Taux des pénalités de retard** : valeur par défaut proposée (3 fois le taux d'intérêt légal, comme Crealead) ou saisie libre ?
- [ ] **Devis signé** : seulement « Bon pour accord » renvoyé à la main en V1 (cohérent avec le phasage D9 du doc 03) ?
- [ ] **Unités** : liste fermée (forfait, jour, heure, km, nuit, %) ou texte libre ?
