# Step 04: Dashboard Table, Camera CRUD UI, and Filters

**Date:** 2026-10-03  
**Branch:** `step/04-dashboard-crud`  
**Status:** Complete  

## Objectives
Implement the complete camera dashboard, table view, CRUD modals (Add/Edit/Delete), search and location filtering, and dedicated E2E test isolation stack for Camera Monitor without modifying backend application code (`backend/app/*`):

1. **E2E Test Stack Isolation**:
   - In-process Uvicorn runner (`scripts/e2e_backend.py`) running FastAPI on dedicated port `18000` via backend venv Python.
   - Separate test database (`backend/.e2e-data/e2e.db`) with automatic pre-run wiping of `.db`, `-wal`, and `-shm` files.
   - Vite test preview server on dedicated port `15173`.
   - Playwright configured with `workers: 1`, `fullyParallel: false`, and `reuseExistingServer: false`.
   - Port verification helper `assertE2eStack` (`frontend/src/lib/e2e-stack.ts`) and unit test (`e2e-stack.test.ts`) that asserts dedicated e2e ports (18000/15173) and rejects default dev ports (8000/5173).
   - Proven leak-free isolation via back-to-back runs of `python scripts/check.py --e2e` confirming ports are released after runs.

2. **Data Layer, Validation Parity, and API Client**:
   - Single shared vector suite `shared/camera-validation-vectors.json` evaluated against both backend Pydantic (`backend/tests/test_validation_parity.py`) and frontend Zod (`frontend/src/lib/schemas.test.ts`).
   - Resilient frontend API client (`frontend/src/lib/api.ts`) mapping 204 No Content without JSON parsing, 5xx server/proxy HTML errors to kind `"server"`, network failures to kind `"network"`, and schema parsing issues to kind `"invalid-response"`.
   - Form-level error messaging ("Couldn't reach the server. Try again.") and field-level error mapping (`mapServerErrors`).
   - TanStack Query v5 hooks (`frontend/src/features/cameras/queries.ts`) with `isPending` for initial loading, retaining table view during background refetches, and mutation `onSuccess` returning `invalidateQueries` promise.
   - Deterministic timestamp formatting `formatLastChecked` (`frontend/src/features/cameras/utils.ts`) using `Intl.DateTimeFormat.formatToParts` with `hourCycle: "h23"` ensuring 00:00:00 midnight format, DST safety, null timestamp handling ("Never"), and timezone name in tooltip title.
   - Location filter state `string | null` using internal control character sentinel `\x00__ALL__` ensuring locations named "all", "All", and "__ALL__" function as valid distinct locations.

3. **Design System & Semantic Error Tokens**:
   - Textarea primitive via shadcn restyled with design tokens (`border-input-border`, `bg-surface`, `focus-visible:ring-focus`).
   - Added `--color-error` semantic token (`#c81e1e` light / `#ef4444` dark) and `aria-invalid:border-error` across Input, Textarea, and SelectTrigger.
   - Extended `frontend/scripts/verify-css-utilities.mjs` to enforce production build presence for color utilities (`text-error`, `border-error`) and column width tokens.
   - Expanded WCAG AA contrast suite from 39 to 46 measured pairs (+7 pairs including Form Error Text inside dialogs), achieving 100% pass rate in both light and dark modes.

4. **Dashboard Geometry & Component Layout**:
   - Fixed column width design tokens measured at 1280px viewport in Chromium:
     - Status: `--spacing-col-status: 100px;` (measured 85.34px)
     - IP Address: `--spacing-col-ip: 140px;` (measured 129.61px)
     - Last Checked: `--spacing-col-checked: 170px;` (measured 152.72px)
     - Actions: `--spacing-col-actions: 160px;` (measured 151.38px)
     - Table min-width: `--spacing-table-min: 1080px;`
     - Description: `w-3/12` (widest flexible column, sharing remaining width with Name ~120px and Location ~120px).
   - Non-truncating table wrapped in an `overflow-x-auto` container, ensuring horizontal scrolling inside the table container without document body overflow at narrow viewports (e.g. 1024px).
   - Toolbar with search input, location select dropdown, singular/plural camera count line ("Showing 1 of 1 camera", "Showing X of Y cameras"), and disabled controls on 0 cameras.
   - Pure text empty state ("No cameras yet. Add your first camera to start monitoring.") with no duplicate Add button.

5. **Dialogs, Interaction Locks, and Focus Management**:
   - `CameraFormDialog.tsx`: Modal form for adding and editing cameras.
   - Snapshot on open: State initialized from camera snapshot, immunizing typed input from background refetches.
   - Dirty fields payload: `PATCH` sends only dirty fields.
   - IP change warning: Discloses reset of monitoring state when IP is changed; automatically clears if reverted to original IP.
   - Interaction locks: While mutation request is pending, Escape, overlay clicks, Cancel, and close buttons are inert.
   - Explicit focus management: Focus returns to toolbar Add button on add, row Edit button on edit/cancel, and next/prev row or Add button on delete.

---

## Checkpoint Summary
- [x] **Checkpoint 1 (Documentation & Housekeeping)**: Updated `docs/roadmap.md` and `docs/backlog.md`.
- [x] **Checkpoint 2 (E2E Stack & Isolation)**: `scripts/e2e_backend.py`, `frontend/src/lib/e2e-stack.ts`, `frontend/src/lib/e2e-stack.test.ts`, `frontend/playwright.config.ts`, `scripts/check.py --e2e`.
- [x] **Checkpoint 3 (Data Layer, Vectors & Parity)**: `shared/camera-validation-vectors.json`, `backend/tests/test_validation_parity.py`, `frontend/src/lib/schemas.test.ts`, `frontend/src/lib/api.ts`, `frontend/src/features/cameras/utils.ts`, `frontend/src/features/cameras/queries.ts`.
- [x] **Checkpoint 4 (Textarea, Error State & Contrast)**: `frontend/src/components/ui/textarea.tsx`, `--color-error` token, `verify-css-utilities.mjs` extension, Styleguide specimen, and expanded 46-pair WCAG AA contrast suite.
- [x] **Checkpoint 5 (Dashboard Table & Layout Geometry)**: Measured column widths, tokenized widths in `index.css`, `CameraToolbar.tsx`, `CameraTable.tsx`, `DashboardPage.tsx`.
- [x] **Checkpoint 6 (CRUD Dialogs & Focus Management)**: `CameraFormDialog.tsx`, `DeleteCameraDialog.tsx`, focus restoration wiring on `DashboardPage.tsx`.
- [x] **Checkpoint 7 (Testing & Verification)**: Vitest unit/integration tests in `Dashboard.test.tsx` (13 tests) and Playwright E2E tests in `cameras.spec.ts`.
- [x] **Checkpoint 8 (ADR & Step Review)**: ADR 0005 (`docs/adr/0005-frontend-data-layer.md`), `docs/steps/step-04.md`, `README.md`, `docs/roadmap.md`.
