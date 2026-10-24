"""Where the server runs, and the two switches that need a positive statement that it is not prod
(S9; docs/OBSERVABILITY.md):

- `PERF_TEST_MODE=1` serves the perf stub (a config whose generator provider is `perf-stub`), and
  the stub is served only with it: two keys that must match, so the mode never runs under a real
  model and the stub never answers outside the mode.
- `RAGLAB_TRACE_CONTENT=1` is the content opt-in (D4: "Opt-in for local debugging only"): the
  question and the answer of an ok answer on raglab's pipeline span.

Each is honoured only where `RAGLAB_ENV` is exactly `ci` or `local`; under `prod`, unset or any
other value the server refuses to start, before the port binds, with one line naming the reason.
That fails closed, as the tenant guard does. A switch set to anything but `1` also refuses. With
neither switch set nothing changes: the container and the API smoke serve as before. `raglab
serve` checks before it builds anything, and `create_app` checks again, so an app built another
way refuses too. From S10 on, the demo controls' exemptions for a load test live under
PERF_TEST_MODE (S10 decides which); this refusal covers them.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from raglab.evals.config import PERF_STUB, ConfigError

ENV = "RAGLAB_ENV"
PERF_MODE = "PERF_TEST_MODE"
TRACE_CONTENT = "RAGLAB_TRACE_CONTENT"
NOT_PROD = ("ci", "local")


class EnvironmentRefused(ConfigError):
    """The server may not start in this environment (one line, naming the reason)."""


@dataclass(frozen=True)
class Switches:
    perf_mode: bool
    capture_content: bool


def _switch(environ: Mapping[str, str], name: str) -> bool:
    value = environ.get(name)
    if value is None:
        return False
    if value != "1":
        raise EnvironmentRefused(f"{name}={value!r}: only {name}=1 switches it on; unset it")
    return True


def switches(environ: Mapping[str, str], provider: str) -> Switches:
    """The switches this environment allows for a server of this generator provider, or
    EnvironmentRefused."""
    perf_mode = _switch(environ, PERF_MODE)
    capture_content = _switch(environ, TRACE_CONTENT)
    place = environ.get(ENV)
    for name, on in ((PERF_MODE, perf_mode), (TRACE_CONTENT, capture_content)):
        if on and place not in NOT_PROD:
            raise EnvironmentRefused(
                f"{name}=1 is honoured only where {ENV} is ci or local, not "
                f"{'unset' if place is None else repr(place)}: the server does not start"
            )
    if perf_mode and provider != PERF_STUB:
        raise EnvironmentRefused(
            f"{PERF_MODE}=1 serves only a {PERF_STUB} config (config/perf.toml), not a "
            f"{provider} generator: the mode never runs under a real model"
        )
    if provider == PERF_STUB and not perf_mode:
        raise EnvironmentRefused(
            f"a {PERF_STUB} config is served only with {PERF_MODE}=1 (and {ENV} ci or local)"
        )
    return Switches(perf_mode, capture_content)
