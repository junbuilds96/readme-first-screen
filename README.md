# readme-first-screen

readme-first-screen is a Python CLI for open-source maintainers who need to know
whether a stranger can understand their GitHub README first screen in 10 seconds.
It is not a generic Markdown linter and it does not generate README text. It
scores the opening screen, finds comprehension blockers, and suggests concrete
fixes.

## Quick start

```bash
git clone https://github.com/junbuilds96/readme-first-screen.git
cd readme-first-screen
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
readme-first-screen README.md
```

Check a public GitHub repository:

```bash
readme-first-screen https://github.com/owner/repo
```

Check Markdown from stdin:

```bash
cat README.md | readme-first-screen -
```

Get machine-readable output:

```bash
readme-first-screen --json README.md
```

Gate CI on a minimum score:

```bash
readme-first-screen --fail-under 80 README.md
```

Compare a README rewrite against a before version:

```bash
readme-first-screen --baseline README-before.md README.md
```

For a copy-paste GitHub Actions quality gate and local preflight command, see
[CI Quality Gate](docs/ci.md).

## Sample output

```text
README first-screen score: 87/100 (excellent)
Source: README.md

Section scores:
  - what is it: 18/20
  - target user: 15/15
  - problem value: 14/15
  - quick start: 18/20
  - proof credibility: 11/15
  - visual clarity: 11/15

Strengths:
  - The opening explains what the project is.
  - The first screen identifies who it is for.
  - A runnable command appears on the first screen.

Issues:
  - No demo, sample output, or proof example was found.

Actionable suggestions:
  - Include sample output, a demo link, screenshot, or adoption proof.
```

## JSON schema

`--json` prints a stable JSON object:

```json
{
  "schema_version": "1.0",
  "total_score": 87,
  "max_score": 100,
  "grade": "excellent",
  "source": "README.md",
  "first_screen": {
    "line_limit": 30,
    "char_limit": 2400,
    "lines_seen": 30,
    "chars_seen": 2400
  },
  "categories": {
    "what_is_it": {
      "score": 18,
      "max_score": 20,
      "strengths": [],
      "issues": [],
      "suggestions": []
    },
    "target_user": {
      "score": 15,
      "max_score": 15,
      "strengths": [],
      "issues": [],
      "suggestions": []
    },
    "problem_value": {
      "score": 14,
      "max_score": 15,
      "strengths": [],
      "issues": [],
      "suggestions": []
    },
    "quick_start": {
      "score": 18,
      "max_score": 20,
      "strengths": [],
      "issues": [],
      "suggestions": []
    },
    "proof_credibility": {
      "score": 11,
      "max_score": 15,
      "strengths": [],
      "issues": [],
      "suggestions": []
    },
    "visual_clarity": {
      "score": 11,
      "max_score": 15,
      "strengths": [],
      "issues": [],
      "suggestions": []
    }
  },
  "strengths": [],
  "issues": [],
  "suggestions": [],
  "metadata": {
    "line_count": 80,
    "heading_count": 10,
    "first_heading_line": 1,
    "first_explanation_line": 3,
    "badges_before_explanation": 0
  }
}
```

The category keys are stable for the `1.0` schema:

- `what_is_it`
- `target_user`
- `problem_value`
- `quick_start`
- `proof_credibility`
- `visual_clarity`

When `--baseline PATH_OR_URL` is provided, JSON output also includes a top-level
`comparison` object with the baseline source, baseline score, current score,
signed delta, and result (`improved`, `regressed`, or `unchanged`).

## Scoring rubric

The total score is 100 points:

- `what_is_it` (20): the first screen names the project, defines the concrete product shape, and avoids vague adjective-first positioning.
- `target_user` (15): the first screen says who should care.
- `problem_value` (15): the first screen states the pain, outcome, or job-to-be-done.
- `quick_start` (20): the README includes copy-paste install/run commands and at least one example. First-screen commands score higher.
- `proof_credibility` (15): the README shows license, CI/tests, demo, screenshot, sample output, or other proof signals.
- `visual_clarity` (15): the first heading and explanation arrive early, the first screen is scannable, and badges do not crowd out the explanation.

The first 30 lines or 2400 characters count as the first screen. The scorer gives
extra weight to signals found there, while still inspecting the whole README for
quick start and proof evidence.

## Anti-patterns it catches

- Badge wall before explanation
- Vague adjectives without concrete nouns
- No install or run command
- No target user
- No example
- No license, CI, demo, sample output, or proof signal
- Heading starts too late

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Run the CLI from the checkout:

```bash
python -m readme_first_screen README.md
```

## Safety and limitations

readme-first-screen uses deterministic regular-expression and structure
heuristics. It does not call an LLM, upload README text, or require network
access unless you pass a GitHub or raw URL as input.

The score is a fast editorial signal, not a universal truth. It can miss domain
specific phrasing, over-reward keyword stuffing, or under-score strong READMEs
that intentionally lead with visuals. Treat suggestions as review prompts.

## Roadmap

- GitHub Action that comments on pull requests when the first screen regresses
- Config file for project-specific vocabulary and thresholds
- More precise Markdown parsing while keeping deterministic scoring

## License

MIT. See [LICENSE](LICENSE).
