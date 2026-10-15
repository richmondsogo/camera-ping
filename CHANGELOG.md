# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Standard open-source license: MIT License (`LICENSE`).
- Third-party dependency notices and license attributions (`THIRD_PARTY_NOTICES.md`).
- Community guidelines and contributor workflows (`CONTRIBUTING.md`).
- Security policy and vulnerability disclosure procedures (`SECURITY.md`).
- GitHub issue templates for bug reports and feature requests, and pull request template (`.github/`).
- Hardware compatibility and tested environments reference guide (`docs/compatibility.md`).

### Changed
- Repositioned project documentation and README for public open-source audience, replacing office-specific references with neutral host PC terminology.
- Updated troubleshooting guide with diagnostics for cameras that show offline but function normally.
- Updated system architecture with high-level system context diagram.

## [0.9.0] - 2026-10-06

### Added
- Offline distribution bundle packaging portable 64-bit Python 3.12 embeddable runtime with pre-installed dependencies.
- Production server CLI flags (`--home` and `--frontend-dist`) supporting separated program and data directories (`C:\ProgramData\CameraMonitor`).
- Windows Task Scheduler integration starting the service as SYSTEM at boot with 30-second delay and crash auto-restart.
- Administrative scripts for installation, upgrade, service control, status inspection, and automated SQLite online backup rotation.
- Comprehensive operator, maintenance, and installation documentation for air-gapped server environments.
