import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Filter, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { ExecutionsTable } from '@/components/executions/ExecutionsTable';
import { useExecutions } from '@/hooks/useExecutions';

export function ExecutionsPage() {
  const navigate = useNavigate();
  const { projectSlug } = useParams<{ projectSlug?: string }>();
  const resolvedProjectSlug = projectSlug ?? 'default';

  const [provider, setProvider] = useState<string>('all');
  const [model, setModel] = useState<string>('');
  const [agentId, setAgentId] = useState<string>('');
  const [promptId, setPromptId] = useState<string>('');
  const [hasTemplatesOnly, setHasTemplatesOnly] = useState<boolean>(false);
  const [pageSize, setPageSize] = useState<number>(25);

  const filters = useMemo(() => ({
    provider: provider === 'all' ? undefined : provider,
    model: model || undefined,
    agent_id: agentId || undefined,
    prompt_id: promptId || undefined,
    has_templates: hasTemplatesOnly ? true : undefined,
    limit: pageSize,
  }), [agentId, hasTemplatesOnly, model, pageSize, promptId, provider]);

  const {
    executions,
    total,
    limit,
    offset,
    loading,
    error,
    refresh,
    setOffset,
  } = useExecutions(filters);

  useEffect(() => {
    setOffset(0);
  }, [provider, model, agentId, promptId, hasTemplatesOnly, pageSize, setOffset]);

  const handleRowClick = (traceId: string) => {
    navigate(`/project/${resolvedProjectSlug}/executions/${traceId}`);
  };

  const handleResetFilters = () => {
    setProvider('all');
    setModel('');
    setAgentId('');
    setPromptId('');
    setHasTemplatesOnly(false);
  };

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-border bg-card px-6 py-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Executions</h1>
            <p className="text-sm text-muted-foreground">
              Inspect agent runs, token usage, and costs across this project.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
              <RotateCcw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        <div className="mt-4">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-3">
            <Filter className="w-4 h-4" />
            Filters
          </div>
          <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="provider">Provider</Label>
              <Select value={provider} onValueChange={(value) => setProvider(value)}>
                <SelectTrigger id="provider" className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All providers</SelectItem>
                  <SelectItem value="openai">OpenAI</SelectItem>
                  <SelectItem value="azure_openai">Azure OpenAI</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="model">Model</Label>
              <Input
                id="model"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                placeholder="e.g. gpt-4o"
                className="h-9"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="agent">Agent ID</Label>
              <Input
                id="agent"
                value={agentId}
                onChange={(event) => setAgentId(event.target.value)}
                placeholder="agent identifier"
                className="h-9"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="prompt">Prompt ID</Label>
              <Input
                id="prompt"
                value={promptId}
                onChange={(event) => setPromptId(event.target.value)}
                placeholder="prompt identifier"
                className="h-9"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="has-templates">Templates</Label>
              <label
                htmlFor="has-templates"
                className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 cursor-pointer"
              >
                <input
                  id="has-templates"
                  type="checkbox"
                  checked={hasTemplatesOnly}
                  onChange={(event) => setHasTemplatesOnly(event.target.checked)}
                  className="h-4 w-4 rounded border border-border text-primary focus:ring-primary"
                />
                <span className="text-sm text-muted-foreground">
                  Has template usages
                </span>
              </label>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="page-size">Page size</Label>
              <Select
                value={String(pageSize)}
                onValueChange={(value) => setPageSize(Number(value))}
              >
                <SelectTrigger id="page-size" className="h-9">
                  <SelectValue placeholder="25" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="25">25</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <Button variant="ghost" size="sm" onClick={handleResetFilters} className="w-full">
                Clear filters
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <ExecutionsTable
          executions={executions}
          loading={loading}
          error={error}
          offset={offset}
          limit={limit}
          total={total}
          onRowClick={handleRowClick}
          onPrevPage={() => setOffset(Math.max(0, offset - limit))}
          onNextPage={() => setOffset(offset + limit)}
          onRefresh={refresh}
        />
      </div>
    </div>
  );
}
