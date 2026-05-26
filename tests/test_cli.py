import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


README = """# Demo CLI

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


WEAK_README = """# Demo

![build](https://example.com/build.svg)
![coverage](https://example.com/coverage.svg)
![downloads](https://example.com/downloads.svg)
"""


LATE_COMMAND_README = (
    "# Demo CLI\n"
    "\n"
    "Demo CLI is a Python CLI for developers who need to check README files "
    "before release so you can catch unclear docs.\n"
    "\n"
    "## Details\n"
    "\n"
    "This section explains enough proof. MIT License. CI runs tests. Demo example output.\n"
    + "\n" * 25
    + "```bash\n"
    "python -m demo --help\n"
    "```\n"
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args, input_text=None, module="readme_first_screen"):
    src_path = str(REPO_ROOT / "src")
    pythonpath = os.environ.get("PYTHONPATH")
    env = {
        **os.environ,
        "PYTHONPATH": src_path if not pythonpath else f"{src_path}{os.pathsep}{pythonpath}",
    }
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def run_checkout_module(*args, pythonpath=None):
    env = {**os.environ}
    if pythonpath is None:
        env.pop("PYTHONPATH", None)
    else:
        env["PYTHONPATH"] = str(pythonpath)
    return subprocess.run(
        [sys.executable, "-m", "readme_first_screen", *args],
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )


def test_cli_reads_local_file(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")

    result = run_cli(str(readme))

    assert result.returncode == 0
    assert "README first-screen score:" in result.stdout
    assert "First screen analyzed: 18/30 lines, 298/2400 chars" in result.stdout
    assert "Section scores:" in result.stdout
    assert result.stderr == ""


def test_cli_module_invocation_reads_local_file(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")

    result = run_cli(str(readme), module="readme_first_screen.cli")

    assert result.returncode == 0
    assert "README first-screen score:" in result.stdout
    assert result.stderr == ""


def test_checkout_module_invocation_shows_help_without_pythonpath():
    result = run_checkout_module("--help")

    assert result.returncode == 0
    assert "Score whether a stranger can understand" in result.stdout
    assert "source" in result.stdout
    assert result.stderr == ""


def test_checkout_module_invocation_prefers_local_src_over_stale_package(tmp_path):
    stale_package = tmp_path / "stale_site" / "readme_first_screen"
    stale_package.mkdir(parents=True)
    (stale_package / "__init__.py").write_text("__version__ = 'stale'\n", encoding="utf-8")
    (stale_package / "__main__.py").write_text(
        "print('STALE INSTALLED PACKAGE')\nraise SystemExit(43)\n",
        encoding="utf-8",
    )
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")

    result = run_checkout_module(str(readme), pythonpath=stale_package.parent)

    assert result.returncode == 0
    assert "README first-screen score:" in result.stdout
    assert "STALE INSTALLED PACKAGE" not in result.stdout
    assert result.stderr == ""


def test_cli_reads_stdin():
    result = run_cli("-", input_text=README)

    assert result.returncode == 0
    assert "Source: stdin" in result.stdout


def test_cli_json_output(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")

    result = run_cli("--json", str(readme))
    data = json.loads(result.stdout)

    assert result.returncode == 0
    assert data["schema_version"] == "1.0"
    assert data["source"] == str(readme)
    assert data["total_score"] >= 70
    assert set(data["categories"]) == {
        "what_is_it",
        "target_user",
        "problem_value",
        "quick_start",
        "proof_credibility",
        "visual_clarity",
    }


def test_cli_sarif_output_is_parseable_json(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--sarif", str(readme))
    data = json.loads(result.stdout)
    run = data["runs"][0]

    assert result.returncode == 0
    assert data["version"] == "2.1.0"
    assert run["tool"]["driver"]["name"] == "readme-first-screen"
    assert run["tool"]["driver"]["rules"]
    assert run["results"]
    assert result.stderr == ""


def test_cli_sarif_local_file_locations_include_start_line(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(LATE_COMMAND_README, encoding="utf-8")
    expected_line = LATE_COMMAND_README.splitlines().index("python -m demo --help") + 1

    result = run_cli("--sarif", str(readme))
    data = json.loads(result.stdout)
    sarif_result = next(
        item
        for item in data["runs"][0]["results"]
        if item["message"]["text"].startswith("The first runnable command appears")
    )
    location = sarif_result["locations"][0]["physicalLocation"]

    assert result.returncode == 0
    assert location["artifactLocation"]["uri"] == readme.as_posix()
    assert location["region"]["startLine"] == expected_line
    assert result.stderr == ""


def test_cli_sarif_from_stdin_has_no_locations():
    result = run_cli("--sarif", "-", input_text=WEAK_README)
    data = json.loads(result.stdout)

    assert result.returncode == 0
    assert data["runs"][0]["results"]
    assert all("locations" not in item for item in data["runs"][0]["results"])
    assert result.stderr == ""


def test_cli_sarif_output_can_be_written_to_file(tmp_path):
    readme = tmp_path / "README.md"
    out = tmp_path / "artifacts" / "report.sarif"
    readme.write_text(WEAK_README, encoding="utf-8")

    expected = run_cli("--sarif", str(readme))
    result = run_cli("--sarif", "--out", str(out), str(readme))
    report_text = out.read_text(encoding="utf-8")

    assert expected.returncode == 0
    assert result.returncode == 0
    assert result.stdout == f"Wrote report to {out}\n"
    assert report_text == expected.stdout
    assert json.loads(report_text)["version"] == "2.1.0"
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("extra_args", "expected_error"),
    [
        (("--json",), "--sarif cannot be used with --json"),
        (("--summary",), "--summary cannot be used with --sarif"),
        (("--fix-plan",), "--fix-plan cannot be used with --sarif"),
        (("--batch",), "--sarif cannot be used with --batch"),
    ],
)
def test_cli_sarif_rejects_incompatible_options(tmp_path, extra_args, expected_error):
    readme = tmp_path / "README.md"
    batch = tmp_path / "batch.txt"
    readme.write_text(README, encoding="utf-8")
    batch.write_text(f"{readme}\n", encoding="utf-8")

    if extra_args == ("--batch",):
        result = run_cli("--sarif", "--batch", str(batch))
    else:
        result = run_cli("--sarif", *extra_args, str(readme))

    assert result.returncode == 2
    assert result.stdout == ""
    assert expected_error in result.stderr


def test_cli_github_annotations_emit_warnings_to_stderr(tmp_path):
    readme = tmp_path / "README,weak.md"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--github-annotations", str(readme))
    annotation_lines = result.stderr.splitlines()

    assert result.returncode == 0
    assert "README first-screen score:" in result.stdout
    assert len(annotation_lines) == 5
    assert all(line.startswith("::warning ") for line in annotation_lines)
    assert all(f"file={str(readme).replace(',', '%2C')}" in line for line in annotation_lines)
    assert any("line=1" in line for line in annotation_lines)
    assert "The first screen does not clearly say what the project is." in result.stderr
    assert "Suggested fix:" in result.stderr


def test_cli_github_annotations_keep_json_stdout_parseable(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--json", "--github-annotations", str(readme))
    data = json.loads(result.stdout)

    assert result.returncode == 0
    assert data["source"] == str(readme)
    assert data["total_score"] < 100
    assert result.stderr.startswith("::warning ")


def test_cli_github_annotations_with_out_keep_stdout_message(tmp_path):
    readme = tmp_path / "README.md"
    out = tmp_path / "report.txt"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--github-annotations", "--out", str(out), str(readme))

    assert result.returncode == 0
    assert result.stdout == f"Wrote report to {out}\n"
    assert "README first-screen score:" in out.read_text(encoding="utf-8")
    assert result.stderr.startswith("::warning ")


def test_cli_github_annotations_from_stdin_do_not_include_file_or_line():
    result = run_cli("--github-annotations", "-", input_text=WEAK_README)
    annotation_lines = result.stderr.splitlines()

    assert result.returncode == 0
    assert "Source: stdin" in result.stdout
    assert annotation_lines
    assert all("file=" not in line for line in annotation_lines)
    assert all("line=" not in line for line in annotation_lines)


def test_cli_github_annotations_reject_batch(tmp_path):
    readme = tmp_path / "README.md"
    batch = tmp_path / "batch.txt"
    readme.write_text(README, encoding="utf-8")
    batch.write_text(f"{readme}\n", encoding="utf-8")

    result = run_cli("--github-annotations", "--batch", str(batch))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--github-annotations cannot be used with --batch" in result.stderr


def test_cli_single_summary_output(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--summary", str(readme))

    assert result.returncode == 0
    assert "README first-screen score:" in result.stdout
    assert result.stdout.endswith(
        f"Summary: score=26/100, grade=unclear, source={readme}, "
        "fix_first=Open with a project name and one-sentence definition "
        "before any secondary detail.\n"
    )
    assert result.stderr == ""


def test_cli_github_step_summary_output_includes_baseline_comparison(tmp_path):
    current = tmp_path / "README.md"
    baseline = tmp_path / "README-before.md"
    current.write_text(README, encoding="utf-8")
    baseline.write_text(WEAK_README, encoding="utf-8")

    result = run_cli(
        "--format",
        "github-step-summary",
        "--baseline",
        str(baseline),
        str(current),
    )

    assert result.returncode == 0
    assert result.stdout.startswith("# README First-Screen Summary\n")
    assert "| Score | 98/100 |" in result.stdout
    assert "| Grade | excellent |" in result.stdout
    assert "| First-screen scope | 18/30 lines, 298/2400 chars |" in result.stdout
    assert "## Comparison" in result.stdout
    assert "| 26/100 | 98/100 | +72 | improved |" in result.stdout
    assert "## Top Priority Fixes" in result.stdout
    assert "## Section Scores" in result.stdout
    assert "| What Is It | 18/20 |" in result.stdout
    assert "README first-screen score:" not in result.stdout
    assert result.stderr == ""


def test_cli_github_step_summary_output_can_be_written_to_file(tmp_path):
    readme = tmp_path / "README.md"
    out = tmp_path / "github-step-summary.md"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli(
        "--format",
        "github-step-summary",
        "--out",
        str(out),
        str(readme),
    )
    report_text = out.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert result.stdout == f"Wrote report to {out}\n"
    assert report_text.startswith("# README First-Screen Summary\n")
    assert "| Score | 26/100 |" in report_text
    assert "- Open with a project name and one-sentence definition" in report_text
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("extra_args", "expected_error"),
    [
        (("--json",), "--format github-step-summary cannot be used with --json"),
        (("--sarif",), "--format github-step-summary cannot be used with --sarif"),
        (("--fix-plan",), "--format github-step-summary cannot be used with --fix-plan"),
        (("--summary",), "--format github-step-summary cannot be used with --summary"),
    ],
)
def test_cli_github_step_summary_rejects_incompatible_options(
    tmp_path,
    extra_args,
    expected_error,
):
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")

    result = run_cli("--format", "github-step-summary", *extra_args, str(readme))

    assert result.returncode == 2
    assert result.stdout == ""
    assert expected_error in result.stderr


def test_cli_summary_rejects_json(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")

    result = run_cli("--summary", "--json", str(readme))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--summary cannot be used with --json" in result.stderr


def test_cli_fix_plan_outputs_markdown_plan_for_weak_readme(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--fix-plan", str(readme))

    assert result.returncode == 0
    assert result.stdout.startswith("# README First-Screen Remediation Plan\n")
    assert f"**Source:** {readme}" in result.stdout
    assert "**Score:** 26/100 (unclear)" in result.stdout
    assert "## First-Screen Evidence" in result.stdout
    assert "- First heading line: 1" in result.stdout
    assert "## Top 3 Priority Fixes" in result.stdout
    assert (
        "- Open with a project name and one-sentence definition before any secondary detail."
        in result.stdout
    )
    assert "## Suggested Opening Shape" in result.stdout
    assert "````markdown" in result.stdout
    assert result.stderr == ""


def test_cli_fix_json_outputs_structured_remediation_items(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--fix-json", str(readme))
    data = json.loads(result.stdout)

    assert result.returncode == 0
    assert data == {
        "schema_version": "1.0",
        "source": str(readme),
        "total_score": 26,
        "grade": "unclear",
        "evidence": {
            "first_screen": {
                "line_limit": 30,
                "char_limit": 2400,
                "lines_seen": 5,
                "chars_seen": 142,
            },
            "items": [
                "First heading line: 1",
                "Badges before explanation: 3",
            ],
        },
        "fixes": [
            {
                "priority": 1,
                "issue": "The first screen does not clearly say what the project is.",
                "suggestion": (
                    "Open with a project name and one-sentence definition "
                    "before any secondary detail."
                ),
                "section": "what_is_it",
                "rule_id": "what_is_it",
            },
            {
                "priority": 2,
                "issue": "No clear target user is named.",
                "suggestion": "Put the target user and main outcome in the opening paragraph.",
                "section": "target_user",
                "rule_id": "target_user",
            },
            {
                "priority": 3,
                "issue": "No install or run command was found.",
                "suggestion": "Add a copy-paste install or run command to the first screen.",
                "section": "quick_start",
                "rule_id": "quick_start",
            },
        ],
    }
    assert result.stderr == ""


def test_cli_fix_json_output_can_be_written_to_file(tmp_path):
    readme = tmp_path / "README.md"
    out = tmp_path / "artifacts" / "fixes.json"
    readme.write_text(WEAK_README, encoding="utf-8")

    expected = run_cli("--fix-json", str(readme))
    result = run_cli("--fix-json", "--out", str(out), str(readme))
    report_text = out.read_text(encoding="utf-8")
    data = json.loads(report_text)

    assert expected.returncode == 0
    assert result.returncode == 0
    assert result.stdout == f"Wrote report to {out}\n"
    assert report_text == expected.stdout
    assert data["fixes"][0]["priority"] == 1
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("extra_args", "expected_error"),
    [
        (("--json",), "--fix-json cannot be used with --json"),
        (("--sarif",), "--fix-json cannot be used with --sarif"),
        (("--summary",), "--fix-json cannot be used with --summary"),
        (("--fix-plan",), "--fix-json cannot be used with --fix-plan"),
        (
            ("--format", "github-step-summary"),
            "--format github-step-summary cannot be used with --fix-json",
        ),
        (("--batch",), "--fix-json cannot be used with --batch"),
    ],
)
def test_cli_fix_json_rejects_incompatible_options(
    tmp_path,
    extra_args,
    expected_error,
):
    readme = tmp_path / "README.md"
    batch = tmp_path / "batch.txt"
    readme.write_text(README, encoding="utf-8")
    batch.write_text(f"{readme}\n", encoding="utf-8")

    if extra_args == ("--batch",):
        result = run_cli("--fix-json", "--batch", str(batch))
    else:
        result = run_cli("--fix-json", *extra_args, str(readme))

    assert result.returncode == 2
    assert result.stdout == ""
    assert expected_error in result.stderr


def test_cli_fix_json_rejects_baseline(tmp_path):
    current = tmp_path / "README.md"
    baseline = tmp_path / "README-before.md"
    current.write_text(README, encoding="utf-8")
    baseline.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--fix-json", "--baseline", str(baseline), str(current))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--baseline cannot be used with --fix-json" in result.stderr


def test_cli_fix_plan_rejects_json(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")

    result = run_cli("--fix-plan", "--json", str(readme))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--fix-plan cannot be used with --json" in result.stderr


def test_cli_fix_plan_rejects_batch(tmp_path):
    readme = tmp_path / "README.md"
    batch = tmp_path / "batch.txt"
    readme.write_text(README, encoding="utf-8")
    batch.write_text(f"{readme}\n", encoding="utf-8")

    result = run_cli("--fix-plan", "--batch", str(batch))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--fix-plan cannot be used with --batch" in result.stderr



def test_cli_multiple_positional_sources_use_batch_human_output(tmp_path):
    good = tmp_path / "README-good.md"
    weak = tmp_path / "README-weak.md"
    good.write_text(README, encoding="utf-8")
    weak.write_text(WEAK_README, encoding="utf-8")

    result = run_cli(str(good), str(weak))

    assert result.returncode == 0
    assert "README first-screen batch: 2 sources, 2 ok, 0 errors" in result.stdout
    assert f"  - ok     98/100 excellent {good}" in result.stdout
    assert f"  - ok     26/100 unclear {weak}" in result.stdout
    assert result.stderr == ""


def test_cli_multiple_positional_sources_support_json_and_fail_under(tmp_path):
    good = tmp_path / "README-good.md"
    weak = tmp_path / "README-weak.md"
    good.write_text(README, encoding="utf-8")
    weak.write_text(WEAK_README, encoding="utf-8")

    json_result = run_cli("--json", str(good), str(weak))
    fail_result = run_cli("--fail-under", "80", str(good), str(weak))
    data = json.loads(json_result.stdout)

    assert json_result.returncode == 0
    assert data["item_count"] == 2
    assert data["ok_count"] == 2
    assert data["items"][0]["source"] == str(good)
    assert data["items"][1]["source"] == str(weak)
    assert fail_result.returncode == 1
    assert "README first-screen batch: 2 sources, 2 ok, 0 errors" in fail_result.stdout
    assert json_result.stderr == ""
    assert fail_result.stderr == ""


@pytest.mark.parametrize(
    ("flag", "expected_error"),
    [
        ("--sarif", "--sarif cannot be used with multiple sources"),
        ("--github-annotations", "--github-annotations cannot be used with multiple sources"),
        ("--fix-plan", "--fix-plan cannot be used with multiple sources"),
        ("--fix-json", "--fix-json cannot be used with multiple sources"),
    ],
)
def test_cli_multiple_positional_sources_reject_single_source_modes(tmp_path, flag, expected_error):
    good = tmp_path / "README-good.md"
    weak = tmp_path / "README-weak.md"
    good.write_text(README, encoding="utf-8")
    weak.write_text(WEAK_README, encoding="utf-8")

    result = run_cli(flag, str(good), str(weak))

    assert result.returncode == 2
    assert result.stdout == ""
    assert expected_error in result.stderr


def test_cli_multiple_positional_sources_reject_baseline(tmp_path):
    current = tmp_path / "README.md"
    second = tmp_path / "README-second.md"
    baseline = tmp_path / "README-before.md"
    current.write_text(README, encoding="utf-8")
    second.write_text(README, encoding="utf-8")
    baseline.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--baseline", str(baseline), str(current), str(second))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--baseline cannot be used with multiple sources" in result.stderr


def test_pre_commit_hook_metadata_is_present():
    hook_text = (REPO_ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")

    assert "id: readme-first-screen" in hook_text
    assert "entry: readme-first-screen" in hook_text
    assert "language: python" in hook_text
    assert "types_or: [markdown]" in hook_text
    assert "pass_filenames: true" in hook_text


def test_cli_batch_human_output(tmp_path):
    good = tmp_path / "README-good.md"
    weak = tmp_path / "README-weak.md"
    batch = tmp_path / "batch.txt"
    good.write_text(README, encoding="utf-8")
    weak.write_text(WEAK_README, encoding="utf-8")
    batch.write_text(
        f"\n# release candidates\n{good}\n\n{weak}\n",
        encoding="utf-8",
    )

    result = run_cli("--batch", str(batch))

    assert result.returncode == 0
    assert "README first-screen batch: 2 sources, 2 ok, 0 errors" in result.stdout
    assert "Average score:" in result.stdout
    assert f"  - ok     98/100 excellent {good}" in result.stdout
    assert f"  - ok     26/100 unclear {weak}" in result.stdout
    assert result.stderr == ""


def test_cli_batch_summary_output(tmp_path):
    good = tmp_path / "README-good.md"
    weak = tmp_path / "README-weak.md"
    batch = tmp_path / "batch.txt"
    good.write_text(README, encoding="utf-8")
    weak.write_text(WEAK_README, encoding="utf-8")
    batch.write_text(f"{good}\n{weak}\n", encoding="utf-8")

    result = run_cli("--summary", "--batch", str(batch))

    assert result.returncode == 0
    assert "README first-screen batch: 2 sources, 2 ok, 0 errors" in result.stdout
    assert result.stdout.endswith(
        "Summary: item_count=2, ok_count=2, error_count=0, "
        f"average_score=62.0/100, lowest_ok={weak} (26/100 unclear)\n"
    )
    assert result.stderr == ""


def test_cli_batch_github_step_summary_output(tmp_path):
    good = tmp_path / "README-good.md"
    weak = tmp_path / "README-weak.md"
    batch = tmp_path / "batch.txt"
    good.write_text(README, encoding="utf-8")
    weak.write_text(WEAK_README, encoding="utf-8")
    batch.write_text(f"{good}\n{weak}\n", encoding="utf-8")

    result = run_cli("--format", "github-step-summary", "--batch", str(batch))

    assert result.returncode == 0
    assert result.stdout.startswith("# README First-Screen Batch Summary\n")
    assert "| Sources | 2 |" in result.stdout
    assert "| OK | 2 |" in result.stdout
    assert "| Errors | 0 |" in result.stdout
    assert "| Average score | 62.0/100 |" in result.stdout
    assert f"| {good} | ok | 98/100 | excellent |" in result.stdout
    assert f"| {weak} | ok | 26/100 | unclear |" in result.stdout
    assert f"<summary>{weak}: 26/100 unclear</summary>" in result.stdout
    assert "| First-screen scope | 5/30 lines," in result.stdout
    assert "## Top Priority Fixes" in result.stdout
    assert "## Section Scores" in result.stdout
    assert result.stderr == ""


def test_cli_batch_json_output_continues_after_missing_source(tmp_path):
    readme = tmp_path / "README.md"
    missing = tmp_path / "missing.md"
    batch = tmp_path / "batch.txt"
    readme.write_text(README, encoding="utf-8")
    batch.write_text(f"{readme}\n{missing}\n", encoding="utf-8")

    result = run_cli("--json", "--batch", str(batch))
    data = json.loads(result.stdout)

    assert result.returncode == 0
    assert data == {
        "schema_version": "1.0",
        "item_count": 2,
        "ok_count": 1,
        "error_count": 1,
        "average_score": 98.0,
        "items": [
            {
                "source": str(readme),
                "status": "ok",
                "total_score": 98,
                "grade": "excellent",
            },
            {
                "source": str(missing),
                "status": "error",
                "error": f"README file not found: {missing}",
            },
        ],
    }
    assert result.stderr == ""


def test_cli_batch_out_writes_report_to_file(tmp_path):
    readme = tmp_path / "README.md"
    batch = tmp_path / "batch.txt"
    out = tmp_path / "artifacts" / "batch-report.json"
    readme.write_text(README, encoding="utf-8")
    batch.write_text(f"{readme}\n", encoding="utf-8")

    expected = run_cli("--json", "--batch", str(batch))
    result = run_cli("--json", "--batch", str(batch), "--out", str(out))

    assert expected.returncode == 0
    assert result.returncode == 0
    assert result.stdout == f"Wrote report to {out}\n"
    assert out.read_text(encoding="utf-8") == expected.stdout
    assert result.stderr == ""


def test_cli_batch_fail_under_exits_one_for_low_scores_or_load_errors(tmp_path):
    good = tmp_path / "README-good.md"
    weak = tmp_path / "README-weak.md"
    missing = tmp_path / "missing.md"
    low_score_batch = tmp_path / "low-score-batch.txt"
    missing_batch = tmp_path / "missing-batch.txt"
    good.write_text(README, encoding="utf-8")
    weak.write_text(WEAK_README, encoding="utf-8")
    low_score_batch.write_text(f"{good}\n{weak}\n", encoding="utf-8")
    missing_batch.write_text(f"{good}\n{missing}\n", encoding="utf-8")

    low_score_result = run_cli("--batch", str(low_score_batch), "--fail-under", "80")
    missing_result = run_cli("--batch", str(missing_batch), "--fail-under", "0")

    assert low_score_result.returncode == 1
    assert "README first-screen batch: 2 sources, 2 ok, 0 errors" in low_score_result.stdout
    assert low_score_result.stderr == ""
    assert missing_result.returncode == 1
    assert "README first-screen batch: 2 sources, 1 ok, 1 error" in missing_result.stdout
    assert f"README file not found: {missing}" in missing_result.stdout
    assert missing_result.stderr == ""


def test_cli_human_output_can_be_written_to_file(tmp_path):
    readme = tmp_path / "README.md"
    out = tmp_path / "report.txt"
    readme.write_text(README, encoding="utf-8")

    expected = run_cli(str(readme))
    result = run_cli("--out", str(out), str(readme))
    report_text = out.read_text(encoding="utf-8")

    assert expected.returncode == 0
    assert result.returncode == 0
    assert result.stdout == f"Wrote report to {out}\n"
    assert "README first-screen score:" not in result.stdout
    assert report_text == expected.stdout
    assert result.stderr == ""


def test_cli_json_output_can_be_written_to_file(tmp_path):
    readme = tmp_path / "README.md"
    out = tmp_path / "report.json"
    readme.write_text(README, encoding="utf-8")

    expected = run_cli("--json", str(readme))
    result = run_cli("--json", "--out", str(out), str(readme))
    report_text = out.read_text(encoding="utf-8")
    data = json.loads(report_text)

    assert expected.returncode == 0
    assert result.returncode == 0
    assert result.stdout == f"Wrote report to {out}\n"
    assert report_text == expected.stdout
    assert data["schema_version"] == "1.0"
    assert data["source"] == str(readme)
    assert data["total_score"] >= 70
    assert result.stderr == ""


def test_cli_out_creates_parent_directories(tmp_path):
    readme = tmp_path / "README.md"
    out = tmp_path / "artifacts" / "reports" / "readme-score.txt"
    readme.write_text(README, encoding="utf-8")

    result = run_cli("--out", str(out), str(readme))

    assert result.returncode == 0
    assert result.stdout == f"Wrote report to {out}\n"
    assert out.exists()
    assert "README first-screen score:" in out.read_text(encoding="utf-8")
    assert result.stderr == ""


def test_cli_fail_under_with_out_writes_report_before_exiting_one(tmp_path):
    readme = tmp_path / "README.md"
    out = tmp_path / "failed-report.json"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--json", "--out", str(out), "--fail-under", "100", str(readme))
    data = json.loads(out.read_text(encoding="utf-8"))

    assert result.returncode == 1
    assert result.stdout == f"Wrote report to {out}\n"
    assert data["source"] == str(readme)
    assert data["total_score"] < 100
    assert result.stderr == ""


def test_cli_human_output_includes_baseline_comparison(tmp_path):
    current = tmp_path / "README.md"
    baseline = tmp_path / "README-before.md"
    current.write_text(README, encoding="utf-8")
    baseline.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--baseline", str(baseline), str(current))

    assert result.returncode == 0
    assert result.stderr == ""
    assert (
        result.stdout.index("First screen analyzed:")
        < result.stdout.index("Comparison:")
        < result.stdout.index("Section scores:")
    )
    assert "  - Baseline score: 26/100" in result.stdout
    assert "  - Current score: 98/100" in result.stdout
    assert "  - Delta: +72 (improved)" in result.stdout


def test_cli_json_output_includes_baseline_comparison(tmp_path):
    current = tmp_path / "README.md"
    baseline = tmp_path / "README-before.md"
    current.write_text(README, encoding="utf-8")
    baseline.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--json", "--baseline", str(baseline), str(current))
    data = json.loads(result.stdout)

    assert result.returncode == 0
    assert data["source"] == str(current)
    assert data["comparison"] == {
        "baseline_source": str(baseline),
        "baseline_total_score": 26,
        "current_total_score": 98,
        "delta": 72,
        "result": "improved",
    }
    assert result.stderr == ""


def test_cli_fail_under_passes_when_score_meets_threshold(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")

    result = run_cli("--fail-under", "0", str(readme))

    assert result.returncode == 0
    assert "README first-screen score:" in result.stdout
    assert result.stderr == ""


def test_cli_fail_under_exits_one_when_score_is_below_threshold(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--fail-under", "100", str(readme))

    assert result.returncode == 1
    assert "README first-screen score:" in result.stdout
    assert result.stderr == ""


def test_cli_fail_under_json_output_still_emitted_on_failure(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--json", "--fail-under", "100", str(readme))
    data = json.loads(result.stdout)

    assert result.returncode == 1
    assert data["source"] == str(readme)
    assert data["total_score"] < 100
    assert result.stderr == ""


def test_cli_fail_under_applies_to_current_score_only_with_baseline(tmp_path):
    current = tmp_path / "README.md"
    baseline = tmp_path / "README-before.md"
    current.write_text(README, encoding="utf-8")
    baseline.write_text(WEAK_README, encoding="utf-8")

    result = run_cli("--baseline", str(baseline), "--fail-under", "90", str(current))

    assert result.returncode == 0
    assert "  - Baseline score: 26/100" in result.stdout
    assert "  - Current score: 98/100" in result.stdout
    assert result.stderr == ""


def test_cli_fail_under_rejects_invalid_threshold(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")

    result = run_cli("--fail-under", "101", str(readme))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "argument --fail-under: must be an integer from 0 to 100" in result.stderr


def test_cli_missing_file_exits_two():
    result = run_cli("missing.md")

    assert result.returncode == 2
    assert "README file not found" in result.stderr


def test_cli_baseline_load_error_exits_two(tmp_path):
    readme = tmp_path / "README.md"
    missing_baseline = tmp_path / "missing-before.md"
    readme.write_text(README, encoding="utf-8")

    result = run_cli("--baseline", str(missing_baseline), str(readme))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "could not load baseline: README file not found" in result.stderr
    assert str(missing_baseline) in result.stderr
