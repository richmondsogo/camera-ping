# Notes for later steps

## For Step 05 (ping discovery) and Step 06 (monitoring engine)
- Sequential pings do not scale. One check can take up to ~2s, so 30 unreachable cameras take up to ~60s, which equals the whole default check interval. The engine must ping concurrently.
- On Windows, ping.exe can exit with code 0 when a router replies "Destination host unreachable". Exit code alone is not proof of reachability. Step 05 must test this on the real Windows machine and decide whether to also require "TTL=" in the output, and verify that works on non-English Windows.
- The v1 script (cctv-ping.py) keeps its state in memory only. The new design persists failure streaks and alert state in the database so restarts do not lose them. The restart test (failure #7, restart, failure #8) proves this.
## For Step 13 (deploy)
- The admin PC will reboot. The app must auto-start (Task Scheduler or a service wrapper) and resume monitoring state.
