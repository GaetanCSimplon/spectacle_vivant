# Bòrd Pro — charte graphique appliquée à l'application

Version 1 — 2026-10-21. Source : `Bord_Pro_Charte_marque_brief_developpeur.md` (charte du 15/10/2026). **Elle remplace entièrement** l'identité « Scène » (teal, corail foncé, Sora). Ce document dit comment la charte s'applique au code et ce qui a été décidé là où elle ne tranche pas.

## 1. Nom et ton
- Le produit s'écrit **Bòrd Pro** (avec l'accent, jamais « Bord Pro »). « BÒRD PRO » en capitales disparaît de l'interface. Le menu de la structure reste « Bòrd ».
- Slogan : **Reprenez le contrôle de votre tournée.** Sous-titre : *Contacts, dates, contrats, budgets et équipe : tout au même endroit.* Écran de connexion : *Votre activité, au clair.*
- Ton direct, phrases courtes, verbes d'action, vouvoiement. À éviter : « assistant », « carnet de route », métaphores maritimes, clichés du spectacle.
- Mention à faire figurer dans les CGU et sur les pages contrats et factures : *Bòrd Pro facilite la préparation et le suivi administratif ; il ne remplace pas les obligations légales ni un conseil juridique, social ou comptable personnalisé.*

## 2. Couleurs
Source des valeurs : la charte (couleurs de marque) et `bord-pro.tokens.css` (jetons proposés par l'associé le 2026-10-21 : teintes d'état, bordures, focus, rayons, ombre). **Nous reprenons ses valeurs** ; seules deux valeurs sont ajoutées par nous (corail au survol, série claire des graphiques). Contrastes calculés (WCAG : 4,5:1 pour du texte, 3:1 pour un graphique ou le bord d'un champ).

| Jeton (`--bord-…`) | Valeur | Usage | Contraste |
|---|---|---|---|
| `brand-navy` Bleu Nuit | `#10243F` | titres, texte courant, navigation, liens, focus | 15,6:1 sur blanc, 14,3:1 sur le fond |
| `brand-coral` Corail | `#FF6B5B` | l'action principale d'un écran, éléments actifs | texte bleu nuit dessus : 5,6:1 |
| *(ajouté)* corail au survol | `#F55F4E` | survol du bouton principal | bleu nuit dessus : 4,9:1 |
| `brand-offwhite` Blanc Cassé | `#F7F5F1` | **fond de page** (jamais de blanc pur en fond) | — |
| `surface` | `#FFFFFF` | cartes, champs, menus | bleu nuit : 15,6:1 |
| `brand-slate` Ardoise | `#5B6673` | textes secondaires, libellés, icônes (jamais un long texte principal) | 5,8:1 sur blanc, 5,4:1 sur le fond |
| `brand-green` / `brand-amber` / `brand-red` | `#2FA37C` / `#F2A93B` / `#D64545` | point, bordure ou pastille d'état, **jamais du texte** (menthe 3,2:1, ambre 2,0:1, rouge 4,4:1 sur blanc) | décoratif, toujours avec un libellé |
| `success-text` / `success-bg` | `#176445` / `#E5F3EC` | pastille « confirmé, signé, payé, validé » | 6,2:1 |
| `warning-text` / `warning-bg` | `#714700` / `#FFF1D8` | pastille « option, en attente, échéance » | 7,2:1 |
| `danger-text` / `danger-bg` | `#A52D2D` / `#FCEAEA` | erreur, retard, action destructrice | 6,0:1 |
| `border` | `#D8DDE3` | filets entre blocs et contour des cartes (décoratif) | — |
| `control-border` | `#768292` | contour des champs de formulaire | 3,9:1 sur blanc |
| `focus` | `#10243F` | anneau de focus : 3 px, décalé de 3 px | 14,3:1 |
| *(ajouté)* série claire (graphique) | `#838E9B` | dépenses dans les graphiques (la recette est en bleu nuit) | 3,3:1 sur blanc |

Les trois couleurs d'état sont **fonctionnelles** : jamais décoratives, et le corail n'est jamais un état d'erreur ou d'alerte. Une couleur ne porte jamais seule le sens : un libellé ou un symbole l'accompagne.

L'échelle `blue-*` de Tailwind, déjà employée partout pour « la couleur de la marque », est redéfinie autour du bleu nuit (`blue-700` = `#10243F`) : un changement dans `css/source.css` recolore tout, sans toucher aux gabarits. Les jetons `--bord-*` sont repris tels quels dans `css/source.css`.

## 3. Décisions d'accessibilité (validées le 2026-10-21)
1. **Bouton principal : corail avec texte bleu nuit.** Le texte blanc sur corail n'atteint que 2,8:1.
2. **Liens : bleu nuit souligné.** Un lien corail sur fond clair n'atteint que 2,6:1.
3. **États : texte foncé sur teinte claire** (jetons de l'associé, tous au-dessus de 6:1), car les couleurs de la charte seules ne sont pas lisibles en texte. Un **test automatique de contraste** vérifie chaque couple du tableau ci-dessus.
4. **Statuts :** « confirmé », « signé », « payé » en vert (la charte réserve le vert à la validation) ; « option » et « en attente » en ambre ; retards et erreurs en rouge ; « annulé » en gris ardoise. « Confirmée » et « Signée » restent distinguées par leur libellé et leur nuance (teinte claire contre plein). Le bleu n'est plus une couleur d'état.

## 4. Typographie, formes, icônes
- **Space Grotesk** (Medium, SemiBold) pour les titres, le nom et les chiffres clés ; **Inter** (Regular, Medium) pour tout le reste : champs, boutons, tableaux, textes longs. Deux familles seulement, **hébergées chez nous** (`static/fonts/`, licence libre), sans fournisseur externe.
- Échelle : H1 40 px / H2 28 px / H3 20 px / corps 16 px / libellés 14 px / mentions 12–13 px. Sur téléphone, les titres sont réduits pour tenir en 375 px.
- Rayons : **8 px** pour les boutons et les champs, **12 px** pour les cartes, forme de pilule pour les pastilles d'état seulement (les boutons ne sont plus des pilules). Ombre très discrète : `0 4px 16px rgb(16 36 63 / 6%)`. Beaucoup d'espace. L'échelle d'espacement de l'associé (4, 8, 12, 16, 24, 32, 48, 64 px) est celle de Tailwind : rien à changer.
- Focus visible : anneau bleu nuit de 3 px, décalé de 3 px.
- **Navigation :** colonne fixe à gauche à partir de 1024 px (demande de l'associé, 2026-10-21) ; en dessous, barre du haut avec menu burger. Page active : bleu nuit avec une barre corail.
- Icônes : trait de 1,5 à 2 px, angles arrondis, `currentColor`. Pas de micro, note de musique, rideau ni guitare.
- **Une seule action principale (corail) par écran.**
- Les PDF de contrat, de devis et de facture sont les documents de l'utilisateur : ils **ne reprennent pas** l'habillage de la marque.

## 5. Logo
Fichiers fournis par le graphiste, déposés dans `static/brand/`. Règles : ne jamais déformer ni recolorer ; zone de protection = hauteur du « B » ; monogramme 16 px minimum, logo horizontal 120 px de large minimum ; fond blanc cassé ou bleu nuit.

## 6. Hors périmètre de ce chantier
La section « Priorisation fonctionnelle » de la charte (pipeline de diffusion, CRM complet, contrats CDDU et checklist GUSO, budget prévisionnel contre réel, rôles collaboratifs) n'est pas un sujet d'habillage : elle est enregistrée comme **Q19** dans le cahier des charges, rien n'est codé. Pas de mode sombre : « lisibles en faible luminosité » est traité par les contrastes ci-dessus.

## 7. Plan de livraison (Sprint 3.14)
1. Documentation (ce document, Q19, `CLAUDE.md`).
2. Fondations du thème : polices, jetons, fond, arrondis, boutons, en-tête, échelle typographique, test de contraste.
3. Nom, logo, slogan et messages : titres des pages, en-tête, favicon, connexion, inscription, écrans vides, e-mails.
4. États et icônes : statuts des dates, des paiements et de Bòrd, graphiques, icônes en trait.
5. Mention juridique, relevé des écrans à plusieurs boutons principaux, checklist de cohérence, vérification visuelle en 1280 px et 375 px.

## 8. Checklist de cohérence avant publication
- [ ] Le nom est écrit « Bòrd Pro », avec accent, partout dans l'interface.
- [ ] Le slogan est « Reprenez le contrôle de votre tournée ».
- [ ] Un seul bouton principal corail par écran.
- [ ] Les couleurs d'état ne servent jamais à décorer, le corail n'est jamais un état.
- [ ] Space Grotesk réservée aux titres et à la marque, Inter ailleurs.
- [ ] Aucun symbole littéral du spectacle ou du territoire dans le logo et les illustrations.
- [ ] La mention juridique figure dans les CGU et sur les pages contrats et factures.
- [ ] Les écrans restent lisibles en 375 px et à faible luminosité (test de contraste vert).
