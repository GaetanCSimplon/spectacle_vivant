# Données de démonstration

Pour voir l'application « en usage » (listes remplies, argent encaissé et dû, feuilles de route, espace équipe), une commande remplit une base de **développement** avec une structure entièrement fictive.

```bash
python manage.py seed_demo            # crée la démonstration (refuse si elle existe déjà)
python manage.py seed_demo --reset    # la supprime puis la recrée (dates à jour)
python manage.py seed_demo --remove   # la supprime
python manage.py seed_demo --no-map   # sans recherche de position (cartes) : plus rapide
```

## Ce qui est créé
Une seule structure, **« Compagnie des Nuits d'Été »**, avec ses deux comptes, **sans toucher à vos propres données** :
- `demo@example.org` (propriétaire) et `gestion@example.org` (rôle « membre »), mot de passe `demo-bordpro-2026` ;
- 3 spectacles, 6 membres d'équipe (artistes et techniciens), 6 organisateurs, 6 lieux, 16 contacts (dont des personnes qui travaillent pour plusieurs organisateurs ou lieux, et deux « sans rattachement »), 3 lieux rattachés à un ou deux organisateurs ;
- 15 dates réparties autour d'aujourd'hui (passées, à venir, options, une annulée) : les dates sont **relatives à aujourd'hui**, la démonstration reste actuelle quand on la recrée ;
- 7 contrats signés, 12 factures (acomptes et soldes), paiements encaissés, une facture en retard, des dépenses de la structure et de membres (dont des « à rembourser »), 2 dépenses déclarées en attente de validation ;
- 3 feuilles de route préparées (créneaux, hébergement et repas avec leurs contacts), dont une partagée ;
- le lien personnel de Léa Durand (affiché à la fin de la commande) : à ouvrir dans une fenêtre privée.

Les adresses sont des rues et places publiques, choisies pour que les cartes s'affichent ; les noms de personnes, d'organisateurs et d'e-mails (`example.org`) sont inventés.

## Garde-fous
- **Développement seulement** : la commande refuse de tourner si `DJANGO_DEBUG` est désactivé (`--force` pour l'imposer, à ne jamais faire en production).
- Elle ne supprime que la structure de démonstration (`--reset`, `--remove`), jamais une autre.
- Les cartes demandent une position par adresse au service OpenStreetMap (une seconde d'écart) ; `--no-map` l'évite.
