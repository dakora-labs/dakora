import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DollarSign, Activity, TrendingUp, TrendingDown, Settings } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { useToast } from '@/hooks/use-toast';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface BudgetStatus {
  exceeded: boolean;
  budget_usd: number | null;
  current_spend_usd: number;
  percentage_used: number;
  alert_threshold_pct: number;
  enforcement_mode: string;
  status: 'unlimited' | 'ok' | 'warning' | 'exceeded';
}

interface ProjectStats {
  prompts_count: number;
  total_cost: number;
  total_executions: number;
  avg_cost_per_execution: number;
  daily_costs: Array<{ date: string; cost: number }>;
  top_prompts: Array<{ prompt_id: string; name: string; cost: number; execution_count: number }>;
}

export function ProjectDashboardPage() {
  const { projectSlug } = useParams<{ projectSlug: string }>();
  const navigate = useNavigate();
  const { api, projectId, contextLoading } = useAuthenticatedApi();
  const { toast } = useToast();

  const [budgetStatus, setBudgetStatus] = useState<BudgetStatus | null>(null);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (contextLoading || !projectId) return;

    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [budgetResponse, statsResponse] = await Promise.all([
          api.getBudget(projectId),
          api.getProjectStats(projectId),
        ]);

        setBudgetStatus(budgetResponse);
        setStats(statsResponse);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load dashboard data';
        setError(errorMessage);
        toast({
          title: 'Error Loading Dashboard',
          description: errorMessage,
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [projectId, contextLoading, api, toast]);

  const getBudgetColor = () => {
    if (!budgetStatus || budgetStatus.status === 'unlimited') return 'bg-gray-500';
    if (budgetStatus.status === 'exceeded') return 'bg-red-500';
    if (budgetStatus.status === 'warning') return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getBudgetStatusText = () => {
    if (!budgetStatus) return 'Loading...';
    if (budgetStatus.status === 'unlimited') return 'No limit';
    if (budgetStatus.status === 'exceeded') return 'Exceeded';
    if (budgetStatus.status === 'warning') return 'Warning';
    return 'Healthy';
  };

  const getBudgetRemaining = () => {
    if (!budgetStatus || budgetStatus.budget_usd === null) return null;
    return Math.max(0, budgetStatus.budget_usd - budgetStatus.current_spend_usd);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading analytics...</div>
      </div>
    );
  }

  if (error && !budgetStatus && !stats) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <p className="text-destructive">Failed to load analytics</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    );
  }

  const budgetRemaining = getBudgetRemaining();

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Analytics Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Monitor project performance and budget usage
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/project/${projectSlug}/settings`)}
          >
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Stat Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total Cost */}
            <Card className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-muted-foreground">Total Cost</p>
                  <p className="text-2xl font-bold mt-2">${stats?.total_cost.toFixed(2) || '0.00'}</p>
                </div>
                <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                  <DollarSign className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
              </div>
            </Card>

            {/* Total Executions */}
            <Card className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-muted-foreground">Executions</p>
                  <p className="text-2xl font-bold mt-2">{stats?.total_executions.toLocaleString() || '0'}</p>
                </div>
                <div className="p-3 bg-green-100 dark:bg-green-900/20 rounded-lg">
                  <Activity className="w-6 h-6 text-green-600 dark:text-green-400" />
                </div>
              </div>
            </Card>

            {/* Average Cost */}
            <Card className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-muted-foreground">Avg Cost</p>
                  <p className="text-2xl font-bold mt-2">${stats?.avg_cost_per_execution.toFixed(4) || '0.0000'}</p>
                </div>
                <div className="p-3 bg-purple-100 dark:bg-purple-900/20 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </Card>

            {/* Budget Remaining */}
            <Card className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-muted-foreground">Budget Remaining</p>
                  <p className="text-2xl font-bold mt-2">
                    {budgetRemaining !== null ? `$${budgetRemaining.toFixed(2)}` : 'Unlimited'}
                  </p>
                </div>
                <div className="p-3 bg-orange-100 dark:bg-orange-900/20 rounded-lg">
                  <TrendingDown className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                </div>
              </div>
            </Card>
          </div>

          {/* Budget Progress */}
          {budgetStatus && budgetStatus.status !== 'unlimited' && (
            <Card className="p-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Monthly Budget</h2>
                  <Badge variant={
                    budgetStatus.status === 'exceeded' ? 'destructive' :
                    budgetStatus.status === 'warning' ? 'default' :
                    'secondary'
                  }>
                    {getBudgetStatusText()}
                  </Badge>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      ${budgetStatus.current_spend_usd.toFixed(2)} of ${budgetStatus.budget_usd?.toFixed(2)}
                    </span>
                    <span className="font-medium">
                      {budgetStatus.percentage_used.toFixed(1)}%
                    </span>
                  </div>
                  <Progress
                    value={budgetStatus.percentage_used}
                    className="h-3"
                    indicatorClassName={getBudgetColor()}
                  />
                </div>

                {budgetStatus.status === 'exceeded' && (
                  <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-md">
                    <p className="text-sm text-red-900 dark:text-red-200">
                      Budget exceeded. Agent executions are{' '}
                      {budgetStatus.enforcement_mode === 'strict' ? 'blocked' : 'being monitored'}.
                    </p>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Daily Cost Trend */}
          {stats && stats.daily_costs.length > 0 && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-6">Daily Cost Trend (Last 30 Days)</h2>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={stats.daily_costs}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      className="text-xs"
                      tickFormatter={(value) => {
                        const date = new Date(value);
                        return `${date.getMonth() + 1}/${date.getDate()}`;
                      }}
                    />
                    <YAxis
                      className="text-xs"
                      tickFormatter={(value) => `$${value.toFixed(2)}`}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-card border border-border rounded-lg shadow-lg p-3">
                              <p className="text-sm font-medium">
                                {new Date(data.date).toLocaleDateString()}
                              </p>
                              <p className="text-sm text-muted-foreground">
                                Cost: <span className="font-medium text-foreground">${data.cost.toFixed(2)}</span>
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="cost"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {/* Top Prompts */}
          {stats && stats.top_prompts.length > 0 && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">Top Prompts by Cost</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Prompt ID</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Executions</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Total Cost</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Avg Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.top_prompts.map((prompt, index) => (
                      <tr key={index} className="border-b border-border last:border-0 hover:bg-muted/50">
                        <td className="py-3 px-4">
                          <button
                            onClick={() => navigate(`/project/${projectSlug}/prompts/${prompt.prompt_id}`)}
                            className="text-sm font-mono text-primary hover:underline"
                          >
                            {prompt.name}
                          </button>
                        </td>
                        <td className="py-3 px-4 text-right text-sm">
                          {prompt.execution_count.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right text-sm font-medium">
                          ${prompt.cost.toFixed(2)}
                        </td>
                        <td className="py-3 px-4 text-right text-sm text-muted-foreground">
                          ${(prompt.cost / prompt.execution_count).toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Empty State */}
          {stats && stats.total_executions === 0 && (
            <Card className="p-12">
              <div className="text-center space-y-4">
                <Activity className="w-16 h-16 mx-auto text-muted-foreground" />
                <div>
                  <h3 className="text-lg font-semibold">No Execution Data Yet</h3>
                  <p className="text-sm text-muted-foreground mt-2">
                    Start executing prompts to see analytics and cost tracking
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => navigate(`/project/${projectSlug}/prompts`)}
                >
                  View Prompts
                </Button>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}