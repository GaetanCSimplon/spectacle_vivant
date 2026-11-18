# Résumé des PR fusionnées depuis la livraison v2026-11-16

Écrit le 2026-11-17, avant la livraison en production. Il couvre les PR #380 à #392, toutes fusionnées dans `main` (CI verte, 2773 tests). La livraison suit la procédure de [livraison.md](../technique/livraison.md). Suivi détaillé : [feuille-de-route.md](feuille-de-route.md).

« Migration additive » = ajout d'une colonne ou d'une table, sans toucher aux données existantes.

## 1. Devis et factures, spécification v2 (PR #380 à #385)

| PR | Ce qui a changé | Migration |
|---|---|---|
| #380 | Mentions de la spécification v2 sur les PDF des devis, factures et avoirs. | — |
| #381 | Réglages de facturation sur la structure et sur l'organisateur. | `tenants/0018`, `addressbook/0019` (additives) |
| #382 | Acceptation du devis, n° de bon de commande, date d'échéance. | `documents/0013` (additive) |
| #384 | Règles du Radar sur les devis et factures : SIREN, licence, médiateur, total, devis expiré. | — |
| #385 | Types de lignes et unités fermés ; facture de solde avec l'acompte déduit. | `documents/0014` |
| #386 | Documentation : spécification du contrat, archivage des anciennes spécifications, plan du chantier. | — |

## 2. Contrat de cession, spécification du 13/11 (PR #387 à #392)

Direction : un seul contrat, avec deux variantes de l'article 5 (avec ou sans TVA) choisies par le régime de TVA de la structure. Plus de choix de modèle pour l'utilisateur. Sources : `docs/metier/sources-associees/01` à `03`.

| PR | Étape | Ce qui a changé | Migration |
|---|---|---|---|
| #387 | A | **Structure** : texte d'exonération de TVA, date de confirmation du régime, détails de la licence (catégories, validité, motif de dispense), contact de production. | `tenants/0019` (additive) |
| #388 | B | **Organisateur** : nature juridique, signataire et habilitation confirmée, licence ou dispense, contact administratif. | `addressbook/0020` (additive) |
| #389 | C | **Fiche « Contrat » de la date** : intérieur ou plein air (repli, référents), transport, frais supplémentaires, « le prix comprend », acompte oui/non, modalités de facturation, contact sur place. SACEM renommé « programme type ». | `gigs/0014`, `catalog/0008` (additives) |
| #390 | D | **Moteur de contrôles** : anomalies bloquantes, à confirmer ou simples avertissements, groupées par écran ; confirmations enregistrées ; version « à actualiser » ; bandeau « BROUILLON — INFORMATIONS INCOMPLÈTES » ; Radar RAD-10 recâblée. | `documents/0015` (additive) |
| #391 | E | **Contrat unique** : un seul gabarit (`contract.html`), variante de l'article 5 par `contract_variant`. Chaque version fige le régime fiscal et l'identité des deux parties. Les quatre anciens gabarits et leurs tests sont retirés. | `documents/0016` (**supprime des colonnes**) |
| #392 | F | **Annexes et PDF unique** : contrat + fiche technique du spectacle + fiche d'accueil générée, assemblés avec pypdf. Titre, date, empreinte et pages de chaque annexe gardés par version. Génération bloquée sans fiche technique ; annexe illisible ou de plus de 10 Mo = erreur explicite. | `documents/0017` (additive) |

Le contrat n'imprime plus l'IBAN (la spec renvoie au relevé d'identité bancaire), ni la configuration de la salle, les minutes de balances, la distribution, le code APE, les conditions particulières ni la ville du tribunal.

## 3. À vérifier avant de livrer (liste de contrôle de livraison.md)

1. **Migration `documents/0016` : règle 2 non respectée.** Elle supprime les colonnes `template` de `Contract` et `ContractVersion` et contient une petite migration de données (la variante des anciennes versions est calculée d'après le régime de TVA actuel de leur structure). Aucun PDF n'est modifié. Il faut **valider cette exception** avant de livrer, et faire la sauvegarde manuelle de la base le jour même.
2. **Dépendance nouvelle : `pypdf` 7.1.0** (dans `requirements/base.txt` et `constraints.txt`). Scalingo l'installe au déploiement ; aucune variable d'environnement nouvelle.
3. **Contrats existants** : les brouillons sont régénérés avec le nouveau gabarit à leur prochaine génération ; les contrats signés gardent leur PDF figé. Les anciennes versions n'ont pas d'annexes (`annexes_snapshot` vide).
4. **Données à compléter après livraison** : pour les dates existantes, « acompte demandé » est vide et la fiche technique du spectacle peut manquer. La génération définitive sera bloquée tant que ce n'est pas rempli. L'aperçu reste possible.
5. **Page publique** : le texte de la page des fonctionnalités passe de « quatre modèles » à « avec ou sans TVA selon votre structure ».

## 4. Ce qui reste du chantier contrat

- **PR G (recette)** : les 20 scénarios du §20 de la spécification, la documentation, les points pour le juriste (bp14), et le contrôle de cohérence entre la fiche d'accueil et les repas et nuitées.
- Envoi par e-mail avec les trois pièces (V2, après Brevo) et signature électronique (V3, hors MVP).
- Le rendu visuel du PDF assemblé n'a pas été vérifié dans un lecteur PDF : à faire à la recette.
