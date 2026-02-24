from __future__ import annotations

import os
import time

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .metrics import record_http_duration


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

    @app.before_request
    def _capture_request_start() -> None:
        from flask import g

        g._genesis_request_start = time.perf_counter()

    @app.after_request
    def _capture_request_duration(response):
        from flask import g

        started = getattr(g, "_genesis_request_start", None)
        if isinstance(started, float):
            record_http_duration(time.perf_counter() - started)
        return response


def instrument_fastapi_app(app, service_name: str) -> None:
    _init_provider(service_name)
    FastAPIInstrumentor.instrument_app(app)

    @app.middleware("http")
    async def _capture_request_duration(request, call_next):
        started = time.perf_counter()
        try:
            response = await call_next(request)
            return response
        finally:
            record_http_duration(time.perf_counter() - started)
