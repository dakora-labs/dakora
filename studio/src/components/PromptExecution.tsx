import { useState, useEffect, useMemo } from 'react';
import { ChevronDown, Play, Loader2, Copy, Clock, Coins, Zap, CheckCircle2, XCircle, AlertCircle, ArrowRight, Download, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectGroup, SelectLabel } from '@/components/ui/select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useModels, useExecutePrompt, useExecutionHistory } from '@/hooks/useApi';
import type { ExecutionResponse, ExecutionHistoryItem, InputSpec } from '@/types';
import { ProviderBadge } from './ProviderBadge';

interface PromptExecutionProps {
  projectId: string;
  promptId: string;
  inputs: Record<string, InputSpec>;
}

export function PromptExecution({ projectId, promptId, inputs }: PromptExecutionProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [inputValues, setInputValues] = useState<Record<string, unknown>>({});
  const [lastExecution, setLastExecution] = useState<ExecutionResponse | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [invalidInputs, setInvalidInputs] = useState<Set<string>>(new Set());

  const { models, loading: modelsLoading } = useModels(projectId);
  const { execute, loading: executing, error: executeError } = useExecutePrompt(projectId);
  const { history, refetch: refetchHistory } = useExecutionHistory(projectId, promptId);

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
    const defaultValues: Record<string, unknown> = {};
    Object.entries(inputs).forEach(([key, spec]) => {
      if (spec.default !== undefined) {
        defaultValues[key] = spec.default;
      } else if (spec.type === 'string') {
        defaultValues[key] = '';
      } else if (spec.type === 'number') {
        defaultValues[key] = 0;
      } else if (spec.type === 'boolean') {
        defaultValues[key] = false;
      } else if (spec.type === 'array<string>') {
        defaultValues[key] = [];
      } else if (spec.type === 'object') {
        defaultValues[key] = {};
      }
    });
    setInputValues(defaultValues);
  }, [inputs]);

  const handleExecute = async () => {
    if (!selectedModelInfo) return;

    const missingInputs = Object.entries(inputs)
      .filter(([key, spec]) => spec.required && !inputValues[key])
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

    try {
      const result = await execute(promptId, {
        inputs: inputValues,
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

  const handleCopyOutput = () => {
    if (lastExecution?.content) {
      navigator.clipboard.writeText(lastExecution.content);
    }
  };

  const formatCost = (cost: number) => {
    return cost < 0.01 ? `$${cost.toFixed(4)}` : `$${cost.toFixed(3)}`;
  };

  const formatLatency = (ms: number) => {
    return ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms}ms`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
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

            <Separator orientation="vertical" className="h-4" />

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
              return (
                <div key={key} className="flex items-center gap-3">
                  <label className={`text-xs font-medium w-24 shrink-0 ${isInvalid ? 'text-destructive' : ''}`}>
                    {key}
                  </label>
                  <input
                    type={spec.type === 'number' ? 'number' : 'text'}
                    value={inputValues[key] as string}
                    onChange={(e) => {
                      setInputValues({ ...inputValues, [key]: e.target.value });
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
              <div className="px-4 py-2.5 flex items-center justify-between cursor-pointer hover:bg-muted/30 transition-colors">
                <div className="flex items-center gap-2">
                  <ChevronDown className="w-4 h-4 text-muted-foreground transition-transform" />
                  <span className="text-sm font-medium">Execution Results</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCopyOutput();
                  }}
                  className="h-6 gap-1.5 text-xs"
                >
                  <Copy className="w-3 h-3" />
                  Copy
                </Button>
              </div>
            </CollapsibleTrigger>

            <CollapsibleContent>
              <div className="px-4 py-3 space-y-3 animate-in slide-in-from-top-2 duration-250">
                <div className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">Response</span>
                  <div className="p-3 bg-muted/30 rounded border border-border">
                    <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                      {lastExecution.content}
                    </pre>
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
              <div className="px-4 py-2.5 flex items-center justify-between cursor-pointer hover:bg-muted/30 transition-colors">
                <div className="flex items-center gap-2">
                  <ChevronDown className="w-4 h-4 text-muted-foreground transition-transform" />
                  <span className="text-sm font-medium">Run History</span>
                  <Badge variant="secondary" className="text-xs h-5">
                    {history.total}
                  </Badge>
                </div>
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