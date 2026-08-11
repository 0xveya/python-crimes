import inspect
from collections.abc import Callable

import pytest

from python_crimes import Pipe, pipe


def test_pipe_returns_pipe() -> None:
    @pipe
    def double(x: int) -> int:
        return x * 2

    assert isinstance(double, Pipe)


def test_pipe_regular_call() -> None:
    @pipe
    def double(x: int) -> int:
        return x * 2

    assert double(21) == 42


def test_pipe_with_binds_later_arguments() -> None:
    @pipe
    def clamp(value: int, *, low: int, high: int) -> int:
        return max(low, min(value, high))

    assert 120 @ clamp.with_(low=0, high=100) == 100


def test_pipe_operator() -> None:
    @pipe
    def double(x: int) -> int:
        return x * 2

    assert 21 @ double == 42


def test_pipe_chain() -> None:
    @pipe
    def double(x: int) -> int:
        return x * 2

    @pipe
    def stringify(x: int) -> str:
        return str(x)

    assert 21 @ double @ stringify == "42"


def test_long_pipe_chain() -> None:
    @pipe
    def increment(x: int) -> int:
        return x + 1

    @pipe
    def double(x: int) -> int:
        return x * 2

    @pipe
    def stringify(x: int) -> str:
        return str(x)

    @pipe
    def length(x: str) -> int:
        return len(x)

    result = 10 @ increment @ double @ stringify @ length

    assert result == 2


def test_pipeline_runs_left_to_right() -> None:
    calls: list[str] = []

    @pipe
    def first(x: int) -> int:
        calls.append("first")
        return x + 1

    @pipe
    def second(x: int) -> int:
        calls.append("second")
        return x * 2

    @pipe
    def third(x: int) -> int:
        calls.append("third")
        return x - 1

    result = 10 @ first @ second @ third

    assert result == 21
    assert calls == ["first", "second", "third"]


def test_pipeline_can_change_type_multiple_times() -> None:
    @pipe
    def stringify(x: int) -> str:
        return str(x)

    @pipe
    def encode(x: str) -> bytes:
        return x.encode()

    @pipe
    def length(x: bytes) -> int:
        return len(x)

    result = 12345 @ stringify @ encode @ length

    assert result == 5


def test_pipe_preserves_identity_semantics() -> None:
    obj = object()

    @pipe
    def identity(x: object) -> object:
        return x

    assert obj @ identity is obj


def test_pipe_can_return_none() -> None:
    seen: list[int] = []

    @pipe
    def consume(x: int) -> None:
        seen.append(x)

    result = 42 @ consume

    assert result is None
    assert seen == [42]


def test_pipe_can_return_callable() -> None:
    def callback() -> int:
        return 42

    @pipe
    def get_callback(_: int) -> Callable[[], int]:
        return callback

    result = 1 @ get_callback

    assert result is callback
    assert result() == 42


def test_exception_propagates_unchanged() -> None:
    error = ValueError("boom")

    @pipe
    def explode(_: int) -> int:
        raise error

    with pytest.raises(ValueError) as exc:
        42 @ explode

    assert exc.value is error


def test_chain_stops_after_exception() -> None:
    calls: list[str] = []

    @pipe
    def first(x: int) -> int:
        calls.append("first")
        return x

    @pipe
    def explode(_: int) -> int:
        calls.append("explode")
        raise ValueError("boom")

    @pipe
    def never(x: int) -> int:
        calls.append("never")
        return x

    with pytest.raises(ValueError, match="boom"):
        42 @ first @ explode @ never

    assert calls == ["first", "explode"]


def test_name_is_preserved() -> None:
    @pipe
    def double(x: int) -> int:
        return x * 2

    assert double.__name__ == "double"


def test_docstring_is_preserved() -> None:
    @pipe
    def double(x: int) -> int:
        """Double a value."""
        return x * 2

    assert double.__doc__ == "Double a value."


def test_annotations_are_preserved() -> None:
    @pipe
    def double(x: int) -> int:
        return x * 2

    assert double.__annotations__ == {
        "x": int,
        "return": int,
    }


def test_wrapped_function_is_exposed() -> None:
    def original(x: int) -> int:
        return x * 2

    wrapped = pipe(original)

    assert wrapped.__wrapped__ is original
    assert inspect.unwrap(wrapped) is original


def test_signature_is_preserved() -> None:
    def original(x: int) -> int:
        return x * 2

    wrapped = pipe(original)

    assert inspect.signature(wrapped) == inspect.signature(original)


def test_qualname_is_preserved() -> None:
    def original(x: int) -> int:
        return x * 2

    wrapped = pipe(original)

    assert wrapped.__qualname__ == original.__qualname__


def test_module_is_preserved() -> None:
    def original(x: int) -> int:
        return x * 2

    wrapped = pipe(original)

    assert wrapped.__module__ == original.__module__
