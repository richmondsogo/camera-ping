"""Tests for design token linter."""

from pathlib import Path
import unittest

from scripts.lint_tokens import lint_content, lint_directory


class TestLintTokens(unittest.TestCase):
    def test_good_samples_pass(self) -> None:
        good_sample = """
        export function ValidComponent() {
            return (
                <div className="max-w-page p-6 bg-background text-foreground border border-border rounded-control shadow-none">
                    <h1 className="text-page-title text-foreground">Dashboard</h1>
                    <h2 className="text-section-heading text-muted-foreground">Cameras</h2>
                    <p className="text-sm text-foreground">Status summary</p>
                    <span className="text-xs text-muted-foreground">Last updated</span>
                    <table className="text-table tabular-nums">
                        <tbody>
                            <tr className="hover:bg-muted data-[state=open]:bg-accent [&>svg]:size-4">
                                <td className="text-table">192.0.2.10</td>
                            </tr>
                        </tbody>
                    </table>
                    <button className="h-8 rounded-control bg-primary text-primary-foreground focus-visible:ring-2 focus-visible:ring-ring">
                        Click
                    </button>
                    <div className="max-w-[var(--container-page)]" />
                </div>
            );
        }
        """
        violations = lint_content(good_sample, Path("test.tsx"))
        self.assertEqual(violations, [])

    def test_bad_palette_colors_fail(self) -> None:
        samples = [
            ('<div className="bg-blue-500" />', "bg-blue-500"),
            ('<div className="hover:text-gray-400" />', "hover:text-gray-400"),
            ('<div className="bg-white" />', "bg-white"),
            ('<div className="text-black" />', "text-black"),
            ('<div className="bg-black/40" />', "bg-black/40"),
            ('<div className="border-red-600" />', "border-red-600"),
        ]
        for snippet, match_expected in samples:
            with self.subTest(snippet=snippet):
                violations = lint_content(snippet, Path("test.tsx"))
                self.assertTrue(len(violations) >= 1)
                self.assertIn(match_expected, [v.match_text for v in violations])

    def test_bad_color_literals_fail(self) -> None:
        samples = [
            ('const color = "#3b82f6";', '"#3b82f6"'),
            ('const c = "rgb(10, 20, 30)";', "rgb("),
            ('const c = "rgba(0, 0, 0, 0.5)";', "rgba("),
            ('const c = "hsl(210, 50%, 50%)";', "hsl("),
            ('const c = "oklch(0.6 0.2 250)";', "oklch("),
        ]
        for snippet, token_expected in samples:
            with self.subTest(snippet=snippet):
                violations = lint_content(snippet, Path("test.tsx"))
                self.assertTrue(len(violations) >= 1)
                self.assertTrue(any(token_expected in v.match_text for v in violations))

    def test_bad_arbitrary_values_fail(self) -> None:
        samples = [
            ('<div className="text-[13px]" />', "-[13px]"),
            ('<div className="w-[200px]" />', "-[200px]"),
            ('<div className="p-[1rem]" />', "-[1rem]"),
            ('<div className="bg-[#123456]" />', "-[#123456]"),
            ('<div className="h-[50%]" />', "-[50%]"),
        ]
        for snippet, match_expected in samples:
            with self.subTest(snippet=snippet):
                violations = lint_content(snippet, Path("test.tsx"))
                self.assertTrue(len(violations) >= 1)
                self.assertIn(match_expected, [v.match_text for v in violations])

    def test_bad_shadows_fail(self) -> None:
        samples = [
            ('<div className="shadow" />', "shadow"),
            ('<div className="shadow-md" />', "shadow-md"),
            ('<div className="shadow-lg" />', "shadow-lg"),
            ('<div className="drop-shadow-sm" />', "drop-shadow-sm"),
        ]
        for snippet, match_expected in samples:
            with self.subTest(snippet=snippet):
                violations = lint_content(snippet, Path("test.tsx"))
                self.assertTrue(len(violations) >= 1)
                self.assertIn(match_expected, [v.match_text for v in violations])

    def test_bad_text_sizes_and_leading_fail(self) -> None:
        samples = [
            ('<h1 className="text-xl font-semibold" />', "text-xl"),
            ('<h1 className="text-2xl" />', "text-2xl"),
            ('<h1 className="leading-7" />', "leading-7"),
            ('<h1 className="leading-[28px]" />', "leading-[28px]"),
        ]
        for snippet, match_expected in samples:
            with self.subTest(snippet=snippet):
                violations = lint_content(snippet, Path("test.tsx"))
                self.assertTrue(len(violations) >= 1)
                self.assertIn(match_expected, [v.match_text for v in violations])

    def test_zero_files_scanned_fails(self) -> None:
        empty_dir = Path("scripts/tests/nonexistent_dir")
        scanned, violations = lint_directory(empty_dir)
        self.assertEqual(scanned, 0)
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
