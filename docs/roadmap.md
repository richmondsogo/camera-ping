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
| 09       | settings                   | settings (check interval and theme only)                                                          | done   |
| 10       | email-discovery            | dropped: no email, admin PC is offline                                                            | dropped     |
| 11       | email-alerts               | dropped: no email, admin PC is offline                                                            | dropped     |
| 12       | e2e                        | Complete smoke and end-to-end integration test suite simulating camera states                     | later       |
| 13       | deploy                     | deploy (must work offline): admin PC deployment, single-port serving, and autostart               | later       |

