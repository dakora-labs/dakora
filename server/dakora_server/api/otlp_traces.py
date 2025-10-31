"""OTLP trace ingestion endpoint for OpenTelemetry spans."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine

from dakora_server.core.database import get_engine, get_connection
from dakora_server.auth import get_auth_context, AuthContext

router = APIRouter()
logger = logging.getLogger(__name__)


class OTLPSpan(BaseModel):
    """Simplified OTLP span format (from Dakora exporter)."""

    trace_id: str = Field(..., description="Trace ID (hex string, 32 chars)")
    span_id: str = Field(..., description="Span ID (hex string, 16 chars)")
    parent_span_id: str | None = Field(None, description="Parent span ID")
    span_name: str = Field(..., description="Span name")
    span_kind: str | None = Field(None, description="Span kind")
    attributes: dict[str, Any] = Field(default_factory=dict, description="OTLP attributes")
    events: list[dict[str, Any]] = Field(default_factory=list, description="Span events")
    start_time_ns: int = Field(..., description="Start time in nanoseconds")
    end_time_ns: int = Field(..., description="End time in nanoseconds")
    status_code: str | None = Field(None, description="Span status code")
    status_message: str | None = Field(None, description="Span status message")


class OTLPTraceRequest(BaseModel):
    """OTLP trace ingestion request."""

    spans: list[OTLPSpan] = Field(..., description="List of spans to ingest")


class OTLPTraceResponse(BaseModel):
    """OTLP trace ingestion response."""

    success: bool
    spans_ingested: int
    message: str


@router.post("/api/v1/traces")
async def ingest_otlp_traces(
    request: OTLPTraceRequest,
    auth_ctx: AuthContext = Depends(get_auth_context),
    engine: Engine = Depends(get_engine),
) -> OTLPTraceResponse:
    """
    Ingest OTLP traces from OpenTelemetry exporters.

    This endpoint:
    1. Stores raw OTLP spans in otel_spans table
    2. Extracts execution traces using smart strategy:
       - New traces: Extract immediately from batch (fast path)
       - Existing traces: Recompute with full span set (late arrivals)

    Authentication: Requires X-API-Key header with valid project API key.
    """
    if not request.spans:
        raise HTTPException(status_code=400, detail="No spans provided")

    # API key authentication must provide project_id
    if not auth_ctx.project_id:
        raise HTTPException(
            status_code=401,
            detail="API key required with project scope"
        )

    project_id = UUID(auth_ctx.project_id)
    logger.info(f"Ingesting {len(request.spans)} span(s) for project {project_id}")

    try:
        # Import here to avoid circular dependency
        from dakora_server.core.otlp_processor import process_trace_batch

        with get_connection(engine) as conn:
            # Process the trace batch with smart extraction strategy
            stats = process_trace_batch(
                spans=request.spans,
                project_id=project_id,
                conn=conn,
            )

        logger.info(
            f"Successfully processed: {stats['spans_stored']} spans stored, "
            f"{stats['executions_created']} executions created, "
            f"{stats['recomputes']} recomputes triggered"
        )

        return OTLPTraceResponse(
            success=True,
            spans_ingested=stats["spans_stored"],
            message=f"Ingested {stats['spans_stored']} span(s), "
                    f"created {stats['executions_created']} execution(s), "
                    f"{stats['recomputes']} recompute(s)",
        )

    except Exception as e:
        logger.error(f"Failed to process trace batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process traces: {str(e)}"
        )
