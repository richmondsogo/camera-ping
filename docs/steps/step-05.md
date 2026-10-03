# Step 05: CSV Import, Export, and Template

**Date:** 2026-10-03  
**Branch:** `step/05-csv-import-export`  
**Status:** Complete

## Summary

1. Implemented backend endpoints: `GET /api/cameras/import/template`, `GET /api/cameras/export`, and `POST /api/cameras/import?dry_run=...` with 1 MiB streaming limit, UTF-8-sig BOM support, strict 4-column schema, line tracking via `csv.reader.line_num`, 100-error limit, and 409 conflict handling.
2. Created `shared/sample-cameras-30.csv` containing 30 realistic RFC 5737 camera records and documented CSV rules in `docs/csv-format.md`.
3. Added 23 backend unit tests in `backend/tests/test_csv_import_export.py` verifying template output, streaming limits without Content-Length, multiline row tracking, batch insertion, and concurrent duplicate guards.
4. Updated frontend Zod schemas and API client to accept number/string `loc` arrays and `total_errors` in error responses while supporting preview and confirmation modes.
5. Built `ImportCamerasDialog` featuring template download, instant dry-run validation, line-by-line error tables, preview table, NotReadableError recovery (e.g. locked in Excel), and focus restoration.
6. Added Import and Export buttons to `CameraToolbar` with Export disabled during loading, errors, or 0 cameras.
7. Enhanced `frontend/e2e/contrast.spec.ts` to output formatted tables only on failure or when `CONTRAST_REPORT=1`.
8. Added 10 Vitest tests in `ImportCamerasDialog.test.tsx` and 2 Playwright E2E tests validating 30-row sample import and export roundtrip.
