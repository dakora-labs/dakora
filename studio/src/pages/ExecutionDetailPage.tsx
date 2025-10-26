import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Check, Copy, FileJson2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ProviderBadge } from '@/components/executions/ProviderBadge';
import { ExecutionMetricsSummary } from '@/components/executions/ExecutionMetricsSummary';
import { ConversationTimeline } from '@/components/executions/ConversationTimeline';
import { TemplateUsageList } from '@/components/executions/TemplateUsageList';
import { MetadataPanel } from '@/components/executions/MetadataPanel';
import { useExecutionDetail } from '@/hooks/useExecutions';
import { formatTimestamp } from '@/utils/format';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export function ExecutionDetailPage() {
  const navigate = useNavigate();
  const { projectSlug, traceId } = useParams<{ projectSlug?: string; traceId?: string }>();
  const { execution, loading, error, refresh } = useExecutionDetail(traceId);
  const [copied, setCopied] = useState(false);
  const [rawOpen, setRawOpen] = useState(false);
  const resolvedProjectSlug = projectSlug ?? 'default';

  const conversation = execution?.conversationHistory ?? [];
  const templateUsages = execution?.templateUsages ?? [];

  const contextItems = useMemo(() => {
    if (!execution) return [];
    return [
      {
        label: 'Trace ID',
        value: execution.traceId,
        copyable: true,
      },
      {
        label: 'Created',
        value: formatTimestamp(execution.createdAt),
      },
      {
        label: 'Provider',
        value: execution.provider ?? '—',
      },
      {
        label: 'Model',
        value: execution.model ?? '—',
      },
      {
        label: 'Session ID',
        value: execution.sessionId ?? '—',
      },
      {
        label: 'Agent ID',
        value: execution.agentId ?? '—',
      },
      {
        label: 'Parent Trace',
        value: execution.parentTraceId ?? '—',
      },
    ];
  }, [execution]);

  const handleCopy = async () => {
    if (!execution) return;
    try {
      await navigator.clipboard.writeText(execution.traceId);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (copyError) {
      console.error('Failed to copy trace id', copyError);
    }
  };

  return (
    <div className="h-full flex flex-col bg-muted/20">
      <div className="border-b border-border bg-card px-6 py-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate(`/project/${resolvedProjectSlug}/executions`)}>
            <ArrowLeft className="w-5 h-5" />
            <span className="sr-only">Back to executions</span>
          </Button>
          <div>
            <h1 className="text-xl font-semibold">Trace Detail</h1>
            <p className="text-sm text-muted-foreground break-all">
              {traceId}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={() => setRawOpen(true)} disabled={!execution}>
            <FileJson2 className="w-4 h-4 mr-2" />
            View JSON
          </Button>
          <Button variant="outline" size="sm" onClick={handleCopy}>
            {copied ? <Check className="w-4 h-4 mr-2 text-emerald-500" /> : <Copy className="w-4 h-4 mr-2" />}
            {copied ? 'Copied' : 'Copy ID'}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto w-full px-6 py-6 space-y-5">
        {loading && !execution && (
          <Card className="p-6 text-center text-muted-foreground">
            Loading execution details...
          </Card>
        )}

        {error && (
          <Card className="p-6 text-center text-destructive">
            {error}
          </Card>
        )}

        {execution && (
          <>
            <ExecutionMetricsSummary
              tokensIn={execution.tokens.in}
              tokensOut={execution.tokens.out}
              tokensTotal={execution.tokens.total}
              costUsd={execution.costUsd}
              latencyMs={execution.latencyMs}
            />

            <div className="grid gap-5 lg:grid-cols-[2fr,1fr]">
              <ConversationTimeline messages={conversation} />
              <div className="space-y-4">
                <Card className="p-4 space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-base font-semibold">Context</h2>
                      <p className="text-xs text-muted-foreground">
                        Quick reference for identifiers and runtime details.
                      </p>
                    </div>
                    {execution.provider && <ProviderBadge provider={execution.provider} />}
                  </div>
                  <dl className="grid gap-4 sm:grid-cols-2">
                    {contextItems.map((item) => (
                      <div key={item.label} className="rounded-lg border border-border/60 bg-background p-3">
                        <dt className="text-xs uppercase tracking-wide text-muted-foreground flex items-center justify-between">
                          <span>{item.label}</span>
                          {item.copyable && (
                            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleCopy}>
                              <Copy className="w-3 h-3" />
                              <span className="sr-only">Copy trace id</span>
                            </Button>
                          )}
                        </dt>
                        <dd className="mt-2 text-sm font-medium text-foreground break-all">
                          {item.value}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </Card>

                <TemplateUsageList templateUsages={templateUsages} />

                <MetadataPanel metadata={execution.metadata} />
              </div>
            </div>
          </>
        )}

        {!loading && !execution && !error && (
          <Card className="p-6 text-center text-muted-foreground">
            Execution not found.
          </Card>
        )}
        </div>
      </div>

      <Dialog open={rawOpen} onOpenChange={setRawOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Raw Execution JSON</DialogTitle>
          </DialogHeader>
          <div className="max-h-[70vh] overflow-auto rounded-md border border-border/60 bg-background p-4">
            <pre className="text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-all">
              {execution ? JSON.stringify(execution, null, 2) : '—'}
            </pre>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
