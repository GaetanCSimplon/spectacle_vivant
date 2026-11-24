Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

# Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

Nov 12, 2026 · @JEFF 

L'app est déjà riche et cohérente visuellement : la charte est bien appliquée, la fiche date et la feuille de route sont de vraies réussites. Les plus gros chantiers ne sont pas graphiques : ce sont des chiffres qui ne disent pas la même chose d'une page à l'autre, des saisies en double, et une navigation qui disperse les actions d'une date sur trop de pages. 

## Les 5 priorités 

1. **Une seule vérité pour les chiffres.** Trois « soldes » différents pour 2026 selon la page (+250 €, +1 050 €, 250 €), HT et TTC mélangés, et un acompte d'une date 2027 compté dans le facturé 2026. Voir section suivante. 

2. **Une seule saisie pour les salaires.** Le brut est saisi dans Social (200 € pour 1 cachet) et aussi en dépense « Cachets » (500 € + 250 €). La Navette sociale et le Bòrd ne pourront jamais être d'accord tant que les deux existent. 

3. **La checklist doit se cocher toute seule** pour ce que l'app sait déjà (contrat signé, facture émise, paiement reçu, feuille de route partagée). Aujourd'hui elle est vide sur une date entièrement signée et payée. 

4. **La fiche date en onglets.** Une date ouvre aujourd'hui 9 sous-pages différentes (compléter, aperçu, versions, devis et factures, paiements et dépenses, échéances, prix, checklist, feuille de route). Le sous-menu latéral C/B/S/R est une très bonne base : il faut en faire la vraie navigation de la date. 

5. **Ne pas redemander ce qui est déjà saisi.** La page « Compléter le contrat » redemande les horaires (déjà dans la feuille de route) et le SIRET, l'APE et le représentant de l'organisateur (déjà dans sa fiche). 

## Incohérences de chiffres et de données 

Constatées le 12/11 sur les données de test du compte. Ce sont les points à corriger avant d'ouvrir l'app à d'autres utilisateurs. 

Page 1 of 10 

Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

|#|Où|Ce qu'on voit|Pourquoi c'est un<br>problème|Proposition|
|---|---|---|---|---|
|I1|Accueil, Bòrd, fiche<br>date|Accueil : « Solde<br>de l'année 2026 :<br>+250 € »<br>(encaissé −<br>dépensé). Bòrd :<br>« Ce qu'il reste<br>après ces frais :<br>+1 050 € » (prévu<br>− frais). Date du<br>07/11 : « Résultat<br>250 € »|Trois chiffres<br>pour une même<br>question «<br>combien il me<br>reste », avec des<br>mots proches|Deux libellés fixes<br>partout : « Reste<br>prévu » (prévu −<br>frais) et « Reste réel »<br>(encaissé −<br>dépensé), toujours<br>côte à côte|
|I2|Bòrd, carte Budget|Prévu 2026 = 2<br>000 € (dates<br>2026<br>seulement),<br>mais Facturé<br>2026 = 1 270 €,<br>dont l'acompte<br>de 270 € de la<br>date du<br>23/07/2027|Le prévu suit la<br>date de<br>prestation, le<br>facturé suit la<br>date de facture :<br>c'est le bug BRD-<br>02 de la recette,<br>toujours présent|Vue activité<br>rattachée à la date de<br>prestation ; vue<br>trésorerie à part<br>(BRD-04)|
|I3|Bòrd et fiche date|Bòrd affiche<br>Prévu (HT) à<br>côté d'Encaissée<br>(TTC) ;<br>Paiements et<br>dépenses<br>affiche « Prévu<br>(TTC) 1 055 € »<br>pour un prix de 1<br>000 € HT|On compare des<br>montants qui ne<br>sont pas sur la<br>même base|Tout en HT dans les<br>synthèses ; TTC<br>uniquement sur les<br>factures et les<br>paiements, toujours<br>écrit|



Page 2 of 10 

Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

|#|Où|Ce qu'on voit|Pourquoi c'est un<br>problème|Proposition|
|---|---|---|---|---|
|I4|Social et dépenses<br>de la date du 07/11|Social : Jeff<br>Bonnier, 1<br>cachet, 200 €<br>brut. Dépenses :<br>« Salaire Brut<br>Jeff 500 € » et «<br>Cotisation 250 €<br>» en catégorie<br>Cachets|Même salaire<br>saisi deux fois,<br>avec des<br>montants<br>différents|Le brut saisi dans<br>Social crée la<br>dépense « Cachets »<br>automatiquement<br>(plus de saisie à la<br>main dans cette<br>catégorie)|
|I5|Mes dates|« 2 dates en<br>2026 », alors que<br>la liste en affiche<br>3 (dont une en<br>2027)|Le compteur ne<br>correspond pas à<br>ce qu'on voit|Compteur = nombre<br>de cartes affichées<br>avec les filtres actifs|
|I6|Fiche date, volet<br>Social|« Social 1/1 –<br>Équipe ajoutée –<br>fait » dès qu'une<br>personne est<br>ajoutée|Le volet paraît<br>terminé alors que<br>l'adresse ou la<br>date de<br>naissance<br>manquent<br>(signalé dans<br>Bòrd › Social)|Deux étapes : «<br>Équipe ajoutée » et «<br>Infos de paie<br>complètes »|
|I7|Checklist<br>contractualisation|Date du 07/11<br>signée, facturée<br>et payée, mais<br>checklist vide («<br>Aucune<br>modification »)|Double saisie, et<br>la checklist<br>contredit<br>l'avancement<br>C/B/S/R|Cocher<br>automatiquement ce<br>que l'app sait ; ne<br>laisser à la main que<br>DPAE, rider envoyé,<br>etc.|
|I8|Contacts ›<br>Organisateurs|« Le Sonambule »<br>sans statut de<br>suivi alors qu'il a<br>2 dates signées|Le suivi<br>commercial<br>décroche des<br>dates réelles|Passer<br>automatiquement à «<br>Client actif » à la<br>première date signée<br>(modifiable)|



Page 3 of 10 

Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

## Où en est la recette n°1 

À la date du 12/11, 4 retours sont faits, 13 sont en partie faits et la plupart des autres restent à faire. Plusieurs points sont mieux couverts que prévu : régime de TVA, historique des actions de la date, formulaire de régie envoyé à l'organisateur, page Social. Les ID renvoient au document de recette. 

|ID|État|Ce que montre l'app|
|---|---|---|
|STR-09 Régime TVA|Fait|Assujetti / Franchise en base / Non<br>assujetti + taux, dans Informations de la<br>structure|
|DAT-04 Étapes de la date|Fait|« Dernières actions » datées +<br>avancement C/B/S/R + « Prochaine<br>action »|
|SPE-01 Ajouter une personne|Fait|« Ajouter un autre membre à l'équipe »<br>dans la fiche spectacle|
|SPE-02 N° d'objet|Fait|Champ présent sur le spectacle<br>(contrôle du format non vérifié)|
|NAV-01 Icônes du menu|En partie|Une icône, mais la même (le « b ») pour<br>toutes les entrées : elle ne distingue rien|
|NAV-02 Accès à la structure|En partie|Lien « Informations de la structure » en<br>haut à droite, uniquement dans Bòrd|
|NAV-03 Navigation|En partie|Sous-menu de la date dans la barre<br>latérale (Contrats, Budget, Social, Régie)<br>; « Retour » partout, même sur les pages<br>de premier niveau|
|ORG-04/05 Formulaires<br>organisateur|En partie|Formulaire d'infos légales + « demande<br>de régie » (horaires, accueil, repas,<br>hébergement) : les 2 formulaires<br>existent|
|ORG-08 EPK, fiche<br>technique, rider|En partie|Champs présents sur le spectacle ;<br>paragraphe automatique dans les mails<br>non vu|
|DAT-01 Nom de l'événement|En partie|Champ dans « Compléter le contrat »,<br>pas à la création de la date ni sur les<br>cartes|



Page 4 of 10 

Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

|ID|État|Ce que montre l'app|
|---|---|---|
|DAT-05 Documents de la date|En partie|Page Documents globale très claire ; sur<br>la date, documents répartis dans<br>plusieurs sous-pages|
|DAT-06 Mini-vue chiffrée|En partie|Prix et échéances sur chaque carte ; pas<br>de total en tête de liste|
|DAT-07 Rappels|En partie|« Alertes et rappels » sur l'accueil, « À<br>traiter maintenant » dans Bòrd|
|CTR-04 Retour après devis|En partie|Sous-menu de la date toujours visible|
|CTR-06 Page Compléter le<br>contrat|En partie|Sections La date / Le spectacle / Le lieu /<br>L'organisateur / Signature ; horaires de<br>régie encore mélés au contrat|
|FDR-03 Pièces jointes|En partie|« Documents pour l'équipe » au niveau<br>de la date (pas par créneau)|
|SOC-01/02 Navette sociale|En partie|Bòrd › Social existe : tableau du mois par<br>personne, n° d'objet, cachets, brut, « à<br>compléter », export CSV. Manquent<br>heures, frais, coût estimé, totaux, PDF,<br>alerte Radar|
|NAV-04 Années à venir|Pas fait|Accueil : Semaine / Mois / Année|
|STR-01, 03 à 07|Pas fait|Forme juridique, APE, représentant en<br>texte libre ; SIRET sans espaces (fiche et<br>facture) ; pas de logo|
|ORG-01, ORG-02|Pas fait|Pas de remplissage par SIRET ; ville et<br>département saisis à la main (liste de 101<br>départements)|
|DAT-02, SPE-03|Pas fait|Titre des cartes = spectacle ; pas de<br>couleur par spectacle|
|DAT-08 Onglet Contacts|Pas fait|Contacts visibles seulement sur la fiche<br>organisateur|
|CTR-05 Échéances en liste|Pas fait|Champs date libres, dans deux pages<br>(Compléter le contrat et Échéances)|
|CTR-07 Repas / hébergement|Pas fait|Champs texte « pris en charge »|
|CTR-08 Envoi du contrat|Pas fait|Page Versions : téléchargement et dépôt<br>du PDF signé, pas d'envoi|



Page 5 of 10 

Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

|ID|État|Ce que montre l'app|
|---|---|---|
|CTR-10 Facture complète|Pas fait|Pas de référence au devis, à l'acompte ni<br>au solde restant|
|BRD-01 « Prévisionnel »|Pas fait|Toujours « Prévue (HT) »|
|BRD-02/03/04|Pas fait|Voir incohérences I1 à I3|
|FDR-01 Cohérence des<br>horaires|Pas fait (après<br>MVP)|Sur la date du 23/07 : repas à 12:00 et<br>départ à 12:00, arrivée à 14:42, aucune<br>alerte|
|FDR-02 Plusieurs jours|Pas fait|Créneaux sans date : le retour est saisi «<br>23:59 » pour contourner|
|FDR-04 Repas dans le<br>programme|Pas fait|Repas et hébergement dans leurs blocs,<br>absents du programme de la journée|



## Charte graphique 

La charte v1.3 est bien appliquée. Les écarts sont peu nombreux et faciles à corriger. 

#### **Conforme** 

- Polices : Archivo pour les titres (800), Instrument Sans pour le texte, police à chasse fixe pour les montants et numéros. 

- Couleurs : texte et menu en nuit #10243F ; volets C nuit, B corail, S océan, R bleu clair avec contour, toujours avec leur lettre ou leur nom. 

- États : badges avec icône et mot (« ✓ Confirmée », « Signée », « Payée », « À traiter »). Actions destructives en bordeaux #8E1F3F (Supprimer), distinctes du corail. 

#### **Écarts** 

|Constat|Règle|Correction proposée|
|---|---|---|
|Fiche date : bouton «|Corail réservé à l'action|Bouton flottant en contour|
|Générer le contrat » corail +|principale, une seule par|nuit, ou checklist intégrée au|
|bouton rond flottant corail|écran|volet C|
|(checklist) en bas à droite|||
|Avancement : C, B et R en|Un volet = sa lettre ou son|Lettre S partout dans|
|lettres, mais S affiché avec la|nom|l'avancement ; tuiles « b »|
|tuile « b »||réservées au sous-menu|



Page 6 of 10 

Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

|Constat|Règle|Correction proposée|
|---|---|---|
|Menu principal : même icône<br>« b » devant chaque entrée|Icône utile seulement si elle<br>distingue|Une icône par entrée<br>(maison, tableau, calendrier,<br>document, spectacle,<br>carnet), trait fin nuit|
|Calendrier : statut indiqué<br>par un simple point de<br>couleur (vert pour|Jamais la couleur seule|Pastille avec lettre ou icône,<br>et titre de la date dans la<br>case|
|Confirmée comme pour<br>Signée)|||
|Accueil : carte « Solde de<br>l'année » en aplat corail à<br>côté du bouton corail «<br>Nouvelle date »|Corail = action principale ou<br>volet Budget|Acceptable (volet B), mais<br>étiqueter la carte « B · Budget<br>» comme dans Bòrd|



## Propositions de navigation et d'ergonomie 

Idée directrice : chaque objet (une date, un organisateur, ma structure) a **une page à onglets** , et chaque information ne se saisit **qu'à un seul endroit** . Ce sont des propositions, à arbitrer avec le développeur selon le cahier des charges. 

### Menu proposé 

- **Accueil** : alertes Radar, prochaines dates, chiffres clés 

- **Mes dates** : liste et calendrier 

- **Bòrd** : tableau de bord, Social (Navette sociale) 

- **Contacts** : Organisateurs, Lieux, Personnes. Correction de Jeff (12/11) : l'équipe ne va pas ici mais dans le menu « Ma structure » (Mon entreprise, Mon équipe, Mes contrats, Mes devis, Mes factures, Paratge). Ancienne proposition : **Équipe** (déplacée depuis Bòrd) 

- **Spectacles** 

#### **Documents** 

- En bas du menu : **Ma structure** (sous le nom de l'utilisateur), puis Se déconnecter 

### Fiche date en onglets 

Onglets en haut de la fiche, reliés au sous-menu latéral déjà en place : **Vue d'ensemble** (avancement, prochaine action, historique) · **C · Contrat** (compléter, aperçu, versions, envoi) · **B · Budget** (prix, échéances, devis et factures, paiements et dépenses) · **S · Social** 

Page 7 of 10 

Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

(équipe, cachets, brut) · **R · Régie** (feuille de route) · **Contacts** (DAT-08) · **Documents** (DAT-05). La checklist disparaît en tant que page : ses points manuels rejoignent le volet concerné. 

### Propositions priorisées 

|ID|Prio|Où|Proposition|
|---|---|---|---|
|UX-01|P1|Partout|Libellés financiers fixes et partagés : Prévu,<br>Facturé, Encaissé, Reste prévu, Reste réel, toujours<br>avec HT ou TTC (incohérences I1 à I3)|
|UX-02|P1|Social, dépenses|Précision de Jeff (12/11) : le brut de la fiche Équipe<br>est un cachet habituel (une moyenne). Il se reporte<br>par défaut sur chaque date, où il reste modifiable.<br>Le brut de la date doit ensuite alimenter<br>automatiquement l'état financier de la date (ligne «<br>Cachets », avec coût employeur estimé) : ce n'est<br>pas encore le cas. Plus de saisie de salaire à la main<br>dans les dépenses (I4)|
|UX-03|P1|Checklist|Cases cochées automatiquement d'après les<br>données ; intégrer les cases manuelles dans les<br>volets (I7)|
|UX-04|P1|Fiche date|Fiche en onglets (voir ci-dessus), au lieu des 9<br>sous-pages et des 5 boutons empilés|
|UX-05|P1|Compléter le contrat|Ne plus redemander les horaires (lus dans la feuille<br>de route) ni le SIRET, l'APE et le représentant (lus<br>dans la fiche organisateur) ; afficher ces valeurs en<br>lecture avec un lien « modifier »|
|UX-06|P1|Compléter le contrat|Enregistrer automatiquement avant « Envoyer un<br>formulaire à l'organisateur » ; aujourd'hui un<br>message prévient que les modifications seront<br>perdues|
|UX-07|P2|Menu|Icônes distinctes ; Équipe dans Contacts ; Ma<br>structure sous le nom de l'utilisateur (NAV-01,<br>NAV-02)|
|UX-08|P2|Menu|L'entrée « Contacts » ouvre une page titrée «<br>Organisateurs » : titrer la page « Contacts » avec ses<br>onglets|



Page 8 of 10 

Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

|ID|Prio|Où|Proposition|
|---|---|---|---|
|UX-09|P2|Toutes les pages|Supprimer « Retour » sur les pages de premier<br>niveau ; ailleurs, fil d'Ariane cliquable (Mes dates › A<br>TROI 30/11 › Contrat). Aujourd'hui « Retour » depuis<br>Bòrd mène à Mes dates|
|UX-10|P2|Calendrier|Titre de l'événement ou du spectacle dans la case ;<br>statut par lettre ou icône ; clic sur un jour vide pour<br>créer une date à ce jour|
|UX-11|P2|Cartes de dates|Nom de l'événement en titre, spectacle et ville en<br>sous-titre, couleur du spectacle (DAT-01, DAT-02,<br>SPE-03)|
|UX-12|P2|Feuille de route|Mettre le programme de la journée en premier ;<br>partage, notes et documents ensuite (ou onglets<br>Programme / Logistique / Équipe / Partage).<br>L'aperçu « Ce que voit l'artiste » à droite est à<br>garder|
|UX-13|P2|Organisateurs|Replier les 7 filtres derrière un bouton « Filtres » ;<br>statut « Client actif » automatique (I8)|
|UX-14|P2|Fiche date, Social|Étape « Infos de paie complètes » dans le volet S<br>(I6)|
|UX-15|P3|Bòrd|Retirer « Annuler la date » du tableau des<br>opérations : une action aussi lourde n'a pas sa place<br>dans un tableau de chiffres ; la garder sur la fiche<br>date avec confirmation|
|UX-16|P3|Formulaires d'adresse|Code postal → ville et département remplis<br>automatiquement (ORG-02), au lieu de la liste de<br>101 départements|
|UX-17|P3|Nouvelle date|Étape 1 : spectacles en cartes (titre, couleur, durée)<br>plutôt qu'une liste déroulante|
|UX-18|P3|Fiches et factures|SIRET espacé (111 222 333 00012), APE écrit 90.01Z<br>(STR-03)|
|UX-19|P3|Mes dates|Compteur cohérent avec les filtres (I5)|



**Points forts à garder** : la « Prochaine action » sur la fiche date, l'historique daté, l'aperçu « Ce que voit l'artiste » de la feuille de route, la page Documents (filtres, numéros, statuts), la page Social qui préfigure la Navette sociale, et l'assistant de création de date en 5 étapes. 

Page 9 of 10 

Bòrd Pro — Audit UX/UI de l'app (12/11/2026) 

## Méthode, limites et questions 

**Méthode.** Parcours de app.bordpro.fr le 12/11/2026 avec le compte de Jeff, en lecture seule (rien n'a été enregistré ni envoyé), en largeur ordinateur 1 440 px. Pages vues : Accueil, Bòrd (tableau de bord, Équipe, Social, Informations de la structure), Mes dates (liste, calendrier), deux fiches date, Compléter le contrat, Versions du contrat, Échéances, Devis et factures, une facture, Paiements et dépenses, Checklist, Feuille de route, Documents, Spectacles et fiche spectacle, Organisateurs et fiche organisateur, étape 1 de « Nouvelle date ». Couleurs et polices vérifiées dans le code de la page, comparées aux tokens de la charte v1.3. 

#### **Limites.** 

- Étapes 2 à 5 de « Nouvelle date » non ouvertes, pour ne pas créer de date de test. PDF (contrat, facture, feuille de route) non ouverts : la mention TVA sur la facture PDF reste à vérifier. 

- Pages publiques (feuille de route partagée, formulaires organisateur) et affichage téléphone non testés. 

- App en cours de développement : certains écarts sont peut-être déjà en cours de correction sur la branche de travail. 

#### **Questions pour le développeur.** 

- La dépense « Cachets » est-elle censée venir du volet Social, ou les deux saisies sontelles voulues (brut d'un côté, coût total de l'autre) ? 

- Quelle règle de rattachement est appliquée aujourd'hui dans Bòrd : date de prestation ou date de facture ? 

- La checklist vient de la spécification de l'associé : peut-on la cocher automatiquement sans la contredire ? 

- Le passage de la fiche date en onglets est-il compatible avec les fragments HTMX actuels (un fragment par onglet) ? 

Page 10 of 10 

