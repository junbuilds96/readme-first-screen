# CI Quality Gate

Use `readme-first-screen` in CI when README clarity is part of your release
bar. The score gives maintainers a measurable first-screen quality gate: can a
new visitor quickly understand what the project is, who it is for, why it
matters, and how to try it?

## GitHub Actions

Copy this workflow into `.github/workflows/readme-first-screen.yml`:

```yaml
name: README first-screen

on:
  pull_request:
    paths:
      - README.md
      - .github/workflows/readme-first-screen.yml
  push:
    branches: [main]
    paths:
      - README.md
      - .github/workflows/readme-first-screen.yml

jobs:
  readme-first-screen:
    runs-on: ubuntu-latest
    env:
      README_FIRST_SCREEN_FAIL_UNDER: "80"
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install readme-first-screen
        run: python -m pip install git+https://github.com/junbuilds96/readme-first-screen.git

      - name: Score README first screen
        run: readme-first-screen --json --github-annotations --out artifacts/readme-first-screen.json --fail-under "$README_FIRST_SCREEN_FAIL_UNDER" README.md

      - name: Upload README score artifact
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: readme-first-screen
          path: artifacts/readme-first-screen.json
```

Adjust `README_FIRST_SCREEN_FAIL_UNDER` to match your project standard. A higher
threshold makes README clarity a stricter merge requirement; a lower threshold is
useful while adopting the check. The `--out` flag writes the JSON report before
the score gate exits, so failed runs can still upload the report artifact.
`--github-annotations` sends warning annotations to the workflow log while
keeping stdout and the JSON artifact valid.

## Local Preflight

Run the same gate before opening a pull request:

```bash
README_FIRST_SCREEN_FAIL_UNDER=80 readme-first-screen --fail-under "$README_FIRST_SCREEN_FAIL_UNDER" README.md
```
