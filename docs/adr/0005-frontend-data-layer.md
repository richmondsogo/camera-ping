# 5. Frontend Data Layer, Table Column Geometry, and E2E Isolation

Date: 2026-10-03

## Context
Step 04 requires reliable client-side data management, resilient error handling, non-truncating tabular display, and leak-free E2E test isolation without mutating backend application code.

## Decision
- TanStack Query v5 manages camera caching and invalidations (`isPending` for initial loading, retaining table on background refetch; mutation invalidation returned in `onSuccess`).
- Strict Zod validation parses API response schemas; network and proxy errors map to user-friendly messages while field validation errors map directly to form inputs.
- Shared validation vector file (`shared/camera-validation-vectors.json`) executed across Vitest and pytest ensures strict frontend-backend rule parity.
- Fixed column widths via design tokens (`w-col-status`, `w-col-ip`, `w-col-checked`, `w-col-actions`) and minimum table width (`min-w-table-min: 1080px`) inside an `overflow-x-auto` container eliminate cell truncation while preserving page container bounds.
- Isolated E2E stack runs on dedicated ports (18000/15173) with a wiped test database (`backend/.e2e-data/e2e.db`), guarded by port checks, single-worker execution, and in-process uvicorn.

## Consequences & Cost
- Eliminates test pollution and port collisions between local development servers and automated test suites.
- Requires snapshotting entity state on dialog open to prevent background refetches from overwriting active form typing.
- Preserves full WCAG AA contrast compliance (46 measured pairs across light and dark modes).
