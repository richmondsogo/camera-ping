#!/usr/bin/env python3
"""Docs, links, and configuration alignment checker for Camera Monitor.

Standard-library only script to verify:
1. Relative markdown links point to existing files (with URL-decoding,
   skipping docs/steps and unindexed ADR files, and flagging machine-specific
   file:// or drive-letter links).
2. All ADR files are listed in docs/adr/README.md.
3. All top-level docs/*.md files are linked in docs/README.md.
4. All Settings fields in backend/app/config.py are documented in
   docs/configuration.md and .env.example.
5. All environment variables accessed across scripts/**, frontend/*.config.*,
   frontend/e2e/**, and frontend/scripts/** are documented in
   docs/configuration.md or docs/development.md.
6. Fails if zero files are scanned.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys
import urllib.parse

REPO_ROOT = Path(__file__).resolve().parent.parent

# Regex patterns for detecting env vars
ENV_PATTERNS = [
    re.compile(
        r"""(?:os\.(?:environ(?:\[['"]|\.get\(['"]|\.setdefault\(['"])|getenv\(['"])|process\.env(?:\[['"]|\.))([A-Za-z0-9_]+)"""
    )
]

# Markdown link pattern: [label](target) or ![alt](target)
LINK_PATTERN = re.compile(r"""(?:!?)\[[^\]]*\]\(([^)]+)\)""")


def get_docs_files_to_check(repo_root: Path) -> list[Path]:
    """Return the list of markdown files in scope for link checking."""
    files: list[Path] = []

    # Root markdown files
    for name in ["README.md", "AGENTS.md", "DESIGN.md"]:
        p = repo_root / name
        if p.is_file():
            files.append(p)

    # Top-level docs/*.md
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for item in docs_dir.glob("*.md"):
            if item.is_file():
                files.append(item)

    # docs/adr/README.md
    adr_readme = repo_root / "docs" / "adr" / "README.md"
    if adr_readme.is_file():
        files.append(adr_readme)

    return sorted(files)


def check_markdown_links(files: list[Path], repo_root: Path) -> list[str]:
    """Check markdown files for broken relative links and machine-specific paths."""
    errors: list[str] = []

    for file_path in files:
        rel_src = file_path.relative_to(repo_root).as_posix()
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"Cannot read {rel_src}: {e}")
            continue

        for match in LINK_PATTERN.finditer(content):
            raw_target = match.group(1).strip()
            if not raw_target:
                continue

            # Flag machine-specific links
            if raw_target.startswith("file://") or re.search(r"^[a-zA-Z]:[/\\]", raw_target) or re.search(r"file:///[a-zA-Z]:", raw_target):
                errors.append(
                    f"{rel_src}: Machine-specific link target '{raw_target}' is forbidden"
                )
                continue

            # Ignore external links and anchors
            if raw_target.startswith(("http://", "https://", "mailto:")):
                continue

            # Strip anchor part
            path_part = raw_target.split("#")[0].strip()
            if not path_part:
                # In-page anchor link
                continue

            # URL decode %20 etc.
            decoded_path = urllib.parse.unquote(path_part)
            # Normalize slashes
            normalized_path = decoded_path.replace("\\", "/")

            # Resolve relative to the markdown file's directory
            target_path = (file_path.parent / normalized_path).resolve()

            if not target_path.exists():
                errors.append(
                    f"{rel_src}: Broken relative link '{raw_target}' -> '{target_path.as_posix()}' not found"
                )

    return errors


def check_adr_index(repo_root: Path) -> list[str]:
    """Verify that all ADR files are indexed in docs/adr/README.md."""
    errors: list[str] = []
    adr_dir = repo_root / "docs" / "adr"
    if not adr_dir.is_dir():
        return errors

    adr_readme = adr_dir / "README.md"
    if not adr_readme.is_file():
        errors.append("docs/adr/README.md is missing")
        return errors

    content = adr_readme.read_text(encoding="utf-8")
    for adr_file in sorted(adr_dir.glob("*.md")):
        if adr_file.name == "README.md":
            continue
        if adr_file.name not in content:
            errors.append(
                f"docs/adr/README.md: Missing index entry for ADR '{adr_file.name}'"
            )

    return errors


def check_docs_index(repo_root: Path) -> list[str]:
    """Verify that all top-level docs/*.md files are linked in docs/README.md."""
    errors: list[str] = []
    docs_dir = repo_root / "docs"
    if not docs_dir.is_dir():
        return errors

    docs_readme = docs_dir / "README.md"
    if not docs_readme.is_file():
        errors.append("docs/README.md is missing")
        return errors

    content = docs_readme.read_text(encoding="utf-8")
    for doc_file in sorted(docs_dir.glob("*.md")):
        if doc_file.name == "README.md":
            continue
        if doc_file.name not in content:
            errors.append(
                f"docs/README.md: Missing link to top-level doc '{doc_file.name}'"
            )

    return errors


def extract_settings_fields(config_path: Path) -> list[str]:
    """Derive environment variable names from backend Settings class in config.py via AST."""
    if not config_path.is_file():
        return []

    code = config_path.read_text(encoding="utf-8")
    tree = ast.parse(code, filename=str(config_path))

    fields: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    name = item.target.id
                    if not name.startswith("_") and not name.startswith("model_"):
                        fields.append(name.upper())
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            name = target.id
                            if not name.startswith("_") and not name.startswith("model_"):
                                fields.append(name.upper())
    return sorted(fields)


def check_settings_documentation(repo_root: Path) -> list[str]:
    """Verify that all Settings fields are in docs/configuration.md AND .env.example."""
    errors: list[str] = []
    config_path = repo_root / "backend" / "app" / "config.py"
    fields = extract_settings_fields(config_path)

    if not fields:
        errors.append("Could not extract any fields from backend Settings class")
        return errors

    docs_config_path = repo_root / "docs" / "configuration.md"
    env_example_path = repo_root / ".env.example"

    docs_content = (
        docs_config_path.read_text(encoding="utf-8")
        if docs_config_path.is_file()
        else ""
    )
    env_content = (
        env_example_path.read_text(encoding="utf-8")
        if env_example_path.is_file()
        else ""
    )

    for field in fields:
        if field not in docs_content:
            errors.append(
                f"docs/configuration.md: Missing documentation for Settings field '{field}'"
            )
        if field not in env_content:
            errors.append(
                f".env.example: Missing configuration entry for Settings field '{field}'"
            )

    return errors


def extract_script_and_frontend_env_vars(repo_root: Path) -> set[str]:
    """Scan scripts/**, frontend/*.config.*, frontend/e2e/**, and frontend/scripts/** for env vars."""
    detected: set[str] = set()

    scan_targets: list[Path] = []

    # scripts/**
    scripts_dir = repo_root / "scripts"
    if scripts_dir.is_dir():
        scan_targets.extend(p for p in scripts_dir.rglob("*") if p.is_file())

    # frontend/*.config.*
    frontend_dir = repo_root / "frontend"
    if frontend_dir.is_dir():
        for p in frontend_dir.glob("*.config.*"):
            if p.is_file():
                scan_targets.append(p)

    # frontend/e2e/**
    e2e_dir = repo_root / "frontend" / "e2e"
    if e2e_dir.is_dir():
        scan_targets.extend(p for p in e2e_dir.rglob("*") if p.is_file())

    # frontend/scripts/**
    fe_scripts_dir = repo_root / "frontend" / "scripts"
    if fe_scripts_dir.is_dir():
        scan_targets.extend(p for p in fe_scripts_dir.rglob("*") if p.is_file())

    for path in scan_targets:
        if path.suffix.lower() not in [".py", ".ts", ".tsx", ".js", ".mjs", ".cjs"]:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern in ENV_PATTERNS:
            for match in pattern.finditer(content):
                var_name = match.group(1)
                # Keep valid env var identifiers (uppercase or alphanumeric)
                if var_name:
                    detected.add(var_name)

    return detected


def check_env_vars_documentation(repo_root: Path) -> list[str]:
    """Verify that every detected env var is in docs/configuration.md or docs/development.md."""
    errors: list[str] = []
    detected_vars = extract_script_and_frontend_env_vars(repo_root)

    docs_config = repo_root / "docs" / "configuration.md"
    docs_dev = repo_root / "docs" / "development.md"

    config_text = (
        docs_config.read_text(encoding="utf-8") if docs_config.is_file() else ""
    )
    dev_text = docs_dev.read_text(encoding="utf-8") if docs_dev.is_file() else ""

    for var in sorted(detected_vars):
        if var not in config_text and var not in dev_text:
            errors.append(
                f"Environment variable '{var}' is accessed in code but not documented in docs/configuration.md or docs/development.md"
            )

    return errors


def run_all_docs_checks(repo_root: Path) -> list[str]:
    """Run full suite of docs, links, and configuration checks."""
    all_errors: list[str] = []

    files = get_docs_files_to_check(repo_root)
    if len(files) == 0:
        all_errors.append("Scanned zero documentation files! Check configuration.")
        return all_errors

    print(f"Scanned {len(files)} markdown file(s) for links.")
    all_errors.extend(check_markdown_links(files, repo_root))
    all_errors.extend(check_adr_index(repo_root))
    all_errors.extend(check_docs_index(repo_root))
    all_errors.extend(check_settings_documentation(repo_root))
    all_errors.extend(check_env_vars_documentation(repo_root))

    return all_errors


def main() -> None:
    errors = run_all_docs_checks(REPO_ROOT)
    if errors:
        print(f"\n[FAIL] {len(errors)} documentation error(s) found:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("[PASS] All documentation links, ADR indexes, and configuration mappings verified successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
