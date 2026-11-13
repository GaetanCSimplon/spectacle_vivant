# Radar + Paratge — journal des changements

**À lire en premier à chaque fois que le dossier change.** Le plus récent en haut. Chaque entrée dit ce qui a changé, dans quel fichier, et ce que ça change pour le code.

| Date | Ce qui change | Fichiers | Effet pour le développement |
| --- | --- | --- | --- |
| 12/11/2026 | **Radar et Paratge deviennent deux modules séparés**, chacun avec sa spécification. Interconnexion décrite à l'identique dans les deux (§9). Offres : Radar dans Pilotage et Collectif, Paratge dans Collectif (catalogue Stripe du 11/11) | `02-RADAR-copilote.md`, `03-PARATGE-agent.md` (nouveaux) ; ancienne spec commune → `archives/` ; fichiers 03 à 07 renumérotés en 04 à 08 | Lire les deux §0 et §9. Nouvelle règle RAD-29 (dépenses saisies > prix, pour Pilotage, à valider). Ligne de frais « administratif / paie » ajoutée aux formules |
| 08/11/2026 | **Financements du spectacle** (aide à la création, aide à la tournée, mécénat, coproduction, fonds propres), dès la V0 ; surplus d'aide à la création : l'artiste choisit (RAD-37) ; frais de fonctionnement réservés à Collectif (D20 à D22) | Spécification v4 (aujourd'hui dans `archives/`) | Nouveau modèle « financements du spectacle » ; formules modifiées (soutien par date) ; 3 cas de test ajoutés |
| 07/11/2026 (soir) | **Version 0** à construire en premier et à tester ; message d'accueil ; fichiers numérotés | `01-A-LIRE-EN-PREMIER.md`, spécification v3 | Alertes calculées à l'affichage en V0, sans modèle `Alert` ni commande de nuit |
| 07/11/2026 | Décisions D1 à D19 : tournée par période, un spectacle par tournée, aucune alerte bloquante, repères ajustables, Radar copilote / Paratge agent, finir le MVP d'abord | Spécifications v1 et v2 | Base de tout le reste |

## Règle

- Chaque modification d'un document du dossier ajoute **une ligne en haut** de ce journal, le jour même.
- Si une ligne touche ce que tu as déjà commencé à coder, elle est signalée par **« CODE EN COURS »**.
- En cas de doute sur une version, ce sont les fichiers `02` et `03` qui font foi.
