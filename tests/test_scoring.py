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


def test_strong_readme_scores_well():
    report = score_readme(STRONG_README)

    assert report.total_score >= 80
    assert report.categories["what_is_it"].score >= 15
    assert report.categories["quick_start"].score >= 15
    assert "A runnable command appears on the first screen." in report.strengths


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
