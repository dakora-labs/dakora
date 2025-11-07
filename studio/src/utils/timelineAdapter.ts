import type { TimelineEvent, Message } from '@/types';

/**
 * Convert normalized timeline events to MessageTimeline-compatible messages.
 * Ordering is preserved as provided by the backend timeline.
 */
export function timelineToMessages(timeline: TimelineEvent[]): Message[] {
  let idx = 0;
  const toJsonString = (v: unknown) => {
    if (typeof v === 'string') return v;
    try { return JSON.stringify(v); } catch { return String(v); }
  };

  const msgs: Message[] = [];
  for (const ev of timeline) {
    switch (ev.kind) {
      case 'user':
        msgs.push({
          role: (ev.role as any) || 'user',
          parts: [{ type: 'text', content: ev.text }],
          msg_index: idx++,
        });
        break;
      case 'assistant':
        msgs.push({
          role: 'assistant',
          parts: [{ type: 'text', content: ev.text }],
          msg_index: idx++,
          span_id: ev.span_id ?? null,
          span_type: 'chat',
          agent_name: ev.agent_name ?? null,
        });
        break;
      case 'tool': {
        // Composite tool event -> single message card with call + result parts
        const parts = [
          { type: 'tool_call', id: ev.tool_call_id, name: ev.name || 'tool', arguments: toJsonString(ev.arguments) },
        ] as any[];
        if (typeof (ev as any).output !== 'undefined') {
          parts.push({ type: 'tool_call_response', id: ev.tool_call_id, response: toJsonString((ev as any).output) });
        }
        msgs.push({
          role: 'tool',
          parts,
          msg_index: idx++,
          span_id: ev.span_id ?? null,
          span_type: 'tool',
        });
        break;
      }
      case 'tool_call':
        msgs.push({
          role: 'assistant',
          parts: [{ type: 'tool_call', id: ev.tool_call_id, name: ev.name || 'tool', arguments: toJsonString(ev.arguments) }],
          msg_index: idx++,
          span_id: ev.span_id ?? null,
          span_type: 'tool',
        });
        break;
      case 'tool_result':
        msgs.push({
          role: 'tool',
          parts: [{ type: 'tool_call_response', id: ev.tool_call_id, response: toJsonString(ev.output) }],
          msg_index: idx++,
          span_id: ev.span_id ?? null,
          span_type: 'tool',
        });
        break;
      default:
        break;
    }
  }
  return msgs;
}
