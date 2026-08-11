"""Build a reusable matcher that can also participate in @ pipelines."""

from python_crimes import ge, matcher, type_

status = (
    matcher()
    .case(200, 201, 204)
    .then("success")
    .case(404)
    .then("missing")
    .case(type_(int) & ge(500))
    .then("server error")
    .default.then("unknown")
)

for code in (200, 404, 503, "wat"):
    print(code, "->", code @ status)
