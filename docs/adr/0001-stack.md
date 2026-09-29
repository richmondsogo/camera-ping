# 1. Technology Stack

Date: 2026-09-29

## Context
Camera Monitor runs locally on an admin PC in an office server room to monitor Hikvision cameras over ICMP. It requires a resilient, lightweight stack with zero external cloud runtime dependencies.

## Decision
- Backend: Python 3.12+, FastAPI, SQLAlchemy, Alembic, SQLite
- Frontend: React 19, TypeScript, Vite, Tailwind CSS v4 (@tailwindcss/vite), TanStack Query
- Verification: pytest, Ruff, mypy (strict), Vitest, Playwright, ESLint, Prettier

## Consequences & Cost
- Self-contained and portable with low memory overhead on a Windows admin PC.
- SQLite is local-file-based with batch migration requirements (Alembic `render_as_batch=True`).
- Separate backend and frontend processes require unified runner scripts for dev and checks.
