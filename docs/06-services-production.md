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
| 11 | Signature électronique | Faire signer les contrats en ligne | À la charge de l'utilisateur (guide dans l'application) | Aucun compte à créer |
| 12 | Plateforme de facturation électronique | Obligation légale | Phase 5, avant 09/2027 | Plus tard |
| 13 | Paiement des abonnements | Encaisser les abonnés | Phase 4-5 | Plus tard |

---

## 1. Hébergement applicatif — Scalingo

- **À quoi ça sert** : Scalingo exécute le code Django (gunicorn). Hébergeur français, déploiement depuis GitHub.
- **À faire** : créer un compte, une application (région France), lier le dépôt GitHub.
- **Variables d'environnement à renseigner** (jamais dans Git) :
  `DJANGO_SETTINGS_MODULE=config.settings.prod`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` (fournie par l'addon), puis celles des services ci-dessous.
- **Fichiers de déploiement (faits, 2026-10-12)** : `Procfile` (gunicorn sans journal d'accès, migrations après chaque déploiement), `.python-version` (3.12), `requirements.txt` (renvoie vers `requirements/prod.txt`), `.buildpacks` et `Aptfile` (bibliothèques système de WeasyPrint et polices pour les PDF), `bin/post_compile` (compile Tailwind puis `collectstatic`, car le CSS compilé n'est pas dans Git), `bin/post_deploy.sh` (migrations puis `set_site_domain`), `cron.json` (purge quotidienne à 3 h UTC). Non testés sur Scalingo tant que l'application n'y est pas déployée.
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
- **Côté code** : `django-storages` est déjà dans les dépendances. Le branchement est fait (Sprint 3.4) : disque local en dev, S3 privé en prod.

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
- **Règle** : aucune donnée personnelle dans les rapports (CLAUDE.md §6.3). Déjà réglé dans `config/settings/prod.py` : Sentry n'est actif que si `SENTRY_DSN` est défini ; e-mail, IP et variables locales ne sont pas envoyés ; le jeton du lien de feuille de route est masqué (`apps/core/sentry.py`).
- **Journaux du serveur** : ne pas activer le journal d'accès de gunicorn (`--access-logfile`), car il contiendrait le jeton des feuilles de route.
- **Coût indicatif** : offre gratuite suffisante au départ.

## 7. Sauvegardes

- **À quoi ça sert** : retrouver les données après une erreur ou une panne. Ce n'est pas la même chose que la base de données elle-même.
- **À faire** : vérifier que l'offre PostgreSQL choisie inclut des sauvegardes quotidiennes et une durée de conservation ; **tester une restauration au moins une fois** avant d'avoir de vrais utilisateurs. Prévoir aussi la sauvegarde du bucket (versionnage ou copie).
- **Lié à** : politique de conservation des données (Sprint 3.8, RGPD).

## 7 bis. Tâche planifiée — purge des comptes supprimés

La suppression d'une structure est effective 30 jours après la demande. Il faut donc planifier chaque jour la commande `python manage.py purge_deleted_tenants` (cron Scalingo, fichier `cron.json`, par exemple `0 3 * * *`). Sans elle, les données demandées à la suppression ne sont jamais effacées.

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

- **Signature électronique** : décision du 2026-10-12, budget serré. Chaque utilisateur signe avec **son propre compte** chez le service de son choix (DocuSeal, Yousign, DocuSign…), puis ajoute le PDF signé dans l'application (guide sur la page du contrat). Pas de compte, ni de coût, ni de donnée transmise de notre côté. Un branchement par clé d'accès de l'utilisateur (DocuSeal Pro ≈ 20 $/mois à sa charge) viendra seulement s'il est demandé ; un compte partagé BÒRD PRO seulement si l'application génère du revenu.
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
- [ ] `collectstatic` exécuté au déploiement (commande de build Scalingo) : les fichiers statiques sont servis par WhiteNoise

## Variables d'environnement prévues en production

| Variable | Origine |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
| `DJANGO_SECRET_KEY` | générée par toi, longue et aléatoire |
| `DJANGO_ALLOWED_HOSTS` | ton domaine |
| `DATABASE_URL` | addon PostgreSQL Scalingo |
| `S3_BUCKET_NAME`, `S3_ENDPOINT_URL`, `S3_REGION_NAME`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | prestataire S3 (noms définis, voir `.env.example`) |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | identifiants SMTP du prestataire d'e-mails (Brevo : `EMAIL_HOST` vaut `smtp-relay.brevo.com` par défaut, port 587) |
| `DEFAULT_FROM_EMAIL` | adresse d'envoi sur ton domaine, ex. `BÒRD PRO <contact@bord-pro.fr>` |
| `DJANGO_SITE_DOMAIN` | ton domaine sans `https://` (ex. `bord-pro.fr`) : sert aux liens des e-mails |
| `SENTRY_DSN` | Sentry (facultatif : sans valeur, rien n'est envoyé) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | ton domaine avec `https://` (ex. `https://mon-domaine.fr`) |

## Procédure de premier déploiement (Scalingo)

1. **Créer l'application** (région France) et ajouter l'addon PostgreSQL. Lier le dépôt GitHub (branche `main`) ou pousser le code.
2. **Saisir les variables** du tableau ci-dessus dans l'interface Scalingo. `DJANGO_ALLOWED_HOSTS` contient l'adresse Scalingo de l'application, puis ton domaine une fois branché. `DJANGO_CSRF_TRUSTED_ORIGINS` contient les mêmes adresses avec `https://`.
3. **Déployer**, puis lire les journaux de construction : le Tailwind doit se compiler, `collectstatic` passer, les migrations s'appliquer.
4. **Créer ton compte administrateur** : `scalingo --app <nom> run python manage.py createsuperuser`.
5. **Activer le planificateur** (Scalingo Scheduler) pour que `cron.json` soit pris en compte.
6. **Vérifier de bout en bout** (liste ci-dessous), puis seulement brancher le domaine.

Vérifications après le premier déploiement :
- la page de connexion s'affiche avec ses styles ;
- une inscription envoie bien l'e-mail de confirmation, et son lien pointe vers la bonne adresse en `https` ;
- un PDF de contrat se génère avec un texte lisible (polices) ;
- un fichier ajouté (rider, justificatif) est lisible après un redémarrage (stockage S3) ;
- le lien public d'une feuille de route fonctionne sans compte ;
- aucune requête n'apparaît dans les journaux avec un jeton de feuille de route ;
- une erreur volontaire remonte dans Sentry sans donnée personnelle.

Les dépendances ne sont pas encore figées par version : une mise à jour inattendue d'une bibliothèque pourrait casser un déploiement. À figer (fichier de versions) avant l'ouverture au public.

*Cette liste évoluera avec les sprints. Les noms exacts des variables seront ajoutés ici quand le code les utilisera.*
