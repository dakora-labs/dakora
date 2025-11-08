import { useMemo, useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Check, Copy, FileJson2, Zap, MessageSquare, TrendingUp, Clock, DollarSign } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ProviderBadge } from '@/components/executions/ProviderBadge';
import { MessageTimeline } from '@/components/executions/MessageTimeline';
import { RelatedTracesPanel } from '@/components/executions/RelatedTracesPanel';
import { useExecutionDetail, useRelatedTraces, useExecutionTimeline } from '@/hooks/useExecutions';
import { formatNumber } from '@/utils/format';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { timelineToMessages } from '@/utils/timelineAdapter';

// New schema only

export function ExecutionDetailPage() {
  const navigate = useNavigate();
  const { projectSlug, traceId } = useParams<{ projectSlug?: string; traceId?: string }>();
  const { execution, loading, error, refresh, refetchWithMessages } = useExecutionDetail(traceId);
  const { timeline, error: timelineError } = useExecutionTimeline(traceId);
  const { related } = useRelatedTraces(traceId);
  const [copied, setCopied] = useState(false);
  const [jsonCopied, setJsonCopied] = useState(false);
  const [rawOpen, setRawOpen] = useState(false);
  const resolvedProjectSlug = projectSlug ?? 'default';
  
  // When timeline fails to load, fetch messages as fallback
  useEffect(() => {
    if (timelineError && execution && (!execution.input_messages?.length && !execution.output_messages?.length)) {
      console.log('Timeline failed, fetching execution with messages for fallback');
      refetchWithMessages();
    }
  }, [timelineError, execution, refetchWithMessages]);
  
  // Template usages (new schema)
  const templateUsages = execution ? (execution.template_usages ?? []) : [];

  const inputMessages = execution ? execution.input_messages : [];
  const outputMessages = execution ? execution.output_messages : [];
  const childSpans = execution ? execution.child_spans : [];
  
  // Build a unified conversation view from normalized timeline when available
  const allMessages = useMemo(() => {
    if (!execution) return [];
    
    let messages = [];
    
    // If timeline loaded, adapt it to Message[] expected by MessageTimeline
    if (Array.isArray(timeline) && timeline.length > 0) {
      messages = timelineToMessages(timeline);
    } else {
      // Fallback to existing merged messages if no timeline available
      // Fallback ordering: always show inputs before outputs, then by msg_index.
      // We infer outputs by span_type === 'chat' (set on output_messages in API).
      const merged = [
        ...inputMessages.map((m) => ({ ...m, _isOutput: false } as any)),
        ...outputMessages.map((m) => ({ ...m, _isOutput: true } as any)),
      ];
      merged.sort((a: any, b: any) => {
        const aw = a._isOutput ? 1 : 0;
        const bw = b._isOutput ? 1 : 0;
        if (aw !== bw) return aw - bw;
        return (a.msg_index ?? 0) - (b.msg_index ?? 0);
      });
      messages = merged.map(({ _isOutput, ...rest }: any) => rest);
    }
    
    // If execution failed, append error after input messages but before any outputs
    // (or at the end if there are no outputs, which is typical for failed executions)
    if (execution.status === 'ERROR' && execution.status_message) {
      const errorMessage = {
        role: 'system',
        parts: [{ type: 'text', content: `ERROR: ${execution.status_message}` }],
        _isError: true,
        _errorDetails: {
          statusMessage: execution.status_message,
          affectedSpanIds: execution.child_spans?.map(span => span.span_id) || [],
        },
      };
      
      // Find the last input message index
      const lastInputIndex = messages.findIndex((m: any) => m.role !== 'user');
      if (lastInputIndex === -1) {
        // All messages are inputs, append at end
        messages.push(errorMessage as any);
      } else {
        // Insert after last input, before first output
        messages.splice(lastInputIndex, 0, errorMessage as any);
      }
    }
    
    return messages;
  }, [execution, timeline, inputMessages, outputMessages]);

  const handleNavigateToTrace = (navigateTraceId: string) => {
    navigate(`/project/${resolvedProjectSlug}/executions/${navigateTraceId}`);
  };

  // Calculate additional metrics (new schema only)
  const derivedMetrics = useMemo(() => {
    if (!execution) return null;
    
    const tokensIn = execution.tokens_in ?? 0;
    const tokensOut = execution.tokens_out ?? 0;
    const totalTokens = tokensIn + tokensOut;
    
    const latency = execution.latency_ms;
    const cost = execution.total_cost_usd;
    
    const tokensPerSecond = tokensOut && latency 
      ? (tokensOut / latency) * 1000 
      : null;
    const costPerToken = cost && totalTokens > 0
      ? cost / totalTokens
      : null;
    const hasMultipleAgents = related?.session_agents && related.session_agents.length > 1;
    
    const isNested = false; // no nested concept in new schema here
    
    return {
      totalTokens,
      tokensIn,
      tokensOut,
      tokensPerSecond,
      costPerToken,
      costPer1KTokens: costPerToken ? costPerToken * 1000 : null,
      hasMultipleAgents,
      isNested,
      latency,
      cost,
    };
  }, [execution, related]);

  const handleCopy = async (text: string, label: string = 'ID') => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (copyError) {
      console.error(`Failed to copy ${label}`, copyError);
    }
  };

  return (
    <div className="h-full flex flex-col bg-muted/20">
      {/* Header */}
      <div className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center gap-3 mb-3">
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => navigate(`/project/${resolvedProjectSlug}/executions`)}
            className="flex-shrink-0"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="sr-only">Back to executions</span>
          </Button>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-semibold mb-1">Trace Detail</h1>
            <div className="flex items-center gap-2 flex-wrap">
              <code className="text-xs font-mono text-muted-foreground bg-muted px-2 py-1 rounded truncate max-w-md">
                {traceId}
              </code>
              {execution?.status === 'ERROR' && (
                <Badge className="bg-red-100 text-red-700 border-red-200 text-xs">
                  Error
                </Badge>
              )}
              {execution?.provider && <ProviderBadge provider={execution.provider} />}
              {/* Nested trace badge removed (new schema only) */}
              {derivedMetrics?.hasMultipleAgents && (
                <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 text-xs">
                  Multi-Agent
                </Badge>
              )}
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={() => setRawOpen(true)} disabled={!execution}>
            <FileJson2 className="w-4 h-4 mr-2" />
            View JSON
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => {
              if (!execution) return;
              handleCopy(execution.trace_id, 'Trace ID');
            }}
            disabled={!execution}
          >
            {copied ? <Check className="w-4 h-4 mr-2 text-emerald-500" /> : <Copy className="w-4 h-4 mr-2" />}
            {copied ? 'Copied' : 'Copy ID'}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto w-full px-6 py-6 space-y-5">
          {loading && !execution && (
            <Card className="p-8 text-center">
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 rounded-full border-4 border-primary border-t-transparent animate-spin" />
                <p className="text-muted-foreground">Loading execution details...</p>
              </div>
            </Card>
          )}

          {error && (
            <Card className="p-6 text-center text-destructive border-destructive/50 bg-destructive/5">
              <p className="font-semibold mb-1">Error loading execution</p>
              <p className="text-sm">{error}</p>
            </Card>
          )}

          {execution && (
            <>
              {/* Enhanced Metrics Summary */}
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {/* Tokens Card */}
                <Card className="p-4 bg-gradient-to-br from-blue-50 to-blue-100/50 border-blue-200">
                  <div className="flex items-start justify-between mb-2">
                    <div className="p-2 bg-blue-600 rounded-lg">
                      <TrendingUp className="w-5 h-5 text-white" />
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-blue-900">
                        {formatNumber(derivedMetrics?.totalTokens)}
                      </div>
                      <div className="text-xs text-blue-700 uppercase tracking-wide">Total Tokens</div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-green-700">↓ {formatNumber(derivedMetrics?.tokensIn ?? 0)}</span>
                    <span className="text-blue-700">↑ {formatNumber(derivedMetrics?.tokensOut ?? 0)}</span>
                  </div>
                  {derivedMetrics?.tokensPerSecond && (
                    <div className="mt-2 pt-2 border-t border-blue-300">
                      <div className="text-xs text-blue-700">
                        <span className="font-semibold">{derivedMetrics.tokensPerSecond.toFixed(1)}</span> tokens/sec
                      </div>
                    </div>
                  )}
                </Card>

                {/* Cost Card */}
                <Card className="p-4 bg-gradient-to-br from-green-50 to-green-100/50 border-green-200">
                  <div className="flex items-start justify-between mb-2">
                    <div className="p-2 bg-green-600 rounded-lg">
                      <DollarSign className="w-5 h-5 text-white" />
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-green-900">
                        ${derivedMetrics?.cost?.toFixed(4) ?? '0.0000'}
                      </div>
                      <div className="text-xs text-green-700 uppercase tracking-wide">Cost (USD)</div>
                    </div>
                  </div>
                  {derivedMetrics?.costPer1KTokens && (
                    <div className="mt-2 pt-2 border-t border-green-300">
                      <div className="text-xs text-green-700">
                        <span className="font-semibold">${derivedMetrics.costPer1KTokens.toFixed(4)}</span> per 1K tokens
                      </div>
                    </div>
                  )}
                </Card>

                {/* Latency Card */}
                <Card className="p-4 bg-gradient-to-br from-purple-50 to-purple-100/50 border-purple-200">
                  <div className="flex items-start justify-between mb-2">
                    <div className="p-2 bg-purple-600 rounded-lg">
                      <Clock className="w-5 h-5 text-white" />
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-purple-900">
                        {derivedMetrics?.latency ? `${derivedMetrics.latency.toLocaleString()}` : '—'}
                      </div>
                      <div className="text-xs text-purple-700 uppercase tracking-wide">Latency (ms)</div>
                    </div>
                  </div>
                  {derivedMetrics?.latency && (
                    <div className="mt-2 pt-2 border-t border-purple-300">
                      <div className="text-xs text-purple-700">
                        <span className="font-semibold">{(derivedMetrics.latency / 1000).toFixed(2)}</span> seconds
                      </div>
                    </div>
                  )}
                </Card>

                {/* Context Card */}
                <Card className="p-4 bg-gradient-to-br from-orange-50 to-orange-100/50 border-orange-200">
                  <div className="flex items-start justify-between mb-2">
                    <div className="p-2 bg-orange-600 rounded-lg">
                      <MessageSquare className="w-5 h-5 text-white" />
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-orange-900">
                        {allMessages.length}
                      </div>
                      <div className="text-xs text-orange-700 uppercase tracking-wide">Messages</div>
                    </div>
                  </div>
                  <div className="mt-2 pt-2 border-t border-orange-300">
                    <div className="text-xs text-orange-700">
                      {templateUsages.length > 0 ? (
                        <><span className="font-semibold">{templateUsages.length}</span> template{templateUsages.length === 1 ? '' : 's'}</>
                      ) : (
                        'No templates'
                      )}
                    </div>
                  </div>
                </Card>
              </div>

              {/* Main Content Grid */}
              <div className="grid gap-5 lg:grid-cols-[1fr,400px]">
                {/* Left Column - Conversation */}
                <div className="space-y-5 min-w-0">
                  {/* Unified Conversation */}
                  {allMessages.length > 0 && (
                    <MessageTimeline 
                      messages={allMessages} 
                      direction="input" 
                      title="Conversation"
                      childSpans={childSpans}
                    />
                  )}
                </div>

                {/* Right Column - Context & Related */}
                <div className="space-y-4">
                  {/* Related Traces Panel */}
                  {related && execution && (
                    <RelatedTracesPanel
                      related={related}
                      currentTraceId={execution.trace_id}
                      onNavigate={handleNavigateToTrace}
                    />
                  )}

                  {/* Execution Context */}
                  <Card className="p-4">
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Zap className="w-4 h-4 text-muted-foreground" />
                      Execution Context
                    </h3>
                    
                    <div className="space-y-3">
                      {/* Templates Used */}
                      {templateUsages.length > 0 && (
                        <div className="p-3 bg-indigo-50 rounded-lg border border-indigo-200">
                          <div className="text-xs text-indigo-700 mb-2 font-semibold">
                            {templateUsages.length === 1 ? 'Template Used' : 'Templates Used'}
                          </div>
                          <div className="space-y-2">
                            {templateUsages.map((usage, idx) => (
                              <button
                                key={idx}
                                onClick={() => navigate(`/project/${resolvedProjectSlug}/prompt/edit?prompt=${usage.prompt_id}`)}
                                className="w-full text-left p-2 bg-white rounded border border-indigo-200 hover:border-indigo-400 hover:bg-indigo-50/50 transition-colors group"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex-1 min-w-0">
                                    <div className="text-sm font-mono font-semibold text-indigo-900 truncate group-hover:text-indigo-700">
                                      {usage.prompt_id}
                                    </div>
                                    <div className="text-xs text-indigo-600 mt-0.5">
                                      v{usage.version}
                                    </div>
                                  </div>
                                  <div className="ml-2 text-indigo-400 group-hover:text-indigo-600">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                  </div>
                                </div>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Model Info */}
                      <div className="p-3 bg-muted/40 rounded-lg border border-border/60">
                        <div className="text-xs text-muted-foreground mb-1">Model</div>
                        <code className="text-sm font-mono font-semibold text-foreground">
                          {execution.model ?? 'unknown'}
                        </code>
                      </div>

                      {/* Agent Name */}
                      {execution.agent_name && (
                        <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                          <div className="text-xs text-purple-700 mb-1 flex items-center justify-between">
                            <span>Agent Name</span>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-5 w-5"
                              onClick={() => {
                                if (execution.agent_name) handleCopy(execution.agent_name, 'Agent');
                              }}
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                          <code className="text-sm font-mono font-semibold text-purple-900 break-all">
                            {execution.agent_name}
                          </code>
                        </div>
                      )}

                      {/* Session ID (old schema) removed */}

                      {/* Parent trace (old schema) removed */}

                      {/* Timestamp */}
                      <div className="p-3 bg-muted/40 rounded-lg border border-border/60">
                         <div className="text-xs text-muted-foreground mb-1">Created</div>
                         <div className="text-sm font-semibold text-foreground">{new Date(execution.created_at).toLocaleString()}</div>
                      </div>

                      {/* Trace ID */}
                      <div className="p-3 bg-muted/40 rounded-lg border border-border/60">
                           <div className="text-xs text-muted-foreground mb-1 flex items-center justify-between">
                             <span>Trace ID</span>
                             <Button variant="ghost" size="icon" className="h-5 w-5" onClick={() => handleCopy(execution.trace_id, 'Trace ID')}>
                               <Copy className="w-3 h-3" />
                             </Button>
                           </div>
                           <code className="text-xs font-mono text-muted-foreground break-all">{execution.trace_id}</code>
                      </div>

                      {/* Span ID */}
                      {execution && (
                        <div className="p-3 bg-muted/40 rounded-lg border border-border/60">
                          <div className="text-xs text-muted-foreground mb-1 flex items-center justify-between">
                            <span>Span ID</span>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-5 w-5"
                              onClick={() => handleCopy(execution.span_id, 'Span ID')}
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                          <code className="text-xs font-mono text-muted-foreground break-all">
                            {execution.span_id}
                          </code>
                        </div>
                      )}

                      {/* Metadata removed - not in new schema */}
                    </div>
                  </Card>
                </div>
              </div>
            </>
          )}

          {!loading && !execution && !error && (
            <Card className="p-12 text-center">
              <div className="text-muted-foreground">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-40" />
                <p className="font-semibold mb-1">Execution not found</p>
                <p className="text-sm">The trace you're looking for doesn't exist or has been deleted.</p>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* JSON Dialog */}
      <Dialog open={rawOpen} onOpenChange={setRawOpen}>
        <DialogContent className="max-w-4xl max-h-[85vh]">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle>Raw Execution JSON</DialogTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (execution) {
                    navigator.clipboard.writeText(JSON.stringify(execution, null, 2));
                    setJsonCopied(true);
                    setTimeout(() => setJsonCopied(false), 2000);
                  }
                }}
                className="h-8 gap-2"
              >
                {jsonCopied ? (
                  <>
                    <Check className="w-4 h-4" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    Copy JSON
                  </>
                )}
              </Button>
            </div>
          </DialogHeader>
          <div className="overflow-auto rounded-md border border-border/60 bg-slate-950 p-4 max-h-[calc(85vh-8rem)]">
            <pre className="text-xs leading-relaxed text-slate-200 font-mono">
              {execution ? JSON.stringify(execution, null, 2) : '—'}
            </pre>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
