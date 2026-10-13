# Guide 2 — Le métier expliqué simplement

> Objectif : comprendre **pourquoi** chaque fonctionnalité existe, avec les yeux d'un artiste qui n'a jamais fait d'administratif.
> Ce guide simplifie volontairement. Les points juridiques et fiscaux sont signalés par ⚠️ : **à faire valider** par un professionnel (expert-comptable, juriste, CAE, syndicat) avant d'être présentés comme fiables aux utilisateurs.

---

## 1. Le contexte en 2 minutes

Un **artiste ou un groupe** (« la structure de production ») veut jouer des concerts. Quelqu'un doit gérer tout ce qui n'est pas la musique : contrats, factures, horaires, hébergement, paiements, papiers officiels. Les grosses structures ont un administrateur ; les petites (association, micro-entreprise, artiste seul) le font à la main avec Word, Excel et des SMS, en oubliant des choses et en perdant du temps.

**Ton application = un administrateur de poche** qui prend les infos d'un concert une seule fois et fabrique tous les papiers à partir de là.

### Les acteurs

| Acteur | Qui c'est | Dans l'app |
|---|---|---|
| **Artiste / structure de production** | Celui qui vend le spectacle (association, micro-entreprise…) | **L'utilisateur** (`Tenant`) |
| **Organisateur / programmateur** | Celui qui achète le concert : salle, festival, mairie, bar, association | `Promoter` (le **client**) |
| **Lieu / salle** | L'endroit où ça se passe | `Venue` |
| **Équipe** | Musiciens, technicien son/lumière, tourneur (celui qui cherche des dates) | `GigMember` |

### Deux mots à ne pas confondre
- **Prix de cession** : la somme que l'**organisateur paie à la structure** pour acheter le spectacle. C'est la recette.
- **Cachet** : la rémunération d'**un artiste** pour une représentation. C'est une dépense de la structure. Dans le langage courant, on dit parfois « mon cachet » pour désigner le prix demandé ; dans l'app, on distingue les deux.

### Cession ou engagement ?
- **Contrat de cession** (ce que fait l'app) : la structure **vend un spectacle clé en main** à l'organisateur pour un prix. La structure reste l'employeur de ses artistes et les paie elle-même.
- **Contrat d'engagement** : l'organisateur **embauche directement** les artistes. Ce n'est pas le sujet de l'app.

⚠️ Vendre des spectacles peut nécessiter une **licence / un récépissé d'entrepreneur de spectacles vivants** (catégories selon l'activité). À indiquer aux utilisateurs comme point de vigilance, sans en faire le sujet de l'app.

---

## 2. La vie d'une date (le scénario à garder en tête)

Presque toute l'application suit ce parcours. Apprends-le : chaque fonctionnalité en est une étape.

1. **Un organisateur s'intéresse** → l'artiste note la date. Statut **Option** (« je te la garde, mais rien n'est sûr »).
2. **L'organisateur confirme** → statut **Confirmé**. Ils se sont mis d'accord sur date, lieu, prix, conditions.
3. **Le contrat de cession est généré** et envoyé à l'organisateur.
4. **L'organisateur signe** → statut **Signé**. C'est le moment où la date devient contractuellement sûre.
5. **Un acompte est facturé** (souvent une partie du prix, payée avant). Il peut y avoir un **devis** avant.
6. **La logistique se prépare** : qui vient, à quelle heure, où dormir, où manger, qui contacter sur place → la **feuille de route**, envoyée à l'équipe.
7. **Le concert a lieu.**
8. **La facture de solde est émise** (le reste du prix), l'organisateur paie.
9. **L'artiste paie son équipe et note ses dépenses** (essence, hébergement, location de matériel…).
10. **Bilan** : la date a-t-elle rapporté de l'argent ? Le comptable reçoit un export.

Une date peut aussi être **Annulée** (à toute étape). L'app doit le gérer proprement (sans effacer l'historique).

---

## 3. Les fonctionnalités, une par une

### 3.1 Carnet d'adresses (organisateurs, lieux, contacts)

- **À quoi ça sert** : ne **jamais ressaisir** les infos d'un organisateur (nom, SIRET, adresse de facturation, contact). On les saisit une fois, on les réutilise à chaque contrat et facture.
- **Situation réelle** : l'artiste rejoue tous les ans dans le même festival. Aujourd'hui il recopie l'adresse à chaque fois, avec des erreurs.
- **Ce que fait l'app** : fiches `Promoter` (qui facture-t-on ?), `Venue` (où joue-t-on ?), `Contact` (qui appeler ?). Recherche instantanée.
- **Pourquoi Promoter ≠ Venue** : une mairie (organisateur, à facturer) programme dans une salle municipale (lieu). Le régisseur qu'on appelle le jour J est rattaché à la **salle**, pas à la mairie.
- **Simplification MVP** : champs essentiels seulement (nom, adresse, SIRET, contact principal).

### 3.2 Le suivi des statuts d'une date

- **À quoi ça sert** : voir d'un coup d'œil où en est chaque date et ce qu'il reste à faire.
- **Statuts** : `Option → Confirmé → Signé`, plus `Annulé`. « Réalisé » (date passée) et « Payé » (facture soldée) ne sont pas des statuts : ce sont des **indicateurs calculés** affichés à côté.
- **Pourquoi c'est utile** : une option qui traîne bloque une date qu'on aurait pu vendre à quelqu'un d'autre. Un contrat non signé la veille du concert est un risque.
- **Ce que fait l'app** : un statut par date, des transitions autorisées (on ne passe pas de Option à Signé sans contrat), un affichage coloré.
- **Plus tard (v1)** : **relances automatiques** (« l'option expire dans 7 jours », « le contrat n'est pas signé »).

### 3.3 Contrat de cession

- **À quoi ça sert** : c'est le **document qui protège les deux parties** : l'artiste sera payé, l'organisateur aura son spectacle. Il fixe : qui, quoi, quand, où, combien, conditions techniques, annulation, paiement.
- **Situation réelle** : beaucoup d'artistes jouent sur une poignée de main ou un mail, puis n'ont aucun recours en cas d'annulation ou d'impayé.
- **Ce que fait l'app** : à partir d'un **modèle type**, elle **pré-remplit** le contrat avec les infos de la date (artiste, organisateur, date, lieu, prix, conditions) et produit un **PDF propre**. L'utilisateur ne rédige rien.
- **Contenu habituel** : identité des parties, description du spectacle, date/lieu/horaires, prix de cession (HT/TTC), modalités de paiement (acompte, solde, délais), conditions techniques (fiche technique, loges, repas, hébergement), clause d'annulation, assurance/responsabilité, droits d'auteur (SACEM, à la charge de l'organisateur en général).
- **⚠️ Point critique** : les modèles doivent être **relus par un juriste ou repris de modèles de référence** (organismes professionnels comme le CNM, des syndicats). Vérifie les **droits de réutilisation** avant de les intégrer. Ne rédige pas toi-même les clauses.
- **Signature électronique (v1)** : permettre de signer en ligne au lieu d'imprimer/scanner. On **achète** ce service (Yousign ou équivalent).
- **MVP** : un modèle unique de contrat, PDF téléchargeable, statut « signé » marqué manuellement.

### 3.4 Devis et factures

- **Devis** : une proposition de prix, avant l'accord. **Facture** : la demande de paiement officielle après (ou pour) la prestation.
- **À quoi ça sert** : se faire payer, **légalement** et proprement. La facture est aussi le document que le comptable réclame.
- **Ce que fait l'app** : génère devis et factures depuis la date (client, montant, TVA, échéance), avec numérotation automatique et PDF.
- **Règles à comprendre** :
  - **Numérotation** : chronologique et **sans trou** (2026-001, 2026-002…). C'est une obligation ; un trou peut alerter un contrôle fiscal.
  - **Immuable** : une facture émise ne se modifie plus. Pour corriger, on émet un **avoir** (facture négative).
  - **Mentions obligatoires** : identité des parties, SIRET, adresse, date, numéro, désignation, prix HT, TVA, total TTC, conditions de paiement, pénalités de retard…
  - **TVA** : selon le statut, la structure facture avec TVA, ou est en **franchise** (mention du type « TVA non applicable, article 293 B du CGI »). ⚠️ Le régime des associations est particulier : à faire valider. L'app doit permettre de choisir le régime dans les infos de la structure.
- **Acompte / solde** : une date peut donner lieu à **deux factures** (acompte puis solde). Il faut suivre laquelle est payée.
- **⚠️ Facture électronique** : à partir du **1er septembre 2027**, l'émission de factures électroniques via une plateforme agréée devient obligatoire pour les micro-entreprises et PME. Le MVP génère des PDF ; la conformité (format Factur-X) est prévue en v1.

### 3.5 Suivi de trésorerie (recettes / dépenses)

- **À quoi ça sert** : répondre à « cette date m'a-t-elle rapporté de l'argent ? » et « qui me doit quoi ? ».
- **Ce que fait l'app** : pour chaque date, on voit ce qui doit rentrer (facturé), ce qui est rentré (payé), ce qui est sorti (dépenses), et le **résultat**.
- **Catégories de dépenses** : cachets, transport, hébergement, technique (location de matériel, sonorisation), communication, autres.
- **Suivi des paiements** : `Payment` = argent reçu. Un statut par facture : à payer / acompte reçu / soldée / en retard.
- **Tableau de bord** : total facturé, total encaissé, factures en retard, dates sans contrat.
- **Export CSV/Excel** : le fichier qu'on remet au comptable en fin d'année. C'est un vrai gain de temps pour lui, donc un argument de vente.
- **Ce que l'app NE fait PAS** : ce n'est pas un logiciel de comptabilité (pas de plan comptable, pas de bilan, pas de déclaration de TVA). C'est un **suivi simplifié**.
- **Connecteur CAE / expert-comptable** : hors périmètre, l'export CSV suffit.

### 3.6 Charges sociales (GUSO, intermittence) — **hors MVP**

- **Contexte** : les artistes sont généralement **salariés** pour leurs prestations. Payer un cachet implique un salaire, des cotisations sociales, une déclaration.
- **GUSO** (Guichet unique du spectacle occasionnel) : un service qui permet aux employeurs *occasionnels* (par ex. des associations) de déclarer et payer les cotisations en une seule démarche.
- **Intermittence** : régime d'assurance chômage spécifique aux artistes et techniciens, lié à un nombre d'heures travaillées par an.
- **Pourquoi c'est exclu** : c'est un métier à part entière, très réglementé, avec des risques d'erreurs qui engageraient ta responsabilité. Le prompt client le demande ; la bonne réponse est « **plus tard, avec un expert, ou jamais** ». En attendant, l'app peut enregistrer le montant des cachets comme dépense, sans calculer les charges.

### 3.7 Feuille de route

- **À quoi ça sert** : le jour J, chaque membre de l'équipe sait **où aller, quand, avec qui, où dormir, où manger**, sans avoir à poser 15 questions au responsable.
- **Situation réelle** : aujourd'hui, c'est un long message WhatsApp ou un PDF bricolé, envoyé tard et jamais à jour.
- **Contenu type** :
  - **Lieu** : adresse, accès, parking ;
  - **Horaires** : arrivée, chargement, **balances** (répétition technique avant le concert, aussi dite « soundcheck »), repas, concert, démontage, départ ;
  - **Contacts sur place** : régisseur, organisateur, en-cas d'urgence ;
  - **Hébergement** : adresse, horaires d'arrivée ;
  - **Repas** (« catering ») : quand, où, régimes alimentaires ;
  - **Notes** : loges, parking camion, code d'accès…
- **Ce que fait l'app** : la génère à partir des infos de la date, en **version mobile** lisible d'un coup d'œil, partagée par un **lien secret** (pas besoin de créer un compte pour les musiciens), et exportable en PDF.
- **Plus tard (v1)** : consultation **hors-ligne** (utile en sous-sol de salle sans réseau), via une PWA.
- **Rôle « technicien invité »** : le lien secret le remplace en MVP.

### 3.8 Calendrier de tournée

- **À quoi ça sert** : voir toutes les dates sur une ligne de temps, repérer les trous et les conflits (deux dates trop proches, éloignées de 800 km).
- **MVP** : vue **liste** et vue **calendrier mensuel**, filtres par statut et par mois.
- **v1** : **export iCal** (une date s'ajoute dans Google Agenda / Apple Calendrier) : simple à faire, très apprécié.
- **v2** : **carte** avec distances et temps de trajet (API de calcul d'itinéraire) : utile pour le budget transport, mais complexe et coûteux.

### 3.9 Gestion de la structure

- **À quoi ça sert** : centraliser les **infos légales** de l'artiste (nom, forme juridique, SIRET, TVA, adresse, IBAN, licence) qui alimentent automatiquement les contrats et factures. Et **ne rien oublier** d'administratif.
- **MVP** : une page « Ma structure » avec ces infos. Elles sont copiées dans chaque document émis.
- **v1** : **rappels d'échéances** (déclaration de chiffre d'affaires, cotisations, assemblée générale annuelle d'une association) + **bibliothèque de documents types** (statuts, modèles de convention…).
- **Hors périmètre** : « aide au choix du statut juridique » (association, auto-entrepreneur, CAE…). C'est du conseil personnalisé. On peut proposer un **article ou un lien** vers des ressources fiables.
- **CAE** (coopérative d'activité et d'emploi, par ex. Crealead) : structure qui héberge juridiquement l'activité d'un artiste, gère sa facturation et sa paie. Certains utilisateurs y seront ; l'app doit pouvoir facturer **au nom de** la CAE (infos légales adaptables).

### 3.10 Multi-utilisateurs, rôles, onboarding, freemium

- **Comptes** : chaque personne a son compte ; plusieurs personnes peuvent faire partie d'une même structure.
- **Rôles simples** : `owner` (tout faire) / `member` ; « invité en lecture » plus tard.
- **Onboarding < 10 min** : au premier lancement, un assistant en quelques écrans (nom de la structure, forme juridique, SIRET, premier spectacle, première date) avec des **modèles pré-remplis**. Un utilisateur qui a un contrat PDF en 10 minutes est un utilisateur conquis.
- **Freemium** : gratuit jusqu'à 3 dates par an, puis abonnement bas. Justification : les artistes émergents n'ont presque pas de revenus. Techniquement : un champ « plan » sur la structure et une vérification de quota ; le paiement (Stripe) vient en v1.

⚠️ **À arbitrer** : la note de cadrage technique du 29/09 propose de remplacer ce freemium par deux formules payantes dès le départ (« Essentiel » / « Collectif »). Voir Q9, `docs/cadrage/03-cahier-des-charges.md` §14 — non tranché à ce jour, ce guide garde la description du freemium tant que ce n'est pas confirmé.

---

## 4. Ce que le client a demandé vs ce qu'on fait vraiment

| Demande du client | Décision | Pourquoi |
|---|---|---|
| Contrats de cession PDF | **MVP** | Cœur de valeur |
| Carnet d'adresses | **MVP** | Évite la ressaisie |
| Statuts de date | **MVP** | Vision du cycle de vie |
| Devis / factures | **MVP** | Se faire payer |
| Relances automatiques | v1 | Nécessite e-mails + tâches planifiées |
| Signature électronique | v1 (achetée) | Valeur juridique, ne se code pas |
| Suivi recettes/dépenses | **MVP** simplifié | Utile mais pas de la compta |
| Export CSV | **MVP** | Argument de vente pour le comptable |
| Calcul GUSO / charges | Hors périmètre | Responsabilité juridique |
| Connecteur expert-comptable / CAE | Hors périmètre | Trop spécifique |
| Feuille de route | **MVP** | Forte valeur perçue, simple |
| Hors-ligne | v1 (PWA) | Complexe, pas indispensable au début |
| Calendrier liste/mois | **MVP** | Simple |
| Export iCal | v1 | Facile, très demandé |
| Carte + trajets | v2 | Coûteux |
| Aide statut juridique | Hors périmètre | Conseil personnalisé |
| Rappels d'échéances | v1 | Après les usages de base |
| Rôles (artiste, technicien invité) | MVP simple + lien secret | Le reste plus tard |

---

## 5. Les questions à poser à de vrais artistes (Phase 0)

Ton meilleur atout pour compenser le manque de connaissance métier : **écouter 5 à 10 personnes**.

1. Montre-moi comment tu gères ta dernière date, de la prise de contact au paiement. (Demande à voir les fichiers, tableurs, messages.)
2. Quelle étape te fait perdre le plus de temps ? Laquelle te stresse le plus ?
3. As-tu déjà eu un impayé, une annulation, un contrat manquant ? Que s'est-il passé ?
4. Comment fais-tu tes contrats ? Qui te les a fournis ?
5. Comment envoies-tu les infos à ton équipe le jour J ?
6. Comment fais-tu ta comptabilité ? Qui t'aide ? Que te demande ton comptable ?
7. Quel est ton statut (asso, micro, CAE, autre) ? Combien de dates par an ?
8. Combien serais-tu prêt à payer par mois pour un outil qui fait ça ?
9. Qu'utilises-tu aujourd'hui (Orfeo, Bob Booking, Excel, Word) et qu'est-ce qui t'agace ?

**Consigne** : ne présente pas ton produit, **observe**. Note les mots qu'ils utilisent : ils deviendront le vocabulaire de l'interface.

---

## 6. Mini-glossaire

| Terme | Sens simple |
|---|---|
| **Spectacle vivant** | Concert, théâtre, danse, cirque… tout ce qui se joue devant un public |
| **Cession** | Vente d'un spectacle à un organisateur |
| **Cachet** | Salaire d'un artiste pour une représentation |
| **Organisateur / diffuseur / programmateur** | Celui qui achète et programme le spectacle |
| **Tourneur / booker** | Professionnel qui cherche des dates pour un artiste |
| **Option** | Date réservée provisoirement |
| **Fiche technique** | Liste du matériel et besoins techniques (son, lumière, scène) |
| **Balances / soundcheck** | Réglages sonores avant le concert |
| **Régie / régisseur** | Technique de la salle / la personne qui s'en occupe |
| **Catering** | Repas et boissons fournis à l'équipe |
| **Défraiements** | Remboursement de frais (transport, repas) |
| **Acompte / solde** | Partie payée à l'avance / le reste |
| **Avoir** | Facture négative qui annule ou corrige une facture |
| **Franchise en base de TVA** | Régime où l'on ne facture pas la TVA |
| **CAE** | Coopérative qui héberge l'activité d'entrepreneurs (ex. Crealead) |
| **GUSO** | Guichet simplifié pour employeurs occasionnels du spectacle |
| **Intermittence** | Régime d'assurance chômage des artistes et techniciens |
| **SACEM** | Société qui collecte les droits d'auteur de la musique |
| **CNM** | Centre national de la musique |
| **Licence / récépissé d'entrepreneur de spectacles** | Autorisation administrative pour produire ou diffuser des spectacles |