import os
import platform
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from app.config import BACKEND_DIR

IS_WINDOWS = platform.system() == "Windows"
PYTHON_BIN = sys.executable


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_for_server(port: int, timeout: float = 25.0) -> bool:
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


def make_dummy_frontend(tmp_path: Path) -> Path:
    dist = tmp_path / "frontend_dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        "<!doctype html><html>App</html>", encoding="utf-8"
    )
    return dist


def test_home_layout_created_and_lifecycle(tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    dist_dir = make_dummy_frontend(tmp_path)
    port = get_free_port()

    env = os.environ.copy()
    env["BACKEND_PORT"] = str(port)
    env["BACKEND_HOST"] = "127.0.0.1"

    proc = subprocess.Popen(
        [
            PYTHON_BIN,
            "-m",
            "app.serve",
            "--home",
            str(home_dir),
            "--frontend-dist",
            str(dist_dir),
        ],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert wait_for_server(port), "Server failed to start in time"
        assert (home_dir / "data" / "camera_monitor.db").is_file()
        log_file = home_dir / "logs" / "camera-monitor.log"
        assert log_file.is_file()
        log_content = log_file.read_text(encoding="utf-8")
        assert "Camera Monitor" in log_content
        assert f"home={home_dir}" in log_content
        assert f"port={port}" in log_content
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


def test_home_env_file_honored(tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = make_dummy_frontend(tmp_path)
    port = get_free_port()

    env_file = home_dir / "camera-monitor.env"
    env_file.write_text(
        f"# test comment\nBACKEND_PORT={port}\nMONITOR_INTERVAL_SECONDS=15\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.pop("BACKEND_PORT", None)
    env["BACKEND_HOST"] = "127.0.0.1"

    proc = subprocess.Popen(
        [
            PYTHON_BIN,
            "-m",
            "app.serve",
            "--home",
            str(home_dir),
            "--frontend-dist",
            str(dist_dir),
        ],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert wait_for_server(port), (
            f"Server did not start on port {port} from env file"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


def test_home_env_var_beats_file(tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = make_dummy_frontend(tmp_path)
    file_port = get_free_port()
    real_port = get_free_port()

    env_file = home_dir / "camera-monitor.env"
    env_file.write_text(f"BACKEND_PORT={file_port}\n", encoding="utf-8")

    env = os.environ.copy()
    env["BACKEND_PORT"] = str(real_port)
    env["BACKEND_HOST"] = "127.0.0.1"

    proc = subprocess.Popen(
        [
            PYTHON_BIN,
            "-m",
            "app.serve",
            "--home",
            str(home_dir),
            "--frontend-dist",
            str(dist_dir),
        ],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert wait_for_server(real_port), "Server should have started on real env port"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


def test_home_unknown_key_and_malformed_line_warns(tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = make_dummy_frontend(tmp_path)
    port = get_free_port()

    env_file = home_dir / "camera-monitor.env"
    env_file.write_text(
        "UNKNOWN_DISALLOWED_KEY=123\n"
        "malformed line with no equals\n"
        f"BACKEND_PORT={port}\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.pop("BACKEND_PORT", None)
    env["BACKEND_HOST"] = "127.0.0.1"

    proc = subprocess.Popen(
        [
            PYTHON_BIN,
            "-m",
            "app.serve",
            "--home",
            str(home_dir),
            "--frontend-dist",
            str(dist_dir),
        ],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert wait_for_server(port)
        log_file = home_dir / "logs" / "camera-monitor.log"
        assert log_file.is_file()
        log_content = log_file.read_text(encoding="utf-8")
        assert "Ignoring unauthorized or unknown key" in log_content
        assert "Ignoring malformed line" in log_content
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


def test_home_port_busy_writes_to_log_and_exits_3(tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = make_dummy_frontend(tmp_path)
    port = get_free_port()

    # Pre-occupy port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    so_exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", -5)
    sock.setsockopt(socket.SOL_SOCKET, so_exclusive, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(1)

    env = os.environ.copy()
    env["BACKEND_PORT"] = str(port)
    env["BACKEND_HOST"] = "127.0.0.1"

    try:
        proc = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "app.serve",
                "--home",
                str(home_dir),
                "--frontend-dist",
                str(dist_dir),
            ],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert proc.returncode == 3
        log_file = home_dir / "logs" / "camera-monitor.log"
        assert log_file.is_file()
        log_content = log_file.read_text(encoding="utf-8")
        assert (
            f"Port {port} is already in use" in log_content
            or "Choose another port" in log_content
        )
        assert "starting" in log_content
    finally:
        sock.close()


def test_home_second_instance_exits_4_and_logs(tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    dist_dir = make_dummy_frontend(tmp_path)
    port1 = get_free_port()
    port2 = get_free_port()

    env1 = os.environ.copy()
    env1["BACKEND_PORT"] = str(port1)
    env1["BACKEND_HOST"] = "127.0.0.1"

    proc1 = subprocess.Popen(
        [
            PYTHON_BIN,
            "-m",
            "app.serve",
            "--home",
            str(home_dir),
            "--frontend-dist",
            str(dist_dir),
        ],
        cwd=BACKEND_DIR,
        env=env1,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert wait_for_server(port1)

        env2 = os.environ.copy()
        env2["BACKEND_PORT"] = str(port2)
        env2["BACKEND_HOST"] = "127.0.0.1"

        proc2 = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "app.serve",
                "--home",
                str(home_dir),
                "--frontend-dist",
                str(dist_dir),
            ],
            cwd=BACKEND_DIR,
            env=env2,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc2.returncode == 4
        log_file = home_dir / "logs" / "camera-monitor.log"
        log_content = log_file.read_text(encoding="utf-8")
        assert "Another instance of Camera Monitor is already running" in log_content
    finally:
        proc1.terminate()
        try:
            proc1.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc1.kill()
            proc1.wait(timeout=2)


def test_home_non_loopback_refused_and_logs_in_home_mode(tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    dist_dir = make_dummy_frontend(tmp_path)

    env = os.environ.copy()
    env["BACKEND_HOST"] = "192.0.2.1"

    proc = subprocess.run(
        [
            PYTHON_BIN,
            "-m",
            "app.serve",
            "--home",
            str(home_dir),
            "--frontend-dist",
            str(dist_dir),
        ],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 2
    log_file = home_dir / "logs" / "camera-monitor.log"
    assert log_file.is_file()
    log_content = log_file.read_text(encoding="utf-8")
    assert "This program only listens on this computer (127.0.0.1)." in log_content
