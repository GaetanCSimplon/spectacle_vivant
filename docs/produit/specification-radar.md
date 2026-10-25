
> **Statut (2026-10-25) : reporté après la bêta** (décision avec l'utilisateur). Document fourni par l'associé, repris tel quel (seul le nom « Scènsemble », ancien nom du produit, est corrigé en « Bòrd Pro »). Analyse et ordre d'implémentation proposé : `docs/produit/etat-du-projet.md`, section « Après le MVP ». Rien n'est codé.

**Module « Radar de tournée »**


**1. Intention produit**
BÒRD PRO aide les artistes entrepreneurs et les petites structures du spectacle vivant à gérer leurs dates sans multiplier les fichiers et les ressaisies. 
Le module « Radar de tournée » doit transformer les dates saisies en une vue d’aide à la décision : ordre géographique, distances indicatives, budget prévisionnel et actions à effectuer.
La promesse n’est pas de remplacer un outil spécialisé de cartographie, de paie ou de calcul carbone. Elle est d’aider l’utilisateur à repérer rapidement les oublis, les coûts à anticiper et les occasions de mieux organiser les dates.

-> Principe produit : une date est créée une seule fois et réutilisée dans le calendrier, le contrat, le budget, la feuille de route et le Radar.
L’idée : le Radar de tournée
À partir des dates envisagées et de quelques données simples — villes, cachets, équipe, frais de route et hébergement — Bòrd Pro afficherait :

-     Les incohérences à vérifier : dates trop rapprochées, longs trajets, horaires ou informations logistiques manquantes.
-     Le coût prévisionnel réel de chaque date et de la tournée : recettes attendues moins frais saisis.
-     Les occasions d’optimiser le parcours : dates proches à regrouper, zone où une date supplémentaire pourrait réduire les kilomètres à vide.
-     Les prochaines actions : relancer tel lieu, confirmer telle option, demander les conditions techniques ou valider le budget.
-     Une synthèse partageable avec les personnes concernées : itinéraire, horaires, contacts, documents et points restant à confirmer.

L’originalité ne serait donc pas « on a aussi un agenda », mais : « on vous aide à décider quoi faire de votre tournée, avant d’engager des frais ».

**2. Utilisateurs visés**
Artiste ou groupe qui gère directement son activité.
Petite compagnie ou structure de production sans équipe administrative dédiée.
Personne chargée de la diffusion ou de la tournée.
Le module doit être compréhensible sans formation et utilisable sur ordinateur comme sur téléphone.

3. Parcours utilisateur cible
L’utilisateur crée ou sélectionne un spectacle et une version (distribution, équipe, besoins techniques).
Il ajoute une date et sélectionne l’organisateur / le lieu depuis le CRM, ou le crée.
Il renseigne au minimum la ville ou l’adresse, la date, le statut de la date et les recettes/frais connus.
La date apparaît dans le calendrier et dans le Radar.
Le Radar présente les dates, les informations manquantes, une estimation de distance et le budget renseigné.
L’utilisateur consulte les alertes, ajoute une prochaine action (relancer, confirmer, demander une information) et peut partager/exporter la synthèse.

**4. Périmètre fonctionnel MVP**
**4.1 Vue Radar**
Vue chronologique des dates par tournée / période.
Vue liste mobile, avec ville, date, organisateur, statut et prochaine action.
Carte facultative si un service cartographique adapté est retenu ; le MVP peut fonctionner sans carte.
Filtres : spectacle, période, statut, organisateur, tournée.
Affichage explicite du caractère estimatif des distances et des coûts calculés.

**4.2 Alertes simples et explicables**
Créer des règles configurables, sans IA au MVP :
Adresse ou ville manquante.
Date sans statut clair ou option arrivée à échéance.
Contrat non envoyé / non signé, si ces statuts existent dans le workflow.
Date passée sans état « jouée », « annulée » ou autre clôture.
Facture à émettre ou paiement à vérifier, selon le statut enregistré.
Frais ou montant de cession non renseignés.
Distance entre deux dates supérieure à un seuil paramétrable par l’utilisateur.
Dates rapprochées avec temps de trajet estimé potentiellement contraint : présenter comme point à vérifier, jamais comme validation de sécurité ou de faisabilité.
Chaque alerte indique sa cause, la date concernée et une action possible. L’utilisateur peut ignorer ou marquer l’alerte comme traitée.

**4.3 Budget prévisionnel**
Par date, permettre de saisir ou reprendre :
Recettes prévues (cession, coréalisation ou autres lignes configurables).
Dépenses prévues (transport, hébergement, repas, location, rémunérations estimées et autres frais).
Dépenses réelles, séparées du prévisionnel.
Statut de facturation et d’encaissement si le module financier correspondant existe.
Calculs de base :
Solde prévisionnel = recettes prévues − dépenses prévues.
Solde réalisé = recettes encaissées/saisies comme réalisées − dépenses réelles saisies.
Totaux par date et pour la tournée.
Ne pas présenter le solde comme bénéfice comptable ou résultat certifié. Afficher les éléments non renseignés et la date de dernière mise à jour.

**4.4 Contacts et occasions à proximité**
MVP : l’utilisateur peut filtrer/afficher les organisateurs déjà présents dans sa base autour des villes de la tournée, si les données de localisation sont disponibles. La proximité est une aide à la recherche, pas une recommandation de booking.
Ne pas envoyer de courriel ou de message automatiquement. Toute prospection demeure déclenchée et validée par l’utilisateur.

**4.5 Partage et export**
Export PDF ou vue imprimable de la synthèse de tournée.
Lien de partage sécurisé en option, désactivable et révocable, avec durée de validité.
Vue partageable limitée aux informations logistiques nécessaires ; ne pas exposer les budgets internes par défaut.
Prévoir l’export CSV des dates et lignes budgétaires.

**5. Hors périmètre du MVP**
Optimisation automatique de tournée ou promesse d’itinéraire optimal.
Calcul carbone certifié ou affirmation de conformité environnementale.
Calcul de temps de repos, conformité au droit du travail ou validation de sécurité.
Moteur de paie intermittent.
Envoi automatique de prospection.
IA générative qui prendrait des décisions ou modifierait des données sans validation.
Réservation de transport ou d’hébergement.
Ces fonctions pourront faire l’objet d’études séparées après retours utilisateurs.

**6. Modèle de données proposé**
Réutiliser les entités existantes ; éviter de dupliquer les données du CRM et du booking.
Tournee
id
nom
id_spectacle / id_version (si une tournée porte une version précise)
date_debut, date_fin (calculables ou éditables)
statut
devise
paramètres utilisateur (seuil d’alerte distance, unités)
DateEvenement
id
id_tournee (nullable si date isolée)
id_organisateur
id_lieu (ou adresse de représentation)
id_spectacle, id_version
date_debut, date_fin / horaires connus
statut_booking
adresse, code_postal, ville, pays
latitude, longitude (nullable, avec provenance et date de géocodage)
montant_recettes_previsionnelles
statut_facture, statut_encaissement (références aux objets existants, pas de duplication)
notes_logistiques
prochaine_action, prochaine_action_date
LigneBudgetDate
id
id_date_evenement
catégorie
libellé
nature (recette/dépense)
phase (prévisionnel/réel)
montant, devise
justificatif_id (nullable)
date_saisie, auteur_id
Alerte / Action (si l’architecture le justifie)
id, id_date_evenement, type, règle_source
description, priorité, créée_le
statut (ouverte/ignorée/traitée)
action_suggérée, échéance
auteur_id / assigné_a_id (si multi-utilisateur)

Ne pas stocker les distances comme vérité permanente : elles dépendent du point de départ, du mode de transport et du fournisseur de calcul. Si mises en cache, stocker fournisseur, méthode, date de calcul et unité.

**7. Architecture et intégrations**
Le module consomme les identifiants existants de dates, lieux, organisateurs, spectacles, contrats, factures et utilisateurs.
Les calculs financiers doivent être réalisés côté serveur ou dans une couche métier testée, avec règles d’arrondi et devise explicites.

Géocodage : prévoir une interface fournisseur interchangeable. Ne pas géocoder sans nécessité ; permettre une saisie manuelle et corriger une adresse.

Routage/distance : décider si l’on affiche une distance à vol d’oiseau (simple, non routière) ou une distance routière issue d’un fournisseur. Toujours étiqueter la méthode. Ne pas afficher un temps de trajet comme garanti.
Gérer les erreurs de fournisseur : le Radar reste utilisable sans carte ni géocodage.
Respecter les conditions d’utilisation, quotas, coûts, conservation et éventuelles restrictions d’affichage des fournisseurs cartographiques.
Prévoir une API interne pour obtenir les dates d’une tournée et ses agrégats, sans requêtes lourdes répétées côté interface.

**8. Règles métier et qualité des données**
Une date peut exister sans tournée ; rattachement à une tournée facultatif.
Une tournée peut contenir plusieurs dates et éventuellement plusieurs lieux.
Les données héritées du spectacle/version servent de valeurs par défaut ; une modification sur une date ne modifie pas rétroactivement la fiche spectacle.
Une date annulée n’est pas supprimée : conserver l’historique et son statut.
Les montants doivent distinguer prévu, engagé, facturé, encaissé et réalisé lorsque ces états sont disponibles ; ne pas les confondre.
Les devises et taxes éventuelles doivent suivre les règles déjà retenues dans l’application ; ne pas coder une règle fiscale implicite.
Toute donnée calculée doit pouvoir être expliquée et corrigée par l’utilisateur.

**9. Confidentialité et sécurité**
Contrôle d’accès par structure et rôle ; appliquer les permissions existantes.
Ne pas exposer les coûts, recettes ou données personnelles dans un lien public par défaut.
Les liens de partage doivent être révocables, limités dans le temps et protégés par un jeton non devinable.
Minimiser les données envoyées aux services tiers de géocodage/cartographie.
Journaliser les changements importants sur les dates, montants et statuts.
Prévoir export et suppression conformément aux règles de conservation applicables et à la politique de l’application.

**10. Écrans attendus**
Liste des tournées : nom, période, nombre de dates, état et indicateur de données manquantes.
Radar de tournée : dates chronologiques, alertes, prochaines actions, totaux budgétaires ; carte optionnelle.
Fiche date : logistique, booking, budget prévisionnel/réel, documents et historique.
Vue partage : informations pratiques uniquement, selon les permissions.

**11. Critères d’acceptation MVP**
Une date déjà créée dans le booking apparaît dans le Radar sans ressaisie.
Une date peut être créée sans adresse complète et reste consultable ; l’app signale ce qui manque.
Une tournée affiche correctement ses dates triées et ses totaux à partir des lignes saisies.
Le prévisionnel et le réel restent distincts.
Les alertes affichent une raison compréhensible et peuvent être traitées ou ignorées.
Une panne cartographique n’empêche ni l’accès aux dates ni la saisie du budget.
L’utilisateur peut exporter une synthèse sans divulguer les montants internes par défaut.
Les droits d’accès empêchent un autre compte/structure de consulter les données.
Les calculs et transitions de statut sont couverts par des tests automatisés.

**12. Découpage recommandé**
Lot 1 — utile sans dépendance externe
Tournée, rattachement de dates existantes, liste chronologique, alertes basées sur les données, budget prévisionnel/réel, prochaines actions.
Lot 2 — mobilité et partage
Interface mobile responsive, PDF/impression, lien de partage sécurisé et vue logistique.
Lot 3 — géographie
Géocodage, carte et estimation de distances, fournisseur interchangeable et contrôles de coûts/quotas.
**Lot 4 — aide à la décision**
Recherche des contacts CRM à proximité, indicateurs de regroupement de dates et tests utilisateurs. Toute suggestion reste explicable et validée par l’utilisateur.

**13. Indicateurs de validation produit**
À mesurer pendant un pilote, sans présumer du résultat :
Temps nécessaire pour créer et préparer une date.
Nombre de ressaisies évitées entre date, contrat, facture et feuille de route.
Part des dates avec une prochaine action renseignée.
Nombre d’alertes traitées / ignorées.
Utilisation de la synthèse ou du partage de tournée.
Retours qualitatifs : les alertes sont-elles pertinentes ou trop nombreuses ? Le budget aide-t-il à décider ?

14. Positionnement concurrentiel et différenciation
Orféo et Bob Booking couvrent déjà de nombreux besoins de gestion, de diffusion et de suivi des tournées. BÒRD PRO ne doit donc pas présenter comme unique une carte, une application mobile ou des rappels. La différenciation à tester est le Radar lisible pour l’artiste qui gère seul : dates centralisées, alertes explicables, budget de tournée compréhensible et prochaines actions au même endroit.
Le calcul d’impact environnemental n’est pas inclus comme calcul certifié. Une évolution pourra étudier un export ou une interopérabilité avec des outils spécialisés, après validation des méthodes et des données.

15. Décisions à confirmer avec le développeur
L’architecture actuelle possède-t-elle déjà une entité « tournée » ou suffit-il d’un regroupement de dates ?
Le budget doit-il reprendre les objets financiers existants ou introduire les lignes prévisionnel/réel ?
Pour le MVP, afficher une distance à vol d’oiseau, une distance routière via fournisseur, ou aucune distance ?
Quel fournisseur cartographique respecte le budget, les conditions d’usage et les besoins de couverture ?
Le partage de feuille de route est-il déjà prévu dans le produit ?
Quelles permissions s’appliquent aux artistes, administrateurs et collaborateurs ?
Quels champs sont obligatoires selon les types de contrat et les modes de production ?
Note de cadrage : cette note décrit une proposition fonctionnelle et technique à valider avec l’architecture, les coûts d’intégration et des tests avec des artistes. Elle ne constitue ni une validation juridique, ni un calcul comptable, social ou carbone certifié.
