# Recette sur la production — grille à dérouler

**Pour qui :** le développeur, avec son associé. **But :** vérifier sur `https://app.bordpro.fr` les neuf critères du MVP (`cahier-des-charges.md` §11), plus ce qui n'est testable qu'en production (e-mails, fichiers, domaine). **Règle : on ne triche pas** : on fait chaque étape comme un utilisateur qui n'a jamais vu l'application, sans aide, et on note la durée et chaque hésitation.

**Avant de commencer**
- Utiliser **deux comptes** : le vôtre (compte A) et celui de votre associé (compte B). Ils servent aussi au test d'isolation (§9).
- Ne saisir que des **données fictives** (organisateur « Test Recette », montants ronds). La recette crée de vraies lignes en base : les nommer « Recette » pour les retrouver et les supprimer ensuite.
- Faire une **sauvegarde manuelle** Scalingo juste avant.
- Noter pour chaque ligne : ✅ ok, ❌ défaut (avec l'écran et ce qui s'est passé), ⚠️ gêne sans blocage.

---

## 1. Compte et structure en moins de 10 minutes
Compte B (nouvelle personne) : *prendre un chronomètre.*
| # | Étape | Attendu | Résultat |
|---|---|---|---|
| 1.1 | Page de connexion → « J'ai reçu une invitation : créer un compte », adresse invitée | l'inscription est acceptée | |
| 1.2 | Une adresse **non invitée** | refusée, avec un message clair | |
| 1.3 | E-mail de confirmation | arrive (noter le dossier : réception ou spam), lien en `https://app.bordpro.fr/…` | |
| 1.4 | Connexion, onboarding de la structure | structure créée, accès à l'Accueil | |
| 1.5 | Durée totale | moins de 10 minutes, sans aide | |
| 1.6 | « Mot de passe oublié » | e-mail reçu, nouveau mot de passe accepté | |

## 2. Organisateur, lieu, spectacle
| # | Étape | Attendu | Résultat |
|---|---|---|---|
| 2.1 | Créer un organisateur (« Test Recette ») | apparaît dans l'annuaire | |
| 2.2 | Créer un lieu avec adresse | enregistré ; position trouvée si l'adresse est connue | |
| 2.3 | Créer un spectacle | apparaît dans la liste | |
| 2.4 | Rattacher un contact | visible sur l'organisateur et dans l'annuaire | |

## 3. Une date, d'« option » à « signée »
| # | Étape | Attendu | Résultat |
|---|---|---|---|
| 3.1 | « Nouvelle date » avec spectacle, organisateur, lieu, prix | date créée en `option` | |
| 3.2 | La faire avancer : option → confirmée → … → signée | chaque changement de statut est accepté, les interdits sont refusés | |
| 3.3 | Calendrier et export iCal | la date apparaît, le fichier ne contient aucun montant | |

## 4. Contrat PDF
| # | Étape | Attendu | Résultat |
|---|---|---|---|
| 4.1 | Générer le contrat (essayer les 4 modèles en brouillon) | PDF correct : bonnes parties, prix, dates, informations de la structure | |
| 4.2 | Télécharger | le fichier s'ouvre | |
| 4.3 | Marquer « signé » | PDF figé, visible dans l'onglet **Documents** | |
| 4.4 | Fichier dans le bucket Scaleway | un objet de plus ; adresse directe refusée (`AccessDenied`) | |
| 4.5 | Après `scalingo --app bordpro restart` | le PDF s'ouvre encore | |
| 4.6 | **Relecture humaine du PDF** | pas de faute, pas de mention étrange (la relecture professionnelle reste à faire) | |

## 5. Factures d'acompte et de solde
| # | Étape | Attendu | Résultat |
|---|---|---|---|
| 5.1 | Émettre un acompte (ex. 30 %) | facture n° 1 de l'année, montants au centime | |
| 5.2 | Émettre le solde | facture n° 2, sans trou de numérotation | |
| 5.3 | Tenter de modifier une facture émise | impossible : la correction passe par un avoir | |
| 5.4 | Avoir | numérotation propre, facture d'origine inchangée | |
| 5.5 | PDF de la facture | IBAN et BIC affichés, infos légales de la structure | |

## 6. Paiement
| # | Étape | Attendu | Résultat |
|---|---|---|---|
| 6.1 | Enregistrer le paiement de l'acompte | la facture passe à `payée` | |
| 6.2 | Paiement partiel | état « partiellement payée », reste dû exact | |
| 6.3 | Recette prévue / facturée / encaissée | trois montants séparés, jamais fusionnés | |

## 7. Feuille de route
| # | Étape | Attendu | Résultat |
|---|---|---|---|
| 7.1 | Créer la feuille de route (horaires, contacts, hébergement, repas) | enregistrée, aperçu à droite | |
| 7.2 | Partager par lien | lien secret en `https://app.bordpro.fr/…` | |
| 7.3 | **Ouvrir le lien sur un téléphone**, sans être connecté | lisible à 375 px, pas de donnée financière | |
| 7.4 | Raccourci et interrupteur « partagée / non partagée » dans « Mes dates » | l'état est juste | |
| 7.5 | Révoquer le lien | l'ancien lien ne marche plus | |
| 7.6 | Espace équipe (lien personnel d'un membre) | s'ouvre sans connexion, ne montre que ce qui est prévu ; déclarer une dépense avec photo depuis un téléphone | |

## 8. Dépense, bilan, export
| # | Étape | Attendu | Résultat |
|---|---|---|---|
| 8.1 | Saisir une dépense sur la date | enregistrée | |
| 8.2 | Bilan de la date | encaissé − dépenses cohérent avec les saisies | |
| 8.3 | Export CSV | le fichier s'ouvre dans un tableur, colonnes lisibles (accents, montants), code analytique présent | |
| 8.4 | Accueil et tableau de bord | chiffres cohérents avec ce qui a été saisi | |

## 9. Isolation entre structures (le point le plus important)
Avec les deux comptes, après avoir créé les données « Recette » dans le compte A :
| # | Étape | Attendu | Résultat |
|---|---|---|---|
| 9.1 | Compte B : Mes dates, Contacts, Documents, Dépenses, bilan | **aucune** donnée du compte A | |
| 9.2 | Compte B : coller l'adresse (URL) d'une date, d'une facture, d'un PDF du compte A | **404**, jamais la page | |
| 9.3 | Compte B : exports CSV et iCal | ne contiennent rien du compte A | |
| 9.4 | Lien de feuille de route du compte A | ne donne que cette feuille, rien d'autre | |
| 9.5 | Tests automatiques (CI) | verts sur le commit livré | |

## 10. Transversal
| # | Étape | Attendu | Résultat |
|---|---|---|---|
| 10.1 | Déconnexion, retour arrière du navigateur | aucune page privée n'est affichée sans connexion | |
| 10.2 | Pages légales, contact | s'affichent ; le formulaire de contact envoie (e-mail reçu à `contact@bordpro.fr`) | |
| 10.3 | Sentry | une erreur provoquée volontairement (ou le message de test) apparaît, sans donnée personnelle | |
| 10.4 | Export puis suppression d'un compte de test | l'export contient ses données ; la suppression est demandée et annulable pendant 30 jours | |
| 10.5 | Temps de chargement des pages principales | raisonnable (moins de 2 s) | |

## À la fin
1. Supprimer les données « Recette » (ou garder le compte de test pour la suite).
2. Lister les ❌ et ⚠️ : chaque défaut devient une PR séparée.
3. Cocher les neuf cases de `cahier-des-charges.md` §11 seulement quand tout est ✅ **et** que la relecture professionnelle (4.6, 5.5) est faite. Mettre à jour `etat-du-projet.md`.
4. Ensuite : trois testeurs externes, sans aide (`etat-du-projet.md` §4).
