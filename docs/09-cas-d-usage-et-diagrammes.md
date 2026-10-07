# Cas d'usage et diagrammes

> Illustration des fonctionnalités réalisées au 2026-10-07 (voir `08-synthese-fonctionnalites.md`).
> Les schémas sont écrits en **Mermaid** : ils s'affichent directement sur GitHub, et dans VS Code avec une extension d'aperçu Markdown qui gère Mermaid.
> Ils décrivent ce que fait le code. Les 16 premiers schémas ont été validés par l'analyseur syntaxique de Mermaid le 03/10 ; ceux ajoutés le 07/10 (cas d'usage UC19 à UC22, séquence 4.10, états 5.4, architecture) ne l'ont pas été. Le rendu visuel n'a pas été contrôlé à l'œil, signalez tout schéma qui s'affiche mal.

Sommaire : 1. Acteurs · 2. Cas d'usage · 3. Parcours complet d'une date · 4. Diagrammes de séquence · 5. Cycles de vie (états) · 6. Modèle de données · 7. Architecture.

---

## 1. Acteurs

| Acteur | Rôle | Dans l'application |
|---|---|---|
| **Artiste / propriétaire** | Utilise l'application pour gérer ses dates | Accès complet, seul à modifier « Ma structure » |
| **Membre** | Autre personne de la même structure | Accès aux données, consulte « Ma structure » sans la modifier |
| **Organisateur** | Le client (mairie, festival, salle, association…) | **N'a pas de compte** : reçoit les PDF par l'artiste, signe hors de l'application |
| **Équipe sur la route** | Musiciens, techniciens, accompagnants | **N'a pas de compte** : ouvre la feuille de route avec le lien secret que l'artiste lui envoie |
| **Visiteur** | Toute personne sur le site | Lit les pages légales sans compte |
| **Système** | L'application elle-même | Numérote, fige, génère les PDF, contrôle l'accès, purge les comptes supprimés après 30 jours |

---

## 2. Cas d'usage

### 2.1 Vue d'ensemble

```mermaid
flowchart LR
    artiste(["Artiste / propriétaire"])
    membre(["Membre"])
    orga(["Organisateur<br/>(sans compte)"])
    equipe(["Équipe<br/>(sans compte)"])
    visiteur(["Visiteur<br/>(sans compte)"])

    subgraph app["Application Spectacle Vivant"]
        direction TB
        UC1(["Créer son compte et sa structure"])
        UC2(["Renseigner Ma structure"])
        UC3(["Gérer organisateurs, lieux, contacts"])
        UC4(["Gérer ses spectacles"])
        UC5(["Créer une date"])
        UC6(["Suivre et filtrer ses dates<br/>liste et calendrier"])
        UC7(["Confirmer, annuler, réactiver une date"])
        UC8(["Compléter la date"])
        UC9(["Générer le contrat de cession"])
        UC10(["Marquer le contrat signé"])
        UC11(["Créer un devis ou une facture"])
        UC12(["Émettre un document"])
        UC13(["Corriger par un avoir"])
        UC14(["Télécharger les PDF"])
        UC15(["Préparer et partager<br/>la feuille de route"])
        UC16(["Enregistrer un paiement"])
        UC17(["Noter une dépense"])
        UC18(["Suivre ses finances<br/>bilan, tableau de bord, export CSV"])
        UC19(["Exporter ses données"])
        UC20(["Demander ou annuler la suppression<br/>de la structure"])
        UC21(["Quitter la structure"])
        UC22(["Lire les pages légales"])
    end

    artiste --- UC1
    artiste --- UC2
    artiste --- UC3
    artiste --- UC4
    artiste --- UC5
    artiste --- UC6
    artiste --- UC7
    artiste --- UC8
    artiste --- UC9
    artiste --- UC10
    artiste --- UC11
    artiste --- UC12
    artiste --- UC13
    artiste --- UC14
    artiste --- UC15
    artiste --- UC16
    artiste --- UC17
    artiste --- UC18
    artiste --- UC19
    artiste --- UC20
    membre --- UC21
    visiteur --- UC22
    artiste --- UC22
    membre --- UC3
    membre --- UC5
    membre --- UC6
    membre --- UC16
    membre --- UC17
    UC9 -.->|"PDF envoyé"| orga
    orga -.->|"signe hors de l'application"| UC10
    UC12 -.->|"PDF envoyé"| orga
    UC15 -.->|"lien secret"| equipe
```

Le membre fait tout ce que fait l'artiste **sauf modifier « Ma structure »** (il la consulte), exporter les données ou demander la suppression (réservés au propriétaire) ; il peut en revanche quitter la structure. Il est représenté sur les cas principaux pour la lisibilité (le diagramme n'en montre qu'une partie).

### 2.2 Fiches des cas d'usage principaux

**UC1 — Créer son compte et sa structure**
- *Déclencheur* : première connexion.
- *Scénario* : l'utilisateur s'inscrit → est redirigé vers « Bienvenue » → saisit le nom, la forme juridique, le régime de TVA → la structure et son lien propriétaire sont créés → il arrive sur l'assistant de création d'une date.
- *Résultat* : une structure vide, isolée de toutes les autres.

**UC5 — Créer une date** (assistant en 5 étapes)
- *Scénario* : choisir ou créer un spectacle → un organisateur → un lieu → saisir date, prix HT, fin d'option, conditions → relire le récapitulatif → valider.
- *Cas d'erreur* : une étape sautée renvoie à l'étape 1 ; un spectacle, organisateur ou lieu d'une autre structure est refusé même si son identifiant est falsifié.
- *Résultat* : une date au statut « option ».

**UC7 — Confirmer, annuler, réactiver**
- *Règles* : option → confirmée ; confirmée ou signée → annulée ; l'annulation demande une confirmation et garde l'historique ; la réactivation remet « en option » (ou « signée » si le contrat est signé).
- *Cas d'erreur* : une transition interdite est refusée avec un message (un double clic ne rejoue rien).

**UC9 — Générer le contrat**
- *Précondition* : date non annulée.
- *Scénario* : « Compléter la date » (facultatif) → « Aperçu » → « Générer le contrat » → une version numérotée est enregistrée → téléchargement.
- *Variante* : régénérer ajoute une version, les anciennes restent.
- *Cas d'erreur* : date annulée sans contrat → refus ; contrat signé → plus de génération.

**UC10 — Marquer le contrat signé**
- *Préconditions* : date confirmée et au moins une version générée.
- *Scénario* : « Marquer comme signé » → écran « Vous allez figer la version N » → l'artiste confirme que la signature a eu lieu hors de l'application, ajoute éventuellement le scan → la version est figée, le contrat et la date passent à « signée ».
- *Cas d'erreur* : fichier qui n'est pas un PDF ou de plus de 10 Mo → refusé ; date non confirmée → refusé.

**UC11/UC12 — Créer puis émettre une facture**
- *Scénario* : « Devis et factures » → « Facture d'acompte » → brouillon avec la ligne suggérée (30 % du prix) → ajuster les lignes → s'il manque une information, la page la liste → « Émettre » → confirmation → numéro attribué, informations figées, PDF créé.
- *Cas d'erreur* : adresse, SIRET, numéro ou taux de TVA, ou adresse de facturation manquants → émission refusée avec la liste ; document déjà émis → refusé, aucun numéro consommé.

**UC13 — Corriger par un avoir**
- *Précondition* : facture émise avec un montant encore créditable.
- *Scénario* : « Créer un avoir » → brouillon qui reprend les lignes en négatif (modifiable pour un avoir partiel) → « Émettre ».
- *Règles* : un avoir ne dépasse jamais la facture ; un avoir total marque la facture « Annulée par avoir ».

**UC15 — Préparer et partager la feuille de route**
- *Scénario* : sur la fiche de la date, « Feuille de route » → les créneaux Arrivée, Balances et Concert sont pré-remplis avec les horaires de la date → l'artiste ajoute des créneaux, l'hébergement, les repas, l'équipe et des notes → « Activer le partage » → il copie le lien et l'envoie à l'équipe.
- *Ce que voit l'équipe* : une page lisible sur téléphone, sans compte : lieu, programme, hébergement, repas, équipe, contacts du lieu, boutons « Appeler », « Itinéraire » et « Copier l'adresse », export PDF. **Jamais** le prix, les conditions, le contrat, les factures, l'organisateur facturé ni les e-mails.
- *Cas d'erreur* : lien inconnu ou partage arrêté → page introuvable (404). « Arrêter le partage » tue le lien pour de bon ; réactiver en crée un nouveau.

**UC16 — Enregistrer un paiement**
- *Précondition* : facture émise (ni brouillon, ni avoir, ni annulée).
- *Scénario* : « Paiements et dépenses » → sur la facture, saisir montant, date et mode (le reste à payer est proposé) → la facture passe à « Payée » quand le total est atteint.
- *Cas d'erreur* : un paiement qui dépasse le reste à payer est refusé ; un montant nul ou négatif aussi. Un paiement peut être modifié ou supprimé : la facture revient alors à « Émise » si le total n'est plus atteint.

**UC17 — Noter une dépense**
- *Scénario* : « Paiements et dépenses » → catégorie, libellé, montant, date, justificatif facultatif (PDF, JPEG ou PNG, 10 Mo maximum).
- *Cas d'erreur* : un fichier qui n'est pas un vrai PDF ou une vraie image est refusé, même avec la bonne extension.

**UC18 — Suivre ses finances**
- *Bilan d'une date* : prévu, facturé, encaissé, reste à encaisser, dépensé, résultat (encaissé moins dépensé), en TTC et en euros entiers à l'affichage.
- *Tableau de bord* (page d'accueil) : facturé et encaissé de l'année, factures à encaisser (avec le retard), dates confirmées sans contrat, prochaines dates.
- *Export CSV* : factures et avoirs, recettes, dépenses, sur la période choisie, prêts pour Excel ou le comptable.

**UC19 — Exporter ses données**
- *Scénario* : « Ma structure » → « Exporter mes données » → un ZIP est téléchargé : CSV (spectacles, organisateurs, lieux, contacts, dates, finances) et fichiers stockés (contrats, PDF, justificatifs).
- *Isolation* : le ZIP ne contient que les données de sa propre structure.

**UC20 — Demander ou annuler la suppression de la structure**
- *Précondition* : être propriétaire.
- *Scénario* : « Supprimer ma structure » → l'utilisateur saisit le nom de la structure et son mot de passe → la suppression est **programmée à 30 jours** ; elle peut être annulée pendant ce délai. Passé le délai, la commande `purge_deleted_tenants` efface les données et les fichiers.
- *Cas d'erreur* : nom ou mot de passe faux → refus ; un simple membre → accès refusé ; demander deux fois garde la première date.
- ⚠️ Les factures émises sont supprimées avec le reste : conservation légale de 10 ans à valider avec un comptable.

**UC21 — Quitter la structure**
- *Scénario* : un membre clique sur « Quitter » et perd l'accès aux données de la structure.
- *Cas d'erreur* : le dernier propriétaire ne peut pas partir (il doit supprimer la structure ou la confier).

**UC22 — Lire les pages légales**
- *Scénario* : sans compte, ouvrir mentions légales, conditions d'utilisation ou confidentialité. Les textes sont des gabarits provisoires (« [À compléter] ») avant relecture.

---

## 3. Parcours complet d'une date

```mermaid
flowchart TD
    A([Compte et structure]) --> B[Créer la date<br/>statut : option]
    B --> C{L'organisateur<br/>confirme ?}
    C -- non --> X[Annuler la date]
    C -- oui --> D[Confirmer la date<br/>statut : confirmée]
    D --> E[Compléter la date<br/>horaires, conditions, acompte]
    E --> F[Générer le contrat<br/>version 1, référence C-2026-001]
    F --> G[Envoyer le PDF à l'organisateur]
    G --> H[Signature hors de l'application]
    H --> I[Marquer le contrat signé<br/>PDF figé, statut : signée]
    I --> J[Facture d'acompte<br/>F-2026-0001]
    J --> K[Facture de solde<br/>F-2026-0002]
    K --> M[Feuille de route<br/>partagée par lien secret]
    K --> P[Paiements reçus<br/>facture payée]
    P --> Q[Bilan de la date et<br/>tableau de bord]
    Q --> L[("Export CSV<br/>pour le comptable")]
    X --> R[Réactiver si besoin]
    R --> B
```

La feuille de route se prépare dès que la date existe ; elle est placée ici par commodité. Les dépenses se saisissent à tout moment et alimentent le bilan.

---

## 4. Diagrammes de séquence

### 4.1 Création d'une date par l'assistant

```mermaid
sequenceDiagram
    actor U as Artiste
    participant N as Navigateur (HTMX)
    participant V as Vues de l'assistant
    participant S as Session
    participant DB as Base de données

    U->>N: Choisit un spectacle (étape 1)
    N->>V: POST étape 1
    V->>S: Mémorise show_id
    V-->>N: Étape 2 (fragment HTML)
    Note over U,N: Idem organisateur, lieu, détails
    U->>N: Valide le récapitulatif
    N->>V: POST récapitulatif
    V->>DB: Relit spectacle, organisateur, lieu AVEC le filtre de la structure
    alt Un identifiant appartient à une autre structure
        DB-->>V: Introuvable
        V-->>N: 404
    else Tout est valide
        V->>DB: Crée la date (structure posée côté serveur, statut option)
        V-->>N: Redirection vers la fiche de la date
    end
```

### 4.2 Génération d'une version de contrat

```mermaid
sequenceDiagram
    actor U as Artiste
    participant V as Vue ContractGenerate
    participant SV as Service contrat
    participant DB as Base de données
    participant W as WeasyPrint
    participant ST as Stockage privé

    U->>V: POST "Générer le contrat"
    V->>SV: generate_contract_pdf(date, utilisateur)
    SV->>DB: Verrouille le contrat (select_for_update)
    alt Contrat signé
        SV-->>V: Contrat inchangé
    else Date annulée sans contrat
        SV-->>V: Refus
    else Cas normal
        opt Première génération
            SV->>DB: Verrouille la séquence, numéro suivant
            SV->>DB: Enregistre la référence C-2026-001
        end
        SV->>W: Rend le gabarit HTML en PDF
        W-->>SV: Octets du PDF
        SV->>ST: Enregistre le fichier (dossier uuid)
        SV->>DB: Ajoute la version N+1
        SV-->>V: Contrat à jour
    end
    V-->>U: Redirection vers la page du contrat
```

### 4.3 Marquage « signé »

```mermaid
sequenceDiagram
    actor U as Artiste
    participant V as Vue ContractSign
    participant F as Formulaire PDF
    participant SV as Service contrat
    participant DB as Base de données

    U->>V: GET signer
    V-->>U: Confirmation "figer la version N"
    U->>V: POST (scan facultatif)
    V->>F: Valide : taille 10 Mo max, début de fichier %PDF
    alt Fichier refusé
        F-->>V: Erreur
        V-->>U: Formulaire avec message
    else Fichier valide ou absent
        V->>SV: mark_contract_signed(date, scan)
        SV->>DB: Début de transaction, verrouille le contrat
        SV->>SV: Vérifie : version existante, pas déjà signé, date confirmée
        SV->>DB: Date passe à signée (transition contrôlée)
        SV->>DB: Contrat signé, signed_at, signed_version figée
        SV->>DB: Fin de transaction
        V-->>U: "Le contrat est marqué signé"
    end
```

Tout se passe dans une seule transaction : le contrat et la date sont signés ensemble, ou pas du tout.

### 4.4 Émission d'une facture

```mermaid
sequenceDiagram
    actor U as Artiste
    participant V as Vue DocumentIssue
    participant SV as Service facturation
    participant DB as Base de données
    participant W as WeasyPrint
    participant ST as Stockage privé

    U->>V: GET émettre
    V-->>U: Confirmation "ne pourra plus être modifié"
    U->>V: POST émettre
    V->>SV: issue_invoice(facture)
    SV->>DB: Début de transaction, verrouille la facture
    SV->>SV: Vérifie : brouillon, au moins une ligne, informations complètes
    alt Il manque une information
        SV-->>V: Erreur avec la liste
        V-->>U: Message, la facture reste brouillon
    else Tout est complet
        SV->>DB: Recalcule les totaux depuis les lignes
        SV->>SV: Copie émetteur et client dans les instantanés
        SV->>DB: Verrouille la séquence, numéro F-2026-000N
        SV->>W: Rend le PDF depuis les instantanés
        W-->>SV: Octets du PDF
        SV->>ST: Enregistre le PDF (dossier uuid)
        SV->>DB: Statut émise, numéro, dates, PDF
        SV->>DB: Fin de transaction
        V-->>U: "Le document est émis : numéro F-2026-000N"
    end
    Note over SV,DB: Si le PDF échoue, tout est annulé :<br/>la facture reste brouillon, le numéro est rendu
```

### 4.5 Avoir

```mermaid
sequenceDiagram
    actor U as Artiste
    participant V as Vues facturation
    participant SV as Service facturation
    participant DB as Base de données

    U->>V: POST "Créer un avoir" sur la facture émise
    V->>SV: create_credit_note(facture)
    SV->>DB: Brouillon d'avoir, lignes de la facture en négatif
    V-->>U: Page du brouillon d'avoir
    opt Avoir partiel
        U->>V: Modifie les lignes
    end
    U->>V: POST émettre
    V->>SV: issue_invoice(avoir)
    SV->>DB: Verrouille l'avoir ET la facture d'origine
    SV->>SV: Montant négatif ? Total des avoirs ≤ facture ?
    SV->>DB: Numéro suivant dans la série des factures, PDF, statut émis
    alt Total des avoirs = montant de la facture
        SV->>DB: Facture d'origine : annulée par avoir
    end
    V-->>U: Avoir émis
```

### 4.6 Modification d'une ligne en direct (HTMX)

```mermaid
sequenceDiagram
    actor U as Artiste
    participant N as Navigateur (HTMX)
    participant V as Vue LineEdit
    participant SV as Service facturation
    participant DB as Base de données

    U->>N: Clique "Modifier" sur une ligne
    N->>V: GET modifier (requête HTMX)
    V-->>N: Bloc "lignes" avec la ligne en formulaire
    U->>N: Change le prix, enregistre
    N->>V: POST modifier (requête HTMX)
    V->>V: Valide le formulaire
    V->>SV: update_line(ligne, valeurs)
    SV->>DB: Met à jour la ligne et recalcule les totaux
    V-->>N: Bloc "lignes" rafraîchi (fragment, pas la page entière)
    N->>N: Remplace uniquement le bloc
```

Sans JavaScript, les mêmes adresses fonctionnent par rechargement de page (redirection au lieu du fragment).

### 4.7 Accès protégé à un fichier

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant V as Vue de téléchargement
    participant DB as Base de données
    participant ST as Stockage privé

    U->>V: GET /dates/12/factures/7/pdf/
    alt Pas connecté
        V-->>U: Redirection vers la connexion
    else Connecté
        V->>DB: Cherche la date 12 ET la facture 7 dans MA structure
        alt Introuvable (autre structure, autre date, mauvais type)
            V-->>U: 404
        else Trouvé
            V->>ST: Ouvre le fichier
            ST-->>V: Contenu
            V-->>U: PDF en pièce jointe
        end
    end
    Note over U,ST: Aucune adresse /media/ n'existe :<br/>le fichier ne sort que par cette vue
```

### 4.8 Lien secret de la feuille de route

```mermaid
sequenceDiagram
    actor Artiste
    actor Equipe as Équipe (sans compte)
    participant App as Application
    participant DB as Base de données

    Artiste->>App: Activer le partage
    App->>DB: nouveau jeton (token_urlsafe 32), is_published = vrai
    App-->>Artiste: lien à copier
    Equipe->>App: GET /feuille-de-route/jeton/
    App->>DB: feuille publiée avec ce jeton ?
    alt trouvée
        App-->>Equipe: page limitée à la liste blanche (pas de prix, contrat, factures)
    else inconnue ou partage arrêté
        App-->>Equipe: 404
    end
    Artiste->>App: Arrêter le partage
    App->>DB: jeton vidé, is_published = faux
```

Le lien ne montre que les données d'une liste blanche (`public_context`). La page est servie avec `no-store`, `noindex` et `no-referrer`, parce que le jeton est dans l'adresse.

### 4.9 Enregistrement d'un paiement

```mermaid
sequenceDiagram
    actor U as Artiste
    participant V as Vue PaymentAdd
    participant SV as Service finance
    participant DB as Base de données

    U->>V: POST montant, date, mode (sur une facture)
    V->>DB: Cherche la date ET la facture dans MA structure
    alt Introuvable
        V-->>U: 404
    else Trouvée
        V->>SV: record_payment(facture, montant, date, mode)
        SV->>DB: Début de transaction, verrouille la facture
        SV->>SV: Facture émise ? Montant positif ? Montant ≤ reste à payer ?
        alt Refusé
            SV-->>V: Erreur (dépasse le reste à payer...)
            V-->>U: Formulaire avec le message, rien d'enregistré
        else Accepté
            SV->>DB: Enregistre le paiement
            SV->>DB: Total payé ≥ total de la facture ? statut payée, sinon émise
            SV->>DB: Fin de transaction
            V-->>U: Page rafraîchie (bloc HTMX ou redirection)
        end
    end
```

Modifier ou supprimer un paiement passe par le même verrou et recalcule le statut : une facture « payée » revient à « émise » si le total n'est plus atteint.

### 4.10 Suppression de la structure

```mermaid
sequenceDiagram
    actor U as Propriétaire
    participant V as Vue DeleteTenant
    participant SV as Service tenants
    participant DB as Base de données
    participant C as Commande purge_deleted_tenants

    U->>V: POST nom de la structure + mot de passe
    alt Nom ou mot de passe faux
        V-->>U: Formulaire avec message, rien ne change
    else Valide
        V->>SV: request_deletion(structure)
        SV->>DB: deletion_requested_at = maintenant
        V-->>U: Suppression programmée dans 30 jours
    end
    opt Le propriétaire change d'avis
        U->>V: POST annuler la suppression
        V->>SV: cancel_deletion(structure)
        SV->>DB: deletion_requested_at = vide
    end
    Note over C,DB: Tâche planifiée en production (à configurer)
    C->>DB: Structures dont la demande a plus de 30 jours
    C->>DB: Supprime données et fichiers, dans un ordre explicite (liens protégés)
```

La suppression n'est jamais immédiate : le délai de 30 jours laisse le temps de se rétracter ou d'exporter ses données.

---

## 5. Cycles de vie (diagrammes d'états)

### 5.1 Une date

```mermaid
stateDiagram-v2
    [*] --> option : création
    option --> confirmee : confirmer
    confirmee --> signee : contrat marqué signé
    option --> annulee : annuler
    confirmee --> annulee : annuler
    signee --> annulee : annuler
    annulee --> option : réactiver (contrat non signé)
    annulee --> signee : réactiver (contrat signé)
```

Le passage à « signée » ne se fait que par le marquage du contrat. Rien n'est annulé automatiquement, même quand une option expire.

### 5.2 Un contrat

```mermaid
stateDiagram-v2
    [*] --> brouillon : première génération
    brouillon --> brouillon : nouvelle version
    brouillon --> signe : marquer signé
    signe --> signe : ajout unique du PDF signé
```

Un contrat signé ne bouge plus : la version figée est protégée contre la suppression et aucune version n'est ajoutée.

### 5.3 Une facture

```mermaid
stateDiagram-v2
    [*] --> brouillon : création
    brouillon --> emise : émettre (numéro, figeage, PDF)
    brouillon --> [*] : supprimer le brouillon
    emise --> payee : paiements = total
    payee --> emise : paiement modifié ou supprimé
    emise --> annulee : avoirs = montant total
    payee --> annulee : avoirs = montant total
    emise --> emise : avoir partiel
```

Une facture émise ne peut ni être modifiée ni supprimée ; seul son statut bouge, avec les paiements. Une facture payée reste créditable. Un devis suit le même cycle, sans avoir ni paiement.

### 5.4 Une structure

```mermaid
stateDiagram-v2
    [*] --> active : onboarding
    active --> suppression_programmee : propriétaire demande (nom + mot de passe)
    suppression_programmee --> active : annulation dans les 30 jours
    suppression_programmee --> [*] : purge après 30 jours
```

Pendant le délai, la structure existe encore et l'export reste possible.

---

## 6. Modèle de données

```mermaid
erDiagram
    USER ||--o{ MEMBERSHIP : "appartient via"
    TENANT ||--o{ MEMBERSHIP : "a des membres"
    TENANT ||--o{ SHOW : possede
    TENANT ||--o{ PROMOTER : possede
    TENANT ||--o{ VENUE : possede
    TENANT ||--o{ GIG : possede

    PROMOTER ||--o{ CONTACT : "a des contacts"
    VENUE ||--o{ CONTACT : "a des contacts"

    SHOW ||--o{ GIG : "est joue lors de"
    PROMOTER ||--o{ GIG : "achete"
    VENUE ||--o{ GIG : "accueille"

    GIG ||--o| CONTRACT : "a un contrat"
    CONTRACT ||--o{ CONTRACT_VERSION : "versions du PDF"
    CONTRACT }o--o| CONTRACT_VERSION : "version figee a la signature"

    GIG ||--o{ INVOICE : "factures et avoirs"
    GIG ||--o{ QUOTE : "devis"
    INVOICE ||--o{ INVOICE : "avoirs sur la facture"
    INVOICE ||--o{ DOCUMENT_LINE : "lignes"
    QUOTE ||--o{ DOCUMENT_LINE : "lignes"

    GIG ||--o| ROADMAP : "a une feuille de route"
    ROADMAP ||--o{ ROADMAP_SLOT : "creneaux"
    ROADMAP ||--o{ LODGING : "hebergements"
    ROADMAP ||--o{ MEAL : "repas"
    GIG ||--o{ GIG_MEMBER : "equipe"

    INVOICE ||--o{ PAYMENT : "paiements recus"
    GIG ||--o{ EXPENSE : "depenses"

    TENANT ||--o{ CONTRACT_SEQUENCE : "numerotation des contrats"
    TENANT ||--o{ DOCUMENT_SEQUENCE : "numerotation factures et devis"

    TENANT {
        string name
        string siret
        string vat_regime
        decimal vat_rate
        string vat_number
        string iban
        datetime deletion_requested_at
    }
    GIG {
        date date
        string status
        decimal price
        decimal deposit_percent
        date option_expires_on
        text conditions
    }
    CONTRACT {
        string reference
        string status
        datetime signed_at
        file signed_pdf
    }
    INVOICE {
        string number
        string kind
        string status
        json issuer_snapshot
        json customer_snapshot
        decimal total_incl_tax
        file pdf_file
    }
    ROADMAP {
        string token
        bool is_published
        text notes
    }
    PAYMENT {
        decimal amount
        date date
        string method
    }
    EXPENSE {
        string category
        string label
        decimal amount
        date date
        file receipt_file
    }
    DOCUMENT_LINE {
        string label
        decimal quantity
        decimal unit_price_excl_tax
        decimal vat_rate
    }
```

Règle d'or : **tous** les modèles métier (tout sauf `USER`) portent une clé vers `TENANT` (via `TenantOwnedModel`). C'est ce qui garantit l'isolation des structures. Les contraintes en base : un contact a un seul parent, un avoir est lié à sa facture (et seulement lui), une ligne a un seul document, un numéro est unique par structure, le jeton d'une feuille de route est unique, un montant de paiement ou de dépense est strictement positif.

---

## 7. Architecture

```mermaid
flowchart LR
    nav["Navigateur<br/>(mobile ou ordinateur)<br/>HTMX + Alpine.js + Tailwind"]

    subgraph srv["Application Django (monolithe)"]
        mw["Middleware<br/>identifie la structure"]
        vues["Vues<br/>filtrent par structure"]
        svc["Services<br/>règles métier, numérotation,<br/>transitions, montants"]
        pdf["WeasyPrint<br/>HTML vers PDF"]
    end

    cron(["Tâche planifiée<br/>purge des comptes supprimés"])
    public(["Équipe<br/>(lien secret, sans compte)"])
    pg[("PostgreSQL")]
    st[("Stockage privé<br/>disque en dev<br/>S3 européen en prod")]

    nav -->|"pages et fragments HTML"| mw
    mw --> vues
    vues --> svc
    svc --> pg
    svc --> pdf
    pdf --> st
    vues -->|"fichiers après contrôle"| st
    st -.->|"jamais d'URL directe"| nav
    cron -->|"commande de purge"| svc
    public -->|"page publique de la feuille de route"| vues
```

Les pages légales et la page publique de la feuille de route sont les seules vues sans connexion (hors inscription et connexion). La feuille de route ne passe que par le jeton, et n'expose qu'une liste blanche de données.

Choix assumés : un seul programme (pas d'API séparée), des pages rendues par le serveur avec de petits échanges HTMX, la logique métier dans des services testables, et les fichiers servis uniquement par des vues qui vérifient la structure.
