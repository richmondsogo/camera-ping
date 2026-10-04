# Step 08: Monitoring UI

## Overview
Step 08 connects the dashboard frontend to the monitoring engine with live controls, status summaries, timing indicators, and fault alerts.

## Key Changes
- **Backend Schema & Timings**: Added `running_since` to `MonitoringStatusResponse` and exposed read-only `consecutive_failures` on `CameraRead`. Refined `next_check_at` to remain null until cycle 1 finishes.
- **Monitoring Panel**: Created `MonitoringPanel` displaying running/stopped status, camera counts by status, cycle timings (Last check, Next check, interval), and accessible Start/Stop controls.
- **Accessible Focus & Alerts**: Managed focus across Start/Stop mutations (opposite button on success, retained on failure); provided live announcements and inline retry errors.
- **Fault Detection & Status**: Added stall detection with ticking clock hook (`useNow`), connection-lost banner (suppressing stall alert while active), all-offline diagnostic banner, and stopped status notice.
- **Consecutive Check Failures**: Displayed badge with title (`Failed N consecutive checks`) on offline camera rows in `CameraTable`.
- **Live Tab Title**: Dynamic browser document title `(N offline) Camera Monitor` with automatic cleanup on unmount.
- **Polling & E2E Validation**: 5000ms polling for status and camera queries; verified live probe cycles and reload persistence with Playwright.
