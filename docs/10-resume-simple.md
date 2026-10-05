# Où en est le projet ? — Résumé simple

> Un texte pour comprendre l'essentiel sans connaître la technique.
> État au **3 octobre 2026**, douze jours après le premier commit (21 septembre).
> Pour le détail : `08-synthese-fonctionnalites.md` (ce qui existe) et `09-cas-d-usage-et-diagrammes.md` (les schémas).

## L'idée en une phrase

Un artiste ou une petite compagnie qui joue quelques concerts par an n'a pas d'administrateur. Il jongle entre Word, Excel et sa messagerie pour faire ses contrats, ses factures et suivre ses dates. **L'application remplace tout cela par un seul outil, simple, utilisable sur téléphone** : on saisit sa date une fois, et les documents se préparent.

## Ce qu'on peut faire aujourd'hui

Prenons Julie, qui chante dans un groupe et vient de se faire proposer un concert par la mairie de Nîmes.

1. **Elle crée son compte** et renseigne « Ma structure » (son association : nom, SIRET, adresse, IBAN).
2. **Elle crée la date** en cinq étapes guidées : le spectacle, l'organisateur (la mairie), le lieu, la date et le prix. La date est d'abord « en option » : si l'organisateur tarde à répondre, l'application la signale en orange puis en rouge.
3. **Elle suit ses dates** dans une liste filtrable et dans un calendrier du mois, avec une couleur par statut.
4. **L'organisateur confirme** : elle confirme la date.
5. **Elle génère le contrat de cession** en PDF, déjà rempli avec toutes les informations. Elle peut le régénérer si quelque chose change : chaque version est gardée, et le contrat reçoit un numéro (par exemple C-2026-001).
6. **Le contrat est signé** (sur papier ou à sa façon). Elle clique sur « Marquer comme signé » : la version signée est **figée**, plus personne ne peut la modifier. Elle peut ajouter le scan.
7. **Elle facture** : une facture d'acompte (30 % du prix par défaut), puis une facture de solde. Les lignes sont proposées automatiquement, elle les ajuste, puis elle **émet** la facture. À ce moment elle reçoit un numéro (F-2026-0001), et la facture est figée avec les informations du jour. Elle peut aussi faire un devis.
8. **Une erreur sur une facture ?** On ne la modifie pas, on émet un **avoir** qui l'annule, comme le veut la règle comptable.
9. **Elle télécharge les PDF** et les envoie à l'organisateur.
10. **Elle prépare la feuille de route** du jour J : horaires (déjà pré-remplis), hébergement, repas, équipe, notes. Elle active le partage, copie le lien et l'envoie au groupe : chacun l'ouvre sur son téléphone **sans compte**, appelle le lieu en un geste, ouvre l'itinéraire ou copie l'adresse. Le lien ne montre jamais le prix, le contrat ni les factures, et elle peut l'arrêter quand elle veut.
11. **Elle note les paiements reçus** : quand le total d'une facture est atteint, elle passe automatiquement à « Payée ». L'application refuse un paiement plus gros que ce qui reste à payer.
12. **Elle note ses dépenses** (essence, hôtel, cachets…) avec la photo du ticket si elle le souhaite.
13. **Elle voit où elle en est** : pour chaque date, ce qui était prévu, ce qui a été facturé, ce qui a été encaissé, ce qui a été dépensé et le résultat. La page d'accueil résume l'année, les factures à encaisser (celles en retard sont signalées), les dates qui attendent encore un contrat et les prochains concerts.
14. **Elle exporte ses chiffres** en fichiers Excel (factures, recettes, dépenses) pour son comptable, sur la période de son choix.

Tout cela fonctionne déjà, sur ordinateur comme sur téléphone.

## Ce qui reste à faire

- **Les pages légales** (mentions légales, conditions d'utilisation, confidentialité) et la possibilité d'exporter ou de supprimer ses données.
- **La mise en ligne** : pour l'instant l'application tourne uniquement sur l'ordinateur du développeur. Il faut encore l'héberger, choisir un service d'e-mails et un nom de domaine.

Une envie notée pour plus tard : joindre à la feuille de route un **plan des lieux** (salle, accès, scène), sans passer par un service de cartes externe.

Plus tard (version payante) : la signature électronique par un prestataire, la facture électronique obligatoire, les relances automatiques, le paiement des abonnements.

## Ce qui rend l'outil fiable

- **Chaque structure ne voit que ses données.** C'est la règle numéro un : une fuite entre deux utilisateurs serait fatale au produit. Chaque donnée est rattachée à sa structure, chaque page vérifie ce lien, et des tests automatiques le contrôlent partout.
- **Ce qui est émis est figé.** Une facture émise ne peut plus être modifiée ni supprimée. Les numéros se suivent sans jamais sauter, même si une génération échoue en cours de route. Les informations légales sont copiées dans le document au moment de l'émission : changer son adresse demain ne modifie pas les factures d'hier.
- **Les fichiers sont protégés.** Un contrat ou une facture n'a pas d'adresse web qu'on pourrait deviner : on ne peut les télécharger qu'en étant connecté et seulement les siens.
- **Les calculs sont exacts au centime.** Pas d'arrondi caché : la TVA est calculée taux par taux, et un avoir reprend exactement les montants de sa facture.

## Comment le travail est organisé

- Le développeur travaille avec un assistant (Claude Code) : l'assistant propose un **plan**, le développeur l'approuve, puis l'assistant code **avec les tests**. Le développeur relit et applique lui-même tout ce qui touche à la base de données.
- Le travail avance par **petites étapes** : une idée, une branche, une relecture (« pull request »), puis la fusion. Il y en a eu **46 de fusionnées** en douze jours, et aucune n'est en attente.
- **717 tests automatiques** vérifient le fonctionnement à chaque modification. Une vérification automatique sur GitHub les rejoue avant toute fusion.

## Les chiffres

| | |
|---|---|
| Premier commit | 21 septembre 2026 |
| Modules du MVP terminés | 9 sur 10 (comptes, structure, carnet d'adresses, spectacles, dates, contrats, devis et factures, feuille de route, finances) ; reste la partie légale |
| Tests automatiques | 717, tous verts |
| Lignes de code | environ 5 200 (et 8 300 lignes de tests) |
| En ligne | pas encore |

## Ce qui demande une décision ou une validation humaine

- **Tester à la main sur téléphone** les nouveaux écrans (paiements, dépenses, accueil, exports) et ouvrir un export dans Excel : les tests automatiques ne remplacent pas un vrai essai.
- **Faire relire les documents par un professionnel** : le contrat et surtout les factures (mentions légales, TVA, conditions de paiement). Les PDF portent pour l'instant la mention « Modèle provisoire — non relu par un professionnel ».
- **Choisir le modèle économique** : gratuit jusqu'à trois dates par an, ou deux formules payantes proposées par le collègue.
- **Trancher la structure des spectacles** (projets, spectacles, versions) proposée par le collègue : à décider avant de la construire.
- **Rappel important** : les factures PDF du MVP ne remplacent pas la future plateforme de facturation électronique obligatoire. L'application ne doit pas se présenter comme « conforme » avant cette étape.

## Et ensuite ?

Les fonctions principales du produit sont faites : de la date au contrat, aux factures, à la feuille de route et au suivi de l'argent. La prochaine étape est la **partie légale** (pages légales, export et suppression des données, vérification finale de l'isolation, sauvegardes, essai complet), puis la **mise en ligne**. Une fois ces étapes terminées, le produit sera prêt pour une première série de testeurs réels.
