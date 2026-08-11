from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from types import TracebackType
from typing import Concatenate, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


Cleanup = Callable[[], object]


class DeferError(Exception):
    """Raised after one or more deferred callbacks fail."""

    def __init__(self, exceptions: list[BaseException]) -> None:
        self.exceptions = exceptions
        count = len(exceptions)
        noun = "callback" if count == 1 else "callbacks"
        super().__init__(f"{count} deferred {noun} failed")


class DeferStack:
    """A LIFO stack of deferred cleanup callbacks."""

    def __init__(self) -> None:
        self._callbacks: list[Cleanup] = []
        self._closed = False

    def add(self, callback: Cleanup) -> None:
        """Register a callback to run later."""
        if self._closed:
            raise RuntimeError("defer stack has already run")

        self._callbacks.append(callback)

    def __lshift__(self, callback: Cleanup) -> DeferStack:
        """Register a callback using `stack << callback`."""
        self.add(callback)
        return self

    def run(self) -> None:
        """Run all callbacks in reverse registration order.

        Every registered callback is attempted.  Failures are collected and
        raised together as :class:`DeferError` after the stack has drained.
        """
        if self._closed:
            return

        self._closed = True
        exceptions: list[BaseException] = []

        while self._callbacks:
            callback = self._callbacks.pop()
            try:
                callback()
            except BaseException as error:
                exceptions.append(error)

        if exceptions:
            raise DeferError(exceptions)

    def __len__(self) -> int:
        return len(self._callbacks)


class defer(DeferStack):
    """A DeferStack usable as a context manager."""

    def __enter__(self) -> defer:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.run()


def terminate(callback: Callable[[None], object]) -> Cleanup:
    """Turn a callback accepting None into a deferred cleanup callback."""

    def cleanup() -> object:
        return callback(None)

    return cleanup


def deferred(
    fn: Callable[Concatenate[DeferStack, P], R],
) -> Callable[P, R]:
    """Inject a function-scoped DeferStack as the first argument."""

    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with defer() as stack:
            return fn(stack, *args, **kwargs)

    return wrapper


__all__ = [
    "DeferError",
    "DeferStack",
    "defer",
    "deferred",
    "terminate",
]
