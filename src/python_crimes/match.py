"""A deliberately expressive, first-match-wins pattern matcher."""

from __future__ import annotations

from collections.abc import Callable, Container
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from typed_errs import Nothing

from .patterns import ANY, Match, Pattern, in_, pattern, regex

T = TypeVar("T")
R = TypeVar("R")
_MISSING = object()


class NonExhaustiveMatch(Exception):
    """Raised when no registered arm accepts a subject."""

    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"no pattern matched {value!r}")


@dataclass(frozen=True)
class Constant(Generic[R]):
    value: R


def const(value: R) -> Constant[R]:
    """Mark a callable (or any value) as a literal match result."""
    return Constant(value)


@dataclass
class _RegisteredArm:
    pattern: Pattern[Any]
    result: object


class _ArmOwner:
    def _register(self, arm_pattern: Pattern[Any], result: object) -> None: ...

    def case(self, *values: object) -> Arm[Any]:
        raise NotImplementedError

    @property
    def default(self) -> DefaultArm:
        raise NotImplementedError

    def __call__(self, subject: object) -> Any:
        raise NotImplementedError

    def __rmatmul__(self, subject: object) -> Any:
        raise NotImplementedError


class Arm(Generic[T]):
    def __init__(self, owner: _ArmOwner, arm_pattern: Pattern[Any]) -> None:
        self._owner, self._pattern = owner, arm_pattern

    def when(self, condition: Pattern[Any] | Callable[[T], bool]) -> Arm[T]:
        if not isinstance(condition, Pattern):
            from .patterns import when

            condition = when(condition)
        self._pattern = self._pattern & condition
        return self

    def __lshift__(self, result: object) -> _ArmOwner:
        self._owner._register(self._pattern, result)
        return self._owner

    def then(self, result: object) -> _ArmOwner:
        return self << result


class DefaultArm:
    def __init__(self, owner: _ArmOwner) -> None:
        self._owner = owner

    def __lshift__(self, result: object) -> _ArmOwner:
        self._owner._register(ANY, result)
        return self._owner

    def then(self, result: object) -> _ArmOwner:
        return self << result


def _evaluate(subject: object, result: object, matched: Match) -> object:
    if isinstance(result, Constant):
        return result.value
    if callable(result):
        return result(*matched.captures) if matched.captures else result(subject)
    return result


def _resolve(subject: object, arms: list[_RegisteredArm]) -> object:
    for arm in arms:
        matched = arm.pattern.match(subject)
        if isinstance(matched, Nothing):
            continue
        return _evaluate(subject, arm.result, matched.value)
    raise NonExhaustiveMatch(subject)


class Matcher(Generic[T], _ArmOwner):
    """A subject-bound matcher, useful with ``with match_(value) as m``."""

    def __init__(self, value: T) -> None:
        self._subject = value
        self._arms: list[_RegisteredArm] = []
        self._value: object = _MISSING

    def __enter__(self) -> Matcher[T]:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            self.resolve()

    def _register(self, arm_pattern: Pattern[Any], result: object) -> None:
        self._arms.append(_RegisteredArm(arm_pattern, result))

    def case(self, *values: object) -> Arm[Any]:
        if not values:
            raise TypeError("case requires at least one pattern")
        combined = pattern(values[0])
        for value in values[1:]:
            combined = combined | pattern(value)
        return Arm(self, combined)

    def when(self, condition: Callable[[T], bool]) -> Arm[T]:
        from .patterns import when

        return Arm(self, when(condition))

    def regex(self, expression: str) -> Arm[str]:
        return Arm(self, regex(expression))

    def in_(self, values: Container[object]) -> Arm[Any]:
        return Arm(self, in_(values))

    @property
    def default(self) -> DefaultArm:
        return DefaultArm(self)

    @property
    def ok(self) -> Arm[Any]:
        from .typed import OK

        return Arm(self, OK)

    @property
    def err(self) -> Arm[Any]:
        from .typed import ERR

        return Arm(self, ERR)

    @property
    def some(self) -> Arm[Any]:
        from .typed import SOME

        return Arm(self, SOME)

    @property
    def nothing(self) -> Arm[Any]:
        from .typed import NOTHING

        return Arm(self, NOTHING)

    def resolve(self) -> object:
        if self._value is _MISSING:
            self._value = _resolve(self._subject, self._arms)
        return self._value

    @property
    def value(self) -> Any:
        return self.resolve()


class Dispatch(_ArmOwner):
    """A reusable matcher callable as ``dispatch(subject)`` or ``subject @ dispatch``."""

    def __init__(self) -> None:
        self._arms: list[_RegisteredArm] = []

    def _register(self, arm_pattern: Pattern[Any], result: object) -> None:
        self._arms.append(_RegisteredArm(arm_pattern, result))

    def case(self, *values: object) -> Arm[Any]:
        if not values:
            raise TypeError("case requires at least one pattern")
        combined = pattern(values[0])
        for value in values[1:]:
            combined = combined | pattern(value)
        return Arm(self, combined)

    def when(self, condition: Callable[[Any], bool]) -> Arm[Any]:
        from .patterns import when

        return Arm(self, when(condition))

    def __call__(self, subject: object) -> Any:
        return _resolve(subject, self._arms)

    def __rmatmul__(self, subject: object) -> Any:
        return self(subject)

    @property
    def default(self) -> DefaultArm:
        return DefaultArm(self)


def match_(value: T) -> Matcher[T]:
    return Matcher(value)


def matcher() -> Dispatch:
    return Dispatch()


__all__ = [
    "Arm",
    "Constant",
    "Dispatch",
    "Matcher",
    "NonExhaustiveMatch",
    "const",
    "match_",
    "matcher",
]
