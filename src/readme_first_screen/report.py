from __future__ import annotations

from .models import CATEGORY_NAMES, ScoreReport


def render_human(report: ScoreReport) -> str:
    lines = [
        f"README first-screen score: {report.total_score}/{report.max_score} ({report.grade})",
        f"Source: {report.source}",
        (
            "First screen analyzed: "
            f"{report.first_screen['lines_seen']}/{report.first_screen['line_limit']} lines, "
            f"{report.first_screen['chars_seen']}/{report.first_screen['char_limit']} chars"
        ),
        "",
        "Section scores:",
    ]

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
    lines.extend(_section("Strengths", report.strengths, empty="No strong signals found."))
    lines.extend(_section("Issues", report.issues, empty="No major issues found."))
    lines.extend(_section("Actionable suggestions", report.suggestions, empty="No suggestions."))
    return "\n".join(lines) + "\n"


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
    has_name_and_definition = (
        "The first screen names the project." in what_is_it_strengths
        and "The opening explains what the project is." in what_is_it_strengths
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


def _section(title: str, values: tuple[str, ...], empty: str) -> list[str]:
    lines = ["", f"{title}:"]
    if values:
        lines.extend(f"  - {value}" for value in values)
    else:
        lines.append(f"  - {empty}")
    return lines
