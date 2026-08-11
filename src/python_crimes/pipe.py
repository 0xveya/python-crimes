from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")
R = TypeVar("R")


class Pipe(Generic[T, R]):
    """A callable that can receive its argument through the @ operator."""

    def __init__(self, fn: Callable[[T], R]) -> None:
        self._fn = fn

    def __getattribute__(self, name: str) -> Any:
        """Delegate function metadata without overriding ``object`` dunders.

        ``__qualname__``, ``__module__``, ``__doc__``, and
        ``__annotations__`` are declared on ``object`` with concrete types.
        Defining properties for them makes type checkers reject ``Pipe`` even
        though those properties work at runtime.  Intercepting their instance
        lookup retains live metadata delegation without changing the class
        declarations.
        """
        if name in {"__name__", "__qualname__", "__module__", "__doc__", "__annotations__"}:
            fn = object.__getattribute__(self, "_fn")
            return getattr(fn, name)
        return object.__getattribute__(self, name)

    @property
    def __wrapped__(self) -> Callable[[T], R]:
        return self._fn

    def __call__(self, value: T) -> R:
        return self._fn(value)

    def __rmatmul__(self, value: T) -> R:
        return self._fn(value)


def pipe(fn: Callable[[T], R]) -> Pipe[T, R]:
    """Make a unary function usable as a pipeline stage."""
    return Pipe(fn)


__all__ = ["Pipe", "pipe"]
