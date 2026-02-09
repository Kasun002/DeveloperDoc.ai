"""
OpenTelemetry instrumentation configuration.

This module sets up OpenTelemetry tracing for the AI Agent System,
including FastAPI auto-instrumentation and custom span creation for
agent operations.
"""

from typing import Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)

logger = get_logger(__name__)


def get_span_exporter() -> Optional[SpanExporter]:
    """
    Get the appropriate span exporter based on configuration.
    
    Returns:
        SpanExporter configured based on settings.otel_exporter_type
        - "console": ConsoleSpanExporter for local development
        - "otlp": OTLPSpanExporter for production (requires OTLP endpoint)
        
    Returns None if OpenTelemetry is disabled.
    """
    if not settings.otel_enabled:
        return None
    
    exporter_type = settings.otel_exporter_type.lower()
    
    if exporter_type == "console":
        logger.info(
            "telemetry_exporter_configured",
            exporter_type="console",
            service_name=settings.otel_service_name
        )
        return ConsoleSpanExporter()
    elif exporter_type == "otlp":
        # OTLP exporter requires endpoint configuration and additional package
        # For production, install: pip install opentelemetry-exporter-otlp-proto-grpc
        # and set OTEL_EXPORTER_OTLP_ENDPOINT environment variable
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            logger.info(
                "telemetry_exporter_configured",
                exporter_type="otlp",
                service_name=settings.otel_service_name
            )
            return OTLPSpanExporter()
        except ImportError:
            logger.warning(
                "telemetry_exporter_import_failed",
                exporter_type="otlp",
                fallback="console",
                message="Install opentelemetry-exporter-otlp-proto-grpc for OTLP support"
            )
            return ConsoleSpanExporter()
    else:
        logger.warning(
            "telemetry_exporter_unknown",
            exporter_type=exporter_type,
            fallback="console"
        )
        return ConsoleSpanExporter()


def configure_telemetry() -> Optional[TracerProvider]:
    """
    Configure OpenTelemetry tracing for the application.
    
    Sets up:
    - TracerProvider with service name and resource attributes
    - Span exporter (console, OTLP, etc.)
    - Batch span processor for efficient export
    
    Returns:
        TracerProvider instance if telemetry is enabled, None otherwise
    """
    if not settings.otel_enabled:
        logger.info("telemetry_disabled", reason="otel_enabled=False")
        return None
    
    try:
        # Create resource with service information
        resource = Resource.create({
            "service.name": settings.otel_service_name,
            "service.version": "1.0.0",
            "deployment.environment": settings.app_env,
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Get and configure span exporter
        exporter = get_span_exporter()
        if exporter:
            # Use batch processor for better performance
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
        
        # Set as global tracer provider
        trace.set_tracer_provider(provider)
        
        logger.info(
            "telemetry_configured",
            service_name=settings.otel_service_name,
            exporter_type=settings.otel_exporter_type,
            environment=settings.app_env
        )
        
        return provider
        
    except Exception as e:
        logger.error(
            "telemetry_configuration_failed",
            error=str(e),
            exc_info=True
        )
        return None


def instrument_fastapi(app) -> None:
    """
    Instrument FastAPI application with OpenTelemetry auto-instrumentation.
    
    This adds automatic tracing for all HTTP requests, including:
    - Request/response timing
    - HTTP method, path, status code
    - Exception tracking
    
    Args:
        app: FastAPI application instance
    """
    if not settings.otel_enabled:
        logger.info("fastapi_instrumentation_skipped", reason="otel_enabled=False")
        return
    
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info(
            "fastapi_instrumentation_successful",
            service_name=settings.otel_service_name
        )
    except Exception as e:
        logger.error(
            "fastapi_instrumentation_failed",
            error=str(e),
            exc_info=True
        )


def get_tracer(name: str = __name__):
    """
    Get a tracer instance for creating custom spans.
    
    Args:
        name: Tracer name (typically __name__ of the calling module)
        
    Returns:
        Tracer instance for creating spans
        
    Example:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("agent_operation") as span:
            span.set_attribute("agent_type", "supervisor")
            # ... perform operation
    """
    return trace.get_tracer(name)


def add_span_attributes(span, **attributes):
    """
    Add attributes to the current span.
    
    Helper function to add multiple attributes to a span at once.
    
    Args:
        span: Span instance
        **attributes: Key-value pairs to add as span attributes
        
    Example:
        span = trace.get_current_span()
        add_span_attributes(
            span,
            trace_id="abc-123",
            tokens_used=150,
            agent_type="supervisor"
        )
    """
    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)
