# Où en est le projet ? — Résumé simple

> Un texte pour comprendre l'essentiel sans connaître la technique.
> État au **1er octobre 2026**, onze jours après le premier commit (21 septembre).
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

Tout cela fonctionne déjà, sur ordinateur comme sur téléphone.

## Ce qui reste à faire

- **La feuille de route** : un document pratique pour le jour J (horaires, contacts, hébergement, repas), partagé par un lien secret que l'équipe ouvre sur son téléphone, sans compte.
- **Les paiements et les dépenses** : savoir ce qui est encaissé, ce qui est dépensé, le résultat de chaque date, un tableau de bord, un export pour le comptable.
- **Les pages légales** (mentions légales, conditions d'utilisation, confidentialité) et la possibilité d'exporter ou de supprimer ses données.
- **La mise en ligne** : pour l'instant l'application tourne uniquement sur l'ordinateur du développeur. Il faut encore l'héberger, choisir un service d'e-mails et un nom de domaine.

Plus tard (version payante) : la signature électronique par un prestataire, la facture électronique obligatoire, les relances automatiques, le paiement des abonnements.

## Ce qui rend l'outil fiable

- **Chaque structure ne voit que ses données.** C'est la règle numéro un : une fuite entre deux utilisateurs serait fatale au produit. Chaque donnée est rattachée à sa structure, chaque page vérifie ce lien, et des tests automatiques le contrôlent partout.
- **Ce qui est émis est figé.** Une facture émise ne peut plus être modifiée ni supprimée. Les numéros se suivent sans jamais sauter, même si une génération échoue en cours de route. Les informations légales sont copiées dans le document au moment de l'émission : changer son adresse demain ne modifie pas les factures d'hier.
- **Les fichiers sont protégés.** Un contrat ou une facture n'a pas d'adresse web qu'on pourrait deviner : on ne peut les télécharger qu'en étant connecté et seulement les siens.
- **Les calculs sont exacts au centime.** Pas d'arrondi caché : la TVA est calculée taux par taux, et un avoir reprend exactement les montants de sa facture.

## Comment le travail est organisé

- Le développeur travaille avec un assistant (Claude Code) : l'assistant propose un **plan**, le développeur l'approuve, puis l'assistant code **avec les tests**. Le développeur relit et applique lui-même tout ce qui touche à la base de données.
- Le travail avance par **petites étapes** : une idée, une branche, une relecture (« pull request »), puis la fusion. Il y en a eu **34 de fusionnées** en onze jours, et deux sont en cours de relecture.
- **535 tests automatiques** vérifient le fonctionnement à chaque modification. Une vérification automatique sur GitHub les rejoue avant toute fusion.

## Les chiffres

| | |
|---|---|
| Premier commit | 21 septembre 2026 |
| Modules du MVP terminés | 7 sur 10 (comptes, structure, carnet d'adresses, spectacles, dates, contrats, devis et factures) |
| Tests automatiques | 535, tous verts |
| Lignes de code | environ 3 750 (et 6 200 lignes de tests) |
| En ligne | pas encore |

## Ce qui demande une décision ou une validation humaine

- **Faire relire les documents par un professionnel** : le contrat et surtout les factures (mentions légales, TVA, conditions de paiement). Les PDF portent pour l'instant la mention « Modèle provisoire — non relu par un professionnel ».
- **Choisir le modèle économique** : gratuit jusqu'à trois dates par an, ou deux formules payantes proposées par le collègue.
- **Trancher la structure des spectacles** (projets, spectacles, versions) proposée par le collègue : à décider avant de la construire.
- **Rappel important** : les factures PDF du MVP ne remplacent pas la future plateforme de facturation électronique obligatoire. L'application ne doit pas se présenter comme « conforme » avant cette étape.

## Et ensuite ?

La feuille de route est faite. La prochaine étape est les **paiements et dépenses**, puis les pages légales et la mise en ligne. Une fois ces étapes terminées, le produit sera prêt pour une première série de testeurs réels.
