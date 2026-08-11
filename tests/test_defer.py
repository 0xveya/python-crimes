import pytest

from python_crimes import DeferError, DeferStack, defer, deferred, terminate


def test_manual_defer() -> None:
    calls: list[str] = []

    stack = DeferStack()
    stack << (lambda: calls.append("cleanup"))

    assert calls == []

    stack.run()

    assert calls == ["cleanup"]


def test_defer_runs_lifo() -> None:
    calls: list[int] = []

    stack = DeferStack()

    stack << (lambda: calls.append(1))
    stack << (lambda: calls.append(2))
    stack << (lambda: calls.append(3))

    stack.run()

    assert calls == [3, 2, 1]


def test_lshift_returns_stack() -> None:
    stack = DeferStack()

    result = stack << (lambda: None)

    assert result is stack


def test_lshift_can_chain() -> None:
    calls: list[int] = []

    stack = DeferStack()

    stack << (lambda: calls.append(1)) << (lambda: calls.append(2))

    stack.run()

    assert calls == [2, 1]


def test_len() -> None:
    stack = DeferStack()

    assert len(stack) == 0

    stack << (lambda: None)
    assert len(stack) == 1

    stack << (lambda: None)
    assert len(stack) == 2

    stack.run()

    assert len(stack) == 0


def test_run_only_runs_once() -> None:
    calls: list[int] = []

    stack = DeferStack()
    stack << (lambda: calls.append(1))

    stack.run()
    stack.run()
    stack.run()

    assert calls == [1]


def test_run_attempts_all_callbacks_after_a_failure() -> None:
    calls: list[str] = []

    def fail() -> None:
        calls.append("failing cleanup")
        raise ValueError("boom")

    stack = DeferStack()
    stack << (lambda: calls.append("first cleanup"))
    stack << fail
    stack << (lambda: calls.append("last cleanup"))

    with pytest.raises(DeferError, match="1 deferred callback failed") as exc_info:
        stack.run()

    assert calls == ["last cleanup", "failing cleanup", "first cleanup"]
    assert len(stack) == 0
    assert [str(error) for error in exc_info.value.exceptions] == ["boom"]


def test_run_collects_all_cleanup_failures_in_lifo_order() -> None:
    def first() -> None:
        raise ValueError("first")

    def second() -> None:
        raise RuntimeError("second")

    stack = DeferStack()
    stack << first
    stack << second

    with pytest.raises(DeferError, match="2 deferred callbacks failed") as exc_info:
        stack.run()

    assert [str(error) for error in exc_info.value.exceptions] == ["second", "first"]


def test_cannot_add_after_run() -> None:
    stack = DeferStack()

    stack.run()

    with pytest.raises(RuntimeError, match="already run"):
        stack << (lambda: None)


def test_context_manager_runs_on_exit() -> None:
    calls: list[str] = []

    with defer() as stack:
        stack << (lambda: calls.append("cleanup"))

        assert calls == []

    assert calls == ["cleanup"]


def test_context_manager_runs_on_exception() -> None:
    calls: list[str] = []

    with pytest.raises(ValueError, match="boom"):
        with defer() as stack:
            stack << (lambda: calls.append("cleanup"))

            raise ValueError("boom")

    assert calls == ["cleanup"]


def test_context_manager_does_not_swallow_exception() -> None:
    with pytest.raises(ValueError, match="original"):
        with defer():
            raise ValueError("original")


def test_terminate_passes_none() -> None:
    values: list[str | None] = []

    def writer(value: str | None) -> None:
        values.append(value)

    cleanup = terminate(writer)

    cleanup()

    assert values == [None]


def test_terminate_with_defer() -> None:
    values: list[str | None] = []

    def writer(value: str | None) -> None:
        values.append(value)

    with defer() as stack:
        stack << terminate(writer)

        writer("hello")
        writer("world")

    assert values == [
        "hello",
        "world",
        None,
    ]


def test_deferred_injects_stack() -> None:
    calls: list[str] = []

    @deferred
    def operation(stack: DeferStack) -> int:
        stack << (lambda: calls.append("cleanup"))

        calls.append("body")
        return 42

    result = operation()

    assert result == 42
    assert calls == [
        "body",
        "cleanup",
    ]


def test_deferred_preserves_arguments() -> None:
    @deferred
    def add(stack: DeferStack, a: int, b: int) -> int:
        stack << (lambda: None)
        return a + b

    assert add(20, 22) == 42


def test_deferred_preserves_keyword_arguments() -> None:
    @deferred
    def add(
        stack: DeferStack,
        a: int,
        *,
        b: int,
    ) -> int:
        stack << (lambda: None)
        return a + b

    assert add(20, b=22) == 42


def test_deferred_runs_on_exception() -> None:
    calls: list[str] = []

    @deferred
    def explode(stack: DeferStack) -> None:
        stack << (lambda: calls.append("cleanup"))
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        explode()

    assert calls == ["cleanup"]


def test_deferred_runs_lifo() -> None:
    calls: list[int] = []

    @deferred
    def operation(stack: DeferStack) -> None:
        stack << (lambda: calls.append(1))
        stack << (lambda: calls.append(2))
        stack << (lambda: calls.append(3))

    operation()

    assert calls == [3, 2, 1]


def test_deferred_preserves_name() -> None:
    @deferred
    def operation(stack: DeferStack) -> None:
        pass

    assert operation.__name__ == "operation"


def test_deferred_preserves_docstring() -> None:
    @deferred
    def operation(stack: DeferStack) -> None:
        """Do crimes."""

    assert operation.__doc__ == "Do crimes."
