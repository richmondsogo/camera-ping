# Architectural Decision Records (ADRs)

This directory documents the key architectural choices, constraints, and tradeoffs made in Camera Monitor.

- [ADR 0001: Technology Stack](0001-stack.md): Python 3.12/FastAPI/SQLite backend with React 19/Vite/Tailwind CSS v4 frontend.
- [ADR 0002: Git Workflow](0002-git-workflow.md): One step per conversation with strict branch discipline and incremental verification.
- [ADR 0003: UI Foundation & Design System](0003-ui-foundation.md): Headless Base UI primitives, self-hosted Inter variable font, and centralized tokens.
- [ADR 0004: Camera Data Model and API Semantics](0004-data-model.md): Named SQLite constraints with Alembic batch migrations and validation semantics.
- [ADR 0005: Frontend Data Layer, Table Column Geometry, and E2E Isolation](0005-frontend-data-layer.md): TanStack Query caching, Zod schemas, and isolated E2E server harness.
- [ADR 0006: Ping Mechanism](0006-ping-mechanism.md): Concurrent `ping.exe` execution requiring exit code 0, target IP, and TTL= match.
- [ADR 0007: Removal of Email Alerts](0007-no-email.md): Removal of SMTP/Graph notification machinery due to offline admin PC environment.
- [ADR 0008: Application Settings Storage and Dynamic Check Interval](0008-settings-storage.md): Singleton `app_settings` SQLite table for dynamic interval persistence.
