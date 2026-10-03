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
- **Base Grid:** 4px base scale.
- **Page Container:** Max-width 1200px (`max-w-page`, via `--container-page: 1200px`), 32px side padding (`px-gutter`), 40px top padding (`pt-section`), 64px bottom padding (`pb-container-bottom`).
- **Header:** Height 56px (`h-header`), 32px side padding (`px-gutter`), 24px brand-to-nav gap (`gap-stack`), 12px link padding (`px-control-x`), 4px link gap (`gap-1`).
- **Layout Alignment:** Left-aligned content within centered container. Brand left edge aligns identically with page titles.
- **Section & Layout Spacing:**
  - Between major sections: 40px (`gap-section`, `space-y-section`).
  - Page title to first content: 24px (`gap-stack`, `space-y-stack`).
  - Toolbar to table: 16px (`gap-toolbar`, `space-y-toolbar`).
  - Controls row gap: 12px (`gap-inline`).
  - Button groups: 8px (`gap-tight`).
  - Icon-to-label gap: 8px (`gap-tight`).
  - Form spacing: label to control 8px (`gap-tight`), field to field 24px (`space-y-stack`), helper text 8px below control.
- **Table Dimensions:**
  - Header row: 40px (`h-row-header`).
  - Body row: 48px (`h-row-body`).
  - Cell horizontal padding: 16px (`px-cell-x`).
  - Typography: 13px / 18px (`text-table`).
  - Long descriptions truncate with ellipsis and title attribute.
- **Controls & Buttons:**
  - Default button (32px): horizontal padding 16px (`px-button-x`).
  - Small button (28px): horizontal padding 12px (`px-control-x`).
  - Form input and select trigger: horizontal padding 12px (`px-control-x`), height 32px (`h-8`).
- **Select Popup:**
  - Padding: 4px (`p-popup-pad`).
  - Offset below trigger: 4px (`sideOffset={4}`).
  - Min-width: equal to trigger width (`min-w-[var(--anchor-width)]`).
  - Items: min-height 32px (`min-h-8`), horizontal padding 12px (`px-control-x`), 2px vertical gap (`gap-item-gap`).
  - Radius: 8px (`rounded-dialog`), border: 1px (`border border-border`), shadow: none (`shadow-none`).
- **Dialog:**
  - Interior padding: 24px (`p-dialog-pad`).
  - Header to body: 16px (`gap-toolbar`).
  - Body to footer: 24px (`gap-stack`).
  - Footer buttons gap: 8px (`gap-tight`).
  - Dimensions: width 480px, max 90vw (`w-dialog`).
- **Badge & Status:**
  - Badge horizontal padding: 8px (`px-tight`).
  - Status indicator: 8px dot (`size-2`), 8px gap to label (`gap-tight`).

#### Semantic Spacing Token to Role Map
| Token | Value | Role | Generated Utility Examples |
| :--- | :--- | :--- | :--- |
| `--spacing-header` | 56px | App shell header height | `h-header` |
| `--spacing-gutter` | 32px | Page container side padding | `px-gutter` |
| `--spacing-section` | 40px | Major section gap & page top padding | `pt-section`, `space-y-section`, `gap-section` |
| `--spacing-container-bottom` | 64px | Page container bottom padding | `pb-container-bottom` |
| `--spacing-stack` | 24px | Title-to-content, field-to-field, dialog body-to-footer | `gap-stack`, `space-y-stack` |
| `--spacing-dialog-pad` | 24px | Dialog interior padding | `p-dialog-pad` |
| `--spacing-toolbar` | 16px | Toolbar-to-table, dialog header-to-body | `gap-toolbar`, `space-y-toolbar` |
| `--spacing-button-x` | 16px | Default button horizontal padding | `px-button-x` |
| `--spacing-cell-x` | 16px | Table cell horizontal padding | `px-cell-x` |
| `--spacing-row-header` | 40px | Table header row height | `h-row-header` |
| `--spacing-row-body` | 48px | Table body row height | `h-row-body` |
| `--spacing-control-x` | 12px | Horizontal padding for inputs, selects, nav links, small buttons | `px-control-x` |
| `--spacing-inline` | 12px | Gap between controls in a row / toolbar | `gap-inline` |
| `--spacing-tight` | 8px | Button groups, icon gap, label gap, helper text, badge px, status gap | `gap-tight`, `space-y-tight`, `px-tight` |
| `--spacing-popup-pad` | 4px | Select popup container padding | `p-popup-pad` |
| `--spacing-item-gap` | 2px | Vertical gap between items in select popup list | `gap-item-gap` |
| `--spacing-col-status` | 100px | Fixed column width: Status indicator & text | `w-col-status` |
| `--spacing-col-ip` | 140px | Fixed column width: Longest IPv4 address | `w-col-ip` |
| `--spacing-col-checked` | 170px | Fixed column width: Full ISO timestamp | `w-col-checked` |
| `--spacing-col-actions` | 160px | Fixed column width: Edit & Delete button group | `w-col-actions` |
| `--spacing-table-min` | 1000px | Minimum table width in horizontal scroll wrapper | `min-w-table-min` |

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

All color combinations must meet or exceed WCAG 2.1 AA contrast requirements (minimum 4.5:1 for normal text, 3:1 for control borders, status dots, and focus rings). Decorative borders are exempt and kept subtle (low-contrast).

#### Token Values
| Token | Light Value | Dark Value | Usage |
| :--- | :--- | :--- | :--- |
| `--background` | `#ffffff` | `#09090b` | Base canvas background |
| `--foreground` | `#09090b` | `#fafafa` | Primary text |
| `--muted` | `#f4f4f5` | `#27272a` | Subdued surface / secondary fill |
| `--muted-foreground` | `#71717a` | `#a1a1aa` | Secondary / metadata text |
| `--border` | `#e4e4e7` | `#27272a` | Structural borders (decorative, low-contrast) |
| `--input` | `#84848a` | `#5e5e66` | Form control borders (>= 3:1) |
| `--ring` | `#2358e1` | `#3b82f6` | 2px focus ring (>= 3:1) |
| `--primary` | `#2358e1` | `#2358e1` | Primary blue accent fill |
| `--primary-foreground`| `#ffffff` | `#ffffff` | Text on primary button/badge |
| `--destructive` | `#c81e1e` | `#c81e1e` | Error / destructive fill |
| `--destructive-foreground` | `#ffffff`| `#ffffff`| Text on destructive button/badge |
| `--error` | `#c81e1e` | `#ef4444` | Form error text and invalid input borders (>= 4.5:1 text, >= 3:1 border) |
| `--overlay` | `rgba(0,0,0,0.45)` | `rgba(0,0,0,0.70)` | Dialog modal backdrop |
| `--status-online` | `#16a34a` | `#22c55e` | Reachable camera status dot |
| `--status-offline` | `#dc2626` | `#ef4444` | Unreachable camera status dot |
| `--status-unknown` | `#71717a` | `#a1a1aa` | Unchecked camera status dot |

#### Measured Contrast Ratios (WCAG 2.1 AA)

Measured via automated headless browser tests (`frontend/e2e/contrast.spec.ts`) using sRGB canvas normalization and layer alpha compositing:

##### Light Mode Measurements
| Element / Pair | Foreground | Background | Measured Ratio | Threshold | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Button: Default | `#ffffff` | `#2358e1` | **5.91:1** | 4.5:1 | PASS |
| Button: Default (hover) | `#e9eefc` | `#2358e1` | **5.09:1** | 4.5:1 | PASS |
| Button: Secondary | `#09090b` | `#f4f4f5` | **18.1:1** | 4.5:1 | PASS |
| Button: Secondary (hover) | `#09090b` | `#f6f6f7` | **18.42:1** | 4.5:1 | PASS |
| Button: Outline | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Button: Outline (hover) | `#09090b` | `#f4f4f5` | **18.1:1** | 4.5:1 | PASS |
| Button: Outline border | `#84848a` | `#ffffff` | **3.72:1** | 3:1 | PASS |
| Button: Ghost | `#71717a` | `#ffffff` | **4.83:1** | 4.5:1 | PASS |
| Button: Ghost (hover) | `#09090b` | `#f4f4f5` | **18.1:1** | 4.5:1 | PASS |
| Button: Destructive | `#ffffff` | `#c81e1e` | **5.74:1** | 4.5:1 | PASS |
| Button: Destructive (hover) | `#fae9e9` | `#c81e1e` | **4.89:1** | 4.5:1 | PASS |
| Badge: Default | `#ffffff` | `#2358e1` | **5.91:1** | 4.5:1 | PASS |
| Badge: Secondary | `#09090b` | `#f4f4f5` | **18.1:1** | 4.5:1 | PASS |
| Badge: Outline | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Badge: Destructive | `#ffffff` | `#c81e1e` | **5.74:1** | 4.5:1 | PASS |
| Input: Value text | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Input: Placeholder text | `#71717a` | `#ffffff` | **4.83:1** | 4.5:1 | PASS |
| Input: Border | `#84848a` | `#ffffff` | **3.72:1** | 3:1 | PASS |
| Textarea: Value text | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Textarea: Placeholder text | `#71717a` | `#ffffff` | **4.83:1** | 4.5:1 | PASS |
| Textarea: Border | `#84848a` | `#ffffff` | **3.72:1** | 3:1 | PASS |
| Form: Error text | `#c81e1e` | `#ffffff` | **5.74:1** | 4.5:1 | PASS |
| Form: Invalid border | `#c81e1e` | `#ffffff` | **5.74:1** | 3:1 | PASS |
| Select: Trigger text | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Select: Trigger border | `#84848a` | `#ffffff` | **3.72:1** | 3:1 | PASS |
| Select: Popup item text | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Select: Popup item (highlighted) | `#09090b` | `#f4f4f5` | **18.1:1** | 4.5:1 | PASS |
| Dialog: Trigger button | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Dialog: Content text | `#71717a` | `#ffffff` | **4.83:1** | 4.5:1 | PASS |
| Form: Error text (inside dialog) | `#c81e1e` | `#ffffff` | **5.74:1** | 4.5:1 | PASS |
| Dialog: Overlay backdrop | `#8c8c8c` | `#ffffff` | **3.36:1** | 1:1 (Exempt) | PASS |
| Typography: Foreground text | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Typography: Muted-foreground text | `#71717a` | `#ffffff` | **4.83:1** | 4.5:1 | PASS |
| Table: Header text | `#71717a` | `#ffffff` | **4.83:1** | 4.5:1 | PASS |
| Table: Cell text | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Table: Description cell text | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Table: Row hover cell text | `#09090b` | `#f9f9fa` | **18.91:1** | 4.5:1 | PASS |
| Navigation: Active link | `#09090b` | `#ffffff` | **19.9:1** | 4.5:1 | PASS |
| Navigation: Inactive link | `#71717a` | `#ffffff` | **4.83:1** | 4.5:1 | PASS |
| Focus Ring: Button | `#2358e1` | `#ffffff` | **5.91:1** | 3:1 | PASS |
| Focus Ring: Input | `#2358e1` | `#ffffff` | **5.91:1** | 3:1 | PASS |
| Textarea: Focus ring | `#2358e1` | `#ffffff` | **5.91:1** | 3:1 | PASS |
| Focus Ring: Select | `#2358e1` | `#ffffff` | **5.91:1** | 3:1 | PASS |
| Status: Online dot | `#16a34a` | `#ffffff` | **3.3:1** | 3:1 | PASS |
| Status: Offline dot | `#dc2626` | `#ffffff` | **4.83:1** | 3:1 | PASS |
| Status: Unknown dot | `#71717a` | `#ffffff` | **4.83:1** | 3:1 | PASS |

##### Dark Mode Measurements
| Element / Pair | Foreground | Background | Measured Ratio | Threshold | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Button: Default | `#ffffff` | `#2358e1` | **5.91:1** | 4.5:1 | PASS |
| Button: Default (hover) | `#e9eefc` | `#2358e1` | **5.09:1** | 4.5:1 | PASS |
| Button: Secondary | `#fafafa` | `#27272a` | **14.27:1** | 4.5:1 | PASS |
| Button: Secondary (hover) | `#fafafa` | `#212124` | **15.39:1** | 4.5:1 | PASS |
| Button: Outline | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Button: Outline (hover) | `#fafafa` | `#27272a` | **14.27:1** | 4.5:1 | PASS |
| Button: Outline border | `#5e5e66` | `#09090b` | **3.1:1** | 3:1 | PASS |
| Button: Ghost | `#a1a1aa` | `#09090b` | **7.76:1** | 4.5:1 | PASS |
| Button: Ghost (hover) | `#fafafa` | `#27272a` | **14.27:1** | 4.5:1 | PASS |
| Button: Destructive | `#ffffff` | `#c81e1e` | **5.74:1** | 4.5:1 | PASS |
| Button: Destructive (hover) | `#fae9e9` | `#c81e1e` | **4.89:1** | 4.5:1 | PASS |
| Badge: Default | `#ffffff` | `#2358e1` | **5.91:1** | 4.5:1 | PASS |
| Badge: Secondary | `#fafafa` | `#27272a` | **14.27:1** | 4.5:1 | PASS |
| Badge: Outline | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Badge: Destructive | `#ffffff` | `#c81e1e` | **5.74:1** | 4.5:1 | PASS |
| Input: Value text | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Input: Placeholder text | `#a1a1aa` | `#09090b` | **7.76:1** | 4.5:1 | PASS |
| Input: Border | `#5e5e66` | `#09090b` | **3.1:1** | 3:1 | PASS |
| Textarea: Value text | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Textarea: Placeholder text | `#a1a1aa` | `#09090b` | **7.76:1** | 4.5:1 | PASS |
| Textarea: Border | `#5e5e66` | `#09090b` | **3.1:1** | 3:1 | PASS |
| Form: Error text | `#ef4444` | `#09090b` | **5.29:1** | 4.5:1 | PASS |
| Form: Invalid border | `#ef4444` | `#09090b` | **5.29:1** | 3:1 | PASS |
| Select: Trigger text | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Select: Trigger border | `#5e5e66` | `#09090b` | **3.1:1** | 3:1 | PASS |
| Select: Popup item text | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Select: Popup item (highlighted) | `#fafafa` | `#27272a` | **14.27:1** | 4.5:1 | PASS |
| Dialog: Trigger button | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Dialog: Content text | `#a1a1aa` | `#09090b` | **7.76:1** | 4.5:1 | PASS |
| Form: Error text (inside dialog) | `#ef4444` | `#09090b` | **5.29:1** | 4.5:1 | PASS |
| Dialog: Overlay backdrop | `#030303` | `#09090b` | **1.04:1** | 1:1 (Exempt) | PASS |
| Typography: Foreground text | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Typography: Muted-foreground text | `#a1a1aa` | `#09090b` | **7.76:1** | 4.5:1 | PASS |
| Table: Header text | `#a1a1aa` | `#09090b` | **7.76:1** | 4.5:1 | PASS |
| Table: Cell text | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Table: Description cell text | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Table: Row hover cell text | `#fafafa` | `#19191b` | **16.82:1** | 4.5:1 | PASS |
| Navigation: Active link | `#fafafa` | `#09090b` | **19.06:1** | 4.5:1 | PASS |
| Navigation: Inactive link | `#a1a1aa` | `#09090b` | **7.76:1** | 4.5:1 | PASS |
| Focus Ring: Button | `#3b82f6` | `#09090b` | **5.41:1** | 3:1 | PASS |
| Focus Ring: Input | `#3b82f6` | `#09090b` | **5.41:1** | 3:1 | PASS |
| Textarea: Focus ring | `#3b82f6` | `#09090b` | **5.41:1** | 3:1 | PASS |
| Focus Ring: Select | `#3b82f6` | `#09090b` | **5.41:1** | 3:1 | PASS |
| Status: Online dot | `#22c55e` | `#09090b` | **8.73:1** | 3:1 | PASS |
| Status: Offline dot | `#ef4444` | `#09090b` | **5.29:1** | 3:1 | PASS |
| Status: Unknown dot | `#a1a1aa` | `#09090b` | **7.76:1** | 3:1 | PASS |

#### Strict Usage Rule for Status
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
