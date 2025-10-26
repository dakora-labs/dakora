import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { TemplateUsageEntry } from '@/types';
import { ChevronDown } from 'lucide-react';
import { useState } from 'react';

interface TemplateUsageListProps {
  templateUsages: TemplateUsageEntry[];
}

export function TemplateUsageList({ templateUsages }: TemplateUsageListProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (templateUsages.length === 0) {
    return null;
  }

  return (
    <Card className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Template Usage</h2>
        <Badge variant="outline" className="text-xs">
          {templateUsages.length} linked template{templateUsages.length === 1 ? '' : 's'}
        </Badge>
      </div>

      <div className="space-y-3">
        {templateUsages
          .slice()
          .sort((a, b) => a.position - b.position)
          .map((usage, index) => {
            const isExpanded = expandedIndex === index;

            return (
              <div
                key={`${usage.promptId}-${usage.version}-${usage.position}`}
                className="border border-border/60 rounded-lg p-3"
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="text-sm font-semibold text-foreground">
                      {usage.promptId}
                      <span className="text-muted-foreground font-normal">
                        @{usage.version}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Position {usage.position + 1}
                    </div>
                  </div>
                  {usage.renderedPrompt && (
                    <button
                      type="button"
                      onClick={() => setExpandedIndex(isExpanded ? null : index)}
                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      <ChevronDown
                        className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      />
                      Rendered prompt
                    </button>
                  )}
                </div>

                {usage.inputs && (
                  <div className="mt-3">
                    <div className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                      Inputs
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(usage.inputs).map(([key, value]) => (
                        <span
                          key={key}
                          className="text-xs bg-muted px-2 py-1 rounded-md border border-border/60"
                        >
                          <span className="font-medium text-muted-foreground">{key}</span>
                          <span className="mx-1 text-muted-foreground/60">=</span>
                          <span className="text-foreground break-all">
                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {isExpanded && usage.renderedPrompt && (
                  <pre className="mt-3 rounded-md bg-background border border-border/60 p-3 text-xs text-foreground/90 overflow-x-auto">
                    {usage.renderedPrompt}
                  </pre>
                )}
              </div>
            );
          })}
      </div>
    </Card>
  );
}
