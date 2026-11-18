# Bòrd Pro — Navette sociale (export mensuel pour la paie)

12/11/2026 · Jeff Bonnier · document de référence : https://claude.ai/artifact/826K745z28emXh8ewizeSR

Bòrd Pro ne fait pas la paie. Chaque mois, il aide l'utilisateur à vérifier son social, puis lui remet deux exports : un PDF « Navette sociale » s'il fait la paie lui-même, et un CSV à transmettre à son prestataire de paie.

**Décisions du 12/11/2026 :** la Navette sociale fait partie de Bòrd Pro, dans l'offre **Collectif** ; le rappel passe par **Radar** (règle RAD-65) ; le PDF est en **A4 paysage**. Maquette de référence : `Bord-Pro_Navette-sociale_simulation_2026-11.pdf` (dans ce dossier).

## 1. Cadrage

La Navette sociale rassemble et vérifie les données déjà saisies dans Bòrd Pro. Elle ne calcule ni bulletin, ni cotisation, ni déclaration.

| Fait | Ne fait pas |
| --- | --- |
| Rappelle (via Radar) de vérifier le social 10 jours avant la fin du mois | Établir des bulletins de paie |
| Liste les engagements du mois, spectacle par spectacle | Calculer les cotisations réelles |
| Signale ce qui manque (brut, n° d'objet, n° de sécurité sociale…) | Déclarer en DSN, AEM ou GUSO |
| Affiche un coût employeur **estimé**, marqué comme tel | Garantir le montant réel des charges |
| Produit un PDF et un CSV | Envoyer quoi que ce soit au prestataire sans action de l'utilisateur |

**Points à trancher avec CLAUDE.md avant de coder :**

- **Paie des intermittents hors MVP.** Décision du 12/11 : la Navette sociale fait partie de Bòrd Pro, dans l'offre Collectif. Reste à l'inscrire au cahier des charges, puisque CLAUDE.md classe la paie des intermittents hors MVP (la Navette, elle, ne fait pas la paie).
- **Calcul de charges interdit (§ 10).** Le « coût employeur estimé » reprend le taux de repère de Paratge (0,45 par défaut, réglable par la structure). Il est toujours écrit « estimation », comme le prévoit la règle proposée pour Paratge. À valider par le porteur du projet.
- **Pas de Celery ni de Redis.** Décision du 12/11 : le rappel passe par Radar, avec une nouvelle règle RAD-65. Pas de mécanisme propre à la Navette.
- **Données sensibles.** N° de sécurité sociale et adresse ne sont visibles que du propriétaire de la structure, comme dans la fiche Équipe aujourd'hui. Les exports sont donc réservés au propriétaire.

## 2. Le parcours du mois

Quatre temps, chaque mois, uniquement si la structure a au moins un engagement salarié dans le mois.

1. **J-10 avant la fin du mois : rappel.** Alerte Radar RAD-65, volet Social : « Navette sociale de [mois] : [n] paies à vérifier avant le [dernier jour], [k] points à compléter ». Comme toute alerte Radar, elle se ferme d'elle-même quand tout est complet.
2. **Entre J-10 et la fin du mois : vérification.** Écran « Vérifier mon social du mois » (section 3). Chaque point manquant renvoie vers la fiche à corriger (date, équipe, spectacle).
3. **Fin du mois : exports.** L'écran propose deux boutons : « Télécharger le PDF » et « Télécharger le CSV pour mon prestataire ». Les exports restent possibles avec des points manquants, mais ces points sont listés en tête du PDF.
4. **Après export : suivi.** L'utilisateur peut cocher « Transmis à mon prestataire » ou « Paie faite ». Les anciens mois restent téléchargeables dans un historique.

Le mois d'un engagement est celui de la date travaillée (représentation, répétition), pas celui du paiement de l'organisateur. Un engagement à cheval sur deux mois est à trancher (section 8).

## 3. Écran « Vérifier mon social du mois »

Une liste par spectacle, une ligne par engagement, avec l'état écrit en toutes lettres (« Complet », « À compléter »). Rien ne bloque l'export : les contrôles signalent seulement.

| Contrôle | Niveau | Lien avec Radar |
| --- | --- | --- |
| Chaque date du mois a au moins un membre d'équipe affecté | À compléter | — |
| Chaque engagement a un brut saisi | À compléter | — |
| Nombre de cachets (artiste) ou d'heures (technicien) renseigné | À compléter | — |
| Fonction ou emploi renseigné | À compléter | — |
| Le spectacle a un n° d'objet | À compléter | — |
| Le membre a un n° de sécurité sociale (ou n° GUSO si l'employeur est au GUSO) | À compléter | RAD-62 |
| Défraiements saisis à part du brut | Information | — |
| Déclaration préalable à l'embauche cochée | Information | RAD-60 |
| Date annulée mais engagement encore présent | À vérifier | RAD-54 |

En haut de l'écran, le même récapitulatif que le PDF (section 4). Chaque ligne « À compléter » ouvre directement le bon formulaire.

## 4. Export 1 : le PDF « Navette sociale »

Pour l'utilisateur qui fait sa paie lui-même : un document de travail, regroupé par spectacle et n° d'objet, qu'il garde à côté de son logiciel de paie ou du GUSO. Il s'adresse à des artistes et des compagnies, pas à des administrateurs.

### Mise en page (référence : la simulation du 12/11, v2)

- **Format** : A4 paysage, charte Bòrd Pro, WeasyPrint comme les autres PDF.
- **Page 1, l'essentiel**, en deux colonnes.
  - À gauche : titre « Navette sociale » + mois ; structure, SIRET, date d'édition ; encadré « À quoi sert ce document ? » qui précise « Ce n'est pas un bulletin de paie » ; quatre cases : paies à faire, personnes à payer, salaires bruts, coût total estimé pour la compagnie (case en pointillé avec « ≈ ») ; une ligne qui explique l'estimation et donne le total des frais remboursés.
  - À droite : encadré « [n] choses à compléter avant de faire la paie », chaque point avec « Où corriger » ; puis trois étapes : 1 · Complète, 2 · Fais la paie, 3 · Ou transmets (CSV).
- **Pages suivantes, le détail spectacle par spectacle.** Une légende sous le titre : « * Heures : 1 cachet = 12 heures pour les artistes (règle France Travail) ; heures réelles pour les techniciens. Coût employeur estimé = salaire brut + 45 % (taux de repère, réglable). Ordre de grandeur, pas un calcul de charges. »
  - Un bandeau nuit par spectacle : type, titre, n° d'objet en police à chasse fixe (ou « ! N° d'objet à compléter »), nombre de dates, de paies et de personnes.
  - Lignes regroupées par date (ligne de date sur fond bleu clair : jour, ville, lieu).
  - **Colonnes** : Qui (nom · fonction, catégorie) · Travail (cachets ou heures) · Heures* · Salaire brut · Coût employeur estimé (brut × 1,45, colonne sur fond bleuté) · Frais remboursés · État (« ✓ Prêt » ou « ! À compléter », jamais la couleur seule).
  - **Ligne de total par spectacle** : heures, brut, coût employeur estimé, frais remboursés.
- **Fin, le récap par personne** : mêmes colonnes (total de cachets ou d'heures + nombre de paies, heures, brut, coût estimé, frais, état) et **ligne « Total du mois »**.
- **Bas du document** : icône Radar + « Radar t'a prévenu le [date] » ; mention offre Collectif ; date et heure des données.
- **Pied de page** : mois et structure · « Confidentiel : données personnelles » · numéro de page.
- **Charte** : filet des quatre volets, pastille S en océan (volet Social), Archivo pour les titres, Instrument Sans pour le texte, IBM Plex Mono pour le n° d'objet ; ambre et vert réservés aux états.

### Règles du PDF

- **Une paie** = un engagement d'un salarié sur une date (ou une période continue de travail). Définition à valider (section 8).
- **Heures** : artiste payé au cachet → 1 cachet = 12 heures ; technicien → heures réelles saisies.
- **Coût employeur estimé** = brut × (1 + taux), taux de repère de Paratge (0,45 par défaut). Le mot « estimé » est toujours visible. Ligne sans brut → « — ».
- **Bloc « À compléter »** sous le récapitulatif, s'il reste des manques.
- **Tri** : un bloc par spectacle, trié par n° d'objet, puis par date puis par nom.
- **N° de sécurité sociale** : absent du PDF par défaut, option « inclure les n° de sécurité sociale » au moment de l'export. Proposition de prudence, à valider.
- **Nom du fichier** : `navette-sociale-AAAA-MM-<structure>.pdf`.

## 5. Export 2 : le CSV pour le prestataire de paie

Une ligne par engagement, sans mise en forme ni total, pour qu'un gestionnaire de paie puisse l'importer ou le lire dans un tableur. Mêmes conventions que les exports CSV déjà livrés (séparateur, encodage, format des dates).

| Colonne | Contenu | Source dans Bòrd Pro | Existe ? |
| --- | --- | --- | --- |
| mois | AAAA-MM | calculé | — |
| siret_employeur | SIRET de la structure | Tenant | oui |
| numero_objet | N° d'objet du spectacle | Show | oui |
| spectacle | Titre | Show | oui |
| code_analytique | Code analytique du spectacle | Show | oui |
| date_debut, date_fin | Premier et dernier jour travaillés | Gig | oui |
| lieu, commune | Lieu et ville de la date | Venue | oui |
| nom, prenom | Salarié | Équipe | oui |
| date_naissance | Salarié | Équipe | à vérifier |
| numero_secu | N° de sécurité sociale | Équipe | à vérifier |
| numero_guso | N° GUSO | Équipe | oui |
| categorie | artiste ou technicien | Équipe | à vérifier |
| fonction | Emploi tenu sur la date | engagement | à vérifier |
| nb_cachets | Artistes | engagement | à vérifier |
| nb_heures | Techniciens | engagement | à vérifier |
| brut | Montant brut, au centime, point décimal | engagement | à vérifier |
| defraiements | Total des frais remboursés, séparé du brut | Expense | oui |
| statut_ligne | complet ou a_completer | calculé | — |
| reference_bordpro | Identifiant de l'engagement, pour les corrections | calculé | — |

« À vérifier » = on ne sait pas si le champ existe dans le code ; c'est la première question pour le développeur. Le coût employeur estimé n'est **pas** dans le CSV : le prestataire calcule les vraies charges. Nom du fichier : `navette-sociale-AAAA-MM-<structure>.csv`.

## 6. Règles techniques

Propositions alignées sur CLAUDE.md ; app et noms de fichiers à confirmer par le développeur.

- **Où** : un service `build_social_month(tenant, year, month)` dans l'app qui porte l'équipe (probablement `accounts` ou `finance`). PDF et CSV lisent ce même service, pour que les deux exports aient toujours les mêmes chiffres.
- **Montants** : `Decimal`, au centime (F-58). Le coût estimé utilise la fonction et le taux de Paratge (`apps/finance/services.py`), jamais un calcul séparé.
- **Isolation** : vues héritant de `TenantScopedMixin`, test d'isolation obligatoire (le tenant B ne télécharge jamais la Navette de A).
- **Accès** : propriétaire de la structure seulement (rôle `owner`), comme les n° GUSO aujourd'hui. Offre Collectif.
- **Journaux** : aucune donnée personnelle dans les logs ni dans Sentry (§ 6.3).
- **Rappel J-10** : règle Radar RAD-65, évaluée par la vérification de nuit `radar_daily` déjà prévue dans la spec Radar. Condition : jour ≥ dernier jour du mois − 10 et au moins un engagement salarié dans le mois. Gravité « à faire », ou « à compléter » s'il reste des manques.
- **Historique** : un mois exporté peut être régénéré si les données changent. Garder la date du dernier export et signaler « modifié depuis le dernier export », plutôt que figer le document. Proposition, à valider.
- **Tests** : mois vide, mois avec manques, engagement annulé, deux spectacles, total PDF = total CSV, conversion cachets → heures.
- **Plan requis** avant de coder : oui (PDF et sans doute nouveaux champs sur l'engagement).

## 7. Réglementaire et concurrence

Le n° d'objet est le bon critère de regroupement : il est obligatoire sur les documents de paie et pénalisé s'il manque.

### Faits sourcés

| Fait | Effet sur la Navette | Source |
| --- | --- | --- |
| Le n° d'objet est attribué par employeur et par spectacle ; il doit figurer sur l'AEM, les bulletins de paie et les contrats de travail | Regroupement par n° d'objet ; contrôle « n° d'objet manquant » | [ARTCENA, lexique](https://www.artcena.fr/guide/lexique/numero-dobjet) |
| Une tournée avec plusieurs contrats de cession n'a besoin que d'un seul n° d'objet, si c'est le même spectacle et le même employeur | Un bloc par spectacle, pas par date | [Service-public](https://sites.service-information-publique.fr/saint-barthelemy-d-anjou/guide-associations/F23992.html) |
| L'absence du n° d'objet sur les AEM est pénalisée de 7,50 € par salarié et par mois, plafonnés à 750 € par mois de retard | Justifie l'alerte en tête du PDF | [ARTCENA, précis juridique](https://www.artcena.fr/precis-juridique/etudes/assurance-chomage/les-obligations-declaratives-prealables-a-louverture-et-au-renouvellement-des-droits) |
| Le n° d'objet compte 12 caractères, dont 2 pour l'année de la demande, 6 pour un numéro d'ordre et 2 pour une clé de contrôle | Confirme l'exemple 223P51344757 (retour SPE-02) ; contrôle de longueur possible | [Circulaire Unédic 2008-03](https://www.unedic.org/ged/documents/circulars/pdf/ci200803.pdf) |
| Depuis le 20 juillet 2026, un compte entreprise certifié est obligatoire pour obtenir un n° d'objet et accéder à l'AEM | Message d'aide si le n° d'objet manque | [France Travail](https://www.francetravail.fr/spectacle/spectacle--employeur-dintermitte/aem-et-intermittents-pectacle.html) |
| D'ici fin mars 2027, les employeurs du secteur déclarent progressivement les contrats des intermittents en DSN | Le CSV sert au prestataire qui fait la DSN ; RAD-64 déjà prévu | [France Travail](https://www.francetravail.fr/spectacle/spectacle--intermittents/intermittents-du-spectacle-ce-qu.html) |
| Lorsque l'activité des artistes est déclarée en cachets, chaque cachet est converti en heures sur la base de 1 cachet = 12 heures | Colonne « Heures » du PDF | [Unédic, annexe 10 (convention du 15/11/2024)](https://www.unedic.org/la-reglementation/conventions-d-assurance-chomage/annexe-10-au-reglement-annexe-a-la-convention-du-15-novembre-2024-2) |

### Concurrence

| Outil | Ce qui a été relevé | Lecture |
| --- | --- | --- |
| Orféo | Production complète du booking à la facturation : devis, feuilles de route, contrats, fiches techniques ; plus de 600 structures ([Appvizer](https://www.appvizer.fr/marketing/evenementiel/orfeo)) | Pas d'export de préparation de paie relevé, à confirmer en démo |
| Bob Booking | CRM du spectacle, avec export vers le logiciel de comptabilité ([GetApp](https://www.getapp.fr/software/2056006/bob-booking)) | Export comptable, pas d'export de paie relevé |
| sPAIEctacle (GHS) | Logiciel de paie dédié au spectacle ; livre de paie avec choix des colonnes à exporter ([GHS](https://www.ghs.fr/wp-content/uploads/2016/01/sPAIEctaclev55.pdf)) | C'est un logiciel de paie, pas un concurrent : un des destinataires possibles du CSV |

Hypothèse, non vérifiée : une Navette sociale prête pour la paie serait un point de différence de Bòrd Pro. Le format CSV idéal dépend du prestataire ; il faudrait le valider avec un ou deux gestionnaires de paie du spectacle.

## 8. Questions ouvertes

- [ ] **Cahier des charges** : ajouter la Navette sociale au périmètre (offre Collectif ; la paie des intermittents y est hors MVP).
- [ ] **Coût employeur estimé** : accepté avec le taux de repère de Paratge et la mention « estimation », ou retiré pour rester strictement dans « jamais calculer de charges » ?
- [ ] **Définition d'une paie** : un engagement par date, ou un bulletin par salarié et par contrat (un contrat pouvant couvrir plusieurs dates) ? À faire confirmer par un gestionnaire de paie.
- [ ] **Mois de rattachement** : engagement à cheval sur deux mois (répétition fin octobre, représentation début novembre).
- [ ] **Champs manquants** : date de naissance, n° de sécurité sociale, catégorie, fonction, cachets ou heures et brut par engagement existent-ils déjà ?
- [x] **Rappel** : tranché le 12/11 : par Radar (RAD-65).
- [ ] **N° de sécurité sociale dans le PDF** : exclus par défaut avec option, ou toujours inclus ?
- [ ] **Format CSV** : le valider avec un prestataire de paie du spectacle avant de le figer.
