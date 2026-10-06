#!/usr/bin/env python3
"""Bundle smoke test for Camera Monitor offline distribution.

Verifies:
1. Extraction into a path containing spaces.
2. Complete environment isolation in a scrubbed environment (no external Python leaks).
3. Presence of all required runtime DLLs in python/.
4. Server execution with cwd set to <bundle>/app.
5. Verification of routes, /api/health, initial empty DB, and startup logging.
6. CSV import of sample cameras, adding a 127.0.0.1 camera, and starting probe.
7. Verification that 127.0.0.1 camera turns online.
8. Hard process kill (taskkill /F).
9. Server restart with cwd set to unrelated directory (temp root) verifying auto-resume.
10. Database PRAGMA integrity_check and log contents verification.
11. Port conflict handling writing exit-3 error to the log file.
12. Full process and filesystem cleanup.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

REQUIRED_DLLS: Final[list[str]] = [
    "python312.dll",
    "python.exe",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
]


def get_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_for_health(port: int, timeout: float = 20.0) -> bool:
    start = time.time()
    url = f"http://127.0.0.1:{port}/api/health"
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as res:
                if res.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def http_get(url: str) -> tuple[int, str]:
    with urllib.request.urlopen(url, timeout=2.0) as res:
        return res.status, res.read().decode("utf-8")


def http_post_json(url: str, payload: dict[str, object]) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=2.0) as res:
        return res.status, res.read().decode("utf-8")


def http_post_raw(url: str, raw_bytes: bytes, content_type: str) -> tuple[int, str]:
    req = urllib.request.Request(
        url, data=raw_bytes, headers={"Content-Type": content_type}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=5.0) as res:
        return res.status, res.read().decode("utf-8")


def run_smoke_test(zip_path: Path) -> None:
    if not zip_path.is_file():
        raise FileNotFoundError(f"Bundle zip not found: {zip_path}")

    print("=" * 60)
    print("Camera Monitor - Offline Bundle Smoke Test")
    print(f"Archive: {zip_path}")
    print("=" * 60)

    # 1. Extract into directory containing a space
    extract_parent = Path(tempfile.mkdtemp(prefix="camera bundle smoke space "))
    home_dir = Path(tempfile.mkdtemp(prefix="camera home space "))

    proc_to_kill: subprocess.Popen[str] | None = None

    try:
        print(f"\n[1/10] Extracting bundle into: {extract_parent}...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_parent)

        # Locate bundle root
        bundle_root = extract_parent / "CameraMonitor"
        if not bundle_root.is_dir():
            bundle_root = extract_parent

        python_dir = bundle_root / "python"
        python_exe = python_dir / "python.exe"
        app_dir = bundle_root / "app"
        frontend_dist = bundle_root / "frontend" / "dist"

        assert python_exe.is_file(), f"python.exe not found at {python_exe}"
        assert app_dir.is_dir(), f"app directory not found at {app_dir}"
        assert frontend_dist.is_dir(), f"frontend dist not found at {frontend_dist}"

        # 2. Check DLLs (Amendment 3)
        print("\n[2/10] Verifying runtime DLLs in bundle python/ folder...")
        present_files = [f.name.lower() for f in python_dir.iterdir()]
        for req_dll in REQUIRED_DLLS:
            if req_dll.lower() not in present_files:
                raise AssertionError(f"Required DLL missing from python/: {req_dll}")
            print(f"       PASS: {req_dll} is present")

        # 3. Test environment isolation with scrubbed environment
        print("\n[3/10] Verifying runtime environment isolation...")
        win_dir = os.path.splitdrive(tempfile.gettempdir())[0] + "\\Windows"
        temp_root = tempfile.gettempdir()
        scrubbed_env = {
            "SYSTEMROOT": win_dir,
            "WINDIR": win_dir,
            "PATH": f"{win_dir}\\System32",
            "TEMP": temp_root,
            "TMP": temp_root,
        }

        inspect_code = (
            "import sys, app.serve, uvicorn;"
            "print('PREFIX=' + sys.prefix);"
            "print('PATH=' + repr(sys.path));"
            "print('APP=' + app.serve.__file__);"
            "print('UVICORN=' + uvicorn.__file__)"
        )
        res = subprocess.run(
            [str(python_exe), "-c", inspect_code],
            cwd=str(app_dir),
            env=scrubbed_env,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(
                f"Scrubbed Python inspection failed (code {res.returncode}):\n"
                f"{res.stderr}"
            )

        output_text = res.stdout
        print("       Runtime report:")
        for line in output_text.splitlines():
            print(f"         {line}")

        # Assert no paths point into git repo or dev venv
        repo_lower = str(REPO_ROOT).lower()
        dev_venv_lower = str(REPO_ROOT / "backend" / ".venv").lower()
        for line in output_text.splitlines():
            line_lower = line.lower()
            if dev_venv_lower in line_lower:
                raise AssertionError(f"Leak detected: line references dev venv: {line}")
            if (
                repo_lower in line_lower
                and "camera bundle smoke space" not in line_lower
            ):
                raise AssertionError(
                    f"Leak detected: line references source repo: {line}"
                )
        print(
            "       PASS: Python runtime is completely isolated from dev environment."
        )

        # 4. Start Server Run 1 (cwd = <bundle>/app)
        port1 = get_free_port()
        print(f"\n[4/10] Starting server (Run 1: cwd=<bundle>/app) on port {port1}...")

        # Create camera-monitor.env in test home with interval 10s
        home_env_file = home_dir / "camera-monitor.env"
        home_env_file.write_text("MONITOR_INTERVAL_SECONDS=10\n", encoding="utf-8")

        run1_env = dict(scrubbed_env)
        run1_env["BACKEND_PORT"] = str(port1)

        proc_to_kill = subprocess.Popen(
            [
                str(python_exe),
                "-m",
                "app.serve",
                "--home",
                str(home_dir),
                "--frontend-dist",
                str(frontend_dist),
            ],
            cwd=str(app_dir),
            env=run1_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        assert wait_for_health(port1), f"Server failed to start on port {port1}"
        print("       PASS: /api/health returned 200 OK")

        # 5. Verify routes and startup log
        print("\n[5/10] Verifying routes and startup version log...")
        status_root, html_root = http_get(f"http://127.0.0.1:{port1}/")
        assert status_root == 200 and len(html_root) > 0, "Failed to load /"

        status_settings, html_settings = http_get(f"http://127.0.0.1:{port1}/settings")
        assert status_settings == 200 and len(html_settings) > 0, (
            "Failed to load /settings"
        )

        # Check DB and log file
        db_path = home_dir / "data" / "camera_monitor.db"
        assert db_path.is_file(), f"Database not created at {db_path}"

        log_path = home_dir / "logs" / "camera-monitor.log"
        assert log_path.is_file(), f"Log file not created at {log_path}"
        log_content = log_path.read_text(encoding="utf-8")

        # Amendment 4: Assert startup log line contains "0.9.0" and not "dev"
        assert "Camera Monitor 0.9.0 starting" in log_content, (
            f"Expected 'Camera Monitor 0.9.0 starting' in log, got:\n{log_content}"
        )
        assert "Camera Monitor dev starting" not in log_content, (
            "Log line incorrectly logged 'dev' version!"
        )
        print("       PASS: Startup log contains version '0.9.0' and routes responded.")

        # Check initial empty state
        _, cameras_json = http_get(f"http://127.0.0.1:{port1}/api/cameras")
        cameras = json.loads(cameras_json)
        assert len(cameras) == 0, f"Expected 0 cameras initially, found {len(cameras)}"

        _, mon_status_json = http_get(f"http://127.0.0.1:{port1}/api/monitoring/status")
        mon_status = json.loads(mon_status_json)
        assert mon_status["running"] is False, "Monitoring should initially be stopped"
        print("       PASS: Initial DB is empty with monitoring stopped.")

        # 6. Import sample cameras and add local camera
        print("\n[6/10] Importing sample cameras and adding loopback camera...")
        sample_csv = REPO_ROOT / "shared" / "sample-cameras-30.csv"
        csv_bytes = sample_csv.read_bytes()
        status_imp, _ = http_post_raw(
            f"http://127.0.0.1:{port1}/api/cameras/import",
            csv_bytes,
            "text/csv; charset=utf-8",
        )
        assert status_imp in (200, 201), f"CSV import failed with status {status_imp}"

        # Add 127.0.0.1 camera
        local_camera = {
            "camera_name": "Smoke Local Camera",
            "ip_address": "127.0.0.1",
            "location": "Server Room",
            "description": "Loopback monitor probe",
        }
        status_create, create_resp = http_post_json(
            f"http://127.0.0.1:{port1}/api/cameras", local_camera
        )
        assert status_create == 201, f"Failed to create camera: {create_resp}"
        created_cam = json.loads(create_resp)
        cam_id = created_cam["id"]

        # 7. Start monitoring and verify 127.0.0.1 turns online
        print("\n[7/10] Starting monitoring engine and polling reachability...")
        status_start, _ = http_post_json(
            f"http://127.0.0.1:{port1}/api/monitoring/start", {}
        )
        assert status_start == 200

        # Wait for camera to become online (up to 15s)
        camera_online = False
        start_poll = time.time()
        while time.time() - start_poll < 20.0:
            _, cams_json = http_get(f"http://127.0.0.1:{port1}/api/cameras")
            cams = json.loads(cams_json)
            for c in cams:
                if c["id"] == cam_id and c["status"] == "online":
                    camera_online = True
                    break
            if camera_online:
                break
            time.sleep(1.0)

        assert camera_online, "Camera 127.0.0.1 did not transition to online status"
        print("       PASS: Camera 127.0.0.1 transitioned to online status.")

        # 8. Hard kill the server process (taskkill /F)
        print("\n[8/10] Hard-killing server process (taskkill /F)...")
        pid1 = proc_to_kill.pid
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/PID", str(pid1)], check=True)
        else:
            proc_to_kill.kill()
        proc_to_kill.wait(timeout=5)
        proc_to_kill = None
        print("       PASS: Server process terminated.")

        # 9. Server Run 2 with UNRELATED cwd (Amendment 2)
        port2 = get_free_port()
        print(f"\n[9/10] Starting server (Run 2: unrelated cwd) on port {port2}...")
        run2_env = dict(scrubbed_env)
        run2_env["BACKEND_PORT"] = str(port2)

        proc_to_kill = subprocess.Popen(
            [
                str(python_exe),
                "-m",
                "app.serve",
                "--home",
                str(home_dir),
                "--frontend-dist",
                str(frontend_dist),
            ],
            cwd=str(extract_parent),  # Unrelated working directory!
            env=run2_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        assert wait_for_health(port2), (
            f"Server failed to start on port {port2} from unrelated cwd"
        )

        # Verify monitoring auto-resumed
        _, mon_status_json2 = http_get(
            f"http://127.0.0.1:{port2}/api/monitoring/status"
        )
        mon_status2 = json.loads(mon_status_json2)
        assert mon_status2["running"] is True, (
            "Monitoring engine did not auto-resume on restart"
        )
        print("       PASS: Monitoring engine automatically resumed.")

        # Verify database integrity check
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        integrity_res = cursor.execute("PRAGMA integrity_check;").fetchall()
        conn.close()
        assert integrity_res == [("ok",)], f"Integrity check failed: {integrity_res}"
        print("       PASS: SQLite PRAGMA integrity_check returned ok.")

        # 10. Lock and port conflict testing
        print("\n[10/10] Testing lock conflict (exit 4) and port conflict (exit 3) logging...")
        # A. Lock conflict: same home_dir -> exit 4
        lock_res = subprocess.run(
            [
                str(python_exe),
                "-m",
                "app.serve",
                "--home",
                str(home_dir),
                "--frontend-dist",
                str(frontend_dist),
            ],
            cwd=str(extract_parent),
            env=run2_env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert lock_res.returncode == 4, (
            f"Expected exit code 4 for lock conflict, got {lock_res.returncode}"
        )
        print("       PASS: Lock conflict correctly detected and exited 4.")

        # B. Port conflict: different home_dir, same port -> exit 3
        conflict_home = extract_parent / "conflict_home"
        conflict_home.mkdir(parents=True, exist_ok=True)
        (conflict_home / "camera-monitor.env").write_text(
            f"BACKEND_PORT={port2}\n", encoding="utf-8"
        )
        port_res = subprocess.run(
            [
                str(python_exe),
                "-m",
                "app.serve",
                "--home",
                str(conflict_home),
                "--frontend-dist",
                str(frontend_dist),
            ],
            cwd=str(extract_parent),
            env=run2_env,
            capture_output=True,
            text=True,
            timeout=25,
        )
        assert port_res.returncode == 3, (
            f"Expected exit code 3 for port conflict, got {port_res.returncode}"
        )
        conflict_log = conflict_home / "logs" / "camera-monitor.log"
        assert conflict_log.is_file(), "Conflict log file not found"
        conflict_log_text = conflict_log.read_text(encoding="utf-8")
        assert (
            f"Port {port2} is already in use" in conflict_log_text
            or "Choose another port" in conflict_log_text
        ), "Exit code 3 message was not found in log file!"
        print("       PASS: Port conflict correctly logged error and exited 3.")

    finally:
        # Full cleanup
        print("\n[CLEANUP] Terminating processes and cleaning temporary directories...")
        if proc_to_kill is not None:
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(proc_to_kill.pid)],
                        capture_output=True,
                    )
                else:
                    proc_to_kill.kill()
                proc_to_kill.wait(timeout=3)
            except Exception:
                pass

        shutil.rmtree(extract_parent, ignore_errors=True)
        shutil.rmtree(home_dir, ignore_errors=True)
        print("       Cleanup complete.")

    print("\n" + "=" * 60)
    print("ALL BUNDLE SMOKE CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


def main() -> None:
    if len(sys.argv) > 1:
        zip_path = Path(sys.argv[1]).resolve()
    else:
        # Build bundle first if no zip is provided
        from scripts.build_bundle import build_bundle

        print("[INFO] No bundle zip specified. Building fresh bundle...")
        zip_path = build_bundle()

    run_smoke_test(zip_path)


if __name__ == "__main__":
    main()
