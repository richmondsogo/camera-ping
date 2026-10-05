# Project Roadmap

| Step     | Name                       | Description                                                                                       | Status |
| :------- | :------------------------- | :------------------------------------------------------------------------------------------------ | :----- |
| 01       | scaffold                   | Initial repository setup, tools, FastAPI backend, Vite React frontend, and unified runner scripts | done   |
| 02 / 02b | design system & refinement | Base UI primitives, semantic spacing tokens, Tailwind v4 design tokens, and styleguide            | done   |
| 03       | camera-api                 | Database foundation, Camera model, Alembic migrations, and REST CRUD API                          | done   |
| 04       | dashboard-crud             | Camera table, add/edit modal form, delete confirmation, and client-side filtering                 | done   |
| 05       | csv-import-export          | CSV upload validation, preview-and-confirm, and camera inventory export                           | done        |
| 06       | ping-discovery             | dropped: keep the v1 ping.exe method, no discovery needed                                         | dropped     |
| 07       | monitoring-engine          | monitoring engine + status API                                                                    | done   |
| 08       | monitoring-ui              | monitoring-ui (Start/Stop buttons, summary, polling; API already exists)                          | done   |
| 09       | settings                   | settings (check interval and theme only)                                                          | done        |
| 10       | email-discovery            | dropped: no email, admin PC is offline                                                            | dropped     |
| 11       | email-alerts               | dropped: no email, admin PC is offline                                                            | dropped     |
| 12       | ci-e2e-cleanup-docs        | CI e2e + cleanup + documentation foundation                                                        | done        |
| 13       | production-runtime         | production runtime (single port serving the built frontend, configurable port, port-in-use message, Host-header check, log file) | in progress |
| 14       | offline-bundle             | offline bundle (portable Python 3.12 runtime, pre-installed dependencies, prebuilt frontend, install/start/stop/uninstall scripts, boot-time scheduled task, backup/restore, operator install guide, CHANGELOG and VERSION) | later       |
| 15       | office-acceptance          | office acceptance and handover                                                                    | later       |

