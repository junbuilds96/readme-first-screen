from readme_first_screen.scoring import score_readme


STRONG_README = """# readme-first-screen

readme-first-screen is a Python CLI for open-source maintainers who need to know
whether a stranger can understand their GitHub README first screen in 10 seconds.
It scores the first screen, flags confusing gaps, and suggests concrete fixes.

## Quick start

```bash
pip install -e .
readme-first-screen README.md
```

## Example output

```text
README first-screen score: 88/100 (excellent)
```

## Proof

MIT License. CI runs pytest on Python 3.11 and 3.12.
"""


WEAK_README = """![build](https://example.com/build.svg)
![coverage](https://example.com/coverage.svg)
![version](https://example.com/version.svg)
![downloads](https://example.com/downloads.svg)

Awesome modern lightweight flexible thing.
"""


SCREENSHOT_README = """# Demo Shot

Demo Shot is a Python CLI for developers who need to inspect terminal runs.
It reports command results before release.

![Terminal output screenshot](docs/terminal.png)
"""


BADGE_ONLY_README = """# Badge Only

![CI](https://img.shields.io/badge/ci-passing-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

Badge Only is a Python CLI for developers who need release checks.
It reports command results before release.
"""


def test_strong_readme_scores_well():
    report = score_readme(STRONG_README)

    assert report.total_score >= 80
    assert report.categories["what_is_it"].score >= 15
    assert report.categories["quick_start"].score >= 15
    assert "A runnable command appears on the first screen." in report.strengths
    assert report.metadata["first_command_line"] == 10


def test_weak_readme_flags_first_screen_antipatterns():
    report = score_readme(WEAK_README)

    assert report.total_score < 45
    assert any("Badge wall" in issue for issue in report.issues)
    assert any("No install or run command" in issue for issue in report.issues)
    assert any("No clear target user" in issue for issue in report.issues)


def test_json_schema_contains_stable_categories():
    data = score_readme(STRONG_README, source="README.md").to_dict()

    assert data["schema_version"] == "1.0"
    assert data["source"] == "README.md"
    assert data["max_score"] == 100
    assert list(data["categories"]) == [
        "what_is_it",
        "target_user",
        "problem_value",
        "quick_start",
        "proof_credibility",
        "visual_clarity",
    ]
    assert data["categories"]["what_is_it"]["max_score"] == 20


def test_command_metadata_uses_command_lines_not_project_name_mentions():
    readme = """# readme-first-screen

readme-first-screen is a Python CLI for maintainers who need README checks.
It reports confusing first screens before a release.

## Usage

```bash
readme-first-screen README.md
```
"""

    report = score_readme(readme)

    assert report.metadata["first_command_line"] == 9
    assert "A runnable command appears on the first screen." in report.strengths


def test_screenshot_image_counts_as_demo_proof_evidence():
    report = score_readme(SCREENSHOT_README)

    assert "Some credibility signal appears early." in report.strengths
    assert not any(
        "No demo, sample output, or proof example was found." == issue
        for issue in report.issues
    )


def test_badge_images_do_not_count_as_demo_proof_evidence():
    report = score_readme(BADGE_ONLY_README)

    assert report.metadata["badges_before_explanation"] == 2
    assert any(
        "No demo, sample output, or proof example was found." == issue
        for issue in report.issues
    )
