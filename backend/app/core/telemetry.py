"""OpenTelemetry setup and the manual spans that matter (DEP-032).

Production exports to the console; the collector endpoint is read from
`OTEL_EXPORTER_OTLP_ENDPOINT` and stays unset there. Locally the LGTM stack is
available through `make obs`, which is an optional compose override so it does
not consume memory on every start (DEP-033).

The two manual spans — `simulation.compute` and `document.upload` — are opened
by the services that own them, using `span()` below. A third,
`document.classify`, appears when the optional classifier is enabled (AI-030).

**Span attributes obey the same privacy rule as the logs** (DEP-035): region,
term, document type, a size *bucket*. Never an amount, never a filename.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter

from app.core.config import get_settings

_SERVICE_NAME = "borrower-portal"

# DEP-032. Size is bucketed rather than exact, because an exact byte count of an
# identity document is a fingerprint of that document.
_SIZE_BUCKETS = ((100_000, "small"), (1_000_000, "medium"))
_LARGEST_BUCKET = "large"


def size_bucket(size_bytes: int) -> str:
    """Bucket an upload size, so no exact size reaches telemetry."""
    for ceiling, name in _SIZE_BUCKETS:
        if size_bytes < ceiling:
            return name
    return _LARGEST_BUCKET


def _exporter() -> SpanExporter | None:
    """Pick the exporter from the environment. Three cases, not two.

    An endpoint is set — locally that means `make obs` — so export to it.
    Otherwise, in production, export to the console: Fly collects stdout, and
    standing up a collector for one machine would be infrastructure for its own
    sake (DEP-033).

    Otherwise **nothing**. In development with no collector, a console exporter
    prints a JSON span for every request into the same terminal the developer is
    reading, and at the end of a test run it writes to a stdout pytest has
    already closed. Spans are still created and the instrumentation is still
    exercised; only the sink is absent.
    """
    settings = get_settings()
    if settings.otel_exporter_otlp_endpoint:
        return OTLPSpanExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces")
    if settings.is_development:
        return None
    return ConsoleSpanExporter()


def configure(app: FastAPI) -> None:
    """Install the tracer provider and instrument the application."""
    provider = TracerProvider(resource=Resource.create({"service.name": _SERVICE_NAME}))
    exporter = _exporter()
    if exporter is not None:
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


@contextmanager
def span(name: str, **attributes: str | int | bool) -> Iterator[None]:
    """Open a manual span around an operation worth measuring.

    Args:
        name: The span name, e.g. `simulation.compute`.
        **attributes: Categories and identifiers only. Passing an amount, an
            email or a filename here breaks DEP-035 as surely as logging it.
    """
    tracer = trace.get_tracer(_SERVICE_NAME)
    with tracer.start_as_current_span(name) as current:
        for key, value in attributes.items():
            current.set_attribute(key, value)
        yield
