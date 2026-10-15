---
name: Bug Report
about: Create a report to help us improve Camera Monitor
title: "[BUG] "
labels: ["bug"]
assignees: ""
---

## Description
A clear and concise description of the bug.

## Environment
- **OS & Version**: [e.g. Windows 11 Pro 64-bit Build 22631, Windows 10 Pro 22H2]
- **Camera Monitor Version**: [e.g. 0.9.0]
- **Runtime Mode**: [Production scheduled service / Development (`scripts/dev.py`)]
- **Browser**: [e.g. Chrome 131, Edge 131]

## Network Topology
- How the host PC connects to the cameras (e.g. flat LAN, routed VLAN, intermediate firewall):

## Direct Ping Check
Output of `ping -n 1 -w 2000 <camera-ip>` from Command Prompt on the host PC:
```text
(paste ping output here)
```

## Logs
Relevant lines from `C:\ProgramData\CameraMonitor\logs\camera-monitor.log` (or console in dev):
```text
(paste log lines here)
```

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. See error

## Expected Behavior
What you expected to happen.

## Checklist
- [ ] Confirmed that example/pasted data uses documentation addresses or redacted IPs (no real camera IPs or private secrets).
- [ ] Checked existing issues to verify this is not a duplicate.
