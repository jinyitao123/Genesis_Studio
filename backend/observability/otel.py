from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


_initialized = False


def _init_provider(service_name: str) -> None:
    global _initialized
    if _initialized:
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    enable_exporter = os.getenv("ENABLE_OTEL_EXPORTER", "false").lower() in {"1", "true", "yes", "on"}
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    if enable_exporter:
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True


def instrument_flask_app(app, service_name: str) -> None:
    _init_provider(service_name)
    FlaskInstrumentor().instrument_app(app)


def instrument_fastapi_app(app, service_name: str) -> None:
    _init_provider(service_name)
    FastAPIInstrumentor.instrument_app(app)
