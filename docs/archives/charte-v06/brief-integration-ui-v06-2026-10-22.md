# BÒRD PRO — Brief d’intégration graphique et UI

Version de transmission : 22 octobre 2026 · référence visuelle V06
Destinataire : développeur du projet / contributeurs du dépôt GitHub.

## 1. Objet de cette demande

Intégrer la direction visuelle validée dans l’application existante, sans reconstruire le produit à partir de la maquette et sans modifier les règles métier, les permissions ou la base de données par défaut.

Ce document explique QUOI intégrer et COMMENT le vérifier. La charte graphique PDF décrit les règles visuelles. Le HTML V06 montre le résultat attendu ; c’est une référence de conception, pas du code de production audité.

### Fichiers à joindre ensemble

- Le dernier HTML déjà livré : `BORD_PRO_dates_carte_feuille_de_route.html` (V06).
- Ce brief Markdown.
- La charte graphique PDF livrée avec ce brief.
- `LOGO_2.pdf`, master graphique fourni par le porteur de projet.

La pièce HTML doit être récupérée dans la livraison précédente et ajoutée au dépôt. Ce brief ne présume pas qu’elle s’y trouve déjà. Ne pas prendre une ancienne V04/V05 comme référence principale.

### Ce qui est arrêté / ce qui ne l’est pas

| Statut | Éléments |
|---|---|
| Direction retenue | Fond clair, cartes colorées franches, logo inchangé, Archivo / Instrument Sans / IBM Plex Mono, RADAR en bas à droite. |
| Contenus validés | Vocabulaire financier simplifié ; aucune simulation d’hébergement ; aucun tampon ; pas de slogan publicitaire dans les écrans de travail. |
| Parcours attendus | Dates en liste et en carte, feuille de route artiste, bòrd, budget lisible, transmission adaptée à l’équipe. |
| À inventorier dans le dépôt | Écrans et composants déjà présents, stack, données disponibles, navigation, authentification, moteur cartographique. |
| À arbitrer séparément | Fonctions absentes, moteur de routage, notifications, droits détaillés, partage réel, export de documents, connexion bancaire. |

Ne pas assimiler un bouton de maquette à une fonctionnalité disponible. Aucun accès au dépôt ni audit de son code n’a été réalisé pour produire ces documents.

## 2. Intention à respecter

L’utilisateur est un artiste qui gère lui-même son activité. Il doit comprendre sa prochaine date, les informations manquantes et le budget, sans jargon.

- Davantage de couleur que des bordures surlignées : utiliser des surfaces pleines bleu nuit, corail et bleu clair.
- Conserver une majorité de surfaces claires et blanches. Ne pas réintroduire le fond beige/marronnasse `#E9E4D6`.
- Une information peut être colorée sans devenir un bouton. Une action doit rester identifiable par sa forme, son libellé et ses états.
- Le corail peut porter une carte de synthèse et un bouton principal. Il ne signifie pas « erreur ».
- La couleur seule ne porte jamais un statut : pictogramme + libellé.
- Les noms de salle, personnes et montants de la maquette sont fictifs : aucun jeu de démonstration injecté en production.

## 3. Mode de travail proposé dans GitHub

### Organisation documentaire suggérée — à adapter au dépôt

```text
docs/design/
  README.md                 # Référence active et décisions
  integration-ui.md         # Ce brief
  charte-graphique.pdf
  references/
    brandboard-v06.html
  assets/
    LOGO_2.pdf
```

Les chemins ci-dessus sont proposés : ne pas déplacer les composants existants pour les faire correspondre à ce schéma.

### Ticket de départ

Titre : `UI — intégrer la direction graphique V06 BÒRD PRO`

Description :
> Appliquer la charte jointe et la référence HTML V06 aux composants et écrans existants. Commencer par un inventaire. Livrer une première tranche verticale : navigation, liste des dates, RADAR et une feuille de route mobile. Ne pas changer les règles de calcul, les permissions ou les APIs sans validation. Signaler les fonctionnalités manquantes et les traiter dans des tickets séparés.

### Découpage en pull requests

1. **Inventaire + tokens** : état des lieux, correspondance composants, variables de thème et assets.
2. **Socle UI** : typographies, navigation, boutons, champs, cartes, badges, états.
3. **Dates + feuille de route** : liste, navigation et consultation artiste responsive.
4. **Carte** : intégration au composant ou service existant ; différencier schéma et routage réel.
5. **Budget + RADAR** : présentation simple ; règles existantes conservées ou nouvelles règles explicitement validées.
6. **Recette transversale** : responsive, clavier, permissions, captures et régressions.

Une PR doit permettre une revue ciblée. Une refonte monolithique est à éviter.

### À inclure dans chaque PR

- Résumé et périmètre ; composants et écrans modifiés.
- Captures avant / après sur les mêmes données.
- Vérifications réellement exécutées, résultats et limites.
- Liste des comportements non implémentés.
- Risques de régression et méthode de retour arrière.
- Aucun nouveau package, service payant, tracking ou appel externe sans justification et accord.

## 4. Socle graphique à traduire dans le code

Les noms de variables sont indicatifs : les adapter au système de tokens existant.

```css
:root {
  --color-brand-night: #102440;
  --color-brand-coral: #FF6B5B;
  --color-brand-cream: #F5F2EA;
  --color-brand-gray: #687080;

  --color-canvas: #F2F5FA;
  --color-surface: #FFFFFF;
  --color-line: #D8E0EB;
  --color-text: #102440;
  --color-text-secondary: #5B6372;
  --color-info-surface: #DCE8F7;

  --color-success: #1F6B4A;
  --color-success-surface: #E4F0E8;
  --color-warning: #E3A21A;
  --color-warning-surface: #FFF0C8;
  --color-problem: #8E1F3F;
  --color-problem-surface: #F6E3EB;

  --font-heading: 'Archivo', sans-serif;
  --font-body: 'Instrument Sans', sans-serif;
  --font-data: 'IBM Plex Mono', monospace;

  --radius-control: 12px;
  --radius-card: 20px;
  --radius-section: 28px;
  --touch-target: 48px;
}

.heading {
  font-family: var(--font-heading);
  font-weight: 800;
  font-variation-settings: 'wdth' 112;
  letter-spacing: -0.04em;
}
.data {
  font-family: var(--font-data);
  font-variant-numeric: tabular-nums;
}
```

- Ne pas copier le CSS global de la planche dans l’application : il contient des règles de présentation des mockups.
- Charger uniquement les fontes et graisses utiles ; vérifier les licences et la politique d’hébergement du projet.
- Les fontes intégrées dans le PDF logo ne constituent pas une autorisation de les déployer sur le web.
- Utiliser le logo original et son symbole : pas un mot composé au clavier ni un dessin approximatif.
- Utiliser un export SVG validé lorsqu’il sera disponible. À défaut, conserver un rendu fidèle et transparent du fichier source ; ne pas prétendre qu’un PNG est vectoriel.

## 5. Composants attendus

| Composant | Comportement / apparence |
|---|---|
| Logo / symbole | Logo complet dans les zones de marque ; symbole compact pour RADAR. Pas de déformation ni recoloration improvisée. |
| Bouton principal | Fond corail, texte nuit, cible 48 px. Un CTA dominant par vue. |
| Bouton secondaire | Fond blanc, texte et contour nuit. |
| Carte de synthèse | Aplat de couleur, libellé explicite, valeur et limite éventuelle. Aucune information utile uniquement au survol. |
| Badge de statut | Icône + mot ; vert confirmé, ambre à suivre, bordeaux problème/incomplet. |
| Pavé de date | Jour + mois en mono. Contraste net ; ce n’est pas un statut financier. |
| Tableau / liste | Hiérarchie date → lieu → ville → statut → prochaine action. Version mobile adaptée. |
| Chronologie | Heures en mono, événement en texte, détails courts ; concert repéré sans couleur seule. |
| RADAR | Pastille en bas à droite + panneau ouvrable, liste de points utiles, accès au détail source. |
| Détail de calcul | Replié au départ ; bouton ou disclosure « Voir le détail du calcul ». |

Prévoir les états chargement, vide, erreur, succès, désactivé, sélectionné et focus. Ne pas afficher « confirmé », « enregistré » ou « transmis » avant l’événement réellement constaté.

## 6. Écrans et parcours de référence

### bòrd

Vue d’ensemble : prochaines dates, frais et informations à compléter. La navigation s’appelle `bòrd`, pas « Dashboard ». RADAR n’est pas un onglet.

### Dates — liste

- Date et horaire ; salle et ville ; statut ; préparation ; accès à la feuille de route.
- Distinguer date confirmée, contrat signé, paiement reçu et feuille de route prête : ce ne sont pas quatre synonymes.
- Ouvrir la vue carte sans perdre les dates, la tournée ni le filtre en cours.
- Présenter les contacts à recontacter et échéances lorsque ces données existent.

### Dates — carte et itinéraire

La carte de la V06 est schématique. Elle relie les étapes dans l’ordre : Béziers (départ), Montpellier, Toulouse, Nîmes (option).

- Réutiliser exactement les mêmes identifiants de dates que la liste.
- Cliquer sur un repère ouvre les informations de cette date.
- Distinguer les étapes en option par le tracé ET le libellé.
- Ne pas afficher de kilomètres, trafic ou durées calculés depuis le schéma SVG.
- S’il existe déjà un moteur cartographique, conserver son architecture et documenter les ajustements UI.
- Sinon, distinguer deux tickets : présentation de la carte / choix d’un service de géocodage et routage. Coûts, clés, attribution, conditions et confidentialité restent à valider.
- Adresse inconnue : signaler le point manquant ; ne pas le placer arbitrairement au centre-ville comme si c’était la salle.
- Ne pas présenter la vue comme un outil de navigation routière tant que cela n’est pas développé.

### App artiste — feuille de route

Écran de consultation mobile, défilant :

1. Date, salle, ville, groupe ; version et dernière mise à jour.
2. Chronologie : départ, arrivée matériel, balance, repas, concert, démontage.
3. Accès matériel et adresse réelle lorsqu’elle est connue.
4. Contact du lieu et coordonnées renseignées.
5. Hôtel : adresse, réservation, chambres et arrivée.
6. Documents utiles : fiche technique, plan, autres pièces disponibles.
7. Actions de partage / impression uniquement si réellement développées et autorisées.

Les exemples d’horaires ne deviennent pas des valeurs par défaut. Prévoir passage à minuit, date du lendemain et fuseau du lieu si pertinent. Ne pas attribuer « disponible hors connexion » sans mécanisme réel.

### Transmission équipe

Les informations financières et contrats de gestion ne sont pas visibles dans la vue équipe par défaut. Cela doit être assuré par les permissions et réponses serveur, pas uniquement par un élément caché en CSS.

La feuille de route doit indiquer sa version. Une confirmation de lecture n’est ni une signature ni un accord contractuel. Aucun envoi automatique dans ce lot graphique.

## 7. Budget : vocabulaire validé

| Éviter dans la lecture principale | Employer |
|---|---|
| Recettes de cession prévues | Ce que les concerts doivent rapporter |
| Dépenses renseignées | Les frais déjà ajoutés |
| Solde partiel | Ce qu’il reste après ces frais |
| Disponible saisi | L’argent disponible aujourd’hui |
| Écart de trésorerie | Ce qu’il manque pour payer les prochains frais |

Les termes métier précis peuvent rester dans le modèle de données et les aides détaillées. Ne pas fusionner encaissement, facture, prix de cession et salaire.

### Jeu de démonstration à conserver uniquement pour les tests

- Recettes attendues : 450 € + 500 € + 400 € = 1 350 € ; la date de 400 € est en option.
- Frais ajoutés : 312 € + 240 € + 118 € + 85 € = 755 €.
- Reste après ces seuls frais : 595 €.
- Les rémunérations et charges de l’équipe sont absentes : ne pas nommer ce résultat « bénéfice net » ou « somme disponible pour l’artiste ».
- 260 € de frais déjà payés ; 495 € restent à payer avant le prochain paiement prévu.
- Disponible saisi : 180 €. Manque avant ce paiement : 315 €.
- Les 180 € sont une photographie saisie distincte du résultat de la tournée. Ne pas les déduire du seul budget.

Un coût manquant n’est pas un coût égal à zéro. Prévoir un statut « non renseigné ».

## 8. RADAR : trois messages compréhensibles

### A. Paiements

Titre : **Des frais arrivent avant le prochain paiement.**

> Tu as 180 € disponibles et 495 € à payer. Il manque 315 € pour couvrir ces frais.

Action : `Voir les frais à payer`.
Détail : période concernée, frais restants, montant disponible, date de mise à jour et prochain paiement attendu. Si une de ces données manque, ne pas afficher un montant calculé comme certain.

### B. Date en option

Titre : **Une date n’est pas encore confirmée.**

> Les 400 € de Nîmes sont inclus dans ton budget. Attends la confirmation du lieu avant de compter dessus.

Action : `Voir la date` ou `Voir la date sur la carte`.
Ne déclencher ce message que si cette recette incertaine est effectivement incluse dans le total affiché.

### C. Coûts manquants

Titre : **Ton budget n’est pas encore complet.**

> La rémunération de l’équipe n’a pas été ajoutée. Les 595 € ne représentent donc pas encore ce que tu pourras garder.

Action : `Compléter le budget`.
Ne pas conclure qu’une tournée est rentable à partir des seuls frais de transport, hôtel, repas et matériel.

### Comportement de RADAR

- Pas un chatbot générique ni un onglet indépendant.
- Pastille avec symbole, nom et nombre de points ; position tenant compte de la navigation mobile et des zones sûres.
- Ouverture explicite, fermeture possible, touche Échap, gestion du focus.
- Un rappel → une cause → une action utile → détail accessible.
- Les rappels proviennent des mêmes données que les écrans, pas d’un second budget indépendant.
- Aucun paiement, message, statut ou engagement modifié automatiquement.
- Aucun modèle d’IA n’est nécessaire pour les trois exemples : des règles explicites et testables suffisent.
- Si les règles sont absentes du produit, les traiter comme un développement distinct, pas une simple modification CSS.

Supprimer la simulation « hébergement +80 € » : elle n’appartient plus à la direction retenue.

## 9. Responsive, lisibilité et accessibilité

- Les mockups 390 × 844 px sont des références visuelles, pas des tailles fixes de l’app.
- Ne pas utiliser `transform: scale()` sur l’application pour reproduire la planche.
- Le défilement horizontal de la planche ne doit pas devenir un défilement horizontal général de l’app.
- Sur mobile : cartes et navigation adaptées ; feuille de route défilante ; RADAR ne masque aucun bouton.
- Cible de confort retenue : contrôles tactiles de 48 px minimum.
- Texte courant : contraste AA visé 4,5:1 ; grand texte : 3:1 ; information graphique nécessaire aux contrôles/états : 3:1 avec les surfaces adjacentes.
- Le gris de séparation `#D8E0EB` n’identifie pas à lui seul un champ ou un état interactif : utiliser un contour plus contrasté si nécessaire.
- Ne pas supprimer le focus clavier ; ne pas utiliser la couleur seule ; respecter la préférence de réduction des animations.
- Icônes SVG cohérentes, trait 2 px, coins arrondis ; noms accessibles pour les boutons sans texte.
- Respecter la taille de police système et vérifier le zoom. Pas de masquage définitif de contenu par `overflow: hidden`.

Source des seuils : W3C, WCAG 2.2, critères 1.4.3 et 1.4.11.
https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
https://www.w3.org/TR/WCAG21/#non-text-contrast

## 10. Critères d’acceptation — à reporter dans le ticket

- [ ] Le logo original est utilisé ; le Ò et PRO sont préservés.
- [ ] Pas de fond marronnasse, tampon ni simulation d’hébergement.
- [ ] Couleurs, fontes et rayons passent par les tokens du projet.
- [ ] Une première vue se rapproche de la V06 sans collage du CSS de démonstration.
- [ ] La liste et la carte montrent les mêmes dates et statuts.
- [ ] Les données manquantes ne sont pas remplacées par des valeurs fictives.
- [ ] La carte ne prétend pas calculer une route si elle est schématique.
- [ ] La feuille de route est lisible sur mobile et permet d’accéder à tout son contenu.
- [ ] Le budget indique ce qui manque ; 595 € n’est pas présenté comme un revenu net.
- [ ] RADAR est compréhensible sans jargon et chaque action ouvre la bonne information.
- [ ] Aucun exemple fictif n’est publié dans les données réelles.
- [ ] Les règles de permissions existantes sont respectées et les vues équipe ne reçoivent pas les données exclues.
- [ ] Navigation clavier, focus, contrastes, zoom et responsive vérifiés.
- [ ] Captures fournies à environ 390 px et 1440 px ; tests de contenu long et données vides.
- [ ] Les tests réellement exécutés sont listés ; les points non testés sont signalés.

## 11. Prompt prêt à transmettre à un assistant de développement

> Lis d’abord ce brief, la charte graphique et le HTML V06 de référence. Inspecte la structure du dépôt et identifie la stack, les routes, le thème et les composants déjà disponibles. Présente un plan court avant de modifier le code. Intègre la direction graphique dans les composants existants : ne transforme pas le brandboard en application et ne copie pas ses dimensions fixes. Ne modifie ni base de données, ni permissions, ni contrats d’API, ni règles métier sans validation. Signale les fonctions absentes. Commence par les tokens et une tranche verticale dates + feuille de route + RADAR. Conserve les libellés financiers simples et supprime toute simulation d’hébergement. À la fin, fournis les fichiers modifiés, captures, tests exécutés et limites. N’annonce pas une vérification que tu n’as pas exécutée.

## 12. Questions à trancher avec le développeur

1. Quels composants du dépôt portent déjà le thème ?
2. La liste, la feuille de route et la carte existent-elles déjà ?
3. Les règles RADAR sont-elles disponibles ou à développer ?
4. Les montants, échéances et statuts incomplets sont-ils représentés explicitement ?
5. Quel est le périmètre de la première PR, et quelle capture servira à sa validation ?

Aucune comparaison concurrentielle ni évolution réglementaire n’est affirmée par ce brief : ce lot concerne la transmission graphique et l’intégration UI, pas une refonte de paie ou de conformité.
