from readme_first_screen.report import (
    render_batch_github_step_summary,
    render_github_step_summary,
    render_human,
)
from readme_first_screen.scoring import score_readme


STRONG_README = """# Demo CLI

Demo CLI is a Python CLI for developers who need to check a README before release.
It helps teams catch unclear first screens before a stranger gives up.

## Quick start

```bash
python -m demo --help
```

## Example

Sample output shows a score.

## Proof

MIT License. CI runs tests.
"""


WEAK_README = """![build](https://example.com/build.svg)
![coverage](https://example.com/coverage.svg)
![version](https://example.com/version.svg)
![downloads](https://example.com/downloads.svg)

Awesome modern lightweight flexible thing.
"""


H1_BADGE_WALL_WITHOUT_DEFINITION_README = """# Gemini CLI

![build](https://example.com/build.svg)
![coverage](https://example.com/coverage.svg)
![version](https://example.com/version.svg)
![downloads](https://example.com/downloads.svg)

An open-source AI agent that brings Gemini to your terminal.
"""


DENSE_STRONG_WHAT_IS_IT_README = """# Bounty Sieve
![ci](https://example.com/ci.svg)
![coverage](https://example.com/cov.svg)
![version](https://example.com/version.svg)

## Status
## Install
## Usage
## Output
## Limits
## License

Bounty Sieve is a Python CLI for maintainers who need to triage open-source bounties before release.
It helps each developer understand confusing issues and reports a ranked workflow so you can pick work quickly.

```bash
python -m bounty_sieve --help
```

## Example

Sample output shows a score table.

## Proof

MIT License. CI runs tests and includes demo output.
"""


def test_human_report_prioritizes_weak_first_screen_fixes():
    output = render_human(score_readme(WEAK_README))

    assert output.index("Fix first:") < output.index("Strengths:")
    assert output.index("Evidence:") < output.index("Strengths:")
    assert _section_bullets(output, "Fix first") == [
        "Replace the badge wall with a project name and one-sentence definition at the top.",
        "Put the target user and main outcome in the opening paragraph.",
        "Add a copy-paste install or run command to the first screen.",
    ]
    assert _section_bullets(output, "Evidence") == [
        "Badges before explanation: 4",
    ]


def test_human_report_keeps_existing_h1_when_badges_precede_missing_definition():
    report = score_readme(H1_BADGE_WALL_WITHOUT_DEFINITION_README)
    output = render_human(report)

    assert "The first screen names the project." in report.strengths
    assert "The first screen does not clearly say what the project is." in report.issues
    assert "Badge wall appears before the explanation." in report.issues
    assert _section_bullets(output, "Fix first")[0] == (
        "Keep the H1, add a one-sentence definition below it, and move badges after that opening explanation."
    )
    assert "Replace the badge wall with a project name" not in output


def test_human_report_shows_no_urgent_fix_for_strong_report():
    output = render_human(score_readme(STRONG_README))

    assert _section_bullets(output, "Fix first") == [
        "No urgent first-screen fix found.",
    ]
    assert _section_bullets(output, "Evidence") == [
        "First heading line: 1",
        "First explanation line: 3",
        "First runnable command line: 9",
    ]
    assert "fix_first" not in score_readme(STRONG_README).to_dict()


def test_human_report_does_not_recommend_definition_when_what_is_it_is_strong():
    report = score_readme(DENSE_STRONG_WHAT_IS_IT_README)
    output = render_human(report)

    assert report.total_score >= 85
    assert report.categories["what_is_it"].score >= 18
    assert "The first screen names the project." in report.strengths
    assert "The opening explains what the project is." in report.strengths
    assert "Fix first:" not in output
    assert output.index("Polish opportunities:") < output.index("Strengths:")
    assert output.index("Evidence:") < output.index("Strengths:")
    assert _section_bullets(output, "Polish opportunities") == [
        "Put a one- or two-sentence explanation before badges, screenshots, and tables.",
        "Use a short intro, short sections, and one compact example before deeper detail.",
    ]
    assert "Open with a project name and one-sentence definition" not in output


def test_github_step_summary_renders_concise_markdown():
    report = score_readme(WEAK_README)
    output = render_github_step_summary(
        report,
        comparison={
            "baseline_source": "README-before.md",
            "baseline_total_score": 10,
            "current_total_score": report.total_score,
            "delta": report.total_score - 10,
            "result": "improved",
        },
    )

    assert output.startswith("# README First-Screen Summary\n")
    assert f"| Score | {report.total_score}/{report.max_score} |" in output
    assert "| First-screen scope |" in output
    assert "## Comparison" in output
    assert f"| 10/{report.max_score} | {report.total_score}/{report.max_score} |" in output
    assert output.index("## Top Priority Fixes") < output.index("## Section Scores")
    assert (
        "- Replace the badge wall with a project name and one-sentence definition at the top."
        in output
    )
    assert "| What Is It |" in output


def test_batch_github_step_summary_includes_item_details():
    weak_report = score_readme(WEAK_README, source="README|weak.md")
    strong_report = score_readme(STRONG_README, source="README.md")
    output = render_batch_github_step_summary(
        {
            "schema_version": "1.0",
            "item_count": 3,
            "ok_count": 2,
            "error_count": 1,
            "average_score": 62.0,
            "items": [
                {
                    "source": "README|weak.md",
                    "status": "ok",
                    "total_score": weak_report.total_score,
                    "grade": weak_report.grade,
                    "_score_report": weak_report,
                },
                {
                    "source": "README.md",
                    "status": "ok",
                    "total_score": strong_report.total_score,
                    "grade": strong_report.grade,
                    "_score_report": strong_report,
                },
                {
                    "source": "missing.md",
                    "status": "error",
                    "error": "README file not found: missing.md",
                },
            ],
        }
    )

    assert output.startswith("# README First-Screen Batch Summary\n")
    assert "| Average score | 62.0/100 |" in output
    assert "| README\\|weak.md | ok |" in output
    assert "| missing.md | error | n/a | README file not found: missing.md |" in output
    assert "<details>" in output
    assert "<summary>README|weak.md:" in output
    assert "## Top Priority Fixes" in output
    assert "## Section Scores" in output


def _section_bullets(output: str, title: str) -> list[str]:
    lines = output.splitlines()
    start = lines.index(f"{title}:") + 1
    bullets: list[str] = []
    for line in lines[start:]:
        if not line:
            break
        bullets.append(line.removeprefix("  - "))
    return bullets
