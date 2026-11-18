---
name: planifier-fonctionnalite
description: Planifie une nouvelle fonctionnalité de Gestion Spectacle Vivant, la découpe en PR et écrit son fichier de suivi dans docs/fonctionnalites/. À lancer manuellement au début d'une fonctionnalité.
argument-hint: [nom-de-la-fonctionnalite] [description courte]
disable-model-invocation: true
---

# Planifier une fonctionnalité

Demande de l'utilisateur : $ARGUMENTS

## Contexte du dépôt

Documents disponibles :
!`ls docs/ docs/fonctionnalites/ 2>/dev/null || true`

Branche actuelle :
!`git branch --show-current 2>/dev/null || true`

## Étapes

1. Déduis de la demande un identifiant court en kebab-case (ex. `contrats-cession`). C'est le `<slug>` de la fonctionnalité.
2. Si `docs/fonctionnalites/<slug>.md` existe déjà, arrête-toi et demande s'il faut le reprendre ou le remplacer.
3. Lis CLAUDE.md, puis uniquement les documents de `docs/` utiles à cette fonctionnalité (spécifications métier, charte graphique, cahier des charges, audits). Indique lesquels tu as lus. Vérifie que la fonctionnalité figure dans `docs/produit/cahier-des-charges.md` et n'est pas dans le hors-périmètre (CLAUDE.md §10) ; sinon, signale-le avant toute question.
4. Pose-moi au maximum 5 questions sur ce qui est ambigu ou manquant. Attends mes réponses avant de continuer.
5. Propose un découpage en PR :
   - chaque PR est petite, testable et fusionnable seule, sans casser l'application ;
   - ordre logique : modèles et données d'abord, puis vues et formulaires, puis interface, puis génération de documents ;
   - pour chaque PR : objectif, fichiers concernés, tests à écrire, documents de `docs/` à relire, risques (isolation des tenants, migrations, sécurité, accessibilité).
6. Attends ma validation. Si je demande des changements, révise le découpage.
7. Une fois validé, crée `docs/fonctionnalites/<slug>.md` avec exactement ce modèle :

```markdown
# Fonctionnalité : <titre>

## Objectif
<2 à 3 phrases>

## Documents de référence
- docs/...

## Découpage en PR
- [ ] PR 1 — <titre>
  - Objectif :
  - Fichiers :
  - Tests :
  - Documents à relire :
  - Risques :
- [ ] PR 2 — ...

## Décisions prises
- <date> — <décision et raison>

## Points en suspens
- <question ouverte>

## Journal
- <date> — Plan validé.
```

8. Termine par ce message, et rien d'autre :
   « Plan enregistré dans docs/fonctionnalites/<slug>.md. Prochaine étape : /clear, repasse sur Sonnet si besoin (/model), puis /demarrer-pr <slug>. »

N'écris aucun code dans cette session.
