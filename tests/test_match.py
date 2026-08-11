from dataclasses import dataclass
from enum import Enum, auto

import pytest
from typed_errs import Err, Nothing, Ok, Some

from python_crimes import (
    ANY,
    REST,
    NonExhaustiveMatch,
    attr,
    capture,
    const,
    contains,
    eq,
    ge,
    gt,
    is_,
    length,
    match_,
    matcher,
    type_,
)


def resolve(value: object, register: object) -> object:
    with match_(value) as m:
        register(m)  # type: ignore[operator]
    return m.value


def test_literal_type_first_match_and_default() -> None:
    assert resolve(200, lambda m: m.case(200) << "ok") == "ok"
    assert resolve("x", lambda m: m.case(str) << "string") == "string"
    assert resolve(1, lambda m: (m.case(int) << "first").default << "last") == "first"
    assert resolve("x", lambda m: m.default << "fallback") == "fallback"


def test_non_exhaustive_and_constants() -> None:
    with pytest.raises(NonExhaustiveMatch):
        match_("missing").resolve()

    def callback() -> int:
        return 42

    assert resolve("x", lambda m: m.default << const(callback)) is callback


def test_handlers_and_multiple_cases() -> None:
    assert resolve(21, lambda m: m.case(int) << (lambda n: n * 2)) == 42
    assert resolve("b", lambda m: m.case("a", "b") << "yes") == "yes"


def test_predicates_guards_and_operators() -> None:
    positive = type_(int) & gt(0)
    assert resolve(2, lambda m: m.case(positive) << "yes") == "yes"
    assert resolve("y", lambda m: m.case(eq("yes") | eq("y")) << True) is True
    assert resolve("value", lambda m: m.case(~eq("no")) << "yes") == "yes"
    assert resolve(3, lambda m: m.case(int).when(gt(2)) << "yes") == "yes"


def test_comparison_and_container_patterns() -> None:
    assert resolve(3, lambda m: m.case(ge(3)) << "yes") == "yes"
    assert resolve("y", lambda m: m.in_({"y"}) << "yes") == "yes"
    assert resolve([1, 2], lambda m: m.case(contains(2)) << "yes") == "yes"
    marker = object()
    assert resolve(marker, lambda m: m.case(is_(marker)) << "yes") == "yes"
    assert resolve(object(), lambda m: m.case(ANY) << "yes") == "yes"


def test_structural_and_captures() -> None:
    value = {"user": {"name": "veya", "age": 21}}
    assert resolve(
        value,
        lambda m: (
            m.case({"user": {"name": capture(str), "age": capture(int)}})
            << (lambda name, age: (name, age))
        ),
    ) == ("veya", 21)
    assert resolve([1, "x"], lambda m: m.case([int, str]) << "yes") == "yes"
    assert resolve([1, "x", None], lambda m: m.case([int, str, REST]) << "yes") == "yes"


def test_regex_attribute_and_length() -> None:
    assert resolve(
        "12x34", lambda m: m.regex(r"(\d+)x(\d+)") << (lambda x, y: (int(x), int(y)))
    ) == (12, 34)

    @dataclass
    class User:
        name: str
        age: int

    assert (
        resolve(
            User("veya", 21),
            lambda m: (
                m.case(attr("name", capture(str)) & attr("age", ge(18))) << (lambda name: name)
            ),
        )
        == "veya"
    )
    assert resolve("x", lambda m: m.case(type_(str) & length(gt(0))) << "yes") == "yes"


def test_handler_and_predicate_exceptions_propagate() -> None:
    with pytest.raises(RuntimeError):
        resolve(1, lambda m: m.case(int) << (lambda _: (_ for _ in ()).throw(RuntimeError())))
    with pytest.raises(RuntimeError):
        resolve(
            1,
            lambda m: m.case(int).when(lambda _: (_ for _ in ()).throw(RuntimeError())) << "never",
        )


def test_context_does_not_mask_body_error_and_value_is_cached() -> None:
    with pytest.raises(ValueError, match="body"):
        with match_("x") as m:
            m.case(int) << "never"
            raise ValueError("body")
    calls: list[int] = []
    with match_(1) as m:
        m.case(int) << (lambda n: calls.append(n) or n)
    assert m.value == m.value == 1
    assert calls == [1]


def test_typed_errs_variants_are_first_class() -> None:
    class ExampleError(Enum):
        PROBLEM = auto()

    assert resolve(Ok("value"), lambda m: m.ok << (lambda value: value.upper())) == "VALUE"
    assert (
        resolve(Err(ExampleError.PROBLEM), lambda m: m.err << (lambda error: f"{error.name}!"))
        == "PROBLEM!"
    )
    assert resolve(Some(4), lambda m: m.some << (lambda value: value * 2)) == 8
    assert resolve(Nothing(), lambda m: m.nothing << "empty") == "empty"


def test_reusable_dispatch_and_pipe_composition() -> None:
    status = (
        matcher()
        .case(200)
        .then("ok")
        .case(type_(int) & ge(500))
        .then("server")
        .default.then("unknown")
    )
    assert status(200) == "ok"
    assert 503 @ status == "server"
