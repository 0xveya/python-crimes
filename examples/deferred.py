"""Run LIFO cleanup on normal returns and typed-errs `.q` bubbling."""

from enum import Enum, auto

from typed_errs import Err, Ok, Result, catch_bubble

from python_crimes import DeferStack, deferred, terminate


class ReadError(Enum):
    MISSING = auto()


def read_name(found: bool) -> Result[str, ReadError]:
    return Ok("veya") if found else Err(ReadError.MISSING)


@catch_bubble
@deferred
def greet(cleanup: DeferStack, found: bool) -> Result[str, ReadError]:
    events: list[str] = []

    def writer(chunk: str | None) -> None:
        if chunk is None:
            events.append("writer closed")
        else:
            events.append(chunk)

    cleanup << terminate(writer)
    cleanup << (lambda: events.append("other cleanup"))
    name = read_name(found).q
    writer(f"hello {name}")
    print(events)
    return Ok(name)


print(greet(True))
print(greet(False))  # both deferred callbacks still ran before this Err returned.
