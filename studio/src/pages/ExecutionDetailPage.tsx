import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Check, Copy, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ProviderBadge } from '@/components/executions/ProviderBadge';
import { ExecutionMetricsSummary } from '@/components/executions/ExecutionMetricsSummary';
import { ConversationTimeline } from '@/components/executions/ConversationTimeline';
import { TemplateUsageList } from '@/components/executions/TemplateUsageList';
import { MetadataPanel } from '@/components/executions/MetadataPanel';
import { useExecutionDetail } from '@/hooks/useExecutions';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { formatTimestamp } from '@/utils/format';

export function ExecutionDetailPage() {
  const navigate = useNavigate();
  const { projectSlug, traceId } = useParams<{ projectSlug?: string; traceId?: string }>();
  const { projectId } = useAuthenticatedApi();
  const { execution, loading, error, refresh } = useExecutionDetail(traceId);
  const [copied, setCopied] = useState(false);
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

  const apiBase = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api';
  const rawJsonLink = execution && projectId
    ? `${apiBase}/projects/${projectId}/executions/${execution.traceId}`
    : null;

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
    <div className="h-full flex flex-col">
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
          <Button variant="outline" size="sm" onClick={handleCopy}>
            {copied ? <Check className="w-4 h-4 mr-2 text-emerald-500" /> : <Copy className="w-4 h-4 mr-2" />}
            {copied ? 'Copied' : 'Copy ID'}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
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

            <div className="grid gap-4 lg:grid-cols-[2fr,1fr]">
              <ConversationTimeline messages={conversation} />
              <div className="space-y-4">
                <Card className="p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="text-base font-semibold">Context</h2>
                    {execution.provider && <ProviderBadge provider={execution.provider} />}
                  </div>
                  <dl className="space-y-2">
                    {contextItems.map((item) => (
                      <div key={item.label} className="flex flex-col gap-1">
                        <dt className="text-xs uppercase tracking-wide text-muted-foreground">{item.label}</dt>
                        <dd className="text-sm text-foreground flex items-center gap-2">
                          {item.value}
                          {item.copyable && (
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCopy}>
                              <Copy className="w-4 h-4" />
                              <span className="sr-only">Copy trace id</span>
                            </Button>
                          )}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </Card>

                <TemplateUsageList templateUsages={templateUsages} />

                <MetadataPanel metadata={execution.metadata} />

                <Card className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-base font-semibold">Raw Payload</h2>
                    {rawJsonLink && (
                      <a
                        href={rawJsonLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Open JSON
                      </a>
                    )}
                  </div>
                  <pre className="rounded-md bg-background border border-border/60 p-3 text-xs text-muted-foreground overflow-x-auto">
                    {JSON.stringify(execution, null, 2)}
                  </pre>
                </Card>
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
  );
}
