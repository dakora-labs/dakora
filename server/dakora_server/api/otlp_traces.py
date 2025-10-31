"""OTLP trace ingestion endpoint for OpenTelemetry spans."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
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
    request: Request,
    auth_ctx: AuthContext = Depends(get_auth_context),
    engine: Engine = Depends(get_engine),
) -> OTLPTraceResponse:
    """
    Ingest OTLP traces from OpenTelemetry exporters.

    This endpoint accepts both:
    - Standard OTLP protobuf format (Content-Type: application/x-protobuf)
    - Custom JSON format (Content-Type: application/json)

    This endpoint:
    1. Stores raw OTLP spans in otel_spans table
    2. Extracts execution traces using smart strategy:
       - New traces: Extract immediately from batch (fast path)
       - Existing traces: Recompute with full span set (late arrivals)

    Authentication: Requires X-API-Key header with valid project API key.
    """
    # Parse request based on Content-Type
    content_type = request.headers.get("content-type", "").lower()

    try:
        if "application/x-protobuf" in content_type or "application/protobuf" in content_type:
            # Parse OTLP protobuf format
            from dakora_server.core.otlp_parser import parse_otlp_protobuf

            body = await request.body()
            spans = parse_otlp_protobuf(body)
            logger.debug(f"Parsed {len(spans)} span(s) from protobuf")

        elif "application/json" in content_type:
            # Parse custom JSON format
            body_json = await request.json()
            trace_request = OTLPTraceRequest.model_validate(body_json)
            spans = trace_request.spans
            logger.debug(f"Parsed {len(spans)} span(s) from JSON")

        else:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported Content-Type: {content_type}. "
                       f"Expected application/x-protobuf or application/json"
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse request: {e}")

    if not spans:
        raise HTTPException(status_code=400, detail="No spans provided")

    # Validate spans have expected OTLP attributes (warning only, don't block)
    for span in spans:
        attrs = span.attributes or {}
        operation = attrs.get("gen_ai.operation.name")

        # Warn if critical attributes are missing
        if not operation:
            logger.warning(
                f"Span {span.span_id} missing 'gen_ai.operation.name' attribute. "
                f"This may indicate incompatible OTEL exporter or MAF version."
            )

    # API key authentication must provide project_id
    if not auth_ctx.project_id:
        raise HTTPException(
            status_code=401,
            detail="API key required with project scope"
        )

    project_id = UUID(auth_ctx.project_id)
    logger.info(f"Ingesting {len(spans)} span(s) for project {project_id}")

    try:
        # Import here to avoid circular dependency
        from dakora_server.core.otlp_processor import process_trace_batch

        with get_connection(engine) as conn:
            # Process the trace batch with smart extraction strategy
            stats = process_trace_batch(
                spans=spans,
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
