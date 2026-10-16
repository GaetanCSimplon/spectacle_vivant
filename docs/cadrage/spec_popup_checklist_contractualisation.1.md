# Spécification — Popup « Checklist contractualisation »

## Objectif

Ajouter dans l’application une **popup d’aide** permettant de cocher les étapes réalisées dans la contractualisation et le suivi administratif d’une date, d’un engagement ou d’un projet.

Il ne s’agit **pas** d’un module de workflow, ni d’un outil de gestion documentaire : aucune génération automatique, aucune alerte, aucun blocage, aucun statut intermédiaire. Une étape est soit **faite**, soit **pas faite**.

## Périmètre

### Inclus

- Affichage d’une popup accessible depuis une fiche date, un engagement, un projet ou une tournée.
- Liste de cases à cocher organisée par sections.
- Enregistrement de l’état coché / décoché.
- Bouton « Réinitialiser ».
- Bouton « Fermer ».
- Conservation de la checklist par entité concernée.

### Exclus pour cette version

- Génération de devis, contrats, factures, fiches techniques ou riders.
- Envoi automatique de documents.
- Suivi de signature électronique.
- Alertes, relances, échéances ou notifications.
- Contrôle de conformité DPAE / GUSO.
- Gestion des versions de documents.
- Calcul d’avancement ou barre de progression.
- Statuts intermédiaires du type « à faire », « en cours » ou « à envoyer ».

## Déclenchement

La popup peut être ouverte depuis :

- La fiche d’une date de représentation.
- La fiche d’un engagement / contrat.
- La fiche d’un projet ou d’une tournée.

Bouton ou icône suggérée :

- Libellé : **Checklist contractualisation**
- Icône : coche ou liste à cocher
- Emplacement : barre d’actions de la fiche concernée

## Principe de fonctionnement

- Chaque ligne correspond à une action **réalisée ou non réalisée**.
- Case décochée = action non réalisée.
- Case cochée = action réalisée.
- Aucune case « à faire » n’est affichée.
- Aucune dépendance automatique entre les cases.
- L’utilisateur coche librement, sans contrainte d’ordre.

## Structure des données

```json
{
  "entity_type": "date | engagement | projet",
  "entity_id": "123",
  "items": {
    "devis_envoye": true,
    "devis_accepte": false,
    "contrat_envoye": false,
    "contrat_signe": false,
    "fiche_technique_envoyee": false,
    "rider_envoye": false,
    "feuille_route_envoyee": false,
    "acompte_envoye": false,
    "acompte_recu": false,
    "facture_solde_envoyee": false,
    "solde_recu": false,
    "contrats_intermittents_envoyes_signes": false,
    "dpae_envoyee": false,
    "accuse_dpae_recu": false,
    "documents_archives": false,
    "date_cloturee": false
  },
  "updated_at": "2026-10-16T09:59:00Z",
  "updated_by": "user_id"
}
```

### Règles

- Une checklist est rattachée à une seule entité : `entity_type` + `entity_id`.
- Chaque case est un booléen : `true` ou `false`.
- Par défaut, toutes les cases sont décochées.
- La sauvegarde peut être automatique à chaque changement de case.
- La date de dernière modification et l’utilisateur doivent être conservés pour l’audit.

## Contenu de la popup

Titre : **Checklist contractualisation**

Sous-titre : *Cochez les éléments réalisés pour cette date.*

### Avant confirmation de la date

- [ ] Devis envoyé
- [ ] Devis accepté / accord du lieu

### Contrat

- [ ] Contrat envoyé
- [ ] Contrat signé / retourné

### Documents techniques

- [ ] Fiche technique envoyée
- [ ] Rider envoyé
- [ ] Feuille de route envoyée

### Facturation

- [ ] Acompte envoyé
- [ ] Acompte reçu
- [ ] Facture de solde envoyée
- [ ] Solde reçu

### Intervenants / intermittents

- [ ] Contrats intermittents envoyés / signés
- [ ] DPAE envoyée
- [ ] Accusé DPAE reçu

### Clôture

- [ ] Tous les documents archivés
- [ ] Date clôturée

## Comportement UI

- La popup est modale, avec un fond assombri.
- Elle doit rester lisible sur desktop et mobile.
- Les sections sont affichées dans l’ordre défini ci-dessus.
- Les cases sont indépendantes : cocher une case ne modifie pas les autres.
- Le clic sur une case enregistre immédiatement l’état.
- En cas d’échec de sauvegarde, afficher un message discret : « Modification non enregistrée. Réessayez. »
- Le bouton « Réinitialiser » décoche toutes les cases après confirmation : « Réinitialiser toutes les cases ? »
- Le bouton « Fermer » ferme la popup sans action supplémentaire.

## API suggérée

### Lire la checklist

```http
GET /api/checklists?entity_type=date&entity_id=123
```

Réponse :

```json
{
  "entity_type": "date",
  "entity_id": "123",
  "items": { "...": true },
  "updated_at": "2026-10-16T09:59:00Z",
  "updated_by": "user_id"
}
```

### Mettre à jour une case

```http
PATCH /api/checklists/{entity_type}/{entity_id}
```

Corps :

```json
{
  "item": "devis_envoye",
  "value": true
}
```

### Réinitialiser

```http
POST /api/checklists/{entity_type}/{entity_id}/reset
```

## Permissions

- Tout utilisateur ayant accès en lecture à la fiche peut consulter la checklist.
- Tout utilisateur ayant accès en écriture à la fiche peut cocher ou décocher les cases.
- La réinitialisation suit la même permission que la modification.

## Évolutions possibles, hors V1

À ne pas développer maintenant, mais à prévoir dans l’architecture :

- Ajout de cases personnalisées par l’utilisateur.
- Checklist par modèle de projet ou type de spectacle.
- Attribution d’un responsable par case.
- Date d’échéance et alerte.
- Génération ou lien vers le document correspondant.
- Statuts enrichis si besoin plus tard : à faire, envoyé, validé, refusé.
- Contrôle automatique de conformité pour les intermittents.

## Critères d’acceptation

1. L’utilisateur peut ouvrir la checklist depuis une fiche date, engagement ou projet.
2. Toutes les cases sont décochées à la première ouverture.
3. Le clic sur une case est enregistré et persiste après fermeture puis réouverture.
4. La checklist est propre à l’entité sélectionnée.
5. Aucune ligne « à faire » n’apparaît : une case signifie uniquement que l’action est réalisée.
6. Le bouton « Réinitialiser » décoche toutes les cases après confirmation.
7. Aucune notification, alerte ou blocage n’est déclenché par la checklist.
8. La popup fonctionne sur desktop et mobile.
