# MF 2.0 — Design Tokens

Extracted from: https://www.figma.com/design/hVKNd1TNmfgDDXkIXXKQrg/MF-2.0-UI-LIBRARY

---

## Typography

**Font Family**: `'Helvetica Now for Monks', Helvetica, Arial, sans-serif`
**Weights**: 400 (Regular), 500 (Medium — called "Text Md" in Figma)

### Type Scale

| Token | Size | Line Height | Weight | Letter Spacing |
|-------|------|-------------|--------|----------------|
| Display/Large | 57px | 64px (1.12) | 400 | -4% |
| Display/Medium | 40px | 48px (1.2) | 400 | -4% |
| Display/Small | 36px | 44px (1.22) | 400 | -4% |
| Headline/Large | 32px | 40px (1.25) | 400 | -4% |
| Headline/Large-Md | 32px | 40px (1.25) | 500 | -4% |
| Headline/Medium | 24px | 32px (1.33) | 400 | -4% |
| Headline/Medium-Md | 24px | 32px (1.33) | 500 | -4% |
| Headline/Small | 20px | 28px (1.4) | 400 | -4% |
| Headline/Small-Md | 20px | 24px (1.2) | 500 | -4% |
| Title/Large | 16px | 24px (1.5) | 500 | -1% |
| Title/Medium | 14px | 20px (1.43) | 500 | -1% |
| Title/Small | 14px | 20px (1.43) | 500 | 0.71% (uppercase labels) |
| Body/Large | 16px | 24px (1.5) | 400 | -1% |
| Body/Large-Md | 16px | 24px (1.5) | 500 | -1% |
| Body/Medium | 14px | 20px (1.43) | 400 | -1% |
| Body/Medium-Md | 14px | 20px (1.43) | 500 | -1% |
| Body/Small | 12px | 16px (1.33) | 400 | 0 |
| Body/Small-Md | 12px | 16px (1.33) | 500 | 0 |
| Label/Large | 16px | 24px (1.5) | 400 | -1% |
| Label/Small | 12px | 16px (1.33) | 400/500 | 0 |
| Button/Large | 16px | 24px (1.5) | 500 | -1% |
| Button/Medium | 14px | 20px (1.43) | 500 | -1% |
| Button/Small | 12px | 16px (1.33) | 500 | 0 |

### CSS Helper (use this in components)

```css
/* Paste these as JS style objects or CSS vars */
--font-family: 'Helvetica Now for Monks', Helvetica, Arial, sans-serif;

/* Display */
--text-display-lg: { fontSize: 57, lineHeight: '64px', fontWeight: 400, letterSpacing: '-0.04em' }
--text-display-md: { fontSize: 40, lineHeight: '48px', fontWeight: 400, letterSpacing: '-0.04em' }
--text-display-sm: { fontSize: 36, lineHeight: '44px', fontWeight: 400, letterSpacing: '-0.04em' }

/* Headline */
--text-headline-lg: { fontSize: 32, lineHeight: '40px', fontWeight: 400, letterSpacing: '-0.04em' }
--text-headline-md: { fontSize: 24, lineHeight: '32px', fontWeight: 400, letterSpacing: '-0.04em' }
--text-headline-sm: { fontSize: 20, lineHeight: '28px', fontWeight: 400, letterSpacing: '-0.04em' }

/* Title */
--text-title-lg: { fontSize: 16, lineHeight: '24px', fontWeight: 500, letterSpacing: '-0.01em' }
--text-title-md: { fontSize: 14, lineHeight: '20px', fontWeight: 500, letterSpacing: '-0.01em' }

/* Body */
--text-body-lg: { fontSize: 16, lineHeight: '24px', fontWeight: 400, letterSpacing: '-0.01em' }
--text-body-md: { fontSize: 14, lineHeight: '20px', fontWeight: 400, letterSpacing: '-0.01em' }
--text-body-sm: { fontSize: 12, lineHeight: '16px', fontWeight: 400, letterSpacing: 0 }

/* Button */
--text-btn-lg: { fontSize: 16, lineHeight: '24px', fontWeight: 500, letterSpacing: '-0.01em' }
--text-btn-md: { fontSize: 14, lineHeight: '20px', fontWeight: 500, letterSpacing: '-0.01em' }
--text-btn-sm: { fontSize: 12, lineHeight: '16px', fontWeight: 500, letterSpacing: 0 }
```

---

## Color Palette

### Semantic / Surface Tokens

| Token | Value | Usage |
|-------|-------|-------|
| Surface/Contrast | `#FFFFFF` | Primary background, cards |
| Surface/Gradient/Gradient1 | `linear-gradient(101deg, #CFE8FC 0%, #ECF4FE 16%, #F7F6FE 52%, #FAF6FD 87%, #FFF3F6 100%)` | Hero, cover backgrounds |
| Text/Primary | `#3C3C3E` | Body text, default text |
| Text/Contrast | `#FFFFFF` | Text on dark/colored backgrounds |
| Border/Strong | `rgba(0, 0, 0, 0.19)` | Card borders, section dividers |
| Border/Default | `rgba(0, 0, 0, 0.12)` | Subtle dividers |

### Elevation / Shadows

| Token | Value |
|-------|-------|
| Elevation/2 | `box-shadow: 0px 2px 7px 0px rgba(0, 0, 0, 0.1)` |
| Elevation/4 | `box-shadow: 0px 4px 16px 0px rgba(0, 0, 0, 0.1)` |

### Brand Colors (Primitive Palette)

**Blue (Primary action, lightBlue)**
| Step | Hex |
|------|-----|
| 50 | `#E7F3FD` |
| 100 | `#CFE8FC` |
| 200 | `#9FD1F9` |
| 300 | `#6FBAF6` |
| 400 | `#3FA3F3` |
| 500 | `#0F8CF0` ← **primary light blue action** |
| 600 | `#0D7ED8` |
| 700 | `#0A62A8` |
| 800 | `#095490` |
| 900 | `#074678` ← dark blue |

**Plum / Purple (Brand accent)**
| Step | Hex |
|------|-----|
| 50 | `#F7F6FE` |
| 100 | `#F0ECFE` |
| 200 | `#E1D9FC` |
| 300 | `#D2C6FB` |
| 400 | `#BFAFF9` |
| 500 | `#A892F7` |
| 600 | `#7252E9` |
| 700 | `#4F24EE` ← **primary brand accent** |
| 800 | `#3B11D5` |
| 900 | `#2A0C97` |
| 950 | `#220A7B` |

**Indigo**
| Step | Hex |
|------|-----|
| 500 | `#3F51B5` |
| 700 | `#303F9F` |
| 900 | `#1A237E` |

**Orange**
| Step | Hex |
|------|-----|
| 50 | `#FFF8F0` |
| 500 | `#FB961F` |
| 700 | `#AF5F03` |

**Green / Fern**
| Step | Hex |
|------|-----|
| 50 | `#E8F5E9` |
| 500 | `#4CAF50` |
| 700 | `#388E3C` |

**Red / Ruby**
| Step | Hex |
|------|-----|
| 50 | `#FFF3F6` |
| 300 | `#FFA8BE` |
| 500 | `#FF245B` |
| 700 | `#A30029` |

**Grey (Steel)**
| Step | Hex |
|------|-----|
| 50 | `#F4F4F6` |
| 100 | `#E8E9ED` |
| 200 | `#D1D2DB` |
| 300 | `#BDBFCC` |
| 400 | `#A6A9BA` |
| 500 | `#8F92A8` |
| 600 | `#787C96` |
| 700 | `#656982` |
| 800 | `#52566A` |
| 900 | `#3E4150` |
| 950 | `#353845` |

**Neutral Grey**
| Step | Hex |
|------|-----|
| 50 | `#F7F7F7` |
| 100 | `#F2F2F2` |
| 200 | `#E4E4E5` |
| 300 | `#CECECF` |
| 400 | `#B6B6B9` |
| 500 | `#A1A1A5` |
| 600 | `#8A8A8E` |
| 700 | `#737378` |
| 800 | `#5D5D60` |
| 900 | `#49494B` |

**Tonal/Tinted Surfaces (use for colored section backgrounds)**
| Color | Pastel | Tinted |
|-------|--------|--------|
| Blue | `#F1F6FF` | `#CFE8FC` |
| Plum | `#F7F6FE` | `#E1D9FC` |
| Green | `#F1FDF8` | `#E3FCF1` |
| Orange | `#FFF8F0` | `#FEEEDC` |
| Red | `#FFF3F6` | `#FFEBF0` |

---

## Spacing

The system uses an 8pt base grid. Common values:

| Token | Value |
|-------|-------|
| xs | 4px |
| sm | 8px |
| md | 16px |
| lg | 24px |
| xl | 32px |
| 2xl | 40px |
| 3xl | 48px |
| 4xl | 64px |
| section | 80px–120px |

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| sm | 8px | Small chips, tags |
| md | 12px | Default cards, inputs |
| lg | 16px | Cards, panels |
| xl | 24px | Large panels, artboards |
| 2xl | 40px | Full design system frames |
| pill | 999px | Badge pills, toggle buttons |

---

## Grid / Layout

- **Desktop container**: 1160px max-width, centered
- **Column gutter**: 16px
- **Section padding**: 64px vertical, 24px–40px horizontal
- **Card padding**: 16px–24px internal