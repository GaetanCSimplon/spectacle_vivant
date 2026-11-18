---
name: terminer-pr
description: Clôture la PR en cours d'une fonctionnalité - vérifications, débriefing, mise à jour du fichier de suivi, commit, push et ouverture de la PR. À lancer manuellement après avoir testé.
argument-hint: [nom-de-la-fonctionnalite]
arguments: [slug]
disable-model-invocation: true
allowed-tools:
  - Bash(pytest *)
  - Bash(ruff *)
  - Bash(git status *)
  - Bash(git diff *)
---

# Terminer la PR en cours de « $slug »

## État du dépôt

Branche actuelle :
!`git branch --show-current 2>/dev/null || true`

Résumé des changements par rapport à main :
!`git diff --stat main 2>/dev/null || true`

## Étapes

1. Si la branche actuelle est `main`, arrête-toi : on ne termine jamais une PR depuis main.
2. Lance `pytest` puis `ruff check .`. Si quelque chose échoue, arrête-toi et montre-moi l'erreur. Vérifie aussi le reste de la définition de « terminé » (CLAUDE.md §8) : cas d'erreur testés, test d'isolation des tenants si un modèle ou une vue est concerné, pages publiques lisibles à 375 px.
3. Si le subagent `tenant-guard` existe (`.claude/agents/tenant-guard.md`), délègue-lui l'audit des changements de cette branche et intègre son rapport.
4. Débriefing pour moi, clair et pédagogique (je veux comprendre le code) :
   - ce qui a été fait, en 5 à 10 lignes ;
   - les fichiers modifiés et le rôle de chacun ;
   - les choix techniques et leur raison ;
   - ce que je dois tester à la main, s'il en reste ;
   - les points d'attention et ce qui a été repoussé.
5. Mets à jour `docs/fonctionnalites/$slug.md` :
   - coche la PR terminée, et la case correspondante dans `docs/produit/feuille-de-route.md` (CLAUDE.md §8) ;
   - ajoute les nouvelles décisions dans « Décisions prises », datées ;
   - mets à jour « Points en suspens » ;
   - ajoute une ligne datée dans « Journal ».
6. Propose un message de commit selon CLAUDE.md §7 (court, impératif, en anglais). Attends mon accord.
7. Après accord : commit (fichier de suivi inclus), puis `git push -u origin <branche>`.
8. Si la commande `gh` est disponible, propose une description de PR tirée du débriefing et ouvre la PR avec `gh pr create` après mon accord. Sinon, donne-moi la description à copier.
9. Ne fusionne jamais la PR et ne pousse jamais sur main : la relecture et la fusion sont faites par moi.
10. Termine par :
    - s'il reste des PR : « PR prête. Après fusion : /clear, puis /demarrer-pr $slug. »
    - sinon : « Dernière PR de la fonctionnalité. Après fusion, la fonctionnalité $slug est terminée. »
