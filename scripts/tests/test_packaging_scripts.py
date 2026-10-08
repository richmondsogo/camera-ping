import ast
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGING_DIR = REPO_ROOT / "packaging" / "windows"


def run_packaging_script(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute a packaging script, strictly enforcing that -DryRun is present."""
    if "-DryRun" not in args:
        raise ValueError(
            f"Safety Violation: Invocations of packaging scripts in tests must include '-DryRun'. Received: {args}"
        )
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        args,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        env=merged_env,
    )


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
            res_dry = run_packaging_script(
                ["cmd.exe", "/c", str(verify_cmd), "-DryRun"],
                cwd=temp_path,
            )
            self.assertEqual(
                res_dry.returncode,
                0,
                f"verify-install.cmd -DryRun failed (code {res_dry.returncode}):\n{res_dry.stderr}\n{res_dry.stdout}",
            )

            # 2. Deliberately failing preflight via launcher must pass through non-zero exit code (exit code 1)
            # The production task name guard fires under -DryRun as the first executable statement.
            res_fail = run_packaging_script(
                ["cmd.exe", "/c", str(verify_cmd), "-TaskName", "CameraMonitor", "-DryRun"],
                cwd=temp_path,
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
        res_task = run_packaging_script(
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
            ]
        )
        self.assertNotEqual(res_task.returncode, 0)
        self.assertIn("Safety Violation", res_task.stderr + res_task.stdout)

        # Refuse production install path
        res_path = run_packaging_script(
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
            ]
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
            res_with_file = run_packaging_script(
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
                ]
            )
            self.assertEqual(res_with_file.returncode, 0)
            output = res_with_file.stdout
            self.assertIn("Would restore AC sleep (15 min) and hibernate (30 min)", output)

            # Test DryRun when power-before.txt is missing
            power_file.unlink()
            res_without_file = run_packaging_script(
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
                ]
            )
            self.assertEqual(res_without_file.returncode, 0)
            output_missing = res_without_file.stdout
            self.assertIn("power-before.txt found; leaving power settings unchanged", output_missing)

    def test_derived_backup_task_names_dry_run(self) -> None:
        """Verify default and custom TaskName derive '<TaskName> Backup' across scripts in DryRun."""
        install_ps1 = PACKAGING_DIR / "install.ps1"
        uninstall_ps1 = PACKAGING_DIR / "uninstall.ps1"
        status_ps1 = PACKAGING_DIR / "status.ps1"
        verify_ps1 = PACKAGING_DIR / "verify-install.ps1"

        # 1. install.ps1: default vs custom
        res_inst_def = run_packaging_script(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(install_ps1), "-DryRun"]
        )
        self.assertEqual(res_inst_def.returncode, 0)
        self.assertIn("Backup Task:         CameraMonitor Backup", res_inst_def.stdout)

        res_inst_custom = run_packaging_script(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(install_ps1),
                "-TaskName",
                "CameraMonitorTest",
                "-DryRun",
            ]
        )
        self.assertEqual(res_inst_custom.returncode, 0)
        self.assertIn("Backup Task:         CameraMonitorTest Backup", res_inst_custom.stdout)

        # 2. uninstall.ps1: default vs custom
        res_uninst_def = run_packaging_script(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(uninstall_ps1), "-DryRun"]
        )
        self.assertEqual(res_uninst_def.returncode, 0)
        self.assertIn("Scheduled Tasks:     CameraMonitor, CameraMonitor Backup", res_uninst_def.stdout)

        res_uninst_custom = run_packaging_script(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(uninstall_ps1),
                "-TaskName",
                "CameraMonitorTest",
                "-DryRun",
            ]
        )
        self.assertEqual(res_uninst_custom.returncode, 0)
        self.assertIn("Scheduled Tasks:     CameraMonitorTest, CameraMonitorTest Backup", res_uninst_custom.stdout)

        # 3. status.ps1: default vs custom
        res_stat_def = run_packaging_script(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(status_ps1), "-DryRun"]
        )
        self.assertEqual(res_stat_def.returncode, 0)
        self.assertIn("Backup Task: 'CameraMonitor Backup'", res_stat_def.stdout)

        res_stat_custom = run_packaging_script(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(status_ps1),
                "-TaskName",
                "CameraMonitorTest",
                "-DryRun",
            ]
        )
        self.assertEqual(res_stat_custom.returncode, 0)
        self.assertIn("Backup Task: 'CameraMonitorTest Backup'", res_stat_custom.stdout)

        # 4. verify-install.ps1: default vs custom
        res_ver_def = run_packaging_script(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(verify_ps1), "-DryRun"]
        )
        self.assertEqual(res_ver_def.returncode, 0)
        self.assertIn("Backup Task Name:   CameraMonitorTest Backup", res_ver_def.stdout)

        res_ver_custom = run_packaging_script(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(verify_ps1),
                "-TaskName",
                "CustomMonitorTest",
                "-DryRun",
            ]
        )
        self.assertEqual(res_ver_custom.returncode, 0)
        self.assertIn("Backup Task Name:   CustomMonitorTest Backup", res_ver_custom.stdout)

    def test_no_hardcoded_backup_task_name_outside_defaults_or_guards(self) -> None:
        """Verify no packaging script hardcodes 'CameraMonitor Backup' outside parameter defaults and production guards."""
        target_str = "CameraMonitor Backup"
        for script_path in PACKAGING_DIR.glob("*.ps1"):
            content = script_path.read_text(encoding="ascii")
            if target_str in content:
                # Allowed only in verify-install.ps1 for production guardrail & existence check
                if script_path.name == "verify-install.ps1":
                    lines = [
                        line.strip()
                        for line in content.splitlines()
                        if target_str in line and not line.strip().startswith("#")
                    ]
                    for line in lines:
                        self.assertTrue(
                            "forbiddenNames" in line
                            or "Test-ScheduledTaskExists" in line
                            or "Write-Error" in line,
                            f"Unexpected hardcoded occurrence in {script_path.name}: {line}",
                        )
                else:
                    self.fail(f"Found hardcoded '{target_str}' in {script_path.name}")

    def test_no_restart_count_3_in_code_or_docs(self) -> None:
        """Ensure neither 'RestartCount=3' nor 'RestartCount 3' appears in codebase or docs (must be 999)."""
        forbidden_patterns = ["RestartCount=3", "RestartCount 3"]
        repo_files = list(REPO_ROOT.glob("docs/**/*.md")) + list(REPO_ROOT.glob("packaging/**/*.*"))
        for f in repo_files:
            if f.is_file():
                text = f.read_text(encoding="utf-8", errors="ignore")
                for pat in forbidden_patterns:
                    self.assertNotIn(pat, text, f"Found forbidden '{pat}' in {f.relative_to(REPO_ROOT)}")

    def test_task_name_validation_good_and_bad_values(self) -> None:
        """Validate TaskName rules (letters, digits, space, dash, underscore, 1-64 chars) across all 6 scripts."""
        scripts_to_test = [
            PACKAGING_DIR / "install.ps1",
            PACKAGING_DIR / "uninstall.ps1",
            PACKAGING_DIR / "status.ps1",
            PACKAGING_DIR / "start.ps1",
            PACKAGING_DIR / "stop.ps1",
            PACKAGING_DIR / "verify-install.ps1",
        ]

        good_values = [
            "ValidTaskName",
            "Valid-Task_Name 123",
            "A" * 64,
        ]

        bad_values = [
            'Task"Name',
            'Task\\Name',
            'Task/Name',
            'Task;Name',
            "A" * 65,
        ]

        for script in scripts_to_test:
            # Test bad values
            for bad in bad_values:
                res = run_packaging_script(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(script),
                        "-TaskName",
                        bad,
                        "-DryRun",
                    ]
                )
                self.assertEqual(
                    res.returncode,
                    1,
                    f"{script.name} should reject bad TaskName '{bad}', got code {res.returncode}\n{res.stderr}\n{res.stdout}",
                )
                output = " ".join((res.stderr + res.stdout).split())
                self.assertIn("Invalid TaskName", output)
                self.assertIn("1 to 64 characters", output)

            # Test good values
            for good in good_values:
                res = run_packaging_script(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(script),
                        "-TaskName",
                        good,
                        "-DryRun",
                    ]
                )
                self.assertEqual(
                    res.returncode,
                    0,
                    f"{script.name} should accept valid TaskName '{good}', got code {res.returncode}\n{res.stderr}\n{res.stdout}",
                )

    def test_verify_install_refuses_when_existing_production_task_simulated(self) -> None:
        """Verify verify-install.ps1 refuses to run when production task is simulated via CAMERA_MONITOR_TEST_EXISTING_TASK=1."""
        verify_ps1 = PACKAGING_DIR / "verify-install.ps1"
        res = run_packaging_script(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(verify_ps1),
                "-DryRun",
            ],
            env={"CAMERA_MONITOR_TEST_EXISTING_TASK": "1"},
        )
        self.assertEqual(res.returncode, 1)
        output = " ".join((res.stderr + res.stdout).split())
        self.assertIn("Safety Violation", output)
        self.assertIn("already exists", output)

    def test_real_task_lookup_reports_not_found_without_elevation(self) -> None:
        """Run real Get-ScheduledTask lookup against a random nonexistent name and assert it reports not found without elevation."""
        random_task_name = f"CameraMonitorNonExistent_{uuid.uuid4().hex[:12]}"
        cmd = (
            f"$t = Get-ScheduledTask -TaskName '{random_task_name}' -ErrorAction SilentlyContinue; "
            f"if ($null -eq $t) {{ 'NOT_FOUND' }} else {{ 'FOUND' }}"
        )
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", cmd],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "NOT_FOUND")

    def test_elevation_injection_preflight_messages_dry_run(self) -> None:
        """Test CAMERA_MONITOR_TEST_ELEVATED=0|1 preflight notices in DryRun mode."""
        install_ps1 = PACKAGING_DIR / "install.ps1"
        uninstall_ps1 = PACKAGING_DIR / "uninstall.ps1"
        verify_ps1 = PACKAGING_DIR / "verify-install.ps1"

        # Case 0: simulated non-elevated
        res_inst_0 = run_packaging_script(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(install_ps1), "-DryRun"],
            env={"CAMERA_MONITOR_TEST_ELEVATED": "0"},
        )
        self.assertEqual(res_inst_0.returncode, 0)
        self.assertIn("Notice: Script is running without elevation", res_inst_0.stdout)

        res_uninst_0 = run_packaging_script(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(uninstall_ps1), "-DryRun"],
            env={"CAMERA_MONITOR_TEST_ELEVATED": "0"},
        )
        self.assertEqual(res_uninst_0.returncode, 0)
        self.assertIn("Notice: Script is running without elevation", res_uninst_0.stdout)

        res_ver_0 = run_packaging_script(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(verify_ps1), "-DryRun"],
            env={"CAMERA_MONITOR_TEST_ELEVATED": "0"},
        )
        self.assertEqual(res_ver_0.returncode, 0)
        self.assertIn("Notice: Session is NOT elevated", res_ver_0.stdout)
        self.assertIn("Administrator:      False", res_ver_0.stdout)

        # Case 1: simulated elevated
        res_inst_1 = run_packaging_script(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(install_ps1), "-DryRun"],
            env={"CAMERA_MONITOR_TEST_ELEVATED": "1"},
        )
        self.assertEqual(res_inst_1.returncode, 0)
        self.assertNotIn("without elevation", res_inst_1.stdout)

        res_uninst_1 = run_packaging_script(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(uninstall_ps1), "-DryRun"],
            env={"CAMERA_MONITOR_TEST_ELEVATED": "1"},
        )
        self.assertEqual(res_uninst_1.returncode, 0)
        self.assertNotIn("without elevation", res_uninst_1.stdout)

        res_ver_1 = run_packaging_script(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(verify_ps1), "-DryRun"],
            env={"CAMERA_MONITOR_TEST_ELEVATED": "1"},
        )
        self.assertEqual(res_ver_1.returncode, 0)
        self.assertNotIn("Notice: Session is NOT elevated", res_ver_1.stdout)
        self.assertIn("Administrator:      True", res_ver_1.stdout)

    def test_elevation_injection_ignored_without_dryrun(self) -> None:
        """Verify that CAMERA_MONITOR_TEST_ELEVATED is ignored without -DryRun.

        Verification method:
        1. Static assertion on packaging scripts: every script strictly checks $DryRun before inspecting
           $env:CAMERA_MONITOR_TEST_ELEVATED.
        2. Execution of the script elevation check logic under $DryRun = $false with CAMERA_MONITOR_TEST_ELEVATED=1
           asserts $isAdmin remains False on non-elevated sessions.
        """
        for script_name in ["install.ps1", "uninstall.ps1", "verify-install.ps1"]:
            content = (PACKAGING_DIR / script_name).read_text(encoding="ascii")
            self.assertIn(
                'if ($DryRun -and ($env:CAMERA_MONITOR_TEST_ELEVATED -eq "0" -or $env:CAMERA_MONITOR_TEST_ELEVATED -eq "1"))',
                content,
                f"{script_name} must gate CAMERA_MONITOR_TEST_ELEVATED evaluation behind $DryRun",
            )

        # Run PowerShell execution verifying logic path ignores the env var when DryRun is false
        cmd = (
            "$DryRun = $false; "
            "$isAdmin = $false; "
            "if ($DryRun -and ($env:CAMERA_MONITOR_TEST_ELEVATED -eq '0' -or $env:CAMERA_MONITOR_TEST_ELEVATED -eq '1')) { "
            "    $isAdmin = ($env:CAMERA_MONITOR_TEST_ELEVATED -eq '1'); "
            "}; "
            "Write-Output $isAdmin"
        )
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", cmd],
            capture_output=True,
            text=True,
            env={**os.environ, "CAMERA_MONITOR_TEST_ELEVATED": "1"},
        )
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "False")

    def test_dry_run_creates_no_filesystem_or_task_artifacts(self) -> None:
        """Verify that running install.ps1 and verify-install.ps1 in -DryRun creates NO folders or files."""
        install_ps1 = PACKAGING_DIR / "install.ps1"
        verify_ps1 = PACKAGING_DIR / "verify-install.ps1"

        with tempfile.TemporaryDirectory(prefix="camera_dryrun_fs_") as temp_dir:
            temp_root = Path(temp_dir)
            fake_install = temp_root / "NonExistentInstall"
            fake_home = temp_root / "NonExistentHome"

            # 1. install.ps1 -DryRun
            res_inst = run_packaging_script(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(install_ps1),
                    "-InstallPath",
                    str(fake_install),
                    "-HomePath",
                    str(fake_home),
                    "-DryRun",
                ]
            )
            self.assertEqual(res_inst.returncode, 0)
            self.assertFalse(fake_install.exists(), f"{fake_install} was created during install.ps1 -DryRun!")
            self.assertFalse(fake_home.exists(), f"{fake_home} was created during install.ps1 -DryRun!")
            self.assertEqual(list(temp_root.iterdir()), [])

            # 2. verify-install.ps1 -DryRun
            res_ver = run_packaging_script(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(verify_ps1),
                    "-TestInstallPath",
                    str(fake_install),
                    "-TestHomePath",
                    str(fake_home),
                    "-DryRun",
                ]
            )
            self.assertEqual(res_ver.returncode, 0)
            self.assertFalse(fake_install.exists(), f"{fake_install} was created during verify-install.ps1 -DryRun!")
            self.assertFalse(fake_home.exists(), f"{fake_home} was created during verify-install.ps1 -DryRun!")
            self.assertEqual(list(temp_root.iterdir()), [])

    def test_scanner_enforces_run_packaging_script_and_dry_run(self) -> None:
        """Scan test_packaging_scripts.py to ensure every invocation routes through run_packaging_script with -DryRun."""
        test_file = Path(__file__).resolve()
        source_text = test_file.read_text(encoding="utf-8")
        tree = ast.parse(source_text, filename=str(test_file))

        packaging_names = {
            "install.ps1",
            "install.cmd",
            "uninstall.ps1",
            "uninstall.cmd",
            "restore.ps1",
            "restore.cmd",
            "verify-install.ps1",
            "verify-install.cmd",
            "status.ps1",
            "status.cmd",
            "start.ps1",
            "start.cmd",
            "stop.ps1",
            "stop.cmd",
        }

        class PackagingCallVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.violations: list[str] = []
                self.current_func: str | None = None

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                old_func = self.current_func
                self.current_func = node.name
                self.generic_visit(node)
                self.current_func = old_func

            def visit_Call(self, node: ast.Call) -> None:
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name == "run_packaging_script":
                    has_dry_run = False
                    if node.args and isinstance(node.args[0], ast.List):
                        for elt in node.args[0].elts:
                            if isinstance(elt, ast.Constant) and elt.value == "-DryRun":
                                has_dry_run = True
                                break
                    if not has_dry_run:
                        self.violations.append(
                            f"Call to run_packaging_script in '{self.current_func}' missing '-DryRun' argument."
                        )
                elif self.current_func != "run_packaging_script":
                    is_exec_call = False
                    if isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name) and node.func.value.id in {"subprocess", "os"}:
                            is_exec_call = True
                    elif isinstance(node.func, ast.Name):
                        if node.func.id in {"system", "popen", "spawn"}:
                            is_exec_call = True

                    if is_exec_call:
                        for arg in node.args:
                            arg_str = ast.unparse(arg)
                            for pkg_name in packaging_names:
                                if pkg_name in arg_str:
                                    self.violations.append(
                                        f"Direct execution of '{pkg_name}' found in '{self.current_func}' outside run_packaging_script: {arg_str}"
                                    )

                self.generic_visit(node)

        visitor = PackagingCallVisitor()
        visitor.visit(tree)
        self.assertEqual(
            visitor.violations,
            [],
            f"Scanner detected forbidden packaging script invocations:\n" + "\n".join(visitor.violations),
        )


if __name__ == "__main__":
    unittest.main()
