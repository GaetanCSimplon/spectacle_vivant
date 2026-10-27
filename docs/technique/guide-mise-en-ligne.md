# Guide de mise en ligne — pas à pas

**Pour qui :** le développeur du projet, qui fait la mise en ligne lui-même. **Version du 2026-10-25.** À suivre dans l'ordre : chaque étape se termine par un **test** qui dit si elle a marché.

**Important avant de commencer**
- Je n'ai pas vu les écrans de Brevo, Scalingo, Scaleway ou Sentry : les noms de menus ci-dessous viennent de leur documentation et peuvent avoir légèrement changé. Si un menu n'est pas là où je le dis, cherche le mot-clé en gras.
- **Tous les mots de passe, clés et jetons vont dans Proton Pass, tout de suite**, quand ils s'affichent. Une clé qui ne s'affiche qu'une fois (Brevo, Scaleway) est perdue si tu fermes la page.
- **Ne colle jamais un secret** dans un message, dans le dépôt, ni dans un fichier suivi par Git.
- **Changer une variable Scalingo ne relance pas le build** : après chaque changement, fais un **déploiement manuel**, puis ouvre le **déploiement le plus récent** pour lire son journal.
- Contexte : application Scalingo `bordpro` (région France), adresse temporaire `https://bordpro.osc-fr1.scalingo.io`, domaine `bordpro.fr` acheté par ton associé.

Ordre : **1.** Brevo → **2.** domaine → **3.** bucket de fichiers → **4.** compte administrateur et premier invité → **5.** Sentry → **6.** sauvegardes → **7.** surveillance et tâche planifiée → **8.** contrôle final.

---

## 1. Brevo : l'envoi des e-mails

**Pourquoi d'abord :** sans lui, personne ne peut s'inscrire (l'e-mail de confirmation est obligatoire) et le formulaire de contact ne marche pas.

### 1.1 Faire valider le domaine par ton associé
1. Retrouve le **lien de délégation** envoyé à ton associé (méthode « Déléguer » dans Brevo). S'il est perdu : dans Brevo, ouvre ton nom en haut à droite → **Senders, domains & dedicated IPs** (« Expéditeurs, domaines et IP dédiées ») → onglet **Domains** → `bordpro.fr` → **Authenticate** → « Déléguer », et renvoie-lui le nouveau lien.
2. Ton associé l'ouvre et suit les étapes : soit Brevo ajoute tout seul les enregistrements chez son registrar, soit Brevo lui affiche une liste de lignes à créer dans la zone DNS (types **TXT** et **CNAME**).
3. Règle à lui transmettre : **n'ajouter que les lignes données par Brevo**. S'il existe déjà un enregistrement **SPF** (un TXT qui commence par `v=spf1`), on le **complète**, on n'en crée jamais un deuxième.
4. **Test :** dans Brevo, le domaine `bordpro.fr` passe à **« Authenticated »** (« Authentifié »). Les changements DNS peuvent mettre de quelques minutes à quelques heures : si ce n'est pas encore le cas, clique sur **Authenticate/Vérifier** de nouveau plus tard.

### 1.2 Valider l'expéditeur
1. Même menu → onglet **Senders** → **Add a sender** : nom `Bòrd Pro`, adresse `contact@bordpro.fr`.
2. Brevo envoie un e-mail de confirmation à `contact@bordpro.fr` : ouvre-le (cette boîte doit exister et être lisible par toi) et clique le lien.
3. **Test :** l'expéditeur est marqué **Verified**.

### 1.3 Créer la clé SMTP
1. En haut à droite → **SMTP & API** → onglet **SMTP**.
2. Note l'**identifiant** (de la forme `xxxxxx@smtp-brevo.com`) et le serveur (`smtp-relay.brevo.com`, port 587 : c'est déjà le réglage par défaut du projet).
3. **Generate a new SMTP key** : donne-lui un nom (`bordpro-prod`). La clé s'affiche **une seule fois** → **Proton Pass immédiatement**.
4. **Test :** tu as dans Proton Pass deux éléments : l'identifiant `…@smtp-brevo.com` et la clé SMTP.

### 1.4 Les donner à Scalingo
1. Scalingo → application `bordpro` → **Environment** (Environnement).
2. Modifie ces trois variables (sans espace avant ni après la valeur) :
   - `EMAIL_HOST_USER` = l'identifiant `…@smtp-brevo.com`
   - `EMAIL_HOST_PASSWORD` = la clé SMTP
   - `DEFAULT_FROM_EMAIL` = `Bòrd Pro <contact@bordpro.fr>`
3. Enregistre, puis **Deploy → Manual deployment** sur la branche `production` (voir `livraison.md` : `production` n'avance que lorsqu'on livre ; pour un simple changement de variable, déploie la branche telle qu'elle est). Attends la fin et ouvre le déploiement le plus récent : il doit finir par un message de réussite (les journaux du build ne montrent pas d'erreur `Set the ...`).

### 1.5 Tester l'envoi sans passer par l'inscription
Ce test est indépendant du compte et de la liste d'invités. Dans Scalingo, ouvre une **console** de l'application (bouton **Run console** / « Exécuter une commande »), puis tape (remplace par une adresse à toi) :
```
python manage.py shell -c "from django.core.mail import send_mail; print(send_mail('Test Bòrd Pro', 'Bonjour, ceci est un test.', None, ['ton.adresse@exemple.fr']))"
```
- **Test :** la commande affiche `1` et l'e-mail arrive (regarde aussi les **spams**).
- Si elle affiche une erreur `535` : l'identifiant ou la clé est faux (recopie depuis Proton Pass). Erreur de connexion : vérifie que `EMAIL_HOST` n'a pas été modifié.

### 1.6 Tester le formulaire de contact
Ouvre `https://bordpro.osc-fr1.scalingo.io/contact/`, envoie un message. **Test :** il arrive dans la boîte `contact@bordpro.fr`.

---

## 2. Le domaine `bordpro.fr`

**Quand :** après Brevo. Avec ton associé (il a la main sur le DNS).

1. Scalingo → `bordpro` → **Domains** → **Add a domain** : ajoute `bordpro.fr`, puis `www.bordpro.fr`.
2. Scalingo affiche, pour chacun, l'enregistrement DNS à créer (un **CNAME** vers `bordpro.osc-fr1.scalingo.io` ou une cible indiquée). **Recopie ce que Scalingo affiche**, pas ce que j'écris ici.
3. Ton associé les crée chez le registrar. Particularité : on ne peut en principe pas mettre de CNAME sur le nom « nu » `bordpro.fr`. S'il propose un enregistrement **ALIAS** ou **ANAME**, il l'utilise. Sinon, `www.bordpro.fr` devient l'adresse principale et le registrar redirige `bordpro.fr` vers elle.
4. Scalingo délivre le certificat **HTTPS** tout seul (quelques minutes). **Test :** `https://bordpro.fr` (ou `www`) affiche le site, avec le cadenas, **sans avertissement**.
5. **Seulement quand le HTTPS marche**, change les 3 variables (le site force le HTTPS et l'HSTS pendant 30 jours : une adresse sans certificat valide serait inaccessible) :
   - `DJANGO_ALLOWED_HOSTS` = `bordpro.fr,www.bordpro.fr,bordpro.osc-fr1.scalingo.io` (une seule ligne, sans `https://`, sans `/`)
   - `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://bordpro.fr,https://www.bordpro.fr,https://bordpro.osc-fr1.scalingo.io` (**sans `/` final**)
   - `DJANGO_SITE_DOMAIN` = `bordpro.fr` (sans `https://`, sans `/`)
6. Déploiement manuel. **Test :** la page de connexion s'ouvre sur `https://bordpro.fr`, et le formulaire de contact s'envoie sans erreur 403 (si 403 : `DJANGO_CSRF_TRUSTED_ORIGINS` est faux).

---

## 3. Le bucket de fichiers privé (Scaleway)

**À quoi ça sert :** Scalingo n'a pas de disque permanent. Sans bucket, les fichiers (PDF figés, riders, fiches techniques) disparaissent à chaque redémarrage. Les instructions sont pour **Scaleway** ; chez OVH la logique est la même.

1. Crée un compte sur `console.scaleway.com` (région France) et un **projet** (ex. `bordpro`). Active la double authentification.
2. **Object Storage → Create a bucket** : région **Paris (fr-par)**, nom unique (ex. `bordpro-prod-` + quelques lettres), visibilité **Private**.
3. **IAM → Applications** : crée une application `bordpro-app`, avec une règle d'accès **Object Storage** limitée à ce projet. Puis **API keys → Generate an API key** pour cette application. Tu obtiens :
   - une **clé d'accès** (commence par `SCW…`) ;
   - une **clé secrète**, affichée **une seule fois** → Proton Pass.
4. Dans Scalingo, remplace les `placeholder` :
   - `S3_BUCKET_NAME` = le nom du bucket
   - `S3_ENDPOINT_URL` = `https://s3.fr-par.scw.cloud` (avec `https://`)
   - `S3_REGION_NAME` = `fr-par`
   - `S3_ACCESS_KEY_ID` = la clé d'accès
   - `S3_SECRET_ACCESS_KEY` = la clé secrète
5. Déploiement manuel.
6. **Test (console Scalingo) :**
```
python manage.py shell -c "from django.core.files.base import ContentFile; from django.core.files.storage import default_storage as s; n=s.save('test-bordpro.txt', ContentFile(b'ok')); print(n, s.exists(n)); s.delete(n)"
```
   **Résultat attendu :** le nom du fichier puis `True`. Dans la console Scaleway, le bucket doit rester **privé** (un lien direct vers un fichier doit être refusé).

---

## 4. Compte administrateur et premier invité

L'inscription est **sur invitation** : seules les adresses de la liste d'invités peuvent s'inscrire.

1. Dans la console Scalingo : `python manage.py createsuperuser` (adresse e-mail, mot de passe fort → Proton Pass).
2. Ouvre `https://bordpro.fr/admin/` (ou l'adresse Scalingo), connecte-toi.
3. Section **Invitations d'inscription** → **Ajouter** : l'adresse de la personne (et une note, ex. « Marie, bêta »).
4. **Test complet du parcours :** invite **une de tes adresses** (pas celle de l'administrateur), puis sur la page de connexion clique **« J'ai reçu une invitation : créer un compte »**, inscris-toi, ouvre l'e-mail de confirmation (le lien doit pointer vers `https://bordpro.fr/…`), confirme, connecte-toi, crée ta structure.
5. Retourne dans l'administration : la colonne **« inscrit le »** de cette invitation est remplie.
6. Teste aussi **« Mot de passe oublié »** : l'e-mail doit arriver et le lien fonctionner.

---

## 5. Sentry : être prévenu quand une page plante

1. Crée un compte sur `sentry.io` en choisissant l'**hébergement des données dans l'UE** au moment de l'inscription (ce choix ne se change pas ensuite).
2. Crée un projet, plateforme **Django**.
3. Copie le **DSN** (Settings → Projects → ton projet → **Client Keys (DSN)**) → Proton Pass.
4. Scalingo : `SENTRY_DSN` = le DSN, puis déploiement manuel.
5. **Test :** dans la console, `python manage.py shell -c "import sentry_sdk; sentry_sdk.capture_message('test bordpro')"` ; l'événement apparaît dans Sentry en une minute. Vérifie qu'il ne contient pas d'adresse e-mail.

---

## 6. Sauvegardes de la base et test de restauration

1. Scalingo → `bordpro` → **Resources/Addons** → l'addon **PostgreSQL** → onglet **Backups**. Repère : les sauvegardes sont-elles **automatiques**, et pendant **combien de jours** sont-elles conservées ? C'est lié à ton offre (voir le tarif de l'addon). Note la réponse dans Proton Pass (note) ou dans ce fichier.
2. Lance une sauvegarde manuelle (**Create a backup**) et attends qu'elle soit terminée.
3. **Test de restauration (indispensable, une sauvegarde jamais testée n'existe pas) :**
   - télécharge la sauvegarde (bouton de téléchargement ; fichier `.pgsql.tar.gz` ou similaire) ;
   - en local, crée une base jetable (`createdb bordpro_restore_test` ou dans le conteneur `docker compose exec db createdb -U spectacle bordpro_restore_test`) ;
   - restaure : `pg_restore --no-owner --no-privileges -d bordpro_restore_test le_fichier` (décompresse d'abord s'il est en archive) ;
   - **vérifie** : `psql bordpro_restore_test -c "select count(*) from accounts_user;"` donne le nombre attendu de comptes ;
   - supprime la base jetable. **Ne restaure jamais sur la base de production pour tester.**

---

## 7. Surveillance de disponibilité et tâche planifiée

### 7.1 Surveillance
1. Crée un compte gratuit sur un service de surveillance (UptimeRobot, Better Stack…).
2. Ajoute un contrôle HTTP sur `https://bordpro.fr/` toutes les 5 minutes, alerte par e-mail à `contact@bordpro.fr`. (La page d'accueil publique répond toujours `200` : pas besoin d'une adresse spéciale.)
3. **Test :** le contrôle passe au vert.

### 7.2 Tâche planifiée (purge des structures supprimées, 3 h du matin)
Le fichier `cron.json` du projet décrit la tâche, mais Scalingo ne l'exécute que si le module **Scheduler** est ajouté.
1. Scalingo → `bordpro` → **Addons** → ajoute **Scheduler** (gratuit).
2. Déploiement manuel : Scalingo lit `cron.json` à ce moment.
3. **Test :** dans l'onglet du Scheduler, la tâche `purge_deleted_tenants` apparaît avec son horaire.

---

## 8. Contrôle final

1. Console Scalingo : `python manage.py check --deploy` → **0 problème** (à me coller si ce n'est pas le cas).
2. Déroule la **recette du MVP** (`docs/produit/cahier-des-charges.md` §11) avec ton compte de test **sur la production**, sans aide :
   - créer son compte et sa structure en moins de 10 minutes ;
   - créer un organisateur, un lieu, un spectacle ;
   - créer une date et la faire passer de « option » à « signée » ;
   - générer le contrat PDF, le télécharger ;
   - émettre une facture d'acompte puis de solde ;
   - enregistrer un paiement ;
   - créer une feuille de route, la partager par lien, l'ouvrir **sur ton téléphone** ;
   - saisir une dépense, voir le bilan, exporter le CSV.
3. Reviens vers moi : on coche la recette, on met à jour la page d'état (`docs/produit/etat-du-projet.md`) et on prépare les invitations des testeurs.

---

## Si quelque chose ne marche pas

| Symptôme | Cause probable | Que faire |
|---|---|---|
| Le build s'arrête avec `Set the …` | Une variable obligatoire manque (`S3_*`, `EMAIL_*`, `DEFAULT_FROM_EMAIL`) | La créer, même provisoire, puis redéployer |
| Erreur 500 à l'inscription, journal `SMTPAuthenticationError 535` | Identifiant ou clé SMTP faux | Recopier depuis Proton Pass ; test 1.5 |
| Erreur 400 « Bad Request » sur le site | `DJANGO_ALLOWED_HOSTS` ne contient pas l'adresse utilisée | Ajouter l'adresse, redéployer |
| Erreur 403 sur un formulaire | `DJANGO_CSRF_TRUSTED_ORIGINS` faux (manque `https://` ou `/` final en trop) | Corriger, redéployer |
| Page blanche ou CSS absent | `DISABLE_COLLECTSTATIC` n'est pas à `1` | Le remettre à `1`, redéployer |
| « J'ai modifié une variable, rien ne change » | Pas de nouveau déploiement | Déploiement manuel, puis journal du dernier déploiement |
| Les liens des e-mails pointent vers la mauvaise adresse | `DJANGO_SITE_DOMAIN` | Corriger (sans `https://`), redéployer |
| Les e-mails arrivent en spam | Domaine non authentifié dans Brevo, ou DMARC absent | Reprendre 1.1 ; regarder l'état du domaine dans Brevo |
| « L'inscription se fait sur invitation » pour un testeur | Son adresse n'est pas dans la liste | L'ajouter dans `/admin/` (même orthographe que celle qu'il saisit) |
