import { useMemo } from 'react';
import { Loader2, RefreshCw, Link2, Zap, MessageSquare, TrendingUp, Clock, DollarSign } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ProviderBadge } from './ProviderBadge';
import type { ExecutionListItem } from '@/types';
import { formatCurrency, formatNumber, formatRelativeTime, parseApiDate } from '@/utils/format';
import { cn } from '@/lib/utils';

interface ExecutionsTableProps {
  executions: ExecutionListItem[];
  loading: boolean;
  error: string | null;
  offset: number;
  limit: number;
  total: number;
  onRowClick: (traceId: string) => void;
  onPrevPage: () => void;
  onNextPage: () => void;
  onRefresh: () => void;
}

// Helper to calculate tokens per second
const calculateTokensPerSecond = (tokensOut: number | null, latencyMs: number | null): number | null => {
  if (tokensOut === null || latencyMs === null || latencyMs === 0) return null;
  return (tokensOut / latencyMs) * 1000;
};

// Helper to get performance badge
const getPerformanceBadge = (latencyMs: number | null) => {
  if (latencyMs === null) return null;
  if (latencyMs < 2000) return { label: 'Fast', variant: 'secondary' as const };
  if (latencyMs < 5000) return { label: 'Normal', variant: 'default' as const };
  if (latencyMs < 10000) return { label: 'Slow', variant: 'outline' as const };
  return { label: 'Very Slow', variant: 'destructive' as const };
};

// Helper to get cost badge for expensive calls
const getCostBadge = (costUsd: number | null) => {
  if (costUsd === null || costUsd < 0.01) return null;
  if (costUsd >= 0.10) return { label: 'High Cost', variant: 'destructive' as const };
  if (costUsd >= 0.05) return { label: 'Med Cost', variant: 'outline' as const };
  return null;
};

export function ExecutionsTable({
  executions,
  loading,
  error,
  offset,
  limit,
  total,
  onRowClick,
  onPrevPage,
  onNextPage,
  onRefresh,
}: ExecutionsTableProps) {
  const rows = Array.isArray(executions) ? executions : [];
  const safeOffset = Number.isFinite(offset) ? offset : 0;
  const safeLimit = Number.isFinite(limit) && limit > 0 ? limit : rows.length || 25;
  const safeTotal = Number.isFinite(total) ? total : rows.length;

  const pageStart = safeTotal === 0 ? 0 : safeOffset + 1;
  const pageEnd = Math.min(safeOffset + rows.length, safeTotal);
  const disablePrev = safeOffset === 0 || loading;
  const disableNext = safeOffset + safeLimit >= safeTotal || rows.length < safeLimit || loading;

  // Calculate summary stats for current page
  const summaryStats = useMemo(() => {
    if (rows.length === 0) return null;
    
    const totalCost = rows.reduce((sum, exec) => sum + (exec.costUsd ?? 0), 0);
    const totalTokensIn = rows.reduce((sum, exec) => sum + (exec.tokensIn ?? 0), 0);
    const totalTokensOut = rows.reduce((sum, exec) => sum + (exec.tokensOut ?? 0), 0);
    const avgLatency = rows.reduce((sum, exec) => sum + (exec.latencyMs ?? 0), 0) / rows.filter(e => e.latencyMs).length;
    const withTemplates = rows.filter(exec => exec.templateCount > 0).length;
    
    return {
      totalCost,
      totalTokensIn,
      totalTokensOut,
      avgLatency: isFinite(avgLatency) ? avgLatency : 0,
      withTemplates,
      totalExecutions: rows.length,
    };
  }, [rows]);


  return (
    <Card className="p-0 overflow-hidden border border-border/80">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/60 bg-muted/40">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-foreground">Recent Executions</h2>
          {loading && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {pageStart}-{pageEnd} of {total}
          </span>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onRefresh} disabled={loading}>
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
            <span className="sr-only">Refresh</span>
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      {summaryStats && !loading && (
        <div className="px-4 py-3 border-b border-border/60 bg-gradient-to-r from-blue-50/50 to-purple-50/50">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
            <div className="flex flex-col">
              <span className="text-muted-foreground font-medium mb-0.5">Page Cost</span>
              <span className="text-base font-bold text-green-700">
                {formatCurrency(summaryStats.totalCost, { compact: false })}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-muted-foreground font-medium mb-0.5">Total Tokens</span>
              <span className="text-base font-bold text-blue-700">
                {formatNumber(summaryStats.totalTokensIn + summaryStats.totalTokensOut)}
              </span>
              <span className="text-[10px] text-muted-foreground">
                ↓{formatNumber(summaryStats.totalTokensIn)} ↑{formatNumber(summaryStats.totalTokensOut)}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-muted-foreground font-medium mb-0.5">Avg Latency</span>
              <span className="text-base font-bold text-purple-700">
                {summaryStats.avgLatency > 0 ? `${Math.round(summaryStats.avgLatency)}ms` : '—'}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-muted-foreground font-medium mb-0.5">With Templates</span>
              <span className="text-base font-bold text-indigo-700">
                {summaryStats.withTemplates} / {summaryStats.totalExecutions}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-muted-foreground font-medium mb-0.5">Avg Cost/Exec</span>
              <span className="text-base font-bold text-orange-700">
                {formatCurrency(summaryStats.totalCost / summaryStats.totalExecutions, { compact: false })}
              </span>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="px-4 py-3 text-sm text-destructive border-b border-border/60">
          {error}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground border-b border-border/60 bg-muted/20">
              <th className="px-4 py-3 font-semibold">Time</th>
              <th className="px-4 py-3 font-semibold">Model</th>
              <th className="px-4 py-3 font-semibold">Agent / Session</th>
              <th className="px-4 py-3 font-semibold text-right">Tokens</th>
              <th className="px-4 py-3 font-semibold text-right">Performance</th>
              <th className="px-4 py-3 font-semibold text-right">Cost</th>
              <th className="px-4 py-3 font-semibold text-center">Templates</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-sm text-muted-foreground">
                  <div className="flex flex-col items-center gap-2">
                    <MessageSquare className="w-8 h-8 text-muted-foreground/40" />
                    <p>No executions found for the selected filters.</p>
                    <p className="text-xs">Try adjusting your filters or refresh the page.</p>
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((execution) => {
                const totalTokens = (execution.tokensIn ?? 0) + (execution.tokensOut ?? 0);
                const tokensPerSecond = calculateTokensPerSecond(execution.tokensOut, execution.latencyMs);
                const performanceBadge = getPerformanceBadge(execution.latencyMs);
                const costBadge = getCostBadge(execution.costUsd);
                const hasTemplates = execution.templateCount > 0;
                
                return (
                  <tr
                    key={execution.traceId}
                    className="border-t border-border/40 hover:bg-muted/50 cursor-pointer transition-all duration-150"
                    onClick={() => onRowClick(execution.traceId)}
                  >
                    {/* Time Column */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <span className="font-semibold text-foreground text-sm">
                          {formatRelativeTime(execution.createdAt)}
                        </span>
                        <span className="text-[11px] text-muted-foreground/80 font-mono">
                          {(() => {
                            const date = parseApiDate(execution.createdAt ?? null);
                            return date ? date.toLocaleTimeString() : '—';
                          })()}
                        </span>
                        {execution.parentTraceId && (
                          <Badge variant="outline" className="mt-0.5 w-fit text-[10px] h-5 px-1.5 bg-blue-50 text-blue-700 border-blue-200">
                            <Link2 className="w-2.5 h-2.5 mr-0.5" />
                            nested
                          </Badge>
                        )}
                      </div>
                    </td>

                    {/* Model Column */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1.5">
                        <div className="flex items-center gap-2">
                          <ProviderBadge provider={execution.provider} />
                        </div>
                        <code className="text-xs font-mono text-foreground/90 bg-muted/50 px-1.5 py-0.5 rounded">
                          {execution.model ?? 'unknown'}
                        </code>
                      </div>
                    </td>

                    {/* Agent / Session Column */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        {execution.agentId ? (
                          <div className="flex items-center gap-1.5">
                            <Zap className="w-3 h-3 text-purple-500" />
                            <code className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded border border-purple-200 font-mono">
                              {execution.agentId}
                            </code>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground italic">No agent</span>
                        )}
                        {execution.sessionId && (
                          <div className="flex items-center gap-1.5">
                            <MessageSquare className="w-3 h-3 text-blue-500" />
                            <code className="text-[10px] bg-muted/60 text-muted-foreground px-1.5 py-0.5 rounded font-mono truncate max-w-[120px]" title={execution.sessionId}>
                              {execution.sessionId.substring(0, 12)}...
                            </code>
                          </div>
                        )}
                      </div>
                    </td>

                    {/* Tokens Column */}
                    <td className="px-4 py-3 text-right">
                      <div className="flex flex-col gap-1 items-end">
                        <div className="flex items-center gap-2 text-sm font-mono">
                          <span className="text-green-600 font-semibold">{formatNumber(execution.tokensIn)}</span>
                          <span className="text-muted-foreground">→</span>
                          <span className="text-blue-600 font-semibold">{formatNumber(execution.tokensOut)}</span>
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          Total: <span className="font-semibold">{formatNumber(totalTokens)}</span>
                        </div>
                        {tokensPerSecond !== null && (
                          <div className="flex items-center gap-1 text-[10px] text-purple-600">
                            <TrendingUp className="w-3 h-3" />
                            <span>{tokensPerSecond.toFixed(1)} tok/s</span>
                          </div>
                        )}
                      </div>
                    </td>

                    {/* Performance Column */}
                    <td className="px-4 py-3 text-right">
                      <div className="flex flex-col gap-1.5 items-end">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                          <span className="text-sm font-mono font-semibold">
                            {execution.latencyMs !== null && execution.latencyMs !== undefined
                              ? `${execution.latencyMs.toLocaleString()} ms`
                              : '—'}
                          </span>
                        </div>
                        {performanceBadge && (
                          <Badge 
                            variant={performanceBadge.variant}
                            className="text-[10px] h-5 px-2"
                          >
                            {performanceBadge.label}
                          </Badge>
                        )}
                        {execution.latencyMs && execution.latencyMs > 0 && (
                          <span className="text-[10px] text-muted-foreground">
                            {(execution.latencyMs / 1000).toFixed(2)}s
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Cost Column */}
                    <td className="px-4 py-3 text-right">
                      <div className="flex flex-col gap-1.5 items-end">
                        <div className="flex items-center gap-1.5">
                          <DollarSign className="w-3.5 h-3.5 text-green-600" />
                          <span className="text-sm font-mono font-bold text-foreground">
                            {formatCurrency(execution.costUsd, { compact: false })}
                          </span>
                        </div>
                        {costBadge && (
                          <Badge 
                            variant={costBadge.variant}
                            className="text-[10px] h-5 px-2"
                          >
                            {costBadge.label}
                          </Badge>
                        )}
                        {execution.costUsd && execution.costUsd > 0 && totalTokens > 0 && (
                          <span className="text-[10px] text-muted-foreground">
                            ${((execution.costUsd / totalTokens) * 1000).toFixed(4)}/1K
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Templates Column */}
                    <td className="px-4 py-3 text-center">
                      {hasTemplates ? (
                        <Badge variant="secondary" className="bg-indigo-50 text-indigo-700 border-indigo-200">
                          {execution.templateCount} {execution.templateCount === 1 ? 'template' : 'templates'}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}

            {loading && rows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-sm text-muted-foreground">
                  <div className="flex flex-col items-center gap-3">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    <p>Loading executions...</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between px-4 py-3 border-t border-border/60 bg-muted/30">
        <div className="text-xs text-muted-foreground">
          Showing {pageStart}-{pageEnd} of {total} executions
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onPrevPage} disabled={disablePrev}>
            Previous
          </Button>
          <Button variant="outline" size="sm" onClick={onNextPage} disabled={disableNext}>
            Next
          </Button>
        </div>
      </div>
    </Card>
  );
}
