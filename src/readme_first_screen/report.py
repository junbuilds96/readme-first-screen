from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import CATEGORY_NAMES, ScoreReport


def render_batch_human(report: Mapping[str, Any]) -> str:
    average_score = report["average_score"]
    if average_score is None:
        average_text = "n/a"
    else:
        average_text = f"{float(average_score):.1f}/100"

    lines = [
        (
            "README first-screen batch: "
            f"{report['item_count']} {_plural(int(report['item_count']), 'source')}, "
            f"{report['ok_count']} ok, "
            f"{report['error_count']} {_plural(int(report['error_count']), 'error')}"
        ),
        f"Average score: {average_text}",
        "",
        "Items:",
    ]

    for item in report["items"]:
        if item["status"] == "ok":
            lines.append(
                f"  - ok    {item['total_score']:>3}/100 {item['grade']} {item['source']}"
            )
        else:
            lines.append(f"  - error ---/100 {item['source']}: {item['error']}")

    return "\n".join(lines) + "\n"


def render_batch_summary(report: Mapping[str, Any]) -> str:
    average_score = report["average_score"]
    average_text = "n/a" if average_score is None else f"{float(average_score):.1f}/100"
    lowest_ok = min(
        (item for item in report["items"] if item["status"] == "ok"),
        key=lambda item: item["total_score"],
        default=None,
    )
    if lowest_ok is None:
        lowest_text = "none"
    else:
        lowest_text = (
            f"{lowest_ok['source']} "
            f"({lowest_ok['total_score']}/100 {lowest_ok['grade']})"
        )
    return (
        "Summary: "
        f"item_count={report['item_count']}, "
        f"ok_count={report['ok_count']}, "
        f"error_count={report['error_count']}, "
        f"average_score={average_text}, "
        f"lowest_ok={lowest_text}"
    )


def render_batch_github_step_summary(report: Mapping[str, Any]) -> str:
    average_score = report["average_score"]
    average_text = "n/a" if average_score is None else f"{float(average_score):.1f}/100"
    lines = [
        "# README First-Screen Batch Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Sources | {report['item_count']} |",
        f"| OK | {report['ok_count']} |",
        f"| Errors | {report['error_count']} |",
        f"| Average score | {average_text} |",
        "",
        "## Results",
        "",
        "| Source | Status | Score | Grade |",
        "| --- | --- | ---: | --- |",
    ]

    for item in report["items"]:
        source = _markdown_table_cell(str(item["source"]))
        if item["status"] == "ok":
            lines.append(
                f"| {source} | ok | {item['total_score']}/100 | {item['grade']} |"
            )
        else:
            error = _markdown_table_cell(str(item["error"]))
            lines.append(f"| {source} | error | n/a | {error} |")

    for item in report["items"]:
        if item["status"] != "ok":
            continue
        score_report = item.get("_score_report")
        if not isinstance(score_report, ScoreReport):
            continue
        lines.extend(
            [
                "",
                "<details>",
                (
                    f"<summary>{_markdown_inline_text(str(item['source']))}: "
                    f"{score_report.total_score}/{score_report.max_score} "
                    f"{score_report.grade}</summary>"
                ),
                "",
                *_github_step_summary_body(score_report),
                "</details>",
            ]
        )

    return "\n".join(lines) + "\n"


def _plural(count: int, singular: str) -> str:
    if count == 1:
        return singular
    return f"{singular}s"


def render_human(
    report: ScoreReport,
    comparison: Mapping[str, int | str] | None = None,
) -> str:
    lines = [
        f"README first-screen score: {report.total_score}/{report.max_score} ({report.grade})",
        f"Source: {report.source}",
        (
            "First screen analyzed: "
            f"{report.first_screen['lines_seen']}/{report.first_screen['line_limit']} lines, "
            f"{report.first_screen['chars_seen']}/{report.first_screen['char_limit']} chars"
        ),
    ]

    if comparison is not None:
        lines.extend(_comparison_section(comparison, report.max_score))

    lines.extend(["", "Section scores:"])

    for name in CATEGORY_NAMES:
        category = report.categories[name]
        label = name.replace("_", " ")
        lines.append(f"  - {label}: {category.score}/{category.max_score}")

    lines.extend(
        _section(
            _priority_section_title(report),
            _fix_first_items(report),
            empty="No urgent first-screen fix found.",
        )
    )
    evidence = _evidence_items(report)
    if evidence:
        lines.extend(_section("Evidence", evidence, empty="No source evidence found."))
    lines.extend(_section("Strengths", report.strengths, empty="No strong signals found."))
    lines.extend(_section("Issues", report.issues, empty="No major issues found."))
    lines.extend(_section("Actionable suggestions", report.suggestions, empty="No suggestions."))
    return "\n".join(lines) + "\n"


def render_summary(report: ScoreReport) -> str:
    priority_title = _priority_section_title(report)
    priority_items = _fix_first_items(report)
    if priority_items:
        priority_label = priority_title.lower().replace(" ", "_")
        priority_text = f"{priority_label}={priority_items[0]}"
    else:
        priority_text = "fix_first=no urgent first-screen fix"
    return (
        "Summary: "
        f"score={report.total_score}/{report.max_score}, "
        f"grade={report.grade}, "
        f"source={report.source}, "
        f"{priority_text}"
    )


def render_github_step_summary(
    report: ScoreReport,
    comparison: Mapping[str, int | str] | None = None,
) -> str:
    lines = [
        "# README First-Screen Summary",
        "",
        *_github_step_summary_body(report, comparison=comparison),
    ]
    return "\n".join(lines) + "\n"


def render_fix_plan(report: ScoreReport) -> str:
    evidence = _evidence_items(report)
    fixes = _fix_first_items(report)
    return "\n".join(
        [
            "# README First-Screen Remediation Plan",
            "",
            f"**Source:** {report.source}",
            f"**Score:** {report.total_score}/{report.max_score} ({report.grade})",
            "",
            "## First-Screen Evidence",
            *(_markdown_bullets(evidence) or ["- No source evidence found."]),
            "",
            "## Top 3 Priority Fixes",
            *(_markdown_bullets(fixes) or ["- No urgent first-screen fix found."]),
            "",
            "## Suggested Opening Shape",
            "",
            "````markdown",
            "# <Project name>",
            "",
            "<Project name> is a <concrete product type> for <target user> that need to <main job or outcome>.",
            "",
            "```bash",
            "<one copy-paste install or run command>",
            "```",
            "````",
            "",
        ]
    )


def _github_step_summary_body(
    report: ScoreReport,
    comparison: Mapping[str, int | str] | None = None,
) -> list[str]:
    lines = [
        "| Metric | Value |",
        "| --- | --- |",
        f"| Score | {report.total_score}/{report.max_score} |",
        f"| Grade | {report.grade} |",
        (
            "| First-screen scope | "
            f"{report.first_screen['lines_seen']}/{report.first_screen['line_limit']} lines, "
            f"{report.first_screen['chars_seen']}/{report.first_screen['char_limit']} chars |"
        ),
    ]

    if comparison is not None:
        delta = int(comparison["delta"])
        lines.extend(
            [
                "",
                "## Comparison",
                "",
                "| Baseline | Current | Delta | Result |",
                "| ---: | ---: | ---: | --- |",
                (
                    f"| {comparison['baseline_total_score']}/{report.max_score} "
                    f"| {comparison['current_total_score']}/{report.max_score} "
                    f"| {delta:+d} | {comparison['result']} |"
                ),
            ]
        )

    fixes = _fix_first_items(report)
    lines.extend(
        [
            "",
            "## Top Priority Fixes",
            "",
            *(_markdown_bullets(fixes) or ["- No urgent first-screen fix found."]),
            "",
            "## Section Scores",
            "",
            "| Section | Score |",
            "| --- | ---: |",
        ]
    )
    for name in CATEGORY_NAMES:
        category = report.categories[name]
        label = name.replace("_", " ").title()
        lines.append(f"| {label} | {category.score}/{category.max_score} |")
    lines.append("")
    return lines


def _priority_section_title(report: ScoreReport) -> str:
    if report.grade == "excellent" and report.issues:
        return "Polish opportunities"
    return "Fix first"


def _fix_first_items(report: ScoreReport) -> tuple[str, ...]:
    if not report.issues:
        return ()

    metadata = report.metadata
    issues = set(report.issues)
    candidates: list[str] = []

    badge_wall = (
        "Badge wall appears before the explanation." in issues
        or metadata.get("badges_before_explanation", 0) >= 4
    )
    what_is_it_strengths = set(report.categories["what_is_it"].strengths)
    has_project_name = "The first screen names the project." in what_is_it_strengths
    has_name_and_definition = (
        has_project_name and "The opening explains what the project is." in what_is_it_strengths
    )
    missing_definition = (
        "The first screen does not clearly say what the project is." in issues
        or (metadata.get("first_explanation_line") is None and not has_name_and_definition)
    )
    late_explanation = (
        "The first plain-language explanation starts too late." in issues
        and has_name_and_definition
    )
    dense_first_screen = "The first screen is dense or mostly structural markup." in issues
    if badge_wall and missing_definition:
        if has_project_name:
            candidates.append(
                "Keep the H1, add a one-sentence definition below it, and move badges after that opening explanation."
            )
        else:
            candidates.append(
                "Replace the badge wall with a project name and one-sentence definition at the top."
            )
    elif missing_definition:
        candidates.append(
            "Open with a project name and one-sentence definition before any secondary detail."
        )
    elif late_explanation:
        candidates.append(
            "Put a one- or two-sentence explanation before badges, screenshots, and tables."
        )
    elif badge_wall:
        candidates.append(
            "Move badges below the opening explanation; keep at most one or two above the fold."
        )
    if dense_first_screen and has_name_and_definition:
        candidates.append(
            "Use a short intro, short sections, and one compact example before deeper detail."
        )

    if (
        "No clear target user is named." in issues
        or "The target user appears, but not on the first screen." in issues
        or "The README does not state the problem or outcome clearly." in issues
        or "The value is present, but it lands after the first screen." in issues
    ):
        candidates.append("Put the target user and main outcome in the opening paragraph.")

    if "The first runnable command appears after the first screen." in issues:
        candidates.append("Move one copy-paste install or run command above the fold.")
    elif "No install or run command was found." in issues:
        candidates.append("Add a copy-paste install or run command to the first screen.")

    if (
        "The project name or first heading starts too late." in issues
        or "The first heading starts too late." in issues
    ):
        candidates.append("Start with a concise H1 project name in the first three lines.")

    for category_name in _weakest_category_names(report):
        category = report.categories[category_name]
        if category.suggestions:
            candidates.append(category.suggestions[0])

    if not candidates:
        candidates.extend(report.suggestions[:3])
    if not candidates:
        candidates.extend(report.issues[:3])

    return tuple(dict.fromkeys(candidates))[:3]


def _weakest_category_names(report: ScoreReport) -> list[str]:
    return sorted(
        CATEGORY_NAMES,
        key=lambda name: (
            report.categories[name].score / report.categories[name].max_score,
            CATEGORY_NAMES.index(name),
        ),
    )


def _evidence_items(report: ScoreReport) -> tuple[str, ...]:
    metadata = report.metadata
    items: list[str] = []

    first_heading_line = metadata.get("first_heading_line")
    if first_heading_line is not None:
        items.append(f"First heading line: {first_heading_line}")

    first_explanation_line = metadata.get("first_explanation_line")
    if first_explanation_line is not None:
        items.append(f"First explanation line: {first_explanation_line}")

    badges_before_explanation = metadata.get("badges_before_explanation")
    if badges_before_explanation:
        items.append(f"Badges before explanation: {badges_before_explanation}")

    first_command_line = metadata.get("first_command_line")
    if first_command_line is not None:
        items.append(f"First runnable command line: {first_command_line}")

    return tuple(items)


def _section(title: str, values: tuple[str, ...], empty: str) -> list[str]:
    lines = ["", f"{title}:"]
    if values:
        lines.extend(f"  - {value}" for value in values)
    else:
        lines.append(f"  - {empty}")
    return lines


def _markdown_bullets(values: tuple[str, ...]) -> list[str]:
    return [f"- {value}" for value in values]


def _markdown_table_cell(value: str) -> str:
    return _markdown_inline_text(value).replace("|", "\\|")


def _markdown_inline_text(value: str) -> str:
    return " ".join(value.split())


def _comparison_section(comparison: Mapping[str, int | str], max_score: int) -> list[str]:
    delta = int(comparison["delta"])
    delta_text = f"{delta:+d}"
    return [
        "",
        "Comparison:",
        f"  - Baseline score: {comparison['baseline_total_score']}/{max_score}",
        f"  - Current score: {comparison['current_total_score']}/{max_score}",
        f"  - Delta: {delta_text} ({comparison['result']})",
    ]
