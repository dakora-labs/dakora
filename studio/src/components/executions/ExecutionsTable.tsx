import { Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
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

      {error && (
        <div className="px-4 py-3 text-sm text-destructive border-b border-border/60">
          {error}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-2 font-medium">Time</th>
              <th className="px-4 py-2 font-medium">Provider / Model</th>
              <th className="px-4 py-2 font-medium">Tokens In / Out</th>
              <th className="px-4 py-2 font-medium">Latency</th>
              <th className="px-4 py-2 font-medium text-right">Cost</th>
              <th className="px-4 py-2 font-medium">Agent</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
                  No executions found for the selected filters.
                </td>
              </tr>
            ) : (
              rows.map((execution) => (
                <tr
                  key={execution.traceId}
                  className="border-t border-border/60 hover:bg-muted/40 cursor-pointer transition-colors"
                  onClick={() => onRowClick(execution.traceId)}
                >
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <span className="font-medium text-foreground">
                        {formatRelativeTime(execution.createdAt)}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {(() => {
                          const date = parseApiDate(execution.createdAt ?? null);
                          return date ? date.toLocaleString() : '—';
                        })()}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <ProviderBadge provider={execution.provider} />
                      <span className="text-sm text-muted-foreground">
                        {execution.model ?? '—'}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium">
                        {formatNumber(execution.tokensIn)} / {formatNumber(execution.tokensOut)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm">
                      {execution.latencyMs !== null && execution.latencyMs !== undefined
                        ? `${execution.latencyMs} ms`
                        : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-sm font-medium">
                      {formatCurrency(execution.costUsd, { compact: true })}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {execution.agentId ? (
                      <code className="text-xs bg-muted px-2 py-1 rounded-md">
                        {execution.agentId}
                      </code>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}

            {loading && rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
                  Loading executions...
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
