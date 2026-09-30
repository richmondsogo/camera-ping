# Step 02b: Design Refinement

**Date:** 2026-09-29  
**Branch:** `step/02b-design-refinement`  
**Status:** Complete  

## Objectives
Execute design refinements across the frontend design system based on owner feedback following Step 02 review:
1. **Fix Screenshot Script Timing & Theme Toggle Synchronization**: Resolve mid-transition color captures by disabling CSS transitions/animations during screenshot capture, switching themes via the styleguide's own toggle button so the toggle label and `.dark` class agree, and awaiting network idle, font loading, and settle timeout.
2. **Generous Semantic Spacing Tokens**: Implement a dedicated token per role (strict 1:1 mapping, no token reuse across unrelated roles even when values match). Update `@theme` in `frontend/src/index.css` and document the full token-to-role map in `DESIGN.md`.
3. **No Dead Tokens & Built Utility Verification**: Ensure every defined token is used by a component. Verify after `pnpm build` that every spacing/size utility used in `src/` exists in the built CSS bundle with a non-zero selector count.
4. **Tailwind Merge Configuration**: Extend `tailwind-merge` v3 in `src/lib/utils.ts` so custom spacing tokens are recognized in spacing-based groups (`padding`, `margin`, `gap`, `height`, `width`, `size`) and `w-dialog` in the `width` group. Add comprehensive conflict-resolution unit tests in `src/lib/utils.test.ts`.
5. **Primitive Restyling**:
   - **Select**: Unalign trigger popup (`alignItemWithTrigger: false`), drop popup 4px below trigger (`sideOffset: 4`), apply 4px container padding (`p-popup-pad`), 32px item min-height (`min-h-8`), 12px item horizontal padding (`px-control-x`), and 2px flex container gap (`gap-item-gap`) without per-item margins.
   - **Ghost Button**: Subdued `bg-transparent text-muted-foreground` at rest; subtle `hover:bg-muted hover:text-foreground` on hover. Retain standard focus ring.
   - **Small Button**: 28px height (`h-7`) with exactly 12px horizontal padding (`px-control-x`).
   - **Table**: 6-column dashboard contract (`Camera Name`, `Location`, `Description`, `IP Address`, `Status`, `Last Checked`) with fixed layout (`table-fixed`), explicit fraction column widths (2/12, 2/12, 4/12, 2/12, 1/12, 1/12), generous row heights (header 40px, body 48px), 16px cell horizontal padding (`px-cell-x`), and inside-cell text truncation with ellipsis and full text `title` attribute.
   - **Dialog**: 480px width (`w-dialog`), 24px padding (`p-dialog-pad`), responsive max-width 90vw on narrow viewports.
   - **Navigation**: Clean 4px link gap (`gap-1`), 12px horizontal padding (`px-control-x`).
   - **AppShell**: 56px header height (`h-header`), 32px page gutter (`px-gutter`), 1200px page max-width (`max-w-page`), 40px section spacing (`pt-section`), 64px container bottom padding (`pb-container-bottom`). Left alignment between header brand and page titles.
6. **Styleguide & Specimen Updates**: Realistic select options (30s, 1m, 2m, 5m, 10m), realistic 6-row sample table with RFC 5737 IPs (192.0.2.10–15), and two full layout specimens (Dashboard Page Composition and Settings Form).
7. **Contrast Verification**: Update WCAG 2.1 AA contrast suite (`frontend/e2e/contrast.spec.ts`) with literal expected pair count increased from 38 to 39 by adding `Table: Description cell text`.
8. **Computed-Style Test Assertions**: Add 18 exact computed-style assertions in `frontend/e2e/design-tokens.spec.ts` covering row heights, paddings, margins, alignment, dialog sizing, select popup offsets, item gaps, and text truncation.

---

## Checkpoint Progress
- [x] **Checkpoint 1**: Screenshot timing fix, mid-transition evidence, and "before" state capture (`frontend/scripts/screenshots.mjs`, `frontend/screenshots/before/`)
- [x] **Checkpoint 2**: Semantic spacing tokens, tailwind-merge spacing extension, unit tests, AppShell spacing, and `DESIGN.md` documentation (`frontend/src/index.css`, `frontend/src/lib/utils.ts`, `frontend/src/lib/utils.test.ts`, `frontend/src/components/AppShell.tsx`, `DESIGN.md`)
- [x] **Checkpoint 3**: Primitive component restyling (`button.tsx`, `select.tsx`, `table.tsx`, `input.tsx`, `dialog.tsx`, `badge.tsx`, `StatusIndicator.tsx`, `AppShell.tsx`)
- [x] **Checkpoint 4**: Styleguide page specimens update and contrast test suite update (N: 38 -> 39, `frontend/src/pages/StyleguidePage.tsx`, `frontend/e2e/contrast.spec.ts`)
- [x] **Checkpoint 5**: Computed-style spacing assertions (`frontend/e2e/design-tokens.spec.ts`)
- [x] **Checkpoint 6**: CSS utility proof, documentation, "after" screenshot capture, and full test verification

---

## Technical Implementation Details

### 1. Mid-Transition Timing Investigation (Amendment 1)
To verify the hypothesis that previous screenshots captured colors mid-transition during dark mode toggling:
- An empirical comparison script ran the old screenshot logic against the settled screenshot logic under identical code:
  - **Old Script (t = 50ms without transition suppression)**:
    - Ghost button text color: `rgb(51, 51, 53)` (interpolating between `#71717a` and dark text `#fafafa`).
    - Secondary button background: `rgb(208, 208, 209)` (interpolating between `#f4f4f5` and `#27272a`).
    - Outline button border: `rgb(203, 203, 207)` (interpolating between `#84848a` and `#5e5e66`).
    - Input border: `rgb(203, 203, 207)`.
  - **New Settled Script (transitions suppressed, toggle button clicked, 200ms settle)**:
    - Ghost button text color: `rgb(250, 250, 250)` (`#fafafa`).
    - Secondary button background: `rgb(39, 39, 42)` (`#27272a`).
    - Outline button border: `rgb(94, 94, 102)` (`#5e5e66`).
    - Input border: `rgb(94, 94, 102)`.
- **Conclusion**: The mid-transition theory was empirically confirmed. Suppressing transitions/animations via an injected style tag and clicking the styleguide's native toggle button ensures rock-solid, settled visual and color captures.

### 2. Semantic Spacing Tokens (`frontend/src/index.css`)
Sixteen semantic tokens were defined in `@theme` using a strict one-token-per-role discipline:

| Token Name | Value | Role |
| :--- | :--- | :--- |
| `--spacing-button-x` | `16px` | Button horizontal padding (default size) |
| `--spacing-cell-x` | `16px` | Table cell horizontal padding (header and body) |
| `--spacing-control-x` | `12px` | Control horizontal padding (input, select trigger, select item, nav link, small button) |
| `--spacing-inline` | `12px` | Inline gap between controls in a row |
| `--spacing-dialog-pad` | `24px` | Modal dialog interior padding |
| `--spacing-stack` | `24px` | Vertical spacing between form fields, sections, and title-to-content |
| `--spacing-toolbar` | `16px` | Gap between toolbar control groups |
| `--spacing-header` | `56px` | App shell header height |
| `--spacing-gutter` | `32px` | App shell horizontal page container padding |
| `--spacing-section` | `40px` | App shell vertical padding above main content |
| `--spacing-container-bottom` | `64px` | App shell bottom clearance padding |
| `--spacing-tight` | `8px` | Compact element gap and internal padding |
| `--spacing-popup-pad` | `4px` | Popup menu / dropdown interior padding |
| `--spacing-item-gap` | `2px` | Vertical gap between items in a dropdown popup |
| `--spacing-row-header` | `40px` | Table header row height |
| `--spacing-row-body` | `48px` | Table body row height |

Additionally, `@utility w-dialog { width: 480px; max-width: 90vw; }` was defined.

### 3. Built CSS Utility Proof (Amendment 5)
Every single spacing/size utility used in `frontend/src` was scanned and verified against `frontend/dist/assets/*.css` after `pnpm build`:

| Utility | Selector Count in Built CSS | Status |
| :--- | :--- | :--- |
| `gap-inline` | 1 | PASS |
| `gap-item-gap` | 1 | PASS |
| `gap-stack` | 1 | PASS |
| `gap-tight` | 1 | PASS |
| `gap-toolbar` | 1 | PASS |
| `h-header` | 1 | PASS |
| `h-row-body` | 1 | PASS |
| `h-row-header` | 1 | PASS |
| `mt-stack` | 1 | PASS |
| `p-dialog-pad` | 1 | PASS |
| `p-popup-pad` | 1 | PASS |
| `pb-container-bottom` | 1 | PASS |
| `pt-section` | 1 | PASS |
| `px-button-x` | 1 | PASS |
| `px-cell-x` | 1 | PASS |
| `px-control-x` | 1 | PASS |
| `px-gutter` | 1 | PASS |
| `px-tight` | 1 | PASS |
| `w-dialog` | 1 | PASS |

Zero dead tokens and zero missing utilities.

### 4. Custom Tailwind-Merge Configuration (`frontend/src/lib/utils.ts`)
Extended `extendTailwindMerge` with project spacing tokens across all spacing-dependent groups:
```typescript
const customSpacingTokens = [
  'button-x', 'cell-x', 'control-x', 'inline', 'dialog-pad',
  'stack', 'toolbar', 'header', 'gutter', 'section',
  'container-bottom', 'tight', 'popup-pad', 'item-gap',
  'row-header', 'row-body',
];

export const cn = (...inputs: ClassValue[]): string => {
  return customTwMerge(clsx(inputs));
};
```
Verified with unit tests in `frontend/src/lib/utils.test.ts`:
- `cn("px-gutter", "px-4")` $\rightarrow$ `"px-4"`
- `cn("px-button-x", "px-control-x")` $\rightarrow$ `"px-control-x"`
- `cn("h-8", "h-row-body")` $\rightarrow$ `"h-row-body"`
- `cn("gap-tight", "gap-inline")` $\rightarrow$ `"gap-inline"`
- `cn("w-dialog", "w-full")` $\rightarrow$ `"w-full"`

### 5. Table Layout & Truncation Specification
The dashboard table adheres to a 6-column contract with fixed table layout (`table-fixed`) and exact width fractions:
- **Camera Name**: 2/12 (`w-2/12`)
- **Location**: 2/12 (`w-2/12`)
- **Description**: 4/12 (`w-4/12`) - widest flexible column
- **IP Address**: 2/12 (`w-2/12`)
- **Status**: 1/12 (`w-1/12`)
- **Last Checked**: 1/12 (`w-1/12`)

Cells wrap text content in `<div className="truncate" title={fullText}>{fullText}</div>`. Truncation was verified by measuring `scrollWidth > clientWidth` on the long-description row while short descriptions remain untruncated.

### 6. Contrast Suite Update (N: 38 $\rightarrow$ 39)
- **Old Pair Count**: 38 pairs per mode.
- **New Pair Count**: 39 pairs per mode.
- **Added Pair**: `Table: Description cell text` (`[data-testid="table-cell-description"]`, threshold $\ge 4.5:1$).
- **Removed Pairs**: None.
- All 39 pairs pass WCAG 2.1 AA in both Light (39/39) and Dark (39/39) modes.

---

## Screenshot Artifacts (Amendment 20)

Before and after screenshot captures are saved in `frontend/screenshots/before/` and `frontend/screenshots/after/`:

| Specimen | Light Mode (Before / After) | Dark Mode (Before / After) |
| :--- | :--- | :--- |
| **Select Open** | `before/select-open-light.png`<br>`after/select-open-light.png` | `before/select-open-dark.png`<br>`after/select-open-dark.png` |
| **Dialog Open** | `before/dialog-open-light.png`<br>`after/dialog-open-light.png` | `before/dialog-open-dark.png`<br>`after/dialog-open-dark.png` |
| **Six-Column Table & Page Composition** | `before/design-light.png`<br>`after/design-light.png` | `before/design-dark.png`<br>`after/design-dark.png` |
| **Button Focused** | `before/button-focused-light.png`<br>`after/button-focused-light.png` | `before/button-focused-dark.png`<br>`after/button-focused-dark.png` |
| **Dashboard Route** | `before/dashboard-light.png`<br>`after/dashboard-light.png` | `before/dashboard-dark.png`<br>`after/dashboard-dark.png` |
| **Settings Route** | `before/settings-light.png`<br>`after/settings-light.png` | `before/settings-dark.png`<br>`after/settings-dark.png` |

---

## Verification Evidence

### 1. Unified Quality Check (`python scripts/check.py`)
```text
============================================================
Camera Monitor - Quality Checks
Platform: Windows (11)
============================================================

---> [Backend: Ruff Linter]
     CMD: C:\Users\Richmond\Desktop\Open Source Projects\camera-ping\backend\.venv\Scripts\ruff.exe check .
     PASS (0.16s)

---> [Backend: Mypy Strict Typecheck]
     CMD: C:\Users\Richmond\Desktop\Open Source Projects\camera-ping\backend\.venv\Scripts\mypy.exe .
     PASS (0.43s)

---> [Backend: Pytest Unit Tests]
     CMD: C:\Users\Richmond\Desktop\Open Source Projects\camera-ping\backend\.venv\Scripts\pytest.exe -v
     PASS (0.42s)

---> [Frontend: ESLint]
     CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run lint
     PASS (1.00s)

---> [Frontend: Prettier Formatting Check]
     CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run format:check
     PASS (0.28s)

---> [Frontend: TypeScript Typecheck]
     CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run typecheck
     PASS (1.11s)

---> [Frontend: Vitest Unit Tests]
     CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run test:unit --run
     PASS (1.81s)

============================================================
[PASSED] All checks passed successfully in 5.22s!
```

### 2. End-to-End Suite (`python scripts/check.py --e2e`)
```text
============================================================
Camera Monitor - Quality Checks
Platform: Windows (11)
============================================================

---> [E2E: Playwright Smoke Test]
     CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run test:e2e
     Running 4 tests using 1 worker
     ok 1 [chromium] › e2e\contrast.spec.ts:597:3 › WCAG 2.1 Contrast Measurements › measures all design system pairs in Light mode (2.9s)
     ok 2 [chromium] › e2e\contrast.spec.ts:597:3 › WCAG 2.1 Contrast Measurements › measures all design system pairs in Dark mode (2.8s)
     ok 3 [chromium] › e2e\design-tokens.spec.ts:4:3 › Design Tokens & Computed Styles Verification › asserts computed styles on /_design match token specifications (1.2s)
     ok 4 [chromium] › e2e\smoke.spec.ts:3:1 › smoke test: renders app shell and navigates between routes (712ms)

     4 passed (15.8s)
     PASS (17.92s)

============================================================
[PASSED] All checks passed successfully in 17.92s!
```

### 3. Token Linter (`python scripts/lint_tokens.py`)
```text
Checking frontend files for hardcoded design values...
Scan complete. 0 violations found.
```
