from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .input import ReadmeInputError, load_readme
from .models import ScoreReport
from .report import render_human
from .scoring import score_readme


def fail_under_threshold(value: str) -> int:
    try:
        threshold = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer from 0 to 100") from exc
    if not 0 <= threshold <= 100:
        raise argparse.ArgumentTypeError("must be an integer from 0 to 100")
    return threshold


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
        "--fail-under",
        metavar="N",
        type=fail_under_threshold,
        help="Exit with status 1 if the total score is below N (0-100).",
    )
    parser.add_argument(
        "--baseline",
        metavar="PATH_OR_URL",
        help="Compare the current README score with another README path or URL.",
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

    comparison = None
    if args.baseline is not None:
        try:
            baseline_text, baseline_source_label = load_readme(args.baseline)
        except ReadmeInputError as exc:
            print(f"readme-first-screen: could not load baseline: {exc}", file=sys.stderr)
            return 2
        baseline_report = score_readme(baseline_text, source=baseline_source_label)

    report = score_readme(text, source=source_label)
    if args.baseline is not None:
        comparison = build_comparison(baseline_report, report)

    if args.json:
        output = report.to_dict()
        if comparison is not None:
            output["comparison"] = comparison
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print(render_human(report, comparison=comparison), end="")
    if args.fail_under is not None and report.total_score < args.fail_under:
        return 1
    return 0


def build_comparison(
    baseline_report: ScoreReport,
    current_report: ScoreReport,
) -> dict[str, int | str]:
    delta = current_report.total_score - baseline_report.total_score
    if delta > 0:
        result = "improved"
    elif delta < 0:
        result = "regressed"
    else:
        result = "unchanged"
    return {
        "baseline_source": baseline_report.source,
        "baseline_total_score": baseline_report.total_score,
        "current_total_score": current_report.total_score,
        "delta": delta,
        "result": result,
    }


if __name__ == "__main__":
    raise SystemExit(main())
