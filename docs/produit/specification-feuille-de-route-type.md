> **Statut (2026-11-05) : document de l'associé, source d'inspiration, pas une référence de développement.** La feuille de route existe déjà (`F-60` à `F-64`, espace équipe). Ce qui est retenu à ce jour : voir les notes de la réunion du 2026-11-05 (`docs/archives/2026-11-05-reunion-associe.md`) et `F-86` à `F-93` du cahier des charges. Le reste (modèle de données ci-dessous, transports, rooming list, confirmation de lecture, notifications, score de complétude) est **après le MVP** et à confirmer point par point. Écarts avec les règles du projet à lever avant tout développement : noms d'objets en français (le code est en anglais : `Roadmap`, `Lodging`, `Meal`, `GigMember`…), calculs de distance, de durée de trajet, de défraiements conventionnels et contrôle des temps de travail (hors périmètre, `CLAUDE.md` §10), et toute donnée financière sur un lien partagé.

# Feuille de route type — Spécification produit

> Gabarit destiné à la génération automatisée des feuilles de route dans l’application SaaS de gestion du spectacle vivant.  
> Objectif : transformer la feuille de route en une **vue dynamique générée depuis une date de tournée**, et non en un document à remplir manuellement.

## 1. Principe produit

La feuille de route est une **vue générée à partir d’une date de représentation**, liée à un spectacle, un lieu, un contrat, une équipe, une logistique et un planning.

Elle doit permettre :

- de centraliser les informations utiles à l’équipe et au lieu ;
- de générer automatiquement les documents PDF et liens de partage ;
- de notifier les changements ;
- de tracer les confirmations de lecture ;
- de préparer les données nécessaires aux frais, défraiements, transports, hébergements et comptabilité.

La feuille de route doit couvrir notamment : coordonnées, contacts, hébergements, itinéraires, arrivées/départs et planning, conformément aux usages décrits par ARTCENA.

## 2. Modèle de données

Créer une entité `FeuilleDeRoute` liée à une `DateTournée`, elle-même rattachée à un `Spectacle`, un `Lieu`, un `Contrat` et éventuellement un `Projet`.

| Objet | Champs clés | Règle produit |
|---|---|---|
| `FeuilleDeRoute` | `id`, `date_id`, `statut`, `version`, `langue`, `date_publication`, `confirmation_lecture`, `blocs_actifs` | Statuts : brouillon, à valider, publiée, complétée, archivée |
| `Spectacle` | `titre`, `durée`, `effectif`, `fiche_technique`, `dossier_presse`, `droits`, `mentions` | Pré-rempli depuis la fiche spectacle |
| `DateTournée` | `date`, `heure`, `type_public`, `séance`, `jauge`, `billetterie`, `statut_commercial` | Types : générale, scolaire, jeune public, relais, répétition publique |
| `Lieu` | `nom`, `adresse`, `accès`, `parking`, `chargement`, `loges`, `contacts`, `horaires`, `plan` | Géocodage + liens Maps/Waze |
| `Équipe` | `personne`, `rôle`, `arrivée`, `départ`, `téléphone`, `email`, `régime`, `besoins`, `documents` | Vue filtrée : chacun ne voit que son propre parcours |
| `Transport` | `mode`, `trajet`, `départ`, `arrivée`, `conducteur`, `passagers`, `billet`, `distance`, `coût` | Un trajet de liaison peut apparaître sur deux dates sans doublon |
| `Hébergement` | `hôtel`, `adresse`, `nuits`, `rooming_list`, `contact`, `check-in/out` | Génération automatique de la rooming list |
| `Planning` | `horaires`, `activité`, `responsable`, `lieu`, `participants`, `notes` | Montage, raccord, répétition, représentation, démontage, EAC |
| `Technique` | `fiche_technique`, `plan_feux`, `plan_salle`, `décor`, `matériel`, `besoins`, `régisseur` | Pièces jointes versionnées |
| `Administratif` | `contrat`, `facture`, `droits`, `assurance`, `DUERP`, `consignes_sécurité` | Alerte si document manquant |
| `Frais` | `repas`, `défraiement`, `note_frais`, `justificatif`, `prise_en_charge` | Règle selon convention collective et répartition contractuelle |

## 3. Gabarit de feuille de route

### 3.1 En-tête et alertes

- Titre du spectacle, production, tournée, numéro de date.
- Date, heure, type de séance, lieu, ville.
- Bandeau d’alertes : changement d’horaire, séance scolaire, arrivée anticipée, contrainte technique, absence, document manquant.
- Statut : brouillon / publiée / complétée.
- Date de dernière mise à jour et responsable de la feuille de route.

**Recommandation :** afficher en priorité les informations à fort risque d’erreur : horaire, lieu, contact d’accueil, heure de chargement et consignes de sécurité.

### 3.2 Équipe présente

| Champ | Exemple |
|---|---|
| Nom / prénom | Marie Dupont |
| Rôle | Chanteuse, régisseuse son |
| Arrivée | 12/11 – 14h00 – gare de Lyon |
| Départ | 13/11 – 11h30 – gare de Lyon |
| Téléphone / email | Cliquer pour appeler, SMS ou WhatsApp |
| Régime alimentaire | Végétarien |
| Besoin spécifique | Accès PMR, enfant accompagné, matériel médical |

Chaque membre doit voir uniquement les dates et informations qui le concernent ; les administrateurs conservent une vue globale.

### 3.3 Lieu et accueil

- Nom du lieu, adresse complète, lien itinéraire.
- Contact accueil / administration / technique / billetterie, avec appel, SMS, email et WhatsApp en un clic.
- Horaires d’ouverture, accès camion, zone de déchargement, stationnement.
- Accès loges, foyer, repas, vestiaires, wifi, consignes du lieu.
- Documents : plan d’accès, plan de salle, fiche technique du lieu, convention d’accueil.

### 3.4 Planning de la date

Une timeline unique, filtrable par personne :

| Horaire | Activité | Lieu | Responsable | Participants |
|---|---|---|---|---|
| 09h00 | Arrivée camion / déchargement | Quai de chargement | Régisseur lieu | Régie |
| 10h00 | Montage | Salle | Régisseur son | Techniciens |
| 14h00 | Balance | Salle | Régisseur son | Musiciens |
| 17h00 | Répétition | Salle | Metteur en scène | Équipe artistique |
| 20h30 | Représentation | Salle | Régisseur général | Équipe complète |
| 22h30 | Démontage / chargement | Quai | Régisseur lieu | Régie |

Le gabarit doit permettre des **blocs récurrents** :

- montage ;
- balance ;
- répétition ;
- représentation ;
- démontage ;
- transfert ;
- repas ;
- réunion production ;
- rencontre public ;
- atelier / EAC ;
- interviews ;
- invitations.

### 3.5 Transports et trajets

- Trajet précédent → lieu.
- Lieu → hébergement.
- Hébergement → lieu.
- Lieu → trajet suivant.
- Mode : train, avion, véhicule de production, véhicule personnel, location, tour-bus.
- Conducteur, passagers, horaires, numéro de réservation, billet joint.
- Distance, durée estimée, coût, mode de prise en charge.

**Règle importante :** distinguer trajet de production et trajet personnel. Un trajet de liaison doit être rattaché aux deux dates concernées sans double comptage.

### 3.6 Hébergement

- Hôtel ou gîte, adresse, contact, téléphone.
- Nuits par personne, arrivée, départ, type de chambre.
- Rooming list générée automatiquement et exportable en PDF ou presse-papier.
- Coût, mode de réservation, prise en charge par la production ou le lieu.
- Consignes : petit-déjeuner, parking, dépôt de bagages, accès tardif.

### 3.7 Repas et défraiements

- Repas prévus : déjeuner, dîner, collation.
- Lieu, horaire, invités, prise en charge.
- Régimes alimentaires et allergies consolidés automatiquement.
- Défraiement applicable, calculé selon le barème conventionnel.
- Statut : à renseigner / validé / remboursé.
- Rappel automatique si un repas n’est pas renseigné.

### 3.8 Technique, décor et sécurité

- Fiche technique, plan de feu, plan de salle, plan de chargement.
- Liste du décor, volumes, poids, camion, numéro de réservation, retrait et retour.
- Besoins spécifiques : son, lumière, vidéo, instruments, backstage, sécurité.
- Contacts techniques du lieu et de la production.
- Consignes de sécurité, DUERP ou éléments de prévention, procédure d’urgence, numéro de secours.

La sécurité doit rester un bloc non optionnel : l’employeur a une obligation de sécurité et doit évaluer les risques, notamment via le DUERP.

### 3.9 Administratif et contractuel

- Contrat de cession ou de coréalisation, statut de signature.
- Facture, acompte, solde, statut de règlement.
- Droits d’auteur : redevable, organisme de gestion collective ou paiement direct, mode de calcul.
- Assurances, SACEM/SACD si pertinent, documents douaniers pour tournées à l’étranger.
- Documents à remettre au lieu : fiche technique, plan, liste équipe, SACEM, attestations.

La prise en charge des droits d’auteur par le lieu doit être explicitement prévue au contrat.

### 3.10 Invitations, presse et actions publiques

- Nombre d’invitations par personne et modalité de réservation.
- Liste d’invités, statut de confirmation.
- Contacts presse, éléments de communication, photos autorisées.
- Rencontres public, bord de scène, atelier, masterclass, EAC.
- Consignes : présence obligatoire, tenue, horaire de rappel.

### 3.11 Bloc libre et notes privées

- Bloc texte libre activable par la production.
- Notes visibles par toute l’équipe.
- Notes personnelles visibles uniquement par leur auteur.
- Check-list individuelle : papiers, clés, matériel, médicaments, billets, chargeurs.

## 4. Règles d’automatisation

À implémenter dès la V1 :

1. **Génération depuis la date** : la feuille de route se crée automatiquement dès qu’une date passe en « confirmée ».
2. **Héritage du spectacle** : fiche technique, équipe type, décor, documents, consignes et blocs de texte par défaut.
3. **Héritage du lieu** : adresse, contacts, accès, horaires, plans et consignes.
4. **Héritage du contrat** : prise en charge transport/hébergement/repas, droits, facturation, invitations.
5. **Complétude calculée** : score de complétude par section, avec alertes sur les champs critiques manquants.
6. **Notifications** : publication, modification d’horaire, changement de lieu, ajout de billet, demande d’invitation, document manquant.
7. **Confirmation de lecture** : horodatage par utilisateur, utile en cas de litige ou de changement tardif.
8. **Duplication** : dupliquer une date ou une tournée en conservant les gabarits.
9. **Export** : PDF imprimable FR/EN, avec sélection des sections ; export Excel des trajets, nuits, repas et frais.
10. **Lien public sécurisé** : partage limité à une date avec un lieu ou un prestataire, sans accès complet à l’application.

## 5. Permissions

| Rôle | Lecture | Édition | Informations sensibles |
|---|---|---|---|
| Artiste / interprète | Ses dates et son parcours | Notes personnelles, confirmation de lecture | Non |
| Technicien | Ses dates, planning technique, documents techniques | Planning selon habilitation | Non |
| Régisseur / directeur technique | Dates concernées | Planning, technique, logistique | Oui selon projet |
| Administrateur production | Toutes les dates | Tout | Oui |
| Comptabilité | Frais, trajets, hébergements, justificatifs | Frais et défraiements | Oui |
| Lieu / prestataire | Lien public limité | Non | Non |

## 6. Positionnement concurrentiel

| Capacité | Orféo | Bob Booking | OTour | Recommandation pour notre app |
|---|---|---|---|---|
| Feuille de route | Personnalisable, mobile, notifications, blocs déplaçables | Intégrée au workflow booking / contrat / facture | Dynamique, temps réel, export PDF FR/EN | Faire de la FDR une **vue générée**, pas un document à remplir |
| Gabarits | Modèles de projet, plannings types, champs pré-remplis | Équipes types et documents liés au catalogue | Duplication de dates | Gabarits par type de tournée : solo, bande, orchestre, festival, scolaire |
| Booking | Diffusion, planning, contrats, distribution | Cœur de métier : précontrat, contrat, facture, équipes | Moins orienté booking commercial | Lier FDR au contrat et à la facture dès la création |
| Logistique | Voyages, hébergement, plannings | Dates, équipes, workflow | Trajets, véhicules, rooming list, billets IA | Prioriser trajets + hébergement + rooming list |
| Frais / paie | Suivi administratif et financier évoqué | Facturation et suivi des règlements | Notes de frais IA, défraiements, compta consolidée | Différenciateur fort : défraiements conformes + export comptable |
| Collaboration | App mobile, notifications | Agendas partagés, tâches et workflows | Chat, commentaires, infos secrètes, confirmation de lecture | Prévoir commentaires + statuts de traitement, sans chat complet en V1 |

## 7. MVP recommandé

### Priorité 1 — indispensable

- Fiche date + lieu + contacts cliquables.
- Équipe, rôles, arrivées/départs.
- Planning de journée.
- Transports, billets et hébergement.
- Fiche technique et pièces jointes.
- Statut brouillon/publié, export PDF, notification de modification.
- Confirmation de lecture.

### Priorité 2 — différenciation

- Rooming list automatique.
- Trajets de liaison sans doublon.
- Repas, régimes et défraiements.
- Score de complétude et alertes documentaires.
- Lien public sécurisé pour le lieu.

### Priorité 3 — avantage concurrentiel

- Calcul des défraiements selon barème conventionnel.
- Export comptable avec justificatifs.
- Contrôle des temps de travail, repos et trajets.
- Retour d’expérience post-date : accueil, technique, hébergement, repas.

## 8. Point réglementaire à intégrer

Le gabarit doit comporter un contrôle de conformité sur :

- Repos hebdomadaire : pas plus de 6 jours travaillés consécutifs.
- Repos quotidien : 11 heures consécutives, avec exceptions conventionnelles possibles, notamment 9 heures pour certains personnels techniques.
- Durée quotidienne : 10 heures en principe, jusqu’à 12 heures dans certains cas prévus par la convention collective.
- Temps de trajet : les trajets entre deux lieux de représentation, ou domicile-lieu hors date isolée, peuvent compter comme temps de travail effectif selon la convention applicable.

**Recommandation produit :** ne pas coder un calcul juridique figé. Prévoir un moteur de règles configurable par convention collective, avec alerte plutôt que blocage automatique, et une piste d’audit des décisions manuelles.

## 9. Sources

- ARTCENA — *Gérer l’exploitation d’un spectacle* : <https://www.artcena.fr/guide/diffuser-son-spectacle/gerer-lexploitation-dun-spectacle>
- OTour — Fonctionnalités : <https://www.otour.app/#functions>
- Orféo — Régie de tournée : <https://orfeo.pro/fonctionnalites/regie-de-tournee>
- Orféo — Feuille de route : <https://orfeo.pro/blog/la-feuille-de-route-dorfeo-sest-refait-une-beaute>
- Bob Booking — Processus confirmation / contrat / facture / feuille de route : <https://aide-en-ligne.bobelweb.eu/le-processus-confirmationcontratfacture/>
