# Contributing

Thanks for helping improve readme-first-screen.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## What belongs here

This project checks whether a stranger can understand a README first screen in
10 seconds. Contributions should keep that focus.

Good changes include:

- Better deterministic scoring rules
- Clearer report output
- Tests for README comprehension anti-patterns
- CLI input and packaging fixes
- Documentation that helps maintainers use the tool

Avoid adding README generation, broad Markdown linting, or required external AI
services to the core MVP.

## Pull requests

Please include tests for scoring or CLI behavior changes. If a scoring rule
changes expected output, explain the README pattern it is meant to catch.
