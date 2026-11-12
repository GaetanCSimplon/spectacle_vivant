# Bòrd — dictionnaire des indicateurs (Lot 0)

Version 1 — 2026-10-16, révisée le 2026-11-12 (deux lectures, BRD-04). Applique la spécification de l'associé (`specification-onglet-bord.md`, 15/10/2026) **à ce que le code gère déjà**. Rien de ce document n'est codé tant qu'il n'est pas validé (§6).

## 1. Principe
Bòrd = « Où en suis-je ? » : une synthèse qui ouvre le détail de chaque chiffre. Aucune ressaisie : tout vient des dates, factures, paiements et dépenses existants. Un seul module de calcul (`apps/finance/bord.py`), qui servira aussi à RADAR le jour où il sera défini (Q17).

## 2. Périmètre de la première version
| Spécification | Cette version | Pourquoi |
|---|---|---|
| Périmètre « projet / tournée » | **Spectacle** (ou toute l'activité) | Projet et Tournée n'existent pas (Q10) |
| Période : mois, trimestre, saison, intervalle | Mois, trimestre, année, intervalle libre | Saison : bornes à configurer par structure, plus tard |
| Budget initial / actualisé / engagé | **Non** : recette prévue (prix des dates) et dépenses enregistrées | Aucune ligne budgétaire (Q18) |
| Subventions | **Non** | Aucun modèle (Q18) |
| Rémunérations, jours, heures, coût employeur | **Non** (comptage des personnes seulement) | Paie hors périmètre (`CLAUDE.md` §10) |
| Alertes | Règles simples ci-dessous, seuils fixés dans le code | Pas de configuration par l'utilisateur |
| Lien vers RADAR | **Non** | RADAR non défini (Q17) |

## 3. Dates de référence et conventions
- Une période est un intervalle **de dates inclusives**, en heure de Paris.
- Chaque chiffre dit sa date de référence dans son libellé :
  - **date de la représentation** : dates, recette prévue ;
  - **date de la représentation** : facturé (activité) ; **date d'émission** n'est plus la référence du facturé depuis le 2026-11-12 ;
  - **date de réception** : encaissé ;
  - **date de la dépense** : dépenses ;
  - **échéance de la facture** : retards.
- Un événement est rattaché à la période par sa date de représentation (un seul jour : pas de cas « à cheval »).
- Montants : **HT** pour le prévu et le facturé ; **TTC** pour l'encaissé et le restant à encaisser (un paiement règle une facture TTC). Chaque montant porte « HT » ou « TTC ». Pour une structure non assujettie à la TVA, les deux sont égaux. Jamais d'addition HT + TTC.
- Au centime près ; l'arrondi à l'euro n'est qu'un affichage des cartes de synthèse.
- **Valeur absente ≠ zéro** : « à renseigner » ; aucune donnée : état vide avec une action (« Créer une date »).

## 3 bis. Deux lectures de la même donnée (BRD-04, 2026-11-12)
Le Bord se lit de deux façons, au choix en haut de la page, avec la même période et le même filtre de spectacle. Libellés sans jargon comptable.

| | **« Ce que rapportent mes dates »** (activité) | **« Argent reçu et à recevoir »** (argent) |
|---|---|---|
| Date de référence | la **date du concert** | la **date de l'argent** |
| Chiffres | Prévisionnel (HT), Signé (HT, contrat signé), Facturé (HT) | Encaissé (TTC), À encaisser (TTC), en retard |
| Facturé / Encaissé | les factures des dates de la période, **quelle que soit leur date d'émission** | les paiements reçus dans la période, quel que soit le concert |
| Dépenses | celles des **dates** de la période | celles **dépensées** dans la période (date de la dépense) |
| Solde | chiffre choisi − dépenses des dates | encaissé − dépensé |
| Tableau | une ligne par date (« Opérations récentes ») | les paiements et les montants attendus, par date (« Mouvements de la période ») |

**Date d'un montant attendu (À encaisser).** Pour chaque date confirmée ou signée : une facture émise non soldée est attendue à son échéance ; la part du prix **pas encore facturée** est attendue à l'échéance de l'acompte (si aucun acompte n'est facturé : le pourcentage d'acompte de la date) puis à l'échéance du solde ; une échéance manquante est remplacée par la date du concert. Les options et les dates annulées n'attendent rien. « Reste à encaisser » et « dont en retard » restent un état à ce jour (suit le filtre de spectacle, pas la période).

**Cas de contrôle (recette n°1).** Concert le 15/03/2027, 3 000 € HT, acompte de 900 € facturé et encaissé le 10/11/2026 : activité 2027 = 3 000 € ; argent 2026 = 900 € encaissés ; argent 2027 = le restant (2 100 € HT, plus la TVA le cas échéant) à encaisser. Une facture émise sur une date annulée reste comptée (avoirs en négatif).

## 4. Indicateurs
| Indicateur | Définition | Détail au clic |
|---|---|---|
| **Dates confirmées** | Dates de la période au statut confirmée ou signée | Liste des dates filtrée |
| **Options** | Dates au statut option, **comptées à part** | idem |
| **Annulées** | Comptées à part, **exclues** de tous les autres chiffres | idem |
| **Recette prévue (HT)** | Somme des prix des dates confirmées ou signées. Les options ne sont pas une recette acquise : montrées à part, « si confirmées » | Dates |
| **Recette facturée (HT)** | Factures émises, avoirs en négatif (par date d'émission) | Factures |
| **Recette encaissée (TTC)** | Paiements reçus dans la période | Paiements |
| **Dépenses (enregistrées)** | Dépenses de la période, par catégorie. Pas de « prévu » : seules les dépenses saisies comptent | Dépenses |
| **Solde** | Recette (du type choisi : prévue, facturée ou encaissée) − dépenses enregistrées. Appelé « Solde », **jamais « trésorerie »** | Les deux détails |
| **Restant à encaisser (TTC)** | Facture émise − paiements reçus, sur les factures non soldées (acomptes, paiements partiels et avoirs déjà gérés) | Factures concernées |
| **Dont en retard** | Restant positif avec échéance dépassée (jour d'échéance non compris) | idem |
| **Personnes mobilisées** | Personnes **distinctes** de l'équipe affectées à des dates confirmées de la période | Dates et participants |
| **Complétude** | Dates confirmées sans contrat signé, sans échéances ou sans organisateur à jour : « n dates à compléter » | Dates |

**Lecture des chiffres.** Les cartes suivent les dates de référence du §3 (une facture émise hors période n'est pas dans la carte « Facturé »). La table des opérations liste les **dates de la période** avec, pour chacune, ses montants complets (prévu, facturé, encaissé), quelle que soit la date de la facture ou du paiement. Le « restant à encaisser » est un état **à ce jour** : il suit le filtre de spectacle, pas la période. Les dépenses sont de l'argent réellement dépensé (même pour une date annulée) et sont reprises telles que saisies.

**Statut d'une opération** (table « Opérations récentes ») : *annulé* = date annulée ; *payé* = toutes les factures de la date sont soldées ; *en attente* = le reste. Seul « annulé » se modifie à la main ; « payé » vient des paiements.

## 5. « À traiter maintenant » (cinq lignes au maximum)
Chaque ligne : libellé clair, date ou facture concernée, échéance, montant s'il y en a un, action (lien), et **la raison** de l'alerte. Les seuils sont des choix de produit, pas des délais réglementaires.
1. Facture arrivée à échéance avec restant positif.
2. Date confirmée dans moins de **30 jours** sans contrat signé.
3. Date confirmée dans moins de **30 jours** sans échéances de paiement.
4. Option qui expire dans moins de **7 jours** (seuil déjà utilisé par l'application).
5. Date confirmée sans prix verrouillé : *non retenue*, le prix est toujours renseigné.
S'il n'y a rien à signaler, le message dit « Rien à signaler sur les points contrôlés » et **pas** « tout est à jour ».

## 6. Décisions (validées le 2026-10-16)
- [x] HT pour le prévu et le facturé, TTC pour l'encaissé (§3).
- [x] Les options ne comptent pas dans la recette prévue (§4).
- [x] Seuils : 30 jours (contrat, échéances) et 7 jours (option) (§5).
- [x] Statut « payé » calculé, « annulé » modifiable (§4).
- [x] **Visible par tous les membres, modifiable par le propriétaire seul** : un membre voit tous les chiffres ; seul le propriétaire a le bouton « annuler / rétablir » de la table des opérations (une modification posée en POST par un membre est refusée côté serveur).

## 7. Plan de livraison
1. **Calculs et tests** (`bord.py`) : les indicateurs ci-dessus, avec les cas de la recette de la spec (§11) qui s'appliquent : sans date, options et annulation, règlement partiel, personne sur plusieurs dates, deux structures.
2. **Page Bòrd** : bandeau de contexte (période, spectacle, date d'actualisation), cartes Dates / Recette / Dépenses / Solde / Restant à encaisser / Équipe, « À traiter maintenant », « Prochaines dates », table « Opérations récentes ».
3. **Graphiques** (SVG/CSS) : évolution mensuelle recette / dépenses, dépenses par catégorie.
4. **Plus tard, après confirmation** : budget actualisé, subventions, rémunérations, projet et tournée, lien RADAR.
