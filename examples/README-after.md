# Task Pulse

Task Pulse is a Python CLI for release leads who need a quick snapshot of
blocked project tasks before a weekly status meeting. It reads a CSV task list,
groups blockers by owner, and prints the next action to follow up on.

## Quick start

```bash
python -m task_pulse examples/tasks.csv
```

## Example output

```text
Owner    Blocked  Next action
Ada      2        Review deployment checklist
Sam      1        Confirm staging credentials
```

## Proof

MIT License. CI runs unit tests for parsing and report formatting.
