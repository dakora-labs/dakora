import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, GitBranch, Link2, Users } from 'lucide-react';
import type { RelatedTracesResponse } from '@/types';
import { formatTimestamp } from '@/utils/format';

interface RelatedTracesPanelProps {
  related: RelatedTracesResponse;
  currentTraceId: string;
  onNavigate: (traceId: string) => void;
}

export function RelatedTracesPanel({ related, currentTraceId, onNavigate }: RelatedTracesPanelProps) {
  const hasRelations = 
    related.parent || 
    related.children.length > 0 || 
    related.siblings.length > 0;

  const hasMultipleAgents = related.session_agents.length > 1;

  if (!hasRelations && !hasMultipleAgents) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Multi-Agent Session Indicator */}
      {hasMultipleAgents && (
        <Card className="p-4 border-purple-200 bg-purple-50/50">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
              <Users className="w-5 h-5 text-purple-600" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-purple-900 mb-1">
                Multi-Agent Session
              </h3>
              <p className="text-xs text-purple-700 mb-3">
                This trace is part of a collaborative session with {related.session_agents.length} agents
              </p>
              <div className="flex flex-wrap gap-2">
                {related.session_agents.map((agent) => (
                  <Badge 
                    key={agent.agent_id} 
                    variant="secondary"
                    className="bg-purple-100 text-purple-700 border-purple-200"
                  >
                    {agent.agent_id}
                    <span className="ml-1 text-purple-500">×{agent.trace_count}</span>
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Trace Hierarchy */}
      {hasRelations && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <GitBranch className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold">Trace Hierarchy</h3>
          </div>

          <div className="space-y-3">
            {/* Parent Trace */}
            {related.parent && (
              <div>
                <div className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
                  <Link2 className="w-3 h-3" />
                  Parent Trace
                </div>
                <TraceItem
                  trace={related.parent}
                  onNavigate={onNavigate}
                  variant="parent"
                />
              </div>
            )}

            {/* Current Trace Indicator */}
            <div className="pl-4 border-l-2 border-blue-200">
              <div className="text-xs font-medium text-blue-600 mb-1">
                Current Trace
              </div>
              <div className="text-xs font-mono text-muted-foreground truncate">
                {currentTraceId}
              </div>
            </div>

            {/* Child Traces */}
            {related.children.length > 0 && (
              <div>
                <div className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
                  <ArrowRight className="w-3 h-3" />
                  Child Traces ({related.children.length})
                </div>
                <div className="space-y-2">
                  {related.children.map((child) => (
                    <TraceItem
                      key={child.trace_id}
                      trace={child}
                      onNavigate={onNavigate}
                      variant="child"
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Sibling Traces */}
            {related.siblings.length > 0 && (
              <div>
                <div className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
                  <GitBranch className="w-3 h-3" />
                  Sibling Traces ({related.siblings.length})
                </div>
                <div className="space-y-2">
                  {related.siblings.map((sibling) => (
                    <TraceItem
                      key={sibling.trace_id}
                      trace={sibling}
                      onNavigate={onNavigate}
                      variant="sibling"
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

interface TraceItemProps {
  trace: {
    trace_id: string;
    agent_id: string | null;
    created_at: string | null;
    latency_ms: number | null;
    tokens_in: number | null;
    tokens_out: number | null;
  };
  onNavigate: (traceId: string) => void;
  variant: 'parent' | 'child' | 'sibling';
}

function TraceItem({ trace, onNavigate, variant }: TraceItemProps) {
  const variantStyles = {
    parent: 'border-orange-200 bg-orange-50/30 hover:bg-orange-50/60',
    child: 'border-green-200 bg-green-50/30 hover:bg-green-50/60',
    sibling: 'border-slate-200 bg-slate-50/30 hover:bg-slate-50/60',
  };

  const totalTokens = 
    (trace.tokens_in ?? 0) + (trace.tokens_out ?? 0) || null;

  return (
    <button
      onClick={() => onNavigate(trace.trace_id)}
      className={`w-full text-left p-3 rounded-lg border transition-colors ${variantStyles[variant]}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <div className="text-xs font-mono text-muted-foreground truncate">
            {trace.trace_id}
          </div>
          {trace.agent_id && (
            <Badge variant="outline" className="mt-1 text-xs">
              {trace.agent_id}
            </Badge>
          )}
        </div>
        <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
      </div>
      
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        {trace.created_at && (
          <span>{formatTimestamp(trace.created_at)}</span>
        )}
        {trace.latency_ms !== null && (
          <span>{trace.latency_ms}ms</span>
        )}
        {totalTokens !== null && (
          <span>{totalTokens} tokens</span>
        )}
      </div>
    </button>
  );
}
