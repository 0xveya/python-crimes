"""Compose structural patterns and match typed-errs values directly."""

from enum import Enum, auto

from typed_errs import Err, Ok

from python_crimes import capture, ge, gt, match_, type_

payload = {
    "type": "user",
    "payload": {"name": "veya", "age": 21},
}

with match_(payload) as m:
    m.case(
        {
            "type": "user",
            "payload": {"name": capture(str), "age": capture(int) & ge(18)},
        }
    ) << (lambda name, age: f"adult user {name} ({age})")
    m.default << "not an adult user"

print(m.value)

with match_("1920x1080") as m:
    m.case(type_(int)).when(gt(0)) << (lambda number: number * 2)
    m.regex(r"(\d+)x(\d+)") << (lambda width, height: (int(width), int(height)))
    m.default << "not a size"

print(m.value)


class LoginError(Enum):
    DENIED = auto()


with match_(Ok("veya")) as m:
    m.ok << (lambda name: f"welcome {name}")
    m.err << (lambda error: f"login failed: {error.name}")

print(m.value)

with match_(Err(LoginError.DENIED)) as m:
    m.ok << (lambda name: f"welcome {name}")
    m.err << (lambda error: f"login failed: {error.name}")

print(m.value)
