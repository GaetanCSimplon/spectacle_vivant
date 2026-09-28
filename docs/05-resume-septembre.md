# Spectacle Vivant — point d'étape

28 septembre 2026 · @Get

L'application permet déjà de se connecter, de naviguer dans un menu, de consulter la liste de ses dates, de créer une date en 5 étapes, de compléter toutes ses informations, de tenir à jour la fiche de sa structure, puis de générer le contrat de cession en PDF, calé sur le modèle fourni par le métier. Le reste du cycle (devis, factures, feuille de route, paiements) reste à construire.

## Le projet en bref

Spectacle Vivant est une application web, pensée d'abord pour le téléphone, qui aide les artistes auto-produits, les petites compagnies et les associations à gérer seuls leurs dates de concert. L'objectif n°1 est la simplicité : une prise en main en moins de 5 minutes, avec le vocabulaire du métier et sans jargon juridique ou comptable.

Voici les mots utilisés dans l'application :

| Dans l'application | Ce que c'est |
| --- | --- |
| Producteur ou Artiste | L'utilisateur : la compagnie, l'association ou l'artiste qui vend le spectacle. Le contrat l'appelle « le producteur » ou « l'artiste », au choix |
| Organisateur | Le client qui achète le spectacle et à qui l'on facture |
| Lieu | L'endroit où a lieu la représentation |
| Spectacle | Ce que l'artiste vend : titre, durée, nom du groupe, numéros SACEM |
| Date | Une représentation : elle relie un spectacle, un organisateur, un lieu, un jour et un prix |
| Contrat de cession | Le PDF rattaché à une date |

Attention : dans les échanges avec le métier, le mot « structure » désigne parfois l'organisateur ou le lieu. Dans l'application, « Ma structure » désigne la compagnie de l'utilisateur.

## Ce qui fonctionne aujourd'hui

Dix fonctions sont opérationnelles. L'application tourne pour l'instant uniquement sur l'ordinateur du développeur : elle n'est pas encore en ligne, car l'hébergement de test attend la création d'un compte.

| Fonction | Ce qu'elle fait | État |
| --- | --- | --- |
| Compte et connexion | Inscription et connexion par e-mail, avec vérification de l'adresse | Fonctionne ; « mot de passe oublié » pas encore testé |
| Structures séparées | Chaque compagnie ne voit que ses propres données | Fonctionne, testé |
| Navigation principale | Menu avec 4 entrées (Accueil, Mes dates, Nouvelle date, Ma structure) : barre basse sur mobile, liens dans l'en-tête sur ordinateur | Fonctionne |
| Liste « Mes dates » | Les dates à venir (les plus proches d'abord), puis les dates passées ; chaque ligne ouvre la date | Fonctionne, testé |
| Création d'une date | 5 étapes : spectacle, organisateur, lieu (à choisir ou à créer sur le moment), date et prix, récapitulatif | Fonctionne |
| Compléter la date | Une page pour saisir tout ce dont le contrat a besoin : horaires, participants, invitations, numéros SACEM, jauge, représentants, ville du tribunal, signataire | Fonctionne, testé sur mobile |
| Page « Ma structure » | Fiche de la structure de l'utilisateur ; modifiable par le propriétaire, lecture seule pour un membre | Fonctionne, testé |
| Contrat de cession en PDF | Aperçu et téléchargement, 3 pages A4, les 9 articles du modèle du métier | Fonctionne ; filigrane « PROJET » tant qu'un professionnel ne l'a pas relu |
| Contrat signé figé | Un contrat marqué « signé » n'est plus modifiable ni régénéré | Règle en place et testée ; pas encore de bouton pour signer |
| Rôles | Le propriétaire modifie tout ; un membre ne peut pas modifier les informations de la structure | Fonctionne, testé |



## Parcours type d'une date

De la connexion au contrat à signer, l'utilisateur passe par sept étapes.

1. **Se connecter** avec son adresse e-mail. Le menu principal (Accueil, Mes dates, Nouvelle date, Ma structure) est visible partout.
2. **Consulter « Mes dates »** (facultatif) : la liste des dates à venir puis passées, pour retrouver une date déjà créée.
3. **Créer la date** en 5 écrans :
   - le spectacle, choisi dans la liste ou créé sur le moment (titre, durée, prix indicatif) ;
   - l'organisateur, choisi ou créé (nom, SIRET, adresse de facturation, e-mail) ;
   - le lieu, choisi ou créé (nom, adresse) ;
   - la date, le prix HT et les conditions particulières ;
   - un récapitulatif à valider.
4. **Arriver sur l'écran « Date créée »**, avec un message de confirmation et trois boutons : compléter la date, voir l'aperçu du contrat, télécharger le contrat.
5. **Compléter la date** (facultatif) sur une seule page, en cinq blocs : la date, le spectacle, le lieu, l'organisateur, la signature. Un seul bouton « Enregistrer ». Les informations de la structure se renseignent maintenant depuis le menu « Ma structure », pas ici.
6. **Ouvrir l'aperçu du contrat** : un PDF de 3 pages. Toute information non renseignée apparaît en pointillés (……) pour être complétée à la main.
7. **Télécharger le contrat** et le faire signer. Le passage de la date à « signée » n'a pas encore d'écran ; la règle qui fige le PDF existe déjà.

## Cas d'usage

Neuf situations à montrer lors d'une démonstration, toutes déjà testées.

| Cas | Ce que fait l'utilisateur | Ce que fait l'application |
| --- | --- | --- |
| 1. Créer une date vite | Choisit ou crée le spectacle, l'organisateur et le lieu, puis saisit la date et le prix | Enregistre la date et propose aussitôt le contrat |
| 2. Obtenir un contrat | Clique sur « Aperçu du contrat » | Génère un PDF de 3 pages avec les informations disponibles |
| 3. Se nommer « artiste » ou « producteur » | Choisit sa désignation dans « Ma structure » | Adapte tout le texte du contrat (« L'ARTISTE » ou « LE PRODUCTEUR », avec les bons articles) |
| 4. Concert gratuit | Coche « concert gratuit » | Grise le prix des places, le met à 0 et l'affiche comme gratuit dans le contrat |
| 5. Informations incomplètes | Laisse des champs vides | Imprime des pointillés à compléter à la main, sans rien bloquer |
| 6. Signataire différent du représentant | Renseigne le nom et la qualité du signataire | Affiche cette personne dans le bloc de signature |
| 7. Utilisateur non propriétaire | Complète les informations d'une date | Lui laisse tout faire sauf modifier les informations de la structure |
| 8. Deux compagnies sur l'application | Chacune travaille de son côté | Empêche l'une d'ouvrir ou de voir les données de l'autre (page introuvable) |
| 9. Contrat signé | Marque le contrat comme signé (cet écran reste à créer ; testé pour l'instant en modifiant directement la base) | Refuse toute modification et conserve le PDF tel quel |

## Le contrat généré

Le PDF reprend les 9 articles du modèle fourni par le métier, dans le même ordre, avec les deux parties, l'exposé (A et B), les horaires, les obligations de chacun, le prix, les assurances, l'annulation, la compétence juridique, la publicité, puis la date et les signatures avec la mention « lu et approuvé ».

Certaines parties du texte changent selon ce que l'utilisateur a saisi :

| Information saisie | Effet dans le contrat |
| --- | --- |
| Désignation « artiste » ou « producteur » | Tout le texte suit, avec les bons articles |
| Nombre d'invitations supérieur à 0 | La phrase sur les invitations et les laissez-passer presse apparaît ; sinon elle disparaît |
| Concert gratuit | Article 4 : « gratuit : oui », prix des places masqué |
| Structure en franchise de TVA ou non assujettie | Article 5 : « TVA 0 € » et « TVA non applicable — article 293 B du CGI » |
| Structure assujettie à la TVA | La TVA est laissée en pointillés : ce cas n'est pas encore géré |
| Ville du tribunal | Article 8 : « tribunaux de … » avec la ville saisie |
| Signataire | Le bloc de signature affiche son nom et sa qualité |
| Champ non renseigné | Pointillés (……) à compléter à la main |

Le modèle d'origine a été nettoyé : les fautes de frappe sont corrigées (« ORGANISTAEUR », « hébéerments », « est-t-il »), la mention « Nécitge 2000 » est retirée (elle ressemblait à un reste d'un ancien nom de structure) et « Siret / APA » est devenu « SIRET », faute de savoir ce que signifie APA.

Un bandeau « PROJET — modèle non relu par un professionnel » figure en haut du PDF. Il restera tant qu'un juriste ou un expert n'aura pas validé le texte.

## Sécurité et rôles

Une compagnie ne peut jamais voir ni ouvrir les données d'une autre : c'est la règle n°1 du projet. Si elle tente d'ouvrir l'adresse d'une date qui ne lui appartient pas, elle obtient une page « introuvable ». Cette séparation est vérifiée par des tests automatiques à chaque modification, et elle a été contrôlée à la main avec deux compagnies.

Deux rôles existent :

- **Propriétaire** : crée et complète les dates, et peut modifier les informations de la structure (SIRET, adresse, représentant, ville du tribunal, désignation dans le contrat) depuis la page « Ma structure ».
- **Membre** : crée et complète les dates ; sur la page « Ma structure », il voit les mêmes informations mais ne peut pas les modifier (la tentative est refusée par l'application).

Toutes les pages exigent une connexion, sauf l'inscription et la connexion. Il n'existe pas encore d'écran pour inviter un membre ; un rôle intermédiaire (un utilisateur non propriétaire qui pourrait modifier la structure) est à décider plus tard.

Un contrat marqué « signé » garde son PDF figé : ni les informations ni le fichier ne peuvent être modifiés ensuite.

## Ce qui manque encore

La version actuelle prouve le parcours principal, mais elle est loin d'un produit complet. Voici ce qui manque, du plus visible au plus technique.

**Dans l'application**

- Pas de calendrier des dates, ni de page de détail d'une date (infos, documents, feuille de route, paiements réunis) : la liste ouvre directement l'écran « Date créée ».
- Pas d'écran pour marquer un contrat « signé », ni pour faire évoluer le statut d'une date (option, confirmée, signée, annulée).
- La page « Ma structure » n'a pas encore le numéro de TVA, l'IBAN, le logo, ni la forme juridique en liste de choix.
- Pas de parcours d'accueil guidé pour un nouvel utilisateur, ni de confirmation d'e-mail activée.
- Pas de devis ni de factures, pas de feuille de route, pas de suivi des paiements et des dépenses, pas d'export.
- Le logo de la structure n'apparaît pas dans le contrat, et le régime « assujetti à la TVA » n'est pas géré.

**Autour du projet**

- L'application n'est pas en ligne : l'hébergement de test attend un compte.
- Le contrat n'a pas été relu par un professionnel (juriste, expert-comptable ou association d'artistes), d'où le bandeau « PROJET ».
- Les entretiens avec de vrais artistes n'ont pas encore eu lieu : le besoin n'est pas encore confirmé sur le terrain.

## Questions pour vous

Quatorze points attendent une réponse du métier : sept sur le contrat, sept sur le périmètre du produit.

**Sur le contrat**

| N° | Question | Pourquoi c'est important |
| --- | --- | --- |
| 1 | Que signifie « APA » dans « Siret / APA » ? | Aujourd'hui seul le SIRET est affiché |
| 2 | Le contrat doit-il porter la date du jour où le PDF est généré, ou une date fixée à la signature ? | Actuellement « Fait à …, le … » prend la date du jour de chaque aperçu, tant que le contrat n'est pas signé |
| 3 | La mention « article 293 B du CGI » convient-elle aux structures non assujetties (par exemple des associations) comme aux structures en franchise de TVA ? | Le modèle d'origine n'en cite qu'une, appliquée aux deux cas |
| 4 | Combien d'invitations prévoir par défaut ? | Le modèle disait 5 en dur ; c'est désormais un nombre saisi, vide par défaut (la phrase disparaît s'il vaut 0) |
| 5 | Le tribunal compétent doit-il rester propre à chaque structure ? | Le modèle disait Montpellier ; chaque utilisateur saisit sa propre ville |
| 6 | La mention « Nécitge 2000 » était-elle voulue ? | Elle a été retirée, en pensant à un reste d'un ancien nom |
| 7 | Qui peut relire le contrat : juriste, expert-comptable, CAE, association d'artistes ? | Sans relecture, le bandeau « PROJET » reste et la bêta ne peut pas démarrer |

**Sur le périmètre du produit** (questions Q1 à Q7 du cahier des charges, issues du document de logique métier)

| N° | Question | Pourquoi c'est important |
| --- | --- | --- |
| Q1 | Un suivi des prospects (fiche de qualification, statuts, historique des échanges) est-il indispensable dès le début ? | Fonction non prévue aujourd'hui, elle alourdirait beaucoup le démarrage |
| Q2 | Faut-il gérer d'autres contrats que la cession (coréalisation, location de salle) ? | Aujourd'hui seule la cession existe, ce qui correspond au modèle reçu |
| Q3 | Le suivi en direct du jour J (arrivée de l'équipe, horaires réels, incidents) est-il utile à des artistes qui jouent quelques dates par an ? | Aujourd'hui la feuille de route sera un document à consulter, sans suivi en direct |
| Q4 | La paie des intermittents (déclaration préalable, relevés d'heures, GUSO) doit-elle rester hors de l'application ? | Risque juridique élevé et grosse charge de travail si elle entre dans le périmètre |
| Q5 | Les déclarations SACEM, SACD et CNM restent-elles hors de l'application ? | Le contrat les met à la charge de l'organisateur, ce qui va dans ce sens |
| Q6 | L'historique par partenaire et les relances automatiques sont-ils pour plus tard ? | Dépend de la réponse à Q1 |
| Q7 | Un même contrat doit-il pouvoir couvrir plusieurs dates (tournée négociée en un seul accord) ? | Aujourd'hui un contrat correspond à une seule date, comme le modèle reçu |

## Prochaines étapes

Le prochain jalon est le premier sprint du MVP (navigation, accueil guidé, page « Ma structure »). Trois blocages extérieurs au code freinent le reste : le compte d'hébergement, le relecteur du contrat et vos réponses aux questions ci-dessus.

| Étape | Contenu | Dépend de |
| --- | --- | --- |
| Mise en ligne de test | Hébergement en France, surveillance des erreurs, test par 3 personnes du milieu | Création du compte d'hébergement |
| Validation métier | Entretiens avec des artistes, relecture du contrat par un professionnel, réponses aux questions | Vous et le relecteur |
| Fin du Sprint 3.1 | Confirmation d'e-mail, parcours d'accueil guidé (5 écrans maximum), gestion du régime de TVA. Le menu et la page « Ma structure » sont déjà faits | Rien de bloquant |
| Sprint 3.2 | Carnet d'adresses (organisateurs, lieux, contacts) et fiches spectacle, avec recherche | Sprint 3.1 |
| Sprint 3.3 | Statuts d'une date, liste, calendrier mensuel, page de détail | Sprint 3.2 |
| Sprint 3.4 | Contrats finalisés : marquage « signé », historique, stockage sécurisé des PDF | Réponses aux questions sur le contrat |
| Sprint 3.5 | Devis et factures : numérotation sans trou, avoirs, mentions de TVA | Relecteur comptable |
| Sprint 3.6 | Feuille de route mobile, partagée par un lien secret | Sprint 3.3 |
| Sprint 3.7 | Paiements, dépenses, bilan par date, tableau de bord, export pour le comptable | Sprint 3.5 |
| Sprint 3.8 | Pages légales, audit de sécurité, recette complète, mise en production | Tous les sprints précédents |
| Bêta fermée | 5 à 10 utilisateurs réels pendant 4 semaines, corrections | MVP en production |
| Version payante | Abonnement, facture électronique, signature électronique, relances | Retours de la bêta |

Le MVP est estimé à 6 à 8 semaines de travail, avec une marge de 30 à 50 % pour un développeur seul.
