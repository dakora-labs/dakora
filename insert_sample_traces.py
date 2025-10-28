"""Insert sample execution traces for testing analytics dashboard."""

import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add server to path to import database utilities
sys.path.insert(0, str(Path(__file__).parent / "server"))

from dakora_server.core.database import get_engine, get_connection
from sqlalchemy import text

engine = get_engine()

# Project ID to insert traces for
PROJECT_ID = "2676e2d9-4e80-4fc5-9619-773ccda8d7c3"

# Sample prompts
PROMPTS = [
    "customer-support-agent",
    "code-review-bot",
    "content-generator",
    "data-analyzer",
    "email-assistant"
]

# Models and providers
MODELS = [
    ("azure", "gpt-4"),
    ("azure", "gpt-3.5-turbo"),
    ("google", "gemini-pro"),
]

def generate_traces():
    """Generate sample traces for Oct 26-27, 2025."""
    traces = []

    # October 27, 2025 (today) - more data
    base_date = datetime(2025, 10, 27, 0, 0, 0, tzinfo=timezone.utc)
    for hour in range(24):
        for _ in range(3):  # 3 traces per hour
            trace_time = base_date + timedelta(hours=hour, minutes=_ * 20)

            prompt_id = PROMPTS[len(traces) % len(PROMPTS)]
            provider, model = MODELS[len(traces) % len(MODELS)]

            # Vary the costs
            base_cost = 0.002 if "gpt-4" in model else 0.0005
            tokens_in = 500 + (len(traces) % 1000)
            tokens_out = 200 + (len(traces) % 500)
            cost = base_cost * (tokens_in + tokens_out) / 1000
            latency = 800 + (len(traces) % 2000)

            traces.append({
                "trace_id": str(uuid.uuid4()),
                "project_id": PROJECT_ID,
                "prompt_id": prompt_id,
                "version": "v1",
                "provider": provider,
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(cost, 6),
                "latency_ms": latency,
                "created_at": trace_time,
                "source": "test_data",
                "session_id": f"session-{len(traces) % 5}",
            })

    # October 26, 2025 (yesterday) - less data
    base_date = datetime(2025, 10, 26, 0, 0, 0, tzinfo=timezone.utc)
    for hour in range(24):
        for _ in range(2):  # 2 traces per hour
            trace_time = base_date + timedelta(hours=hour, minutes=_ * 30)

            prompt_id = PROMPTS[len(traces) % len(PROMPTS)]
            provider, model = MODELS[len(traces) % len(MODELS)]

            base_cost = 0.002 if "gpt-4" in model else 0.0005
            tokens_in = 400 + (len(traces) % 800)
            tokens_out = 150 + (len(traces) % 400)
            cost = base_cost * (tokens_in + tokens_out) / 1000
            latency = 700 + (len(traces) % 1500)

            traces.append({
                "trace_id": str(uuid.uuid4()),
                "project_id": PROJECT_ID,
                "prompt_id": prompt_id,
                "version": "v1",
                "provider": provider,
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(cost, 6),
                "latency_ms": latency,
                "created_at": trace_time,
                "source": "test_data",
                "session_id": f"session-{len(traces) % 5}",
            })

    return traces

def insert_traces():
    """Insert traces into database."""
    traces = generate_traces()

    print(f"Generated {len(traces)} sample traces")
    print(f"Date range: Oct 26-27, 2025")
    print(f"Project ID: {PROJECT_ID}")
    print()

    with get_connection(engine) as conn:
        # Check if project exists
        result = conn.execute(
            text("SELECT id FROM projects WHERE id = :project_id"),
            {"project_id": PROJECT_ID}
        )
        if not result.fetchone():
            print(f"ERROR: Project {PROJECT_ID} not found!")
            return

        # Delete existing test traces for this project
        result = conn.execute(
            text("""
                DELETE FROM execution_traces
                WHERE project_id = :project_id
                AND source = 'test_data'
            """),
            {"project_id": PROJECT_ID}
        )
        deleted = result.rowcount
        if deleted > 0:
            print(f"Deleted {deleted} existing test traces")

        # Insert new traces
        for trace in traces:
            conn.execute(
                text("""
                    INSERT INTO execution_traces (
                        trace_id, project_id, prompt_id, version,
                        provider, model, tokens_in, tokens_out,
                        cost_usd, latency_ms, created_at, source, session_id
                    ) VALUES (
                        :trace_id, :project_id, :prompt_id, :version,
                        :provider, :model, :tokens_in, :tokens_out,
                        :cost_usd, :latency_ms, :created_at, :source, :session_id
                    )
                """),
                trace
            )

        conn.commit()
        print(f"Successfully inserted {len(traces)} traces")

        # Show summary stats
        result = conn.execute(
            text("""
                SELECT
                    COUNT(*) as total_traces,
                    SUM(cost_usd) as total_cost,
                    AVG(cost_usd) as avg_cost,
                    MIN(created_at) as earliest,
                    MAX(created_at) as latest
                FROM execution_traces
                WHERE project_id = :project_id
                AND source = 'test_data'
            """),
            {"project_id": PROJECT_ID}
        )
        stats = result.fetchone()

        print()
        print("Summary:")
        print(f"  Total traces: {stats.total_traces}")
        print(f"  Total cost: ${stats.total_cost:.2f}")
        print(f"  Avg cost: ${stats.avg_cost:.6f}")
        print(f"  Date range: {stats.earliest} to {stats.latest}")

        # Show per-prompt breakdown
        result = conn.execute(
            text("""
                SELECT
                    prompt_id,
                    COUNT(*) as count,
                    SUM(cost_usd) as total_cost
                FROM execution_traces
                WHERE project_id = :project_id
                AND source = 'test_data'
                GROUP BY prompt_id
                ORDER BY total_cost DESC
            """),
            {"project_id": PROJECT_ID}
        )

        print()
        print("Per-prompt breakdown:")
        for row in result:
            print(f"  {row.prompt_id}: {row.count} executions, ${row.total_cost:.2f}")

if __name__ == "__main__":
    insert_traces()