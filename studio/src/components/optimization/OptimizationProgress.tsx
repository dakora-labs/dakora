import { useEffect, useState } from 'react';
import { Loader2, Sparkles, Brain, Zap } from 'lucide-react';

const steps = [
  { id: 1, label: 'Reading prompt structure', icon: Sparkles },
  { id: 2, label: 'Generating variants', icon: Brain },
  { id: 3, label: 'Testing improvements', icon: Zap },
];

export function OptimizationProgress() {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 1500);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="h-full flex items-center justify-center bg-gradient-to-br from-purple-50/50 via-background to-pink-50/50 overflow-auto">
      <div className="text-center space-y-8 max-w-md px-6 py-12">
        <div className="relative h-24 flex items-center justify-center">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-24 h-24 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-full animate-pulse" />
          </div>
          <div className="relative flex items-center justify-center">
            <Sparkles className="w-12 h-12 text-purple-600 animate-spin-slow" />
          </div>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            Analyzing your prompt
          </h2>
          <p className="text-sm text-muted-foreground">
            Our AI is optimizing your template for clarity and efficiency
          </p>
        </div>

        <div className="space-y-3">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isComplete = index < currentStep;
            const isCurrent = index === currentStep;

            return (
              <div
                key={step.id}
                className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                  isCurrent
                    ? 'bg-purple-100/50 border border-purple-200'
                    : isComplete
                    ? 'bg-green-50/50 border border-green-200'
                    : 'bg-muted/30 border border-transparent'
                }`}
              >
                <div
                  className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
                    isCurrent
                      ? 'bg-purple-500 text-white'
                      : isComplete
                      ? 'bg-green-500 text-white'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {isCurrent ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : isComplete ? (
                    <Icon className="w-4 h-4" />
                  ) : (
                    <Icon className="w-4 h-4" />
                  )}
                </div>
                <span
                  className={`text-sm font-medium ${
                    isCurrent || isComplete
                      ? 'text-foreground'
                      : 'text-muted-foreground'
                  }`}
                >
                  {step.label}
                  {isCurrent && '...'}
                  {isComplete && ' ✓'}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}