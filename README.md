# python-crimes

[![PyPI](https://img.shields.io/pypi/v/python-crimes?cacheSeconds=300)](https://pypi.org/project/python-crimes/)
[![CI](https://github.com/0xveya/python-crimes/actions/workflows/ci.yml/badge.svg)](https://github.com/0xveya/python-crimes/actions/workflows/ci.yml)

**[View python-crimes on PyPI](https://pypi.org/project/python-crimes/)**

Small, typed-enough Python syntax crimes that form one deliberately coherent
ecosystem with [typed-errs](https://github.com/0xveya/typed-errs): pipe values,
defer cleanup, and match rich values without falling back to nullable match
results.

```bash
uv add python-crimes
```

## Examples

Runnable examples live in [examples](examples/README.md): pipes, deferred
cleanup, structural matching and `typed-errs` variants, plus reusable dispatch.

```text
python_crimes/
├── pipe.py       @pipe and value @ function
├── defer.py      DeferStack, with defer(), @deferred, terminate()
├── fuzzy.py      Levenshtein distance and closest-string selection
├── patterns.py   reusable and composable patterns, including fuzzy strings
├── match.py      bound matching and reusable Dispatch
└── typed.py      Result and Option patterns backed by typed-errs
```

## Pipes

`@pipe` preserves normal calls while allowing the left-to-right form.

```python
from python_crimes import pipe


@pipe
def parse(raw: str) -> dict[str, object]: ...


@pipe
def validate(config: dict[str, object]) -> Config: ...


config = raw @ parse @ validate
```

For a function with configuration after its piped first argument, use the
explicit partial form: `score @ clamp.with_(lo=0, hi=100)`.

## Deferred cleanup

`DeferStack` is the boring LIFO implementation. `defer` and `@deferred` are
just convenient frontends over it.

```python
from python_crimes import deferred, terminate
from typed_errs import Result, catch_bubble


@catch_bubble
@deferred
def write_report(d, path) -> Result[None, WriteError]:
    writer = write_text(path).q
    d << terminate(writer)
    writer("started\\n")
    return Ok(None)
```

The cleanup still runs when `.q` bubbles an `Err`, because normal Python stack
unwinding reaches the deferred scope first.

## Matching

Patterns return `typed_errs.Option[Match]`: successful matching is
`Some(Match(...))`, and failure is `Nothing()`. The matcher itself therefore
does not use `Match | None` as an internal failure protocol.

```python
from python_crimes import capture, ge, gt, match_, type_

with match_(data) as m:
    m.case(200, 201, 204) << "success"
    m.case(type_(int)).when(gt(0)) << (lambda number: number * 2)
    m.regex(r"(\d+)x(\d+)") << (lambda width, height: (int(width), int(height)))
    m.case(
        {
            "type": "user",
            "payload": {"name": capture(str), "age": capture(int)},
        }
    ) << (lambda name, age: (name, age))
    m.default << "unknown"

result = m.value
```

### Fluent matching

The context manager is convenient for a visually large decision tree. For a
small match inside an expression or function return, use the exact same engine
without `with`:

```python
level = (
    match_(raw_level)
    .case(type_(int))
    .when(gt(0))
    .then(lambda value: value * 2)
    .regex(r"level:(\d+)")
    .then(int)
    .default.then(0)
    .value
)
```

`<<` and `.then(...)` are equivalent. A callable result is a handler; use
`const(callable_value)` when a callable itself is the wanted result.

Patterns compose with `&`, `|`, and `~`; helpers include `eq`, `type_`, `when`,
`gt`/`ge`/`lt`/`le`, `in_`, `contains`, `is_`, `regex`, `attr`, `length`, `ANY`,
`fuzzy`, and `REST`. A fuzzy arm captures the closest candidate when its edit
distance is within the configured maximum:

```python
with match_("heigth") as m:
    m.fuzzy({"width", "height", "time"}, maximum_distance=2) << (
        lambda candidate: f"did you mean {candidate!r}?"
    )
    m.default << "unknown key"
```

Lists and mappings are structural patterns recursively, and
`capture(...)` passes values to the selected handler in traversal order.

### typed-errs is first class

Result and Option variants have dedicated arms with payload capture:

```python
with match_(read(path)) as m:
    m.ok << process
    m.err << report

with match_(find_user()) as m:
    m.some << (lambda user: user.name)
    m.nothing << "anonymous"
```

No optional adapter is needed: `python-crimes` depends on `typed-errs` and
ships these patterns as part of its public API.

The special arms deliberately unwrap only when their variant matched:

```text
Ok(value)       -> m.ok       handler(value)
Err(error)      -> m.err      handler(error)
Some(value)     -> m.some     handler(value)
Nothing()       -> m.nothing  constant or handler(subject)
```

For ordinary structural matching, failed patterns are `Nothing()` and
successful patterns are `Some(Match(captures))`; this is the same explicit
absence vocabulary used everywhere else in the ecosystem.

### Reusable dispatch

```python
from python_crimes import ge, matcher, type_

status = (
    matcher()
    .case(200)
    .then("ok")
    .case(404)
    .then("missing")
    .case(type_(int) & ge(500))
    .then("server error")
    .default.then("unknown")
)

message = 503 @ status
```

## Ecosystem

- [typed-errs](https://github.com/0xveya/typed-errs) supplies `Result`,
  `Option`, and `.q` bubbling.
- [typed-file-io](https://github.com/0xveya/typed-file-io) supplies typed file
  callbacks; pair a callback writer with `defer` and `terminate`.
- [sqlite-callback-store](https://github.com/0xveya/sqlite-callback-store)
  supplies short-lived typed SQLite callbacks.


## Dependencies

- `typed-errs`

## Use and contributions

This is a personal library, but it is not private or locked to my projects.
You may use it in general Python work and in 42 projects under the MIT license;
just follow the rules that apply to your campus and assignment.

Contributions are welcome: open an issue or send a pull request. I do not care
whether a contribution is written by hand, AI-assisted, or generated another
way; I care about whether it is correct, tested, understandable, and a good fit.
Because this is opinionated personal infrastructure, pull requests are reviewed
selectively and are likely to be rejected unless they clearly improve the
library without making it harder to maintain.

## Development and release

Run `mise run check`. Every push to `master` publishes a unique `0.0.<CI run>` ZeroVer
version through PyPI Trusted Publishing. `mise run publish` remains available.
