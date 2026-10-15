# Camera Monitor

A self-hosted, offline-capable, Windows-first uptime monitor for IP cameras, built for Hikvision camera fleets, that shows on a dashboard which cameras answer ping.

[![CI](https://github.com/richmondsogo/camera-ping/actions/workflows/ci.yml/badge.svg)](https://github.com/richmondsogo/camera-ping/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## What It Does

- **CSV or manual camera inventory**: Import UTF-8 CSV camera lists with preview and validation, or manage cameras directly from the dashboard.
- **Concurrent ICMP ping checks**: Non-blocking background thread pool probes cameras concurrently on a configurable interval.
- **Status dashboard**: Displays live reachability status, consecutive failure streaks, and offline camera counts with tab title indicators.
- **Persistent monitoring state**: Start/Stop state survives system reboots, service restarts, and power loss.
- **Configurable interval**: Adjust probing frequency between 10 seconds and 365 days (default: 60s) directly from the settings page.
- **Clean interface**: Minimal, information-dense UI with system, light, and dark theme support.
- **Automated maintenance**: Daily scheduled SQLite online backups with automatic 14-day rotation and structured rotating logs.
- **Offline deployment**: Self-contained Windows distribution bundle with embedded 64-bit Python runtime and prebuilt frontend assets.

## What It Does NOT Do

- **No camera login or credential storage**: Never requests, stores, or handles camera credentials.
- **No ONVIF, ISAPI, RTSP, or video streaming**: It does not inspect video feeds, camera health, or RTSP streams. "Online" means the camera answered ICMP echo from its own IP address, not that video works.
- **No email, SMS, or push alerts**: All reachability alerts are displayed visually on the web dashboard.
- **No network exposure**: Binds strictly to IPv4 loopback (`127.0.0.1:8742`) without authentication layers. It must not be exposed to a remote network.

## How It Works

Camera Monitor runs as a single-process FastAPI service hosting an embedded SQLite database and serving a prebuilt React single-page application. A background worker pool executes Windows `ping.exe` against configured camera IPs, requiring process exit code 0, matching target IP address, and a TTL response in stdout to mark a camera **Online**. See [Architecture](docs/architecture.md) for design and lifecycle details.

## Requirements

- **Host PC**: Windows 10 or Windows 11 64-bit (x64). Linux and macOS are not currently supported.
- **Network**: The host PC must have network reachability to camera IP addresses (same LAN, subnet, or routed VLAN). The cameras and any intermediate firewalls must answer ICMP echo requests. No internet connection is required.

## Install on a Windows Host

1. Download the latest `CameraMonitor-<version>.zip` and `CameraMonitor-<version>.zip.sha256` from [GitHub Releases](https://github.com/richmondsogo/camera-ping/releases).
2. Verify the SHA-256 checksum before extracting. *Note: The offline install bundle is not code-signed; Windows SmartScreen or antivirus software may show an unrecognized publisher prompt.*
3. Extract the ZIP archive to a temporary directory (e.g., `C:\Temp\CameraMonitor-<version>`).
4. Open an elevated Command Prompt or PowerShell terminal and run:
   ```cmd
   scripts\install.cmd
   ```
5. Open `http://127.0.0.1:8742` in your browser, or double-click the desktop shortcut.

For complete deployment details, service management, and upgrade instructions, see the [Installation Guide](docs/install-guide.md).

## Developer Quick Start

Prerequisites: Python 3.12+, Node.js 24+, pnpm 12+, Git.

```powershell
# 1. Bootstrap Python virtualenv and install frontend dependencies
python scripts/setup.py

# 2. Launch FastAPI backend (:8000) and Vite frontend (:5173) dev servers
python scripts/dev.py

# 3. Run unified lint, type check, and test suite
python scripts/check.py
```

For isolated E2E tests, design tokens, and migration workflows, see the [Development Guide](docs/development.md).

## Tested Environments & Help Wanted

Camera Monitor is at version 0.9.0 (beta). It was developed and is automatically tested in CI on Windows 11 64-bit.

We welcome community reports for Windows 10, real camera hardware, non-English Windows ping locales, and clean Windows installations without pre-installed VC++ runtimes. See [Compatibility & Tested Environments](docs/compatibility.md) for details on how to contribute test captures.

## Security

Camera Monitor binds exclusively to `127.0.0.1` and includes Host and Origin header validation to prevent cross-site request forgery. It must never be exposed to external or untrusted networks. To report security concerns, see [SECURITY.md](SECURITY.md).

## Contributing

Contributions, bug reports, and hardware compatibility feedback are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on code style, testing, and pull requests.

## Documentation Index

- [Documentation Index](docs/README.md)
- [Operator Guide](docs/operator-guide.md)
- [Installation Guide](docs/install-guide.md)
- [Operations & Maintenance Guide](docs/maintenance.md)
- [Architecture](docs/architecture.md)
- [Configuration Reference](docs/configuration.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Compatibility](docs/compatibility.md)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Trademark Disclaimer

"Hikvision" is a trademark of Hangzhou Hikvision Digital Technology Co., Ltd. This project is independent and is not affiliated with, endorsed by, or sponsored by Hikvision.
