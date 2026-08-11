"""First-class :mod:`typed_errs` patterns for ``match_``."""

from __future__ import annotations

from typing import Any

from typed_errs import Err, Nothing, Ok, Option, Some

from .patterns import Match, Pattern


class OkPattern(Pattern[object]):
    def match(self, value: object) -> Option[Match]:
        return Some(Match((value.value,))) if isinstance(value, Ok) else Nothing()


class ErrPattern(Pattern[object]):
    def match(self, value: object) -> Option[Match]:
        return Some(Match((value.error,))) if isinstance(value, Err) else Nothing()


class SomePattern(Pattern[object]):
    def match(self, value: object) -> Option[Match]:
        return Some(Match((value.value,))) if isinstance(value, Some) else Nothing()


class NothingPattern(Pattern[object]):
    def match(self, value: object) -> Option[Match]:
        return Some(Match()) if isinstance(value, Nothing) else Nothing()


OK: Pattern[Any] = OkPattern()
ERR: Pattern[Any] = ErrPattern()
SOME: Pattern[Any] = SomePattern()
NOTHING: Pattern[Any] = NothingPattern()

__all__ = [
    "ERR",
    "NOTHING",
    "OK",
    "SOME",
    "ErrPattern",
    "NothingPattern",
    "OkPattern",
    "SomePattern",
]
