import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.monitoring.probe import classify, ping_host

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ping"


def _read_fixture(filename: str) -> bytes:
    return (FIXTURES_DIR / filename).read_bytes()


def test_classify_genuine_english_reply() -> None:
    output = _read_fixture("genuine_english_reply.txt")
    assert classify(0, output, "192.0.2.10") is True


def test_classify_request_timed_out() -> None:
    output = _read_fixture("request_timed_out.txt")
    assert classify(1, output, "192.0.2.10") is False
    # Even if exit code were 0, missing TTL makes it offline
    assert classify(0, output, "192.0.2.10") is False


def test_classify_destination_host_unreachable_with_exit_code_zero() -> None:
    """Exit code 0 on Windows router unreachable response must classify as Offline."""
    output = _read_fixture("dest_unreachable.txt")
    assert classify(0, output, "192.0.2.10") is False


def test_classify_general_failure() -> None:
    output = _read_fixture("general_failure.txt")
    assert classify(1, output, "192.0.2.10") is False


def test_classify_empty_output_with_exit_code_zero() -> None:
    output = _read_fixture("empty_output.txt")
    assert classify(0, output, "192.0.2.10") is False


def test_classify_german_genuine_reply() -> None:
    output = _read_fixture("german_genuine_reply.txt")
    assert classify(0, output, "127.0.0.1") is True


def test_classify_german_unreachable_with_exit_code_zero() -> None:
    output = _read_fixture("german_unreachable.txt")
    assert classify(0, output, "192.168.1.102") is False


def test_classify_different_ip_with_ttl_in_reply() -> None:
    """A reply containing TTL= but with a different IP than target must be Offline."""
    output = _read_fixture("different_ip_reply.txt")
    assert classify(0, output, "192.0.2.10") is False


def test_ping_host_timeout_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["ping"], timeout=3.0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert ping_host("192.0.2.10") is False


def test_ping_host_invalid_ip_never_spawns_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_run = MagicMock()
    monkeypatch.setattr(subprocess, "run", mock_run)

    for invalid_ip in [
        "not-an-ip",
        "999.1.1.1",
        "192.168.1.1/24",
        "",
        "127.0.0.1; rm -rf",
    ]:
        result = ping_host(invalid_ip)
        assert result is False

    mock_run.assert_not_called()


def test_ping_host_loopback_real_execution() -> None:
    """Real ping test to localhost 127.0.0.1 must succeed."""
    assert ping_host("127.0.0.1") is True
