import { Check } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { OptimizationInsight } from '@/types';

interface ImprovementInsightsProps {
  insights: OptimizationInsight[];
}

const categoryColors: Record<string, string> = {
  clarity: 'bg-blue-100 text-blue-700 border-blue-200',
  specificity: 'bg-purple-100 text-purple-700 border-purple-200',
  efficiency: 'bg-green-100 text-green-700 border-green-200',
  structure: 'bg-amber-100 text-amber-700 border-amber-200',
  default: 'bg-gray-100 text-gray-700 border-gray-200',
};

function getCategoryColor(category: string): string {
  return categoryColors[category.toLowerCase()] || categoryColors.default;
}

export function ImprovementInsights({ insights }: ImprovementInsightsProps) {
  if (insights.length === 0) {
    return (
      <Card className="p-6 bg-muted/30">
        <p className="text-sm text-muted-foreground text-center">
          No specific improvements identified.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {insights.map((insight, index) => (
        <Card
          key={index}
          className="p-4 bg-white hover:shadow-md transition-shadow"
        >
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center mt-0.5">
              <Check className="w-4 h-4" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className={`text-xs font-medium ${getCategoryColor(
                    insight.category
                  )}`}
                >
                  {insight.category}
                </Badge>
              </div>
              <p className="text-sm font-medium text-foreground">
                {insight.description}
              </p>
              {insight.impact && (
                <p className="text-xs text-muted-foreground">
                  Impact: {insight.impact}
                </p>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}