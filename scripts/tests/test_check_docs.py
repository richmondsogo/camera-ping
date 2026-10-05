"""Unit tests for docs, links, and configuration checker."""

from pathlib import Path
import tempfile
import unittest

from scripts.check_docs import (
    check_adr_index,
    check_docs_index,
    check_env_vars_documentation,
    check_markdown_links,
    check_settings_documentation,
    extract_script_and_frontend_env_vars,
    extract_settings_fields,
    get_docs_files_to_check,
)


class TestCheckDocs(unittest.TestCase):
    def test_file_uri_link_fails(self) -> None:
        """A link starting with file:// is rejected as machine-specific."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            md_file = tmppath / "test.md"
            md_file.write_text("[bad link](file:///C:/Users/name/repo/file.txt)", encoding="utf-8")

            errors = check_markdown_links([md_file], tmppath)
            self.assertTrue(any("Machine-specific link target" in e for e in errors))

    def test_percent_20_link_to_existing_file_passes(self) -> None:
        """A link with %20 targeting an existing file resolves correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            target_file = tmppath / "target file.md"
            target_file.write_text("# Target", encoding="utf-8")

            src_file = tmppath / "source.md"
            src_file.write_text("[target link](target%20file.md)", encoding="utf-8")

            errors = check_markdown_links([src_file], tmppath)
            self.assertEqual(errors, [])

    def test_link_into_docs_steps_skipped_from_file_scanner(self) -> None:
        """docs/steps/ files are never included in the checked files list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            docs_steps = tmppath / "docs" / "steps"
            docs_steps.mkdir(parents=True)
            step_file = docs_steps / "step-01.md"
            step_file.write_text("[broken link](nonexistent.md)", encoding="utf-8")

            files = get_docs_files_to_check(tmppath)
            self.assertNotIn(step_file, files)

    def test_missing_relative_target_fails(self) -> None:
        """A missing relative target link is flagged as broken."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            src_file = tmppath / "doc.md"
            src_file.write_text("[missing](does-not-exist.md)", encoding="utf-8")

            errors = check_markdown_links([src_file], tmppath)
            self.assertTrue(any("Broken relative link" in e for e in errors))

    def test_adr_indexing(self) -> None:
        """ADRs missing from docs/adr/README.md are flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            adr_dir = tmppath / "docs" / "adr"
            adr_dir.mkdir(parents=True)
            (adr_dir / "README.md").write_text("# ADRs\n- 0001-stack.md", encoding="utf-8")
            (adr_dir / "0001-stack.md").write_text("# Stack", encoding="utf-8")
            (adr_dir / "0002-git.md").write_text("# Git", encoding="utf-8")

            errors = check_adr_index(tmppath)
            self.assertEqual(len(errors), 1)
            self.assertIn("0002-git.md", errors[0])

    def test_docs_indexing(self) -> None:
        """Top-level docs missing from docs/README.md are flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            docs_dir = tmppath / "docs"
            docs_dir.mkdir(parents=True)
            (docs_dir / "README.md").write_text("# Index\n- [guide](guide.md)", encoding="utf-8")
            (docs_dir / "guide.md").write_text("# Guide", encoding="utf-8")
            (docs_dir / "unlinked.md").write_text("# Unlinked", encoding="utf-8")

            errors = check_docs_index(tmppath)
            self.assertEqual(len(errors), 1)
            self.assertIn("unlinked.md", errors[0])

    def test_settings_documentation_check(self) -> None:
        """Settings fields missing from configuration.md or .env.example are flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            app_dir = tmppath / "backend" / "app"
            app_dir.mkdir(parents=True)
            (app_dir / "config.py").write_text(
                "class Settings:\n    secret_token: str = 'x'\n",
                encoding="utf-8",
            )
            docs_dir = tmppath / "docs"
            docs_dir.mkdir()
            (docs_dir / "configuration.md").write_text("No settings here", encoding="utf-8")
            (tmppath / ".env.example").write_text("No settings here", encoding="utf-8")

            errors = check_settings_documentation(tmppath)
            self.assertTrue(any("SECRET_TOKEN" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
