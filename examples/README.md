# python-crimes examples

Run these from the repository root with `uv run python examples/<name>.py`.

```text
examples/
├── pipes.py       @pipe, value @ stage, and .with_()
├── deferred.py    DeferStack, with defer(), @deferred, terminate(), and .q
├── matching.py    with match_(), fluent matching, captures, and typed-errs
└── dispatch.py    reusable matcher composed using @
```

`matching.py` intentionally shows both matcher entry points:

```python
# Register arms in a scoped block; it resolves on successful scope exit.
with match_(subject) as m:
    m.case(int).when(gt(0)) << (lambda value: value * 2)
    m.default << 0
result = m.value

# Or keep the entire match as an expression.
result = match_(subject).case(int).when(gt(0)).then(lambda value: value * 2).default.then(0).value
```

`deferred.py` likewise covers both ownership styles:

```python
with defer() as cleanup:
    cleanup << close_resource


@deferred
def operation(cleanup: DeferStack) -> Result[str, Error]:
    cleanup << close_resource
    return Ok("done")
```
