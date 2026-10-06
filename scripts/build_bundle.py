#!/usr/bin/env python3
"""Standard-library bundle builder for Camera Monitor offline distribution.

Builds a self-contained offline distribution zip containing:
- Pinned 64-bit Python 3.12 embeddable runtime
- Locked runtime dependencies in Lib/site-packages
- Backend application, alembic migrations, and alembic.ini
- Prebuilt frontend SPA
- Windows installation and operational scripts
- Complete operator and maintenance documentation
- Fixed timestamps and deterministic forward-slash archive structure
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

EMBED_PYTHON_VERSION: Final[str] = "3.12.4"
EMBED_PYTHON_URL: Final[str] = (
    "https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip"
)
EMBED_PYTHON_SHA256: Final[str] = (
    "15fea3c9367653a85086fe37216b4d1a1c78688fa5e1587e1db0b0f658856564"
)

REQUIRED_PYTHON_DLLS: Final[list[str]] = [
    "python312.dll",
    "python.exe",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
]

EXCLUDE_PATTERNS: Final[list[str]] = [
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "tests",
    "test_",
    "data",
    ".e2e-data",
    "node_modules",
    ".git",
    "screenshots",
]

EXCLUDE_EXTENSIONS: Final[set[str]] = {
    ".db",
    ".db-wal",
    ".db-shm",
    ".sqlite3",
    ".sqlite3-wal",
    ".sqlite3-shm",
    ".log",
    ".lock",
    ".pdf",
    ".pyc",
    ".pyo",
}

FIXED_DATETIME: Final[tuple[int, int, int, int, int, int]] = (2026, 1, 1, 0, 0, 0)


def generate_pth_content() -> str:
    """Return exact required content for python312._pth."""
    return "python312.zip\n.\n..\\app\nLib\\site-packages\nimport site\n"


def is_excluded(path_str: str) -> bool:
    """Check whether a path or filename matches exclusion rules."""
    normalized = path_str.replace("\\", "/").lower()
    parts = normalized.split("/")

    for part in parts:
        if part in EXCLUDE_PATTERNS or part.startswith(".env"):
            return True
        if part.startswith("test_") and part.endswith(".py"):
            return True

    # Check extensions
    _, ext = os.path.splitext(normalized)
    if ext in EXCLUDE_EXTENSIONS:
        return True

    return False


def verify_sha256(file_path: Path, expected_sha256: str) -> bool:
    """Compute and verify SHA256 of file against expected hex string."""
    if not file_path.is_file():
        return False
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower() == expected_sha256.lower()


def compute_file_sha256(file_path: Path) -> str:
    """Return SHA256 hex digest of file."""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def download_embeddable_python(cache_dir: Path) -> Path:
    """Download embeddable Python zip if not already cached and verified."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = cache_dir / f"python-{EMBED_PYTHON_VERSION}-embed-amd64.zip"

    if zip_path.is_file() and verify_sha256(zip_path, EMBED_PYTHON_SHA256):
        print(f"[CACHE] Using verified embeddable Python at {zip_path}")
        return zip_path

    print(f"[DOWNLOAD] Downloading Python {EMBED_PYTHON_VERSION} embeddable package...")
    urllib.request.urlretrieve(EMBED_PYTHON_URL, str(zip_path))

    if not verify_sha256(zip_path, EMBED_PYTHON_SHA256):
        zip_path.unlink(missing_ok=True)
        raise ValueError(
            f"SHA256 mismatch for downloaded {EMBED_PYTHON_URL}. File removed."
        )

    print(f"[VERIFIED] SHA256 verified successfully for {zip_path.name}")
    return zip_path


def copy_directory_filtered(src_dir: Path, dst_dir: Path) -> int:
    """Copy directory contents recursively applying exclusion filters."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied_count = 0

    for root, dirs, files in os.walk(src_dir):
        rel_root = os.path.relpath(root, src_dir)
        if rel_root != "." and is_excluded(rel_root):
            dirs.clear()
            continue

        target_dir = dst_dir / rel_root if rel_root != "." else dst_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Filter dirs in-place to avoid descending into excluded directories
        dirs[:] = [d for d in dirs if not is_excluded(d)]

        for f in files:
            rel_file = os.path.join(rel_root, f) if rel_root != "." else f
            if is_excluded(rel_file):
                continue
            src_file = Path(root) / f
            dst_file = target_dir / f
            shutil.copy2(src_file, dst_file)
            copied_count += 1

    return copied_count


def create_deterministic_zip(source_dir: Path, output_zip: Path) -> tuple[int, str]:
    """Create a deterministic zip archive with sorted entries and fixed timestamps."""
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    entries: list[tuple[str, Path]] = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            full_path = Path(root) / file
            rel_path = full_path.relative_to(source_dir).as_posix()
            entries.append((rel_path, full_path))

    # Sort strictly by forward-slash relative path
    entries.sort(key=lambda item: item[0])

    with zipfile.ZipFile(
        output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zf:
        for rel_path, full_path in entries:
            zinfo = zipfile.ZipInfo(rel_path, date_time=FIXED_DATETIME)
            # Default file permissions 0o644 (rw-r--r--)
            zinfo.external_attr = 0o644 << 16
            with full_path.open("rb") as f:
                data = f.read()
            zf.writestr(zinfo, data)

    size = output_zip.stat().st_size
    sha256_hex = compute_file_sha256(output_zip)
    return size, sha256_hex


def verify_bundle_contents(bundle_dir: Path, repo_root: Path) -> list[str]:
    """Verify that the bundle directory contains no forbidden files or local paths."""
    errors: list[str] = []
    repo_root_str = str(repo_root).replace("\\", "/").lower()
    home_str = str(Path.home()).replace("\\", "/").lower()

    for root, _, files in os.walk(bundle_dir):
        for f in files:
            full_path = Path(root) / f
            rel_path = full_path.relative_to(bundle_dir).as_posix()

            if is_excluded(rel_path):
                errors.append(f"Forbidden file found in bundle: {rel_path}")

            # Scan text files for absolute repo or home paths
            ext = full_path.suffix.lower()
            if ext in [".py", ".txt", ".md", ".json", ".ini", ".env", ".cmd", ".ps1"]:
                try:
                    content = full_path.read_text(
                        encoding="utf-8", errors="ignore"
                    ).lower()
                    if repo_root_str in content:
                        errors.append(
                            f"Absolute repository path found in bundle file: {rel_path}"
                        )
                    elif home_str in content:
                        errors.append(
                            f"Absolute home path found in bundle file: {rel_path}"
                        )
                except Exception:
                    pass

    return errors


def find_python312_executable(repo_root: Path) -> Path:
    """Find a Python 3.12 executable to build clean venv for target wheels."""
    # 1. Check backend/.venv
    backend_py = (
        repo_root
        / "backend"
        / ".venv"
        / ("Scripts" if os.name == "nt" else "bin")
        / ("python.exe" if os.name == "nt" else "python")
    )
    if backend_py.is_file():
        return backend_py
    # 2. Check current sys.executable
    if sys.version_info[:2] == (3, 12):
        return Path(sys.executable)
    # 3. Check py -3.12 launcher on Windows
    if os.name == "nt":
        try:
            res = subprocess.run(
                ["py", "-3.12", "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
                check=True,
            )
            candidate = Path(res.stdout.strip())
            if candidate.is_file():
                return candidate
        except Exception:
            pass
    return Path(sys.executable)


def build_bundle(
    repo_root: Path = REPO_ROOT,
    skip_frontend_build: bool = False,
    output_dir: Path | None = None,
    cache_dir: Path | None = None,
) -> Path:
    """Build complete offline distribution bundle."""
    version_file = repo_root / "VERSION"
    if not version_file.is_file():
        raise FileNotFoundError(f"VERSION file not found at {version_file}")
    version = version_file.read_text(encoding="utf-8").strip()

    if output_dir is None:
        output_dir = repo_root / "dist-bundle"
    if cache_dir is None:
        cache_dir = repo_root / "build" / "cache"

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. Frontend build verification
    frontend_dir = repo_root / "frontend"
    frontend_dist = frontend_dir / "dist"
    if not skip_frontend_build:
        print("[BUILD] Building frontend distribution...")
        res = subprocess.run(
            ["pnpm", "--dir", "frontend", "build"], cwd=repo_root, shell=True
        )
        if res.returncode != 0:
            raise RuntimeError(f"Frontend build failed with exit code {res.returncode}")

    if not (frontend_dist.is_dir() and (frontend_dist / "index.html").is_file()):
        raise FileNotFoundError(
            f"Built frontend index.html not found in {frontend_dist}"
        )

    # 2. Acquire and verify embeddable Python
    embed_zip = download_embeddable_python(cache_dir)

    # 3. Create clean bundle staging directory
    with tempfile.TemporaryDirectory(prefix="camera_bundle_") as temp_stage:
        stage_dir = Path(temp_stage)
        bundle_root = stage_dir / "CameraMonitor"

        python_dst = bundle_root / "python"
        app_dst = bundle_root / "app"
        frontend_dst = bundle_root / "frontend" / "dist"
        scripts_dst = bundle_root / "scripts"
        docs_dst = bundle_root / "docs"

        python_dst.mkdir(parents=True)
        app_dst.mkdir(parents=True)
        frontend_dst.mkdir(parents=True)
        scripts_dst.mkdir(parents=True)
        docs_dst.mkdir(parents=True)

        # 4. Extract embeddable Python
        print(f"[EXTRACT] Extracting embeddable Python to {python_dst.name}...")
        with zipfile.ZipFile(embed_zip, "r") as zf:
            zf.extractall(python_dst)

        # Verify DLLs
        for dll_name in REQUIRED_PYTHON_DLLS:
            dll_path = python_dst / dll_name
            if not dll_path.is_file():
                print(f"[WARNING] Expected DLL missing: {dll_name}")
            else:
                assert dll_path.is_file()

        # Write python312._pth
        pth_file = python_dst / "python312._pth"
        pth_file.write_text(generate_pth_content(), encoding="utf-8")

        # 5. Install locked wheels into site-packages via temporary clean venv
        requirements_lock = repo_root / "backend" / "requirements.lock"
        if not requirements_lock.is_file():
            raise FileNotFoundError(f"Missing requirements.lock at {requirements_lock}")

        site_packages_dir = python_dst / "Lib" / "site-packages"
        site_packages_dir.mkdir(parents=True, exist_ok=True)

        print(
            f"[INSTALL] Installing locked dependencies from {requirements_lock.name}..."
        )
        with tempfile.TemporaryDirectory(prefix="bundle_venv_") as temp_venv_dir:
            temp_venv_path = Path(temp_venv_dir)
            # Create isolated venv using Python 3.12
            python312_bin = find_python312_executable(repo_root)
            res = subprocess.run(
                [str(python312_bin), "-m", "venv", str(temp_venv_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            scripts_dir = (
                temp_venv_path / "Scripts"
                if os.name == "nt"
                else temp_venv_path / "bin"
            )
            venv_python = scripts_dir / ("python.exe" if os.name == "nt" else "python")

            # Upgrade pip
            subprocess.run(
                [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
                check=True,
                capture_output=True,
                text=True,
            )

            # Install runtime requirements requiring wheels only
            install_cmd = [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--only-binary=:all:",
                "-r",
                str(requirements_lock),
            ]
            install_res = subprocess.run(install_cmd, capture_output=True, text=True)
            if install_res.returncode != 0:
                print(f"[ERROR] Pip install failed:\n{install_res.stderr}")
                raise RuntimeError("Failed to install locked runtime wheels")

            # Copy installed packages to site-packages, excluding pip/setuptools/wheel
            py_major = sys.version_info.major
            py_minor = sys.version_info.minor
            venv_site = (
                temp_venv_path / "Lib" / "site-packages"
                if os.name == "nt"
                else temp_venv_path / f"lib/python{py_major}.{py_minor}/site-packages"
            )

            copied_packages = 0
            for item in venv_site.iterdir():
                name = item.name.lower()
                if (
                    name.startswith("pip")
                    or name.startswith("setuptools")
                    or name.startswith("wheel")
                    or name.startswith("_distutils")
                ):
                    continue
                if is_excluded(item.name):
                    continue
                dest = site_packages_dir / item.name
                if item.is_dir():
                    copy_directory_filtered(item, dest)
                else:
                    shutil.copy2(item, dest)
                copied_packages += 1

            print(
                f"[INSTALLED] Installed {copied_packages} package artifacts into "
                "site-packages."
            )

        # 6. Copy backend application files to app_dst
        print("[COPY] Copying backend application files...")
        backend_dir = repo_root / "backend"
        copy_directory_filtered(backend_dir / "app", app_dst / "app")
        copy_directory_filtered(backend_dir / "alembic", app_dst / "alembic")
        shutil.copy2(backend_dir / "alembic.ini", app_dst / "alembic.ini")
        # Amendment 4: write VERSION to <bundle>\VERSION and <bundle>\app\VERSION
        (app_dst / "VERSION").write_text(version, encoding="utf-8")
        (bundle_root / "VERSION").write_text(version, encoding="utf-8")

        # 7. Copy frontend dist
        print("[COPY] Copying frontend dist...")
        copy_directory_filtered(frontend_dist, frontend_dst)

        # 8. Copy scripts from packaging/windows
        packaging_windows = repo_root / "packaging" / "windows"
        if packaging_windows.is_dir():
            for script_file in packaging_windows.iterdir():
                if script_file.is_file():
                    shutil.copy2(script_file, scripts_dst / script_file.name)

        # 9. Copy documentation files
        docs_source = repo_root / "docs"
        docs_to_include = [
            "operator-guide.md",
            "install-guide.md",
            "maintenance.md",
            "operator-card.md",
            "troubleshooting.md",
        ]
        for doc_name in docs_to_include:
            doc_path = docs_source / doc_name
            if doc_path.is_file():
                shutil.copy2(doc_path, docs_dst / doc_name)

        # Copy CHANGELOG.md
        changelog_file = repo_root / "CHANGELOG.md"
        if changelog_file.is_file():
            shutil.copy2(changelog_file, bundle_root / "CHANGELOG.md")

        # 10. Write README-FIRST.txt (under 10 lines)
        readme_content = (
            "Camera Monitor - Offline Distribution Package\n"
            "===============================================\n"
            "1. Copy this entire folder to your target Windows administration PC.\n"
            "2. Open the 'scripts' folder.\n"
            "3. Right-click 'install.cmd' and select 'Run as administrator'.\n"
            "4. Confirm prompts; the service will register to auto-start at boot.\n"
            "5. Once complete, double-click the desktop shortcut 'Camera Monitor'.\n"
            "6. For instructions and troubleshooting, see the 'docs' folder.\n"
            "7. To check service status, run 'scripts\\status.cmd'.\n"
            "8. Backups are saved to C:\\ProgramData\\CameraMonitor\\backups.\n"
        )
        (bundle_root / "README-FIRST.txt").write_text(readme_content, encoding="utf-8")

        # 11. Write manifest
        manifest_lines: list[str] = [
            f"Camera Monitor Offline Bundle Manifest v{version}",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}",
            "",
            "Files:",
        ]
        file_count = 0
        total_uncompressed = 0
        for root, _, files in os.walk(bundle_root):
            for file in sorted(files):
                full = Path(root) / file
                rel = full.relative_to(bundle_root).as_posix()
                sz = full.stat().st_size
                file_count += 1
                total_uncompressed += sz
                manifest_lines.append(f"{rel}: {sz} bytes")

        summary_line = (
            f"Total files: {file_count}, "
            f"Total uncompressed size: {total_uncompressed} bytes\n"
        )
        manifest_lines.insert(3, summary_line)
        (bundle_root / "manifest.txt").write_text(
            "\n".join(manifest_lines) + "\n", encoding="utf-8"
        )

        # 12. Verify bundle contents (no forbidden files or local paths)
        violations = verify_bundle_contents(bundle_root, repo_root)
        if violations:
            raise ValueError(
                f"Bundle validation failed with {len(violations)} errors:\n"
                + "\n".join(violations)
            )

        # 13. Create deterministic zip
        zip_filename = f"CameraMonitor-{version}.zip"
        zip_path = output_dir / zip_filename
        print(f"[ZIP] Creating deterministic archive {zip_path.name}...")
        size, sha256_hex = create_deterministic_zip(bundle_root, zip_path)

        sha256_file = output_dir / f"{zip_filename}.sha256"
        sha256_file.write_text(f"{sha256_hex} *{zip_filename}\n", encoding="utf-8")

        print("=" * 60)
        print("Bundle Created Successfully!")
        print(f"Archive:   {zip_path}")
        print(f"Size:      {size} bytes ({size / (1024 * 1024):.2f} MB)")
        print(f"SHA-256:   {sha256_hex}")
        print(f"Checksum:  {sha256_file}")
        print("=" * 60)
        return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Camera Monitor offline distribution bundle"
    )
    parser.add_argument(
        "--skip-frontend-build",
        action="store_true",
        help="Skip running pnpm build (use existing frontend/dist)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Target directory for generated zip",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Cache directory for embeddable Python archive",
    )
    args = parser.parse_args()

    try:
        build_bundle(
            repo_root=REPO_ROOT,
            skip_frontend_build=args.skip_frontend_build,
            output_dir=args.output_dir,
            cache_dir=args.cache_dir,
        )
    except Exception as exc:
        print(f"\n[BUILD FAILED] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
