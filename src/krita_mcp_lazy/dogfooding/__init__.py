"""Dogfooding suite and production benchmark runner."""

from krita_mcp_lazy.dogfooding.challenges import Challenge, get_all_challenges
from krita_mcp_lazy.dogfooding.runner import (
    BenchmarkReport,
    ChallengeResult,
    DogfoodingRunner,
)

__all__ = [
    "BenchmarkReport",
    "Challenge",
    "ChallengeResult",
    "DogfoodingRunner",
    "get_all_challenges",
]
