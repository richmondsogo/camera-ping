# 10. Offline Bundle, Windows Auto-Start, and Lifecycle

Date: 2026-10-06

## Decision
- Ship a self-contained offline zip bundling official 64-bit embeddable Python 3.12, pre-installed wheels, built frontend, and management scripts with zero runtime downloads.
- Program files install to `C:\Program Files\CameraMonitor`; runtime data, logs, backups, and configuration live in `C:\ProgramData\CameraMonitor` and survive upgrades.
- Auto-start runs as `SYSTEM` (`S-1-5-18`, highest privileges) at boot via Windows Task Scheduler with a 30-second startup delay.
- The scheduled task executes bundled `python.exe` directly rather than invoking script wrappers to avoid leaving orphaned child processes on task termination.
- Task configuration disables runtime execution limits (`ExecutionTimeLimit=0`), ignores duplicate instances, and enables automated restart on failure.
- PowerShell 5.1 scripts paired with `.cmd` launchers provide native management across all Windows 10/11 installations without external dependencies.
- Automated daily backups use SQLite's online backup API to ensure snapshot consistency while the server actively runs.
- Hard process termination (Task Scheduler stop / SIGKILL) is fully safe: the OS releases socket and instance file locks immediately, while SQLite WAL protects data integrity.
