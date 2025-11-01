"""OTLP trace processing orchestration.

This module handles the extraction of execution traces from OTLP spans.

Architecture:
- Fast path: When complete traces arrive in one batch, extract immediately
- Recompute path: When late spans arrive, recompute with full context from DB

Future optimization points:
- Make recompute async (background worker)
- Add trace completion detection
- Add extraction result caching
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from dakora_server.core.database import (
    otel_spans_table,
    template_traces_table,
    traces_table,
)
from dakora_server.core.otlp_extractor import (
    build_span_hierarchy,
    extract_execution_trace,
    extract_template_usages,
    is_root_execution_span,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

    from dakora_server.api.otlp_traces import OTLPSpan

logger = logging.getLogger(__name__)


def process_trace_batch(
    spans: list[OTLPSpan],
    project_id: UUID,
    conn: Connection,
) -> dict[str, int]:
    """
    Process a batch of OTLP spans with smart extraction strategy.

    Strategy:
    1. Store all incoming spans in otel_spans table
    2. For each unique trace_id in the batch:
       - If NEW trace: extract immediately with spans from batch
       - If EXISTING trace: trigger recompute with all spans from DB

    This handles:
    - Fast path: Complete traces in one batch (99% case) → instant extraction
    - Late arrivals: Spans arrive after initial trace → eventually consistent

    Args:
        spans: List of OTLP spans to process
        project_id: Project UUID
        conn: Database connection

    Returns:
        Statistics dict with keys:
        - spans_stored: Number of spans stored
        - executions_created: Number of new executions
        - recomputes: Number of trace recomputes triggered
    """
    if not spans:
        return {"spans_stored": 0, "executions_created": 0, "recomputes": 0}

    stats = {"spans_stored": 0, "executions_created": 0, "recomputes": 0}

    # Step 1: Store all incoming spans
    for span in spans:
        _store_span(span, project_id, conn)
        stats["spans_stored"] += 1

    # Step 2: Process each unique trace
    trace_ids = _get_unique_trace_ids(spans)

    for trace_id in trace_ids:
        trace_spans = [s for s in spans if s.trace_id == trace_id]

        if _is_new_trace(trace_id, conn):
            # Fast path: Extract immediately with current batch
            logger.info(f"New trace {trace_id}, extracting from batch")
            created = _extract_executions_from_batch(
                trace_spans, project_id, conn
            )
            stats["executions_created"] += created
        else:
            # Recompute path: Late-arriving spans, recompute with full context
            logger.info(f"Existing trace {trace_id}, triggering recompute")
            _recompute_trace(trace_id, project_id, conn)
            stats["recomputes"] += 1

    return stats


def _store_span(span: OTLPSpan, project_id: UUID, conn: Connection) -> None:
    """
    Store a single OTLP span in the database.

    Uses ON CONFLICT DO NOTHING for idempotency - if exporter retries,
    we don't duplicate spans.
    """
    duration_ns = span.end_time_ns - span.start_time_ns

    stmt = insert(otel_spans_table).values(
        trace_id=span.trace_id,
        span_id=span.span_id,
        parent_span_id=span.parent_span_id,
        project_id=project_id,
        span_name=span.span_name,
        span_kind=span.span_kind,
        attributes=span.attributes,
        events=span.events,
        start_time_ns=span.start_time_ns,
        end_time_ns=span.end_time_ns,
        duration_ns=duration_ns,
        status_code=span.status_code,
        status_message=span.status_message,
    ).on_conflict_do_nothing(
        index_elements=['span_id']
    )

    conn.execute(stmt)


def _get_unique_trace_ids(spans: list[OTLPSpan]) -> list[str]:
    """Extract unique trace IDs from span batch."""
    return list(set(span.trace_id for span in spans))


def _is_new_trace(trace_id: str, conn: Connection) -> bool:
    """
    Check if this is the first time we're seeing this trace.

    We consider a trace "new" if there are no execution traces for it yet.
    Note: otel_spans might have 1 span already (the one we just inserted),
    but if there's no execution trace, we treat it as new.
    """
    result = conn.execute(
        select(traces_table.c.trace_id)
        .where(traces_table.c.trace_id == trace_id)
        .limit(1)
    )
    return result.first() is None


def _extract_executions_from_batch(
    spans: list[OTLPSpan],
    project_id: UUID,
    conn: Connection,
) -> int:
    """
    Extract execution traces from current batch (fast path).

    Builds span hierarchy once for O(1) child lookups.

    Args:
        spans: Spans for a single trace_id
        project_id: Project UUID
        conn: Database connection

    Returns:
        Number of executions created
    """
    executions_created = 0

    # Build span hierarchy once (O(n)) for efficient child lookups (O(1) per lookup)
    span_hierarchy = build_span_hierarchy(spans)

    # Find root execution spans
    for span in spans:
        if not is_root_execution_span(span):
            continue

        # Extract execution trace
        trace_data = extract_execution_trace(
            root_span=span,
            span_hierarchy=span_hierarchy,
            project_id=project_id,
        )

        # Upsert execution trace (handles race conditions on recompute)
        stmt = insert(traces_table).values(**trace_data).on_conflict_do_update(
            index_elements=['trace_id'],
            set_=trace_data
        )
        conn.execute(stmt)

        # Insert template linkages
        template_usages = extract_template_usages(span, span_hierarchy)
        if template_usages:
            for usage in template_usages:
                conn.execute(
                    insert(template_traces_table).values(
                        trace_id=span.trace_id,
                        prompt_id=usage["prompt_id"],
                        version=usage["version"],
                        inputs_json=usage["inputs_json"],
                        position=usage["position"],
                        role=usage.get("role"),
                        source=usage.get("source"),
                        message_index=usage.get("message_index"),
                        metadata_json=usage.get("metadata_json"),
                    )
                )

        executions_created += 1
        logger.debug(f"Created execution trace for span {span.span_id}")

    return executions_created


def _recompute_trace(trace_id: str, project_id: UUID, conn: Connection) -> None:
    """
    Recompute execution traces with complete span set from database.

    This is triggered when late-arriving spans are detected for an existing trace.

    Future optimization: Make this async by enqueueing to a background worker.

    Args:
        trace_id: Trace ID to recompute
        project_id: Project UUID
        conn: Database connection
    """
    # Load all spans for this trace from DB
    all_spans = _load_all_spans_for_trace(trace_id, conn)

    if not all_spans:
        logger.warning(f"No spans found for trace {trace_id} during recompute")
        return

    logger.info(f"Recomputing trace {trace_id} with {len(all_spans)} total spans")

    # Delete template linkages (execution trace uses UPSERT now)
    _delete_template_linkages(trace_id, conn)

    # Re-extract with full context (will UPSERT execution trace)
    _extract_executions_from_batch(all_spans, project_id, conn)


def _load_all_spans_for_trace(trace_id: str, conn: Connection) -> list[OTLPSpan]:
    """
    Load all stored spans for a trace from database.

    Reconstructs OTLPSpan objects from database rows.
    """
    from dakora_server.api.otlp_traces import OTLPSpan

    result = conn.execute(
        select(otel_spans_table).where(otel_spans_table.c.trace_id == trace_id)
    )

    spans = []
    for row in result:
        spans.append(
            OTLPSpan(
                trace_id=row.trace_id,
                span_id=row.span_id,
                parent_span_id=row.parent_span_id,
                span_name=row.span_name,
                span_kind=row.span_kind,
                attributes=row.attributes or {},
                events=row.events or [],
                start_time_ns=row.start_time_ns,
                end_time_ns=row.end_time_ns,
                status_code=row.status_code,
                status_message=row.status_message,
            )
        )

    return spans


def _delete_template_linkages(trace_id: str, conn: Connection) -> None:
    """
    Delete existing template linkages for a trace.

    Used before recomputing to clear old template linkages.
    Execution trace itself uses UPSERT so no need to delete.
    """
    conn.execute(delete(template_traces_table).where(template_traces_table.c.trace_id == trace_id))
    logger.debug(f"Deleted template linkages for trace {trace_id}")