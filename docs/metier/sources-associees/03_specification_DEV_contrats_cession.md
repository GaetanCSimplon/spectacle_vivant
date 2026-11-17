# Bòrd Pro — Spécification DEV des contrats de cession de spectacle

Version consolidée — 13 novembre 2026 (v2, cadrage avec l'existant ajouté)
Statut : spécification fonctionnelle de travail à valider avant mise en production.

## 0. Cadrage avec l'existant (à lire en premier)

Cette section relie la spécification au code actuel de Bòrd Pro (CLAUDE.md, lexique § 5). En cas de doute sur un nom, elle prime sur les noms de variables proposés dans les modèles.

### 0.1. Décisions du 13/11/2026

| # | Décision | Conséquence pour le code |
|---|---|---|
| D1 | Les **4 modèles** de contrat de cession livrés le 13/10 sont **remplacés** par les 2 modèles de ce dossier (avec TVA / sans TVA). | Plus de choix de modèle par l'utilisateur : la variante est choisie par le régime TVA de la structure (§ 2). Les contrats déjà signés gardent leur PDF figé. Les brouillons non envoyés sont régénérés avec le nouveau modèle. |
| D2 | L'organisateur peut être un **particulier** (forme juridique « Particulier »). | Identification adaptée : voir § 11.2. Seul cas d'organisateur sans SIRET accepté en V1. |
| D3 | La **fiche d'accueil** (annexe 2) est **générée par Bòrd Pro** à partir des données de la date (effectif, repas, hébergement, transport, horaires, contacts). | Pas de fichier à téléverser pour l'annexe 2. Elle mentionne aussi l'absence de prise en charge. La fiche technique (annexe 1) est celle déjà déposée sur la fiche spectacle (`Show`). |
| D4 | Les informations souvent inconnues à la signature **ne bloquent plus** : heure d'arrivée, installation et balances, jauge, contact opérationnel sur place. | Niveau AVERTISSEMENT. Si vide, le contrat affiche « À préciser dans la fiche d'accueil ». |
| D5 | On garde le libellé métier **« N° de licence »**. | Pas de renommage en « récépissé » à l'écran. Dans ce document, « licence » désigne le n° de licence d'entrepreneur de spectacles ou la situation de dispense. |
| D6 | On garde 4 champs actuels : **nombre d'invitations, nombre d'exemplaires, prix des places, nombre de représentations**. | Intégrés aux deux modèles (article 1 et signatures). |
| D7 | Les autres champs actuels de « Compléter le contrat » non repris sont **supprimés** : délai de retour du contrat signé, conditions particulières, ville du tribunal compétent. | Le litige relève du droit commun (article 10). Champs à retirer des formulaires et des modèles. |

### 0.2. Vocabulaire : correspondance avec le code

| Dans cette spécification | Dans le code | À l'écran |
|---|---|---|
| Producteur, structure productrice | `Tenant` | Ma structure |
| Informations de la structure | `Tenant` (infos légales et fiscales) | Informations de la structure — `/bord/informations/` |
| Organisateur | `Promoter` | Organisateur |
| Lieu | `Venue` | Lieu |
| Spectacle, fiche artiste | `Show` | Spectacle |
| Représentation, date | `Gig` | Date |
| Fiche « Contrat » | `Contract` lié au `Gig` | Volet C · Contrats de la date |
| Équipe en tournée | équipe de la date (`GigMember`) | Social de la date |

Règle CLAUDE.md : ne jamais écrire `Client` ni « Structure » dans le code pour désigner l'organisateur.

### 0.3. Champs existants : renommer, compléter, ne pas dupliquer

| Champ actuel | Devient | Action |
|---|---|---|
| « Configuration » du contrat (texte libre) | « Intérieur / plein air » (choix) | Renommer. Ne pas confondre avec la configuration du lieu (assis, debout…) qui reste sur `Venue`. |
| « N° SACEM » (fiche spectacle et contrat) | « N° de programme type SACEM » | Renommer le champ existant, ne pas en créer un second (§ 5). |
| « Régime de TVA » (Assujetti / Franchise en base / Non assujetti) et « Taux de TVA » | Champs fiscaux du § 2.2 | Compléter les champs existants, ne pas créer un second régime. |
| « Acompte (%) » prérempli à 30 % | Acompte oui / non, puis montant et échéance | Retirer la valeur par défaut (§ 8 : pas d'acompte universel). |
| « Repas / Hébergement pris en charge » (texte libre) | Choix explicite + effectif, dates, modalités (§ 14) | Remplacer le texte libre. |
| « Nom du signataire » / « Qualité du signataire » | Signataire confirmé dans la fiche Contrat (§ 3.1) | Garder, ajouter la confirmation d'habilitation. |
| Montants | `Decimal`, au centime (F-58) | « Arrondi monétaire » = arrondi au centime. |

### 0.4. Décisions validées le 13/11/2026 (suite)

| # | Décision | Conséquence pour le code |
|---|---|---|
| D8 | La **décision Q8 du 01/10/2026** (pas de mention 293 B dans le contrat) est **annulée**. | Le modèle sans TVA affiche la mention d'absence de TVA et son fondement légal, repris d'« Informations de la structure » (§ 2.2). |
| D9 | **Phasage** : V1 = un PDF unique (contrat + fiche technique + fiche d'accueil) à télécharger, suivi de signature manuel (« Contrat envoyé », « PDF signé déposé ») ; V2 = envoi par e-mail avec les trois pièces (§ 6.2), après branchement de Brevo ; V3 = signature électronique (§ 6.3), hors MVP selon CLAUDE.md. | Les §§ 6.2, 6.3 et 18 ne sont pas à coder en V1. Les règles de version, d'immuabilité et de statut « complet signé » s'appliquent dès la V1. |

### 0.5. Reste à faire valider

- [ ] **Licence d'un organisateur particulier** : mention à faire valider par un juriste du spectacle vivant (§ 11.2), comme l'ensemble des modèles avant diffusion publique (§ 21).

Ce document remplace la première version du document 03 et intègre les champs obligatoires, les règles de blocage et le parcours de validation. Il accompagne les deux modèles Markdown : contrat avec TVA et contrat sans TVA.

## 1. Périmètre et architecture

Périmètre standard : une représentation de spectacle vivant musical en France, producteur et organisateur établis en France, rémunération forfaitaire. Coréalisation, contrats de travail, international et autoliquidation sont hors périmètre. Un organisateur particulier est dans le périmètre (§ 11.2). Une opération gratuite entre les parties nécessite un autre parcours ; ne pas la confondre avec une représentation gratuite pour le public mais vendue à l’organisateur.

Un acheteur public nécessite la vérification du circuit de commande et de paiement ; le contrat ne remplace pas les documents de commande exigés par cet acheteur.

Implémenter un socle de clauses commun et deux variantes fiscales de l’article 5. Ne pas maintenir deux versions divergentes des clauses communes.

Les variables entre doubles accolades dans les modèles sont des noms proposés à mapper sur les champs existants, pas la description du schéma actuel de l’application. Aucun commentaire technique ou champ non remplacé ne doit apparaître dans une version définitive.

La présente liste définit les obligations fonctionnelles du produit. Elle ne signifie pas que l’absence de chaque champ entraîne, à elle seule, la nullité juridique d’un contrat.

## 2. Choix du modèle depuis « Informations de la structure » (/bord/informations/)

### 2.1. Structure de référence

Le profil fiscal utilisé est celui du PRODUCTEUR qui facture la cession. Le régime TVA de l’organisateur ne choisit jamais le modèle.

La saisie du réglage TVA dans « Informations de la structure » déclenche automatiquement le choix du modèle. Les taux, mentions fiscales et articles de référence proviennent également de cette fiche : ne pas les coder en dur dans le modèle.

Libellé recommandé : « Facturation de la TVA sur les cessions : oui / non ». Ce réglage complète le champ existant « Régime de TVA » (§ 0.3) : ne pas créer de second régime. Le mot « assujetti » seul est insuffisant : une structure en franchise en base peut être assujettie sans collecter de TVA. Si l’interface conserve « assujettissement », documenter cette distinction et stocker le régime détaillé.

### 2.2. Champs fiscaux proposés

| Champ | Usage |
|---|---|
| structure.fiscalite.facture_tva_cessions | Booléen obligatoire ; routage vers le modèle |
| structure.fiscalite.regime | TVA facturée / franchise en base / exonération / hors champ ; régime confirmé |
| structure.fiscalite.taux_tva_cession | Taux applicable à la cession ; requis avec TVA |
| structure.fiscalite.mention_tva | Mention fiscale applicable avec TVA |
| structure.fiscalite.reference_legale_tva | Référence applicable, distincte ou intégrée à la mention |
| structure.fiscalite.numero_tva_intracommunautaire | Identification fiscale du producteur lorsque requise |
| structure.fiscalite.mention_absence_tva | Mention exacte applicable sans TVA |
| structure.fiscalite.reference_legale_absence_tva | Fondement exact ; obligatoire sans TVA |
| structure.fiscalite.date_effet | Date d’effet du régime enregistré |

Ne pas appliquer automatiquement l’article 293 B du CGI à toute absence de TVA : il correspond à la franchise en base, pas à toutes les exonérations ou situations hors champ. Ne pas afficher l’absence de TVA comme un taux à 0 %.

Le taux de cession ne doit pas être confondu avec le taux de billetterie. Si plusieurs profils ou taux sont nécessaires, prévoir leur sélection confirmée pour l’opération, sinon bloquer ce cas en V1. Un booléen ne valide pas à lui seul la fiscalité d’une opération.

### 2.3. Génération et instantané fiscal

```text
charger la structure productrice
vérifier que son profil fiscal est complet, cohérent et adapté à l’opération
si facture_tva_cessions = oui :
    sélectionner le modèle avec TVA
    reprendre taux, mention et référence des paramètres
    montant_tva = arrondi au centime, en Decimal (F-58), de prix_cession_ht × taux / 100
    prix_cession_ttc = prix_cession_ht + montant_tva
sinon :
    sélectionner le modèle sans TVA
    reprendre mention et référence d’absence de TVA des paramètres
    utiliser le prix net de TVA, sans taux 0 %
créer un instantané fiscal daté lié à la version du contrat
```

Les variables fiscalite_snapshot.* reprennent les paramètres retenus à la génération. Une modification ultérieure des paramètres ne modifie jamais un contrat envoyé ou signé. Conserver l’historique ; toute correction suit une nouvelle version ou un avenant selon le stade du dossier.

Alerter si un changement de régime est annoncé ou si la date de représentation dépasse la période de validité connue des paramètres.

## 3. Provenance des données

### 3.1. Informations de la structure du producteur (/bord/informations/)

Identité juridique, forme, adresse, SIRET, n° de licence et catégories, informations de validité, coordonnées, signataire habituel et qualité, fiscalité, RIB.

Le signataire doit être confirmé dans la fiche « Contrat ». Il peut être remplacé par une personne habilitée. Ses données doivent être identiques dans l’en-tête et le bloc de signature.

### 3.2. Fiche organisateur

Identité juridique, nature ou forme (dont « Particulier »), adresse, SIRET sauf particulier, n° de licence ou dispense, signataire habilité et qualité, contact administratif, informations de commande et de facturation spécifiques, notamment publiques.

Ne pas assimiler le nom du festival à la structure organisatrice. Le contact administratif n’est pas nécessairement le signataire.

### 3.3. Fiche « Contrat »

Source impérative pour les conditions propres à la représentation :

- artiste/groupe, titre, date, nombre de représentations, lieu, intérieur/plein air, durée, horaires, jauge, accès gratuit/payant et prix des places ;
- nombre d'invitations réservées au producteur et nombre d'exemplaires du contrat ;
- nombre total de personnes en tournée ;
- restauration : prise en charge, personnes, repas, dates et modalités ;
- hébergement : prise en charge, personnes, nuitées, dates et modalités ;
- transport et frais convenus ;
- prix, échéancier et facturation ;
- plein air, repli et procédure de décision ;
- référence éventuelle du programme type SACEM ;
- contacts opérationnels.

Ne pas reprendre automatiquement les effectifs ou conditions habituelles de la fiche spectacle (`Show`) à la place des données de la fiche « Contrat ». Une pré-saisie peut être proposée, mais doit être confirmée pour cette représentation.

Les variables contrat.restauration_resume, contrat.hebergement_resume et contrat.transport_resume sont des résumés lisibles produits depuis ces données, sans inventer d’engagement.

Exemple : « À la charge de l’organisateur : 4 personnes, 1 repas le 23/07/2027 ; modalités précisées en annexe ». En l’absence de prise en charge : « Aucun hébergement à la charge de l’organisateur ». Ne pas laisser ces rubriques vides.

## 4. Personnel

L’organisateur assume ses salariés. Le producteur assume l’équipe en tournée placée sous sa responsabilité et ses obligations d’employeur envers ses salariés.

Ne pas attribuer automatiquement un technicien son ou une chargée de production à l’une des parties sur la seule base de son métier. Prendre en compte la partie qui engage la personne et l’organisation convenue.

Le nombre de personnes en tournée comprend toutes les personnes accompagnant le spectacle, pas seulement les artistes. Les clauses ne doivent pas laisser entendre qu’elles écartent les obligations légales de vigilance ou de coordination.

## 5. SACEM

Le champ correspond exclusivement au « N° de programme type SACEM », déclaré par l’artiste. Ne pas le nommer simplement « numéro SACEM » ni le confondre avec un numéro de sociétaire, d’œuvre ou d’autorisation de manifestation.

Si renseigné, générer :

> N° de programme type SACEM déclaré par l’artiste : [valeur].

Sinon, générer :

> Programme des œuvres interprétées à transmettre par le producteur pour les démarches de déclaration.

Ce champ n’est pas bloquant. Ne jamais inventer de numéro. Il ne choisit ni le régime TVA ni l’assujettissement à la taxe CNM et ne dispense pas de déclarer la manifestation.

## 6. Annexes et parcours de signature

### 6.1. Deux annexes obligatoires

Le contrat reste simple sur la technique et l’accueil. Les détails sont portés dans :

1. Annexe 1 : fiche technique.
2. Annexe 2 : fiche d’accueil.

Ces documents font partie intégrante du contrat et doivent être signés par les deux parties.

Provenance (décision D3) : la fiche technique est le fichier déposé sur la fiche spectacle (`Show`) ; la fiche d'accueil est générée par Bòrd Pro à partir des données de la date (effectif, restauration, hébergement, transport, horaires, contacts sur place). Les informations non encore connues y figurent « à préciser ».

Stocker pour chaque annexe : identifiant, titre, date/version, fichier, empreinte si possible et statut de signature. Associer les versions exactes à chaque version du contrat.

Une fiche d’accueil reste requise même sans repas ni nuitées pris en charge ; elle indique cette absence de prise en charge.

Vérifier sa cohérence avec la fiche « Contrat » : effectif, restauration et hébergement. Ne pas modifier automatiquement une annexe déjà signée : une modification nécessite une nouvelle version et une nouvelle acceptation.

### 6.2. Envoi par e-mail

Joindre au même e-mail : le contrat, la fiche technique et la fiche d’accueil correspondant à la version du contrat.

Le Markdown constitue le format source ; l’application peut produire un PDF pour l’envoi. Les annexes doivent être réellement jointes, pas seulement accessibles par lien ou mentionnées « sur demande ».

Une limite de taille ou une pièce inaccessible doit provoquer une erreur explicite, jamais l’envoi silencieux d’un dossier incomplet.

### 6.3. Signature

En signature électronique, inclure les trois documents dans le dossier et recueillir l’acceptation explicite de chacun. En signature manuscrite, demander leur retour signé.

Les annexes n’ont pas à être déjà signées pour envoyer le dossier à signer. En revanche, le statut « complet signé » exige la signature du contrat et des deux annexes par les deux parties. Conserver les versions et preuves de signature.

## 7. Plein air

Si intérieur, générer contrat.clause_plein_air :

> Sans objet : représentation prévue en intérieur.

Si plein air, exiger : repli prévu ou absence expressément acceptée, référents des deux parties, procédure de maintien/report/arrêt et conditions financières applicables.

Bloc minimal :

> Les modalités de repli convenues sont les suivantes : [modalités ou absence de repli]. Les parties coordonnent toute décision de maintien, de report ou d’arrêt de la représentation dans les conditions suivantes : [procédure et référents], sous réserve des décisions des autorités compétentes. Aucune annulation pour intempéries n’est automatiquement qualifiée de force majeure : les conditions légales doivent être réunies. [Conditions financières spécifiques ou texte par défaut.]

Texte financier par défaut :

> À défaut de stipulation financière spécifique, les dispositions du présent article relatives à l’annulation et à la force majeure s’appliquent.

L’absence de repli n’est pas à elle seule bloquante ; l’absence d’information sur ce point l’est.

Ne pas générer automatiquement une indemnité de 100 %. Une option négociée de garantie météo nécessite une clause validée : déclencheurs, calcul ou montant, acomptes, frais, articulation avec la force majeure. Un simple pourcentage ne suffit pas. Ne jamais imposer le maintien au mépris de la sécurité ou d’une décision des autorités.

## 8. Prix, échéances et facturation

Les modèles supposent un prix principal relevant d’un seul régime fiscal. Les frais supplémentaires doivent être décrits, chiffrés ou déterminables et expressément acceptés. Aucune ligne « à définir » dans une version définitive.

Si le producteur facture des frais supplémentaires, intégrer leur fiscalité et leur montant au récapitulatif global ou prévoir une facturation séparée clairement convenue. Bloquer en V1 les cas multi-taux non gérés.

Exiger au minimum une échéance du règlement total. Si acompte : préciser montant et échéance de l’acompte, montant et échéance du solde. Échéancier en TTC avec TVA, en net de TVA sans TVA.

Contrôler que le total des échéances correspond au total à régler. Distinguer les prises en charge payées directement par l’organisateur des sommes dues au producteur.

Ne pas préremplir un acompte ou une pénalité universelle. Les circuits de paiement des acheteurs publics et privés doivent être traités selon le cas. Les mentions des factures relèvent du module facturation approprié.

Le RIB n’est pas bloquant pour générer le contrat si sa remise séparée est prévue. Il doit être disponible avant une demande de virement lorsque le destinataire ne dispose pas déjà de coordonnées vérifiées. Toute modification bancaire nécessite une vérification adaptée.

## 9. Taxe CNM

Conserver la clause dans les deux variantes : absence de TVA ne signifie pas absence de taxe CNM.

Pour un spectacle entrant dans le champ de la taxe :

- représentation payante : redevable détenteur de la billetterie pour le compte duquel les recettes sont encaissées ;
- représentation gratuite avec cession : redevable producteur qui facture la cession.

En V1, aucun transfert automatique de déclaration au diffuseur. Ne pas appliquer la taxe indistinctement à tous les genres : prévoir une qualification ou confirmation lorsque nécessaire.

Pour les représentations gratuites, ne pas réduire automatiquement l’assiette au seul salaire artistique ; les sommes facturées au titre de la cession et les frais concernés doivent être examinés dans le module approprié. Aucun calcul de taxe CNM n’est affiché dans le contrat standard. Ne pas ajouter de supplément de refacturation non convenu.

## 10. Niveaux de validation

| Niveau | Effet |
|---|---|
| BLOCAGE | Empêche la génération définitive tant que l’anomalie subsiste |
| CONFIRMATION_REQUISE | Exige une validation explicite et enregistrée de l’utilisateur |
| AVERTISSEMENT | Signale une information à compléter ou vérifier sans interdire la génération |

L’enregistrement d’un dossier incomplet reste autorisé. Une prévisualisation peut être produite avec la mention « BROUILLON — INFORMATIONS INCOMPLÈTES — NON DESTINÉ À LA SIGNATURE » et le signalement des champs manquants.

La génération définitive exige l’absence de blocage et l’enregistrement de toutes les confirmations requises.

## 11. Identification des parties : champs obligatoires

### 11.1. Producteur

| Renseignement | Validation | Niveau |
|---|---|---|
| Dénomination juridique ou nom complet de l’entrepreneur individuel | Le seul nom artistique/commercial ne suffit pas | BLOCAGE |
| Forme juridique | Inclure entreprise individuelle lorsque pertinent | BLOCAGE |
| SIRET | Requis dans le périmètre standard France ; 14 chiffres et contrôle de cohérence | BLOCAGE |
| Adresse | Voie ou lieu-dit, code postal, commune, pays ; compléments facultatifs | BLOCAGE |
| Nom et prénom du signataire | Obligatoires | BLOCAGE |
| Qualité du signataire | Obligatoire | BLOCAGE |
| Habilitation du signataire | Confirmation utilisateur obligatoire | BLOCAGE tant que non confirmée |
| N° de licence ou dispense | Sélection et informations requises | BLOCAGE |
| Contact de production | Nom et e-mail obligatoires | BLOCAGE |
| Téléphone | Recommandé | AVERTISSEMENT |

### 11.2. Organisateur

| Renseignement | Validation | Niveau |
|---|---|---|
| Dénomination juridique | Le seul nom d’événement/festival ne suffit pas ; particulier : nom et prénom | BLOCAGE |
| Forme ou nature juridique | Association, société, collectivité, établissement, particulier… | BLOCAGE |
| SIRET | Requis dans le périmètre standard France, sauf particulier | BLOCAGE |
| Adresse | Voie ou lieu-dit, code postal, commune, pays | BLOCAGE |
| Nom et prénom du signataire | Obligatoires | BLOCAGE |
| Qualité du signataire | Obligatoire | BLOCAGE |
| Habilitation du signataire | Confirmation utilisateur obligatoire | BLOCAGE tant que non confirmée |
| N° de licence ou dispense | Sélection et informations requises (particulier : voir ci-dessous) | BLOCAGE |
| Contact administratif | Nom et e-mail obligatoires | BLOCAGE |
| Téléphone | Recommandé | AVERTISSEMENT |

**Organisateur particulier (décision D2).** Le bloc d'identité devient : « [Prénom Nom], particulier, demeurant [adresse] ». Pas de SIRET ni de forme juridique sociétaire. La mention de licence est remplacée par une mention propre au particulier, à faire valider par un juriste avant mise en ligne. Tous les autres contrôles s'appliquent.

### 11.3. Règles communes

Utiliser la même identité juridique et les mêmes données de signature dans tout le document. Ne pas déduire l’habilitation d’un intitulé de poste. Prévoir une vérification manuelle documentée si un service externe de SIRET est indisponible ou ne retourne aucun résultat : absence de résultat ne signifie pas automatiquement invalidité.

Une identité hors périmètre nécessite un parcours spécifique ; ne jamais imposer un faux SIRET français ni une valeur fictive pour contourner le blocage.

## 12. Licence ou dispense : contrôles

Choix explicites : « n° de licence renseigné », « dispense renseignée », « situation à vérifier ».

| Situation | Données et effet |
|---|---|
| N° de licence | Numéro, catégories, informations de validité ; blocage si incomplet |
| Dispense | Motif et confirmation ; blocage si motif absent |
| Situation à vérifier | Blocage ; ne pas la convertir automatiquement en dispense |
| Validité ne couvrant pas la représentation | Blocage du parcours automatique ; vérification/renouvellement à documenter |

Ne pas proposer une dispense incompatible avec l’activité du producteur sans examen. La seule présence d’un numéro ne certifie ni validité ni adéquation. Prévoir séparément les alertes de renouvellement et les justificatifs de vigilance requis selon le cas.

## 13. Représentation : champs obligatoires

| Renseignement | Validation | Niveau |
|---|---|---|
| Artiste/groupe et titre du spectacle | Renseignés | BLOCAGE |
| Date | Date valide | BLOCAGE |
| Nombre de représentations | Entier au moins égal à 1 | BLOCAGE |
| Nom et localisation du lieu | Adresse ou localisation assez précise pour identifier le site | BLOCAGE |
| Intérieur / plein air | Choix explicite | BLOCAGE |
| Durée | Positive | BLOCAGE |
| Arrivée | Date/heure ; si vide : « À préciser dans la fiche d'accueil » | AVERTISSEMENT |
| Installation et balances | Horaires, « Sans balances convenues » ou, si vide, « À préciser dans la fiche d'accueil » | AVERTISSEMENT |
| Début de représentation | Date/heure renseignées | BLOCAGE |
| Accès public | Gratuit / payant | BLOCAGE |
| Prix des places | Si payant ; si vide : « À préciser » | AVERTISSEMENT |
| Jauge | Entier positif ; si vide : « À préciser dans la fiche d'accueil » | AVERTISSEMENT |
| Contact opérationnel organisateur | Nom et moyen de contact ; si vide : « À préciser dans la fiche d'accueil » | AVERTISSEMENT |
| Invitations réservées au producteur | Entier ≥ 0 ; 0 par défaut | AVERTISSEMENT |
| Nombre d'exemplaires | Entier ≥ 2 ; 2 par défaut | BLOCAGE |

Lorsqu'elles sont renseignées : arrivée après le début du spectacle : blocage. Balances après le début : blocage sauf configuration particulière traitée explicitement. Utiliser des dates/heures complètes pour les passages à minuit et les opérations sur plusieurs jours.

Une représentation passée exige une confirmation ; ne pas interdire indistinctement toute régularisation, mais ne jamais antidater le contrat.

## 14. Tournée, restauration et hébergement : champs obligatoires

| Renseignement | Validation | Niveau |
|---|---|---|
| Effectif total en tournée | Entier au moins égal à 1 | BLOCAGE |
| Restauration | Choix explicite prise en charge / aucune prise en charge | BLOCAGE |
| Si restauration prévue | Effectif, repas, dates et modalités | BLOCAGE si incomplet |
| Hébergement | Choix explicite prise en charge / aucun hébergement | BLOCAGE |
| Si hébergement prévu | Effectif, dates, nuitées et modalités | BLOCAGE si incomplet |
| Transport | Répartition explicite des prises en charge | BLOCAGE |

Champ vide = information manquante, pas absence de prise en charge.

Un effectif nourri/hébergé inférieur à l’effectif total impose une confirmation, sans imposer l’égalité. Un effectif supérieur exige correction ou justification avant génération. Éviter les doubles comptes entre personnes, repas et nuitées.

## 15. Prix et fiscalité : champs obligatoires

| Renseignement | Validation | Niveau |
|---|---|---|
| Prix de cession | Strictement positif dans ce modèle rémunéré | BLOCAGE |
| Profil fiscal | Complet, cohérent et confirmé | BLOCAGE |
| Variante fiscale | Déterminable depuis le producteur | BLOCAGE si indéterminée |
| Taux | Requis si TVA facturée | BLOCAGE |
| Mention fiscale | Conforme au profil retenu | BLOCAGE |
| Fondement sans TVA | Référence renseignée | BLOCAGE |
| Frais supplémentaires | Montant/calcul convenu ou « Aucun » | BLOCAGE |
| Acompte | Choix oui/non explicite | BLOCAGE |
| Si acompte | Montant et échéance | BLOCAGE |
| Solde/règlement total | Montant et échéance | BLOCAGE |
| Modalités de facturation | Renseignées, exigences de l’acheteur comprises | BLOCAGE |

Bloquer les calculs incohérents, l’acompte supérieur au total, la somme d’échéances incorrecte, les frais « à définir », les contradictions fiscales et les cas multi-taux non gérés. Ne pas bloquer pour un numéro de TVA intracommunautaire qui n’est pas applicable au profil ; une situation particulière doit être vérifiée, non comblée par un faux numéro.

## 16. Autres blocages de génération définitive

- Champ indispensable manquant ou variable entre doubles accolades non remplacée.
- Valeur fictive, donnée de démonstration ou coordonnées « à compléter » identifiées.
- Identité ou signataire incohérents entre les sections.
- Annexe absente, illisible ou non identifiée par titre et date/version.
- Contradiction identifiée entre contrat et annexes.
- Plein air sans repli/absence de repli renseigné, procédure, référents ou conditions financières applicables.
- Opération hors périmètre standard sans parcours spécifique validé.

Les annexes non encore signées ne bloquent pas la génération d’un dossier destiné à la signature ; elles bloquent uniquement le statut « complet signé ».

## 17. Dates et données de signature

La date de génération n’est pas la date de signature des deux parties. Ne pas exiger une signature déjà réalisée pour produire le dossier à signer.

- Manuscrit : prévoir les emplacements de date et lieu à compléter, ou les informations expressément confirmées.
- Électronique : enregistrer les dates et preuves issues du parcours de signature.

Adapter les variables contrat.date_signature et contrat.lieu_signature en conséquence. Aucun champ vide technique ne doit subsister : générer un emplacement de saisie approprié plutôt qu’une fausse date.

## 18. Blocages propres à l’envoi

L’envoi exige une version définitive valide et actuelle, ainsi que :

- destinataires présents et adresses correctement formées ;
- contrat et deux annexes réellement disponibles et lisibles ;
- versions des annexes identiques à celles référencées ;
- taille totale compatible avec le service d’envoi.

Tout échec bloque l’envoi avec un message explicite. Ne jamais retirer silencieusement une pièce jointe.

## 19. Affichage des erreurs et validation serveur

Ne pas afficher seulement « Contrat incomplet ». Regrouper les anomalies par écran, afficher le nombre d’éléments à corriger et proposer un accès au champ concerné.

Exemple :

> Génération impossible : 5 éléments à compléter.
> - Informations de la structure : SIRET producteur manquant.
> - Organisateur : qualité du signataire manquante.
> - Contrat : échéance du solde absente.
> - Contrat : hébergement non précisé.
> - Annexes : fiche technique non jointe.

Format proposé :

```json
{
  "code": "PRODUCTEUR_SIRET_MANQUANT",
  "niveau": "BLOCAGE",
  "champ_concerne": "producteur.siret",
  "message_utilisateur": "Renseignez le SIRET de la structure productrice.",
  "ecran_de_correction": "informations_structure"
}
```

Valider côté serveur, pas uniquement dans l’interface. Enregistrer les confirmations avec auteur, date et version des données concernées. Une modification de ces données impose une nouvelle confirmation.

```text
ENREGISTREMENT : autorisé même incomplet
BROUILLON : autorisé, mention et anomalies visibles
GENERATION DEFINITIVE : aucun blocage et confirmations enregistrées
ENVOI : génération valide et actuelle + destinataires + trois documents conformes
COMPLET SIGNE : contrat et deux annexes signés par les deux parties
```

Une modification d’une donnée utilisée rend une version non envoyée et non signée « à actualiser ». Une version déjà envoyée ou signée est immuable : correction par nouvelle version ou avenant selon le stade. Conserver l’historique et distinguer la version active des versions remplacées.

## 20. Recette fonctionnelle minimale

1. Producteur facturant la TVA : variante avec TVA, taux/mention issus des paramètres.
2. Producteur en franchise : variante sans TVA, mention propre au régime, aucun taux 0 %.
3. Producteur exonéré sous un autre fondement : sa référence, aucun 293 B automatique.
4. Organisateur sans TVA et producteur facturant la TVA : conserver la variante avec TVA.
5. Changement des paramètres après signature : document signé inchangé.
6. Concert gratuit pour le public : clause CNM maintenue, sans automatisme d’exonération.
7. Quatre personnes en tournée et trois hébergées : confirmation, puis reprise exacte des effectifs.
8. Annexe manquante : brouillon possible ; génération définitive et envoi bloqués.
9. Annexe non signée : envoi à signer possible ; statut complet signé impossible.
10. Programme type SACEM absent : texte de remplacement, pas de faux numéro ni blocage.
11. Plein air sans repli : absence explicite et procédure renseignées ; pas de garantie de prix total implicite.
12. Annexe modifiée après accord : nouvelle version et nouvelle acceptation.
13. SIRET absent : génération définitive bloquée, lien vers la fiche concernée.
14. Service externe SIRET indisponible : parcours de contrôle manuel documenté, pas d’invalidation automatique.
15. Nom du contact différent du signataire : données conservées distinctement.
16. Échéancier incomplet ou total incorrect : blocage.
17. Signature future : aucune date de génération présentée comme date de signature.
18. Horaires passant minuit : contrôle sur dates complètes, sans faux blocage.
19. Dossier incomplet trop volumineux pour l’e-mail : blocage, aucune pièce supprimée.
20. Modification d’une donnée confirmée : confirmation à renouveler et document à actualiser.

## 21. Validation et maintenance

Faire valider les modèles par un juriste du spectacle vivant avant diffusion publique. Revue particulière : annulation/restitutions, garantie météo optionnelle, fiscalité, droits incorporés, acheteurs publics et parcours de signature.

Versionner les clauses juridiques, profils fiscaux et spécifications. Les contrôles de cohérence ne doivent pas être présentés comme une certification juridique automatique.

Références de travail déjà consultées dans l’analyse initiale : ARTCENA, « Contrat de cession du droit d’exploitation d’un spectacle » ; CNM, rubrique « Taxe » ; Code civil, article 1218. Les guides anciens du projet ne constituent pas, seuls, une base de règles actuelles automatisées.
