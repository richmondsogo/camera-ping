# Step 01: Project Scaffold

**Date:** 2026-09-29  
**Branch:** `step/01-scaffold`  
**Status:** In Progress  

## Objectives
Establish the repository foundation and project scaffolding with zero application features, models, or screens:
1. Repo docs skeleton (`AGENTS.md`, `DESIGN.md`, `README.md`, `BUILD_PROTOCOL.md`, ADRs, step log).
2. Backend scaffold (`backend/`: Python 3.12+, FastAPI, SQLAlchemy Base, Alembic initialized, SQLite via config, pytest, Ruff, mypy strict, `GET /api/health`).
3. Frontend scaffold (`frontend/`: React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, Vitest, Playwright smoke test, placeholder page).
4. Standard root commands (`python scripts/check.py`, `python scripts/dev.py`, `python scripts/setup.py`).
5. Dev fixtures (`backend/app/dev_fixtures.py` with RFC 5737 addresses).
6. Config (`.gitignore`, `.env.example`, `.gitattributes`, `.nvmrc`).
7. CI (GitHub Actions workflow running `check.py` on `windows-latest`).

## Checkpoint Progress
- [x] Checkpoint 1: Repo docs skeleton and ADRs
- [ ] Checkpoint 2: Backend scaffold
- [ ] Checkpoint 3: Frontend scaffold
- [ ] Checkpoint 4: Standard commands and scripts
- [ ] Checkpoint 5: Dev fixtures
- [ ] Checkpoint 6: Configuration files
- [ ] Checkpoint 7: Continuous Integration workflow

## Checkpoint 1 Verification & Log
- Created `.gitattributes` enforcing `eol=lf` across all platforms.
- Created `.nvmrc` pinning Node version to 24.
- Created `AGENTS.md` with complete architecture summary, stack details, standard command documentation, and the Working Agreement.
- Kept `BUILD_PROTOCOL.md` intact at repo root.
- Created `DESIGN.md` placeholder.
- Updated `README.md` with overview and run instructions.
- Created `docs/adr/0001-stack.md` (18 lines, under 25 lines).
- Created `docs/adr/0002-git-workflow.md` (18 lines).
- Initialized `docs/steps/step-01.md`.
