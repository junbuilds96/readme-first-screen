from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .input import ReadmeInputError, load_readme
from .models import ScoreReport
from .report import (
    render_batch_human,
    render_batch_summary,
    render_fix_plan,
    render_human,
    render_summary,
)
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
        nargs="?",
        help="Path to a README/Markdown file, GitHub repo URL, raw URL, or '-' for stdin.",
    )
    parser.add_argument(
        "--batch",
        metavar="PATH",
        help=(
            "Score README sources listed in PATH, one per non-empty non-comment line."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a stable JSON report instead of the human-readable report.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Append a concise one-line summary to the human-readable report.",
    )
    parser.add_argument(
        "--fix-plan",
        action="store_true",
        help="Print a concise Markdown remediation plan instead of the human-readable report.",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="Write the rendered report to PATH instead of printing it to stdout.",
    )
    parser.add_argument(
        "--github-annotations",
        action="store_true",
        help=(
            "Emit GitHub Actions warning annotations for top README first-screen "
            "issues to stderr."
        ),
    )
    parser.add_argument(
        "--fail-under",
        metavar="N",
        type=fail_under_threshold,
        help=(
            "Exit with status 1 if the total score is below N (0-100); "
            "in batch mode, also fail if any source cannot be loaded."
        ),
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

    if args.summary and args.json:
        parser.error("--summary cannot be used with --json")
    if args.fix_plan and args.json:
        parser.error("--fix-plan cannot be used with --json")
    if args.fix_plan and args.summary:
        parser.error("--fix-plan cannot be used with --summary")

    if args.batch is not None:
        if args.github_annotations:
            parser.error("--github-annotations cannot be used with --batch")
        if args.fix_plan:
            parser.error("--fix-plan cannot be used with --batch")
        if args.source is not None:
            parser.error("source cannot be used with --batch")
        if args.baseline is not None:
            parser.error("--baseline cannot be used with --batch")
        return run_batch(args)

    if args.source is None:
        parser.error("the following arguments are required: source")

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
        rendered_output = json.dumps(output, indent=2, sort_keys=True) + "\n"
    elif args.fix_plan:
        rendered_output = render_fix_plan(report)
    else:
        rendered_output = render_human(report, comparison=comparison)
        if args.summary:
            rendered_output += render_summary(report) + "\n"

    write_or_print(rendered_output, args.out)
    if args.github_annotations:
        emit_github_annotations(report, args.source)

    if args.fail_under is not None and report.total_score < args.fail_under:
        return 1
    return 0


def run_batch(args: argparse.Namespace) -> int:
    try:
        sources = load_batch_sources(args.batch)
    except ReadmeInputError as exc:
        print(f"readme-first-screen: {exc}", file=sys.stderr)
        return 2

    report = build_batch_report(sources)
    if args.json:
        rendered_output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    else:
        rendered_output = render_batch_human(report)
        if args.summary:
            rendered_output += render_batch_summary(report) + "\n"

    write_or_print(rendered_output, args.out)

    if args.fail_under is not None and batch_fails_threshold(report, args.fail_under):
        return 1
    return 0


def load_batch_sources(path: str) -> list[str]:
    batch_path = Path(path)
    try:
        text = batch_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReadmeInputError(f"Batch file not found: {path}") from exc
    except OSError as exc:
        raise ReadmeInputError(f"Could not read batch file {path}: {exc}") from exc

    sources = []
    for line in text.splitlines():
        source = line.strip()
        if source and not source.startswith("#"):
            sources.append(source)
    return sources


def build_batch_report(sources: list[str]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    score_sum = 0
    ok_count = 0
    error_count = 0

    for source in sources:
        try:
            text, source_label = load_readme(source)
        except ReadmeInputError as exc:
            error_count += 1
            items.append(
                {
                    "source": source,
                    "status": "error",
                    "error": str(exc),
                }
            )
            continue

        score_report = score_readme(text, source=source_label)
        ok_count += 1
        score_sum += score_report.total_score
        items.append(
            {
                "source": source,
                "status": "ok",
                "total_score": score_report.total_score,
                "grade": score_report.grade,
            }
        )

    average_score = round(score_sum / ok_count, 2) if ok_count else None
    return {
        "schema_version": "1.0",
        "item_count": len(items),
        "ok_count": ok_count,
        "error_count": error_count,
        "average_score": average_score,
        "items": items,
    }


def batch_fails_threshold(report: dict[str, Any], threshold: int) -> bool:
    if report["error_count"]:
        return True
    return any(
        item["status"] == "ok" and item["total_score"] < threshold
        for item in report["items"]
    )


def write_or_print(rendered_output: str, output_path_value: str | None) -> None:
    if output_path_value is not None:
        output_path = Path(output_path_value)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered_output, encoding="utf-8")
        print(f"Wrote report to {output_path_value}")
    else:
        print(rendered_output, end="")


def emit_github_annotations(
    report: ScoreReport,
    original_source: str,
    *,
    limit: int = 5,
) -> None:
    file_path = report.source if _is_local_file_source(original_source) else None
    for issue in report.issues[:limit]:
        properties = {}
        if file_path is not None:
            properties["file"] = file_path
            properties["line"] = str(_annotation_line(issue, report.metadata))
        properties["title"] = "README first-screen issue"
        property_text = ",".join(
            f"{name}={_escape_github_property(value)}"
            for name, value in properties.items()
        )
        message = _annotation_message(issue, report)
        print(
            f"::warning {property_text}::{_escape_github_message(message)}",
            file=sys.stderr,
        )


def _annotation_message(issue: str, report: ScoreReport) -> str:
    suggestion = _suggestion_for_issue(issue, report)
    if suggestion is None:
        return issue
    return f"{issue} Suggested fix: {suggestion}"


def _suggestion_for_issue(issue: str, report: ScoreReport) -> str | None:
    for category in report.categories.values():
        if issue not in category.issues or not category.suggestions:
            continue
        issue_index = list(category.issues).index(issue)
        if issue_index < len(category.suggestions):
            return category.suggestions[issue_index]
        return category.suggestions[0]
    if report.suggestions:
        return report.suggestions[0]
    return None


def _annotation_line(issue: str, metadata: dict[str, Any]) -> int:
    issue_lower = issue.lower()
    if any(
        token in issue_lower
        for token in ("explanation", "value", "definition", "problem", "outcome")
    ):
        return int(metadata.get("first_explanation_line") or 1)
    if any(token in issue_lower for token in ("command", "quick start", "usage", "run")):
        return int(metadata.get("first_command_line") or 1)
    if any(
        token in issue_lower
        for token in ("heading", "project name", "project-name", "h1")
    ):
        return int(metadata.get("first_heading_line") or 1)
    return 1


def _is_local_file_source(source: str) -> bool:
    if source == "-":
        return False
    parsed = urlparse(source)
    return not (parsed.scheme in {"http", "https"} and bool(parsed.netloc))


def _escape_github_message(value: str) -> str:
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


def _escape_github_property(value: str) -> str:
    return (
        _escape_github_message(value)
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


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
