import { useState } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Clock, TrendingDown, Check, ChevronLeft, ChevronRight } from 'lucide-react';
import type { OptimizationRunRecord } from '@/types';

interface OptimizationHistoryProps {
  history: OptimizationRunRecord[];
  selectedRunId?: string;
  onSelectRun: (run: OptimizationRunRecord) => void;
  isOptimizing?: boolean;
}

export function OptimizationHistory({
  history,
  selectedRunId,
  onSelectRun,
  isOptimizing = false,
}: OptimizationHistoryProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  if (isCollapsed) {
    return (
      <div className="w-12 border-r border-border bg-muted/30 flex flex-col items-center py-4 gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsCollapsed(false)}
          className="h-8 w-8 p-0"
        >
          <ChevronRight className="w-4 h-4" />
        </Button>
        {history.length > 0 && (
          <>
            <div className="w-px h-4 bg-border" />
            <Clock className="w-4 h-4 text-muted-foreground" />
            <div className="flex flex-col gap-1.5 mt-1">
              {history.slice(0, 10).map((run, index) => {
                const isSelected = run.optimization_id === selectedRunId;
                return (
                  <Button
                    key={run.optimization_id}
                    variant={isSelected ? "default" : "outline"}
                    size="sm"
                    onClick={() => onSelectRun(run)}
                    className={`h-7 w-7 p-0 text-xs ${
                      isSelected
                        ? 'bg-purple-600 hover:bg-purple-700'
                        : 'hover:bg-purple-50 hover:border-purple-300'
                    }`}
                  >
                    {history.length - index}
                  </Button>
                );
              })}
            </div>
          </>
        )}
      </div>
    );
  }

  if (history.length === 0 && !isOptimizing) {
    return (
      <div className="w-64 border-r border-border bg-muted/30 flex flex-col">
        <div className="p-3 border-b border-border flex items-center justify-between">
          <h2 className="font-semibold text-xs text-muted-foreground uppercase tracking-wide">
            History
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsCollapsed(true)}
            className="h-6 w-6 p-0"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </Button>
        </div>
        <div className="flex-1 flex items-center justify-center p-4">
          <p className="text-xs text-muted-foreground text-center">
            No optimization history yet
          </p>
        </div>
      </div>
    );
  }

  if (history.length === 0 && isOptimizing) {
    return (
      <div className="w-64 border-r border-border bg-muted/30 flex flex-col">
        <div className="p-3 border-b border-border flex items-center justify-between">
          <h2 className="font-semibold text-xs text-muted-foreground uppercase tracking-wide">
            History
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsCollapsed(true)}
            className="h-6 w-6 p-0"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </Button>
        </div>
        <div className="flex-1 flex items-center justify-center p-4">
          <p className="text-xs text-muted-foreground text-center">
            Running optimization...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-64 border-r border-border bg-muted/30 flex flex-col">
      <div className="p-3 border-b border-border flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-xs text-muted-foreground uppercase tracking-wide">
            History
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {history.length} run{history.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsCollapsed(true)}
          className="h-6 w-6 p-0 flex-shrink-0"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-2 space-y-2">
          {history.map((run) => {
            const isSelected = run.optimization_id === selectedRunId;

            return (
              <Card
                key={run.optimization_id}
                className={`p-2.5 cursor-pointer transition-all hover:shadow-md ${
                  isSelected
                    ? 'border-purple-500 bg-purple-50/50'
                    : 'border-border hover:border-purple-200'
                }`}
                onClick={() => onSelectRun(run)}
              >
                <div className="space-y-1.5">
                  <div className="flex items-start justify-between gap-1.5">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <Clock className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                      <span className="text-xs text-muted-foreground">
                        {formatDate(run.created_at)}
                      </span>
                    </div>
                    {run.applied && (
                      <Badge className="bg-green-500 text-white text-xs gap-1 flex-shrink-0 h-4 px-1">
                        <Check className="w-2.5 h-2.5" />
                        Applied
                      </Badge>
                    )}
                  </div>

                  {run.token_reduction_pct > 0 && (
                    <div className="flex items-center gap-1">
                      <TrendingDown className="w-3 h-3 text-green-600" />
                      <span className="text-xs font-medium text-green-700">
                        {run.token_reduction_pct.toFixed(1)}% reduction
                      </span>
                    </div>
                  )}

                  {run.insights && run.insights.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {run.insights.slice(0, 2).map((insight, i) => (
                        <Badge
                          key={i}
                          variant="outline"
                          className="text-xs h-4 px-1.5"
                        >
                          {insight.category}
                        </Badge>
                      ))}
                      {run.insights.length > 2 && (
                        <Badge variant="outline" className="text-xs h-4 px-1.5">
                          +{run.insights.length - 2}
                        </Badge>
                      )}
                    </div>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}