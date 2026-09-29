# Step 02: Design System and Shell

**Date:** 2026-09-29  
**Branch:** `step/02-design-system`  
**Status:** Complete  

## Objectives
Establish a cohesive, accessible UI foundation and application shell for Camera Monitor:
1. Document the complete visual and design system specifications in `DESIGN.md`.
2. Configure Tailwind CSS v4 design tokens and semantic color variables in `frontend/src/index.css` for both light and dark modes.
3. Build accessible UI primitives using Base UI and class-variance-authority (`Button`, `Badge`, `Input`, `Select`, `Dialog`, `Table`, `StatusIndicator`).
4. Implement utility helper `cn` using `clsx` and `tailwind-merge` v3 (extended with project class groups).
5. Build the application shell (`AppShell`) with semantic navigation and header layout.
6. Build an internal styleguide page (`/_design`) exposing all primitives, variants, states, and design tokens for automated and visual verification.
7. Enforce design token usage with a token linter (`scripts/lint_tokens.py`).
8. Implement automated WCAG 2.1 AA contrast verification in Playwright (`frontend/e2e/contrast.spec.ts`) measuring text, borders, focus rings, and status dots across both modes.
9. Record design and dependency decisions in `docs/adr/0003-ui-foundation.md`.

---

## Checkpoint Progress
- [x] Checkpoint 1: Design documentation (`DESIGN.md` & `docs/adr/0003-ui-foundation.md`)
- [x] Checkpoint 2: Design tokens & CSS theme configuration (`frontend/src/index.css`)
- [x] Checkpoint 3: UI component primitives & utilities (`frontend/src/components/ui/`, `frontend/src/lib/utils.ts`)
- [x] Checkpoint 4: App shell, navigation, and styleguide page (`frontend/src/components/AppShell.tsx`, `frontend/src/pages/StyleguidePage.tsx`)
- [x] Checkpoint 5: Token linter & computed style verification (`scripts/lint_tokens.py`, `frontend/e2e/design-tokens.spec.ts`)
- [x] Checkpoint 6 (Fix 1): ESLint config to allow CVA variant exports (`frontend/eslint.config.js`)
- [x] Checkpoint 7 (Fix 2): Replace `cn` package dependency with `clsx` + `tailwind-merge` v3
- [x] Checkpoint 8 (Fix 3): Automated contrast measurement helper, token fixes, and 38-pair test suite
- [x] Checkpoint 9 (Fix 4): Step documentation and verification

---

## Technical Implementation Details

### 1. Design Tokens and Styling (`frontend/src/index.css`)
- Configured CSS custom properties under `:root` and `.dark` matching modern dark-mode palettes with a single blue accent (`--primary: #2358e1`).
- Enforced strict minimum contrast ratios:
  - Normal text on surfaces: $\ge 4.5:1$
  - Form control borders (`--input`: `#84848a` light / `#5e5e66` dark): $\ge 3:1$
  - Focus rings (`--ring`: `#2358e1` light / `#3b82f6` dark): $\ge 3:1$
  - Status dots (`--status-online`, `--status-offline`, `--status-unknown`): $\ge 3:1$
  - Structural decorative borders (`--border`: `#e4e4e7` light / `#27272a` dark): subtle and exempt from 3:1 to preserve a quiet, non-distracting UI.

### 2. UI Component Primitives
- Built 7 primitive components in `frontend/src/components/ui/`:
  - `Button`: default, secondary, outline, ghost, destructive variants with standard 32px (`h-8`) and compact 28px (`h-7`) sizing.
  - `Badge`: default, secondary, outline, destructive variants.
  - `Input`: text input with styled focus ring and accessible border.
  - `Select`: accessible Base UI Select with styled trigger, content popup, items, and indicators.
  - `Dialog`: accessible modal dialog with backdrop overlay, header, title, description, and close button.
  - `Table`: semantic table wrapper, header, body, row, head, cell with hover row highlighting.
  - `StatusIndicator`: 8px status dot with accessible semantic text label.

### 3. Utility Function `cn` and Dependency Hygiene
- Removed external package `cn@0.4.0` in favor of `clsx@2.1.1` and `tailwind-merge@3.7.0` (Tailwind v4 compatible).
- Configured custom class groups in `extendTailwindMerge`:
  - `font-size`: `['page-title', 'section-heading', 'table']`
  - `rounded`: `['control', 'dialog']`
  - `max-w`: `['page']`
- Confirmed with unit tests (`frontend/src/lib/utils.test.ts`) that conflicting custom classes (e.g. `cn("text-page-title", "text-sm")`) correctly resolve to the latter class.
- Documented in `docs/adr/0003-ui-foundation.md`.

### 4. WCAG 2.1 AA Contrast Helper and Playwright Suite
- Built `frontend/src/lib/contrast.ts` and companion unit tests (`contrast.test.ts`):
  - Canvas 2D context normalization converts all CSS color formats (`rgb`, `rgba`, `hsl`, `oklch`, `color(srgb ...)`) to clean sRGB `[r, g, b, a]`.
  - Layer alpha compositing walks ancestor elements to calculate effective background color on layered semi-transparent elements.
  - Computes WCAG 2.1 relative luminance and contrast ratios.
- Authored `frontend/e2e/contrast.spec.ts` asserting exactly 38 element pairs per mode against contrast thresholds:
  - Light mode: 38/38 pairs pass.
  - Dark mode: 38/38 pairs pass.
- Verified test failure detection: deliberately setting a low-contrast token fails with 16 reported violations and exit code 1.

---

## ELIFECYCLE Investigation

During test executions under Windows, occasional `[ELIFECYCLE] Command failed with exit code 1` messages from Vite can appear if child server processes terminate abruptly or if a test failure triggers process teardown.

To evaluate current process teardown and port cleanliness, `python scripts/check.py --e2e` was executed three consecutive times:

### Run 1
- **Exact Last Lines:**
  ```text
    ok 2 [chromium] › e2e\contrast.spec.ts:597:3 › WCAG 2.1 Contrast Measurements › measures all design system pairs in Dark mode (2.9s)
    ok 3 [chromium] › e2e\design-tokens.spec.ts:4:3 › Design Tokens & Computed Styles Verification › asserts computed styles on /_design match token specifications (1.2s)
    ok 4 [chromium] › e2e\smoke.spec.ts:3:1 › smoke test: renders app shell and navigates between routes (687ms)

    4 passed (16.2s)
  ============================================================
  Camera Monitor - Quality Checks
  Platform: Windows (11)
  ============================================================

  ---> [E2E: Playwright Smoke Test]
       CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run test:e2e
       PASS (18.32s)

  ============================================================
  [PASSED] All checks passed successfully in 18.32s!
  ============================================================
  ```
- **Exit Code:** `0`
- **Port Status (5173, 8000):** Ports are completely free (zero listening sockets; only short-lived TIME_WAIT sockets).

### Run 2
- **Exact Last Lines:**
  ```text
    ok 2 [chromium] › e2e\contrast.spec.ts:597:3 › WCAG 2.1 Contrast Measurements › measures all design system pairs in Dark mode (2.9s)
    ok 3 [chromium] › e2e\design-tokens.spec.ts:4:3 › Design Tokens & Computed Styles Verification › asserts computed styles on /_design match token specifications (1.3s)
    ok 4 [chromium] › e2e\smoke.spec.ts:3:1 › smoke test: renders app shell and navigates between routes (671ms)

    4 passed (16.4s)
  ============================================================
  Camera Monitor - Quality Checks
  Platform: Windows (11)
  ============================================================

  ---> [E2E: Playwright Smoke Test]
       CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run test:e2e
       PASS (18.32s)

  ============================================================
  [PASSED] All checks passed successfully in 18.32s!
  ============================================================
  ```
- **Exit Code:** `0`
- **Port Status (5173, 8000):** Ports are completely free (zero listening sockets).

### Run 3
- **Exact Last Lines:**
  ```text
    ok 2 [chromium] › e2e\contrast.spec.ts:597:3 › WCAG 2.1 Contrast Measurements › measures all design system pairs in Dark mode (2.7s)
    ok 3 [chromium] › e2e\design-tokens.spec.ts:4:3 › Design Tokens & Computed Styles Verification › asserts computed styles on /_design match token specifications (1.2s)
    ok 4 [chromium] › e2e\smoke.spec.ts:3:1 › smoke test: renders app shell and navigates between routes (547ms)

    4 passed (16.3s)
  ============================================================
  Camera Monitor - Quality Checks
  Platform: Windows (11)
  ============================================================

  ---> [E2E: Playwright Smoke Test]
       CMD: C:\Users\Richmond\AppData\Roaming\npm\pnpm.CMD run test:e2e
       PASS (17.76s)

  ============================================================
  [PASSED] All checks passed successfully in 17.76s!
  ============================================================
  ```
- **Exit Code:** `0`
- **Port Status (5173, 8000):** Ports are completely free (zero listening sockets).

**Conclusion on [ELIFECYCLE]:** Across 3 clean passing runs, `[ELIFECYCLE]` did not reproduce when tests pass cleanly, and ports are consistently released. However, because its intermittent appearance under test failure or process abort was not definitively isolated to a specific runtime hook, the root cause is **cause not established**.
