from collections.abc import Callable
from functools import partial
from typing import Any, Generic, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class Pipe(Generic[P, R]):
    """A callable that can receive its argument through the @ operator."""

    def __init__(self, fn: Callable[P, R]) -> None:
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
    def __wrapped__(self) -> Callable[P, R]:
        return self._fn

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return self._fn(*args, **kwargs)

    def __rmatmul__(self, value: object) -> R:
        return self._fn(value)  # type: ignore[arg-type, call-arg]

    def with_(self, /, *args: object, **kwargs: object) -> "Pipe[Any, R]":
        """Bind later arguments while leaving the piped value as argument one.

        This is deliberately explicit: ``value @ clamp.with_(lo=0, hi=100)``
        remains readable without introducing placeholder syntax.
        """
        return Pipe(partial(self._fn, *args, **kwargs))  # type: ignore[arg-type, return-value]


def pipe(fn: Callable[P, R]) -> Pipe[P, R]:
    """Make a function usable as a pipeline stage through its first argument."""
    return Pipe(fn)


__all__ = ["Pipe", "pipe"]
