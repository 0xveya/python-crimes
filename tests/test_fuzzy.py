from typed_errs import Nothing, Some

from python_crimes import closest_string, levenshtein_distance


def test_levenshtein_distance() -> None:
    assert levenshtein_distance("levstein", "levenshtein") == 3


def test_closest_string_uses_stable_tie_breaks() -> None:
    result = closest_string("heigth", ["width", "height", "time"])

    assert isinstance(result, Some)
    assert result.value.value == "height"
    assert result.value.distance == 2


def test_closest_string_without_candidates() -> None:
    assert isinstance(closest_string("key", []), Nothing)
