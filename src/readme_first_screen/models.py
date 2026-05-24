from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CATEGORY_NAMES = (
    "what_is_it",
    "target_user",
    "problem_value",
    "quick_start",
    "proof_credibility",
    "visual_clarity",
)


@dataclass(frozen=True)
class CategoryScore:
    name: str
    score: int
    max_score: int
    strengths: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    suggestions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "max_score": self.max_score,
            "strengths": list(self.strengths),
            "issues": list(self.issues),
            "suggestions": list(self.suggestions),
        }


@dataclass(frozen=True)
class ScoreReport:
    total_score: int
    max_score: int
    grade: str
    source: str
    first_screen: dict[str, int]
    categories: dict[str, CategoryScore]
    strengths: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    suggestions: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "total_score": self.total_score,
            "max_score": self.max_score,
            "grade": self.grade,
            "source": self.source,
            "first_screen": self.first_screen,
            "categories": {
                name: self.categories[name].to_dict()
                for name in CATEGORY_NAMES
            },
            "strengths": list(self.strengths),
            "issues": list(self.issues),
            "suggestions": list(self.suggestions),
            "metadata": self.metadata,
        }
