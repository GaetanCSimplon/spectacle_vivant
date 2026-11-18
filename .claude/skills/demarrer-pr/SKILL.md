---
name: demarrer-pr
description: Démarre la PR suivante d'une fonctionnalité planifiée, à partir de son fichier de suivi dans docs/fonctionnalites/. À lancer manuellement en début de session.
argument-hint: [nom-de-la-fonctionnalite]
arguments: [slug]
disable-model-invocation: true
---

# Démarrer la prochaine PR de « $slug »

## État du dépôt

Branche actuelle :
!`git branch --show-current 2>/dev/null || true`

Fichiers modifiés non commités :
!`git status --short 2>/dev/null || true`

## Étapes

1. Lis `docs/fonctionnalites/$slug.md`. S'il n'existe pas, arrête-toi et dis-moi de lancer `/planifier-fonctionnalite`.
2. Repère la première PR non cochée (`- [ ]`). Si toutes sont cochées, dis-moi que la fonctionnalité est terminée et arrête-toi.
3. Vérifie l'état du dépôt ci-dessus. S'il reste des modifications non commitées, arrête-toi et montre-les-moi.
4. Mets à jour la branche principale (`git checkout main && git pull`), puis crée la branche `feature/<sujet>` (convention : CLAUDE.md §9 ; `<sujet>` = `$slug`, suivi du sujet de la PR si la fonctionnalité en compte plusieurs).
5. Relis uniquement :
   - les « Décisions prises » et « Points en suspens » du fichier de suivi ;
   - les documents listés pour cette PR ;
   - le code existant concerné.
6. Présente un plan détaillé pour cette PR seulement : fichiers créés ou modifiés, étapes, tests. Signale tout écart avec le découpage prévu.
7. Attends ma validation. N'écris aucun code avant.
8. Après validation, implémente en écrivant les tests avec le code, puis applique la définition de « terminé » de CLAUDE.md §8. Corrige jusqu'à ce que tout passe.
9. Termine par ce message :
   « Implémentation terminée. Teste dans le navigateur, puis lance /terminer-pr $slug. »

Reste dans le périmètre de cette PR. Si tu repères un problème qui concerne une autre PR, note-le pour le débriefing au lieu de le corriger.
