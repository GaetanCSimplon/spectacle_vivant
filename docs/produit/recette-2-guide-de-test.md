# Bòrd Pro — Guide de test de la recette n°2

Livraison en production : **v2026-11-19** (app.bordpro.fr). Ce guide couvre ce qui a été ajouté depuis la livraison de la recette n°1 (`v2026-11-13`) et la mise à jour Radar du 16/11 : devis et factures (spécification v2), contrat de cession (spécification du 13/11), Navette sociale, et trois ajustements avant production.

## Mode d'emploi

- **Identifiant** : chaque point a un code (ex. FAC-03) à reprendre dans vos retours. Mêmes familles que la recette n°1 (STR, ORG, DAT, BRD, RAD). Les nouveaux préfixes sont **DEV** (devis), **FAC** (factures), **CTR** (contrat, numérotés à partir de 11 pour ne pas reprendre ceux de la recette n°1), **SOC** (Navette sociale) et **AID** (aide à la saisie).
- **Données** : créez une structure de test avec **un spectacle, deux dates dans le mois en cours et trois personnes dans l'équipe**. Nommez tout « Recette » pour retrouver et supprimer ensuite.
- **Résultat** : notez ✅ (conforme), ❌ (défaut : écran, ce qui s'est passé, capture) ou ⚠️ (gêne sans blocage).
- **Rôle** : sauf indication contraire, testez connecté en **propriétaire**.
- Les montants s'affichent à l'euro dans les synthèses, **au centime** dans les documents.

## Ce qui a changé, en bref

| Chantier | En deux phrases |
|---|---|
| **Devis et factures** | Les PDF reprennent toutes les mentions légales (TVA selon le régime, pénalités, médiateur, licence, IBAN, devis et contrat d'origine). Le devis peut être marqué « accepté », la facture de solde déduit l'acompte, et Radar prévient quand quelque chose manque. |
| **Contrat de cession** | Les quatre anciens modèles sont remplacés par **un seul contrat**, avec ou sans TVA selon le régime de la structure (plus de choix manuel). Un PDF unique réunit le contrat, la fiche technique et une fiche d'accueil générée. Des contrôles bloquent la version définitive tant qu'il manque l'essentiel ; l'aperçu reste toujours possible. |
| **Navette sociale** | L'onglet Social devient « Vérifier mon social du mois » : contrôle par spectacle, export CSV pour le prestataire de paie, export PDF « Navette sociale », suivi du mois et rappel Radar. Estimation du coût employeur uniquement, jamais de bulletin ni de cotisation. |
| **Ajustements** | Bouton « ? » d'aide à la saisie, IBAN plus tolérant, cachets de l'équipe comptés dans le Budget et le Bord, ligne « Total ». |

---

## 1. Structure et organisateur : nouveaux champs

| ID | Type | À tester | Scénario | Attendu |
|---|---|---|---|---|
| STR-10 | Nouveau | Régime de TVA et mention d'absence de TVA | « Ma structure » : choisir « Franchise en base », vérifier le texte d'exonération et la date de confirmation du régime. Répéter avec « Assujetti » (taux demandé) | Le régime pilote les mentions des devis, factures et du contrat. Pas de « taux 0 % » affiché pour l'absence de TVA |
| STR-11 | Nouveau | Licence d'entrepreneur de spectacles | Saisir un n° de licence avec catégories et validité ; puis tester « dispense » avec un motif | Les deux cas sont possibles ; un motif est exigé pour la dispense |
| STR-12 | Nouveau | Contact de production | Renseigner nom et e-mail du contact de production | Repris dans le contrat |
| STR-13 | Nouveau | Réglages de facturation | Délai de validité du devis, délai de paiement, médiateur de la consommation, option TVA sur les débits | Valeurs reprises dans les PDF |
| ORG-08 | Nouveau | Nature juridique de l'organisateur | Créer un organisateur « Association », puis un « Particulier » | Le particulier n'a pas de SIRET obligatoire et la mention de médiation apparaît sur ses documents |
| ORG-09 | Nouveau | Signataire de l'organisateur | Nom, qualité, case « habilitation confirmée » | Obligatoire pour générer le contrat définitif |
| ORG-10 | Nouveau | Licence ou dispense de l'organisateur | Choisir « n° de licence », « dispense » ou « situation à vérifier » | « À vérifier » bloque le contrat définitif |
| ORG-11 | Nouveau | Contact administratif et facturation | Nom et e-mail du contact administratif ; adresse de facturation différente, SIREN, n° de TVA | Repris sur les factures |

## 2. Aide à la saisie

| ID | Type | À tester | Scénario | Attendu |
|---|---|---|---|---|
| AID-01 | Nouveau | Bouton « ? » | Dans « Ma structure », un organisateur, un lieu, un spectacle ou un membre d'équipe : cliquer sur « ? » à côté d'IBAN, BIC, SIRET, TVA, code APE, n° de sécurité sociale, n° d'objet SACEM, code postal | Une bulle donne la règle et un exemple ; Échap la ferme ; utilisable au clavier |
| AID-02 | Nouveau | IBAN avec séparateurs | Saisir un IBAN avec espaces, tirets ou points | Accepté |
| AID-03 | Nouveau | IBAN faux | Changer un chiffre d'un IBAN valide | Message « erreur de saisie » ; un IBAN de longueur fausse indique la longueur attendue |

## 3. Devis

| ID | Type | À tester | Scénario | Attendu |
|---|---|---|---|---|
| DEV-01 | Nouveau | Mentions du PDF | Créer et envoyer un devis pour une date ; ouvrir le PDF | Émetteur, client, objet, lieu, lignes, totaux, mention fiscale selon le régime, licence, validité, modalités et IBAN/BIC. Numéro `D-AAAA-NNN` attribué à l'envoi, brouillon sans numéro |
| DEV-02 | Nouveau | Lignes à unités fermées | Ajouter des lignes de chaque type (cession, transport, hébergement, repas, technique, communication, autre, remise) | Les unités proposées dépendent du type ; pas de saisie libre |
| DEV-03 | Nouveau | Régime sans TVA | Avec la structure en franchise | Pas de colonne TVA ; mention « TVA non applicable, article 293 B du CGI » |
| DEV-04 | Nouveau | Acceptation du devis | Cocher « Devis signé reçu », indiquer le n° de bon de commande et la date | Le devis passe à « accepté » ; la mention « Bon pour accord » figure sur le PDF |
| DEV-05 | Nouveau | Devis expiré | Pour une date dont le devis est dépassé sans acceptation | Radar signale « devis expiré » (RAD-44) |

## 4. Factures et avoirs

| ID | Type | À tester | Scénario | Attendu |
|---|---|---|---|---|
| FAC-01 | Nouveau | Facture d'acompte | Depuis un devis accepté, émettre un acompte (montant ou %) | Numéro `F-AAAA-NNN`, rappel du devis (« accepté le … ») et du contrat d'origine |
| FAC-02 | Nouveau | Facture de solde | Émettre le solde après l'acompte | Ligne « Acompte déjà facturé » en négatif, total à payer = total − acompte |
| FAC-03 | Nouveau | Numérotation | Émettre plusieurs documents, dont un avoir | Numéros sans trou, dans une même suite ; avoir dans la même suite |
| FAC-04 | Nouveau | Immuabilité | Tenter de modifier une facture émise | Impossible ; correction par « Créer un avoir » |
| FAC-05 | Nouveau | Pénalités et médiateur | Facture à un organisateur professionnel, puis à un particulier | Professionnel : 3 fois le taux légal et indemnité de 40 €. Particulier : pas de pénalités pro, mention du médiateur |
| FAC-06 | Nouveau | Échéance | Vérifier la date d'échéance | 30 jours par défaut, plafonnée à 60 |
| FAC-07 | Nouveau | Bon de commande | Saisir un n° de bon de commande | Présent sur la facture |
| FAC-08 | Nouveau | Radar avant émission | Émettre sans SIRET de l'organisateur, sans licence, sans médiateur (client particulier), ou au-delà du prix de cession | La modale Radar prévient (RAD-40, 41, 42, 43) et ne bloque pas |
| FAC-09 | Nouveau | Instantané légal | Changer l'adresse de la structure après émission, rouvrir la facture | Le document garde les informations d'origine |

## 5. Contrat de cession

| ID | Type | À tester | Scénario | Attendu |
|---|---|---|---|---|
| CTR-11 | Nouveau | Un seul contrat | Générer un contrat : plus de choix entre quatre modèles | La variante avec ou sans TVA est choisie par le régime de la structure |
| CTR-12 | Nouveau | Article 5 selon le régime | Générer avec une structure « assujettie » puis « en franchise » | Avec TVA : HT, taux, montant de TVA, TTC. Sans TVA : prix net et mention légale d'absence de TVA |
| CTR-13 | Nouveau | Fiche « Compléter le contrat » | Ouvrir « Compléter le contrat » sur la date | Intérieur / plein air (repli, référents), horaires, jauge, accès gratuit ou payant, effectif, repas, hébergement, transport, frais supplémentaires, acompte oui/non, modalités de facturation, contact sur place |
| CTR-14 | Nouveau | Contrôles regroupés | Laisser des champs vides | Les anomalies sont groupées par écran ; trois niveaux : bloquant, à confirmer, simple avertissement |
| CTR-15 | Nouveau | Aperçu toujours possible | Avec un dossier incomplet, ouvrir l'aperçu | Bandeau « BROUILLON — INFORMATIONS INCOMPLÈTES — NON DESTINÉ À LA SIGNATURE » |
| CTR-16 | Nouveau | Génération bloquée | Retirer la fiche technique du spectacle, ou ne pas répondre à « acompte demandé » | La génération définitive est refusée avec la liste des manques |
| CTR-17 | Nouveau | Confirmations | Cas « à confirmer » (par exemple effectif nourri inférieur à l'effectif total) | Une confirmation explicite est demandée, puis enregistrée |
| CTR-18 | Nouveau | Informations inconnues | Laisser vides heure d'arrivée, balances, jauge, contact sur place | Pas de blocage ; le contrat affiche « À préciser dans la fiche d'accueil » |
| CTR-19 | Nouveau | PDF unique | Générer puis télécharger | Un seul PDF : contrat, fiche technique du spectacle, fiche d'accueil (générée) |
| CTR-20 | Nouveau | Fiche d'accueil | Ouvrir la dernière annexe | Effectif, repas, hébergement, transport, horaires, contacts ; indique l'absence de prise en charge si c'est le cas |
| CTR-21 | Nouveau | Organisateur particulier | Contrat pour un particulier | Bloc d'identité « Prénom Nom, particulier, demeurant… », pas de SIRET (mention de licence à faire valider par un juriste) |
| CTR-22 | Nouveau | Version à actualiser | Générer, puis modifier une donnée de la date | Le contrat est signalé « à actualiser » |
| CTR-23 | Nouveau | Envoi et signature | « Confirmer : le contrat est envoyé », puis « Confirmer : le contrat est signé » | PDF figé conservé dans Documents ; l'envoi par e-mail du dossier complet n'est pas encore disponible |
| CTR-24 | Nouveau | Contenu retiré | Lire le contrat | Plus d'IBAN, de configuration de salle, de délai de retour, de conditions particulières ni de ville du tribunal (litige : droit commun, article 10) |
| CTR-25 | Nouveau | Lecture du PDF | Lire entièrement le PDF | Pas de faute, pas de champ non remplacé (« {{ … }} »). La relecture juridique reste à faire |

## 6. Bord : cachets de l'équipe et Total

| ID | Type | À tester | Scénario | Attendu |
|---|---|---|---|---|
| BRD-05 | Nouveau | Cachets dans le Budget de la date | Date avec équipe ayant un « Montant brut » | « Dépensé » détaille « dont dépenses saisies » et « dont cachets (équipe) » ; « Résultat » en tient compte |
| BRD-06 | Nouveau | Double compte | Saisir à la main une dépense « Cachets » sur la même date | Un avertissement apparaît, sans blocage |
| BRD-07 | Nouveau | Débit du Bord | « Opérations récentes » d'une date avec équipe | Débit = dépenses saisies + cachets, identique au Budget |
| BRD-08 | Nouveau | Ligne « Total » | Tableau et affichage mobile | Débit, crédit et solde sur toute la période (même avec plus de 20 dates) ; solde écrit « Excédent », « À l'équilibre » ou « Déficit », jamais en couleur seule |
| BRD-09 | Nouveau | Filtre « Dépenses faites par » | Activer le filtre | Les cachets sortent du débit |
| BRD-10 | Nouveau | Carte « frais » et accueil | Comparer avec le Bord | Les cachets y sont aussi comptés |
| BRD-11 | Nouveau | Compte membre | Se connecter avec un compte non propriétaire | Aucun cachet visible ni compté |
| BRD-12 | À savoir | Arrondi | Comparer le Total à la somme des lignes | Un écart d'un euro est possible (arrondi à l'affichage seulement). À signaler s'il vous gêne |
| BRD-13 | À savoir | Exports CSV | Exporter des dépenses | Les cachets n'y figurent pas (volontaire : le CSV liste des lignes de dépense) |

## 7. Navette sociale

Réservée au propriétaire. Menu « Équipe » → « Social ».

| ID | Type | À tester | Scénario | Attendu |
|---|---|---|---|---|
| SOC-01 | Nouveau | Écran du mois | Ouvrir « Vérifier mon social du mois » ; changer de mois | Liste par spectacle ; récapitulatif en haut ; le changement de mois ne recharge pas toute la page |
| SOC-02 | Nouveau | États en toutes lettres | Laisser un brut ou un n° de sécurité sociale vide | « À compléter », « Information » ou « À vérifier » écrits, jamais en couleur seule |
| SOC-03 | Nouveau | Liens de correction | Cliquer « Fiche » puis « Date » sur une ligne à compléter | Mène à la fiche de la personne, puis à la date |
| SOC-04 | Nouveau | Heures d'un technicien | Dans le bloc équipe d'une date, renseigner « Heures (technicien) » | Enregistré et repris dans le mois ; un artiste avec cachets est compté cachets × 12 |
| SOC-05 | Nouveau | Taux de repère | « Ma structure », groupe « Social » : taux 0,45 | Modifiable (entre 0 et 1) ; le coût employeur est toujours marqué « estimation » |
| SOC-06 | Nouveau | Export CSV | « Exporter pour ma paie (CSV) » ; ouvrir dans un tableur | Séparateur `;`, accents corrects, dates JJ/MM/AAAA, `nb_heures` à deux décimales, nom `navette-sociale-AAAA-MM-…csv` ; pas de coût estimé |
| SOC-07 | Nouveau | Export PDF | Générer le PDF | A4 paysage, mention « estimation », mention « Offre Collectif », totaux identiques au CSV, **n° de sécurité sociale absent** sauf case cochée. Regarder la page 3 (récapitulatif par personne) |
| SOC-08 | Nouveau | Suivi du mois | Cocher « Transmis à mon prestataire » et « Paie faite », enregistrer | Les cases sont retenues après rechargement |
| SOC-09 | Nouveau | Historique | Ouvrir « Historique des mois » | Le mois suivi y figure |
| SOC-10 | Nouveau | Modifié depuis l'export | Après un export, changer un cachet | La mention « modifié depuis le dernier export » apparaît |
| SOC-11 | Nouveau | Rappel Radar | À partir de 10 jours avant la fin du mois, avec au moins une paie | RAD-65 dans le bouton Radar ; disparaît quand tout est complet ou « Paie faite » cochée |
| SOC-12 | À savoir | Date annulée | Annuler une date qui a une équipe | Ligne « À vérifier », pas comptée dans les cachets du Bord |
| SOC-13 | À savoir | Écran étroit | Ouvrir l'écran à largeur de téléphone | Le tableau défile horizontalement (écran conçu pour l'ordinateur) |

## 8. Radar

| ID | Type | À tester | Scénario | Attendu |
|---|---|---|---|---|
| RAD-50 | Nouveau | Règles de facturation | Rejouer FAC-08 et DEV-05 | RAD-40 (SIREN), 41 (licence), 42 (médiateur), 43 (total), 44 (devis expiré) apparaissent avec leur explication |
| RAD-51 | Nouveau | Contrat incomplet | Tenter d'envoyer un contrat avec des blancs | RAD-10 prévient dans une modale ; l'utilisateur garde la décision |
| RAD-52 | À savoir | Bouton Radar | Page d'accueil à 1440 px | Défaut connu : le bouton (en bas à droite) recouvre le coin de la carte « À traiter maintenant » et son texte est coupé. À confirmer |

## 9. Contrôles généraux

| ID | À tester | Attendu |
|---|---|---|
| GEN-01 | Connexion, déconnexion, retour arrière après déconnexion | Aucune page privée n'est affichée |
| GEN-02 | Une page de données par domaine (dates, organisateurs, documents) | Chargement rapide et sans erreur |
| GEN-03 | Feuille de route par lien secret, à 375 px (téléphone) | Lisible, aucune donnée financière |
| GEN-04 | Isolation : avec deux structures de test, comparer Bord, Social, exports CSV et PDF | Aucune structure ne voit les données de l'autre ; l'adresse d'un document de l'autre structure donne une erreur 404 |

## Points que seul le métier peut trancher

- **Format du CSV** pour le prestataire de paie et définition d'une « paie à faire » : à confirmer avec votre gestionnaire de paie.
- **Mentions juridiques** des contrats, devis et factures : relecture par un juriste, notamment pour l'organisateur particulier et le régime « autre exonération ».
- **« N° de compte »** de la fiche Équipe : en attente de votre réponse.

## À la fin de la recette

1. Notez les ❌ et ⚠️ avec leur identifiant : chaque défaut devient une PR séparée.
2. Supprimez les données « Recette » (ou gardez la structure de test).
3. Transmettez le tableau rempli pour mise à jour de `docs/produit/etat-du-projet.md`.
