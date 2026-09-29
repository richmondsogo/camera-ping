# 3. UI Foundation & Design System

Date: 2026-09-29

## Context
Camera Monitor requires a minimal, quiet, offline-first admin interface with zero cloud runtime dependencies, running locally on a server room PC.

## Decision
- Base UI (`@base-ui/react` via shadcn `base-nova` preset) over Radix: modern, unstyled headless primitives natively supported by the CLI.
- Self-hosted Inter font via `@fontsource-variable/inter` with system fallbacks; zero Google Fonts or external CDNs.
- Declarative client routing via `react-router` v7 (`BrowserRouter` in `main.tsx`) without data routers or loaders.
- Single source of truth in `frontend/src/index.css` using Tailwind CSS v4 `@theme`, `@utility`, `:root`, and `.dark`.
- Strict design limits: 1200px container (`max-w-page`), 4px spacing grid, 32px/28px controls, 6px/8px radii, no shadows except dialog overlay, no gradients, minimal palette with one blue accent.

## Consequences & Cost
- All primitives must be restyled to project tokens; default library styles cannot be used directly.
- Font files are bundled locally, increasing frontend asset footprint by ~100KB while guaranteeing offline reliability.
