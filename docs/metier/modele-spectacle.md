# Annexe — Modèle de données « Projet – Spectacle » (détaillé)

> Référence pour **Q10** (`docs/produit/cahier-des-charges.md` §14). Document fourni par le collègue le 2026-09-29, complété le 2026-10-01 par un export Excel détaillant les champs exacts, des exemples et les listes de valeurs. **Non adopté dans le modèle MVP actuel** (`Show`/`Gig`) — conservé ici comme matière pour trancher Q10, pas comme spécification à implémenter.
>
> Source : export Excel fourni par le collègue (non versionné dans le dépôt).

## Pourquoi cette annexe existe

Le cahier des charges (§9) documente le modèle **MVP actuel** (`Show`, `Gig`…), déjà construit. Ce fichier détaille une **alternative structurelle plus riche**, proposée par le métier, qui remplacerait `Show` par une hiérarchie `Projet → Spectacle → Version` avec un référentiel `Personne` et plusieurs entités administratives dédiées. Tant que Q10 n'est pas tranché, cette annexe sert de référence précise pour la discussion — elle n'engage aucun changement de code.

## Les entités

### `Projet`
Le projet ou la tournée qui chapeaute un ou plusieurs spectacles.

| Champ | Exemple |
|---|---|
| `projet_id` | `PRJ-001` |
| `nom_projet` | Tournée Les Éclats 2027 |
| `statut_projet` | En diffusion *(valeurs : En création / En diffusion / En exploitation / En pause / Archivé)* |
| `structure_porteuse_id` | `STR-014` — correspond à notre `Tenant` |
| `description_interne` | Tournée Occitanie |

### `Spectacle`
Le spectacle au sens large (équivalent enrichi de notre `Show` actuel).

| Champ | Exemple |
|---|---|
| `spectacle_id` | `SP-001` |
| `projet_id` | `PRJ-001` |
| `nom_spectacle` | Les Éclats |
| `sous_titre` | Chansons en mouvement |
| `compagnie_artiste` | Collectif Azur |
| `discipline_principale` | Musique *(+ Théâtre, Danse, Cirque, Humour, Conte, Marionnettes, Pluridisciplinaire, Autre)* |
| `type_spectacle` | Concert *(+ Spectacle musical, Théâtre, Danse, Cirque, Humour, Conte, Autre)* |
| `public_cible` | Tout public *(+ Jeune public, Public familial, Public adulte, Autre)* |
| `age_min_recommande` | 6 |
| `jauge_recommandee_min` / `max` | 80 / 600 |
| `resume_court`, `description_longue` | — |
| `statut_spectacle` | En diffusion *(mêmes valeurs que statut_projet + Suspendu)* |
| `date_creation`, `notes_internes` | — |

### `Version`
Une déclinaison technique/commerciale d'un spectacle (durée, jauge, prix par défaut). **N'existe pas dans le modèle MVP actuel** — un `Show` = une seule configuration aujourd'hui.

| Champ | Exemple |
|---|---|
| `version_id` | `VER-001` |
| `spectacle_id` | `SP-001` |
| `nom_version` | Plateau complet |
| `version_active` | Oui/Non |
| `duree_spectacle_min`, `entracte_min` | 75, 0 |
| `duree_balance_min`, `duree_montage_min`, `duree_demontage_min` | 45, 90, 60 |
| `nb_artistes_type`, `nb_techniciens_type`, `nb_accompagnants_type` | 3, 2, 1 |
| `implantation_scenique` | Plateau 6 m × 4 m minimum |
| `besoins_electriques` | 2 prises 16 A |
| `conditions_vhr_defaut` | texte libre (transport/hébergement/restauration) |
| `vhr_transport_defaut`, `vhr_hebergement_defaut`, `vhr_restauration_defaut` | Producteur / Diffuseur / Diffuseur *(valeurs : Producteur, Diffuseur, Partagé, À négocier)* |
| `prix_cession_ht_defaut` | 2500 |
| `notes_version` | Adaptation scolaire possible. |

**Point d'attention** : la fiche d'usage du fichier précise explicitement que les conditions *réellement convenues* pour une date donnée doivent être stockées sur la date/le contrat, **sans écraser** ces valeurs par défaut de la `Version`. C'est cohérent avec notre règle actuelle (le contrat capture un instantané, jamais une référence dynamique).

### `Personne`
Annuaire réutilisable d'artistes/techniciens, indépendant d'un spectacle donné.

| Champ | Exemple |
|---|---|
| `personne_id` | `PER-021` |
| `prenom`, `nom`, `nom_scene` | Camille, Martin, Camille M. |
| `email_pro`, `telephone_pro` | — |

### `Distribution_type`
Le casting/équipe **par défaut** d'une version — copié (pas référencé) sur chaque représentation au moment de la création, pour ne pas que l'historique change si l'équipe change plus tard.

| Champ | Exemple |
|---|---|
| `distribution_type_id` | `DST-001` |
| `version_id`, `personne_id` | `VER-001`, `PER-021` |
| `categorie_equipe` | Artiste *(+ Technicien, Production, Administration, Accompagnement, Autre)* |
| `fonction` | Chant *(+ Guitare, Batterie, Régie son, Régie lumière, Régie plateau, Tour management, Production, Autre)* |
| `intitule_libre` | Chant / guitare |
| `statut_distribution` | Titulaire *(+ Remplaçant, Poste à pourvoir, Inactif)* |
| `ordre_affichage` | 1 |

### `Numero_objet`
Le numéro d'objet France Travail (spectacle occasionnel), **par spectacle ET par employeur** — un même spectacle peut avoir plusieurs employeurs dans le temps.

| Champ | Exemple |
|---|---|
| `spectacle_id`, `employeur_id` | `SP-001`, `STR-014` |
| `numero_objet` | AB1234567890 |
| `statut_objet` | À obtenir *(+ Obtenu, Non applicable, À vérifier)* |
| `date_obtention` | — |

### `Programme_SACEM`
La déclaration SACEM, **par spectacle ET par version** (le programme peut différer selon la version jouée).

| Champ | Exemple |
|---|---|
| `spectacle_id`, `version_id` | `SP-001`, `VER-001` |
| `numero_programme` | PT-EXEMPLE-001 |
| `titre_programme` | Les Éclats – plateau complet |
| `statut_sacem` | Déclaré *(+ À déclarer, Non applicable, À vérifier)* |

### `Document`
Entité générique pour les fichiers liés à un spectacle/une version (fiche technique, riders, plans…), versionnée.

| Champ | Exemple |
|---|---|
| `document_id` | `DOC-010` |
| `spectacle_id`, `version_id` | `SP-001`, `VER-001` |
| `type_document` | Fiche technique *(+ Rider accueil, Rider hospitalité, Plan de scène, Patch, Dossier artistique, Visuel, Autre)* |
| `nom_fichier`, `stockage_ref` | fiche-technique-les-eclats-v2.pdf, `stockage://doc-010` |
| `version_document` | 2 |
| `date_validite` | 2027-06-30 |
| `statut_document` | Validé *(+ Brouillon, À valider, Archivé)* |

## Ce qui est réutilisable dès maintenant, indépendamment de Q10

Certaines listes de valeurs de l'onglet `Listes` sont des choix d'UI directement exploitables sur le modèle MVP actuel, sans adopter la hiérarchie Projet/Spectacle/Version :

- **`categorie_equipe` / `fonction`** (Artiste, Technicien, Production, Administration, Accompagnement / Chant, Guitare, Batterie, Régie son, Régie lumière, Régie plateau, Tour management, Production, Autre) → candidat pour structurer `GigMember.role` au lieu d'un champ texte libre.
- **`type_document`** (Fiche technique, Rider accueil, Rider hospitalité, Plan de scène, Patch, Dossier artistique, Visuel, Autre) → candidat pour qualifier les pièces jointes de `Show` (`tech_sheet_file`, `rider_file`) si on les multiplie un jour.
- **`statut_objet` / `statut_sacem`** (À obtenir/Obtenu/Non applicable/À vérifier ; À déclarer/Déclaré/Non applicable/À vérifier) → vocabulaire utile pour un futur suivi des numéros SACEM/objet sur `Show`, même sans la refonte complète.

## Sources citées par le document métier

- France Travail (numéro d'objet / AEM spectacle occasionnel) : francetravail.fr/spectacle
- Sacem (déclaration de programme) : createursediteurs.sacem.fr