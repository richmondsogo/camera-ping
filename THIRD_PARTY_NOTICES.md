# Third-Party Software Notices and Licenses

This file lists the third-party software components, runtimes, and dependencies distributed with or utilized by Camera Monitor.

> [!NOTE]
> This document is provided for informational purposes only and does not constitute legal advice.

---

## Bundled Runtimes

| Component | Version / Target | License | Project URL |
| :--- | :--- | :--- | :--- |
| **Python** (Windows embeddable 64-bit runtime) | 3.12 | Python Software Foundation License (PSFL) | https://www.python.org/psf/license/ |

---

## Backend Python Dependencies

The following dependencies are pinned in `backend/requirements.lock` and bundled into the offline distribution package:

| Package | Version | License | Project URL |
| :--- | :--- | :--- | :--- |
| `alembic` | 1.20.0 | MIT | https://alembic.sqlalchemy.org |
| `annotated-doc` | 0.0.5 | MIT | https://github.com/fastapi/annotated-doc |
| `annotated-types` | 0.8.0 | MIT | https://github.com/annotated-types/annotated-types |
| `anyio` | 4.15.1 | MIT | https://github.com/agronholm/anyio |
| `click` | 8.5.0 | BSD-3-Clause | https://github.com/pallets/click/ |
| `fastapi` | 0.142.2 | MIT | https://github.com/fastapi/fastapi |
| `h11` | 0.16.0 | MIT | https://github.com/python-hyper/h11 |
| `httptools` | 0.8.0 | MIT | https://github.com/MagicStack/httptools |
| `idna` | 3.20 | BSD-3-Clause | https://github.com/kjd/idna |
| `Mako` | 1.4.3 | MIT | https://www.makotemplates.org/ |
| `MarkupSafe` | 3.0.4 | BSD-3-Clause | https://github.com/pallets/markupsafe/ |
| `opentelemetry-api` | 1.45.0 | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-python |
| `pydantic` | 2.13.5 | MIT | https://github.com/pydantic/pydantic |
| `pydantic-settings` | 2.15.0 | MIT | https://github.com/pydantic/pydantic-settings |
| `pydantic_core` | 2.46.5 | MIT | https://github.com/pydantic/pydantic |
| `python-dotenv` | 1.2.4 | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| `PyYAML` | 6.0.3 | MIT | https://pyyaml.org/ |
| `SQLAlchemy` | 2.1.3 | MIT | https://www.sqlalchemy.org |
| `starlette` | 1.7.0 | BSD-3-Clause | https://github.com/Kludex/starlette |
| `typing-inspection` | 0.4.4 | MIT | https://github.com/pydantic/typing-inspection |
| `typing_extensions` | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions |
| `uvicorn` | 0.54.0 | BSD-3-Clause | https://github.com/Kludex/uvicorn |
| `watchfiles` | 1.3.0 | MIT | https://github.com/samuelcolvin/watchfiles |
| `websockets` | 17.2 | BSD-3-Clause | https://github.com/python-websockets/websockets |

---

## Frontend Runtime Dependencies & Assets

The following runtime libraries are specified in `frontend/package.json` and compiled into the production frontend bundle:

| Package | Version | License | Project URL |
| :--- | :--- | :--- | :--- |
| `@base-ui/react` | 1.8.0 | MIT | https://github.com/mui/base-ui |
| `@fontsource-variable/inter` | 5.3.0 | OFL-1.1 | https://github.com/fontsource/font-files |
| `@hookform/resolvers` | 5.9.1 | MIT | https://github.com/react-hook-form/resolvers |
| `@tanstack/react-query` | 5.104.0 | MIT | https://github.com/TanStack/query |
| `@tanstack/react-table` | 8.21.3 | MIT | https://github.com/TanStack/table |
| `class-variance-authority` | 0.7.1 | Apache-2.0 | https://github.com/joe-bell/cva |
| `clsx` | 2.1.1 | MIT | https://github.com/lukeed/clsx |
| `cn` | 0.4.0 | MIT | https://github.com/shadcn-ui/cn |
| `lucide-react` | 1.48.0 | ISC | https://github.com/lucide-icons/lucide |
| `react` | 19.3.0 | MIT | https://github.com/react/react |
| `react-dom` | 19.3.0 | MIT | https://github.com/react/react |
| `react-hook-form` | 7.89.0 | MIT | https://github.com/react-hook-form/react-hook-form |
| `react-router` | 8.4.0 | MIT | https://github.com/remix-run/react-router |
| `tailwind-merge` | 3.7.0 | MIT | https://github.com/dcastil/tailwind-merge |
| `zod` | 4.6.5 | MIT | https://github.com/colinhacks/zod |

### Typography

- **Inter Variable Font**: Distributed via `@fontsource-variable/inter` under the **SIL Open Font License 1.1 (OFL-1.1)**. Copyright (c) 2016-2024 The Inter Project Authors (https://github.com/rsms/inter).
