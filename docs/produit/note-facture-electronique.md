# Note — Facture électronique et Factur-X

**Rédigée le 2026-11-02.** Note de réflexion, **rien n'est codé** (Phase 5 de la feuille de route, hors MVP). Elle sert à décider quoi faire et à préparer la question au comptable.

> **Fiabilité.** Les dates viennent de la page officielle de l'administration (service-public). Les cas particuliers (franchise de TVA, associations, e-reporting) viennent de sites de cabinets comptables et d'éditeurs, **pas d'une source officielle** : les sources ne sont pas toujours d'accord entre elles. **À faire confirmer par le comptable avant toute décision.** Les règles ont déjà changé de calendrier plusieurs fois.

## 1. En bref
- **Factur-X** : un PDF (lisible par une personne) qui contient un fichier XML (lisible par un logiciel). C'est l'un des trois formats acceptés (avec UBL et CII, qui sont du XML seul).
- Le PDF actuel de Bòrd Pro **n'est pas** une facture électronique au sens de la réforme.
- Les factures électroniques doivent **transiter par une plateforme agréée** (PA), pas être envoyées directement par e-mail. Bòrd Pro n'est pas une PA et ne le deviendra pas.
- Échéance qui concerne nos utilisateurs : **1er septembre 2027** pour l'émission (PME, micro-entreprises), avec l'e-reporting au même calendrier.
- **Recommandation** : produire un fichier Factur-X téléchargeable que l'utilisateur dépose sur sa plateforme (option B ci-dessous), après avis du comptable. Une connexion directe à une plateforme (option C) se décide plus tard, sur les retours de la bêta.

## 2. Ce que dit la réforme

| | Réception | Émission | E-reporting |
|---|---|---|---|
| Grandes entreprises et ETI | 1er sept. 2026 | 1er sept. 2026 | idem |
| PME et micro-entreprises | **1er sept. 2026** | **1er sept. 2027** | idem |

- **Champ** : opérations entre entreprises établies en France et assujetties à la TVA. Les non-assujettis semblent hors champ pour la facture électronique.
- **E-reporting** : transmission à l'administration des données des opérations qui ne passent pas par une facture électronique (ventes aux particuliers, clients étrangers, clients non assujettis). Son champ exact pour les structures non assujetties est contesté selon les sources.
- **Franchise en base de TVA** (« art. 293 B ») : d'après plusieurs sources, cela **ne sort pas** du champ. Une structure en franchise est assujettie mais non redevable.
- **Associations** : non assujetties (activité non lucrative, gestion désintéressée) = hors facture électronique ; assujetties = traitées comme les entreprises.
- **Organisateurs publics** (mairies, etc.) : ils passent déjà par **Chorus Pro** ; la nouvelle réforme se raccorde à ce dispositif. Le modèle de contrat parle déjà du bon de commande et du numéro d'engagement pour ces cas.
- Nouvelles **mentions obligatoires** sur la facture (dont le SIREN du client), selon le même calendrier.

**Conséquence pour Bòrd Pro** : ce qu'il faut produire dépend du client facturé (entreprise ou association assujettie : facture électronique ; collectivité : Chorus Pro ; particulier ou association non assujettie : au mieux e-reporting). Il faudra probablement savoir si l'organisateur est assujetti, ce que la fiche ne dit peut-être pas aujourd'hui (à vérifier dans le code le moment venu).

## 3. Les options

| | A. Rien de plus | B. Factur-X téléchargeable | C. Envoi direct à une plateforme (API) |
|---|---|---|---|
| Principe | On garde le PDF et l'export CSV ; l'utilisateur ressaisit dans sa plateforme | Bòrd Pro produit le fichier Factur-X ; l'utilisateur le dépose sur sa plateforme | Bòrd Pro envoie la facture à une plateforme agréée et suit son statut |
| Service externe | Non | Non | **Oui** (contrat, tarifs, RGPD : sous-traitant) |
| Effort de code | Nul | Moyen | Élevé |
| Pour l'utilisateur | Pénible, risque d'erreur | Un clic de plus, simple | Le plus fluide |
| Conformité affichable | Non | Non seule : la transmission reste à l'utilisateur | Oui, via la plateforme partenaire |
| Frein pour nous | Produit moins attractif en 2027 | Qualité du PDF/A-3 à valider | Statuts qui reviennent de la plateforme (retours asynchrones, alors que `CLAUDE.md` interdit Celery/Redis) ; accord explicite requis (`CLAUDE.md` §2) |

Une 4e voie, **devenir plateforme agréée**, est exclue : immatriculation par la DGFiP, hors de portée d'un projet de cette taille.

## 4. Recommandation
1. **Maintenant** : rien à coder. Poser les questions du §6 au comptable pendant la relecture des factures.
2. **Phase 5, avant septembre 2027** : option B. Un fichier Factur-X par facture ou avoir émis, généré à partir des données **déjà figées à l'émission** (cela respecte la règle d'immutabilité de `CLAUDE.md` §6.2). Aucun service externe.
3. **Après la bêta** : regarder l'option C si les testeurs la demandent, avec un partenaire choisi dans la liste officielle des plateformes immatriculées.
4. **Tant que ce n'est pas livré** : l'application ne doit pas se dire « conforme à la facturation électronique » (règle déjà notée dans `feuille-de-route.md`).

## 5. Ce que l'option B demande techniquement (aperçu)
- Un **PDF/A-3** avec polices incluses et profil de couleur, plus le XML joint (relation « Alternative »). WeasyPrint sait produire des variantes PDF/A ; **à vérifier** que la variante A-3 convient à notre gabarit `billing_pdf.html`.
- Une bibliothèque Python qui construit et valide le XML (`factur-x` est la référence ; `ads-facturx` s'appuie dessus). Nouvelle dépendance : il faudra votre accord (`CLAUDE.md` §2). Validation PDF/A avec **veraPDF** (outil externe, utile surtout pour les tests).
- Profil visé : **EN 16931** (le plus complet), à confirmer avec le comptable.
- Les données manquantes à saisir ou copier au moment de l'émission, au minimum le **SIREN du client**, probablement l'adresse de livraison et le statut d'assujettissement.
- Cela touche aux **modèles, migrations et PDF** : plan à valider avant de coder, comme le demande `CLAUDE.md` §9.
- Les **avoirs** doivent aussi sortir en Factur-X.

## 6. Questions pour le comptable
1. Mes utilisateurs types (micro-entreprise en franchise, association loi 1901, petite société) sont-ils tenus d'émettre en facture électronique au 1er sept. 2027 ? Dans quels cas seulement l'e-reporting ?
2. Pour une association **non assujettie** qui vend un spectacle : facture électronique, e-reporting, ou rien ?
3. Facture à une **collectivité** : Chorus Pro reste-t-il obligatoire séparément, ou la plateforme agréée suffit-elle ?
4. Quel profil Factur-X (Basic, EN 16931) est le plus sûr pour une prestation de spectacle ?
5. Un fichier Factur-X généré par un logiciel qui n'est pas une plateforme, puis déposé par l'utilisateur, est-il acceptable ?
6. Le calendrier de 2027 est-il toujours confirmé ?

## 7. Sources
- [Facturation numérique, service-public.gouv.fr (calendrier officiel)](https://entreprendre.service-public.gouv.fr/actualites/A15683)
- [Présentation des logos « plateforme agréée » et « solution compatible », impots.gouv.fr](https://www.impots.gouv.fr/presentation-des-logos-plateforme-agreee-et-solution-compatible)
- [Facture électronique et associations, Legifiscal](https://www.legifiscal.fr/creation-entreprise/facture-electronique-associations.html) (non officiel)
- [Associations et facturation électronique, Fiducial](https://www.fiducial.fr/facturation-electronique/actualites-conseils/associations-facturation-electronique) (non officiel)
- [`ads-facturx` sur PyPI](https://pypi.org/project/ads-facturx/) (bibliothèque ; documentation de `factur-x` non consultée directement)
