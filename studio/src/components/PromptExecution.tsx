import { useState, useEffect, useMemo, type MouseEvent as ReactMouseEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, Play, Loader2, Copy, Clock, Coins, Zap, CheckCircle2, XCircle, AlertCircle, ArrowRight, Download, Upload, BarChart3, Code, FileText, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectGroup, SelectLabel } from '@/components/ui/select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useModels, useExecutePrompt, useExecutionHistory } from '@/hooks/useApi';
import type { ExecutionResponse, ExecutionHistoryItem, InputSpec } from '@/types';
import { ProviderBadge } from './ProviderBadge';
import { parseApiDate } from '@/utils/format';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface PromptExecutionProps {
  projectId: string;
  promptId: string;
  inputs: Record<string, InputSpec>;
  projectSlug?: string | null;
}

export function PromptExecution({ projectId, promptId, inputs, projectSlug }: PromptExecutionProps) {
  const navigate = useNavigate();
  const resolvedProjectSlug = projectSlug ?? 'default';
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [inputValues, setInputValues] = useState<Record<string, string>>({});
  const [lastExecution, setLastExecution] = useState<ExecutionResponse | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [invalidInputs, setInvalidInputs] = useState<Set<string>>(new Set());
  const [showRaw, setShowRaw] = useState(false);
  const [copied, setCopied] = useState(false);

  const { models, loading: modelsLoading } = useModels(projectId);
  const { execute, loading: executing, error: executeError } = useExecutePrompt(projectId);
  const { history, refetch: refetchHistory } = useExecutionHistory(projectId, promptId);

  // Detect if content looks like markdown
  const hasMarkdownSyntax = (content: string): boolean => {
    const markdownPatterns = [
      /^#{1,6}\s/m,
      /\*\*.*\*\*/,
      /\*.*\*/,
      /\[.*\]\(.*\)/,
      /^[-*+]\s/m,
      /^\d+\.\s/m,
      /```/,
      /`[^`]+`/,
      /^>\s/m,
      /\|.*\|/,
    ];
    
    return markdownPatterns.some(pattern => pattern.test(content));
  };

  const hasMarkdown = lastExecution?.content ? hasMarkdownSyntax(lastExecution.content) : false;

  const modelsByProvider = useMemo(() => {
    if (!models) return {};
    return models.models.reduce((acc, model) => {
      if (!acc[model.provider]) {
        acc[model.provider] = [];
      }
      acc[model.provider].push(model);
      return acc;
    }, {} as Record<string, typeof models.models>);
  }, [models]);

  const selectedModelInfo = useMemo(() => {
    return models?.models.find((m) => m.id === selectedModel);
  }, [models, selectedModel]);

  useEffect(() => {
    if (models && !selectedModel && models.default_model) {
      setSelectedModel(models.default_model);
    }
  }, [models, selectedModel]);

  useEffect(() => {
    const defaultValues: Record<string, string> = {};

    const serializeDefault = (value: unknown): string => {
      if (value === undefined || value === null) {
        return '';
      }
      if (typeof value === 'object') {
        try {
          return JSON.stringify(value, null, 2);
        } catch {
          return '';
        }
      }
      return String(value);
    };

    Object.entries(inputs).forEach(([key, spec]) => {
      if (spec.default !== undefined) {
        defaultValues[key] = serializeDefault(spec.default);
        return;
      }

      switch (spec.type) {
        case 'string':
          defaultValues[key] = '';
          break;
        case 'number':
          defaultValues[key] = '';
          break;
        case 'boolean':
          defaultValues[key] = 'false';
          break;
        case 'array<string>':
          defaultValues[key] = '';
          break;
        case 'object':
          defaultValues[key] = '';
          break;
        default:
          defaultValues[key] = '';
      }
    });
    setInputValues(defaultValues);
  }, [inputs]);

  const handleExecute = async () => {
    if (!selectedModelInfo) return;

    const missingInputs = Object.entries(inputs)
      .filter(([key, spec]) => {
        const raw = inputValues[key];
        if (!spec.required) {
          return false;
        }
        return raw === undefined || raw === null || String(raw).trim() === '';
      })
      .map(([key]) => key);

    if (missingInputs.length > 0) {
      if (!isExpanded) {
        setIsExpanded(true);
        return;
      }
      setInvalidInputs(new Set(missingInputs));
      return;
    }

    setInvalidInputs(new Set());

    const parseErrorKeys: string[] = [];
    const transformedInputs: Record<string, unknown> = {};

    const parseArray = (value: string) => {
      return value
        .split(/\r?\n|,/)
        .map((item) => item.trim())
        .filter((item) => item.length > 0);
    };

    Object.entries(inputs).forEach(([key, spec]) => {
      const rawValue = inputValues[key];
      if (rawValue === undefined || String(rawValue).trim() === '') {
        // skip optional empty values
        return;
      }

      let parsed: unknown = rawValue;
      const trimmed = rawValue.trim();

      try {
        switch (spec.type) {
          case 'number': {
            const numeric = Number(trimmed);
            if (Number.isNaN(numeric)) {
              throw new Error('Invalid number');
            }
            parsed = numeric;
            break;
          }
          case 'boolean': {
            const lowered = trimmed.toLowerCase();
            parsed = lowered === 'true' || lowered === '1' || lowered === 'yes';
            break;
          }
          case 'array<string>':
            parsed = parseArray(trimmed);
            break;
          case 'object':
            parsed = JSON.parse(trimmed);
            break;
          default:
            parsed = rawValue;
        }
      } catch {
        parseErrorKeys.push(key);
      }

      if (!parseErrorKeys.includes(key)) {
        transformedInputs[key] = parsed;
      }
    });

    if (parseErrorKeys.length > 0) {
      setInvalidInputs(new Set(parseErrorKeys));
      return;
    }

    try {
      const result = await execute(promptId, {
        inputs: transformedInputs,
        model: selectedModel,
        provider: selectedModelInfo.provider,
      });
      setLastExecution(result);
      setShowResults(true);
      setIsExpanded(false);
      refetchHistory?.();
    } catch (err) {
      console.error('Execution failed:', err);
      setIsExpanded(true);
    }
  };

  const handleViewTrace = (event: ReactMouseEvent<HTMLButtonElement>, traceId: string) => {
    event.stopPropagation();
    navigate(`/project/${resolvedProjectSlug}/executions/${traceId}`);
  };

  const formatCost = (cost?: number | null) => {
    if (cost === undefined || cost === null || Number.isNaN(cost)) {
      return '—';
    }
    return cost < 0.01 ? `$${cost.toFixed(4)}` : `$${cost.toFixed(3)}`;
  };

  const formatLatency = (ms?: number | null) => {
    if (ms === undefined || ms === null || Number.isNaN(ms)) {
      return '—';
    }
    return ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms}ms`;
  };

  const formatDate = (dateStr: string) => {
    const date = parseApiDate(dateStr);
    if (!date) return '—';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 60) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  const getStatusIcon = (status: ExecutionHistoryItem['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />;
      case 'error':
        return <XCircle className="w-3.5 h-3.5 text-red-500" />;
      case 'quota_exceeded':
        return <AlertCircle className="w-3.5 h-3.5 text-amber-500" />;
    }
  };

  return (
    <div className="flex flex-col">
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <div className="border-b border-border bg-muted/30 px-4 py-2.5">
          <div className="flex items-center gap-3">
            {!modelsLoading && models && (
              <>
                {selectedModelInfo && (
                  <ProviderBadge provider={selectedModelInfo.provider} size="sm" />
                )}
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger className="h-7 w-[180px] text-xs">
                    <SelectValue placeholder="Select model" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(modelsByProvider).map(([provider, providerModels]) => (
                      <SelectGroup key={provider}>
                        <SelectLabel className="text-xs font-semibold capitalize">
                          {provider.replace('_', ' ')}
                        </SelectLabel>
                        {providerModels.map((model) => (
                          <SelectItem key={model.id} value={model.id} className="text-xs">
                            {model.name}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    ))}
                  </SelectContent>
                </Select>
              </>
            )}

            <Separator orientation="vertical" className="h-4" />

            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1.5 text-xs"
                disabled={Object.keys(inputs).length === 0}
              >
                {Object.keys(inputs).length === 0 ? 'No inputs' : 'Configure inputs'}
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
              </Button>
            </CollapsibleTrigger>

            <Button
              size="sm"
              onClick={handleExecute}
              disabled={executing || modelsLoading || !selectedModel}
              className="h-7 gap-1.5 text-xs"
            >
              {executing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5" />
              )}
              {executing ? 'Running...' : 'Run Prompt'}
            </Button>
          </div>
        </div>

        <CollapsibleContent>
          <div className="border-b border-border bg-muted/10 px-4 py-3 space-y-3 animate-in slide-in-from-top-2 duration-200">
            {Object.entries(inputs).map(([key, spec]) => {
              const isInvalid = invalidInputs.has(key);
              const rawValue = inputValues[key];
              const displayValue =
                rawValue === undefined || rawValue === null ? '' : rawValue;

              return (
                <div key={key} className="flex items-center gap-3">
                  <label className={`text-xs font-medium w-24 shrink-0 ${isInvalid ? 'text-destructive' : ''}`}>
                    {key}
                  </label>
                  <input
                    type={spec.type === 'number' ? 'number' : 'text'}
                    value={displayValue}
                    onChange={(e) => {
                      setInputValues({
                        ...inputValues,
                        [key]: e.target.value,
                      });
                      if (invalidInputs.has(key)) {
                        const newInvalid = new Set(invalidInputs);
                        newInvalid.delete(key);
                        setInvalidInputs(newInvalid);
                      }
                    }}
                    placeholder={spec.required ? 'Required' : 'Optional'}
                    className={`flex-1 h-7 px-2 text-xs border rounded bg-background transition-all ${
                      isInvalid
                        ? 'border-destructive focus:ring-destructive focus:ring-2 animate-shake'
                        : 'border-border'
                    }`}
                  />
                  <Badge variant="outline" className="text-xs">
                    {spec.type}
                  </Badge>
                </div>
              );
            })}
          </div>
        </CollapsibleContent>
      </Collapsible>

      {executeError && (
        <div className="border-b border-destructive/20 bg-destructive/10 px-4 py-2">
          <p className="text-xs text-destructive">{executeError}</p>
        </div>
      )}

      {showResults && lastExecution && (
        <Collapsible defaultOpen>
          <div className="border-b border-border bg-card">
            <CollapsibleTrigger asChild>
              <div className="px-4 py-2.5 flex items-center gap-2 cursor-pointer hover:bg-muted/30 transition-colors">
                <ChevronDown className="w-4 h-4 text-muted-foreground transition-transform" />
                <span className="text-sm font-medium">Execution Results</span>
              </div>
            </CollapsibleTrigger>

            <CollapsibleContent>
              <div className="px-4 py-3 space-y-3 animate-in slide-in-from-top-2 duration-250">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">Response</span>
                    <div className="flex items-center gap-2">
                      {hasMarkdown && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setShowRaw(!showRaw)}
                          className="h-6 gap-1.5 text-xs"
                        >
                          {showRaw ? (
                            <>
                              <FileText className="w-3 h-3" />
                              Markdown
                            </>
                          ) : (
                            <>
                              <Code className="w-3 h-3" />
                              Raw
                            </>
                          )}
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText(lastExecution.content);
                          setCopied(true);
                          setTimeout(() => setCopied(false), 2000);
                        }}
                        className="h-6 gap-1.5 text-xs"
                      >
                        {copied ? (
                          <>
                            <Check className="w-3 h-3" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                  <div className="p-3 bg-muted/30 rounded border border-border">
                    {showRaw || !hasMarkdown ? (
                      <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                        {lastExecution.content}
                      </pre>
                    ) : (
                      <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {lastExecution.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                </div>

                <Separator />

                <div className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Metrics</span>
                  <div className="flex flex-wrap gap-3">
                    <div className="flex items-center gap-2">
                      <ProviderBadge provider={lastExecution.provider} size="sm" />
                      <Badge variant="outline" className="text-xs h-5">
                        {lastExecution.model}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 px-2.5 py-1.5 bg-muted/30 rounded border border-border">
                      <div className="flex items-center gap-1">
                        <Download className="w-3 h-3 text-blue-500" />
                        <span className="text-xs font-medium">{lastExecution.metrics.tokens_input}</span>
                      </div>
                      <ArrowRight className="w-3 h-3 text-muted-foreground" />
                      <div className="flex items-center gap-1">
                        <Upload className="w-3 h-3 text-green-500" />
                        <span className="text-xs font-medium">{lastExecution.metrics.tokens_output}</span>
                      </div>
                      <Separator orientation="vertical" className="h-3" />
                      <div className="flex items-center gap-1">
                        <Zap className="w-3 h-3 text-muted-foreground" />
                        <span className="text-xs font-medium text-muted-foreground">{lastExecution.metrics.tokens_total}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-muted/30 rounded border border-border">
                      <Coins className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="text-xs font-medium">
                        {formatCost(lastExecution.metrics.cost_usd)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-muted/30 rounded border border-border">
                      <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="text-xs font-medium">
                        {formatLatency(lastExecution.metrics.latency_ms)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CollapsibleContent>
          </div>
        </Collapsible>
      )}

      {history && history.executions.length > 0 && (
        <Collapsible defaultOpen={false}>
          <div className="border-b border-border bg-card">
            <CollapsibleTrigger asChild>
              <div className="px-4 py-2.5 flex items-center gap-2 cursor-pointer hover:bg-muted/30 transition-colors">
                <ChevronDown className="w-4 h-4 text-muted-foreground transition-transform" />
                <span className="text-sm font-medium">Run History</span>
                <Badge variant="secondary" className="text-xs h-5">
                  {history.total}
                </Badge>
              </div>
            </CollapsibleTrigger>

            <CollapsibleContent>
              <div className="divide-y divide-border">
                {history.executions.map((exec) => (
                  <div
                    key={exec.execution_id}
                    className="px-4 py-2.5 hover:bg-muted/30 transition-colors cursor-pointer flex items-center gap-3"
                    onClick={() => {
                      if (exec.output_text && exec.metrics) {
                        setLastExecution({
                          execution_id: exec.execution_id,
                          trace_id: exec.trace_id ?? null,
                          content: exec.output_text,
                          metrics: exec.metrics,
                          model: exec.model,
                          provider: exec.provider,
                          created_at: exec.created_at,
                        });
                        setShowResults(true);
                      }
                    }}
                  >
                    {getStatusIcon(exec.status)}
                    <span className="text-xs text-muted-foreground w-16">{formatDate(exec.created_at)}</span>
                    <ProviderBadge provider={exec.provider} size="sm" showIcon={false} />
                    <Badge variant="outline" className="text-xs h-5">
                      {exec.model}
                    </Badge>
                    {exec.metrics?.latency_ms && (
                      <span className="text-xs text-muted-foreground">
                        {formatLatency(exec.metrics.latency_ms)}
                      </span>
                    )}
                    {exec.metrics?.cost_usd !== undefined && (
                      <span className="text-xs text-muted-foreground">
                        {formatCost(exec.metrics.cost_usd)}
                      </span>
                    )}
                    {exec.trace_id && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="ml-auto h-6 gap-1 text-xs"
                        onClick={(event) => handleViewTrace(event, exec.trace_id!)}
                      >
                        <BarChart3 className="w-3 h-3" />
                        View trace
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </div>
        </Collapsible>
      )}
    </div>
  );
}
