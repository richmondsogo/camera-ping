import tempfile
import unittest
from pathlib import Path

from scripts.build_bundle import (
    REPO_ROOT,
    create_deterministic_zip,
    generate_pth_content,
    is_excluded,
    verify_bundle_contents,
    verify_sha256,
)


class TestBuildBundleHelpers(unittest.TestCase):
    def test_pth_content_format_and_order(self) -> None:
        expected = "python312.zip\n.\n..\\app\nLib\\site-packages\nimport site\n"
        self.assertEqual(generate_pth_content(), expected)

    def test_exclusion_rules(self) -> None:
        # Forbidden paths
        self.assertTrue(is_excluded("__pycache__"))
        self.assertTrue(is_excluded("app/__pycache__/main.cpython-312.pyc"))
        self.assertTrue(is_excluded(".venv/bin/python"))
        self.assertTrue(is_excluded("backend/tests/test_health.py"))
        self.assertTrue(is_excluded("backend/data/camera_monitor.db"))
        self.assertTrue(is_excluded("backend/.e2e-data/temp.db"))
        self.assertTrue(is_excluded("node_modules/@vitejs/plugin-react"))
        self.assertTrue(is_excluded(".git/HEAD"))
        self.assertTrue(is_excluded("frontend/screenshots/settings.png"))
        self.assertTrue(is_excluded("camera_monitor.db"))
        self.assertTrue(is_excluded("camera_monitor.db-wal"))
        self.assertTrue(is_excluded("camera_monitor.db-shm"))
        self.assertTrue(is_excluded("camera-monitor.log"))
        self.assertTrue(is_excluded("camera-monitor.lock"))
        self.assertTrue(is_excluded(".env"))
        self.assertTrue(is_excluded(".env.production"))
        self.assertTrue(is_excluded("manual.pdf"))

        # Allowed paths
        self.assertFalse(is_excluded("app/main.py"))
        self.assertFalse(is_excluded("app/serve.py"))
        self.assertFalse(is_excluded("alembic.ini"))
        self.assertFalse(is_excluded("alembic/env.py"))
        self.assertFalse(is_excluded("alembic/versions/0001_initial.py"))
        self.assertFalse(is_excluded("frontend/dist/index.html"))
        self.assertFalse(is_excluded("frontend/dist/assets/index.js"))
        self.assertFalse(is_excluded("scripts/install.ps1"))
        self.assertFalse(is_excluded("docs/operator-guide.md"))

    def test_verify_sha256_detects_corruption(self) -> None:
        with tempfile.NamedTemporaryFile("wb", delete=False) as f:
            f.write(b"original data")
            temp_path = Path(f.name)

        try:
            # Hash of b"original data"
            expected_hash = (
                "988841927a7a71a5334419bd893c8dd594a1354029ccdf4cfda3e28600b363c7"
            )
            self.assertTrue(verify_sha256(temp_path, expected_hash))

            # Corrupt file
            temp_path.write_bytes(b"corrupted data")
            self.assertFalse(verify_sha256(temp_path, expected_hash))
        finally:
            temp_path.unlink(missing_ok=True)

    def test_deterministic_zip_produces_identical_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            (source_dir / "b.txt").write_bytes(b"file b content")
            (source_dir / "a.txt").write_bytes(b"file a content")
            sub = source_dir / "subdir"
            sub.mkdir()
            (sub / "c.txt").write_bytes(b"file c content")

            zip1 = Path(temp_dir) / "archive1.zip"
            zip2 = Path(temp_dir) / "archive2.zip"

            size1, sha1 = create_deterministic_zip(source_dir, zip1)
            size2, sha2 = create_deterministic_zip(source_dir, zip2)

            self.assertEqual(size1, size2)
            self.assertEqual(sha1, sha2)
            self.assertEqual(zip1.read_bytes(), zip2.read_bytes())

    def test_verify_bundle_contents_flags_forbidden_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_dir = Path(temp_dir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "app.py").write_text("print('hello')", encoding="utf-8")
            (bundle_dir / "test.db").write_bytes(b"sqlite")
            (bundle_dir / "local_leak.txt").write_text(
                f"path: {REPO_ROOT.as_posix()}", encoding="utf-8"
            )

            violations = verify_bundle_contents(bundle_dir, REPO_ROOT)
            self.assertIn("Forbidden file found in bundle: test.db", violations)
            self.assertTrue(
                any("Absolute repository path found" in v for v in violations)
            )

    def test_requirements_lock_integrity(self) -> None:
        """Assert lockfile contains only runtime deps and no dev/test dependencies."""
        lock_file = REPO_ROOT / "backend" / "requirements.lock"
        self.assertTrue(lock_file.is_file(), f"Missing {lock_file}")

        lines = [
            line.strip().lower()
            for line in lock_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

        # Must have packages
        self.assertGreater(len(lines), 0)

        forbidden_packages = {
            "pytest",
            "httpx",
            "ruff",
            "mypy",
            "mypy-extensions",
            "mypy_extensions",
            "pytest-asyncio",
            "anyio-test",
        }

        package_names = [line.split("==")[0].strip() for line in lines]
        for pkg in package_names:
            self.assertNotIn(
                pkg,
                forbidden_packages,
                f"Forbidden dev/test package '{pkg}' found in requirements.lock",
            )

        # Print summary for audit report
        print(
            f"\n[LOCK AUDIT] backend/requirements.lock contains {len(package_names)} "
            "runtime packages."
        )


if __name__ == "__main__":
    unittest.main()
