# Compatibility & Tested Environments

This document details network requirements, supported host systems and camera hardware, currently tested environments, and areas where community verification is needed.

## Network Requirements: What "Same Network" Means

Camera Monitor determines camera availability exclusively through ICMP echo requests (ping). It does not maintain persistent TCP sockets, log in to camera web interfaces, query RTSP video feeds, or utilize ONVIF/ISAPI protocols.

For Camera Monitor to report a camera as **Online**, the following conditions must be satisfied:

1. **Host-to-Camera Reachability**: The host PC must be capable of reaching the camera's IP address directly. This typically means the camera resides on the same local subnet, or on a routed subnet or VLAN with an active route from the host.
2. **ICMP Echo Replies**: The camera must be powered on, have its network interface up, and respond to standard ICMP echo requests from its own IP address.
3. **Firewalls and Network Policies**: Any intermediate switches, routers, VLAN gateways, or host firewall rules must permit ICMP traffic (type 8 echo request and type 0 echo reply) between the host PC and the cameras.

### Verifying Reachability from the Host PC

Before troubleshooting the Camera Monitor application or dashboard, test reachability directly from a standard Command Prompt or PowerShell terminal on the host PC:

```cmd
ping -n 1 -w 2000 <camera-ip>
```

- If `ping <camera-ip>` fails in the terminal (request timed out, destination host unreachable, or general failure), Camera Monitor will also report the camera as **Offline**.
- If a camera or NVR is explicitly configured to silence or drop ICMP ping requests for security hardening, Camera Monitor will report it as **Offline** even though its video stream or web interface may be fully functional.
- Camera Monitor never sends credentials, modifies camera configuration, or accesses camera video streams. It sends a single ICMP echo packet per configured interval.

---

## Supported and Unsupported Hardware

### Cameras

- **Supported**: Any network camera, NVR, DVR, or IP device that has a static or DHCP-reserved IPv4 address and replies to ICMP echo requests with a standard TTL response. While originally built for Hikvision camera fleets, monitoring is completely vendor-neutral.
- **Unsupported**:
  - Cameras behind separate NAT routers without routed IP access from the host PC.
  - Cameras configured to ignore or drop ICMP echo requests.
  - Battery-powered Wi-Fi cameras that enter deep sleep and drop network connectivity between video events.
  - Cloud-only cameras that do not expose a local IP address on the LAN.

### Host Systems

- **Supported**:
  - Windows 11 (64-bit x64).
  - Windows 10 (64-bit x64, version 1809 / build 17763 or newer).
- **Unsupported**:
  - 32-bit (x86) Windows systems (the offline bundle bundles a 64-bit Python runtime).
  - Linux and macOS (currently unsupported; background service management, scheduled tasks, and single-process host launchers currently rely on Windows Task Scheduler, `ping.exe`, and Windows-specific process management).

---

## Tested Environments

Camera Monitor is currently at **version 0.9.0 (beta)**. The following table reflects environments verified in this repository's automated tests and development logs:

| Environment | Status | Verification Method | Notes |
| :--- | :--- | :--- | :--- |
| **Windows 11 64-bit** (CI Runner `windows-latest`) | Verified | GitHub Actions automated workflow | Unified checks (`check.py`), Playwright E2E suite, installer dry-run tests, and bundle smoke test (`bundle_smoke.py`). |
| **Windows 11 64-bit** (Development Machine) | Verified | Local development and testing | Full developer stack (`scripts/dev.py`), single-process production runtime (`scripts/run_prod.py`), and test suites. |
| **Windows 10 64-bit** | Not Yet Confirmed | Pending community / field testing | Target environment specifications documented; physical hardware test pending. |
| **Physical Hikvision Cameras** | Not Yet Confirmed | Synthetic test vectors only | Test suite uses mocked subprocess outputs and synthetic fixtures in `backend/tests/fixtures/ping/`. |
| **Non-English Windows Locales** | Not Yet Confirmed | Synthetic test vectors only | Tested with synthetic German fixtures; real localized `ping.exe` output captures not yet confirmed. |
| **Clean Windows Install** (no VC++ redistributable) | Not Yet Confirmed | Pending clean VM testing | Embedded Python 3.12 runtime dependency on system CRT / VC++ runtime on completely fresh Windows installs is not yet verified. |
| **Production Installer under Live Conditions** | Not Yet Confirmed | Dry-run and smoke test only | Tested with `-DryRun` and standalone isolated directories; live production deployment to `C:\Program Files` awaiting field validation. |

---

## Help Wanted: How to Contribute Results

We welcome verification results and fixtures from users and contributors. Areas where feedback is actively needed:

### 1. Windows 10 Verification
If you run Camera Monitor on Windows 10 Pro or Enterprise (64-bit), please open an issue reporting your Windows build number (`winver`), whether the installer and scheduled tasks operated smoothly, and any unexpected behavior.

### 2. Real Camera Fleet Results
If you monitor physical cameras (Hikvision, Dahua, Axis, Hanwha, Amcrest, or others), let us know your camera models, network topology (flat LAN vs routed VLAN), and whether any cameras drop ICMP packets under load.

### 3. Non-English Windows Ping Captures
Camera Monitor parses `ping.exe` output for exit code 0, matching target IP address, and `"TTL="`. If you run Windows in a language other than English (e.g., German, French, Spanish, Japanese, Chinese):
1. Run the following command from Command Prompt against a reachable IP and an unreachable IP:
   ```cmd
   ping.exe -n 1 -w 2000 <reachable-ip> > reachable.txt
   ping.exe -n 1 -w 2000 <unreachable-ip> > unreachable.txt
   ```
2. Check if the output contains `"TTL="` or a localized equivalent.
3. Submit the text captures as a pull request under `backend/tests/fixtures/ping/` or attach them to an issue with your Windows language and build version.

### 4. Clean Windows Machine Testing
Test extracting `dist-bundle/CameraMonitor-<version>.zip` on a fresh, newly installed Windows 10 or 11 virtual machine that has never had Python, Visual Studio, or developer tools installed. Report whether `scripts\install.cmd` or `python\python.exe` report missing DLLs (such as `VCRUNTIME140.dll`).

### 5. Cross-Platform Ports
If you are interested in porting the daemon and process launcher to Linux (systemd) or macOS (launchd) with POSIX ping parsing, please open a discussion or pull request.

---

## Trademark Disclaimer

"Hikvision" is a trademark of Hangzhou Hikvision Digital Technology Co., Ltd. This project is independent and is not affiliated with, endorsed by, or sponsored by Hikvision.
