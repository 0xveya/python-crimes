"""Composable runtime patterns used by :mod:`python_crimes.match`."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from typed_errs import Nothing, Option, Some

T = TypeVar("T")


@dataclass(frozen=True)
class Match:
    """A successful match and its positional captures."""

    captures: tuple[object, ...] = ()


class Pattern(ABC, Generic[T]):
    """A reusable test which returns ``Some(Match)`` on success."""

    @abstractmethod
    def match(self, value: object) -> Option[Match]: ...

    def __and__(self, other: object) -> Pattern[object]:
        return AndPattern(self, pattern(other))

    def __or__(self, other: object) -> Pattern[object]:
        return OrPattern(self, pattern(other))

    def __invert__(self) -> Pattern[object]:
        return NotPattern(self)


class EqPattern(Pattern[object]):
    def __init__(self, expected: object) -> None:
        self.expected = expected

    def match(self, value: object) -> Option[Match]:
        return Some(Match()) if value == self.expected else Nothing()


class TypePattern(Pattern[T]):
    def __init__(self, expected: type[T]) -> None:
        self.expected = expected

    def match(self, value: object) -> Option[Match]:
        return Some(Match()) if isinstance(value, self.expected) else Nothing()


class PredicatePattern(Pattern[T]):
    def __init__(self, predicate: Callable[[T], bool]) -> None:
        self.predicate = predicate

    def match(self, value: object) -> Option[Match]:
        return Some(Match()) if self.predicate(value) else Nothing()  # type: ignore[arg-type]


class ComparisonPattern(Pattern[object]):
    def __init__(self, expected: object, compare: Callable[[Any, Any], bool]) -> None:
        self.expected = expected
        self.compare = compare

    def match(self, value: object) -> Option[Match]:
        try:
            return Some(Match()) if self.compare(value, self.expected) else Nothing()
        except (TypeError, ValueError):
            return Nothing()


class InPattern(Pattern[object]):
    def __init__(self, container: Container[object]) -> None:
        self.container = container

    def match(self, value: object) -> Option[Match]:
        return Some(Match()) if value in self.container else Nothing()


class ContainsPattern(Pattern[object]):
    def __init__(self, expected: object) -> None:
        self.expected = expected

    def match(self, value: object) -> Option[Match]:
        try:
            return Some(Match()) if self.expected in value else Nothing()  # type: ignore[operator]
        except TypeError:
            return Nothing()


class IdentityPattern(Pattern[object]):
    def __init__(self, expected: object) -> None:
        self.expected = expected

    def match(self, value: object) -> Option[Match]:
        return Some(Match()) if value is self.expected else Nothing()


class RegexPattern(Pattern[str]):
    def __init__(self, expression: str | re.Pattern[str]) -> None:
        self.expression = re.compile(expression)

    def match(self, value: object) -> Option[Match]:
        if not isinstance(value, str):
            return Nothing()
        result = self.expression.fullmatch(value)
        return Nothing() if result is None else Some(Match(tuple(result.groups())))


class CapturePattern(Pattern[T]):
    def __init__(self, inner: Pattern[T]) -> None:
        self.inner = inner

    def match(self, value: object) -> Option[Match]:
        result = self.inner.match(value)
        if isinstance(result, Nothing):
            return result
        return Some(Match((value, *result.value.captures)))


class AndPattern(Pattern[object]):
    def __init__(self, left: Pattern[Any], right: Pattern[Any]) -> None:
        self.left, self.right = left, right

    def match(self, value: object) -> Option[Match]:
        left = self.left.match(value)
        if isinstance(left, Nothing):
            return left
        right = self.right.match(value)
        if isinstance(right, Nothing):
            return right
        return Some(Match(left.value.captures + right.value.captures))


class OrPattern(Pattern[object]):
    def __init__(self, left: Pattern[Any], right: Pattern[Any]) -> None:
        self.left, self.right = left, right

    def match(self, value: object) -> Option[Match]:
        left = self.left.match(value)
        return self.right.match(value) if isinstance(left, Nothing) else left


class NotPattern(Pattern[object]):
    def __init__(self, inner: Pattern[Any]) -> None:
        self.inner = inner

    def match(self, value: object) -> Option[Match]:
        return Some(Match()) if isinstance(self.inner.match(value), Nothing) else Nothing()


class MappingPattern(Pattern[Mapping[object, object]]):
    def __init__(self, fields: Mapping[object, Pattern[Any]]) -> None:
        self.fields = fields

    def match(self, value: object) -> Option[Match]:
        if not isinstance(value, Mapping):
            return Nothing()
        captures: list[object] = []
        for key, expected in self.fields.items():
            if key not in value:
                return Nothing()
            result = expected.match(value[key])
            if isinstance(result, Nothing):
                return result
            captures.extend(result.value.captures)
        return Some(Match(tuple(captures)))


class AttrPattern(Pattern[object]):
    def __init__(self, name: str, expected: Pattern[Any]) -> None:
        self.name, self.expected = name, expected

    def match(self, value: object) -> Option[Match]:
        try:
            actual = getattr(value, self.name)
        except AttributeError:
            return Nothing()
        return self.expected.match(actual)


class LengthPattern(Pattern[object]):
    def __init__(self, expected: Pattern[Any]) -> None:
        self.expected = expected

    def match(self, value: object) -> Option[Match]:
        try:
            size = len(value)  # type: ignore[arg-type]
        except TypeError:
            return Nothing()
        return self.expected.match(size)


class _AnyPattern(Pattern[object]):
    def match(self, value: object) -> Option[Match]:
        return Some(Match())


class _Rest:
    """Sentinel allowing a sequence pattern to accept trailing items."""


ANY = _AnyPattern()
REST = _Rest()


class SequencePattern(Pattern[Sequence[object]]):
    def __init__(self, items: list[object]) -> None:
        self.items = items

    def match(self, value: object) -> Option[Match]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            return Nothing()
        has_rest = bool(self.items) and self.items[-1] is REST
        expected = self.items[:-1] if has_rest else self.items
        if (has_rest and len(value) < len(expected)) or (
            not has_rest and len(value) != len(expected)
        ):
            return Nothing()
        captures: list[object] = []
        for expected_item, actual in zip(expected, value, strict=False):
            result = pattern(expected_item).match(actual)
            if isinstance(result, Nothing):
                return result
            captures.extend(result.value.captures)
        return Some(Match(tuple(captures)))


def pattern(value: object) -> Pattern[Any]:
    if isinstance(value, Pattern):
        return value
    if isinstance(value, type):
        return TypePattern(value)
    if isinstance(value, Mapping):
        return MappingPattern({key: pattern(item) for key, item in value.items()})
    if isinstance(value, list):
        return SequencePattern(value)
    return EqPattern(value)


def eq(value: object) -> Pattern[object]:
    return EqPattern(value)


def type_(value: type[T]) -> Pattern[T]:
    return TypePattern(value)


def when(predicate: Callable[[T], bool]) -> Pattern[T]:
    return PredicatePattern(predicate)


def capture(value: object = ANY) -> Pattern[Any]:
    return CapturePattern(pattern(value))


def gt(value: object) -> Pattern[object]:
    return ComparisonPattern(value, lambda a, b: a > b)


def ge(value: object) -> Pattern[object]:
    return ComparisonPattern(value, lambda a, b: a >= b)


def lt(value: object) -> Pattern[object]:
    return ComparisonPattern(value, lambda a, b: a < b)


def le(value: object) -> Pattern[object]:
    return ComparisonPattern(value, lambda a, b: a <= b)


def in_(container: Container[object]) -> Pattern[object]:
    return InPattern(container)


def contains(value: object) -> Pattern[object]:
    return ContainsPattern(value)


def is_(value: object) -> Pattern[object]:
    return IdentityPattern(value)


def regex(expression: str | re.Pattern[str]) -> Pattern[str]:
    return RegexPattern(expression)


def attr(name: str, expected: object = ANY) -> Pattern[object]:
    return AttrPattern(name, pattern(expected))


def length(expected: object) -> Pattern[object]:
    return LengthPattern(pattern(expected))


__all__ = [
    "ANY",
    "REST",
    "Match",
    "Pattern",
    "attr",
    "capture",
    "contains",
    "eq",
    "ge",
    "gt",
    "in_",
    "is_",
    "le",
    "length",
    "lt",
    "pattern",
    "regex",
    "type_",
    "when",
]
