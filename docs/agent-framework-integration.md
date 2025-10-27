# Agent Framework Integration: Implementation Spec

**Status**: Draft
**Date**: 2025-01-25

---

## Overview

Integration between Dakora and Microsoft Agent Framework (AF) via ChatMiddleware to provide:

1. Automatic observability (cost, latency, tokens, conversation history)
2. Optional template usage tracking (link Dakora templates to executions)
3. Minimal code changes (middleware pattern, no AF wrapper)

**Key Principle**: Progressive adoption - start with observability only, add template management optionally.

---

## Architecture

```
AF Agent → DakoraTraceMiddleware → Dakora API → Studio
              ↓ (reads metadata)
         RenderResult.as_message() (optional)
```

**Components:**
- **DakoraTraceMiddleware** - ChatMiddleware that logs executions
- **RenderResult** - Enhanced return type with `.as_message()` helper
- **ExecutionsAPI** - New dakora-client endpoints
- **template_executions** table - Links templates to executions

---

## Database Schema

### Update `logs` Table

```python
# In server/dakora_server/core/database.py

logs_table = Table(
    "logs",
    metadata,
    # Existing columns...
    Column("prompt_id", String(255)),
    Column("version", String(50)),
    Column("inputs_json", Text),
    Column("output_text", Text),
    Column("provider", String(50)),
    Column("model", String(100)),
    Column("tokens_in", Integer),
    Column("tokens_out", Integer),
    Column("cost_usd", Float),
    Column("latency_ms", Integer),
    Column("created_at", DateTime, server_default=text("NOW()")),

    # NEW: Tracing columns
    Column("trace_id", String(255), unique=True, index=True),
    Column("session_id", String(255), index=True),
    Column("agent_id", String(255), index=True),
    Column("conversation_history", JSONB),
    Column("metadata", JSONB),
)
```

### Add `template_executions` Table

```python
template_executions_table = Table(
    "template_executions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("trace_id", String(255), ForeignKey("logs.trace_id", ondelete="CASCADE"), index=True),
    Column("prompt_id", String(255), nullable=False, index=True),
    Column("version", String(50), nullable=False),
    Column("inputs_json", JSONB),
    Column("position", Integer),  # Order in conversation
    Column("created_at", DateTime, server_default=text("NOW()")),
)
```

---

## Client SDK Changes

### 1. RenderResult Class

```python
# In packages/client-python/dakora_client/types.py

from dataclasses import dataclass, field
from typing import Any

@dataclass
class RenderResult:
    """Template render result with execution tracking"""
    text: str
    prompt_id: str
    version: str
    inputs: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Allow using as string"""
        return self.text

    def as_message(self, role):
        """Create AF ChatMessage with template metadata attached"""
        from agent_framework import ChatMessage

        message = ChatMessage(role=role, text=self.text)

        # Store in AF's native additional_properties
        message.additional_properties.update({
            "dakora_prompt_id": self.prompt_id,
            "dakora_version": self.version,
            "dakora_inputs": self.inputs,
            "dakora_metadata": self.metadata,
        })

        return message
```

### 2. Update PromptsAPI

```python
# In packages/client-python/dakora_client/prompts.py

class PromptsAPI:
    async def render(
        self,
        template_id: str,
        inputs: dict[str, Any],
        version: str | None = None,
    ) -> RenderResult:
        response = await self.client._request(
            "POST",
            f"/api/prompts/{template_id}/render",
            json={"inputs": inputs, "version": version},
        )

        return RenderResult(
            text=response["rendered"],
            prompt_id=template_id,
            version=response["version"],
            inputs=inputs,
        )
```

### 3. ExecutionsAPI

```python
# In packages/client-python/dakora_client/executions.py

class ExecutionsAPI:
    def __init__(self, client: "Dakora"):
        self.client = client

    async def create(
        self,
        project_id: str,
        trace_id: str,
        session_id: str,
        agent_id: str | None = None,
        template_usages: list[dict] | None = None,
        conversation_history: list[dict] | None = None,
        **kwargs,  # provider, model, tokens_in, tokens_out, latency_ms, cost_usd
    ) -> dict:
        return await self.client._request(
            "POST",
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_id,
                "session_id": session_id,
                "agent_id": agent_id,
                "template_usages": template_usages,
                "conversation_history": conversation_history,
                **kwargs,
            },
        )

    async def list(self, project_id: str, **filters) -> list[dict]:
        return await self.client._request(
            "GET",
            f"/api/projects/{project_id}/executions",
            params=filters,
        )

    async def get(self, project_id: str, trace_id: str) -> dict:
        return await self.client._request(
            "GET",
            f"/api/projects/{project_id}/executions/{trace_id}",
        )

# In packages/client-python/dakora_client/client.py
class Dakora:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.prompts = PromptsAPI(self)
        self.executions = ExecutionsAPI(self)  # NEW
```

---

## Server API

```python
# In server/dakora_server/api/project_executions.py (NEW)

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import insert, select
from ..core.database import logs_table, template_executions_table

router = APIRouter()

class ExecutionCreate(BaseModel):
    trace_id: str
    session_id: str
    agent_id: str | None = None
    template_usages: list[dict] | None = None
    conversation_history: list[dict] | None = None
    provider: str | None = None
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None
    metadata: dict | None = None

@router.post("/api/projects/{project_id}/executions")
async def create_execution(
    project_id: str,
    body: ExecutionCreate,
    db=Depends(get_connection),
    auth=Depends(validate_project_access),
):
    # Insert execution log
    log_stmt = insert(logs_table).values(
        trace_id=body.trace_id,
        session_id=body.session_id,
        agent_id=body.agent_id,
        conversation_history=body.conversation_history,
        metadata=body.metadata,
        provider=body.provider,
        model=body.model,
        tokens_in=body.tokens_in,
        tokens_out=body.tokens_out,
        latency_ms=body.latency_ms,
        cost_usd=body.cost_usd,
    )
    db.execute(log_stmt)

    # Insert template linkage
    if body.template_usages:
        for idx, usage in enumerate(body.template_usages):
            template_stmt = insert(template_executions_table).values(
                trace_id=body.trace_id,
                prompt_id=usage["prompt_id"],
                version=usage["version"],
                inputs_json=usage["inputs"],
                position=idx,
            )
            db.execute(template_stmt)

    db.commit()
    return {"trace_id": body.trace_id}

@router.get("/api/projects/{project_id}/executions")
async def list_executions(
    project_id: str,
    session_id: str | None = None,
    agent_id: str | None = None,
    limit: int = 100,
    db=Depends(get_connection),
    auth=Depends(validate_project_access),
):
    query = select(logs_table).order_by(logs_table.c.created_at.desc())
    if session_id:
        query = query.where(logs_table.c.session_id == session_id)
    if agent_id:
        query = query.where(logs_table.c.agent_id == agent_id)
    query = query.limit(limit)

    results = db.execute(query).fetchall()
    return [dict(row._mapping) for row in results]

@router.get("/api/projects/{project_id}/prompts/{prompt_id}/analytics")
async def get_template_analytics(
    project_id: str,
    prompt_id: str,
    db=Depends(get_connection),
    auth=Depends(validate_project_access),
):
    # Join logs + template_executions to get stats
    stmt = (
        select(
            logs_table.c.trace_id,
            logs_table.c.session_id,
            logs_table.c.created_at,
            logs_table.c.latency_ms,
            logs_table.c.cost_usd,
            template_executions_table.c.version,
        )
        .select_from(
            logs_table.join(
                template_executions_table,
                logs_table.c.trace_id == template_executions_table.c.trace_id,
            )
        )
        .where(template_executions_table.c.prompt_id == prompt_id)
        .order_by(logs_table.c.created_at.desc())
    )

    results = db.execute(stmt).fetchall()

    return {
        "prompt_id": prompt_id,
        "total_executions": len(results),
        "unique_sessions": len(set(r.session_id for r in results)),
        "total_cost_usd": sum(r.cost_usd or 0 for r in results),
        "avg_latency_ms": sum(r.latency_ms or 0 for r in results) / len(results) if results else 0,
        "executions": [dict(r._mapping) for r in results[:100]],
    }
```

---

## Middleware Implementation

```python
# In packages/dakora-af/dakora_af/middleware.py

from agent_framework import ChatMiddleware, ChatContext
from dakora_client import Dakora
import uuid
import time

class DakoraTraceMiddleware(ChatMiddleware):
    def __init__(
        self,
        dakora_client: Dakora,
        project_id: str,
        agent_id: str | None = None,
        session_id: str | None = None,
    ):
        self.dakora = dakora_client
        self.project_id = project_id
        self.agent_id = agent_id
        self.session_id = session_id or str(uuid.uuid4())

    async def process(self, context: ChatContext, next):
        trace_id = str(uuid.uuid4())
        start_time = time.time()

        # Extract template metadata from messages
        template_usages = []
        for msg in context.messages:
            if "dakora_prompt_id" in msg.additional_properties:
                template_usages.append({
                    "prompt_id": msg.additional_properties["dakora_prompt_id"],
                    "version": msg.additional_properties["dakora_version"],
                    "inputs": msg.additional_properties["dakora_inputs"],
                })

        # Execute LLM call
        await next(context)

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract conversation and usage
        conversation_history = [
            {"role": msg.role.value, "content": msg.text or str(msg.contents)}
            for msg in context.messages
        ]

        usage = getattr(context.result, "usage", {}) if context.result else {}

        # Log to Dakora (async, non-blocking)
        try:
            await self.dakora.executions.create(
                project_id=self.project_id,
                trace_id=trace_id,
                session_id=self.session_id,
                agent_id=self.agent_id,
                template_usages=template_usages or None,
                conversation_history=conversation_history,
                provider=context.chat_options.model_id.split("/")[0],
                model=context.chat_options.model_id,
                latency_ms=latency_ms,
                tokens_in=usage.get("input_tokens") or usage.get("prompt_tokens"),
                tokens_out=usage.get("output_tokens") or usage.get("completion_tokens"),
            )
        except Exception as e:
            # Don't fail request if logging fails
            print(f"[Dakora] Failed to log: {e}")
```

---

## Usage Examples

### Observability Only (No Templates)

```python
from dakora_client import Dakora
from dakora_af import DakoraTraceMiddleware

dakora = Dakora("https://api.dakora.io", api_key="dk_xxx")

agent = await AzureAIAgentClient().create_agent(
    name="Support",
    middleware=DakoraTraceMiddleware(dakora, project_id="support-bot"),
)

# Use AF normally - automatic tracking
await agent.run("I need help")
```

### With Template Management

```python
# Render template
greeting = await dakora.prompts.render(
    "customer-greeting",
    {"name": "Alice", "tier": "premium"},
)

# Use .as_message() to attach metadata
await agent.run([
    greeting.as_message(Role.SYSTEM),
    ChatMessage(role=Role.USER, text="I need help"),
])

# ✅ Dakora Studio shows:
# - Execution cost/latency/tokens
# - Template "customer-greeting" was used
# - Inputs: {"name": "Alice", "tier": "premium"}
```

---

## Implementation Phases

**Phase 1: Core Infrastructure**
- Database migrations (logs + template_executions tables)
- Server API endpoints (/executions)
- Update dakora-client SDK (RenderResult, ExecutionsAPI)

**Phase 2: AF Integration**
- Create dakora-af package
- Implement DakoraTraceMiddleware
- Write integration tests
- Publish to PyPI

**Phase 3: Studio UI**
- Executions list page
- Session detail view with conversation history
- Template analytics page
- Add usage metrics to template list

**Phase 4: Documentation**
- Integration guide
- Migration guide (hardcoded prompts → Dakora)
- Code examples

---

## Migration Path

1. **Start with observability** - Just add middleware, no code changes
2. **Migrate high-value prompts** - Complex/changing prompts to Dakora templates
3. **Keep simple prompts in code** - Not all-or-nothing
4. **Full adoption** - All prompts managed in Dakora Studio

**Progressive, not disruptive.**