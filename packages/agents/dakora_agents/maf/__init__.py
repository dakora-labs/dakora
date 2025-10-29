"""
Dakora MAF Integration - OpenTelemetry observability for Microsoft Agent Framework

Provides automatic telemetry and observability for MAF agents via OTEL:
- Budget enforcement with caching
- Template linkage with Dakora prompts
- Agent ID, token, and latency tracking (via OTEL)
- Export to Dakora API and other OTEL backends

Quick Start:
    >>> from dakora_client import Dakora
    >>> from dakora_agents.maf import DakoraIntegration
    >>> from agent_framework.azure import AzureOpenAIChatClient
    >>>
    >>> dakora = Dakora(api_key="dk_proj_...")
    >>> middleware = DakoraIntegration.setup(dakora)
    >>>
    >>> azure_client = AzureOpenAIChatClient(..., middleware=[middleware])
    >>> agent = azure_client.create_agent(id="chat-v1", ...)
    >>> response = await agent.run("Hello!")
"""

from .exporter import DakoraSpanExporter
from .helpers import to_instruction_template, to_message
from .integration import DakoraIntegration
from .middleware import DakoraTraceMiddleware

__all__ = [
    # Main integration (recommended)
    "DakoraIntegration",
    # Components (for advanced usage)
    "DakoraTraceMiddleware",
    "DakoraSpanExporter",
    # Helpers
    "to_message",
    "to_instruction_template",
]
