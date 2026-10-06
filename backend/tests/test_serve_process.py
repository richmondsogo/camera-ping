import os
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from app.config import BACKEND_DIR

IS_WINDOWS = platform.system() == "Windows"
PYTHON_BIN = sys.executable


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_for_server(port: int, timeout: float = 15.0) -> bool:
    start = time.time()
    url = f"http://127.0.0.1:{port}/api/health"
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as res:
                if res.status == 200:
                    return True
        except Exception:
            time.sleep(0.1)
    return False


def read_locked_pid(lock_file: Path) -> str:
    """Read the PID written at offset 0 without buffering into locked byte 100."""
    with lock_file.open("rb", buffering=0) as f:
        return f.read(16).decode("ascii", errors="ignore").strip()


def test_serve_lifecycle_and_routes(tmp_path: Path) -> None:
    """Real-process test: serves /, /settings, and /api/health; cleans up cleanly."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text(
        "<!doctype html><html>Prod App</html>", encoding="utf-8"
    )

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_file = data_dir / "camera_monitor.db"
    log_dir = tmp_path / "logs"

    port = get_free_port()
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    env["LOG_DIR"] = str(log_dir)
    env["FRONTEND_DIST"] = str(dist_dir)
    env["BACKEND_PORT"] = str(port)
    env["BACKEND_HOST"] = "127.0.0.1"

    proc = subprocess.Popen(
        [PYTHON_BIN, "-m", "app.serve"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert wait_for_server(port), "Server failed to start in time"

        # Check /api/health
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/health", timeout=1.0
        ) as res:
            assert res.status == 200
            assert b"ok" in res.read()

        # Check /
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1.0) as res:
            assert res.status == 200
            assert b"Prod App" in res.read()

        # Check /settings
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/settings", timeout=1.0
        ) as res:
            assert res.status == 200
            assert b"Prod App" in res.read()

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


def test_second_instance_same_data_dir_exits_4(tmp_path: Path) -> None:
    """Second instance on same data dir exits 4 within 3s and mentions existing PID."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>App</html>", encoding="utf-8")

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_file = data_dir / "camera_monitor.db"
    log_dir = tmp_path / "logs"

    port1 = get_free_port()
    port2 = get_free_port()

    env1 = os.environ.copy()
    env1["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    env1["LOG_DIR"] = str(log_dir)
    env1["FRONTEND_DIST"] = str(dist_dir)
    env1["BACKEND_PORT"] = str(port1)
    env1["BACKEND_HOST"] = "127.0.0.1"

    proc1 = subprocess.Popen(
        [PYTHON_BIN, "-m", "app.serve"],
        cwd=BACKEND_DIR,
        env=env1,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert wait_for_server(port1), "Server 1 failed to start"

        # Attempt to launch second instance on different port but SAME data dir
        env2 = env1.copy()
        env2["BACKEND_PORT"] = str(port2)

        start_time = time.monotonic()
        res2 = subprocess.run(
            [PYTHON_BIN, "-m", "app.serve"],
            cwd=BACKEND_DIR,
            env=env2,
            capture_output=True,
            text=True,
            timeout=5,
        )
        duration = time.monotonic() - start_time

        lock_file = data_dir / "camera-monitor.lock"
        assert lock_file.exists()
        locked_pid = read_locked_pid(lock_file)
        assert locked_pid.isdigit()
        assert int(locked_pid) > 0

        assert duration < 3.0, f"Second instance took too long to exit: {duration:.2f}s"
        assert res2.returncode == 4
        assert (
            "Another instance of Camera Monitor is already running on this data folder"
            in res2.stderr
        )
        assert locked_pid in res2.stderr
    finally:
        proc1.terminate()
        try:
            proc1.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc1.kill()
            proc1.wait(timeout=2)


def test_different_instance_occupied_port_exits_3(tmp_path: Path) -> None:
    """Instance on occupied port exits 3 with explanatory message."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>App</html>", encoding="utf-8")

    port = get_free_port()

    # Occupy the port with a raw socket
    occupied_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    so_exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", -5)
    occupied_sock.setsockopt(socket.SOL_SOCKET, so_exclusive, 1)
    occupied_sock.bind(("127.0.0.1", port))
    occupied_sock.listen(5)

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_file = data_dir / "camera_monitor.db"

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    env["LOG_DIR"] = str(tmp_path / "logs")
    env["FRONTEND_DIST"] = str(dist_dir)
    env["BACKEND_PORT"] = str(port)
    env["BACKEND_HOST"] = "127.0.0.1"

    try:
        # Test create_bound_socket with short retry (1s) to keep test fast
        code = f"""
from app.serve import create_bound_socket
create_bound_socket('127.0.0.1', {port}, max_retry_seconds=1)
"""
        res = subprocess.run(
            [PYTHON_BIN, "-c", code],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert res.returncode == 3
        assert "already in use or reserved/blocked by Windows" in res.stderr
        assert "BACKEND_PORT" in res.stderr
    finally:
        occupied_sock.close()


def test_non_loopback_host_exits_2(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>App</html>", encoding="utf-8")

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    env["LOG_DIR"] = str(tmp_path / "logs")
    env["FRONTEND_DIST"] = str(dist_dir)
    env["BACKEND_HOST"] = "192.0.2.1"

    res = subprocess.run(
        [PYTHON_BIN, "-m", "app.serve"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 2
    assert "This program only listens on this computer (127.0.0.1)." in res.stderr


def test_missing_dist_exits_2(tmp_path: Path) -> None:
    empty_dist = tmp_path / "empty_dist"
    empty_dist.mkdir()

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    env["LOG_DIR"] = str(tmp_path / "logs")
    env["FRONTEND_DIST"] = str(empty_dist)
    env["BACKEND_HOST"] = "127.0.0.1"

    res = subprocess.run(
        [PYTHON_BIN, "-m", "app.serve"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 2
    assert "Frontend not built. Run: pnpm --dir frontend build" in res.stderr


def test_hard_kill_releases_lock(tmp_path: Path) -> None:
    """After Popen.kill(), the OS lock is released and a subsequent launch succeeds."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>App</html>", encoding="utf-8")

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_file = data_dir / "camera_monitor.db"
    log_dir = tmp_path / "logs"

    port1 = get_free_port()
    port2 = get_free_port()

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    env["LOG_DIR"] = str(log_dir)
    env["FRONTEND_DIST"] = str(dist_dir)
    env["BACKEND_PORT"] = str(port1)
    env["BACKEND_HOST"] = "127.0.0.1"

    proc = subprocess.Popen(
        [PYTHON_BIN, "-m", "app.serve"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert wait_for_server(port1), "Server failed to start"

    lock_file = data_dir / "camera-monitor.lock"
    assert lock_file.exists()
    server_pid = int(read_locked_pid(lock_file))

    # Hard kill server process using the PID from the lock file
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/F", "/PID", str(server_pid)], check=True)
    else:
        os.kill(server_pid, 9)
    try:
        proc.wait(timeout=3)
    except Exception:
        pass

    # Instance 2 starts on the same data dir
    env["BACKEND_PORT"] = str(port2)
    proc2 = subprocess.Popen(
        [PYTHON_BIN, "-m", "app.serve"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert wait_for_server(port2), (
            "Server 2 failed to acquire lock and start after hard kill"
        )
    finally:
        proc2.terminate()
        try:
            proc2.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc2.kill()
            proc2.wait(timeout=2)


def test_wrapper_kill_orphans_child(tmp_path: Path) -> None:
    """When the wrapper scripts/run_prod.py is killed directly without /T,

    the child server process continues running (orphaned) and the lock is retained.
    """
    repo_root = BACKEND_DIR.parent
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>App</html>", encoding="utf-8")

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_file = data_dir / "camera_monitor.db"
    log_dir = tmp_path / "logs"

    port = get_free_port()
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    env["LOG_DIR"] = str(log_dir)
    env["FRONTEND_DIST"] = str(dist_dir)
    env["BACKEND_PORT"] = str(port)
    env["BACKEND_HOST"] = "127.0.0.1"

    wrapper_script = repo_root / "scripts" / "run_prod.py"
    wrapper_proc = subprocess.Popen(
        [sys.executable, str(wrapper_script)],
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert wait_for_server(port), "Server failed to start via wrapper"

        lock_file = data_dir / "camera-monitor.lock"
        server_pid = int(read_locked_pid(lock_file))

        # Kill the wrapper process directly (without /T)
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(wrapper_proc.pid)], check=True
            )
        else:
            os.kill(wrapper_proc.pid, 9)

        try:
            wrapper_proc.wait(timeout=3)
        except Exception:
            pass

        # Verify child server process is still running (orphaned)
        # and server is still responding to requests
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/health", timeout=1.0
        ) as res:
            assert res.status == 200

        # Terminate the orphaned server process
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/F", "/PID", str(server_pid)], check=True)
        else:
            os.kill(server_pid, 9)

    finally:
        try:
            wrapper_proc.kill()
        except Exception:
            pass


def test_subprocess_run_honors_log_dir(tmp_path: Path) -> None:
    """Subprocess server run honors LOG_DIR and writes strictly to configured path."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>App</html>", encoding="utf-8")

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_file = data_dir / "camera_monitor.db"
    temp_log_dir = tmp_path / "custom_logs"

    port = get_free_port()
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    env["LOG_DIR"] = str(temp_log_dir)
    env["FRONTEND_DIST"] = str(dist_dir)
    env["BACKEND_PORT"] = str(port)
    env["BACKEND_HOST"] = "127.0.0.1"

    proc = subprocess.Popen(
        [PYTHON_BIN, "-m", "app.serve"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert wait_for_server(port)
        log_file = temp_log_dir / "camera-monitor.log"
        assert log_file.is_file(), f"Expected log file at {log_file}"
        assert log_file.stat().st_size > 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
