"""A tiny CLI for scoring the first screen of a GitHub README."""

from .scoring import ScoreReport, score_readme

__all__ = ["ScoreReport", "score_readme"]

__version__ = "0.1.0"
