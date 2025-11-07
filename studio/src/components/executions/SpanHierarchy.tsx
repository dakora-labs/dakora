import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { SpanTreeNode } from '@/types';
import { ChevronRight, Activity, Clock, Zap } from 'lucide-react';
import { formatNumber, parseApiDate, formatRelativeTime } from '@/utils/format';
import { cn } from '@/lib/utils';

interface SpanHierarchyProps {
  spans: SpanTreeNode[];
  onSpanClick?: (spanId: string) => void;
}

const getSpanTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    agent: 'bg-blue-50 text-blue-700 border-blue-200',
    chat: 'bg-purple-50 text-purple-700 border-purple-200',
    tool: 'bg-orange-50 text-orange-700 border-orange-200',
    llm: 'bg-green-50 text-green-700 border-green-200',
    message_send: 'bg-pink-50 text-pink-700 border-pink-200',
    executor_process: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    edge_group_process: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    workflow_run: 'bg-violet-50 text-violet-700 border-violet-200',
    workflow_build: 'bg-amber-50 text-amber-700 border-amber-200',
  };
  return colors[type] ?? 'bg-gray-50 text-gray-700 border-gray-200';
};

export function SpanHierarchy({ spans, onSpanClick }: SpanHierarchyProps) {
  if (spans.length === 0) {
    return (
      <Card className="p-5 border-border/80">
        <div className="text-center text-sm text-muted-foreground py-8">
          No span hierarchy available
        </div>
      </Card>
    );
  }

  // Calculate total tokens and latency
  const totalTokens = spans.reduce(
    (sum, span) => sum + (span.tokens_in ?? 0) + (span.tokens_out ?? 0),
    0
  );
  const totalLatency = spans.reduce(
    (sum, span) => sum + (span.latency_ms ?? 0),
    0
  );

  return (
    <Card className="p-5 border-border/80">
      <div className="flex items-center justify-between mb-5 pb-4 border-b border-border/60">
        <div>
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Activity className="w-5 h-5 text-muted-foreground" />
            Execution Hierarchy
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            Trace with {spans.length} span{spans.length === 1 ? '' : 's'}
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1">
            <Zap className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="font-mono">{formatNumber(totalTokens)} tokens</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="font-mono">{totalLatency}ms</span>
          </div>
        </div>
      </div>

      <div className="space-y-1">
        {spans.map((span) => {
          const isClickable = !!onSpanClick;
          const tokens = (span.tokens_in ?? 0) + (span.tokens_out ?? 0);
          const hasTokens = tokens > 0;
          const hasLatency = span.latency_ms !== null && span.latency_ms > 0;
          const startTime = span.start_time ? parseApiDate(span.start_time) : null;

          return (
            <div
              key={span.span_id}
              className={cn(
                'group relative flex items-center gap-2 py-2 px-3 rounded-md border',
                'transition-colors hover:bg-muted/50',
                isClickable && 'cursor-pointer'
              )}
              onClick={() => isClickable && onSpanClick(span.span_id)}
              style={{ paddingLeft: `${12 + span.depth * 24}px` }}
            >
              {/* Depth indicator */}
              {span.depth > 0 && (
                <div className="absolute left-3" style={{ left: `${12 + (span.depth - 1) * 24}px` }}>
                  <ChevronRight className="w-3 h-3 text-muted-foreground/40" />
                </div>
              )}

              {/* Span type badge */}
              <Badge 
                variant="outline" 
                className={cn('text-xs font-medium', getSpanTypeColor(span.type))}
              >
                {span.type}
              </Badge>

              {/* Span name/agent */}
              <span className="text-sm font-medium flex-1 min-w-0">
                {span.agent_name ?? 'Unnamed'}
              </span>

              {/* Metrics */}
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                {hasTokens && (
                  <div className="flex items-center gap-1">
                    <Zap className="w-3 h-3" />
                    <span className="font-mono">{formatNumber(tokens)}</span>
                  </div>
                )}
                
                {hasLatency && (
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span className="font-mono">{span.latency_ms}ms</span>
                  </div>
                )}

                {startTime && (
                  <span className="text-muted-foreground/60">
                    {formatRelativeTime(span.start_time)}
                  </span>
                )}
              </div>

              {/* Span ID (on hover) */}
              <code className="opacity-0 group-hover:opacity-100 transition-opacity text-[10px] font-mono text-muted-foreground/60 truncate max-w-[100px]">
                {span.span_id.slice(0, 8)}
              </code>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-5 pt-4 border-t border-border/60">
        <p className="text-xs text-muted-foreground mb-2 font-medium">Span Types:</p>
        <div className="flex flex-wrap gap-2">
          {['agent', 'chat', 'tool', 'llm', 'workflow_run'].map((type) => (
            <Badge 
              key={type} 
              variant="outline" 
              className={cn('text-xs', getSpanTypeColor(type))}
            >
              {type}
            </Badge>
          ))}
        </div>
      </div>
    </Card>
  );
}
