# BÒRD PRO — Spécification fonctionnelle de l’onglet BÒRD

Version : 1.0 — 15 octobre 2026  
Statut : proposition de cadrage à valider avant développement  
Destinataire : développeur de BÒRD PRO

## 1. Objectif produit

L’onglet BÒRD est la page de pilotage général de BÒRD PRO. Il donne à l’utilisateur une vue d’ensemble de son activité : projets, tournées, dates, budget, paiements, équipe et rémunérations.

L’utilisateur doit comprendre rapidement :
- où en est son activité ;
- ce qui arrive prochainement ;
- la situation budgétaire et les paiements à suivre ;
- qui est mobilisé et pour quel coût ;
- les actions prioritaires à réaliser.

BÒRD est une synthèse actionnable, pas une copie de tous les modules. Chaque indicateur doit être explicite et permettre d’accéder aux données qui le composent.

Public prioritaire : artistes-entrepreneurs, petites compagnies et microstructures du spectacle vivant, notamment sans administrateur salarié.

## 2. Périmètre et limites

### Inclus
- Synthèse multi-projets et par tournée.
- Dates et états de préparation.
- Suivi budgétaire prévisionnel, actualisé et engagé.
- Suivi des encaissements et décaissements enregistrés.
- Équipe mobilisée et rémunérations renseignées.
- Alertes métier simples et explicables.
- Navigation vers les fiches sources et vers RADAR.

### Hors périmètre de cette version
- Production de bulletins de paie et de contrats d’intermittents.
- Calcul réglementaire automatique des cotisations et du salaire net.
- Tenue comptable et rapprochement bancaire automatique.
- Présentation d’une trésorerie bancaire sans données bancaires fiables.
- Alertes prédictives par intelligence artificielle.

Les montants sociaux sont saisis ou importés. Leur affichage ne constitue pas une validation de conformité de la paie.

## 3. Articulation avec RADAR

La répartition ci-dessous est une proposition à confirmer avec le périmètre actuel de RADAR.

| BÒRD | RADAR |
|---|---|
| Vue globale de l’activité | Suivi approfondi et anticipation de tournée |
| Chiffres clés et priorités | Lecture contextualisée des dates et de leur préparation |
| Répond à « Où en suis-je ? » | Répond à « Que faut-il préparer ou ajuster ? » |
| Oriente vers les dossiers | Permet d’approfondir la situation concernée |

Règles :
1. BÒRD et RADAR partagent les mêmes données sources.
2. Une information n’est jamais ressaisie pour alimenter une synthèse.
3. Les règles de calcul et d’alerte sont mutualisées.
4. Un lien depuis BÒRD ouvre RADAR sur la bonne tournée ou date.
5. Une modification dans une fiche source se répercute dans les deux vues.

## 4. Structure de l’écran

### 4.1 Bandeau de contexte

Filtres :
- Période : mois, trimestre, saison, intervalle personnalisé.
- Périmètre : toute l’activité, projet, tournée.
- Date de dernière actualisation.

Tous les blocs suivent ces filtres. Toute exception doit être indiquée dans le bloc. Les bornes d’une saison doivent être configurées, et non supposées identiques pour toutes les structures.

### 4.2 Première ligne : cinq cartes maximum

| Carte | Information principale | Information complémentaire | Destination au clic |
|---|---|---|---|
| Activité | Projets actifs sur la période | Création / diffusion | Liste des projets filtrée |
| Dates | Représentations confirmées | Options comptées séparément | Calendrier ou liste filtrée |
| Budget | Résultat prévisionnel actualisé | Écart avec le budget initial | Détail du budget |
| Paiements | Restant à encaisser | Dont montant en retard | Liste des créances concernées |
| Équipe | Personnes distinctes mobilisées | Coût employeur renseigné et complétude | Affectations et coûts autorisés |

La subvention devient un bloc complémentaire selon les usages : demandé, accordé, reçu.

### 4.3 Bloc « À traiter maintenant »

Afficher au maximum cinq priorités, puis un accès à la liste complète.

Chaque alerte contient :
- un libellé compréhensible ;
- le projet ou la date concernée ;
- une échéance ;
- le montant si pertinent ;
- une action explicite ;
- la raison du déclenchement.

Exemples de règles à valider :
- Facture arrivée à échéance avec solde restant positif.
- Date confirmée proche avec information de préparation obligatoire manquante.
- Affectation sans coût de personnel renseigné.
- Dépenses dépassant l’enveloppe prévue.
- Échéance de bilan de subvention renseignée et proche.

Les délais et seuils doivent être configurés ou validés avant implémentation. Ne pas inventer d’échéance réglementaire en l’absence de donnée vérifiée.

### 4.4 Bloc « Prochaines dates et tournées »

Pour chaque date : date, lieu, spectacle/projet, statut, équipe affectée, préparation, liens vers la fiche et RADAR.

Statuts minimum proposés : option, confirmé, annulé. L’état réalisé peut être ajouté si nécessaire, avec une règle de transition explicite.

Pour une tournée : période, dates confirmées, recettes prévues et dépenses restant à renseigner.

### 4.5 Bloc « Situation financière »

Séparer deux lectures :

| Équilibre budgétaire | Suivi des paiements |
|---|---|
| Recettes prévues et confirmées, distinguées | Encaissements enregistrés |
| Dépenses prévues et engagées, distinguées | Décaissements enregistrés |
| Résultat prévisionnel actualisé | Restant à encaisser et restant à payer |
| Écart avec le budget initial | Retards selon échéances renseignées |

Ne pas appeler « trésorerie » la simple différence entre recettes et dépenses budgétaires.

### 4.6 Bloc « Équipe et rémunérations »

Afficher selon les droits :
- nombre de personnes distinctes mobilisées ;
- cachets, jours et heures dans des compteurs séparés ;
- rémunérations brutes prévues ou renseignées ;
- coût employeur estimé ou transmis par le prestataire de paie ;
- nombre d’affectations dont les montants restent à compléter ;
- prochaines mobilisations.

Ne pas confondre net, brut et coût employeur. Un coût employeur incluant déjà le brut ne doit pas être additionné une seconde fois au brut.

## 5. Règles métier et qualité des données

### 5.1 Valeurs et états

Distinguer :
- zéro confirmé ;
- donnée absente ;
- donnée partielle ;
- donnée estimée ;
- donnée importée ou renseignée.

Une valeur absente s’affiche « À renseigner », et non « 0 € ». Un total incomplet doit porter un avertissement de complétude. L’absence d’alerte ne signifie pas que les données ont été contrôlées intégralement.

### 5.2 Indicateurs financiers

- Résultat prévisionnel actualisé = recettes du budget actualisé − dépenses du budget actualisé, à périmètre comparable.
- Restant à encaisser = montant des créances suivies après corrections applicables − règlements affectés.
- Retard = restant à encaisser positif avec échéance dépassée.
- Subvention accordée et subvention reçue sont deux états distincts.
- Un devis ou une option ne constitue pas automatiquement une recette acquise.
- Les acomptes, paiements partiels et avoirs doivent être traités explicitement.
- Ne pas additionner des montants HT et TTC sans règle de conversion ou de présentation explicite.

Pour le budget actualisé, une ligne engagée remplace ou consomme la prévision correspondante selon une règle validée ; elle ne s’ajoute pas automatiquement à la prévision initiale.

### 5.3 Périodes

Chaque indicateur doit préciser sa date de référence : date de représentation, date d’engagement, date d’échéance ou date de paiement. Le même filtre visuel ne doit pas masquer des conventions différentes.

Définir notamment :
- ce qu’est un projet actif pendant un intervalle ;
- le traitement des événements à cheval sur deux périodes ;
- le fuseau horaire et les bornes inclusives/exclusives ;
- la convention utilisée pour les échéances et retards.

### 5.4 Affectation des coûts

Un frais commun à plusieurs dates est soit rattaché à la tournée, soit ventilé entre dates. Ne jamais additionner le coût global et ses ventilations.

Le comptage des personnes doit dédupliquer une même personne affectée à plusieurs dates.

## 6. Données et relations minimales

Adapter les entités existantes plutôt que créer des doublons pour BÒRD.

| Entité | Données utiles |
|---|---|
| Structure | Identifiant, configuration, droits |
| Projet | Statut, période, rattachement structure |
| Tournée | Projet, période, dates associées |
| Date | Horaire, lieu, statut, projet, tournée éventuelle |
| Personne | Identité et informations visibles selon droits |
| Affectation | Personne, date/projet, quantité et unité, rémunération, coût employeur, provenance |
| Ligne budgétaire | Catégorie, montant initial/actualisé, engagement, affectation |
| Créance/dette suivie | Montant, échéance, statut, lien au dossier |
| Paiement | Montant, date, sens, affectation à la créance/dette |
| Subvention | Demandé, accordé, reçu, échéances renseignées |
| Alerte | Règle, objet source, priorité, échéance, état |

La structure exacte dépend du modèle déjà développé. Ne pas imposer ces noms comme schéma définitif.

## 7. Architecture proposée

Créer une couche de synthèse commune à BÒRD et RADAR :
1. réception du périmètre et de la période ;
2. contrôle des droits et restriction à la structure autorisée ;
3. récupération des données utiles ;
4. calcul des indicateurs et de leur complétude ;
5. évaluation des règles d’alerte ;
6. restitution aux composants d’interface.

La réponse de synthèse devrait inclure les valeurs, unités, périodes de référence, avertissements de données partielles, date d’actualisation et cibles de navigation.

Choisir avec le développeur entre calcul à la demande et synthèses mises en cache selon le volume réel. Si un cache est utilisé, préciser son invalidation après modification d’une donnée source.

Les restrictions sur les rémunérations doivent être appliquées côté accès aux données, et pas seulement en masquant un composant visuel.

## 8. Principes d’interface

- Libellés accessibles à un non-spécialiste.
- Cinq indicateurs principaux maximum.
- Éviter les répétitions de chiffres sans information supplémentaire.
- Chaque montant indique sa nature et sa période.
- Une couleur accompagne toujours un texte ou un symbole explicite.
- Les états vides proposent une action utile.
- Prévoir les états chargement, erreur, absence de données et données partielles.
- Sur mobile, conserver une hiérarchie claire : contexte, indicateurs, priorités, détail.

## 9. Lots de développement

| Lot | Contenu | Résultat attendu |
|---|---|---|
| 0 — Cadrage | Inventaire des données, dictionnaire des indicateurs, statuts, règles financières, droits | Définitions validées avant codage |
| 1 — Synthèse MVP | Filtres, cartes, prochaines dates, budget, paiements, équipe, navigation | Vue globale fiable et compréhensible |
| 2 — Pilotage | Alertes, complétude, préparation, écarts et liens contextuels RADAR | Passage immédiat de la synthèse à l’action |
| 3 — Personnalisation | Blocs activables, organisation de la page, comparaisons, imports complémentaires | Adaptation aux usages réels |

Ne pas chiffrer le délai avant examen du modèle existant et des sources disponibles.

## 10. Critères d’acceptation

- [ ] Le filtre de période actualise tous les blocs concernés.
- [ ] Le filtre projet/tournée restreint correctement les données.
- [ ] Chaque chiffre ouvre le détail qui permet de le vérifier.
- [ ] Une option n’est pas comptée parmi les dates confirmées.
- [ ] Une date annulée est exclue des prochaines représentations.
- [ ] Une subvention accordée n’est pas considérée automatiquement comme encaissée.
- [ ] Un règlement partiel réduit correctement le restant à encaisser.
- [ ] Un coût absent affiche « À compléter » et non zéro.
- [ ] Le coût employeur n’est pas additionné une seconde fois au brut qu’il inclut.
- [ ] Les personnes sont dédupliquées dans le compteur d’équipe.
- [ ] Les frais communs ne sont pas comptés deux fois.
- [ ] Les données partielles sont signalées dans les totaux concernés.
- [ ] Une modification source est répercutée dans BÒRD et RADAR.
- [ ] Les droits protègent les rémunérations individuelles et les données des autres structures.
- [ ] Les états vide, erreur et chargement sont pris en charge.
- [ ] Une base incomplète n’affiche pas un message trompeur « Tout est à jour ».

## 11. Scénarios de recette à préparer

1. Structure sans projet ni date : états vides et actions de démarrage.
2. Tournée avec options, dates confirmées et annulation : compteurs distincts.
3. Subvention accordée mais non versée : séparation budget/paiement.
4. Créance réglée partiellement : solde et retard correctement calculés.
5. Personne affectée à plusieurs dates : compteur dédupliqué et coûts correctement agrégés.
6. Équipe avec coûts manquants : total marqué incomplet.
7. Frais de tournée ventilés : absence de double comptage.
8. Compte sans droit de consultation des rémunérations : accès refusé aux détails protégés.

## 12. Décisions à valider avant développement

- [ ] Périmètre exact et fonctions existantes de RADAR.
- [ ] Définition de la saison et du projet actif.
- [ ] Date de référence de chaque indicateur.
- [ ] Choix HT/TTC et traitement des éventuelles devises multiples.
- [ ] Règle d’actualisation du budget et de consommation des prévisions.
- [ ] Sources disponibles pour rémunérations, paiements et subventions.
- [ ] Droits d’accès aux données d’équipe et aux montants individuels.
- [ ] Seuils et priorités des alertes.
- [ ] Fréquence d’actualisation et comportement après modification.

## 13. Repères concurrentiels et intention de différenciation

Repères issus de la note de cadrage précédente, à revalider lors d’une veille dédiée :
- Orféo présente un suivi budgétaire collaboratif et opérationnel : https://orfeo.pro/blog/spectacle-vivant-orfeo-permet-de-gerer-le-budget-en-equipe-et-en-temps-reel
- La documentation de Bob Booking référence les budgets liés ou non à une date et le suivi de tournée : https://aide-en-ligne.bobelweb.eu/organisation-des-donnees-schemas/
- Mascaron présente une approche CRM culturel et de gestion de documents commerciaux : https://www.mascaron.eu/

Hypothèse de différenciation à tester : une synthèse plus immédiatement compréhensible et actionnable pour l’artiste-entrepreneur, plutôt qu’une promesse de nouveauté fondée sur la seule présence de budgets et de plannings.

## 14. Brief de réunion

> Je veux que BÒRD permette de comprendre toute mon activité d’un coup d’œil : mes projets, mes dates, mon budget, les paiements et les personnes mobilisées. Chaque chiffre a une définition claire et ouvre son détail. BÒRD montre la situation générale ; RADAR accompagne le suivi et l’anticipation de tournée. Les deux utilisent les mêmes données, sans double saisie.
