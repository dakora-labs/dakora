"""Integration helper for easy Dakora + OTEL setup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dakora_client import Dakora
    from opentelemetry.sdk._logs._internal.export import LogExporter
    from opentelemetry.sdk.metrics.export import MetricExporter
    from opentelemetry.sdk.trace.export import SpanExporter

    from .middleware import DakoraTraceMiddleware

__all__ = ["DakoraIntegration"]

logger = logging.getLogger(__name__)


class DakoraIntegration:
    """
    One-line setup for Dakora OTEL integration with Microsoft Agent Framework.

    Example:
        >>> from dakora_client import Dakora
        >>> from dakora_agents.maf import DakoraIntegration
        >>> from agent_framework.azure import AzureOpenAIChatClient
        >>>
        >>> # 1. Initialize Dakora
        >>> dakora = Dakora(api_key="dk_proj_...")
        >>>
        >>> # 2. One-line OTEL setup
        >>> middleware = DakoraIntegration.setup(dakora)
        >>>
        >>> # 3. Use with any MAF client
        >>> azure_client = AzureOpenAIChatClient(
        ...     endpoint=...,
        ...     deployment_name=...,
        ...     api_key=...,
        ...     middleware=[middleware],
        ... )
        >>>
        >>> # 4. Templates auto-link via to_message()
        >>> greeting = await dakora.prompts.render("greeting", {"name": "Alice"})
        >>> agent = azure_client.create_agent(id="chat-v1", ...)
        >>> response = await agent.run(greeting.to_message())
        >>>
        >>> # Everything is automatically tracked:
        >>> # - Budget enforcement (before execution)
        >>> # - Template linkage (via _dakora_context)
        >>> # - Agent ID, tokens, latency (via OTEL)
        >>> # - Exported to Dakora API
    """

    @staticmethod
    def setup(
        dakora_client: Dakora,
        enable_sensitive_data: bool = True,
        budget_check_cache_ttl: int = 30,
        additional_exporters: list[LogExporter | SpanExporter | MetricExporter] | None = None,
        **observability_kwargs: Any,
    ) -> DakoraTraceMiddleware:
        """
        Setup OTEL with Dakora integration in one line.

        This method:
        1. Creates standard OTLP exporter pointing to Dakora API
        2. Configures MAF's OTEL infrastructure via setup_observability()
        3. Returns DakoraTraceMiddleware for budget enforcement

        Args:
            dakora_client: Dakora client instance with API key configured
            enable_sensitive_data: Capture messages and prompts in OTEL (default: True)
            budget_check_cache_ttl: Budget check cache TTL in seconds (default: 30)
            additional_exporters: Optional OTEL exporters (Jaeger, Azure Monitor, etc.)
            **observability_kwargs: Additional args passed to setup_observability()

        Returns:
            DakoraTraceMiddleware instance to add to chat client

        Example:
            >>> # Basic setup
            >>> middleware = DakoraIntegration.setup(dakora)
            >>>
            >>> # With additional OTEL exporters
            >>> from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            >>>
            >>> middleware = DakoraIntegration.setup(
            ...     dakora,
            ...     additional_exporters=[
            ...         OTLPSpanExporter(endpoint="http://localhost:4317")
            ...     ]
            ... )
            >>>
            >>> # Now your traces go to both Dakora AND Jaeger/Grafana!
        """
        try:
            from agent_framework.observability import setup_observability
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            from .middleware import DakoraTraceMiddleware

        except ImportError as e:
            raise ImportError(
                f"Failed to import dependencies: {e}\n"
                "Install with: pip install agent-framework opentelemetry-exporter-otlp-proto-http"
            ) from e

        # Create standard OTLP exporter pointing to Dakora API
        # Use the standard OTLP HTTP exporter for maximum compatibility
        headers = {}
        if hasattr(dakora_client, "_Dakora__api_key"):
            api_key = getattr(dakora_client, "_Dakora__api_key")
            if api_key:
                headers["X-API-Key"] = api_key

        dakora_exporter = OTLPSpanExporter(
            endpoint=f"{dakora_client.base_url}/api/v1/traces",
            headers=headers,
            timeout=30,
        )

        # Combine with any additional exporters
        exporters: list[Any] = [dakora_exporter]
        if additional_exporters:
            exporters.extend(additional_exporters)

        # Suppress verbose OTEL logging
        import os
        os.environ.setdefault("OTEL_LOG_LEVEL", "ERROR")

        # Suppress console metrics output
        otel_logger = logging.getLogger("opentelemetry")
        otel_logger.setLevel(logging.ERROR)

        # Setup OTEL with all exporters
        logger.info(
            f"Setting up OTEL with {len(exporters)} exporter(s): "
            f"Dakora OTLP exporter + {len(additional_exporters or [])} additional"
        )

        setup_observability(
            enable_sensitive_data=enable_sensitive_data,
            exporters=exporters,
            **observability_kwargs,
        )

        logger.info("OTEL configured with Dakora integration")

        # Create and return middleware
        middleware = DakoraTraceMiddleware(
            dakora_client=dakora_client,
            budget_check_cache_ttl=budget_check_cache_ttl,
        )

        logger.info(
            f"Dakora middleware configured (budget cache TTL: {budget_check_cache_ttl}s)"
        )

        return middleware

    @staticmethod
    def force_flush(timeout_seconds: int = 5) -> bool:
        """
        Force flush all pending OTEL spans to exporters.

        Call this before your application exits to ensure all traces are exported.
        OTEL uses BatchSpanProcessor which batches spans asynchronously, so without
        this, spans may not be exported if your script exits quickly.

        Args:
            timeout_seconds: Maximum time to wait for flush (default: 5)

        Returns:
            True if flush succeeded within timeout

        Example:
            >>> # Run your agent
            >>> response = await agent.run("Hello!")
            >>>
            >>> # Force export all pending traces before exit
            >>> DakoraIntegration.force_flush()
            >>> await dakora.close()
        """
        try:
            from opentelemetry import trace

            tracer_provider = trace.get_tracer_provider()
            if hasattr(tracer_provider, "force_flush"):
                result = tracer_provider.force_flush(timeout_seconds * 1000)  # type: ignore
                logger.info(f"OTEL force_flush completed: {result}")
                return result
            else:
                logger.warning("TracerProvider does not support force_flush")
                return False
        except Exception as e:
            logger.error(f"Failed to force flush OTEL spans: {e}")
            return False

    @staticmethod
    def setup_with_jaeger(
        dakora_client: Dakora,
        jaeger_endpoint: str = "http://localhost:4317",
        **kwargs: Any,
    ) -> DakoraTraceMiddleware:
        """
        Setup Dakora + Jaeger for local development/debugging.

        Sends traces to both Dakora and Jaeger (for visualization).

        Args:
            dakora_client: Dakora client instance
            jaeger_endpoint: Jaeger OTLP endpoint (default: http://localhost:4317)
            **kwargs: Additional args passed to setup()

        Returns:
            DakoraTraceMiddleware instance

        Example:
            >>> # Start Jaeger locally:
            >>> # docker run -d --name jaeger \\
            >>> #   -p 16686:16686 -p 4317:4317 \\
            >>> #   jaegertracing/all-in-one:latest
            >>>
            >>> middleware = DakoraIntegration.setup_with_jaeger(dakora)
            >>>
            >>> # View traces at http://localhost:16686
        """
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        jaeger_exporter = OTLPSpanExporter(endpoint=jaeger_endpoint)

        logger.info(f"Adding Jaeger exporter: {jaeger_endpoint}")

        return DakoraIntegration.setup(
            dakora_client=dakora_client,
            additional_exporters=[jaeger_exporter],
            **kwargs,
        )

    @staticmethod
    def setup_with_azure_monitor(
        dakora_client: Dakora,
        connection_string: str,
        **kwargs: Any,
    ) -> DakoraTraceMiddleware:
        """
        Setup Dakora + Azure Monitor (Application Insights).

        Sends traces to both Dakora and Azure Monitor.

        Args:
            dakora_client: Dakora client instance
            connection_string: Azure Monitor connection string
            **kwargs: Additional args passed to setup()

        Returns:
            DakoraTraceMiddleware instance

        Example:
            >>> connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
            >>> middleware = DakoraIntegration.setup_with_azure_monitor(
            ...     dakora,
            ...     connection_string=connection_string
            ... )
        """
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

        azure_exporter = AzureMonitorTraceExporter(connection_string=connection_string)

        logger.info("Adding Azure Monitor exporter")

        return DakoraIntegration.setup(
            dakora_client=dakora_client,
            additional_exporters=[azure_exporter],
            **kwargs,
        )