# Schema Deprecation Plan: Old Execution Traces → New Normalized Schema

**Status:** Planning
**Created:** 2025-11-04
**Target Completion:** TBD

---

## Table of Contents

- [Overview](#overview)
- [Background](#background)
- [Schema Comparison](#schema-comparison)
- [Migration Goals](#migration-goals)
- [Impact Analysis](#impact-analysis)
- [Phased Deprecation Plan](#phased-deprecation-plan)
- [Detailed Implementation Steps](#detailed-implementation-steps)
- [Verification & Rollback](#verification--rollback)
- [Timeline & Dependencies](#timeline--dependencies)
- [Post-Deprecation Cleanup](#post-deprecation-cleanup)

---

## Overview

This document outlines the plan to fully deprecate the old execution traces schema (`execution_traces` and `template_traces` tables) in favor of the new normalized OTLP-based schema (`traces`, `executions`, `execution_messages`).

### Key Objectives

1. **Eliminate dual-write complexity** - Currently writing to both old and new schemas
2. **Unify data model** - Single source of truth for execution data
3. **Improve query performance** - Normalized schema enables better analytics
4. **Preserve historical data** - Backfill old data to maintain continuity
5. **Zero downtime** - Phased rollout with fallback capability

### Current State

- ✅ New schema tables exist (`traces`, `executions`, `execution_messages`)
- ✅ OTLP processor dual-writes to both schemas
- ✅ Read paths prioritize new schema with old-schema fallbacks
- ⚠️ `template_traces` table still references old `execution_traces.trace_id`
- ⚠️ Manual execution API writes only to old schema
- ⚠️ Template analytics query old schema

### Target State

- New schema is the **only** source of truth
- Old tables (`execution_traces`, `template_traces`) are dropped
- All reads/writes use normalized tables
- Historical data is preserved via one-time backfill

---

## Background

### Why Migrate?

The old schema was designed before OTLP (OpenTelemetry Protocol) support and has several limitations:

1. **Denormalized structure** - Conversation history stored as JSONB blob
2. **Poor queryability** - Can't efficiently filter by message content or role
3. **Limited observability** - No support for nested spans, parent-child relationships
4. **Inflexible** - Adding new execution types requires schema changes

The new schema addresses these issues:

- **Trace-level grouping** - `traces` table groups related executions
- **Span-based executions** - `executions` table supports nested spans with parent-child links
- **Normalized messages** - `execution_messages` enables efficient message queries
- **Extensible** - JSONB attributes allow adding metadata without migrations

### Architecture

```
OLD SCHEMA:
execution_traces (denormalized, monolithic)
  ├─ conversation_history (JSONB blob)
  └─ template_traces (FK to trace_id)

NEW SCHEMA:
traces (trace-level metadata)
  └─ executions (individual spans)
       └─ execution_messages (normalized messages)
            ├─ input messages
            └─ output messages
```

---

## Schema Comparison

### Old Schema

**`execution_traces` (41 rows currently)**

| Column | Type | Purpose | Notes |
|--------|------|---------|-------|
| `trace_id` | String(255) | Primary identifier | FK target for template_traces |
| `conversation_history` | JSONB | Full chat messages | Denormalized blob |
| `provider`, `model` | String | LLM details | Top-level fields |
| `tokens_in/out`, `cost_usd` | Integer/Float | Metrics | Aggregated values |
| `project_id` | UUID | Multi-tenancy | FK to projects |
| `created_at` | Timestamp | Creation time | Single timestamp |

**`template_traces` (linkage table)**

| Column | Type | Purpose | Notes |
|--------|------|---------|-------|
| `trace_id` | String(255) | **FK → execution_traces** | **Blocker for deprecation** |
| `prompt_id`, `version` | String | Template reference | Links execution to prompt |
| `position` | Integer | Order in conversation | Multi-template support |

### New Schema

**`traces` (trace-level)**

| Column | Type | Purpose | Notes |
|--------|------|---------|-------|
| `trace_id` | Text | Primary identifier | Groups multiple spans |
| `project_id` | UUID | Multi-tenancy | FK to projects |
| `start_time`, `end_time` | Timestamp | Trace duration | Separate start/end |
| `duration_ms` | Integer | Computed field | Auto-calculated |
| `attributes` | JSONB | Extensible metadata | OTLP compatibility |

**`executions` (span-level)**

| Column | Type | Purpose | Notes |
|--------|------|---------|-------|
| `trace_id`, `span_id` | Text | Composite PK | Enables nested spans |
| `parent_span_id` | Text | Hierarchy | Supports multi-agent flows |
| `type` | Text | Execution type | 'chat', 'agent', 'tool', etc. |
| `provider`, `model` | Text | LLM details | Per-span values |
| `tokens_in/out`, `total_cost_usd` | Integer/Numeric | Metrics | Precise decimal cost |
| `status`, `status_message` | Text | Execution result | Success/error tracking |

**`execution_messages` (message-level)**

| Column | Type | Purpose | Notes |
|--------|------|---------|-------|
| `trace_id`, `span_id` | Text | FK to executions | Message belongs to span |
| `direction` | Text | Input vs output | 'input' or 'output' |
| `role` | Text | Message role | 'user', 'assistant', 'system' |
| `parts` | JSONB | Message content | Array of {type, content} |
| `msg_index` | Integer | Message order | Preserves sequence |

---

## Migration Goals

### Must-Haves (P0)

- [ ] Zero data loss - all historical executions preserved
- [ ] Zero downtime - phased rollout with fallback
- [ ] Foreign key integrity - `template_traces` references valid `traces.trace_id`
- [ ] Backward compatibility - existing API contracts unchanged
- [ ] Accurate analytics - template stats match or improve upon old queries

### Should-Haves (P1)

- [ ] Performance improvement - faster query times for execution lists
- [ ] Test coverage - comprehensive integration tests for new paths
- [ ] Documentation - updated API docs and developer guides
- [ ] Monitoring - metrics to track migration progress

### Nice-to-Haves (P2)

- [ ] Cleanup old columns - remove deprecated fields from new schema
- [ ] Rename tables - `template_traces` → `template_usages`
- [ ] Add indexes - optimize common query patterns

---

## Impact Analysis

### Code Locations Using Old Schema

| File | Line | Function | Old Schema Usage | Impact |
|------|------|----------|------------------|--------|
| `api/execution_traces.py` | 94 | `create_execution` | Inserts into `execution_traces` | **HIGH** - Primary write path |
| `api/execution_traces.py` | 500 | `list_executions` | OLD SCHEMA QUERY fallback | **MEDIUM** - Reads with fallback |
| `api/execution_traces.py` | 875 | `get_execution` | OLD SCHEMA QUERY fallback | **MEDIUM** - Reads with fallback |
| `api/execution_traces.py` | 1221 | `get_template_analytics` | Aggregates from old tables | **HIGH** - Template stats broken without migration |
| `api/project_executions.py` | 158 | Manual run logging | Inserts into `execution_traces` + `template_traces` | **HIGH** - Prompt execution API |
| `core/otlp_processor.py` | 200 | OTLP ingestion | Dual-writes to old + new | **CRITICAL** - Main ingestion path |
| `core/otlp_extractor.py` | 211 | `extract_execution_trace` | Returns old schema dict | **MEDIUM** - Used by dual-write |
| `core/database.py` | 41 | Schema definition | Defines `execution_traces`, `template_traces` | **LOW** - Schema source of truth |
| `tests/test_database.py` | 112 | Schema tests | Asserts old table structure | **LOW** - Test cleanup |

### Foreign Key Blocker

**Critical Issue:** `template_traces.trace_id` currently has FK to `execution_traces.trace_id`

```sql
-- Current (OLD)
template_traces.trace_id → execution_traces.trace_id

-- Target (NEW)
template_traces.trace_id → traces.trace_id
```

**Why it matters:** We cannot drop `execution_traces` until the FK is retargeted. This is the first migration step.

### Data Volume

- **Current `execution_traces` rows:** ~41 (based on test data)
- **Current `template_traces` rows:** Unknown (needs query)
- **Estimated backfill time:** < 1 minute for current volume
- **Production volume:** Unknown - needs assessment before rollout

---

## Phased Deprecation Plan

### Phase 0: Prepare & Validate (1-2 days)

**Goal:** Set up infrastructure for safe migration

**Tasks:**
- [ ] Create Alembic migration to add new FK on `template_traces`
- [ ] Backfill missing `traces` rows for existing `template_traces.trace_id`
- [ ] Add comprehensive integration tests for new write paths
- [ ] Document rollback procedures

**Success Criteria:**
- FK migration runs successfully on local DB
- All existing `template_traces` rows have corresponding `traces` rows
- Tests pass with new FK in place

**Rollback:** Drop new FK, revert to old FK (requires migration downgrade)

---

### Phase 1: Stop New Writes to Old Schema (2-3 days)

**Goal:** Eliminate dual-write complexity, write only to new schema

#### 1.1: Update OTLP Ingestion

**File:** `server/dakora_server/core/otlp_processor.py:200`

**Change:** Remove dual-write block

```python
# BEFORE (dual-write):
async def _write_execution_trace(...):
    # Write to new schema
    await _write_to_new_schema(...)
    
    # DUAL-WRITE: Upsert to OLD execution_traces table
    execution_data = extractor.extract_execution_trace(...)
    stmt = postgresql.insert(traces_table).values(...)
    await conn.execute(stmt)  # ← REMOVE THIS

# AFTER (new schema only):
async def _write_execution_trace(...):
    # Write to new schema
    await _write_to_new_schema(...)
    # Old dual-write removed
```

**Validation:**
- Ensure `_write_to_new_schema` upserts `traces` **before** inserting `template_traces`
- Add logging to confirm old writes are skipped
- Monitor error rates after deployment

---

#### 1.2: Update Manual Execution API

**File:** `server/dakora_server/api/project_executions.py:158`

**Change:** Replace old schema writes with new schema mapping

**OLD CODE:**
```python
# Insert into execution_traces
trace_values = {
    "trace_id": trace_id,
    "project_id": project_id,
    "conversation_history": [...],
    "provider": provider,
    "model": model,
    # ... old schema fields
}
await conn.execute(traces_table.insert().values(trace_values))

# Insert into template_traces
await conn.execute(
    template_traces_table.insert().values({
        "trace_id": trace_id,
        "prompt_id": prompt_id,
        # ...
    })
)
```

**NEW CODE:**
```python
# 1. Upsert trace-level record
trace_values = {
    "trace_id": trace_id,
    "project_id": project_id,
    "provider": provider,
    "start_time": created_at,
    "end_time": created_at + timedelta(milliseconds=latency_ms or 0),
    "attributes": {},
}
stmt = postgresql.insert(traces_new_table).values(trace_values)
stmt = stmt.on_conflict_do_update(
    index_elements=["trace_id"],
    set_={"end_time": stmt.excluded.end_time}
)
await conn.execute(stmt)

# 2. Insert chat span into executions
span_id = f"{trace_id}-root"  # Or generate unique span_id
execution_values = {
    "trace_id": trace_id,
    "span_id": span_id,
    "parent_span_id": None,
    "project_id": project_id,
    "type": "chat",
    "span_kind": "internal",
    "agent_name": agent_id,  # From request
    "provider": provider,
    "model": model,
    "start_time": created_at,
    "end_time": created_at + timedelta(milliseconds=latency_ms or 0),
    "tokens_in": tokens_in,
    "tokens_out": tokens_out,
    "total_cost_usd": cost_usd,
    "status": "ok",
    "attributes": {},
}
await conn.execute(executions_new_table.insert().values(execution_values))

# 3. Insert input messages (rendered prompt + conversation context)
for idx, msg in enumerate(conversation_history):
    if msg["role"] in ("user", "system"):
        msg_values = {
            "trace_id": trace_id,
            "span_id": span_id,
            "direction": "input",
            "msg_index": idx,
            "role": msg["role"],
            "parts": [{"type": "text", "content": msg["content"]}],
        }
        await conn.execute(execution_messages_new_table.insert().values(msg_values))

# 4. Insert output message (assistant response)
for idx, msg in enumerate(conversation_history):
    if msg["role"] == "assistant":
        msg_values = {
            "trace_id": trace_id,
            "span_id": span_id,
            "direction": "output",
            "msg_index": idx,
            "role": "assistant",
            "parts": [{"type": "text", "content": msg["content"]}],
        }
        await conn.execute(execution_messages_new_table.insert().values(msg_values))

# 5. Insert template linkage (now FK → traces.trace_id)
await conn.execute(
    template_traces_table.insert().values({
        "trace_id": trace_id,
        "prompt_id": prompt_id,
        "version": version,
        "inputs_json": inputs_json,
        "position": 0,
        "source": "manual",
    })
)
```

**Validation:**
- Test manual prompt execution via UI/API
- Verify executions appear in list with correct metrics
- Check template linkage is preserved

---

#### 1.3: Update Direct Create Execution API

**File:** `server/dakora_server/api/execution_traces.py:94`

**Change:** Apply same new schema mapping as 1.2

**Key Differences:**
- May receive `conversation_history` directly in request
- Need to extract `agent_id` from request body if provided
- Preserve existing validation logic

**Validation:**
- Test SDK `client.traces.create()` calls
- Verify backward compatibility for existing integrations

---

**Phase 1 Success Criteria:**
- [ ] Zero writes to `execution_traces` table (monitor with DB query)
- [ ] All new executions queryable via new schema paths
- [ ] No increase in error rates
- [ ] Template linkage intact (FK constraint not violated)

**Phase 1 Rollback:**
- Revert code changes via git
- Re-enable dual-write if needed (temporary fix)
- Investigate failures before retry

---

### Phase 2: Replace Old Schema Reads (2-3 days)

**Goal:** Remove fallback queries, always use new schema

#### 2.1: Remove List Executions Fallback

**File:** `server/dakora_server/api/execution_traces.py:500`

**Change:** Delete "OLD SCHEMA QUERY" block

```python
# BEFORE:
if not results:
    # OLD SCHEMA QUERY - fallback to execution_traces
    old_query = select([traces_table, ...]).where(...)
    results = await conn.execute(old_query).fetchall()

# AFTER:
# Fallback removed - new schema is source of truth
```

**Impact:** API will only return executions stored in new schema. After backfill (Phase 3), this is complete data.

---

#### 2.2: Remove Get Execution Detail Fallback

**File:** `server/dakora_server/api/execution_traces.py:875`

**Change:** Delete old schema fallback path

**Validation:**
- Test fetching execution detail by `trace_id`
- Verify message history renders correctly

---

#### 2.3: Reimplement Template Analytics

**File:** `server/dakora_server/api/execution_traces.py:1221`

**Change:** Rewrite `get_template_analytics` to query new schema

**OLD QUERY (aggregates from old tables):**
```python
# Joins execution_traces + template_traces
query = select([
    func.count(distinct(traces_table.c.trace_id)).label("total_executions"),
    func.sum(traces_table.c.cost_usd).label("total_cost"),
    # ...
]).select_from(
    traces_table.join(template_traces_table, ...)
).where(template_traces_table.c.prompt_id == prompt_id)
```

**NEW QUERY (aggregates from new tables):**
```python
# Total executions - count distinct traces linked to template
total_executions_query = (
    select(func.count(func.distinct(traces_new_table.c.trace_id)))
    .select_from(
        template_traces_table.join(
            traces_new_table,
            template_traces_table.c.trace_id == traces_new_table.c.trace_id
        )
    )
    .where(
        and_(
            traces_new_table.c.project_id == project_id,
            template_traces_table.c.prompt_id == prompt_id
        )
    )
)

# Total cost/tokens - sum from executions (type='chat')
metrics_query = (
    select(
        func.sum(executions_new_table.c.total_cost_usd).label("total_cost"),
        func.sum(executions_new_table.c.tokens_in).label("total_tokens_in"),
        func.sum(executions_new_table.c.tokens_out).label("total_tokens_out"),
    )
    .select_from(
        template_traces_table.join(
            executions_new_table,
            template_traces_table.c.trace_id == executions_new_table.c.trace_id
        )
    )
    .where(
        and_(
            executions_new_table.c.project_id == project_id,
            executions_new_table.c.type == "chat",
            template_traces_table.c.prompt_id == prompt_id
        )
    )
)

# Average latency - from traces duration
latency_query = (
    select(func.avg(traces_new_table.c.duration_ms))
    .select_from(
        template_traces_table.join(
            traces_new_table,
            template_traces_table.c.trace_id == traces_new_table.c.trace_id
        )
    )
    .where(
        and_(
            traces_new_table.c.project_id == project_id,
            template_traces_table.c.prompt_id == prompt_id
        )
    )
)
```

**Important Notes:**
- Filter by `project_id` for multi-tenancy
- Filter by `type='chat'` to exclude non-LLM spans (tools, agents)
- Use `duration_ms` computed column for latency
- Handle null values (no executions yet)

**Validation:**
- Compare analytics results before/after migration on test project
- Verify counts match within acceptable tolerance
- Test edge cases (no executions, single execution)

---

**Phase 2 Success Criteria:**
- [ ] All API endpoints read from new schema only
- [ ] Template analytics return accurate results
- [ ] Execution list/detail pages load correctly
- [ ] Performance metrics stable or improved

**Phase 2 Rollback:**
- Restore old query paths via git revert
- Template analytics can fall back to old schema temporarily

---

### Phase 3: Backfill Legacy Data (1-2 days)

**Goal:** Migrate historical `execution_traces` data to new schema

#### 3.1: Pre-Backfill Validation

**Tasks:**
- [ ] Count rows in `execution_traces` (production)
- [ ] Estimate backfill duration (row count × avg insert time)
- [ ] Test backfill script on staging/local DB copy
- [ ] Plan maintenance window if needed (likely unnecessary for low volume)

---

#### 3.2: Backfill Script

**Location:** Create `server/scripts/backfill_old_executions.py`

**Logic:**
```python
"""
Backfill old execution_traces data into new normalized schema.
Run once during Phase 3 of deprecation.
"""

import asyncio
from datetime import timedelta
from sqlalchemy import select
from dakora_server.core.database import (
    get_engine,
    traces_table,  # OLD
    template_traces_table,
    traces_new_table,  # NEW
    executions_new_table,
    execution_messages_new_table,
)

async def backfill_legacy_executions():
    engine = get_engine()
    async with engine.begin() as conn:
        # Fetch all old execution_traces rows
        old_traces = await conn.execute(
            select(traces_table).order_by(traces_table.c.created_at)
        )
        
        total = 0
        for row in old_traces:
            trace_id = row.trace_id
            
            # Check if already migrated
            exists = await conn.execute(
                select(traces_new_table.c.trace_id)
                .where(traces_new_table.c.trace_id == trace_id)
            )
            if exists.fetchone():
                print(f"Skipping {trace_id} (already migrated)")
                continue
            
            # 1. Insert into traces
            start_time = row.created_at
            end_time = start_time + timedelta(milliseconds=row.latency_ms or 0)
            
            await conn.execute(
                traces_new_table.insert().values({
                    "trace_id": trace_id,
                    "project_id": row.project_id,
                    "provider": row.provider,
                    "start_time": start_time,
                    "end_time": end_time,
                    "attributes": row.metadata or {},
                })
            )
            
            # 2. Insert into executions (single chat span)
            span_id = f"{trace_id}-backfill"
            
            await conn.execute(
                executions_new_table.insert().values({
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "parent_span_id": None,
                    "project_id": row.project_id,
                    "type": "chat",
                    "span_kind": "internal",
                    "agent_name": row.agent_id,
                    "provider": row.provider,
                    "model": row.model,
                    "start_time": start_time,
                    "end_time": end_time,
                    "tokens_in": row.tokens_in,
                    "tokens_out": row.tokens_out,
                    "total_cost_usd": row.cost_usd,
                    "status": "unknown",  # Old schema doesn't track status
                    "attributes": {},
                })
            )
            
            # 3. Insert into execution_messages
            conversation_history = row.conversation_history or []
            
            for idx, msg in enumerate(conversation_history):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Map role to direction
                direction = "input" if role in ("user", "system") else "output"
                
                await conn.execute(
                    execution_messages_new_table.insert().values({
                        "trace_id": trace_id,
                        "span_id": span_id,
                        "direction": direction,
                        "msg_index": idx,
                        "role": role,
                        "parts": [{"type": "text", "content": content}],
                    })
                )
            
            total += 1
            print(f"Migrated {trace_id} ({total} total)")
        
        print(f"✅ Backfill complete: {total} executions migrated")

if __name__ == "__main__":
    asyncio.run(backfill_legacy_executions())
```

**Run Instructions:**
```bash
cd server
export PATH="$HOME/.local/bin:$PATH" && uv run python scripts/backfill_old_executions.py
```

---

#### 3.3: Verify Backfill

**Validation Queries:**
```sql
-- Count old vs new executions
SELECT COUNT(*) FROM execution_traces;  -- Should match...
SELECT COUNT(DISTINCT trace_id) FROM traces;  -- ...this count

-- Verify template linkage
SELECT COUNT(*) FROM template_traces tt
LEFT JOIN traces t ON t.trace_id = tt.trace_id
WHERE t.trace_id IS NULL;
-- Should return 0 (all templates have corresponding traces)

-- Spot-check a migrated execution
SELECT * FROM execution_traces WHERE trace_id = '<some-trace-id>';
SELECT * FROM traces WHERE trace_id = '<same-trace-id>';
SELECT * FROM executions WHERE trace_id = '<same-trace-id>';
SELECT * FROM execution_messages WHERE trace_id = '<same-trace-id>';
```

---

**Phase 3 Success Criteria:**
- [ ] All `execution_traces` rows have corresponding `traces` rows
- [ ] Message counts match (conversation_history → execution_messages)
- [ ] Template analytics numbers unchanged after backfill
- [ ] No FK violations in `template_traces`

**Phase 3 Rollback:**
- Delete backfilled `traces`, `executions`, `execution_messages` rows
- Use `WHERE attributes->>'backfill' = 'true'` if tagged during migration

---

### Phase 4: Cleanup & Drop Old Tables (1 day)

**Goal:** Remove deprecated code and schema

#### 4.1: Drop Old Table Definitions

**File:** `server/dakora_server/core/database.py:41`

**Change:** Remove table definitions

```python
# DELETE:
traces_table = Table("execution_traces", metadata, ...)
# Keep template_traces_table (now references traces.trace_id)
```

---

#### 4.2: Create Alembic Migration to Drop Tables

**Migration Steps:**
```python
def upgrade():
    # Drop old table (FK already retargeted in Phase 0)
    op.drop_table("execution_traces")

def downgrade():
    # Recreate table if needed (discouraged - data loss)
    op.create_table("execution_traces", ...)
```

**Run Migration:**
```bash
cd server
export PATH="$HOME/.local/bin:$PATH" && uv run alembic revision -m "drop_old_execution_traces"
# Edit migration file
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head
```

---

#### 4.3: Remove Dead Code

**Files to Update:**

1. `server/dakora_server/core/otlp_extractor.py:211`
   - Mark `extract_execution_trace` as deprecated or remove entirely

2. `server/tests/test_database.py:112`
   - Remove assertions for `execution_traces` table structure
   - Add tests for new schema tables if missing

3. Update documentation:
   - `CLAUDE.md` - Update core tables list
   - `assets/DATABASE_MIGRATIONS.md` - Add migration case study
   - API docs (if any) - Update trace data model

---

#### 4.4: Optional: Rename template_traces

**Consideration:** `template_traces` is a confusing name now that it references `traces.trace_id` instead of `execution_traces.trace_id`.

**Suggested Rename:** `template_usages` or `prompt_executions`

**Migration Steps:**
```python
def upgrade():
    op.rename_table("template_traces", "template_usages")

def downgrade():
    op.rename_table("template_usages", "template_traces")
```

**Impact:** Requires updating all code references to `template_traces_table`

**Recommendation:** Defer to Phase 5 (post-deprecation improvements)

---

**Phase 4 Success Criteria:**
- [ ] `execution_traces` table dropped in all environments
- [ ] No code references old table
- [ ] All tests pass
- [ ] Documentation updated

**Phase 4 Rollback:**
- Restore table via Alembic downgrade
- Revert code changes

---

## Detailed Implementation Steps

### Step-by-Step Checklist

#### Phase 0: Prepare

- [ ] **Create FK migration** (`server/alembic/versions/`)
  ```bash
  cd server
  export PATH="$HOME/.local/bin:$PATH" && uv run alembic revision -m "retarget_template_traces_fk_to_new_traces"
  ```
  
- [ ] **Write migration upgrade logic:**
  ```python
  def upgrade():
      # 1. Backfill missing traces rows
      op.execute("""
          INSERT INTO traces (trace_id, project_id, provider, start_time, end_time, attributes)
          SELECT DISTINCT
              tt.trace_id,
              et.project_id,
              et.provider,
              et.created_at,
              et.created_at + (et.latency_ms || ' milliseconds')::interval,
              '{}'::jsonb
          FROM template_traces tt
          JOIN execution_traces et ON et.trace_id = tt.trace_id
          WHERE NOT EXISTS (SELECT 1 FROM traces t WHERE t.trace_id = tt.trace_id)
      """)
      
      # 2. Drop old FK constraint
      op.drop_constraint(
          "template_traces_trace_id_fkey",
          "template_traces",
          type_="foreignkey"
      )
      
      # 3. Add new FK constraint
      op.create_foreign_key(
          "template_traces_trace_id_fkey",
          "template_traces",
          "traces",
          ["trace_id"],
          ["trace_id"],
          ondelete="CASCADE"
      )
  ```

- [ ] **Test migration locally:**
  ```bash
  export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head
  export PATH="$HOME/.local/bin:$PATH" && uv run alembic downgrade -1  # Test rollback
  export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head   # Re-apply
  ```

- [ ] **Verify FK integrity:**
  ```sql
  -- Should return 0
  SELECT COUNT(*) FROM template_traces tt
  LEFT JOIN traces t ON t.trace_id = tt.trace_id
  WHERE t.trace_id IS NULL;
  ```

- [ ] **Add integration tests** for new write paths (see Testing section)

---

#### Phase 1: Stop New Writes

- [ ] **Update OTLP processor** (`otlp_processor.py:200`)
  - Remove dual-write block
  - Add debug logging to confirm old writes stopped
  
- [ ] **Update manual execution API** (`project_executions.py:158`)
  - Implement new schema mapping (see Phase 1.2)
  - Test via UI: Create → Execute Prompt
  
- [ ] **Update create execution API** (`execution_traces.py:94`)
  - Apply same new schema logic
  - Test via SDK/curl
  
- [ ] **Deploy to staging**
  - Monitor error rates
  - Verify new executions appear in UI
  
- [ ] **Monitor metrics:**
  ```sql
  -- Should decrease to 0 after deployment
  SELECT COUNT(*) FROM execution_traces
  WHERE created_at > NOW() - INTERVAL '1 hour';
  ```

---

#### Phase 2: Replace Reads

- [ ] **Remove list fallback** (`execution_traces.py:500`)
- [ ] **Remove detail fallback** (`execution_traces.py:875`)
- [ ] **Reimplement analytics** (`execution_traces.py:1221`)
  - Write new query (see Phase 2.3)
  - Test on project with known execution count
  - Compare results with old query (run both temporarily)
  
- [ ] **Deploy to staging**
- [ ] **Validate analytics accuracy:**
  - Template page shows correct execution count
  - Cost/token sums match expectations
  - Average latency is reasonable

---

#### Phase 3: Backfill

- [ ] **Create backfill script** (`server/scripts/backfill_old_executions.py`)
- [ ] **Test on local DB copy**
- [ ] **Run on staging**
- [ ] **Verify results** (see Phase 3.3)
- [ ] **Run on production** (coordinate with team)
- [ ] **Final validation:**
  ```sql
  -- Execution counts match
  SELECT
      (SELECT COUNT(*) FROM execution_traces) AS old_count,
      (SELECT COUNT(DISTINCT trace_id) FROM traces) AS new_count;
  ```

---

#### Phase 4: Cleanup

- [ ] **Create drop migration** (`alembic revision -m "drop_execution_traces"`)
- [ ] **Update database.py** - Remove old table definition
- [ ] **Remove dead code:**
  - `otlp_extractor.py` - Deprecate old functions
  - `test_database.py` - Remove old schema tests
  
- [ ] **Update docs:**
  - `CLAUDE.md` - Update core tables section
  - Add this deprecation doc to `assets/`
  
- [ ] **Deploy migration**
- [ ] **Run full test suite**
- [ ] **Verify production health**

---

## Verification & Rollback

### Pre-Deployment Checklist

Before each phase deployment:

- [ ] All tests pass locally
- [ ] Alembic migrations tested (upgrade + downgrade)
- [ ] Code review completed
- [ ] Staging environment validated
- [ ] Rollback plan documented

### Monitoring During Rollout

**Key Metrics:**

1. **Error rates** - No increase in 5xx responses
2. **Write counts** - Old table writes drop to 0
3. **Query performance** - List/detail endpoints < 500ms
4. **Data integrity** - FK violations = 0

**Dashboard Queries:**

```sql
-- Recent writes to old table (should be 0 after Phase 1)
SELECT COUNT(*) FROM execution_traces
WHERE created_at > NOW() - INTERVAL '1 hour';

-- FK integrity
SELECT COUNT(*) FROM template_traces tt
LEFT JOIN traces t ON t.trace_id = tt.trace_id
WHERE t.trace_id IS NULL;

-- Execution message counts (sanity check)
SELECT
    trace_id,
    COUNT(*) AS message_count
FROM execution_messages
GROUP BY trace_id
ORDER BY created_at DESC
LIMIT 10;
```

### Rollback Procedures

#### Phase 0 Rollback (FK Migration)

```bash
cd server
export PATH="$HOME/.local/bin:$PATH" && uv run alembic downgrade -1
```

**Verify:**
```sql
-- FK should point to execution_traces again
SELECT constraint_name, table_name, column_name
FROM information_schema.key_column_usage
WHERE constraint_name = 'template_traces_trace_id_fkey';
```

---

#### Phase 1 Rollback (Write Paths)

**Git Revert:**
```bash
git revert <commit-hash>
git push origin debug/dakora-sdk
```

**Emergency Fix (if needed):**
- Temporarily re-enable dual-write in `otlp_processor.py`
- Deploy hotfix
- Investigate root cause before re-attempting migration

---

#### Phase 2 Rollback (Read Paths)

**Git Revert:**
```bash
git revert <commit-hash>
```

**Template Analytics Emergency Fix:**
- Restore old query temporarily
- Accept dual-source data (old + new executions)
- Reschedule analytics migration

---

#### Phase 3 Rollback (Backfill)

**Delete Backfilled Data:**
```sql
-- If backfill added a marker attribute
DELETE FROM execution_messages WHERE trace_id IN (
    SELECT trace_id FROM traces WHERE attributes->>'backfill' = 'true'
);
DELETE FROM executions WHERE trace_id IN (
    SELECT trace_id FROM traces WHERE attributes->>'backfill' = 'true'
);
DELETE FROM traces WHERE attributes->>'backfill' = 'true';
```

**Alternative (if no marker):**
```sql
-- Delete only rows with backfill span_id pattern
DELETE FROM execution_messages WHERE span_id LIKE '%-backfill';
DELETE FROM executions WHERE span_id LIKE '%-backfill';
-- Keep traces (may have been created by OTLP)
```

---

#### Phase 4 Rollback (Drop Tables)

**Restore Table:**
```bash
cd server
export PATH="$HOME/.local/bin:$PATH" && uv run alembic downgrade -1
```

**Note:** This will **not** restore data, only the schema. If table is dropped prematurely, data is lost unless backed up.

**Recommendation:** Backup `execution_traces` table before Phase 4:
```bash
pg_dump -t execution_traces dakora_db > execution_traces_backup.sql
```

---

## Timeline & Dependencies

### Estimated Timeline

| Phase | Duration | Dependencies | Assignee |
|-------|----------|--------------|----------|
| Phase 0: Prepare | 1-2 days | None | TBD |
| Phase 1: Stop Writes | 2-3 days | Phase 0 complete | TBD |
| Phase 2: Replace Reads | 2-3 days | Phase 1 deployed | TBD |
| Phase 3: Backfill | 1-2 days | Phase 2 validated | TBD |
| Phase 4: Cleanup | 1 day | Phase 3 complete | TBD |
| **Total** | **7-11 days** | Sequential | - |

### Critical Path

```
Phase 0 (FK migration) → Phase 1 (stop writes) → Phase 2 (stop reads) → Phase 3 (backfill) → Phase 4 (drop)
```

**Blocking Dependencies:**

- Phase 1 **requires** Phase 0 FK migration (else template inserts fail)
- Phase 4 **requires** Phase 3 backfill (else historical data lost)
- Phases 1-2 can be combined if confident in testing

### Resource Requirements

- **Engineering Time:** 1 developer full-time for 2 weeks
- **QA Time:** 2-3 days for regression testing
- **DB Maintenance:** Minimal (backfill ~1 min for current volume)
- **Downtime:** Zero (phased rollout)

---

## Post-Deprecation Cleanup

### Optional Improvements (Phase 5)

After old schema is fully removed:

#### 5.1: Rename template_traces

**Change:** `template_traces` → `template_usages`

**Benefits:**
- Clearer naming (no longer tied to old "execution_traces")
- Consistent with new schema terminology

**Migration:**
```python
def upgrade():
    op.rename_table("template_traces", "template_usages")

def downgrade():
    op.rename_table("template_usages", "template_traces")
```

**Code Updates:** Replace all references to `template_traces_table`

---

#### 5.2: Add Indexes for Common Queries

**Suggested Indexes:**

```sql
-- Template analytics queries
CREATE INDEX idx_template_usages_prompt_trace 
ON template_usages (prompt_id, trace_id);

-- Execution filtering by status
CREATE INDEX idx_executions_status 
ON executions (status) 
WHERE status IS NOT NULL;

-- Message content search (if needed)
CREATE INDEX idx_execution_messages_content_gin 
ON execution_messages USING gin ((parts::text));
```

---

#### 5.3: Archive Old Backups

After 30 days of successful operation:

- [ ] Delete `execution_traces` table backup files
- [ ] Remove old schema documentation references
- [ ] Close related GitHub issues/tickets

---

## Testing

### Integration Test Coverage

**Required Tests (add to `server/tests/`):**

#### Test New Write Paths

```python
# tests/test_execution_traces_migration.py

@pytest.mark.integration
async def test_manual_execution_writes_to_new_schema(
    db_connection, test_project, test_prompt
):
    """Verify manual prompt execution writes to new schema only."""
    # Execute prompt via API
    response = await client.post(
        f"/api/projects/{test_project.id}/prompts/{test_prompt.id}/execute",
        json={"inputs": {"name": "Alice"}},
        headers={"X-API-Key": api_key}
    )
    
    trace_id = response.json()["trace_id"]
    
    # Assert trace exists in new schema
    trace = await db_connection.execute(
        select(traces_new_table).where(traces_new_table.c.trace_id == trace_id)
    )
    assert trace.fetchone() is not None
    
    # Assert execution exists
    execution = await db_connection.execute(
        select(executions_new_table).where(executions_new_table.c.trace_id == trace_id)
    )
    assert execution.fetchone() is not None
    
    # Assert messages exist
    messages = await db_connection.execute(
        select(execution_messages_new_table)
        .where(execution_messages_new_table.c.trace_id == trace_id)
    )
    assert len(messages.fetchall()) > 0
    
    # Assert NOT in old schema
    old_trace = await db_connection.execute(
        select(traces_table).where(traces_table.c.trace_id == trace_id)
    )
    assert old_trace.fetchone() is None  # Should not exist after Phase 1
```

#### Test Template Analytics

```python
@pytest.mark.integration
async def test_template_analytics_from_new_schema(db_connection, test_project, test_prompt):
    """Verify analytics queries work with new schema."""
    # Create test executions
    for i in range(3):
        await create_test_execution(
            db_connection,
            project_id=test_project.id,
            prompt_id=test_prompt.id,
            cost_usd=1.00,
            tokens_in=100,
            tokens_out=50,
        )
    
    # Fetch analytics
    response = await client.get(
        f"/api/projects/{test_project.id}/prompts/{test_prompt.id}/analytics"
    )
    
    analytics = response.json()
    assert analytics["total_executions"] == 3
    assert analytics["total_cost_usd"] == 3.00
    assert analytics["total_tokens_in"] == 300
    assert analytics["total_tokens_out"] == 150
```

#### Test FK Integrity

```python
@pytest.mark.integration
async def test_template_traces_fk_to_new_traces(db_connection, test_project):
    """Verify template_traces references traces.trace_id (not old table)."""
    trace_id = str(uuid.uuid4())
    
    # Insert into new traces table
    await db_connection.execute(
        traces_new_table.insert().values({
            "trace_id": trace_id,
            "project_id": test_project.id,
            "start_time": datetime.now(timezone.utc),
            "end_time": datetime.now(timezone.utc),
        })
    )
    
    # Insert into template_traces (should succeed)
    await db_connection.execute(
        template_traces_table.insert().values({
            "trace_id": trace_id,
            "prompt_id": "test-prompt",
            "version": "1.0.0",
        })
    )
    
    # Verify FK constraint
    template_trace = await db_connection.execute(
        select(template_traces_table).where(template_traces_table.c.trace_id == trace_id)
    )
    assert template_trace.fetchone() is not None
```

---

### Manual Testing Checklist

**UI Validation:**

- [ ] Navigate to project executions page
- [ ] Verify execution list loads (with new schema data)
- [ ] Click on execution detail
- [ ] Verify conversation history displays correctly
- [ ] Navigate to template analytics
- [ ] Verify metrics match expectations (compare to DB query)

**API Validation:**

```bash
# List executions
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/api/projects/$PROJECT_ID/executions"

# Get execution detail
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/api/projects/$PROJECT_ID/executions/$TRACE_ID"

# Get template analytics
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/api/projects/$PROJECT_ID/prompts/$PROMPT_ID/analytics"
```

---

## Success Criteria

### Overall Success Metrics

- [ ] **Zero data loss** - All historical executions queryable
- [ ] **Zero downtime** - No service interruptions during migration
- [ ] **Performance stable** - Execution list/detail latency ≤ baseline
- [ ] **Analytics accurate** - Template metrics match within 1% of old schema
- [ ] **Code quality** - No old schema references remaining
- [ ] **Test coverage** - All new paths covered by integration tests
- [ ] **Documentation** - Developer docs updated with new schema

### Phase-Specific Success Criteria

See each phase section for detailed criteria.

---

## Risks & Mitigations

### High-Risk Areas

| Risk | Impact | Mitigation |
|------|--------|------------|
| FK constraint violation during Phase 0 | **CRITICAL** - Blocks writes | Pre-backfill missing traces before FK migration |
| Data loss during backfill | **HIGH** - Historical data unrecoverable | Test on staging, backup old table before Phase 4 |
| Analytics query bugs | **MEDIUM** - Incorrect metrics displayed | Compare old vs new query results before removing fallback |
| Performance regression | **MEDIUM** - Slow execution pages | Benchmark queries, add indexes if needed |
| Incomplete fallback removal | **LOW** - Old schema still referenced | Grep codebase for `traces_table` references |

### Mitigation Strategies

1. **Comprehensive Testing:** Integration tests for all write/read paths
2. **Phased Rollout:** Deploy one phase at a time with validation
3. **Monitoring:** Track error rates, query latency, FK violations
4. **Rollback Plan:** Document rollback for each phase
5. **Backup:** Dump `execution_traces` table before Phase 4

---

## References

### Related Documentation

- [Database Migrations Guide](DATABASE_MIGRATIONS.md)
- [Testing Guide](testing-guide.md)
- [CLAUDE.md](../CLAUDE.md) - Database section

### Database Schema Files

- `server/dakora_server/core/database.py` - Table definitions
- `server/alembic/versions/` - Migration history

### API Endpoints

- `POST /api/projects/{id}/prompts/{id}/execute` - Manual execution
- `GET /api/projects/{id}/executions` - List executions
- `GET /api/projects/{id}/executions/{trace_id}` - Execution detail
- `GET /api/projects/{id}/prompts/{id}/analytics` - Template analytics

### Code Locations

See [Impact Analysis](#impact-analysis) table for full list.

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-04 | TBD | Initial deprecation plan created |

---

## Approval & Sign-Off

**Technical Review:** [ ] Pending
**QA Approval:** [ ] Pending
**Product Approval:** [ ] Pending

**Ready to Execute:** ☐ Yes  ☐ No

---

**End of Deprecation Plan**
