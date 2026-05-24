from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .input import ReadmeInputError, load_readme
from .report import render_human
from .scoring import score_readme


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="readme-first-screen",
        description="Score whether a stranger can understand a GitHub README first screen in 10 seconds.",
    )
    parser.add_argument(
        "source",
        help="Path to a README/Markdown file, GitHub repo URL, raw URL, or '-' for stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a stable JSON report instead of the human-readable report.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text, source_label = load_readme(args.source)
    except ReadmeInputError as exc:
        print(f"readme-first-screen: {exc}", file=sys.stderr)
        return 2

    report = score_readme(text, source=source_label)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_human(report), end="")
    return 0
