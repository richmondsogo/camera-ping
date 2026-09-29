# Camera Monitor Design System & Visual Specification

**Status:** Active  
**Source of Truth:** [frontend/src/index.css](file:///c:/Users/Richmond/Desktop/Open%20Source%20Projects/camera-ping/frontend/src/index.css)  

---

## 1. Principles & Goals

Camera Monitor is built for an admin PC in an office server room. The design aesthetic is:

> **Modern, minimal, quiet, information-dense, highly consistent.**

The interface prioritizes immediate situational awareness over visual flair. It operates offline on a local intranet without external assets or cloud services.

### Non-Goals (Strictly Prohibited)
- **No cards** unless a specific screen strictly requires contained framing.
- **No hero sections** or marketing banners.
- **No gradients** anywhere in backgrounds, text, or borders.
- **No shadows** except for the dialog modal backdrop/overlay.
- **No dashboard junk** (gauges, metric donuts, filler widgets).
- **No charts** (reachability is tabular and status-oriented).
- **No decorative icons** (icons are used only where functionally necessary for interactive controls).
- **No ad-hoc styles**: no arbitrary utility classes (`[#...]`, `[13px]`, `[32px]`) or raw Tailwind color palettes (`text-gray-500`, `bg-blue-600`) outside the token definitions.

---

## 2. Tokens & Specifications

### 2.1 Typography
The font family is self-hosted Inter variable font via `@fontsource-variable/inter` with robust system fallbacks:
```text
"Inter Variable", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif
```

Semantic typography utilities defined in `frontend/src/index.css`:

| Role | Utility | Font Size | Line Height | Weight | Tabular Numbers |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Page Title** | `text-page-title` | 20px | 28px | 600 (Semibold) | No |
| **Section Heading** | `text-section-heading` | 16px | 24px | 600 (Semibold) | No |
| **Body** | `text-sm` | 14px | 20px | 400 (Regular) | No |
| **Table Text** | `text-table` | 13px | 18px | 400 (Regular) | Yes (`tabular-nums`) |
| **Small / Helper** | `text-xs` | 12px | 16px | 400 (Regular) | No |
| **Numerals / IPs** | `tabular-nums` | Inherit | Inherit | Inherit | Yes |

*Rule:* Page and section headings must use `text-page-title` and `text-section-heading`. Repeated ad-hoc strings like `text-xl font-semibold leading-7` are prohibited.

---

### 2.2 Spacing & Layout
- **Base Grid:** 4px scale (Tailwind base unit: `p-1` = 4px, `p-2` = 8px, `p-3` = 12px, `p-4` = 16px, `p-6` = 24px).
- **Page Container:** Max-width 1200px (`max-w-page`, via `--container-page: 1200px`).
- **Page Padding:** 24px (`p-6` or `px-6`).
- **Layout Alignment:** Left-aligned content within centered container.

---

### 2.3 Controls & Radii
- **Control Heights:**
  - Default: 32px (`h-8`, used for standard buttons, inputs, selects).
  - Small: 28px (`h-7`, used for compact table action buttons or badges).
- **Radii:**
  - Controls: 6px (`rounded-control`, via `--radius-control: 6px`).
  - Dialogs: 8px (`rounded-dialog`, via `--radius-dialog: 8px`).
- **Borders:**
  - 1px solid low-contrast neutral border (`border border-border`).
  - **Single Allowed Exception:** 2px primary accent bottom-border for the active navigation link (`border-b-2 border-primary`).

---

### 2.4 Focus Ring
- **Focus Token:** `--ring` (accent blue).
- **Behavior:** Visible in both light and dark mode on keyboard focus (`focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none focus-visible:ring-offset-1`).

---

### 2.5 Colors & Contrast (WCAG 2.1 AA Compliance)

All color combinations must meet or exceed WCAG 2.1 AA contrast requirements (minimum 4.5:1 for normal text).

#### Neutral Tokens
| Token | Light Mode Value | Dark Mode Value | Usage | Light Contrast | Dark Contrast |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `--background` | `#ffffff` | `#09090b` | Base canvas background | Canvas | Canvas |
| `--foreground` | `#09090b` | `#fafafa` | Primary text | 19.8:1 (vs bg) | 19.2:1 (vs bg) |
| `--muted` | `#f4f4f5` | `#27272a` | Subdued surface / zebra striping | Surface | Surface |
| `--muted-foreground` | `#71717a` | `#a1a1aa` | Secondary / metadata text | 4.88:1 (vs bg) | 7.85:1 (vs bg) |
| `--border` | `#e4e4e7` | `#27272a` | Structural borders | Border | Border |
| `--input` | `#e4e4e7` | `#27272a` | Form control borders | Border | Border |
| `--overlay` | `rgba(0,0,0,0.45)` | `rgba(0,0,0,0.70)` | Dialog modal backdrop | Overlay | Overlay |

#### Accent & Semantic Tokens
| Token | Light Value | Light Contrast | Dark Value | Dark Contrast | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `--primary` | `#2563eb` | 5.17:1 (on white bg) | `#3b82f6` | 5.41:1 (on dark bg) | Single blue accent |
| `--primary-foreground`| `#ffffff` | 5.17:1 (on primary) | `#09090b` | 5.41:1 (on primary) | In dark mode, `#09090b` text guarantees >4.5:1 (white text on `#3b82f6` fails at ~3.7:1) |
| `--destructive` | `#dc2626` | 4.83:1 (on white bg) | `#ef4444` | 5.25:1 (on dark bg) | Error / deletion action |
| `--destructive-foreground` | `#ffffff`| 4.83:1 (on destructive)| `#09090b` | 5.25:1 (on destructive)| High-contrast action text |
| `--ring` | `#2563eb` | Focus ring | `#3b82f6` | Focus ring | 2px focus ring |

#### Status Colors
Status indicators indicate device reachability:
- **Online:** `#16a34a` (light) / `#22c55e` (dark)
- **Offline:** `#dc2626` (light) / `#ef4444` (dark)
- **Unknown:** `#71717a` (light) / `#a1a1aa` (dark)

**Strict Usage Rule for Status:**
Status color is applied **only to the 8px dot** of the `StatusIndicator` component. The accompanying label text always uses standard `--foreground` or `--muted-foreground`. Green and gray status colors fail 4.5:1 text contrast and must never be applied to typography, row backgrounds, or large badges.

---

### 2.6 Navigation Active State Rule
The app shell header navigation must:
- Use semantic `<nav aria-label="Main">`.
- Rely on `NavLink`'s `aria-current="page"` attribute for screen readers.
- Prevent layout shifts: active and inactive links use the exact same font weight (no bolding on active).
- Active state is indicated by an active text color (`text-foreground` vs `text-muted-foreground`) and a 2px bottom border (`border-b-2 border-primary`), which is the sole exception to the 1px border rule.

---

## 3. How to Add a New Token

If a future step requires a new visual token:
1. Define the raw token in `:root` and `.dark` in `frontend/src/index.css`.
2. Map it in `@theme` (e.g., `--color-my-token: var(--my-token)`) or create an `@utility` class if outside standard Tailwind namespaces.
3. Calculate and verify WCAG 2.1 AA contrast ratio (minimum 4.5:1 against its background in both light and dark modes).
4. Document the token name, values, contrast ratios, and rationale in this file (`DESIGN.md`).
5. Run `python scripts/check.py` to ensure it passes the design token linter (`scripts/lint_tokens.py`).
