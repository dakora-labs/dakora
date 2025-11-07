import { describe, it, expect } from 'vitest';
import { timelineToMessages } from './timelineAdapter';
import type { TimelineEvent } from '@/types';

describe('timelineToMessages', () => {
  it('orders user inputs before assistant outputs and preserves order', () => {
    const timeline: TimelineEvent[] = [
      { kind: 'user', ts: '2025-11-04T21:49:18.907Z', text: 'Hello' },
      { kind: 'assistant', ts: '2025-11-04T21:49:19.000Z', text: 'Hi!', span_id: 's1', agent_name: 'A' },
      { kind: 'user', ts: '2025-11-04T21:49:20.000Z', text: 'Tell me about Python' },
      { kind: 'assistant', ts: '2025-11-04T21:49:22.000Z', text: 'Python is great', span_id: 's1', agent_name: 'A' },
    ];
    const msgs = timelineToMessages(timeline);
    expect(msgs.map((m) => m.role)).toEqual(['user', 'assistant', 'user', 'assistant']);
    expect(msgs[0].parts[0].content).toBe('Hello');
    expect(msgs[3].parts[0].content).toBe('Python is great');
  });

  it('represents tool calls and results as tool_call and tool_call_response parts', () => {
    const timeline: TimelineEvent[] = [
      { kind: 'user', ts: 't0', text: 'Search web' },
      { kind: 'tool_call', ts: 't1', tool_call_id: 'call1', name: 'search', arguments: { q: 'python' }, span_id: 's1' },
      { kind: 'tool_result', ts: 't2', tool_call_id: 'call1', output: { items: 3 }, span_id: 's1' },
      { kind: 'assistant', ts: 't3', text: 'Found results', span_id: 's1', agent_name: 'A' },
    ];
    const msgs = timelineToMessages(timeline);
    expect(msgs[1].parts[0].type).toBe('tool_call');
    expect(msgs[2].role).toBe('tool');
    expect(msgs[2].parts[0].type).toBe('tool_call_response');
  });

  it('supports composite tool events (single message with call+result)', () => {
    const timeline: TimelineEvent[] = [
      { kind: 'user', ts: 't0', text: 'Weather?' },
      { kind: 'tool', ts: 't2', tool_call_id: 'call1', name: 'get_weather', arguments: { city: 'Seattle' }, output: { text: 'Sunny' }, span_id: 's1' },
      { kind: 'assistant', ts: 't3', text: 'It is sunny', span_id: 's1', agent_name: 'A' },
    ];
    const msgs = timelineToMessages(timeline);
    expect(msgs.length).toBe(3);
    expect(msgs[1].role).toBe('tool');
    expect(msgs[1].parts[0].type).toBe('tool_call');
    expect(msgs[1].parts[1].type).toBe('tool_call_response');
  });

  it('handles tool-only timelines (no assistant text)', () => {
    const timeline: TimelineEvent[] = [
      { kind: 'user', ts: 't0', text: 'Do thing' },
      { kind: 'tool_call', ts: 't1', tool_call_id: 'c1', name: 'run', arguments: { x: 1 }, span_id: 'sX' },
      { kind: 'tool_result', ts: 't2', tool_call_id: 'c1', output: { ok: true }, span_id: 'sX' },
    ];
    const msgs = timelineToMessages(timeline);
    expect(msgs.map((m) => m.role)).toEqual(['user', 'assistant', 'tool']);
    expect(msgs[1].parts[0].type).toBe('tool_call');
    expect(msgs[2].parts[0].type).toBe('tool_call_response');
  });

  it('preserves order with interleaved agents across lanes', () => {
    const timeline: TimelineEvent[] = [
      { kind: 'user', ts: 't0', text: 'Start' },
      { kind: 'assistant', ts: 't1', text: 'Agent A says hi', span_id: 'a1', agent_name: 'A' },
      { kind: 'assistant', ts: 't2', text: 'Agent B responds', span_id: 'b1', agent_name: 'B' },
      { kind: 'assistant', ts: 't3', text: 'Agent A again', span_id: 'a1', agent_name: 'A' },
    ];
    const msgs = timelineToMessages(timeline);
    expect(msgs.map((m) => (m.agent_name ?? null))).toEqual([null, 'A', 'B', 'A']);
    expect(msgs[2].parts[0].content).toBe('Agent B responds');
  });
});
