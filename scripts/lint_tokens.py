"""Design Token Linter for Camera Monitor.

Scans all .ts and .tsx files under frontend/src (excluding index.css)
to enforce design token usage and prohibit raw Tailwind palettes,
arbitrary length/color values, disallowed shadows, non-token font sizes/leading,
and hardcoded color literals.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
    file_path: Path
    line_number: int
    rule: str
    match_text: str
    line_content: str


# 1. Raw Tailwind palette colors with shades + bare white/black colors
BANNED_COLOR_NAMES = (
    "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|"
    "emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose"
)
COLOR_PREFIXES = (
    "bg|text|border|ring|outline|fill|stroke|divide|from|via|to|decoration|accent|caret"
)

# Matches e.g. bg-blue-500, hover:text-gray-300, bg-white, text-black, bg-black/40
PALETTE_COLOR_PATTERN = re.compile(
    rf"(?:^|[\s\"'`])((?:[a-zA-Z0-9_-]+:)*(?:{COLOR_PREFIXES})-(?:(?:{BANNED_COLOR_NAMES})-\d+|white(?:\/\d+)?|black(?:\/\d+)?))\b"
)

# 2. Color literals: #hex (3, 4, 6, 8 hex digits in string context), rgb(), rgba(), hsl(), hsla(), oklch()
COLOR_LITERAL_PATTERN = re.compile(
    r"""(?:["'`]#[0-9a-fA-F]{3,8}["'`]|:\s*["']?#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\()"""
)

# 3. Arbitrary values containing literal lengths or colors (px, rem, em, %, #, rgb, hsl, oklch)
# Does not match arbitrary variants like data-[state=open]: or [&>svg]: (which have a trailing colon)
# Allows var(--token)
ARBITRARY_VALUE_PATTERN = re.compile(
    r"""(-[\[](?![^\]]*var\(--)[^\]]*(?:px|rem|em|%|#[0-9a-fA-F]|rgb|hsl|oklch)[^\]]*\])(?!:)"""
)

# 4. Shadow utilities except shadow-none
SHADOW_PATTERN = re.compile(
    r"(?:^|[\s\"'`])((?:[a-zA-Z0-9_-]+:)*(?:shadow|drop-shadow)(?:-(?!none\b)[a-zA-Z0-9_-]+)?)(?=[\s\"'`]|$)"
)

# 5. Non-semantic text sizes (text-lg .. text-9xl) and line heights (leading-*)
TEXT_SIZE_PATTERN = re.compile(
    r"(?:^|[\s\"'`])((?:[a-zA-Z0-9_-]+:)*text-(?:lg|xl|[2-9]xl))\b"
)
LEADING_PATTERN = re.compile(
    r"(?:^|[\s\"'`])((?:[a-zA-Z0-9_-]+:)*leading-(?:[a-zA-Z0-9_-]+\b|\[.*?\]))"
)


def lint_content(content: str, file_path: Path) -> list[Violation]:
    violations: list[Violation] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        # Check rule 1: Raw palette colors
        for match in PALETTE_COLOR_PATTERN.finditer(line):
            violations.append(
                Violation(
                    file_path=file_path,
                    line_number=idx,
                    rule="No raw Tailwind palette colors or bare white/black. Use semantic tokens.",
                    match_text=match.group(1).strip(),
                    line_content=line.strip(),
                )
            )

        # Check rule 2: Color literals
        for match in COLOR_LITERAL_PATTERN.finditer(line):
            violations.append(
                Violation(
                    file_path=file_path,
                    line_number=idx,
                    rule="No hardcoded color literals (#hex, rgb, hsl, oklch). Use semantic tokens.",
                    match_text=match.group(0).strip(),
                    line_content=line.strip(),
                )
            )

        # Check rule 3: Arbitrary length/color values
        for match in ARBITRARY_VALUE_PATTERN.finditer(line):
            violations.append(
                Violation(
                    file_path=file_path,
                    line_number=idx,
                    rule="No arbitrary literal values (px, rem, %, hex). Use semantic tokens.",
                    match_text=match.group(1).strip(),
                    line_content=line.strip(),
                )
            )

        # Check rule 4: Shadows
        for match in SHADOW_PATTERN.finditer(line):
            violations.append(
                Violation(
                    file_path=file_path,
                    line_number=idx,
                    rule="No shadows allowed (except shadow-none).",
                    match_text=match.group(1).strip(),
                    line_content=line.strip(),
                )
            )

        # Check rule 5: Non-semantic font sizes & leading
        for match in TEXT_SIZE_PATTERN.finditer(line):
            violations.append(
                Violation(
                    file_path=file_path,
                    line_number=idx,
                    rule="No ad-hoc text sizes (text-lg..text-9xl). Use semantic utilities (text-page-title, text-section-heading, text-table, text-sm, text-xs).",
                    match_text=match.group(1).strip(),
                    line_content=line.strip(),
                )
            )
        for match in LEADING_PATTERN.finditer(line):
            violations.append(
                Violation(
                    file_path=file_path,
                    line_number=idx,
                    rule="No ad-hoc leading-* utilities. Line height is bundled in typography utilities.",
                    match_text=match.group(1).strip(),
                    line_content=line.strip(),
                )
            )

    return violations


def lint_directory(src_dir: Path) -> tuple[int, list[Violation]]:
    violations: list[Violation] = []
    files_scanned = 0

    if not src_dir.exists():
        return 0, violations

    for p in sorted(src_dir.rglob("*")):
        if p.is_file() and p.suffix in (".ts", ".tsx"):
            files_scanned += 1
            content = p.read_text(encoding="utf-8")
            violations.extend(lint_content(content, p))

    return files_scanned, violations


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "frontend" / "src"

    files_scanned, violations = lint_directory(src_dir)

    print(f"Scanned {files_scanned} files in {src_dir}")

    if files_scanned == 0:
        print("ERROR: Zero files scanned! Target directory may be missing or empty.", file=sys.stderr)
        return 1

    if violations:
        print(f"\nFAILED: Found {len(violations)} design token violation(s):", file=sys.stderr)
        for v in violations:
            rel_path = v.file_path.relative_to(repo_root) if v.file_path.is_relative_to(repo_root) else v.file_path
            print(f"  {rel_path}:{v.line_number} [{v.rule}] -> {v.match_text}", file=sys.stderr)
            print(f"    Line: {v.line_content}", file=sys.stderr)
        return 1

    print("PASS: All files adhere to design tokens.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
