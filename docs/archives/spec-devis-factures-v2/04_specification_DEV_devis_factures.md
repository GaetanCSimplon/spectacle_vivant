# Bòrd Pro — Devis et factures : spécification pour le développement

Version 2 — 13/11/2026 — remplace `04_modeles_devis_facture.md` (v1)
Fichiers liés : `05_modele_devis.md`, `06_modele_facture.md`, spec contrat `03` (décisions D1 à D9)

---

## 0. Décisions validées par Jeff (13/11/2026)

| # | Sujet | Décision |
|---|---|---|
| DF1 | Coopérative d'activité (CAE) | **Non.** On retire le bloc CAE et ses champs. Un artiste en CAE utilise les documents de sa coopérative. |
| DF2 | Pénalités de retard | **3 fois le taux d'intérêt légal** + indemnité forfaitaire de 40 € (client professionnel uniquement). Pas d'escompte. |
| DF3 | Devis signé | Seule la mention **« Bon pour accord »** est demandée (avec nom, qualité, date, signature). Pas de « lu et approuvé », pas de cachet obligatoire. |
| DF4 | Unités | **Liste fermée**, reliée aux éléments de l'appli (type de ligne → unités autorisées). Pas de saisie libre. |

---

## 1. Principes (rappel des règles du projet)

1. Montants en `Decimal`, arrondis au centime **par ligne**, puis totaux = somme des lignes arrondies (F-58).
2. **Prévu ≠ facturé ≠ encaissé** : trois notions séparées (F-57). Un devis ne crée pas de recette ; une facture crée du « facturé » ; un paiement crée de l'« encaissé ».
3. **Facture émise = figée.** Aucune modification après émission. Toute correction passe par un **avoir** (facture négative qui référence la facture d'origine).
4. **Instantané (snapshot) à l'émission** : identité du producteur, de l'organisateur, régime de TVA, mentions légales sont copiés dans le document au moment de l'émission. Un changement ultérieur dans « Bòrd / Informations » ne modifie pas les documents déjà émis.
5. Isolation : `Quote`, `Invoice`, `InvoiceLine` héritent de `TenantOwnedModel` ; vues avec `TenantScopedMixin`.
6. Vocabulaire code : `Tenant`, `Promoter`, `Venue`, `Show`, `Gig`, `Contract`, `Quote`, `Invoice`. Jamais « Client » ni « Structure » dans le code. À l'écran, sur le PDF, la colonne s'appelle « Client » (c'est le terme attendu sur une facture).
7. Interface pour artistes, pas pour administrateurs : 1 bouton principal par écran (corail), libellés simples (« Créer le devis », « Émettre la facture »).

---

## 2. Vocabulaire écran ↔ code

| Écran / PDF | Code | Remarque |
|---|---|---|
| Émetteur | `Tenant` (producteur) | Données de « Bòrd / Informations » |
| Client | `Promoter` (organisateur) | Adresse **de facturation** |
| Spectacle | `Show` | |
| Date / Représentation | `Gig` | Date, lieu, nb de représentations |
| Lieu | `Venue` | |
| Devis | `Quote` | |
| Facture / Facture d'acompte / Facture de solde / Avoir | `Invoice` + `type` | |
| N° de licence | `Tenant.licence_numero` | On garde le terme métier |

---

## 3. Modèle de données

### 3.1 `Quote` (devis)

| Champ | Type | Règle |
|---|---|---|
| `numero` | char | Séquence par tenant : `D-AAAA-NNN`, sans trou, attribuée à l'envoi (brouillon = pas de numéro) |
| `gig` | FK Gig | Obligatoire |
| `promoter` | FK Promoter | Obligatoire |
| `objet` | char | Pré-rempli : « Cession du droit d'exploitation du spectacle {titre} » |
| `date_emission` | date | |
| `date_validite` | date | Défaut : émission + 30 jours (paramétrable dans Bòrd / Informations) |
| `statut` | enum | `brouillon`, `envoye`, `accepte`, `refuse`, `expire` |
| `echeancier` | JSON | Ex. `[{"libelle":"Acompte","pourcentage":30},{"libelle":"Solde","pourcentage":70}]` — **pas de 30 % par défaut** (D-contrat) |
| `mode_paiement` | enum | `virement`, `cheque`, `especes`, `autre` |
| `fiscalite_snapshot` | JSON | Rempli à l'envoi (voir § 6) |
| `accepte_le` | date, null | Rempli quand l'artiste coche « Devis signé reçu » |
| `fichier_signe` | FileField, null | Scan du devis « Bon pour accord » |

### 3.2 `Invoice` (facture)

| Champ | Type | Règle |
|---|---|---|
| `numero` | char | Séquence **unique et continue** par tenant : `F-AAAA-NNN`, attribuée à l'émission. Avoirs dans la même séquence. |
| `type` | enum | `facture`, `acompte`, `solde`, `avoir` |
| `quote` | FK Quote, null | |
| `contract` | FK Contract, null | |
| `gig`, `promoter` | FK | Obligatoires |
| `facture_origine` | FK Invoice, null | Obligatoire si `type = avoir` |
| `date_emission`, `date_echeance` | date | Échéance défaut : émission + 30 jours, plafonnée à 60 jours |
| `numero_bon_de_commande` | char, null | Si l'organisateur en fournit un (collectivités) |
| `statut` | enum | `brouillon`, `emise`, `payee_partiellement`, `payee`, `annulee_par_avoir` |
| `fiscalite_snapshot` | JSON | Rempli à l'émission |
| `pdf` | FileField | Généré une fois à l'émission, jamais régénéré |

### 3.3 `QuoteLine` / `InvoiceLine`

| Champ | Type | Règle |
|---|---|---|
| `ordre` | int | |
| `type_ligne` | enum | Voir § 4 |
| `designation` | char | Pré-remplie selon le type, modifiable |
| `quantite` | Decimal(10,2) | > 0 (sauf ligne « acompte déduit ») |
| `unite` | enum | **Liste fermée**, filtrée par `type_ligne` (§ 4) |
| `prix_unitaire_ht` | Decimal(12,2) | |
| `taux_tva` | Decimal(4,2), null | null si non assujetti (voir § 6) |
| `montant_ht`, `montant_tva`, `montant_ttc` | Decimal(12,2) | Calculés, arrondis à la ligne |

### 3.4 Champs à ajouter ou vérifier

| Modèle | Champ | Raison |
|---|---|---|
| `Promoter` | `siren` (9 chiffres) | Mention obligatoire facture électronique (§ 7) |
| `Promoter` | `numero_tva` | Si assujetti |
| `Promoter` | `adresse_facturation` (si ≠ adresse principale) | |
| `Promoter` | `est_particulier` (bool) | Déclenche médiation et masque pénalités pro (§ 5.6) |
| `Tenant` | `tva_sur_debits` (bool) | Mention « option pour le paiement de la TVA d'après les débits » |
| `Tenant` | `delai_validite_devis`, `delai_paiement` (int jours) | |
| `Tenant` | `iban`, `bic` | Affichés en pied de page si virement. **Jamais en dur dans un modèle.** |

À **supprimer** de la v1 : tous les champs `cae_*` (DF1).

---

## 4. Lignes : types et unités (liste fermée — DF4)

Chaque type de ligne est relié à un élément déjà présent dans l'appli. L'utilisateur choisit le type, l'unité se limite à la liste autorisée.

| `type_ligne` | Libellé écran | Source dans l'appli | Unités autorisées | Quantité par défaut |
|---|---|---|---|---|
| `cession` | Cession du spectacle | Contrat → prix de cession ; Date → nb de représentations | `representation`, `forfait` | `gig.nombre_representations` |
| `transport` | Transport / défraiement | Budget de la date → catégorie Transport | `km`, `forfait` | 1 |
| `hebergement` | Hébergement | Contrat → accueil (si à la charge du producteur et refacturé) | `nuit` | nb personnes × nb nuits |
| `repas` | Repas | Contrat → accueil / défraiements | `repas` | nb personnes × nb repas |
| `technique` | Technique / régie | Budget → catégorie Technique ; fiche technique | `jour`, `heure`, `forfait` | 1 |
| `communication` | Communication | Budget → catégorie Communication | `forfait` | 1 |
| `autre` | Autre | Budget → catégorie Autres | `forfait` | 1 |
| `remise` | Remise | — | `pourcentage`, `forfait` | 1 (montant négatif) |
| `acompte_deduit` | Acompte déjà facturé | Factures d'acompte liées | `forfait` | 1 (montant négatif, facture de solde seulement, ajoutée automatiquement) |

Libellés des unités sur le PDF : représentation(s), forfait, km, nuit(s), repas, jour(s), heure(s), %.

Règles :
- Une ligne `cession` est **obligatoire** sur un devis de cession et toujours en première position.
- `remise` en `pourcentage` s'applique au sous-total HT des lignes qui la précèdent.
- Pas de ligne « cachet » ou « salaire » : les salaires ne se facturent pas, ils sont inclus dans le prix de cession (la Navette sociale s'en occupe à part).

---

## 5. Variables des modèles et génération des blocs

Les modèles `05` et `06` utilisent des variables simples (valeur directe) et des **blocs** (texte généré par le code, vide si sans objet → la ligne disparaît du PDF).

### 5.1 Variables simples

| Variable | Source |
|---|---|
| `producteur.*` | Snapshot `Tenant` (Bòrd / Informations) |
| `producteur.mention_licence_ou_dispense` | `licence_numero` sinon « Non soumis (moins de 7 représentations par an) » si l'artiste l'a déclaré |
| `organisateur.*` | Snapshot `Promoter` |
| `organisateur.mention_siren` | « SIREN 123 456 789 » ou vide si particulier |
| `organisateur.mention_numero_tva` | « N° TVA FR… » ou vide |
| `gig.*` | `Gig` + `Show` + `Venue` |
| `devis.echeancier_resume` | Ex. « 30 % à la signature, 70 % le jour de la représentation » |
| `facture.type_libelle` | Facture / Facture d'acompte / Facture de solde / Avoir |
| `facture.mention_devis` | « Devis n° D-2026-012 accepté le 03/10/2026 » ou vide |
| `facture.mention_contrat` | « Contrat de cession n° C-2026-008 du 05/10/2026 » ou vide |
| `facture.mention_bon_de_commande` | « Bon de commande n° … » ou vide |
| `facture.total_a_payer` | Total TTC − acomptes déjà encaissés (jamais négatif sauf avoir) |

### 5.2 `lignes` (devis et facture)

Une ligne de tableau Markdown par `QuoteLine` / `InvoiceLine` :
`| 1 | Cession du spectacle « X » | 2 | représentations | 1 500,00 | 3 000,00 | 5,5 % | 3 165,00 |`
- Montants au format français (espace fine pour les milliers, virgule décimale), police IBM Plex Mono.
- Si non assujetti : colonnes TVA et TTC **masquées** (pas de « 0 % »).

### 5.3 `bloc_totaux`

Assujetti :
```
Total HT ........ 3 000,00 €
TVA 5,5 % ....... 165,00 €      (une ligne par taux utilisé)
Total TTC ....... 3 165,00 €
```
Non assujetti : une seule ligne `Total ....... 3 000,00 €`.

### 5.4 `fiscalite_snapshot.bloc_mention_fiscale`

| Profil fiscal du producteur | Texte |
|---|---|
| Assujetti | vide (les taux figurent dans le tableau) |
| Franchise en base | « TVA non applicable, article 293 B du CGI. » |
| Association non lucrative exonérée | « TVA non applicable, article 261-7-1° b du CGI. » |
| Autre exonération | Texte saisi dans Bòrd / Informations — **à valider par le juriste** |

`mention_numero_tva_producteur` : « N° TVA intracommunautaire : FR… » si assujetti, sinon vide.
`mention_option_debits` : « Option pour le paiement de la TVA d'après les débits. » si `tva_sur_debits`, sinon vide.

### 5.5 `facture.bloc_pieces_precedentes` et `bloc_recapitulatif_date`

- **Facture de solde** : liste des factures d'acompte (« Facture d'acompte F-2026-031 du 05/10/2026 : 900,00 € ») + ligne `acompte_deduit` automatique dans le tableau.
- **Avoir** : « Avoir sur la facture n° F-2026-040 du 12/11/2026 » (obligatoire).
- `bloc_recapitulatif_date` (facture de solde uniquement) : petit tableau « Prix total convenu / Déjà facturé / Reste à payer ». Vide sinon.

### 5.6 `facture.bloc_conditions_retard` (DF2)

| Client | Texte |
|---|---|
| Professionnel (`est_particulier = False`) | « En cas de retard de paiement, des pénalités égales à trois fois le taux d'intérêt légal sont exigibles, ainsi qu'une indemnité forfaitaire pour frais de recouvrement de 40 €. Aucun escompte n'est accordé pour paiement anticipé. » |
| Particulier | vide (les pénalités pro ne s'appliquent pas) ; la mention médiation va dans le pied de page |

### 5.7 `pied_de_page`

- Dénomination, forme juridique, capital (si société), adresse, SIRET, code APE, RCS (si inscrit).
- Si virement : IBAN / BIC du tenant.
- Si client particulier : « En cas de litige, vous pouvez recourir gratuitement au médiateur de la consommation : {nom et site du médiateur} » — champ à remplir dans Bòrd / Informations ; si vide, alerte Radar.
- « Document généré avec Bòrd Pro » (petit, facultatif).

---

## 6. Calculs et contrôles

### 6.1 Calculs
- `montant_ht = arrondi(quantite × prix_unitaire_ht, 2)`
- `montant_tva = arrondi(montant_ht × taux / 100, 2)`
- Totaux = sommes des lignes. Pas de recalcul global de la TVA.
- Facture d'acompte : une ligne « Acompte de X % sur la cession du spectacle … » (unité `forfait`).

### 6.2 Niveaux de blocage (même logique que le contrat)

| Contrôle | Niveau |
|---|---|
| SIRET producteur manquant | BLOCAGE |
| Profil fiscal producteur non renseigné | BLOCAGE |
| Aucune ligne `cession` sur un devis de cession | BLOCAGE |
| Adresse de facturation organisateur manquante | BLOCAGE (facture) / AVERTISSEMENT (devis) |
| SIREN organisateur manquant (client pro) | AVERTISSEMENT jusqu'au 31/08/2027, puis BLOCAGE |
| Échéance > 60 jours | BLOCAGE |
| Avoir sans facture d'origine | BLOCAGE |
| N° de licence manquant (et pas de dispense déclarée) | AVERTISSEMENT |
| Médiateur non renseigné et client particulier | AVERTISSEMENT |
| Total facturé > prix du contrat | CONFIRMATION_REQUISE |
| Devis expiré au moment de facturer | CONFIRMATION_REQUISE |

Les messages s'affichent dans le bandeau Radar, en langage simple (« Il manque le SIRET de ta structure : ajoute-le dans Bòrd / Informations »).

### 6.3 Parcours utilisateur (Fiche date → onglet Contrat)
1. « Créer le devis » : lignes pré-remplies depuis le contrat et le budget de la date.
2. « Envoyer » : numéro + snapshot + PDF + mail (modèle de mail bp9).
3. « Devis signé reçu » : case + dépôt du scan → statut `accepte`.
4. « Facturer l'acompte » / « Facturer le solde » : générés depuis l'échéancier.
5. « Marquer comme payé » : crée l'encaissé (montant, date).

Cible : 3 clics maximum entre la fiche date et l'envoi d'une facture.

---

## 7. Facture électronique — à préparer dès maintenant

**Faits vérifiés** (sources ci-dessous) :
- Depuis le 01/09/2026, toutes les entreprises doivent pouvoir **recevoir** des factures électroniques.
- **Émission** obligatoire pour les PME et micro-entreprises au **01/09/2027** (les grandes et moyennes entreprises dès le 01/09/2026).
- Nouvelles mentions : SIREN du client, adresse de livraison si différente, catégorie d'opération (biens / services / mixte), option TVA sur les débits.

**Ce que fait Bòrd Pro en v1** : affiche ces mentions sur le PDF (déjà dans les modèles 05/06) et stocke les données structurées.

**Hypothèse à confirmer** : en 2027, Bòrd Pro devra transmettre au format Factur-X via une plateforme agréée (partenariat) plutôt que de devenir lui-même plateforme. À arbitrer avant mi-2027.

**Concerne aussi les associations** assujetties à la TVA ; une association non assujettie n'est pas concernée par l'émission (à faire confirmer par le juriste).

---

## 8. Hors périmètre v1

- Relances automatiques d'impayés (prévu dans Radar, plus tard).
- Signature électronique du devis (le scan suffit en v1).
- Multi-devises.
- Export comptable (FEC) : à spécifier à part.

---

## 9. Points à faire valider par le juriste (tâche bp14)

1. Mention d'exonération pour les associations (§ 5.4).
2. Formulation « Non soumis » pour les artistes sans licence (§ 5.1).
3. Mention médiation pour les clients particuliers.
4. Calendrier facture électronique pour les associations.

---

## Sources

- Mentions obligatoires sur facture : Code de commerce, art. L441-9 ; CGI annexe II, art. 242 nonies A.
- Pénalités (minimum 3 × taux d'intérêt légal) et indemnité de 40 € : Code de commerce, art. L441-10 et D441-5.
- Franchise en base de TVA : CGI, art. 293 B.
- Médiation de la consommation : Code de la consommation, art. L612-1 et R111-1.
- Facture électronique (calendrier et nouvelles mentions) : impots.gouv.fr — « Facturation électronique entre entreprises » ; economie.gouv.fr — « Facturation électronique : obligations et calendrier ».
- Licence d'entrepreneur de spectacles (seuil de 6 représentations par an) : Code du travail, art. L7122-3 et L7122-19.
