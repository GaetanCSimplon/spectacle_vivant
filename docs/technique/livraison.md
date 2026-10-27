# Livraison en production

Mise en place le 2026-10-28. Deux branches :

| Branche | Rôle |
|---|---|
| `main` | le travail : toutes les PR y sont fusionnées, CI verte |
| `production` | ce qui tourne sur Scalingo ; mise à jour **seulement** quand on décide de livrer |

## Règles
- Jamais de correction directe sur `production`, sauf urgence (voir plus bas).
- `production` avance **uniquement** par avancement rapide sur `main` (`--ff-only`) : pas de commit de fusion, `production` est toujours un état exact de `main`.
- On ne livre qu'un état de `main` dont la CI (`test` et `audit`) est verte.
- Une migration déjà livrée n'est **jamais modifiée** (`CLAUDE.md` §7) : une correction passe par une nouvelle migration.
- GitHub ne permet pas la protection de branche sur un dépôt privé gratuit : ces règles reposent sur la discipline, pas sur un blocage.

## Avant de livrer : liste de contrôle
1. `main` à jour et CI verte sur son dernier commit (`gh run list --branch main --limit 1`).
2. **Migrations incluses** : `git diff production..main --stat -- '*/migrations/*'`. Chaque nouvelle migration doit **ajouter** (table, colonne) sans supprimer ni transformer de données ; sinon, en parler avant.
3. **Sauvegarde de la base** de production faite le jour même (tant que les sauvegardes automatiques ne sont pas vérifiées, voir `guide-mise-en-ligne.md` §6).
4. Nouvelles **variables d'environnement** nécessaires ? (`git diff production..main -- .env.example docs/technique/services-production.md`) : les ajouter sur Scalingo **avant** de livrer.
5. Notes de livraison : la liste des PR depuis la dernière livraison (`git log --oneline --merges production..main`).

## Livrer
```bash
git checkout main && git pull
git checkout production && git pull
git merge --ff-only main        # refuse s'il n'y a pas moyen d'avancer proprement
git tag v2026-11-01             # la date de la livraison ; v2026-11-01b si deux le même jour
git push origin production --tags
```
Puis Scalingo → `bordpro` → **Deploy → Manual deployment** sur la branche `production`. Ouvrir le déploiement le plus récent et lire son journal : les migrations s'appliquent à la fin (`bin/post_deploy.sh`), il doit se terminer par un message de réussite. Ensuite, ouvrir le site et vérifier la connexion et une page de données.

## Correction urgente en production
1. `git checkout production && git checkout -b hotfix/<sujet>`.
2. Corriger, tester (`pytest`, `ruff`), ouvrir une PR **vers `production`**, CI verte, fusionner.
3. Reporter la correction sur `main` (PR `production` → `main`, ou `git cherry-pick`), pour que la livraison suivante ne l'écrase pas.
4. Étiquette, déploiement manuel de `production`.

## Retour arrière
Une migration qui a ajouté des colonnes ne se défait pas automatiquement : revenir au commit précédent suffit si la version précédente du code ignore les nouvelles colonnes (c'est le cas pour des ajouts). Restaurer une sauvegarde de la base seulement si des données ont été abîmées. Ne jamais supprimer une migration livrée.

## Historique des livraisons
| Date | Étiquette | Contenu |
|---|---|---|
| 2026-10-22 | — | premier déploiement (depuis `main`, avant la création de `production`) |
