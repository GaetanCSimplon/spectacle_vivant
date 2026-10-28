# Audit d'accessibilité automatique (axe-core)

Relancé le **2026-10-29** sur l'application du jour (annuaire avec import/export, étiquettes colorées, boutons de téléchargement). Le premier audit date du 2026-10-23 (voir `feuille-de-route.md`, Sprint « Charte v1.0 », PR 5).

## Méthode (reproductible)
1. Compte de démonstration (`seed_demo`) ; chaque écran est enregistré en HTML par le client de test Django, les adresses `/static/` pointant vers les fichiers locaux (le CSS compilé par `tailwind build` doit être à jour).
2. axe-core 4.10 est injecté dans chaque page, exécutée dans Chromium sans écran, à **1440 px** (ordinateur) et **375 px** (téléphone). Règles : WCAG 2.0, 2.1 et **2.2 AA** (dont la taille des cibles, 24 px) + bonnes pratiques d'axe. En plus : détection du débordement horizontal.
3. Un défaut volontairement injecté (bouton sans nom, image sans texte alternatif) est bien détecté : l'outil fonctionne.

## Périmètre
- **40 écrans** : accueil, Bòrd, informations de la structure, équipe (liste, fiche, formulaire), organisateurs, lieux, contacts (listes, fiches, formulaires), import, spectacles, dates (liste, calendrier, fiche, assistant), feuille de route (éditeur et page publique), finances, facturation, historique du contrat, facture, exports, connexion, inscription, mot de passe oublié, pages légales, site vitrine, espace équipe (accueil et dépenses).
- **7 états** : aperçu d'import, import refusé, formulaires en erreur (contact, organisateur), connexion refusée, liste filtrée sans résultat, menus ouverts.

## Résultat
- **Défauts trouvés et corrigés** (règle WCAG 2.2 « taille des cibles », nouvelle depuis le dernier audit) : liens e-mail et téléphone des fiches et des cartes de contacts (20 px de haut), documents de la page Bòrd, lien « Mot de passe oublié ? » (15 px) : tous ont désormais 24 px au moins.
- **Résultat final : 0 violation, 0 débordement horizontal**, aux deux largeurs.
- Deux signalements ne sont pas retenus : ils viennent de l'audit lui-même, qui ouvrait tous les menus d'une liste en même temps (ils se recouvraient). Un menu ouvert seul n'a pas le défaut.

## Ce que l'audit ne couvre pas (à faire à la main)
Une analyse automatique ne repère qu'une partie des problèmes (de l'ordre d'un tiers). Restent à vérifier : parcours complet **au clavier** (ordre de tabulation, infobulles des étiquettes au focus, menus) ; **lecteur d'écran** (NVDA ou VoiceOver) sur un parcours type (créer une date) ; **zoom à 200 %** ; vrai **téléphone** (pages publiques à 375 px, envoi d'une photo de justificatif) ; clarté des messages d'erreur.
