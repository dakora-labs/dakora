import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Lightbulb, TrendingDown, ArrowRight } from 'lucide-react';
import { DiffView } from './DiffView';
import { ImprovementInsights } from './ImprovementInsights';
import type { OptimizationInsight } from '@/types';

interface OptimizationResultsProps {
  original: string;
  optimized: string;
  insights: OptimizationInsight[];
  tokenReduction: number;
  onKeepOriginal: () => void;
  onApply: () => void;
  isHistoricalRun?: boolean;
}

export function OptimizationResults({
  original,
  optimized,
  insights,
  tokenReduction,
  onKeepOriginal,
  onApply,
  isHistoricalRun = false,
}: OptimizationResultsProps) {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Split-screen comparison */}
      <div className="flex-shrink-0 grid grid-cols-2 gap-0 border-b border-border" style={{ height: '40vh' }}>
        <div className="border-r border-border overflow-auto">
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-muted-foreground">
                Your Original Prompt
              </h2>
            </div>
            <Card className="p-4 bg-muted/30">
              <pre className="text-sm font-mono whitespace-pre-wrap text-muted-foreground leading-relaxed">
                {original}
              </pre>
            </Card>
          </div>
        </div>

        <div className="overflow-auto bg-gradient-to-br from-purple-50/30 to-pink-50/30">
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                Optimized Version
              </h2>
              {tokenReduction > 0 && (
                <Badge className="bg-gradient-to-r from-green-500 to-emerald-500 text-white gap-1.5">
                  <TrendingDown className="w-3.5 h-3.5" />
                  {tokenReduction.toFixed(1)}% fewer tokens
                </Badge>
              )}
            </div>
            <Card className="p-4 bg-white shadow-sm border-purple-100">
              <pre className="text-sm font-mono whitespace-pre-wrap leading-relaxed">
                {optimized}
              </pre>
            </Card>
          </div>
        </div>
      </div>

      {/* Scrollable details section */}
      <div className="flex-1 overflow-auto">
        <div className="p-6 space-y-6 max-w-7xl mx-auto pb-12">
          <div>
            <DiffView original={original} optimized={optimized} />
          </div>

          <div>
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="w-5 h-5 text-amber-500" />
              <h3 className="text-base font-semibold">Key Improvements</h3>
            </div>
            <ImprovementInsights insights={insights} />
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-center gap-4 pt-6 pb-8 border-t border-border">
            {!isHistoricalRun && (
              <Button
                variant="outline"
                size="lg"
                onClick={onKeepOriginal}
                className="min-w-[180px]"
              >
                Keep Original
              </Button>
            )}
            <Button
              size="lg"
              onClick={onApply}
              className="min-w-[180px] gap-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            >
              Apply Optimization
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}