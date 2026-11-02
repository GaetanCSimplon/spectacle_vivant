# Bòrd Pro — charte graphique appliquée à l'application

Version 3 — 2026-10-27 (charte « blanc & contrastes francs » v1.0 du 26/10/2026). Sources de l'associé : `BORD_PRO_charte_visuelle.html` (planche de référence), `BRD_PRO_design-tokens.css` et `.css.md` (jetons) ; pour le nom, le ton et le slogan : `sources-associe/brief-marque-2026-10-15.md`. La V06 (`docs/archives/charte-v06/`) est archivée. Ce document dit comment la charte s'applique au code, et **où nous nous en écartons, et pourquoi**.

## 1. Nom et ton
- Le produit s'écrit **Bòrd Pro** (avec l'accent, jamais « Bord Pro »). « BÒRD PRO » en capitales disparaît de l'interface. Le menu de la structure reste « Bòrd ».
- Slogan : **Prenez le contrôle de votre tournée.** Sous-titre : *Contacts, dates, contrats, budgets et équipe : tout au même endroit.* Écran de connexion : le slogan seul, sans sous-titre.
- Ton direct, phrases courtes, verbes d'action, vouvoiement. À éviter : « assistant », « carnet de route », métaphores maritimes, clichés du spectacle, « solution innovante », « disruptif », « all-in-one ».
- Mention à faire figurer dans les CGU et sur les pages contrats et factures : *Bòrd Pro facilite la préparation et le suivi administratif ; il ne remplace pas les obligations légales ni un conseil juridique, social ou comptable personnalisé.*

## 2. Couleurs
Les jetons `--bord-*` sont dans `css/source.css` (bloc `:root`) ; `test_brand_contrast.py` lit ce bloc et vérifie chaque couple (WCAG : 4,5:1 pour du texte, 3:1 pour un graphique ou le bord d'un champ). Blanc dominant ; les aplats rythment la page, on ne colore pas chaque cellule.

| Jeton (`--bord-…`) | Valeur | Usage |
|---|---|---|
| `brand-navy` Nuit | `#102440` | titres, texte, structure, navigation |
| `brand-coral` Corail | `#FF695B` | l'action principale d'un écran, la carte de synthèse, la page active du menu ; texte **nuit** dessus (5,5:1), jamais blanc |
| `action-bg-hover` *(ajouté)* | `#F55F4E` | survol du bouton principal |
| `brand-ocean` Océan | `#007299` | bloc d'information (texte blanc, 5,4:1), anneau de focus, recette des graphiques |
| `bg` / `surface` | `#FFFFFF` | fond général, cartes, champs |
| `brand-cream` Crème | `#F5F2EA` | document, information secondaire, pavé de date |
| `context-bg` Bleu clair | `#E2F1F6` | contexte discret (aide, message d'information), **jamais** le fond dominant |
| `text-muted` | `#465A6C` | texte secondaire |
| `border` | `#C4CFDA` | filets des cartes et séparateurs (ne suffit pas à repérer un champ) |
| `control-border` *(ajouté)* | `#6F7A8A` | contour des champs (3:1 minimum) |
| `success-text` / `-bg` | `#1F6B4A` / `#E4F0E8` | « confirmé, signé, payé » : coche + mot |
| `warning-text` / `-bg` | `#714700` / `#FFF0C8` | « à suivre, option, échéance » : horloge + mot ; l'ambre `#E3A21A` ne sert qu'au pictogramme |
| `danger-text` / `-bg` | `#8E1F3F` / `#F6E3EB` | « à compléter, problème, retard », actions destructrices : alerte + mot |
| `focus` | `#007299` | anneau de focus : 3 px, décalé de 3 px |
| `chart-revenue` / `chart-expense` *(ajoutés)* | `#007299` / `#D9473A` | graphiques (3:1 minimum sur blanc) |

Les cartes de synthèse sont des **aplats** (nuit, corail, océan, crème) ; une carte corail n'est pas cliquable d'office. Le corail n'est jamais un état d'erreur. Une couleur ne porte jamais seule le sens : pictogramme et mot l'accompagnent. L'échelle `blue-*` de Tailwind est redéfinie autour du nuit (`blue-700`), `red-*` autour du bordeaux, `green-*` et `amber-*` autour des teintes d'état : un changement dans `css/source.css` recolore l'application sans toucher aux gabarits.

### Écarts assumés avec les jetons de l'associé (décision du 2026-10-27)
1. **Texte « à suivre »** : la charte écrit le statut en ambre `#E3A21A`, environ 2:1 sur blanc, illisible. Texte `#714700`, ambre pour le pictogramme seul.
2. **Contour des champs** : `#C4CFDA` est trop clair pour repérer un champ (la charte le dit elle-même). Contour `#6F7A8A`.
3. **Interlettrage des titres** : la planche dit −0,04 em, le fichier de jetons +0,04 em. Retenu : **−0,04 em**.
4. **IBM Plex Mono « 450 »** : cette graisse n'existe pas dans nos polices. 400, et 500 pour l'emphase.
5. **Favicon 16 px** : la charte fixe 32 px minimum pour le symbole ; le 16 px est une réduction de l'icône capsule, lisible mais petite.
6. **Anneau de focus** : océan par défaut, mais blanc sur la navigation et les blocs nuit ou océan, nuit sur les blocs corail et crème (l'océan sur corail n'atteint que 1,9:1).

## 3. Décisions d'accessibilité
1. **Bouton principal : corail avec texte nuit** (blanc sur corail : 2,8:1). Un seul par écran.
2. **Liens : nuit souligné** (dans un aplat, le texte prend la couleur du bloc, souligné).
3. **États : texte foncé sur teinte claire**, tous au-dessus de 4,5:1, vérifiés par test.
4. **Statuts** : « confirmé », « signé », « payé » en vert ; « option » et « en attente » en ambre ; retards, erreurs et « à compléter » en bordeaux ; « annulé » en gris. « Signée » reste distinguée de « Confirmée » par un fond plein.
5. Cibles tactiles de **48 px** minimum.
6. Pas de texte corail sur crème (2,5:1).

## 4. Typographie, formes, icônes
- **Archivo** (800, largeur 112 %, interlettrage −0,04 em) pour les titres ; **Instrument Sans** (400 à 700) pour le texte et les libellés ; **IBM Plex Mono** (400, 500, chiffres tabulaires) pour dates, heures et montants. Trois familles **hébergées chez nous** (`static/fonts/`, licence OFL). Le nom du logo est une image, jamais recomposé en police.
- Échelle : titre de page 30–34 px, titre de carte 20–24 px, corps 16 px (interligne 24), libellés 14 px, chiffres importants 24–40 px en mono. Texte aligné à gauche.
- Rayons : **12 px** contrôles, **16 px** cartes, **24 px** grandes cartes, **28 px** sections ; pilule pour les pastilles d'état. Espacement de base 4 px. **Aucune ombre floue, aucun dégradé décoratif** (les dégradés propres aux SVG livrés restent tels quels).
- **Navigation** : colonne nuit à gauche à partir de 1024 px (logo capsule, page active en corail gras avec une barre) ; en dessous, barre blanche du haut avec menu burger. La barre de navigation du bas évoquée par la charte n'est pas faite.
- Icônes : trait de 2 px, angles arrondis, `currentColor`. Pas de micro, note de musique, rideau ni guitare.
- **Cartes de date** (2026-11-02) : la carte reste blanche. Le pavé de date et la pastille d'icône du lieu sont crème, celle de l'organisateur bleu clair avec une icône océan (le code couleur de l'annuaire), celle de la feuille de route océan plein avec une icône blanche ; les paiements sont posés sur une bande crème. Les couleurs d'état (vert, ambre) restent réservées aux statuts, jamais à la décoration. Les pastilles (`.icon-chip-*`) sont décoratives : le libellé est toujours écrit à côté.
- Les PDF de contrat, de devis et de facture sont les documents de l'utilisateur : ils **ne reprennent pas** l'habillage de la marque.

## 5. Logos et icônes (`static/brand/`)
Fournis par le graphiste, **jamais modifiés** (ni recolorés, déformés, filtrés ou recadrés ; pas de version monochrome).

| Fichier | Rôle | Où |
|---|---|---|
| `logo.svg` | logo horizontal, fond transparent | fond **blanc** : en-tête, pages publiques, site |
| `logo-capsule.svg` | logo horizontal, fond crème embarqué | fond nuit, corail, océan, image : barre latérale |
| `icon.svg` | symbole « b », fond transparent | fond blanc (réserve) |
| `icon-capsule.svg` | icône d'application | source des favicons et icônes d'app |
| `radar.svg` | icône RADAR | rangée, **non utilisée** (RADAR pas développé) |

Les PNG (`favicon-16/32/48.png`, `favicon.ico`, `icon-192/512.png`, `apple-touch-icon.png`) sont générés depuis `icon-capsule.svg` (marge transparente retirée ; l'`apple-touch-icon` est posé sur fond crème). Zone de protection : environ 50 % de la largeur du symbole ; symbole 32 px minimum ; pas de seuil défini pour le logo horizontal. La version transparente sur un fond coloré fait disparaître le nom : toujours la capsule.

## 6. Hors périmètre
La **carte et l'itinéraire** et **RADAR** (voir `docs/produit/specification-radar.md`) viendront après le MVP. Les sections « Priorisation fonctionnelle » des briefs de l'associé sont des sujets produit (Q19 du cahier des charges), pas d'habillage. Pas de mode sombre.

## 7. Historique
- Sprint 3.14 (2026-10-21) : première charte (nom, slogan, logo graphiste).
- Sprint 3.16 (2026-10-23) : refonte V06 (polices, états avec pictogramme, aplats).
- Sprint 3.17 (2026-10-27) : charte v1.0 en quatre PR (jetons, logos, composants, nettoyage). Détail dans `docs/produit/feuille-de-route.md`.

## 8. Checklist de cohérence avant publication
- [x] Nom « Bòrd Pro » avec accent partout (test : aucun gabarit n'écrit l'ancienne graphie).
- [x] Slogan « Prenez le contrôle de votre tournée » (inscription, accueil vide, e-mails).
- [x] Un seul bouton principal corail par écran ; les actions qui détruisent sont rouges.
- [x] Les couleurs d'état ne servent jamais à décorer ; aucun gabarit ne cite le corail (classes `.fab`, `.card-accent`).
- [x] Statut = pictogramme + mot.
- [x] Aucune ombre floue dans les gabarits (test).
- [x] Logo adapté au fond : transparent sur blanc, capsule sur nuit.
- [x] Mention juridique dans les CGU et sur les écrans du contrat et de la facturation.
- [ ] Revue des pages publiques à 375 px (non faite ; les écrans connectés sont conçus pour l'ordinateur).

Reste hors de ce chantier : fichiers vectoriels officiels du logo si le graphiste en fournit de nouveaux.
