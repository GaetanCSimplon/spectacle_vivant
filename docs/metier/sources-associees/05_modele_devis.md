# Devis n° {{devis.numero}}

{{producteur.logo}}

Date d’émission : {{devis.date_emission}}  
Valable jusqu’au : {{devis.date_validite}}

| Émetteur | Client |
|---|---|
| {{producteur.denomination_juridique}} | {{organisateur.denomination_juridique}} |
| {{producteur.forme_juridique}} | {{organisateur.contact_nom}} |
| {{producteur.adresse_complete}} | {{organisateur.adresse_facturation}} |
| SIRET {{producteur.siret}} | {{organisateur.mention_siren}} |
| N° de licence : {{producteur.mention_licence_ou_dispense}} | {{organisateur.mention_numero_tva}} |
| {{producteur.contact_email}} — {{producteur.contact_telephone}} | {{organisateur.contact_email}} |

## Objet

{{devis.objet}}

| Représentation | |
|---|---|
| Spectacle | {{gig.spectacle_titre}} — {{gig.artiste_nom}} |
| Date | {{gig.date_representation}} |
| Nombre de représentations | {{gig.nombre_representations}} |
| Lieu | {{gig.lieu_nom}}, {{gig.lieu_commune}} |

## Détail

| N° | Désignation | Qté | Unité | Prix unitaire HT | Montant HT | TVA | Montant TTC |
|---|---|---:|---|---:|---:|---:|---:|
{{devis.lignes}}

{{devis.bloc_totaux}}

{{fiscalite_snapshot.bloc_mention_fiscale}}

## Conditions

Conditions de paiement proposées : {{devis.echeancier_resume}}.  
Mode de paiement : {{devis.mode_paiement}}.  
Catégorie d’opération : prestation de services.

Les conditions définitives (prix, échéances, accueil) sont fixées par le contrat de cession du droit d’exploitation du spectacle.

## Acceptation

Pour accepter ce devis, merci de le renvoyer daté et signé, précédé de la mention manuscrite « Bon pour accord ».

| Pour le client |
|---|
| Nom et qualité : |
| Date : |
| « Bon pour accord » et signature : |

---

{{pied_de_page}}
