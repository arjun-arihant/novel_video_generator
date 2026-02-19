---
description: Design system for the Aurora theme - Dark, glassmorphic, and premium UI components.
---

# Aurora Design System

> "Where logic meets luminescence."

**Aurora** is a premium, high-fidelity design system focused on deep aesthetics, glassmorphism, and vibrant, energy-based interactions. It creates interfaces that feel "alive" through subtle glows, smooth transitions, and profound depth.

## Core Design Philosophy

1.  **Deepest Void**: Backgrounds are never just black. They are deep, rich charcoals (`#0F0F12`) that provide a stage for light.
2.  **Luminescence**: Interactive elements glow. Light is used to indicate state and focus.
3.  **Glass Physics**: Surfaces are translucent, blurring what's behind them to create layout depth.
4.  **Kinetic Type**: Typography is bold and structural (`Clash Display`) paired with clean functional text (`Inter`).

## Design Tokens (Strict)

### Palette

| Token | Value | Role |
|-------|-------|------|
| `bg-primary` | `#0F0F12` | Main application background (Deep Charcoal) |
| `bg-secondary` | `#18181B` | Sidebar / Secondary panels |
| `surface` | `#18181B` | Card backgrounds (often with opacity) |
| `primary` | `#8B5CF6` | Main action color (Violet) |
| `primary-hover` | `#7C3AED` | Hover state for primary |
| `secondary` | `#F59E0B` | Accent/Warning (Amber) |
| `accent` | `#06B6D4` | tech/Info (Cyan) |
| `text-main` | `#FAFAFA` | Primary reading text |
| `text-muted` | `#A1A1AA` | Secondary text |
| `border-subtle` | `#27272A` | Subtle dividers |
| `border-highlight`| `rgba(139, 92, 246, 0.3)` | Active borders |

### Typography

-   **Headings**: `Clash Display`, sans-serif. Weights: 600 (Semibold), 500 (Medium).
    -   `h1`: 3rem (48px)
    -   `h2`: 2.25rem (36px)
    -   `h3`: 1.5rem (24px)
-   **Body**: `Inter`, sans-serif. Weights: 400 (Regular), 500 (Medium).
    -   `body`: 1rem (16px)
    -   `small`: 0.875rem (14px)
-   **Mono**: `JetBrains Mono`, monospace.

### Effects

-   **Glass**: `background: rgba(24, 24, 27, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08);`
-   **Glow**: `box-shadow: 0 0 20px rgba(139, 92, 246, 0.15);`
-   **Card Radius**: `1rem` (16px).
-   **Btn Radius**: `0.75rem` (12px).
-   **Transition**: `all 0.3s cubic-bezier(0.4, 0, 0.2, 1)`.

## Component Library

### 1. Aurora Card
Glass-morphic panel with subtle border. Used for all main content containers.
```css
.aurora-card {
  background: rgba(24, 24, 27, 0.6);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
```

### 2. Primary Button
Glowing violet button with hover lift.
```css
.aurora-btn {
  background: #8B5CF6;
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 0.75rem;
  font-weight: 500;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.3);
  transition: all 0.2s ease;
}
.aurora-btn:hover {
  background: #7C3AED;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
}
.aurora-btn:disabled {
  background: #27272A;
  color: #71717A;
  box-shadow: none;
  cursor: not-allowed;
  transform: none;
}
```

### 3. Gradient Text
For high-impact headers (h1, hero titles).
```css
.aurora-text-gradient {
  background: linear-gradient(135deg, #FAFAFA 0%, #A1A1AA 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  color: transparent;
}
```

### 4. Input Fields
Dark, subtle inputs that glow on focus.
```css
.aurora-input {
  background: rgba(24, 24, 27, 0.5);
  border: 1px solid #27272A;
  color: #FAFAFA;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  font-family: 'Inter', sans-serif;
  transition: all 0.2s ease;
}
.aurora-input:focus {
  outline: none;
  border-color: #8B5CF6;
  box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.15);
}
```

## Layout Patterns

-   **Dashboard Shell**: Fixed Sidebar (Width: `280px`) + Fluid Content Area.
-   **Content Container**: Max-width `1200px` centered.
-   **Grid**: 12-column grid system with `1.5rem` gaps.
