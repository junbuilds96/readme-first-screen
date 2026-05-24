from readme_first_screen.report import render_human
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


def test_human_report_prioritizes_weak_first_screen_fixes():
    output = render_human(score_readme(WEAK_README))

    assert output.index("Fix first:") < output.index("Strengths:")
    assert _section_bullets(output, "Fix first") == [
        "Replace the badge wall with a project name and one-sentence definition at the top.",
        "Put the target user and main outcome in the opening paragraph.",
        "Add a copy-paste install or run command to the first screen.",
    ]


def test_human_report_shows_no_urgent_fix_for_strong_report():
    output = render_human(score_readme(STRONG_README))

    assert _section_bullets(output, "Fix first") == [
        "No urgent first-screen fix found.",
    ]
    assert "fix_first" not in score_readme(STRONG_README).to_dict()


def _section_bullets(output: str, title: str) -> list[str]:
    lines = output.splitlines()
    start = lines.index(f"{title}:") + 1
    bullets: list[str] = []
    for line in lines[start:]:
        if not line:
            break
        bullets.append(line.removeprefix("  - "))
    return bullets
