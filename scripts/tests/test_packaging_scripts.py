import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGING_DIR = REPO_ROOT / "packaging" / "windows"


class TestPackagingScripts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not PACKAGING_DIR.is_dir():
            raise unittest.SkipTest("packaging/windows directory does not exist")

    def test_all_powershell_scripts_syntax(self) -> None:
        """Parse all .ps1 files with PowerShell language parser."""
        ps1_files = list(PACKAGING_DIR.glob("*.ps1"))
        self.assertGreater(len(ps1_files), 0, "No .ps1 files found in packaging/windows")

        parse_script = (
            "$files = Get-ChildItem -Path $args[0] -Filter '*.ps1'; "
            "$failed = @(); "
            "foreach ($f in $files) { "
            "    $errors = $null; $tokens = $null; "
            "    [System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$tokens, [ref]$errors); "
            "    if ($errors) { $failed += \"$($f.Name): \" + ($errors | Out-String) } "
            "}; "
            "if ($failed.Count -gt 0) { "
            "    Write-Error ($failed -join \"`n\"); exit 1 "
            "}"
        )

        pkg_dir_escaped = str(PACKAGING_DIR).replace("'", "''")
        cmd_str = f"& {{ {parse_script} }} '{pkg_dir_escaped}'"
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", cmd_str],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            res.returncode,
            0,
            f"PowerShell syntax errors detected:\n{res.stderr}\n{res.stdout}",
        )

    def test_scripts_are_pure_ascii(self) -> None:
        """Verify all scripts contain strictly ASCII characters."""
        for script_file in PACKAGING_DIR.glob("*.*"):
            if script_file.suffix.lower() in [".ps1", ".cmd"]:
                content = script_file.read_bytes()
                try:
                    content.decode("ascii")
                except UnicodeDecodeError as exc:
                    self.fail(f"Non-ASCII character detected in {script_file.name}: {exc}")

    def test_cmd_launchers_paired_and_quoted(self) -> None:
        """Ensure every .cmd has a corresponding .ps1 and quotes %~dp0 correctly."""
        cmd_files = list(PACKAGING_DIR.glob("*.cmd"))
        self.assertGreater(len(cmd_files), 0, "No .cmd files found in packaging/windows")

        for cmd_file in cmd_files:
            ps1_file = cmd_file.with_suffix(".ps1")
            self.assertTrue(ps1_file.is_file(), f"Missing paired .ps1 for {cmd_file.name}")

            text = cmd_file.read_text(encoding="ascii")
            self.assertIn('%~dp0', text, f"{cmd_file.name} does not reference %~dp0")
            self.assertIn('"%~dp0', text, f"{cmd_file.name} does not properly quote %~dp0")
            self.assertIn("exit /b %ERRORLEVEL%", text, f"{cmd_file.name} does not return %ERRORLEVEL%")

    def test_launcher_path_with_space_and_exit_code_passthrough(self) -> None:
        """Test .cmd launchers in path containing spaces and verify exit code passthrough."""
        with tempfile.TemporaryDirectory(prefix="camera launcher space ") as temp_dir:
            temp_path = Path(temp_dir)
            # Copy all scripts to path with spaces
            for f in PACKAGING_DIR.iterdir():
                if f.is_file():
                    shutil.copy2(f, temp_path / f.name)

            verify_cmd = temp_path / "verify-install.cmd"
            self.assertTrue(verify_cmd.is_file())

            # 1. -DryRun should succeed (exit code 0)
            res_dry = subprocess.run(
                ["cmd.exe", "/c", str(verify_cmd), "-DryRun"],
                cwd=temp_path,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                res_dry.returncode,
                0,
                f"verify-install.cmd -DryRun failed (code {res_dry.returncode}):\n{res_dry.stderr}\n{res_dry.stdout}",
            )

            # 2. Deliberately failing preflight via launcher must pass through non-zero exit code (exit code 1)
            res_fail = subprocess.run(
                ["cmd.exe", "/c", str(verify_cmd), "-TaskName", "CameraMonitor"],
                cwd=temp_path,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                res_fail.returncode,
                1,
                f"verify-install.cmd should return exit code 1 on safety preflight failure, got {res_fail.returncode}",
            )
            self.assertIn(
                "safety violation", (res_fail.stderr + res_fail.stdout).lower()
            )

    def test_verify_install_safety_guardrails(self) -> None:
        """Ensure verify-install refuses production task name or production install paths."""
        verify_ps1 = PACKAGING_DIR / "verify-install.ps1"

        # Refuse production task name CameraMonitor
        res_task = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(verify_ps1),
                "-TestTaskName",
                "CameraMonitor",
                "-DryRun",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res_task.returncode, 0)
        self.assertIn("Safety Violation", res_task.stderr + res_task.stdout)

        # Refuse production install path
        res_path = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(verify_ps1),
                "-TestInstallPath",
                r"C:\Program Files\CameraMonitor",
                "-DryRun",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res_path.returncode, 0)
        self.assertIn("Safety Violation", res_path.stderr + res_path.stdout)

    def test_scheduled_task_definitions_in_install_ps1(self) -> None:
        """Parse install.ps1 and assert all required Scheduled Task parameters."""
        install_ps1 = PACKAGING_DIR / "install.ps1"
        self.assertTrue(install_ps1.is_file())
        content = install_ps1.read_text(encoding="ascii")

        # 1. Main CameraMonitor Task parameters
        self.assertIn('-UserId "S-1-5-18"', content)
        self.assertIn("-RunLevel Highest", content)
        self.assertIn("New-ScheduledTaskTrigger -AtStartup", content)
        self.assertIn('$trigger.Delay = "PT30S"', content)
        self.assertIn('python\\python.exe', content)
        self.assertIn('-m app.serve --home', content)
        self.assertIn('--frontend-dist', content)
        self.assertIn('-WorkingDirectory "$InstallPath\\app"', content)
        self.assertIn("-ExecutionTimeLimit ([TimeSpan]::Zero)", content)
        self.assertIn("-MultipleInstances IgnoreNew", content)
        self.assertIn("-StartWhenAvailable", content)
        self.assertIn("-AllowStartIfOnBatteries", content)
        self.assertIn("-DontStopIfGoingOnBatteries", content)
        self.assertIn("-RestartCount 999", content)
        self.assertIn("-RestartInterval (New-TimeSpan -Minutes 1)", content)

        # 2. Backup Task parameters (daily 03:00, SYSTEM)
        self.assertIn('New-ScheduledTaskTrigger -Daily -At "03:00"', content)
        self.assertIn("-Principal $principal", content)
        self.assertIn('scripts\\backup.ps1', content)

    def test_uninstall_power_settings_restoration(self) -> None:
        """Verify uninstall.ps1 restores AC power settings from power-before.txt."""
        uninstall_ps1 = PACKAGING_DIR / "uninstall.ps1"
        self.assertTrue(uninstall_ps1.is_file())

        with tempfile.TemporaryDirectory(prefix="camera_test_power_") as temp_dir:
            temp_home = Path(temp_dir)
            power_file = temp_home / "power-before.txt"
            power_file.write_text(
                "STANDBY_TIMEOUT_AC=15\nHIBERNATE_TIMEOUT_AC=30\n", encoding="ascii"
            )

            # Test DryRun with power-before.txt present
            res_with_file = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(uninstall_ps1),
                    "-HomeDir",
                    str(temp_home),
                    "-DryRun",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res_with_file.returncode, 0)
            output = res_with_file.stdout
            self.assertIn("Would restore AC sleep (15 min) and hibernate (30 min)", output)

            # Test DryRun when power-before.txt is missing
            power_file.unlink()
            res_without_file = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(uninstall_ps1),
                    "-HomeDir",
                    str(temp_home),
                    "-DryRun",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res_without_file.returncode, 0)
            output_missing = res_without_file.stdout
            self.assertIn("power-before.txt found; leaving power settings unchanged", output_missing)


if __name__ == "__main__":
    unittest.main()
