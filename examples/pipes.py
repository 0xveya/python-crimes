"""Use ordinary functions as left-to-right pipeline stages."""

from python_crimes import pipe


@pipe
def parse_port(raw: str) -> int:
    return int(raw)


@pipe
def as_address(port: int) -> str:
    return f"http://127.0.0.1:{port}"


@pipe
def clamp(value: int, *, low: int, high: int) -> int:
    return max(low, min(value, high))


print("8080" @ parse_port @ as_address)
print(99999 @ clamp.with_(low=1, high=65535))
