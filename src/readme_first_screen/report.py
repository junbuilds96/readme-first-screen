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

    lines.extend(_section("Strengths", report.strengths, empty="No strong signals found."))
    lines.extend(_section("Issues", report.issues, empty="No major issues found."))
    lines.extend(_section("Actionable suggestions", report.suggestions, empty="No suggestions."))
    return "\n".join(lines) + "\n"


def _section(title: str, values: tuple[str, ...], empty: str) -> list[str]:
    lines = ["", f"{title}:"]
    if values:
        lines.extend(f"  - {value}" for value in values)
    else:
        lines.append(f"  - {empty}")
    return lines
