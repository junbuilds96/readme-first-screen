import json
import os
from pathlib import Path
import subprocess
import sys


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
