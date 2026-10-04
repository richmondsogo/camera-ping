# 6. Ping Mechanism

Date: 2026-10-04

## Decision
- Execute Windows `ping.exe` in a `ThreadPoolExecutor` (max 32 workers) via `subprocess.run`.
- Success rule: exit code 0 AND raw stdout bytes contain `TTL=` (case-insensitive) AND target IP as ASCII.
- Why: On Windows, router replies ("Destination host unreachable") can return exit code 0.
- Raw byte matching avoids locale-specific text decoding errors (e.g. German "Antwort von").
- Subprocess uses 3s hard timeout and `CREATE_NO_WINDOW` to suppress console flashes on Windows.
- We avoid async ICMP libraries or raw sockets because Windows raw ICMP requires elevated admin rights.
