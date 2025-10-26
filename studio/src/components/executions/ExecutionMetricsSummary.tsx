import { Card } from '@/components/ui/card';
import { formatCurrency, formatNumber } from '@/utils/format';
import { ArrowDownRight, ArrowUpRight, CircleDot, DollarSign, Timer } from 'lucide-react';

interface ExecutionMetricsSummaryProps {
  tokensIn: number | null;
  tokensOut: number | null;
  tokensTotal: number | null;
  costUsd: number | null;
  latencyMs: number | null;
}

export function ExecutionMetricsSummary({
  tokensIn,
  tokensOut,
  tokensTotal,
  costUsd,
  latencyMs,
}: ExecutionMetricsSummaryProps) {
  const metrics = [
    {
      key: 'tokensIn',
      label: 'Tokens In',
      value: formatNumber(tokensIn),
      icon: ArrowDownRight,
    },
    {
      key: 'tokensOut',
      label: 'Tokens Out',
      value: formatNumber(tokensOut),
      icon: ArrowUpRight,
    },
    {
      key: 'tokensTotal',
      label: 'Total Tokens',
      value: formatNumber(tokensTotal),
      icon: CircleDot,
    },
    {
      key: 'costUsd',
      label: 'Cost (USD)',
      value: formatCurrency(costUsd, { compact: true }),
      icon: DollarSign,
    },
    {
      key: 'latencyMs',
      label: 'Latency',
      value: latencyMs !== null && latencyMs !== undefined ? `${latencyMs} ms` : '—',
      icon: Timer,
    },
  ];

  return (
    <Card className="p-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.key} className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                <Icon className="w-5 h-5 text-muted-foreground" />
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  {metric.label}
                </div>
                <div className="text-lg font-semibold text-foreground">
                  {metric.value}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
