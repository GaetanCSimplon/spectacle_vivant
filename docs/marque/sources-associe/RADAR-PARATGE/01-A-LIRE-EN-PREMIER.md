# Radar + Paratge — à lire en premier

**Pour le développeur · mis à jour le 12/11/2026**

Bonjour,

Ce dossier contient tout ce qu'il faut pour le prochain grand chantier de Bòrd Pro. Il y a désormais **deux modules distincts, chacun avec sa spécification** :

- **Radar, le copilote**, voit ce qui coince : documents, logistique, échéances, obligations. Il sera dans les offres **Pilotage** et **Collectif**.
- **Paratge, l'agent**, prépare ce qui débloque : modèle économique, financements, solde des dates et des tournées, « Et si… ». Il sera dans l'offre **Collectif**.

Les deux sont reliés : une seule liste d'alertes (celle de Radar), une seule formule de calcul (celle de Paratge), un seul pop-up par action. Cette interconnexion est décrite dans **la même section 9 des deux documents**.

Il ne s'agit pas encore de coder : **j'ai d'abord besoin de ta lecture et de ton chiffrage.** Rappel : on termine d'abord le MVP (e-mails, domaine bordpro.fr, stockage, Sentry, sauvegardes, relecture des contrats et factures). Radar et Paratge viennent ensuite (décision D12).

## Les fichiers, dans l'ordre de lecture

| # | Fichier | À quoi il sert | Statut |
| --- | --- | --- | --- |
| 1 | `01-A-LIRE-EN-PREMIER.md` | Ce message | — |
| 2 | **`02-RADAR-copilote.md`** | **Spécification de Radar** : règles d'alerte, écrans, données, feuille de route, interconnexion (§9) | Référence |
| 3 | **`03-PARATGE-agent.md`** | **Spécification de Paratge** : « Mon modèle », financements, formules et jeu de test, « Et si… », tournée, interconnexion (§9) | Référence |
| 4 | `04-PARATGE-nom-et-sens.md` | Le sens du nom, les deux rôles, les règles d'écriture | Référence |
| 5 | `05-paratge-outil-modele-economique.html` | **Facultatif.** L'outil HTML d'origine, pour voir le fonctionnement et comparer tes calculs. Le tableur `PARATGE - HopHopHop.xlsx` (dossier DEV) contient les mêmes formules. Ne pas t'occuper de l'onglet « La structure » (après R2, offre Collectif) | Source |
| 6-7 | `06-radar-dossier-de-conception.md` + `07-radar-feuille-de-route.png` | L'historique des réflexions. En cas d'écart, **les spécifications 02 et 03 l'emportent** | Historique |
| 8 | `08-RADAR-1.txt` | La toute première note de cadrage | Historique |
| — | `archives/02-SPEC-radar-paratge-developpeur.md` | L'ancienne spécification commune (v4, 08/11), remplacée par 02 et 03 | Archive |

## Ce que j'attends de toi (avant d'écrire du code)

1. **Lire** les deux spécifications, en commençant par leur §0 (en bref) et leur §9 (interconnexion).
2. **Répondre aux vérifications** : §10 de Radar et §11 de Paratge (ce qui existe déjà dans le code).
3. **Chiffrer**, même grossièrement : la **version 0** (Radar V0 + Paratge V0, construits et testés ensemble), puis les jalons suivants de chaque module.
4. **Me présenter les options d'organisation du code** (décision D2) : une app par module, une app commune, ou des règles réparties, avec leurs avantages (`CLAUDE.md` §9).
5. **Me signaler** ce qui te paraît risqué, flou ou contradictoire avec `CLAUDE.md`.
6. **Me dire si tu es d'accord avec les ajouts à `CLAUDE.md`** listés ci-dessous. Tu les appliques une fois validés.

## Ce qui est déjà décidé (ne pas rediscuter sans moi)

- Radar observe et prévient ; Paratge calcule et prépare. **Rien n'est envoyé, rien n'est modifié sans la validation de l'artiste.**
- Aucune alerte ne bloque : les cas graves demandent seulement une confirmation.
- Une seule formule de calcul pour toute l'app (Paratge §4), avec son jeu de test.
- Les taux (charges 45 %, provision 5 %, marge 10 %) sont des **repères ajustables** ; tout montant qui en dépend est marqué « estimation ».
- La fiche spectacle porte une liste de financements ; seuls les financements **acquis** comptent.
- Pas de distances ni de carte pour l'instant ; pas de pilotage de la structure avant l'offre Collectif.

## Ajouts proposés pour `CLAUDE.md`

- **Lexique** : « Radar » = le copilote (alertes « Ce qui coince », observe, ne modifie rien) ; « Paratge » = l'agent (« Mon modèle », « Et si… », prépare les actions économiques). Paratge : nom occitan, du latin *pariatio* « action de rendre égal » ; ne jamais écrire « Partatge ».
- **Règle de partage** : Radar = ce qui est (faits, documents, échéances) ; Paratge = ce que vaut une date et ce qui pourrait être.
- **Règle de l'agent** : aucun envoi vers un organisateur, aucune modification de prix ou de document sans validation explicite.
- **Règle 6.2 bis** : une seule fonction de calcul du solde d'une date et des prix plancher / conseillé (`apps/finance/services.py`) ; tout écran l'utilise.
- **Règle** : un montant issu du taux de charges est toujours marqué « estimation » ; Paratge ne calcule pas de charges sociales réelles (§10 inchangé).

## La suite

On se cale après ta lecture. La première chose à construire sera la **version 0**, testée avec 2 ou 3 artistes avant d'aller plus loin.

Merci !
