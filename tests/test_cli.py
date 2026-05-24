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


def test_cli_missing_file_exits_two():
    result = run_cli("missing.md")

    assert result.returncode == 2
    assert "README file not found" in result.stderr
