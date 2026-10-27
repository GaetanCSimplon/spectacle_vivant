# BRD PRO — Design tokens CSS

**Version :** 1.0  
**Date :** 26.10.2026  
**Usage :** référence d’intégration pour le développeur. Centraliser toutes les valeurs visuelles dans des variables CSS.

## 1. Couleurs de marque

```css
:root {
  --color-night: #10243F;      /* Structure, navigation, titres */
  --color-coral: #FF695B;      /* Action principale, carte de synthèse */
  --color-ocean: #007299;      /* Bloc d’information, repère de parcours */
  --color-white: #FFFFFF;      /* Fond général, lecture */
  --color-cream: #F5F2EA;      /* Document, information secondaire */
  --color-light-blue: #E2F1F6; /* Contexte discret, jamais fond dominant */
}
```

## 2. Couleurs d’état

```css
:root {
  --color-success: #1F6B4A; /* Confirmé / à suivre */
  --color-warning: #E3A21A; /* Problème / attention */
  --color-danger: #8E1F3F;  /* Erreur / blocage */
}
```

Un statut doit toujours associer un pictogramme et un mot. La couleur ne doit jamais être le seul signal.

## 3. Texte et séparations

```css
:root {
  --color-text-primary: var(--color-night);
  --color-text-secondary: #465A6C;
  --color-border: #C4CFDA;
}
```

## 4. Typographies

```css
:root {
  --font-display: "Archivo", sans-serif;       /* Titres */
  --font-body: "Instrument Sans", sans-serif;  /* Corps et interface */
  --font-data: "IBM Plex Mono", monospace;     /* Données, montants, dates */

  --font-weight-display: 800;
  --font-weight-body-regular: 400;
  --font-weight-body-medium: 500;
  --font-weight-body-semibold: 600;
  --font-weight-body-bold: 700;
  --font-weight-data: 450;

  --font-data-feature: "tnum"; /* Chiffres tabulaires */
}
```

## 5. Échelle typographique

```css
:root {
  --text-page-title-size: 30px;
  --text-page-title-line-height: 34px;

  --text-card-title-size: 18px;
  --text-card-title-line-height: 24px;

  --text-body-size: 16px;
  --text-body-line-height: 24px;

  --text-label-size: 14px;
  --text-label-line-height: 20px;

  --text-data-important-size: 24px;
  --text-data-important-line-height: 40px;
}
```

## 6. Espacements

Base d’espacement : **4 px**.

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
}
```

## 7. Formes et contrôles

```css
:root {
  --radius-control: 12px;   /* Boutons, champs, petites cartes */
  --radius-card: 16px;      /* Cartes */
  --radius-card-large: 24px;
  --radius-section: 28px;   /* Sections / blocs larges */

  --target-touch: 48px;     /* Cible tactile minimale */
}
```

## 8. Icônes

```css
:root {
  --icon-size: 24px;
  --icon-stroke: 2px;
}
```

## 9. Assets SVG

Adapter les chemins selon l’arborescence du projet.

```css
:root {
  --logo-symbol: "assets/ICON_FD-TRANSPARENT.svg";
  --logo-app: "assets/LOGO_FD-TRANSPARENT.svg";
  --logo-radar: "assets/ICON_RADAR.svg";
  --logo-cream-background: "assets/LOGO_FD-CAPSULE_CREME.svg";

  --logo-min-size: 32px;
  --radar-min-size: 36px;
  --logo-clear-space: 50%;
}
```

## 10. Base typographique

```css
body {
  margin: 0;
  background-color: var(--color-white);
  color: var(--color-text-primary);
  font-family: var(--font-body);
  font-size: var(--text-body-size);
  line-height: var(--text-body-line-height);
  -webkit-font-smoothing: antialiased;
}

h1,
h2,
h3 {
  font-family: var(--font-display);
  font-weight: var(--font-weight-display);
  letter-spacing: 0.04em;
  color: var(--color-text-primary);
  text-align: left;
}

h1 {
  font-size: var(--text-page-title-size);
  line-height: var(--text-page-title-line-height);
}

h2 {
  font-size: var(--text-card-title-size);
  line-height: var(--text-card-title-line-height);
}

.data,
.amount,
.date-value {
  font-family: var(--font-data);
  font-weight: var(--font-weight-data);
  font-variant-numeric: var(--font-data-feature);
}

.data-important {
  font-size: var(--text-data-important-size);
  line-height: var(--text-data-important-line-height);
}
```

## 11. Boutons

Une seule action principale par vue.

```css
.btn-primary,
.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--target-touch);
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-control);
  font-family: var(--font-body);
  font-weight: var(--font-weight-body-semibold);
  cursor: pointer;
}

.btn-primary {
  background-color: var(--color-coral);
  color: var(--color-night); /* Obligatoire */
  border: none;
}

.btn-secondary {
  background-color: var(--color-white);
  color: var(--color-night);
  border: 2px solid var(--color-night);
}

.btn-primary:focus-visible,
.btn-secondary:focus-visible {
  outline: 3px solid var(--color-ocean);
  outline-offset: 2px;
}
```

## 12. Cartes et blocs

```css
.card {
  background-color: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: var(--space-5);
}

.card-highlight {
  background-color: var(--color-coral);
  color: var(--color-night);
  border-radius: var(--radius-card);
  padding: var(--space-5);
}

.info-block {
  background-color: var(--color-ocean);
  color: var(--color-white);
  border-radius: var(--radius-card);
  padding: var(--space-5);
}

.secondary-block {
  background-color: var(--color-cream);
  color: var(--color-text-primary);
  border-radius: var(--radius-card);
  padding: var(--space-5);
}

.discreet-context {
  background-color: var(--color-light-blue);
  color: var(--color-text-primary);
  border-radius: var(--radius-control);
  padding: var(--space-4);
}
```

Les cartes corail ne sont pas automatiquement cliquables.

## 13. Navigation

```css
.navigation {
  background-color: var(--color-night);
  color: var(--color-white);
}

.navigation__item--active {
  color: var(--color-coral);
  font-weight: var(--font-weight-body-bold);
}
```

## 14. Statuts

```css
.status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-control);
  font-size: var(--text-label-size);
  font-weight: var(--font-weight-body-semibold);
}

.status--confirmed {
  color: var(--color-success);
  border: 1px solid currentColor;
}

.status--warning {
  color: var(--color-warning);
  border: 1px solid currentColor;
}

.status--danger {
  color: var(--color-danger);
  border: 1px solid currentColor;
}
```

## 15. Formulaires

```css
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field__label {
  font-size: var(--text-label-size);
  line-height: var(--text-label-line-height);
  font-weight: var(--font-weight-body-semibold);
  color: var(--color-text-primary);
}

.field__input {
  min-height: var(--target-touch);
  padding: var(--space-3);
  background-color: var(--color-white);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  font-family: var(--font-body);
  font-size: var(--text-body-size);
}

.field__input:focus-visible {
  outline: 3px solid var(--color-ocean);
  outline-offset: 2px;
}

.field--error .field__input {
  border-color: var(--color-danger);
}

.field__error {
  color: var(--color-danger);
  font-size: var(--text-label-size);
}
```

## 16. RADAR

```css
.radar-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--radar-min-size);
  height: var(--radar-min-size);
  border-radius: 50%;
  background-color: var(--color-coral);
  color: var(--color-night);
  font-family: var(--font-data);
  font-weight: var(--font-weight-data);
}
```

Sur mobile, le RADAR se place en bas à droite, au-dessus de la navigation, sans masquer l’action principale.

## 17. Contrastes

| Association | Ratio | Règle |
|---|---:|---|
| Nuit sur corail | 5.51 | Autorisé. Texte de bouton corail toujours bleu nuit |
| Blanc sur océan | 5.43 | Autorisé pour les blocs d’information |
| Corail sur crème | 2.53 | Interdit pour du texte utile |

## 18. Interdits

- Glow, ombre floue décorative ou dégradé décoratif.
- Logo recoloré, déformé, filtré ou recadré.
- Version monochrome non fournie.
- Texte utile en corail sur crème.
- Statut ou contrôle identifié uniquement par la couleur.
- Valeurs visuelles en dur : utiliser les tokens CSS.
