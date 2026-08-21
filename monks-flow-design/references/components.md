# MF 2.0 — Component Patterns

Extracted from the Figma UI Library component pages. Use these patterns faithfully.

---

## Navbar

- Height: ~64px, full width
- Background: `#FFFFFF` with `border-bottom: 1px solid rgba(0,0,0,0.12)`
- Contains: workspace logo/avatar (left), nav items (center or left), action icons (right)
- Nav items use `Body/Medium` or `Title/Medium` text
- Active item: `color: #4F24EE` (plum/700)
- Use `Elevation/2` shadow when scrolled

```jsx
const Navbar = () => (
  <nav style={{
    height: 64, display: 'flex', alignItems: 'center',
    padding: '0 24px', background: '#fff',
    borderBottom: '1px solid rgba(0,0,0,0.12)',
    position: 'sticky', top: 0, zIndex: 100
  }}>
    {/* Logo */}
    {/* Nav links */}
    {/* Actions */}
  </nav>
);
```

---

## Buttons

### Standard Button

Three sizes: Large (h=48), Medium (h=40), Small (h=32)
Border radius: `12px` (md) for Large/Medium, `8px` for Small
Font: Button/* tokens (500 weight, -1% tracking)

**Variants:**

| Variant | Background | Text | Border |
|---------|-----------|------|--------|
| Primary (filled) | `#4F24EE` | `#fff` | none |
| Secondary | `transparent` | `#4F24EE` | `1px solid #4F24EE` |
| Tertiary / Ghost | `rgba(0,0,0,0.05)` | `#3C3C3E` | none |
| Destructive | `#FF245B` | `#fff` | none |
| Light Blue | `#0F8CF0` | `#fff` | none |

```jsx
// Primary Large
<button style={{
  height: 48, padding: '0 24px',
  background: '#4F24EE', color: '#fff',
  border: 'none', borderRadius: 12,
  fontSize: 16, fontWeight: 500, letterSpacing: '-0.01em',
  fontFamily: "'Helvetica Now for Monks', Helvetica, sans-serif",
  cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 8
}}>
  Label
</button>
```

### Glass Button

Used for actions on gradient/image backgrounds:
- Background: `rgba(255,255,255,0.15)` with `backdrop-filter: blur(12px)`
- Border: `1px solid rgba(255,255,255,0.3)`
- Text: `#fff`
- Border radius: `12px`

### Icon Button

Square, same height as corresponding size.
- Large: 48×48, radius 12
- Medium: 40×40, radius 10
- Small: 32×32, radius 8

---

## Cards

### Standard Card

```jsx
<div style={{
  background: '#fff',
  borderRadius: 16,
  border: '1px solid rgba(0,0,0,0.08)',
  boxShadow: '0px 2px 7px 0px rgba(0,0,0,0.1)',
  padding: 24,
  overflow: 'hidden'
}}>
  {/* Card content */}
</div>
```

### Task Card (used in dashboards/app views)
- Compact, 16px padding
- Status badge top-right
- Uses `Title/Medium` for title, `Body/Small` for metadata
- Subtle left border accent for status color

### Agent / Feature Card
- Larger, hero-like
- Often has gradient or tinted background
- Image/illustration top, content below
- Radius: 24px

---

## Badges

Small status indicators. Always use pill shape (`border-radius: 999px`).

| Variant | Background | Text |
|---------|-----------|------|
| Default | `#F2F2F2` | `#49494B` |
| Blue | `#E7F3FD` | `#0A62A8` |
| Plum | `#F0ECFE` | `#4F24EE` |
| Green | `#E3FCF1` | `#06A25F` |
| Orange | `#FEEEDC` | `#AF5F03` |
| Red | `#FFEBF0` | `#A30029` |

```jsx
<span style={{
  display: 'inline-flex', alignItems: 'center', gap: 4,
  padding: '2px 10px',
  borderRadius: 999,
  background: '#F0ECFE', color: '#4F24EE',
  fontSize: 12, fontWeight: 500, lineHeight: '16px'
}}>
  Label
</span>
```

---

## Tags / Chips

Similar to badges but interactive (can be toggled/removable).
- Radius: 8px (square-ish, not pill)
- Height: 28px–32px
- Border: `1px solid rgba(0,0,0,0.12)`
- Background: `#fff` (default), `#F0ECFE` (selected/plum)

---

## Text Fields / Inputs

```jsx
<div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
  <label style={{ fontSize: 12, fontWeight: 500, color: '#3C3C3E' }}>Label</label>
  <input style={{
    height: 48, padding: '0 16px',
    background: '#F7F7F7', border: '1px solid rgba(0,0,0,0.12)',
    borderRadius: 12, outline: 'none',
    fontSize: 14, fontWeight: 400, color: '#3C3C3E',
    fontFamily: "'Helvetica Now for Monks', Helvetica, sans-serif"
  }} placeholder="Placeholder" />
</div>
```

On focus: `border-color: #4F24EE`, `background: #fff`

---

## Modals

- Max width: 480px–640px
- Radius: 24px
- Background: `#fff`
- Shadow: `Elevation/4` (`0px 4px 16px rgba(0,0,0,0.1)`)
- Overlay: `rgba(0,0,0,0.4)` backdrop
- Padding: 32px
- Header: `Headline/Medium-Md` title + close icon button

---

## Menu / Dropdown

- Width: ~254px
- Radius: `8px`
- Background: `#fff`
- Border: `1px solid rgba(0,0,0,0.19)`
- Shadow: `Elevation/2`
- Item height: 40px, padding `0 8px`
- Item text: `Body/Medium` (`#3C3C3E`)
- Item hover: `background: #F7F7F7`
- Divider: `1px solid rgba(0,0,0,0.08)`

---

## Chat Input

Used in AI/session interfaces:
- Full width, min-height 56px
- Radius: 16px
- Background: `#fff`
- Border: `1px solid rgba(0,0,0,0.12)`
- Shadow: `Elevation/4`
- Contains textarea + action row (file attach, send button)
- Send button: plum filled circle icon button

---

## Dividers

- `border-bottom: 1px solid rgba(0,0,0,0.12)` (default)
- `border-bottom: 1px solid rgba(0,0,0,0.19)` (strong, between sections)

---

## Layout Patterns

### Landing Page Structure

```
<Navbar />                          ← sticky, white
<HeroSection />                     ← gradient bg, Display/Large headline
<FeaturesSection />                 ← white bg, 3-col grid of cards
<CTASection />                      ← tinted bg (#F1F6FF), centered
<Footer />                          ← dark (#353845 or #3E4150), white text
```

### App/Dashboard Structure

```
<Navrail />                         ← left sidebar, 64px wide collapsed / 240px expanded
<MainContent />                     ← fills remaining width
  <TopBar />                        ← page title + actions
  <ContentGrid />                   ← cards, tables, widgets
```

### Section Anatomy

```jsx
<section style={{ padding: '80px 0', background: '#fff' }}>
  <div style={{ maxWidth: 1160, margin: '0 auto', padding: '0 24px' }}>
    {/* Section label (Badge/tag, optional) */}
    {/* Headline/Large or Display/Small title */}
    {/* Body/Large subtitle */}
    {/* Content grid or card array */}
  </div>
</section>
```

---

## Avatars

- Sizes: 24, 32, 40, 48, 56, 64, 80px
- Radius: 50% (circle) for people, 8–12px for workspace logos
- Fallback: initials on tinted background

---

## Toggle / Switch

- Height: 28px, width: 52px pill shape
- Off: `background: #E4E4E5`
- On: `background: #4F24EE`
- Knob: white circle, 24px, with `Elevation/2`

---

## Checkboxes & Radio Buttons

- Size: 20×20px
- Border: `1.5px solid rgba(0,0,0,0.3)` (unchecked)
- Checked fill: `#4F24EE`
- Check icon: white
- Radio: circle; Checkbox: 4px radius

---

## Snackbar / Toast

- Fixed bottom-center, `z-index: 9999`
- Background: `#3C3C3E`
- Text: `#fff`, `Body/Medium`
- Radius: `12px`
- Padding: `12px 20px`
- Shadow: `Elevation/4`
- Optional action button: plum text on right

---

## Tooltips

- Background: `#3C3C3E` (dark)
- Text: `#fff`, `Body/Small` (12px)
- Radius: `8px`
- Padding: `6px 10px`
- Arrow: 6px triangle pointing to trigger

---

## Table

- Header row: `background: #F7F7F7`, `Body/Small-Md` (12px, 500), `color: rgba(0,0,0,0.5)`
- Data row: white bg, `Body/Medium` (14px, 400)
- Row height: 52px (header 40px)
- Row hover: `background: #F7F7F7`
- Cell padding: `16px`
- Border: `1px solid rgba(0,0,0,0.08)` between rows

---

## Icons

- Library uses custom icon set
- Default size: 20×20px (medium), 16px (small), 24px (large)
- Color: inherits from `Text/Primary` (`#3C3C3E`) or semantic token
- Stroke weight: 1.5px

Use Lucide React icons as substitutes when the exact icon isn't specified:
```jsx
import { ChevronRight, Plus, Search, X } from 'lucide-react'
```

---

## Animation / Motion

- Default transition: `all 0.2s ease`
- Hover scale (cards): `transform: scale(1.01)`
- Button press: `transform: scale(0.98)`
- Modal appear: `opacity 0→1 + translateY(8px→0)`, 200ms ease-out