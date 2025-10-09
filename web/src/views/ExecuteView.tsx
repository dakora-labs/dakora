import { useState, useEffect } from 'react';
import { TemplateList } from '../components/TemplateList';
import { useTemplate } from '../hooks/useApi';
import { Rocket, Plus, X, Loader2, CheckCircle, AlertCircle, Copy, DollarSign, Clock, Hash } from 'lucide-react';
import { Card, CardContent, CardTitle, CardHeader, CardDescription } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { cn } from '@/lib/utils';

interface ModelConfig {
  id: string;
  name: string;
  temperature: number;
  maxTokens: number;
}

interface ExecutionResult {
  model: string;
  output?: string;
  provider?: string;
  tokens_in?: number;
  tokens_out?: number;
  cost_usd?: number;
  latency_ms?: number;
  error?: string;
}

interface ExecutionResponse {
  results: ExecutionResult[];
  total_cost_usd: number;
  total_time_ms: number;
  successful_count: number;
  failed_count: number;
}

export function ExecuteView() {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [models, setModels] = useState<ModelConfig[]>([{
    id: '1',
    name: '',
    temperature: 0.7,
    maxTokens: 1000
  }]);
  const [inputs, setInputs] = useState<Record<string, any>>({});
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecutionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const templateData = useTemplate(selectedTemplateId);
  const template = templateData?.template ?? null;

  useEffect(() => {
    if (template) {
      const initialInputs: Record<string, any> = {};
      Object.entries(template.inputs).forEach(([name, spec]: [string, any]) => {
        initialInputs[name] = spec.default || '';
      });
      setInputs(initialInputs);
      setExecutionResult(null);
      setError(null);
    }
  }, [template]);

  const addModel = () => {
    if (models.length < 3) {
      setModels([...models, {
        id: Date.now().toString(),
        name: '',
        temperature: 0.7,
        maxTokens: 1000
      }]);
    }
  };

  const removeModel = (id: string) => {
    if (models.length > 1) {
      setModels(models.filter(m => m.id !== id));
    }
  };

  const updateModel = (id: string, updates: Partial<ModelConfig>) => {
    setModels(models.map(m => m.id === id ? { ...m, ...updates } : m));
  };

  const handleExecute = async () => {
    if (!selectedTemplateId) {
      return;
    }

    const modelNames = models.map(m => m.name).filter(n => n.trim() !== '');
    if (modelNames.length === 0) {
      return;
    }

    setExecuting(true);
    setError(null);
    try {
      const response = await fetch(`/api/templates/${selectedTemplateId}/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          inputs,
          models: modelNames,
          temperature: models[0].temperature,
          max_tokens: models[0].maxTokens,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();
      setExecutionResult(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Execution failed';
      console.error('Execution failed:', errorMessage);
      setError(errorMessage);
    } finally {
      setExecuting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const sidebar = (
    <TemplateList
      selectedTemplate={selectedTemplateId}
      onSelectTemplate={setSelectedTemplateId}
    />
  );

  const content = !template ? (
    <div className="flex-1 flex items-center justify-center bg-muted/10">
      <Card className="w-full max-w-md mx-4 text-center animate-in fade-in-50 duration-500">
        <CardContent className="pt-6 pb-6">
          <Rocket className="w-12 h-12 text-muted-foreground/50 mx-auto mb-4" aria-hidden="true" />
          <CardTitle className="mb-2">Execute Templates with LLMs</CardTitle>
          <p className="text-sm text-muted-foreground">
            Select a template from the sidebar to execute it against one or more LLM models
          </p>
        </CardContent>
      </Card>
    </div>
  ) : (
    <ScrollArea className="h-full">
      <main className="p-4 md:p-6 space-y-6 max-w-6xl mx-auto">
        <div>
          <h1 className="text-2xl font-bold">{template.id}</h1>
          {template.description && (
            <p className="text-sm text-muted-foreground mt-1">{template.description}</p>
          )}
        </div>

        <Separator />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Object.keys(template.inputs).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Template Inputs</CardTitle>
                <CardDescription>Fill in the required values for your template</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {Object.entries(template.inputs).map(([name, spec]: [string, any]) => (
                  <div key={name} className="space-y-2">
                    <Label htmlFor={name}>
                      {name}
                      {spec.required && <span className="text-destructive ml-1">*</span>}
                    </Label>
                    {spec.type === 'string' && (
                      <Textarea
                        id={name}
                        value={inputs[name] || ''}
                        onChange={(e) => setInputs({ ...inputs, [name]: e.target.value })}
                        placeholder={spec.default || `Enter ${name}...`}
                        className="min-h-[100px] font-mono text-sm"
                      />
                    )}
                    {spec.type === 'number' && (
                      <Input
                        id={name}
                        type="number"
                        value={inputs[name] || ''}
                        onChange={(e) => setInputs({ ...inputs, [name]: parseFloat(e.target.value) })}
                        placeholder={spec.default?.toString() || '0'}
                      />
                    )}
                    {spec.type === 'boolean' && (
                      <div className="flex items-center space-x-2">
                        <input
                          id={name}
                          type="checkbox"
                          checked={inputs[name] || false}
                          onChange={(e) => setInputs({ ...inputs, [name]: e.target.checked })}
                          className="w-4 h-4 rounded border-gray-300"
                        />
                        <Label htmlFor={name} className="text-sm font-normal">
                          {spec.default !== undefined ? `Default: ${spec.default}` : 'Enable'}
                        </Label>
                      </div>
                    )}
                    {(spec.type === 'array<string>' || spec.type?.startsWith('array')) && (
                      <Textarea
                        id={name}
                        value={Array.isArray(inputs[name]) ? inputs[name].join('\n') : ''}
                        onChange={(e) => setInputs({ ...inputs, [name]: e.target.value.split('\n').filter(line => line.trim()) })}
                        placeholder={Array.isArray(spec.default) ? spec.default.join('\n') : 'Enter items (one per line)'}
                        className="min-h-[100px] font-mono text-sm"
                      />
                    )}
                    {spec.type === 'object' && (
                      <Textarea
                        id={name}
                        value={typeof inputs[name] === 'object' ? JSON.stringify(inputs[name], null, 2) : ''}
                        onChange={(e) => {
                          try {
                            const parsed = JSON.parse(e.target.value);
                            setInputs({ ...inputs, [name]: parsed });
                          } catch {
                            // Keep current value if invalid JSON
                          }
                        }}
                        placeholder={spec.default ? JSON.stringify(spec.default, null, 2) : '{}'}
                        className="min-h-[100px] font-mono text-sm"
                      />
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Model Configuration</CardTitle>
              <CardDescription>Configure 1-3 models to execute in parallel</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
            {models.map((model, index) => (
              <div key={model.id} className="space-y-4 p-4 border rounded-lg relative">
                {models.length > 1 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 h-6 w-6"
                    onClick={() => removeModel(model.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}

                <div className="space-y-2">
                  <Label htmlFor={`model-${model.id}`}>
                    Model {index + 1}
                    {index === 0 && <span className="text-destructive ml-1">*</span>}
                  </Label>
                  <Input
                    id={`model-${model.id}`}
                    value={model.name}
                    onChange={(e) => updateModel(model.id, { name: e.target.value })}
                    placeholder="e.g., gpt-4, claude-3-5-sonnet, gemini-2.0-flash"
                    list="common-models"
                  />
                  <datalist id="common-models">
                    <option value="gpt-4" />
                    <option value="gpt-4-turbo" />
                    <option value="gpt-3.5-turbo" />
                    <option value="claude-3-5-sonnet-20241022" />
                    <option value="claude-3-opus-20240229" />
                    <option value="gemini-2.0-flash-exp" />
                    <option value="gemini-1.5-pro" />
                  </datalist>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`temp-${model.id}`}>
                      Temperature: {model.temperature}
                    </Label>
                    <Input
                      id={`temp-${model.id}`}
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={model.temperature}
                      onChange={(e) => updateModel(model.id, { temperature: parseFloat(e.target.value) })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`tokens-${model.id}`}>Max Tokens</Label>
                    <Input
                      id={`tokens-${model.id}`}
                      type="number"
                      value={model.maxTokens}
                      onChange={(e) => updateModel(model.id, { maxTokens: parseInt(e.target.value) })}
                      min="1"
                      max="8000"
                    />
                  </div>
                </div>
              </div>
            ))}

            {models.length < 3 && (
              <Button
                variant="outline"
                size="sm"
                onClick={addModel}
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Model (max 3)
              </Button>
            )}
            </CardContent>
          </Card>
        </div>

        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            {models.filter(m => m.name.trim()).length} model(s) configured
          </div>
          <Button
            onClick={handleExecute}
            disabled={executing || !models[0].name.trim()}
            size="lg"
            className="min-w-[140px]"
          >
            {executing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Rocket className="h-4 w-4 mr-2" />
                Execute
              </>
            )}
          </Button>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>Execution failed:</strong> {error}
            </AlertDescription>
          </Alert>
        )}

        {executionResult && (
          <>
            <Separator />

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Execution Results</CardTitle>
                  <div className="flex items-center gap-4 text-sm">
                    <Badge variant="outline" className="gap-1">
                      <CheckCircle className="h-3 w-3 text-green-600" />
                      {executionResult.successful_count}/{executionResult.results.length}
                    </Badge>
                    <Badge variant="outline" className="gap-1">
                      <Clock className="h-3 w-3" />
                      {executionResult.total_time_ms}ms
                    </Badge>
                    <Badge variant="outline" className="gap-1">
                      <DollarSign className="h-3 w-3" />
                      ${executionResult.total_cost_usd.toFixed(4)}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className={cn(
                  "grid gap-4",
                  executionResult.results.length === 1 ? "grid-cols-1" :
                  executionResult.results.length === 2 ? "grid-cols-1 lg:grid-cols-2" :
                  "grid-cols-1 lg:grid-cols-3"
                )}>
                  {executionResult.results.map((result, index) => (
                    <Card key={index} className={cn(
                      "border-2",
                      result.error ? "border-destructive" : "border-green-600/20"
                    )}>
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <CardTitle className="text-sm font-mono truncate">
                              {result.model}
                            </CardTitle>
                            {result.provider && (
                              <CardDescription className="text-xs mt-1">
                                {result.provider}
                              </CardDescription>
                            )}
                          </div>
                          {result.error ? (
                            <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0" />
                          ) : (
                            <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                          )}
                        </div>

                        {!result.error && (
                          <div className="flex flex-wrap gap-2 pt-2">
                            <Badge variant="secondary" className="text-xs gap-1">
                              <Clock className="h-3 w-3" />
                              {result.latency_ms}ms
                            </Badge>
                            {result.cost_usd !== undefined && (
                              <Badge variant="secondary" className="text-xs gap-1">
                                <DollarSign className="h-3 w-3" />
                                ${result.cost_usd.toFixed(4)}
                              </Badge>
                            )}
                            {result.tokens_in !== undefined && (
                              <Badge variant="secondary" className="text-xs gap-1">
                                <Hash className="h-3 w-3" />
                                {result.tokens_in}→{result.tokens_out}
                              </Badge>
                            )}
                          </div>
                        )}
                      </CardHeader>
                      <CardContent className="pt-0">
                        {result.error ? (
                          <Alert variant="destructive">
                            <AlertDescription className="text-xs">
                              {result.error}
                            </AlertDescription>
                          </Alert>
                        ) : (
                          <div className="space-y-2">
                            <div className="relative">
                              <ScrollArea className="h-[200px] w-full rounded-md border bg-muted p-3">
                                <pre className="text-xs whitespace-pre-wrap font-mono">
                                  {result.output}
                                </pre>
                              </ScrollArea>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="absolute top-2 right-2 h-6 w-6"
                                onClick={() => copyToClipboard(result.output || '')}
                              >
                                <Copy className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </ScrollArea>
  );

  return { sidebar, content };
}