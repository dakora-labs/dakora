import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi';
import { OptimizationProgress } from '@/components/optimization/OptimizationProgress';
import { OptimizationResults } from '@/components/optimization/OptimizationResults';
import { OptimizationHistory } from '@/components/optimization/OptimizationHistory';
import type { Template, OptimizePromptResponse, OptimizationRunRecord } from '@/types';

export function OptimizePromptPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { api, projectId, projectSlug, contextLoading } = useAuthenticatedApi();
  const promptId = searchParams.get('prompt');
  const runId = searchParams.get('run');

  const [prompt, setPrompt] = useState<Template | null>(null);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [history, setHistory] = useState<OptimizationRunRecord[]>([]);
  const [selectedRun, setSelectedRun] = useState<OptimizationRunRecord | null>(null);
  const [newResult, setNewResult] = useState<OptimizePromptResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (contextLoading || !projectId || !projectSlug) return;

    if (!promptId) {
      navigate(`/project/${projectSlug}/prompts`);
      return;
    }

    const loadData = async () => {
      try {
        // Load prompt and history in parallel
        const [promptData, historyData] = await Promise.all([
          api.getPrompt(projectId, promptId),
          api.getOptimizationRuns(projectId, promptId),
        ]);

        setPrompt(promptData);
        setHistory(historyData.optimization_runs);

        // If there's a run ID in the URL, select that run
        if (runId) {
          const run = historyData.optimization_runs.find(r => r.optimization_id === runId);
          if (run) {
            setSelectedRun(run);
          }
        }

        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
        setLoading(false);
      }
    };

    loadData();
  }, [promptId, runId, navigate, api, projectId, projectSlug, contextLoading]);

  const handleRunOptimization = async () => {
    if (!projectId || !prompt) return;

    try {
      setOptimizing(true);
      setError('');
      setSelectedRun(null);
      setNewResult(null);

      const response = await api.optimizePrompt(projectId, prompt.id, {
        test_cases: null,
      });

      setNewResult(response);

      // Reload history to show the new run
      const historyData = await api.getOptimizationRuns(projectId, prompt.id);
      setHistory(historyData.optimization_runs);

      // Update URL to show the new run
      setSearchParams({ prompt: promptId!, run: response.optimization_id });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to optimize prompt');
    } finally {
      setOptimizing(false);
    }
  };

  const handleSelectRun = (run: OptimizationRunRecord) => {
    setSelectedRun(run);
    setNewResult(null);
    setSearchParams({ prompt: promptId!, run: run.optimization_id });
  };

  const handleBack = () => {
    navigate(`/project/${projectSlug}/prompt/edit?prompt=${promptId}`);
  };

  const handleKeepOriginal = () => {
    handleBack();
  };

  const handleApply = () => {
    // TODO: Actually apply the optimization by updating the prompt template
    navigate(`/project/${projectSlug}/prompt/edit?prompt=${promptId}&applied=true`);
  };

  // Determine what to show
  const displayResult = newResult || (selectedRun ? {
    optimization_id: selectedRun.optimization_id,
    original_template: selectedRun.original_template,
    optimized_template: selectedRun.optimized_template,
    insights: selectedRun.insights,
    token_reduction_pct: selectedRun.token_reduction_pct,
    created_at: selectedRun.created_at,
  } : null);

  if (loading || contextLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-background">
        <p className="text-muted-foreground">Loading prompt...</p>
      </div>
    );
  }

  if (!prompt) {
    return (
      <div className="h-full flex items-center justify-center bg-background">
        <p className="text-muted-foreground">Prompt not found</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex flex-col bg-background">
        <div className="border-b border-border bg-card px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleBack}
              className="gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>
            <div className="h-4 w-px bg-border" />
            <h1 className="text-lg font-semibold">Optimize Prompt</h1>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-4 max-w-md">
            <div className="text-destructive text-sm bg-destructive/10 border border-destructive/20 rounded-lg p-4">
              {error}
            </div>
            <Button onClick={handleBack}>Go Back</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="border-b border-border bg-card px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          <div className="h-4 w-px bg-border" />
          <h1 className="text-lg font-semibold">Optimize Prompt</h1>
          {prompt && (
            <span className="text-sm text-muted-foreground">
              {prompt.id}
            </span>
          )}
        </div>
        {!optimizing && (
          <Button
            onClick={handleRunOptimization}
            className="gap-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            <Sparkles className="w-4 h-4" />
            Run New Optimization
          </Button>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* History Sidebar */}
        <OptimizationHistory
          history={history}
          selectedRunId={selectedRun?.optimization_id || newResult?.optimization_id}
          onSelectRun={handleSelectRun}
          isOptimizing={optimizing}
        />

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {optimizing && <OptimizationProgress />}

          {!optimizing && !displayResult && history.length === 0 && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-4 max-w-md px-6">
                <Sparkles className="w-16 h-16 mx-auto text-purple-500" />
                <h2 className="text-xl font-semibold">No optimization runs yet</h2>
                <p className="text-sm text-muted-foreground">
                  Click "Run New Optimization" to improve this prompt with AI
                </p>
              </div>
            </div>
          )}

          {!optimizing && displayResult && (
            <OptimizationResults
              original={prompt.template}
              optimized={displayResult.optimized_template}
              insights={displayResult.insights}
              tokenReduction={displayResult.token_reduction_pct}
              onKeepOriginal={handleKeepOriginal}
              onApply={handleApply}
              isHistoricalRun={!!selectedRun}
            />
          )}
        </div>
      </div>
    </div>
  );
}