"""Integration tests for DakoraIntegration with standard OTLP"""

import pytest
from unittest.mock import MagicMock, patch

from dakora_agents.maf import DakoraIntegration


class TestDakoraIntegration:
    """Test suite for DakoraIntegration setup

    Note: DakoraIntegration.setup() is primarily glue code that wires together
    standard OTLP exporters with MAF's observability system. We test it manually
    and with end-to-end tests rather than mocking all the dependencies.

    The real business logic is in DakoraTraceMiddleware (see test_middleware.py).
    """

    def test_force_flush_calls_tracer_provider(self):
        """Test force_flush() calls TracerProvider.force_flush()"""
        mock_provider = MagicMock()
        mock_provider.force_flush.return_value = True

        mock_trace = MagicMock()
        mock_trace.get_tracer_provider.return_value = mock_provider

        with patch('opentelemetry.trace', mock_trace):
            result = DakoraIntegration.force_flush(timeout_seconds=10)

        assert result is True
        mock_provider.force_flush.assert_called_once_with(10000)  # milliseconds

    def test_force_flush_handles_no_support(self):
        """Test force_flush() handles providers without force_flush"""
        mock_provider = MagicMock(spec=[])  # No force_flush method

        mock_trace = MagicMock()
        mock_trace.get_tracer_provider.return_value = mock_provider

        with patch('opentelemetry.trace', mock_trace):
            result = DakoraIntegration.force_flush()

        assert result is False

    def test_force_flush_handles_exception(self):
        """Test force_flush() handles exceptions gracefully"""
        mock_provider = MagicMock()
        mock_provider.force_flush.side_effect = Exception("OTEL error")

        mock_trace = MagicMock()
        mock_trace.get_tracer_provider.return_value = mock_provider

        with patch('opentelemetry.trace', mock_trace):
            result = DakoraIntegration.force_flush()

        assert result is False
