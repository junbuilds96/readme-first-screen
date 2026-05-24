import json
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


def run_cli(*args, input_text=None):
    return subprocess.run(
        [sys.executable, "-m", "readme_first_screen", *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_reads_local_file(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")

    result = run_cli(str(readme))

    assert result.returncode == 0
    assert "README first-screen score:" in result.stdout
    assert "Section scores:" in result.stdout
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
