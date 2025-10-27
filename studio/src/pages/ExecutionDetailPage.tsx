import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Check, Copy, FileJson2, Zap, MessageSquare, TrendingUp, Clock, DollarSign } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ProviderBadge } from '@/components/executions/ProviderBadge';
import { ConversationTimeline } from '@/components/executions/ConversationTimeline';
import { TemplateUsageList } from '@/components/executions/TemplateUsageList';
import { RelatedTracesPanel } from '@/components/executions/RelatedTracesPanel';
import { useExecutionDetail, useRelatedTraces } from '@/hooks/useExecutions';
import { formatNumber } from '@/utils/format';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export function ExecutionDetailPage() {
  const navigate = useNavigate();
  const { projectSlug, traceId } = useParams<{ projectSlug?: string; traceId?: string }>();
  const { execution, loading, error, refresh } = useExecutionDetail(traceId);
  const { related } = useRelatedTraces(traceId);
  const [copied, setCopied] = useState(false);
  const [jsonCopied, setJsonCopied] = useState(false);
  const [rawOpen, setRawOpen] = useState(false);
  const resolvedProjectSlug = projectSlug ?? 'default';

  const conversation = execution?.conversationHistory ?? [];
  const templateUsages = execution?.templateUsages ?? [];

  const handleNavigateToTrace = (navigateTraceId: string) => {
    navigate(`/project/${resolvedProjectSlug}/executions/${navigateTraceId}`);
  };

  // Calculate additional metrics
  const derivedMetrics = useMemo(() => {
    if (!execution) return null;
    
    const totalTokens = (execution.tokens.in ?? 0) + (execution.tokens.out ?? 0);
    const tokensPerSecond = execution.tokens.out && execution.latencyMs 
      ? (execution.tokens.out / execution.latencyMs) * 1000 
      : null;
    const costPerToken = execution.costUsd && totalTokens > 0
      ? execution.costUsd / totalTokens
      : null;
    const hasMultipleAgents = related?.session_agents && related.session_agents.length > 1;
    
    return {
      totalTokens,
      tokensPerSecond,
      costPerToken,
      costPer1KTokens: costPerToken ? costPerToken * 1000 : null,
      hasMultipleAgents,
      isNested: !!execution.parentTraceId,
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
              {execution?.provider && <ProviderBadge provider={execution.provider} />}
              {derivedMetrics?.isNested && (
                <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
                  Nested Trace
                </Badge>
              )}
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
            onClick={() => execution && handleCopy(execution.traceId, 'Trace ID')}
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
                    <span className="text-green-700">↓ {formatNumber(execution.tokens.in)}</span>
                    <span className="text-blue-700">↑ {formatNumber(execution.tokens.out)}</span>
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
                        ${execution.costUsd?.toFixed(4) ?? '0.0000'}
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
                        {execution.latencyMs ? `${execution.latencyMs.toLocaleString()}` : '—'}
                      </div>
                      <div className="text-xs text-purple-700 uppercase tracking-wide">Latency (ms)</div>
                    </div>
                  </div>
                  {execution.latencyMs && (
                    <div className="mt-2 pt-2 border-t border-purple-300">
                      <div className="text-xs text-purple-700">
                        <span className="font-semibold">{(execution.latencyMs / 1000).toFixed(2)}</span> seconds
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
                        {conversation.length}
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
                {/* Left Column - Templates & Conversation */}
                <div className="space-y-5">
                  {/* Templates First - Most Important */}
                  {templateUsages.length > 0 && (
                    <TemplateUsageList templateUsages={templateUsages} />
                  )}
                  
                  {/* Conversation */}
                  <ConversationTimeline messages={conversation} />
                </div>

                {/* Right Column - Context & Related */}
                <div className="space-y-4">
                  {/* Related Traces Panel */}
                  {related && (
                    <RelatedTracesPanel
                      related={related}
                      currentTraceId={execution.traceId}
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
                      {/* Model Info */}
                      <div className="p-3 bg-muted/40 rounded-lg border border-border/60">
                        <div className="text-xs text-muted-foreground mb-1">Model</div>
                        <code className="text-sm font-mono font-semibold text-foreground">
                          {execution.model ?? 'unknown'}
                        </code>
                      </div>

                      {/* Agent ID */}
                      {execution.agentId && (
                        <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                          <div className="text-xs text-purple-700 mb-1 flex items-center justify-between">
                            <span>Agent ID</span>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-5 w-5"
                              onClick={() => handleCopy(execution.agentId!, 'Agent ID')}
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                          <code className="text-sm font-mono font-semibold text-purple-900 break-all">
                            {execution.agentId}
                          </code>
                        </div>
                      )}

                      {/* Session ID */}
                      {execution.sessionId && (
                        <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                          <div className="text-xs text-blue-700 mb-1 flex items-center justify-between">
                            <span>Session ID</span>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-5 w-5"
                              onClick={() => handleCopy(execution.sessionId!, 'Session ID')}
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                          <code className="text-sm font-mono font-semibold text-blue-900 break-all">
                            {execution.sessionId}
                          </code>
                        </div>
                      )}

                      {/* Parent Trace */}
                      {execution.parentTraceId && (
                        <div className="p-3 bg-orange-50 rounded-lg border border-orange-200">
                          <div className="text-xs text-orange-700 mb-1">Parent Trace</div>
                          <button
                            onClick={() => handleNavigateToTrace(execution.parentTraceId!)}
                            className="text-sm font-mono font-semibold text-orange-900 hover:text-orange-700 hover:underline text-left break-all"
                          >
                            {execution.parentTraceId}
                          </button>
                        </div>
                      )}

                      {/* Timestamp */}
                      <div className="p-3 bg-muted/40 rounded-lg border border-border/60">
                        <div className="text-xs text-muted-foreground mb-1">Created</div>
                        <div className="text-sm font-semibold text-foreground">
                          {execution.createdAt ? new Date(execution.createdAt).toLocaleString() : '—'}
                        </div>
                      </div>

                      {/* Trace ID */}
                      <div className="p-3 bg-muted/40 rounded-lg border border-border/60">
                        <div className="text-xs text-muted-foreground mb-1 flex items-center justify-between">
                          <span>Trace ID</span>
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-5 w-5"
                            onClick={() => handleCopy(execution.traceId, 'Trace ID')}
                          >
                            <Copy className="w-3 h-3" />
                          </Button>
                        </div>
                        <code className="text-xs font-mono text-muted-foreground break-all">
                          {execution.traceId}
                        </code>
                      </div>

                      {/* Metadata - Smart Display */}
                      {execution.metadata && Object.keys(execution.metadata).length > 0 && (
                        <div className="pt-3 border-t border-border/60">
                          <div className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
                            Metadata
                          </div>
                          <div className="space-y-2">
                            {Object.entries(execution.metadata).map(([key, value]) => {
                              const isObject = typeof value === 'object' && value !== null;
                              const displayValue = isObject 
                                ? JSON.stringify(value, null, 2) 
                                : String(value);
                              
                              return (
                                <div key={key} className="p-2.5 bg-muted/30 rounded border border-border/40">
                                  <div className="text-xs font-medium text-foreground mb-1">
                                    {key}
                                  </div>
                                  {isObject ? (
                                    <pre className="text-xs text-muted-foreground font-mono overflow-x-auto">
                                      {displayValue}
                                    </pre>
                                  ) : (
                                    <div className="text-xs text-muted-foreground break-all">
                                      {displayValue}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
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
