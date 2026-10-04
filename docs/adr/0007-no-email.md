# 7. Removal of Email Alerts

Date: 2026-10-04

## Decision
- Dropped all email alerting, notification triggers, and Microsoft Graph / SMTP machinery.
- Why: The admin PC operates on an isolated office LAN with no internet access.
- The operator monitors camera reachability manually via the local dashboard.
- Removed `alert_sent_for_current_outage` database column and threshold logic.
- Consequence: Failure streak (`consecutive_failures`) is retained for display in the UI.
