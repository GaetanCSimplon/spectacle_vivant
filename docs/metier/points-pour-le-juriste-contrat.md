# Contrat de cession : points pour la relecture juridique (bp14)

Écrit le 2026-11-17, à la fin du chantier « contrat de cession » (PR A à G). À remettre au professionnel relecteur avec les deux modèles sources (`docs/metier/sources-associees/01` et `02`) et un PDF généré. Les contrôles de cohérence de Bòrd Pro ne sont **pas** une certification juridique (spécification `03`, §21).

## 1. Ce que Bòrd Pro produit
Un seul contrat, en un seul PDF : le contrat, l'annexe 1 (fiche technique du spectacle) et l'annexe 2 (fiche d'accueil, générée à partir des informations de la date). Seul l'article 5 change : avec TVA (HT, TVA, TTC) si la structure facture de la TVA, sans TVA (prix net, mention et fondement légal) sinon. Le choix dépend uniquement du régime de TVA de la **structure productrice**, jamais de l'organisateur.

## 2. Parties à relire en priorité (§21 de la spécification)
1. **Annulation et restitutions** (article 9) : réparation « selon le droit commun », décompte final, acomptes « non automatiquement acquis au producteur ».
2. **Garantie météo en plein air** : la clause reprend ce que l'utilisateur saisit (repli, procédure, référents, conditions financières). Sans conditions financières saisies, ce sont les règles d'annulation et de force majeure qui s'appliquent ; aucune garantie de paiement total n'est écrite d'office.
3. **Fiscalité** (article 5) : voir le §3 ci-dessous.
4. **Droits incorporés et droits d'auteur** (article 6) : SACEM à la charge de l'organisateur ; sans numéro de programme type, un texte de remplacement est imprimé.
5. **Taxe sur les spectacles (CNM)** : le contrat désigne le redevable légal selon que la représentation est payante ou gratuite ; la gratuité ne vaut pas exonération.
6. **Acheteurs publics** : le contrat ne remplace pas les documents de commande exigés par l'acheteur ; le champ « modalités de facturation » permet de les citer (n° de bon de commande, service payeur).
7. **Parcours de signature** : en V1, signature manuscrite hors de l'application ; « PDF signé déposé » vaut « complet signé ». Les trois pièces sont dans le même PDF. La signature électronique et l'envoi par e-mail sont prévus plus tard.

## 3. Textes provisoires à faire confirmer
| Texte | Où | Question |
|---|---|---|
| « TVA non applicable, article 293 B du CGI. » | franchise en base | exact et suffisant ? |
| « TVA non applicable, article 261-7-1° b du CGI. » | non assujetti (association) | l'article convient-il à tous les cas de non-assujettissement ? L'utilisateur peut le remplacer par son propre fondement (champ de la structure). |
| « Aucune TVA n'est facturée sur cette cession. » | article 5 sans TVA | utile en plus de la mention ? |
| Clause CNM (article 6) | tous | formulation du redevable légal |
| « Le contrat est soumis au droit français… juridiction compétente selon les règles de droit commun » | article 10 | suppression de la « ville du tribunal » (décision D7) : acceptable ? |
| Mention « lu et approuvé » avant les signatures | signatures | reste-t-elle nécessaire ? |

## 4. Données traitées automatiquement
- Les informations de la structure et de l'organisateur (nom, forme juridique, SIRET, adresse, signataire et qualité, licence ou dispense) sont **copiées dans chaque version** : une modification ultérieure ne change jamais un contrat déjà généré.
- Un signataire dont l'habilitation n'est pas confirmée, un SIRET manquant ou erroné, une licence expirée ou incomplète, un échéancier incohérent, une annexe manquante ou illisible **bloquent** la génération définitive. L'aperçu reste possible, avec un bandeau « BROUILLON — INFORMATIONS INCOMPLÈTES ».
- Un effectif nourri ou hébergé inférieur à l'effectif total demande une confirmation ; supérieur, il bloque.
- La date de signature n'est jamais celle de la génération : un emplacement à compléter est imprimé.

## 4 bis. Scénarios non couverts par la V1
| Scénario du §20 | Pourquoi |
|---|---|
| 9 et 12 : annexe non signée, annexe modifiée après accord | pas de statut de signature par annexe en V1 ; une modification crée une nouvelle version du PDF, à faire signer en entier |
| 14 : service SIRET externe indisponible | la recherche d'entreprise est facultative ; le SIRET se saisit et se contrôle (clé de Luhn) à la main, sans blocage par le service |
| 19 : dossier trop volumineux pour l'e-mail | l'envoi par e-mail du dossier complet est prévu en V2 ; la fiche technique est limitée à 10 Mo |

## 5. Ce qui n'est pas géré
Coréalisation, location de salle, contrats de travail, opérations hors de France, autoliquidation, taux de TVA multiples, opérations gratuites entre les parties.
