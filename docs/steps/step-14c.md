# Step 14c: Installer Runtime Resilience & Pre-Flight Validation

**Date:** 2026-10-09  
**Branch:** `step/14c-installer-fixes`  
**Status:** In Progress  

## Overview
Step 14c hardens the offline installer and maintenance PowerShell scripts against argument parsing edge cases, variable collisions with PowerShell automatic variables, and missing distribution bundle payload structures.

---

## Scope & Decisions

### 1. Pre-Flight Bundle Root Validation (`install.ps1`)
- Verify at the beginning of `install.ps1` that required payload directories (`python`, `app`, `frontend\dist`) exist relative to the distribution bundle structure before attempting any copy or directory preparation actions.
- If required payload directories are absent, emit a clear, friendly error explaining that `install.ps1` must be executed from an extracted distribution bundle (referencing `scripts/build_bundle.py`), and exit with code 1.

### 2. Automatic Variable Collision Prevention (`verify-install.ps1`)
- In `verify-install.ps1`, rename `$pId` to `$servicePrincipalId` when inspecting the scheduled task principal.
- PowerShell defines `$PID` as a built-in read-only automatic variable holding the process ID of the current PowerShell instance. Re-assigning `$pId` (case-insensitive in PowerShell) risks errors or state corruption.

### 3. Direct Invocation for Python Subcommands (`backup.ps1` & `restore.ps1`)
- Replace `Start-Process` with direct invocation using the call operator (`& $pythonExe -c $script ...`) in both `backup.ps1` and `restore.ps1`.
- Direct invocation avoids argument array unquoting and whitespace-splitting issues in PowerShell 5.1 when passing inline Python scripts (`-c "..."`).
- Verify execution success using `$LASTEXITCODE`.
- Confirm SQLite integrity verification connection teardown (`d.close()`).

### 4. Packaging Test Suite Updates (`scripts/tests/test_packaging_scripts.py`)
- Add assertions testing the pre-flight bundle root error path when invoked outside an extracted bundle.
- Add assertions verifying direct call operator invocation and variable safety across scripts.
- Maintain 100% compliance with the test suite's AST scanner (enforcing safe `-DryRun` routing for packaging script invocations).

---

## Out of Scope
- No database schema or migration changes.
- No backend monitoring logic changes.
- No frontend UI modifications.
- No new dependencies.

---

## Verification
- Targeted packaging test suite (`python -m unittest scripts.tests.test_packaging_scripts`): 19 passed in 89.7s.
  - Pre-flight bundle root validation tests (missing bundle payload, incomplete bundle, valid bundle layout).
  - Call operator direct invocation and variable safety tests.
  - AST scanner enforcing `-DryRun` routing across all 8 packaging script pairs.
