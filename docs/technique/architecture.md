# Guide 1 — L'architecture expliquée simplement

> Ce guide reprend le point « 3. Architecture » de la proposition et explique chaque terme.
> Lecture recommandée avant de commencer la Phase 1.

## 1. Qu'est-ce que « l'architecture » ?

C'est le plan de la maison avant de poser les briques : **comment le code est découpé, où sont stockées les données, et comment les différents utilisateurs sont séparés les uns des autres.** Une mauvaise décision ici est coûteuse à corriger plus tard ; une mauvaise décision dans un bouton, non. C'est pourquoi on la fixe au début.

## 2. « Monolithe modulaire »

### Monolithe
Toute l'application est **un seul programme**, déployé en un seul endroit, avec une seule base de données.
- Alternative : les **microservices** (plusieurs petits programmes qui se parlent par le réseau). C'est puissant pour de grosses équipes, mais très lourd à maintenir seul (plusieurs déploiements, communications réseau, pannes partielles…).
- **Pour toi** : un monolithe = un seul dépôt, un seul déploiement, un seul endroit où chercher un bug. C'est le bon choix pour un développeur solo.

### Modulaire
Le monolithe n'est pas un gros bloc en désordre : il est **rangé en tiroirs**. Dans Django, un tiroir s'appelle une **app**. Chaque app gère un domaine du métier :

| App | Rôle (en une phrase) |
|---|---|
| `accounts` | Les personnes : comptes utilisateurs, connexion, lien avec une structure |
| `tenants` | Les structures (l'artiste, l'association) et leurs infos légales |
| `core` | Les outils communs (notamment la protection entre structures, voir §4) |
| `catalog` | Les spectacles vendus |
| `addressbook` | Le carnet d'adresses : organisateurs, lieux, contacts |
| `gigs` | Les dates de concert (le cœur de l'application) |
| `documents` | Contrats, devis, factures, génération des PDF |
| `roadmaps` | Les feuilles de route |
| `finance` | Paiements, dépenses, tableau de bord, exports |

**Règle de rangement** : si tu hésites où mettre du code, demande-toi « de quel domaine métier ça parle ? ». Un contrat parle de documents → `documents`. Le tiroir évite qu'un fichier de 3 000 lignes contienne tout.

## 3. Comment une page s'affiche (le trajet d'une requête)

Prenons « voir la liste de mes dates » :

```
Navigateur ──► URL (/dates/) ──► Vue (View) ──► Modèle (Model) ──► Base PostgreSQL
                                     │                                   │
                                     ◄────── données (les dates) ◄───────┘
                                     │
                                     ▼
                               Template (HTML) ──► Navigateur (la page)
```

- **URL** : l'adresse demandée. Le fichier `urls.py` dit « pour cette adresse, appelle telle vue ».
- **Vue** : le chef d'orchestre. Elle vérifie qui est connecté, demande les données, choisit le template.
- **Modèle** : la description d'une table de la base (ex. `Gig` = une date). Django traduit le Python en SQL pour toi (c'est l'**ORM**).
- **Template** : le HTML avec des trous à remplir (« affiche le titre de chaque date »).
- **Service** (`services.py`) : quand la logique est un peu complexe (ex. « numéroter une facture »), on la range dans une fonction à part plutôt que dans la vue. Ça se teste plus facilement.

**Et HTMX ?** Sans lui, chaque clic recharge toute la page. Avec HTMX, un clic peut ne remplacer **qu'un morceau** de la page (ex. filtrer la liste par mois sans rechargement). Le serveur renvoie un petit fragment de HTML, pas du JSON : c'est ce qui évite d'avoir à écrire une application JavaScript séparée.

## 4. Le multi-tenant (le point le plus important)

### Le problème
Ton application sert **plusieurs clients** (des artistes, des associations) **sur le même serveur et la même base**. Chacun doit voir **uniquement ses propres données**. Si l'artiste A voit un jour les contrats de l'artiste B, c'est une faute grave (RGPD, confiance, réputation).

*Tenant* signifie « locataire » : chaque structure est un locataire de l'immeuble. On parle de **multi-tenant** quand un seul immeuble héberge plusieurs locataires.

### Les trois façons de faire

| Approche | Image | Avantage | Inconvénient |
|---|---|---|---|
| Une base par client | Un immeuble par locataire | Isolation maximale | Très lourd à gérer : des dizaines de bases à migrer |
| Un schéma par client | Un étage par locataire | Bonne isolation | Complexe, outils spécifiques |
| **Base partagée + clé `tenant`** | Un immeuble, un badge sur chaque objet | **Simple**, une seule base | Il faut **ne jamais oublier** de filtrer |

**Choix retenu : base partagée avec une clé `tenant`.** Chaque ligne de chaque table métier porte l'identifiant de la structure propriétaire.

### Comment ça fonctionne concrètement

1. Chaque modèle métier (`Show`, `Gig`, `Invoice`…) contient un champ `tenant` (une clé étrangère vers `Tenant`).
2. Pour éviter de le réécrire partout, on crée une classe mère **`TenantOwnedModel`** dont tous héritent :

```python
# apps/core/models.py (schéma, à faire écrire par Claude Code)
class TenantOwnedModel(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE
    )

    class Meta:
        abstract = True  # cette classe n'a pas de table à elle seule
```

3. À chaque requête, un **middleware** (un petit code exécuté avant toutes les vues) détermine « quelle structure est en train d'utiliser l'app ? » et la place dans `request.tenant`.
4. Chaque vue hérite d'un **`TenantScopedMixin`** qui ajoute automatiquement le filtre :

```python
# Ce que fait le mixin, en substance
Gig.objects.filter(tenant=request.tenant)
```

5. Résultat : même si un utilisateur devine l'URL `/dates/42/` d'une date d'une autre structure, il reçoit une **erreur 404**, car la date 42 n'existe pas *dans son périmètre*.

### Pourquoi c'est risqué (et comment on se protège)
Le danger, c'est **l'oubli silencieux** : une vue qui écrit `Gig.objects.get(pk=42)` sans filtre marche parfaitement… et montre les données de tout le monde. Aucune erreur ne s'affiche. Défenses :
- Règle écrite dans `CLAUDE.md` pour que l'agent ne l'oublie pas ;
- Tous les accès passent par le mixin ;
- **Un test d'isolation par modèle** (« l'organisation B ne voit pas l'objet de A ») ;
- Un test qui **échoue** si un nouveau modèle n'a pas son test d'isolation ;
- Ta relecture attentive de chaque vue générée par l'IA.

## 5. Utilisateurs, structures et rôles

```
User  ──(Membership + rôle)──►  Tenant
```

- **User** : une personne avec un e-mail et un mot de passe.
- **Tenant** : une structure (l'association « Les Nocturnes », l'artiste « Julie Martin »).
- **Membership** : la ligne qui dit « cette personne fait partie de cette structure, avec ce rôle ».

**Pourquoi une table intermédiaire plutôt qu'un simple champ `user.tenant` ?** Parce qu'un manager peut gérer deux artistes, ou un artiste peut inviter son tourneur. Ajouter cette table plus tard obligerait à réécrire l'authentification et les migrations. L'ajouter maintenant coûte une heure.

**En MVP** : un utilisateur = une structure (on prend la première `Membership`), sans sélecteur de structure. Le modèle de données est prêt pour plus tard.

## 6. Les données : PostgreSQL et les migrations

- **PostgreSQL** stocke tout de façon structurée (tables, relations, contraintes). C'est un choix sûr, avec des **transactions** : « tout ou rien », indispensable pour la numérotation des factures.
- **Migration** : un fichier qui décrit un changement de structure de la base (« ajoute la colonne `status` à `Gig` »). Django les génère (`makemigrations`) et les applique (`migrate`). Elles sont versionnées avec le code : on peut recréer la base à l'identique n'importe où.
- **Relations** : `Gig` a une clé étrangère vers `Show`, `Promoter`, `Venue`. C'est ce qui permet de dire « cette date est pour ce spectacle chez cet organisateur ».
- **Snapshots** : une facture émise **copie** les infos légales au moment de l'émission. Si l'artiste change son adresse dans un an, l'ancienne facture doit rester exactement telle qu'elle était.

## 7. Génération des PDF

`WeasyPrint` prend une page HTML/CSS (un template Django comme les autres) et la transforme en PDF. Avantages : tu écris le contrat comme une page web ; tu modifies le style en CSS.
**Point d'attention** : il a besoin de bibliothèques système (Pango) installées sur ta machine, dans Docker et sur Scalingo. On teste donc **tôt** (Phase 1 et 2), pas en fin de projet.

## 8. Stockage des fichiers

Les PDF figés et les justificatifs ne vont pas dans la base, mais dans un **bucket S3** (un espace de stockage de fichiers en ligne). On utilise un bucket **européen** (RGPD). En développement, un simple dossier local suffit ; la bascule S3 se fait par configuration (`django-storages`).

## 9. Environnements et déploiement

| Environnement | Rôle |
|---|---|
| **Local** | Ton ordinateur, où tu développes |
| **Staging** | Copie de la production, pour tester en conditions réelles sans risque |
| **Production** | Ce que voient les vrais utilisateurs |

- **CI (intégration continue)** : à chaque modification poussée sur GitHub, un robot (GitHub Actions) lance le lint puis les tests (`.github/workflows/ci.yml`). Si ça échoue, on ne fusionne pas. Pour économiser les minutes GitHub incluses : pas de CI si seuls des fichiers `.md` ou `docs/` changent, un nouveau push annule l'exécution précédente de la même branche, et le job dure 15 minutes au maximum. Le lint échoue avant l'installation des bibliothèques système de WeasyPrint. En local, `pre-commit` lance `ruff` à chaque commit et `pytest` à chaque push (en parallèle, `-n auto` : environ 5 minutes au lieu de 26 pour toute la suite) : `pip install -r requirements/dev.txt` puis `pre-commit install --hook-type pre-commit --hook-type pre-push`.
- **CD (déploiement continu)** : après fusion, le code part automatiquement sur staging ; la production se déclenche à la main.
- **Variables d'environnement** : les secrets (mot de passe de base, clés) vivent hors du code, dans un fichier `.env` en local et dans les réglages de Scalingo en production.

## 10. Les tâches en arrière-plan

Certaines actions ne doivent pas bloquer la page : envoyer un e-mail de relance, générer un gros export. En v1, on utilisera un **cron** (tâche planifiée : « tous les matins à 8 h, cherche les options qui expirent »). Plus tard seulement, si nécessaire, une file de tâches (`procrastinate`, qui utilise PostgreSQL). **Pas de Celery/Redis** : c'est de la complexité inutile à ce stade.

## 11. Ce qu'on achète ou réutilise au lieu de le coder

| Besoin | Solution | Pourquoi |
|---|---|---|
| Connexion, mot de passe oublié | `django-allauth` | La sécurité des mots de passe ne s'improvise pas |
| Signature électronique | Prestataire (Yousign ou équivalent) | Valeur juridique = ne se code pas soi-même |
| E-mails | Brevo / Scaleway TEM | Délivrabilité, conformité UE |
| Paiement des abonnements | Stripe | Idem |
| Erreurs en production | Sentry (région UE) | Tu sais qu'un bug existe avant l'utilisateur |

## 12. Schéma d'ensemble

```
              Utilisateur (mobile / ordinateur)
                          │  HTTPS
                          ▼
                 ┌───────────────────┐
                 │  Scalingo (FR)    │
                 │  Django           │  ← un seul programme
                 │  ├ middleware → request.tenant
                 │  ├ vues (HTMX)    │
                 │  ├ services       │
                 │  └ WeasyPrint     │
                 └───┬──────────┬────┘
                     │          │
            ┌────────▼───┐  ┌───▼──────────┐
            │ PostgreSQL │  │ Bucket S3 UE │
            │ (données)  │  │ (PDF figés)  │
            └────────────┘  └──────────────┘
      + services externes : e-mail, Sentry, (plus tard) signature, Stripe
```

## 13. Récapitulatif : les 6 décisions à retenir

1. **Un monolithe Django** rangé en apps par domaine.
2. **Base partagée**, chaque donnée porte son `tenant`.
3. **Le filtre par organisation est obligatoire et testé**, jamais laissé au hasard.
4. **`Membership`** entre utilisateurs et structures.
5. **Documents figés** (snapshots, factures immuables, numérotation sans trou).
6. **Déploiement dès la semaine 1** : le pipeline est vert avant d'avoir des fonctionnalités.