---
name: monks-flow-design
description: >
  Design and build React/JSX pages and components following the Monks Flow 2.0 (MF 2.0) design system.
  Use this skill whenever the user asks to create, build, design, or implement any UI, landing page,
  app screen, component, or interface — even if they don't explicitly mention "Monks Flow" or "design system".
  This skill ensures every output matches the exact visual language of MF 2.0: typography, colors,
  spacing, elevation, and component patterns extracted directly from the Figma UI Library.
---

# Monks Flow 2.0 — Design Skill

This skill produces React/JSX components and pages that faithfully implement the MF 2.0 design system.
Always read `references/tokens.md` before generating any UI output. It contains the ground-truth tokens.

## Workflow

1. Read `references/tokens.md` (design tokens, typography, colors, components)
2. Read `references/components.md` (component patterns and usage rules)
3. Understand the user's request — layout, content, interactivity needed
4. Build the React component using only the tokens and patterns from those references
5. Never invent colors, fonts, spacing, or radii — always use the defined tokens

## Core Design Principles

- **Font**: `Helvetica Now for Monks` for all text — import via `@fontsource` or assume it's globally available
- **Negative tracking**: All headings use negative letter-spacing (`-1%` to `-4%`) — never forget this
- **Two weights only**: `400` (Regular) and `500` (Medium/Text Md) — never use 600 or 700
- **Background**: White (`#FFFFFF`) as default surface; use gradient for hero/cover treatments
- **Elevation**: Use `box-shadow` tokens (Elevation/2, Elevation/4) for cards and floating elements
- **Borders**: Use `rgba(0,0,0,0.12)` for dividers, `rgba(0,0,0,0.19)` for strong borders
- **Accent color**: `#4F24EE` (Plum/600) is the primary brand purple — use for CTAs, active states, highlights
- **Light blue**: `#0F8CF0` is the secondary action color
- **Backgrounds with tint**: `#F1F6FF` for section backgrounds, card surfaces

## Output Format

Always output a single self-contained `.jsx` file. Use Tailwind utility classes where appropriate,
but prefer inline styles for precise token values that Tailwind can't express exactly.
Include all styles inline or in a `<style>` tag within the component file.

## Reference Files

- `references/tokens.md` — All design tokens (colors, typography, spacing, elevation, border radius)
- `references/components.md` — Component anatomy and usage (Buttons, Cards, Navbar, Badges, etc.)