from __future__ import annotations
import sqlite3, json, time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY,
  prompt_id TEXT,
  version TEXT,
  inputs_json TEXT,
  output_text TEXT,
  cost REAL,
  latency_ms INTEGER,
  provider TEXT,
  model TEXT,
  tokens_in INTEGER,
  tokens_out INTEGER,
  cost_usd REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_MIGRATION_ADD_LLM_COLUMNS = """
ALTER TABLE logs ADD COLUMN provider TEXT;
ALTER TABLE logs ADD COLUMN model TEXT;
ALTER TABLE logs ADD COLUMN tokens_in INTEGER;
ALTER TABLE logs ADD COLUMN tokens_out INTEGER;
ALTER TABLE logs ADD COLUMN cost_usd REAL;
"""

class Logger:
    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as con:
            con.execute(_SCHEMA)
            self._migrate_if_needed(con)

    def _migrate_if_needed(self, con: sqlite3.Connection) -> None:
        cursor = con.execute("PRAGMA table_info(logs)")
        columns = {row[1] for row in cursor.fetchall()}

        if "provider" not in columns:
            for statement in _MIGRATION_ADD_LLM_COLUMNS.strip().split(";"):
                if statement.strip():
                    try:
                        con.execute(statement)
                    except sqlite3.OperationalError:
                        pass

    def write(self, prompt_id: str, version: str, inputs: Dict[str, Any], output: str,
              cost: float | None = None, latency_ms: int | None = None,
              provider: str | None = None, model: str | None = None,
              tokens_in: int | None = None, tokens_out: int | None = None,
              cost_usd: float | None = None) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                """INSERT INTO logs(prompt_id,version,inputs_json,output_text,cost,latency_ms,provider,model,tokens_in,tokens_out,cost_usd)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (prompt_id, version, json.dumps(inputs, ensure_ascii=False), output, cost, latency_ms,
                 provider, model, tokens_in, tokens_out, cost_usd)
            )

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