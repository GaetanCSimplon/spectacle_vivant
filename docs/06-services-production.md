# Services nécessaires à la mise en production

> Liste des comptes et services à prévoir avant de mettre l'application en ligne.
> Rien de tout cela n'est nécessaire en développement (tout tourne en local).
> Les prix sont des **ordres de grandeur à vérifier** sur les sites des prestataires au moment de s'inscrire.
> Règle du projet (CLAUDE.md §2, §6.3) : hébergement en **France / UE**, aucun secret dans Git.

## Vue d'ensemble

| # | Service | Rôle en une phrase | Quand | Obligatoire |
|---|---|---|---|---|
| 1 | Hébergement applicatif (Scalingo) | Fait tourner l'application | Phase 3.8 / déploiement | Oui |
| 2 | Base de données PostgreSQL | Stocke toutes les données | Avec l'hébergement | Oui |
| 3 | Stockage de fichiers (bucket S3 privé, UE) | Garde les PDF (contrats, fiches techniques) | Sprint 3.4 en prod | Oui |
| 4 | Envoi d'e-mails | Confirmation d'adresse, mot de passe oublié | Avant l'ouverture au public | Oui |
| 5 | Nom de domaine | Adresse du site (ex. `monapp.fr`) | Avant l'ouverture au public | Oui |
| 6 | Suivi des erreurs (Sentry, UE) | Te prévient quand l'app plante | Au déploiement | Recommandé |
| 7 | Sauvegardes | Récupérer les données en cas de problème | Au déploiement | Oui |
| 8 | Supervision de disponibilité | Alerte si le site ne répond plus | Après le déploiement | Recommandé |
| 9 | Dépôt GitHub + CI | Code et tests automatiques | Déjà en place | Fait |
| 10 | Relecture professionnelle | Contrat et facture validés | Avant la phase 4 | Oui (juridique) |
| 11 | Signature électronique | Faire signer les contrats en ligne | v1 (Phase 5) | Plus tard |
| 12 | Plateforme de facturation électronique | Obligation légale | Phase 5, avant 09/2027 | Plus tard |
| 13 | Paiement des abonnements | Encaisser les abonnés | Phase 4-5 | Plus tard |

---

## 1. Hébergement applicatif — Scalingo

- **À quoi ça sert** : Scalingo exécute le code Django (gunicorn). Hébergeur français, déploiement depuis GitHub.
- **À faire** : créer un compte, une application (région France), lier le dépôt GitHub.
- **Variables d'environnement à renseigner** (jamais dans Git) :
  `DJANGO_SETTINGS_MODULE=config.settings.prod`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` (fournie par l'addon), puis celles des services ci-dessous.
- **Fichier à prévoir côté code** : un `Procfile` (commande de démarrage et migrations). Je le crée au moment du déploiement.
- **Coût indicatif** : environ 10 à 25 €/mois pour un petit conteneur.

## 2. Base de données PostgreSQL

- **À quoi ça sert** : toutes les données de l'application.
- **À faire** : ajouter l'addon PostgreSQL de Scalingo (version 16 ou plus). Il fournit `DATABASE_URL`.
- **Coût indicatif** : de quelques euros à environ 30 €/mois selon la taille et les sauvegardes incluses.

## 3. Stockage de fichiers — bucket S3 privé, européen

- **À quoi ça sert** : Scalingo n'a pas de disque permanent. Les PDF y seraient perdus à chaque redémarrage.
- **Prestataires possibles** : Scaleway Object Storage (France) ou OVHcloud Object Storage (France).
- **À faire** :
  1. créer un compte et un bucket **privé** (accès public désactivé), région Paris ou UE ;
  2. créer une clé d'accès limitée à ce bucket ;
  3. renseigner dans Scalingo : nom du bucket, région, URL du service (endpoint), clé d'accès, clé secrète.
- **Coût indicatif** : quelques centimes à quelques euros par mois pour ce volume.
- **Côté code** : `django-storages` est déjà dans les dépendances. Je code le branchement au Sprint 3.4 (local en dev, S3 en prod).

## 4. Envoi d'e-mails

- **À quoi ça sert** : e-mail de confirmation d'adresse (obligatoire dans la config actuelle), mot de passe oublié, plus tard invitations de membres.
- **Pourquoi un prestataire** : un serveur qui envoie des mails directement finit en spam.
- **Prestataires possibles hébergés en UE** : Brevo (France, offre gratuite limitée), Scaleway Transactional Email, Mailjet. À choisir : voir « Décisions à prendre » de la feuille de route.
- **À faire** : créer le compte, **vérifier le domaine d'envoi** (enregistrements DNS SPF et DKIM, voir §5), récupérer l'accès SMTP ou la clé API.
- **Coût indicatif** : gratuit à quelques euros par mois au départ.

## 5. Nom de domaine

- **À quoi ça sert** : une adresse propre au lieu de celle fournie par Scalingo. Nécessaire aussi pour que les e-mails ne soient pas classés en spam.
- **À faire** : acheter un domaine chez un registrar (OVH, Gandi…), pointer le DNS vers Scalingo, activer HTTPS (certificat automatique chez Scalingo).
- **Coût indicatif** : 8 à 15 €/an.

## 6. Suivi des erreurs — Sentry (UE)

- **À quoi ça sert** : être prévenu avec le détail technique quand une page plante chez un utilisateur.
- **À faire** : créer un compte Sentry avec **hébergement des données dans l'UE**, créer un projet Django, renseigner `SENTRY_DSN`.
- **Règle** : aucune donnée personnelle dans les rapports (CLAUDE.md §6.3), réglage à vérifier au branchement.
- **Coût indicatif** : offre gratuite suffisante au départ.

## 7. Sauvegardes

- **À quoi ça sert** : retrouver les données après une erreur ou une panne. Ce n'est pas la même chose que la base de données elle-même.
- **À faire** : vérifier que l'offre PostgreSQL choisie inclut des sauvegardes quotidiennes et une durée de conservation ; **tester une restauration au moins une fois** avant d'avoir de vrais utilisateurs. Prévoir aussi la sauvegarde du bucket (versionnage ou copie).
- **Lié à** : politique de conservation des données (Sprint 3.8, RGPD).

## 8. Supervision de disponibilité

- **À quoi ça sert** : être alerté par e-mail si le site ne répond plus.
- **Exemples** : UptimeRobot, Better Stack (offres gratuites).
- **À faire** : créer un contrôle sur la page d'accueil, toutes les 5 minutes.

## 9. GitHub et intégration continue

- **Déjà en place** : dépôt, CI (tests et ruff), tickets et projet.
- **À prévoir** : décider si le déploiement Scalingo part automatiquement après fusion dans `main`.

## 10. Relecture professionnelle

- **À quoi ça sert** : faire valider par un juriste ou un expert-comptable (ou une CAE) le contrat, la facture et les mentions de TVA avant d'accueillir de vrais clients.
- **Suivi** : Phase 0 et Sprint 3.5 de la feuille de route ; voir aussi Q13 (cahier des charges §14).

## 11 à 13. Plus tard (v1 et Phase 4-5)

- **Signature électronique** : prestataire à choisir (Yousign, Universign…). À décider en v1.
- **Plateforme agréée de facturation électronique** : obligation à anticiper avant 09/2027.
- **Paiement des abonnements** : Stripe ou équivalent, après décision sur le modèle économique (Q9) et sur le statut juridique de ton activité.
- **Pages légales** (mentions légales, CGU, politique de confidentialité, RGPD) : à rédiger avant l'ouverture au public ; relecture professionnelle conseillée.

---

## Checklist de démarrage (ordre conseillé)

- [ ] Nom de domaine acheté
- [ ] Compte Scalingo + application + addon PostgreSQL
- [ ] Compte du bucket S3 (privé, UE) + 4 valeurs récupérées
- [ ] Prestataire d'e-mails choisi, domaine vérifié (SPF, DKIM)
- [ ] Compte Sentry (UE) + `SENTRY_DSN`
- [ ] Variables d'environnement saisies dans Scalingo
- [ ] Restauration d'une sauvegarde testée
- [ ] Contrôle de disponibilité créé
- [ ] `python manage.py check --deploy` propre

## Variables d'environnement prévues en production

| Variable | Origine |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
| `DJANGO_SECRET_KEY` | générée par toi, longue et aléatoire |
| `DJANGO_ALLOWED_HOSTS` | ton domaine |
| `DATABASE_URL` | addon PostgreSQL Scalingo |
| variables du bucket (nom, région, endpoint, clé d'accès, clé secrète) | prestataire S3, noms définis au Sprint 3.4 |
| variables d'e-mail (SMTP ou clé API) | prestataire d'e-mails, noms définis à la mise en place |
| `SENTRY_DSN` | Sentry |

*Cette liste évoluera avec les sprints. Les noms exacts des variables seront ajoutés ici quand le code les utilisera.*
