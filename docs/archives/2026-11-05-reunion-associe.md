# Réunion avec l'associé — 2026-11-05

Notes brutes du développeur, puis tri et décisions (réponses du 2026-11-05). Fichiers reçus : `docs/produit/specification-feuille-de-route-type.md` et `docs/marque/sources-associe/maquette-site-vitrine.html`.

## Notes de la réunion
- **Ergonomie** : bouton précédent / suivant pour faciliter la navigation.
- **Mes dates** : « Compléter ma date » devient « Compléter le contrat » ; champ « Gestion d'équipe » peuplé par les données du spectacle et de la fiche équipe ; bouton d'envoi du formulaire de complétion de la fiche organisateur (phase de contractualisation) ; « Régie de tournée » : formulaire envoyé à l'organisateur pour les informations de la tournée (get in, balance, restauration, hébergement…).
- **Feuille de route** : côté artiste, accès aux documents (contrats, factures…) ; partie « Notes » plus haut (informations importantes) ; contacts (organisateurs, lieux).
- **Gestion sociale** : affichage et export des données par artiste pour la paie. Artiste : nom, prénom, date de naissance, adresse, n° de sécurité sociale, emploi occupé (artiste ou technicien). Employeur : SIRET, APE, n° de licence. Date : date, nombre de cachets, montant du cachet. Spectacle : numéro d'objet.
- **Application côté artiste / technicien (hors MVP)** : vue Accueil (résumé des dates et du social), Profil (modification des informations), Dates (accès aux feuilles de route), Social.

## Décisions (2026-11-05)
1. **Précédent** : un bouton « Retour » en haut de chaque page, vers la page précédente (le navigateur le fait déjà, le bouton est voulu pour la simplicité).
2. **Contacts** sur la feuille de route : afficher ceux de l'organisateur et du lieu.
3. **Documents pour l'artiste** : un accès rapide pendant la date ou la tournée. Exemple 1 : montrer le contrat signé. Exemple 2 : le propriétaire de la structure ajoute à la feuille de route des documents qu'il a téléversés (billet de train…). Mécanisme (lien partagé, espace personnel de chaque membre) et règle sur les données financières : à trancher dans un plan avant de coder.
4. **Site vitrine** : le design de la maquette est retenu, mais le site ne parle que de ce qui existe. **Offre commerciale : trois formules** (Découverte, Pilotage, Tournée Connectée), comme dans la maquette ; la page Tarifs et les quotas viendront plus tard (décision Q9 précisée, voir `cahier-des-charges.md` §1.5).

## Écarts relevés dans la maquette du site (à corriger à l'intégration)
Fonctions promises mais absentes (Radar, espace artiste mobile, application mobile de gestion, signature électronique, synchronisation Google Agenda, comparaison prévu / réel) ; « Commencer gratuitement » et `/inscription` alors que l'inscription est sur invitation (`/accounts/signup/`) ; « BÒRD PRO » en capitales (la charte veut « Bòrd Pro ») ; polices chargées depuis Google Fonts (la charte les veut hébergées dans `static/fonts/`) ; images `assets/GIMIC_*.svg` non fournies.
