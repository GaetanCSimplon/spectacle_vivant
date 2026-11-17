# {{facture.type_libelle}} n° {{facture.numero}}

{{producteur.logo}}

Date d’émission : {{facture.date_emission}}  
Date de la prestation : {{gig.date_representation}}  
Date d’échéance : {{facture.date_echeance}}  
{{facture.mention_bon_de_commande}}

| Émetteur | Client |
|---|---|
| {{producteur.denomination_juridique}} | {{organisateur.denomination_juridique}} |
| {{producteur.forme_juridique}} | {{organisateur.contact_nom}} |
| {{producteur.adresse_complete}} | {{organisateur.adresse_facturation}} |
| SIRET {{producteur.siret}} | {{organisateur.mention_siren}} |
| N° de licence : {{producteur.mention_licence_ou_dispense}} | {{organisateur.mention_numero_tva}} |
| {{fiscalite_snapshot.mention_numero_tva_producteur}} | {{organisateur.contact_email}} |

## Références

{{facture.mention_devis}}  
{{facture.mention_contrat}}

{{facture.bloc_pieces_precedentes}}

## Détail

| N° | Désignation | Qté | Unité | Prix unitaire HT | Montant HT | TVA | Montant TTC |
|---|---|---:|---|---:|---:|---:|---:|
{{facture.lignes}}

{{facture.bloc_totaux}}

{{fiscalite_snapshot.bloc_mention_fiscale}}

{{facture.bloc_recapitulatif_date}}

## Règlement

**Montant à payer : {{facture.total_a_payer}} € avant le {{facture.date_echeance}}, par {{facture.mode_paiement}}.**

Catégorie d’opération : prestation de services.  
{{fiscalite_snapshot.mention_option_debits}}

{{facture.bloc_conditions_retard}}

---

{{pied_de_page}}
