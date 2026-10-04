# Camera Monitor MVP: Build Plan

**Status:** Planning complete (Amended Step 07)

> **Amended (Step 07):** The admin PC in the office server room has no internet access. The owner checks the dashboard manually on-site. All email, notification, and Microsoft email/alert machinery has been dropped. The 10-consecutive-failures alert trigger and `alert_sent_for_current_outage` column are removed. Consecutive failure counting (`consecutive_failures`) and restart persistence are retained for display on the dashboard.

**Purpose:** Canonical scope and execution plan for the Camera Monitor MVP.

**Deployment target:** Admin PC in the office server room

**Monitoring target:** Hikvision cameras reachable on the office network

**Development constraint:** Real camera IP addresses are not available during development. The application must be fully buildable and testable using clearly marked non-production fixtures. Real IPs are introduced only during final deployment and acceptance testing.

---

## 0. Project Contract and Scaffold

Create the repository with this baseline structure:

```text
camera-monitor/
├── backend/
├── frontend/
├── docs/
│   ├── adr/
│   └── steps/
├── AGENTS.md
├── DESIGN.md
├── BUILD_PROTOCOL.md
├── README.md
└── ...
```

### Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- SQLite

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/Base UI
- TanStack Query
- TanStack Table
- React Hook Form
- Zod

### Engineering and verification

- pytest
- Ruff
- mypy or pyright
- Playwright
- ESLint
- Prettier

### Runtime assumptions

- The application runs on the admin PC in the server room.
- No cloud dependency is required for the MVP.
- The application must work on the office network without requiring an external monitoring service.
- Real camera IP addresses are not required during development.
- Development fixtures must use clearly marked non-production/test addresses.
- The codebase must provide a way to simulate ping results in automated tests so monitoring behavior can be tested without real cameras.

Example development fixture addresses:

```text
192.0.2.10
192.0.2.11
192.0.2.12
```

### Project rules

The repository must include the project's build protocol and a durable `AGENTS.md` so every fresh builder conversation has the same architectural, testing, scope, and working-agreement context.

The builder must not make architectural or product-scope decisions that have not been established in this plan or an approved ADR.

---

# 1. Design System

Establish the design system before building application screens.

The design goal is:

> **Modern, minimal, quiet, information-dense, highly consistent.**

### Visual principles

- Excellent typography
- Generous but not wasteful spacing
- Restrained borders
- Subtle status treatment
- Very few colors
- Minimal decoration
- No gradients
- No giant hero sections
- No excessive cards
- No unnecessary shadows
- No dashboard junk

### Component strategy

Use **shadcn/Base UI as the component foundation** rather than creating equivalent primitives from scratch.

Use the shadcn MCP during development where available to discover and install appropriate primitives.

Build the application's own small design layer on top of those primitives.

The design system owns:

```text
Design tokens
├── typography
├── spacing
├── colors
├── radius
├── borders
├── control heights
├── table density
└── status states
```

All application components should reuse these rules rather than inventing local values.

### Design consistency rule

The interface should feel like one product, not a collection of independently designed screens.

Prefer an existing component or established visual treatment over introducing a new one.

### Explicit design non-goals

- No decorative dashboard elements with no operational purpose
- No visual treatment added solely to make the interface feel more complex
- No separate styling language per page
- No custom component when an existing shadcn/Base UI primitive can express the interaction cleanly

`DESIGN.md` is the source of truth for these rules.

---

# 2. Database and Camera Inventory

The camera inventory is the source of truth for the cameras being monitored.

## Camera record

```text
Camera
├── id
├── camera_name
├── location
├── description
├── ip_address
├── status
├── last_checked
├── last_online
├── consecutive_failures
├── created_at
└── updated_at
```

### User-managed fields

```text
camera_name
location
description
ip_address
```

### System-managed fields

```text
status
last_checked
last_online
```

### Internal monitoring state

```text
consecutive_failures
```

The internal monitoring field tracks failure streaks reliably across application restarts.

### Inventory scope

The MVP supports:

- Add camera
- Edit camera
- Delete camera
- Import cameras from CSV
- Export camera data to CSV

The MVP does not include:

- Camera groups
- Bulk editing
- Bulk deletion
- Historical uptime analytics
- Audit history

---

# 3. Monitoring Engine

Turn the original v1 polling script into a persistent monitoring service.

## Monitoring flow

```text
Scheduler
   ↓
Monitoring cycle
   ↓
Ping all cameras concurrently
   ↓
Persist results
   ↓
Evaluate failure streaks
```

## Monitoring definition

Monitoring is based on **ICMP reachability only**.

- Successful ICMP ping = `Online`
- Failed ICMP ping = `Offline`

The MVP does not verify RTSP, HTTP/HTTPS, video availability, Hikvision APIs, SADP, or other camera-specific services.

This means the system measures whether the monitoring machine can reach the camera IP over ICMP. It does not claim that the camera's video service is healthy.

## Check behavior

Checks should run concurrently so one slow or unreachable camera does not unnecessarily delay the others.

`last_checked` means the timestamp of the most recent **attempted** check, whether successful or failed.

`last_online` means the timestamp of the most recent successful check.

## Failure tracking

```text
Ping succeeds
→ status = Online
→ consecutive_failures = 0
→ last_online = now

Ping fails
→ status = Offline
→ consecutive_failures += 1

Successful ping after an outage
→ reset failure streak (consecutive_failures = 0)
```

### Start and stop

**Start Monitoring**

- Start the scheduler.
- Perform an immediate monitoring cycle.
- Continue checks according to the configured interval.

**Stop Monitoring**

- Stop future scheduled monitoring cycles.
- Leave the most recently recorded camera state visible.
- Do not reset persisted monitoring state merely because monitoring was stopped.

### Restart behavior

Monitoring state must survive application restarts.

Example:

```text
failure #7
→ application restarts
→ next failed check becomes failure #8
```

A restart must not silently reset the failure streak to zero.

---

# 4. Backend API

Keep the API small and boring.

Planned endpoints:

```text
GET    /api/cameras
POST   /api/cameras
GET    /api/cameras/{id}
PATCH  /api/cameras/{id}
DELETE /api/cameras/{id}

POST   /api/cameras/import
GET    /api/cameras/export

GET    /api/monitoring/status
POST   /api/monitoring/start
POST   /api/monitoring/stop

GET    /api/settings
PATCH  /api/settings
```

### API architecture

Use a straightforward structure:

```text
FastAPI
   ↓
service layer
   ↓
database
```

Do not introduce GraphQL, microservices, or unnecessary infrastructure.

---

# 5. Dashboard

The application uses a small application shell with two primary destinations:

```text
Camera Monitor

Dashboard    Settings
```

No additional navigation sections are required for the MVP.

## Dashboard content

The dashboard is the operational home of the application.

It should provide a compact summary of the monitoring state, monitoring controls, camera management actions, filters, and the camera table.

Conceptually:

```text
Camera Monitor

Dashboard     Settings

┌─────────────────────────────────────────────┐
│ Cameras                     Monitoring ●    │
│                                             │
│ 30 total    28 online    2 offline          │
│                                             │
│ Last check  09:42:01                        │
│ Next check  09:43:01                        │
│                                             │
│ [ Start ] [ Stop ]                          │
└─────────────────────────────────────────────┘

Search / filters                         Import
                                         Add Camera

┌────────────────────────────────────────────────────┐
│ Camera        Location      Description    IP ...  │
├────────────────────────────────────────────────────┤
│ Front Gate    Main Gate     Entrance cam   ...     │
│ Warehouse     Loading Dock  Corridor cam   ...     │
└────────────────────────────────────────────────────┘
```

The exact layout is subject to the design-system discovery/implementation step, but the information hierarchy should remain this simple.

## Camera table

Columns:

**Camera Name | Location | Description | IP Address | Status | Last Checked**

## Filtering

Basic filtering only:

- Text search
- Status
- Location

Do not turn filtering into an advanced query builder.

## Dashboard monitoring indicator

The dashboard must make the monitoring engine state visible.

At minimum, the interface should communicate:

- Running or stopped state
- Most recent completed cycle
- Next scheduled check when monitoring is running

This prevents stale camera data from appearing current merely because it remains visible on screen.

---

# 6. Camera CRUD

The Add and Edit flows use the same underlying form component.

Fields:

```text
Camera Name
Location
Description
IP Address
```

### Validation

Validation must exist on both frontend and backend.

The server remains authoritative.

### Editing rules

Users may edit:

- Camera Name
- Location
- Description
- IP Address

Users may not directly edit:

- Status
- Last Checked
- Last Online
- Consecutive Failures


### Delete

Deleting a camera requires a confirmation step.

Deleting a camera removes that camera from the active monitoring inventory and its associated monitoring state.

No separate history is retained in the MVP.

---

# 7. CSV Import and Export

## Canonical import format

The required headers are exactly:

```csv
camera_name,location,description,ip_address
```

Example:

```csv
camera_name,location,description,ip_address
Front Gate Bullet,Main Entrance Gate,Front gate entrance camera,192.168.1.102
Backyard Dome,Rear Perimeter Wall,Rear perimeter camera,192.168.1.51
Warehouse Corridor,Loading Dock A,Warehouse corridor camera,192.168.1.52
```

The import UI should explain the required headers and display an example.

Provide a **Download CSV Template** action so users do not have to construct the format manually.

## Import validation

Reject the entire import if any row fails validation.

Validation includes:

```text
wrong headers              → reject
missing required value     → reject
invalid IP address         → reject
duplicate IP in CSV        → reject
duplicate IP already stored → reject
```

**No partial imports.**

If the CSV is invalid, nothing from that import is committed.

## Export

Export should produce a CSV containing the camera inventory and current system-provided status information needed by the dashboard/export requirement.

The exact export header contract should be finalized during the implementation step so the import and export schemas remain intentionally distinct where system-generated fields require it.

---

# 8. Settings

Only the required settings are included in the MVP.

```text
Monitoring
└── Check interval

Appearance
└── Light / Dark
```

### Check interval

The checking interval is configurable from Settings.

The scheduler uses the saved interval when monitoring is running.

The exact allowed interval range and UI control can be finalized during implementation, but the MVP should keep this intentionally simple rather than exposing arbitrary scheduling rules.

### Appearance

Provide light and dark modes using the same design system and component styling.

No additional personalization is required.

---

# 9. Integration and E2E Testing

Testing must prove the application's behavior without depending on the real office cameras.

## Basic monitoring flow

```text
Add dummy camera
        ↓
Start monitoring
        ↓
Ping runs
        ↓
Dashboard updates
        ↓
Stop monitoring
```

## Import flow

```text
Import CSV
        ↓
30 cameras appear
        ↓
Start monitoring
        ↓
All cameras are checked
        ↓
Statuses update
```

## Failure streak and recovery flow

```text
Offline
→ failure streak increases (consecutive_failures += 1)

Online
→ failure streak resets (consecutive_failures = 0)
```

## Restart persistence flow

```text
failure #7
→ restart application
→ next failed check = failure #8
```

## UI verification

Every user-visible step must be run and visually inspected in a real browser.

A green type checker or test suite does not prove the UI is correct.

---

# 10. Final Acceptance Test on the Actual Office Network

Real camera IP addresses are intentionally introduced only at the final deployment/test stage.

Deployment flow:
```text
Admin PC in server room
          ↓
Install application
          ↓
Import real camera CSV
          ↓
Start Monitoring
          ↓
30 real Hikvision camera IPs
          ↓
Actual ICMP checks
          ↓
Dashboard displays live results
```

The final test must verify at minimum:

1. Real CSV import succeeds with the office camera inventory.
2. Real Hikvision IPs are reachable and receive correct Online/Offline status.
3. Last Checked timestamps update correctly.
4. Start and Stop work correctly.
5. The configured interval is respected.
6. Failure streak persists across a restart (failure #7, restart, failure #8).
7. Unplug one camera and see it Offline after the next cycle.
8. Restoring reachability resets the failure streak to 0.

This is the final acceptance boundary between development and operational deployment.

---

# Development Protocol

The repository follows `BUILD_PROTOCOL.md` throughout implementation.

## Roles

**Planner:** this planning process decides scope, architecture, prompts, reviews, and next steps.

**Builder:** the IDE agent executes one approved implementation prompt at a time.

The builder does not receive an open-ended instruction to "build the app."

## Fresh conversations

Every implementation step uses a fresh builder conversation.

Durable project context belongs in repository files, especially `AGENTS.md`, rather than relying on chat history.

## Plan before code

Every builder turn begins with:

> Make a numbered implementation plan first. Do not modify any files until I approve the plan.

Only after approval should the builder make changes.

## Discovery before uncertain implementation

If implementation depends on an unfamiliar, fragile, or externally controlled behavior, create a discovery step first and record the findings before implementation.

Examples for this project include:

- Windows ping command output across locales
- shadcn/Base UI component availability and MCP usage
- Browser behavior that cannot be reliably inferred
- Any other external integration whose behavior needs real evidence

## Checkpoint commits

Commit at meaningful checkpoints rather than treating the whole project as one final commit.

Each commit should represent a small, verifiable unit of progress.

## Verification ritual

After every builder turn, before accepting its summary:

```text
git status
git diff
project checks/tests
typecheck/lint
run the application
inspect the UI in a browser when applicable
```

The builder's report is treated as a claim to verify, not as proof of completion.

When a file is runtime-critical, confirm its actual contents from disk and run the application rather than relying only on static checks.

When a visual change is made, inspect the rendered result and compare it with the established design system.

## Scope discipline

Features not explicitly included in this plan do not enter the MVP implicitly.

Do not add:

- Authentication/roles
- Notification types or emails
- Recovery emails
- Historical monitoring analytics
- RTSP/video verification
- Hikvision API integration
- Automatic camera discovery
- SNMP
- Cloud services
- Redis/Celery or equivalent infrastructure without a demonstrated need
- Bulk management features
- AI features

Any real scope change must be discussed and recorded before implementation.

## Decision records

Meaningful architectural decisions should be recorded as ADRs under:

```text
docs/adr/
```

Examples likely to require ADRs:

- Database/runtime architecture
- Scheduler/monitoring architecture
- Frontend/backend boundary
- Any decision that materially changes the operational or deployment model

## Step logs

Each implementation step gets a corresponding log under:

```text
docs/steps/
```

A step log records what actually happened, including discoveries, deviations, verification results, and notable problems.

---

# MVP Boundary

The MVP is complete when the following is true:

> An operator on the admin PC can maintain a camera inventory, import real camera IPs from the documented CSV format, start and stop periodic ICMP monitoring, see current camera status and timestamps in a clean dashboard, and configure the monitoring interval and theme.

Everything else is outside the MVP unless explicitly added through a documented scope decision.
