# Informations à compléter avant l'ouverture publique

> Dernière mise à jour : 2026-11-10. À cocher au fur et à mesure ; quand une ligne est faite, retirer le crochet `[À compléter]` dans le gabarit indiqué.
> La plupart de ces informations dépendent de la **structure juridique** (décision ouverte, voir `feuille-de-route.md`, « Décisions à prendre »).

## 1. Pages légales (`templates/legal/`)

Tant qu'un crochet `[À compléter]` reste, le bandeau « Texte provisoire » s'affiche (`templates/legal/_base.html`) : à retirer une fois tout rempli **et** relu par un professionnel.

| ☐ | Information | Où la mettre | Qui la fournit | Dépend de |
|---|---|---|---|---|
| ☐ | Nom de l'éditeur, forme juridique, capital, SIRET, adresse du siège | `mentions.html`, « Éditeur du site » | Associé / vous | Structure juridique créée |
| ☐ | Directeur de la publication (nom d'une personne physique) | `mentions.html`, « Éditeur du site » | Associé / vous | Idem |
| ☐ | Adresse du siège de Scalingo | `mentions.html`, « Hébergement » | À copier depuis `scalingo.com/legal-notice` (les sources trouvées se contredisent : 13 rue Jacques Peirotes ou 15 avenue du Rhin, Strasbourg) | Rien, à vérifier |
| ☐ | Conservation des factures émises après suppression du compte (obligation de 10 ans) | `privacy.html`, « Combien de temps ? » | Comptable | Relecteur professionnel |
| ☐ | Tarifs, durée, résiliation | `terms.html`, article 6 | Associé / vous | Modèle économique et page Tarifs |
| ☐ | Tribunal compétent, médiation de la consommation | `terms.html`, article 7 | Juriste | Structure juridique |

Déjà rempli (2026-11-10) : contact `contact@bordpro.fr`, hébergeur Scalingo, stockage Scaleway (Paris), e-mails Brevo, suivi d'erreurs Sentry (UE).

## 2. Site vitrine (`templates/site/`)

| ☐ | Information | Qui la fournit |
|---|---|---|
| ☐ | Textes définitifs des pages (accueil, fonctionnalités, contact) | Associé |
| ☐ | Validation du slogan | Associé |
| ☐ | Page Tarifs (trois formules prévues) | Associé, après le modèle économique |
| ☐ | Décision sur le suivi de fréquentation | Vous + associé (respect de la vie privée : aucun cookie de mesure aujourd'hui, à garder dans la confidentialité) |
| ☐ | Passage de `SITE_INDEXABLE` à `True` (variable d'environnement Scalingo) | Vous, **en dernier**, quand tout ce qui précède est fait |

## 3. Charte graphique v1.3 (en attente de l'associé)

| ☐ | Élément |
|---|---|
| ☐ | Validation des icônes de volet Social et Régie (propositions « à valider ») |
| ☐ | Nouveau fichier de l'icône RADAR sans dégradé |
| ☐ | Exports finaux du logo depuis Affinity (le fichier Régie est aujourd'hui rogné) |

## 4. Documents (contrat, factures)

| ☐ | Information | Qui |
|---|---|---|
| ☐ | Relecture professionnelle des modèles de contrat et des mentions de facture (pénalités de retard, indemnité de 40 €, TVA) ; ensuite retrait du bandeau « Modèle provisoire » (`invoicing.PDF_PROVISIONAL`) | Juriste / expert-comptable |
| ☐ | « N° de compte » de la fiche Équipe : savoir ce que l'associé entend par là | Associé |
| ☐ | Statut juridique de l'activité (facturation de l'application) | Vous + associé |

## 5. Ordre conseillé

1. Choisir la structure juridique (débloque l'éditeur, le directeur de la publication, le tribunal).
2. Définir le modèle économique (débloque les tarifs et la résiliation).
3. Faire relire pages légales, contrats et factures par un professionnel.
4. Retirer les crochets et le bandeau provisoire, valider les textes du site, puis passer `SITE_INDEXABLE` à `True`.
