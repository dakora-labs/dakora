from __future__ import annotations
import json
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any

from sqlalchemy import insert
from sqlalchemy.engine import Engine

from .database import create_db_engine, get_connection, logs_table


class Logger:
    """Logger for execution logs using PostgreSQL"""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        """
        Initialize logger with SQLAlchemy engine.

        Args:
            engine: SQLAlchemy Engine (if None, creates new engine from DATABASE_URL)
        """
        self.engine = engine or create_db_engine()

    def close(self) -> None:
        """Close the database connection pool."""
        if hasattr(self, 'engine') and self.engine:
            self.engine.dispose()

    def write(
        self,
        prompt_id: str,
        version: str,
        inputs: Dict[str, Any],
        output: str,
        cost: float | None = None,
        latency_ms: int | None = None,
        provider: str | None = None,
        model: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        cost_usd: float | None = None,
    ) -> None:
        """
        Write execution log to database.

        Args:
            prompt_id: Template ID
            version: Template version
            inputs: Input parameters (will be JSON-serialized)
            output: LLM output text
            cost: Deprecated (use cost_usd)
            latency_ms: Execution latency in milliseconds
            provider: LLM provider (e.g., "openai", "anthropic")
            model: Model identifier (e.g., "gpt-4", "claude-3-opus")
            tokens_in: Input tokens
            tokens_out: Output tokens
            cost_usd: Execution cost in USD
        """
        stmt = insert(logs_table).values(
            prompt_id=prompt_id,
            version=version,
            inputs_json=json.dumps(inputs, ensure_ascii=False),
            output_text=output,
            cost=cost,
            latency_ms=latency_ms,
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
        )

        with get_connection(self.engine) as conn:
            conn.execute(stmt)
            conn.commit()

@contextmanager
def run(logger: Optional[Logger], prompt_id: str, version: str):
    t0 = time.time()
    record = {"inputs": None, "output": None, "cost": None, "latency_ms": None}
    try:
        yield record
    finally:
        if logger:
            latency = int((time.time() - t0) * 1000)
            logger.write(prompt_id, version, record["inputs"] or {}, record["output"] or "",
                         cost=record["cost"], latency_ms=record["latency_ms"] or latency)