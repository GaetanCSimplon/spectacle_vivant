# Bòrd Pro — charte graphique appliquée à l'application

Version 2 — 2026-10-23 (direction V06). Sources : `sources-associe/charte-graphique-v06.pdf`, `brief-integration-ui-v06-2026-10-22.md` et, pour le nom, le ton et le logo, `brief-marque-2026-10-15.md`. Là où la V06 diffère du brief du 15/10 (couleurs, polices, formes), **la V06 l'emporte**. Ce document dit comment la charte s'applique au code et ce qui a été décidé là où elle ne tranche pas.

## 1. Nom et ton
- Le produit s'écrit **Bòrd Pro** (avec l'accent, jamais « Bord Pro »). « BÒRD PRO » en capitales disparaît de l'interface. Le menu de la structure reste « Bòrd ».
- Slogan : **Prenez le contrôle de votre tournée.** Sous-titre : *Contacts, dates, contrats, budgets et équipe : tout au même endroit.* Écran de connexion : le slogan seul, sans sous-titre (« Votre activité, au clair. » n'est plus utilisé).
- Ton direct, phrases courtes, verbes d'action, vouvoiement. À éviter : « assistant », « carnet de route », métaphores maritimes, clichés du spectacle.
- Mention à faire figurer dans les CGU et sur les pages contrats et factures : *Bòrd Pro facilite la préparation et le suivi administratif ; il ne remplace pas les obligations légales ni un conseil juridique, social ou comptable personnalisé.*

## 2. Couleurs (direction V06, 2026-10-23)
Sources : `docs/marque/sources-associe/charte-graphique-v06.pdf` et le brief du 22/10. La V06 **remplace** les valeurs du brief du 15/10 là où elles diffèrent. Les jetons `--bord-*` sont dans `css/source.css` ; le test `test_brand_contrast.py` lit ce bloc et vérifie chaque couple (WCAG : 4,5:1 pour du texte, 3:1 pour un graphique ou le bord d'un champ).

| Jeton (`--bord-…`) | Valeur | Usage |
|---|---|---|
| `brand-navy` Bleu nuit | `#102440` | titres, texte, structure, grands aplats |
| `brand-coral` Corail | `#FF6B5B` | l'action principale d'un écran et une carte de synthèse ; texte bleu nuit dessus (5,6:1), jamais blanc |
| *(ajouté)* `action-bg-hover` | `#F55F4E` | survol du bouton principal |
| `bg` Fond de page | `#F2F5FA` | fond général, gris-bleu très clair (**plus de blanc cassé ni de beige**) |
| `surface` | `#FFFFFF` | cartes, champs, zones de lecture |
| `info-bg` Information | `#DCE8F7` | carte ou bandeau d'information |
| `brand-cream` Crème | `#F5F2EA` | document, support secondaire (jamais le fond de l'application) |
| `text-muted` | `#5B6372` | texte secondaire (6:1 sur blanc) |
| `brand-gray` Gris-bleu | `#687080` | repère secondaire, icônes (à tester avant tout texte) |
| `border` | `#D8E0EB` | filets décoratifs (1,3:1 : ne suffit pas à identifier un champ) |
| `control-border` | `#6F7A8A` | contour des champs (3,0:1 minimum sur blanc et sur le fond) |
| `success-text` / `success-bg` | `#1F6B4A` / `#E4F0E8` | « confirmé, signé, payé » : coche + mot |
| `warning-text` / `warning-bg` | `#714700` / `#FFF0C8` | « à suivre, option, échéance » : horloge + mot (`brand-amber` `#E3A21A` pour le pictogramme) |
| `danger-text` / `danger-bg` | `#8E1F3F` / `#F6E3EB` | « à compléter, problème, retard », actions destructrices : alerte + mot (bordeaux) |
| `focus` | `#102440` | anneau de focus : 3 px, décalé de 3 px |
| *(ajouté)* `chart-revenue` / `chart-expense` | `#2F6FB5` / `#D9473A` | graphiques : recette en bleu, dépenses en corail foncé (3:1 minimum sur blanc) |

Répartition indicative d'une vue : 60 % de surfaces claires, 25 % de structure bleu nuit, 10 % de supports, 5 % d'actions corail (repère, pas une règle mécanique). **Les cartes de synthèse sont des aplats** (bleu nuit, corail, bleu clair, crème), pas de simples bordures colorées. Le corail n'est jamais un état d'erreur. Une couleur ne porte jamais seule le sens : un pictogramme et un mot l'accompagnent.

L'échelle `blue-*` de Tailwind (employée partout pour « la couleur de la marque ») est redéfinie autour du bleu nuit (`blue-700`), `red-*` autour du bordeaux, `green-*`, `amber-*` autour des teintes d'état : un changement dans `css/source.css` recolore l'application sans toucher aux gabarits.

## 3. Décisions d'accessibilité
1. **Bouton principal : corail avec texte bleu nuit.** Le texte blanc sur corail n'atteint que 2,8:1.
2. **Liens : bleu nuit souligné.**
3. **États : texte foncé sur teinte claire**, tous au-dessus de 4,5:1, vérifiés par test.
4. **Statuts** : « confirmé », « signé », « payé » en vert ; « option » et « en attente » en ambre ; retards, erreurs et « à compléter » en bordeaux ; « annulé » en gris. « Signée » reste distinguée de « Confirmée » par un fond plein.
5. Cibles tactiles de **48 px** minimum (boutons, champs).

## 4. Typographie, formes, icônes
- **Archivo** (graisse 800, largeur 112 %, interlettrage −0,04 em) pour les titres ; **Instrument Sans** (400 à 700) pour le texte, les formulaires et les libellés ; **IBM Plex Mono** (400, 500, chiffres tabulaires) pour les dates, heures et montants. Trois familles **hébergées chez nous** (`static/fonts/`, licence OFL), sans fournisseur externe. Le lettrage du logo est celui de l'image, indépendant des polices.
- Échelle : titre de page 30–34 px, titre de carte 20–24 px, corps 16 px (interligne 24), libellés 14 px, chiffres importants 24–40 px en mono.
- Rayons : **12 px** pour les contrôles, **20 px** pour les cartes, **28 px** pour les grandes sections ; pilule pour les pastilles d'état. Ombre très discrète. Base d'espacement : 4 px.
- Focus visible : anneau bleu nuit de 3 px, décalé de 3 px.
- **Navigation :** colonne fixe à gauche à partir de 1024 px ; en dessous, barre du haut avec menu burger. Les entrées actuelles sont conservées (décision du 2026-10-23). Page active : bleu clair avec une barre corail.
- Icônes : trait de 2 px, angles arrondis, `currentColor`. Pas de micro, note de musique, rideau ni guitare. Pas de tampon, de dégradé, de néon ni d'ombre floue.
- **Une seule action principale (corail) par écran.**
- Les PDF de contrat, de devis et de facture sont les documents de l'utilisateur : ils **ne reprennent pas** l'habillage de la marque.

## 5. Logo
Fichiers fournis par le graphiste, déposés dans `static/brand/`. Le `LOGO_2.pdf` cité par le brief V06 n'est pas encore fourni : le logo actuel est conservé en attendant (décision du 2026-10-23). Règles : ne jamais déformer ni recolorer ; zone de protection = hauteur du « B » ; monogramme 16 px minimum, logo horizontal 120 px de large minimum ; fond blanc cassé ou bleu nuit.

## 6. Hors périmètre de ce chantier
La **carte et l'itinéraire** et **RADAR** (brief V06) sont mis de côté jusqu'à la fin de la refonte (décision du 2026-10-23) : la carte suppose un service de géolocalisation (`CLAUDE.md` §10), RADAR des règles à définir (Q17).

La section « Priorisation fonctionnelle » de la charte (pipeline de diffusion, CRM complet, contrats CDDU et checklist GUSO, budget prévisionnel contre réel, rôles collaboratifs) n'est pas un sujet d'habillage : elle est enregistrée comme **Q19** dans le cahier des charges, rien n'est codé. Pas de mode sombre : « lisibles en faible luminosité » est traité par les contrastes ci-dessus.

## 7. Plan de livraison (Sprint 3.14)
1. Documentation (ce document, Q19, `CLAUDE.md`).
2. Fondations du thème : polices, jetons, fond, arrondis, boutons, en-tête, échelle typographique, test de contraste.
3. Nom, logo, slogan et messages : titres des pages, en-tête, favicon, connexion, inscription, écrans vides, e-mails.
4. États et icônes : statuts des dates, des paiements et de Bòrd, graphiques, icônes en trait.
5. Mention juridique, relevé des écrans à plusieurs boutons principaux, checklist de cohérence, vérification visuelle en 1280 px et 375 px.

## 8. Checklist de cohérence avant publication (contrôlée le 2026-10-21)
- [x] Le nom est écrit « Bòrd Pro », avec accent, partout dans l'interface (test : aucun gabarit n'écrit l'ancienne graphie).
- [x] Le slogan est « Prenez le contrôle de votre tournée » (inscription, accueil d'une structure vide, e-mails).
- [x] Un seul bouton principal corail par écran (test sur les écrans principaux, vides et remplis ; contrôle visuel de 43 écrans en 1280 px et 375 px). Les actions qui détruisent sont rouges.
- [x] Les couleurs d'état ne servent jamais à décorer, le corail n'est jamais un état (test : aucun gabarit ne cite le corail).
- [x] Space Grotesk réservée aux titres, au nom et aux chiffres clés ; Inter ailleurs.
- [x] Aucun symbole littéral du spectacle ou du territoire dans l'interface ; le logo est celui du graphiste.
- [x] La mention juridique figure dans les CGU et sur les écrans du contrat et de la facturation.
- [x] Les écrans restent lisibles en 375 px et à faible luminosité (test de contraste de tous les couples de texte).

Reste hors de ce chantier : fichiers vectoriels officiels du logo et version simplifiée du favicon pour 16 px (à demander au graphiste).
