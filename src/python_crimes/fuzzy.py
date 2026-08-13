"""Small deterministic fuzzy matching helpers."""

from collections.abc import Iterable
from dataclasses import dataclass

from typed_errs import Nothing, Option, Some


@dataclass(frozen=True)
class StringMatch:
    """The closest candidate and its edit distance."""

    value: str
    distance: int


def levenshtein_distance(left: str, right: str) -> int:
    """Return the Levenshtein edit distance between two strings."""
    distances = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        diagonal = distances[0]
        distances[0] = left_index
        for right_index, right_char in enumerate(right, start=1):
            previous = distances[right_index]
            if left_char == right_char:
                distances[right_index] = diagonal
            else:
                distances[right_index] = 1 + min(
                    distances[right_index],
                    distances[right_index - 1],
                    diagonal,
                )
            diagonal = previous
    return distances[-1]


def closest_string(target: str, candidates: Iterable[str]) -> Option[StringMatch]:
    """Return the closest candidate with stable, human-friendly tie breaks."""
    matches = [
        StringMatch(candidate, levenshtein_distance(target, candidate))
        for candidate in candidates
    ]
    if not matches:
        return Nothing()

    def common_prefix(candidate: str) -> int:
        return next(
            (
                index
                for index, (left, right) in enumerate(
                    zip(target, candidate, strict=False)
                )
                if left != right
            ),
            min(len(target), len(candidate)),
        )

    return Some(
        min(
            matches,
            key=lambda match: (
                match.distance,
                -common_prefix(match.value),
                abs(len(target) - len(match.value)),
                match.value,
            ),
        )
    )
