# Dakora Agents - OTEL Refactoring Plan

## Overview

Refactor `dakora-agents` to leverage Microsoft Agent Framework's built-in OpenTelemetry support instead of custom tracing logic.

**Key Principle:** Use OTEL for everything except Dakora's unique features:
1. Budget enforcement
2. Template linkage
3. Project-scoped API key context

## Current State

**Current Implementation:**
- ~600 lines of custom tracing code
- Manual trace creation/completion
- Duplicates what MAF already provides via OTEL
- Complex async handling

**What MAF OTEL Already Provides:**
- ✅ Agent ID tracking (`gen_ai.agent.id`)
- ✅ Token tracking (`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`)
- ✅ Message capture (`gen_ai.input.messages`, `gen_ai.output.messages`)
- ✅ Provider/model tracking
- ✅ Latency tracking
- ✅ Parent/child span relationships (multi-agent)
- ✅ Tool call tracking

## Target State

**New Implementation:**
- ~280 lines of focused code
- Leverage OTEL infrastructure
- Keep budget enforcement
- Keep template linkage
- Compatible with OTEL ecosystem (Jaeger, Grafana, etc.)

## Architecture

### 3 Core Components

#### 1. DakoraTraceMiddleware (~80 lines)
**Purpose:** Budget enforcement + project context

```python
class DakoraTraceMiddleware(ChatMiddleware):
    def __init__(self, dakora_client: Dakora, budget_check_cache_ttl: int = 30):
        self.dakora = dakora_client
        self._project_id = None  # Lazy-loaded from API key
        self._budget_cache = None
        self._budget_cache_time = None
        self.budget_check_cache_ttl = budget_check_cache_ttl

    async def process(self, context, next):
        # 1. Get project_id from API key context (cached)
        project_id = await self._get_project_id()

        # 2. Check budget BEFORE execution (blocking if exceeded)
        if project_id:
            budget_status = await self._check_budget_with_cache(project_id)

            if budget_status.get("exceeded") and budget_status.get("enforcement_mode") == "strict":
                context.terminate = True
                context.result = self._format_budget_error(budget_status)
                return  # Block execution

        # 3. Add project_id to current OTEL span
        span = trace.get_current_span()
        if span.is_recording() and project_id:
            span.set_attribute("dakora.project_id", project_id)

        # 4. Execute (MAF + OTEL handle the rest)
        await next(context)
```

**Responsibilities:**
- Fetch project_id from `/api/me/context`
- Check budget with TTL caching
- Block execution if budget exceeded (strict mode)
- Add project_id to OTEL span

**What it NO LONGER does:**
- ❌ Manual trace creation
- ❌ Token tracking (OTEL does it)
- ❌ Agent ID tracking (OTEL does it)
- ❌ Conversation history building (OTEL does it)
- ❌ Session management (removed - app-specific)

#### 2. DakoraSpanExporter (~150 lines)
**Purpose:** Transform OTEL spans → Dakora API format

```python
class DakoraSpanExporter(SpanExporter):
    def __init__(self, dakora_client: Dakora):
        self.dakora = dakora_client

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            for span in spans:
                # Only export agent invocation spans
                if self._is_agent_span(span):
                    await self._export_to_dakora(span)
            return SpanExportResult.SUCCESS
        except Exception as e:
            logger.error(f"Failed to export spans: {e}")
            return SpanExportResult.FAILURE

    def _is_agent_span(self, span: ReadableSpan) -> bool:
        attrs = span.attributes or {}
        return attrs.get("gen_ai.operation.name") == "invoke_agent"

    async def _export_to_dakora(self, span: ReadableSpan):
        attrs = span.attributes or {}

        # Map OTEL span → Dakora API format
        payload = {
            "project_id": attrs.get("dakora.project_id"),
            "trace_id": format_trace_id(span.context.trace_id),
            "parent_trace_id": format_span_id(span.parent.span_id) if span.parent else None,
            "agent_id": attrs.get("gen_ai.agent.id"),
            "source": attrs.get("dakora.source", "maf"),
            "provider": attrs.get("gen_ai.provider.name"),
            "model": attrs.get("llm.request.model"),
            "tokens_in": attrs.get("gen_ai.usage.input_tokens"),
            "tokens_out": attrs.get("gen_ai.usage.output_tokens"),
            "latency_ms": int((span.end_time - span.start_time) / 1e6),  # ns → ms
            "conversation_history": self._extract_conversation_history(span),
            "template_usages": self._extract_template_usages(span),
            "metadata": self._extract_metadata(attrs),
        }

        # Send to Dakora API
        await self.dakora.traces.create(**payload)

    def _extract_template_usages(self, span: ReadableSpan) -> list:
        """Extract template linkage from message events"""
        template_usages = []

        for event in span.events:
            if event.name in ["gen_ai.user.message", "gen_ai.assistant.message"]:
                # Check if message has _dakora_context
                dakora_ctx = event.attributes.get("dakora_template")
                if dakora_ctx:
                    template_usages.append({
                        "prompt_id": dakora_ctx["prompt_id"],
                        "version": dakora_ctx["version"],
                        "inputs": dakora_ctx["inputs"],
                        "metadata": dakora_ctx.get("metadata", {}),
                        "role": event.attributes.get("role"),
                        "source": "message",
                        "message_index": len(template_usages),
                    })

        return template_usages or None

    def _extract_conversation_history(self, span: ReadableSpan) -> list:
        """Extract conversation from span events"""
        # Parse gen_ai.input.messages and gen_ai.output.messages
        # from span attributes or events
        ...
```

**Responsibilities:**
- Filter for agent invocation spans only
- Map OTEL span attributes → Dakora API format
- Extract template linkage from message events
- Extract conversation history
- Send to Dakora API asynchronously

#### 3. DakoraIntegration Helper (~50 lines)
**Purpose:** Simple setup for users

```python
class DakoraIntegration:
    """One-line setup for Dakora OTEL integration"""

    @staticmethod
    def setup(
        dakora_client: Dakora,
        enable_sensitive_data: bool = True,
        budget_check_cache_ttl: int = 30,
        additional_exporters: list | None = None,
    ) -> DakoraTraceMiddleware:
        """
        Setup OTEL with Dakora integration.

        Args:
            dakora_client: Dakora client instance
            enable_sensitive_data: Capture messages and prompts in OTEL
            budget_check_cache_ttl: Budget check cache TTL in seconds
            additional_exporters: Optional OTEL exporters (Jaeger, etc.)

        Returns:
            DakoraTraceMiddleware instance to add to chat client

        Example:
            >>> dakora = Dakora(api_key="dk_proj_...")
            >>> middleware = DakoraIntegration.setup(dakora)
            >>>
            >>> azure_client = AzureOpenAIChatClient(
            ...     ...,
            ...     middleware=[middleware]
            ... )
        """
        from agent_framework import setup_observability

        exporters = [DakoraSpanExporter(dakora_client)]
        if additional_exporters:
            exporters.extend(additional_exporters)

        # Setup OTEL with Dakora exporter
        setup_observability(
            enable_sensitive_data=enable_sensitive_data,
            exporters=exporters,
        )

        # Return middleware instance
        return DakoraTraceMiddleware(
            dakora_client=dakora_client,
            budget_check_cache_ttl=budget_check_cache_ttl,
        )
```

## User Experience

### Before (Current)

```python
from dakora_client import Dakora
from dakora_agents.maf import create_dakora_middleware

dakora = Dakora(api_key="dk_proj_...")

middleware = create_dakora_middleware(
    dakora_client=dakora,
    session_id="session-123",  # Manual session management
    instruction_template=...,  # Manual template setup
    budget_check_cache_ttl=30,
)

azure_client = AzureOpenAIChatClient(
    ...,
    middleware=[middleware]
)
```

### After (OTEL)

```python
from dakora_client import Dakora
from dakora_agents.maf import DakoraIntegration
from agent_framework.azure import AzureOpenAIChatClient

# 1. Initialize Dakora
dakora = Dakora(api_key="dk_proj_...")

# 2. One-line OTEL setup
middleware = DakoraIntegration.setup(dakora)

# 3. Use with any MAF client
azure_client = AzureOpenAIChatClient(
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    middleware=[middleware],
)

# 4. Templates auto-link via to_message()
greeting = await dakora.prompts.render("greeting", {"name": "Alice"})
agent = azure_client.create_agent(
    id="chat-v1",
    name="ChatBot",
    instructions=greeting.text,
)

# 5. Run agent - everything auto-tracked!
response = await agent.run(greeting.to_message())

# Automatic:
# - Budget checking (before execution)
# - Template linkage (via _dakora_context)
# - Agent ID tracking (via OTEL)
# - Token tracking (via OTEL)
# - Conversation history (via OTEL)
# - Export to Dakora API (via OTEL exporter)
```

## Template Linkage

**Current Approach (KEEP THIS):**

```python
# dakora_client/types.py - RenderResult.to_message()
def to_message(self, role: str = "user") -> ChatMessage:
    msg = ChatMessage(role=role_enum, text=self.text)

    # Attach Dakora context as private attribute
    msg._dakora_context = {
        "prompt_id": self.prompt_id,
        "version": self.version,
        "inputs": self.inputs,
        "metadata": self.metadata,
    }

    return msg
```

**How it Works with OTEL:**

1. User renders template and creates message:
   ```python
   result = await dakora.prompts.render("greeting", {"name": "Alice"})
   msg = result.to_message()  # Has _dakora_context
   ```

2. MAF's OTEL captures message in span events:
   ```python
   # MAF automatically adds event
   span.add_event(
       "gen_ai.user.message",
       attributes={
           "role": "user",
           "content": msg.text,
           "dakora_template": msg._dakora_context,  # Preserved!
       }
   )
   ```

3. DakoraSpanExporter extracts from events:
   ```python
   def _extract_template_usages(self, span):
       for event in span.events:
           if dakora_ctx := event.attributes.get("dakora_template"):
               template_usages.append({
                   "prompt_id": dakora_ctx["prompt_id"],
                   "version": dakora_ctx["version"],
                   ...
               })
   ```

**No changes needed to template linkage!**

## API Changes

**NONE.** Your existing API is already OTEL-compatible:

```python
# Current API format (unchanged)
POST /api/projects/{project_id}/executions
{
  "trace_id": str,           # OTEL trace_id
  "parent_trace_id": str,    # OTEL parent span
  "agent_id": str,           # gen_ai.agent.id
  "source": str,             # "maf"
  "provider": str,           # gen_ai.provider.name
  "model": str,              # llm.request.model
  "tokens_in": int,          # gen_ai.usage.input_tokens
  "tokens_out": int,         # gen_ai.usage.output_tokens
  "latency_ms": int,         # span duration
  "conversation_history": list,
  "template_usages": list,
  "metadata": dict
}
```

The exporter handles the mapping.

## Session Support (Optional)

Session tracking is **removed** from core middleware (app-specific).

If users want session tracking, they can add it manually:

```python
from opentelemetry import trace

@app.post("/chat")
async def chat(msg: str, session_id: str):
    # Optional: Add session to OTEL span
    span = trace.get_current_span()
    span.set_attribute("dakora.session_id", session_id)

    # Use agent normally
    agent = azure_client.create_agent(...)
    return await agent.run(msg)
```

Your API already supports optional `session_id` field.

## Implementation Timeline

### Day 1: Refactor Middleware
- Strip out manual trace creation/completion
- Keep budget checking logic
- Keep project_id resolution
- Add OTEL span attribute for project_id
- Remove session management

**Files:**
- `middleware.py` - Simplify from 600 → 80 lines

### Day 2: Implement OTEL Exporter
- Create `DakoraSpanExporter` class
- Implement span filtering (agent spans only)
- Map OTEL attributes → Dakora API format
- Extract template linkage from events
- Extract conversation history from events
- Handle async API calls

**Files:**
- `exporter.py` - NEW, ~150 lines

### Day 3: Setup Helper + Testing
- Create `DakoraIntegration` helper class
- Update `__init__.py` exports
- Update examples and documentation
- Test budget enforcement
- Test template linkage
- Test multi-agent scenarios

**Files:**
- `__init__.py` - Add integration helper
- `README.md` - Update examples
- Tests

## File Structure

```
packages/agents/dakora_agents/
├── __init__.py                    # Export DakoraIntegration
├── maf/
│   ├── __init__.py                # Export middleware, exporter, integration
│   ├── middleware.py              # REFACTORED - 80 lines (was 600)
│   ├── exporter.py                # NEW - 150 lines
│   ├── integration.py             # NEW - 50 lines (setup helper)
│   ├── helpers.py                 # UNCHANGED (to_message, etc.)
│   └── __init__.py
```

## Benefits

### Code Quality
- ✅ **50% less code** (600 → 280 lines)
- ✅ **Simpler logic** (OTEL handles complexity)
- ✅ **Battle-tested** (OTEL is production-proven)
- ✅ **Maintainable** (focused on unique features)

### Features
- ✅ **Budget enforcement** (unique value preserved)
- ✅ **Template linkage** (unique value preserved)
- ✅ **Project context** (from API keys)
- ✅ **Multi-agent support** (automatic via OTEL)
- ✅ **OTEL ecosystem** (Jaeger, Grafana, etc.)

### Developer Experience
- ✅ **One-line setup** (`DakoraIntegration.setup(dakora)`)
- ✅ **Auto-tracking** (zero boilerplate in endpoints)
- ✅ **Flexible** (optional session support)
- ✅ **Compatible** (works with all MAF clients)

## Migration Guide (for existing users)

### Breaking Changes
- `session_id` parameter removed from middleware (now optional)
- `instruction_template` parameter removed (use `to_message()` instead)
- `create_dakora_middleware()` replaced with `DakoraIntegration.setup()`

### Migration Steps

**Before:**
```python
middleware = create_dakora_middleware(
    dakora_client=dakora,
    session_id="session-123",
    instruction_template=template_dict,
)
```

**After:**
```python
# Just use the integration helper
middleware = DakoraIntegration.setup(dakora)

# Templates now use to_message()
template = await dakora.prompts.render("greeting", {...})
agent = client.create_agent(instructions=template.text)
await agent.run(template.to_message())
```

## Success Criteria

- ✅ Budget enforcement still works (strict + alert modes)
- ✅ Template linkage preserved in API
- ✅ Agent ID tracking automatic
- ✅ Token/cost tracking automatic
- ✅ Multi-agent scenarios work
- ✅ Code reduced by 50%+
- ✅ Setup is one-line
- ✅ Compatible with OTEL ecosystem