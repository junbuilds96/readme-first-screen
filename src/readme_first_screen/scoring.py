from __future__ import annotations

import re
from dataclasses import dataclass

from .models import CATEGORY_NAMES, CategoryScore, ScoreReport


FIRST_SCREEN_LINES = 30
FIRST_SCREEN_CHARS = 2400

CATEGORY_WEIGHTS = {
    "what_is_it": 20,
    "target_user": 15,
    "problem_value": 15,
    "quick_start": 20,
    "proof_credibility": 15,
    "visual_clarity": 15,
}

CONCRETE_NOUNS = {
    "api",
    "app",
    "bot",
    "cli",
    "dashboard",
    "extension",
    "framework",
    "github action",
    "library",
    "package",
    "plugin",
    "sdk",
    "server",
    "service",
    "tool",
    "workflow",
}

TARGET_PATTERNS = (
    r"\bfor\s+(developers|maintainers|teams|users|founders|engineers|designers|writers|contributors)\b",
    r"\bfor\s+[a-z0-9][a-z0-9 -]{2,40}\b",
    r"\bif you\b",
    r"\bwhen you\b",
    r"\bwho (need|needs|want|wants|build|builds|maintain|maintains)\b",
)

VALUE_PATTERNS = (
    r"\bso you can\b",
    r"\bwithout\b",
    r"\breduce[sd]?\b",
    r"\bsave[sd]?\b",
    r"\bprevent[sd]?\b",
    r"\bcatch(?:es)?\b",
    r"\bunderstand\b",
    r"\bbefore\b",
    r"\binstead of\b",
)

COMMAND_PATTERNS = (
    r"\bpipx?\s+install\b",
    r"\buv\s+(tool\s+)?(run|install)\b",
    r"\bpython\s+-m\b",
    r"\bnpm\s+(install|run|exec)\b",
    r"\bnpx\b",
    r"\bmake\s+[a-z0-9_-]+\b",
    r"\bdocker\s+(run|compose)\b",
    r"\breadme-first-screen\b",
)

PROOF_PATTERNS = (
    r"\blicen[cs]e\b",
    r"\bmit\b",
    r"\bci\b",
    r"\bgithub actions\b",
    r"\bdemo\b",
    r"\bexample\b",
    r"\bscreenshot\b",
    r"\bused by\b",
    r"\bcoverage\b",
    r"\btests?\b",
    r"\brelease\b",
)

VAGUE_ADJECTIVES = {
    "awesome",
    "beautiful",
    "blazing",
    "delightful",
    "easy",
    "fast",
    "flexible",
    "intuitive",
    "lightweight",
    "modern",
    "powerful",
    "simple",
}

BADGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)|<img\b[^>]*>", re.IGNORECASE)
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S+")


@dataclass(frozen=True)
class ReadmeFacts:
    text: str
    lines: list[str]
    first_lines: list[str]
    first_text: str
    first_text_plain: str
    full_text_plain: str
    code_blocks: list[str]
    first_code_blocks: list[str]
    headings: list[tuple[int, str]]
    badges_before_explanation: int
    first_explanation_line: int | None
    first_heading_line: int | None


def score_readme(text: str, source: str = "input") -> ScoreReport:
    facts = _extract_facts(text)
    categories = {
        "what_is_it": _score_what_is_it(facts),
        "target_user": _score_target_user(facts),
        "problem_value": _score_problem_value(facts),
        "quick_start": _score_quick_start(facts),
        "proof_credibility": _score_proof_credibility(facts),
        "visual_clarity": _score_visual_clarity(facts),
    }
    total = sum(category.score for category in categories.values())
    strengths = _top_items(categories, "strengths", limit=20)
    issues = _top_items(categories, "issues", limit=20)
    suggestions = _top_items(categories, "suggestions", limit=20)

    return ScoreReport(
        total_score=total,
        max_score=100,
        grade=_grade(total),
        source=source,
        first_screen={
            "line_limit": FIRST_SCREEN_LINES,
            "char_limit": FIRST_SCREEN_CHARS,
            "lines_seen": min(len(facts.lines), FIRST_SCREEN_LINES),
            "chars_seen": min(len(text), FIRST_SCREEN_CHARS),
        },
        categories=categories,
        strengths=tuple(strengths),
        issues=tuple(issues),
        suggestions=tuple(suggestions),
        metadata={
            "line_count": len(facts.lines),
            "heading_count": len(facts.headings),
            "first_heading_line": facts.first_heading_line,
            "first_explanation_line": facts.first_explanation_line,
            "badges_before_explanation": facts.badges_before_explanation,
        },
    )


def _extract_facts(text: str) -> ReadmeFacts:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.splitlines()
    first_lines = lines[:FIRST_SCREEN_LINES]
    first_text = "\n".join(first_lines)[:FIRST_SCREEN_CHARS]
    code_blocks = CODE_FENCE_RE.findall(normalized)
    first_code_blocks = CODE_FENCE_RE.findall(first_text)
    headings = [
        (index + 1, line.strip())
        for index, line in enumerate(lines)
        if HEADING_RE.match(line)
    ]
    first_explanation_line = _first_explanation_line(lines)

    return ReadmeFacts(
        text=normalized,
        lines=lines,
        first_lines=first_lines,
        first_text=first_text,
        first_text_plain=_plain_text(first_text),
        full_text_plain=_plain_text(normalized),
        code_blocks=code_blocks,
        first_code_blocks=first_code_blocks,
        headings=headings,
        badges_before_explanation=_badges_before_explanation(lines, first_explanation_line),
        first_explanation_line=first_explanation_line,
        first_heading_line=headings[0][0] if headings else None,
    )


def _score_what_is_it(facts: ReadmeFacts) -> CategoryScore:
    score = 0
    strengths: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []
    first = facts.first_text_plain

    if _has_h1_in_first_screen(facts):
        score += 4
        strengths.append("The first screen names the project.")
    else:
        issues.append("The project name or first heading starts too late.")
        suggestions.append("Put a clear H1 project name at the top of the README.")

    if _has_definition(first):
        score += 8
        strengths.append("The opening explains what the project is.")
    else:
        issues.append("The first screen does not clearly say what the project is.")
        suggestions.append("Add a one-sentence definition near the top: '<name> is a ...'.")

    if _contains_concrete_noun(first):
        score += 4
    else:
        issues.append("The opening uses too few concrete product nouns.")
        suggestions.append("Name the concrete shape: CLI, library, GitHub Action, app, API, or service.")

    if _has_example_signal(facts.first_text):
        score += 2
        strengths.append("An example appears early.")
    else:
        suggestions.append("Show one tiny example in the first screen if the concept is not obvious.")

    if _vague_without_concrete(first):
        score -= 3
        issues.append("Vague adjectives appear before concrete explanation.")
        suggestions.append("Replace claims like 'simple' or 'powerful' with a concrete job and output.")

    return _category("what_is_it", score, strengths, issues, suggestions)


def _score_target_user(facts: ReadmeFacts) -> CategoryScore:
    score = 0
    strengths: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []
    first = facts.first_text_plain
    full = facts.full_text_plain

    if _matches_any(first, TARGET_PATTERNS):
        score += 11
        strengths.append("The first screen identifies who it is for.")
    elif _matches_any(full, TARGET_PATTERNS):
        score += 6
        issues.append("The target user appears, but not on the first screen.")
        suggestions.append("Move the target user into the opening paragraph.")
    else:
        issues.append("No clear target user is named.")
        suggestions.append("Say who should care, for example 'for maintainers of small open-source tools'.")

    if re.search(r"\b(stranger|newcomer|maintainer|contributor|developer|team|reader|user)\b", first):
        score += 4
    elif re.search(r"\b(stranger|newcomer|maintainer|contributor|developer|team|reader|user)\b", full):
        score += 2

    return _category("target_user", score, strengths, issues, suggestions)


def _score_problem_value(facts: ReadmeFacts) -> CategoryScore:
    score = 0
    strengths: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []
    first = facts.first_text_plain
    full = facts.full_text_plain

    if _matches_any(first, VALUE_PATTERNS):
        score += 8
        strengths.append("The first screen explains the practical value.")
    elif _matches_any(full, VALUE_PATTERNS):
        score += 4
        issues.append("The value is present, but it lands after the first screen.")
        suggestions.append("Move the main problem or outcome into the opening paragraph.")
    else:
        issues.append("The README does not state the problem or outcome clearly.")
        suggestions.append("Add a sentence that says what pain it prevents or what result it creates.")

    if re.search(r"\b(10 seconds?|first screen|scan|understand|confusing|unclear|before)\b", first):
        score += 4
    elif re.search(r"\b(10 seconds?|first screen|scan|understand|confusing|unclear|before)\b", full):
        score += 2

    if re.search(r"\b(checks?|scores?|reports?|flags?|detects?|suggests?)\b", first):
        score += 3

    return _category("problem_value", score, strengths, issues, suggestions)


def _score_quick_start(facts: ReadmeFacts) -> CategoryScore:
    score = 0
    strengths: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []
    first = facts.first_text_plain
    full = facts.full_text_plain
    code_text = "\n".join(facts.code_blocks)

    if _matches_any(first, COMMAND_PATTERNS) or _matches_any("\n".join(facts.first_code_blocks), COMMAND_PATTERNS):
        score += 10
        strengths.append("A runnable command appears on the first screen.")
    elif _matches_any(full, COMMAND_PATTERNS) or _matches_any(code_text, COMMAND_PATTERNS):
        score += 7
        strengths.append("A runnable command is included.")
        issues.append("The first runnable command appears after the first screen.")
        suggestions.append("Move one install or run command above the fold.")
    else:
        issues.append("No install or run command was found.")
        suggestions.append("Add a copy-paste install command and one copy-paste run command.")

    if re.search(r"\b(install|installation|quick start|usage|getting started)\b", full):
        score += 4
    else:
        issues.append("There is no obvious quick start or usage section.")
        suggestions.append("Add a short 'Quick start' or 'Usage' section.")

    if _has_example_signal(facts.text):
        score += 4
        strengths.append("The README includes an example.")
    else:
        issues.append("No concrete example was found.")
        suggestions.append("Show a realistic input and output example.")

    if len(facts.code_blocks) > 0:
        score += 2

    return _category("quick_start", score, strengths, issues, suggestions)


def _score_proof_credibility(facts: ReadmeFacts) -> CategoryScore:
    score = 0
    strengths: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []
    first = facts.first_text_plain
    full = facts.full_text_plain

    if _matches_any(first, PROOF_PATTERNS) or facts.badges_before_explanation > 0:
        score += 5
        strengths.append("Some credibility signal appears early.")
    elif _matches_any(full, PROOF_PATTERNS):
        score += 4
        strengths.append("The README includes credibility signals.")

    if re.search(r"\blicen[cs]e\b|\bmit\b|\bapache\b|\bgpl\b", full):
        score += 4
    else:
        issues.append("No license signal was found.")
        suggestions.append("Mention the license in the README and include a LICENSE file.")

    if re.search(r"\b(ci|tests?|coverage|github actions)\b", full, re.IGNORECASE) or "github/workflows" in full:
        score += 3
    else:
        issues.append("No CI, test, or quality signal was found.")
        suggestions.append("Add a CI/test badge or a short testing note once it exists.")

    if re.search(r"\b(demo|screenshot|example output|sample output|used by|case study)\b", full, re.IGNORECASE):
        score += 3
    else:
        issues.append("No demo, sample output, or proof example was found.")
        suggestions.append("Include sample output, a demo link, screenshot, or adoption proof.")

    return _category("proof_credibility", score, strengths, issues, suggestions)


def _score_visual_clarity(facts: ReadmeFacts) -> CategoryScore:
    score = 0
    strengths: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []

    if facts.first_heading_line is not None and facts.first_heading_line <= 3:
        score += 4
    else:
        issues.append("The first heading starts too late.")
        suggestions.append("Start with a concise H1 in the first three lines.")

    if facts.first_explanation_line is not None and facts.first_explanation_line <= 8:
        score += 4
        strengths.append("Explanation starts early.")
    else:
        issues.append("The first plain-language explanation starts too late.")
        suggestions.append("Put a one- or two-sentence explanation before badges, screenshots, and tables.")

    if facts.badges_before_explanation >= 4:
        score -= 4
        issues.append("Badge wall appears before the explanation.")
        suggestions.append("Keep at most one or two high-value badges above the opening explanation.")
    elif facts.badges_before_explanation <= 2:
        score += 3

    if _has_readable_first_screen(facts):
        score += 4
        strengths.append("The first screen is scannable.")
    else:
        issues.append("The first screen is dense or mostly structural markup.")
        suggestions.append("Use a short intro, short sections, and one compact example before deeper detail.")

    return _category("visual_clarity", score, strengths, issues, suggestions)


def _category(
    name: str,
    score: int,
    strengths: list[str],
    issues: list[str],
    suggestions: list[str],
) -> CategoryScore:
    max_score = CATEGORY_WEIGHTS[name]
    return CategoryScore(
        name=name,
        score=max(0, min(max_score, score)),
        max_score=max_score,
        strengths=tuple(dict.fromkeys(strengths)),
        issues=tuple(dict.fromkeys(issues)),
        suggestions=tuple(dict.fromkeys(suggestions)),
    )


def _plain_text(markdown: str) -> str:
    text = CODE_FENCE_RE.sub(" ", markdown)
    text = BADGE_RE.sub(" ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_>#|~-]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _first_explanation_line(lines: list[str]) -> int | None:
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        plain = _plain_text(stripped)
        if not plain:
            continue
        if HEADING_RE.match(stripped) or BADGE_RE.search(stripped):
            continue
        if len(plain.split()) >= 6:
            return index
    return None


def _badges_before_explanation(lines: list[str], first_explanation_line: int | None) -> int:
    limit = first_explanation_line or min(len(lines), FIRST_SCREEN_LINES)
    return sum(len(BADGE_RE.findall(line)) for line in lines[:limit])


def _has_h1_in_first_screen(facts: ReadmeFacts) -> bool:
    return any(line.lstrip().startswith("# ") for line in facts.first_lines)


def _has_definition(text: str) -> bool:
    return bool(
        re.search(
            r"\b(is|are|helps?|lets?|checks?|scores?|detects?|reports?|provides?|turns?|makes?)\b.{0,80}\b("
            + "|".join(re.escape(noun) for noun in CONCRETE_NOUNS)
            + r")\b",
            text,
        )
    )


def _contains_concrete_noun(text: str) -> bool:
    return any(noun in text for noun in CONCRETE_NOUNS)


def _vague_without_concrete(text: str) -> bool:
    words = set(re.findall(r"[a-z]+", text[:500]))
    return bool(words & VAGUE_ADJECTIVES) and not _contains_concrete_noun(text[:500])


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _has_example_signal(text: str) -> bool:
    return bool(re.search(r"\b(example|sample|output|usage)\b|```", text, re.IGNORECASE))


def _has_readable_first_screen(facts: ReadmeFacts) -> bool:
    nonblank = [line for line in facts.first_lines if line.strip()]
    if not nonblank:
        return False
    average_length = sum(len(line) for line in nonblank) / len(nonblank)
    heading_count = sum(1 for line in nonblank if HEADING_RE.match(line))
    code_line_count = sum(1 for line in nonblank if line.startswith("    ") or line.strip().startswith("```"))
    return average_length <= 110 and heading_count <= 5 and code_line_count <= 12


def _top_items(categories: dict[str, CategoryScore], field: str, limit: int) -> list[str]:
    items: list[str] = []
    for name in CATEGORY_NAMES:
        items.extend(getattr(categories[name], field))
    return list(dict.fromkeys(items))[:limit]


def _grade(score: int) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 50:
        return "needs_work"
    return "unclear"
